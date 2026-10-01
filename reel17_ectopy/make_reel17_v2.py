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
    dict(no='①', name='PAC', col=C_ATR, rep=1, hint="形のちがうP波",
         one="形のちがうP'が早く出る・QRSは細い",
         beats=[(0, 'N'), (.48, 'A'), (1.40, 'N'), (2.20, 'N')], L=3.0),
    dict(no='②', name="P'が隠れるPAC", col=C_ATR, rep=1, hint="Tがとがる",
         one="P'がT波に重なって、Tがとがる",
         beats=[(0, 'N'), (.40, 'A'), (1.35, 'N'), (2.15, 'N')], L=2.95),
    dict(no='③', name='伝わらないPAC', col=C_ATR, rep=1, hint="QRSが来ない",
         one="P'のあとにQRSがない → 休みに見える",
         beats=[(0, 'N'), (.27+PR, 'B'), (1.40, 'N'), (2.20, 'N')], L=3.0),
    dict(no='④', name='変行伝導のPAC', col=C_ATR, rep=1, hint="Pはあるのに広い",
         one="P'はあるのに、QRSが広い",
         beats=[(0, 'N'), (.45, 'Aa'), (1.40, 'N'), (2.20, 'N')], L=3.0),
    dict(no='⑤', name='PJC', col=C_JUN, rep=1, hint="Pのない細いQRS",
         one='細いQRSが早く出る・P波がない',
         beats=[(0, 'N'), (.50, 'J'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑥', name='PVC', col=C_VEN, rep=1, hint="広いQRS",
         one='広いQRS・Tが逆向き・休みは2拍ぶん',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑦', name='逆行性P波つきPVC', col=C_VEN, rep=1, hint="うしろに逆向きのP",
         one='QRSのあとに、逆向きのP波',
         beats=[(0, 'N'), (.48, 'Vr'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑧', name='多源性PVC', col=C_VEN, rep=1, hint="形が2種類",
         one='PVCの形が、2種類以上',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N'), (2.88, 'V2'),
                (3.2, 'p'), (4.0, 'N')], L=4.8),
    dict(no='⑨', name='二段脈', col=C_PAT, rep=3, hint="1拍おき",
         one='1拍おきにPVC。脈は半分のことも',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p')], L=1.6),
    dict(no='⑩', name='三段脈', col=C_PAT, rep=2, hint="2拍おき",
         one='2拍おきにPVC',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N')], L=2.4),
    dict(no='⑪', name='四段脈', col=C_PAT, rep=1, hint="3拍おき",
         one='3拍おきにPVC',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (1.6, 'N'), (2.4, 'N')], L=3.2),
    dict(no='⑫', name='2連発', col=C_DNG, rep=2, hint="2つ続く",
         one='PVCが2つ続く → 報告',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (.90, 'V'), (1.6, 'N')], L=2.4),
    dict(no='⑬', name='3連以上', col=C_DNG, rep=1, hint="3つ以上続く",
         one='3つ以上・100/分超 → 非持続性心室頻拍',
         beats=[(0, 'N'), (.48, 'V'), (.8, 'p'), (.90, 'V'), (1.32, 'V'), (1.6, 'p'),
                (1.74, 'V'), (2.4, 'N')], L=3.2),
    dict(no='⑭', name='R on T', col=C_DNG, rep=2, hint="T波に乗る",
         one='PVCがT波に乗る。QT延長があると危ない',
         beats=[(0, 'N'), (.27, 'V'), (.8, 'p'), (1.6, 'N')], L=2.4),
]
N_PAT = len(PATTERNS)


def beat_wave(tau, r, kind):
    """1拍ぶんの波形（tau は R の時刻からの秒）。"""
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    if kind == 'Vr':
        v += p_retro(tau - 0.20)
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
T_TITLE = 2.5                     # タイトルのあいだ（洞調律だけ）
END_HOLD = 6.0                    # 14個そろってからの時間


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for rep in range(pat['rep']):
            for r, kind in pat['beats']:
                beats.append((t + r, kind, None if kind in ('N', 'p') else i))
            t += pat['L']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -12:                     # 前：洞調律
        beats.append((k*RR, 'N', None)); k -= 1
    k = 0
    while k*RR < 40:                      # うしろ：洞調律
        beats.append((end + k*RR, 'N', None)); k += 1
    beats.sort(key=lambda b: b[0])
    return beats, segs, end


STRIP, SEGS, STRIP_END = _strip()

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
F_BASE = 1090
F_Y0, F_Y1 = 890, 1236
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# t=T_TITLE で、パターン①の区間の始まりが画面の右端に来る
OFFSET = -HALF - T_TITLE


def tau_c(t):
    """画面の中央にある実際の時刻。"""
    return t / SLOW + OFFSET


def t_of(tau_center):
    return (tau_center - OFFSET) * SLOW


WINDOWS = []
for _i in range(len(PATTERNS)):
    _a = T_TITLE if _i == 0 else WINDOWS[-1][1]
    _b = t_of(SEGS[_i][1] - HALF)          # 区間の終わりが右端に来た瞬間
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
DUR = round(T_END + FLY + END_HOLD, 1)


# --- ミニ波形の枠 -----------------------------------------------------------------
CELL_W, CELL_H = 400, 92
COL_X = (130, 550)
TOP_Y = [380, 480, 580, 680]
BOT_Y = [1248, 1348, 1448]
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


def featured(t, base_col, a):
    h = F_Y1 - F_Y0
    xs = np.arange(0, W + 1, 0.5)
    tau = tau_c(t) + (xs - XC) / F_PXS
    v = wave_from(STRIP, tau)
    ys = F_BASE - F_Y0 - v*F_MV
    cid = strip_colors(tau)
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in np.unique(cid):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 62, 38     # ミニ波形の帯（枠の中）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0):
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
        out.alpha_composite(glow_line(size, runs, col, lw, a, blur=blur))
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


def mini(base, i, t, u=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl)
    base.alpha_composite(im, pos)


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。番号とヒント）/'now'（紹介中）/'done'（ミニ波形あり）"""
    x0, y0, x1, y1 = cell_rect(i)
    pat = PATTERNS[i]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if state in ('now', 'landing'):
        pulse = 0.55 + 0.45*math.sin(t*5.0)**2
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(150*a_all),),
                            outline=pat['col'] + (int(255*pulse*a_all),), width=3)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(170*a_all),),
                            outline=CARD_EDGE + (int(255*a_all),), width=2)
    base.alpha_composite(lay)
    if state in ('done', 'landing'):
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17,
            a=a_all, max_w=CELL_W - 30)
    elif state == 'now':
        put(base, f"{pat['no']} 紹介中", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17, a=a_all)
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=CELL_W - 80)


# --- 画面 ---------------------------------------------------------------------------
HEADER = '期外収縮、ぜんぶで14パターン'
NOTE1 = '実際の速さ（心拍数75/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


_GRID = None


def frame(t):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    put(im, HEADER, 46, 800, WHITE, cx=540, cy=330, a=ramp(t, 2.0, 0.5))

    a_cells = ramp(t, 1.6, 0.6)
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
            mini(im, i, t, 1.0)

    # 中部：紹介中の名前とひとこと
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        al = ramp(t, a_i + 0.1, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=812, a=al, max_w=820)
        put(im, pat['one'], 32, 500, (226, 232, 231), cx=540, cy=866, a=al, max_w=820)

    a_t = 1 - ramp(t, 1.8, 0.6)
    if a_t > 0:
        put(im, '心電図で気づく', 34, 500, PURPLE, cx=540, cy=760, a=a_t)
        put(im, '期外収縮', 130, 900, WHITE, cx=540, cy=860, a=a_t)

    a_end = ramp(t, T_END + FLY, 0.6)
    if a_end > 0:
        put(im, '1拍だけ早い拍は、この14パターン', 40, 800, WHITE, cx=540, cy=812, a=a_end, max_w=820)
        put(im, '保存して見返してね', 36, 700, GREEN, cx=540, cy=866, a=ramp(t, T_END + FLY + 1.5, 0.6))

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a_strip = min(a_strip, ramp(t, b_i + FLY - 0.1, 0.45))
    u = ramp(t, 1.4, 1.0)
    base_col = mix(PURPLE, WAVE_GREEN, u)
    if a_strip > 0.01:
        im.alpha_composite(featured(t, base_col, a_strip), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=1567, a=0.85*ramp(t, 2.0, 0.5))
    put(im, NOTE2, 24, 400, GREY, x=135, cy=1594, a=0.85*ramp(t, 2.0, 0.5))
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
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
    print(f"PJC の休み {pause(PATTERNS[4], 'J'):.2f}s（2拍ぶん）")
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
    i0, i1, fps, path = args
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
           '-crf', '18', '-pix_fmt', 'yuv420p', path]
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
        if not (2.5 <= ts <= DUR - 0.3):
            continue
        f = 720.0 if k.startswith('V') else 960.0
        L = int(0.08*sr)
        tt = np.arange(L)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr)
        a[j:j+L] += s[:max(0, min(L, n-j))]
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
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    o = ap.parse_args()
    if o.check:
        check(); return
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
    jobs = [(i, min(total, i+step), o.fps, os.path.join(tmp, f'p{j:02d}.mp4'))
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
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', o.out],
                   check=True)
    print(o.out)


if __name__ == '__main__':
    main()
