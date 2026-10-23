"""第29弾：心臓を抜いた背面の体（19）に、心臓だけ（23・後ろから）を置く。

19 は 02 から作った背面で、18（正面）と体の位置・大きさが同じ（鎖骨・肩の高さが一致）。
後ろから見ると患者さんの左は画面の左。心臓の外形は、正面（compose_front.py）で肋骨に合わせた外形を左右に写す：
  正面の右の縁 x1335 → 背面 x1737、正面の左の縁の一番外 x2340 → 背面 x732、心臓の一番下 y2595
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

A = 'assets3d/追加_1024/'
L_T, R_T, BOTTOM_T = 3072 - 2340, 3072 - 1335, 2595
VESSEL_FADE = (1330, 1470)


def heart_layer():
    h = Image.open(A + '23_心臓だけ_後ろから_4K.png').convert('RGB')
    a = np.asarray(h).astype(np.float32)
    alpha = np.clip((a.max(2) - 20) / 50, 0, 1)
    m = alpha > 0.5
    ys, xs = np.nonzero(m)
    rows = range(1550, ys.max())
    lo = min(np.nonzero(m[y])[0].min() for y in rows if m[y].any())
    hi = max(np.nonzero(m[y])[0].max() for y in rows if m[y].any())
    s = (R_T - L_T) / (hi - lo)
    ox, oy = L_T - lo*s, BOTTOM_T - ys.max()*s
    rgba = np.dstack([a, alpha*255]).astype(np.uint8)
    im = Image.fromarray(rgba, 'RGBA')
    im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    lay = Image.new('RGBA', (3072, 5504), (0, 0, 0, 0))
    lay.paste(im, (round(ox), round(oy)), im)
    L = np.asarray(lay).astype(np.float32)
    yy = np.arange(5504)[:, None]
    L[..., 3] *= np.clip((yy - VESSEL_FADE[0]) / (VESSEL_FADE[1] - VESSEL_FADE[0]), 0, 1)
    return L, dict(scale=s)


def compose():
    body = np.asarray(Image.open(A + '19_背面_心臓なし_4K.png').convert('RGB')).astype(np.float32)
    L, info = heart_layer()
    ha = L[..., 3:4] / 255 * 0.78           # 後ろからは、背骨・肺ごしに透けて見える
    out = body*(1 - ha) + L[..., :3]*ha
    # 背骨・肋骨・肩甲骨は心臓より手前（見ている人の側）
    bone = np.clip((body[..., 0:1] - 80) / 100, 0, 1) * 0.90
    bone = np.asarray(Image.fromarray((bone[..., 0]*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None]/255
    out = out*(1 - bone*ha) + body*(bone*ha)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), info


if __name__ == '__main__':
    im, info = compose()
    dst = sys.argv[1] if len(sys.argv) > 1 else A + '25_背面_心臓を肋骨に合わせた_4K.png'
    im.save(dst)
    print(dst, info)
