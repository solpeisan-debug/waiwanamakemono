"""第17弾 期外収縮 14パターン（v2）

配置：
- 上部：①〜⑧ のミニ波形（2列×4段。左が心房、右が接合部・心室）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと
- 下部：⑨〜⑭ のミニ波形（2列×3段。左が並び方、右が危険なもの）

紹介が終わった波形は、中部から自分の枠へ移り、ミニ波形として流れ続ける。
紹介中の枠と、まだ紹介していない枠は番号だけ。

使い方:
    python3 make_reel17_v2.py              # 90秒・60fps
    python3 make_reel17_v2.py --still 20   # 1コマだけ
    python3 make_reel17_v2.py --check      # 検算・タイミング表
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

C_ATR = (110, 200, 255)          # 心房
C_JUN = (190, 160, 255)          # 接合部
C_VEN = (255, 212, 90)           # 心室
C_PAT = (255, 152, 72)           # 並び方
C_DNG = (255, 92, 112)           # 危険

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
RR = 0.80                        # 洞調律 75/分
PR = 0.16                        # P頂点 → R頂点
RETRO_P = 0.12                   # PVCのR頂点 → 逆行性P波（ST部分）


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


# 拍の種類 → (QRSの形, P波の形, P→Rの間隔)
KINDS = {
    'N':  (qrs_normal, p_sinus, PR),
    'A':  (qrs_normal, p_ect, PR),          # PAC
    'Aa': (qrs_aberrant, p_ect, PR),        # 変行伝導のPAC
    'Ah': (qrs_normal, p_ect, 0.18),        # T波の下り坂に出たPAC（不応期をぎりぎり抜けて伝わる。PRが少し延びる）
    'B':  (None, p_ect, PR),                # 伝わらないPAC（P'だけ。時刻はP'の位置+PR）
    'J':  (qrs_normal, None, 0),            # PJC（P波なし）
    'V':  (qrs_pvc, None, 0),
    'Vr': (qrs_pvc, None, 0),               # 逆行性P波つきPVC
    'V2': (qrs_pvc2, None, 0),
    'p':  (None, p_sinus, PR),              # 伝わらなかった洞のP（PVCに隠れる）
}

# 14パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ
# どれも洞調律 0.80秒の上に置く。PVC・PJCは洞の時計を乱さない（休みは2拍ぶん）
PATTERNS = [
    dict(no='①', name='PAC', col=C_ATR, rep=2, hint="形のちがうP波",
         one="形のちがうP'が早く出る・QRSは細い",
         beats=[(0, 'N'), (.60, 'A'), (1.52, 'N'), (2.32, 'N')], L=3.12),       # P'は T波のあと（0.44秒）
    dict(no='②', name="P'が隠れるPAC", col=C_ATR, rep=2, hint="Tの形が変わる",
         one="P'がT波に重なり、Tの形が変わる",
         beats=[(0, 'N'), (.50, 'Ah'), (1.45, 'N'), (2.25, 'N')], L=3.05),      # P'は T波の下り坂（0.32秒）
    dict(no='③', name='伝わらないPAC', col=C_ATR, rep=2, hint="QRSが来ない",
         one="P'のあとにQRSがない → 休みに見える",
         beats=[(0, 'N'), (.27+PR, 'B'), (1.40, 'N'), (2.20, 'N')], L=3.0),
    dict(no='④', name='変行伝導のPAC', col=C_ATR, rep=2, hint="Pはあるのに広い",
         one="P'はあるのに、QRSが広い",
         beats=[(0, 'N'), (.45, 'Aa'), (1.40, 'N'), (2.20, 'N')], L=3.0),
    dict(no='⑤', name='PJC', col=C_JUN, rep=2, hint="Pのない細いQRS",
         one='細いQRSが早く出る・P波がない',
         beats=[(0, 'N'), (.50, 'J'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),  # LITFL: followed by a compensatory pause（2拍ぶん）
    dict(no='⑥', name='PVC', col=C_VEN, rep=2, hint="広いQRS",
         one='広いQRS・Tが逆向き・休みは2拍ぶん',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑦', name='逆行性P波つきPVC', col=C_VEN, rep=2, hint="うしろに逆向きのP",
         one='QRSのあとに、逆向きのP波',
         beats=[(0, 'N'), (.40, 'Vr'), (1.48, 'N'), (2.28, 'N')], L=3.08),      # 逆行性P（0.52秒）が洞結節をリセット → 休み 1.48秒
    dict(no='⑧', name='多源性PVC', col=C_VEN, rep=1, hint="形が2種類",
         one='PVCの形が、2種類以上',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N'), (2.88, 'V2'),
                (3.2, 'p'), (4.0, 'N')], L=4.8),
    dict(no='⑨', name='二段脈', col=C_PAT, rep=3, hint="1拍おき",
         one='1拍おきにPVC。脈は半分のことも',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p')], L=1.6),
    dict(no='⑩', name='三段脈', col=C_PAT, rep=1, hint="2拍おき",
         one='2拍おきにPVC',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N')], L=2.4),
    dict(no='⑪', name='四段脈', col=C_PAT, rep=1, hint="3拍おき",
         one='3拍おきにPVC',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑫', name='2連発', col=C_DNG, rep=2, hint="2つ続く",
         one='PVCが2つ続く → 報告（基準は施設の指示で）',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (.90, 'V'), (1.6, 'N')], L=2.4),
    dict(no='⑬', name='3連以上', col=C_DNG, rep=2, hint="3つ以上続く",
         one='3つ以上・100/分超 → 非持続性心室頻拍（ショートラン）',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (.90, 'V'), (1.32, 'V'), (1.6, 'p'),
                (1.74, 'V'), (2.4, 'N'), (3.2, 'N')], L=4.0),    # ふつうの拍を1つ足して周期4.0秒 → 7.2秒で切れる
    dict(no='⑭', name='R on T', col=C_DNG, rep=2, hint="T波に乗る",
         one='PVCがT波に乗る。QT延長があると危ない',
         beats=[(0, 'N'), (.27, 'V'), (.8, 'p'), (1.6, 'N')], L=2.4),
]
N_PAT = len(PATTERNS)

# 区間の長さ（秒）。ナレーションの長さ＋0.2秒以上になる、いちばん短い「ふつうの拍の位置」で切る。
# その位置には次のパターンの最初のふつうの拍が来るので、拍の間隔は変わらない。
# 中部から縮むとき、見えている3.1秒がそのパターンだけになるよう、原則 3.2秒以上にする。
SEG_D = {'①': 6.24, '②': 4.50, '③': 4.4, '④': 5.2, '⑤': 5.6, '⑥': 6.4, '⑦': 4.56,
         '⑧': 4.0, '⑨': 4.8, '⑩': 4.0, '⑪': 3.2, '⑫': 2.4, '⑬': 7.2, '⑭': 4.8}
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    _n = [r for r, k in _p['beats'] if k == 'N']
    assert any(abs(((_p['D'] - r) / _p['L']) - round((_p['D'] - r) / _p['L'])) < 1e-6 for r in _n), _p['no']


def beat_wave(tau, r, kind):
    """1拍ぶんの波形（tau は R の時刻からの秒）。"""
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    if kind == 'Vr':
        v += p_retro(tau - RETRO_P)
    return v


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, r, k)
    return v


def periodic_beats(pat, t0, t1):
    """パターンを繰り返した拍の列（t0〜t1 の範囲）。"""
    out = []
    L = pat['L']
    k0 = int(math.floor(t0 / L)) - 1
    k1 = int(math.ceil(t1 / L)) + 1
    for k in range(k0, k1):
        for r, kind in pat['beats']:
            out.append((k*L + r, kind))
    return out


# --- 中部の帯：14パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンを rep 回くり返して置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 7.5                     # ナレーションの冒頭3文（約7.4秒）が入る長さ
END_HOLD = 5.9                    # 14個そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [0, 8, 7, 13, 12]          # ①PAC → ⑨二段脈 → ⑧多源性 → ⑭R on T → ⑬3連以上
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < pat['D'] - 1e-9:
                beats.append((t + r, kind, None if kind in ('N', 'p') else i))
        t += pat['D']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -12:                     # 前：洞調律
        beats.append((k*RR, 'N', None)); k -= 1
    # うしろ：洞調律。尺をちょうど DUR_TARGET にしてもループがつながるよう、
    # 最初の6拍の間隔を少しだけ広げて位相をそろえる（0.80秒 → 最大 0.80+0.8/6 秒）
    # 尺は「最後の2文が入る長さ」以上で、うしろの洞調律の位相が冒頭とそろういちばん短い長さ。
    # こうすると、うしろの拍の間隔を変えずにループがつながる
    need = T_TITLE + end + 0.8 + END_HOLD                      # 0.8 = FLY
    k = math.ceil((need - FREEZE - end) / RR - 1e-9)
    dur_target = FREEZE + end + k*RR
    shift = 0.0
    tt = end
    beats.append((tt, 'N', None))
    for k in range(1, 60):
        tt += RR + (shift/6 if k <= 6 else 0.0)
        beats.append((tt, 'N', None))
    beats.sort(key=lambda b: b[0])
    return beats, segs, end, dur_target


STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.6mV）
_TOP_END = 696 + 92                # ④⑧の下端
_BOT_TOP = 1248                    # ⑨⑫の上端
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
    _b = t_of(SEGS[_i][1] - HALF)          # 区間の終わりが右端に来た瞬間
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
CELL_W, CELL_H = 400, 92
COL_X = (130, 550)
TOP_Y = [396, 496, 596, 696]
BOT_Y = [1248, 1348, 1448]
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 88.0                      # ミニ波形：実際の1秒 = 88px
M_MV = 27.0


def cell_rect(i):
    if i < 8:
        col, row = i // 4, i % 4
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 8
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
    """期外収縮の拍だけ、そのパターンの色。"""
    cid = np.full(len(tau), -1, dtype=int)
    for r, k, i in STRIP:
        if i is None:
            continue
        lo, hi = (r - PR - 0.06, r + 0.40) if k in ('A', 'Aa', 'B') else (r - 0.09, r + 0.40)
        m = (tau >= lo) & (tau <= hi)
        cid[m] = i
    return cid


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
    tau = tau_center + (FX - XC) / F_PXS
    return wave_from(STRIP, tau), strip_colors(tau)


def ectopic_mask(bl, rel):
    ect = np.zeros(len(rel), dtype=bool)
    for r, k in bl:
        if k in ('N', 'p'):
            continue
        lo, hi = (r - PR - 0.06, r + 0.40) if k in ('A', 'Aa', 'B') else (r - 0.09, r + 0.40)
        ect |= (rel >= lo) & (rel <= hi)
    return ect


def hook_arrays(i):
    """フック用：パターン i の、期外収縮が中央の少し左に来る一場面。"""
    pat = PATTERNS[i]
    first = min(r for r, k in pat['beats'] if k not in ('N', 'p'))
    rel = first + 0.35 + (FX - XC) / F_PXS + pat['L']
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    cid = np.where(ectopic_mask(bl, rel), i, -1)
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
    for ci in np.unique(cid):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


def featured(t, base_col, a):
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a)
    v, cid = strip_arrays(tau_c(t))
    return draw_wave(v, cid, base_col, a)


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 62, 38     # ミニ波形の帯（枠の中）


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
    v = wave_from(bl, rel)
    ys = base_y - v*mv
    ect = np.zeros(len(xs), dtype=bool)
    for r, k in bl:
        if k in ('N', 'p'):
            continue
        lo, hi = (r - PR - 0.06, r + 0.40) if k in ('A', 'Aa', 'B') else (r - 0.09, r + 0.40)
        ect |= (rel >= lo) & (rel <= hi)
    y_lo = int(min(ys.min(), base_y - 1.1*mv) - 30)
    y_hi = int(max(ys.max(), base_y + 0.9*mv) + 30)
    bx0, by0 = int(x_lo) - 30, y_lo
    size = (int(x_hi - x_lo) + 60, max(4, y_hi - y_lo))
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        if not len(idx):
            continue
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
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
HEADER = [('期外収縮、まず覚えたい', 1.0, WHITE), ('14', 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
HEADER_BASE = 372                   # 見出しのベースライン（y）
NOTE1 = '実際の速さ（心拍数75/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「期外収縮、まず覚えたい」＋大きな黄色の「14」＋「パターン」。左右の余白（130px）に収める。"""
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
        put(im, pat['one'], 32, 500, (226, 232, 231), cx=540, cy=Y_ONE, a=al, max_w=820)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        put(im, '心電図で気づく', 36, 500, PURPLE, cx=540, cy=560, a=a_t)
        put(im, '期外収縮', 150, 900, WHITE, cx=540, cy=690, a=a_t)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, '1拍だけ早かったら、この14パターン', 42, 800, WHITE, cx=540, cy=Y_NAME, a=a_end, max_w=820)
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
    put(im, '1拍だけ早い拍、見分けられる？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 28, max_w=820)
    put(im, '期外収縮', 96, 900, WHITE, cx=540, cy=Y_ONE + 8)
    v, cid = hook_arrays(5)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0)
    im.alpha_composite(wl, (0, F_Y0 + 50))
    return im.convert('RGB')


THUMB_DESC = ['形のちがうP波', 'Tの形が変わる', 'QRSが来ない', 'Pはあるのに広い', 'Pのない細いQRS',
              '広いQRS', 'うしろに逆向きP', '形が2種類', '1拍おき', '2拍おき', '3拍おき',
              '2つ続く', '3つ以上続く', 'T波に乗る']


def dashed_ellipse(d, box, col, dash=7, gap=6, width=3):
    """点線の楕円。"""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1)/2, (y0 + y1)/2, (x1 - x0)/2, (y1 - y0)/2
    th = np.linspace(0, 2*np.pi, 721)
    pts = np.stack([cx + rx*np.cos(th), cy + ry*np.sin(th)], 1)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    on = (seg % (dash + gap)) < dash
    idx = np.where(on)[0]
    for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
        if len(r) >= 2:
            d.line([tuple(q) for q in pts[r]], fill=col + (255,), width=width)


def thumb_row_wave(i, x0, x1, base_y, mv):
    """パターン i を1本の色で描き、期外収縮の拍を点線の丸で囲む（サムネイル用）。"""
    pat = PATTERNS[i]
    span = 4.0                                    # どの段も同じ時間（4秒）を見せる
    pxs = (x1 - x0) / span
    first = min(r for r, k in pat['beats'] if k not in ('N', 'p'))
    t0 = first - 1.25                             # 最初の期外収縮が左から3割くらい
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = t0 + (xs - x0) / pxs
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    # 端はなだらかに0へ（参考画像のように、線が枠の端で切れて見えないように）
    v *= np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(3.2*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.7*mv) - pad
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], pat['col'], 2.8, 1.0, blur=(4, 10))
    # 期外収縮の拍の範囲
    ect = np.zeros(len(xs), dtype=bool)
    for r, k in bl:
        if k in ('N', 'p'):
            continue
        lo, hi = (r - PR - 0.06, r + 0.30) if k in ('A', 'Aa', 'B', 'Ah') else (r - 0.08, r + 0.30)
        ect |= (rel >= lo) & (rel <= hi)
    ect &= (xs > x0 + 12) & (xs < x1 - 12)
    # 続いている期外収縮（2連発・3連以上）は1つの丸にまとめる
    idx = np.where(ect)[0]
    runs = [r for r in (np.split(idx, np.where(np.diff(idx) > 0.25*pxs*2)[0] + 1) if len(idx) else [])
            if len(r) >= 20]
    boxes = []
    for r in runs:
        bx0, bx1 = xs[r[0]] - 6, xs[r[-1]] + 6
        by0, by1 = ys[r].min() - 9, ys[r].max() + 9
        by0, by1 = min(by0, base_y - 0.5*mv), max(by1, base_y + 0.35*mv)
        boxes.append((bx0 - ox, by0 - oy, bx1 - ox, by1 - oy))
    d = ImageDraw.Draw(lay)
    for b in boxes:
        dashed_ellipse(d, b, pat['col'], dash=6, gap=5, width=2)
    return lay, (ox, oy)


def thumbnail_list():
    """サムネイル（透かしなし）。参考：房室ブロック「どれが危ない？」の作り。
    タイトル → 14パターンを2列×7段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, '期外収縮', 126, 900, WHITE, cx=540, cy=436)
    put(im, '見分けられる？', 60, 900, YEL, cx=540, cy=546)
    COLS = [(145, 505), (575, 935)]             # 列のあいだは70px あける（線は引かない）
    Y0, RH = 628, 122
    for i, pat in enumerate(PATTERNS):
        c, r = divmod(i, 7)
        x0, x1 = COLS[c]
        y = Y0 + r*RH
        # 名前（色）＋ひとこと（灰色）
        name = f"{pat['no']} {pat['name']}"
        im_n, _ = text_img(name, 27, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 27, 800, pat['col'], x=x0, cy=y + 22, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if nx + 110 < x1:
            put(im, THUMB_DESC[i], 19, 500, (176, 186, 186), x=nx, cy=y + 24, max_w=x1 - nx)
        lay, pos = thumb_row_wave(i, x0, x1, y + 86, 27.0)
        im.alpha_composite(lay, pos)
        if r < 6:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)], fill=(38, 54, 48, 255), width=1)
    # 下の枠
    by = Y0 + 7*RH + 24
    d.rounded_rectangle([(230, by), (850, by + 96)], radius=18, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('まず覚えたい', 40, WHITE), ('14', 72, YEL), ('パターン', 40, WHITE)]
    ims = [text_img(t, sz, 900, col) for t, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 70                          # 文字の下端（ベースライン）をそろえる
    for (t, sz, col), (a, asc) in zip(parts, ims):
        put(im, t, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def check():
    print('パターンごとの拍（実際の秒）・紹介する画面の時間')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        bs = pat['beats']
        rr = [round(b2[0]-b1[0], 2) for b1, b2 in zip(bs, bs[1:]) if b1[1] != 'p' and b2[1] != 'p']
        print(f"{pat['no']} {pat['name']:<12} 周期{pat['L']:.2f}s×{pat['rep']}  画面 {a:5.1f}–{b:5.1f}s"
              f"（{b-a:4.1f}s）  R-R {rr}")
    print(f'14個目の終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.0f}s')
    # 休み（期外収縮の前の洞 → 次の洞）
    def pause(pat, kind):
        bs = [b for b in pat['beats'] if b[1] != 'p']
        L = pat['L']
        ext = bs + [(r + L, k) for r, k in bs]
        for j, (r, k) in enumerate(ext):
            if k == kind:
                prev = max(x for x, kk in ext[:j] if kk == 'N')
                nxt = min(x for x, kk in ext[j+1:] if kk == 'N')
                return nxt - prev
    print(f"PAC の休み {pause(PATTERNS[0], 'A'):.2f}s（2拍ぶん 1.60 と一致しない）")
    print(f"伝わらないPAC の休み {pause(PATTERNS[2], 'B'):.2f}s（洞の間隔 0.80 よりずっと長い）")
    print(f"PJC の休み {pause(PATTERNS[4], 'J'):.2f}s（2拍ぶん。LITFL: compensatory pause）")
    print(f"逆行性P波つきPVC の休み {pause(PATTERNS[6], 'Vr'):.2f}s（逆行性P {0.40+RETRO_P:.2f}s が洞のP 0.64s より先 → リセット）")
    print(f"P'の位置（直前のRから）：③伝わらない {0.27:.2f}s ＜ ④変行伝導 {0.45-PR:.2f}s ＜ ②隠れる {0.50-0.18:.2f}s ＜ ①PAC {0.60-PR:.2f}s（早いほど伝わりにくい）")
    print(f"PVC の休み {pause(PATTERNS[5], 'V'):.2f}s（2拍ぶん）")
    print(f"3連以上：PVCの間隔 0.42s = {60/0.42:.0f}/分（100/分超）")
    tt = np.arange(-0.2, 0.2, 0.0005)
    for name, f in (('ふつう', qrs_normal), ('変行伝導', qrs_aberrant), ('PVC', qrs_pvc), ('PVC形B', qrs_pvc2)):
        v = f(tt); m = (np.abs(v) > 0.05) & (tt < 0.11)
        print(f'QRS幅 {name}: {(tt[m].max()-tt[m].min())*1000:.0f}ms')
    print(f"R on T：PVCは直前のRから {0.27:.2f}s（T波の頂点 {0.27:.2f}s）")


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
        if k in ('p', 'B'):
            continue
        ts = t_of(r)
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 720.0 if k.startswith('V') else 960.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel17_ectopy_v2.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel17_ectopy_v2_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel17_ectopy_v2_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel17_v2.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel17_list.png')
        thumbnail_list().save(p); print(p); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'v2_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(os.path.dirname(o.out), 'parts_v2')
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
