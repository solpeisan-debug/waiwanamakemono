"""第29弾 冒頭の3D：全身 → 心臓へ寄る → 心臓のまわりを 前 → 左 → 下 → 後ろ と回る → 輪切りの図へ。

素材（assets3d/。git に入れない）：取扱説明書.md の 2・3・8章
- 03（心臓だけの正面）→ 04（心臓の寄り）は、心臓の中心と幅を合わせて重ねて切り替え（8章の表の値）
- 回り込み動画 10・11・12（1080×1920・24fps・8秒）は、最初のコマが 04・07・08 にそのまま重なる（相関 0.99・0.91・0.93、
  幅合わせ・中央）。最後のコマは次の絵と少しずれる（相関 0.63〜0.67）ので、終わりは長めに重ねて切り替える
- 動画は前後のコマを混ぜない（1コマずつ。速さはコマを飛ばして調整）。コマは out/cache3d/<番号>/NNN.jpg に書き出して使う
- 冠動脈は絵のものを使わない。壁の場所は、やわらかい光（半透明の色のにじみ）だけで示す

座標：U＝4K画像（3072×5504）のピクセル。画面＝s・U＋c。動画のコマは px＝KV・U＋(0, −VOFF)。
"""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
A3 = os.path.join(HERE, 'assets3d')
CACHE = os.path.join(HERE, 'out', 'cache3d')
W, H = 1080, 1920
KV = 1080 / 3072                         # 動画（と「寄り」の絵を画面いっぱいに見せるとき）の倍率
VOFF = (5504*KV - H) / 2                 # 上下の切り落とし（7.8px）
FILL = (8, 16, 44)

STILL_FILES = {'03': '03_正面_心臓だけ_4K.jpg', '04': '04_心臓の寄り_4K.jpg', '07': '07_左側面_心臓_4K.jpg',
               '08': '08_下から_心臓_4K.jpg', '09': '09_背面_心臓の寄り_4K.jpg'}
VIDEO_FILES = {'10': '10_回り込み_前から左.mp4', '11': '11_回り込み_左から下.mp4', '12': '12_回り込み_下から後ろ.mp4'}
N_VF = 192

# 心臓の中心と幅（U。8章の表。03 は 2章の値）
HEART = {'03': ((1745, 2150), 870), '04': ((1636, 2155), 1510), '07': ((1557, 2204), 1360),
         '08': ((1613, 1784), 1690), '09': ((1329, 2278), 1290)}

# --- タイムライン（秒） --------------------------------------------------------------
Z1 = 1.10                                # 03 の全身 → 心臓へ寄り終わる
XF03 = (0.68, 1.10)                      # 03 → 04 の重ねて切り替え
# (種類, 素材, 始め, 終わり)。hold＝その向きで止まる（ゆっくり寄りつづける）、orbit＝回り込み動画
# 2026-10-23 夜（確認版③）：順番を 前 → 左 → 後ろ → 下 にして 08（下から）で終える。
# 08 は輪切りの図（足もとから見た向き：上＝前・右＝患者の左・下＝背骨）と同じ向きなので、08 の心臓に輪切りを重ねて切り替える。
# 後ろ＝動画11 の途中の背面のコマ（B＝154コマめ）で止める。回り込み1本は約1.45秒（目が回らないように）
B_FRAME = 154                            # 動画11 の背面のコマ（6.4秒）
SEQ = [('hold', '04', 1.10, 2.00),
       ('orbit', '10', 2.00, 3.45),
       ('hold', '07', 3.45, 4.30),
       ('orbit', '11a', 4.30, 5.75),
       ('hold', 'B', 5.75, 6.65),
       ('orbit', '11b', 6.65, 7.25),
       ('hold', '08', 7.25, 8.55)]
T_FIN = 8.55                             # ここから 08 の心臓に輪切りの図を重ねる
XF_D = 0.60                              # 08 → 輪切り（同じ位置・同じ大きさ）
MV_D = 0.80                              # 輪切りが下の定位置へ縮みながら移動
FIN_D = XF_D + MV_D
INTRO_END = T_FIN + FIN_D                # 9.95
Q_T = (0.0, 2.05)                        # 問いかけ「ST上昇、心臓のどこ？」
PUSH = 0.055                             # 止まっているあいだも、ゆっくり寄りつづける（Z1〜T_FIN で 5.5%）
ANCHOR = (540, 800)

# 回り込み動画の「出力の進み u（0〜1）→ 動画の秒」。早送りしたい所は u の幅を狭く
TIME_MAP = {
    '10': ([0, 0.40, 0.56, 1.0], [0, 3.0, 5.0, 7.96]),     # 3〜5秒（腕で心臓が隠れる）を早送り
    '11a': ([0, 1.0], [0, (B_FRAME - 1)/24]),              # 左 → 背中側（背面のコマで止める）
    '11b': ([0, 1.0], [(B_FRAME - 1)/24, 6.75]),           # 背面 → 下（6.5〜6.75秒で 08 へ重ねて切り替え。最後の1秒の飛びは使わない）
}
ORBIT_VID = {'10': '10', '11a': '11', '11b': '11'}
ORBIT_XF_IN = {'10': 0.14, '11a': 0.14, '11b': 0.0}       # 動画の最初：前の絵 → 動画（u の幅）
ORBIT_XF_OUT = {'10': 0.26, '11a': 0.0, '11b': 0.45}      # 動画の終わり：動画 → 次の絵
ORBIT_TO = {'10': '07', '11a': 'B', '11b': '08'}
ORBIT_FROM = {'10': '04', '11a': '07', '11b': 'B'}

# 壁の場所（U。楕円：中心・半径・傾き度）。絵を見て決めた目安。07 は心尖がほぼ真下なので縦長
GLOW = {'04': (2110, 2700, 250, 560, 10),     # 前壁：前室間溝（LAD の溝）より左（画面の右）の左室の前の面。右室の前面は光らせない
        '07': (1480, 2760, 470, 600, 0),      # 側壁（左から見える左室の面。心尖は真下）
        '08': (1640, 2180, 740, 400, 0),      # 下壁（横隔膜に乗っている面）
        'B': (1150, 2540, 300, 240, -10)}     # 後壁（動画11 の背面のコマ）：左室の後ろの基部寄り。上の左房・下の横隔膜面は光らせない
GLOW_COL = (255, 226, 120)
LABELS = {'04': ('前壁中隔', 'V1〜V4'), '07': ('側壁', 'I・aVL・V5・V6'),
          '08': ('下壁', 'II・III・aVF'), 'B': ('後壁', 'V7〜V9', '（背中に追加）')}
LABEL_CY = 1340                          # 3D の札（心臓の下・透かしの下）。字幕の枠はその下（make_reel29.BOX3D）


# --- 素材の読み込み ----------------------------------------------------------------
_ST = {}


def still(k, half=True):
    """(画像, a, b)：画像の px ＝ a・U ＋ b。ふだんは半分の大きさ（1536×2752）。03 で大きく寄るときだけ 4K のまま。"""
    key = (k, half)
    if key not in _ST:
        im = Image.open(os.path.join(A3, STILL_FILES[k])).convert('RGB')
        if half:
            im = im.resize((1536, 2752), Image.LANCZOS)
            _ST[key] = (im, 0.5, (0.0, 0.0))
        else:
            _ST[key] = (im, 1.0, (0.0, 0.0))
    return _ST[key]


def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def ensure_frames():
    """回り込み動画のコマを JPEG に書き出しておく（1回だけ）。"""
    for n, f in VIDEO_FILES.items():
        d = os.path.join(CACHE, n)
        if os.path.exists(os.path.join(d, f'{N_VF:03d}.jpg')):
            continue
        os.makedirs(d, exist_ok=True)
        subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-i', os.path.join(A3, f), '-q:v', '2',
                        os.path.join(d, '%03d.jpg')], check=True)


_VF = {}


def vframe(n, i):
    i = int(min(N_VF, max(1, i)))
    key = (n, i)
    if key not in _VF:
        if len(_VF) > 24:
            _VF.clear()
        _VF[key] = (Image.open(os.path.join(CACHE, n, f'{i:03d}.jpg')).convert('RGB'), KV, (0.0, -VOFF))
    return _VF[key]


def src_of(k):
    """止まる絵：静止画か、動画11 の背面のコマ。"""
    return vframe('11', B_FRAME) if k == 'B' else still(k)


def render(src, s, c):
    """src（画像, a, b）を、画面＝s・U＋c で描く。"""
    im, a, b = src
    k = a / s
    co = (k, 0, b[0] - k*c[0], 0, k, b[1] - k*c[1])
    return im.transform((W, H), Image.AFFINE, co, resample=Image.BICUBIC, fillcolor=FILL)


# --- カメラ -------------------------------------------------------------------------
def ease(u):
    u = min(1.0, max(0.0, u))
    return u*u*(3 - 2*u)


def push(t):
    return 1.0 + PUSH*min(1.0, max(0.0, (t - Z1) / (T_FIN - Z1)))


def cam_main(t):
    """04・07・08・09・動画のコマに共通のカメラ（画面いっぱい＋ゆっくり寄る）。"""
    z = push(t)
    s = KV*z
    c = (ANCHOR[0] + z*(0 - ANCHOR[0]), ANCHOR[1] + z*(-VOFF - ANCHOR[1]))
    return s, c


def cam_match(s4, c4, k_from='04', k_to='03'):
    """k_from の絵のカメラ (s4, c4) と、心臓の中心と幅が同じに見える k_to のカメラ。"""
    (h4, w4), (h3, w3) = HEART[k_from], HEART[k_to]
    s3 = s4*w4/w3
    p = (s4*h4[0] + c4[0], s4*h4[1] + c4[1])
    return s3, (p[0] - s3*h3[0], p[1] - s3*h3[1])


CAM_FULL = (1536, 2600, 1080/3072, 960)  # 03 の全身（見本の CAM_FULL）


def cam_03(t):
    """0〜Z1：03 の全身 → 心臓へ（倍率は対数で補間、心臓の画面上の位置は直線で）。"""
    cx, cy, s0, ys = CAM_FULL
    c0 = (540 - s0*cx, ys - s0*cy)
    s4, c4 = cam_main(Z1)
    s1, c1 = cam_match(s4, c4, '04', '03')
    u = ease(t / Z1)
    s = math.exp(math.log(s0) + (math.log(s1) - math.log(s0))*u)
    h = HEART['03'][0]
    p0 = (s0*h[0] + c0[0], s0*h[1] + c0[1])
    p1 = (s1*h[0] + c1[0], s1*h[1] + c1[1])
    p = (p0[0] + (p1[0] - p0[0])*u, p0[1] + (p1[1] - p0[1])*u)
    return s, (p[0] - s*h[0], p[1] - s*h[1])


def interp(xs, ys, x):
    return float(np.interp(x, xs, ys))


# --- 光（壁の場所） ------------------------------------------------------------------
def glow_layer(k, s, c, amp):
    if amp <= 0.004:
        return None
    gx, gy, rx, ry, ang = GLOW[k]
    q = 4                                     # 1/4 の大きさで描いてぼかす
    m = Image.new('L', (W//q, H//q), 0)
    d = ImageDraw.Draw(m)
    cx, cy = (s*gx + c[0])/q, (s*gy + c[1])/q
    a = math.radians(ang)
    pts = []
    for j in range(64):
        th = 2*math.pi*j/64
        x, y = s*rx*math.cos(th)/q, s*ry*math.sin(th)/q
        pts.append((cx + x*math.cos(a) - y*math.sin(a), cy + x*math.sin(a) + y*math.cos(a)))
    d.polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(s*min(rx, ry)*0.42/q)).resize((W, H), Image.BILINEAR)
    lay = Image.new('RGBA', (W, H), GLOW_COL + (0,))
    lay.putalpha(m.point(lambda v: int(v*amp)))
    return lay


# --- 文字（影つき・下地つき） --------------------------------------------------------
def shadow_text(m, base, s, size, weight, col, cy, a=1.0):
    """絵の上でも読めるように、ぼかした黒い影をつけて中央ぞろえ。"""
    if a <= 0.004:
        return
    if base is None:
        m.put(None, s, size, weight, col, cx=540, cy=cy, a=a, max_w=800)
        return
    im, asc, gb, sz = m.text_img(s, size, weight, col, 800)
    w, h = im.size
    px, py = int(540 - w/2), int(cy - 4 - asc*0.62)
    pad = 24
    sh = Image.new('RGBA', (w + 2*pad, h + 2*pad), (0, 0, 0, 0))
    al = im.getchannel('A')
    blk = Image.new('RGBA', im.size, (0, 0, 0, 255))
    blk.putalpha(al)
    sh.alpha_composite(blk, (pad, pad + 3))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    sh.putalpha(sh.getchannel('A').point(lambda v: int(min(255, v*1.9)*a)))
    base.alpha_composite(sh, (px - pad, py - pad))
    m.put(base, s, size, weight, col, cx=540, cy=cy, a=a, max_w=800)


def label_pill(m, base, k, a):
    """「前壁 V1〜V4」：壁の名前（白）＋見ている誘導（黄）。うすい黒の下地。"""
    if a <= 0.004:
        return
    name, leads = LABELS[k][:2]
    parts = [(name, 64, 900, m.WHITE), (leads, 52, 900, m.YELLOW)]
    if len(LABELS[k]) > 2:
        parts.append((LABELS[k][2], 40, 800, m.YELLOW))
    gap = 22
    ws = [m.text_w(p[0], p[1], p[2]) for p in parts]
    tot = sum(ws) + gap*(len(parts) - 1)
    if base is not None:
        d = ImageDraw.Draw(base, 'RGBA')
        x0, x1 = 540 - tot/2 - 34, 540 + tot/2 + 34
        d.rounded_rectangle([x0, LABEL_CY - 52, x1, LABEL_CY + 48], radius=26, fill=(0, 6, 20, int(150*a)))
    m.put_parts(base, parts, LABEL_CY, a=a, gap=gap)


# --- 1コマ --------------------------------------------------------------------------
def scene(t):
    """t（0〜T_FIN）の3Dの絵（RGB）と、その場の (光の素材, 光の強さ, カメラ)。"""
    if t < Z1:
        s3, c3 = cam_03(t)
        im = render(still('03', half=s3 < 0.55), s3, c3)
        w = ease((t - XF03[0]) / (XF03[1] - XF03[0]))
        if w > 0.004:
            s4, c4 = cam_match(s3, c3, '03', '04')
            im = Image.blend(im, render(still('04'), s4, c4), w)
        return im, None
    s, c = cam_main(t)
    for kind, k, a, b in SEQ:
        if a <= t < b or (kind == 'hold' and k == '08' and t >= a):
            if kind == 'hold':
                return render(src_of(k), s, c), (k, s, c)
            u = (t - a) / (b - a)
            xs, ys = TIME_MAP[k]
            sec = interp(xs, ys, u)
            im = render(vframe(ORBIT_VID[k], int(round(sec*24)) + 1), s, c)       # 1コマずつ（混ぜない）
            xi = ORBIT_XF_IN[k]
            if xi and u < xi:
                im = Image.blend(render(src_of(ORBIT_FROM[k]), s, c), im, ease(u / xi))
            xo = ORBIT_XF_OUT[k]
            if xo and u > 1 - xo:
                im = Image.blend(im, render(src_of(ORBIT_TO[k]), s, c), ease((u - (1 - xo)) / xo))
            return im, None
    return render(still('08'), s, c), ('08', s, c)


def hold_amp(k, t):
    """その向きで止まっているあいだの光・名前の濃さ（少し前から出て、回り始めたら消える）。"""
    for kind, kk, a, b in SEQ:
        if kind == 'hold' and kk == k:
            end = b if k != '08' else T_FIN
            return ease((t - (a - 0.05)) / 0.25) * (1 - ease((t - (end - 0.10)) / 0.22))
    return 0.0


def intro_frame(m, t, base_only=False):
    """0〜T_FIN の1コマ（RGBA）。m＝make_reel29（文字の道具）。"""
    if base_only and m.REC is not None:
        im = None
    else:
        im, gk = scene(min(t, T_FIN))
        im = im.convert('RGBA')
        # 光：止まっている向きのとき（07・08・09 の絵は動画の最後から重ねて切り替わる）
        for k in ('04', '07', 'B', '08'):
            amp = hold_amp(k, t)
            if amp > 0.004:
                s, c = cam_main(min(t, T_FIN))
                pulse = 0.82 + 0.18*math.sin(2*math.pi*(t - 0.2)/1.1)
                g = glow_layer(k, s, c, 0.62*amp*pulse)
                if g is not None:
                    im.alpha_composite(g)
    for k in ('04', '07', 'B', '08'):
        label_pill(m, im, k, hold_amp(k, t))
    qa = ease((t - Q_T[0] + 0.01) / 0.2) * (1 - ease((t - (Q_T[1] - 0.35)) / 0.35))
    shadow_text(m, im, m.QUESTION, 66, 900, m.YELLOW, 333, a=qa if t > 0.005 else 1.0)
    return im


def photo08():
    """T_FIN で止まった 08 の絵（RGB）と、そのときの心臓の画面上の中心・幅。"""
    s, c = cam_main(T_FIN)
    (hx, hy), hw = HEART['08']
    return render(still('08'), s, c), (s*hx + c[0], s*hy + c[1]), s*hw
