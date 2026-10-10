"""第21弾v3 致死性不整脈 見るのは5か所（波形は v2 と同じ。見せ方を「見る場所ごとの場面」に作り直した）

決まった中身は docs/reel21_v2_spec.md（次の対応の文言はそのまま使う）、根拠は docs/reel21_v2_evidence.md。
波形の定義（ev・art・gain・hl）は reel21_v2/make_reel21v2.py と同じ（ここに写した）。

構成（12個の一覧はやめた）：
1. 冒頭（0〜約3秒）：「致死性不整脈」「見るのは5か所」（大きな黄色の「5」）。下で波形が流れ、そのまま場面①の1本目になる
2. 5つの場面（見る場所ごと。① → ⑤）
   - 上：場所の名前（大きく、場所の色）と、その下に「何を見るか」の1行
   - 中：その場所の波形を縦に並べる（名前のラベル＋実際の速さで流れる波形。25mm/秒・横 1mm＝14px）
   - はじめ（場所の説明）は全部を同じ扱いで。そのあと1つずつ紹介：いまの波形は大きく（10mm/mV）、特徴の部分を場所の色で。
     ほかは小さく薄く（アコーディオン）
   - 下：いまのパターンの「→ 次の対応」（固定の場所）
   - 場面のつなぎ目は、前の場面が上へ抜けて薄くなり、次の場面が下から上がってくる（何もない画面にはしない）
3. 最後：5か所（場所の色・小さな波形つき）→「どこを見落としやすい？コメントで教えてね」→「保存して見返してね」（緑）
   → 冒頭の画面へ戻る（ループ）

秒数は、表 BLOCKS（冒頭・場所の説明・パターン・最後）から決める。
【仮の秒数】ナレーションは録音前。いまは台本の字数から声の長さを見積もっている（1.2倍速で 約9字/秒）。
録音が届いたら align_vo.py で声の長さを測り、voice_len.json に書く → この表が声に合わせて組み直される。

使い方:
    python3 make_reel21v3.py --check      # 検算・秒数の表・字の幅と重なり
    python3 make_reel21v3.py --still 20   # 1コマだけ（out/still_020.0.png）
    python3 make_reel21v3.py --thumb      # サムネイル（透かしなし）
    python3 make_reel21v3.py --jobs 2     # 書き出し・60fps（音なし。out/reel21_v3.mp4）
    python3 make_reel21v3.py --hq         # 高画質（out/reel21_v3_hq.mp4）
    python3 make_reel21v3.py --preview    # スマホ確認用の軽い版（540×960・30fps。out/preview_low.mp4）
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


def p_sinus(t):                   # P波 0.24mV（ふつうの範囲 2.5mm 以下。拡大したとき顔が中に入る高さ）
    return 0.24*_g(t, 0.0, 0.026)


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


# --- 秒数の表（BLOCKS） ---------------------------------------------------------------
# 各ブロック：kind（open／ov／pat／end）、key（NARR のキー）、start・dur（秒）、voice（声の始まり・長さ）
# - open：冒頭。声は OPEN_LEAD 秒から。長さは OPEN_MIN 以上
# - ov：場所の説明。前の場面からの切りかえ（XF 秒）の真ん中が始まり。声は LEAD_OV 秒から、言い終わって GAP_OV 秒で1つめのパターンへ
# - pat：パターンの紹介。いまの波形が大きくなり（ACC 秒）、声は LEAD_PAT 秒から。言い終わって GAP_PAT 秒（≥0.4秒）あけて次へ。
#        次の対応は TEXT_IN 秒から出し（0.3秒で）、終わりの 0.25秒で消す。全部見えている時間が「1字 READ_S_PER_CHAR 秒（最低 READ_MIN）」以上
# - end：最後。声「見るのは5か所…」は END_LEAD から、「保存して…」はそのあと END_GAP。言い終わって END_HOLD、最後の LOOP_FADE で冒頭へ戻る
OPEN_LEAD, OPEN_MIN, OPEN_GAP = 0.10, 3.0, 0.6
LEAD_OV, GAP_OV, OV_MIN = 0.40, 0.55, 2.8
LEAD_PAT, GAP_PAT, PAT_MIN = 0.45, 0.65, 4.0
TEXT_IN, TEXT_FADE_IN, TEXT_FADE_OUT = 0.50, 0.30, 0.25
READ_S_PER_CHAR, READ_MIN = 0.11, 4.0
END_LEAD, END_GAP, END_HOLD = 0.35, 0.35, 1.2
LOOP_FADE = 0.75
FPS_GRID = 60


def _q(x):
    """コマ（1/60秒）にそろえる。"""
    return math.ceil(x*FPS_GRID - 1e-6) / FPS_GRID


def read_need(i):
    return max(READ_MIN, READ_S_PER_CHAR*act_chars(PATTERNS[i]))


ZOOM = 2.5                        # 紹介中の拡大（ふつう。パターンの zoom で変えられる）
HI_PXS = 25 * 14.0 * ZOOM          # 紹介中：実際の1秒 = 875px（2.5倍のとき）
HI_MV = 10 * 14.0 * 2.0            # 顔の大きさの基準（280px/mV のとき 1）


def zoom_of(i):
    return PATTERNS[i].get('zoom', ZOOM)


def hi_pxs(i):
    return 25 * 14.0 * zoom_of(i)


def hi_mv(i):
    return 10 * 14.0 * zoom_of(i)


def event_need(i):
    """特徴の部分が右端に入ってから左端へ抜けきるまで（紹介の始まりから・秒）。色の範囲が全部のパターンは 0。"""
    pat = PATTERNS[i]
    if pat['hl'] is ALL:
        return 0.0
    a, b = pat['hl'][0]
    return pat['enter'] + ((b - a) + W / hi_pxs(i)) / pat['slow'] + 0.2


def build_blocks():
    blocks, t = [], 0.0

    def add(kind, key, dur, lead, **kw):
        nonlocal t
        dur = _q(dur)
        blocks.append(dict(kind=kind, key=key, start=t, dur=dur, end=t + dur,
                           v0=t + lead, vlen=VOICE_LEN[key], **kw))
        t += dur

    add('open', '冒頭', max(OPEN_MIN, OPEN_LEAD + VOICE_LEN['冒頭'] + OPEN_GAP), OPEN_LEAD)
    for s in range(len(PLACES)):
        add('ov', f'場所{s}', max(OV_MIN, LEAD_OV + VOICE_LEN[f'場所{s}'] + GAP_OV), LEAD_OV, scene=s)
        for i in SCENE_PATS[s]:
            key = PATTERNS[i]['key']
            d_voice = LEAD_PAT + VOICE_LEN[key] + GAP_PAT
            d_read = TEXT_IN + TEXT_FADE_IN + read_need(i) + TEXT_FADE_OUT
            d_event = event_need(i)
            add('pat', key, max(PAT_MIN, d_voice, d_read, d_event), LEAD_PAT, scene=s, pat=i,
                d_voice=d_voice, d_read=d_read, d_event=d_event)
    v_end, v_save = VOICE_LEN['まとめ'], VOICE_LEN['保存']
    add('end', 'まとめ', END_LEAD + v_end + END_GAP + v_save + END_HOLD + LOOP_FADE, END_LEAD,
        save0=None)
    b = blocks[-1]
    b['save0'] = b['v0'] + v_end + END_GAP
    return blocks, t


BLOCKS, DUR = build_blocks()
PAT_BLOCK = {b['pat']: b for b in BLOCKS if b['kind'] == 'pat'}
OV_BLOCK = {b['scene']: b for b in BLOCKS if b['kind'] == 'ov'}
OPEN_B = BLOCKS[0]
END_B = BLOCKS[-1]


def scene_span(s):
    """場面 s の [場所の説明の始まり, 最後のパターンの終わり]。"""
    return OV_BLOCK[s]['start'], PAT_BLOCK[SCENE_PATS[s][-1]]['end']


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


# --- 帯ごとの時計 ------------------------------------------------------------------
# 帯 i の画面の中央にある時刻（パターンの rel）を c_i(t) とする。ふだんは実際の速さ（1秒に1秒）で進み、
# その帯を紹介しているあいだ（紹介の始まりから ACC 秒で切りかえ）は slow 倍で進む。
# 画面の x の点は rel = c_i(t) + (x − XC)/pxs（pxs：その時の横の倍率。ふつう 350、紹介中 700）。
# 表 BLOCKS から作るので、録音に合わせて秒数を組み直しても、そのままついていく。
CLOCK_DT = 1/240
_TG = np.arange(-2.0, DUR + 2.0, CLOCK_DT)


def _speed(i):
    b = PAT_BLOCK[i]
    sl = PATTERNS[i]['slow']
    u_in = np.clip((_TG - b['start']) / 0.5, 0, 1)
    u_out = np.clip((_TG - b['end']) / 0.5, 0, 1)
    u = u_in*u_in*(3 - 2*u_in) * (1 - u_out*u_out*(3 - 2*u_out))
    return 1 + (sl - 1)*u


_C = {}
for _i in range(N_PAT):
    _sp = _speed(_i)
    _cum = np.concatenate([[0.0], np.cumsum((_sp[1:] + _sp[:-1]) / 2 * CLOCK_DT)])
    _C[_i] = _cum - np.interp(0.0, _TG, _cum)          # C_i(0) = 0


def clock_raw(i, t):
    t = np.asarray(t, dtype=float)
    lo, hi = _TG[0], _TG[-1]
    c = np.interp(t, _TG, _C[i])
    c = np.where(t < lo, _C[i][0] + (t - lo), c)
    return np.where(t > hi, _C[i][-1] + (t - hi), c)


def t_of_clock(i, c):
    """clock_raw の逆（時刻）。"""
    return float(np.interp(c, _C[i], _TG))


def phase_of(i):
    """帯 i の位相：特徴の部分（hl の始まり）が、紹介の始まりから enter 秒で右端に入ってくるようにする。
    色の範囲が全部のパターンは、紹介の始まりで周期の頭が画面の中央に。"""
    pat = PATTERNS[i]
    b = PAT_BLOCK[i]
    if pat['hl'] is ALL:
        return -float(clock_raw(i, b['start']))
    te = b['start'] + pat['enter']
    return pat['hl'][0][0] - (W - XC) / hi_pxs(i) - float(clock_raw(i, te))


PHASE = {i: phase_of(i) for i in range(N_PAT)}


def clock(i, t):
    return clock_raw(i, t) + PHASE[i]


def rel_at(i, t, x, pxs=F_PXS):
    return clock(i, t) + (np.asarray(x, dtype=float) - XC) / pxs


def x_of(i, t, rel, pxs=F_PXS):
    """rel_at の逆：パターンの時刻 rel が、時刻 t に画面のどの x にあるか。"""
    return XC + (np.asarray(rel, dtype=float) - clock(i, t)) * pxs


def screen_speed(i, t, pxs):
    """画面の上で波形が流れる速さ（px/秒）。"""
    dt = 1/120
    return float(clock(i, t + dt) - clock(i, t - dt)) / (2*dt) * pxs


# --- 拍ごとのできごと（あとでキャラクターを重ねるため） --------------------------------------
# 種類ごとの T波の頂点（R から・秒）。V（PVC）は逆向きのT
T_PEAK = {'N': 0.27, 'Q': 0.40, 'V': 0.25, 'X': 0.27, 'W': 0.34}


def beat_events(i, rel0, rel1):
    """パターン i の、rel0〜rel1 にあるできごと [(種類, rel)]。種類：
    'P'（伝わったP波の頂点）・'P_dropped'（QRSが続かないP波。モビッツII型の抜け）・'P_dissoc'（完全房室ブロックの、QRSと関係のないP波）・
    'QRS'（ふつうのQRS・補充調律のR）・'PVC'（PVC・VT・多形性VT の拍）・'T'（T波の頂点）。
    トルサードの区間で消した拍は入れない。VF・心静止は拍がないので空。"""
    pat = PATTERNS[i]
    L = pat['L']
    out = []
    for r, kind in periodic_beats(pat, rel0, rel1):
        if pat.get('gain') is not None and pat['gain'](np.array([r]), L)[0] < 0.5:
            continue
        q, p, pr = KINDS[kind]
        if p is not None:
            if q is None:
                out.append(('P_dissoc' if pat['key'] == '完全房室ブロック' else 'P_dropped', r))
            else:
                out.append(('P', r - pr))
        if q is not None:
            out.append(('PVC' if kind in ('V', 'X') else 'QRS', r))
            out.append(('T', r + T_PEAK[kind]))
    if pat['key'] == '多形性VT':
        for k in range(int(math.floor(rel0 / L)) - 1, int(math.ceil(rel1 / L)) + 1):
            for c, a, _ in POLY:
                out.append(('PVC', k*L + c))
    return sorted([(e, r) for e, r in out if rel0 <= r <= rel1], key=lambda q_: q_[1])


def strip_events(geo, t):
    """帯の形（geo：draw_strip が返すもの）と時刻 t から、画面に見えているできごと [dict(type, rel, x, y)]。
    y はその点の波形の高さ（画面の y）。"""
    i = geo['i']
    pxs = geo.get('pxs', F_PXS)
    r0, r1 = rel_at(i, t, geo['x0'], pxs), rel_at(i, t, geo['x1'], pxs)
    ev = beat_events(i, float(r0), float(r1))
    if not ev:
        return []
    rels = np.array([r for _, r in ev])
    v = pattern_wave(i, rels)
    xs = x_of(i, t, rels, pxs)
    return [dict(type=e, rel=float(r), x=float(x) + geo.get('dx', 0), y=float(geo['base'] - vv*geo['g']))
            for (e, r), x, vv in zip(ev, xs, v)]


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


def draw_strip(base, i, t, st, x0=0, x1=W, col_all=None, part='all'):
    """帯 i（パターン i をくり返した波形）を、状態 st（基線 y・倍率 g・濃さ a・線の太さ lw・グロー glow・
    特徴の色の強さ hl・緑の強さ green）で描く。col_all があれば全部をその色で。"""
    a = st['a']
    dx = int(round(st.get('dx', 0.0)))
    pxs = st.get('pxs', F_PXS)
    geo = dict(i=i, base=st['base'], g=st['g'], a=a, x0=x0, x1=x1, dx=dx, kind=st.get('kind'), pxs=pxs)
    # 場面の切りかえ（横に押し出す）では、帯ごと dx ずらす。波形は帯の中の x で計算し、見えるところだけ描く
    vx0, vx1 = max(x0, -dx - 30), min(x1, W - dx + 30)
    if a <= 0.01 or vx1 <= vx0:
        return geo
    x0, x1 = vx0, vx1
    pat = PATTERNS[i]
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = rel_at(i, t, xs, pxs)
    v = pattern_wave(i, rel)
    ys = st['base'] - v*st['g']
    pad = 26
    y_lo = int(math.floor(ys.min())) - pad
    y_hi = int(math.ceil(ys.max())) + pad
    bx0 = int(x0) - pad
    size = (int(x1 - x0) + 2*pad, max(4, y_hi - y_lo))
    lay = Image.new('RGBA', size, (0, 0, 0, 0))
    base_col = mix(OPEN_COL, WAVE_GREEN, st['green'])
    if col_all is not None:
        groups = [(np.ones(len(xs), bool), col_all)]
    else:
        m = hl_mask(pat, rel)
        hl_col = mix(base_col, pat['col'], st['hl'])
        groups = [(~m, base_col), (m, hl_col)]
    for sel0, col in groups:
        if not sel0.any():
            continue
        sel = sel0 | np.roll(sel0, 1) | np.roll(sel0, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - y_lo)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
        lay.alpha_composite(glow_line(size, runs, col, st['lw'], a, st['glow'], part))
    base.alpha_composite(lay, (bx0 + dx, y_lo))
    return geo


# --- 場面の並べ方（アコーディオン） ---------------------------------------------------
TITLE_CY, TITLE_SZ = 340, 54       # 場所の名前
OVL_CY, OVL_SZ = 410, 34           # 何を見るか（1行）
STACK_Y0, STACK_Y1 = 446, 1312     # 波形を並べる範囲
ACT_Y0, ACT_PITCH, ACT_SZ = 1364, 44, 32   # 次の対応（最大3行）の1行目の字の中心・行の間隔・字の大きさ
ACT_W = 760                        # 次の対応の幅の上限
LBL = {  # ラベル（パターンの名前）：字の大きさ・太さ・行の高さ・波との余白
    'ov': dict(sz=34, wt=800, h=46, pad=12),
    'hi': dict(sz=46, wt=900, h=60, pad=14),
    'co': dict(sz=26, wt=700, h=34, pad=6),
}
STRIP_GAP = 10
OV_GAINS = (F_MV, F_MV*0.5, F_MV*0.4, F_MV*0.3)    # 場所の説明のときの倍率（入るいちばん大きいもの）
CO_GAINS = (F_MV*0.3, F_MV*0.25, F_MV*0.2)          # 小さくした波形の倍率
HI_ROOM_UP, HI_ROOM_DOWN = 30, 120  # いま紹介中の帯：波の上の余白と、基線から下の余白（あとで重ねるキャラクター用。落ちるQRSなど）
OPEN_BASE = 1050                   # 冒頭の波形の基線（太い線の上）
LABEL_X = 135


def _snap_up(y, step):
    return GRID_Y0 + math.ceil((y - GRID_Y0) / step - 1e-9) * step


def _stack(items):
    """items: [(パターン, 種類 'ov'/'hi'/'co', 倍率)] → 各帯の基線・ラベルの中心と、下端。
    10mm/mV と 5mm/mV の帯は基線を太い線（70px）に、ほかは細い線（14px）にのせる。"""
    y = STACK_Y0
    out = []
    for i, kind, g in items:
        L_ = LBL[kind]
        vmax, vmin = extent(i)
        up, down = vmax*g, -vmin*g
        below = down + L_['pad']
        if kind == 'hi':                  # キャラクター用の余白（上に HI_ROOM_UP、基線の下に HI_ROOM_DOWN 以上）
            up += HI_ROOM_UP
            below = max(below, HI_ROOM_DOWN)
        step = 70 if g in (F_MV, F_MV*0.5) else 14
        base = _snap_up(y + L_['h'] + L_['pad'] + up, step)
        lbl_cy = base - up - L_['pad'] - L_['h']/2 + 2
        out.append(dict(i=i, kind=kind, g=g, base=base, lbl_cy=lbl_cy, below=below))
        y = base + below + STRIP_GAP
    return out, y - STRIP_GAP


def _fit(items_fn, gain_list):
    for g in gain_list:
        out, bot = _stack(items_fn(g))
        if bot <= STACK_Y1:
            return out, bot
    return out, bot


_LAYOUT = {}


def scene_layout(s, mode):
    """場面 s の並べ方。mode：'ov'（場所の説明。全部同じ扱い）／パターン番号（その帯を大きく、ほかを小さく）。
    かたまりを縦の真ん中へ、太い線の間隔（70px）ごとに動かす（基線は線の上のまま）。"""
    k = (s, mode)
    if k in _LAYOUT:
        return _LAYOUT[k]
    pats = SCENE_PATS[s]
    if mode != 'ov':
        _LAYOUT[k] = big_layout(s, mode)
        return _LAYOUT[k]
    out, bot = _fit(lambda g: [(i, 'ov', g) for i in pats], OV_GAINS)
    top = min(o['lbl_cy'] - LBL[o['kind']]['h']/2 for o in out)
    shift = math.floor(((STACK_Y1 - bot) - (top - STACK_Y0)) / 2 / 70) * 70
    shift = max(-(top - STACK_Y0) // 70 * 70, min(shift, (STACK_Y1 - bot) // 70 * 70))
    res = {}
    for o in out:
        kind = o['kind']
        L_ = LBL[kind]
        i = o['i']
        st = dict(base=o['base'] + shift, g=o['g'], lbl_cy=o['lbl_cy'] + shift, green=1.0, below=o['below'],
                  lbl_sz=L_['sz'], lbl_wt=L_['wt'], kind=kind, pxs=F_PXS)
        if kind == 'hi':
            st.update(a=1.0, lw=4.5, glow=1.0, hl=1.0, lbl_a=1.0, lbl_col=PATTERNS[i]['col'])
        elif kind == 'ov':
            st.update(a=1.0, lw=3.6, glow=0.6, hl=1.0, lbl_a=1.0, lbl_col=mix(LIGHT, PATTERNS[i]['col'], 0.55))
        else:
            st.update(a=0.38, lw=2.4, glow=0.0, hl=0.8, lbl_a=0.55, lbl_col=GREY)
        res[i] = st
    _LAYOUT[k] = res
    return res


# 紹介中：その波形だけを 2倍に拡大（1mm＝28px）して大きく。ほかの波形は隠し、場所のパターンは上の小さな札（チップ）で示す
CHIP_CY, CHIP_SZ = 470, 24         # パターンの札の字の中心・大きさ
BIG_LBL_CY = 530                   # 紹介中のパターンの名前（46px）の字の中心
BIG_TOP, BIG_Y1 = 568, 1312        # 拡大した波形（とキャラクター・小物の余白）の範囲
UP_ROOM = {'心静止': 230, 'R on T': 40}                       # 波の上の余白（px）。心静止はプラグ・CPR の手
DOWN_ROOM = {'モビッツII': 200, 'PEA1': 260, 'PEA2': 250}     # 基線の下の余白（px）。落ちるQRS・ハートと脈をみる手


def big_room(i):
    key = PATTERNS[i]['key']
    vmax, vmin = extent(i)
    up = vmax*hi_mv(i) + UP_ROOM.get(key, 18)
    down = max(-vmin*hi_mv(i) + 18, DOWN_ROOM.get(key, 30))
    return up, down


def big_layout(s, i):
    """場面 s でパターン i を紹介しているときの並べ方。i は拡大（横 700px/秒・縦 280px/mV）、ほかは隠す（その位置で消える）。
    背景のマス目は、この基線を太い線にして、1mm＝28px に広げる。"""
    ov = scene_layout(s, 'ov')
    res = {}
    for j in SCENE_PATS[s]:
        up, down = big_room(j)
        avail = BIG_Y1 - BIG_TOP
        base = float(round(BIG_TOP + up + max(0.0, (avail - up - down) / 2)))
        st = dict(base=base, g=hi_mv(j), pxs=hi_pxs(j), lbl_cy=BIG_LBL_CY, green=1.0, below=down,
                  lbl_sz=46, lbl_wt=900, kind='hi' if j == i else 'hid',
                  a=1.0, lw=5.5, glow=1.0, hl=1.0, lbl_a=1.0, lbl_col=PATTERNS[j]['col'])
        if j != i:
            st.update(a=0.0, lbl_a=0.0)
        res[j] = st
    return res


def open_layout():
    """冒頭：場面①の1本目（モビッツII型）が画面の真ん中を灰色で流れ、2本目はまだ出ない。"""
    ov = scene_layout(0, 'ov')
    res = {}
    for n, i in enumerate(SCENE_PATS[0]):
        st = dict(ov[i])
        if n == 0:
            st.update(base=OPEN_BASE, g=F_MV, pxs=F_PXS, a=1.0, lw=4.5, glow=1.0, hl=0.0, green=0.0, lbl_a=0.0,
                      lbl_cy=ov[i]['lbl_cy'] + (OPEN_BASE - ov[i]['base']))
        else:
            st.update(a=0.0, lbl_a=0.0, base=ov[i]['base'] + 60, lbl_cy=ov[i]['lbl_cy'] + 60)
        res[i] = st
    return res


NUM_KEYS = ('base', 'g', 'lbl_cy', 'green', 'a', 'lw', 'glow', 'hl', 'lbl_a', 'lbl_sz', 'pxs')


def lerp_state(s0, s1, u):
    st = dict(s1)
    for k in NUM_KEYS:
        st[k] = lerp(s0[k], s1[k], u)
    # 消える帯は前半ですばやく消え、出てくる帯は後半で出る（重ならないように）
    if s1['a'] < s0['a']:
        st['a'] = lerp(s0['a'], s1['a'], ease(u*2.2))
        st['lbl_a'] = lerp(s0['lbl_a'], s1['lbl_a'], ease(u*2.2))
    elif s1['a'] > s0['a']:
        st['a'] = lerp(s0['a'], s1['a'], ease((u - 0.45) / 0.55))
        st['lbl_a'] = lerp(s0['lbl_a'], s1['lbl_a'], ease((u - 0.45) / 0.55))
    st['lbl_col'] = mix(s0['lbl_col'], s1['lbl_col'], u)
    st['lbl_sz'] = int(round(st['lbl_sz']))
    st['lbl_wt'] = s1['lbl_wt'] if u >= 0.5 else s0['lbl_wt']
    return st


ACC = 0.5                         # アコーディオンの動き（秒）
OPEN_MOVE = 0.8                   # 冒頭の波形が場面①の1本目の位置へ動く（秒）
OPEN_STAGGER = 0.45               # 2本目が出てくるまでのずれ（秒）


def scene_states(s, t):
    """場面 s の各帯の状態（時刻 t）。"""
    ov_b = OV_BLOCK[s]
    modes = [(ov_b['start'], 'ov', OPEN_MOVE if s == 0 else 0.0)] + \
        [(PAT_BLOCK[i]['start'], i, ACC) for i in SCENE_PATS[s]]
    if s == 0:
        prev = open_layout()
    else:
        prev = None
    cur = prev
    for t0, mode, dur in modes:
        if t < t0:
            break
        lay = scene_layout(s, mode)
        # 冒頭 → 場面①：1本目が上へ動いてから、2本目が出てくる（OPEN_STAGGER 秒ずらす）
        stag = OPEN_STAGGER if (s == 0 and mode == 'ov') else 0.0
        if prev is not None and dur > 0 and t < t0 + dur + stag*(len(lay) - 1):
            cur = {i: lerp_state(prev[i], lay[i], ease((t - t0 - stag*n) / dur)) for n, i in enumerate(lay)}
        else:
            cur = lay
        prev = lay
    if cur is None:
        cur = scene_layout(s, 'ov')
    return cur


def draw_scene(base, s, t, a=1.0, dy=0.0, t_wave=None, dx=0.0):
    """場面 s：場所の名前・何を見るか・波形の帯とラベル。a・dy は場面の切りかえ用（全体の濃さ・縦のずれ）。"""
    tw = t if t_wave is None else t_wave
    states = scene_states(s, t)
    sts = {}
    for i, st in states.items():
        st = dict(st)
        st['a'] *= a
        st['base'] += dy
        st['dx'] = dx
        sts[i] = st
    # 顔と手は波形の線の下に描く（線がいつも見えるように）
    pre = [dict(i=i, base=st['base'], g=st['g'], a=st['a'], x0=0, x1=W, dx=int(round(dx)), kind=st.get('kind'),
                pxs=st.get('pxs', F_PXS), lbl_cy=st['lbl_cy'], scene=s) for i, st in sts.items()]
    # 紹介中の帯：にじみ（グロー）→ 顔と手 → 線、の順に重ねる（顔がにじみで薄くならず、線はいつも上）
    his = [i for i, st in sts.items() if st.get('kind') == 'hi' and st['a'] > 0.01]
    for i in his:
        draw_strip(base, i, tw, sts[i], part='glow')
    import characters
    characters.draw(sys.modules[__name__], base, t, s, current_pattern(t), pre, layer='under')
    geos = []
    for i, st in sts.items():
        geo = draw_strip(base, i, tw, st, part='core' if i in his else 'all')
        geo['lbl_cy'] = st['lbl_cy']
        geos.append(geo)
        la = st['lbl_a'] * a
        if la > 0.01:
            put(base, PATTERNS[i]['name'], st['lbl_sz'], st['lbl_wt'], st['lbl_col'], x=LABEL_X + dx,
                cy=st['lbl_cy'], a=la, max_w=W - 2*MARGIN)
    return geos


def current_pattern(t):
    for i, b in PAT_BLOCK.items():
        if b['start'] <= t < b['end']:
            return i
    return None


def draw_overlays(img, t, scene, pattern, strip_geometry):
    """波形を描いたあとに呼ぶ（いまは何もしない）。あとで、波形の部品（P・QRS・T・PVC）に顔や手を重ねるための入り口。
    - scene：いま見えている場面の番号（0〜4。冒頭・最後は None）
    - pattern：紹介中のパターンの番号（場所の説明・冒頭・最後は None）
    - strip_geometry：見えている帯ごとの dict(i, scene, base, g, a, x0, x1, kind, lbl_cy)。
      kind：'hi'（紹介中・10mm/mV。基線の下に HI_ROOM_DOWN px 以上の余白）／'ov'／'co'（小さく薄い）。
      strip_events(geo, t) で、画面に見えている拍のできごと [dict(type, rel, x, y)] が取れる
      （type：P／P_dropped／P_dissoc／QRS／PVC／T）。拍の時刻は beat_events、画面の x は x_of で計算できる。
    キャラクター（顔と手・小物）は characters.py。"""
    import characters
    characters.draw(sys.modules[__name__], img, t, scene, pattern, strip_geometry, layer='over')


def scene_hi(s, t):
    """場面 s が「紹介中（拡大）」になっている度合い（0：場所の説明、1：紹介中）。"""
    return ease((t - PAT_BLOCK[SCENE_PATS[s][0]]['start']) / ACC)


def scene_hi_base(s, t):
    """紹介中の帯の (基線, 横の倍率 px/秒)。マス目の太い線を基線にそろえ、マスの大きさを倍率に合わせる。"""
    st = scene_states(s, t)
    his = [v for v in st.values() if v.get('kind') == 'hi']
    return (his[0]['base'], his[0]['pxs']) if his else (OPEN_BASE, F_PXS)


def draw_chips(base, s, t, a, dx=0.0):
    """紹介中：その場所のパターンを小さな札で並べる（いまのパターンは場所の色）。"""
    if a <= 0.01:
        return
    pats = SCENE_PATS[s]
    cur = current_pattern(t)
    ws = [text_w(PATTERNS[i]['name'], CHIP_SZ, 700) + 26 for i in pats]
    gap = 12
    total = sum(ws) + gap*(len(ws) - 1)
    x = XC - total/2 + dx
    d = ImageDraw.Draw(base, 'RGBA')
    for i, w in zip(pats, ws):
        on = (i == cur)
        col = PATTERNS[i]['col'] if on else DIM
        d.rounded_rectangle((x, CHIP_CY - 19, x + w, CHIP_CY + 19), radius=19, fill=(9, 19, 16, int(200*a)),
                            outline=col + (int(255*a),), width=3 if on else 2)
        put(base, PATTERNS[i]['name'], CHIP_SZ, 700, PATTERNS[i]['col'] if on else GREY, cx=x + w/2, cy=CHIP_CY, a=a)
        x += w + gap


def draw_scene_head(base, s, a, dy=0.0, dx=0.0, t=0.0):
    pl = PLACES[s]
    put(base, f"{pl['no']} {pl['name']}", TITLE_SZ, 900, pl['col'], cx=XC + dx, cy=TITLE_CY + dy, a=a, max_w=W - 2*MARGIN)
    put(base, pl['ov'], OVL_SZ, 600, LIGHT, cx=XC + dx, cy=OVL_CY + dy, a=a*0.95, max_w=W - 2*MARGIN)
    draw_chips(base, s, t, a*scene_hi(s, t), dx)


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


def act_alpha(i, t):
    b = PAT_BLOCK[i]
    return ramp(t, b['start'] + TEXT_IN, TEXT_FADE_IN) * (1 - ramp(t, b['end'] - TEXT_FADE_OUT, TEXT_FADE_OUT))


# --- 冒頭・最後・サムネイル --------------------------------------------------------
TITLE = '致死性不整脈'
TITLE_SUB = [('見るのは', 1.0, WHITE), ('5', 1.8, YEL), ('か所', 1.0, WHITE)]
OPEN_TITLE_CY, OPEN_TITLE_SZ = 560, 130
OPEN_SUB_BASE, OPEN_SUB_SZ = 790, 72
OPEN_DOTS_CY = 868                  # 「① ② ③ ④ ⑤」（場所の色）
END_HEAD = [('見るのは', 1.0, WHITE), ('5', 1.8, YEL), ('か所', 1.0, WHITE)]
END_ASK = 'どこを見落としやすい？コメントで教えてね'
END_SAVE = '保存して見返してね'
NOTE1 = '実際の速さ（25mm/秒）'      # 冒頭・場所の説明・最後（実際の速さ・1mm＝14px）
NOTE_ZOOM = '※拡大・ゆっくり表示'      # 紹介中（2倍に拡大・ゆっくり）
NOTE2 = '※数値はこの波形での一例'
NOTE_CY = (1560, 1586)
WATERMARK = '@nurse_polarbearden'
REP = [0, 3, 6, 7, 10]              # 場所ごとの代表の波形：モビッツII型・単形性VT・R on T・粗いVF・PEA（ふつうに見える）


def place_rows(base, t, y0, pitch, lbl_sz, wave_h, a_list, x0=LABEL_X, x1=W - MARGIN, t_static=None, dx=0.0):
    """5か所を、場所の色の名前＋小さな波形（実際の速さ 25mm/秒、高さ wave_h に入る倍率・最大 5mm/mV）で並べる。"""
    for s, pl in enumerate(PLACES):
        a = a_list[s]
        if a <= 0.01:
            continue
        top = y0 + s*pitch
        put(base, f"{pl['no']} {pl['name']}", lbl_sz, 800, pl['col'], x=x0 + dx, cy=top + lbl_sz*0.55, a=a)
        i = REP[s]
        vmax, vmin = extent(i)
        g = min(F_MV*0.5, (wave_h - 8) / (vmax - vmin))
        wy0 = top + lbl_sz*1.15 + 4
        bl = wy0 + 4 + vmax*g
        tt = t if t_static is None else t_static[s]
        draw_strip(base, i, tt, dict(base=bl, g=g, a=a, lw=3.0, glow=0.5, hl=1.0, green=1.0, dx=dx), x0=x0, x1=x1,
                   col_all=pl['col'])


END_ROW_Y0, END_ROW_PITCH, END_ROW_LBL, END_ROW_WAVE = 452, 158, 40, 96
END_HEAD_BASE = 390
END_ASK_CY, END_SAVE_CY = 1384, 1452
END_CHAR_BASE = 1342               # 最後に並ぶキャラクターの基線（5か所の下・問いかけの上）


def end_times():
    b = END_B
    t_list = [b['start'] + 0.15 + 0.12*s for s in range(len(PLACES))]
    t_ask = b['v0'] + max(0.6, VOICE_LEN['まとめ']*0.32)        # 「見るのは5か所。」を言い終わるころ
    return t_list, t_ask, b['save0'] - 0.1


def draw_end(im, t, a, dx=0.0):
    """最後：見るのは5か所（見出し）と5か所（場所の色・小さな波形）は押し出しで入ってくる。問いかけ・保存は声に合わせて出す。"""
    if a <= 0.004:
        return
    _, t_ask, t_save = end_times()
    draw_parts(im, END_HEAD, 60, END_HEAD_BASE, a, dx=dx)
    place_rows(im, t, END_ROW_Y0, END_ROW_PITCH, END_ROW_LBL, END_ROW_WAVE, [a]*len(PLACES), dx=dx)
    import characters
    characters.draw_end_chars(sys.modules[__name__], im, t, a*ramp(t, t_ask - 0.2, 0.4), dx, END_CHAR_BASE)
    put(im, END_ASK, 38, 800, WHITE, cx=XC + dx, cy=END_ASK_CY, a=a*ramp(t, t_ask, 0.4), max_w=W - 2*MARGIN)
    put(im, END_SAVE, 46, 900, GREEN, cx=XC + dx, cy=END_SAVE_CY, a=a*ramp(t, t_save, 0.4), max_w=W - 2*MARGIN)


def draw_open_text(im, a, dx=0.0):
    if a <= 0.004:
        return
    put(im, TITLE, OPEN_TITLE_SZ, 900, WHITE, cx=XC + dx, cy=OPEN_TITLE_CY, a=a, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE, a, dx=dx)
    gap = 96
    for k, pl in enumerate(PLACES):
        put(im, pl['no'], 50, 800, pl['col'], cx=XC + (k - 2)*gap + dx, cy=OPEN_DOTS_CY, a=a)


_GRID = None
XF = 0.8                          # 場面の切りかえ（秒）：前の場面が左へ押し出され、次の場面が右から入る（波形の流れと同じ向き）


def push(t, t_mid, d=XF):
    """切りかえの進み具合（0→1）。t_mid が真ん中。"""
    return ease((t - (t_mid - d/2)) / d)


def zoom_state(t):
    """いまの拡大の度合い zf（0：ふつう、1：紹介中）と、マス目の (小さいマス, 基準 x, 基準 y)。
    場面の押し出しのあいだは、出ていく場面と入ってくる場面を重みでまぜる。"""
    zf, ax, ay, sp = 0.0, 0.0, 0.0, 0.0
    for s in range(len(PLACES)):
        s0, s1 = scene_span(s)
        u_in = 1.0 if s == 0 else push(t, s0)
        w = u_in * (1 - push(t, s1))
        if w <= 0.0:
            continue
        z = scene_hi(s, t)
        if z <= 0.0:
            continue
        bs, px = scene_hi_base(s, t)
        zf += w*z
        sp += w*z*(px / F_PXS - 1)
        ax += w*z*XC
        ay += w*z*bs
    return zf, (F_PXMM*(1 + sp), ax, ay)


def frame(t, watermark=True):
    zf, gp = zoom_state(t)
    im = grid_cached(*gp).copy()

    # 最後 → 冒頭（ループ）：最後の画面が左へ抜け、冒頭の画面が右から入る。t = DUR で冒頭（t = 0）と同じ
    u_loop = ease((t - (DUR - LOOP_FADE)) / LOOP_FADE)
    # 冒頭の文字：0〜 出ていて、場面①の始まりで消える
    ov0 = OV_BLOCK[0]['start']
    draw_open_text(im, 1 - ramp(t, ov0 - 0.35, 0.5))

    # 場面
    geos, scene_now, best, scene_dx = [], None, 1e9, {}
    for s in range(len(PLACES)):
        s0, s1 = scene_span(s)
        u_in = 1.0 if s == 0 else push(t, s0)
        u_out = push(t, s1)
        dx = W*(1 - u_in) - W*u_out
        scene_dx[s] = dx
        if abs(dx) >= W - 1:
            continue
        a_head = ramp(t, s0, 0.45) if s == 0 else 1.0
        for g_ in draw_scene(im, s, t, 1.0, 0.0, dx=dx):
            g_['scene'] = s
            geos.append(g_)
        if abs(dx) < best:
            scene_now, best = s, abs(dx)
        draw_scene_head(im, s, a_head, 0.0, dx, t=t)

    # 最後
    u_end = push(t, END_B['start'])
    if u_end > 0.001:
        draw_end(im, t, 1.0, dx=W*(1 - u_end) - W*u_loop)
    # 冒頭へ戻るところ：冒頭の文字と波形（場面①の1本目、冒頭の位置）を t − DUR の時刻で
    if u_loop > 0.001:
        dxl = W*(1 - u_loop)
        draw_open_text(im, 1.0, dx=dxl)
        st = dict(open_layout()[SCENE_PATS[0][0]])
        st['dx'] = dxl
        draw_strip(im, SCENE_PATS[0][0], t - DUR, st)

    if t < OV_BLOCK[0]['start'] or t >= END_B['start']:
        scene_now = None
    draw_overlays(im, t, scene_now, current_pattern(t), geos)

    # 次の対応
    for i, b in PAT_BLOCK.items():
        if b['start'] <= t < b['end']:
            draw_act(im, PATTERNS[i], act_alpha(i, t), dx=scene_dx.get(PATTERNS[i]['place'], 0.0))

    put(im, NOTE1, 24, 400, GREY, x=135, cy=NOTE_CY[0], a=0.85*cl(1 - 2*zf))          # 重ならないよう、順に入れかえる
    put(im, NOTE_ZOOM, 24, 400, GREY, x=135, cy=NOTE_CY[0], a=0.85*cl(2*zf - 1))
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_CY[1], a=0.85)
    if watermark:
        put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')



# --- サムネイル ---------------------------------------------------------------------
THUMB_TITLE_CY, THUMB_TITLE_SZ = 400, 124
THUMB_SUB_BASE, THUMB_SUB_SZ = 590, 74
THUMB_ROW_Y0, THUMB_ROW_PITCH, THUMB_ROW_LBL, THUMB_ROW_WAVE = 654, 186, 44, 118


def thumb_times():
    """サムネイルの波形：特徴の部分が帯の真ん中に来る時刻（場所ごと）。"""
    xm = (LABEL_X + W - MARGIN) / 2
    out = []
    for s in range(len(PLACES)):
        i = REP[s]
        pat = PATTERNS[i]
        c = pat['L'] / 2 if pat['hl'] is ALL else sum(pat['hl'][0]) / 2
        target = c - PHASE[i] - (xm - XC) / F_PXS
        target += math.ceil(-target / pat['L']) * pat['L']        # 0 秒以降の最初
        out.append(t_of_clock(i, target))
    return out


def thumbnail():
    """サムネイル（透かしなし）。大きな「致死性不整脈」「見るのは5か所」と、5か所（場所の色）それぞれに代表の小さな波形。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    put(im, TITLE, THUMB_TITLE_SZ, 900, WHITE, cx=XC, cy=THUMB_TITLE_CY, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, THUMB_SUB_SZ, THUMB_SUB_BASE, 1.0)
    place_rows(im, 0.0, THUMB_ROW_Y0, THUMB_ROW_PITCH, THUMB_ROW_LBL, THUMB_ROW_WAVE, [1.0]*5,
               t_static=thumb_times())
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _qrs_ms(f, lim=0.12):
    tt = np.arange(-0.2, 0.3, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < lim)
    return (tt[m].max() - tt[m].min()) * 1000


def screen_strings():
    out = [TITLE] + [s for s, _, _ in TITLE_SUB] + [END_ASK, END_SAVE, NOTE1, NOTE_ZOOM, NOTE2]
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


def check():
    ok = True
    print(f"映像 {DUR:.2f}秒（{round(DUR*60)}コマ）"
          f"{'（声の長さは録音から）' if VOICE_MEASURED else '（仮：声の長さは台本の字数からの見積もり）'}")
    print('秒数の表（BLOCKS）')
    print('  ブロック                          始まり   長さ   声（始まり–終わり）  次まで  下限（声／読む）')
    for k, (name, b) in enumerate(timing_table()):
        v1 = b['v0'] + b['vlen']
        nxt = BLOCKS[k+1]['start'] if k + 1 < len(BLOCKS) else DUR
        gap = nxt - v1
        extra = ''
        if b['kind'] == 'pat':
            extra = f"  声{b['d_voice']:.2f}／読む{b['d_read']:.2f}（{act_chars(PATTERNS[b['pat']])}字）"
            if gap < 0.4 - 1e-9:
                extra += '  ← 間が短い'; ok = False
        print(f"  {name:<30} {b['start']:6.2f} {b['dur']:6.2f}   {b['v0']:6.2f}–{v1:6.2f}     {gap:5.2f}{extra}")
        if b['kind'] == 'end':
            print(f"     （保存の声 {b['save0']:.2f}–{b['save0'] + VOICE_LEN['保存']:.2f}、冒頭へ戻る {DUR - LOOP_FADE:.2f}–{DUR:.2f}）")
    # 声と次の声の間（パターンの声の終わり → 次のパターンの強調）
    # 文言
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
        bot = max(text_box(s, ACT_SZ, 600, cy)[1] for s, _, cy, _ in rows)
        flag = '' if (wmax <= ACT_W and x0 >= 160 - 1 and bot <= 1545) else '  ← 幅が広い・下が近い'
        ok &= not flag
        print(f"  {pat['name']}：{len(rows)}行 幅{wmax:.0f}px 左{x0:.0f}px 下端{bot}{flag}")
        for s, x, cy, cont in rows:
            print(f"      {'  ' if cont else ''}{s}")
    for s in screen_strings() + list(NARR.values()):
        if any(w in s for w in NG_WORDS):
            print(f'  ✗ 出してはいけない言葉：{s}'); ok = False
    if any('すぐ報' in s for s in NARR.values()):
        ok = False
    # 上の安全域
    tt = text_box(f"{PLACES[0]['no']} {PLACES[0]['name']}", TITLE_SZ, 900, TITLE_CY)
    ob = text_box(PLACES[0]['ov'], OVL_SZ, 600, OVL_CY)
    print(f'場所の名前 y {tt[0]}〜{tt[1]}、何を見るか y {ob[0]}〜{ob[1]}（上 300 以上、波形の範囲 {STACK_Y0}〜）')
    ok &= tt[0] >= 300 and ob[1] < STACK_Y0
    for p in PLACES:
        for s_, sz, wt in ((f"{p['no']} {p['name']}", TITLE_SZ, 900), (p['ov'], OVL_SZ, 600)):
            if text_w(s_, sz, wt) > W - 2*MARGIN:
                print(f'  ✗ 広い：{s_}'); ok = False
    # 並べ方（場所の説明）：範囲に入るか・ラベルと上の帯の波が重ならないか・基線がマス目の線の上か
    print(f'場所の説明の並べ方（範囲 y {STACK_Y0}〜{STACK_Y1}。実際の速さ・1mm＝14px。基線：10・5mm/mV は太い線＝70の倍数）')
    for s in range(len(PLACES)):
        lay = scene_layout(s, 'ov')
        desc, prev_bot = [], None
        for i in SCENE_PATS[s]:
            st = lay[i]
            vmax, vmin = extent(i)
            lt, lb = text_box(PATTERNS[i]['name'], st['lbl_sz'], st['lbl_wt'], st['lbl_cy'], max_w=W - 2*MARGIN)
            wt_, wb_ = st['base'] - vmax*st['g'], st['base'] - vmin*st['g']
            bad = lt < STACK_Y0 - 4 or wb_ > STACK_Y1 or lb > wt_ - 3 or (prev_bot is not None and lt < prev_bot + 3)
            grid_ok = (st['base'] - GRID_Y0) % (70 if st['g'] in (F_MV, F_MV*0.5) else 14) == 0
            if bad or not grid_ok:
                ok = False
            desc.append(f"{PATTERNS[i]['name']}[{st['g']/F_PXMM:.1f}mm/mV 字{lt}〜{lb} 波{wt_:.0f}〜{wb_:.0f}"
                        f" 基線{st['base']:.0f}{'' if grid_ok else '✗線'}]{' ✗' if bad else ''}")
            prev_bot = wb_
        print(f"  {PLACES[s]['no']}：" + ' / '.join(desc))
    # 紹介中（拡大）：名前の札・名前・波形と余白が範囲に入るか（マス目はこの基線を太い線にして 28px）
    cb = text_box(PATTERNS[0]['name'], CHIP_SZ, 700, CHIP_CY)
    nb = text_box(PATTERNS[0]['name'], 46, 900, BIG_LBL_CY)
    print(f'紹介中（拡大）：札 y {CHIP_CY-19}〜{CHIP_CY+19}、名前 y {nb[0]}〜{nb[1]}、'
          f'波形の範囲 {BIG_TOP}〜{BIG_Y1}')
    ok &= CHIP_CY - 19 > ob[1] and nb[0] > CHIP_CY + 19 and nb[1] < BIG_TOP
    for s in range(len(PLACES)):
        pats = SCENE_PATS[s]
        wsum = sum(text_w(PATTERNS[i]['name'], CHIP_SZ, 700) + 26 for i in pats) + 12*(len(pats) - 1)
        if wsum > W - 2*MARGIN:
            print(f'  ✗ 札が広い：{PLACES[s]["no"]} {wsum}px'); ok = False
        for i in pats:
            st = big_layout(s, i)[i]
            up, down = big_room(i)
            top, bot = st['base'] - up, st['base'] + down
            vmax, vmin = extent(i)
            bad = top < BIG_TOP - 1 or bot > BIG_Y1 + 1
            ok &= not bad
            print(f"  {PATTERNS[i]['name']:<14} {zoom_of(i)}倍（1mm＝{14*zoom_of(i):.0f}px） 基線 {st['base']:.0f}"
                  f"  波 {st['base'] - vmax*hi_mv(i):.0f}〜{st['base'] - vmin*hi_mv(i):.0f}"
                  f"  余白こみ {top:.0f}〜{bot:.0f}  ゆっくり {PATTERNS[i]['slow']}倍{' ✗' if bad else ''}")
    # 冒頭
    ttop = text_box(TITLE, OPEN_TITLE_SZ, 900, OPEN_TITLE_CY)
    stop, sw = parts_top(TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE)
    vmax0 = extent(SCENE_PATS[0][0])[0]
    dots = text_box('①', 50, 800, OPEN_DOTS_CY)
    print(f'冒頭：タイトル y {ttop[0]}〜{ttop[1]}、見るのは5か所 上端 {stop}（幅 {sw}）、①〜⑤ {dots[0]}〜{dots[1]}、'
          f'波の上端 {OPEN_BASE - vmax0*F_MV:.0f}')
    ok &= ttop[1] < stop and dots[1] < OPEN_BASE - vmax0*F_MV - 6 and ttop[0] >= 300
    # 最後
    eh, _ = parts_top(END_HEAD, 60, END_HEAD_BASE)
    last = END_ROW_Y0 + 4*END_ROW_PITCH + END_ROW_LBL*1.15 + 4 + END_ROW_WAVE
    ask = text_box(END_ASK, 38, 800, END_ASK_CY); sv = text_box(END_SAVE, 46, 900, END_SAVE_CY)
    print(f'最後：見出し上端 {eh}、5か所 {END_ROW_Y0}〜{last:.0f}、問いかけ {ask[0]}〜{ask[1]}、保存 {sv[0]}〜{sv[1]}')
    ok &= eh >= 300 and last < ask[0] - 6 and sv[1] <= 1530
    # 次の対応と注記
    n1, n2 = text_box(NOTE1, 24, 400, NOTE_CY[0]), text_box(NOTE2, 24, 400, NOTE_CY[1])
    print(f'注記：{n1[0]}〜{n2[1]}（1600 以下）')
    ok &= n2[1] <= 1600
    # サムネイル
    th = text_box(TITLE, THUMB_TITLE_SZ, 900, THUMB_TITLE_CY)
    tlast = THUMB_ROW_Y0 + 4*THUMB_ROW_PITCH + THUMB_ROW_LBL*1.15 + 4 + THUMB_ROW_WAVE
    print(f'サムネイル：タイトル上端 {th[0]}、5か所の下端 {tlast:.0f}（285〜1635）')
    ok &= th[0] >= 285 and tlast <= 1635
    # 特徴の部分が名前を言っているあいだに見えるか
    print('特徴の部分（色の範囲）が見えている時間（紹介の始まりから）')
    for i, pat in enumerate(PATTERNS):
        if pat['hl'] is ALL:
            continue
        b = PAT_BLOCK[i]
        ts = np.arange(b['start'], b['end'], 0.02)
        vis = []
        xs = np.arange(0, W, 4.0)
        for t in ts:
            vis.append(hl_mask(pat, rel_at(i, t, xs, hi_pxs(i))).any())
        vis = np.array(vis)
        # 新しい特徴の部分（hl の始まり）が右端に入る時刻・左端から抜けきる時刻
        a0, b0 = pat['hl'][0]
        te = b['start'] + pat['enter']
        rr = float(rel_at(i, te, W, hi_pxs(i)))
        k = round((rr - a0) / pat['L'])
        a_k, b_k = a0 + k*pat['L'], b0 + k*pat['L']
        t_in = t_of_clock(i, a_k - PHASE[i] - (W - XC)/hi_pxs(i)) - b['start']
        t_out = t_of_clock(i, b_k - PHASE[i] + XC/hi_pxs(i)) - b['start']
        v_name = (b['v0'] + 0.25, b['v0'] + min(1.2, b['vlen']))     # 名前を言っているあいだ（言い始めの 0.25秒は除く）
        seen = all(vis[(ts >= v_name[0]) & (ts <= v_name[1])])
        crossed = t_out <= b['dur'] + 1e-6
        print(f"  {pat['name']}（{pat['slow']}倍）：特徴が右端に入る {t_in:.2f}秒 → 左端から抜ける {t_out:.2f}秒（紹介 {b['dur']:.2f}秒）"
              f"{'' if crossed else ' ✗ 抜けきらない'}、名前を言うあいだ{'見えている' if seen else ' ✗ 見えない'}")
        ok &= seen and t_in >= 0.3 and crossed
    print('モデルの値')
    print(f'  モビッツII型：PR {PR:.2f}秒で一定、4つめのP波が伝わらない（4:3）')
    print(f'  完全房室ブロック：心房 {60/0.68:.0f}/分、心室 {60/1.7:.0f}/分（QRS {_qrs_ms(qrs_escape):.0f}ms）')
    print(f'  単形性VT：{60/0.32:.0f}/分、QRS幅 {_qrs_ms(qrs_vt_rs, 0.3):.0f}ms（PVC {_qrs_ms(qrs_pvc):.0f}ms）')
    print(f'  多形性VT：約{60*POLY_N/POLY_L:.0f}/分　トルサード：{TDP_B-TDP_A:.2f}秒、約{TDP_F*60:.0f}/分')
    print(f'  R on T：PVCは直前のRから {RONT_C:.2f}秒')
    print('OK' if ok else '✗ 見直す')
    return ok


# --- 書き出し ---------------------------------------------------------------------
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


def focus_strip(t):
    """モニター音を鳴らす帯：冒頭は1本目、場所の説明はその場面の1本目、紹介中はそのパターン。最後は鳴らさない。"""
    for b in BLOCKS:
        if b['start'] <= t < b['end']:
            if b['kind'] == 'open':
                return SCENE_PATS[0][0]
            if b['kind'] == 'ov':
                return SCENE_PATS[b['scene']][0]
            if b['kind'] == 'pat':
                return b['pat']
    return None


def beeps(path, sr=44100):
    """いまの帯の R（QRS）が画面の中央を通るときに「ピッ」。心室の拍は低い音。トルサードで消した拍は鳴らさない。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for i, pat in enumerate(PATTERNS):
        if not pat['ev']:
            continue
        L = pat['L']
        # 中央を通る時刻：clock(i, t) = r + kL
        c0, c1 = float(clock(i, 0.0)), float(clock(i, DUR))
        for k in range(int(math.floor(c0 / L)) - 1, int(math.ceil(c1 / L)) + 2):
            for r, kind in pat['ev']:
                if KINDS[kind][0] is None:
                    continue
                if pat.get('gain') is not None and pat['gain'](np.array([r]), L)[0] < 0.5:
                    continue
                ts = t_of_clock(i, r + k*L - PHASE[i])
                if not (0 <= ts < DUR - 0.1) or focus_strip(ts) != i:
                    continue
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel21_v3.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel21_v3_hq.mp4')
    ap.add_argument('--preview', action='store_true', help='スマホ確認用（540×960・30fps）。out/preview_low.mp4')
    o = ap.parse_args()
    if o.check:
        assert check(); return
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    if o.thumb:
        p = os.path.join(HERE, 'out', 'thumb_reel21v3.png')
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
        out = os.path.join(HERE, 'out', 'reel21_v3_hq.mp4')
    render(out, o.fps, o.jobs, crf, preset)


if __name__ == '__main__':
    main()
