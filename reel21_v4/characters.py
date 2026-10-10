"""第21弾v4：波形の部品（Pくん・Tちゃん・QRSくん・PVCくん）の顔と手（白い手ぶくろ）、小物。

make_reel21v4.frame から毎コマ呼ばれる（draw(m, img, t, layer)）。
- 波形は1本で、ずっと同じ大きさ・同じ速さ。顔は「こぶの中に、線にふれずに入る」ときだけ描く（fit_hump：形で確かめる。
  --check で全編を 0.1秒ごとに確かめる）。顔は動かさない（こぶからはみ出さないように）。幅の狭い QRS は顔が入らないので、手だけ
- 動きは「その拍が画面の右端に入ってからの時間」と「ブロックの時刻」で決める（録音に合わせて秒数を組み直してもついていく）
- ④⑤（心停止）はまじめな顔だけ。心静止の線には顔を描かない
- 手は、昔ながらのアニメ風の白い手ぶくろ（ふつうの形。特定のキャラクターではない）。腕は細い線
"""
import math

import numpy as np
from PIL import Image, ImageDraw

DK = (6, 14, 12)              # 縁どり
LT = (242, 247, 245)          # 顔・手の線
EYE = (250, 252, 252)
SWEAT = (140, 205, 255)
SS = 3
NARROW = False                # 目を寄せた細い顔（幅の広い QRS・PVC など、こぶが細いとき）
SPIN = 0.0                    # ぐるぐる目の回り具合（顔は回さない：こぶからはみ出さないように）
DRY = False                   # True：描かずに、顔の位置だけ記録する（--check 用）
FACE_LOG = []
LAYER = 'any'                 # 'under'：顔と手（波形の線の下）／'over'：吹き出し・小物（線の上）／'any'：両方
FACE_K = 1.0                  # 顔の大きさの倍率（r は描く顔の半径。顔の幅は約 1.3r）


def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(u):
    u = cl(u)
    return u*u*(3 - 2*u)


def win(x, a, b, fi=0.25, fo=0.25):
    """a〜b のあいだ 1（前後 fi・fo 秒でなめらかに）。"""
    return ease((x - a) / fi) * (1 - ease((x - (b - fo)) / fo))


# --- 下書き（Pad） ---------------------------------------------------------------
class Pad:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0 = int(math.floor(x0)), int(math.floor(y0))
        self.w = max(2, int(math.ceil(x1)) - self.x0)
        self.h = max(2, int(math.ceil(y1)) - self.y0)
        self.im = Image.new('RGBA', (self.w*SS, self.h*SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im, 'RGBA')

    def P(self, x, y):
        return ((x - self.x0)*SS, (y - self.y0)*SS)

    def line(self, pts, col, w, a=255, cap=True):
        q = [self.P(*p) for p in pts]
        ww = max(1, int(round(w*SS)))
        self.d.line(q, fill=col + (a,), width=ww, joint='curve')
        if cap:
            r = ww/2
            for (x, y) in (q[0], q[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=col + (a,))

    def ell(self, x, y, rx, ry, fill=None, outline=None, w=1.0, a=255):
        X, Y = self.P(x, y)
        self.d.ellipse((X - rx*SS, Y - ry*SS, X + rx*SS, Y + ry*SS),
                       fill=None if fill is None else fill + (a,),
                       outline=None if outline is None else outline + (a,),
                       width=max(1, int(round(w*SS))))

    def poly(self, pts, fill=None, outline=None, w=1.0, a=255):
        self.d.polygon([self.P(*p) for p in pts], fill=None if fill is None else fill + (a,),
                       outline=None if outline is None else outline + (a,), width=max(1, int(round(w*SS))))

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, w=1.0, a=255):
        A, B = self.P(x0, y0); C, D = self.P(x1, y1)
        self.d.rounded_rectangle((A, B, C, D), radius=r*SS, fill=None if fill is None else fill + (a,),
                                 outline=None if outline is None else outline + (a,), width=max(1, int(round(w*SS))))

    def paste(self, img, a=1.0):
        if a <= 0.01 or DRY:
            return
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        if a < 0.999:
            im.putalpha(im.getchannel('A').point(lambda v: int(v*a)))
        W, H = img.size
        x0, y0 = self.x0, self.y0
        cx0, cy0 = max(0, -x0), max(0, -y0)
        cx1, cy1 = min(self.w, W - x0), min(self.h, H - y0)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        if (cx0, cy0, cx1, cy1) != (0, 0, self.w, self.h):
            im = im.crop((cx0, cy0, cx1, cy1))
        img.alpha_composite(im, (x0 + cx0, y0 + cy0))


def stroke(pad, pts, w, a=255, col=LT):
    """縁どりつきの線（2回目の線で描くときは、先に縁だけ全部描くと線どうしの間に縁が入らない）。"""
    pad.line(pts, DK, w + 3.2, a=int(a*0.85))
    pad.line(pts, col, w, a=a)


def arc_pts(cx, cy, rx, ry, a0, a1, n=14, rot=0.0, ox=0.0, oy=0.0):
    out = []
    for k in range(n + 1):
        th = math.radians(a0 + (a1 - a0)*k/n)
        x, y = rx*math.cos(th), ry*math.sin(th)
        out.append(_rot(x + cx - ox, y + cy - oy, rot, ox, oy))
    return out


def _rot(x, y, rot, ox, oy):
    """(x, y) は中心 (ox, oy) からのずれ。回して、画面の座標に戻す。"""
    c, s = math.cos(rot), math.sin(rot)
    return (ox + x*c - y*s, oy + x*s + y*c)


# --- 顔 -----------------------------------------------------------------------------
# 表情：smile・happy（^^）・calm（目を閉じてほほえむ）・ah（「あっ」）・oops（「あらっ」汗）・dizzy（ぐるぐる目。トルサードだけ）・
#       worried・serious・angry・surprised・troubled・tired・determined
def _face_layers(cx, cy, r, expr, look=0.0, rot=0.0):
    """顔の線を [(種類, 点列 or 円, 太さ)] で返す。種類：'line'（縁どりつきの線）・'eye'（白目＋瞳）・'drop'（汗）・'dot'。"""
    L = []
    ex, ey = (0.30 if NARROW else 0.42)*r, -0.08*r
    def P(x, y):
        return _rot(x, y, rot, cx, cy)
    lw = max(1.8, 0.14*r)
    closed = expr in ('happy', 'calm')
    half = expr in ('tired',)
    for sgn in (-1, 1):
        x0 = sgn*ex
        if expr == 'dizzy':
            pts = []
            for k in range(22):
                th = k*0.55 + (SPIN if sgn > 0 else -SPIN)
                rr = 0.03*r + 0.012*r*k
                pts.append(P(x0 + rr*math.cos(th), ey + rr*math.sin(th)))
            L.append(('line', pts, lw*0.8))
        elif closed:
            if expr == 'happy':      # ^
                L.append(('line', [P(x0 - 0.15*r, ey + 0.06*r), P(x0, ey - 0.1*r), P(x0 + 0.15*r, ey + 0.06*r)], lw))
            else:                    # ‿
                L.append(('line', [P(x0 + 0.15*r*math.cos(math.radians(a)), ey - 0.02*r + 0.11*r*math.sin(math.radians(a)))
                                   for a in range(0, 181, 20)], lw))
        else:
            big = 1.18 if expr in ('surprised', 'oops', 'ah') else 1.0
            L.append(('eye', P(x0, ey), 0.21*r*big, 0.28*r*big, look, half))
    # 眉
    by = ey - 0.36*r
    if expr in ('ah', 'oops', 'surprised'):
        for sgn in (-1, 1):
            L.append(('line', [P(sgn*ex - 0.13*r, by), P(sgn*ex, by - 0.08*r), P(sgn*ex + 0.13*r, by)], lw*0.75))
    elif expr in ('worried', 'troubled'):
        for sgn in (-1, 1):   # 内側が上がる
            L.append(('line', [P(sgn*(ex + 0.15*r), by + 0.04*r), P(sgn*(ex - 0.13*r), by - 0.09*r)], lw*0.75))
    elif expr in ('angry', 'determined'):
        k = 0.12 if expr == 'angry' else 0.06
        for sgn in (-1, 1):   # 内側が下がる
            L.append(('line', [P(sgn*(ex + 0.15*r), by - k*r), P(sgn*(ex - 0.13*r), by + k*r)], lw*0.75))
    # 口
    my = 0.36*r
    if expr in ('smile', 'happy', 'calm'):
        w_ = 0.26*r if expr != 'calm' else 0.2*r
        L.append(('line', [P(w_*math.cos(math.radians(a)), my - 0.06*r + 0.13*r*math.sin(math.radians(a)))
                           for a in range(10, 171, 16)], lw))
    elif expr in ('ah', 'oops'):
        L.append(('ring', P(0, my + 0.02*r), 0.09*r, 0.11*r))
    elif expr == 'surprised':
        L.append(('ring', P(0, my + 0.04*r), 0.12*r, 0.16*r))
    elif expr in ('worried', 'dizzy'):
        L.append(('line', [P(-0.2*r + 0.4*r*k/8, my + 0.05*r*math.sin(k*math.pi/2)) for k in range(9)], lw*0.9))
    elif expr == 'troubled':
        L.append(('line', [P(-0.2*r + 0.1*r*k, my + (0.05*r if k % 2 else -0.04*r)) for k in range(5)], lw*0.9))
    elif expr == 'angry':
        L.append(('line', [P(0.18*r*math.cos(math.radians(a)), my + 0.12*r - 0.12*r*math.sin(math.radians(a)))
                           for a in range(10, 171, 16)], lw))
    else:   # serious・tired・determined
        L.append(('line', [P(-0.14*r, my), P(0.14*r, my)], lw))
    if expr == 'oops':
        L.append(('drop', P(0.78*r, -0.3*r), 0.12*r))
    return L


def face(img, cx, cy, r, expr, a=1.0, look=0.0, rot=0.0, expr2=None, u=0.0):
    """顔を描く。expr2・u があれば、expr から expr2 へ u（0→1）で入れかわる（重ねて薄く切りかえる）。"""
    if LAYER == 'over':
        return
    if a <= 0.01:
        return
    if expr2 is not None and expr2 != expr and 0.0 < u < 1.0:
        face(img, cx, cy, r, expr, a*(1 - u), look, rot)
        face(img, cx, cy, r, expr2, a*u, look, rot)
        return
    if expr2 is not None and u >= 1.0:
        expr = expr2
    r = r*FACE_K
    m = r*1.2
    pad = Pad(cx - m - 6, cy - m - 6, cx + m + 6, cy + m + 6)
    layers = _face_layers(cx, cy, r, expr, look, rot)
    # 1回目：縁どり、2回目：中身
    for pass_ in (0, 1):
        for L in layers:
            kind = L[0]
            if kind == 'line':
                _, pts, w = L
                if pass_ == 0:
                    pad.line(pts, DK, w + 3.0, a=220)
                else:
                    pad.line(pts, LT, w)
            elif kind == 'eye':
                _, (x, y), rx, ry, lk, half = L
                if pass_ == 0:
                    pad.ell(x, y, rx + 1.6, ry + 1.6, fill=DK, a=230)
                else:
                    pad.ell(x, y, rx, ry, fill=EYE)
                    pad.ell(x + lk*rx*0.4, y + ry*0.15, rx*0.58, ry*0.58, fill=DK)
                    pad.ell(x + lk*rx*0.4 - rx*0.2, y - ry*0.12, rx*0.18, rx*0.18, fill=EYE)
                    if half:
                        pad.poly([(x - rx - 1, y - ry - 1), (x + rx + 1, y - ry - 1), (x + rx + 1, y - ry*0.1),
                                  (x - rx - 1, y - ry*0.1)], fill=DK)
                        pad.line([(x - rx, y - ry*0.1), (x + rx, y - ry*0.1)], LT, 1.4)
            elif kind == 'ring':
                _, (x, y), rx, ry = L
                if pass_ == 0:
                    pad.ell(x, y, rx + 1.8, ry + 1.8, fill=DK, a=220)
                else:
                    pad.ell(x, y, rx, ry, fill=(40, 30, 34), outline=LT, w=max(1.3, 0.07*r))
            elif kind == 'drop':
                _, (x, y), s = L
                pts = [(x, y - 1.6*s)] + [(x + s*math.cos(math.radians(t)), y + s*math.sin(math.radians(t)))
                                          for t in range(-30, 211, 20)]
                if pass_ == 0:
                    pad.poly(pts, fill=DK, outline=DK, w=2.5, a=220)
                else:
                    pad.poly(pts, fill=SWEAT)
    pad.paste(img, a)


def arms(img, segs, a=1.0, w=4.2, hand=6.5):
    """手：segs = [(肩, 手)]。縁どりつきの線と丸い手。"""
    if LAYER == 'over':
        return
    if a <= 0.01 or not segs:
        return
    xs = [p[0] for s in segs for p in s]; ys = [p[1] for s in segs for p in s]
    pad = Pad(min(xs) - 12, min(ys) - 12, max(xs) + 12, max(ys) + 12)
    for (p0, p1) in segs:
        pad.line([p0, p1], DK, w + 3.2, a=210)
        pad.ell(p1[0], p1[1], hand + 1.6, hand + 1.6, fill=DK, a=220)
    for (p0, p1) in segs:
        pad.line([p0, p1], LT, w)
        pad.ell(p1[0], p1[1], hand, hand, fill=LT)
    pad.paste(img, a)


def bubble(m, img, x, y, s, a=1.0, tail=None, size=42, col=(250, 250, 248)):
    """吹き出し（中心 x, y）。tail：しっぽの先 (x, y)。文字は4字まで。"""
    if LAYER == 'under':
        return
    if a <= 0.01:
        return
    tw = m.text_w(s, size, 800)
    w, h = tw + 34, size + 26
    x = min(m.W - m.MARGIN - w/2, max(m.MARGIN + w/2, x))          # 左右の余白（130px）の内側に
    x0, y0 = x - w/2, y - h/2
    pts = [p for p in ([tail] if tail else [])]
    xs = [x0, x0 + w] + [p[0] for p in pts]; ys = [y0, y0 + h] + [p[1] for p in pts]
    pad = Pad(min(xs) - 6, min(ys) - 6, max(xs) + 6, max(ys) + 6)
    if tail:
        bx = cl(tail[0], x0 + 12, x0 + w - 12)
        by = y0 + h if tail[1] > y else y0
        tri = [(bx - 11, by), (bx + 11, by), tail]
        pad.poly(tri, fill=DK, outline=DK, w=3.0, a=230)
    pad.rrect(x0, y0, x0 + w, y0 + h, h/2, fill=col, outline=DK, w=3.2)
    if tail:
        pad.poly(tri, fill=col)
        pad.rrect(x0 + 1.2, y0 + 1.2, x0 + w - 1.2, y0 + h - 1.2, h/2 - 1, fill=col)
    pad.paste(img, a)
    m.put(img, s, size, 800, (24, 30, 32), cx=x, cy=y + 1, a=a)


# --- 小物 ---------------------------------------------------------------------------
def magnifier(img, x, y, r, col, a=1.0):
    if LAYER == 'under':
        return
    pad = Pad(x - r - 12, y - r - 12, x + r*2.0 + 12, y + r*2.0 + 12)
    hx0, hy0 = x + r*0.72, y + r*0.72
    hx1, hy1 = x + r*1.6, y + r*1.6
    pad.line([(hx0, hy0), (hx1, hy1)], DK, 12, a=220)
    pad.ell(x, y, r + 3.5, r + 3.5, outline=DK, w=8, a=220)
    pad.ell(x, y, r, r, fill=(255, 255, 255), a=28)
    pad.ell(x, y, r, r, outline=LT, w=4.2)
    pad.line([(hx0 + 2, hy0 + 2), (hx1, hy1)], col, 7.5)
    pad.line([(x - r*0.45, y - r*0.55), (x - r*0.15, y - r*0.72)], LT, 2.4, a=200)
    pad.paste(img, a)


def heart(img, x, y, s, col, a=1.0, beat=0.0):
    if LAYER == 'under':
        return
    k = 1.0 + 0.12*beat
    pts = []
    for tt in np.linspace(0, 2*math.pi, 60):
        hx = 16*math.sin(tt)**3
        hy = -(13*math.cos(tt) - 5*math.cos(2*tt) - 2*math.cos(3*tt) - math.cos(4*tt))
        pts.append((x + hx*s*k/16, y + hy*s*k/16))
    pad = Pad(x - s*1.3, y - s*1.3, x + s*1.3, y + s*1.3)
    pad.poly(pts, fill=DK, outline=DK, w=5, a=220)
    pad.poly(pts, fill=tuple(int(c*0.35) for c in col), outline=col, w=3.2)
    pad.paste(img, a)


def lightning(img, x, y, s, a=1.0, col=(255, 214, 64)):
    if LAYER == 'under':
        return
    pts = [(0.15, -1.0), (-0.45, 0.1), (-0.02, 0.1), (-0.25, 1.0), (0.48, -0.22), (0.05, -0.22), (0.3, -1.0)]
    pts = [(x + px*s, y + py*s) for px, py in pts]
    pad = Pad(x - s - 6, y - s - 6, x + s + 6, y + s + 6)
    pad.poly(pts, fill=DK, outline=DK, w=5, a=230)
    pad.poly(pts, fill=col, outline=(255, 246, 200), w=1.5)
    pad.paste(img, a)


def spark(img, x, y, s, a=1.0, col=(255, 236, 140), rot=0.0):
    if LAYER == 'under':
        return
    pad = Pad(x - s - 6, y - s - 6, x + s + 6, y + s + 6)
    segs = []
    for k in range(8):
        th = rot + k*math.pi/4
        r0, r1 = (0.35*s, s) if k % 2 == 0 else (0.35*s, 0.65*s)
        segs.append([(x + r0*math.cos(th), y + r0*math.sin(th)), (x + r1*math.cos(th), y + r1*math.sin(th))])
    for sg in segs:
        pad.line(sg, DK, 6.5, a=200)
    for sg in segs:
        pad.line(sg, col, 3.2)
    pad.paste(img, a)


def ruler(m, img, x0, x1, y, col, a=1.0, mark=None, tick=14.0):
    """定規（1mm＝14px の目盛り）。mark=(xa, xb) で幅のしるし（両矢印）。"""
    if LAYER == 'under':
        return
    h = 33
    pad = Pad(x0 - 8, y - 42, x1 + 8, y + h + 8)
    pad.rrect(x0, y, x1, y + h, 4, fill=(232, 222, 190), outline=DK, w=2.5)
    for k in range(int((x1 - x0) / tick) + 1):
        xx = x0 + 6 + k*tick
        if xx > x1 - 4:
            break
        L_ = 17 if k % 5 == 0 else 9
        pad.line([(xx, y), (xx, y + L_)], (70, 60, 40), 2.2 if k % 5 == 0 else 1.5, cap=False)
    if mark:
        xa, xb = mark
        pad.line([(xa, y - 20), (xb, y - 20)], DK, 8.5, a=220)
        pad.line([(xa, y - 20), (xb, y - 20)], col, 4.5)
        for xx, sg in ((xa, 1), (xb, -1)):
            pad.line([(xx + sg*10, y - 30), (xx, y - 20), (xx + sg*10, y - 10)], col, 4.2)
            pad.line([(xx, y - 36), (xx, y - 4)], col, 3.0)
    pad.paste(img, a)


def signpost(m, img, x, y, col, a=1.0, left='脈あり', right='脈なし', size=34):
    """分かれ道の看板：x は柱、y は板の中心。左の板「脈あり」・右の板「脈なし」を同じ高さに。"""
    if LAYER == 'under':
        return
    wl, wr = m.text_w(left, size, 800) + 44, m.text_w(right, size, 800) + 44
    hh = size + 18
    pad = Pad(x - wl - 12, y - hh, x + wr + 12, y + hh*1.6 + 12)
    pad.line([(x, y - hh*0.6), (x, y + hh*1.5)], DK, 12, a=220)
    pad.line([(x, y - hh*0.6), (x, y + hh*1.5)], (190, 170, 140), 7)
    L_ = [(x - 6, y - hh/2), (x - wl + 16, y - hh/2), (x - wl, y), (x - wl + 16, y + hh/2), (x - 6, y + hh/2)]
    R_ = [(x + 6, y - hh/2), (x + wr - 16, y - hh/2), (x + wr, y), (x + wr - 16, y + hh/2), (x + 6, y + hh/2)]
    for pts in (L_, R_):
        pad.poly(pts, fill=(14, 26, 22), outline=DK, w=6, a=230)
        pad.poly(pts, fill=(14, 26, 22), outline=col, w=3.2)
    pad.paste(img, a)
    m.put(img, left, size, 800, m.LIGHT, cx=x - wl/2 + 4, cy=y, a=a)
    m.put(img, right, size, 800, m.LIGHT, cx=x + wr/2 - 4, cy=y, a=a)


def loop_arrow(m, img, x, y, r, col, a=1.0, rot=0.0, label='くり返す'):
    if LAYER == 'under':
        return
    pad = Pad(x - r - 14, y - r - 14, x + r + 14, y + r + 14)
    pts = arc_pts(x, y, r, r, 30, 320, n=30, rot=rot, ox=x, oy=y)
    th = math.radians(320) + rot
    tip = (x + r*math.cos(th), y + r*math.sin(th))
    tx, ty = -math.sin(th), math.cos(th)
    nx, ny = math.cos(th), math.sin(th)
    head = [(tip[0] + tx*10, tip[1] + ty*10), (tip[0] - nx*9 - tx*2, tip[1] - ny*9 - ty*2),
            (tip[0] + nx*9 - tx*2, tip[1] + ny*9 - ty*2)]
    pad.line(pts, DK, 9, a=220); pad.poly(head, fill=DK, outline=DK, w=4, a=220)
    pad.line(pts, col, 5); pad.poly(head, fill=col)
    pad.paste(img, a)
    if label:
        m.put(img, label, 34, 800, col, x=x + r + 16, cy=y, a=a)


def plug(img, x, y, s, col, a=1.0, gap=0.0):
    """電極のプラグ（左）とソケット（右）。gap：すき間（px）。"""
    if LAYER == 'under':
        return
    pad = Pad(x - 2.6*s - 10, y - s - 10, x + 2.4*s + gap + 10, y + s + 10)
    body = (x - 1.8*s, y - 0.55*s, x - 0.4*s, y + 0.55*s)
    cable = [(x - 1.8*s, y), (x - 2.3*s, y + 0.2*s), (x - 2.6*s, y + 0.6*s)]
    prongs = [[(x - 0.4*s, y - 0.25*s), (x + 0.15*s, y - 0.25*s)], [(x - 0.4*s, y + 0.25*s), (x + 0.15*s, y + 0.25*s)]]
    sock = (x + 0.3*s + gap, y - 0.6*s, x + 1.4*s + gap, y + 0.6*s)
    pad.line(cable, DK, 8, a=220); pad.line(cable, (200, 205, 205), 4)
    for pr in prongs:
        pad.line(pr, DK, 6, a=220); pad.line(pr, (220, 220, 210), 3)
    pad.rrect(*body, 4, fill=(220, 226, 226), outline=DK, w=2.5)
    pad.rrect(*sock, 4, fill=(60, 70, 70), outline=col, w=2.6)
    pad.paste(img, a)


def name_tag(m, img, x, y, col, a=1.0):
    """空いた名札「QRS」（点線の枠）。"""
    if LAYER == 'under':
        return
    w, h = 144, 66
    pad = Pad(x - w/2 - 6, y - h/2 - 6, x + w/2 + 6, y + h/2 + 6)
    pad.rrect(x - w/2, y - h/2, x + w/2, y + h/2, 10, fill=(10, 20, 18), a=200)
    per = 2*(w + h)
    n = 18
    for k in range(n):
        u0, u1 = k/n, (k + 0.55)/n
        def at(u):
            d = u*per
            if d < w: return (x - w/2 + d, y - h/2)
            d -= w
            if d < h: return (x + w/2, y - h/2 + d)
            d -= h
            if d < w: return (x + w/2 - d, y + h/2)
            d -= w
            return (x - w/2, y + h/2 - d)
        pad.line([at(u0), at(u1)], col, 2.4, cap=False)
    pad.paste(img, a)
    m.put(img, 'QRS', 34, 800, m.GREY, cx=x, cy=y, a=a*0.9)




# --- 白い手ぶくろ（昔ながらのアニメ風の、ふつうの手ぶくろ。特定のキャラクターではない） ---------------------------
GLOVE = (250, 250, 247)
GLOVE_LINE = (60, 64, 70)


def _capsule(p0, p1, r, n=8):
    (x0, y0), (x1, y1) = p0, p1
    ang = math.atan2(y1 - y0, x1 - x0)
    pts = []
    for k in range(n + 1):
        th = ang + math.pi/2 + math.pi*k/n
        pts.append((x0 + r*math.cos(th), y0 + r*math.sin(th)))
    for k in range(n + 1):
        th = ang - math.pi/2 + math.pi*k/n
        pts.append((x1 + r*math.cos(th), y1 + r*math.sin(th)))
    return pts


def _ellipse(cx, cy, rx, ry, n=24):
    return [(cx + rx*math.cos(2*math.pi*k/n), cy + ry*math.sin(2*math.pi*k/n)) for k in range(n)]


def glove_shapes(s, pose):
    """手ぶくろの形（手首が原点、指先が +x の向き）。ふっくらした指3本と親指、丸い袖口。"""
    sh = []
    sh.append(('poly', [(-0.08*s, -0.27*s), (0.2*s, -0.24*s), (0.2*s, 0.24*s), (-0.08*s, 0.27*s)]))   # 袖口
    sh.append(('poly', _ellipse(0.5*s, 0.0, 0.31*s, 0.34*s)))                                        # 手のひら
    fr = 0.125*s
    if pose in ('open', 'wave'):
        for yo in (0.21, 0.0, -0.21):
            sh.append(('poly', _capsule((0.62*s, yo*s), (1.0*s, yo*1.35*s), fr)))
        sh.append(('poly', _capsule((0.44*s, -0.27*s), (0.6*s, -0.55*s), 0.115*s)))                   # 親指
    elif pose == 'flat':
        for yo in (0.2, 0.0, -0.2):
            sh.append(('poly', _capsule((0.62*s, yo*s), (1.02*s, yo*s), fr)))
        sh.append(('poly', _capsule((0.44*s, -0.28*s), (0.66*s, -0.36*s), 0.11*s)))
    elif pose == 'point':
        for yo in (0.2, 0.05):
            sh.append(('poly', _capsule((0.62*s, yo*s), (0.78*s, yo*s), fr)))
        sh.append(('poly', _capsule((0.62*s, -0.14*s), (1.12*s, -0.14*s), fr)))                        # 人さし指
        sh.append(('poly', _capsule((0.44*s, -0.27*s), (0.6*s, -0.4*s), 0.11*s)))
    else:                                                                                               # 'fist'・'grip'
        for yo in (0.2, 0.0, -0.2):
            sh.append(('poly', _capsule((0.66*s, yo*s), (0.8*s, yo*s), 0.13*s)))
        sh.append(('poly', _capsule((0.46*s, -0.28*s), (0.7*s, -0.16*s), 0.11*s)))
    lines = [[(0.3*s, y*s), (0.48*s, y*s)] for y in (-0.12, 0.0, 0.12)]                                # 手の甲の線
    band = [(0.1*s, -0.25*s), (0.1*s, 0.25*s)]                                                          # 袖口の線
    return sh, lines, band


def glove(img, x, y, s, ang, pose='open', mirror=False, a=1.0):
    """手首 (x, y)、向き ang（ラジアン）、大きさ s（袖口から指先まで約 s px）。"""
    if LAYER == 'over' or a <= 0.01:
        return
    sh, lines, band = glove_shapes(s, pose)
    c, si = math.cos(ang), math.sin(ang)

    def T(p):
        px, py = p
        if mirror:
            py = -py
        return (x + px*c - py*si, y + px*si + py*c)
    pad = Pad(x - 1.3*s, y - 1.3*s, x + 1.3*s, y + 1.3*s)
    # 袖口・手のひら → 線 → 指（1本ずつ縁どり）の順。指のあいだに縁の線が残る
    for _, pts in sh[:2]:
        pad.poly([T(p) for p in pts], fill=DK, outline=DK, w=4.5, a=240)
    for _, pts in sh[:2]:
        pad.poly([T(p) for p in pts], fill=GLOVE)
    for ln in lines:
        pad.line([T(p) for p in ln], GLOVE_LINE, 2.0, cap=False)
    pad.line([T(p) for p in band], (190, 190, 186), 2.0, cap=False)
    for _, pts in sh[2:]:
        q = [T(p) for p in pts]
        pad.poly(q, fill=DK, outline=DK, w=4.0, a=240)
        pad.poly(q, fill=GLOVE)
    pad.paste(img, a)


def arm(img, p0, p1, s=52, pose='open', a=1.0, mirror=False, w=3.0):
    """細い腕（p0 → p1）と、p1 の手ぶくろ（腕の向きに）。"""
    if LAYER == 'over' or a <= 0.01:
        return
    pad = Pad(min(p0[0], p1[0]) - 8, min(p0[1], p1[1]) - 8, max(p0[0], p1[0]) + 8, max(p0[1], p1[1]) + 8)
    pad.line([p0, p1], DK, w + 3.0, a=215)
    pad.line([p0, p1], LT, w)
    pad.paste(img, a)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    glove(img, p1[0], p1[1], s, ang, pose, mirror, a)


# --- 顔の大きさと位置：こぶの中に、線にふれずに入るか（形で確かめる） ------------------------------------
R_MIN, R_CAP = 16.0, 50.0
AX_K, AY_K = 0.74, 0.62            # 顔の線（目・眉・口・縁どり）が入る形（|x/a|^4＋|y/b|^4≦1、角の丸い四角）の大きさ（顔の半径 r に対して）
SE = 4.0                           # その形のべき（4：角の丸い四角。眉の端・目の端まで入る）
AX_K_OOPS = 0.94                   # 汗のしずくがある顔
AX_K_NARROW = 0.58                 # 目を寄せた細い顔
LINE_M = 5.5                       # 波形の線（太さ 5.5px）の半分＋すき間
_FIT = {}


def _hump_samples(m, tau_pk, span):
    tau = tau_pk + np.arange(-span, span, 0.5/m.PXS)
    return (tau - tau_pk)*m.PXS, m.BASE - m.stream_wave(tau)*m.G


def fit_hump(m, tau_pk, sign=1, axk=AX_K, r_cap=R_CAP):
    """こぶ（sign=1：上向き、-1：下向き）の頂点 tau_pk の真下（上）に、線にふれずに入るいちばん大きな顔。
    返り値：(dy, r)。dy は基線からの顔の中心の高さ（上向きは負）。入らなければ None。形は流れの中で変わらないので覚えておく。"""
    key = (round(float(np.mod(tau_pk, m.LTOT)), 4), sign, axk, r_cap)
    if key in _FIT:
        return _FIT[key]
    dx, ys = _hump_samples(m, tau_pk, 0.16)
    y_pk = m.BASE - float(m.stream_wave(np.array([tau_pk]))[0])*m.G
    res = None
    for r in np.arange(r_cap, R_MIN - 0.01, -1.0):
        ax, ay = axk*r + 2, AY_K*r + 2
        A, B = ax + LINE_M, ay + LINE_M
        near = np.abs(dx) <= A + 1
        xs_, ys_ = dx[near], ys[near]
        found = None
        if sign > 0:
            cy = m.BASE - 2 - ay
            while cy - B > y_pk:
                d = np.min(np.abs(xs_/A)**SE + np.abs((ys_ - cy)/B)**SE)
                if d > 1.15 and y_pk < cy:
                    found = cy
                    break
                cy -= 2
        else:
            cy = m.BASE + 2 + ay
            while cy + B < y_pk:
                d = np.min(np.abs(xs_/A)**SE + np.abs((ys_ - cy)/B)**SE)
                if d > 1.15 and y_pk > cy:
                    found = cy
                    break
                cy += 2
        if found is not None:
            res = (found - m.BASE, float(r))
            break
    _FIT[key] = res
    return res


def hface(m, img, t, tau_pk, expr, a, sign=1, axk='auto', r_cap=R_CAP, **kw):
    """こぶの中の顔（入らなければ描かない）。顔は動かさない（こぶからはみ出さないように）。
    axk='auto'：ふつうの顔と目を寄せた細い顔のうち、大きく入るほう。"""
    if axk == 'auto':
        f1 = fit_hump(m, tau_pk, sign, AX_K, r_cap)
        f2 = fit_hump(m, tau_pk, sign, AX_K_NARROW, r_cap)
        if f2 is not None and (f1 is None or f2[1] > f1[1] + 3):
            axk, f = AX_K_NARROW, f2
        else:
            axk, f = AX_K, f1
    else:
        f = fit_hump(m, tau_pk, sign, axk, r_cap)
    if f is None or a <= 0.01:
        return None
    dy, r = f
    x = float(m.x_of(tau_pk, t))
    if x < -60 or x > m.W + 60:
        return None
    cy = m.BASE + dy
    aa = a*ease((r - R_MIN) / 5.0 + 0.2)
    FACE_LOG.append(dict(tau=float(tau_pk), x=x, y=cy, r=r, axk=axk, sign=sign, expr=expr))
    if not DRY:
        global NARROW
        NARROW = axk <= AX_K_NARROW + 1e-9
        try:
            face(img, x, cy, r, expr, a=aa, **kw)
        finally:
            NARROW = False
    return (x, cy, r)


# --- 流れの上の拍・こぶ ------------------------------------------------------------------------
_LOBES = {}


def lobes(m, sign, thr):
    """流れ全体の山（sign=1）・谷（-1）の時刻（1周ぶん）。大きさ thr mV 以上。"""
    k = (sign, thr)
    if k not in _LOBES:
        tau = np.arange(0, m.LTOT, 0.001)
        v = m.stream_wave(tau)*sign
        idx = np.where((v[1:-1] > thr) & (v[1:-1] >= v[:-2]) & (v[1:-1] > v[2:]))[0] + 1
        _LOBES[k] = (tau[idx], v[idx])
    return _LOBES[k]


def visible_lobes(m, t, sign, thr, seg_keys, margin=60):
    taus, vals = lobes(m, sign, thr)
    c = m.c_of(t)
    lo, hi = c + (-margin - m.XC)/m.PXS, c + (m.W + margin - m.XC)/m.PXS
    out = []
    for kk in (math.floor(lo/m.LTOT), math.floor(hi/m.LTOT)):
        tt = taus + kk*m.LTOT
        sel = (tt >= lo) & (tt <= hi)
        for tau, v in zip(tt[sel], vals[sel]):
            g = m.SEG[int(m.seg_index(np.array([tau]))[0])]
            if g['key'] in seg_keys and tau >= g['sp'] + 0.05 and not any(abs(o[0] - tau) < 1e-9 for o in out):
                out.append((float(tau), float(v), g))
    return out


def d_in(m, t, tau):
    """その点が画面の右端に入ってからの時間（秒）。"""
    return (m.W - float(m.x_of(tau, t))) / m.SCROLL


def nearest_center(m, t, items, key=lambda q: q, n=2):
    return sorted(items, key=lambda q: abs(float(m.x_of(key(q), t)) - m.XC))[:n]


# --- 場面ごとのお話（拍の位置とブロックの時刻で決める） ------------------------------------------------------
def handshake(m, img, t, b, a, reach):
    """伝わる拍：Pくん（P波のこぶの中）と、QRS（細いので顔なし。手だけ）が握手。"""
    tP = b['tau'] - m.PR
    f = hface(m, img, t, tP, 'smile', a)
    xr = float(m.x_of(b['tau'], t))
    xp = float(m.x_of(tP, t))
    my = m.BASE - 70
    mx = (xp + xr)/2 + 4
    rest_p = (xp + 44, m.BASE - 104)
    rest_q = (xr - 30, m.BASE - 120)
    if f is not None:
        sh_p = (f[0] + 0.55*f[2], f[1] - 0.1*f[2])
        hp = (rest_p[0] + (mx - 18 - rest_p[0])*reach, rest_p[1] + (my - rest_p[1])*reach)
        arm(img, sh_p, hp, s=52, pose='open' if reach < 0.95 else 'fist', a=a)
    sh_q = (xr - 7, m.BASE - 0.42*m.G)
    hq = (rest_q[0] + (mx + 18 - rest_q[0])*reach, rest_q[1] + (my - rest_q[1])*reach)
    arm(img, sh_q, hq, s=52, pose='open' if reach < 0.95 else 'fist', mirror=True, a=a)


def mobitz(m, img, t, beats, g, a):
    for b in beats:
        if b['kind'] == 'N':
            d = d_in(m, t, b['tau'] - m.PR)
            handshake(m, img, t, b, a, ease((d - 0.55) / 0.5))
        elif b['kind'] == 'P':
            named = g['h'] is not None and m.unwrap_near(b['tau'], t) >= m.unwrap_near(g['h'], t) - 0.2 \
                and b['tau'] - m.unwrap_near(g['h'], t) < 0.5
            dropped(m, img, t, b['tau'], a, story=named or b['tau'] > m.unwrap_near(g['h'], t))


def dropped(m, img, t, tP, a, story=True):
    """抜けたP：手が空ぶり（あっ）→ 来るはずだった QRS が基線の下からのぞき（あらっ）→ 落ちる。"""
    d = d_in(m, t, tP)
    f = hface(m, img, t, tP, 'smile', a, expr2='ah' if story else None, u=ease((d - 1.0) / 0.25))
    if not story:
        return
    xp = float(m.x_of(tP, t))
    xe = float(m.x_of(tP + m.PR, t))
    if f is not None:
        sh_p = (f[0] + 0.55*f[2], f[1] - 0.1*f[2])
        rest = (xp + 44, m.BASE - 104)
        target = ((xp + xe)/2 + 22, m.BASE - 70)
        u = ease((d - 0.55) / 0.45) * (1 - ease((d - 1.6) / 0.45))
        over = ease((d - 0.95) / 0.3) * (1 - ease((d - 1.6) / 0.45))
        hp = (rest[0] + (target[0] + 30*over - rest[0])*u, rest[1] + (target[1] + 10*over - rest[1])*u)
        arm(img, sh_p, hp, s=52, pose='open', a=a)
        bubble(m, img, xp - 30, f[1] - f[2] - 74, 'あっ', a=a*win(d, 1.0, 2.2, 0.2, 0.3), tail=(xp, f[1] - 0.7*f[2]))
    rq = 40
    rise = ease((d - 1.2) / 0.4)
    fall = ease((d - 2.0) / 0.45)
    yq = m.BASE + rq + 100 - 92*rise + 190*fall*fall
    aq = a*rise*(1 - ease((d - 2.3) / 0.22))
    if aq > 0.01:
        if not DRY:
            face(img, xe, yq, rq, 'serious', a=aq, expr2='oops', u=ease((d - 1.55) / 0.25))
        if fall < 0.05:
            for sg in (-1, 1):
                arm(img, (xe + sg*0.7*rq, yq - 0.2*rq), (xe + sg*1.05*rq, m.BASE + 6), s=48, pose='grip', a=aq,
                    mirror=sg > 0)
        else:
            for sg in (-1, 1):
                arm(img, (xe + sg*0.7*rq, yq - 0.2*rq), (xe + sg*1.25*rq, yq - 1.25*rq), s=48, pose='open', a=aq,
                    mirror=sg > 0)
        bubble(m, img, xe + rq + 110, m.BASE + 84, 'あらっ', a=aq*win(d, 1.55, 2.4, 0.2, 0.2), tail=(xe + 0.8*rq, yq))


def chb(m, img, t, beats, g, a):
    ws = [b['tau'] for b in beats if b['kind'] == 'W']
    for b in beats:
        if b['kind'] == 'P' and not any(-0.25 < b['tau'] - w < 0.5 for w in ws):
            f = hface(m, img, t, b['tau'], 'serious', a, look=-1.0)
            if f is not None:
                reach = 0.5 + 0.5*math.sin(2*math.pi*0.6*t + b['tau'])
                sh_ = (f[0] + 0.55*f[2], f[1] - 0.1*f[2])
                arm(img, sh_, (sh_[0] + 34 + 30*reach, sh_[1] - 34 - 10*reach), s=50, pose='open', a=a)
        elif b['kind'] == 'W':
            hface(m, img, t, b['tau'], 'tired', a, look=1.0)


def shortrun(m, img, t, beats, g, a, mode):
    if mode == 'ov':
        # ② 場所の説明：真ん中に近いふつうの QRS の下に定規（QRS の幅）
        ns = [b for b in beats if b['kind'] == 'N']
        if ns:
            b = nearest_center(m, t, ns, key=lambda q: q['tau'], n=1)[0]
            xr = float(m.x_of(b['tau'], t))
            qw = 0.07*m.PXS
            mm = m.PXMM
            ruler(m, img, xr - qw/2 - 3*mm, xr + qw/2 + 3*mm, m.BASE + 0.25*m.G, g['pat']['col'], a=a,
                  mark=(xr - qw/2, xr + qw/2), tick=mm)
        return
    vs = [b for b in beats if b['kind'] == 'V']
    groups = {}
    for b in vs:
        groups.setdefault(round((b['tau'] - b['rel']) / 4.0), []).append(b)
    for _, gr in groups.items():
        gr.sort(key=lambda b: b['tau'])
        sit = ease((d_in(m, t, gr[-1]['tau']) - 1.0) / 0.35)
        fs = [hface(m, img, t, b['tau'], 'determined', a, expr2='happy', u=sit) for b in gr]
        # 3人つながって走る：先頭（左）の人が前（左）へ手を伸ばし、うしろの人は前の人へ手を伸ばす（止まると手を下ろす）
        for k, f in enumerate(fs):
            if f is None:
                continue
            swing = 8*math.sin(2*math.pi*3.0*t + k)*(1 - sit)
            tip = m.BASE - 0.95*m.G                                   # QRS の頂点より上（線にかからない高さ）
            p0 = (f[0], tip - 6)
            p1 = (f[0] - 46 - 10*(1 - sit), tip - 34 + 30*sit + swing)
            arm(img, p0, p1, s=48, pose='open' if sit < 0.5 else 'fist', mirror=True, a=a)


def vt(m, img, t, beats, g, a):
    xs = [b for b in beats if b['kind'] == 'X']
    for b in nearest_center(m, t, xs, key=lambda q: q['tau'], n=4):
        k = int(round((b['rel'] or 0) / 0.32))
        if k % 2:
            continue
        hface(m, img, t, b['tau'], 'smile', a)                       # 同じ顔（手は線にかかるので出さない）


def poly(m, img, t, g, a):
    exprs = ['angry', 'surprised', 'troubled', 'ah', 'serious', 'worried']
    items = [(tau, v, 1) for tau, v, gg in visible_lobes(m, t, 1, 0.45, ('多形性VT',))] + \
            [(tau, v, -1) for tau, v, gg in visible_lobes(m, t, -1, 0.45, ('多形性VT',))]
    for tau, v, sg in nearest_center(m, t, items, key=lambda q: q[0], n=3):
        hface(m, img, t, tau, exprs[int(round(tau*7)) % len(exprs)], a, sign=sg)


def torsade(m, img, t, g, a):
    global SPIN
    items = [(tau, 1) for tau, v, gg in visible_lobes(m, t, 1, 0.45, ('トルサード',))] + \
            [(tau, -1) for tau, v, gg in visible_lobes(m, t, -1, 0.45, ('トルサード',))]
    SPIN = 2*math.pi*0.9*t
    for tau, sg in nearest_center(m, t, items, key=lambda q: q[0], n=3):
        hface(m, img, t, tau, 'dizzy', a, sign=sg)
    SPIN = 0.0


def ront(m, img, t, beats, g, a):
    for b in beats:
        if b['kind'] != 'N':
            continue
        tT = b['tau'] + m.T_PEAK['N']
        hit = b['rel'] is not None and abs((b['rel'] % 3.2) - 0.8) < 1e-6
        if not hit:
            hface(m, img, t, tT, 'calm', a)
            continue
        tV = b['tau'] + m.RONT_C
        d = d_in(m, t, tV) + 0.45                                     # 画面の右寄りで起きるように
        fv = hface(m, img, t, tV, 'determined', a, expr2='ah', u=ease((d - 1.1) / 0.25))
        ft = hface(m, img, t, tT, 'calm', a, expr2='surprised', u=ease((d - 0.95) / 0.2))
        xt = float(m.x_of(tT, t))
        if fv is not None:
            top = m.BASE - 0.95*m.G
            xv_ = float(m.x_of(tV, t))
            for sg in (-1, 1):                                       # 頂点の上で手をあげる（線にかからない）
                arm(img, (xv_, top - 4), (xv_ + sg*40, top - 40), s=46, pose='open', mirror=sg < 0, a=a)
        yT = m.BASE - float(m.stream_wave(np.array([tT]))[0])*m.G
        bubble(m, img, xt - 170, yT - 60, 'ひゃっ', a=a*win(d, 0.95, 2.3, 0.2, 0.3), tail=(xt - 30, yT - 10))
        sa = a*win(d, 0.95, 1.8, 0.12, 0.3)
        if sa > 0.01:
            spark(img, xt - 60, yT - 110, 30, a=sa, rot=t*3)
        fa = a*win(d, 1.3, 2.5, 0.12, 0.3)
        if fa > 0.01 and fv is not None:
            xv = fv[0]
            lightning(img, xv + 120, m.BASE - 0.86*m.G, 30, a=fa)
            _vf_hint(img, xv + 240, m.BASE - 0.86*m.G, fa, t)


def _vf_hint(img, x, y, a, t):
    if LAYER == 'under':
        return
    pad = Pad(x - 70, y - 36, x + 70, y + 36)
    rs = np.random.RandomState(int(t*20) % 7)
    pts = [(x - 62 + 124*k/18, y + rs.uniform(-22, 22)) for k in range(19)]
    pad.rrect(x - 70, y - 34, x + 70, y + 34, 12, fill=(40, 6, 12), outline=(255, 92, 112), w=2.5, a=210)
    pad.line(pts, DK, 7, a=200)
    pad.line(pts, (255, 120, 136), 3.6)
    pad.paste(img, a)


def coarse_vf(m, img, t, g, a):
    items = visible_lobes(m, t, 1, 0.3, ('粗いVF',))
    n = 0
    for tau, v, gg in nearest_center(m, t, items, key=lambda q: q[0], n=4):
        if hface(m, img, t, tau, 'worried', a) is not None:
            n += 1
        if n >= 2:
            break


def cpr_gloves(m, img, x, y, s, col, a=1.0, press=0.0):
    """胸骨圧迫：胸（弧）の上に、重ねた手ぶくろ（指をそろえて手のひらを下に）と、下向きの矢印、「CPR」の字。"""
    yy = y + press*0.14*s
    if LAYER != 'under':
        pad = Pad(x - 1.6*s, y - 1.2*s, x + 1.6*s, y + 1.9*s)
        chest = arc_pts(x, y + 1.55*s, 1.35*s, 0.75*s, 200, 340, n=24)
        pad.line(chest, DK, 8, a=200); pad.line(chest, (200, 205, 205), 4)
        for sx in (-1.25, 1.25):
            ax_ = x + sx*s
            pad.line([(ax_, yy - 0.3*s), (ax_, yy + 0.35*s)], DK, 8, a=220)
            pad.line([(ax_ - 0.18*s, yy + 0.12*s), (ax_, yy + 0.37*s), (ax_ + 0.18*s, yy + 0.12*s)], DK, 8, a=220)
            pad.line([(ax_, yy - 0.3*s), (ax_, yy + 0.35*s)], col, 4.2)
            pad.line([(ax_ - 0.18*s, yy + 0.12*s), (ax_, yy + 0.37*s), (ax_ + 0.18*s, yy + 0.12*s)], col, 4.2)
        pad.paste(img, a)
        m.put(img, 'CPR', 36, 900, col, cx=x, cy=y - 0.95*s, a=a)
    if LAYER != 'over':
        glove(img, x - 0.62*s, yy + 0.42*s, 1.05*s, 0.0, 'flat', True, a)          # 下の手（指を右へ）
        glove(img, x + 0.62*s, yy - 0.12*s, 1.05*s, math.pi, 'flat', False, a)     # 上の手（指を左へ。上に重ねる）


def pulse_glove(m, img, x, y, s, a=1.0, press=0.0):
    """脈をみる：手首（帯）の上に、手ぶくろの人さし指を当てる。(x, y) は指先。"""
    yy = y - press*4
    if LAYER != 'under':
        pad = Pad(x - 2.0*s, y - 0.4*s, x + 2.0*s, y + 1.0*s)
        pad.rrect(x - 1.9*s, y + 0.05*s, x + 1.9*s, y + 0.75*s, 0.35*s, fill=(238, 210, 190), outline=DK, w=2.6)
        pad.ell(x, y + 0.35*s, 0.2*s, 0.13*s, fill=(255, 110, 125), a=200)
        pad.paste(img, a)
    if LAYER != 'over':
        glove(img, x - 0.05*s, yy - 1.12*s, 1.15*s, math.pi/2, 'point', False, a)


def scene5_props(m, img, t, a):
    """⑤：動かないハート（脈がない）と、脈をみる手ぶくろ（？）。波形の下の空いたところ。"""
    y = m.BASE + 210
    heart(img, m.XC - 220, y, 54, m.PLACES[4]['col'], a=a)
    press = 0.5 + 0.5*math.sin(2*math.pi*0.8*t)
    pulse_glove(m, img, m.XC + 150, y + 40, 52, a=a, press=press)
    bubble(m, img, m.XC + 290, y - 40, '？', a=a, tail=(m.XC + 200, y - 10))


def pea1(m, img, t, beats, g, a):
    ns = [b for b in beats if b['kind'] == 'N']
    for b in nearest_center(m, t, ns, key=lambda q: q['tau'], n=1):
        hface(m, img, t, b['tau'] - m.PR, 'calm', a)
        hface(m, img, t, b['tau'] + m.T_PEAK['N'], 'calm', a)


def pea2(m, img, t, beats, g, a):
    for b in beats:
        if b['kind'] == 'W':
            hface(m, img, t, b['tau'], 'tired', a)


def ending(m, img, t, beats, a):
    """最後：洞調律の Pくん・Tちゃんが、手ぶくろで手をふる（QRS は手だけ）。"""
    ns = [b for b in beats if b['kind'] == 'N' and m.SEG[b['seg']]['key'] == '洞調律']
    for b in nearest_center(m, t, ns, key=lambda q: q['tau'], n=1):
        wv = math.sin(2*math.pi*1.4*t)
        fp = hface(m, img, t, b['tau'] - m.PR, 'happy', a)
        ft = hface(m, img, t, b['tau'] + m.T_PEAK['N'], 'happy', a)
        for f, ph in ((fp, 0.0), (ft, 1.3)):
            if f is None:
                continue
            ang = -math.pi/2 + 0.45*math.sin(2*math.pi*1.4*t + ph)
            sh_ = (f[0] + 0.5*f[2], f[1] - 0.2*f[2])
            arm(img, sh_, (sh_[0] + 58*math.cos(ang) + 20, sh_[1] + 58*math.sin(ang) - 10), s=52, pose='wave', a=a)
        xr = float(m.x_of(b['tau'], t))
        ang = -math.pi/2 - 0.5 + 0.45*wv
        sh_ = (xr - 7, m.BASE - 0.62*m.G)
        arm(img, sh_, (sh_[0] + 60*math.cos(ang), sh_[1] + 60*math.sin(ang)), s=52, pose='wave', mirror=True, a=a)


# --- 毎コマの入り口 --------------------------------------------------------------------------------
_DUMMY = None


def _blk_mode(m, t, g):
    """その区間について、いまは 'ov'（場所の説明）か 'hi'（パターンの紹介）か。"""
    if g['idx'] is None:
        return None
    b = m.PAT_BLOCK[g['idx']]
    return 'hi' if t >= b['p'] else 'ov'


def _draw(m, img, t):
    # 冒頭（洞調律が流れているだけ）は顔なし。最後は洞調律の手ふり。冒頭へ戻る前に消える
    a_all = 1.0 - ease((t - (m.DUR - m.LOOP_FADE - 0.2)) / 0.5)
    if t < m.OPEN_DUR - 0.6 or a_all <= 0.01:
        return
    a_all *= ease((t - (m.OPEN_DUR - 0.6)) / 0.5)
    beats = m.visible_beats(t)
    for b in beats:
        b['tau'] = float(b['tau'])
    by_seg = {}
    for b in beats:
        by_seg.setdefault(b['seg'], []).append(b)
    c = m.c_of(t)
    shown = set()
    for n, g in enumerate(m.SEG):
        # この区間が画面に入っているか（回した時刻で）
        k = round((c - (g['s0'] + g['s1'])/2) / m.LTOT)
        s0, s1 = g['s0'] + k*m.LTOT, g['s1'] + k*m.LTOT
        if s1 < c - m.XC/m.PXS - 0.3 or s0 > c + (m.W - m.XC)/m.PXS + 0.3:
            continue
        key = g['key']
        mode = _blk_mode(m, t, g)
        bs = by_seg.get(n, [])
        a = a_all
        if key == 'モビッツII':
            mobitz(m, img, t, bs, g, a)
        elif key == '完全房室ブロック':
            chb(m, img, t, bs, g, a)
        elif key == 'ショートラン':
            shortrun(m, img, t, bs, g, a, mode)
        elif key == '単形性VT':
            vt(m, img, t, bs, g, a)
            bk = m.PAT_BLOCK[g['idx']]
            aa = a*ease((t - (bk['p'] + m.TEXT_IN)) / 0.35)*(1 - ease((t - (bk['end'] - 0.3)) / 0.3))
            if aa > 0.01:
                signpost(m, img, 800, m.NAME_CY, g['pat']['col'], a=aa)
        elif key == '多形性VT':
            poly(m, img, t, g, a)
        elif key == 'トルサード':
            torsade(m, img, t, g, a)
            bk = m.PAT_BLOCK[g['idx']]
            t_stop = g['T'] + (g['hb'] - g['s0'])/m.SLOW                 # ねじれの終わりが真ん中を過ぎたら
            aa = a*ease((t - t_stop) / 0.35)*(1 - ease((t - (bk['end'] - 0.3)) / 0.3))
            if aa > 0.01:
                loop_arrow(m, img, 830, m.NAME_CY, 26, g['pat']['col'], a=aa, rot=2*math.pi*0.35*t)
        elif key == 'R on T':
            ront(m, img, t, bs, g, a)
        elif key == '粗いVF':
            coarse_vf(m, img, t, g, a)
            ob = m.OV_BLOCK[3]
            if ob['start'] <= t < ob['end'] + 0.3:                       # ④ 場所の説明：虫めがねで「どこ？」と、空いた名札
                ao = a*ease((t - ob['start'] - 0.3) / 0.3)*(1 - ease((t - ob['end']) / 0.3))
                u = cl((t - ob['start'] - 0.3) / max(0.5, ob['end'] - ob['start'] - 0.6))
                gx = 230 + 600*ease(u)
                gy = m.BASE - 0.12*m.G                                   # 波形の上を探す
                magnifier(img, gx, gy, 60, col=g['pat']['col'], a=ao)
                bubble(m, img, gx + 4, gy - 250, 'どこ？', a=ao, tail=(gx, gy - 66))
                name_tag(m, img, 880, m.NAME_CY, g['pat']['col'], a=ao)
        elif key == '細かいVF':
            bk = m.PAT_BLOCK[g['idx']]
            am = a*ease((t - bk['p']) / 0.3)*(1 - ease((t - (bk['end'] - 0.3)) / 0.3))
            if am > 0.01:
                magnifier(img, m.XC - 60, m.BASE - 10, 110, g['pat']['col'], a=am*0.9)
            la = a*ease((t - (bk['p'] + m.TEXT_IN + 1.5)) / 0.3)*(1 - ease((t - (bk['end'] - 0.3)) / 0.3))
            if la > 0.01:
                lightning(img, 880, m.NAME_CY - 4, 40, a=la)
        elif key == '心静止':
            bk = m.PAT_BLOCK[g['idx']]
            tb = t - bk['p']
            fade = 1 - ease((t - (bk['end'] - 0.3)) / 0.3)
            pa = a*ease((tb - 0.3) / 0.3)*fade
            if pa > 0.01:
                gap = 10*(0.5 + 0.5*math.sin(2*math.pi*0.8*t))
                plug(img, 330, m.BASE - 150, 45, g['pat']['col'], a=pa, gap=gap)
                bubble(m, img, 330, m.BASE - 246, '外れ？', a=pa, tail=(330, m.BASE - 195))
            ca = a*ease((tb - 1.4) / 0.35)*fade
            if ca > 0.01:
                cpr_gloves(m, img, 770, m.BASE - 200, 60, g['pat']['col'], a=ca, press=0.5 + 0.5*math.sin(2*math.pi*1.8*t))
        elif key == 'PEA1':
            pea1(m, img, t, bs, g, a)
        elif key == 'PEA2':
            pea2(m, img, t, bs, g, a)
        elif key == '洞調律' and t >= m.END_B['start']:
            ending(m, img, t, bs, a*ease((t - m.END_B['start'] - 0.3) / 0.4))
        shown.add(key)
    # ⑤ の小物（⑤ の場面のあいだ）
    s0, s1 = m.scene_span(4)
    a5 = a_all*ease((t - (s0 + 0.4)) / 0.35)*(1 - ease((t - (s1 - 0.35)) / 0.3))
    if a5 > 0.01:
        scene5_props(m, img, t, a5)


def draw(m, img, t, layer='any'):
    """make_reel21v4.frame から呼ばれる。layer='under'：顔と手ぶくろ（線の下）／'over'：吹き出し・小物（線の上）。"""
    global LAYER
    LAYER = layer
    try:
        _draw(m, img, t)
    finally:
        LAYER = 'any'


def plan_faces(m, t):
    """--check 用：そのコマに描く顔（位置と大きさ）だけを返す。"""
    global DRY, _DUMMY, LAYER
    if _DUMMY is None:
        _DUMMY = Image.new('RGBA', (m.W, m.H), (0, 0, 0, 0))
    DRY = True
    LAYER = 'under'
    FACE_LOG.clear()
    try:
        _draw(m, _DUMMY, t)
    finally:
        DRY = False
        LAYER = 'any'
    return list(FACE_LOG)


def face_clearance(m, t, f):
    """顔の楕円（線の太さ・すき間こみ）と、そのコマの波形の線との、いちばん近い正規化した距離。1 より大きければふれない。
    こぶの内側（上向きのこぶは、顔の真上に波形）でなければ 0。"""
    ax, ay = f['axk']*f['r'] + 2, AY_K*f['r'] + 2
    A, B = ax + LINE_M, ay + LINE_M
    xs = np.arange(f['x'] - A - 2, f['x'] + A + 2, 0.25)
    tau = m.c_of(t) + (xs - m.XC)/m.PXS
    ys = m.BASE - m.stream_wave(tau)*m.G
    d = float(np.min(np.abs((xs - f['x'])/A)**SE + np.abs((ys - f['y'])/B)**SE))**(1/SE)
    yc = m.BASE - float(m.stream_wave(np.array([m.c_of(t) + (f['x'] - m.XC)/m.PXS]))[0])*m.G
    inside = (yc < f['y'] - B) if f['sign'] > 0 else (yc > f['y'] + B)
    below_base = (f['y'] + B <= m.BASE + LINE_M) if f['sign'] > 0 else (f['y'] - B >= m.BASE - LINE_M)
    return d if (inside and below_base) else 0.0
