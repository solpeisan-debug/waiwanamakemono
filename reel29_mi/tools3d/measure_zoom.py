"""回る動画の、コマごとの寄り・引き（縦の大きさ）を測る（第29弾）。
体が縦の軸のまわりに回っても、高さ（肋骨・鎖骨・骨盤の縦の並び）は変わらないので、
コマの横方向の平均（縦の明るさの並び）を前のコマと比べて、縦の倍率とずれを求めてつないでいく。
出力：out/cache3d/<名前>/zoom.json  [[倍率, 縦のずれ px（1080×1920 の画面で）], ...]（最初のコマ＝[1, 0]）
"""
import json
import os
import sys

import numpy as np
from PIL import Image


def profile(path, w=270, h=480):
    a = np.asarray(Image.open(path).convert('L').resize((w, h), Image.BILINEAR), np.float32)
    p = a[:, int(w*0.15):int(w*0.85)].mean(1)
    return (p - p.mean()) / (p.std() + 1e-6)


def fit(p0, p1, cy=240):
    """p1 を倍率 k・ずれ dy で変えたとき p0 にいちばん合う (k, dy)。"""
    y = np.arange(len(p0), dtype=np.float32)
    best = (-9, 1.0, 0.0)
    for k in np.arange(0.96, 1.04001, 0.002):
        for dy in np.arange(-8, 8.01, 0.5):
            src = (y - cy - dy)/k + cy          # p1 のこの位置が p0 の y に来る
            m = (src > 2) & (src < len(p0) - 3)
            v = np.interp(src[m], y, p1)
            c = float(np.corrcoef(p0[m], v)[0, 1])
            if c > best[0]:
                best = (c, k, dy)
    return best


def main(d):
    fs = sorted(f for f in os.listdir(d) if f.endswith('.jpg'))
    ps = [profile(os.path.join(d, f)) for f in fs]
    S, D, out = 1.0, 0.0, [[1.0, 0.0]]
    for i in range(1, len(ps)):
        c, k, dy = fit(ps[i - 1], ps[i])
        # p_i を k 倍・dy ずらすと p_{i-1} に合う → コマ i はコマ i-1 より 1/k 倍の大きさ
        S, D = S/k, (D - dy)/k
        out.append([S, D*4])                    # 480 → 1920
    json.dump(out, open(os.path.join(d, 'zoom.json'), 'w'))
    print(d, ' '.join(f'{o[0]:.3f}' for o in out[::8]), f'last {out[-1][0]:.3f}')


if __name__ == '__main__':
    for d in sys.argv[1:]:
        main(d)
