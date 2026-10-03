"""第19弾 ペースメーカー心電図 まず覚えたい12パターン（第17・18弾と同じ作り）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。左がペーシングの基本、右が「打つ・休む」の見え方）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと
- 下部：⑦〜⑫ のミニ波形（2列×3段。左が融合・不全、右がセンシングの異常・ペースメーカー頻拍）

ペーシングスパイク（約2ms）は、波形の点の並びとは別に、縦の線として描く（縮めても消えないように）。
II誘導・右室心尖部のリードを想定（ペーシングのQRSは幅が広く下向き、Tは上向き）。下限レートは60/分。

使い方:
    python3 make_reel19.py              # 書き出し・60fps
    python3 make_reel19.py --still 20   # 1コマだけ
    python3 make_reel19.py --check      # 検算・タイミング表
    python3 make_reel19.py --thumb      # サムネイル（透かしなし）
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

C_PACE = (110, 200, 255)         # ペーシングの基本
C_INH = (190, 160, 255)          # 休む・見えにくい
C_FUS = (255, 212, 90)           # 融合・偽融合
C_BAD = (255, 92, 112)           # 不全（すぐ報告）
C_PMT = (255, 152, 72)           # ペースメーカー頻拍

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

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


def p_ect(t):                     # P'：小さく、とがって、少し二相性
    return 0.13*_g(t, 0.0, 0.015) - 0.04*_g(t, 0.032, 0.013)


def p_retro(t):                   # 逆行性P：逆向き
    return -0.12*_g(t, 0.0, 0.020)


def qrs_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_aberrant(t):              # 変行伝導（右脚ブロック型）：幅が広く、終わりがなまる
    return (0.85*_g(t, 0.0, 0.012) - 0.32*_ga(t, 0.055, 0.022, 0.030)
            + 0.12*_ga(t, 0.27, 0.060, 0.045))


def qrs_pvc(t):                   # PVC（形A）：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def qrs_pvc2(t):                  # PVC（形B）：下向きのQRS、上向きのT（多源性用）
    return (-0.80*_ga(t, 0.01, 0.022, 0.026) + 0.25*_g(t, 0.075, 0.020)
            + 0.36*_ga(t, 0.26, 0.060, 0.045))


def qrs_paced(t):                 # 右室ペーシング（II誘導）：幅の広い下向きのQRS（約150ms）、上向きのT（逆向き＝discordant）
    return (-0.78*_ga(t, 0.0, 0.030, 0.036) + 0.08*_g(t, 0.072, 0.016)
            + 0.32*_ga(t, 0.30, 0.075, 0.055))


def qrs_fusion(t):                # 融合収縮：自分のQRSとペーシングのQRSの中間
    return 0.5*qrs_normal(t) + 0.5*qrs_paced(t)


PV_DELAY = 0.075                 # 心室スパイク → ペーシングQRSの谷（スパイクはQRSの立ち上がりの直前）
A_SPIKE = 0.045                  # 心房スパイク → ペーシングのP波の頂点
RETRO_P = 0.22                   # ペースメーカー頻拍：心室ペーシング → 逆行性P波

# 出来事の種類 → (QRSの形, P波の形, P→Rの間隔)。時刻は R（ペーシングのQRSは谷）。スパイクだけのものはスパイクの時刻
KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 自分の拍（洞調律）
    'A': (qrs_normal, p_sinus, 0.20),       # 心房ペーシング → 自分の房室結節を通って細いQRS
    'V': (qrs_paced, None, 0.0),            # 心室ペーシング（P波なし）
    'Vs': (qrs_paced, None, 0.0),           # 心室ペーシング（スパイクが小さい：双極リード）
    'D': (qrs_paced, p_sinus, 0.22),        # 心房・心室ペーシング（スパイク2本）
    'PV': (qrs_paced, p_sinus, 0.22),       # 自分のP波 → 心室ペーシング
    'F': (qrs_fusion, p_sinus, PR),         # 融合収縮
    'PF': (qrs_normal, p_sinus, PR),        # 偽融合（自分のQRSにスパイクが重なるだけ）
    'S': (None, None, 0.0),                 # スパイクだけ（QRSがつづかない）
    'VR': (qrs_paced, None, 0.0),           # 心室ペーシング＋逆行性P波（ペースメーカー頻拍）
}
# スパイク：種類 → [(時刻のずれ, 高さ mV)]
SPIKES = {
    'A': [(-0.20 - A_SPIKE, 1.0)],
    'V': [(-PV_DELAY, 1.0)],
    'Vs': [(-PV_DELAY, 0.16)],
    'D': [(-0.22 - A_SPIKE, 1.0), (-PV_DELAY, 1.0)],
    'PV': [(-PV_DELAY, 1.0)],
    'F': [(-0.035, 0.75)],                  # LITFL：融合ではスパイクが短くなる
    'PF': [(0.0, 1.0)],
    'S': [(0.0, 1.0)],
    'VR': [(-PV_DELAY, 1.0)],
}
LRI = 1.0                                   # 下限レート 60/分 の間隔
ALL = [(-1e9, 1e9)]                         # 全部をその色で

# 12パターン：1周期ぶんの出来事と周期の長さ（L）、色を付ける範囲（hl。周期の中の時刻）
PATTERNS = [
    dict(no='①', name='心房ペーシング', col=C_PACE, hint='Pの前にスパイク',
         one='スパイク → P波 → 細いQRS',
         ev=[(0, 'A')], L=LRI, hl=ALL),
    dict(no='②', name='心室ペーシング', col=C_PACE, hint='QRSの前にスパイク',
         one='スパイク → 幅の広いQRS（Tは逆向き）',
         ev=[(0, 'V')], L=LRI, hl=ALL),
    dict(no='③', name='心房・心室ペーシング', col=C_PACE, hint='スパイクが2本',
         one='スパイクが2本：P波の前と、QRSの前',
         ev=[(0, 'D')], L=LRI, hl=ALL),
    dict(no='④', name='P波に合わせるペーシング', col=C_PACE, hint='自分のPのあとにスパイク',
         one='自分のP波のあと、QRSの前にだけスパイク',
         ev=[(0, 'PV')], L=0.8, hl=ALL),
    dict(no='⑤', name='自分の脈があれば休む', col=C_INH, hint='スパイクが出ない時間',
         one='自分の脈が出ているあいだは、スパイクが出ない',
         ev=[(0, 'N'), (.8, 'N'), (1.6, 'N'), (1.6 + LRI, 'V'), (1.6 + 2*LRI, 'V')], L=4.4,
         hl=[(-0.25, 1.6 + 0.45)]),
    dict(no='⑥', name='スパイクが小さい', col=C_INH, hint='スパイクが見えにくい',
         one='スパイクが小さく、見えにくいことも（双極リード）',
         ev=[(0, 'Vs')], L=LRI, hl=ALL),
    dict(no='⑦', name='融合収縮', col=C_FUS, hint='中間の形のQRS',
         one='スパイクと自分の脈がほぼ同時。QRSが中間の形',
         ev=[(0, 'V'), (LRI, 'V'), (2*LRI, 'F'), (2.8, 'N'), (3.6, 'N')], L=3.6 + LRI,
         hl=[(2*LRI - 0.25, 2*LRI + 0.45)]),
    dict(no='⑧', name='偽融合', col=C_FUS, hint='QRSの上にスパイク',
         one='自分のQRSにスパイクが重なるだけ。形は変わらない',
         ev=[(0, 'V'), (LRI, 'V'), (2*LRI, 'PF'), (2.8, 'N'), (3.6, 'N')], L=3.6 + LRI,
         hl=[(2*LRI - 0.25, 2*LRI + 0.45)]),
    dict(no='⑨', name='ペーシング不全', col=C_BAD, hint='スパイクだけ',
         one='スパイクのあとに、QRSがない',
         ev=[(0, 'V'), (LRI, 'V'), (2*LRI, 'S'), (3*LRI, 'V')], L=4*LRI,
         hl=[(2*LRI - 0.12, 2*LRI + 0.30)]),
    dict(no='⑩', name='オーバーセンシング', col=C_BAD, hint='スパイクも出ない休み',
         one='スパイクが出ず、長く止まる',
         ev=[(0, 'V'), (LRI, 'V'), (3.4, 'V')], L=3.4 + LRI,
         hl=[(LRI + 0.45, 3.4 - 0.12)]),
    dict(no='⑪', name='アンダーセンシング', col=C_BAD, hint='T波の上にスパイク',
         one='自分の脈があるのに、スパイクが出る',
         ev=[(0, 'N'), (.8, 'N'), (1.10, 'S'), (1.6, 'N')], L=2.4,
         hl=[(1.10 - 0.10, 1.10 + 0.10)]),
    dict(no='⑫', name='ペースメーカー頻拍', col=C_PMT, hint='速いペーシング',
         one='ペーシングのまま速い（上限の速さで続く）',
         ev=[(0, 'VR')], L=0.5, hl=ALL),
]
N_PAT = len(PATTERNS)
for _p in PATTERNS:
    _p['beats'] = _p['ev']

# 区間の長さ（秒）。ナレーションが届くまでの仮の値：周期の倍数で 5秒以上のいちばん短い長さ。
# 録音が届いたら、第18弾と同じく「声の長さ＋0.2秒」以上で、拍の並びがくずれない位置で切り直す
SEG_D = {}
for _p in PATTERNS:
    SEG_D[_p['no']] = _p['L'] * math.ceil(5.0 / _p['L'] - 1e-9)
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    assert _p['D'] >= 3.44 - 1e-9, _p['no']


def beat_wave(tau, r, kind):
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    if kind == 'VR':
        v += p_retro(tau - RETRO_P)
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


def fwave(rel, L):
    """心房細動の細動波（f波）。周期 L でくり返す（ミニ波形でループするため）。0.5mm 程度。"""
    out = np.zeros_like(rel)
    for f, a, ph in ((5.6, 0.020, 0.3), (6.9, 0.017, 1.7), (8.3, 0.012, 2.9), (4.7, 0.010, 0.9)):
        n = max(1, round(f*L))
        out += a*np.sin(2*np.pi*n*rel/L + ph)
    return out


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


# --- 中部の帯：14パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンを rep 回くり返して置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 7.5                     # 冒頭の文が入る長さ（録音が届いたら合わせる）
END_HOLD = 5.9                    # 12個そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [2, 6, 8, 10, 11]          # ③心房・心室 → ⑦融合 → ⑨ペーシング不全 → ⑪アンダーセンシング → ⑫ペースメーカー頻拍
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12


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


HANDOFF_EARLY = 0.35
STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()
STRIP_SPK = spike_times(STRIP)          # 中部の帯のスパイク [(時刻, 高さ)]

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.6mV）
_TOP_END = 636 + 110               # ③⑥の下端
_BOT_TOP = 1188                    # ⑦⑩の上端
# 見た目の上端（名前の字の上）〜下端（PVCのS波の底、約0.4mV）で余白をそろえる
_MID_H = 22 + 54 + 16 + 30 + 140 + 56
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + 16 + 30 + 140
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
    # 区間の終わりが右端の少し先（0.35秒）に来た瞬間。次のパターンの最初のP波・細動波が
    # 右端に入る前に縮み始めるので、見えているのはパターン i だけになる
    _b = t_of(SEGS[_i][1] - HALF - HANDOFF_EARLY)
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60
DUR_TARGET = round(_DUR_LOOP * FPS_LOOP) / FPS_LOOP


def _loop_dur_search():
    """14個そろったあと END_HOLD 秒ほど置き、最後のコマの次が t=0 のコマになる長さ。
    最後に見えている洞調律と、冒頭の洞調律の位相（0.80秒周期）をそろえる。"""
    base = T_END + FLY + END_HOLD
    best = None
    for n in range(int(base*FPS_LOOP), int((base + RR*SLOW + 0.5)*FPS_LOOP)):
        d = n / FPS_LOOP
        ph = ((tau_c(d) - STRIP_END) - tau_c(0.0)) % RR
        err = min(ph, RR - ph)
        if best is None or err < best[0] - 1e-9:
            best = (err, d)
    return best[1]


DUR = DUR_TARGET


# --- ミニ波形の枠 -----------------------------------------------------------------
CELL_W, CELL_H = 400, 110
COL_X = (130, 550)
TOP_Y = [396, 516, 636]
BOT_Y = [1188, 1308, 1428]
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える。洞停止・完全房室ブロック用）
M_MV = 33.0


def cell_rect(i):
    if i < 6:
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 6
        col, row = j // 3, j % 3
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


def strip_fib(tau):
    """細動の区間だけ f波を足す（区間の端は0.25秒でなめらかに）。"""
    v = np.zeros_like(tau)
    for i, (s0, s1) in enumerate(SEGS):
        if not PATTERNS[i].get('fib'):
            continue
        env = np.clip((tau - (s0 - 0.25)) / 0.25, 0, 1) * np.clip(((s1 + 0.05) - tau) / 0.25, 0, 1)
        if env.any():
            v += fwave(tau - s0, PATTERNS[i]['L']) * env
    return v


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
    return wave_from(STRIP, tau) + strip_fib(tau), strip_colors(tau), spk


def spike_runs(spk, xs, ys, mv, x_off=0.0, y_off=0.0):
    """スパイクを縦の線（点列）にする。根元は波形の高さ、少し下から上へ。"""
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
    v = wave_from(bl, rel) + (fwave(rel, pat['L']) if pat.get('fib') else 0)
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
        runs += spike_runs([q for q in spk if q[2] == ci], FX, ys, F_MV)
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


def featured(t, base_col, a):
    if T_STOP <= t < T_GO:
        (v0, c0, s0), (v1, c1, s1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a, s1 if u >= 0.5 else s0)
    v, cid, spk = strip_arrays(tau_c(t))
    return draw_wave(v, cid, base_col, a, spk)


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
    v = wave_from(bl, rel) + (fwave(rel, pat['L']) if pat.get('fib') else 0)
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
        runs += spike_runs([q for q in spk if q[2] == flag], xs, ys, mv, bx0, by0)
        if not runs:
            continue
        out.alpha_composite(glow_line(size, runs, col, (lw_e or lw) if flag else lw,
                                      a if flag else a*a_norm, blur=blur))
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


MINI_LW_ECT = 3.8                  # ミニ波形で、期外収縮の拍の線の太さ（ふつうの拍は 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、ふつうの拍の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u))
    base.alpha_composite(im, pos)


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。番号とヒント）/'now'（紹介中）/'done'（ミニ波形あり）"""
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
HEADER = [('ペースメーカー、まず覚えたい', 1.0, WHITE), ('12', 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
HEADER_BASE = 372                   # 見出しのベースライン（y）
NOTE1 = '実際の速さ（下限レート60/分の想定）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「ペースメーカー、まず覚えたい」＋大きな黄色の「12」＋「パターン」。左右の余白（130px）に収める。"""
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


# 第18弾の専門医レビューにならい、見つけたらすぐ報告する波形には、ひとことのうしろに赤で「→ すぐ報告」
ALERT = {'⑨', '⑩', '⑪', '⑫'}
ALERT_TXT = '→ すぐ報告'
ALERT_COL = (255, 96, 96)


def draw_one(im, pat, a):
    """中部のひとこと。ALERT のパターンは赤い「→ すぐ報告」を続けて、2つまとめて中央ぞろえ。"""
    if pat['no'] not in ALERT:
        put(im, pat['one'], 32, 500, (226, 232, 231), cx=540, cy=Y_ONE, a=a, max_w=820)
        return
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(ALERT_TXT, sz, 800, ALERT_COL)[0].size[0] - 8
        if w1 + 14 + w2 <= 820 or sz <= 24:
            break
        sz -= 1
    x0 = 540 - (w1 + 14 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=Y_ONE, a=a)
    put(im, ALERT_TXT, sz, 800, ALERT_COL, x=x0 + w1 + 14, cy=Y_ONE, a=a)


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
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=al, max_w=820)
        draw_one(im, pat, al)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        put(im, '心電図で気づく', 36, 500, PURPLE, cx=540, cy=560, a=a_t)
        put(im, 'ペースメーカー', 150, 900, WHITE, cx=540, cy=690, a=a_t, max_w=880)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, 'スパイクを見たら、この12パターン', 42, 800, WHITE, cx=540, cy=Y_NAME, a=a_end, max_w=820)
        put(im, '保存して見返してね', 36, 700, GREEN, cx=540, cy=Y_ONE,
            a=ramp(t, T_END + FLY + 1.5, 0.6)*keep)

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a_strip = min(a_strip, ramp(t, b_i + FLY - 0.1, 0.45))
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    if a_strip > 0.01:
        im.alpha_composite(featured(t, base_col, a_strip), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=1567, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=1594, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


def thumbnail():
    """サムネイル（透かしなし）。14個そろった一覧に、大きな「期外収縮」と⑥PVCの波形。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    global _GRID
    if _GRID is None:
        _GRID = grid()
    t = T_END + FLY + 2.0
    im = _GRID.copy()
    draw_header(im, 1.0)
    for i in range(N_PAT):
        draw_cell(im, i, t, 'done', 1.0)
        mini(im, i, t, 1.0)
    put(im, 'スパイクの意味、わかる？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 28, max_w=820)
    put(im, 'ペースメーカー', 96, 900, WHITE, cx=540, cy=Y_ONE + 14, max_w=880)
    v, cid, spk = hook_arrays(8)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0, spk)
    im.alpha_composite(wl, (0, F_Y0 + 50))
    return im.convert('RGB')


# --- 一覧型のサムネイル（第17弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {
    0: (0.0, []),
    1: (0.0, []),
    2: (0.0, []),
    3: (0.0, []),
    4: (0.4, [(1.6 + 0.55, 2.6 + 0.30)]),          # 自分の脈のあと、下限の間隔でペーシングが始まる
    5: (0.0, []),
    6: (0.4, [(2*LRI - 0.14, 2*LRI + 0.12)]),      # 融合
    7: (0.4, [(2*LRI - 0.12, 2*LRI + 0.12)]),      # 偽融合
    8: (0.4, [(2*LRI - 0.12, 2*LRI + 0.30)]),      # スパイクだけ
    9: (0.4, [(LRI + 0.45, 3.4 - 0.15)]),          # スパイクも出ない休み
    10: (0.2, [(1.10 - 0.06, 1.10 + 0.06)]),       # T波の上のスパイク
    11: (0.0, []),
}
THUMB_MAX_MARKS = {}
THUMB_DESC = ['Pの前にスパイク', 'QRSの前', '2本', '', '', '見えにくい',      # '' は名前だけ（入らない）
              '中間の形', '形は変わらない', 'QRSがない', '止まる', 'T波の上', '上限の速さ']


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
    v = wave_from(bl, rel) + (fwave(rel, pat['L']) if pat.get('fib') else 0)
    v = v * np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(3.2*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.7*mv) - pad
    spk = [(x0 + (ts - t0)*pxs, amp) for ts, amp in spike_times(bl) if rel[0] + 0.03 <= ts <= rel[-1] - 0.03]
    runs = [list(zip(xs - ox, ys - oy))] + spike_runs(spk, xs, ys, mv, ox, oy)
    lay = glow_line(size, runs, pat['col'], 2.8, 1.0, blur=(4, 10))
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
            for xs_, amp in spk:                      # 丸の中のスパイクの先まで囲む
                if bx0 <= xs_ <= bx1:
                    by0 = min(by0, float(np.interp(xs_, xs, ys)) - amp*mv - 6)
            by1 = max(ys[sel].max() + 9, base_y + 0.35*mv)
            dashed_ellipse(d, (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy), pat['col'])
    return lay, (ox, oy)


def thumbnail_list():
    """サムネイル（透かしなし）。第17弾の一覧型と同じ作り：
    タイトル → 12パターンを2列×6段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, 'ペースメーカー', 112, 900, WHITE, cx=540, cy=436, max_w=880)
    put(im, '見分けられる？', 60, 900, YEL, cx=540, cy=546)
    COLS = [(135, 515), (565, 945)]             # 列のあいだは50px あける（線は引かない）
    Y0, RH = 628, 142
    for i, pat in enumerate(PATTERNS):
        c, r = divmod(i, 6)
        x0, x1 = COLS[c]
        y = Y0 + r*RH
        name = f"{pat['no']} {pat['name']}"
        im_n, _ = text_img(name, 26, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 26, 800, pat['col'], x=x0, cy=y + 24, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if THUMB_DESC[i]:
            im_h, _ = text_img(THUMB_DESC[i], 18, 500, (176, 186, 186))
            assert nx + im_h.size[0] - 8 <= x1 + 4, f'{pat["no"]} のひとことが入らない'
            put(im, THUMB_DESC[i], 18, 500, (176, 186, 186), x=nx, cy=y + 26)
        lay, pos = thumb_row_wave(i, x0, x1, y + 98, 30.0)
        im.alpha_composite(lay, pos)
        if r < 5:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)], fill=(38, 54, 48, 255), width=1)
    by = Y0 + 6*RH + 24
    d.rounded_rectangle([(230, by), (850, by + 96)], radius=18, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('まず覚えたい', 40, WHITE), ('12', 72, YEL), ('パターン', 40, WHITE)]
    ims = [text_img(t, sz, 900, col) for t, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 70                          # 文字の下端（ベースライン）をそろえる
    for (t, sz, col), (a, asc) in zip(parts, ims):
        put(im, t, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _pr_ms(prc):
    """P頂点→R頂点 prc のときの PR間隔（P波の始まり → QRSの始まり、ms）。"""
    tt = np.arange(-0.6, 0.2, 0.0005)
    p = p_sinus(tt + prc); q = qrs_normal(tt)
    p_on = tt[p > 0.05*p.max()].min()
    q_on = tt[(np.abs(q) > 0.05) & (tt < 0.1)].min()
    return (q_on - p_on) * 1000


def _qrs_ms(f):
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < 0.12)
    return (tt[m].max() - tt[m].min()) * 1000


def check():
    print('パターンごとの紹介の時間')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']} {pat['name']:<10} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s  画面 {a:5.1f}–{b:5.1f}s（{b-a:4.1f}s）")
    print(f'12個目の終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s')
    # 区間のつなぎ目：前のパターンの最後の拍 → 次のパターン（またはうしろの洞調律）の最初の拍
    for i, (s0, s1) in enumerate(SEGS):
        last = max((b for b in STRIP if s0 <= b[0] < s1 and b[1] != 'P'), key=lambda b: b[0])
        nxt = min((b for b in STRIP if b[0] >= s1 - 1e-9 and b[1] != 'P'), key=lambda b: b[0])
        print(f"  つなぎ目 {PATTERNS[i]['no']}→ : QRS {last[1]} {last[0]-s0:.2f} → {nxt[1]} 間隔 {nxt[0]-last[0]:.2f}s")
    print(f'下限レート {60/LRI:.0f}/分（間隔 {LRI:.2f}秒）')
    print(f'① 心房ペーシング：スパイク → P波の頂点 {A_SPIKE*1000:.0f}ms、PR（スパイク → R）{(0.20 + A_SPIKE)*1000:.0f}ms')
    print(f'② 心室ペーシング：QRS幅 {_qrs_ms(qrs_paced):.0f}ms（下向き）、T波は上向き（逆向き）')
    print(f'③ 心房・心室：スパイクの間隔（AV delay）{(0.22 + A_SPIKE - PV_DELAY)*1000:.0f}ms')
    print(f'④ P波に合わせる：P波の頂点 → 心室スパイク {(0.22 - PV_DELAY)*1000:.0f}ms、心拍 {60/0.8:.0f}/分（自分の洞調律）')
    print(f'⑤ 休む：自分の拍 0.80秒ごと → 最後の自分の拍から {LRI:.2f}秒でペーシング（下限の間隔）')
    print(f'⑥ 小さいスパイク：高さ {SPIKES["Vs"][0][1]:.2f}mV（ふつうは 1.0mV で描く）')
    print(f'⑦ 融合：QRS幅 {_qrs_ms(qrs_fusion):.0f}ms（自分 {_qrs_ms(qrs_normal):.0f} と ペーシング {_qrs_ms(qrs_paced):.0f} の間）、スパイク {SPIKES["F"][0][1]:.2f}mV')
    print('⑧ 偽融合：自分のQRS（形は同じ）の頂点にスパイク')
    print(f'⑨ ペーシング不全：QRSどうしの間隔 {2*LRI:.1f}秒（スパイクは{LRI:.1f}秒ごとに出ている）')
    print(f'⑩ オーバーセンシング：スパイクの出ない休み {3.4 - LRI:.1f}秒（下限の間隔 {LRI:.1f}秒より長い）')
    print(f'⑪ アンダーセンシング：スパイクは直前のRから {1.10 - 0.8:.2f}秒（T波の頂点は約0.27秒）')
    print(f'⑫ ペースメーカー頻拍：{60/0.5:.0f}/分、逆行性P波は心室スパイクから {(RETRO_P + PV_DELAY)*1000:.0f}ms')
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:8]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])


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
    """中部の波形の R が画面の中央を通るときに「ピッ」。心室の拍は低い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, i in STRIP:
        if k in ('S',):
            continue
        ts = t_of(r)
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 960.0 if k in ('N', 'A', 'PF') else 720.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel19_pacing.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel19_pacing_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel19_pacing_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel19.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel19_list.png')
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
