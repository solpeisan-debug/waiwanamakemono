"""第21弾v2 致死性不整脈 見るのは5か所（第21弾と同じ作り。分類を「見る場所」に変え、各パターンに「→ 次の対応」）

決まった中身は docs/reel21_v2_spec.md（文言はそのまま使う）、根拠は docs/reel21_v2_evidence.md。

配置：
- 上部：6つのミニ波形（2列×3段、横に読む）
  [モビッツII型, 完全房室ブロック] [ショートラン, 単形性VT] [多形性VT, トルサード・ド・ポワント]
- 中部：いま紹介中の波形（大きく流れる）と、見る場所・名前・次の対応（→ …）
- 下部：6つのミニ波形（2列×3段、横に読む）
  [R on T, 粗いVF] [細かいVF, 心静止] [PEA（ふつうに見える）, PEA（遅く幅広い）]
- 色は「見る場所」ごと：① PとQRSのつながり（黄）② QRSの幅と形（橙）③ T波の上（紫）④ QRSがない（赤）⑤ 波形では分からない（青）

波形は、パターンの周期でくり返す決まった形（乱数の種を固定）。区間の端は0.2秒でなめらかに切りかえる。
II誘導を想定。波形の定義（ev・art・gain・hl）は第21弾と同じ。

使い方:
    python3 make_reel21v2.py --jobs 2     # 書き出し・60fps
    python3 make_reel21v2.py --still 20   # 1コマだけ
    python3 make_reel21v2.py --check      # 検算・タイミング表・字の幅と重なり
    python3 make_reel21v2.py --thumb      # サムネイル（透かしなし）
    python3 make_reel21v2.py --hq         # 高画質（out/reel21_v2_hq.mp4）
"""
import argparse
import math
import os
import subprocess
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
SLOW = 1.0                        # 実際の速さ

BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (70, 82, 82)
LIGHT = (226, 232, 231)
CARD_FILL = (9, 19, 16)
CARD_EDGE = (60, 78, 72)
OPEN_COL = (176, 186, 190)        # 冒頭（タイトルのあいだ）の波形の色。5か所の色がどれも目立つよう、色のない明るい灰色
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)
YEL = (255, 214, 64)

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 見る場所（5か所）。色は場所ごと ---------------------------------------------
PLACES = [
    dict(no='①', name='PとQRSのつながり', col=(255, 212, 90)),
    dict(no='②', name='QRSの幅と形', col=(255, 152, 72)),
    dict(no='③', name='T波の上', col=(200, 150, 255)),
    dict(no='④', name='QRSがない', col=(255, 92, 112)),
    dict(no='⑤', name='波形では分からない', col=(110, 200, 255)),
]

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
RR = 0.80                        # 洞調律 75/分
PR = 0.16                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.022)


def qrs_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_pvc(t):                   # PVC（形A）：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def qrs_vt_rs(t):                 # 単形性VTのQRS（R＋S）。幅 約190ms（LITFL：VTはふつう 160ms をこえる。専門医レビュー 2026-10-09）
    return 0.95*_ga(t, 0.0, 0.026, 0.021) - 0.55*_g(t, 0.070, 0.025)


def qrs_vt(t):                    # 単形性VTの1拍：幅の広いQRS＋逆向きのST-T
    return qrs_vt_rs(t) - 0.38*_ga(t, 0.27, 0.058, 0.045)


def qrs_pvc2(t):                  # PVC（形B）：下向きのQRS、上向きのT（多形性VT用）
    return (-0.80*_ga(t, 0.01, 0.022, 0.026) + 0.25*_g(t, 0.075, 0.020)
            + 0.36*_ga(t, 0.26, 0.060, 0.045))


def qrs_longqt(t):                # QT延長の洞調律：Tが遅く、幅が広い（QT 約0.56秒）
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.24*_ga(t, 0.40, 0.085, 0.060))


def qrs_escape(t):                # 遅く幅の広いQRS（120ms以上）、逆向きのT
    return (0.70*_ga(t, 0.0, 0.030, 0.034) - 0.18*_g(t, 0.085, 0.022)
            - 0.32*_ga(t, 0.34, 0.075, 0.055))


KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍（PEAでも同じ形）
    'Q': (qrs_longqt, p_sinus, PR),         # QT延長の洞調律
    'V': (qrs_pvc, None, 0.0),              # PVC（幅の広いQRS。ショートラン・R on T）
    'X': (qrs_vt, None, 0.0),               # 単形性VTの1拍（もっと幅の広いQRS）
    'W': (qrs_escape, None, 0.0),           # 遅く幅の広いQRS
    'P': (None, p_sinus, 0.0),              # P波だけ
}
SPIKES = {}                                 # この回はペーシングスパイクなし
ALL = [(-1e9, 1e9)]                         # 全部をその色で


# --- 連続した波形（パターンの周期 L でくり返す） ------------------------------------
def _rs(seed):
    return np.random.RandomState(seed)


def band_noise(rel, L, f_lo, f_hi, amp, seed, n_max=400):
    """f_lo〜f_hi Hz の帯域の不規則な揺れ。周期 L でくり返す（周波数は 1/L の整数倍）。RMSが amp。"""
    rs = _rs(seed)
    ks = np.arange(max(1, int(np.ceil(f_lo*L))), int(f_hi*L) + 1)
    if len(ks) > n_max:
        ks = np.sort(rs.choice(ks, n_max, replace=False))
    a = rs.normal(0, 1, len(ks)); ph = rs.uniform(0, 2*np.pi, len(ks))
    out = np.zeros_like(rel)
    for k, ak, pk in zip(ks, a, ph):
        out += ak*np.sin(2*np.pi*k*rel/L + pk)
    return out * amp / np.sqrt(np.sum(a**2)/2 + 1e-9)


# 多形性VT：幅の広いQRSが約230/分で、形・大きさ・向きが1拍ごとに変わる
POLY_N, POLY_L = 15, 4.0
_rs2 = _rs(21)
POLY = [(k*POLY_L/POLY_N + _rs2.uniform(-0.03, 0.03), _rs2.uniform(0.45, 1.15)*(1 if _rs2.rand() < 0.6 else -1),
         _rs2.randint(2)) for k in range(POLY_N)]


def art_poly(rel, L):
    r = np.mod(rel, L)
    out = np.zeros_like(rel)
    for c, a, kind in POLY:
        f = qrs_pvc if kind == 0 else qrs_pvc2
        for sh in (-L, 0.0, L):
            m = np.abs(r - c - sh) < 0.35
            if m.any():
                out[m] += a*f(r[m] - c - sh)
    return out


# トルサード：QT延長の洞調律 → T波の上のPVC（R on T）から、QRSの大きさがねじれるように変わる → 自然に止まる
TDP_A, TDP_B = 1.40, 3.95                  # 周期の中のトルサードの区間（秒）
TDP_F = 4.0                                # 約240/分


def art_tdp(rel, L):
    r = np.mod(rel, L)
    m = (r >= TDP_A - 0.1) & (r <= TDP_B + 0.1)
    out = np.zeros_like(rel)
    if m.any():
        x = r[m] - TDP_A
        dur = TDP_B - TDP_A
        env = np.sin(np.pi*np.clip(x/dur, 0, 1))**0.6                     # だんだん大きく → 小さく
        twist = np.cos(2*np.pi*x/1.25)                                     # 向きがゆっくり反転（ねじれ）
        car = np.sin(2*np.pi*TDP_F*x - 0.4) + 0.35*np.sin(4*np.pi*TDP_F*x)  # 幅の広いQRSが続く形
        out[m] = 0.95*env*twist*car * (x >= 0)
    return out


def gain_tdp(rel, L):                      # トルサードのあいだは洞調律の拍を消す
    r = np.mod(rel, L)
    return np.where((r >= TDP_A - 0.02) & (r < TDP_B + 0.05), 0.0, 1.0)


def art_vf_coarse(rel, L):                 # 粗いVF：3〜9Hzの不規則で大きな揺れ
    env = 0.75 + 0.25*np.sin(2*np.pi*rel/L)
    return env*band_noise(rel, L, 3.0, 9.0, 0.42, 24)


def art_vf_fine(rel, L):                   # 細かいVF：同じ揺れが小さい
    return band_noise(rel, L, 3.5, 10.0, 0.075, 25)


def art_asys(rel, L):                      # 心静止：ほぼまっすぐ（ごくわずかな基線のゆれ）
    return band_noise(rel, L, 0.25, 1.5, 0.012, 26)


SR_SHIFT = 1.2                    # ショートランの拍の並びをずらす長さ（秒）
RONT_C = 0.36                     # R on T：直前のRから PVC の頂点まで（秒）。T波（頂点 0.27秒・終わり 約0.42秒）の下りに乗る


# --- 12パターン（見る場所の順） --------------------------------------------------
# key：中の呼び名（画面には出さない）。place：見る場所（PLACES の番号）。
# act：次の対応（docs/reel21_v2_spec.md の文言そのまま。「 ／ 」で2つの対応）。
# lines：画面での行の分け方。(文字, 続きの行か)。続きの行は矢印なしで字下げ。
#        つなぐと act に戻ることを --check で確かめる。
# narr：ナレーション（下書き。録音前）。
# 波形：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、連続した波形 art・倍率 gain、色を付ける範囲 hl（第21弾と同じ）
PATTERNS = [
    dict(key='モビッツII', place=0, name='モビッツII型',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='PとQRSのつながり。PRは一定のまま、突然QRSが抜ける、モビッツII型。',
         ev=[(0.16, 'N'), (0.96, 'N'), (1.76, 'N'), (2.4, 'P')], L=3.2, hl=[(2.30, 2.52)]),
    dict(key='完全房室ブロック', place=0, name='完全房室ブロック',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='PとQRSが別々に動く、完全房室ブロック。',
         ev=[(k*0.68, 'P') for k in range(10)] + [(0.3 + k*1.7, 'W') for k in range(4)], L=6.8, hl=ALL),
    dict(key='ショートラン', place=1, name='ショートラン',
         act='→ 症状を見て、12誘導。QT、K・Mgなどを確認',
         lines=[('→ 症状を見て、12誘導。QT、K・Mgなどを確認', False)],
         narr='次は、QRSの幅と形。幅広いQRSが3つ以上続いて、自然に止まる。ショートラン。',
         # 第21弾と同じ拍の並び（周期 4.0秒）を 1.2秒うしろへずらしたもの（洞調律3拍 → PVC 3連）。
         # 区間を長くしても、縮んで枠へ移るときに3連が見えている範囲に入るように
         ev=sorted(((r + SR_SHIFT) % 4.0, k) for r, k in
                   [(0, 'N'), (0.8, 'N'), (1.28, 'V'), (1.66, 'V'), (2.04, 'V'), (3.2, 'N')]),
         L=4.0, hl=[(1.19 + SR_SHIFT, 2.46 + SR_SHIFT)]),
    dict(key='単形性VT', place=1, name='単形性VT',
         act='→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。パッド装着 ／ → 脈なしなら人を呼ぶ。CPR＋電気ショック',
         lines=[('→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。', False), ('パッド装着', True),
                ('→ 脈なしなら人を呼ぶ。CPR＋電気ショック', False)],
         narr='速く、幅広く、同じ形。単形性VT。脈のあるなしで、動きが分かれる。',
         ev=[(k*0.32, 'X') for k in range(15)], L=4.8, hl=ALL),
    dict(key='多形性VT', place=1, name='多形性VT',
         act='→ 脈なし：CPR＋電気ショック ／ → 脈あり：人を呼び、パッド装着（続けば脈があってもショック）',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 脈あり：人を呼び、パッド装着', False),
                ('（続けば脈があってもショック）', True)],
         narr='形が毎回変わる、多形性VT。',
         ev=[], L=POLY_L, art=art_poly, hl=ALL),
    dict(key='トルサード', place=1, name='トルサード・ド・ポワント',
         act='→ 脈なし：CPR＋電気ショック ／ → 止まっても12誘導。QT、K・Mgなどを確認',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 止まっても12誘導。QT、K・Mgなどを確認', False)],
         narr='ねじれる、トルサード。止まっても、くり返す。',
         ev=[(0, 'Q'), (1.0, 'Q'), (4.6, 'Q')], L=5.6, art=art_tdp, gain=gain_tdp,
         hl=[(TDP_A - 0.1, TDP_B + 0.1)]),
    dict(key='R on T', place=2, name='R on T',
         act='→ 12誘導。QT、K・Mgなどを確認。除細動器を近くに',
         lines=[('→ 12誘導。QT、K・Mgなどを確認。', False), ('除細動器を近くに', True)],
         narr='T波の上。T波に乗るPVC、R on T。',
         # PVC は直前のRから RONT_C 秒。T波の頂点（0.27秒）を過ぎた下りに乗せ、乗られたT波の山が見えるようにした
         # （第21弾は 0.27秒ちょうどで、T波がPVCに隠れて見えなかった。専門医レビュー 2026-10-09）
         ev=[(0, 'N'), (0.8, 'N'), (0.8 + RONT_C, 'V'), (2.4, 'N')], L=3.2, hl=[(0.8 + 0.14, 0.8 + RONT_C + 0.42)]),
    dict(key='粗いVF', place=3, name='粗いVF',
         act='→ 反応を確認し、人を呼んでCPR＋電気ショック',
         lines=[('→ 反応を確認し、人を呼んでCPR＋電気ショック', False)],
         narr='QRSがない。大きくバラバラ、粗いVF。',
         ev=[], L=4.0, art=art_vf_coarse, hl=ALL),
    dict(key='細かいVF', place=3, name='細かいVF',
         act='→ CPR＋電気ショック（細かくてもVFならショック）',
         lines=[('→ CPR＋電気ショック', False), ('（細かくてもVFならショック）', True)],
         narr='小さな揺れでも、VFならショック。細かいVF。',
         ev=[], L=4.0, art=art_vf_fine, hl=ALL),
    dict(key='心静止', place=3, name='心静止',
         act='→ 反応がなければ人を呼び、すぐCPR（ショックはしない）。並行して電極外れ・感度を確認',
         lines=[('→ 反応がなければ人を呼び、', False), ('すぐCPR（ショックはしない）。', True),
                ('並行して電極外れ・感度を確認', True)],
         narr='ほぼまっすぐ、心静止。反応がなければ、すぐCPR。',
         ev=[], L=4.0, art=art_asys, hl=ALL),
    dict(key='PEA1', place=4, name='PEA（ふつうに見える）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='最後は、波形では分からない。ふつうに見えても、脈がない。PEA。',
         ev=[(k*0.75, 'N') for k in range(6)], L=4.5, hl=ALL),
    dict(key='PEA2', place=4, name='PEA（遅く幅広い）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='遅く幅広くても、脈がなければPEA。',
         ev=[(0.3, 'W'), (2.3, 'W')], L=4.0, hl=ALL),
]
for _p in PATTERNS:
    _pl = PLACES[_p['place']]
    _p['col'] = _pl['col']
    _p['pno'] = _pl['no']
    _p['beats'] = _p['ev']
N_PAT = len(PATTERNS)

# ナレーション（下書き）：冒頭とまとめ
NARR_OPEN = '致死性不整脈、見るのは5か所。'
NARR_END = '見るのは5か所。どこを見落としやすい？コメントで教えてね。'
NARR_SAVE = '保存して、見返してね。'
NARR = {'冒頭': NARR_OPEN, **{p['key']: p['narr'] for p in PATTERNS}, 'まとめ': NARR_END, '保存': NARR_SAVE}


def art_apply(pat, rel, v):
    """パターンのノイズと倍率をかける：gain(rel)*v + art(rel)（周期 L でくり返す）"""
    L = pat['L']
    if pat.get('gain'):
        v = pat['gain'](rel, L) * v
    if pat.get('art'):
        v = v + pat['art'](rel, L)
    return v


# 区間の長さ（秒）。【仮】録音前なので、声の長さは「1.2倍速で 1秒に約8.5字」と見積もった。
# 録音したら align_vo.py の配置を見て、声の長さ＋0.75秒（話し始めるまで 0.55秒＋次までの間 0.2秒）に合わせて詰め直す。
# 下限は (1) 見積もった声の長さ＋0.75秒 (2) 次の対応を読む時間（1字 0.12秒、最低 4秒）の大きいほう（--check で確かめる）。
# そのうえで、拍の並びがくずれない位置で切る（つなぎ目は --check で表示）：
# - モビッツII 5.6：P-P 0.8秒の倍数。次の完全房室ブロックの最初のP波まで P-P 0.8秒（R-R は 4.96 → 5.9秒）。
#   縮んで枠へ移るとき見えている範囲（区間の 2.16〜5.25秒）に、伝わらなかったP波（2.4秒）が入る
# - 完全房室ブロック 4.52：3つめの補充調律（3.7秒）のT波のあと、次のP波（4.76秒）の手前。
#   次のショートランの最初のP波（区間の 0.24秒）が、心房のP-P 0.68秒の続きの位置（4.76秒）に来る。R-R は 3.7 → 4.92秒（1.22秒）
# - ショートラン 5.6：拍の並びを 1.2秒ずらした周期（SR_SHIFT）の、洞調律（5.2秒）のあと 0.4秒で単形性VTが始まる。
#   見えている範囲（2.16〜5.25秒）に3連のPVC（2.48〜3.24秒）が入る
# - 単形性VT 6.08：VTの拍の間隔 0.32秒の倍数（19拍）
# - 多形性VT・粗いVF・細かいVF・心静止：連続した波形なのでどこで切ってもよい（端0.2秒でなめらかにつなぐ）。
#   心静止 5.1 は次の対応（3行）を読む時間から
# - トルサード 5.6：トルサードが止まり、洞調律に戻ったところ（1周期）。次の R on T の最初の拍まで 1.0秒
# - R on T 4.8：周期 3.2秒のあと、2つめのR on T（4.36秒）が乗り、そのT波のあと（0.44秒）に粗いVFが始まる
#   （R on T から VF へ。見えている範囲（1.36〜4.45秒）に2つめのR on T が入る）
# - PEA（ふつうに見える）5.25：拍の間隔 0.75秒の倍数。次の PEA（遅く幅広い）の最初のQRSまで 1.05秒
# - PEA（遅く幅広い）4.8：2つめと3つめのQRS（2.3・4.3秒）が見えている範囲（1.36〜4.45秒）に入る。
#   うしろの洞調律は区間の終わりから 0.96秒（TAIL_OFF）で始める（4.3秒のQRSから 1.46秒）
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {'モビッツII': 5.6, '完全房室ブロック': 4.52, 'ショートラン': 5.6, '単形性VT': 6.08, '多形性VT': 6.0,
         'トルサード': 5.6, 'R on T': 4.8, '粗いVF': 4.0, '細かいVF': 4.0, '心静止': 5.1, 'PEA1': 5.25, 'PEA2': 4.8}
SPEAK_CPS = 8.5                   # 【仮】声の速さ（字/秒、1.2倍速のあと）
READ_S_PER_CHAR = 0.12            # 次の対応を読む時間（字あたり）
READ_MIN = 4.0
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['key']]
    assert _p['D'] >= 3.44 - 1e-9, _p['key']


def act_chars(pat):
    """次の対応の字数（矢印・空白・区切りの ／ は数えない）。"""
    return len(pat['act'].replace('→', '').replace('／', '').replace(' ', ''))


def text_in(i):
    """紹介の始まりから文字が出はじめるまで（秒）。前のパターンが上の枠へ縮んで移るときは、
    その波形が文字の上を通りすぎてから出す（0.45秒。声の話し始め 0.55秒とほぼ同じ）。"""
    return 0.45 if 1 <= i <= 6 else 0.1


def need_d(i):
    """区間の長さの下限（声の見積もりと、読む時間）。1つめは区間より 0.35秒短く見えるので、そのぶん足す。
    文字が遅れて出るパターンは、そのぶん（0.35秒）読む時間に足す。"""
    pat = PATTERNS[i]
    voice = len(pat['narr']) / SPEAK_CPS + 0.75
    read = max(READ_MIN, READ_S_PER_CHAR*act_chars(pat)) + (text_in(i) - 0.1)
    return max(voice, read) + (HANDOFF_EARLY if i == 0 else 0.0), voice, read


def beat_wave(tau, r, kind):
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    return v


def spike_times(beats):
    """拍の列 → スパイクの列 [(時刻, 高さ), …]"""
    out = []
    for r, k, *_ in beats:
        for dt, amp in SPIKES.get(k, ()):
            out.append((r + dt, amp))
    return out


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, r, k)
    return v


def periodic_beats(pat, t0, t1):
    out = []
    L = pat['L']
    k0 = int(math.floor(t0 / L)) - 1
    k1 = int(math.ceil(t1 / L)) + 1
    for k in range(k0, k1):
        for r, kind in pat['ev']:
            out.append((k*L + r, kind))
    return out


def hl_mask(pat, rel):
    """周期の中の色を付ける範囲（rel は区間の始まりからの時刻）。"""
    L = pat['L']
    r = np.mod(rel, L)
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-L, 0.0, L):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


# --- 中部の帯：12パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンをくり返して置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つの場所の代表に素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE で1つめのパターンが右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 4.0                     # 【仮】冒頭の1文（約2秒）のあと、見出しと枠（5か所の名前）を読む時間
END_HOLD = 6.5                    # 【仮】12個そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [0, 3, 6, 7, 10]           # 場所ごとに1つ：モビッツII型 → 単形性VT → R on T → 粗いVF → PEA（ふつうに見える）
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12
HANDOFF_EARLY = 0.35
LEAD_PH = PR                      # 前の洞調律：R が LEAD_PH + k*RR（モビッツII型の最初のP波まで P-P 0.8秒）
TAIL_OFF = PR + RR                # うしろの洞調律：区間の終わりから TAIL_OFF 秒で最初の R（LEAD_PH と RR の倍数ちがい → ループがつながる）
FLY = 0.8                         # 中部から枠へ縮んで移る時間


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        lim = pat['D'] - pat.get('trim', 0.0)
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < lim - 1e-9:
                beats.append((t + r, kind, i))
        t += pat['D']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -14:                     # 前：洞調律
        beats.append((LEAD_PH + k*RR, 'N', None)); k -= 1
    # うしろ：洞調律（間隔は変えない）。尺は「最後の2文が入る長さ」以上で、
    # うしろの洞調律の位相が冒頭とそろういちばん短い長さにする。こうするとループがつながる
    need = T_TITLE + end - HANDOFF_EARLY + FLY + END_HOLD
    base = FREEZE + end + (TAIL_OFF - LEAD_PH)
    k = math.ceil((need - base) / RR - 1e-9)
    dur_target = base + k*RR
    for k in range(0, 60):
        beats.append((end + TAIL_OFF + k*RR, 'N', None))
    beats.sort(key=lambda b: b[0])
    return beats, segs, end, dur_target


STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()
STRIP_SPK = spike_times(STRIP)          # 中部の帯のスパイク [(時刻, 高さ)]

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM

# --- ミニ波形の枠（2列×3段 を上下に） -------------------------------------------
CELL_W, CELL_H = 400, 92
COL_X = (130, 550)
CELL_GAP = 8
TOP_Y = [384 + k*(CELL_H + CELL_GAP) for k in range(3)]          # 384, 484, 584 → 下端 676
BOT_Y = [1252 + k*(CELL_H + CELL_GAP) for k in range(3)]         # 1252, 1352, 1452 → 下端 1544（下の注記と 12px あける）
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える）
M_MV = 25.0                       # ミニ波形：1mV = 25px（いちばん大きいR on T（上）・トルサード（下）も枠に収まる）

# 中部のかたまり：見る場所（小）→ 名前（大）→ 次の対応（最大3行）→ 波形
_TOP_END = TOP_Y[-1] + CELL_H      # 上の枠の下端（676）
_BOT_TOP = BOT_Y[0]                # 下の枠の上端（1252）
NEG_MAX = 1.22                     # いちばん下へ振れる波（トルサード -1.22mV）
F_BASE = _BOT_TOP - int(NEG_MAX*F_MV) - 6        # 基線（下の枠に 6px 余白）。背景のマス目の太い線をここにそろえる
Y_LABEL = _TOP_END + 27            # 見る場所（26px）の字の中心
Y_NAME = Y_LABEL + 47              # 名前（48px）の字の中心
Y_ACT0 = Y_NAME + 51               # 次の対応の1行目（32px）の字の中心
ACT_PITCH = 40                     # 次の対応の行の間隔
LABEL_SZ, NAME_SZ, ACT_SZ = 26, 48, 32
ACT_W = 760                        # 次の対応の幅の上限（左右に 160px 以上の余白）
F_Y0, F_Y1 = int(F_BASE - 230), int(_BOT_TOP - 2)
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# t=T_TITLE で、1つめのパターンの区間の始まりが画面の右端に来る（止まっていた時間を引く）
OFFSET = -HALF - (T_TITLE - FREEZE) / SLOW


def te(t):
    """波形の時計：T_STOP〜T_GO は止まる。"""
    if t < T_STOP:
        return t
    if t < T_GO:
        return T_STOP
    return t - FREEZE


def tau_c(t):
    """画面の中央にある実際の時刻。"""
    return te(t) / SLOW + OFFSET


def t_of(tau_center):
    """その時刻が画面の中央に来る t（止まっているあいだは除く）。"""
    t = (tau_center - OFFSET) * SLOW
    return t if t < T_STOP else t + FREEZE


WINDOWS = []
for _i in range(len(PATTERNS)):
    _a = T_TITLE if _i == 0 else WINDOWS[-1][1]
    # 区間の終わりが右端の少し先（0.35秒）に来た瞬間。次のパターンの最初のP波・細動波が
    # 右端に入る前に縮み始めるので、見えているのはパターン i だけになる
    _b = t_of(SEGS[_i][1] - HALF - HANDOFF_EARLY)
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60
DUR = round(_DUR_LOOP * FPS_LOOP) / FPS_LOOP


def cell_rect(i):
    """横に読む：上の枠は i=0..5、下の枠は i=6..11。それぞれ2列×3段。"""
    j = i if i < 6 else i - 6
    row, col = j // 2, j % 2
    x, y = COL_X[col], (TOP_Y if i < 6 else BOT_Y)[row]
    return (x, y, x + CELL_W, y + CELL_H)


# --- 道具 ---------------------------------------------------------------------
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(u):
    u = cl(u)
    return u*u*(3-2*u)


def ramp(t, t0, d=0.5):
    return ease((t - t0) / d)


def mix(a, b, u):
    return tuple(int(round(a[i] + (b[i]-a[i])*u)) for i in range(3))


_FONTS, _TXT = {}, {}


def font(size, weight):
    k = (size, weight)
    if k not in _FONTS:
        f = ImageFont.truetype(FONT, size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _FONTS[k] = f
    return _FONTS[k]


# 閉じかっこのすぐあとの句読点（「）。」「）、」）は、全角の空きで離れて見えるので、字の幅の KERN ぶん詰める
# （専門医レビュー 2026-10-09：「（ショックはしない）　。」のように見える）
KERN_PAIRS = ('）。', '）、')
KERN = 0.45


def _layout(f, s, sz):
    """文字列を「）」と句読点のあいだで切った部品と、それぞれの左端（詰めたあと）、全体の bbox。"""
    pieces, start = [], 0
    for i in range(len(s) - 1):
        if s[i:i+2] in KERN_PAIRS:
            pieces.append(s[start:i+1]); start = i + 1
    pieces.append(s[start:])
    offs, x = [], 0.0
    for j, pc in enumerate(pieces):
        offs.append(x)
        x += f.getlength(pc) - (KERN*sz if j + 1 < len(pieces) else 0.0)
    boxes = [f.getbbox(pc) for pc in pieces]
    x0 = min(o + b[0] for o, b in zip(offs, boxes)); x1 = max(o + b[2] for o, b in zip(offs, boxes))
    y0 = min(b[1] for b in boxes); y1 = max(b[3] for b in boxes)
    return pieces, offs, (int(math.floor(x0)), y0, int(math.ceil(x1)), y1)


def text_img(s, size, weight, col, max_w=None):
    k = (s, size, weight, col, max_w)
    if k in _TXT:
        return _TXT[k]
    sz = size
    while True:
        f = font(sz, weight)
        pieces, offs, (x0, y0, x1, y1) = _layout(f, s, sz)
        if max_w is None or (x1 - x0) <= max_w or sz <= 16:
            break
        sz -= 1
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (x1 - x0 + 8, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for pc, o in zip(pieces, offs):
        d.text((4 - x0 + o, 4), pc, font=f, fill=col + (255,))
    _TXT[k] = (im, asc)
    return _TXT[k]


def text_w(s, size, weight):
    return text_img(s, size, weight, WHITE)[0].size[0] - 8


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None):
    if a <= 0.004:
        return
    im, asc = text_img(s, size, weight, col, max_w)
    if a < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel('A').point(lambda v: int(v*a)))
    w, h = im.size
    if right is not None:
        px = int(right - w + 4)
    elif x is not None:
        px = int(x - 4)
    else:
        px = int(cx - w/2)
    py = int(cy - 4 - asc*0.62)
    base.alpha_composite(im, (px, py))


def text_box(s, size, weight, cy, max_w=None):
    """put(cy=…) で置いたときの、字の上端・下端（y）。--check の重なりの検算用。"""
    im, asc = text_img(s, size, weight, WHITE, max_w)
    bb = im.getchannel('A').getbbox()
    py = int(cy - 4 - asc*0.62)
    return py + bb[1], py + bb[3]


def grid():
    """背景のマス目：心電図用紙と同じ。波形と同じ 1mm＝14px（25mm/秒・10mm/mV）なので、
    小さいマス 14px＝0.04秒・0.1mV、大きいマス 70px（5マスごとの太い線）＝0.2秒・0.5mV。
    中部の帯の基線（F_BASE）が太い線に乗るように、横の線の位置をそろえる。"""
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = F_PXMM
    y0 = F_BASE % (5*pm)
    for i in range(int(W/pm) + 2):
        x = round(i*pm)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,),
               width=2 if i % 5 == 0 else 1)
    for k in range(-1, int(H/pm) + 2):
        y = round(y0 + k*pm)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    return im


# --- 中部の波形 --------------------------------------------------------------------
SS = 2


def strip_colors(tau):
    """パターンの区間のうち、色を付ける範囲だけそのパターンの色。"""
    cid = np.full(len(tau), -1, dtype=int)
    for i, (s0, s1) in enumerate(SEGS):
        inside = (tau >= s0 - 0.35) & (tau < s1 + 0.0)
        if not inside.any():
            continue
        m = inside & hl_mask(PATTERNS[i], tau - s0)
        if PATTERNS[i]['hl'] is ALL:
            m = (tau >= s0 - 0.20) & (tau < s1)
        cid[m] = i
    return cid


ART_EDGE = 0.2                    # 区間の端で、ノイズ・倍率をなめらかに切りかえる長さ（秒）


def strip_art(tau, v):
    """中部の帯：区間ごとに、そのパターンのノイズと倍率をかける（区間の端 ART_EDGE 秒でなめらかに）。"""
    out = v.copy()
    for i, (s0, s1) in enumerate(SEGS):
        pat = PATTERNS[i]
        if not (pat.get('art') or pat.get('gain')):
            continue
        m = (tau > s0 - 1e-9) & (tau < s1)
        if not m.any():
            continue
        tt = tau[m]
        e = np.minimum(np.clip((tt - s0) / ART_EDGE, 0, 1), np.clip((s1 - tt) / ART_EDGE, 0, 1))
        e = e*e*(3 - 2*e)
        rel = tt - s0
        L = pat['L']
        g = pat['gain'](rel, L) if pat.get('gain') else 1.0
        n = pat['art'](rel, L) if pat.get('art') else 0.0
        out[m] = v[m] * (1 + e*(g - 1)) + e*n
    return out


def glow_line(size, runs, col, width, a, blur=(8, 20)):
    """runs: 点列のリスト。グロー付きの線を RGBA で返す。"""
    w, h = size
    core = Image.new('L', (w*SS, h*SS), 0)
    dc = ImageDraw.Draw(core)
    for pts in runs:
        if len(pts) >= 2:
            dc.line([(x*SS, y*SS) for x, y in pts], fill=255, width=int(width*SS), joint='curve')
    core = core.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if blur:
        g1 = np.asarray(core.filter(ImageFilter.GaussianBlur(blur[0])), dtype=np.float32)
        g2 = np.asarray(core.filter(ImageFilter.GaussianBlur(blur[1])), dtype=np.float32)
        g = np.maximum(g1*0.95, g2*0.5)
        lay = Image.new('RGBA', (w, h), col + (0,))
        lay.putalpha(Image.fromarray(np.clip(g*a, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), 0.6) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


FX = np.arange(0, W + 1, 0.5)


def strip_arrays(tau_center):
    """中部の帯：(波形, 色の番号, スパイク [(x, 高さ, 色の番号)])"""
    tau = tau_center + (FX - XC) / F_PXS
    spk = []
    for ts, amp in STRIP_SPK:
        x = XC + (ts - tau_center) * F_PXS
        if -10 <= x <= W + 10:
            spk.append((x, amp, int(strip_colors(np.array([ts]))[0])))
    return strip_art(tau, wave_from(STRIP, tau)), strip_colors(tau), spk


SPIKE_W = 1.35
SPIKE_W_MIN = 3.2
SPIKE_LIGHT = 0.35


def spike_layer(size, runs, col, lw, a, blur):
    return glow_line(size, runs, mix(col, (255, 255, 255), SPIKE_LIGHT), max(lw*SPIKE_W, SPIKE_W_MIN), a, blur=blur)


def spike_runs(spk, xs, ys, mv, x_off=0.0, y_off=0.0):
    out = []
    for x, amp, *_ in spk:
        yb = float(np.interp(x, xs, ys))
        out.append([(x - x_off, yb + 0.12*amp*mv - y_off), (x - x_off, yb - amp*mv - y_off)])
    return out


def hook_arrays(i):
    """フック用：パターン i の、色の付いた範囲が中央の少し左に来る一場面。"""
    pat = PATTERNS[i]
    if pat['hl'] is ALL:
        c = pat['L'] / 2
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2 + 0.25
    rel = c + (FX - XC) / F_PXS + pat['L']
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    cid = np.where(hl_mask(pat, rel) | (pat['hl'] is ALL), i, -1)
    spk = []
    for ts, amp in spike_times(bl):
        if rel[0] <= ts <= rel[-1]:
            x = XC + (ts - c - pat['L']) * F_PXS
            on = pat['hl'] is ALL or bool(hl_mask(pat, np.array([ts]))[0])
            spk.append((x, amp, i if on else -1))
    return v, cid, spk


_HOOK = {}


def hook_targets():
    if not _HOOK:
        _HOOK['seq'] = [strip_arrays(tau_c(T_STOP))] + [hook_arrays(i) for i in HOOK] \
            + [strip_arrays(tau_c(T_STOP))]
    return _HOOK['seq']


def hook_state(t):
    """止まっているあいだの (変形の前, 後, 進み具合, 表示中のパターン)。"""
    seq = hook_targets()
    times = [HOOK_T0 + k*HOOK_STEP for k in range(len(HOOK))] + [HOOK_T0 + len(HOOK)*HOOK_STEP]
    k = -1
    for n, tk in enumerate(times):
        if t >= tk:
            k = n
    if k < 0:
        return seq[0], seq[0], 1.0, None
    u = ease((t - times[k]) / HOOK_MORPH)
    shown = HOOK[k] if k < len(HOOK) else None
    return seq[k], seq[k + 1], u, shown


def draw_wave(v, cid, base_col, a, spk=()):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(set(np.unique(cid).tolist()) | {c for *_, c in spk}):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
        sr = spike_runs([q for q in spk if q[2] == ci], FX, ys, F_MV)
        if sr:
            out.alpha_composite(spike_layer((W, h), sr, col, 4.5, a, (8, 20)))
    return out


def featured(t, base_col, a):
    if T_STOP <= t < T_GO:
        (v0, c0, s0), (v1, c1, s1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a, s1 if u >= 0.5 else s0)
    v, cid, spk = strip_arrays(tau_c(t))
    return draw_wave(v, cid, base_col, a, spk)


STRIP_W = CELL_W - 20             # ミニ波形の帯（枠の中）
STRIP_BASE = 31                   # 帯の上端（枠の上から 28px）から基線まで → 基線は枠の上から 59px


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 28


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0):
    """パターン i をくり返した波形を、画面の x_lo〜x_hi に描いた RGBA（全画面サイズの一部）。
    中央 cx に来る時刻は tau_c(t)（中部の帯と同じ）。区間の始まりからの相対時刻で周期にする。"""
    pat = PATTERNS[i]
    s0 = SEGS[i][0]
    xs = np.arange(x_lo, x_hi + 0.5, 0.5)
    tau = tau_c(t) + (xs - cx) / pxs
    rel = tau - s0
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    ys = base_y - v*mv
    ect = np.ones(len(xs), dtype=bool) if pat['hl'] is ALL else hl_mask(pat, rel)
    y_lo = int(min(ys.min(), base_y - 1.1*mv) - 30)
    y_hi = int(max(ys.max(), base_y + 0.9*mv) + 30)
    bx0, by0 = int(x_lo) - 30, y_lo
    size = (int(x_hi - x_lo) + 60, max(4, y_hi - y_lo))
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    spk = []
    for ts, amp in spike_times(bl):
        if rel[0] <= ts <= rel[-1]:
            on = pat['hl'] is ALL or bool(hl_mask(pat, np.array([ts]))[0])
            spk.append((xs[0] + (ts - rel[0]) * pxs, amp, on))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        w_, a_ = ((lw_e or lw) if flag else lw), (a if flag else a*a_norm)
        if runs:
            out.alpha_composite(glow_line(size, runs, col, w_, a_, blur=blur))
        sr = spike_runs([q for q in spk if q[2] == flag], xs, ys, mv, bx0, by0)
        if sr:
            out.alpha_composite(spike_layer(size, sr, col, w_, a_, blur))
    return out, (bx0, by0)


def lerp(a, b, u):
    return a + (b - a)*u


def view_params(i, u):
    """u=0 で中部の帯、u=1 で枠のミニ波形。"""
    ox, oy = cell_strip_origin(i)
    cx = lerp(XC, ox + STRIP_W/2, u)
    base_y = lerp(F_BASE, oy + STRIP_BASE, u)
    pxs = F_PXS*(M_PXS/F_PXS)**u
    mv = F_MV*(M_MV/F_MV)**u
    half = lerp(XC, STRIP_W/2, u)
    lw = lerp(4.5, 2.2, u)
    b1 = lerp(8, 3, u); b2 = lerp(20, 7, u)
    return cx, base_y, pxs, mv, cx - half, cx + half, lw, (b1, b2)


MINI_LW_ECT = 3.8                  # ミニ波形で、特徴の拍の線の太さ（ふつうの拍は 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、ふつうの拍の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u))
    if u >= 1.0:
        # 枠に収まったら、枠の内側だけに描く（となりの段に、はみ出さない）
        _, y0, _, y1 = cell_rect(i)
        top, bot = max(0, y0 + 2 - pos[1]), min(im.size[1], y1 - 2 - pos[1])
        if bot <= top:
            return
        im = im.crop((0, top, im.size[0], bot))
        pos = (pos[0], pos[1] + top)
    base.alpha_composite(im, pos)


def cell_title(pat):
    return f"{pat['pno']} {pat['name']}"


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。見る場所の番号と名前を薄く）/'now'（紹介中）/'landing'/'done'（ミニ波形あり）"""
    x0, y0, x1, y1 = cell_rect(i)
    pat = PATTERNS[i]
    place = PLACES[pat['place']]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a_fill = a_all                          # 枠の中の塗り：方眼が透けすぎないよう、薄くする対象から外す
    if state in ('empty', 'now'):
        a_all = a_all * 0.5                 # ミニ波形がないものは、枠線と文字だけ薄く
    if state in ('now', 'landing'):
        pulse = 0.55 + 0.45*math.sin(t*5.0)**2
        if state == 'now':
            pulse = min(1.0, pulse*1.6)
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=pat['col'] + (int(255*pulse*a_all),), width=3)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=CARD_EDGE + (int(255*a_all),), width=2)
    base.alpha_composite(lay)
    if state in ('done', 'landing'):
        put(base, cell_title(pat), 22, 700, pat['col'], x=x0 + 14, cy=y0 + 16,
            a=a_all, max_w=CELL_W - 30)
    else:
        bright = state == 'now'
        put(base, place['no'], 30, 700, place['col'] if bright else mix(DIM, place['col'], 0.35),
            x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2) if bright else a_all)
        put(base, place['name'], 24, 600 if bright else 500,
            mix(place['col'], LIGHT, 0.3) if bright else (120, 134, 132),
            x=x0 + 60, cy=y0 + CELL_H/2, a=min(1.0, a_all*2) if bright else a_all, max_w=CELL_W - 76)


# --- 画面 ---------------------------------------------------------------------------
HEADER = [('致死性不整脈 見るのは', 1.0, WHITE), ('5', 2.0, YEL), ('か所', 1.0, WHITE)]
HEADER_BASE = 370                   # 見出しのベースライン（y）
TITLE = '致死性不整脈'
TITLE_SUB = [('見るのは', 1.0, WHITE), ('5', 1.35, YEL), ('か所', 1.0, WHITE)]
END_ASK = 'どこを見落としやすい？コメントで教えてね'
END_SAVE = '保存して見返してね'
NOTE1 = '実際の速さ（25mm/秒）'
NOTE2 = '※数値はこの波形での一例'
NOTE_CY = (1560, 1586)              # 注記の字の中心（字は y 1549〜1599。下の枠の下端 1544 と、y 1600 のあいだ）
WATERMARK = '@nurse_polarbearden'
MARGIN = 130


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def parts_layout(parts, size, max_w):
    """[(文字, 倍率, 色)] を1行に並べるときの字の大きさ・幅（max_w に入るまで縮める）。"""
    while True:
        ims = [text_img(sx, int(size*k), 800, col) for sx, k, col in parts]
        widths = [im.size[0] - 8 for im, _ in ims]
        total = sum(widths) + 6*(len(ims) - 1)
        if total <= max_w or size <= 24:
            return ims, widths, total, size
        size -= 1


def draw_parts(base, parts, size, baseline, a, max_w=W - 2*MARGIN - 10):
    """大きさのちがう字をベースラインでそろえて、中央に並べる（見出し・タイトルの「見るのは5か所」）。"""
    if a <= 0.004:
        return
    ims, widths, total, _ = parts_layout(parts, size, max_w)
    x = (W - total) / 2
    for (im, asc), w in zip(ims, widths):
        if a < 0.999:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda q: int(q*a)))
        base.alpha_composite(im, (int(x - 4), int(baseline - 4 - asc)))
        x += w + 6


def draw_header(base, a):
    """「致死性不整脈 見るのは」＋大きな黄色の「5」＋「か所」。左右の余白（130px）に収める。"""
    draw_parts(base, HEADER, 46, HEADER_BASE, a)


def act_layout(pat):
    """次の対応の行：[(文字, 左端x, 字の中心y)]。行のかたまりを中央に置き、行は左ぞろえ。続きの行は矢印のぶん字下げ。"""
    ind = text_w('→ ', ACT_SZ, 600) + 4
    ws = [text_w(s, ACT_SZ, 600) + (ind if cont else 0) for s, cont in pat['lines']]
    x0 = XC - max(ws) / 2
    return [(s, x0 + (ind if cont else 0), Y_ACT0 + k*ACT_PITCH, cont) for k, (s, cont) in enumerate(pat['lines'])], max(ws)


def draw_act(im, pat, a):
    rows, _ = act_layout(pat)
    for s, x, cy, cont in rows:
        if not cont and s.startswith('→ '):
            put(im, '→', ACT_SZ, 800, pat['col'], x=x, cy=cy, a=a)
            put(im, s[2:], ACT_SZ, 600, LIGHT, x=x + text_w('→ ', ACT_SZ, 600) + 4, cy=cy, a=a)
        else:
            put(im, s, ACT_SZ, 600, LIGHT, x=x, cy=cy, a=a)


def place_label(pat):
    pl = PLACES[pat['place']]
    return f"見る場所{pl['no']} {pl['name']}"


def draw_end(im, t, a):
    """最後：5か所の一覧（場所の色）→ 問いかけ → 保存（緑）。"""
    if a <= 0.004:
        return
    names = [f"{p['no']} {p['name']}" for p in PLACES]
    wmax = max(text_w(s, END_SZ, 800) for s in names)
    x0 = XC - wmax / 2
    t0 = T_END + FLY
    for k, (p, s) in enumerate(zip(PLACES, names)):
        put(im, s, END_SZ, 800, p['col'], x=x0, cy=END_Y0 + k*END_PITCH, a=a*ramp(t, t0 + 0.12*k, 0.35))
    put(im, END_ASK, 36, 700, WHITE, cx=XC, cy=END_Y_ASK, a=a*ramp(t, T_END + 1.5, 0.5), max_w=W - 2*170)
    put(im, END_SAVE, 40, 800, GREEN, cx=XC, cy=END_Y_SAVE, a=a*ramp(t, T_END + 4.2, 0.5))


END_SZ, END_PITCH = 38, 56
END_Y0 = _TOP_END + 60
END_Y_ASK = END_Y0 + 4*END_PITCH + 92
END_Y_SAVE = END_Y_ASK + 70

# 冒頭のタイトル（波形が止まっているあいだ）
TITLE_CY = 590
TITLE_SUB_BASE = 750
HOOK_LABEL_CY = 808
HOOK_NAME_CY = 860

_GRID = None


def strip_alpha(t):
    """中部の帯の濃さ。縮んで枠へ移るあいだは消し、最後（まとめ）も消して、冒頭へ戻るときに戻す。"""
    keep = 1 - ramp(t, DUR - LOOP_FADE - 0.05, LOOP_FADE - 0.05)
    a = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a = min(a, ramp(t, b_i + FLY - 0.1, 0.45))
    return a * (1 - ramp(t, T_END + FLY, 0.5)*keep)


def frame(t, watermark=True):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    a_loop = ramp(t, DUR - LOOP_FADE - 0.05, LOOP_FADE - 0.05)   # 1 で冒頭と同じ画面
    keep = 1 - a_loop
    draw_header(im, ramp(t, 2.5, 0.5)*keep)

    a_cells = ramp(t, T_GO - 0.3, 0.6)*keep
    cur = current(t)
    flying = None
    for i in range(N_PAT):
        a_i, b_i = WINDOWS[i]
        if t >= b_i + FLY:
            st = 'done'
        elif b_i <= t < b_i + FLY:
            st = 'landing'
        elif cur == i:
            st = 'now'
        else:
            st = 'empty'
        if b_i <= t < b_i + FLY:
            flying = i
        draw_cell(im, i, t, st, a_cells)
        if st == 'done':
            mini(im, i, t, 1.0, a=keep)

    # 中部：紹介中の見る場所・名前・次の対応
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        al = ramp(t, a_i + text_in(cur), 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, place_label(pat), LABEL_SZ, 700, pat['col'], cx=XC, cy=Y_LABEL, a=al)
        put(im, pat['name'], NAME_SZ, 900, pat['col'], cx=XC, cy=Y_NAME, a=al, max_w=820)
        draw_act(im, pat, al)

    # 冒頭：タイトルと、変形中の見る場所・パターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        put(im, TITLE, 150, 900, WHITE, cx=XC, cy=TITLE_CY, a=a_t, max_w=W - 2*MARGIN)
        draw_parts(im, TITLE_SUB, 64, TITLE_SUB_BASE, a_t)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                aa = a_t*ramp(u, 0.3, 0.4)
                pl = PLACES[pat['place']]
                put(im, f"{pl['no']} {pl['name']}", 36, 700, pat['col'], cx=XC, cy=HOOK_LABEL_CY, a=aa)
                put(im, pat['name'], 48, 900, pat['col'], cx=XC, cy=HOOK_NAME_CY, a=aa, max_w=820)

    draw_end(im, t, ramp(t, T_END + FLY, 0.6)*keep)

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = strip_alpha(t)
    base_col = mix(OPEN_COL, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    if a_strip > 0.01:
        im.alpha_composite(featured(t, base_col, a_strip), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)

    # 注記は y 1600 より上に（インスタのリール画面の下のほうは、名前とキャプションが重なる）
    put(im, NOTE1, 24, 400, GREY, x=135, cy=NOTE_CY[0], a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_CY[1], a=0.85*ramp(t, T_GO, 0.5)*keep)
    if watermark:
        put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


# --- サムネイル ---------------------------------------------------------------------
THUMB_WAVE = 3                    # サムネイルの見本の波形（単形性VT）
THUMB_TITLE_CY = 762
THUMB_SUB_BASE = 904
THUMB_BASE = 1100                 # 見本の波形の基線


def thumbnail():
    """サムネイル（透かしなし）。12個そろった一覧に、大きな「致死性不整脈」「見るのは5か所」と見本の波形。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    t = T_END + FLY + 2.0
    g = grid()
    im = g.copy()                 # 見出しは出さない（大きなタイトルと同じ文言なので）
    for i in range(N_PAT):
        draw_cell(im, i, t, 'done', 1.0)
        mini(im, i, t, 1.0)
    put(im, TITLE, 132, 900, WHITE, cx=XC, cy=THUMB_TITLE_CY, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, 70, THUMB_SUB_BASE, 1.0)
    v, cid, spk = hook_arrays(THUMB_WAVE)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0, spk)
    im.alpha_composite(wl, (0, F_Y0 + (THUMB_BASE - F_BASE)))
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _qrs_ms(f, lim=0.12):
    tt = np.arange(-0.2, 0.3, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < lim)
    return (tt[m].max() - tt[m].min()) * 1000


def screen_strings():
    """画面に出る文字（出してはいけない言葉 NG_WORDS が無いことの確かめ用）。"""
    out = [s for s, _, _ in HEADER] + [TITLE] + [s for s, _, _ in TITLE_SUB] + [END_ASK, END_SAVE, NOTE1, NOTE2]
    for p in PLACES:
        out.append(f"{p['no']} {p['name']}")
    for p in PATTERNS:
        out += [cell_title(p), place_label(p), p['name']] + [s for s, _ in p['lines']]
    return out


# 出さない言葉（spec の「出さないもの」）。この字そのものをコードに書かないよう、文字コードで持つ
NG_WORDS = ['\u5831\u544a', '\u0041\u0045\u0044']


def act_from_lines(pat):
    acts = []
    for s, cont in pat['lines']:
        if cont:
            acts[-1] += s
        else:
            acts.append(s)
    return ' ／ '.join(acts)


def check():
    ok = True
    print(f'映像 {DUR:.2f}秒（{round(DUR*60)}コマ）【仮：録音前の見積もり】')
    print(f'冒頭 0〜{T_TITLE:.1f}s（止めて変形 {T_STOP}〜{T_GO}s）')
    print('パターンごとの紹介の時間（下限＝max(声の見積もり, 読む時間)）')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        nd, voice, read = need_d(i)
        flag = '' if pat['D'] >= nd - 1e-9 else '  ← 短い'
        ok &= not flag
        print(f"  {pat['pno']} {pat['name']:<14} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s（下限{nd:.2f}：声{voice:.2f} 読む{read:.2f}）"
              f"  画面 {a:5.2f}–{b:5.2f}s（{b-a:4.2f}s）{flag}")
    print(f'最後のパターンの終わり {T_END:.2f}s → 一覧・まとめ {T_END+FLY:.2f}〜{DUR:.2f}s（{DUR-T_END-FLY:.2f}s）')
    # 区間のつなぎ目
    print('つなぎ目（前のパターンの最後のQRS・P → 次の最初のQRS・P）')
    qrs = [b for b in STRIP if KINDS[b[1]][0] is not None]
    pw = sorted([(b[0] - KINDS[b[1]][2], b[2]) for b in STRIP if KINDS[b[1]][1] is not None])
    for i, (s0, s1) in enumerate(SEGS):
        inside = [b for b in qrs if s0 <= b[0] < s1]
        nxt_name = PATTERNS[i+1]['name'] if i + 1 < N_PAT else 'うしろの洞調律'
        if not inside:
            print(f"  {PATTERNS[i]['name']} → {nxt_name}：拍なし（連続した波形）"); continue
        last = max(inside, key=lambda b: b[0])
        nxt = min((b for b in qrs if b[0] >= s1 - 1e-9), key=lambda b: b[0])
        lp = [p for p, j in pw if j == i]
        np_ = [p for p, j in pw if s1 - 0.3 <= p < s1 + 1.5 and j != i]
        if i + 1 < N_PAT and not PATTERNS[i+1]['ev']:
            print(f"  {PATTERNS[i]['name']} → {nxt_name}：QRS {last[0]-s0:.2f}s → 次は連続した波形（端0.2秒でつなぐ）"); continue
        ptxt = ''
        if lp and np_:
            ptxt = f"、P-P {min(np_) - max(lp):.2f}s"
        print(f"  {PATTERNS[i]['name']} → {nxt_name}：QRS {last[0]-s0:.2f}s → 次 {nxt[0]-last[0]:.2f}s 後{ptxt}")
    print(f'冒頭の洞調律 → モビッツII型：R の位置', [round(b[0], 2) for b in STRIP if b[2] is None and -2 < b[0] < 0.5])

    # 文言：決まった文言（spec）と同じか・行の幅
    spec_path = os.path.join(HERE, '..', 'docs', 'reel21_v2_spec.md')
    spec = open(spec_path, encoding='utf-8').read() if os.path.exists(spec_path) else None
    print('次の対応（画面の行）')
    for pat in PATTERNS:
        back = act_from_lines(pat)
        if back != pat['act']:
            print(f"  ✗ {pat['name']}：行をつなぐと文言とちがう：{back}"); ok = False
        if spec is not None and pat['act'] not in spec:
            print(f"  ✗ {pat['name']}：spec に同じ文言がない：{pat['act']}"); ok = False
        rows, wmax = act_layout(pat)
        x0 = min(x for _, x, _, _ in rows)
        flag = '' if (wmax <= ACT_W and x0 >= 160 - 1) else '  ← 幅が広い'
        ok &= not flag
        print(f"  {pat['name']}：{len(rows)}行 幅{wmax:.0f}px 左{x0:.0f}px{flag}")
        for s, x, cy, cont in rows:
            print(f"      {'  ' if cont else ''}{s}")
    # 名前・見出しの幅
    for pat in PATTERNS:
        w = text_w(pat['name'], NAME_SZ, 900)
        if w > 820:
            print(f"  ✗ 名前が広い {pat['name']} {w}"); ok = False
        w = text_w(cell_title(pat), 22, 700)
        if w > CELL_W - 30:
            print(f"  ✗ 枠の名前が広い {cell_title(pat)} {w}"); ok = False
    _, _, total, sz = parts_layout(HEADER, 46, W - 2*MARGIN - 10)
    print(f'見出し 幅{total}px（字 {sz}px、5 は {2*sz}px）')
    # 見出しの上端（安全域 300px）
    im5, asc5 = text_img('5', 2*sz, 800, YEL)
    bb = im5.getchannel('A').getbbox()
    top5 = HEADER_BASE - 4 - asc5 + bb[1]
    print(f'見出しの「5」の上端 y={top5}（300 以上）')
    ok &= top5 >= 300
    # 画面・ナレーションに、出してはいけない言葉（spec「出さないもの」）が無い
    for s in screen_strings() + list(NARR.values()):
        if any(w in s for w in NG_WORDS):
            print(f'  ✗ 出してはいけない言葉：{s}'); ok = False

    # 縦の重なり：文字の下端 と 波形の上端、波形の下端 と 下の枠
    print(f'中部：上の枠の下端 {_TOP_END}、見る場所 {Y_LABEL}、名前 {Y_NAME}、対応 {Y_ACT0}〜、基線 F_BASE {F_BASE}'
          f'（マス目の太い線は F_BASE から 70px ごと）、下の枠の上端 {_BOT_TOP}')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        rows, _ = act_layout(pat)
        txt_bot = max(text_box(s, ACT_SZ, 600, cy)[1] for s, _, cy, _ in rows)
        lab_top = text_box(place_label(pat), LABEL_SZ, 700, Y_LABEL)[0]
        top_min, bot_max = 1e9, -1e9
        for tt in np.arange(a + text_in(i) + 0.3, b, 0.05):
            if strip_alpha(tt) < 0.05:
                continue
            v, _, _ = strip_arrays(tau_c(tt))
            top_min = min(top_min, F_BASE - v.max()*F_MV)
            bot_max = max(bot_max, F_BASE - v.min()*F_MV)
        gap_top = top_min - txt_bot - 2.25
        gap_bot = _BOT_TOP - (bot_max + 2.25)
        flag = '' if (gap_top >= 6 and gap_bot >= 0 and lab_top >= _TOP_END + 6) else '  ← 重なる'
        ok &= not flag
        print(f"  {pat['name']:<14} 字の下端 {txt_bot:4d} / 波の上端 {top_min:6.1f}（すき間 {gap_top:5.1f}px）"
              f" 波の下端 {bot_max:6.1f}（下の枠まで {gap_bot:5.1f}px）{flag}")
    # 冒頭の変形の名前と波形
    hook_bot = max(text_box(PATTERNS[i]['name'], 48, 900, HOOK_NAME_CY)[1] for i in HOOK)
    hook_top = min(F_BASE - hook_arrays(i)[0].max()*F_MV for i in HOOK)
    print(f'冒頭：名前の下端 {hook_bot} / 変形した波の上端 {hook_top:.1f}')
    ok &= hook_top - hook_bot >= 6
    # 最後の文字は下の枠より上
    n1, n2 = text_box(NOTE1, 24, 400, NOTE_CY[0]), text_box(NOTE2, 24, 400, NOTE_CY[1])
    print(f'注記：{n1[0]}〜{n2[1]}（下の枠の下端 {BOT_Y[-1] + CELL_H}、1600 以下）')
    ok &= n1[0] > BOT_Y[-1] + CELL_H and n2[1] <= 1600 and n2[0] >= n1[1] - 1
    end_bot = text_box(END_SAVE, 40, 800, END_Y_SAVE)[1]
    print(f'最後：保存の字の下端 {end_bot}（下の枠 {_BOT_TOP}）')
    ok &= end_bot <= _BOT_TOP - 20
    # ミニ波形が枠に収まるか
    for i, pat in enumerate(PATTERNS):
        rel = np.arange(0, pat['L'], 0.002)
        v = art_apply(pat, rel, wave_from(periodic_beats(pat, -1, pat['L'] + 1), rel))
        _, y0, _, y1 = cell_rect(i)
        base_y = cell_strip_origin(i)[1] + STRIP_BASE
        tt = text_box(cell_title(pat), 22, 700, y0 + 16)[1]
        hi, lo = base_y - v.max()*M_MV, base_y - v.min()*M_MV
        flag = '' if (lo <= y1 - 2 and hi >= y0 + 2) else '  ← はみ出す（枠で切る）'
        print(f"  枠 {cell_title(pat):<20} 名前の下端 {tt - y0:3d} 波 {hi - y0:5.1f}〜{lo - y0:5.1f}（枠 0〜{CELL_H}）{flag}")
    print('モデルの値')
    print(f'  モビッツII型：PR {PR:.2f}秒で一定、4つめのP波が伝わらない（4:3）')
    print(f'  完全房室ブロック：心房 {60/0.68:.0f}/分、心室 {60/1.7:.0f}/分（幅の広い補充調律、QRS {_qrs_ms(qrs_escape):.0f}ms）')
    print(f'  ショートラン：3連、間隔 0.38秒（{60/0.38:.0f}/分）')
    print(f'  単形性VT：{60/0.32:.0f}/分、QRS幅 {_qrs_ms(qrs_vt_rs, 0.3):.0f}ms（ショートラン・R on T のPVCは {_qrs_ms(qrs_pvc):.0f}ms）')
    print(f'  多形性VT：約{60*POLY_N/POLY_L:.0f}/分')
    print(f'  トルサード：QT延長の洞調律（60/分）→ {TDP_B-TDP_A:.2f}秒、約{TDP_F*60:.0f}/分 → 自然に止まる')
    print(f'  R on T：洞調律 75/分、PVCは直前のRから {RONT_C:.2f}秒（T波の頂点 0.27秒を過ぎた下り。乗られたT波の山が見える）')
    print(f'  PEA：ふつうの形 {60/0.75:.0f}/分、幅の広いQRS {60/2.0:.0f}/分')
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:6]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])
    ph = ((tau_c(DUR) - (STRIP_END + TAIL_OFF)) - (tau_c(0.0) - LEAD_PH)) % RR
    print(f'ループの位相のずれ {min(ph, RR - ph)*1000:.1f}ms（1コマ {1000/60:.1f}ms 以下）')
    ok &= min(ph, RR - ph) <= 1/60 + 1e-6
    print('OK' if ok else '✗ 見直す')
    assert ok


# --- 書き出し ---------------------------------------------------------------------
def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def render_chunk(args):
    i0, i1, fps, path, crf, preset = args
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset,
           '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def beeps(path, sr=44100):
    """中部の波形の R が画面の中央を通るときに「ピッ」。心室の拍は低い音。
    P波だけの拍・トルサードで消した拍・帯が消えているあいだ（最後のまとめ）は鳴らさない。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, i in STRIP:
        if KINDS[k][0] is None:
            continue
        ts = t_of(r)
        if i is not None and PATTERNS[i].get('gain') is not None:
            g = PATTERNS[i]['gain'](np.array([r - SEGS[i][0]]), PATTERNS[i]['L'])[0]
            if abs(g) < 0.5:
                continue
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO) or strip_alpha(ts) < 0.5:
            continue
        f = 960.0 if k in ('N', 'Q') else 720.0
        L = int(0.08*sr)
        tt = np.arange(L)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr)
        a[j:j+L] += s[:max(0, min(L, n-j))]
    for k in range(len(HOOK)):                # 冒頭の変形のたびに
        ts = HOOK_T0 + k*HOOK_STEP
        L = int(0.07*sr); tt = np.arange(L)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.04)*np.sin(2*np.pi*720.0*tt)
        j = int(ts*sr); a[j:j+L] += s
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel21_v2.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel21_v2_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel21_v2_hq.mp4')
    if o.check:
        check(); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.thumb:
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel21v2.png')
        thumbnail().save(p); print(p); return
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(os.path.dirname(o.out), 'parts')
    os.makedirs(tmp, exist_ok=True)
    jobs = [(i, min(total, i+step), o.fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset)
            for j, i in enumerate(range(0, total, step))]
    with Pool(o.jobs) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    wav = os.path.join(tmp, 'beeps.wav')
    beeps(wav)
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', o.out],
                   check=True)
    print(o.out)


if __name__ == '__main__':
    main()
