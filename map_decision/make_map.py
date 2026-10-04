"""心電図 見分けマップ（1枚で動く保存版）。

モニター（II誘導）の波形を、質問をたどって名前までたどり着く「見分けマップ」にする。
上で例の波形が流れ、光る点がマップの質問を1つずつたどり、答え（と、くわしい回：第◯弾）にたどり着く。
例を6つ見せたあと、マップ全体を光らせて「保存してね」。最後は冒頭の画面に戻ってループする。

マップの中身は、LITFL ECG Library と、これまでのシリーズ（第16〜21弾）をもとにした入口の一例（例外あり）。
ほかの投稿の図を写したものではない（構成・言葉は独自）。

使い方:
    python3 make_map.py              # 書き出し（out/map_decision.mp4）
    python3 make_map.py --still 12   # 1コマだけ
    python3 make_map.py --thumb      # サムネイル（透かしなし）
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
FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (88, 100, 100)
CARD_FILL = (9, 19, 16)
CARD_EDGE = (60, 78, 72)
WAVE_GREEN = (40, 214, 128)
YEL = (255, 206, 72)
C_RED = (255, 92, 112)
C_ORANGE = (255, 152, 72)
C_YEL = (255, 212, 90)
C_BLUE = (110, 200, 255)
C_GREEN = (110, 226, 150)
C_Q = (226, 232, 231)            # 質問の文字
WATERMARK = '@nurse_polarbearden'

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




# --- 波形の部品（秒、mV） ------------------------------------------------------------
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


def qrs_pvc(t):
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def band_noise(t, L, f_lo, f_hi, amp, seed):
    rs = np.random.RandomState(seed)
    ks = np.arange(max(1, int(np.ceil(f_lo*L))), int(f_hi*L) + 1)
    a = rs.normal(0, 1, len(ks)); ph = rs.uniform(0, 2*np.pi, len(ks))
    out = np.zeros_like(t)
    for k, ak, pk in zip(ks, a, ph):
        out += ak*np.sin(2*np.pi*k*t/L + pk)
    return out * amp / np.sqrt(np.sum(a**2)/2 + 1e-9)


def beats_wave(t, beats):
    """beats: [(時刻, 種類)]。'N' 洞調律、'Q' P波なしの細いQRS、'V' 幅の広いQRS、'P' P波だけ"""
    v = np.zeros_like(t)
    for r, k in beats:
        m = np.abs(t - r) < 0.8
        if not m.any():
            continue
        tau = t[m] - r
        if k in ('N', 'Q'):
            v[m] += qrs_normal(tau)
        if k == 'V':
            v[m] += qrs_pvc(tau)
        if k == 'N':
            v[m] += p_sinus(tau + 0.16)
        if k == 'P':
            v[m] += p_sinus(tau)
    return v


def periodic(ev, L, t0, t1):
    out = []
    for k in range(int(math.floor(t0/L)) - 1, int(math.ceil(t1/L)) + 2):
        out += [(k*L + r, kd) for r, kd in ev]
    return out


# 例の波形：周期 L でくり返す
_AF_RR = [0.62, 0.95, 0.48, 0.80, 1.10, 0.55, 0.74, 0.90]
_AF_T = np.cumsum([0] + _AF_RR[:-1]).tolist()
RHYTHMS = {
    'af': dict(ev=[(t, 'Q') for t in _AF_T], L=sum(_AF_RR), f=True),        # 心房細動
    'pvc': dict(ev=[(0, 'N'), (0.8, 'N'), (1.28, 'V'), (2.4, 'N')], L=3.2),  # 期外収縮（PVC）
    'chb': dict(ev=[(k*0.6, 'P') for k in range(10)] + [(0.25 + k*1.5, 'Q') for k in range(4)], L=6.0),  # 完全房室ブロック
    'psvt': dict(ev=[(k*1/3, 'Q') for k in range(9)], L=3.0),                # PSVT（細く速い）
    'vf': dict(ev=[], L=4.0, vf=True),                                         # 心室細動
    'nsr': dict(ev=[(k*0.8, 'N') for k in range(5)], L=4.0),                 # 洞調律
}


def rhythm_wave(key, t):
    R = RHYTHMS[key]
    v = beats_wave(t, periodic(R['ev'], R['L'], t[0], t[-1]))
    if R.get('f'):
        v += band_noise(t, R['L'], 5.0, 8.0, 0.035, 5)
    if R.get('vf'):
        v += band_noise(t, R['L'], 3.0, 9.0, 0.40, 9)
    return v


def rhythm_r_times(key, t0, t1):
    R = RHYTHMS[key]
    return [r for r, k in periodic(R['ev'], R['L'], t0, t1) if k in ('N', 'Q', 'V') and t0 <= r < t1]


# --- マップ（行ごと） -------------------------------------------------------------------
# depth：字下げの段、ans：前の質問への答え、text：質問か名前、kind：'q' 質問 / 't' 名前、reel：くわしい回
ROWS = [
    dict(d=0, ans='', text='QRSはある？', kind='q'),
    dict(d=1, ans='いいえ', text='揺れはある？', kind='q'),
    dict(d=2, ans='ある', text='心室細動（VF）', kind='t', col=C_RED, reel='第21弾'),
    dict(d=2, ans='ない', text='心静止', kind='t', col=C_BLUE, reel='第21弾'),
    dict(d=1, ans='はい', text='R-Rは規則的？', kind='q'),
    dict(d=2, ans='不規則', text='P波はある？', kind='q'),
    dict(d=3, ans='ない', text='QRSの幅は？', kind='q'),
    dict(d=4, ans='狭い', text='心房細動', kind='t', col=C_ORANGE, reel=''),
    dict(d=4, ans='広い', text='多形性VT・トルサード', kind='t', col=C_RED, reel='第21弾'),
    dict(d=3, ans='ある', text='早い1拍がある？', kind='q'),
    dict(d=4, ans='ある', text='期外収縮', kind='t', col=C_YEL, reel='第17弾'),
    dict(d=4, ans='ぬける', text='2度房室ブロック・洞停止', kind='t', col=C_BLUE, reel='第18弾'),
    dict(d=2, ans='規則的', text='心拍数は？', kind='q'),
    dict(d=3, ans='60未満', text='P波のあと、毎回QRS？', kind='q'),
    dict(d=4, ans='はい', text='洞徐脈', kind='t', col=C_BLUE, reel='第18弾'),
    dict(d=4, ans='いいえ', text='2:1・完全房室ブロック', kind='t', col=C_BLUE, reel='第18弾'),
    dict(d=3, ans='60〜100', text='洞調律', kind='t', col=C_GREEN, reel=''),
    dict(d=3, ans='100以上', text='QRSの幅は？', kind='q'),
    dict(d=4, ans='狭い', text='洞頻脈・PSVT・心房粗動', kind='t', col=C_ORANGE, reel='第16弾'),
    dict(d=4, ans='広い', text='心室頻拍（VT）', kind='t', col=C_RED, reel='第21弾'),
]
for _i, _r in enumerate(ROWS):                       # 親の行
    _r['parent'] = None
    for _j in range(_i - 1, -1, -1):
        if ROWS[_j]['d'] == _r['d'] - 1:
            _r['parent'] = _j
            break

TREE_Y0, ROW_H = 646, 46
X0, IND = 150, 40
SZ_Q, SZ_T, SZ_A = 29, 30, 22


def row_y(i):
    return TREE_Y0 + i*ROW_H


def row_x(i):
    return X0 + ROWS[i]['d']*IND


def ans_w(i):
    s = ROWS[i]['ans']
    return (text_img(s, SZ_A, 700, YEL)[0].size[0] - 8 + 12) if s else 0


def anchor(i):
    """その行の、線がつながる点（字下げの位置の中心）"""
    return (row_x(i), row_y(i))


def path_points(rows):
    """たどる行の列 → 光る点が通る折れ線"""
    pts = [anchor(rows[0])]
    for a, b in zip(rows, rows[1:]):
        xa, ya = row_x(a) + 8, row_y(a)
        xb, yb = row_x(b), row_y(b)
        pts += [(xa, ya + 16), (xa, yb), (xb - 6, yb)]
    return pts


# --- 例（6つ） ------------------------------------------------------------------------
CASES = [
    dict(key='af', path=[0, 4, 5, 6, 7], name='心房細動'),
    dict(key='pvc', path=[0, 4, 5, 9, 10], name='期外収縮（PVC）'),
    dict(key='chb', path=[0, 4, 12, 13, 15], name='完全房室ブロック'),
    dict(key='psvt', path=[0, 4, 12, 17, 18], name='PSVT'),
    dict(key='vf', path=[0, 1, 2], name='心室細動（VF）'),
    dict(key='nsr', path=[0, 4, 12, 16], name='洞調律'),
]
T_INTRO = 3.0
CASE_D = 6.2
STEP = 0.55                    # 1つの質問から次へ進む時間
T_OUTRO = T_INTRO + len(CASES)*CASE_D
OUTRO_D = 6.0
LOOP_FADE = 0.7
DUR = T_OUTRO + OUTRO_D

# --- 画面の部品 -------------------------------------------------------------------------
PANEL = (130, 404, 950, 604)          # 上の波形の枠
P_BASE = 530                          # 波形の基線
P_PXS, P_MV = 300.0, 62.0             # 1秒 = 300px、1mV = 62px


def grid():
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = 31.5
    for i in range(int(W/pm) + 2):
        x = round(i*pm)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,), width=2 if i % 5 == 0 else 1)
    for k in range(int(H/pm) + 2):
        y = round(k*pm)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,), width=2 if k % 5 == 0 else 1)
    return im


def case_at(t):
    """(例の番号, 例の中の時刻) / 冒頭は (-1, t)、最後は (len, t)"""
    if t < T_INTRO:
        return -1, t
    if t >= T_OUTRO:
        return len(CASES), t - T_OUTRO
    k = int((t - T_INTRO) // CASE_D)
    return k, t - T_INTRO - k*CASE_D


def panel(im, t):
    k, u = case_at(t)
    key = 'nsr' if k < 0 or k >= len(CASES) else CASES[k]['key']
    x0, y0, x1, y1 = PANEL
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle(PANEL, radius=18, fill=CARD_FILL + (215,), outline=CARD_EDGE + (255,), width=2)
    im.alpha_composite(lay)
    xs = np.arange(x0 + 14, x1 - 14, 0.5)
    tt = t + (xs - x1) / P_PXS
    v = rhythm_wave(key, tt)
    a = 1.0
    if 0 <= k < len(CASES):
        a = ramp(u, 0.0, 0.35) * (1 - ramp(u, CASE_D - 0.3, 0.3))
    col = WAVE_GREEN
    if 0 <= k < len(CASES) and u >= reveal_t(k):
        col = mix(WAVE_GREEN, ROWS[CASES[k]['path'][-1]]['col'], ramp(u, reveal_t(k), 0.4))
    ys = P_BASE - v*P_MV
    edge = np.clip(np.minimum(xs - (x0 + 14), (x1 - 14) - xs)/30, 0, 1)
    ys = P_BASE + (ys - P_BASE)*edge
    im.alpha_composite(glow_line((W, H), [list(zip(xs, ys))], col, 3.6, a, blur=(6, 14)))
    # 枠の上のラベル
    if 0 <= k < len(CASES):
        rv = reveal_t(k)
        put(im, 'この波形は？', 30, 800, WHITE, x=x0 + 22, cy=y0 + 30, a=a*(1 - ramp(u, rv, 0.3)))
        put(im, f"→ {CASES[k]['name']}", 32, 900, ROWS[CASES[k]['path'][-1]]['col'], x=x0 + 22, cy=y0 + 30,
            a=a*ramp(u, rv, 0.3))
    elif k < 0:
        put(im, '質問をたどると、名前にたどり着く', 28, 700, WHITE, x=x0 + 22, cy=y0 + 30, a=ramp(t, 0.4, 0.4))
    else:
        put(im, '保存して、迷ったら見返してね', 30, 800, GREEN_SAVE, x=x0 + 22, cy=y0 + 30, a=ramp(u, 0.2, 0.4))


GREEN_SAVE = (130, 232, 172)


def reveal_t(k):
    return 0.8 + (len(CASES[k]['path']) - 1)*STEP + 0.15


def tree_state(t):
    """各行の明るさ（0〜1）、たどった行、光る点の位置、答えの行"""
    k, u = case_at(t)
    n = len(ROWS)
    if k < 0:                                            # 冒頭：上から順に出る
        bright = [0.55*ramp(t, 0.5 + i*0.07, 0.25) for i in range(n)]
        return bright, [], None, None, 0.0
    if k >= len(CASES):                                  # 最後：全部明るく
        b = ramp(u, 0.0, 0.6)
        return [0.55 + 0.45*b]*n, [], None, 'all', b
    c = CASES[k]
    path = c['path']
    prog = (u - 0.8) / STEP                              # 何段目まで進んだか
    reached = [r for j, r in enumerate(path) if prog >= j - 0.001]
    dim = 0.30 + 0.25*(1 - ramp(u, 0.0, 0.5))           # たどらない行はうすく
    bright = [dim]*n
    for r in reached:
        bright[r] = 1.0
    dot = None
    if 0 <= prog < len(path) - 1:                        # 次の行へ移動中
        j = int(prog); f = ease(prog - j)
        pts = path_points(path[j:j+2])
        seg = np.r_[0, np.cumsum([math.hypot(x1 - x0, y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])])]
        s = f*seg[-1]
        q = int(np.searchsorted(seg, s, side='right') - 1); q = min(q, len(pts) - 2)
        w = (s - seg[q]) / max(1e-6, seg[q+1] - seg[q])
        dot = (pts[q][0] + (pts[q+1][0] - pts[q][0])*w, pts[q][1] + (pts[q+1][1] - pts[q][1])*w)
    elif prog < 0:
        dot = anchor(path[0]) if u > 0.45 else None
    final = path[-1] if u >= reveal_t(k) else None
    return bright, reached, dot, final, ramp(u, reveal_t(k), 0.35) if final is not None else 0.0


def draw_tree(im, t):
    bright, reached, dot, final, fa = tree_state(t)
    k, u = case_at(t)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    # 線（親 → 子）
    for i, r in enumerate(ROWS):
        p = r['parent']
        if p is None:
            continue
        xa, ya = row_x(p) + 8, row_y(p)
        xb, yb = row_x(i), row_y(i)
        a = min(bright[i], bright[p]) * 0.8
        d.line([(xa, ya + 16), (xa, yb), (xb - 6, yb)], fill=CARD_EDGE + (int(255*a),), width=2)
    im.alpha_composite(lay)
    # たどった線（光る）
    if reached and len(reached) >= 2:
        im.alpha_composite(glow_line((W, H), [path_points(reached)], YEL, 3.0, 1.0, blur=(5, 12)))
    # 文字
    for i, r in enumerate(ROWS):
        a = bright[i]
        if a <= 0.01:
            continue
        x = row_x(i)
        y = row_y(i)
        if r['ans']:
            on = i in reached or final == 'all'
            put(im, r['ans'], SZ_A, 700, YEL if on else (200, 180, 120), x=x, cy=y + 1, a=a)
            x += ans_w(i)
        if r['kind'] == 'q':
            put(im, r['text'], SZ_Q, 700, C_Q, x=x, cy=y, a=a)
        else:
            col = r['col'] if (final == i or final == 'all' or i in reached) else (190, 198, 198)
            size = SZ_T
            put(im, '■', 16, 900, r['col'], x=x - 2, cy=y + 1, a=a)
            x += 22
            put(im, r['text'], size, 900, col, x=x, cy=y, a=a)
            if r['reel']:
                tw = text_img(r['text'], size, 900, col)[0].size[0] - 8
                ra = a * (0.75 if final not in (i, 'all') else 1.0)
                put(im, r['reel'], 19, 700, (176, 186, 186), x=x + tw + 12, cy=y + 3, a=ra)
    # 答えの行を強調（枠）
    if isinstance(final, int):
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        y = row_y(final)
        pulse = 0.6 + 0.4*math.sin((u - reveal_t(k))*6.0)**2
        d.rounded_rectangle((row_x(final) - 14, y - 22, 950, y + 22), radius=12,
                            outline=ROWS[final]['col'] + (int(255*fa*pulse),), width=3)
        im.alpha_composite(lay)
    # 光る点
    if dot is not None:
        x, y = dot
        im.alpha_composite(glow_line((W, H), [[(x - 0.5, y), (x + 0.5, y)]], YEL, 12, 1.0, blur=(6, 16)))


_GRID = None


def notes(im):
    """左下の注意書き（右下の透かしと重ねない：x 600 まで）"""
    put(im, '※モニター（II誘導）で見る入口の一例。例外あり', 20, 400, GREY, x=135, cy=1566, max_w=470)
    put(im, '※幅の広い速い頻拍は、迷ったらVT（LITFL）', 20, 400, GREY, x=135, cy=1592, max_w=470)


def frame(t):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    tl = t
    a_loop = ramp(t, DUR - LOOP_FADE, LOOP_FADE)        # 最後は冒頭の画面へ
    if a_loop > 0:
        tl = t                                            # 下でまぜる
    im = _GRID.copy()
    # 見出し
    put(im, '心電図で気づく', 30, 700, (118, 226, 150), cx=540, cy=300)
    parts = [('モニター心電図', 52, WHITE), (' 見分けマップ', 52, YEL)]
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    x = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, asc) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=x, cy=362)
        x += a_.size[0] - 8
    panel(im, tl)
    draw_tree(im, tl)
    notes(im)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    out = im.convert('RGB')
    if a_loop > 0:
        start = frame0()
        out = Image.blend(out, start, a_loop)
    return out


_F0 = None


def frame0():
    global _F0
    if _F0 is None:
        _F0 = frame(0.0)
    return _F0


def thumbnail():
    """サムネイル（透かしなし）：マップ全体が光った状態"""
    global _GRID
    if _GRID is None:
        _GRID = grid()
    t = T_OUTRO + 1.5
    im = _GRID.copy()
    put(im, '心電図で気づく', 30, 700, (118, 226, 150), cx=540, cy=300)
    parts = [('モニター心電図', 52, WHITE), (' 見分けマップ', 52, YEL)]
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    x = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, asc) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=x, cy=362)
        x += a_.size[0] - 8
    panel(im, t)
    draw_tree(im, t)
    notes(im)
    return im.convert('RGB')


# --- 書き出し ------------------------------------------------------------------------
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


def sounds(path, sr=44100):
    """上の波形の R が右端から少し入ったところで「ピッ」。答えが出るときに少し高い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    def tone(ts, f, amp=0.2, dur=0.08, dec=0.045):
        L = int(dur*sr); tt = np.arange(L)/sr
        s = amp*np.minimum(1, tt/0.004)*np.exp(-tt/dec)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr)
        if 0 <= j < n:
            a[j:j+L] += s[:max(0, min(L, n - j))]
    lag = (PANEL[2] - 14 - 540) / P_PXS                 # 画面の中央を通るとき
    for k, c in enumerate(CASES):
        t0 = T_INTRO + k*CASE_D
        for r in rhythm_r_times(c['key'], t0 - lag, t0 + CASE_D - lag - 0.3):
            ts = r + lag
            if t0 + 0.3 <= ts < t0 + CASE_D - 0.3:
                tone(ts, 960.0 if c['key'] != 'vf' else 720.0, 0.12)
        for j in range(1, len(c['path'])):
            tone(t0 + 0.8 + j*STEP, 1320.0, 0.06, 0.05, 0.03)
        tone(t0 + reveal_t(k), 1560.0, 0.12, 0.12, 0.06)
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'map_decision.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true')
    o = ap.parse_args()
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.thumb:
        p = os.path.join(os.path.dirname(o.out), 'thumb_map_decision.png')
        thumbnail().save(p); print(p); return
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'map_decision_hq.mp4')
    frame0()
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
    wav = os.path.join(tmp, 'sounds.wav')
    sounds(wav)
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    '-movflags', '+faststart', o.out], check=True)
    print(o.out)


if __name__ == '__main__':
    main()
