"""第21弾v4 致死性不整脈 見るのは5か所（切りかえなし：大きな波形が1本、ずっと同じ大きさ・同じ速さで流れる）

v3 は場面の切りかえ・寄り・引きが多く、せわしない、という声を受けて作り直した。決まった中身は docs/reel21_v2_spec.md
（次の対応の文言・行の分け方はそのまま）、根拠は docs/reel21_v2_evidence.md。波形の定義は v2・v3 と同じ。

作り：
- 画面の真ん中に、大きな波形が1本だけ。最初から最後まで同じ倍率（ZOOM＝2.4倍、1mm＝33.6px、10mm/mV×2.4）・
  同じゆっくりの速さ（SLOW＝実際の約0.5倍、画面の上で約420px/秒）。カメラの動き・場面の切りかえ・ほかの帯はない
- 12パターンを見る場所の順に、1本の流れでつなぐ（新しいリズムは右から入ってくる。モニターと同じ）。
  つなぎ目は拍の途中で切らない（パターンごとの「始めてよい位置」「終えてよい位置」から選ぶ）
- 洞調律 → ①〜⑤ → 洞調律（最後）→ 冒頭の洞調律へ（ループ）
- 変わるのは字だけ（その場で薄く入れかわる）：上に場所の名前と何を見るか、その下にパターン名（特徴が画面に入るころ）、
  下に次の対応。冒頭は「致死性不整脈」「見るのは5か所」、最後は5か所・問いかけ・保存
- キャラクター（characters.py）：顔は P・T のこぶ、幅の広い QRS・PVC の中に、はみ出さずに入るときだけ（毎コマ形で確かめる）。
  幅の狭い QRS は顔が入らないので、手（白い手ぶくろ）だけ

秒数は、表 SEG（波形の区間）と BLOCKS（字・ナレーション）から決める。【仮の秒数】ナレーションは録音前で、
台本の字数から声の長さを見積もっている（1.2倍速で約9字/秒）。録音が届いたら align_vo.py で声の長さを測って
voice_len.json に書くと、区間の長さと秒数が声に合わせて組み直される。

使い方:
    python3 make_reel21v4.py --check      # 検算（秒数の表・つなぎ目・はみ出し・顔がこぶの中か・字の幅）
    python3 make_reel21v4.py --still 20   # 1コマだけ（out/still_020.0.png）
    python3 make_reel21v4.py --thumb      # サムネイル（透かしなし）
    python3 make_reel21v4.py --jobs 2     # 書き出し・60fps（音なし。out/reel21_v4.mp4）
    python3 make_reel21v4.py --hq         # 高画質（out/reel21_v4_hq.mp4）
    python3 make_reel21v4.py --preview    # スマホ確認用の軽い版（540×960・30fps。out/preview_low.mp4）
"""
import argparse
import json
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (70, 82, 82)
LIGHT = (226, 232, 231)
OPEN_COL = (176, 186, 190)        # 冒頭の波形の色（色のない明るい灰色。場面①で緑＋場所の色になる）
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)
YEL = (255, 214, 64)

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 見る場所（5か所）。色は場所ごと。ov＝何を見るか（画面の1行）、narr＝場所の説明のナレーション ----------
PLACES = [
    dict(no='①', name='PとQRSのつながり', col=(255, 212, 90),
         ov='Pのあとに、QRSが続いているか',
         narr='1つめは、PとQRSのつながり。Pのあとに、QRSが続いているか。'),
    dict(no='②', name='QRSの幅と形', col=(255, 152, 72),
         ov='幅が広いか、形がそろっているか',
         narr='2つめは、QRSの幅と形。幅が広いか、形がそろっているか。'),
    dict(no='③', name='T波の上', col=(200, 150, 255),
         ov='T波に、PVCが乗っていないか',
         narr='3つめは、T波の上。T波に、PVCが乗っていないか。'),
    dict(no='④', name='QRSがない', col=(255, 92, 112),
         ov='QRSが見えているか',
         narr='4つめは、QRSがない。QRSが見えているか。'),
    dict(no='⑤', name='波形では分からない', col=(110, 200, 255),
         ov='波形がふつうでも、脈を確かめる',
         narr='最後は、波形では分からない。波形がふつうでも、脈を確かめる。'),
]

# --- 波形の部品（実際の時間・秒、mV）。reel21_v2 と同じ ------------------------------
RR = 0.80                        # 洞調律 75/分
PR = 0.16                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):                   # P波 0.25mV・幅 約0.11秒（どちらもふつうの範囲。拡大したとき顔がこぶの中に入る大きさ）
    return 0.25*_g(t, 0.0, 0.028)


def qrs_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_pvc(t):                   # PVC（形A）：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def qrs_vt_rs(t):                 # 単形性VTのQRS（R＋S）。幅 約190ms
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
ALL = [(-1e9, 1e9)]                         # 全部をその色で


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


RONT_C = 0.36                     # R on T：直前のRから PVC の頂点まで（秒）。T波の頂点（0.27秒）を過ぎた下りに乗る


# --- 12パターン（見る場所の順） --------------------------------------------------
# act：次の対応（docs/reel21_v2_spec.md の文言そのまま。「 ／ 」で2つの対応）。
# lines：画面での行の分け方（v2 と同じ）。(文字, 続きの行か)。続きの行は矢印なしで字下げ。--check で act に戻ることを確かめる。
# narr：ナレーション（下書き。録音前。narration.md と同じ）。
# 波形：1周期ぶんの拍（R頂点の時刻, 種類）と周期 L、連続した波形 art・倍率 gain、色を付ける範囲 hl（v2 と同じ）
# enter：特徴の部分（hl の始まり）が画面の右端に入ってくる時刻（紹介の始まりから・秒）。名前を言っているあいだに見えるように。
#        トルサードは、紹介が始まってから少しあとに始まるように（すぐ始まらない）
# slow：紹介中の再生の速さ（実際の何倍か）。zoom：紹介中の拡大（ふつう 2.5倍＝1mm 35px。振れの大きい波形は 2.0〜2.3倍）。
#       顔がこぶの中に入る大きさにし、特徴の部分が、説明しているあいだに画面を横切りきるように選んだ（速い波形は少し速め）
PATTERNS = [
    dict(key='モビッツII', place=0, name='モビッツII型',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='モビッツII型。PRは一定のまま、突然QRSが抜ける。',
         ev=[(0.16, 'N'), (0.96, 'N'), (1.76, 'N'), (2.4, 'P')], L=3.2, hl=[(2.30, 2.52)], enter=0.4, slow=0.5),
    dict(key='完全房室ブロック', place=0, name='完全房室ブロック',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='完全房室ブロック。PとQRSが、別々に動く。',
         ev=[(k*0.68, 'P') for k in range(10)] + [(0.3 + k*1.7, 'W') for k in range(4)], L=6.8, hl=ALL, slow=0.55),
    dict(key='ショートラン', place=1, name='ショートラン',
         act='→ 症状を見て、12誘導。QT、K・Mgなどを確認',
         lines=[('→ 症状を見て、12誘導。QT、K・Mgなどを確認', False)],
         narr='ショートラン。幅広いQRSが3つ以上続いて、自然に止まる。',
         ev=[(0, 'N'), (0.8, 'N'), (1.28, 'V'), (1.66, 'V'), (2.04, 'V'), (3.2, 'N')], L=4.0, hl=[(1.19, 2.46)],
         enter=0.4, slow=0.65, zoom=2.3),
    dict(key='単形性VT', place=1, name='単形性VT',
         act='→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。パッド装着 ／ → 脈なしなら人を呼ぶ。CPR＋電気ショック',
         lines=[('→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。', False), ('パッド装着', True),
                ('→ 脈なしなら人を呼ぶ。CPR＋電気ショック', False)],
         narr='単形性VT。速く、幅広く、同じ形。脈のあるなしで、動きが分かれる。',
         ev=[(k*0.32, 'X') for k in range(15)], L=4.8, hl=ALL, slow=0.7, zoom=2.3),
    dict(key='多形性VT', place=1, name='多形性VT',
         act='→ 脈なし：CPR＋電気ショック ／ → 脈あり：人を呼び、パッド装着（続けば脈があってもショック）',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 脈あり：人を呼び、パッド装着', False),
                ('（続けば脈があってもショック）', True)],
         narr='多形性VT。形が1拍ごとに変わる。',
         ev=[], L=POLY_L, art=art_poly, hl=ALL, slow=0.75, zoom=2.0),
    dict(key='トルサード', place=1, name='トルサード・ド・ポワント',
         act='→ 脈なし：CPR＋電気ショック ／ → 止まっても12誘導。QT、K・Mgなどを確認',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 止まっても12誘導。QT、K・Mgなどを確認', False)],
         narr='トルサード。ねじれるように変わり、止まっても、くり返す。',
         ev=[(0, 'Q'), (1.0, 'Q'), (4.6, 'Q')], L=5.6, art=art_tdp, gain=gain_tdp,
         hl=[(TDP_A - 0.1, TDP_B + 0.1)], enter=0.6, slow=0.8, zoom=2.0),
    dict(key='R on T', place=2, name='R on T',
         act='→ 12誘導。QT、K・Mgなどを確認。除細動器を近くに',
         lines=[('→ 12誘導。QT、K・Mgなどを確認。', False), ('除細動器を近くに', True)],
         narr='R on T。VFのきっかけになる。',
         ev=[(0, 'N'), (0.8, 'N'), (0.8 + RONT_C, 'V'), (2.4, 'N')], L=3.2, hl=[(0.8 + 0.14, 0.8 + RONT_C + 0.42)],
         enter=0.4, slow=0.55),
    dict(key='粗いVF', place=3, name='粗いVF',
         act='→ 反応を確認し、人を呼んでCPR＋電気ショック',
         lines=[('→ 反応を確認し、人を呼んでCPR＋電気ショック', False)],
         narr='粗いVF。大きくバラバラ。',
         ev=[], L=4.0, art=art_vf_coarse, hl=ALL, slow=0.75, zoom=2.2),
    dict(key='細かいVF', place=3, name='細かいVF',
         act='→ CPR＋電気ショック（細かくてもVFならショック）',
         lines=[('→ CPR＋電気ショック', False), ('（細かくてもVFならショック）', True)],
         narr='細かいVF。小さな揺れでも、VFならショック。',
         ev=[], L=4.0, art=art_vf_fine, hl=ALL, slow=0.75),
    dict(key='心静止', place=3, name='心静止',
         act='→ 反応がなければ人を呼び、すぐCPR（ショックはしない）。並行して電極外れ・感度を確認',
         lines=[('→ 反応がなければ人を呼び、', False), ('すぐCPR（ショックはしない）。', True),
                ('並行して電極外れ・感度を確認', True)],
         narr='心静止。ほぼまっすぐ。反応がなければ、すぐCPR。',
         ev=[], L=4.0, art=art_asys, hl=ALL, slow=0.55),
    dict(key='PEA1', place=4, name='PEA（ふつうに見える）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='PEA。ふつうに見えても、脈がない。',
         ev=[(k*0.75, 'N') for k in range(6)], L=4.5, hl=ALL, slow=0.55),
    dict(key='PEA2', place=4, name='PEA（遅く幅広い）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='遅く幅広いQRSでも、脈がなければPEA。',
         ev=[(0.3, 'W'), (2.3, 'W')], L=4.0, hl=ALL, slow=0.7, zoom=2.0),
]
for _p in PATTERNS:
    _pl = PLACES[_p['place']]
    _p['col'] = _pl['col']
    _p['pno'] = _pl['no']
N_PAT = len(PATTERNS)
SCENE_PATS = [[i for i, p in enumerate(PATTERNS) if p['place'] == s] for s in range(len(PLACES))]

NARR_OPEN = '致死性不整脈、見るのは5か所。'
NARR_END = '見るのは5か所。どこを見落としやすい？コメントで教えてね。'
NARR_SAVE = '保存して、見返してね。'
# ナレーションの文（align_vo.py の切り分けの単位）。キー：冒頭／場所0〜4／パターンの key／まとめ／保存
NARR = {'冒頭': NARR_OPEN}
for _s, _pl in enumerate(PLACES):
    NARR[f'場所{_s}'] = _pl['narr']
    for _i in SCENE_PATS[_s]:
        NARR[PATTERNS[_i]['key']] = PATTERNS[_i]['narr']
NARR['まとめ'] = NARR_END
NARR['保存'] = NARR_SAVE
NARR_ORDER = list(NARR.keys())


# --- 声の長さ（秒） -------------------------------------------------------------------
# 【仮】録音前は台本の字数から見積もる（1.2倍速で 約9字/秒。英字は1字＝2字ぶん、数字は1.5字ぶん、読点 0.2秒、文の中の句点 0.35秒）。
# 録音が届いたら align_vo.py が voice_len.json に測った長さを書き、そちらを使う。
CPS = 9.0
VOICE_LEN_FILE = os.path.join(HERE, 'voice_len.json')


def est_voice(s):
    n, pause = 0.0, 0.0
    body = s.rstrip('。？')
    for ch in body:
        if ch in '、':
            pause += 0.20
        elif ch in '。？':
            pause += 0.35
        elif ch == ' ':
            continue
        elif ch.isascii() and ch.isalpha():
            n += 2.0
        elif ch.isdigit():
            n += 1.5
        else:
            n += 1.0
    return round(n / CPS + pause, 2)


VOICE_LEN = {k: est_voice(v) for k, v in NARR.items()}
VOICE_MEASURED = False
if os.path.exists(VOICE_LEN_FILE):
    with open(VOICE_LEN_FILE, encoding='utf-8') as _f:
        _vl = json.load(_f)
    VOICE_LEN.update({k: float(v) for k, v in _vl.items() if k in VOICE_LEN})
    VOICE_MEASURED = True


def act_chars(pat):
    """次の対応の字数（矢印・空白・区切りの ／ は数えない）。"""
    return len(pat['act'].replace('→', '').replace('／', '').replace(' ', ''))


# --- 波形（周期 L でくり返す） -----------------------------------------------------
def beat_wave(tau, kind):
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    return v


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, k)
    return v


def periodic_beats(pat, t0, t1):
    out = []
    L = pat['L']
    for k in range(int(math.floor(t0 / L)) - 1, int(math.ceil(t1 / L)) + 1):
        for r, kind in pat['ev']:
            out.append((k*L + r, kind))
    return out


def art_apply(pat, rel, v):
    L = pat['L']
    if pat.get('gain'):
        v = pat['gain'](rel, L) * v
    if pat.get('art'):
        v = v + pat['art'](rel, L)
    return v


def hl_mask(pat, rel):
    if pat['hl'] is ALL:
        return np.ones(len(rel), dtype=bool)
    r = np.mod(rel, pat['L'])
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-pat['L'], 0.0, pat['L']):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


def pattern_wave(i, rel):
    pat = PATTERNS[i]
    bl = periodic_beats(pat, rel.min() - 1, rel.max() + 1)
    return art_apply(pat, rel, wave_from(bl, rel))


_EXT = {}


def extent(i):
    """1周期の波形のいちばん上・下（mV）。"""
    if i not in _EXT:
        rel = np.arange(0, PATTERNS[i]['L'], 0.002)
        v = pattern_wave(i, rel)
        _EXT[i] = (max(0.15, float(v.max())), min(-0.15, float(v.min())))
    return _EXT[i]


# 流れる帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px。新しい波形は右から入り、左へ流れる
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM                # 10mm/mV（いま紹介中の波形）
XC = W / 2




# 種類ごとの T波の頂点（R から・秒）。V（PVC）は逆向きのT
T_PEAK = {'N': 0.27, 'Q': 0.40, 'V': 0.25, 'X': 0.27, 'W': 0.34}


# --- 大きさと速さ（最初から最後まで同じ） --------------------------------------------------
ZOOM = 2.4                         # 拡大（1mm＝33.6px）。いちばん大きく振れるトルサードが、上の字と下の字のあいだに収まる大きさ
PXMM = 14.0*ZOOM
PXS = 25*PXMM                      # 波形の1秒 = 840px（25mm/秒の 2.4倍）
G = 10*PXMM                        # 1mV = 336px（10mm/mV の 2.4倍）
SLOW0 = 0.5                        # 再生の速さ（実際の何倍か）。画面の上で 420px/秒（目が疲れないよう、ゆっくり）
LEFT_TO_RIGHT = W / PXS            # 画面の幅に見える波形の長さ（実際の秒）＝ 約1.29秒

# 画面の配置
TITLE_CY, TITLE_SZ = 340, 54       # 場所の名前
OVL_CY, OVL_SZ = 410, 34           # 何を見るか
NAME_CY, NAME_SZ = 478, 46         # パターン名（左ぞろえ）
STRIP_TOP, STRIP_BOT = 522, 1336   # 波形が動いてよい範囲（上はパターン名の下、下は次の対応の上）
ACT_Y0, ACT_PITCH, ACT_SZ = 1378, 44, 32
ACT_W = 760
LABEL_X = 135
SINUS = dict(key='洞調律', name='洞調律', ev=[(0.16, 'N')], L=0.8, hl=[], place=None, col=WAVE_GREEN)

# 区間の「始めてよい位置」「終えてよい位置」（周期の中の時刻・秒）。None：どこでもよい（連続した波形）。
# 始め：最初の拍の P（または QRS）の 0.2秒前。終わり：最後の拍の T波のあと。拍の途中・トルサードの途中では切らない
def _vt(k0, k1, off):
    return [round((k*0.32 + off) % 4.8, 4) for k in range(k0, k1)]


WINDOWS = {
    'モビッツII': ([3.0, 0.6, 1.4], [0.61, 1.41, 2.21]),
    '完全房室ブロック': ([0.1, 1.8, 3.5, 5.2], dict(ranges=[(0.85, 1.5), (2.55, 3.2), (4.25, 4.9), (5.95, 6.6)])),
    'ショートラン': ([3.64, 0.44, 2.84], [0.45, 3.65]),
    '単形性VT': (_vt(0, 15, -0.1), _vt(0, 15, 0.3)),
    '多形性VT': (None, None),
    'トルサード': ([0.64, 5.24, 4.24], [5.25]),
    'R on T': ([2.84, 0.44, 2.04], [1.6, 2.85, 0.45]),     # 1.6：2つめのPVCのあとで終わる（R on T から VF へ）
    '粗いVF': (None, None),
    '細かいVF': (None, None),
    '心静止': (None, None),
    'PEA1': ([round((0.75*k - 0.36) % 4.5, 4) for k in range(6)], [round((0.75*k + 0.45) % 4.5, 4) for k in range(6)]),
    'PEA2': ([0.2, 2.2], dict(ranges=[(0.9, 1.7), (2.9, 3.7)])),
    '洞調律': ([0.6], [0.61]),
}
# 区間の前に足してよい拍（そのパターンの前の拍と同じリズム：種類・R-R）。特徴の部分が来る時刻を 1拍ずつ調整できる
PRE = {'モビッツII': ('N', 0.8), 'ショートラン': ('N', 0.8), 'トルサード': ('Q', 1.0), 'R on T': ('N', 0.8),
       'PEA1': ('N', 0.75)}
PRE_MAX = 5
ART_EDGE = 0.2                     # 連続した波形の区間の端を、なめらかに切りかえる長さ（秒）

# 秒数の決まり
OPEN_LEAD, OPEN_MIN, OPEN_GAP = 0.10, 3.0, 0.6
LEAD_OV, GAP_OV = 0.40, 0.55
LEAD_PAT, GAP_PAT, PAT_MIN = 0.45, 0.65, 4.0
TEXT_IN, TEXT_FADE_IN, TEXT_FADE_OUT = 0.50, 0.30, 0.25
READ_S_PER_CHAR, READ_MIN = 0.11, 4.0
END_LEAD, END_GAP, END_HOLD = 0.35, 0.35, 1.2
LOOP_FADE = 0.75
NAME_EARLY = 0.4                   # 特徴の部分が右端に入る、この秒数前にパターン名を出す


def read_need(i):
    return max(READ_MIN, READ_S_PER_CHAR*act_chars(PATTERNS[i]))


def pat_need(i):
    key = PATTERNS[i]['key']
    return max(PAT_MIN, LEAD_PAT + VOICE_LEN[key] + GAP_PAT,
               TEXT_IN + TEXT_FADE_IN + read_need(i) + TEXT_FADE_OUT)


def _next_end(a, dmin, L, ends):
    """a から dmin 以上進んだ、いちばん近い「終えてよい位置」までの長さ。"""
    if ends is None:
        return dmin
    if isinstance(ends, dict):
        x = a + dmin
        best = None
        for lo, hi in ends['ranges']:
            k = math.floor((x - lo) / L)
            for kk in (k, k + 1):
                b0, b1 = lo + kk*L, hi + kk*L
                b = x if b0 <= x <= b1 else (b0 if b0 > x else None)
                if b is not None and (best is None or b < best):
                    best = b
        return best - a
    best = None
    for e in ends:
        k = math.ceil((a + dmin - e) / L - 1e-9)
        b = e + k*L
        if best is None or b < best:
            best = b
    return best - a


def solve(slow):
    """波形の区間（SEG）と字・声の秒数（BLOCKS）を決める。"""
    open_dur = max(OPEN_MIN, OPEN_LEAD + VOICE_LEN['冒頭'] + OPEN_GAP)
    c0 = -slow*open_dur                                    # t=0 の画面の真ん中の時刻（モビッツII型の始まりが t=open_dur に真ん中）
    tcen = lambda tau: (tau - c0) / slow
    half = (W - XC) / (PXS*slow)
    tent = lambda tau: tcen(tau) - half
    texit = lambda tau: tcen(tau) + half
    segs, blocks = [], [dict(kind='open', key='冒頭', start=0.0, end=open_dur, v0=OPEN_LEAD)]
    s0 = 0.0
    for s, pl in enumerate(PLACES):
        for n, i in enumerate(SCENE_PATS[s]):
            pat = PATTERNS[i]
            L = pat['L']
            starts, ends = WINDOWS[pat['key']]
            T = tcen(s0)
            ov = (LEAD_OV + VOICE_LEN[f'場所{s}'] + GAP_OV) if n == 0 else 0.0
            best = None
            pre = PRE.get(pat['key'])
            cands = [(a, k_) for a in (starts if starts is not None else [0.0]) for k_ in (range(PRE_MAX + 1) if pre else [0])]
            for a, npre in cands:
                sp = s0 + (npre*pre[1] if pre else 0.0)        # パターン本体の始まり
                Pmin = T + ov
                h = hb = None
                feat_end = 0.0
                if pat['hl'] is ALL:
                    P = Pmin
                    hl_end_tau = s0
                else:
                    ha, hbb = pat['hl'][0]
                    k = math.ceil((a + 0.05 - ha) / L)
                    while True:
                        h = sp + ha + k*L - a
                        if tent(h) >= Pmin - NAME_EARLY:
                            break
                        k += 1
                    hb = h + (hbb - ha)
                    P = max(Pmin, tent(h) - NAME_EARLY)
                    feat_end = texit(hb) + 0.15
                    hl_end_tau = hb
                t_end = max(P + pat_need(i), feat_end)
                dmin = max(c0 + slow*t_end, hl_end_tau + 0.05) - sp
                D = _next_end(a, dmin, L, ends) + (sp - s0)
                if best is None or D < best['D'] - 1e-9:
                    best = dict(a=a, D=D, P=P, h=h, hb=hb, sp=sp, npre=npre)
            seg = dict(key=pat['key'], idx=i, pat=pat, place=s, first=(n == 0), s0=s0, a=best['a'], D=best['D'],
                       s1=s0 + best['D'], T=T, P=best['P'], h=best['h'], hb=best['hb'], sp=best['sp'],
                       npre=best['npre'], pre=pre)
            segs.append(seg)
            if n == 0:
                blocks.append(dict(kind='ov', key=f'場所{s}', scene=s, start=T, end=seg['P'], v0=T + LEAD_OV))
            blocks.append(dict(kind='pat', key=pat['key'], scene=s, pat=i, start=seg['P'] if n == 0 else T,
                               p=seg['P'], end=tcen(seg['s1']), v0=seg['P'] + LEAD_PAT))
            s0 = seg['s1']
    # 最後の洞調律（最後のまとめ → 冒頭の洞調律へ。ここでループ）
    v_end, v_save = VOICE_LEN['まとめ'], VOICE_LEN['保存']
    end_need = END_LEAD + v_end + END_GAP + v_save + END_HOLD + LOOP_FADE
    starts, ends = WINDOWS['洞調律']
    a = starts[0]
    D = _next_end(a, slow*(end_need + open_dur), 0.8, ends)
    T = tcen(s0)
    segs.append(dict(key='洞調律', idx=None, pat=SINUS, place=None, first=False, s0=s0, a=a, D=D, s1=s0 + D,
                     T=T, P=T, h=None, hb=None, sp=s0, npre=0, pre=None))
    Ltot = s0 + D
    blocks.append(dict(kind='end', key='まとめ', start=T, end=Ltot / slow, v0=T + END_LEAD,
                       save0=T + END_LEAD + v_end + END_GAP))
    for b in blocks:
        b['vlen'] = VOICE_LEN[b['key']]
        b['dur'] = b['end'] - b['start']
    return segs, blocks, Ltot, c0, open_dur


# 速さを、映像の長さがちょうど 1/60秒の整数倍になるよう、ほんの少しだけ合わせる（ループのつなぎ目のため）
_segs, _blocks, _L, _c0, _od = solve(SLOW0)
SLOW = _L / (math.ceil(_L / SLOW0 * 60 - 1e-6) / 60)
SEG, BLOCKS, LTOT, C0, OPEN_DUR = solve(SLOW)
for _ in range(3):
    if abs(LTOT / SLOW * 60 - round(LTOT / SLOW * 60)) < 1e-6:
        break
    SLOW = LTOT / (math.ceil(LTOT / SLOW * 60 - 1e-6) / 60)
    SEG, BLOCKS, LTOT, C0, OPEN_DUR = solve(SLOW)
DUR = LTOT / SLOW
SCROLL = PXS*SLOW                  # 画面の上で流れる速さ（px/秒）
CROSS = W / SCROLL                 # 1つの点が右端から左端まで横切る時間（秒）
PAT_BLOCK = {b['pat']: b for b in BLOCKS if b['kind'] == 'pat'}
OV_BLOCK = {b['scene']: b for b in BLOCKS if b['kind'] == 'ov'}
END_B = BLOCKS[-1]
SEG_OF = {g['idx']: g for g in SEG if g['idx'] is not None}
KEY_IDX = {p['key']: n for n, p in enumerate(PATTERNS)}


def scene_span(s):
    pats = SCENE_PATS[s]
    return SEG_OF[pats[0]]['T'], SEG_OF[pats[-1]]['T'] + SEG_OF[pats[-1]]['D'] / SLOW


def c_of(t):
    """時刻 t に画面の真ん中にある、流れの時刻（ループするので LTOT で回る）。"""
    return C0 + SLOW*t


def x_of(tau, t):
    return XC + (np.asarray(tau, dtype=float) - c_of(t))*PXS


# --- 1本の流れ（区間をつないだ波形） ----------------------------------------------------------
def _build_beats():
    out = []
    for n, g in enumerate(SEG):
        pat = g['pat']
        if g['npre']:
            kind, rr = g['pre']
            for j in range(g['npre']):
                out.append((g['s0'] + 0.2 + KINDS[kind][2] + j*rr, kind, n, None))     # 前に足した拍（rel なし）
        Dp = g['s1'] - g['sp']
        for r, kind in periodic_beats(pat, g['a'] - 1, g['a'] + Dp + 1):
            if g['a'] - 1e-9 <= r < g['a'] + Dp - 1e-9:
                if pat.get('gain') is not None and pat['gain'](np.array([r]), pat['L'])[0] < 0.5:
                    continue
                out.append((g['sp'] + r - g['a'], kind, n, r))
    out.sort()
    full = [(tau + sh, kind, n, r) for sh in (-LTOT, 0.0, LTOT) for tau, kind, n, r in out]
    return out, full


BEATS, _BEATS_FULL = _build_beats()
_BT = np.array([b[0] for b in _BEATS_FULL])


def stream_wave(tau):
    """流れの時刻 tau（いくつでもよい。LTOT で回る）の波形（mV）。"""
    tau = np.asarray(tau, dtype=float)
    tm = np.mod(tau, LTOT)
    lo, hi = tm.min() - 0.8, tm.max() + 0.8
    j0, j1 = np.searchsorted(_BT, lo), np.searchsorted(_BT, hi)
    v = np.zeros_like(tm)
    for tb, kind, n, r in _BEATS_FULL[j0:j1]:
        m = np.abs(tm - tb) < 0.75
        if m.any():
            v[m] += beat_wave(tm[m] - tb, kind)
    out = v.copy()
    for g in SEG:
        pat = g['pat']
        if not (pat.get('art') or pat.get('gain')):
            continue
        for sh in (-LTOT, 0.0, LTOT):
            s0, s1 = g['sp'] + sh, g['s1'] + sh
            m = (tm > s0 - 1e-9) & (tm < s1)
            if not m.any():
                continue
            tt = tm[m]
            e = np.minimum(np.clip((tt - s0) / ART_EDGE, 0, 1), np.clip((s1 - tt) / ART_EDGE, 0, 1))
            e = e*e*(3 - 2*e)
            rel = tt - s0 + g['a']
            gg = pat['gain'](rel, pat['L']) if pat.get('gain') else 1.0
            nn = pat['art'](rel, pat['L']) if pat.get('art') else 0.0
            out[m] = v[m]*(1 + e*(gg - 1)) + e*nn
    return out


def seg_index(tau):
    tm = np.mod(np.asarray(tau, dtype=float), LTOT)
    s0s = np.array([g['s0'] for g in SEG])
    return np.clip(np.searchsorted(s0s, tm, side='right') - 1, 0, len(SEG) - 1)


def stream_colors(tau):
    """色：特徴の部分は場所の色、ほかは緑。"""
    tm = np.mod(np.asarray(tau, dtype=float), LTOT)
    si = seg_index(tm)
    cols = np.full(len(tm), -1, dtype=int)            # -1：緑、0〜11：パターンの色
    for n in np.unique(si):
        g = SEG[n]
        if g['idx'] is None:
            continue
        m = si == n
        rel = tm[m] - g['sp'] + g['a']
        hm = hl_mask(g['pat'], rel) & (tm[m] >= g['sp'])       # 前に足した拍は色を付けない
        cc = np.where(hm, g['idx'], -1)
        cols[m] = cc
    return cols


_EXT_ALL = None


def stream_extent():
    """流れ全体のいちばん上・下（mV）。"""
    global _EXT_ALL
    if _EXT_ALL is None:
        tau = np.arange(0, LTOT, 0.002)
        v = stream_wave(tau)
        _EXT_ALL = (float(v.max()), float(v.min()))
    return _EXT_ALL


_vmax, _vmin = stream_extent()
BASE = float(round(STRIP_TOP + _vmax*G + max(0.0, ((STRIP_BOT - STRIP_TOP) - (_vmax - _vmin)*G) / 2)))


def visible_beats(t, margin=160):
    """画面に見えている拍：dict(tau, kind, seg, rel, x)。tau はいまの画面に合わせた（回した）値。"""
    c = c_of(t)
    lo, hi = c + (-margin - XC) / PXS, c + (W + margin - XC) / PXS
    out = []
    for k in (math.floor(lo / LTOT), math.floor(hi / LTOT)):
        for tb, kind, n, r in BEATS:
            tau = tb + k*LTOT
            if lo <= tau <= hi and not any(abs(o['tau'] - tau) < 1e-9 for o in out):
                out.append(dict(tau=tau, kind=kind, seg=n, rel=r, x=float(x_of(tau, t))))
    out.sort(key=lambda b: b['tau'])
    return out


def unwrap_near(tau_loop, t):
    """1周の中の時刻を、いまの画面に近い値に回す。"""
    c = c_of(t)
    return tau_loop + round((c - tau_loop) / LTOT)*LTOT


# --- 字の出し方 ------------------------------------------------------------------------------
def current_pattern(t):
    for b in BLOCKS:
        if b['kind'] == 'pat' and b['p'] <= t < b['end']:
            return b['pat']
    return None


def place_alpha(s, t):
    s0, s1 = scene_span(s)
    return ramp(t, s0, 0.3) * (1 - ramp(t, s1 - 0.3, 0.3))


def name_alpha(i, t):
    b = PAT_BLOCK[i]
    return ramp(t, b['p'], 0.3) * (1 - ramp(t, b['end'] - TEXT_FADE_OUT, TEXT_FADE_OUT))


def act_alpha(i, t):
    b = PAT_BLOCK[i]
    return ramp(t, b['p'] + TEXT_IN, TEXT_FADE_IN) * (1 - ramp(t, b['end'] - TEXT_FADE_OUT, TEXT_FADE_OUT))


def open_alpha(t):
    """冒頭の字の濃さ（最後の LOOP_FADE で戻ってくる）。"""
    return max(1 - ramp(t, OPEN_DUR - 0.35, 0.5), ramp(t, DUR - LOOP_FADE/2, LOOP_FADE/2))   # 最後の字が消えてから出る


def end_alpha(t):
    return ramp(t, END_B['start'], 0.4) * (1 - ramp(t, DUR - LOOP_FADE, LOOP_FADE/2))


def wave_alpha(t):
    """冒頭と最後は字が波形に重なるので、波形を少しだけ薄く。"""
    w = max(1 - ramp(t, OPEN_DUR - 0.3, 0.6), ramp(t, END_B['start'], 0.6))
    return 1 - 0.3*w
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


def lerp(a, b, u):
    return a + (b - a)*u


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


# 閉じかっこのすぐあとの句読点（「）。」「）、」）は、全角の空きで離れて見えるので詰める（v2 と同じ）
KERN_PAIRS = ('）。', '）、')
KERN = 0.45


def _layout(f, s, sz):
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
    if len(_TXT) > 4000:
        _TXT.clear()
    _TXT[k] = (im, asc)
    return _TXT[k]


def text_w(s, size, weight):
    return text_img(s, size, weight, WHITE)[0].size[0] - 8


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None):
    """文字を置く。薄くするときは alpha を掛けてから合成する（PIL の fill のアルファは効かないため）。"""
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
    """put(cy=…) で置いたときの、字の上端・下端（y）。"""
    im, asc = text_img(s, size, weight, WHITE, max_w)
    bb = im.getchannel('A').getbbox()
    py = int(cy - 4 - asc*0.62)
    return py + bb[1], py + bb[3]


def parts_layout(parts, size, max_w):
    while True:
        ims = [text_img(sx, int(size*k), 800, col) for sx, k, col in parts]
        widths = [im.size[0] - 8 for im, _ in ims]
        total = sum(widths) + 6*(len(ims) - 1)
        if total <= max_w or size <= 24:
            return ims, widths, total, size
        size -= 1


MARGIN = 130


def draw_parts(base, parts, size, baseline, a, max_w=W - 2*MARGIN - 10, dx=0.0):
    """大きさのちがう字をベースラインでそろえて、中央に並べる（「見るのは5か所」）。"""
    if a <= 0.004:
        return
    ims, widths, total, _ = parts_layout(parts, size, max_w)
    x = (W - total) / 2 + dx
    for (im, asc), w in zip(ims, widths):
        if a < 0.999:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda q: int(q*a)))
        base.alpha_composite(im, (int(x - 4), int(baseline - 4 - asc)))
        x += w + 6


def parts_top(parts, size, baseline):
    ims, widths, total, sz = parts_layout(parts, size, W - 2*MARGIN - 10)
    return min(baseline - 4 - asc + im.getchannel('A').getbbox()[1] for im, asc in ims), total


GRID_Y0 = 0                        # マス目の太い線は y = 70 の倍数（波形の基線をここにそろえる）


def grid(sp=F_PXMM, ax=0.0, ay=GRID_Y0):
    """背景のマス目：小さいマス sp（ふつう 14px＝1mm、紹介中 28px）、5マスごとの太い線。
    (ax, ay) を通る線が太い線（紹介中は、拡大した波形の基線が太い線に乗る）。マスはいつも正方形。"""
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    k0 = -int(math.ceil(ax / sp)) - 1
    for k in range(k0, k0 + int(W/sp) + 3):
        x = round(ax + k*sp)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    k0 = -int(math.ceil(ay / sp)) - 1
    for k in range(k0, k0 + int(H/sp) + 3):
        y = round(ay + k*sp)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    return im


_GRIDS = {}


def grid_cached(sp, ax, ay):
    k = (round(sp, 2), round(ax) % max(1, round(sp*5)), round(ay) % max(1, round(sp*5)))
    if k not in _GRIDS:
        if len(_GRIDS) > 12:
            _GRIDS.clear()
        _GRIDS[k] = grid(sp, ax, ay)
    return _GRIDS[k]


# --- 線を描く --------------------------------------------------------------------
SS = 2
BLUR = (7, 18)


def glow_line(size, runs, col, width, a, glow=1.0, part='all'):
    """runs: 点列のリスト。グロー付きの線を RGBA で返す。glow=0 で芯の線だけ。"""
    w, h = size
    core = Image.new('L', (w*SS, h*SS), 0)
    dc = ImageDraw.Draw(core)
    for pts in runs:
        if len(pts) >= 2:
            dc.line([(x*SS, y*SS) for x, y in pts], fill=255, width=max(1, int(round(width*SS))), joint='curve')
    core = core.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if glow*a > 0.02 and part != 'core':
        g1 = np.asarray(core.filter(ImageFilter.GaussianBlur(BLUR[0])), dtype=np.float32)
        g2 = np.asarray(core.filter(ImageFilter.GaussianBlur(BLUR[1])), dtype=np.float32)
        g = np.maximum(g1*0.95, g2*0.5)
        lay = Image.new('RGBA', (w, h), col + (0,))
        lay.putalpha(Image.fromarray(np.clip(g*a*glow, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
    if part == 'glow':
        return out
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), 0.6*(0.4 + 0.6*glow)) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


# --- 次の対応 --------------------------------------------------------------------
def act_layout(pat):
    """[(文字, 左端x, 字の中心y, 続きの行か)] と幅。行のかたまりを中央に置き、行は左ぞろえ。続きの行は矢印のぶん字下げ。"""
    ind = text_w('→ ', ACT_SZ, 600) + 4
    ws = [text_w(s, ACT_SZ, 600) + (ind if cont else 0) for s, cont in pat['lines']]
    x0 = XC - max(ws) / 2
    return [(s, x0 + (ind if cont else 0), ACT_Y0 + k*ACT_PITCH, cont) for k, (s, cont) in enumerate(pat['lines'])], max(ws)


def draw_act(im, pat, a, dx=0.0):
    rows, _ = act_layout(pat)
    for s, x, cy, cont in rows:
        x += dx
        if not cont and s.startswith('→ '):
            put(im, '→', ACT_SZ, 800, pat['col'], x=x, cy=cy, a=a)
            put(im, s[2:], ACT_SZ, 600, LIGHT, x=x + text_w('→ ', ACT_SZ, 600) + 4, cy=cy, a=a)
        else:
            put(im, s, ACT_SZ, 600, LIGHT, x=x, cy=cy, a=a)




# --- 波形を描く ----------------------------------------------------------------------------
LW = 5.5                           # 線の太さ
FX = np.arange(0, W + 0.5, 0.5)


def wave_layers(t):
    """いまの画面の波形の (x, y, 色の番号)。"""
    tau = c_of(t) + (FX - XC) / PXS
    v = stream_wave(tau)
    return FX, BASE - v*G, stream_colors(tau)


def draw_wave(img, xs, ys, cols, a, part):
    h0 = int(max(0, math.floor(ys.min()) - 40))
    h1 = int(min(H, math.ceil(ys.max()) + 40))
    size = (W, h1 - h0)
    lay = Image.new('RGBA', size, (0, 0, 0, 0))
    for ci in np.unique(cols):
        sel0 = cols == ci
        sel = sel0 | np.roll(sel0, 1) | np.roll(sel0, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r], ys[r] - h0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
        col = WAVE_GREEN if ci < 0 else PATTERNS[ci]['col']
        lay.alpha_composite(glow_line(size, runs, col, LW, a, 1.0, part))
    img.alpha_composite(lay, (0, h0))


# --- 冒頭・最後の字 --------------------------------------------------------------------------
TITLE = '致死性不整脈'
TITLE_SUB = [('見るのは', 1.0, WHITE), ('5', 1.8, YEL), ('か所', 1.0, WHITE)]
OPEN_TITLE_CY, OPEN_TITLE_SZ = 372, 116
OPEN_SUB_BASE, OPEN_SUB_SZ = 548, 70
OPEN_DOTS_CY = 1420                 # 「① ② ③ ④ ⑤」（場所の色。下の字の場所）
END_ASK = 'どこを見落としやすい？コメントで教えてね'
END_SAVE = '保存して見返してね'
END_LIST_Y0, END_LIST_PITCH, END_LIST_SZ = 340, 58, 36
END_LIST_X = (135, 560)
END_ASK_CY, END_SAVE_CY = 1394, 1460
NOTE_ZOOM = '※拡大・ゆっくり表示'
NOTE2 = '※数値はこの波形での一例'
NOTE_CY = (1560, 1586)
WATERMARK = '@nurse_polarbearden'


def draw_open_text(im, a):
    if a <= 0.004:
        return
    put(im, TITLE, OPEN_TITLE_SZ, 900, WHITE, cx=XC, cy=OPEN_TITLE_CY, a=a, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE, a)
    for k, pl in enumerate(PLACES):
        put(im, pl['no'], 52, 800, pl['col'], cx=XC + (k - 2)*100, cy=OPEN_DOTS_CY, a=a)


def end_list_pos(k):
    """最後の5か所の位置（2列：①② ／ ③④ ／ ⑤）。"""
    row, col = divmod(k, 2)
    return END_LIST_X[col], END_LIST_Y0 + row*END_LIST_PITCH


def end_times():
    b = END_B
    t_ask = b['v0'] + max(0.6, VOICE_LEN['まとめ']*0.32)
    return t_ask, b['save0'] - 0.1


def draw_end(im, t, a):
    if a <= 0.004:
        return
    t_ask, t_save = end_times()
    for k, pl in enumerate(PLACES):
        x, y = end_list_pos(k)
        put(im, f"{pl['no']} {pl['name']}", END_LIST_SZ, 800, pl['col'], x=x, cy=y,
            a=a*ramp(t, END_B['start'] + 0.12*k, 0.35))
    put(im, END_ASK, 38, 800, WHITE, cx=XC, cy=END_ASK_CY, a=a*ramp(t, t_ask, 0.4), max_w=W - 2*MARGIN)
    put(im, END_SAVE, 46, 900, GREEN, cx=XC, cy=END_SAVE_CY, a=a*ramp(t, t_save, 0.4), max_w=W - 2*MARGIN)


def draw_place_head(im, t):
    for s, pl in enumerate(PLACES):
        a = place_alpha(s, t)
        if a <= 0.004:
            continue
        put(im, f"{pl['no']} {pl['name']}", TITLE_SZ, 900, pl['col'], cx=XC, cy=TITLE_CY, a=a, max_w=W - 2*MARGIN)
        put(im, pl['ov'], OVL_SZ, 600, LIGHT, cx=XC, cy=OVL_CY, a=a*0.95, max_w=W - 2*MARGIN)


def draw_names(im, t):
    for i in range(N_PAT):
        a = name_alpha(i, t)
        if a > 0.004:
            put(im, PATTERNS[i]['name'], NAME_SZ, 900, PATTERNS[i]['col'], x=LABEL_X, cy=NAME_CY, a=a,
                max_w=W - 2*MARGIN)
        a2 = act_alpha(i, t)
        if a2 > 0.004:
            draw_act(im, PATTERNS[i], a2)


_GRID = None


def frame(t, watermark=True):
    global _GRID
    if _GRID is None:
        _GRID = grid(PXMM, XC, BASE)              # マス目：1mm＝33.6px（波形と同じ）。基線が太い線
    im = _GRID.copy()
    import characters
    xs, ys, cols = wave_layers(t)
    wa = wave_alpha(t)
    draw_wave(im, xs, ys, cols, wa, 'glow')
    characters.draw(sys.modules[__name__], im, t, layer='under')     # 顔と手（線の下）
    draw_wave(im, xs, ys, cols, wa, 'core')
    characters.draw(sys.modules[__name__], im, t, layer='over')      # 吹き出し・小物
    draw_place_head(im, t)
    draw_names(im, t)
    draw_open_text(im, open_alpha(t))
    draw_end(im, t, end_alpha(t))
    put(im, NOTE_ZOOM, 24, 400, GREY, x=135, cy=NOTE_CY[0], a=0.85)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_CY[1], a=0.85)
    if watermark:
        put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


# --- サムネイル（v3 と同じ作り：大きな題と、5か所それぞれに代表の小さな波形） -----------------------------
THUMB_TITLE_CY, THUMB_TITLE_SZ = 400, 124
THUMB_SUB_BASE, THUMB_SUB_SZ = 590, 74
THUMB_ROW_Y0, THUMB_ROW_PITCH, THUMB_ROW_LBL, THUMB_ROW_WAVE = 654, 186, 44, 118
REP = [0, 3, 6, 7, 10]              # 場所ごとの代表：モビッツII型・単形性VT・R on T・粗いVF・PEA（ふつうに見える）


def mini_wave(img, i, x0, x1, base, g, col, rel_c):
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = rel_c + (xs - (x0 + x1)/2) / (25*14.0)
    ys = base - pattern_wave(i, rel)*g
    runs = [list(zip(xs - x0 + 20, ys - (base - 150)))]
    size = (int(x1 - x0) + 40, 300)
    img.alpha_composite(glow_line(size, runs, col, 3.0, 1.0, 0.5), (int(x0) - 20, int(base - 150)))


def thumbnail():
    im = grid(14.0, XC, 0)
    put(im, TITLE, THUMB_TITLE_SZ, 900, WHITE, cx=XC, cy=THUMB_TITLE_CY, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, THUMB_SUB_SZ, THUMB_SUB_BASE, 1.0)
    for s, pl in enumerate(PLACES):
        top = THUMB_ROW_Y0 + s*THUMB_ROW_PITCH
        put(im, f"{pl['no']} {pl['name']}", THUMB_ROW_LBL, 800, pl['col'], x=LABEL_X, cy=top + THUMB_ROW_LBL*0.55)
        i = REP[s]
        pat = PATTERNS[i]
        vmax, vmin = extent(i)
        g = min(70.0, (THUMB_ROW_WAVE - 8) / (vmax - vmin))
        bl = top + THUMB_ROW_LBL*1.15 + 8 + vmax*g
        c = pat['L']/2 if pat['hl'] is ALL else sum(pat['hl'][0])/2
        mini_wave(im, i, LABEL_X, W - MARGIN, bl, g, pl['col'], c)
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _qrs_ms(f, lim=0.12):
    tt = np.arange(-0.2, 0.3, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < lim)
    return (tt[m].max() - tt[m].min()) * 1000


def screen_strings():
    out = [TITLE] + [s for s, _, _ in TITLE_SUB] + [END_ASK, END_SAVE, NOTE_ZOOM, NOTE2]
    for p in PLACES:
        out += [f"{p['no']} {p['name']}", p['ov']]
    for p in PATTERNS:
        out += [p['name']] + [s for s, _ in p['lines']]
    return out


# 出さない言葉（spec の「出さないもの」＋第◯弾の表示）。この字そのものをコードに書かないよう、文字コードで持つ
NG_WORDS = ['報告', 'AED', '着用', '第']


def act_from_lines(pat):
    acts = []
    for s, cont in pat['lines']:
        if cont:
            acts[-1] += s
        else:
            acts.append(s)
    return ' ／ '.join(acts)




def timing_table():
    rows = []
    for b in BLOCKS:
        if b['kind'] == 'open':
            name = '冒頭'
        elif b['kind'] == 'ov':
            pl = PLACES[b['scene']]
            name = f"{pl['no']} {pl['name']}（場所の説明）"
        elif b['kind'] == 'pat':
            name = f"　{PATTERNS[b['pat']]['name']}"
        else:
            name = '最後（5か所・問いかけ・保存）'
        rows.append((name, b))
    return rows


def check(faces=True):
    ok = True
    print(f"映像 {DUR:.2f}秒（{round(DUR*60)}コマ）"
          f"{'（声の長さは録音から）' if VOICE_MEASURED else '（仮：声の長さは台本の字数からの見積もり）'}")
    print(f"大きさ {ZOOM}倍（1mm＝{PXMM:.1f}px・1mV＝{G:.0f}px・波形の1秒＝{PXS:.0f}px）、速さ 実際の{SLOW:.4f}倍"
          f"（画面の上で {SCROLL:.0f}px/秒、右端から左端まで {CROSS:.2f}秒）。基線 y={BASE:.0f}")
    ok &= SCROLL <= 450
    # 区間
    print('波形の区間（流れの時刻・秒。真ん中に来る時刻 T、パターン名を出す時刻 P）')
    for g in SEG:
        nm = g['pat']['name']
        extra = ''
        if g['h'] is not None:
            extra = f"  特徴が右端に入る {g['T'] + (g['h'] - g['s0'])/SLOW - (W - XC)/SCROLL:6.2f}秒"
        print(f"  {nm:<14} 流れ {g['s0']:6.2f}〜{g['s1']:6.2f}（{g['D']:5.2f}・前に {g['npre']}拍・周期の {g['a']:.2f} から）"
              f"  画面 {g['T']:6.2f}〜{g['T'] + g['D']/SLOW:6.2f}秒  名前 {g['P']:6.2f}秒{extra}")
    # つなぎ目：前の区間の最後の QRS → 次の区間の最初の QRS・P
    print('つなぎ目（最後の QRS → 次の最初の拍）')
    for n in range(len(SEG)):
        g, nx = SEG[n], SEG[(n + 1) % len(SEG)]
        last = [b for b in BEATS if b[2] == n and KINDS[b[1]][0] is not None]
        first = [b for b in BEATS if b[2] == (n + 1) % len(SEG)]
        if not last or not first:
            print(f"  {g['pat']['name']} → {nx['pat']['name']}：連続した波形（端 {ART_EDGE}秒でなめらかに）")
            continue
        lt = last[-1][0]
        ft = first[0][0] + (LTOT if n + 1 == len(SEG) else 0.0)
        fk = first[0][1]
        fp = ft - KINDS[fk][2] if KINDS[fk][1] is not None else ft
        print(f"  {g['pat']['name']} → {nx['pat']['name']}：最後の QRS → 次の拍の始まり {fp - lt:.2f}秒（R→R {ft - lt:.2f}秒）")
        if ft - lt < 0.3:
            ok = False; print('    ✗ 近すぎる')
    # 秒数の表
    print('字と声の秒数（BLOCKS）')
    for k, (name, b) in enumerate(timing_table()):
        v1 = b['v0'] + b['vlen']
        nxt = BLOCKS[k+1]['start'] if k + 1 < len(BLOCKS) else DUR
        gap = nxt - v1
        flag = ''
        if b['kind'] == 'pat':
            i = b['pat']
            full = b['end'] - TEXT_FADE_OUT - (b['p'] + TEXT_IN + TEXT_FADE_IN)
            flag = f"  次の対応が出そろっている {full:4.2f}秒（必要 {read_need(i):.2f}）"
            if full < read_need(i) - 1e-6:
                flag += ' ✗'; ok = False
            if gap < 0.4 - 1e-6:
                flag += ' ✗ 声のあとの間が短い'; ok = False
        if b['kind'] == 'ov' and gap < 0.4 - 1e-6:
            flag += ' ✗ 声のあとの間が短い'; ok = False
        print(f"  {name:<30} {b['start']:6.2f}〜{b['end']:6.2f}  声 {b['v0']:6.2f}–{v1:6.2f}  次まで {gap:5.2f}{flag}")
    # 特徴の部分：名前を言っているあいだに見えていて、紹介のあいだに画面を横切りきる
    print('特徴の部分（色の範囲）')
    for g in SEG:
        if g['h'] is None:
            continue
        b = PAT_BLOCK[g['idx']]
        t_in = g['T'] + (g['h'] - g['s0'])/SLOW - (W - XC)/SCROLL
        t_out = g['T'] + (g['hb'] - g['s0'])/SLOW + XC/SCROLL
        seen = t_in <= b['v0'] + 0.05 and t_out >= b['v0'] + min(1.2, b['vlen'])
        crossed = t_out <= b['end'] + 1e-6
        ok &= seen and crossed
        print(f"  {g['pat']['name']}：右端に入る {t_in:6.2f}秒 → 左端から抜ける {t_out:6.2f}秒（名前 {b['p']:.2f}・声 {b['v0']:.2f}・"
              f"紹介の終わり {b['end']:.2f}）{'' if seen else ' ✗ 名前のあいだに見えない'}{'' if crossed else ' ✗ 横切りきらない'}")
    # はみ出し：流れ全体の波形の上下が、字のあいだに収まる
    vmax, vmin = stream_extent()
    top, bot = BASE - vmax*G, BASE - vmin*G
    nb = text_box(PATTERNS[5]['name'], NAME_SZ, 900, NAME_CY)
    act_top = min(text_box(s, ACT_SZ, 600, ACT_Y0)[0] for p in PATTERNS for s, _ in p['lines'][:1])
    print(f"はみ出し：波形 y {top:.0f}〜{bot:.0f}（いつでも）／パターン名の下端 {nb[1]}／次の対応の上端 {act_top}")
    ok &= top >= nb[1] + 10 and bot <= act_top - 10 and top >= STRIP_TOP - 1 and bot <= STRIP_BOT + 1
    # 文言
    spec_path = os.path.join(HERE, '..', 'docs', 'reel21_v2_spec.md')
    spec = open(spec_path, encoding='utf-8').read() if os.path.exists(spec_path) else None
    print('次の対応（画面の行）')
    for pat in PATTERNS:
        back = act_from_lines(pat)
        if back != pat['act'] or (spec is not None and pat['act'] not in spec):
            print(f"  ✗ {pat['name']}：文言がちがう"); ok = False
        rows, wmax = act_layout(pat)
        x0 = min(x for _, x, _, _ in rows)
        bot_ = max(text_box(s, ACT_SZ, 600, cy)[1] for s, _, cy, _ in rows)
        flag = '' if (wmax <= ACT_W and x0 >= 160 - 1 and bot_ <= 1545) else '  ✗'
        ok &= not flag
        print(f"  {pat['name']}：{len(rows)}行 幅{wmax:.0f}px 下端{bot_}{flag}  " + ' ／ '.join(s for s, _ in pat['lines']))
    for s in screen_strings() + list(NARR.values()):
        if any(w in s for w in NG_WORDS):
            print(f'  ✗ 出してはいけない言葉：{s}'); ok = False
    for p in PLACES:
        for s_, sz, wt in ((f"{p['no']} {p['name']}", TITLE_SZ, 900), (p['ov'], OVL_SZ, 600)):
            if text_w(s_, sz, wt) > W - 2*MARGIN:
                print(f'  ✗ 広い：{s_}'); ok = False
    tt = text_box(f"{PLACES[0]['no']} {PLACES[0]['name']}", TITLE_SZ, 900, TITLE_CY)
    ot = text_box(TITLE, OPEN_TITLE_SZ, 900, OPEN_TITLE_CY)
    sub_top, _ = parts_top(TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE)
    print(f"上：場所の名前 y {tt[0]}〜、冒頭の題 y {ot[0]}〜{ot[1]}、見るのは5か所 上端 {sub_top}（300 以上）")
    ok &= tt[0] >= 300 and ot[0] >= 300 and sub_top > ot[1]
    ey = [end_list_pos(k)[1] for k in range(5)]
    print(f"最後：5か所 y {min(ey)}〜{max(ey)}、問いかけ {END_ASK_CY}、保存 {END_SAVE_CY}")
    # ループ
    print(f'ループ：t={DUR:.4f} の流れの時刻 {c_of(DUR) - C0:.6f} ＝ 1周 {LTOT:.6f}')
    ok &= abs(c_of(DUR) - C0 - LTOT) < 1e-6
    # 顔：こぶの中に、はみ出さず入っているか（全編を 0.1秒ごとに）
    if faces:
        import characters
        bad, n_f, worst = 0, 0, 1e9
        for t in np.arange(0.0, DUR, 0.1):
            for f in characters.plan_faces(sys.modules[__name__], t):
                n_f += 1
                d = characters.face_clearance(sys.modules[__name__], t, f)
                worst = min(worst, d)
                if d < 1.0:
                    bad += 1
                    if bad <= 5:
                        print(f'  ✗ 顔が線にかかる t={t:.1f} {f}')
        print(f'顔：{n_f}個（0.1秒ごと）を確かめた。線とのいちばん近いすき間 {worst:.2f}（1 より大きい＝はみ出さない）')
        ok &= bad == 0
    print('OK' if ok else '✗ 見直す')
    return ok


def ffmpeg_bin():
    p = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
    if os.path.exists(p):
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def render_chunk(args):
    i0, i1, fps, path, crf, preset, vf = args
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-']
    if vf:
        cmd += ['-vf', vf]
    cmd += ['-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path




def render(out, fps, jobs, crf, preset, vf=None):
    total = int(round(DUR*fps))
    step = math.ceil(total / jobs)
    tmp = os.path.join(os.path.dirname(out), 'parts_' + os.path.splitext(os.path.basename(out))[0])
    os.makedirs(tmp, exist_ok=True)
    args = [(i, min(total, i+step), fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset, vf)
            for j, i in enumerate(range(0, total, step))]
    with Pool(jobs) as pool:
        parts = pool.map(render_chunk, args)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-c:v', 'copy', '-movflags', '+faststart', out], check=True)
    print(out)




# --- 書き出し ---------------------------------------------------------------------
def beeps(path, sr=44100):
    """QRS が画面の真ん中を通るときに「ピッ」（心室の拍は低い音）。冒頭・最後の洞調律も鳴らす。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for tb, kind, nseg, r in BEATS:
        if KINDS[kind][0] is None:
            continue
        ts = (tb - C0) / SLOW
        while ts >= DUR:
            ts -= DUR
        while ts < 0:
            ts += DUR
        f = 960.0 if kind in ('N', 'Q') else 720.0
        Ln = int(0.08*sr)
        tt = np.arange(Ln)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr)
        a[j:j+Ln] += s[:max(0, min(Ln, n-j))]
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel21_v4.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel21_v4_hq.mp4')
    ap.add_argument('--preview', action='store_true', help='スマホ確認用（540×960・30fps）。out/preview_low.mp4')
    o = ap.parse_args()
    if o.check:
        assert check(); return
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    if o.thumb:
        p = os.path.join(HERE, 'out', 'thumb_reel21v4.png')
        thumbnail().save(p); print(p); return
    if o.still:
        for s in o.still:
            p = os.path.join(HERE, 'out', f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    if o.preview:
        render(os.path.join(HERE, 'out', 'preview_low.mp4'), 30, o.jobs, 26, 'veryfast',
               vf='scale=540:960:flags=lanczos')
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    out = o.out
    if o.hq and out == ap.get_default('out'):
        out = os.path.join(HERE, 'out', 'reel21_v4_hq.mp4')
    render(out, o.fps, o.jobs, crf, preset)


if __name__ == '__main__':
    main()
