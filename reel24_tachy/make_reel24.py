"""第24弾 頻脈（幅の狭いQRS） まず覚えたい12パターン（第21弾と同じ作り）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。洞から・心房から：洞頻脈 → PACの連発 → 心房頻拍 → 多源性心房頻拍 → 速い心房細動 → 心房粗動2:1）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと（うしろに、看護師がまずすることを色で）
- 下部：⑦〜⑫ のミニ波形（2列×3段。房室結節・副伝導路のあたり：PSVT → 始まりと終わり → 房室回帰性頻拍 → WPW → 接合部頻拍、
  最後に見分けにくい例：P波が隠れた洞頻脈）

波形は、パターンの周期でくり返す決まった形（乱数の種を固定）。区間の端は0.2秒でなめらかに切りかえる。
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
qrs_180 = qrs_rate(0.195, 0.22)             # 180〜200/分
qrs_flut = qrs_rate(0.215, 0.08)            # 心房粗動：T波を小さめにして、粗動波が見えるように
qrs_200 = qrs_rate(0.205, 0.17)             # 房室回帰性頻拍：T波の始まりに逆行性Pの切れこみ


def qrs_avnrt(t):                 # PSVT（房室結節リエントリー）：逆行性P波がQRSの終わりに重なる（II誘導の偽S波）
    return qrs_180(t) - 0.07*_g(t, 0.046, 0.010)


AVRT_RP = 0.115                   # 房室回帰性頻拍：R → 逆行性P の間隔（LITFL：70ms より長い）


def qrs_avrt(t):                  # 房室回帰性頻拍（順方向性）：QRSのあと、STの上に逆向きのP波
    return qrs_200(t) + p_retro(t - AVRT_RP)


# 拍の種類：(QRS＋Tの形, P波の形, P頂点 → R頂点)
KINDS = {
    'N': (qrs_normal, p_sinus, 0.16),       # 前後の洞調律（75/分）
    'S': (qrs_115, p_sinus, 0.15),          # 洞頻脈（⑧の少しずつ変わる洞調律も）
    'H': (qrs_150, p_sinus, 0.12),          # 速い洞頻脈（P波がT波に重なる）
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
    """⑧ 始まり方の対比：洞調律 90/分 → 少しずつ 105 → 120 → 135 → 120 → 105 → 90/分（洞頻脈）
    → PAC（連結 0.36秒・PRが長い）→ PSVT 170/分 7拍 → 突然止まって 0.80秒あく → 洞調律（次の周期の頭）。"""
    t = 0.45
    ev = [(t, 'S')]                          # 周期の頭（止まったあとの最初の洞調律）
    for rr in OO_SINUS_RR:
        t += rr
        ev.append((t, 'S'))
    t += OO_PAC_C
    pac = t
    ev.append((t, 'B'))
    for _ in range(OO_SVT_N):
        t += OO_SVT_RR
        ev.append((t, 'R'))
    stop = t
    L = stop + OO_PAUSE - 0.45
    return ev, L, pac, stop


OO_SINUS_RR = [0.667, 0.571, 0.50, 0.444, 0.50, 0.571, 0.667]   # 90, 105, 120, 135, 120, 105, 90/分
OO_PAC_C = 0.36                             # PACの連結（直前のRから）
OO_SVT_RR = 0.353                           # ⑧ PSVT 170/分
OO_SVT_N = 7
OO_PAUSE = 0.80                             # 止まってから洞調律まで
OO_EV, OO_L, OO_PAC, OO_STOP = _onset_offset()
OO_SIN_END = OO_PAC - OO_PAC_C              # 少しずつ変わる洞調律の最後の拍

# 10パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、連続した波形 art、色を付ける範囲 hl
# tag：ひとことのうしろの色の文字（TAGS）
PATTERNS = [
    dict(no='①', name='洞頻脈', col=C_SIN, hint='Pがそろう',
         one='どの拍にも、ふつうのP波', tag='patient',
         ev=[(k*0.52, 'S') for k in range(8)], L=4.16, hl=ALL),
    dict(no='②', name='洞頻脈（P波がT波に重なる）', col=C_SIN, hint='TにPが重なる',
         one='P波がT波に重なり、PSVTに見える', tag='ecg12',
         ev=[(k*0.40, 'H') for k in range(12)], L=4.8, hl=ALL),
    dict(no='③', name='心房頻拍', col=C_ATR, hint='形のちがうP',
         one='形のちがうP波が、規則正しく', tag='ecg12',
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
    dict(no='⑧', name='始まり方：洞頻脈とPSVT', col=C_AVN, hint='突然か、少しずつか',
         one='少しずつなら洞頻脈、突然ならPSVT', tag='rate',
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

# 区間の長さ（秒）。仮の値（録音前）：台本の各文の長さの見込み（約8モーラ/秒）＋0.75秒以上で、拍の並びがくずれない位置で切る。
# - 規則正しいリズム（①②③⑥⑦⑨⑩）は、拍の間隔の整数倍。次のパターンの最初の拍までが、どちらかのパターンの間隔になる
#   （⑥⑦は1周期より1拍ぶん長い。⑨⑩は最初の拍を少しうしろにずらして、つなぎ目の間隔をそろえた）
# - ④ 5.08：1周期＋1拍　- ⑤ 3.80：8つめの拍のあと（次の⑥の最初の拍まで 0.35秒。心房細動の短いRRくらい）
# - ⑧ 8.88：1周期＋止まったあとの洞調律2拍（少しずつ変わる洞調律 → PAC → PSVT → 突然止まる → 洞調律 75 → 90/分）。
#   止まったところと、戻った洞調律がカウンターの位置を通るまでを中部の帯で見せる
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {'①': 4.16, '②': 4.8, '③': 4.60, '④': 5.08, '⑤': 3.80, '⑥': 4.43,
         '⑦': 4.29, '⑧': 8.88, '⑨': 5.1, '⑩': 5.05}
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    assert _p['D'] >= 3.44 - 1e-9, _p['no']


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
    """周期の中の色を付ける範囲（rel は区間の始まりからの時刻）。"""
    L = pat['L']
    r = np.mod(rel, L)
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-L, 0.0, L):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


# --- 中部の帯：全パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンを置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 4.9                     # 冒頭の1文（仮 4.9秒）が入り、見出しと枠が出そろう長さ
END_HOLD = 5.7                    # 全部そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [3, 4, 5, 6, 8]            # ④多源性心房頻拍 → ⑤心房細動 → ⑥心房粗動 → ⑦PSVT → ⑨房室回帰性頻拍
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12
HANDOFF_EARLY = 0.35


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < pat['D'] - 1e-9:
                beats.append((t + r, kind, i))
        t += pat['D']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -12:                     # 前：洞調律
        beats.append((k*RR, 'N', None)); k -= 1
    # うしろ：洞調律（間隔は変えない）。尺は「最後の2文が入る長さ」以上で、
    # うしろの洞調律の位相が冒頭とそろういちばん短い長さにする。こうするとループがつながる
    need = T_TITLE + end - HANDOFF_EARLY + 0.8 + END_HOLD      # 0.8 = FLY
    k = math.ceil((need - FREEZE - end) / RR - 1e-9)
    dur_target = FREEZE + end + k*RR
    tt = end
    beats.append((tt, 'N', None))
    for k in range(1, 60):
        tt += RR
        beats.append((tt, 'N', None))
    beats.sort(key=lambda b: b[0])
    return beats, segs, end, dur_target


STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.6mV）
_TOP_END = 636 + 110               # 上の枠（①②③／④⑤⑥の3段）の下端
_BOT_TOP = 1298                    # 下の枠（⑦⑧／⑨⑩の2段）の上端。下端は 1528（下の注記と 19px あける）
# 見た目の上端（名前の字の上）〜下端（S波の底、約0.2mV）で余白をそろえる
# その下に心拍数カウンター（波形の下端から CNT_GAP あけて、数字の高さ CNT_H）
CNT_GAP, CNT_H = 34, 46
_MID_H = 22 + 54 + 16 + 30 + 140 + 30 + CNT_GAP + CNT_H
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + 16 + 30 + 140
CNT_TOP = F_BASE + 30 + CNT_GAP          # カウンターの数字の上端
F_Y0, F_Y1 = int(F_BASE - 200), int(_BOT_TOP - 2)
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# t=T_TITLE で、パターン①の区間の始まりが画面の右端に来る（止まっていた時間を引く）
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
    # 区間の終わりが右端の少し先（0.35秒）に来た瞬間。次のパターンの最初の拍・細動波が
    # 右端に入る前に縮み始めるので、見えているのはパターン i だけになる
    _b = t_of(SEGS[_i][1] - HALF - HANDOFF_EARLY)
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60
DUR = round(_DUR_LOOP * FPS_LOOP) / FPS_LOOP


# --- 心拍数カウンター（この回だけの見せ方） -----------------------------------------
# 帯の右のほう（x = COUNT_X）を R が通った瞬間に、その拍の心拍数（60 ÷ 直前の拍からの R-R）に変わる。
# モニターと同じく、新しい拍が右から入ってきたところで数える。ピッという音も同じ瞬間に鳴らす。
# R-R はそのパターンの拍の並び（周期でくり返したもの）から取る。区間のつなぎ目の間隔は使わない。
COUNT_X = 940
DT_REF = (COUNT_X - XC) / F_PXS              # 画面の中央から数える位置までの、実際の時間（秒）


def _strip_hr():
    """中部の帯の拍ごとに (R時刻, 心拍数/分, パターン番号)。"""
    out = []
    for r, k, i in STRIP:
        if KINDS[k][0] is None:
            continue
        if i is None:
            rr = RR
        else:
            pat = PATTERNS[i]
            rel = r - SEGS[i][0]
            prev = [b for b, kk in periodic_beats(pat, rel - 3, rel + 0.1)
                    if KINDS[kk][0] is not None and b < rel - 1e-6]
            rr = rel - max(prev)
        out.append((r, 60.0 / rr, i))
    return out


STRIP_HR = _strip_hr()
_HR_T = np.array([b[0] for b in STRIP_HR])


def hr_at(t):
    """その時刻のカウンター：(心拍数, パターン番号, 数えてからの秒)。数える前なら None。"""
    ref = tau_c(t) + DT_REF
    k = int(np.searchsorted(_HR_T, ref, side='right')) - 1
    if k < 0:
        return None
    r, bpm, i = STRIP_HR[k]
    return bpm, i, (ref - r) * SLOW


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
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = 31.5
    for i in range(int(W/pm) + 2):
        x = round(i*pm)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,),
               width=2 if i % 5 == 0 else 1)
    for k in range(int(H/pm) + 2):
        y = round(k*pm)
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


ART_EDGE = 0.2                    # 区間の端で、細動波・粗動波をなめらかに切りかえる長さ（秒）


def strip_art(tau, v):
    """中部の帯：区間ごとに、そのパターンの細動波・粗動波を足す（区間の端 ART_EDGE 秒でなめらかに）。"""
    out = v.copy()
    for i, (s0, s1) in enumerate(SEGS):
        pat = PATTERNS[i]
        if not pat.get('art'):
            continue
        m = (tau > s0 - 1e-9) & (tau < s1)
        if not m.any():
            continue
        tt = tau[m]
        e = np.minimum(np.clip((tt - s0) / ART_EDGE, 0, 1), np.clip((s1 - tt) / ART_EDGE, 0, 1))
        e = e*e*(3 - 2*e)
        out[m] = v[m] + e*pat['art'](tt - s0, pat['L'])
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
    """中部の帯：(波形, 色の番号)"""
    tau = tau_center + (FX - XC) / F_PXS
    return strip_art(tau, wave_from(STRIP, tau)), strip_colors(tau)


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
    """中部の帯。色を付けるのは、いま紹介中のパターン cur の拍だけ（前のパターンの残りはふつうの緑）。"""
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a)
    v, cid = strip_arrays(tau_c(t))
    cid = np.where(cid == cur, cid, -1) if cur is not None else np.full_like(cid, -1)
    return draw_wave(v, cid, base_col, a)


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 76, 50     # ミニ波形の帯（枠の中）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


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
END_1 = f'速い脈を見たら、この{len(PATTERNS)}パターン'
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
    """心拍数カウンター「♥ 150 /分」を波形の下のまん中に。紹介中のパターンの拍だけを数える。"""
    h = hr_at(t)
    if h is None or cur is None or h[1] != cur or a <= 0.004:
        return
    bpm, _, since = h
    flash = math.exp(-since/0.18)                   # 拍の瞬間に明るく、すぐ戻る
    num = f'{bpm:.0f}'
    im_n, asc_n = text_img(num, 64, 800, WHITE)
    w3 = text_img('888', 64, 800, WHITE)[0].size[0] - 8      # 3けたぶんの幅（数字が変わっても位置が動かない）
    im_u, _ = text_img('/分', 32, 700, GREY)
    hs, gap = 44, 14
    total = hs + gap + w3 + 10 + (im_u.size[0] - 8)
    x0 = 540 - total/2
    cy = CNT_TOP + CNT_H/2
    draw_heart(im, x0 + hs/2, cy + 2, hs*(1 + 0.12*flash), C_HEART, a*(0.55 + 0.45*flash))
    xr = x0 + hs + gap + w3                         # 数字は右ぞろえ
    put(im, num, 64, 800, WHITE, right=xr, cy=cy + 4, a=a)
    put(im, '/分', 32, 700, GREY, x=xr + 10, cy=cy + 14, a=a)


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
        al = ramp(t, a_i + 0.1, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        # クイズ：はじめは「これは？」、波形が見えてから約0.7秒たって名前に変わる（声は特徴 → 名前の順）
        a_q = ramp(t, a_i + 0.1, 0.25) * (1 - ramp(t, a_i + QUIZ_T - 0.15, 0.15))
        a_n = ramp(t, a_i + QUIZ_T, 0.25) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {QUIZ}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=a_q, max_w=820)
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=a_n, max_w=820)
        draw_one(im, pat, al)

    # 冒頭0〜1秒：大きめの問いかけ（見出しが出る前に消す）
    a_ask = max(1 - ramp(t, ASK_END, 0.3), a_loop)
    put(im, ASK, 64, 900, YEL, cx=540, cy=ASK_Y, a=a_ask, max_w=820)

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

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a_strip = min(a_strip, ramp(t, b_i + FLY - 0.1, 0.45))
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    if a_strip > 0.01:
        im.alpha_composite(featured(t, base_col, a_strip, cur), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)
    draw_counter(im, t, cur, a_strip*keep)

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
THUMB_VIEW[7] = (OO_PAC - 1.25, [(OO_PAC - 0.30, OO_PAC + 0.40)])   # ⑧ PACから突然始まる（右に突然止まるところ）
THUMB_MAX_MARKS = {1: 1, 7: 1}
THUMB_NAME = {1: '洞頻脈（PがTに重なる）', 6: 'PSVT（AVNRT）', 7: '始まり方', 8: '房室回帰性頻拍'}   # サムネイルだけ短い名前
THUMB_DESC = ['Pがそろう', '', '形のちがうP', '3種類以上', 'バラバラ', 'のこぎり状',
              'Pが見えない', '突然始まり突然止まる', 'QRSの後にP', '直前に逆向きP']


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
    タイトル → 12パターンを2列×6段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
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
    print(f'映像 {DUR:.1f}秒（目安 60〜70秒）')
    print('パターンごとの紹介の時間')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']} {pat['name']:<16} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s  画面 {a:5.1f}–{b:5.1f}s（{b-a:4.1f}s）")
    print(f'最後のパターンの終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s')
    # 区間のつなぎ目：前のパターンの最後の拍 → 次のパターン（またはうしろの洞調律）の最初の拍
    for i, (s0, s1) in enumerate(SEGS):
        inside = [b for b in STRIP if s0 <= b[0] < s1]
        last = max(inside, key=lambda b: b[0])
        nxt = min((b for b in STRIP if b[0] >= s1 - 1e-9), key=lambda b: b[0])
        own = sorted(b[0] for b in inside)
        rr = np.diff(own)
        print(f"  つなぎ目 {PATTERNS[i]['no']}→ : 最後の拍 {last[1]} {last[0]-s0:.2f} → {nxt[1]} 間隔 {nxt[0]-last[0]:.2f}s"
              f"（区間の中の RR {rr.min():.2f}〜{rr.max():.2f}s）")
    print('--- 各パターンの数値（モデルから） ---')
    print(f"① 洞頻脈：{rate(0.52):.0f}/分、PR {pr_ms('S'):.0f}ms、QRS {qrs_ms(qrs_115):.0f}ms")
    rp = 0.40 - KINDS['H'][2]
    print(f"② 洞頻脈（P波がT波に重なる）：{rate(0.40):.0f}/分、P波の頂点は前のRから {rp:.2f}秒（T波の頂点 0.215秒、T波の終わり 約0.31秒）")
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
    print(f"⑧ 始まり方：洞調律 {' → '.join(f'{rate(r):.0f}' for r in OO_SINUS_RR)}/分（少しずつ）→ PAC（連結 {OO_PAC_C:.2f}秒、"
          f"PR {pr_ms('B'):.0f}ms）→ PSVT {rate(OO_SVT_RR):.0f}/分 {OO_SVT_N}拍 → 突然止まって {OO_PAUSE:.2f}秒後に洞調律")
    print(f"⑨ 房室回帰性頻拍：{rate(0.30):.0f}/分、R → 逆行性P {AVRT_RP*1000:.0f}ms（LITFL：70ms より長い）")
    print(f"⑩ 接合部頻拍：{rate(0.52):.0f}/分、逆向きのP、PR {pr_ms('J'):.0f}ms（<120）")
    print('--- 心拍数カウンター（拍ごとの表示。パターンの区間の中） ---')
    for i, pat in enumerate(PATTERNS):
        vals = [f'{b:.0f}' for r, b, j in STRIP_HR if j == i]
        print(f"  {pat['no']} " + ' '.join(vals))
    print(f'  カウンターの位置 x={COUNT_X}（画面の中央から {DT_REF:.2f}秒先）。ピッという音も同じ瞬間')
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:8]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])
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
    for r, k, i in STRIP:
        ts = t_of(r - DT_REF)                # カウンターが変わる瞬間（帯の右のほう）
        if KINDS[k][0] is None:
            continue
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
