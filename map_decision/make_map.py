"""モニター心電図 見分けマップ（1枚で動く保存版。2枚組）。

① 規則的な波形 ／ ② 不規則な波形・QRSがない。
モニター（II誘導）の波形を、質問をたどって名前までたどり着く「見分けマップ」にする。
上で例の波形が流れ、光る点がマップの質問を1つずつたどり、答えにたどり着く。
例を6つ見せたあと、マップ全体を光らせて「保存してね」。最後は冒頭の画面に戻ってループする。
ナレーションは付けない（2026-10-04 決定）。音はモニター音と、質問をたどる音だけ。

マップの中身は LITFL ECG Library をもとにした入口の一例（例外あり）。ほかの投稿の図を写したものではない（構成・言葉は独自）。

使い方:
    python3 make_map.py --map 1              # 書き出し（out/map1.mp4）
    python3 make_map.py --map 2 --still 12   # 1コマだけ
    python3 make_map.py --map 1 --thumb      # サムネイル（透かしなし）
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


def qrs_wide(t):                  # 幅の広いQRS（補充調律）
    return (0.70*_ga(t, 0.0, 0.030, 0.034) - 0.18*_g(t, 0.085, 0.022)
            - 0.32*_ga(t, 0.34, 0.075, 0.055))


def qrs_paced(t):                 # 右室ペーシング（II誘導）：下向きの幅の広いQRS、上向きのT
    return (-0.78*_ga(t, 0.0, 0.030, 0.036) + 0.08*_g(t, 0.072, 0.016)
            + 0.32*_ga(t, 0.30, 0.075, 0.055))


def beats_wave(t, beats):
    """beats: [(時刻, 種類[, PR])]。'N' P＋細いQRS、'Q' P波なしの細いQRS、'V' PVC、'W' 幅の広いQRS、
    'P' P波だけ、'S' ペーシング（スパイク＋幅の広いQRS）、'A' 早いP'＋細いQRS"""
    v = np.zeros_like(t)
    for b in beats:
        r, k = b[0], b[1]
        pr = b[2] if len(b) > 2 else 0.16
        m = np.abs(t - r) < 0.9
        if not m.any():
            continue
        tau = t[m] - r
        if k in ('N', 'Q', 'A'):
            v[m] += qrs_normal(tau)
        if k == 'N':
            v[m] += p_sinus(tau + pr)
        if k == 'A':
            v[m] += 0.13*_g(tau + pr, 0.0, 0.015) - 0.04*_g(tau + pr, 0.032, 0.013)
        if k == 'V':
            v[m] += qrs_pvc(tau)
        if k == 'W':
            v[m] += qrs_wide(tau)
        if k == 'P':
            v[m] += p_sinus(tau)
        if k == 'S':
            v[m] += qrs_paced(tau) + 1.0*_g(tau, -0.075, 0.0022)
    return v


def periodic(ev, L, t0, t1):
    out = []
    for k in range(int(math.floor(t0/L)) - 1, int(math.ceil(t1/L)) + 2):
        out += [(k*L + e[0],) + tuple(e[1:]) for e in ev]
    return out


# 例の波形：周期 L でくり返す
_AF_RR = [0.62, 0.95, 0.48, 0.80, 1.10, 0.55, 0.74, 0.90]
_AF_T = np.cumsum([0] + _AF_RR[:-1]).tolist()
_SA_RR = [0.72, 0.68, 0.70, 0.78, 0.90, 1.00, 1.02, 0.95, 0.85]            # 洞性不整脈（呼吸でゆれる）
_SA_T = np.cumsum([0] + _SA_RR[:-1]).tolist()
RHYTHMS = {
    'nsr': dict(ev=[(k*0.8, 'N') for k in range(5)], L=4.0),                         # 洞調律
    'av1': dict(ev=[(k*0.8, 'N', 0.30) for k in range(5)], L=4.0),                   # 1度房室ブロック
    'chb': dict(ev=[(k*0.6, 'P') for k in range(10)] + [(0.25 + k*1.5, 'Q') for k in range(4)], L=6.0),
    'flut': dict(ev=[(k*0.4, 'Q') for k in range(10)], L=4.0, flut=True),           # 心房粗動（2:1）
    'vt': dict(ev=[(k*0.32, 'V') for k in range(15)], L=4.8),                        # 心室頻拍
    'pace': dict(ev=[(k*1.0, 'S') for k in range(4)], L=4.0),                        # ペースメーカー調律
    'af': dict(ev=[(t, 'Q') for t in _AF_T], L=sum(_AF_RR), f=True),                # 心房細動
    'pvc': dict(ev=[(0, 'N'), (0.8, 'N'), (1.28, 'V'), (2.4, 'N')], L=3.2),          # 心室期外収縮
    'wk': dict(ev=[(0.18, 'N', 0.18), (1.08, 'N', 0.28), (1.93, 'N', 0.33), (2.4, 'P')], L=3.2),  # ウェンケバッハ
    'sarr': dict(ev=[(t, 'N') for t in _SA_T], L=sum(_SA_RR)),                      # 洞性不整脈
    'vf': dict(ev=[], L=4.0, vf=True),                                                 # 心室細動
    'pasys': dict(ev=[(k*0.8, 'P') for k in range(5)], L=4.0),                       # P波だけ
}


def flutter_waves(t, L):
    """心房粗動の鋸歯状波（F波）：300/分、II誘導で下向きの鋸歯（ゆっくり下がって、すっと戻る）"""
    ph = np.mod(t, 0.2) / 0.2
    saw = np.where(ph < 0.78, -ph/0.78, -(1 - ph)/0.22)
    return 0.16*(saw + 0.5)


def rhythm_wave(key, t):
    R = RHYTHMS[key]
    v = beats_wave(t, periodic(R['ev'], R['L'], t[0], t[-1]))
    if R.get('f'):
        v += band_noise(t, R['L'], 5.0, 8.0, 0.035, 5)
    if R.get('vf'):
        v += band_noise(t, R['L'], 3.0, 9.0, 0.40, 9)
    if R.get('flut'):
        v += flutter_waves(t, R['L'])
    return v


def rhythm_r_times(key, t0, t1):
    R = RHYTHMS[key]
    return [b[0] for b in periodic(R['ev'], R['L'], t0, t1) if b[1] in ('N', 'Q', 'V', 'W', 'S', 'A') and t0 <= b[0] < t1]


# --- マップ（行ごと） -------------------------------------------------------------------
# d：字下げの段、ans：前の質問への答え、text：質問か名前、kind：'q' 質問 / 't' 名前
def T(d, ans, text, col):
    return dict(d=d, ans=ans, text=text, kind='t', col=col)


def Q(d, ans, text):
    return dict(d=d, ans=ans, text=text, kind='q')


MAPS = {
    1: dict(
        title=('見分けマップ①', ' 規則的な波形'),
        rows=[
            Q(0, '', 'ペースメーカーのスパイクがある？'),
            T(1, 'ある', 'ペースメーカー調律', C_BLUE),
            Q(1, 'ない', '心拍数は？'),
            Q(2, '60未満', 'P波はある？'),
            Q(3, 'ない', 'QRSの幅は？'),
            T(4, '狭い', '接合部補充調律', C_BLUE),
            T(4, '広い', '心室補充調律', C_RED),
            Q(3, 'ある', 'P波のあと、毎回QRS？'),
            T(4, 'はい', '洞徐脈', C_BLUE),
            Q(4, 'いいえ', 'PとQRSの関係は？'),
            T(5, '一定', '2:1・高度房室ブロック', C_RED),
            T(5, '別々', '完全房室ブロック', C_RED),
            Q(2, '60〜100', 'PRは？'),
            T(3, '0.2秒以下', '洞調律', C_GREEN),
            T(3, '0.2秒より長い', '1度房室ブロック', C_YEL),
            Q(2, '100以上', 'QRSの幅は？'),
            Q(3, '狭い', 'P波は？'),
            T(4, 'ふつう', '洞頻脈', C_GREEN),
            T(4, 'のこぎり状', '心房粗動', C_ORANGE),
            T(4, '見えない', 'PSVT', C_ORANGE),
            T(3, '広い', '心室頻拍（VT）', C_RED),
        ],
        cases=[
            dict(key='nsr', name='洞調律', end='洞調律'),
            dict(key='av1', name='1度房室ブロック', end='1度房室ブロック'),
            dict(key='chb', name='完全房室ブロック', end='完全房室ブロック'),
            dict(key='flut', name='心房粗動（2:1）', end='心房粗動'),
            dict(key='vt', name='心室頻拍（VT）', end='心室頻拍（VT）'),
            dict(key='pace', name='ペースメーカー調律', end='ペースメーカー調律'),
        ],
        notes=['※モニター（II誘導）で見る入口の一例。例外あり', '※幅の広い速い頻拍は、迷ったらVT（LITFL）'],
    ),
    2: dict(
        title=('見分けマップ②', ' 不規則・QRSなし'),
        rows=[
            Q(0, '', 'QRSはある？'),
            Q(1, 'ない', '何が見える？'),
            T(2, 'バラバラな揺れ', '心室細動（VF）', C_RED),
            T(2, 'P波だけ', 'P波だけの心静止', C_RED),
            T(2, 'まっすぐ', '心静止（電極も確認）', C_RED),
            Q(1, 'ある', 'どう不規則？'),
            Q(2, '全部バラバラ', 'QRSの幅は？'),
            T(3, '狭い', '心房細動', C_ORANGE),
            T(3, '広い', '心房細動＋脚ブロック・多形性VT', C_RED),
            Q(2, '早い1拍', '早い拍は？'),
            T(3, "狭い・前にP'", '心房期外収縮（PAC）', C_BLUE),
            T(3, '狭い・Pなし', '接合部期外収縮（PJC）', C_BLUE),
            T(3, '広い', '心室期外収縮（PVC）', C_YEL),
            Q(2, 'ときどき抜ける', '抜けるのは？'),
            T(3, 'P波ごと', '洞停止・洞房ブロック', C_BLUE),
            Q(3, 'QRSだけ', 'PRは？'),
            T(4, '伸びて抜ける', 'ウェンケバッハ', C_YEL),
            T(4, '一定で突然', 'モビッツII型', C_RED),
            T(2, '呼吸でゆれる', '洞性不整脈', C_GREEN),
        ],
        cases=[
            dict(key='af', name='心房細動', end='心房細動'),
            dict(key='pvc', name='心室期外収縮（PVC）', end='心室期外収縮（PVC）'),
            dict(key='wk', name='ウェンケバッハ', end='ウェンケバッハ'),
            dict(key='sarr', name='洞性不整脈', end='洞性不整脈'),
            dict(key='vf', name='心室細動（VF）', end='心室細動（VF）'),
            dict(key='pasys', name='P波だけの心静止', end='P波だけの心静止'),
        ],
        notes=['※波形があっても、脈がなければPEA。まず患者さん', '※モニター（II誘導）で見る入口の一例。例外あり'],
    ),
}
MAP = int(os.environ.get('MAP_NO', '1'))
CFG = MAPS[MAP]
ROWS = CFG['rows']
for _i, _r in enumerate(ROWS):                       # 親の行
    _r['parent'] = None
    for _j in range(_i - 1, -1, -1):
        if ROWS[_j]['d'] == _r['d'] - 1:
            _r['parent'] = _j
            break

TREE_Y0 = 638
ROW_H = 44 if len(ROWS) > 19 else 48           # 行が少ないマップは、行の間を少し広げる
X0, IND = 146, 20                  # IND：親の質問の書き出しから、子の行までの字下げ
SZ_Q, SZ_T, SZ_A = 29, 30, 22


def row_y(i):
    return TREE_Y0 + i*ROW_H


C_LINK = (98, 124, 116)                 # 質問から答えへの線（背景のマス目より明るく）
_ANS_W = {}


def ans_w(i):
    if i not in _ANS_W:
        s = ROWS[i]['ans']
        _ANS_W[i] = (text_img(s, SZ_A, 700, YEL)[0].size[0] - 8 + 12) if s else 0
    return _ANS_W[i]


def q_x(i):
    """その行の質問（または名前）の書き出し位置（答えのうしろ）"""
    return row_x(i) + ans_w(i)


def row_x(i):
    """行の書き出し位置。子の行は、親の「質問」の書き出しから IND 右へ（答えの字の下からは線を出さない）"""
    p = ROWS[i]['parent']
    return X0 if p is None else q_x(p) + IND


def stem_x(i):
    """質問の行から下へ出る線の x（質問の字の書き出しの少し右）"""
    return q_x(i) + 8


def link(p, i):
    """親の質問 p → 子の行 i の線（質問の下から下ろして、子の答えの手前で止める）"""
    xa, ya = stem_x(p), row_y(p)
    xb, yb = row_x(i), row_y(i)
    return [(xa, ya + 16), (xa, yb), (xb - 6, yb)]


def anchor(i):
    """光る点の出発点：質問の下（線が出るところ）"""
    return (stem_x(i), row_y(i) + 16)


def path_runs(rows):
    """たどる行の列 → 光る線（質問 → 答え ごとに別の線。答えで切れて、次はその行の質問の下から出る）"""
    return [link(a, b) for a, b in zip(rows, rows[1:])]


# --- 例（6つ）：答えの行から、親をたどって道すじを作る ---------------------------------
def _path_to(name):
    i = next(j for j, r in enumerate(ROWS) if r['kind'] == 't' and r['text'] == name)
    out = [i]
    while ROWS[out[-1]]['parent'] is not None:
        out.append(ROWS[out[-1]]['parent'])
    return out[::-1]


CASES = [dict(c, path=_path_to(c['end'])) for c in CFG['cases']]
T_INTRO = 3.0
CASE_D = 6.2
STEP = 0.55                    # 1つの質問から次へ進む時間
T_OUTRO = T_INTRO + len(CASES)*CASE_D
OUTRO_D = 6.0
LOOP_FADE = 0.7
DUR = T_OUTRO + OUTRO_D

# --- 画面の部品 -------------------------------------------------------------------------
PANEL = (130, 418, 950, 594)          # 上の波形の枠（見出しとのあいだを約40px空ける）
P_BASE = 532                          # 波形の基線
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
        pts = link(path[j], path[j+1])
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
        a = min(bright[i], bright[p]) * 0.8
        d.line(link(p, i), fill=C_LINK + (int(255*a),), width=3)
    im.alpha_composite(lay)
    # たどった線（光る）
    if reached and len(reached) >= 2:
        im.alpha_composite(glow_line((W, H), path_runs(reached), YEL, 3.0, 1.0, blur=(5, 12)))
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
    put(im, CFG['notes'][0], 20, 400, GREY, x=135, cy=1566, max_w=470)
    put(im, CFG['notes'][1], 20, 400, GREY, x=135, cy=1592, max_w=470)


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
    put(im, 'モニター心電図', 30, 700, (118, 226, 150), cx=540, cy=298)
    parts = [(CFG['title'][0], 52, YEL), (CFG['title'][1], 52, WHITE)]
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    x = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, asc) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=x, cy=350)
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
    put(im, 'モニター心電図', 30, 700, (118, 226, 150), cx=540, cy=298)
    parts = [(CFG['title'][0], 52, YEL), (CFG['title'][1], 52, WHITE)]
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    x = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, asc) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=x, cy=350)
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', f'map{MAP}.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true')
    ap.add_argument('--map', type=int, default=MAP, help='1：規則的な波形 / 2：不規則・QRSなし（環境変数 MAP_NO でも）')
    o = ap.parse_args()
    if o.map != MAP:                                    # マップを切りかえて、自分をもう一度動かす
        env = dict(os.environ, MAP_NO=str(o.map))
        import sys
        raise SystemExit(subprocess.call([sys.executable] + sys.argv, env=env))
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.thumb:
        p = os.path.join(os.path.dirname(o.out), f'thumb_map{MAP}.png')
        thumbnail().save(p); print(p); return
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'still_map{MAP}_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', f'map{MAP}_hq.mp4')
    frame0()
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(os.path.dirname(o.out), f'parts_map{MAP}')
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
