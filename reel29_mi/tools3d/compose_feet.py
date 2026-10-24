"""第29弾：心臓を抜いた「足もとから見上げた体」（27）に、心臓だけ（28・下から）を置く。

27 は 13 と同じ構図の 4K（5504×3072。13 の4倍）。画面の上＝胸（前）、下＝背中、画面の左＝体の右。
大きさ・位置は、正面（compose_front.py）・左側面（compose_left.py）で肋骨に合わせた心臓と同じ割合にする：
  左右：胸郭の内側の幅（x800〜4720、正中 x2750）に対して、心臓の右の縁 ＝ 胸骨右縁（x2560）から幅の4%外（x2403）、
        左の縁の一番外 ＝ 正中から片側の幅の65%（正面で左鎖骨中線より少し外まで出ている割合と同じ）→ x4122
  前後：心臓の前の縁 ＝ 胸骨のすぐ後ろ（y380）、後ろの縁 ＝ 胸骨の後ろ〜椎体の前（y380〜1920）の66%（左側面と同じ割合）→ y1410
この絵は足もとから見上げているので前後が縮んで見える（体も同じだけ縮んでいる）。心臓も同じ倍率で前後を縮める。
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

A = 'assets3d/追加_1024/'
X0, X1, Y0, Y1 = 2403, 4122, 380, 1410


def compose():
    body = np.asarray(Image.open(A + '27_足もとから_心臓なし_4K.png').convert('RGB')).astype(np.float32)
    h = Image.open(A + '28_心臓だけ_下から_4K.png').convert('RGB')
    a = np.asarray(h).astype(np.float32)
    alpha = np.clip((a.max(2) - 20) / 50, 0, 1)
    ys, xs = np.nonzero(alpha > 0.5)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    rgba = Image.fromarray(np.dstack([a, alpha*255]).astype(np.uint8), 'RGBA').crop(box)
    rgba = rgba.resize((X1 - X0, Y1 - Y0), Image.LANCZOS)
    lay = Image.new('RGBA', (body.shape[1], body.shape[0]), (0, 0, 0, 0))
    lay.paste(rgba, (X0, Y0), rgba)
    L = np.asarray(lay).astype(np.float32)
    ha = L[..., 3:4] / 255 * 0.92
    out = body*(1 - ha) + L[..., :3]*ha
    bone = np.clip((body[..., 0:1] - 95) / 110, 0, 1) * 0.75
    bone = np.asarray(Image.fromarray((bone[..., 0]*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)[..., None]/255
    out = out*(1 - bone*ha) + body*(bone*ha)
    m = L[..., 3] > 127
    yy, xx = np.nonzero(m)
    k = np.argmax(xx - yy)
    info = dict(box=(X0, Y0, X1, Y1), apex=(int(xx[k]), int(yy[k])))
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), info


if __name__ == '__main__':
    im, info = compose()
    dst = sys.argv[1] if len(sys.argv) > 1 else A + '34_足もとから_心臓を肋骨に合わせた_4K.png'
    im.save(dst)
    print(dst, info)
