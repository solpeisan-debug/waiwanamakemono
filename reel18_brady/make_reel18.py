"""第18弾 徐脈 まず覚えたい12パターン（第17弾 期外収縮と同じ作り）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。左が洞結節、右が房室ブロック（軽い〜突然抜ける））
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと
- 下部：⑦〜⑫ のミニ波形（2列×3段。左が房室ブロック（危ない）、右が補充調律・徐脈性心房細動）

紹介が終わった波形は、中部から自分の枠へ移り、ミニ波形として流れ続ける。
紹介中の枠は番号だけ。まだの枠は番号とヒント（薄く）。

使い方:
    python3 make_reel18.py              # 90秒・60fps
    python3 make_reel18.py --still 20   # 1コマだけ
    python3 make_reel18.py --check      # 検算・タイミング表
    python3 make_reel18.py --thumb      # サムネイル（透かしなし）
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

C_SA = (110, 200, 255)           # 洞結節
C_AV1 = (255, 212, 90)           # 房室ブロック（多くは良性）
C_AVD = (255, 92, 112)           # 房室ブロック（危ない・型を決められない）
C_ESC = (190, 160, 255)          # 補充調律
C_AF = (255, 152, 72)            # 徐脈性心房細動

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


def qrs_escape(t):                # 心室補充調律：幅の広いQRS（120ms以上）、逆向きのT
    return (0.70*_ga(t, 0.0, 0.030, 0.034) - 0.18*_g(t, 0.085, 0.022)
            - 0.32*_ga(t, 0.34, 0.075, 0.055))


PR_LONG = 0.28                   # 1度房室ブロック（P頂点 → R頂点）

# 出来事の種類 → (QRSの形, P波の形, P→Rの間隔)。時刻は R頂点（P だけのものは P頂点）
KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍
    'L': (qrs_normal, p_sinus, PR_LONG),    # PRの長い1拍
    'P': (None, p_sinus, 0.0),              # P波だけ（伝わらない、または房室解離）
    'Q': (qrs_normal, None, 0.0),           # P波のない細いQRS（接合部・房室解離・心房細動）
    'W': (qrs_escape, None, 0.0),           # 幅の広い補充収縮（心室）
}


def _cavb():
    pp, rr = 6.4/9, 1.28                    # 心房 約84/分、心室 約47/分（接合部）。比が整数にならない
    ev = [(k*pp, 'P') for k in range(9)] + [(0.40 + m*rr, 'Q') for m in range(5)]
    hl = [(k*pp - 0.07, k*pp + 0.07) for k in range(9)]
    return sorted(ev), hl


_CAVB_EV, _CAVB_HL = _cavb()
ALL = [(-1e9, 1e9)]                         # 全部をその色で

# 12パターン：1周期ぶんの出来事と周期の長さ（L）、色を付ける範囲（hl。周期の中の時刻）
PATTERNS = [
    dict(no='①', name='洞徐脈', col=C_SA, rep=5, hint='全部ゆっくり',
         one='P→QRSはふつう。60/分より遅い',
         ev=[(0, 'N')], L=4/3, hl=ALL),
    dict(no='②', name='洞停止', col=C_SA, rep=1, hint='長く止まる',
         one='P波ごと止まる。3秒をこえる休み',
         ev=[(0, 'N'), (3.3, 'N'), (4.1, 'N')], L=4.9, hl=[(0.32, 3.3 + 0.40)]),   # 休みのあと、再開の拍まで中部に見える
    dict(no='③', name='洞房ブロック', col=C_SA, rep=1, hint='休みがぴったり2拍',
         one='P波が1つ抜ける。休みはちょうど2拍ぶん',
         ev=[(0, 'N'), (.8, 'N'), (2.4, 'N'), (3.2, 'N')], L=4.0, hl=[(0.8 + 0.32, 2.4 + 0.40)]),   # 休みのあと、再開の拍まで中部に見える
    dict(no='④', name='1度房室ブロック', col=C_AV1, rep=8, hint='PRが長い',
         one='PRが200msより長い。毎回QRSにつながる',
         ev=[(0, 'L')], L=0.8, hl=[(-PR_LONG - 0.06, 0.02)]),
    dict(no='⑤', name='ウェンケバッハ', col=C_AV1, rep=2, hint='PRが伸びて抜ける',
         one='PRが少しずつ伸びて、QRSが1つ抜ける',
         ev=[(0, 'P'), (.18, 'Q'), (.8, 'P'), (1.08, 'Q'), (1.6, 'P'), (1.93, 'Q'), (2.4, 'P')], L=3.2,
         hl=[(-0.06, 0.20), (0.74, 1.10), (1.54, 1.95), (2.32, 2.50)]),
    dict(no='⑥', name='モビッツII型', col=C_AVD, rep=2, hint='突然抜ける',
         one='PRは同じまま、突然QRSが抜ける',
         ev=[(0, 'P'), (.18, 'Q'), (.8, 'P'), (.98, 'Q'), (1.6, 'P'), (1.78, 'Q'), (2.4, 'P')], L=3.2,
         hl=[(2.32, 2.50)]),
    dict(no='⑦', name='2:1房室ブロック', col=C_AVD, rep=4, hint='Pが2つにQRS1つ',
         one='P2つにQRS1つ。型は決められない',
         ev=[(0, 'P'), (.18, 'Q'), (.8, 'P')], L=1.6, hl=[(0.72, 0.90)]),
    dict(no='⑧', name='高度房室ブロック', col=C_AVD, rep=3, hint='Pが3つにQRS1つ',
         one='P3つ以上にQRS1つ。とても遅い',
         ev=[(0, 'P'), (.18, 'Q'), (2/3, 'P'), (4/3, 'P')], L=2.0, hl=[(2/3 - .08, 2/3 + .08), (4/3 - .08, 4/3 + .08)]),
    dict(no='⑨', name='完全房室ブロック', col=C_AVD, rep=1, hint='PとQRSがばらばら',
         one='PとQRSが別々に動く。PRが毎回ちがう',
         ev=_CAVB_EV, L=6.4, hl=_CAVB_HL),
    dict(no='⑩', name='接合部補充調律', col=C_ESC, rep=5, hint='Pのない細いQRS',
         one='P波なし・細いQRS・40〜60/分',
         ev=[(0, 'Q')], L=1.25, hl=ALL),
    dict(no='⑪', name='心室補充調律', col=C_ESC, rep=3, hint='幅が広く、とても遅い',
         one='幅の広いQRS・20〜40/分',
         ev=[(0, 'W')], L=2.0, hl=ALL),
    dict(no='⑫', name='徐脈性心房細動', col=C_AF, rep=1, hint='バラバラでゆっくり',
         one='P波なし・R-Rがバラバラ・60/分未満',
         ev=[(.3, 'Q'), (1.45, 'Q'), (2.85, 'Q'), (3.65, 'Q'), (5.05, 'Q')], L=6.0, hl=ALL, fib=True),
]
N_PAT = len(PATTERNS)
for _p in PATTERNS:
    _p['beats'] = _p['ev']

# 区間の長さ（秒）。ナレーションの長さ＋0.2秒以上で、拍の並びがくずれない位置で切る（第17弾と同じ考え方）。
# - 周期のちょうど倍数（①④⑦⑧⑩）
# - 周期の途中なら、次のパターンの最初の拍と同じ種類の拍がそこに来る位置（②③⑤⑥⑨⑫）
#   ②4.1 ③4.0 は洞の拍（③は周期ちょうど）、⑤4.0 ⑥4.8 は伝わるP波、⑨5.52 は接合部の拍、⑫4.8 はうしろの洞調律
# - ⑪5.0：最後の補充収縮から⑫の最初の拍まで 1.3秒（心房細動のR-Rと同じくらい）
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {'①': 4.0, '②': 4.1, '③': 4.0, '④': 4.8, '⑤': 4.0, '⑥': 4.8,
         '⑦': 4.8, '⑧': 4.0, '⑨': 5.52, '⑩': 5.0, '⑪': 5.0, '⑫': 4.8}
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
    return v


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
T_TITLE = 3.6                     # 冒頭の1文（約3.1秒）が入り、見出しと枠が出そろう長さ
END_HOLD = 5.7                    # 12個そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [1, 4, 6, 8, 10]           # ②洞停止 → ⑤ウェンケバッハ → ⑦2:1 → ⑨完全房室ブロック → ⑪心室補充調律
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
    tau = tau_center + (FX - XC) / F_PXS
    return wave_from(STRIP, tau) + strip_fib(tau), strip_colors(tau)


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
HEADER = [('徐脈、まず覚えたい', 1.0, WHITE), ('12', 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
HEADER_BASE = 372                   # 見出しのベースライン（y）
NOTE1 = '実際の速さ（ふつうの拍は75/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「徐脈、まず覚えたい」＋大きな黄色の「12」＋「パターン」。左右の余白（130px）に収める。"""
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
        put(im, '徐脈', 170, 900, WHITE, cx=540, cy=690, a=a_t)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, '遅いと思ったら、この12パターン', 42, 800, WHITE, cx=540, cy=Y_NAME, a=a_end, max_w=820)
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
    put(im, '遅い心電図、見分けられる？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 28, max_w=820)
    put(im, '徐脈', 110, 900, WHITE, cx=540, cy=Y_ONE + 14)
    v, cid = hook_arrays(8)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0)
    im.alpha_composite(wl, (0, F_Y0 + 50))
    return im.convert('RGB')


# --- 一覧型のサムネイル（第17弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {
    0: (0.0, []),
    1: (-0.45, [(0.38, 3.08)]),                # 洞停止：止まっているところ
    2: (0.0, [(1.26, 1.74)]),                  # 洞房ブロック：P波ごと抜けたところ
    3: (-1.0, [(-0.36, 0.0)]),                 # 1度：長いPR
    4: (-0.5, [(2.30, 2.52)]),                 # ウェンケバッハ：伝わらなかったP
    5: (-0.5, [(2.30, 2.52)]),                 # モビッツII型：伝わらなかったP
    6: (-0.4, [(0.70, 0.92)]),                 # 2:1：伝わらなかったP
    7: (-0.4, [(2/3 - 0.10, 4/3 + 0.10)]),     # 高度：伝わらなかったP（2つ）
    8: (0.0, []),
    9: (0.0, []),
    10: (-0.5, []),
    11: (0.0, []),
}
THUMB_MAX_MARKS = {3: 1}                       # 丸の数の上限（ふだんは2つまで。1度は1つ）
THUMB_DESC = ['全部ゆっくり', '長く止まる', 'ぴったり2拍ぶん', 'PRが長い', '伸びて抜ける', '突然抜ける',
              'P2つにQRS1つ', 'P3つにQRS1つ', 'PとQRSが別々', 'Pなし・細い', '広くて遅い', 'バラバラで遅い']


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
    """サムネイル（透かしなし）。第17弾の一覧型と同じ作り：
    タイトル → 12パターンを2列×6段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, '徐脈', 126, 900, WHITE, cx=540, cy=436)
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
    print(f'① 洞徐脈：{60/PATTERNS[0]["L"]:.0f}/分（60/分未満）')
    print(f'② 洞停止：休み {3.3:.1f}秒（3秒をこえる。洞の間隔0.80の倍数ではない：{3.3/0.8:.2f}倍）')
    print(f'③ 洞房ブロック：休み {2.4-0.8:.1f}秒 = 洞の間隔0.80のちょうど2倍')
    print(f'④ 1度房室ブロック：PR {_pr_ms(PR_LONG):.0f}ms（200ms超）／ふつうのPR {_pr_ms(PR):.0f}ms')
    print(f'⑤ ウェンケバッハ：PR {_pr_ms(.18):.0f} → {_pr_ms(.28):.0f} → {_pr_ms(.33):.0f}ms、R-R {1.08-.18:.2f} → {1.93-1.08:.2f} → 抜けをはさんで {3.2+.18-1.93:.2f}s')
    print(f'⑥ モビッツII型：PR {_pr_ms(.18):.0f}msで一定、抜けをはさむR-R {3.2+.18-1.78:.2f}s（直前の0.80のちょうど2倍）')
    print(f'⑦ 2:1：心房 {60/0.8:.0f}/分、心室 {60/1.6:.1f}/分')
    print(f'⑧ 高度（3:1）：心房 {60/(2/3):.0f}/分、心室 {60/2.0:.0f}/分')
    print(f'⑨ 完全：心房 {60/(6.4/9):.0f}/分、心室 {60/1.28:.0f}/分（接合部 40〜60）。比 {(1.28)/(6.4/9):.2f}（整数でない）')
    print(f'⑩ 接合部補充調律：{60/1.25:.0f}/分（40〜60）')
    print(f'⑪ 心室補充調律：{60/2.0:.0f}/分（20〜40）')
    rr = np.diff([.3, 1.45, 2.85, 3.65, 5.05, 6.3][:-1])
    print(f'⑫ 徐脈性心房細動：R-R {[round(float(x), 2) for x in rr]}、平均 {60/rr.mean():.0f}/分（60未満）')
    print(f'QRS幅：ふつう {_qrs_ms(qrs_normal):.0f}ms、心室補充 {_qrs_ms(qrs_escape):.0f}ms（120以上）')
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
        if k == 'P':
            continue
        ts = t_of(r)
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 720.0 if k == 'W' else 960.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel18_brady.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel18_brady_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel18_brady_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel18.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel18_list.png')
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
