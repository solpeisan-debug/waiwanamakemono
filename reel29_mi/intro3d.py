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
# 2026-10-23 夜：冒頭に本物の人の体 17 を出し、電極（V1〜V6・IEC の色）を貼った状態から 03（透けた体）へ重ねて切り替える
T0 = 1.30                                # 人の体から 3D の流れが始まるまで（ここから下の時刻はすべて T0 だけ後ろへ）
X17 = (1.00, 1.90)                       # 17 → 03 の重ねて切り替え（03 の寄りの始まりと重なる）
Z1 = T0 + 1.10                           # 03 の全身 → 心臓へ寄り終わる
XF03 = (T0 + 0.68, T0 + 1.10)            # 03 → 04 の重ねて切り替え
# (種類, 素材, 始め, 終わり)。hold＝その向きで止まる（ゆっくり寄りつづける）、orbit＝回り込み動画
# 2026-10-23 夜（確認版④）：前 → 左 → 後ろ（09）→ 下（08）。08 は輪切りの図（足もとから見た向き）と同じ向き。
# 左→後ろ＝動画11 の背中側（0〜6.4秒）→ 09 へ重ねて切り替え。後ろ→下＝動画12 の逆再生（09→08 の向き。途中は早送り。左右反転はしない）
SEQ = [(k, n, a + T0, b + T0) for k, n, a, b in [
       ('hold', '04', 1.10, 1.90),
       ('orbit', '10', 1.90, 3.35),
       ('hold', '07', 3.35, 4.15),
       ('orbit', '11a', 4.15, 5.60),
       ('hold', '09', 5.60, 6.40),
       ('orbit', '12r', 6.40, 7.90),
       ('hold', '08', 7.90, 9.60)]]
T_FIN = 9.60 + T0                             # ここから 08 → 輪切り
# 08 は「前下方から見た心臓」（説明書8章）。足もとから見るときは、説明の場面（横向きの全身 14＋目の移動）を入れてから、
# 真下から見上げた絵 13 を下からスライドで入れ、13 の心臓へ寄ってから輪切りを重ねる
EX1_D = 0.80                             # 1. 08 の心臓が小さくなりながら、全身 14 の心臓の位置へ重なる（心臓の位置で2枚をつなぐ）
EX1H_D = 0.20                            #    全身がはっきりする
EX2_D = 1.00                             # 2. 胸の前の目が弧を描いて足もとの下へ回り、上を向く。点線の視線が心臓までのびる
X15_D = 0.40                             # 3. 14 → 動画15 の最初のコマ（位置・大きさを合わせて重ねる）。目と視線は消える
ROT_D = 4.00                             # 4. 回る動画で人体が回って足もとから見上げる向きへ（1コマずつ・コマ飛ばしで速さ）
X13_D = 0.40                             # 5. 動画15 の最後 → 13（位置・大きさを合わせて重ねる）
H13_D = 0.40                             # 6. 13 で止まる（方向の字・左上の目印「足もとから見上げる」）
Z13_D = 0.70                             # 7. 13 の心臓へ寄る（輪切りが定位置とほぼ同じ大きさになるところまで）
OV_D = 0.60                              # 8. 13 の心室の外形に筋肉の赤い輪切りをぴったり重ね、13 の絵を消す
RC_D = 0.80                              # 9. 同じ位置・大きさで図の塗りへ（区画の名前）
MV_D = 0.80                              # 10. 下の定位置へ
T_EX1H = T_FIN + EX1_D
T_EX2 = T_EX1H + EX1H_D
T_X15 = T_EX2 + EX2_D
T_ROT = T_X15 + X15_D
T_X13 = T_ROT + ROT_D
T_H13 = T_X13 + X13_D
T_EX3 = T_H13                            # （説明の場面の終わり）
T_Z13 = T_H13 + H13_D
T_OV = T_Z13 + Z13_D
T_RC = T_OV + OV_D
T_MV = T_RC + RC_D
FIN_D = EX1_D + EX1H_D + EX2_D + X15_D + ROT_D + X13_D + H13_D + Z13_D + OV_D + RC_D + MV_D
INTRO_END = T_FIN + FIN_D                # 17.80
Q_T = (0.0, 2.05 + T0)                        # 問いかけ「ST上昇、心臓のどこ？」
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
    ensure_fig_frames()
    ensure_v15()
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
ZOOM_D = {'08': 1.50}                    # 下の面へ連続して、ゆっくり寄る（倍率は対数で補間）
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


# --- 17：本物の人の体（1376×768・横長。診察室で上半身裸で正面に立つ男性）---------------------------------------------
IMG17 = os.path.join(A3, '17_人の体_正面_EL.png')
# 17（2026-10-23 夜に差し替え：肌のきれいな若い男性・頭まで入っている）の px → 03 の U：
# 乳頭（17：(588,483)・(791,481)、まん中 (690,482)）を 03 の第4肋間の高さ（y2118）に、正中（17 x690）を 03 の正中（x1667）に。
# 大きさは、胸郭の幅の比（17：乳頭の高さで x543〜843＝300 ⇔ 03：第4肋間で 2190 → 7.3倍）と、乳頭どうしの間と鎖骨中線どうしの間の比
# （203 ⇔ 921 → 4.5倍）の相乗平均 5.76倍。03 の U ＝ (17 の px − (690, 482)) × 5.76 ＋ (1667, 2118)
P17, P03, K17 = (690.0, 482.0), (1667.0, 2118.0), 5.76
DARK17 = (0.60, 1.45, 0.45)              # 切り替えの前半で、明るい診察室の絵を 03 の紺へ少しずつ暗くする（始め, 終わり, 強さ）
_I17 = None


def img17():
    global _I17
    if _I17 is None:
        im = Image.open(IMG17).convert('RGBA')
        w, h = im.size
        a = np.full((h, w), 255.0)
        f = 70
        ramp = np.arange(f)/f
        a[:f] *= ramp[:, None]; a[-f:] *= ramp[::-1][:, None]
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        bg = im.convert('RGB').resize((int(w*H/h), H), Image.BILINEAR)
        bx = (bg.size[0] - W)//2
        bg = bg.crop((bx, 0, bx + W, H)).filter(ImageFilter.GaussianBlur(28))
        bg = Image.blend(bg, Image.new('RGB', (W, H), FILL), 0.45)      # 上下の背景：絵をぼかして延ばし、少し暗く
        _I17 = (im, bg)
    return _I17


def render17(s3, c3):
    """03 のカメラ (s3, c3) と同じ所に、人の体 17 を重ねた絵（RGB）。"""
    im, bg = img17()
    s = s3*K17
    c = (s3*(P03[0] - K17*P17[0]) + c3[0], s3*(P03[1] - K17*P17[1]) + c3[1])
    k = 1/s
    lay = im.transform((W, H), Image.AFFINE, (k, 0, -k*c[0], 0, k, -k*c[1]), resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
    out = bg.convert('RGBA')
    out.alpha_composite(lay)
    return out.convert('RGB')


def cam_03(t):
    """0〜Z1：03 の全身 → 心臓へ（倍率は対数で補間、心臓の画面上の位置は直線で）。"""
    cx, cy, s0, ys = CAM_FULL
    c0 = (540 - s0*cx, ys - s0*cy)
    s4, c4 = cam_main(Z1)
    s1, c1 = cam_match(s4, c4, '04', '03')
    u = ease((t - T0) / (Z1 - T0))
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
        x0, x1 = 540 - tot/2 - 34, 540 + tot/2 + 34
        m.rrect_overlay(base, (x0, LABEL_CY - 52, x1, LABEL_CY + 48), 26, (0, 6, 20, int(255*m.BOARD_A*a)))   # 半透明（下の絵が透ける）
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
# 03 の U ＝ 04 の U を心臓の中心・幅で合わせて変換（cam_match と同じ。03→04 の寄りで電極が同じ所に残る）
def _e04_to_03(x, y):
    (h4, w4), (h3, w3) = HEART['04'], HEART['03']
    k = w3/w4
    return h3[0] + (x - h4[0])*k, h3[1] + (y - h4[1])*k


ELECTRODES['03'] = [(n, *_e04_to_03(x, y)) for n, x, y in ELECTRODES['04']]
PAD_LAB = {('04', 'V5'): (-30, -36), ('03', 'V5'): (-30, -36)}       # 名前の位置（パッドからのずれ）。04 の V5・V6 は画面の右端なので上下に分ける
ELEC_HOT = {'03': (), '04': ('V1', 'V2', 'V3', 'V4'), '07': ('V5', 'V6'), '09': ('V7', 'V8', 'V9')}


# 電極の色（IEC。日本の「あきみちゃくし」：C1 赤・C2 黄・C3 緑・C4 茶・C5 黒・C6 紫。Wikipedia「Electrocardiography」の
# AHA／IEC の表で確認。LITFL ECG Lead positioning の本文には色の表がない）。V4R・V7〜V9 は決まった色がないので白のまま
ELEC_COLORS = {'V1': (226, 38, 44), 'V2': (246, 206, 36), 'V3': (34, 160, 72), 'V4': (128, 78, 40),
               'V5': (18, 18, 20), 'V6': (146, 70, 196)}


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
            ec = ELEC_COLORS.get(n)
            if ec:                           # パッドの中心を電極の色に（黒の V5 は白いふちを太めに）
                ri = 9 if n == 'V5' else 11
                d.ellipse([x - ri, y - ri, x + ri, y + ri], fill=ec + (int(255*a),))
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(150, 156, 160, int(255*a)))
        dx, dy = PAD_LAB.get((k, n), (0, 36))
        lx = min(m.SAFE_R - 24, max(m.SAFE_L + 24, x + dx))
        m.put(base, n, 30, 900, m.YELLOW if hot else m.WHITE, cx=lx, cy=y + dy, a=a, kind='fade')


# --- 見ている向きの目印（左上）：回転動画 05（人体が 正面→左の側面→背面）の小さなコマ＋目の矢印 -------------------
ICON_BOX = (135, 372, 435, 688)          # 幅 300px。透かし（691〜）の上
FIG_BOX = (210, 380, 360, 647)           # 05 のコマ（9:16）を置く所
FRAME_KEYS = [(0.0, 1)] + [(t + T0, f) for t, f in [(1.90, 1), (3.35, 57), (4.15, 57), (5.60, 137), (6.40, 137), (7.60, 1)]]   # 前＝1・左の側面＝57・背面＝137
VIEW_LABELS = [(0.0, '前から'), (2.60 + T0, '左から'), (4.90 + T0, '後ろから'), (7.00 + T0, '前下から')]          # 向きが変わる途中で入れ替わる
EYE_SIDE, EYE_FEET = ((402, 472), (330, 472)), ((285, 640), (285, 572))   # （目の位置, 矢印の先）：横から／足もとから上へ
_FIG = {}


def fig_frame(i):
    i = int(min(192, max(1, i)))
    if i not in _FIG:
        if len(_FIG) > 40:
            _FIG.clear()
        _FIG[i] = Image.open(os.path.join(CACHE, '05', f'{i:03d}.jpg')).convert('RGB').resize(
            (FIG_BOX[2] - FIG_BOX[0], FIG_BOX[3] - FIG_BOX[1]), Image.LANCZOS)
    return _FIG[i]


def ensure_fig_frames():
    d = os.path.join(CACHE, '05')
    if not os.path.exists(os.path.join(d, '192.jpg')):
        os.makedirs(d, exist_ok=True)
        subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-i', os.path.join(A3, '05_回転_正面から背面_無音.mp4'),
                        '-vf', 'scale=180:320', '-q:v', '3', os.path.join(d, '%03d.jpg')], check=True)


def view_label(t):
    """(前の字, 次の字, 入れ替わりの割合)。最後は起き上がりに合わせて「足もとから見る」。"""
    labs = VIEW_LABELS + [(T_H13, '足もとから見上げる')]
    for (t0, l0), (t1, l1) in zip(labs, labs[1:]):
        if t < t1 - 0.25:
            return l0, l0, 0.0
        if t < t1 + 0.25:
            return l0, l1, ease((t - (t1 - 0.25)) / 0.5)
    return labs[-1][1], labs[-1][1], 0.0


def ex_gate(t):
    """説明の場面（T_FIN〜T_H13）のあいだは、左上の目印・方向の字を隠す。"""
    if t < T_H13:
        return 1 - ease((t - T_FIN) / 0.3)
    return ease((t - T_H13) / 0.4)


SHOW_ICON = True                          # 左上の向きの目印：いったんやめたが、ないと分かりにくいので「透けさせて」付ける（2026-10-23 夜）
# 不透明度（でんさん「後ろの体が見えるくらいに」）：上半身の絵・枠線 28%／目の矢印 45%／板の背景 9%／字 50%
ICON_OP, ICON_EYE_OP, ICON_BOARD_OP, ICON_TEXT_OP = 0.28, 0.45, 0.09, 0.50


def view_icon(m, base, t):
    if not SHOW_ICON:
        return
    a = (1 - ease((t - T_Z13) / 0.3))*ex_gate(t)     # 13 に寄りはじめたら消す（胴体に重ねない）
    if a <= 0.004:
        return
    l0, l1, u = view_label(t)
    feet = 1.0 if t >= T_H13 else 0.0
    at = a*ICON_TEXT_OP
    ae = a*ICON_EYE_OP
    a, ab = a*ICON_OP, a*ICON_BOARD_OP
    if base is not None:
        fi = int(round(float(np.interp(t, [k[0] for k in FRAME_KEYS], [k[1] for k in FRAME_KEYS]))))
        # 別の透明な板に描いてから重ねる（RGBA の絵に直接 ImageDraw で描くと、半透明にならず色がそのまま入るため）
        bx0, by0, bx1, by1 = ICON_BOX
        lay = Image.new('RGBA', (bx1 - bx0 + 1, by1 - by0 + 1), (0, 0, 0, 0))
        board = Image.new('RGBA', lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(board).rounded_rectangle([0, 0, lay.size[0] - 1, lay.size[1] - 1], radius=16, fill=(8, 18, 16, int(255*ab)),
                                                outline=(120, 146, 138, int(255*a)), width=2)
        lay.alpha_composite(board)
        fig = fig_frame(fi).convert('RGBA')
        fig.putalpha(int(255*a))
        lay.alpha_composite(fig, (FIG_BOX[0] - bx0, FIG_BOX[1] - by0))
        base.alpha_composite(lay, (bx0, by0))
        eye = Image.new('RGBA', base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(eye)
        (ex0, ey0), (tx0, ty0) = EYE_SIDE
        (ex1, ey1), (tx1, ty1) = EYE_FEET
        ex, ey = ex0 + (ex1 - ex0)*feet, ey0 + (ey1 - ey0)*feet
        tx, ty = tx0 + (tx1 - tx0)*feet, ty0 + (ty1 - ty0)*feet
        ux, uy = tx - ex, ty - ey
        L = max(1e-6, math.hypot(ux, uy)); ux, uy = ux/L, uy/L
        col = (255, 214, 64, int(255*ae))
        d.line([(ex + ux*18, ey + uy*18), (tx - ux*12, ty - uy*12)], fill=col, width=6)
        d.polygon([(tx, ty), (tx - ux*16 - uy*10, ty - uy*16 + ux*10), (tx - ux*16 + uy*10, ty - uy*16 - ux*10)], fill=col)
        d.ellipse([ex - 15, ey - 10, ex + 15, ey + 10], fill=(8, 18, 16, int(255*ab)), outline=col, width=4)
        d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=col)
        base.alpha_composite(eye)
    yl = ICON_BOX[3] - 22
    if u > 0:
        m.put(base, l0, 26, 800, m.YELLOW, cx=285, cy=yl, a=at*(1 - u), max_w=280, kind='fade')
        m.put(base, l1, 26, 800, m.YELLOW, cx=285, cy=yl, a=at*u, max_w=280, kind='fade')
    else:
        m.put(base, l0, 26, 800, m.YELLOW, cx=285, cy=yl, a=at, max_w=280, kind='fade')


def icon_heart_k(t):
    """3D の心臓が札に大きく重なるコマでは、さらに薄く（0.8倍＝不透明度 40%）。"""
    if t >= T_FIN:
        return 1.0
    k = '04'
    for kind, kk, a, b in SEQ:
        if kind == 'hold' and t >= a - 0.3:
            k = kk
    s, c = cam_main(min(t, T_FIN))
    (hx, _), hw = HEART[k]
    top, bot = HEART_TB[k]
    x0, x1 = s*(hx - hw/2) + c[0], s*(hx + hw/2) + c[0]
    y0, y1 = s*top + c[1], s*bot + c[1]
    bx0, by0, bx1, by1 = ICON_BOX
    ov = max(0, min(x1, bx1) - max(x0, bx0))*max(0, min(y1, by1) - max(y0, by0))
    frac = ov / ((bx1 - bx0)*(by1 - by0))
    return 1 - 0.2*min(1.0, frac*2)


# --- 画面の端の方向の字（いまの向き）。半透明の白・27px ---------------------------------------------------
DIR_SETS = {
    'front': [('体の右', 'L'), ('体の左', 'R'), ('↑ 頭', 'T')],
    'left': [('胸（前）', 'L'), ('背中', 'R'), ('↑ 頭', 'T')],
    'back': [('体の左', 'L'), ('体の右', 'R'), ('↑ 頭', 'T')],
    'feet': [('← 体の右', 'L2'), ('体の左 →', 'R2'), ('↑ 胸（前）', 'T2'), ('↓ 背中', 'B2')],
}
DIR_KEYS = [(0.0, 'front'), (2.60 + T0, 'left'), (4.90 + T0, 'back'), (7.00 + T0, 'front'), (T_H13, 'feet')]


def dir_labels(m, base, t):
    fade_all = (1 - ease((t - T_MV) / 0.3))*ex_gate(t)
    if fade_all <= 0.004:
        return
    sets = []
    for (t0, k0), nxt in zip(DIR_KEYS, DIR_KEYS[1:] + [(1e9, None)]):
        t1 = nxt[0]
        if t < t0 - 0.25 or t >= t1 + 0.25:
            continue
        a_in = 1.0 if t0 == 0 else ease((t - (t0 - 0.25)) / 0.5)
        a_out = 1 - ease((t - (t1 - 0.25)) / 0.5)
        sets.append((k0, a_in*a_out))
    for k, aa in sets:
        aa *= fade_all*0.75
        if aa <= 0.004:
            continue
        for txt, where in DIR_SETS[k]:
            kw = {'L': dict(x=m.SAFE_L + 5, cy=1062), 'R': dict(right=m.SAFE_R - 5, cy=1062), 'T': dict(right=m.SAFE_R - 5, cy=384),
                  'L2': dict(x=m.SAFE_L + 5, cy=960), 'R2': dict(right=m.SAFE_R - 5, cy=960),
                  'T2': dict(cx=540, cy=622), 'B2': dict(cx=540, cy=1300)}[where]
            m.put(base, txt, 27, 700, m.WHITE, a=aa, kind='fade', **kw)


def cl01(x):
    return min(1.0, max(0.0, x))


# --- 1コマ --------------------------------------------------------------------------
def scene(t):
    """t（0〜T_FIN）の3Dの絵（RGB）と、その場の (光の素材, 光の強さ, カメラ)。"""
    if t < Z1:
        s3, c3 = cam_03(t)
        im = render(still('03', half=s3 < 0.55), s3, c3)
        w17 = 1 - ease((t - X17[0]) / (X17[1] - X17[0]))     # 人の体 → 03
        if w17 > 0.004:
            p17 = render17(s3, c3)
            dk = DARK17[2]*ease((t - DARK17[0]) / (DARK17[1] - DARK17[0]))
            if dk > 0.004:
                p17 = Image.blend(p17, Image.new('RGB', (W, H), FILL), dk)
            im = Image.blend(im, p17, w17)
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
    # 電極は人の体の場面から 04 で止まるまで、ずっと同じ所についている（03 のカメラ → 04 のカメラ）
    a4 = hold_amp('04', t)
    if t < Z1 + 0.3 and a4 < 0.999:
        s3, c3 = cam_03(min(t, Z1))
        draw_pads(m, im, '03', s3, c3, 1 - a4)
    for k in ('04', '07', '09'):
        amp = hold_amp(k, t)
        if amp > 0.004:
            s_, c_ = cam_main(min(t, T_FIN))
            draw_pads(m, im, k, s_, c_, amp)
    for k in ('04', '07', '09', '08'):
        label_pill(m, im, k, hold_amp(k, t))
    view_icon(m, im, t)
    dir_labels(m, im, t)
    qa = ease((t - Q_T[0] + 0.01) / 0.2) * (1 - ease((t - (Q_T[1] - 0.35)) / 0.35))
    shadow_text(m, im, m.QUESTION, 66, 900, m.YELLOW, 333, a=qa if t > 0.005 else 1.0)
    return im


# --- 13：足もとから真上に見上げた絵（1376×768・横長。ElevenLabs）。縦の画面のまん中に置き、上下は暗い紺 ----------
IMG13 = os.path.join(A3, '13_真下から_心臓_EL.png')
FILL13 = (1, 4, 36)                      # 絵の端の色
# 心室のかたまりの外形（13 の絵の px。赤い所を測った。左の右房のふくらみと大血管は除く）：x605〜907・y197〜433
HEART13 = ((756.0, 315.0), (302.0, 236.0))
S13_FULL = W / 1376
C13_FULL = (0.0, 1000 - S13_FULL*384)     # 縦のまん中より少し下（左上の目印と重ねない）
_I13 = None


def img13():
    global _I13
    if _I13 is None:
        im = Image.open(IMG13).convert('RGBA')
        w, h = im.size
        a = np.full((h, w), 255.0)
        f = 40                               # 端をなじませる
        ramp = np.clip(np.arange(f)/f, 0, 1)
        a[:f] *= ramp[:, None]; a[-f:] *= ramp[::-1][:, None]
        a[:, :f] *= ramp[None, :]; a[:, -f:] *= ramp[::-1][None, :]
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
        _I13 = im
    return _I13


def render13(s, c):
    out = Image.new('RGBA', (W, H), FILL13 + (255,))
    k = 1/s
    lay = img13().transform((W, H), Image.AFFINE, (k, 0, -k*c[0], 0, k, -k*c[1]), resample=Image.BICUBIC,
                            fillcolor=(0, 0, 0, 0))
    out.alpha_composite(lay)
    return out.convert('RGB')


# --- 説明の場面：横向きの全身 14（1376×768・左＝前を向いて立つ透けた青い人。ElevenLabs）と、目の移動 -------------
IMG14 = os.path.join(A3, '14_横向き全身_EL.png')
# 14 の絵の px：体 x617〜754・y13〜759、心臓（赤い所）x658〜693・y187〜234（中心 677,210）
S14 = 990 / 746                           # 頭〜足を y300〜1290 に（足もとの目と、下の字幕の枠 y1400〜 を重ねない）
C14 = (500 - S14*685, 300 - S14*13)
FEET14_Y = S14*759 + C14[1]
HEART14 = (677.0, 210.5, 35.0)            # 心臓の中心と幅（14 の絵の px）
_I14 = None


def img14():
    global _I14
    if _I14 is None:
        _I14 = Image.open(IMG14).convert('RGB')
    return _I14


# --- 動画15（1280×720・24fps・8秒）：14 の横向きの全身 → 回って → 13 と同じ足もとから見上げる絵 -----------------------
# 最初のコマ＝14 を 0.930倍＋下へ 3px、6秒〜＝13 を 0.930倍＋下へ 3px（体の外形を色で測った）。
# 4.4秒（105コマ）〜6.3秒（150コマ）は「正面の上半身」の不自然なコマなので使わず、105 → 153 を重ねて切り替える
# 回る動画：16（Omni で作り直し）があればそれを、なければ 15。
# 16（Omni・1280×720・24fps・10秒・240コマ）：0〜2秒 横向き → 2〜4.6秒 体の前へ回る → 4.6〜8.3秒 足のあいだから見上げる
#   → 8.3〜9秒 足もとからの断面へ → 9〜10秒 13 と同じ絵。足が通りすぎる所はゆっくり、横向きの所は速く
ROT_SRCS = {'16': ('16_回転_横から足もと_omni.mp4', [(0.0, 1), (0.10, 48), (0.33, 110), (0.78, 205), (1.0, 240)]),
            '15': ('15_回転_横から足もと_EL.mp4', [(0.0, 1), (0.62, 105), (0.78, 153), (1.0, 185)])}
ROT_ID = '16' if os.path.exists(os.path.join(A3, ROT_SRCS['16'][0])) else '15'
# 動画のコマ px ＝ 絵の px × K ＋ (ox, oy)。体の外形を色で測った：最初のコマ＝14（体の上下 14〜719 ⇔ 13〜759）、
# 最後のコマ＝13（体 x43〜1236・y22〜689 ⇔ x48〜1327・y18〜745。心臓の位置も数px でそろう）
ROT_FIT = {'16': ((0.945, -6.0, 1.7), (0.925, -1.4, 5.4)), '15': ((0.930, 0.0, 3.0), (0.930, 0.0, 3.0))}
ROT_MAP = ROT_SRCS[ROT_ID][1]             # ROT の進み → コマ番号（None＝最初から最後まで一定の速さ）
N_ROT = 192
_V15 = {}


def ensure_v15():
    global N_ROT, ROT_MAP
    d = os.path.join(CACHE, 'rot' + ROT_ID)
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(os.path.join(d, '001.jpg')):
        subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-i', os.path.join(A3, ROT_SRCS[ROT_ID][0]), '-q:v', '2',
                        os.path.join(d, '%03d.jpg')], check=True)
    N_ROT = len([f for f in os.listdir(d) if f.endswith('.jpg')])
    if ROT_MAP is None:
        ROT_MAP = [(0.0, 1), (0.5, N_ROT//2), (0.51, N_ROT//2), (1.0, N_ROT)]


# 足を消す（でんさん「足のあいだから見上げる絵になる瞬間は、足を取ってOK」）：胴体（骨盤より上）と腕・心臓を囲む楕円の外を、
# 動画の地の紺へやわらかくなじませる。楕円の位置・大きさはコマ番号でなめらかに動かす（動画16 のコマ px。コマを見て決めた）
LEG_KEYS = [  # (コマ, 中心x, 中心y, 半径x, 半径y)
    (108, 640, 190, 430, 330), (128, 640, 170, 400, 300), (140, 640, 150, 380, 270), (170, 640, 125, 540, 235),
    (194, 640, 205, 540, 195), (205, 640, 250, 420, 175), (212, 640, 360, 500, 380), (222, 640, 360, 700, 470)]
# 消す強さ：3（正面寄りの全身・108コマ）から 4（足のあいだから見上げる・176コマ）へ移るあいだに、足をだんだん透かして消す。
# 足先が大きく手前に入るコマ（180〜）では、もう見えない。断面（212〜）になったら抜く
LEG_ON = [(108, 0.0), (176, 1.0), (212, 1.0), (222, 0.0)]
ROT_BG = (2, 9, 29)
ROT_ZOOM = [(0.0, 1.0, 0.0, 0.0), (1.0, 1.0, 0.0, 0.0)]   # (u, 倍率, ずれx, ずれy)。いまは足していない（お腹付近からのアップにするならここ）
_LEGGRID = None


def leg_strength(i):
    return float(np.interp(i, [k[0] for k in LEG_ON], [k[1] for k in LEG_ON])) if ROT_ID == '16' else 0.0


def leg_mask(i):
    """残す所の重み（0〜1、1280×720）。"""
    global _LEGGRID
    if _LEGGRID is None:
        yy, xx = np.mgrid[0:720:4, 0:1280:4]
        _LEGGRID = (xx.astype(np.float32), yy.astype(np.float32))
    xx, yy = _LEGGRID
    ks = LEG_KEYS
    cx, cy, rx, ry = [float(np.interp(i, [k[0] for k in ks], [k[j] for k in ks])) for j in range(1, 5)]
    r = np.sqrt(((xx - cx)/rx)**2 + ((yy - cy)/ry)**2)
    keep = 1 - np.clip((r - 0.82)/0.36, 0, 1)
    keep = keep*keep*(3 - 2*keep)
    st = leg_strength(i)
    st = st*st*(3 - 2*st)
    keep = 1 - st*(1 - keep)
    return Image.fromarray((keep*255).astype(np.uint8)).resize((1280, 720), Image.BILINEAR)


def v15(i):
    i = int(min(N_ROT, max(1, i)))
    if i not in _V15:
        if len(_V15) > 30:
            _V15.clear()
        im = Image.open(os.path.join(CACHE, 'rot' + ROT_ID, f'{i:03d}.jpg')).convert('RGB')
        if leg_strength(i) > 0.004:
            im = Image.composite(im, Image.new('RGB', im.size, ROT_BG), leg_mask(i))
        _V15[i] = im
    return _V15[i]


def cam15_from(s_img, c_img, fit):
    """14 か 13 の絵のカメラ (s, c) と同じ見え方になる、回る動画のコマのカメラ。fit＝(K, ox, oy)。"""
    k, ox, oy = fit
    s = s_img / k
    return s, (c_img[0] - s*ox, c_img[1] - s*oy)


def render15(img, s, c):
    k = 1/s
    out = Image.new('RGBA', (W, H), (2, 9, 29, 255))   # 回る動画の地の色（コマの隅を測った）
    lay = img.convert('RGBA')
    w, h = lay.size
    a = np.full((h, w), 255.0)
    f = 110                              # 端を広くなじませる（動画の地の色と紺の差を見せない）
    ramp = np.arange(f)/f
    a[:f] *= ramp[:, None]; a[-f:] *= ramp[::-1][:, None]
    a[:, :f] *= ramp[None, :]; a[:, -f:] *= ramp[::-1][None, :]
    lay.putalpha(Image.fromarray(a.astype(np.uint8)))
    out.alpha_composite(lay.transform((W, H), Image.AFFINE, (k, 0, -k*c[0], 0, k, -k*c[1]), resample=Image.BICUBIC,
                                      fillcolor=(0, 0, 0, 0)))
    return out.convert('RGB')


def rot_frame(t):
    """ROT のあいだの動画15 の絵（RGB の全画面）。カメラは 14 に合わせた所 → 13 に合わせた所（倍率は対数）。"""
    u = min(1.0, max(0.0, (t - T_ROT) / ROT_D))
    fa, fb = ROT_FIT[ROT_ID]
    sa, ca = cam15_from(S14, C14, fa)
    sb, cb = cam15_from(S13_FULL, C13_FULL, fb)
    e = ease(u)
    qa = (sa*640 + ca[0], sa*360 + ca[1])
    qb = (sb*640 + cb[0], sb*360 + cb[1])
    sc = math.exp(math.log(sa) + (math.log(sb) - math.log(sa))*e)
    q = (qa[0] + (qb[0] - qa[0])*e, qa[1] + (qb[1] - qa[1])*e)
    # 3→4（正面寄り→足のあいだから見上げる）の寄り・中心をあとから足すとき用（ROT の進み u ごとの倍率・画面のずれ px）
    zk = [k[0] for k in ROT_ZOOM]
    z = float(np.interp(u, zk, [k[1] for k in ROT_ZOOM]))
    q = (q[0] + float(np.interp(u, zk, [k[2] for k in ROT_ZOOM])), q[1] + float(np.interp(u, zk, [k[3] for k in ROT_ZOOM])))
    sc *= z
    c = (q[0] - sc*640, q[1] - sc*360)
    fi = float(np.interp(u, [k[0] for k in ROT_MAP], [k[1] for k in ROT_MAP]))
    return render15(v15(round(fi)), sc, c)        # 1コマずつ（前後のコマは混ぜない）


def heart14_screen():
    return S14*HEART14[0] + C14[0], S14*HEART14[1] + C14[1], S14*HEART14[2]


def render14(s, c):
    k = 1/s
    return img14().transform((W, H), Image.AFFINE, (k, 0, -k*c[0], 0, k, -k*c[1]), resample=Image.BICUBIC, fillcolor=FILL13)


def render_locked(photo, p_src, w_src, q, hw):
    """photo（画面の絵）の中の心臓（中心 p_src・幅 w_src）が、画面の q・幅 hw になるように拡大縮小した絵。"""
    r = hw / w_src
    return photo.transform((W, H), Image.AFFINE, (1/r, 0, p_src[0] - q[0]/r, 0, 1/r, p_src[1] - q[1]/r),
                           resample=Image.BICUBIC, fillcolor=FILL13)


def eye_pose(u):
    """u 0〜1：目の位置と向き（0＝右・90＝上）。胸の前（画面の左）→ 足もとの下（上を向く）。"""
    hx, hy, _ = heart14_screen()
    cx, cy = 492.0, hy                    # 弧の中心：足もとの真上・心臓の高さ
    rx, ry = cx - (hx - 180), FEET14_Y + 70 - hy
    th = math.radians(180 + 90*u)
    return cx + rx*math.cos(th), cy - ry*math.sin(th), 8 + (90 - 8)*u


def draw_eye(d, x, y, ang, a):
    col = (255, 214, 64, int(255*a))
    th = math.radians(ang)
    ux, uy = math.cos(th), -math.sin(th)
    pts = []
    for j in range(24):
        q = 2*math.pi*j/24
        ex, ey = 34*math.cos(q), 18*math.sin(q)
        pts.append((x + ex*ux - ey*uy, y + ex*uy + ey*ux))
    d.polygon(pts, fill=(8, 18, 16, int(230*a)), outline=col, width=5)
    d.ellipse([x - 9 + ux*8, y - 9 + uy*8, x + 9 + ux*8, y + 9 + uy*8], fill=col)
    tip = (x + ux*64, y + uy*64)
    d.polygon([tip, (tip[0] - ux*18 - uy*11, tip[1] - uy*18 + ux*11), (tip[0] - ux*18 + uy*11, tip[1] - uy*18 - ux*11)], fill=col)


def draw_sight(d, x, y, ang, length, a):
    th = math.radians(ang)
    ux, uy = math.cos(th), -math.sin(th)
    col = (255, 236, 160, int(230*a))
    s0 = 70
    k = s0
    while k < s0 + length:
        k1 = min(k + 18, s0 + length)
        d.line([(x + ux*k, y + uy*k), (x + ux*k1, y + uy*k1)], fill=col, width=6)
        k += 32


def sight_done(t):
    """視線が心臓に届いた割合（0〜1）。"""
    return min(1.0, max(0.0, (t - (T_EX2 + 0.55*EX2_D)) / (0.45*EX2_D)))


def explain_layer(m, t, dy=0.0):
    """目・視線・字（RGBA の全画面）。dy：上へ流れるときのずれ。"""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay, 'RGBA')
    a = ease((t - (T_EX1H - 0.2)) / 0.4)
    if a <= 0.004:
        return lay
    a *= 1 - ease((t - T_X15) / X15_D)    # 目と視線は、動画15 で回るあいだは消す（動画のカメラ自体が目線）
    if a <= 0.004:
        return lay
    u2 = ease((t - T_EX2) / EX2_D)
    x, y, ang = eye_pose(u2)
    hx, hy, _ = heart14_screen()
    if u2 > 0.55:
        draw_sight(d, x, y + dy, ang, sight_done(t)*(y - hy - 30 - 70), a)
    draw_eye(d, x, y + dy, ang, a)
    return lay


def photo08():
    """T_FIN で止まった 08 の絵（RGB）と、そのときの心臓の画面上の中心・幅。"""
    s, c = cam_main(T_FIN)
    (hx, hy), hw = HEART['08']
    return render(still('08', half=s < 0.5), s, c), (s*hx + c[0], s*hy + c[1]), s*hw
