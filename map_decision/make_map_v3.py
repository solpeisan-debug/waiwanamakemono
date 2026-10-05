"""モニター心電図 見分けマップ v3（1枚で動く保存版。3枚組：①規則的な波形 ②不規則・QRSなし ③幅の広いQRS）。

v2（カードを並べただけ）は「なぜ並んでいるのか」がわかりにくかったので、マップ（質問と線）を第一にした。
- 左から右へ流れる分かれ道の図。質問は箱、線はまっすぐな直角の線だけ
- 枝の先に、その答えの波形カード（名前と、流れる小さなモニター）。カードは枝の先の空いている幅をぜんぶ使う
- 1コマ目から全部の波形が流れる。2秒ごとに1枚ずつ、根もとの質問からその波形までの道すじが光る（24秒で1周）
- 同じ質問の中で続けて聞く小さな質問（「毎回QRS？」「PとQRSの関係は？」など）は、カードの上の答えの字にまとめた
  （中身は v1 と同じ。専門医レビュー 2026-10-04 を反映済み。review_log.md）

波形は make_map_v2.py と同じ（周期はすべて 24 の約数なので、最後のコマの次が最初のコマとぴったり同じ）。
③（第27弾）の波形は make_map_v2.py の RHYTHMS に足した（'pace' 'vt' 'vesc' は①と同じ波形）。
③の字の大きさ・配置で①②とちがうのは ANS_MIN（答えの字の下限）だけ。専門医レビュー用の資料は make_review_pdf_v3.py。
ナレーションなし。

使い方:
    python3 make_map_v3.py --map 1              # 書き出し（out/map1_v3.mp4）
    python3 make_map_v3.py --map 2 --still 0 5  # 1コマだけ
    python3 make_map_v3.py --map 1 --thumb      # サムネイル（透かしなし）
    python3 make_map_v3.py --map 3 --still 9    # マップ③（幅の広いQRS）
    python3 make_map_v3.py --map 1 --hq         # 高画質（out/map1_v3_hq.mp4）
"""
import argparse
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# make_map / make_map_v2 は読み込むときに自分のマップ（①②）の設定を作る。③は v3 にしかないので、
# ③のときは①として読み込む（使うのは部品と波形だけなので、どちらでも同じ）
_MAP_ENV = os.environ.get('MAP_NO', '1')
os.environ['MAP_NO'] = _MAP_ENV if _MAP_ENV in ('1', '2') else '1'
import make_map as b  # noqa: E402
from make_map import (W, H, WHITE, YEL, CARD_FILL, C_RED, C_ORANGE, C_YEL, C_BLUE, C_GREEN, C_Q,  # noqa: E402
                      WATERMARK, put, text_img, glow_line, mix, ramp)
from make_map_v2 import RHYTHMS, rhythm_wave, r_times, DUR, SPEED  # noqa: E402
os.environ['MAP_NO'] = _MAP_ENV

HERE = os.path.dirname(os.path.abspath(__file__))
GREEN_SAVE = (130, 232, 172)
DIM_ANS = (214, 186, 110)
C_LINE = (104, 132, 124)          # 線
NODE_FILL = (12, 28, 24)
NODE_EDGE = (92, 116, 108)


# --- マップの中身（Q：質問の箱、L：波形カード。ans は前の質問への答え） ------------------------
def Q(ans, q, kids):
    return dict(kind='q', ans=ans, q=q, kids=kids)


def L(ans, name, col, key):
    return dict(kind='l', ans=ans, name=name, col=col, key=key)


MAPS = {
    1: dict(
        title=('見分けマップ①', ' 規則的な波形'),
        tree=Q('', 'スパイクが\nある？', [
            L('ペースメーカーのスパイクがある', 'ペースメーカー調律', C_BLUE, 'pace'),
            Q('ない', '心拍数は？', [
                Q('60未満', 'P波と\nQRSは？', [
                    L('P波なし・QRS狭い', '接合部補充調律', C_BLUE, 'junc'),
                    L('P波なし・QRS広い', '心室補充調律', C_RED, 'vesc'),
                    L('P波あり・毎回QRS', '洞徐脈', C_BLUE, 'sbrady'),
                    L('PとQRSは一定', '2:1・高度房室ブロック', C_RED, 'av21'),
                    L('PとQRSが別々', '完全房室ブロック', C_RED, 'chb'),
                ]),
                Q('60〜100', 'PRは？', [
                    L('0.2秒以下', '洞調律', C_GREEN, 'nsr'),
                    L('0.2秒より長い', '1度房室ブロック', C_YEL, 'av1'),
                ]),
                Q('100以上', 'QRS幅と\nP波は？', [
                    L('狭い・P波ふつう', '洞頻脈', C_GREEN, 'stach'),
                    L('狭い・のこぎり状', '心房粗動', C_ORANGE, 'flut'),
                    L('狭い・P波見えない', 'PSVT', C_ORANGE, 'psvt'),
                    L('広い（迷ったらVT）', '心室頻拍（VT）', C_RED, 'vt'),
                ]),
            ]),
        ]),
        notes=['※モニター（II誘導）で見る入口の一例。例外あり', '※幅の広い速い頻拍は、迷ったらVT（LITFL）'],
    ),
    2: dict(
        title=('見分けマップ②', ' 不規則・QRSなし'),
        tree=Q('', 'QRSは\nある？', [
            Q('ない', '何が見える？', [
                L('バラバラな揺れ', '心室細動（VF）', C_RED, 'vf'),
                L('P波だけ', 'P波だけの心静止', C_RED, 'pasys'),
                L('まっすぐ（電極も確認）', '心静止', C_RED, 'asys'),
            ]),
            Q('ある', 'どう不規則？', [
                Q('全部バラバラ', 'QRSの幅は？', [
                    L('狭い', '心房細動', C_ORANGE, 'af'),
                    L('広い', '心房細動＋脚ブロック・多形性VT', C_RED, 'afbbb'),
                ]),
                Q('早い1拍', '早い拍は？', [
                    L("狭い・前にP'", '心房期外収縮（PAC）', C_BLUE, 'pac'),
                    L('狭い・Pなし', '接合部期外収縮（PJC）', C_BLUE, 'pjc'),
                    L('広い', '心室期外収縮（PVC）', C_YEL, 'pvc'),
                ]),
                Q('ときどき抜ける', '抜けるのは？', [
                    L('P波ごと', '洞停止・洞房ブロック', C_BLUE, 'sarrest'),
                    L('QRSだけ・PRが伸びる', 'ウェンケバッハ', C_YEL, 'wk'),
                    L('QRSだけ・PR一定', 'モビッツII型', C_RED, 'm2'),
                ]),
                L('呼吸でゆれる', '洞性不整脈', C_GREEN, 'sarr'),
            ]),
        ]),
        notes=['※波形があっても、脈がなければPEA。まず患者さん', '※モニター（II誘導）で見る入口の一例。例外あり'],
    ),
    3: dict(
        title=('見分けマップ③', ' 幅の広いQRS'),
        tree=Q('', 'スパイクが\nある？', [
            L('ある・あとに広いQRS', 'ペースメーカー調律', C_BLUE, 'pace'),
            Q('ない', '心拍数は？', [
                Q('100以上', 'リズム\nは？', [
                    L('規則的・迷ったらこれ', '心室頻拍（VT）', C_RED, 'vt'),
                    L('規則的・前から脚ブロック', 'SVT＋変行伝導', C_ORANGE, 'svtbbb'),
                    L('規則的・前からWPW', '逆方向性AVRT', C_RED, 'avrtw'),
                    L('不規則・ねじれる', '多形性VT・トルサード', C_RED, 'tdp'),
                    L('不規則・同じ形', '心房細動＋脚ブロック', C_ORANGE, 'afbbb3'),
                    L('不規則・とても速い', '心房細動＋WPW', C_RED, 'afwpw'),
                ]),
                Q('60〜100', 'P波は？', [
                    L('あり・PRふつう', '脚ブロック', C_YEL, 'bbb'),
                    L('あり・PR短い・デルタ波', 'WPW', C_YEL, 'wpw'),
                    L('なし', '促進心室固有調律（AIVR）', C_YEL, 'aivr'),
                ]),
                Q('60未満', 'P波と\nT波は？', [
                    L('P波なし', '心室補充調律', C_RED, 'vesc'),
                    L('P波平ら・T波とがる', '高カリウム血症', C_RED, 'hyperk'),
                ]),
            ]),
        ]),
        notes=['※幅の広い速い頻拍は、迷ったらVT。まず患者さん', '※II誘導の一例。右脚・左脚の区別は12誘導で'],
    ),
}
MAP = int(os.environ.get('MAP_NO', '1'))
CFG = MAPS[MAP]

# --- 配置 ---------------------------------------------------------------------------------
X0, X_END = 72, 1000                # 左72px・右80px（右下はリールのボタンがかかるので少し広め）
Y_FIRST, Y_LAST = 494, 1500       # 1枚目と最後のカードのまん中（見出しとの間を約60px空ける）
GAP_X = 30                        # 箱の右 → 縦の線 14px → 子 16px
SZ_Q, SZ_A = 25, 19
CARD_H = 86
PAD = 12


def tw(s, size, weight):
    return text_img(s, size, weight, WHITE)[0].size[0] - 8


def node_size(n):
    lines = n['q'].split('\n')
    w = max(tw(s, SZ_Q, 800) for s in lines)
    if n['ans']:
        w = max(w, tw(n['ans'], SZ_A, 800))
    h = len(lines)*33 + (26 if n['ans'] else 0) + 16
    return w + 2*PAD, h


# 葉（カード）を上から順に並べ、質問の箱は子のまん中の高さに置く
LEAVES, NODES = [], []


def _walk(n, depth, parent):
    n['depth'], n['parent'] = depth, parent
    if n['kind'] == 'l':
        n['i'] = len(LEAVES)
        LEAVES.append(n)
        return
    NODES.append(n)
    for c in n['kids']:
        _walk(c, depth + 1, n)


_walk(CFG['tree'], 0, None)
N = len(LEAVES)
PITCH = (Y_LAST - Y_FIRST) / (N - 1)
for _n in LEAVES:
    _n['y'] = Y_FIRST + _n['i']*PITCH


def _y(n):
    if n['kind'] == 'l':
        return n['y']
    ys = [_y(c) for c in n['kids']]
    n['y'] = (ys[0] + ys[-1]) / 2
    return n['y']


_y(CFG['tree'])
_max_d = max(n['depth'] for n in NODES)
COL_W = [max(node_size(n)[0] for n in NODES if n['depth'] == d) for d in range(_max_d + 1)]
COL_X = [X0 + sum(COL_W[:d]) + d*GAP_X for d in range(_max_d + 1)]
for _n in NODES:
    _n['w'], _n['h'] = node_size(_n)
    _n['x'] = COL_X[_n['depth']]
    _n['bar'] = _n['x'] + _n['w'] + 14
for _n in LEAVES:
    _n['x'] = _n['parent']['bar'] + 16
    _n['w'] = X_END - _n['x']
SLOT = DUR / N


def path_to(leaf):
    out = [leaf]
    while out[-1]['parent'] is not None:
        out.append(out[-1]['parent'])
    return out[::-1]


def edge(p, c):
    """親の箱 p → 子 c の線（直角）"""
    return [(p['x'] + p['w'], p['y']), (p['bar'], p['y']), (p['bar'], c['y']), (c['x'], c['y'])]


# --- 波形カード ----------------------------------------------------------------------------
_EXT = {}


def extent(key):
    if key not in _EXT:
        Lp = RHYTHMS[key]['L']
        v = rhythm_wave(key, np.arange(0, 2*Lp, 0.002))
        _EXT[key] = (float(v.max()), float(-v.min()))
    return _EXT[key]


def wave_geom(c):
    x0, x1 = c['x'] + 12, c['x'] + c['w'] - 12
    top, bot = c['y'] - CARD_H/2 + 37, c['y'] + CARD_H/2 - 6
    up, dn = extent(c['key'])
    s = min(30.0, (bot - top)*0.94/(up + dn))          # 1mV の高さ（px）。カードの中に収まる大きさ
    base = (top + bot)/2 + (up - dn)*s/2
    return x0, x1, base, s


ANS_MIN = 18 if MAP == 3 else 15   # ③は答えの字を 18px より小さくしない（①②は前のまま）


def fit_line(ans, name, wmax):
    """答え（小）と名前を1行に。入らなければ、まず答えの字を小さく（ANS_MIN まで）、それでも入らなければ名前を小さく"""
    sa, sn = 21, 26
    while True:
        wa, wn = tw(ans, sa, 700), tw(name, sn, 900)
        if wa + 12 + wn <= wmax or sn <= 17:
            return sa, sn, wa
        if sa > ANS_MIN:
            sa -= 1
        else:
            sn -= 1


def draw_card(im, c, t, glow):
    x, y0, w, h = int(c['x']), int(c['y'] - CARD_H/2), int(round(c['w'])), CARD_H
    lay = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
    if glow > 0:
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=14, outline=c['col'] + (int(210*glow),), width=8)
        lay = lay.filter(ImageFilter.GaussianBlur(8))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=14, fill=CARD_FILL + (232,),
                        outline=mix(NODE_EDGE, c['col'], max(glow, 0.35)) + (255,), width=2 + int(round(glow)))
    im.alpha_composite(lay, (x - 20, y0 - 20))
    sa, sn, wa = fit_line(c['ans'], c['name'], w - 26)
    put(im, c['ans'], sa, 700, mix(DIM_ANS, YEL, glow), x=x + 13, cy=y0 + 21)
    put(im, c['name'], sn, 900, c['col'], x=x + 13 + wa + 12, cy=y0 + 20)
    x0, x1, base, s = wave_geom(c)
    xs = np.arange(x0, x1, 0.5)
    v = rhythm_wave(c['key'], t - (x1 - xs)/SPEED)
    ys = base - v*s
    edge_f = np.clip(np.minimum(xs - x0, x1 - xs)/20, 0, 1)
    ys = base + (ys - base)*edge_f
    pts = [(px - x, py - y0) for px, py in zip(xs, ys)]
    col = mix(mix(c['col'], WHITE, 0.15), (60, 70, 70), 0.18*(1 - glow))
    im.alpha_composite(glow_line((w, h), [pts], col, 2.6 + 0.8*glow, 0.9 + 0.1*glow, blur=(3, 7)), (x, y0))


def draw_node(im, n, on):
    x, y0, w, h = n['x'], n['y'] - n['h']/2, n['w'], n['h']
    lay = Image.new('RGBA', (int(w) + 40, int(h) + 40), (0, 0, 0, 0))
    if on > 0:
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=12, outline=YEL + (int(170*on),), width=7)
        lay = lay.filter(ImageFilter.GaussianBlur(7))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=12, fill=NODE_FILL + (245,),
                        outline=mix(NODE_EDGE, YEL, on) + (255,), width=2)
    im.alpha_composite(lay, (int(x) - 20, int(y0) - 20))
    yy = y0 + 8
    if n['ans']:
        put(im, n['ans'], SZ_A, 800, mix(DIM_ANS, YEL, on), x=x + PAD, cy=yy + 12)
        yy += 26
    for s in n['q'].split('\n'):
        put(im, s, SZ_Q, 800, C_Q, x=x + PAD, cy=yy + 16)
        yy += 33


# --- 1コマ -------------------------------------------------------------------------------
_GRID = None
_STATIC = {}


def lines_layer():
    """灰色の線（全部）。毎コマ同じなので1回だけ描く"""
    if 'lines' not in _STATIC:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for n in NODES:
            ys = [c['y'] for c in n['kids']] + [n['y']]
            d.line([(n['x'] + n['w'], n['y']), (n['bar'], n['y'])], fill=C_LINE + (255,), width=3)
            d.line([(n['bar'], min(ys)), (n['bar'], max(ys))], fill=C_LINE + (255,), width=3)
            for c in n['kids']:
                d.line([(n['bar'], c['y']), (c['x'], c['y'])], fill=C_LINE + (255,), width=3)
        _STATIC['lines'] = lay
    return _STATIC['lines']


def active_at(t):
    k = int((t % DUR) // SLOT)
    return k, (t % DUR) - k*SLOT


SUB_CY, SUB_SZ, TITLE_SZ = 296, 32, 60


def _ink_rows(draw):
    """draw(im) で描いた字の、上端と下端の y（透明な画像に描いて測る）"""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw(im)
    rows = np.where(np.asarray(im.getchannel('A')).max(axis=1) > 40)[0]
    return int(rows[0]), int(rows[-1])


def _title_parts():
    return [(CFG['title'][0], TITLE_SZ, YEL), (CFG['title'][1], TITLE_SZ, WHITE)]


def _draw_title_at(im, cy):
    parts = _title_parts()
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    xx = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, _) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=xx, cy=cy)
        xx += a_.size[0] - 8


def _title_cy():
    """「モニター心電図」の下 〜 タイトル、タイトル 〜 1枚目のカードの上、の間が同じになる高さ"""
    _, sub_bot = _ink_rows(lambda im: put(im, 'モニター心電図', SUB_SZ, 700, WHITE, cx=540, cy=SUB_CY))
    card_top = LEAVES[0]['y'] - CARD_H/2
    t0, t1 = _ink_rows(lambda im: _draw_title_at(im, 400))
    h = t1 - t0
    top = (sub_bot + card_top - h) / 2                 # 上の間 = 下の間
    return 400 + (top - t0)


TITLE_CY = None


def draw_title(im):
    global TITLE_CY
    if TITLE_CY is None:
        TITLE_CY = _title_cy()
    put(im, 'モニター心電図', SUB_SZ, 700, (118, 226, 150), cx=540, cy=SUB_CY)
    _draw_title_at(im, TITLE_CY)


def frame(t, wm=True, highlight=True):
    global _GRID
    if _GRID is None:
        _GRID = b.grid()
    im = _GRID.copy()
    draw_title(im)
    im.alpha_composite(lines_layer())
    # 光る道すじ（前の道から0.25秒で移る）
    glow_leaf = [0.0]*N
    on_node = {id(n): 0.0 for n in NODES}
    if highlight:
        k, u = active_at(t)
        a_new = ramp(u, 0.0, 0.25)
        for leaf, a in ((LEAVES[(k - 1) % N], 1 - a_new), (LEAVES[k], a_new)):
            if a <= 0:
                continue
            p = path_to(leaf)
            runs = [edge(p[j], p[j + 1]) for j in range(len(p) - 1)]
            im.alpha_composite(glow_line((W, H), runs, YEL, 3.6, a, blur=(4, 10)))
            for n in p[:-1]:
                on_node[id(n)] = max(on_node[id(n)], a)
            glow_leaf[leaf['i']] = max(glow_leaf[leaf['i']], a)
    for n in NODES:
        draw_node(im, n, on_node[id(n)])
    for c in LEAVES:
        draw_card(im, c, t, glow_leaf[c['i']])
    put(im, CFG['notes'][0], 20, 400, (150, 160, 162), x=135, cy=1566, max_w=470)
    put(im, CFG['notes'][1], 20, 400, (150, 160, 162), x=135, cy=1592, max_w=470)
    if wm:
        put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


def thumbnail():
    return frame(0.6, wm=False, highlight=False)


# --- 書き出し -----------------------------------------------------------------------------
def render_chunk(args):
    i0, i1, fps, path, crf, preset = args
    cmd = [b.ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset,
           '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def sounds(path, sr=44100):
    """光っているカードの波形の R が、カードのまん中を通るときに「ピッ」。VFは低いアラーム音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)

    def tone(ts, f, amp=0.12, dur=0.08, dec=0.045):
        Ln = int(dur*sr); tt = np.arange(Ln)/sr
        s = amp*np.minimum(1, tt/0.004)*np.exp(-tt/dec)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr) % n
        seg = s[:min(Ln, n - j)]
        a[j:j+len(seg)] += seg
        if len(seg) < Ln:
            a[:Ln - len(seg)] += s[len(seg):]

    for k, c in enumerate(LEAVES):
        t0, t1 = k*SLOT, (k + 1)*SLOT
        x0, x1, _, _ = wave_geom(c)
        lag = (x1 - (x0 + x1)/2) / SPEED
        if c['key'] == 'vf':
            for ts in np.arange(t0 + 0.2, t1 - 0.1, 0.5):
                tone(ts, 720.0, 0.10, 0.25, 0.12)
            continue
        for r in r_times(c['key'], t0 - lag - 0.1, t1 - lag + 0.1):
            ts = r + lag
            if t0 + 0.05 <= ts < t1 - 0.05:
                tone(ts, 960.0)
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=None)
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    ap.add_argument('--hq', action='store_true')
    ap.add_argument('--map', type=int, default=MAP)
    o = ap.parse_args()
    if o.map != MAP:
        env = dict(os.environ, MAP_NO=str(o.map))
        raise SystemExit(subprocess.call([sys.executable] + sys.argv, env=env))
    out_dir = os.path.join(HERE, 'out')
    os.makedirs(out_dir, exist_ok=True)
    if o.thumb:
        p = os.path.join(out_dir, f'thumb_map{MAP}_v3.png')
        thumbnail().save(p); print(p); return
    if o.still is not None:
        for s in o.still:
            p = os.path.join(out_dir, f'still_map{MAP}_v3_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    out = o.out or os.path.join(out_dir, f'map{MAP}_v3{"_hq" if o.hq else ""}.mp4')
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(out_dir, f'parts_map{MAP}_v3')
    os.makedirs(tmp, exist_ok=True)
    jobs = [(i, min(total, i+step), o.fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset)
            for j, i in enumerate(range(0, total, step))]
    with Pool(o.jobs) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    wav = os.path.join(tmp, 'sounds.wav')
    sounds(wav)
    subprocess.run([b.ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    '-movflags', '+faststart', out], check=True)
    print(out)


if __name__ == '__main__':
    main()
