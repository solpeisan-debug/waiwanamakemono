"""第21弾v3：波形の部品（Pくん・QRSくん・Tちゃん・PVCくん）の顔と手、小物（定規・虫めがね・ハートなど）。

make_reel21v3.draw_overlays から毎コマ呼ばれる（draw(m, img, t, scene, pattern, geos)）。
- 顔と手は「紹介中の大きな帯」（と場所の説明の帯）の波形の上に描き、波形と一緒に 25mm/秒で流れる。小さく薄い帯には描かない
- 動きは「その拍が画面の右端に入ってからの時間 d」と「そのブロック（場所の説明・パターン）の始まりからの時間」で決める
  → 録音に合わせて秒数を組み直しても、拍とブロックについていく
- 特徴の部分（抜けたQRS・R on T の接点など）は隠さない。④⑤（心停止）はまじめな顔だけ。心静止の線には顔を描かない

描き方：小さな下書き（3倍の大きさ）に描いて縮め、合成する（線がなめらかになる）。白い線＋濃い縁どり。
"""
import math

import numpy as np
from PIL import Image, ImageDraw

DK = (6, 14, 12)              # 縁どり
LT = (242, 247, 245)          # 顔・手の線
EYE = (250, 252, 252)
SWEAT = (140, 205, 255)
SS = 3
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
        if a <= 0.01:
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
    ex, ey = 0.42*r, -0.08*r
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
                th = k*0.55 + (rot*2 if sgn > 0 else -rot*2)
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


def ruler(m, img, x0, x1, y, col, a=1.0, mark=None):
    """定規（1mm＝14px の目盛り）。mark=(xa, xb) で幅のしるし（両矢印）。"""
    if LAYER == 'under':
        return
    h = 33
    pad = Pad(x0 - 8, y - 42, x1 + 8, y + h + 8)
    pad.rrect(x0, y, x1, y + h, 4, fill=(232, 222, 190), outline=DK, w=2.5)
    for k in range(int((x1 - x0) / 14) + 1):
        xx = x0 + 6 + k*14
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


def cpr_hands(m, img, x, y, s, col, a=1.0, press=0.0):
    """胸骨圧迫：胸（弧）の上に重ねた手（親指つき）と、下向きの矢印、「CPR」の字。press：押しこみ（0〜1）。"""
    if LAYER == 'under':
        return
    yy = y + press*0.16*s
    pad = Pad(x - 1.5*s, y - 1.1*s, x + 1.5*s, y + 1.9*s)
    chest = arc_pts(x, y + 1.55*s, 1.35*s, 0.75*s, 200, 340, n=24)
    pad.line(chest, DK, 8, a=200); pad.line(chest, (200, 205, 205), 4)
    skin, skin2 = (238, 210, 190), (248, 226, 208)
    # 下の手（親指は左）
    x0, y0, x1, y1 = x - 0.8*s, yy + 0.05*s, x + 0.8*s, yy + 0.62*s
    pad.ell(x0 + 0.05*s, y0 + 0.12*s, 0.24*s, 0.15*s, fill=skin, outline=DK, w=2.4)
    pad.rrect(x0, y0, x1, y1, 0.26*s, fill=skin, outline=DK, w=2.6)
    # 上の手（親指は右）
    x2, y2, x3, y3 = x - 0.72*s, yy - 0.42*s, x + 0.72*s, yy + 0.18*s
    pad.ell(x3 - 0.02*s, y2 + 0.12*s, 0.24*s, 0.15*s, fill=skin2, outline=DK, w=2.4)
    pad.rrect(x2, y2, x3, y3, 0.26*s, fill=skin2, outline=DK, w=2.6)
    for j in range(1, 4):
        xx = x2 + (x3 - x2)*j/4
        pad.line([(xx, y3 - 0.2*s), (xx, y3 - 0.04*s)], (150, 110, 95), 1.8, cap=False)
    for sx in (-1.15, 1.15):
        ax = x + sx*s
        pad.line([(ax, yy - 0.3*s), (ax, yy + 0.35*s)], DK, 8, a=220)
        pad.line([(ax - 0.18*s, yy + 0.12*s), (ax, yy + 0.37*s), (ax + 0.18*s, yy + 0.12*s)], DK, 8, a=220)
        pad.line([(ax, yy - 0.3*s), (ax, yy + 0.35*s)], col, 4.2)
        pad.line([(ax - 0.18*s, yy + 0.12*s), (ax, yy + 0.37*s), (ax + 0.18*s, yy + 0.12*s)], col, 4.2)
    pad.paste(img, a)
    m.put(img, 'CPR', 36, 900, col, cx=x, cy=y - 0.85*s, a=a)


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


def finger(img, x, y, s, a=1.0, press=0.0):
    """脈をみる手：手首（帯）の上に、2本の指をそろえて当てる。(x, y) は指先。"""
    if LAYER == 'under':
        return
    yy = y - press*3
    skin, skin2 = (238, 210, 190), (248, 226, 208)
    pad = Pad(x - 2.0*s, yy - 2.6*s, x + 2.0*s, y + 1.0*s)
    pad.rrect(x - 1.9*s, y - 0.05*s, x + 1.9*s, y + 0.8*s, 0.4*s, fill=skin, outline=DK, w=2.6)
    pad.ell(x, y + 0.3*s, 0.22*s, 0.14*s, fill=(255, 110, 125), a=200)
    pad.rrect(x - 0.75*s, yy - 2.5*s, x + 0.95*s, yy - 1.3*s, 0.35*s, fill=skin2, outline=DK, w=2.6)
    for ox in (-0.3*s, 0.3*s):
        pad.rrect(x + ox - 0.27*s, yy - 1.55*s, x + ox + 0.27*s, yy + 0.02*s, 0.26*s, fill=skin2, outline=DK, w=2.4)
    pad.paste(img, a)


def mini_char(m, img, kind, x, y, s, col, t, a=1.0, wave_hand=True, phase=0.0):
    """最後に並ぶ小さなキャラクター（波形の部品の形＋顔＋手をふる）。y は基線。"""
    if kind == 'P':
        pts = [(x - 0.9*s + 1.8*s*k/20, y - 0.45*s*math.exp(-((k - 10)/4.5)**2)) for k in range(21)]
        fx, fy, r = x, y - 0.45*s - 0.52*s, 0.56*s
    elif kind == 'QRS':
        pts = [(x - 0.6*s, y), (x - 0.18*s, y), (x - 0.1*s, y + 0.12*s), (x, y - 1.55*s), (x + 0.1*s, y + 0.25*s),
               (x + 0.18*s, y), (x + 0.6*s, y)]
        fx, fy, r = x, y - 1.55*s + 0.3*s, 0.66*s
    else:
        pts = [(x - 1.0*s + 2.0*s*k/24, y - 0.62*s*math.exp(-((k - 12)/5.5)**2)) for k in range(25)]
        fx, fy, r = x, y - 0.62*s - 0.05*s, 0.5*s
    pad = Pad(min(p[0] for p in pts) - 10, min(p[1] for p in pts) - 10, max(p[0] for p in pts) + 10, y + 0.4*s)
    pad.line(pts, DK, 8, a=200)
    pad.line(pts, col, 4.2)
    pad.paste(img, a)
    face(img, fx, fy, r, 'happy' if kind != 'QRS' else 'smile', a=a)
    if wave_hand:
        ang = math.radians(-60 + 25*math.sin(2*math.pi*1.6*t + phase))
        sh = (fx + r*0.6, fy + r*0.5)
        hd = (sh[0] + 0.55*s*math.cos(ang), sh[1] + 0.55*s*math.sin(ang))
        arms(img, [(sh, hd)], a=a)


# --- 帯の上の拍 ------------------------------------------------------------------------
class Strip:
    """帯の形（geo）と時刻 t から、拍の画面の位置を計算する道具（拡大・ゆっくりにも対応）。"""
    def __init__(self, m, geo, t):
        self.m, self.geo, self.t = m, geo, t
        self.i = geo['i']
        self.pat = m.PATTERNS[geo['i']]
        self.base, self.g, self.dx = geo['base'], geo['g'], geo.get('dx', 0.0)
        self.pxs = geo.get('pxs', m.F_PXS)
        self.sc = cl(self.g / m.HI_MV, 0.3, 1.3)          # 280px/mV で 1（2.5倍の 350px/mV で 1.25）
        self.v = max(1.0, m.screen_speed(self.i, t, self.pxs))

    def xp(self, rel):
        return float(self.m.x_of(self.i, self.t, rel, self.pxs))

    def x(self, rel):
        return self.xp(rel) + self.dx

    def d(self, rel):
        """その点が画面の右端に入ってからの時間（秒・画面の上の時間）。"""
        return (self.m.W - self.xp(rel)) / self.v

    def y(self, rel):
        return self.base - float(self.m.pattern_wave(self.i, np.array([float(rel)]))[0]) * self.g

    def rng(self, margin=120):
        return (float(self.m.rel_at(self.i, self.t, -margin, self.pxs)),
                float(self.m.rel_at(self.i, self.t, self.m.W + margin, self.pxs)))

    def beats(self, margin=120):
        r0, r1 = self.rng(margin)
        out = []
        L = self.pat['L']
        for k in range(int(math.floor(r0 / L)) - 1, int(math.ceil(r1 / L)) + 1):
            for j, (r, kind) in enumerate(self.pat['ev']):
                rr = k*L + r
                if r0 <= rr <= r1:
                    if self.pat.get('gain') is not None and self.pat['gain'](np.array([rr]), L)[0] < 0.5:
                        continue
                    out.append(dict(rel=rr, kind=kind, j=j, k=k, idx=k*len(self.pat['ev']) + j))
        return out

    def extrema(self, thr, sign=1, margin=120, min_gap=0.06):
        """周期の中の山（sign=-1 で谷）の rel。画面に見えるものだけ。"""
        key = ('ext', self.i, thr, sign, min_gap)
        L = self.pat['L']
        if key not in _CACHE:
            rel = np.arange(0, L, 0.002)
            v = self.m.pattern_wave(self.i, rel) * sign
            pk = []
            for k in range(1, len(v) - 1):
                if v[k] > thr and v[k] >= v[k-1] and v[k] >= v[k+1]:
                    if pk and rel[k] - pk[-1][0] < min_gap:
                        if v[k] > pk[-1][1]:
                            pk[-1] = (rel[k], v[k])
                        continue
                    pk.append((rel[k], v[k]))
            _CACHE[key] = [p for p, _ in pk]
        cache = _CACHE[key]
        r0, r1 = self.rng(margin)
        out = []
        for k in range(int(math.floor(r0 / L)) - 1, int(math.ceil(r1 / L)) + 1):
            for n, c in enumerate(cache):
                rr = k*L + c
                if r0 <= rr <= r1:
                    out.append((rr, k*len(cache) + n))
        return out


_CACHE = {}


# 顔は「こぶの中」：P波・T波のこぶの中、R（とがった波）は上のほう、幅の広い波はその中。
# 顔と手は波形の線の下に描くので、線はいつも見える
def p_face(S, rel):
    """Pくん：P波のこぶの中（中心と半径）。"""
    yp = S.y(rel)
    h = max(8.0, S.base - yp)
    return S.x(rel), S.base - 0.46*h, cl(0.62*h, 10, 52)


def t_face(S, rel, shift=0.0):
    yt = S.y(rel)
    h = max(8.0, S.base - yt)
    return S.x(rel) + shift, S.base - 0.44*h, cl(0.55*h, 10, 52)


def r_face(S, rel, r=46.0, k=0.36):
    """QRSくん・PVCくん：とがった波（上向きは先のほう、下向きは谷のほう）の中。"""
    y = S.y(rel)
    h = S.base - y
    r = r*S.sc
    if h >= 0:
        return S.x(rel), y + k*h, r
    return S.x(rel), y + k*h, r          # 下向き：h<0 なので谷から上へ


def _alpha_block(t, b, fi=0.3, fo=0.3, lead=0.2):
    return ease((t - (b['start'] + lead)) / fi) * (1 - ease((t - (b['end'] - fo)) / fo))


def handshake(img, S, a, t, rel_p, rel_r, reach_u, expr_p='smile', expr_q='smile'):
    xp, yp, rp = p_face(S, rel_p)
    xq, yq, rq = r_face(S, rel_r)
    mid = ((xp + xq)/2 + 6, S.base - 44*S.sc + 4*math.sin(2*math.pi*3.0*t)*(reach_u >= 0.99))
    shp = (xp + 0.55*rp, yp)
    shq = (xq - 4, S.base - 80*S.sc)
    hp = (shp[0] + (mid[0] - 4 - shp[0])*reach_u, shp[1] + (mid[1] - shp[1])*reach_u)
    hq = (shq[0] + (mid[0] + 4 - shq[0])*reach_u, shq[1] + (mid[1] - shq[1])*reach_u)
    arms(img, [(shp, hp), (shq, hq)], a=a)
    face(img, xp, yp, rp, expr_p, a=a)
    face(img, xq, yq, rq, expr_q, a=a)


# --- 場面ごと（紹介中＝mode 'hi' のときだけ顔。場所の説明＝'ov' は小物だけ） ---------------------
def scene1(m, img, t, S, mode, a, blk):
    if mode != 'hi':
        return
    key = S.pat['key']
    if key == 'モビッツII':
        for b in S.beats():
            if b['kind'] == 'N' and b['j'] == 2:                 # 抜ける前の、伝わる拍（握手）
                rel_p = b['rel'] - m.PR
                u = ease((S.d(rel_p) - 0.05) / 0.4)
                handshake(img, S, a, t, rel_p, b['rel'], u)
            elif b['kind'] == 'P':
                _dropped(m, img, t, S, b['rel'], a)
    elif key == '完全房室ブロック':
        bts = S.beats()
        ws = [b['rel'] for b in bts if b['kind'] == 'W']
        ps = [b for b in bts if b['kind'] == 'P' and not any(-0.3 < b['rel'] - w < 0.55 for w in ws)]
        ps.sort(key=lambda b: abs(S.x(b['rel']) - m.XC))
        for b in ps[:2]:
            xp, yp, rp = p_face(S, b['rel'])
            reach = 0.5 + 0.5*math.sin(2*math.pi*0.7*t + b['idx'])
            sh = (xp + 0.55*rp, yp)
            hd = (sh[0] + 16 + 34*reach, sh[1] - 10 - 8*reach)
            arms(img, [(sh, hd)], a=a)
            face(img, xp, yp, rp, 'serious', a=a, look=-1.0)
        for w in ws:
            bob = 4*abs(math.sin(math.pi*0.9*t))
            xq, yq, rq = r_face(S, w, 42, 0.38)
            face(img, xq, yq - bob, rq, 'tired', a=a, look=1.0)


def _dropped(m, img, t, S, rel_p, a):
    """モビッツII型の抜け：Pくんの手が空ぶり（あっ）→ QRSくんが基線の下からのぞく（あらっ）→ 下へ落ちる。"""
    d = S.d(rel_p)
    if d < -0.3 or d > 3.4:
        return
    xp, yp, rp = p_face(S, rel_p)
    sh = (xp + 0.55*rp, yp)
    target = (xp + m.PR*S.pxs/2 + 8, S.base - 44*S.sc)
    u = ease((d - 0.05) / 0.4) * (1 - ease((d - 0.8) / 0.45))
    over = ease((d - 0.4) / 0.3) * (1 - ease((d - 0.8) / 0.45))
    hd = (sh[0] + (target[0] + 18*over - sh[0])*u, sh[1] + (target[1] + 8*over - sh[1])*u)
    arms(img, [(sh, hd)], a=a)
    face(img, xp, yp, rp, 'smile', a=a, expr2='ah', u=ease((d - 0.45) / 0.25))
    bubble(m, img, xp - 10, S.base - 150*S.sc, 'あっ', a=a*win(d, 0.5, 1.7, 0.2, 0.3), tail=(xp, yp - rp))
    # QRSくん（来るはずだった位置）が基線の下からのぞき、落ちる
    xe = xp + m.PR*S.pxs
    rq = 40*S.sc
    rise = ease((d - 0.6) / 0.4)
    fall = ease((d - 1.9) / 0.6)
    yq = S.base + rq + 105 - 95*rise + 150*fall*fall
    aq = a*rise*(1 - ease((d - 2.3) / 0.3))
    if aq > 0.01:
        rot = 0.5*fall
        face(img, xe, yq, rq, 'serious', a=aq, expr2='oops', u=ease((d - 0.95) / 0.25), rot=rot)
        if fall < 0.05:
            arms(img, [((xe - rq*0.7, yq - rq*0.2), (xe - rq*1.05, S.base + 4)),
                       ((xe + rq*0.7, yq - rq*0.2), (xe + rq*1.05, S.base + 4))], a=aq)
        else:
            arms(img, [((xe - rq*0.7, yq - rq*0.2), (xe - rq*1.2, yq - rq*1.2)),
                       ((xe + rq*0.7, yq - rq*0.2), (xe + rq*1.2, yq - rq*1.2))], a=aq)
        bubble(m, img, xe + rq + 100, S.base + 70, 'あらっ', a=aq*win(d, 1.0, 1.95, 0.2, 0.25), tail=(xe + rq*0.8, yq))


def scene2(m, img, t, S, mode, a, blk):
    key = S.pat['key']
    if mode == 'ov':
        if key != '単形性VT':
            return
        # 定規（画面に止めて置き、QRSが流れて通る）。幅のしるしは QRS の幅（モデルから）
        ar = a*win(t, blk['start'] + 0.3, blk['end'], 0.3, 0.3)
        if ar > 0.01:
            qw = m._qrs_ms(m.qrs_vt_rs, 0.3) / 1000 * S.pxs
            xr0 = 330 + S.dx
            yb = S.base + 0.75*S.g + 26
            ruler(m, img, xr0, xr0 + 315, yb, S.pat['col'], a=ar, mark=(xr0 + 105, xr0 + 105 + qw))
        return
    if mode != 'hi':
        return
    if key == 'ショートラン':
        bts = [b for b in S.beats() if b['kind'] == 'V']
        groups = {}
        for b in bts:
            groups.setdefault(b['k'], []).append(b)
        for k, g in groups.items():
            g.sort(key=lambda b: b['rel'])
            if len(g) < 3:
                continue
            sit = ease((S.d(g[-1]['rel']) - 0.75) / 0.35)
            faces = []
            for n, b in enumerate(g):
                xq, yq, rq = r_face(S, b['rel'], 38)
                faces.append((xq, yq + 4*math.sin(2*math.pi*3.0*t + n*1.3)*(1 - sit), rq))
            segs = []
            for n in range(1, len(faces)):
                (x1, y1, r1), (x0, y0, r0) = faces[n], faces[n-1]
                segs.append(((x1 - 0.6*r1, y1 + 0.4*r1), (x0 + 0.75*r0, y0 + 0.45*r0)))
            x0, y0, r0 = faces[0]
            segs.append(((x0 - 0.6*r0, y0 + 0.4*r0), (x0 - 1.2*r0, y0 - 8*(1 - sit))))
            arms(img, segs, a=a)
            for (xq, yq, rq) in faces:
                face(img, xq, yq, rq, 'determined', a=a, expr2='happy', u=sit)
    elif key == '単形性VT':
        step = 2*math.pi*1.6
        for b in S.beats():
            if b['idx'] % 3:
                continue                                      # 3拍に1つだけ（同じ顔）
            bob = 3*math.sin(step*t)
            xq, yq, rq = r_face(S, b['rel'], 38)
            yq += bob
            sw = 8*math.sin(step*t)
            arms(img, [((xq - 0.5*rq, yq + 0.5*rq), (xq - 0.8*rq + sw, yq + 1.1*rq)),
                       ((xq + 0.5*rq, yq + 0.5*rq), (xq + 0.8*rq + sw, yq + 1.1*rq))], a=a)
            face(img, xq, yq, rq, 'smile', a=a)
        aa = a*ease((t - (blk['start'] + m.TEXT_IN)) / 0.35)
        if aa > 0.01:
            signpost(m, img, 800 + S.dx, m.BIG_LBL_CY, S.pat['col'], a=aa)
    elif key == '多形性VT':
        exprs = ['angry', 'surprised', 'troubled', 'ah', 'serious', 'oops', 'worried']
        L = S.pat['L']
        r0, r1 = S.rng()
        for k in range(int(math.floor(r0 / L)) - 1, int(math.ceil(r1 / L)) + 1):
            for n, (c, amp, kind) in enumerate(m.POLY):
                if n % 2:
                    continue                                  # 1拍おきに（顔を少なく）
                rr = k*L + c + (0.012 if kind == 1 else 0.0)
                if not (r0 <= rr <= r1):
                    continue
                xq, yq, rq = r_face(S, rr, 38, 0.34)
                face(img, xq, yq, rq, exprs[(n*3 + k) % len(exprs)], a=a)
    elif key == 'トルサード':
        L = S.pat['L']
        cand = []
        for sign in (1, -1):
            for rr, idx in S.extrema(0.6, sign=sign, min_gap=0.12):
                if m.TDP_A < rr % L < m.TDP_B:
                    cand.append((abs(S.x(rr) - m.XC), rr, idx))
        for _, rr, idx in sorted(cand)[:3]:                  # 真ん中に近い3つだけ
            xq, yq, rq = r_face(S, rr, 40, 0.3)
            face(img, xq, yq, rq, 'dizzy', a=a, rot=2*math.pi*1.0*t + idx*0.9)
        # 止まったところが画面に入ったら「くり返す」の矢印
        a0, b0 = S.pat['hl'][0]
        te = blk['start'] + S.pat['enter']
        rr = float(m.rel_at(S.i, te, m.W, m.hi_pxs(S.i)))
        k = round((rr - a0) / L)
        t_stop = m.t_of_clock(S.i, b0 + k*L - m.PHASE[S.i] - (m.W - m.XC) / m.hi_pxs(S.i))
        aa = a*ease((t - t_stop) / 0.35)
        if aa > 0.01:
            loop_arrow(m, img, 700 + S.dx, m.BIG_LBL_CY, 30, S.pat['col'], a=aa, rot=2*math.pi*0.35*t)


RONT_DELAY = 0.7          # R on T のできごとが画面の真ん中あたりで起きるように（秒）


def scene3(m, img, t, S, mode, a, blk):
    if mode != 'hi':
        return
    for b in S.beats():
        if b['kind'] != 'N' or abs((b['rel'] % S.pat['L']) - 0.8) > 1e-6:
            continue                                          # R on T がある拍だけ（Tちゃん・PVCくん）
        rel_t = b['rel'] + m.T_PEAK['N']
        rel_v = b['rel'] + m.RONT_C
        d = S.d(rel_v) - RONT_DELAY
        xt, yt, rt = t_face(S, rel_t, shift=-14*S.sc)            # 接点（PVCの立ち上がり）を隠さないよう左へ
        xtp = S.x(rel_t)
        # PVCくん：跳んできて T波に乗る
        jump = 1 - ease((d - 0.05) / 0.4)
        xv, yv, rv = r_face(S, rel_v, 40)
        yv -= 70*jump*math.sin(math.pi*cl((d + 0.6) / 1.05))
        face(img, xv, yv, rv, 'determined', a=a, expr2='ah', u=ease((d - 0.6) / 0.25))
        arms(img, [((xv - 0.55*rv, yv + 0.4*rv), (xv - 0.95*rv, yv - 0.3*rv*jump)),
                   ((xv + 0.55*rv, yv + 0.4*rv), (xv + 0.95*rv, yv - 0.3*rv*jump))], a=a)
        face(img, xt, yt, rt, 'calm', a=a, expr2='surprised', u=ease((d - 0.4) / 0.2))
        bubble(m, img, xtp - 70, S.base - 205*S.sc, 'ひゃっ', a=a*win(d, 0.45, 1.8, 0.2, 0.3), tail=(xt - 6, yt - rt))
        sa = a*win(d, 0.45, 1.3, 0.12, 0.3)
        if sa > 0.01:
            spark(img, xtp + 8, S.base - 112*S.sc, 26, a=sa, rot=t*3)
            lightning(img, xv + rv + 40, yv - 10, 30, a=sa)
        fa = a*win(d, 0.8, 1.7, 0.12, 0.3)
        if fa > 0.01:
            _vf_hint(img, xv + 200, S.base - 200*S.sc, fa, t)


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


def scene4(m, img, t, S, mode, a, blk):
    key = S.pat['key']
    col = S.pat['col']
    if mode == 'ov':
        if key != '粗いVF':
            return
        u = cl((t - blk['start'] - 0.3) / max(0.5, blk['dur'] - 0.8))
        gx = 230 + 600*ease(u) + 25*math.sin(2*math.pi*0.9*t) + S.dx
        gy = S.base - 10 + 14*math.sin(2*math.pi*0.6*t)
        magnifier(img, gx, gy, 51, col, a=a)
        bubble(m, img, gx + 4, gy - 112, 'どこ？', a=a, tail=(gx, gy - 58))
        name_tag(m, img, 862 + S.dx, S.geo.get('lbl_cy', S.base - 120), col, a=a)
        return
    if mode != 'hi':
        return
    if key == '粗いVF':
        cand = [(abs(S.x(rr) - m.XC), rr, idx) for rr, idx in S.extrema(0.3, sign=1, min_gap=0.1)
                if 150 + S.dx < S.x(rr) < m.W - 150 + S.dx]
        for _, rr, idx in sorted(cand)[:3]:                  # 真ん中に近い3つだけ
            xq, yq = S.x(rr), S.y(rr)
            h = S.base - yq
            jit = 3*math.sin(2*math.pi*4*t + idx*1.7)
            face(img, xq + jit, yq + 0.42*h, 30*S.sc, 'worried', a=a)
    elif key == '細かいVF':
        tb = t - blk['start']
        gx = 300 + 360*ease((tb - 0.3) / 1.4) + S.dx
        gy = S.base - 4
        rg = 84
        ga = a*(1 - ease((tb - (blk['dur'] - 0.6)) / 0.3))
        found = ease((tb - 1.5) / 0.4)
        if found > 0.01:
            near = [(abs(S.x(rr) - gx), rr) for rr, idx in S.extrema(0.07, sign=1, min_gap=0.07)
                    if abs(S.x(rr) - gx) < rg - 20]
            if near:
                rr = min(near)[1]                       # 虫めがねの真ん中の小さな山に、1つだけ顔
                h = S.base - S.y(rr)
                face(img, S.x(rr), S.base - 0.4*h, 30, 'worried', a=a*found)
        magnifier(img, gx, gy, rg, col, a=ga)
        la = a*ease((t - (blk['start'] + m.TEXT_IN + 0.5)) / 0.3)
        if la > 0.01:
            lightning(img, 880 + S.dx, m.BIG_LBL_CY + 6, 45, a=la)
    elif key == '心静止':
        tb = t - blk['start']
        pa = a*ease((tb - 0.3) / 0.3)
        if pa > 0.01:
            gap = 10*(0.5 + 0.5*math.sin(2*math.pi*0.8*t))
            plug(img, 450 + S.dx, S.base - 90, 45, col, a=pa, gap=gap)
            bubble(m, img, 450 + S.dx, S.base - 186, '外れ？', a=pa, tail=(450 + S.dx, S.base - 135))
        ca = a*ease((tb - 1.4) / 0.35)
        if ca > 0.01:
            press = 0.5 + 0.5*math.sin(2*math.pi*1.8*t)
            cpr_hands(m, img, 800 + S.dx, S.base - 175, 60, col, a=ca, press=press)


def scene5_props(m, img, t, dx, y, col, a):
    """⑤：動かないハート（脈がない）と、脈をみる手（？）。"""
    heart(img, m.XC - 130 + dx, y, 57, col, a=a)
    press = 0.5 + 0.5*math.sin(2*math.pi*0.8*t)
    finger(img, m.XC + 110 + dx, y + 46, 36, a=a, press=press)
    bubble(m, img, m.XC + 235 + dx, y - 40, '？', a=a, tail=(m.XC + 150 + dx, y - 20))


def scene5(m, img, t, S, mode, a, blk):
    if mode != 'hi':
        return
    key = S.pat['key']
    if key == 'PEA1':
        for b in S.beats():
            xq, yq, rq = r_face(S, b['rel'], 40)
            face(img, xq, yq, rq, 'calm', a=a)
    elif key == 'PEA2':
        for b in S.beats():
            bob = 4*abs(math.sin(math.pi*0.7*t))
            xq, yq, rq = r_face(S, b['rel'], 42, 0.38)
            face(img, xq, yq - bob, rq, 'tired', a=a)


SCENE5_PROP_Y = 1190


def draw(m, img, t, scene, pattern, geos, layer='any'):
    """make_reel21v3 から呼ばれる。layer='under'：顔と手（波形を描く前）／'over'：吹き出し・小物（波形のあと）。"""
    global LAYER
    LAYER = layer
    try:
        _draw(m, img, t, geos)
    finally:
        LAYER = 'any'


def _draw(m, img, t, geos):
    for geo in geos:
        s = geo.get('scene')
        kind = geo.get('kind')
        if s is None or geo['a'] < 0.05:
            continue
        i = geo['i']
        if kind == 'hi':
            blk = m.PAT_BLOCK[i]
            if not (blk['start'] - 0.5 <= t < blk['end'] + 0.5):
                continue
            a = geo['a']*_alpha_block(t, blk, lead=0.35)
            mode = 'hi'
        elif kind == 'ov':
            blk = m.OV_BLOCK[s]
            if not (blk['start'] <= t < blk['end'] + 0.5):
                continue
            a = geo['a']*_alpha_block(t, blk, lead=0.35 if s else 0.6)
            mode = 'ov'
        else:
            continue
        if a <= 0.01:
            continue
        S = Strip(m, geo, t)
        (scene1, scene2, scene3, scene4, scene5)[s](m, img, t, S, mode, a, blk)
    # ⑤ の小物（場面について動く）
    if LAYER != 'under':
        for geo in geos:
            if geo.get('scene') != 4:
                continue
            s0, s1 = m.scene_span(4)
            a = ease((t - (s0 + 0.4)) / 0.35) * (1 - ease((t - (s1 - 0.35)) / 0.3))
            if a <= 0.01:
                break
            if geo.get('kind') == 'hi':
                up, down = m.big_room(geo['i'])
                y = geo['base'] + down*0.52
            elif geo['i'] == m.SCENE_PATS[4][0] and geo.get('kind') == 'ov':
                y = SCENE5_PROP_Y
            else:
                continue
            scene5_props(m, img, t, geo.get('dx', 0.0), y, m.PLACES[4]['col'], a)
            break


def draw_end_chars(m, img, t, a, dx, y):
    """最後：Pくん・QRSくん・Tちゃんが並んで手をふる（問いかけの上）。"""
    if a <= 0.01:
        return
    for k, (kind, s) in enumerate((('P', 80), ('QRS', 62), ('T', 78))):
        x = m.XC + (k - 1)*210 + dx
        mini_char(m, img, kind, x, y, s, m.WAVE_GREEN, t, a=a, phase=k*1.1)
