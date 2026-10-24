"""第29弾：心臓を抜いた左側面（20b）に、心臓だけ（22・左から）を置く。

20b は 18（正面）と高さをそろえてある（胸骨の上端 y1230・肋骨のいちばん下 y3855。ずれ ±25px）。
なので、正面で肋骨に合わせて決めた高さをそのまま使う：心臓の一番下 y2595、V4〜V6 の高さ y2515（第5肋間）。
前後（画面の左＝胸、右＝背中）は y2515 の体の幅で決める：皮膚の前 x352・後ろ x2658、胸骨の後ろ x≈672、椎体の前 x≈2184。
  心臓の前の縁 ＝ 胸骨のすぐ後ろ（x690）。心尖は前下（左側面で見ると、長軸は後ろ上→前下）
大きさは正面と同じ倍率（21 を置いた 0.553 と、22 の高さから出した倍率がほぼ同じ）。
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

A = 'assets3d/追加_1024/'
TH = -18.0                       # 時計回りに少し回して心尖を前（画面の左）へ
S = 0.553
FRONT_T, BOTTOM_T = 690, 2595
VESSEL_FADE = (1330, 1470)


def heart_layer():
    h = Image.open(A + '22_心臓だけ_左から_4K.png').convert('RGB')
    h = h.rotate(TH, resample=Image.BICUBIC, center=(1500, 2400))
    a = np.asarray(h).astype(np.float32)
    alpha = np.clip((a.max(2) - 20) / 50, 0, 1)
    m = alpha > 0.5
    ys, xs = np.nonzero(m)
    rows = range(1700, ys.max())
    lo = min(np.nonzero(m[y])[0].min() for y in rows if m[y].any())
    ox, oy = FRONT_T - lo*S, BOTTOM_T - ys.max()*S
    rgba = np.dstack([a, alpha*255]).astype(np.uint8)
    im = Image.fromarray(rgba, 'RGBA')
    im = im.resize((round(im.width*S), round(im.height*S)), Image.LANCZOS)
    lay = Image.new('RGBA', (3072, 5504), (0, 0, 0, 0))
    lay.paste(im, (round(ox), round(oy)), im)
    L = np.asarray(lay).astype(np.float32)
    yy = np.arange(5504)[:, None]
    L[..., 3] *= np.clip((yy - VESSEL_FADE[0]) / (VESSEL_FADE[1] - VESSEL_FADE[0]), 0, 1)
    mm = L[..., 3] > 127
    yy2, xx2 = np.nonzero(mm)
    k = np.argmax(-xx2 + yy2)    # 前下の端（心尖）
    return L, dict(front=xx2.min(), back=xx2.max(), bottom=yy2.max(), apex=(xx2[k], yy2[k]))


def compose():
    body = np.asarray(Image.open(A + '20b_左側面_心臓なし_4K.png').convert('RGB')).astype(np.float32)
    L, info = heart_layer()
    ha = L[..., 3:4] / 255 * 0.9
    out = body*(1 - ha) + L[..., :3]*ha
    bone = np.clip((body[..., 0:1] - 95) / 110, 0, 1) * 0.80
    bone = np.asarray(Image.fromarray((bone[..., 0]*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None]/255
    out = out*(1 - bone*ha) + body*(bone*ha)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), info


if __name__ == '__main__':
    im, info = compose()
    dst = sys.argv[1] if len(sys.argv) > 1 else A + '26_左側面_心臓を肋骨に合わせた_4K.png'
    im.save(dst)
    print(dst, info)
