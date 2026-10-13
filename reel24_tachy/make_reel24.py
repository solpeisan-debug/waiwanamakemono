"""第24弾 頻脈（幅の狭いQRS） まず覚えたい10パターン（第21弾と同じ作り）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。洞から・心房から：洞頻脈 → 洞頻脈（P波がT波に重なる）→ 心房頻拍 → 多源性心房頻拍
  → 速い心房細動 → 心房粗動2:1）
- 中部：いま紹介中の波形（大きく流れる）と、名前（はじめは「これは？」）・ひとこと（うしろに、看護師がまずすることを色で）、
  その下に心拍数カウンター「♥ 150 /分」（この回だけ。拍ごとに R-R から計算）
- 下部：⑦〜⑩ のミニ波形（2列×2段。房室結節・副伝導路のあたり：PSVT → 始まり方（PSVTと洞頻脈）→ 房室回帰性頻拍 → 接合部頻拍）
- 冒頭0〜1秒に問いかけ「この10個、全部わかる？」、最後に「何個わかった？コメントで教えてね」

波形は、パターンの周期でくり返す決まった形（乱数の種を固定）。
中部の帯は最初から最後まで消さない（2026-10-13、第25弾と同じ作り）：名前が消えると、そのパターンのコピーだけが縮んで
枠へ飛び、画面に見えている拍がすべて、その場で次のパターンの形へ変わる（くわしくは「中部の帯」の説明）。
II誘導を想定。心房細動・心房粗動のくわしいバリエーションは第26弾なので、ここでは代表の1つずつ。

使い方:
    python3 make_reel24.py --jobs 2     # 書き出し・60fps（CPUは4つなので --jobs 2）
    python3 make_reel24.py --still 20   # 1コマだけ
    python3 make_reel24.py --check      # 検算・タイミング表・字の幅
    python3 make_reel24.py --thumb      # サムネイル（透かしなし）
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
CARD_FILL = (9, 19, 16)
CARD_EDGE = (60, 78, 72)
PURPLE = (178, 150, 240)
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)

C_SIN = (110, 222, 236)          # 洞結節から（洞頻脈）
C_ATR = (255, 168, 76)           # 心房から（心房頻拍・多源性心房頻拍・心房細動・心房粗動）
C_AVN = (255, 120, 172)          # 房室結節・副伝導路のあたり（PSVT・始まり方・房室回帰性頻拍・接合部頻拍）

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
RR = 0.80                        # 前後の洞調律 75/分


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.022)


def p_ect(t):                     # P'（心房の別の場所から）：小さく、とがって、二相性（上 → 下）
    return 0.13*_g(t, 0.0, 0.013) - 0.08*_g(t, 0.030, 0.013)


def p_retro(t):                   # 逆行性P：II誘導で下向き
    return -0.13*_g(t, 0.0, 0.020)


def p_retro_j(t):                 # 接合部頻拍の逆行性P：QRSの直前で見えるよう、深めに
    return -0.20*_g(t, 0.0, 0.020)


# 多源性心房頻拍の P波（3種類以上の形）
def p_tall(t):                    # 高くとがった形
    return 0.21*_g(t, 0.0, 0.016)


def p_inv(t):                     # 下向き（心房の下のほうから。PR 0.12秒以上なので接合部ではない）
    return -0.15*_g(t, 0.0, 0.020)


def p_bi(t):                      # 二相性（下 → 上）
    return -0.105*_g(t, -0.018, 0.014) + 0.135*_g(t, 0.020, 0.015)


def qrs_rate(tc, ta=0.27):
    """幅の狭いQRS＋T波。T波の頂点 tc（R頂点から）は心拍数が速いほど早くする（QTが短くなる）。"""
    k = tc / 0.27

    def f(t):
        return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
                - 0.20*_g(t, 0.028, 0.009) + ta*_ga(t, tc, 0.060*k, 0.042*k))
    return f


qrs_normal = qrs_rate(0.27)                 # 75〜80/分
qrs_115 = qrs_rate(0.235)                   # 115〜120/分
qrs_150 = qrs_rate(0.215, 0.25)             # 130〜150/分
qrs_150h = qrs_rate(0.195, 0.25)            # ② 150/分の洞頻脈：T波を少し早く（QTが短くなる）して、T波の肩のP波のこぶを見やすく
qrs_180 = qrs_rate(0.195, 0.22)             # 180〜200/分
qrs_flut = qrs_rate(0.215, 0.08)            # 心房粗動：T波を小さめにして、粗動波が見えるように
qrs_200 = qrs_rate(0.205, 0.17)             # 房室回帰性頻拍：T波の始まりに逆行性Pの切れこみ


def qrs_avnrt(t):                 # PSVT（房室結節リエントリー）：逆行性P波がQRSの終わりに重なる（II誘導の偽S波）
    return qrs_180(t) - 0.07*_g(t, 0.046, 0.010)


AVRT_RP = 0.110                   # 房室回帰性頻拍：R頂点 → 逆行性Pの頂点。RP（QRSの始まり → Pの始まり）が 100〜140ms、
                                  # Pの始まりがQRSの終わりから 20〜50ms 後になる位置（専門医レビュー 2026-10-06：short RP に）


def p_retro_avrt(t):              # 房室回帰性頻拍の逆行性P：QRSのすぐあとの、細めの下向きの切れこみ
    return -0.14*_g(t, 0.0, 0.016)


def qrs_avrt(t):                  # 房室回帰性頻拍（順方向性）：QRSのすぐあと（STの始まり）に逆向きのP波
    return qrs_200(t) + p_retro_avrt(t - AVRT_RP)


def avrt_rp_ms():
    """⑨の RP（QRSの始まり → Pの始まり）と、QRSの終わり → Pの始まり（ms）。--check と依頼文で使う。"""
    tt = np.arange(-0.2, 0.3, 0.0005)
    q = qrs_200(tt)
    mq = (np.abs(q) > 0.03) & (tt < 0.075) & (tt > -0.15)
    q_on, q_end = tt[mq].min(), tt[mq].max()
    p = p_retro_avrt(tt - AVRT_RP)
    p_on = tt[np.abs(p) > 0.05*np.abs(p).max()].min()
    return (p_on - q_on)*1000, (p_on - q_end)*1000


# 拍の種類：(QRS＋Tの形, P波の形, P頂点 → R頂点)
KINDS = {
    'N': (qrs_normal, p_sinus, 0.16),       # 前後の洞調律（75/分）
    'S': (qrs_115, p_sinus, 0.15),          # 洞頻脈（⑧の少しずつ変わる洞調律も）
    'H': (qrs_150h, p_sinus, 0.12),         # 速い洞頻脈（P波がT波の下り坂に重なる。PRは変えない）
    'A': (qrs_150, p_ect, 0.14),            # 心房頻拍（形のちがうP'）
    'B': (qrs_150, p_ect, 0.22),            # ⑧ PSVTのきっかけのPAC（遅い道を通るのでPRが長い）
    'M1': (qrs_115, p_sinus, 0.16),         # 多源性心房頻拍：4つの形のP波・PRもばらばら
    'M2': (qrs_115, p_tall, 0.13),
    'M3': (qrs_115, p_inv, 0.135),
    'M4': (qrs_115, p_bi, 0.19),
    'F': (qrs_150, None, 0.0),              # 心房細動（P波なし。細動波は art で足す）
    'L': (qrs_flut, None, 0.0),             # 心房粗動（P波なし。粗動波は art で足す）
    'R': (qrs_avnrt, None, 0.0),            # PSVT（房室結節リエントリー）
    'O': (qrs_avrt, None, 0.0),             # 房室回帰性頻拍（逆行性Pは QRS の形に入れた）
    'J': (qrs_115, p_retro_j, 0.085),       # 接合部頻拍：逆向きのP波がQRSのすぐ前（PR 0.12秒未満）
}
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


def art_af(rel, L):                         # ⑤ 心房細動の細動波（f波）：4.5〜8Hz（270〜480/分）の不規則な揺れ
    return band_noise(rel, L, 4.5, 8.0, 0.028, 31)


FL_CYC = 0.20                               # ⑥ 心房粗動：粗動波 300/分（0.2秒ごと）


def art_flutter(rel, L):
    """粗動波（F波）：II誘導で下向きののこぎり（ゆっくり下がって、すっと戻る）。基線の平らなところがない。"""
    ph = np.mod(rel + 0.03, FL_CYC) / FL_CYC
    saw = np.where(ph < 0.78, -ph/0.78, -(1 - ph)/0.22)
    return 0.24*(saw + 0.5)


# 心房細動の R-R（不規則。平均 0.444秒＝135/分）
AF_RR = [0.40, 0.55, 0.34, 0.47, 0.38, 0.61, 0.36, 0.44, 0.52, 0.37]
AF_T = np.cumsum([0.0] + AF_RR[:-1]).tolist()
# 多源性心房頻拍の R-R と P波の形（平均 0.516秒＝116/分）
MAT_RR = [0.47, 0.44, 0.59, 0.49, 0.56, 0.58, 0.45, 0.50, 0.53]
MAT_K = ['M1', 'M3', 'M2', 'M4', 'M2', 'M1', 'M4', 'M3', 'M2']
MAT_T = np.cumsum([0.0] + MAT_RR[:-1]).tolist()
SVT_RR = 0.33                               # ⑦ PSVT 182/分


def _onset_offset():
    """⑧ 始まり方の対比（周期の頭から）：洞調律 90/分 4拍 → PAC（連結 0.36秒・PRが長い）→ PSVT 170/分 4拍
    → 突然止まって 0.80秒あく → 洞調律 75 → 少しずつ 90 → 105 → 120 → 135 → 120 → 105 → 90/分（洞頻脈）→ 次の周期の頭。
    突然のPSVTを先にして、止まったところと少しずつ変わる洞調律が、紹介の時間のうちにカウンターの位置を通るようにした。"""
    t = 0.45
    ev = [(t + k*0.667, 'S') for k in range(OO_PRE_N)]
    t += (OO_PRE_N - 1)*0.667 + OO_PAC_C
    pac = t
    ev.append((t, 'B'))
    for _ in range(OO_SVT_N):
        t += OO_SVT_RR
        ev.append((t, 'R'))
    stop = t
    t += OO_PAUSE
    ev.append((t, 'S'))
    for rr in OO_SINUS_RR:
        t += rr
        ev.append((t, 'S'))
    L = t + 0.667 - 0.45                     # 次の周期の頭まで 90/分
    return ev, L, pac, stop


OO_PAC_C = 0.36                             # PACの連結（直前のRから）
OO_SVT_RR = 0.353                           # ⑧ PSVT 170/分
OO_SVT_N = 4                                # 170 のまま止まっている時間を短く（約1.4秒）
OO_PRE_N = 4                                # PACの前の洞調律（跳ぶ瞬間に、帯の左が⑦の続きではなく洞調律になるように）
OO_PAUSE = 0.80                             # 止まってから洞調律まで（75/分）
OO_SINUS_RR = [0.667, 0.571, 0.50, 0.444, 0.50, 0.571, 0.667]   # 止まったあと少しずつ：90, 105, 120, 135, 120, 105, 90/分
OO_EV, OO_L, OO_PAC, OO_STOP = _onset_offset()

# 10パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、連続した波形 art、色を付ける範囲 hl
# tag：ひとことのうしろの色の文字（TAGS）
PATTERNS = [
    dict(no='①', name='洞頻脈', col=C_SIN, hint='Pがそろう',
         one='どの拍にも、ふつうのP波', tag='patient',
         ev=[(k*0.52, 'S') for k in range(8)], L=4.16, hl=ALL),
    dict(no='②', name='洞頻脈（P波がT波に重なる）', col=C_SIN, hint='TにPが重なる',
         one='P波がT波に重なり、PSVTに見える', tag='ecg12',
         ev=[(k*0.40, 'H') for k in range(12)], L=4.8, hl=ALL),
    dict(no='③', name='心房頻拍', col=C_ATR, hint='いつもと違うP',
         one='いつもと違うP波が、規則正しく', tag='ecg12',
         ev=[(k*0.46, 'A') for k in range(10)], L=4.6, hl=ALL),
    dict(no='④', name='多源性心房頻拍', col=C_ATR, hint='Pが3種類以上',
         one='P波の形が3種類以上・不規則', tag='patient',
         ev=list(zip(MAT_T, MAT_K)), L=sum(MAT_RR), hl=ALL),
    dict(no='⑤', name='心房細動（速い）', col=C_ATR, hint='バラバラ・Pなし',
         one='P波がなく、RRがバラバラ', tag='report',
         ev=[(t, 'F') for t in AF_T], L=sum(AF_RR), art=art_af, hl=ALL),
    dict(no='⑥', name='心房粗動（2:1）', col=C_ATR, hint='150で規則的',
         one='F波が、QRSとT波に隠れる', tag='report',
         ev=[(0.10 + k*0.40, 'L') for k in range(10)], L=4.0, art=art_flutter, hl=ALL),
    dict(no='⑦', name='PSVT（房室結節リエントリー）', col=C_AVN, hint='Pが見えない',
         one='規則正しく速い。P波が見えない', tag='report',
         ev=[(k*SVT_RR, 'R') for k in range(12)], L=12*SVT_RR, hl=ALL),
    dict(no='⑧', name='始まり方：PSVTと洞頻脈', col=C_AVN, hint='突然か、少しずつか',
         one='突然はPSVT、少しずつは洞頻脈が多い', tag='rate',
         ev=OO_EV, L=OO_L, hl=ALL),
    dict(no='⑨', name='房室回帰性頻拍（順方向性）', col=C_AVN, hint='QRSの後にP',
         one='QRSのすぐあとに、逆向きのP波', tag='report',
         ev=[(0.45 + k*0.30, 'O') for k in range(17)], L=5.1, hl=ALL),
    dict(no='⑩', name='接合部頻拍', col=C_AVN, hint='直前に逆向きP',
         one='逆向きのP波が、QRSの直前に', tag='report',
         ev=[(0.37 + k*0.52, 'J') for k in range(9)], L=4.68, hl=ALL),
]


def art_apply(pat, rel, v):
    """パターンの連続した波形（細動波・粗動波）を足す（周期 L でくり返す）"""
    if pat.get('art'):
        v = v + pat['art'](rel, pat['L'])
    return v


N_PAT = len(PATTERNS)

# --- 1拍の形を数値で（移り変わりで、数値を少しずつまぜるため。2026-10-13） ----------------------------
# 1拍＝8つの山（高さ, 位置[R頂点からの秒], 左の幅, 右の幅）。上の qrs_… ・p_… と同じ値：
#   0 q, 1 R, 2 S, 3 T, 4 偽S波（PSVT）, 5 逆行性P（房室回帰性頻拍）, 6 P波の1つめ, 7 P波の2つめ（二相性のP）
# 移り変わりでは、この数値（高さ・位置・幅）を少しずつ変える。波形の重ね合わせにしないので、
# P波・T波のこぶが2つになったり、途中で平らになったりしない。P波のない拍は、相手のP波の位置・幅で高さ0として、まぜる
P_ROWS = {                        # P頂点からの (高さ, 位置, 幅) × 2
    'sinus': [(0.15, 0.0, 0.022), (0.0, 0.030, 0.013)],
    'ect': [(0.13, 0.0, 0.013), (-0.08, 0.030, 0.013)],
    'retro_j': [(-0.20, 0.0, 0.020), (0.0, 0.030, 0.013)],
    'tall': [(0.21, 0.0, 0.016), (0.0, 0.030, 0.013)],
    'inv': [(-0.15, 0.0, 0.020), (0.0, 0.030, 0.013)],
    'bi': [(0.135, 0.020, 0.015), (-0.105, -0.018, 0.014)],   # 上向きの山を1つめに（洞のP波とまぜたとき、上向き同士がつながる）
}
# 種類ごとに：(T波の頂点, T波の高さ), 偽S波の高さ, 逆行性Pの高さ, P波の形, P頂点 → R頂点（KINDS と同じ）
KPAR = {
    'N': ((0.27, 0.27), 0.0, 0.0, 'sinus', 0.16),
    'S': ((0.235, 0.27), 0.0, 0.0, 'sinus', 0.15),
    'H': ((0.195, 0.25), 0.0, 0.0, 'sinus', 0.12),
    'A': ((0.215, 0.25), 0.0, 0.0, 'ect', 0.14),
    'B': ((0.215, 0.25), 0.0, 0.0, 'ect', 0.22),
    'M1': ((0.235, 0.27), 0.0, 0.0, 'sinus', 0.16),
    'M2': ((0.235, 0.27), 0.0, 0.0, 'tall', 0.13),
    'M3': ((0.235, 0.27), 0.0, 0.0, 'inv', 0.135),
    'M4': ((0.235, 0.27), 0.0, 0.0, 'bi', 0.19),
    'F': ((0.215, 0.25), 0.0, 0.0, None, 0.0),
    'L': ((0.215, 0.08), 0.0, 0.0, None, 0.0),
    'R': ((0.195, 0.22), -0.07, 0.0, None, 0.0),
    'O': ((0.205, 0.17), 0.0, -0.14, None, 0.0),
    'J': ((0.235, 0.27), 0.0, 0.0, 'retro_j', 0.085),
}


def _kvec(kind):
    (tc, ta), ps, rp, pk, pr = KPAR[kind]
    k = tc / 0.27
    rows = [(-0.08, -0.030, 0.008, 0.008), (1.00, 0.0, 0.011, 0.011), (-0.20, 0.028, 0.009, 0.009),
            (ta, tc, 0.060*k, 0.042*k), (ps, 0.046, 0.010, 0.010), (rp, AVRT_RP, 0.016, 0.016)]
    for a, c, s in P_ROWS[pk or 'sinus']:
        rows.append((a if pk else 0.0, -pr + c, s, s))
    return np.array(rows, dtype=float)


KVEC = {k: _kvec(k) for k in KPAR}
HAS_P = {k: KPAR[k][3] is not None for k in KPAR}


def eval_vec(vec, tau):
    v = np.zeros_like(tau)
    for a, c, sl, sr in vec:
        if a != 0.0:
            s = np.where(tau < c, sl, sr)
            v += a*np.exp(-0.5*((tau - c)/s)**2)
    return v


def blend_vec(ka, kb, w):
    va, vb = KVEC[ka], KVEC[kb]
    if w <= 0.0:
        return va
    if w >= 1.0:
        return vb
    va, vb = va.copy(), vb.copy()
    if not HAS_P[ka] and HAS_P[kb]:                # P波のない拍：相手のP波の位置・幅で、高さ0
        va[6:8, 1:] = vb[6:8, 1:]
    if HAS_P[ka] and not HAS_P[kb]:
        vb[6:8, 1:] = va[6:8, 1:]
    return va + (vb - va)*w


def beat_wave(tau, kind):
    return eval_vec(KVEC[kind], tau)


def beat_wave_fn(tau, kind):
    """元の関数（qrs_… ＋ p_…）での1拍。--check で数値の形とくらべる。"""
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    return v


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, k)
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
    """周期の中の色を付ける範囲（rel はパターンの中の時刻）。"""
    L = pat['L']
    r = np.mod(rel, L)
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-L, 0.0, L):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


# --- パターンの「拍の番号 → パターンの中の時刻」X_P(k) ----------------------------------------
# X_P(k) = r[k mod N] + (k div N)×L（r は1周期の拍の R時刻）。そのあいだは直線でつなぐ（位相 φ → 時刻）
for _p in PATTERNS:
    _ev = sorted((round(r % _p['L'], 9), k) for r, k in _p['ev'])      # 周期の中へ（⑨は 1拍が周期の外に書いてある）
    _p['r'] = [r for r, _ in _ev]
    _p['kinds'] = [k for _, k in _ev]
    _p['N'] = len(_ev)
    assert 0.0 <= _p['r'][0] and _p['r'][-1] < _p['L'], _p['no']
    _p['regular'] = len(set(_p['kinds'])) == 1 and np.ptp(np.diff(_p['r'] + [_p['r'][0] + _p['L']])) < 1e-9
    _ks = np.arange(-60, 900)
    _p['xtab_k'] = _ks
    _p['xtab'] = np.array(_p['r'])[_ks % _p['N']] + (_ks // _p['N'])*_p['L']


def xk(P, k):
    """拍の番号 k（整数の配列）のパターンの中の時刻。"""
    p = PATTERNS[P]
    k = np.asarray(k)
    return np.array(p['r'])[k % p['N']] + (k // p['N'])*p['L']


def xf(P, ph):
    """位相 ph（実数）のパターンの中の時刻（拍と拍のあいだは直線）。"""
    p = PATTERNS[P]
    return np.interp(ph, p['xtab_k'], p['xtab'])


def xinv(P, u):
    p = PATTERNS[P]
    assert np.min(u) >= p['xtab'][0] and np.max(u) <= p['xtab'][-1], 'X の表が足りない'
    return np.interp(u, p['xtab'], p['xtab_k'])


def _xk1(P, k):
    p = PATTERNS[P]
    n, j = divmod(k, p['N'])
    return p['r'][j] + n*p['L']


def _rr1(P, ph):
    fl = math.floor(ph)
    return _xk1(P, fl + 1) - _xk1(P, fl)


# --- 中部の帯：最初から最後まで1本。画面に見えている拍が、その場で次の形へ変わる（2026-10-13 作り直し） ------
# 第25弾と同じ作り。形は動画の時刻 t だけで決まる（shape_at）。名前・ひとこと・声のあいだは、そのパターンの形そのもの。
# 名前が消えると、そのパターンのコピーだけが縮んで枠へ飛ぶ（帯は消さずに流れつづける）。そのあと、画面に見えている拍が
# すべて、いっしょに次のパターンの形へ変わる（P波の形・向き・PR、偽S波・逆行性P、T波、拍の間隔とその不規則さ、
# 細動波・粗動波の大きさ）。
# - 近いもの：直接 MORPH_T 秒で（①→② 洞頻脈が速くなる、③→④→⑤→⑥ 心房から：心房頻拍 → 多源性 → 心房細動 → 心房粗動）
# - 関係のないもの（②→③、⑥→⑦、⑦→⑧、⑧→⑨、⑨→⑩）：いったん①洞頻脈の形を通る
#   （VIA_T 秒で①の形へ・VIA_HOLD 秒そのまま・VIA_T 秒で次の形へ）。「⑥が⑦に変わる」と読まれないように
# - ⑩のあと：①の形へもどして最後の画面へ。冒頭の帯も①の形なので、動画の終わりが冒頭とつながる
# 拍の位置は、画面の中央を通った拍の数（位相 Θ）を積み上げて決める。パターンごとの X_P（上）を、移り変わりのあいだは
# まぜる。中央の拍は紙送りの速さで流れ、拍の間隔が変わるとき、中央から離れた拍は少しずつ寄ったり離れたりする
# （拍が消えたり増えたり、跳んだりしない）。名前の出ているあいだは、拍は紙に止まって流れる（元の帯と同じ）
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 4.5                     # 冒頭の1文（録音 4.41秒：0.10〜4.51秒）が入り、見出しと枠が出そろう長さ
END_HOLD = 6.4                    # 全部そろってからの時間（①の形へもどる 1.15秒・まとめ 3.33秒・保存 1.41秒と、冒頭へ戻る時間）
HOOK = [3, 4, 5, 6, 8]            # ④多源性心房頻拍 → ⑤心房細動 → ⑥心房粗動 → ⑦PSVT → ⑨房室回帰性頻拍
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12
HANDOFF_EARLY = 0.35

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.6mV）
_TOP_END = 636 + 110               # 上の枠（①②③／④⑤⑥の3段）の下端
_BOT_TOP = 1298                    # 下の枠（⑦⑧／⑨⑩の2段）の上端。下端は 1528（下の注記と 19px あける）
# 見た目の上端（名前の字の上）〜下端（S波の底、約0.2mV）で余白をそろえる
# その下に心拍数カウンター（波形の下端から CNT_GAP あけて、数字の高さ CNT_H）
CNT_GAP, CNT_H = 34, 56
_MID_H = 22 + 54 + 16 + 30 + 140 + 30 + CNT_GAP + CNT_H
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + 16 + 30 + 140
CNT_TOP = F_BASE + 30 + CNT_GAP          # カウンターの数字の上端
F_Y0, F_Y1 = int(F_BASE - 200), int(_BOT_TOP - 2)
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# 紙の時刻：t=T_TITLE で、紙の時刻 0 が画面の右端に来る（止まっていた時間を引く）
OFFSET = -HALF - (T_TITLE - FREEZE) / SLOW


def te(t):
    """波形の時計：T_STOP〜T_GO は止まる。"""
    if t < T_STOP:
        return t
    if t < T_GO:
        return T_STOP
    return t - FREEZE


def tau_c(t):
    """画面の中央にある紙の時刻。"""
    return te(t) / SLOW + OFFSET


def t_of(tau_center):
    """その時刻が画面の中央に来る t（止まっているあいだは除く）。"""
    t = (tau_center - OFFSET) * SLOW
    return t if t < T_STOP else t + FREEZE


# 心拍数カウンター（この回だけの見せ方）：帯の右のほう（x = COUNT_X）を R が通った瞬間に、その拍の心拍数
# （60 ÷ 直前の拍からの間隔）に変わる。モニターと同じく、新しい拍が右から入ってきたところで数える。ピッという音も同じ瞬間。
# 名前の出ているあいだ（＝形がそのパターンそのもの）だけ出す
COUNT_X = 940
DT_REF = (COUNT_X - XC) / F_PXS              # 画面の中央から数える位置までの、紙の時間（秒）

# 声の長さ（align_vo.py で切った長さ。2026-10-07 の録音、文の中の息継ぎは 0.45秒）
VO_LEN = {'①': 3.09, '②': 3.87, '③': 3.63, '④': 4.19, '⑤': 2.99, '⑥': 3.12,
          '⑦': 3.50, '⑧': 5.33, '⑨': 4.28, '⑩': 3.76}
TITLE_VO_END = 4.51                    # 冒頭の文の終わり（0.10＋4.41）
LEAD = 0.55                            # 名前が出てから話し始めるまで（align_vo.py と同じ）
NAME_TAIL = 0.35                       # 話し終わってから名前が消えるまで
MORPH_DELAY, MORPH_T = 0.15, 1.00      # 名前が消えてから形が変わり始めるまで・直接変わる時間
VIA_T, VIA_HOLD = 0.70, 0.30           # ①の形を通るとき：①へ・①のまま・次の形へ
NAME_AFTER = 0.15                      # 形が変わり終わってから次の名前が出るまで
VIA = 0                                # 通る形：①洞頻脈（冒頭と最後の帯も①の形）
DIRECT = {1, 3, 4, 5}                  # 前のパターンから直接変わる：①→②、③→④、④→⑤、⑤→⑥
I8 = 7                                 # ⑧ 始まり方
PAC_AFTER = 1.2                        # ⑧：名前が出てから、きっかけのPACがカウンターの位置を通るまで（洞調律 90/分を少し見せる）
U8_TAIL = 0.20                         # ⑧：最後の「少しずつ」の拍（→ 90/分）がカウンターを通ってから、コピーが飛ぶまで
FLY = 0.8                                  # 中部から枠へ縮んで移る時間（コピー）
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60

DT_TL = 0.001
_TG = np.arange(0.0, 140.0, DT_TL)
_TE = np.where(_TG < T_STOP, _TG, np.where(_TG < T_GO, T_STOP, _TG - FREEZE))
_TC = _TE / SLOW + OFFSET


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u*u*(3 - 2*u)


def _j(t):
    return int(round(t / DT_TL))


OFF = {VIA: 0}                         # パターンごとの拍の番号のずれ（どの拍から見せるか）


def _fill_pure(th, j0, j1, P):
    """th[j0] から th[j1] まで、パターン P のまま（拍は紙に止まって流れる）。"""
    if j1 <= j0:
        return
    o = OFF[P]
    u0 = float(xf(P, th[j0] + o))
    th[j0:j1 + 1] = xinv(P, u0 + (_TC[j0:j1 + 1] - _TC[j0])) - o


def _fill_morph(th, j0, j1, A, B, t0, t1):
    """パターン A → B に変わるあいだ。拍の間隔は、2つのパターンのそのあたりの間隔をまぜたもの。"""
    oa, ob = OFF[A], OFF[B]
    for j in range(j0, j1):
        w = _smooth((_TG[j] - t0) / (t1 - t0))
        rr = (1 - w)*_rr1(A, th[j] + oa) + w*_rr1(B, th[j] + ob)
        th[j + 1] = th[j] + (_TC[j + 1] - _TC[j]) / rr


def _run_steps(th, j_from, steps, P_end, t_end):
    jj = j_from
    for m0, m1, A, B in steps:
        _fill_pure(th, jj, _j(m0), A)
        jj = max(jj, _j(m0))
        _fill_morph(th, jj, _j(m1), A, B, m0, m1)
        jj = _j(m1)
    _fill_pure(th, jj, _j(t_end), P_end)
    return _j(t_end)


def _circ(d, L):
    d = (d + L/2) % L - L/2
    return abs(d)


def _r_of(P, kind):
    p = PATTERNS[P]
    return p['r'][p['kinds'].index(kind)]


def _build():
    th = np.zeros(len(_TG))
    th[0] = float(xinv(VIA, _TC[0]))
    win, ev, info = [], [], {}
    j_done = 0
    for i in range(N_PAT):
        pat = PATTERNS[i]
        if i == 0:
            a = T_TITLE
            v = max(T_TITLE + 0.30, TITLE_VO_END + 0.20)
        else:
            t0 = win[-1][1] + MORPH_DELAY
            _fill_pure(th, j_done, _j(t0), i - 1)
            j_done = _j(t0)
            if i in DIRECT:
                steps = [(t0, t0 + MORPH_T, i - 1, i)]
            else:
                steps = [(t0, t0 + VIA_T, i - 1, VIA), (t0 + VIA_T + VIA_HOLD, t0 + 2*VIA_T + VIA_HOLD, VIA, i)]
            a = steps[-1][1] + NAME_AFTER
            # どの拍から見せるか（拍の番号のずれ）：名前が出る瞬間に、中央に来るパターンの中の時刻が target に近いもの。
            # ⑧は、PACが名前の出てから PAC_AFTER 秒でカウンターを通るように。ほかは周期の頭（元の帯の区間の始まり）
            target = (_r_of(i, 'B') - DT_REF - PAC_AFTER/SLOW) if i == I8 else 0.0
            cands = [0] if pat['regular'] else range(pat['N'])
            best = None
            for o in cands:
                OFF[i] = o
                tmp = th.copy()
                jj = _run_steps(tmp, j_done, steps, i, a)
                err = _circ(float(xf(i, tmp[jj] + o)) - target, pat['L'])
                if best is None or err < best[0] - 1e-9:
                    best = (err, o)
            OFF[i] = best[1]
            j_done = _run_steps(th, j_done, steps, i, a)
            ev += steps
            v = a + LEAD
        u_a = float(xf(i, th[_j(a)] + OFF[i]))       # 名前が出る瞬間に、中央にあるパターンの中の時刻
        info[i] = dict(u_a=u_a)
        b = v + VO_LEN[pat['no']] + NAME_TAIL
        if i == I8:
            # きっかけのPACがカウンターの位置を通る時刻と、最後の「少しずつ」の拍（90/分）が通る時刻
            L = pat['L']
            r_pac = _r_of(i, 'B')
            n = math.ceil((u_a + DT_REF - r_pac) / L - 1e-9)
            u_pac = r_pac + n*L - DT_REF
            t_pac = a + (u_pac - u_a)*SLOW
            u_last = pat['r'][-1] + n*L - DT_REF
            info[i].update(t_pac=t_pac, t_last=a + (u_last - u_a)*SLOW)
            v = max(v, t_pac - 0.5)                  # 「突然始まり…」が、カウンターの跳ぶところに重なるよう
            b = max(v + VO_LEN[pat['no']] + NAME_TAIL, info[i]['t_last'] + U8_TAIL)
        win.append((a, b))
    t0 = win[-1][1] + MORPH_DELAY                     # ⑩のあと：①の形へ
    _fill_pure(th, j_done, _j(t0), N_PAT - 1)
    steps = [(t0, t0 + MORPH_T, N_PAT - 1, VIA)]
    _run_steps(th, _j(t0), steps, VIA, _TG[-1])
    ev += steps
    return th, win, ev, info


_TH, CH_WIN, SHAPE_EV, _INFO = _build()
WINDOWS = list(CH_WIN)                 # (名前が出る, 名前が消えてコピーが枠へ飛び始める)
MORPHS = [(t0, t1) for t0, t1, *_ in SHAPE_EV]
T_END = WINDOWS[-1][1]
PAC_CROSS = _INFO[I8]['t_pac']         # ⑧ PACがカウンターの位置を通る時刻（align_vo.py で使う）


def shape_at(t):
    """動画の時刻 t の形：(前のパターン, 次のパターン, まぜる割合 0〜1)。"""
    P = VIA
    for t0, t1, A, B in SHAPE_EV:
        if t < t0:
            return P, P, 0.0
        if t < t1:
            return A, B, _smooth((t - t0) / (t1 - t0))
        P = B
    return P, P, 0.0


def theta(t):
    return float(np.interp(t, _TG, _TH))


# 動画の長さ：最後の2文と「何個わかった？」が入る長さ以上で、拍の位相が冒頭とそろう（ループがつながる）いちばん短い長さ
def _loop_dur():
    need = T_END + FLY + END_HOLD
    th0 = theta(0.0)
    best = None
    for n in range(int(need*FPS_LOOP), int((need + 1.2)*FPS_LOOP) + 1):
        d = n / FPS_LOOP
        ph = (theta(d) - th0) % 1.0
        err = min(ph, 1 - ph)
        if best is None or err < best[0] - 1e-9:
            best = (err, d)
    return best[1]


DUR = _loop_dur()
SEGS = [(tau_c(a), tau_c(b)) for a, b in WINDOWS]     # 名前の出ている時間に中央にある紙の時刻（説明・依頼文用）
STRIP_END = tau_c(T_END)
# ミニ波形・枠へ飛ぶコピー：名前が消える瞬間に画面にあった並び（そのパターンの形そのもの）を、そのまま流しつづける。
# パターンの中の時刻 rel ＝ 紙の時刻 − PHASE[i]
PHASE = {}
for _i in range(N_PAT):
    _b = WINDOWS[_i][1]
    PHASE[_i] = tau_c(_b) - float(xf(_i, theta(_b) + OFF[_i]))


def ypos(ks, t):
    """動画の時刻 t に、拍の番号 ks の R が画面の中央から何秒（紙の時間）のところにあるか。"""
    A, B, w = shape_at(t)
    th = theta(t)
    ya = xk(A, ks + OFF[A]) - xf(A, th + OFF[A])
    if w <= 0.0:
        return ya
    yb = xk(B, ks + OFF[B]) - xf(B, th + OFF[B])
    return (1 - w)*ya + w*yb


def screen_beats(t, margin=0.9):
    """画面にある拍：(番号の配列, 位置の配列)。"""
    th = theta(t)
    ks = np.arange(math.floor(th) - 18, math.floor(th) + 19)
    ys = ypos(ks, t)
    sel = (ys > -HALF - margin) & (ys < HALF + margin)
    return ks, ys, sel


def kind_of(P, k):
    p = PATTERNS[P]
    return p['kinds'][(k + OFF[P]) % p['N']]


def hr_at(t):
    """カウンター：(心拍数, その拍の番号, 数えてからの秒, 1つ前の拍の心拍数)。"""
    ks, ys, _ = screen_beats(t, 3.0)
    idx = np.where(ys <= DT_REF + 1e-9)[0]
    if len(idx) == 0 or idx[-1] < 2:
        return None
    n = idx[-1]
    bpm = 60.0 / (ys[n] - ys[n - 1])
    prev = 60.0 / (ys[n - 1] - ys[n - 2])
    return bpm, int(ks[n]), (DT_REF - ys[n]) * SLOW, prev


def hr_note(t, k, bpm, prev):
    """⑧だけ：カウンターの横の小さな字（↑ 1拍で跳ぶ／↓ 突然止まる／↗↘ 少しずつ）。PACがカウンターを通ってから。"""
    cur = current(t)
    if cur != I8 or t < PAC_CROSS - 0.02:
        return None
    if kind_of(I8, k) in ('B', 'R'):
        return '↑ 1拍で跳ぶ'
    if bpm < prev - 30:
        return '↓ 突然止まる'
    if bpm > prev + 1:
        return '↗ 少しずつ'
    if bpm < prev - 1:
        return '↘ 少しずつ'
    return None


_CROSS = []


def crossings():
    """R がカウンターの位置（COUNT_X）を通る時刻：[(時刻, 拍の番号, 心拍数, 紹介中のパターン or None)]。"""
    if _CROSS:
        return _CROSS
    dt = 0.002
    ts = np.arange(0.0, DUR + 0.5, dt)
    ph = np.empty(len(ts))
    for n, t in enumerate(ts):
        ks, ys, _ = screen_beats(t, 3.0)
        ph[n] = np.interp(DT_REF, ys, ks)
    for n in range(len(ts) - 1):
        if math.floor(ph[n + 1]) > math.floor(ph[n]):
            k = math.floor(ph[n + 1])
            tc = ts[n] + (k - ph[n]) / (ph[n + 1] - ph[n]) * dt
            if tc > DUR:
                break
            ks, ys, _ = screen_beats(tc + 1e-4, 3.0)
            j = int(np.where(ks == k)[0][0])
            _CROSS.append((tc, k, 60.0 / (ys[j] - ys[j - 1]), current(tc)))
    return _CROSS


# --- ミニ波形の枠 -----------------------------------------------------------------
CELL_W, CELL_H = 400, 110
COL_X = (130, 550)
TOP_Y = [396, 516, 636]
BOT_Y = [1298, 1418]
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える）
M_MV = 33.0


def cell_rect(i):
    if i < 6:
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 6
        col, row = j // 2, j % 2
        x, y = COL_X[col], BOT_Y[row]
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


def text_img(s, size, weight, col, max_w=None):
    k = (s, size, weight, col, max_w)
    if k in _TXT:
        return _TXT[k]
    sz = size
    while True:
        f = font(sz, weight)
        x0, y0, x1, y1 = f.getbbox(s)
        if max_w is None or (x1 - x0) <= max_w or sz <= 16:
            break
        sz -= 1
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (x1 - x0 + 8, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - x0, 4), s, font=f, fill=col + (255,))
    _TXT[k] = (im, asc)
    return _TXT[k]


def fit_size(s, size, weight, max_w):
    """max_w に入るまで縮めたときの字の大きさ（--check 用）。"""
    sz = size
    while sz > 16:
        x0, _, x1, _ = font(sz, weight).getbbox(s)
        if x1 - x0 <= max_w:
            break
        sz -= 1
    return sz


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


def chain_arrays(t):
    """中部の帯：画面にある拍を、すべて動画の時刻 t の形で描いた波形（mV）。
    拍ごとに、前のパターンの拍と次のパターンの拍の数値をまぜる（blend_vec）。細動波・粗動波は、大きさをまぜる。"""
    d = (FX - XC) / F_PXS
    A, B, w = shape_at(t)
    ks, ys, sel = screen_beats(t, 3.0)
    v = np.zeros_like(d)
    for k, y in zip(ks[sel], ys[sel]):
        if not (-HALF - 0.8 < y < HALF + 0.8):
            continue
        m = np.abs(d - y) < 0.75
        if m.any():
            v[m] += eval_vec(blend_vec(kind_of(A, int(k)), kind_of(B, int(k)), w), d[m] - y)
    ph = None
    for P, wt in (((A, 1 - w), (B, w)) if A != B else ((A, 1.0),)):
        if wt > 1e-6 and PATTERNS[P].get('art'):
            if ph is None:
                ph = np.interp(d, ys, ks)                # 画面の各点の位相（拍の番号を実数で）
            v = v + wt*PATTERNS[P]['art'](xf(P, ph + OFF[P]), PATTERNS[P]['L'])
    return v


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
    return v, cid


_HOOK = {}


def hook_targets():
    if not _HOOK:
        v0 = (chain_arrays(T_STOP), np.full(len(FX), -1, dtype=int))
        _HOOK['seq'] = [v0] + [hook_arrays(i) for i in HOOK] + [v0]
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


def draw_wave(v, cid, base_col, a):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(np.unique(cid).tolist()):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


def featured(t, base_col, a, cur=None):
    """中部の帯。名前の出ているあいだ（＝形がそのパターンそのもの）だけ、帯をそのパターンの色に（なめらかに）。"""
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a)
    v = chain_arrays(t)
    col = base_col
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        col = mix(base_col, PATTERNS[cur]['col'], ramp(t, a_i, 0.25)*(1 - ramp(t, b_i - 0.25, 0.25)))
    return draw_wave(v, np.full(len(FX), -1, dtype=int), col, a)


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 76, 50     # ミニ波形の帯（枠の中）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0):
    """パターン i をくり返した波形を、画面の x_lo〜x_hi に描いた RGBA（全画面サイズの一部）。
    中央 cx に来る時刻は tau_c(t)（中部の帯と同じ）。名前が消える瞬間に中部の帯に見えていた並び（PHASE）を、
    そのまま流しつづける（コピーとミニ波形は、そのパターンの形そのもの）。"""
    pat = PATTERNS[i]
    s0 = PHASE[i]
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
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        w_, a_ = ((lw_e or lw) if flag else lw), (a if flag else a*a_norm)
        if runs:
            out.alpha_composite(glow_line(size, runs, col, w_, a_, blur=blur))
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


MINI_LW_ECT = 3.8                  # ミニ波形で、色を付けた範囲の線の太さ（ほかは 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、色を付けていない範囲の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u))
    base.alpha_composite(im, pos)


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。番号とヒント）/'now'（紹介中）/'landing'（枠へ移るところ）/'done'（ミニ波形あり）"""
    x0, y0, x1, y1 = cell_rect(i)
    pat = PATTERNS[i]
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
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17,
            a=a_all, max_w=CELL_W - 30)
    elif state == 'now':
        put(base, pat['no'], 30, 700, pat['col'], x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2))
        # 「これは？」のあいだは、ヒントをそのパターンの色で明るく出す（名前が出たら消す）
        a_h = 1 - ramp(t, WINDOWS[i][0] + QUIZ_T - 0.1, 0.25)
        put(base, f"ヒント：{pat['hint']}", 24, 600, pat['col'], x=x0 + 64, cy=y0 + CELL_H/2,
            a=min(1.0, a_all*2)*a_h, max_w=CELL_W - 80)
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=CELL_W - 80)


# --- 画面 ---------------------------------------------------------------------------
YEL = (255, 214, 64)
HEADER = [('頻脈（幅の狭いQRS）', 1.0, WHITE), (str(len(PATTERNS)), 2.0, YEL), ('パターン', 1.0, WHITE)]
HEADER_BASE = 372                   # 見出しのベースライン（y）
TITLE_SUB = '心電図で気づく'
TITLE = '頻脈'
TITLE_2 = '幅の狭いQRS'
END_1 = f'幅の狭い速い脈は、この{len(PATTERNS)}パターン'
END_2 = '保存して見返してね'
END_3 = '何個わかった？コメントで教えてね'
ASK = f'この{len(PATTERNS)}個、全部わかる？'        # 冒頭0〜1秒の問いかけ
QUIZ = 'これは？'                                    # 名前の前のクイズ
QUIZ_T = 1.6                         # 「これは？」を出しておく時間（波形は約0.9秒から見えるので、見えてから約0.7秒）
ASK_END = 1.0                        # 冒頭の問いかけを消しはじめる時刻
NOTE1 = '実際の速さ（II誘導・25mm/秒）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「頻脈（幅の狭いQRS）」＋大きな黄色の「12」＋「パターン」。左右の余白（130px）に収める。"""
    if a <= 0.004:
        return
    size = 46
    while True:
        parts = [text_img(sx, int(size*k), 800, col) for sx, k, col in HEADER]
        widths = [im.size[0] - 8 for im, _ in parts]
        total = sum(widths) + 6*(len(parts) - 1)
        if total <= W - 2*130 - 10 or size <= 24:
            break
        size -= 1
    x = (W - total) / 2
    for (im, asc), w in zip(parts, widths):
        if a < 0.999:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda q: int(q*a)))
        base.alpha_composite(im, (int(x - 4), int(HEADER_BASE - 4 - asc)))
        x += w + 6


_GRID = None


# ひとことのうしろに、看護師がまずすることを色で。
# 「まず患者さん」：波形より、原因（痛み・発熱・脱水・出血・低酸素・呼吸の病気など）と患者さんの状態を見る
# 「すぐ報告」：持続する上室性の頻拍。医師に知らせる（ナレーションでは言わない）
# 「12誘導で確認」：P波の形・向き・位置は、12誘導で確かめる
# 「数字を見る」：⑧だけ。心拍数カウンターが少しずつ変わるか、1拍で跳ぶか
ONE_W = 760                         # ひとこと＋色の文字の幅の上限（左右に 160px 以上の余白。端で切れて見えないように）
TAGS = {
    'patient': ('→ まず患者さん', (120, 232, 160)),
    'report': ('→ すぐ報告', (255, 196, 64)),
    'ecg12': ('→ 12誘導で確認', (120, 196, 255)),
    'rate': ('→ 数字を見る', (190, 160, 255)),       # ⑧：心拍数カウンターの変わり方を見る
}


def one_layout(pat):
    """ひとこと＋色の文字の字の大きさと幅。ONE_W に入るまで縮める（--check でも使う）。"""
    tag = TAGS[pat['tag']]
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        if w1 + 14 + w2 <= ONE_W or sz <= 24:
            break
        sz -= 1
    return sz, w1, w2


def draw_one(im, pat, a):
    """中部のひとこと。うしろに色の文字（TAGS）を続けて、まとめて中央ぞろえ。"""
    tag = TAGS[pat['tag']]
    sz, w1, w2 = one_layout(pat)
    x0 = 540 - (w1 + 14 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=Y_ONE, a=a)
    put(im, tag[0], sz, 800, tag[1], x=x0 + w1 + 14, cy=Y_ONE, a=a)


C_HEART = (255, 92, 112)
CNT_SUB_IRREG = '1拍ごとの値（モニターは平均）'
CNT_SUB_GRAD = '別の場面の例・実際はもっとゆっくり'


def draw_heart(im, cx, cy, size, col, a):
    """ハート（2つの円＋三角）。拍ごとに明るくする。"""
    if a <= 0.004:
        return
    ss = 4
    n = int(size*ss)
    lay = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(lay)
    r = n*0.27
    d.ellipse((n*0.5 - 2*r, n*0.12, n*0.5, n*0.12 + 2*r), fill=255)
    d.ellipse((n*0.5, n*0.12, n*0.5 + 2*r, n*0.12 + 2*r), fill=255)
    d.polygon([(n*0.5 - 2*r + n*0.02, n*0.12 + r*1.25), (n*0.5 + 2*r - n*0.02, n*0.12 + r*1.25), (n*0.5, n*0.94)], fill=255)
    lay = lay.resize((int(size), int(size)), Image.LANCZOS)
    col_im = Image.new('RGBA', lay.size, col + (0,))
    col_im.putalpha(lay.point(lambda q: int(q*a)))
    im.alpha_composite(col_im, (int(cx - size/2), int(cy - size/2)))


def draw_counter(im, t, cur, a):
    """心拍数カウンター「♥ 150 /分」を波形の下のまん中に。名前の出ているあいだ（形がそのパターンそのもの）だけ。"""
    if cur is None:
        return
    a_i, b_i = WINDOWS[cur]
    a = a * ramp(t, a_i, 0.25) * (1 - ramp(t, b_i - 0.25, 0.25))
    h = hr_at(t)
    if h is None or a <= 0.004:
        return
    bpm, k, since, prev = h
    flash = math.exp(-since/0.18)                   # 拍の瞬間に明るく、すぐ戻る
    num = f'{bpm:.0f}'
    im_n, asc_n = text_img(num, 64, 800, WHITE)
    w3 = text_img('888', 64, 800, WHITE)[0].size[0] - 8      # 3けたぶんの幅（数字が変わっても位置が動かない）
    im_u, _ = text_img('/分', 32, 700, GREY)
    hs, gap = 44, 14
    total = hs + gap + w3 + 10 + (im_u.size[0] - 8)
    x0 = 540 - total/2
    cy = CNT_TOP + CNT_H/2
    xr = x0 + hs + gap + w3                         # 数字は右ぞろえ（右端と「/分」は動かない）
    wn = im_n.size[0] - 8                           # いまの数字の幅。ハートは数字のすぐ左に置く（2けたでも離れない）
    draw_heart(im, xr - wn - gap - hs/2, cy + 7, hs*(1 + 0.12*flash), C_HEART, a*(0.55 + 0.45*flash))
    put(im, num, 64, 800, WHITE, right=xr, cy=cy + 4, a=a)
    xu = xr + 10 + im_u.size[0] - 8
    put(im, '/分', 32, 700, GREY, x=xr + 10, cy=cy + 14, a=a)
    note = hr_note(t, k, bpm, prev)
    if note:
        put(im, note, 26, 700, TAGS['rate'][1], x=xu + 22, cy=cy + 12, a=a)
    # カウンターの下に小さく（まん中ぞろえ）：④⑤は拍ごとの値であること、⑧の洞調律は別の場面の例であること
    sub = None
    if PATTERNS[cur]['no'] in ('④', '⑤'):
        sub = CNT_SUB_IRREG
    elif PATTERNS[cur]['no'] == '⑧' and note and '少しずつ' in note:
        sub = CNT_SUB_GRAD
    if sub:
        put(im, sub, 24, 600, GREY, cx=540, cy=cy + CNT_H/2 + 30, a=a, max_w=820)


def frame(t):
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

    # 中部：紹介中の名前とひとこと
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        # 前のパターンのコピーは、形が変わるあいだに枠へ入り終わっている（名前は形が変わり終わって 0.15秒後）
        t0 = a_i + 0.1
        al = ramp(t, t0, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        # クイズ：はじめは「これは？」、波形が見えてから約0.7秒たって名前に変わる（声は特徴 → 名前の順）
        # 「これは？」→ 名前は 0.1秒で重ねて切りかえる（両方うすくなる時間を作らない）
        a_q = ramp(t, t0, 0.25) * (1 - ramp(t, a_i + QUIZ_T - 0.1, 0.1))
        a_n = ramp(t, a_i + QUIZ_T - 0.1, 0.1) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {QUIZ}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=a_q, max_w=820)
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=a_n, max_w=820)
        draw_one(im, pat, al)

    # 冒頭0〜1秒：大きめの問いかけ（見出しが出る前に消す）
    a_ask = max(1 - ramp(t, ASK_END, 0.3), a_loop)
    put(im, ASK, 80, 900, YEL, cx=540, cy=ASK_Y, a=a_ask, max_w=820)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        put(im, TITLE_SUB, 36, 500, PURPLE, cx=540, cy=TITLE_Y[0], a=a_t)
        put(im, TITLE, 150, 900, WHITE, cx=540, cy=TITLE_Y[1], a=a_t, max_w=880)
        put(im, TITLE_2, 52, 800, WHITE, cx=540, cy=TITLE_Y[2], a=a_t, max_w=880)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, END_1, 42, 800, WHITE, cx=540, cy=Y_NAME, a=a_end, max_w=820)
        put(im, END_2, 36, 700, GREEN, cx=540, cy=Y_ONE,
            a=ramp(t, T_END + FLY + 1.5, 0.6)*keep)
        put(im, END_3, 40, 800, YEL, cx=540, cy=CNT_TOP + CNT_H/2 + 4,
            a=ramp(t, T_END + FLY + 2.0, 0.6)*keep, max_w=820)

    # 中部の波形：最初から最後まで消さない（2026-10-13）。名前が消えると、そのパターンのコピーだけが縮んで枠へ飛び、
    # 帯は流れたまま、画面の拍がその場で次の形へ変わる
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    im.alpha_composite(featured(t, base_col, 1.0, cur), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        # コピーはうすい状態から（帯と重なる最初の一瞬に、二重に見えないように）
        mini(im, flying, t, uu, a=cl(uu / 0.3))
    draw_counter(im, t, cur, keep)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=NOTE_Y[0], a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_Y[1], a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


# 冒頭のタイトル（小さい字・大きい字・その下）の y。ノート2行の y（字の下が 1600 より上）
TITLE_Y = (490, 618, 762)
ASK_Y = 372                          # 冒頭の問いかけ（見出しの位置。見出しは 2.5秒から）
NOTE_Y = (1557, 1584)


# --- 一覧型のサムネイル（第21弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {i: (0.0, []) for i in range(len(PATTERNS))}
THUMB_VIEW[1] = (0.05, [(0.40 + 0.04, 0.40 + 0.38)])       # ② P波がT波に重なる（T波の下り坂のこぶ）
THUMB_VIEW[7] = (OO_STOP + 0.75 - 4.0, [(OO_PAC - 0.30, OO_PAC + 0.40)])   # ⑧ PACから突然始まり、右の端で突然止まる
THUMB_MAX_MARKS = {1: 1, 7: 1}
THUMB_NAME = {1: '洞頻脈（PがTに重なる）', 6: 'PSVT', 7: '始まり方', 8: '房室回帰性頻拍'}   # サムネイルだけ短い名前
THUMB_DESC = ['Pがそろう', '', 'いつもと違うP', '3種類以上', 'バラバラ', '150で規則的',
              'Pが見えない', '突然か、少しずつか', 'QRSの後にP', '直前に逆向きP']


def dashed_ellipse(d, box, col, dash=6, gap=5, width=2):
    """点線の楕円。"""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1)/2, (y0 + y1)/2, (x1 - x0)/2, (y1 - y0)/2
    th = np.linspace(0, 2*np.pi, 721)
    pts = np.stack([cx + rx*np.cos(th), cy + ry*np.sin(th)], 1)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    idx = np.where((seg % (dash + gap)) < dash)[0]
    for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
        if len(r) >= 2:
            d.line([tuple(q) for q in pts[r]], fill=col + (255,), width=width)


def thumb_row_wave(i, x0, x1, base_y, mv, span=4.0):
    """パターン i を1本の色で描き、特徴のところを点線の丸で囲む（サムネイル用）。"""
    pat = PATTERNS[i]
    pxs = (x1 - x0) / span
    t0, marks = THUMB_VIEW[i]
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = t0 + (xs - x0) / pxs
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    v = v * np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(3.2*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.7*mv) - pad
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], pat['col'], 2.8, 1.0, blur=(4, 10))
    d = ImageDraw.Draw(lay)
    L = pat['L']
    n_max, n = THUMB_MAX_MARKS.get(i, 2), 0
    for k in range(-2, 6):
        for a, b in marks:
            lo, hi = a + k*L, b + k*L
            if lo < rel[0] + 0.05 or hi > rel[-1] - 0.05 or n >= n_max:
                continue
            n += 1
            sel = (rel >= lo) & (rel <= hi)
            bx0, bx1 = x0 + (lo - t0)*pxs - 4, x0 + (hi - t0)*pxs + 4
            by0 = min(ys[sel].min() - 9, base_y - 0.45*mv)
            by1 = max(ys[sel].max() + 9, base_y + 0.35*mv)
            dashed_ellipse(d, (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy), pat['col'])
    return lay, (ox, oy)


def thumbnail_list():
    """サムネイル（透かしなし）。第21弾の一覧型と同じ作り：
    タイトル → 10パターンを2列×5段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, '頻脈（幅の狭いQRS）', 96, 900, WHITE, cx=568, cy=436, max_w=880)   # 「頻脈」の左の余白と「）」の右の余白をそろえる
    put(im, f'{N_PAT}個、全部わかる？', 60, 900, (255, 196, 64), cx=540, cy=546)
    COLS = [(135, 515), (565, 945)]             # 列のあいだは50px あける（線は引かない）
    NR = (N_PAT + 1) // 2                       # 1列の段の数
    Y0, RH = 628, 852 // NR
    for i, pat in enumerate(PATTERNS):
        c, r = divmod(i, NR)
        x0, x1 = COLS[c]
        y = Y0 + r*RH
        name = f"{pat['no']} {THUMB_NAME.get(i, pat['name'])}"
        im_n, _ = text_img(name, 26, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 26, 800, pat['col'], x=x0, cy=y + 24, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if THUMB_DESC[i]:
            im_h, _ = text_img(THUMB_DESC[i], 18, 500, (176, 186, 186))
            assert nx + im_h.size[0] - 8 <= x1 + 4, f'{pat["no"]} のひとことが入らない'
            put(im, THUMB_DESC[i], 18, 500, (176, 186, 186), x=nx, cy=y + 26)
        lay, pos = thumb_row_wave(i, x0, x1, y + 24 + (RH - 24)*0.66, 44.0)
        im.alpha_composite(lay, pos)
        if r < NR - 1:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)], fill=(38, 54, 48, 255), width=1)
    by = Y0 + NR*RH + 24
    d.rounded_rectangle([(230, by), (850, by + 96)], radius=18, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('まず覚えたい', 40, WHITE), (str(N_PAT), 72, (255, 196, 64)), ('パターン', 40, WHITE)]
    ims = [text_img(t, sz, 900, col) for t, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 70                          # 文字の下端（ベースライン）をそろえる
    for (t, sz, col), (a, asc) in zip(parts, ims):
        put(im, t, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _onset(v, tt, thr):
    return tt[np.abs(v) > thr].min()


def pr_ms(kind):
    """PR間隔（P波の始まり → QRSの始まり、ms）。"""
    q, p, prc = KINDS[kind]
    tt = np.arange(-0.6, 0.1, 0.0005)
    pv = p(tt + prc)
    p_on = tt[np.abs(pv) > 0.05*np.abs(pv).max()].min()
    q_on = _onset(q(tt) * (tt > -0.2), tt, 0.03)
    return (q_on - p_on) * 1000


def qrs_ms(f):
    """QRS幅（|v| > 0.03mV の範囲、R頂点の前後 0.12秒以内、ms）。"""
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt)
    m =(np.abs(v) > 0.03) & (tt < 0.075) & (tt > -0.15)
    return (tt[m].max() - tt[m].min()) * 1000


def rate(rr):
    return 60.0 / rr


def check():
    print(f'映像 {DUR:.2f}秒')
    print('パターンごとの紹介の時間（名前が出る → 名前が消えてコピーが枠へ飛ぶ）。拍の番号のずれ OFF')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']} {pat['name']:<16} 周期{pat['L']:.2f}s  画面 {a:5.2f}–{b:5.2f}s（{b-a:4.2f}s）  OFF {OFF[i]}"
              f"  名前が出るとき中央はパターンの中の {_INFO[i]['u_a'] % pat['L']:.2f}s")
    print(f'最後のパターンの終わり {T_END:.2f}s → 一覧 {T_END+FLY:.2f}〜{DUR:.2f}s')
    print(f"⑧ PACがカウンターを通る {PAC_CROSS:.2f}s（名前が出てから {PAC_CROSS - WINDOWS[I8][0]:.2f}秒）、"
          f"最後の「少しずつ」の拍 {_INFO[I8]['t_last']:.2f}s")
    print('つなぎ目：名前が消えてコピーが飛ぶ → 形が変わる（その場で。①＝①洞頻脈の形を通る） → 次の名前')
    for i in range(N_PAT):
        nxt = f"次の名前 {WINDOWS[i+1][0]:5.2f}s" if i + 1 < N_PAT else f"最後の画面 {T_END + FLY:5.2f}s"
        mine = [e for e in SHAPE_EV if WINDOWS[i][1] <= e[0] < (WINDOWS[i+1][0] if i + 1 < N_PAT else 1e9)]
        txt = '・'.join(f"{PATTERNS[e[2]]['no']}→{PATTERNS[e[3]]['no']} {e[0]:5.2f}〜{e[1]:5.2f}" for e in mine)
        to = PATTERNS[i+1]['no'] if i + 1 < N_PAT else '最後'
        print(f"  {PATTERNS[i]['no']}→{to}：コピー {WINDOWS[i][1]:5.2f}s・{txt}・{nxt}")
    # 数値の形（eval_vec）と元の関数の形がそろっているか
    tt = np.arange(-0.6, 0.75, 0.0005)
    dmax = max(np.abs(beat_wave(tt, k) - beat_wave_fn(tt, k)).max() for k in KINDS)
    print(f'拍の形：数値の形と元の関数の差 最大 {dmax:.1e} mV')
    assert dmax < 1e-9
    # 拍が中央を通る間隔（動画の時刻）。跳び・抜け・重なりがないか
    th0, th1 = math.ceil(theta(T_GO)), math.floor(theta(DUR))
    bt = [float(np.interp(kk, _TH, _TG)) for kk in range(th0, th1 + 1)]
    gaps = np.diff(bt)
    print(f'拍が中央を通る間隔：{gaps.min():.3f}〜{gaps.max():.3f}秒（{len(bt)}拍）')
    ph = (theta(DUR) - theta(0.0)) % 1.0
    print(f'ループ：動画の終わりと冒頭の拍の位相のずれ {min(ph, 1 - ph)*0.52*1000:.1f}ms')
    print('--- 各パターンの数値（モデルから） ---')
    print(f"① 洞頻脈：{rate(0.52):.0f}/分、PR {pr_ms('S'):.0f}ms、QRS {qrs_ms(qrs_115):.0f}ms")
    rp = 0.40 - KINDS['H'][2]
    print(f"② 洞頻脈（P波がT波に重なる）：{rate(0.40):.0f}/分、PR {pr_ms('H'):.0f}ms、P波の頂点は前のRから {rp:.2f}秒"
          f"（T波の頂点 0.195秒。P波の頂点まで {rp - 0.195:.3f}秒）")
    print(f"③ 心房頻拍：{rate(0.46):.0f}/分、P'（とがった二相性）PR {pr_ms('A'):.0f}ms、基線は平ら")
    rrs = MAT_RR
    print(f"④ 多源性心房頻拍：平均 {rate(np.mean(rrs)):.0f}/分（{rate(max(rrs)):.0f}〜{rate(min(rrs)):.0f}/分）、P波4種類、"
          f"PR {', '.join(f'{pr_ms(k):.0f}' for k in ('M1', 'M2', 'M3', 'M4'))}ms")
    for k in range(len(MAT_RR)):
        nxt = MAT_K[(k + 1) % len(MAT_K)]
        gap = MAT_RR[k] - KINDS[nxt][2]
        assert gap >= 0.30, f'MAT {k}: P波がT波に重なる（R→次のP {gap:.2f}秒）'
    print(f"⑤ 心房細動：平均 {rate(np.mean(AF_RR)):.0f}/分（{rate(max(AF_RR)):.0f}〜{rate(min(AF_RR)):.0f}/分）、f波 4.5〜8Hz、"
          f"幅 ±{np.abs(art_af(np.arange(0, sum(AF_RR), 0.002), sum(AF_RR))).max():.2f}mV")
    print(f"⑥ 心房粗動：F波 {rate(FL_CYC):.0f}/分（のこぎり・下向き、{0.24*10:.1f}mm）、2:1で心室 {rate(0.40):.0f}/分")
    print(f"⑦ PSVT：{rate(SVT_RR):.0f}/分、P波なし（QRSの終わりに偽S波）、QRS {qrs_ms(qrs_avnrt):.0f}ms")
    print(f"⑧ 始まり方：洞調律 90/分 → PAC（連結 {OO_PAC_C:.2f}秒、PR {pr_ms('B'):.0f}ms）→ PSVT {rate(OO_SVT_RR):.0f}/分 {OO_SVT_N}拍 → "
          f"突然止まって {OO_PAUSE:.2f}秒後に洞調律 → 少しずつ {' → '.join(f'{rate(r):.0f}' for r in OO_SINUS_RR)}/分")
    rp, gap = avrt_rp_ms()
    print(f"⑨ 房室回帰性頻拍：{rate(0.30):.0f}/分、RP（QRSの始まり → Pの始まり）{rp:.0f}ms（目標 100〜140）、"
          f"QRSの終わり → Pの始まり {gap:.0f}ms（目標 20〜50）、R頂点 → P頂点 {AVRT_RP*1000:.0f}ms")
    assert 100 <= rp <= 140 and 20 <= gap <= 50, '⑨ の RP が目標の外'
    print(f"⑩ 接合部頻拍：{rate(0.52):.0f}/分、逆向きのP、PR {pr_ms('J'):.0f}ms（<120）")
    print('--- 心拍数カウンター（拍ごとの表示。名前の出ているあいだにカウンターを通った拍） ---')
    cr = crossings()
    for i, pat in enumerate(PATTERNS):
        vals = [f'{b:.0f}' for t, k, b, j in cr if j == i]
        print(f"  {pat['no']} " + ' '.join(vals))
    print(f'  カウンターの位置 x={COUNT_X}（画面の中央から {DT_REF:.2f}秒先）。ピッという音も同じ瞬間（全部で {len(cr)}拍）')
    print('--- 字の幅 ---')
    for pat in PATTERNS:
        sz, w1, w2 = one_layout(pat)
        nm = fit_size(f"{pat['no']} {pat['name']}", 54, 900, 820)
        cell = fit_size(f"{pat['no']} {pat['name']}", 22, 700, CELL_W - 30)
        hint = fit_size(f"ヒント：{pat['hint']}", 24, 500, CELL_W - 80)
        warn = []
        if sz < 32: warn.append(f'ひとこと {sz}px に縮む')
        if nm < 54: warn.append(f'名前 {nm}px')
        if cell < 22: warn.append(f'枠の名前 {cell}px')
        if hint < 24: warn.append(f'ヒント {hint}px')
        if min(cell, hint) < 18: warn.append('★18px未満')
        print(f"  {pat['no']} ひとこと＋色 {w1 + 14 + w2}px（上限 {ONE_W}）{'  ' + '・'.join(warn) if warn else ''}")


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
    """中部の波形の R がカウンターの位置（COUNT_X）を通るときに「ピッ」。この回は全部幅の狭いQRSなので同じ高さ。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for ts, k, bpm, i in crossings():          # カウンターが変わる瞬間（帯の右のほう）
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 960.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel24_tachy.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel24_tachy_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel24_tachy_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel24_list.png')
        thumbnail_list().save(p); print(p); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
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
