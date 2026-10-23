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
# 2026-10-23 夜（確認版④）：前 → 左 → 後ろ（09）→ 下（08）。08 は輪切りの図（足もとから見た向き）と同じ向き。
# 左→後ろ＝動画11 の背中側（0〜6.4秒）→ 09 へ重ねて切り替え。後ろ→下＝動画12 の逆再生（09→08 の向き。途中は早送り。左右反転はしない）
SEQ = [('hold', '04', 1.10, 1.90),
       ('orbit', '10', 1.90, 3.35),
       ('hold', '07', 3.35, 4.15),
       ('orbit', '11a', 4.15, 5.60),
       ('hold', '09', 5.60, 6.40),
       ('orbit', '12r', 6.40, 7.90),
       ('hold', '08', 7.90, 10.15)]
T_FIN = 10.15                             # ここから 08 → 輪切り
CUT_D = 0.50                             # 1. 心室の高さに、光る切り口の線が横切る
XF_D = 0.60                              # 2. 中間の絵（3Dに似せた筋肉の赤の輪切り）を重ねて、3D の絵を消す
RC_D = 1.75                              # 3. 中間の絵の塗り → 図の塗り（区画の名前が出る）
MV_D = 0.80                              # 4. 縮みながら下の定位置へ
FIN_D = CUT_D + XF_D + RC_D + MV_D
INTRO_END = T_FIN + FIN_D                # 13.80
Q_T = (0.0, 2.05)                        # 問いかけ「ST上昇、心臓のどこ？」
PUSH = 0.055                             # 止まっているあいだも、ゆっくり寄りつづける（Z1〜T_FIN で 5.5%）
ANCHOR = (540, 800)

# 回り込み動画の「出力の進み u（0〜1）→ 動画の秒」。早送りしたい所は u の幅を狭く
TIME_MAP = {
    '10': ([0, 0.40, 0.56, 1.0], [0, 3.0, 5.0, 7.96]),     # 3〜5秒（腕で心臓が隠れる）を早送り
    '11a': ([0, 1.0], [0, 6.4]),                           # 左 → 背中側（終わりで 09 へ重ねて切り替え）
    '12r': ([0, 0.30, 0.70, 1.0], [7.96, 6.0, 2.0, 0.0]),  # 12 の逆再生（09→08）。大回りの途中を早送り
}
ORBIT_VID = {'10': '10', '11a': '11', '12r': '12'}
ORBIT_XF_IN = {'10': 0.14, '11a': 0.14, '12r': 0.20}      # 動画の最初：前の絵 → 動画（u の幅）
ORBIT_XF_OUT = {'10': 0.26, '11a': 0.30, '12r': 0.40}     # 動画の終わり：動画 → 次の絵（12r は 0.6秒）
ORBIT_TO = {'10': '07', '11a': '09', '12r': '08'}
ORBIT_FROM = {'10': '04', '11a': '07', '12r': '09'}

# 壁の場所（U。楕円：中心・半径・傾き度）。絵を見て決めた目安。07 は心尖がほぼ真下なので縦長
GLOW = {'04': (2110, 2700, 250, 560, 10),     # 前壁：前室間溝（LAD の溝）より左（画面の右）の左室の前の面。右室の前面は光らせない
        '07': (1480, 2760, 470, 600, 0),      # 側壁（左から見える左室の面。心尖は真下）
        '08': (1640, 2180, 740, 400, 0),      # 下壁（横隔膜に乗っている面）
        '09': (1030, 2620, 380, 260, -12)}    # 後壁：左室の後ろの基部寄り（房室間溝の下・下壁と側壁の間）。上の左房・下の横隔膜面は光らせない
GLOW_COL = (255, 226, 120)
LABELS = {'04': ('前壁中隔', 'V1〜V4', '（前から）'), '07': ('側壁', 'I・aVL・V5・V6', '（左から）'),
          '08': ('下壁', 'II・III・aVF'), '09': ('後壁', 'V7〜V9', '（後ろから・背中に追加）')}
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


def src_of(k, s=0.35):
    return still(k, half=s < 0.5)


def render(src, s, c):
    """src（画像, a, b）を、画面＝s・U＋c で描く。"""
    im, a, b = src
    k = a / s
    co = (k, 0, b[0] - k*c[0], 0, k, b[1] - k*c[1])
    out = im.transform((W, H), Image.AFFINE, co, resample=Image.BICUBIC, fillcolor=FILL)
    top = int(math.ceil(c[1] + s*(-b[1]/a))) if c[1] > 0 else 0
    if top > 0:                          # 上に下げたぶんは、絵の上端の行をのばして埋める（青い地の帯を出さない）
        row = out.crop((0, top + 1, W, top + 2)).resize((W, top + 1))
        out.paste(row, (0, 0))
    return out


# --- カメラ -------------------------------------------------------------------------
def ease(u):
    u = min(1.0, max(0.0, u))
    return u*u*(3 - 2*u)


def push(t):
    return 1.0 + PUSH*min(1.0, max(0.0, (t - Z1) / (T_FIN - Z1)))


# 寄り（確認版④）：止まるたびに、その壁（光らせる場所＝GLOW の中心）へ向かって寄る。倍率は対数で補間、
# 寄る点を画面の ZOOM_Q へ動かす。動画の最初のコマは前の絵の寄ったカメラのまま始まり、前半で全体へもどる
# （動画のコマは s 0.45 まで＝KV×1.25 まで）。08 は 0.35秒 胸全体（横隔膜・背骨）を見せてから、下の面へ寄る
ZOOM = {'04': 1.25, '07': 1.25, '09': 1.25, '08': 1.55}
HOLD_WAIT = {'08': 0.10}                 # 08：いちばん引いた絵（幅いっぱい s≈0.352＝胴体・横隔膜・背骨の中に心臓）から
ZOOM_D = {'08': 1.90}                    # 下の面へ連続して、ゆっくり寄る（倍率は対数で補間）
ZOOM_Q = (540, 760)


def cam_clamp(s, c):
    """絵の外（青い地）が画面に出ないように。"""
    # 上は 60px までは下げてよい（04・07 は大血管の上端が絵の上の方にあるので、心臓全体を y300 より下に入れるため。地の色は絵の上端とほぼ同じ）
    return s, (min(0.0, max(W - s*3072, c[0])), min(60.0, max(H - s*5504, c[1])))


def cam_base():
    return KV, (0.0, -VOFF)


HEART_TB = {'04': (720, 3424), '07': (792, 3456), '08': (916, 2656), '09': (1188, 3416)}   # 心臓の上端（大血管）〜下端（心尖）（U。赤い所を測った）
HEART_Y = (300, 1300)                    # 寄っても、心臓全体がこの高さの中に入る（大血管が切れない）


def cam_zoom(k, u):
    top, bot = HEART_TB[k]
    hy, hh = (top + bot)/2, bot - top
    z1 = max(1.0, min(ZOOM[k], 0.97*(HEART_Y[1] - HEART_Y[0]) / (KV*hh)))
    z = math.exp(math.log(z1)*u)
    s = KV*z
    P = GLOW[k][:2]
    q0 = (KV*P[0], KV*P[1] - VOFF)
    q = (q0[0] + (ZOOM_Q[0] - q0[0])*u, q0[1] + (ZOOM_Q[1] - q0[1])*u)
    cx, cy = q[0] - s*P[0], q[1] - s*P[1]
    cy = min(HEART_Y[1] - s*(hy + hh/2), max(HEART_Y[0] - s*(hy - hh/2), cy))
    return cam_clamp(s, (cx, cy))


def cam_main(t):
    """04・07・09・08・動画のコマに共通のカメラ。"""
    prev = None
    for kind, k, a, b in SEQ:
        if a <= t < b or (kind == 'hold' and k == '08' and t >= a):
            if kind == 'hold':
                w = HOLD_WAIT.get(k, 0.0)
                return cam_zoom(k, ease((t - a - w) / ZOOM_D.get(k, b - a - w)))
            s0, c0 = cam_zoom(prev, 1.0)
            s1, c1 = cam_base()
            u = ease(((t - a) / (b - a)) / 0.45)
            sc = math.exp(math.log(s0) + (math.log(s1) - math.log(s0))*u)
            return cam_clamp(sc, (c0[0] + (c1[0] - c0[0])*u, c0[1] + (c1[1] - c0[1])*u))
        if kind == 'hold':
            prev = k
    return cam_base()


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


# --- 電極（実際に貼る場所。U 座標。LITFL ECG Lead positioning）-------------------------------------------
# 04（前）：正中（胸骨）＝x1500（上に見える椎体の中心）。鎖骨は y450〜600、肋骨（前）は約400U おきに 第1 y750・第2 y1150・
#   第3 y1550・第4 y1900・第5 y2300 → 第4肋間 y2100・第5肋間 y2500。胸骨の幅 約300U（右縁 x1350・左縁 x1650）。
#   左鎖骨中線＝胸鎖関節（x1650）と肩峰（x2950）の中間 x2300。前腋窩線 x2750・中腋窩線＝胸郭の左端 x3000
# 07（左）：胸の前面 x150・背中 x3000（背骨の後ろ）。第5肋間は 04 と同じ高さ y2500。V4（鎖骨中線）は前面の近く x330、
#   V5（前腋窩線）x950、V6（中腋窩線）＝前後のまん中 x1550
# 09（後ろ）：背骨の中心 x1500（椎体 x1250〜1750）、患者の左＝画面の左。V6 と同じ高さ y2550。V9（傍脊椎）x1200、
#   V8（肩甲骨の下の角＝肩甲線。絵に肩甲骨がないので、背骨と胸郭の左端 x120 の 55% の所）x730、V7（後腋窩線）x300
ELECTRODES = {'04': [('V1', 1350, 2100), ('V2', 1650, 2100), ('V3', 1975, 2300), ('V4', 2300, 2500),
                     ('V5', 2750, 2500), ('V6', 3000, 2500)],
              '07': [('V4', 330, 2500), ('V5', 950, 2500), ('V6', 1550, 2500)],
              '09': [('V7', 300, 2550), ('V8', 730, 2550), ('V9', 1200, 2550)]}
PAD_LAB = {('04', 'V5'): (-30, -36)}       # 名前の位置（パッドからのずれ）。04 の V5・V6 は画面の右端なので上下に分ける
ELEC_HOT = {'04': ('V1', 'V2', 'V3', 'V4'), '07': ('V5', 'V6'), '09': ('V7', 'V8', 'V9')}


def draw_pads(m, base, k, s, c, a):
    """電極パッド（白い丸＋まん中の金具）と名前（パッドの下）。その壁を見る誘導は黄色。"""
    if a <= 0.004:
        return
    for n, ux, uy in ELECTRODES[k]:
        x, y = s*ux + c[0], s*uy + c[1]
        hot = n in ELEC_HOT[k]
        if base is not None:
            d = ImageDraw.Draw(base, 'RGBA')
            r = 17
            d.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=(0, 0, 0, int(90*a)))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 244, 242, int(245*a)), outline=(160, 170, 168, int(255*a)), width=2)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(150, 156, 160, int(255*a)))
        dx, dy = PAD_LAB.get((k, n), (0, 36))
        lx = min(m.SAFE_R - 24, max(m.SAFE_L + 24, x + dx))
        m.put(base, n, 30, 900, m.YELLOW if hot else m.WHITE, cx=lx, cy=y + dy, a=a)


# --- 見ている向きの目印（左上）：足もとから見た胴体の輪切り（上＝前・右＝患者の左・下＝背中）と、目の矢印 ---------
ICON_BOX = (135, 380, 405, 684)          # 1.5倍（字は 24px 以上）。透かし（691〜）の上
ICON_C, ICON_RX, ICON_RY, ICON_R = (270, 510), 75, 51, 108
VIEW_KEYS = [  # (時刻, 角度（上＝90＝前）, 半径の割合, 字)
    (0.0, 90, 1.0, '前から'), (1.90, 90, 1.0, '前から'), (3.35, 0, 1.0, '左から'), (4.15, 0, 1.0, '左から'),
    (5.60, -90, 1.0, '後ろから'), (6.40, -90, 1.0, '後ろから'), (7.10, -90, 0.0, '足もとから見上げる')]


def view_at(t):
    ks = VIEW_KEYS
    if t >= ks[-1][0]:
        return ks[-1][1], ks[-1][2], ks[-1][3], ks[-1][3], 1.0
    for (t0, a0, r0, l0), (t1, a1, r1, l1) in zip(ks, ks[1:]):
        if t0 <= t < t1:
            u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            return a0 + (a1 - a0)*u, r0 + (r1 - r0)*u, l0, l1, u
    return 90, 1.0, '前から', '前から', 1.0


def view_icon(m, base, t):
    a = 1 - ease((t - (T_FIN + CUT_D)) / 0.4)
    if a <= 0.004:
        return
    ang, rad, l0, l1, u = view_at(t)
    cx, cy = ICON_C
    if base is not None:
        d = ImageDraw.Draw(base, 'RGBA')
        d.rounded_rectangle(list(ICON_BOX), radius=16, fill=(8, 18, 16, int(170*a)), outline=(120, 146, 138, int(200*a)), width=2)
        # 胴体（足もとから見た輪切り）・背骨・心臓の位置
        d.ellipse([cx - ICON_RX, cy - ICON_RY, cx + ICON_RX, cy + ICON_RY], outline=(220, 232, 230, int(230*a)), width=3)
        d.ellipse([cx - 10, cy + ICON_RY - 27, cx + 10, cy + ICON_RY - 6], fill=(200, 212, 210, int(200*a)))
        d.ellipse([cx + 16, cy - 8, cx + 42, cy + 18], fill=(235, 80, 90, int(240*a)))
        # 目と矢印（半径 0 ＝ 足もとから＝こちら向き：⊙）
        r = ICON_R*rad
        th = math.radians(ang)
        ex, ey = cx + r*math.cos(th), cy - r*math.sin(th)
        col = (255, 214, 64, int(255*a))
        if rad > 0.15:
            ux, uy = (cx - ex)/max(r, 1e-6), (cy - ey)/max(r, 1e-6)
            L = max(0.0, r - 66)
            tx, ty = ex + ux*(18 + L), ey + uy*(18 + L)
            d.line([(ex + ux*18, ey + uy*18), (tx, ty)], fill=col, width=6)
            d.polygon([(tx + ux*18, ty + uy*18), (tx - uy*10, ty + ux*10), (tx + uy*10, ty - ux*10)], fill=col)
            d.ellipse([ex - 15, ey - 10, ex + 15, ey + 10], outline=col, width=4)
            d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=col)
        k = cl01((0.4 - rad) / 0.4)
        if k > 0.01:
            cc = (255, 214, 64, int(255*a*k))
            d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], outline=cc, width=4)
            d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=cc)
    m.put(base, '前', 24, 800, (200, 212, 210), cx=cx, cy=cy - ICON_RY + 20, a=a)   # 胴体の中（矢印と重ねない）
    m.put(base, '背中', 24, 800, (200, 212, 210), cx=cx, cy=cy + ICON_RY + 18, a=a)
    yl = ICON_BOX[3] - 34
    if u < 1:
        m.put(base, l0, 28, 800, m.YELLOW, cx=cx, cy=yl, a=a*(1 - u), max_w=250, kind='fade')
    m.put(base, l1, 28, 800, m.YELLOW, cx=cx, cy=yl, a=a*(u if u < 1 else 1), max_w=250, kind='fade')


def cl01(x):
    return min(1.0, max(0.0, x))


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
                return render(src_of(k, s), s, c), (k, s, c)
            u = (t - a) / (b - a)
            xs, ys = TIME_MAP[k]
            sec = interp(xs, ys, u)
            im = render(vframe(ORBIT_VID[k], int(round(sec*24)) + 1), s, c)       # 1コマずつ（混ぜない）
            xi = ORBIT_XF_IN[k]
            if xi and u < xi:
                im = Image.blend(render(src_of(ORBIT_FROM[k], s), s, c), im, ease(u / xi))
            xo = ORBIT_XF_OUT[k]
            if xo and u > 1 - xo:
                im = Image.blend(im, render(src_of(ORBIT_TO[k], s), s, c), ease((u - (1 - xo)) / xo))
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
        for k in ('04', '07', '09', '08'):
            amp = hold_amp(k, t)
            if amp > 0.004:
                s, c = cam_main(min(t, T_FIN))
                pulse = 0.82 + 0.18*math.sin(2*math.pi*(t - 0.2)/1.1)
                g = glow_layer(k, s, c, 0.62*amp*pulse)
                if g is not None:
                    im.alpha_composite(g)
    for k in ('04', '07', '09'):
        amp = hold_amp(k, t)
        if amp > 0.004:
            s_, c_ = cam_main(min(t, T_FIN))
            draw_pads(m, im, k, s_, c_, amp)
    for k in ('04', '07', '09', '08'):
        label_pill(m, im, k, hold_amp(k, t))
    view_icon(m, im, t)
    qa = ease((t - Q_T[0] + 0.01) / 0.2) * (1 - ease((t - (Q_T[1] - 0.35)) / 0.35))
    shadow_text(m, im, m.QUESTION, 66, 900, m.YELLOW, 333, a=qa if t > 0.005 else 1.0)
    return im


def photo08():
    """T_FIN で止まった 08 の絵（RGB）と、そのときの心臓の画面上の中心・幅。"""
    s, c = cam_main(T_FIN)
    (hx, hy), hw = HEART['08']
    return render(still('08', half=s < 0.5), s, c), (s*hx + c[0], s*hy + c[1]), s*hw
