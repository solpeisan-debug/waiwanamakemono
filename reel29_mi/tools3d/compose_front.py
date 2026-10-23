"""第29弾：心臓を抜いた正面の体（18）に、心臓だけ（21）を肋骨に合わせて置く。

位置は日本光電「電極装着のポイント」の肋間と線（03/18 の座標。intro3d.py の ELEC03・VLINES03 と同じ）で決める：
  心臓の右の縁 ＝ 胸骨右縁（x1425）より少し右（x1335）
  心臓の左の縁の一番外 ＝ 左鎖骨中線（x2320）のわずか内側（x2340。V4 が心尖の上に来る）
  心尖 ＝ 左第5肋間（鎖骨中線の上で y2515）の高さ
使い方：python3 tools3d/compose_front.py [出力.png]
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

A = 'assets3d/追加_1024/'
TH = 10.0                       # 心臓を少し寝かせる（度、反時計回り）。長軸を左下へ
RB_T, LMAX_T, APEX_Y_T = 1335, 2340, 2550
VESSEL_FADE = (1330, 1470)      # 大血管の枝の切り口（胸骨柄の上）を、この高さで消していく


def heart_layer():
    h = Image.open(A + '21_心臓だけ_正面_4K.png').convert('RGB')
    h = h.rotate(TH, resample=Image.BICUBIC, center=(1600, 2400))
    a = np.asarray(h).astype(np.float32)
    alpha = np.clip((a.max(2) - 20) / 50, 0, 1)
    m = alpha > 0.5
    ys, xs = np.nonzero(m)
    rows = range(1800, ys.max())
    rb = min(np.nonzero(m[y])[0].min() for y in rows if m[y].any())
    lmax = max(np.nonzero(m[y])[0].max() for y in rows if m[y].any())
    k = np.argmax(xs + ys)
    apex = (xs[k], ys[k])
    s = (LMAX_T - RB_T) / (lmax - rb)
    ox, oy = RB_T - rb*s, APEX_Y_T - apex[1]*s
    W, H = 3072, 5504
    rgba = np.dstack([a, alpha*255]).astype(np.uint8)
    im = Image.fromarray(rgba, 'RGBA')
    im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lay.paste(im, (round(ox), round(oy)), im)
    L = np.asarray(lay).astype(np.float32)
    yy = np.arange(H)[:, None]
    fade = np.clip((yy - VESSEL_FADE[0]) / (VESSEL_FADE[1] - VESSEL_FADE[0]), 0, 1)
    L[..., 3] *= fade
    info = dict(scale=s, apex=(apex[0]*s+ox, apex[1]*s+oy), rb=RB_T, lmax=LMAX_T)
    return L, info


def compose():
    body = np.asarray(Image.open(A + '18_正面_心臓なし_4K.png').convert('RGB')).astype(np.float32)
    L, info = heart_layer()
    ha = L[..., 3:4] / 255
    out = body*(1 - ha) + L[..., :3]*ha
    # 肋骨・胸骨は心臓の手前：体の白い骨（R が高い）を、心臓の上に透かして重ねる
    bone = np.clip((body[..., 0:1] - 95) / 110, 0, 1) * 0.80
    bone = np.asarray(Image.fromarray((bone[..., 0]*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None]/255
    out = out*(1 - bone*ha) + body*(bone*ha)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), info


if __name__ == '__main__':
    im, info = compose()
    dst = sys.argv[1] if len(sys.argv) > 1 else A + '24_正面_心臓を肋骨に合わせた_4K.png'
    im.save(dst)
    print(dst, info)
