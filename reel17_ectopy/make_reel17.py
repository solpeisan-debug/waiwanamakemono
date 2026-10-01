"""第17弾 期外収縮 ― QT延長の回（reel_qt_torsades）と同じ作りで描く。

画面の配置・速さ・カードの出し方は QT回の実測値に合わせている（plan.md の 0.）。
- 方眼は動かない。波形だけが右から左へ流れる（実際の3分の1の速さ）
- 1mm = 31.5px、10mm/mV、25mm/秒 → 画面では 262.5px/秒

使い方:
    python3 make_reel17.py                 # 90秒・60fps を書き出す
    python3 make_reel17.py --fps 30        # 下見用
    python3 make_reel17.py --still 25.8    # 1コマだけ PNG に
    python3 make_reel17.py --check         # 波形の間隔を検算して終わる
"""
import argparse
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
DUR = 90.0

# --- 見た目（QT回の実測） ---------------------------------------------------
BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
PX_MM = 31.5                     # 1mm
BASE_Y = 1373                    # 基線
MV = 10 * PX_MM                  # 1mV = 10mm
PX_S = 25 * PX_MM                # 実際の1秒 = 787.5px
SLOW = 3.0                       # 3分の1の速さ
XC = W / 2

WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (92, 104, 104)
CARD_FILL = (9, 19, 16)
CARD_EDGE = (88, 110, 100)
PURPLE = (178, 150, 240)
GREEN = (130, 232, 172)

# 段階の色（進むほど危ない色）
C_NORM = WHITE
C_PAC = (110, 200, 255)
C_PVC = (255, 212, 90)
C_BIG = (255, 152, 72)
C_RUN = (255, 112, 172)
C_REP = (255, 86, 86)

WAVE_GREEN = (40, 214, 128)

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形（実際の時間 τ・秒） -------------------------------------------------
PR = 0.17                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def qrs_t_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.29, 0.065, 0.045))


def qrs_t_pvc(t):
    # 幅の広いQRS（120ms以上）と、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.024)


def p_ectopic(t):
    # P'：小さく、とがっていて、少し二相性
    return 0.13*_g(t, 0.0, 0.016) - 0.04*_g(t, 0.035, 0.014)


# 拍の並び（R頂点の時刻, 種類, その拍を見せる段階の色）
def _beats():
    out = [(float(k), 'N', None) for k in range(-4, 9)]      # -4 … 8
    out += [(8.60, 'A', C_PAC)]
    out += [(9.75, 'N', None), (10.75, 'N', None), (11.75, 'N', None)]
    out += [(12.30, 'V', C_PVC)]
    out += [(13.75, 'N', None), (14.75, 'N', None), (15.75, 'N', None)]
    out += [(16.30, 'V', C_BIG), (17.75, 'N', None), (18.30, 'V', C_BIG), (19.75, 'N', None)]
    out += [(20.75, 'N', None), (21.30, 'V', C_RUN), (21.75, 'V', C_RUN)]
    out += [(22.75, 'N', None), (23.75, 'N', None), (24.75, 'N', None)]
    out += [(25.30, 'V', C_REP), (25.72, 'V', C_REP), (26.14, 'V', C_REP)]
    out += [(26.75 + k, 'N', None) for k in range(0, 6)]
    return out


BEATS = _beats()


def _sinus_clock():
    """洞結節が実際に発火した時刻（R頂点にそろえた時刻）と、PACで消えた予定の時刻。"""
    ticks, ghosts = [], []
    ns = [b for b in BEATS if b[1] != 'V']
    for (r0, k0, _), (r1, k1, _) in zip(ns, ns[1:]):
        if k0 == 'N':
            ticks.append(r0)
        if k1 == 'A':
            ghosts.append(r0 + 1.0)            # PACがなければ来ていた洞の拍
            continue
        if k0 == 'N' and k1 == 'N':
            gap = r1 - r0
            n = int(round(gap))
            if n >= 2 and abs(gap - n) < 1e-6:
                ticks += [r0 + j for j in range(1, n)]   # PVCに隠れた洞のP
    ticks.append(ns[-1][0])
    return sorted(ticks), ghosts


TICKS, GHOSTS = _sinus_clock()
HIDDEN_P = [t for t in TICKS if not any(abs(t-b[0]) < 1e-6 and b[1] == 'N' for b in BEATS)]


def v_at(tau):
    v = np.zeros_like(tau)
    for r, k, _ in BEATS:
        m = np.abs(tau - r) < 0.7
        if not m.any():
            continue
        tt = tau[m] - r
        if k == 'N':
            v[m] += qrs_t_normal(tt) + p_sinus(tt + PR)
        elif k == 'A':
            v[m] += qrs_t_normal(tt) + p_ectopic(tt + PR)
        else:
            v[m] += qrs_t_pvc(tt)
    for r in HIDDEN_P:                         # 伝わらなかった洞のP（PVCのT波に隠れる）
        m = np.abs(tau - (r - PR)) < 0.2
        if m.any():
            v[m] += p_sinus(tau[m] - (r - PR))
    return v


def color_windows():
    """期外収縮の拍を、その段階の色で塗る範囲（τ）。"""
    out = []
    for r, k, c in BEATS:
        if c is None:
            continue
        if k == 'A':
            out.append((r - PR - 0.06, r + 0.42, c))
        else:
            out.append((r - 0.09, r + 0.40, c))
    return out


CWIN = color_windows()


def tau_c(t):
    """画面の中央に来ている実際の時刻。"""
    return t / SLOW


def x_of(tau, t):
    return XC + (tau - tau_c(t)) * PX_S


# --- 段階と台本 ---------------------------------------------------------------
QUESTION = '1拍だけ早い。どこから危ない？'
AXIS = ['正常', 'PAC', 'PVC', '二段脈', '連発', '報告']
STAGE_COL = [C_NORM, C_PAC, C_PVC, C_BIG, C_RUN, C_REP]
STAGE_T = [6.0, 22.0, 34.0, 46.0, 60.0, 72.0]
SUMMARY_T = 82.0

CARDS = [
    dict(title='正常', sub='R-R 1000ms（60/分）', t_title=6.0,
         lines=[(7.0, 'P → QRS → T が、同じ間隔で並ぶ'),
                (13.0, '次の拍が来る時刻は、予想できる'),
                (20.0, 'その予想より早い拍が、期外収縮')]),
    dict(title='PAC', sub='心房期外収縮', t_title=23.0,
         lines=[(24.0, '形のちがうP波（P\'）が、早く出る'),
                (29.0, 'QRSは細いまま'),
                (32.0, '休みは、ちょうど2拍ぶんにならない')]),
    dict(title='PVC', sub='心室期外収縮', t_title=35.0,
         lines=[(36.0, 'P波がない・QRSが広い・Tが逆向き'),
                (42.0, '休みは、たいてい ちょうど2拍ぶん'),
                (44.0, '1つだけなら、様子を見ることが多い')]),
    dict(title='二段脈', sub='1拍おきにPVC', t_title=47.0,
         lines=[(48.0, 'ふつうの拍とPVCが、交互に来る'),
                (51.0, 'モニター60でも、脈は30のことがある'),
                (55.0, '脈は、自分の指で数える')]),
    dict(title='連発', sub='PVCが続けて2つ', t_title=61.0,
         lines=[(63.0, '2つ続けば、報告'),
                (68.0, '形が何種類もあっても、報告'),
                (70.0, '3つ以上続けば、心室頻拍')]),
    dict(title='報告', sub='3つ以上・症状あり', t_title=73.0,
         lines=[(74.0, '意識・脈・血圧を確認'),
                (77.0, 'K・Mgの値も、いっしょに'),
                (80.0, '脈がなければ、すぐ急変対応')]),
]

SUMMARY_TITLE = '期外収縮の見分け方'
SUMMARY_ROWS = [
    ('PAC', 'P\'あり', 'QRSは細い・休みは2拍ぶんにならない', C_PAC),
    ('PVC', 'P\'なし', 'QRSが広い・休みはたいてい2拍ぶん', C_PVC),
    ('二段脈', '1拍おき', '脈は、指で数える', C_BIG),
    ('連発', '2つ以上', '報告する', C_RUN),
    ('報告', '3つ以上', '心室頻拍。意識・脈・血圧', C_REP),
    ('確認', 'K・Mg', '電解質も、いっしょに', GREEN),
]
SAVE_T = 85.0

NOTE1 = '実際の3分の1の速さ（心拍数60/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


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


_FONTS = {}


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


_TXT = {}


def text_img(s, size, weight, col, max_w=None):
    """文字を RGBA の画像にする（フェードは alpha を掛けて合成する）。"""
    k = (s, size, weight, col, max_w)
    if k in _TXT:
        return _TXT[k]
    sz = size
    while True:
        f = font(sz, weight)
        x0, y0, x1, y1 = f.getbbox(s)
        if max_w is None or (x1 - x0) <= max_w or sz <= 20:
            break
        sz -= 1
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (x1 - x0 + 8, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - x0, 4), s, font=f, fill=col + (255,))
    _TXT[k] = (im, asc)
    return _TXT[k]


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None):
    """cy は文字の高さの中心（大文字の中心あたり）。"""
    if a <= 0.004:
        return
    im, asc = text_img(s, size, weight, col, max_w)
    if a < 0.999:
        im = im.copy()
        al = im.getchannel('A').point(lambda v: int(v*a))
        im.putalpha(al)
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
    n = int(W / PX_MM) + 2
    for i in range(n):
        x = round(i * PX_MM)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,),
               width=2 if i % 5 == 0 else 1)
    m = int(H / PX_MM) + 2
    off = BASE_Y % (5*PX_MM)
    for k in range(-1, m):
        y = round(off + k * PX_MM)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    return im


# --- 波形を描く -----------------------------------------------------------------
WAVE_Y0, WAVE_Y1 = 900, 1560          # 波形を描く帯
SS = 2


def wave_layer(t, base_col, a=1.0):
    """流れる波形（グロー付き）。期外収縮の拍だけ段階の色。"""
    h = WAVE_Y1 - WAVE_Y0
    xs = np.arange(0, W*SS + 1) / SS
    tau = tau_c(t) + (xs - XC) / PX_S
    v = v_at(tau)
    ys = (BASE_Y - WAVE_Y0 - v*MV) * SS
    pts = np.stack([xs*SS, ys], axis=1)

    # 色ごとに区間を分ける
    groups = {}
    cid = np.zeros(len(xs), dtype=int)
    cols = [base_col]
    for lo, hi, c in CWIN:
        m = (tau >= lo) & (tau <= hi)
        if m.any():
            if c not in cols:
                cols.append(c)
            cid[m] = cols.index(c)
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci, c in enumerate(cols):
        sel = cid == ci
        if not sel.any():
            continue
        # 隣り合う区間をつなげるため、境目を1点ずつ広げる
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        core = Image.new('L', (W*SS, h*SS), 0)
        dc = ImageDraw.Draw(core)
        idx = np.where(sel)[0]
        runs = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)
        for r in runs:
            if len(r) < 2:
                continue
            seg = [tuple(p) for p in pts[r]]
            dc.line(seg, fill=255, width=5*SS, joint='curve')
        core = core.resize((W, h), Image.LANCZOS)
        glow = core.filter(ImageFilter.GaussianBlur(9))
        glow2 = core.filter(ImageFilter.GaussianBlur(22))
        gcol = c if c != base_col else base_col
        lay = Image.new('RGBA', (W, h), gcol + (0,))
        g = np.maximum(np.asarray(glow, dtype=np.float32)*0.95,
                       np.asarray(glow2, dtype=np.float32)*0.55)
        lay.putalpha(Image.fromarray(np.clip(g*a, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
        ccol = mix(gcol, (255, 255, 255), 0.62)
        lay2 = Image.new('RGBA', (W, h), ccol + (0,))
        lay2.putalpha(core.point(lambda q: int(q*a)))
        out.alpha_composite(lay2)
    return out


def wave_labels(base, t, a):
    """P・R・S・T の文字（グレー）。P' はその段階の色。"""
    if a <= 0.01:
        return
    lo, hi = tau_c(t) - 0.75, tau_c(t) + 0.75
    for r, k, c in BEATS:
        if not (lo < r < hi):
            continue
        items = []
        if k in 'NA':
            vp = 0.15 if k == 'N' else 0.13
            items += [('P' if k == 'N' else "P'", r - PR, BASE_Y - vp*MV - 52,
                       GREY if k == 'N' else c)]
            items += [('R', r, BASE_Y - 1.0*MV - 42, GREY),
                      ('S', r + 0.028, BASE_Y + 0.20*MV + 42, GREY),
                      ('T', r + 0.29, BASE_Y - 0.27*MV - 50, GREY)]
        for s, tt, y, col in items:
            x = x_of(tt, t)
            if 40 < x < W - 40:
                put(base, s, 40, 700, col, cx=x, cy=y, a=a)


def clock_ticks(base, t, a):
    """洞結節の時計：洞の拍が来る時刻に小さな目盛り。PACで消えた予定は白抜きの丸。"""
    if a <= 0.01:
        return
    d = ImageDraw.Draw(base, 'RGBA')
    y0, y1 = 1508, 1528
    lo, hi = tau_c(t) - 0.75, tau_c(t) + 0.75
    for r in TICKS:
        if lo < r < hi:
            x = x_of(r, t)
            d.line([(x, y0), (x, y1)], fill=WHITE + (int(110*a),), width=3)
    for r in GHOSTS:
        if lo < r < hi:
            x = x_of(r, t)
            al = int(220*a*ramp(t, 24.5, 0.6))
            d.ellipse([x-9, (y0+y1)/2-9, x+9, (y0+y1)/2+9], outline=C_PAC + (al,), width=3)


def pulse_marks(base, t, a):
    """二段脈：PVCの拍の下に「脈 ✕」。"""
    if a <= 0.01:
        return
    lo, hi = tau_c(t) - 0.75, tau_c(t) + 0.75
    for r, k, c in BEATS:
        if k == 'V' and c == C_BIG and lo < r < hi:
            put(base, '脈 ✕', 30, 700, C_BIG, cx=x_of(r, t), cy=1516, a=a)


# --- 上の部分（問い・段階の軸・カード） --------------------------------------
AX_X0, AX_DX, AX_Y = 165.0, 150.2, 420


def stage_pos(t):
    """段階の位置（0〜5、切り替えのあいだは小数）。"""
    p = 0.0
    for i, s in enumerate(STAGE_T[1:], start=1):
        p += ease((t - s) / 0.75)
    return p


def draw_axis(base, t, a):
    if a <= 0.01:
        return
    d = ImageDraw.Draw(base, 'RGBA')
    pos = stage_pos(t)
    xs = [AX_X0 + i*AX_DX for i in range(6)]
    d.line([(xs[0], AX_Y), (xs[-1], AX_Y)], fill=DIM + (int(200*a),), width=3)
    for i in range(5):                     # 通り過ぎた区間を、次の段階の色で塗る
        u = cl(pos - i)
        if u > 0:
            d.line([(xs[i], AX_Y), (xs[i] + (xs[i+1]-xs[i])*u, AX_Y)],
                   fill=STAGE_COL[i+1] + (int(230*a),), width=4)
    for i, x in enumerate(xs):
        near = cl(1 - abs(pos - i))
        r = 6 + 7*near
        col = mix(DIM, STAGE_COL[i], max(near, 1.0 if i < pos - 0.5 else 0.0))
        if near > 0.05:
            for gr, ga in ((r+12, 40), (r+6, 70)):
                d.ellipse([x-gr, AX_Y-gr, x+gr, AX_Y+gr], fill=STAGE_COL[i] + (int(ga*near*a),))
        d.ellipse([x-r, AX_Y-r, x+r, AX_Y+r], fill=col + (int(255*a),))
        lc = mix(DIM, STAGE_COL[i] if i else WHITE, near)
        put(base, AXIS[i], 26, 700, lc, cx=x, cy=467, a=a)


CARD = (150, 525, 930, 950)


def draw_card_box(base, a):
    if a <= 0.01:
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle(CARD, radius=26, fill=CARD_FILL + (int(215*a),),
                        outline=CARD_EDGE + (int(255*a),), width=3)
    base.alpha_composite(lay)


def draw_card_text(base, t, i):
    c = CARDS[i]
    end = STAGE_T[i+1] if i + 1 < len(STAGE_T) else SUMMARY_T
    out = 1 - ramp(t, end, 0.75)
    if out <= 0:
        return
    col = STAGE_COL[i]
    a0 = ramp(t, c['t_title'], 0.5) * out
    put(base, c['title'], 76, 900, col, cx=540, cy=592, a=a0)
    put(base, c['sub'], 40, 400, mix(col, GREY, 0.45) if i else GREY, cx=540, cy=685, a=a0)
    for k, (tl, s) in enumerate(c['lines']):
        put(base, s, 40, 400, (226, 232, 231), cx=540, cy=773 + 65*k,
            a=ramp(t, tl, 0.5) * out, max_w=730)


def draw_title(base, t):
    a = 1 - ramp(t, 3.0, 0.8)
    if a <= 0:
        return
    d = ImageDraw.Draw(base, 'RGBA')
    d.rectangle([494, 317, 586, 320], fill=PURPLE + (int(255*a),))
    put(base, '心電図で気づく', 34, 500, PURPLE, cx=540, cy=375, a=a)
    put(base, '期外収縮', 150, 900, WHITE, cx=540, cy=498, a=a)
    put(base, '見るべきは 5段階', 46, 700, PURPLE, cx=540, cy=642, a=a)
    put(base, 'PAC → PVC → 二段脈 → 連発 → 報告', 36, 500, WHITE, cx=540, cy=720, a=a, max_w=900)


def draw_summary(base, t):
    a = ramp(t, SUMMARY_T + 0.2, 0.6)
    if a <= 0:
        return
    put(base, SUMMARY_TITLE, 70, 800, WHITE, cx=540, cy=371, a=a)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle((150, 520, 930, 1372), radius=26,
                                          fill=CARD_FILL + (int(215*a),),
                                          outline=CARD_EDGE + (int(255*a),), width=3)
    base.alpha_composite(lay)
    for k, (name, metric, desc, col) in enumerate(SUMMARY_ROWS):
        y = 600 + 128*k
        n_im, _ = text_img(name, 54, 900, col)
        m_im, _ = text_img(metric, 36, 500, mix(col, GREY, 0.3))
        tw = n_im.size[0] + 18 + m_im.size[0]
        x0 = 540 - tw/2
        put(base, name, 54, 900, col, x=x0, cy=y, a=a)
        put(base, metric, 36, 500, mix(col, GREY, 0.3), x=x0 + n_im.size[0] + 18, cy=y + 4, a=a)
        put(base, desc, 38, 400, (226, 232, 231), cx=540, cy=y + 60, a=a, max_w=730)
    put(base, '保存して見返してね', 42, 700, GREEN, cx=540, cy=1474, a=ramp(t, SAVE_T, 0.6))


def draw_notes(base, t, a):
    put(base, NOTE1, 24, 400, GREY, x=135, cy=1557, a=0.85*a)
    put(base, NOTE2, 24, 400, GREY, x=135, cy=1585, a=0.85*a)


def watermark(base):
    put(base, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1562 + 14, a=0.42)


_GRID = None


def frame(t):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    a_main = 1 - ramp(t, SUMMARY_T - 0.4, 0.6)          # 本編（まとめで消える）
    # タイトルのあいだは紫、3.5秒から緑へ
    u = ramp(t, 3.3, 1.0)
    base_col = mix(PURPLE, WAVE_GREEN, u)
    if a_main > 0:
        wl = wave_layer(t, base_col, a_main)
        im.alpha_composite(wl, (0, WAVE_Y0))
        wave_labels(im, t, a_main * ramp(t, 4.5, 0.8))
        clock_ticks(im, t, a_main * ramp(t, 13.0, 0.8))
        pulse_marks(im, t, a_main * ramp(t, 51.0, 0.5) * (1 - ramp(t, STAGE_T[4], 0.6)))
        draw_notes(im, t, a_main * ramp(t, 4.5, 0.8))

    draw_title(im, t)
    a_head = ramp(t, 4.0, 0.5) * a_main
    put(im, QUESTION, 52, 800, WHITE, cx=540, cy=329, a=a_head)
    draw_axis(im, t, ramp(t, 5.0, 0.5) * a_main)
    draw_card_box(im, ramp(t, 5.5, 0.5) * a_main)
    for i in range(len(CARDS)):
        if STAGE_T[i] - 0.1 <= t:
            draw_card_text(im, t, i)
    draw_summary(im, t)
    watermark(im)
    return im.convert('RGB')


# --- 検算 ----------------------------------------------------------------------
def check():
    print('拍（R頂点・実際の秒）と、前の拍からの R-R')
    prev = None
    for r, k, c in BEATS:
        if 7.5 <= r <= 27.5:
            rr = '' if prev is None else f'{(r-prev)*1000:5.0f}ms'
            print(f'  {r:6.2f}  {k}  {rr}   画面で中央を通る {r*SLOW:5.1f}秒')
        prev = r
    print('洞結節の時計（PVCに隠れた洞のP）:', [round(x, 2) for x in HIDDEN_P])
    print('PACで消えた洞の予定:', GHOSTS)
    # 休みの検算
    def rr_around(rv):
        i = [b[0] for b in BEATS].index(rv)
        return BEATS[i-1][0], BEATS[i+1][0]
    a, b = rr_around(8.60)
    print(f'PAC: 前の洞→次の洞 = {b-a:.2f}秒（2拍ぶん=2.00 と一致しない）')
    a, b = rr_around(12.30)
    print(f'PVC: 前の洞→次の洞 = {b-a:.2f}秒（ちょうど2拍ぶん）')
    run = [0.42, 0.42]
    print(f'3連のPVC: {60/run[0]:.0f}/分（100/分を超える → 心室頻拍の条件）')
    # PVCのQRS幅（0.05mV を超える範囲）
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = qrs_t_pvc(tt)
    m = (np.abs(v) > 0.05) & (tt < 0.11)       # ST-Tに入る前まで
    on, off = tt[m].min(), tt[m].max()
    print(f'PVCのQRS幅 ≈ {(off-on)*1000:.0f}ms（120ms以上）')
    vn = qrs_t_normal(tt)
    mn = (np.abs(vn) > 0.05) & (tt < 0.1)
    print(f'ふつうのQRS幅 ≈ {(tt[mn].max()-tt[mn].min())*1000:.0f}ms（120ms未満）')


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
    """R が画面の中央を通るときに「ピッ」。PVC は少し低い音。"""
    n = int(DUR * sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, c in BEATS:
        ts = r * SLOW
        if not (4.5 <= ts <= SUMMARY_T - 0.5):
            continue
        f = 720.0 if k == 'V' else 960.0
        L = int(0.09 * sr)
        tt = np.arange(L) / sr
        env = np.minimum(1, tt/0.004) * np.exp(-tt/0.05)
        s = 0.22 * env * np.sin(2*np.pi*f*tt)
        i = int(ts * sr)
        a[i:i+L] += s[:max(0, min(L, n-i))]
    pcm = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel17_ectopy.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    o = ap.parse_args()
    if o.check:
        check(); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    total = int(round(DUR * o.fps))
    k = o.jobs
    step = math.ceil(total / k)
    tmp = os.path.join(os.path.dirname(o.out), 'parts')
    os.makedirs(tmp, exist_ok=True)
    jobs = [(i, min(total, i+step), o.fps, os.path.join(tmp, f'p{j:02d}.mp4'))
            for j, i in enumerate(range(0, total, step))]
    with Pool(k) as pool:
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
