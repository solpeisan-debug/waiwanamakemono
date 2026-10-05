"""モニター心電図 見分けマップ v2（1枚で動く保存版。2枚組）。

v1（質問の木を光る点がたどる）はトライアルリールで再生されなかったので、作り直した。
- 1コマ目から、すべての波形を「小さなモニター（カード）」で出して、ずっと流す（冒頭の待ち時間をなくす）
- 質問は、カードのまとまりの見出し（答え ▸ 次の質問）と、カードの上の小さな字（答え）で表す
- カードが1枚ずつ順に光る（その波形の音が鳴る）。24秒で全部を1周して、そのまま冒頭につながる
- 波形はすべて周期が24秒の約数になるように作ってあるので、最後のコマの次が最初のコマとぴったり同じになる

ナレーションなし（2026-10-04 決定）。マップの中身は v1 と同じ（専門医レビュー 2026-10-04 を反映済み。review_log.md）。

使い方:
    python3 make_map_v2.py --map 1              # 書き出し（out/map1_v2.mp4）
    python3 make_map_v2.py --map 2 --still 0 5  # 1コマだけ
    python3 make_map_v2.py --map 1 --thumb      # サムネイル（透かしなし）
    python3 make_map_v2.py --map 1 --hq         # 高画質（out/map1_v2_hq.mp4）
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

import make_map as b
from make_map import (W, H, WHITE, YEL, CARD_FILL, CARD_EDGE, C_RED, C_ORANGE, C_YEL, C_BLUE, C_GREEN, C_Q,
                      WATERMARK, put, text_img, glow_line, beats_wave, band_noise, flutter_waves, mix, ramp)

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 24.0                     # 1周（すべての波形の周期の倍数）
SPEED = 100.0                  # 波形の流れる速さ（px/秒）。小さなモニターなので、実際より詰めて見せる
GREEN_SAVE = (130, 232, 172)
DIM_ANS = (214, 186, 110)


# --- 波形（周期 L は 24 の約数） -----------------------------------------------------------
_AF_RR = [0.62, 0.95, 0.48, 0.80, 1.10, 0.55, 0.74, 0.76]              # 合計 6.0
_AF_T = np.cumsum([0] + _AF_RR[:-1]).tolist()
_SA_RR = [r*8.0/7.6 for r in [0.72, 0.68, 0.70, 0.78, 0.90, 1.00, 1.02, 0.95, 0.85]]   # 合計 8.0
_SA_T = np.cumsum([0] + _SA_RR[:-1]).tolist()
RHYTHMS = {
    # マップ①
    'pace':   dict(ev=[(k*1.0, 'S') for k in range(4)], L=4.0),                      # 60/分
    'junc':   dict(ev=[(0.0, 'Q'), (1.5, 'Q')], L=3.0),                              # 40/分、P波なし、細い
    'vesc':   dict(ev=[(0.0, 'W'), (2.0, 'W')], L=4.0),                              # 30/分、幅広い
    'sbrady': dict(ev=[(k*1.2, 'N') for k in range(4)], L=4.8),                      # 50/分
    'av21':   dict(ev=[(0.0, 'N'), (0.59, 'P')], L=1.5),                             # P 80/分、QRS 40/分
    'chb':    dict(ev=[(k*0.6, 'P') for k in range(10)] + [(0.25 + k*1.5, 'Q') for k in range(4)], L=6.0),
    'nsr':    dict(ev=[(k*0.8, 'N') for k in range(5)], L=4.0),                      # 75/分
    'av1':    dict(ev=[(k*0.8, 'N', 0.30) for k in range(5)], L=4.0),                # PR 0.30秒
    'stach':  dict(ev=[(k*0.5, 'N') for k in range(8)], L=4.0),                      # 120/分
    'flut':   dict(ev=[(k*0.4, 'Q') for k in range(10)], L=4.0, flut=True),          # F波 300/分、2:1
    'psvt':   dict(ev=[(k*0.375, 'Q') for k in range(8)], L=3.0),                    # 160/分、P波見えない
    'vt':     dict(ev=[(k*0.32, 'V') for k in range(15)], L=4.8),                    # 188/分
    # マップ②
    'vf':     dict(ev=[], L=4.0, vf=True),
    'pasys':  dict(ev=[(k*0.8, 'P') for k in range(5)], L=4.0),
    'asys':   dict(ev=[], L=4.0, asys=True),
    'af':     dict(ev=[(t, 'Q') for t in _AF_T], L=6.0, f=True),
    'afbbb':  dict(ev=[(t, 'V') for t in _AF_T], L=6.0, f=True),                    # 不規則で幅の広いQRS
    'pac':    dict(ev=[(0.0, 'N'), (0.8, 'N'), (1.3, 'A'), (2.2, 'N')], L=3.0),
    'pjc':    dict(ev=[(0.0, 'N'), (0.8, 'N'), (1.3, 'Q'), (2.2, 'N')], L=3.0),
    'pvc':    dict(ev=[(0.0, 'N'), (0.8, 'N'), (1.28, 'V'), (2.4, 'N'), (3.2, 'N')], L=4.0),   # 休みは2拍ぶん
    'sarrest': dict(ev=[(k*0.8, 'N') for k in range(5)], L=6.0),                     # 2.8秒の休み
    'wk':     dict(ev=[(0.18, 'N', 0.18), (1.28, 'N', 0.28), (2.33, 'N', 0.33), (3.0, 'P')], L=4.0),
    'm2':     dict(ev=[(0.16, 'N'), (1.16, 'N'), (2.16, 'N'), (3.0, 'P')], L=4.0),
    'sarr':   dict(ev=[(t, 'N') for t in _SA_T], L=8.0),
}
QRS_KINDS = ('N', 'Q', 'V', 'W', 'S', 'A')
for _k, _r in RHYTHMS.items():
    assert abs(DUR/_r['L'] - round(DUR/_r['L'])) < 1e-9, _k


def rhythm_wave(key, t):
    R = RHYTHMS[key]
    v = beats_wave(t, b.periodic(R['ev'], R['L'], t[0], t[-1]))
    if R.get('f'):
        v += band_noise(t, R['L'], 5.0, 8.0, 0.035, 5)
    if R.get('vf'):
        v += band_noise(t, R['L'], 3.0, 9.0, 0.30, 9)
    if R.get('asys'):
        v += band_noise(t, R['L'], 0.3, 1.5, 0.015, 11)
    if R.get('flut'):
        v += flutter_waves(t, R['L'])
    return v


def r_times(key, t0, t1):
    R = RHYTHMS[key]
    return [e[0] for e in b.periodic(R['ev'], R['L'], t0, t1) if e[1] in QRS_KINDS and t0 <= e[0] < t1]


# --- マップの中身 -------------------------------------------------------------------------
def C(name, chip, col, key, span=1.0):
    return dict(name=name, chip=chip, col=col, key=key, span=span)


A, Qn = 'a', 'q'                     # 見出しの部品：答え（黄）／質問（白）
MAPS = {
    1: dict(
        title=('見分けマップ①', ' 規則的な波形'),
        sections=[
            dict(head=[('ペースメーカーのスパイク', Qn), (' あり', A)],
                 rows=[[C('ペースメーカー調律', 'スパイクのあとに幅の広いQRS', C_BLUE, 'pace')]]),
            dict(head=[('スパイクなし', A), (' → 心拍数 ', Qn), ('60未満', A), (' → P波は？', Qn)],
                 rows=[[C('接合部補充調律', 'P波なし・QRS狭い', C_BLUE, 'junc'),
                        C('心室補充調律', 'P波なし・QRS広い', C_RED, 'vesc'),
                        C('洞徐脈', 'P波あり・毎回QRS', C_BLUE, 'sbrady')],
                       [C('2:1・高度房室ブロック', 'QRSが抜ける・PとQRSは一定', C_RED, 'av21'),
                        C('完全房室ブロック', 'PとQRSが別々', C_RED, 'chb')]]),
            dict(head=[('60〜100', A), (' → PRは？', Qn)],
                 rows=[[C('洞調律', '0.2秒以下', C_GREEN, 'nsr'),
                        C('1度房室ブロック', '0.2秒より長い', C_YEL, 'av1')]]),
            dict(head=[('100以上', A), (' → QRSの幅・P波は？', Qn)],
                 rows=[[C('洞頻脈', '狭い・P波ふつう', C_GREEN, 'stach'),
                        C('心房粗動', '狭い・のこぎり状', C_ORANGE, 'flut')],
                       [C('PSVT', '狭い・P波見えない', C_ORANGE, 'psvt'),
                        C('心室頻拍（VT）', '広い（迷ったらVT）', C_RED, 'vt')]]),
        ],
        notes=['※モニター（II誘導）で見る入口の一例。例外あり', '※幅の広い速い頻拍は、迷ったらVT（LITFL）'],
    ),
    2: dict(
        title=('見分けマップ②', ' 不規則・QRSなし'),
        sections=[
            dict(head=[('QRSなし', A), (' → 何が見える？', Qn)],
                 rows=[[C('心室細動（VF）', 'バラバラな揺れ', C_RED, 'vf'),
                        C('P波だけの心静止', 'P波だけ', C_RED, 'pasys'),
                        C('心静止', 'まっすぐ（電極も確認）', C_RED, 'asys')]]),
            dict(head=[('QRSあり・全部バラバラ', A), (' → QRSの幅は？', Qn)],
                 rows=[[C('心房細動', 'QRS狭い', C_ORANGE, 'af', 0.8),
                        C('心房細動＋脚ブロック・多形性VT', 'QRS広い', C_RED, 'afbbb', 1.2)]]),
            dict(head=[('早い1拍', A), (' → 早い拍は？', Qn)],
                 rows=[[C('心房期外収縮', "PAC：狭い・前にP'", C_BLUE, 'pac'),
                        C('接合部期外収縮', 'PJC：狭い・Pなし', C_BLUE, 'pjc'),
                        C('心室期外収縮', 'PVC：広い', C_YEL, 'pvc')]]),
            dict(head=[('ときどき抜ける', A), (' → 抜けるのは？', Qn)],
                 rows=[[C('洞停止・洞房ブロック', 'P波ごと', C_BLUE, 'sarrest'),
                        C('ウェンケバッハ', 'QRSだけ・PRが伸びる', C_YEL, 'wk'),
                        C('モビッツII型', 'QRSだけ・PR一定', C_RED, 'm2')]]),
            dict(head=[('呼吸でゆれる', A)],
                 rows=[[C('洞性不整脈', 'R-Rが呼吸に合わせてゆっくり変わる', C_GREEN, 'sarr')]]),
        ],
        notes=['※波形があっても、脈がなければPEA。まず患者さん', '※モニター（II誘導）で見る入口の一例。例外あり'],
    ),
}
MAP = int(os.environ.get('MAP_NO', '1'))
CFG = MAPS[MAP]

# --- 配置 ---------------------------------------------------------------------------------
X0, X1 = 130, 950
Y_TOP, Y_BOT = 446, 1536
HEAD_H, ROW_GAP, COL_GAP, SEC_GAP = 42, 12, 12, 10
SECS = CFG['sections']
_n_rows = sum(len(s['rows']) for s in SECS)
CARD_H = min(176, (Y_BOT - Y_TOP - len(SECS)*HEAD_H - _n_rows*ROW_GAP - (len(SECS) - 1)*SEC_GAP) / _n_rows)
CARDS, HEADS = [], []
_y = Y_TOP
for _si, _s in enumerate(SECS):
    HEADS.append(dict(parts=_s['head'], y=_y + 18, sec=_si))
    _y += HEAD_H
    for _row in _s['rows']:
        tot = sum(c['span'] for c in _row)
        avail = X1 - X0 - COL_GAP*(len(_row) - 1)
        _x = X0
        for c in _row:
            w = avail*c['span']/tot
            CARDS.append(dict(c, x=_x, y=_y, w=w, h=CARD_H, sec=_si))
            _x += w + COL_GAP
        _y += CARD_H + ROW_GAP
    _y += SEC_GAP
N = len(CARDS)
SLOT = DUR / N                 # 1枚が光る時間


def wave_box(c):
    """カードの中の波形の場所（x0, x1, 上, 下）"""
    return (c['x'] + 12, c['x'] + c['w'] - 12, c['y'] + 70, c['y'] + c['h'] - 8)


_EXT = {}


def extent(key):
    if key not in _EXT:
        L = RHYTHMS[key]['L']
        v = rhythm_wave(key, np.arange(0, 2*L, 0.002))
        _EXT[key] = (float(v.max()), float(-v.min()))
    return _EXT[key]


_SCALE = None


def wave_scale(c=None):
    """1mV の高さ（px）。マップの中で共通（いちばん上下に大きい波形が、波形の場所に収まる大きさ）"""
    global _SCALE
    if _SCALE is None:
        _SCALE = 46.0
        for cc in CARDS:
            _, _, top, bot = wave_box(cc)
            up, dn = extent(cc['key'])
            _SCALE = min(_SCALE, (bot - top)*0.94/(up + dn))
    return _SCALE


def base_y(c):
    """上端〜下端のまん中が、波形の場所のまん中に来る基線"""
    _, _, top, bot = wave_box(c)
    up, dn = extent(c['key'])
    s = wave_scale(c)
    return (top + bot)/2 + (up - dn)*s/2


# --- 描画 ---------------------------------------------------------------------------------
def active_at(t):
    k = int((t % DUR) // SLOT)
    u = (t % DUR) - k*SLOT
    return k, u


def draw_head(im, hd, on):
    x = X0 + 4
    for s, kind in hd['parts']:
        if kind == A:
            col = YEL if on else DIM_ANS
            put(im, s, 26, 800, col, x=x, cy=hd['y'])
            w = text_img(s, 26, 800, col)[0].size[0] - 8
        else:
            put(im, s, 26, 700, C_Q, x=x, cy=hd['y'])
            w = text_img(s, 26, 700, C_Q)[0].size[0] - 8
        x += w


def draw_card(im, c, t, glow):
    x, y, w, h = int(c['x']), int(c['y']), int(round(c['w'])), int(round(c['h']))
    lay = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if glow > 0:
        d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=16, outline=c['col'] + (int(200*glow),), width=8)
        lay = lay.filter(ImageFilter.GaussianBlur(9))
        d = ImageDraw.Draw(lay)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=16, fill=CARD_FILL + (228,),
                        outline=mix(CARD_EDGE, c['col'], glow) + (255,), width=2 + int(round(glow)))
    im.alpha_composite(lay, (x - 20, y - 20))
    # 文字：答え（小）→ 名前
    put(im, c['chip'], 20, 700, mix(DIM_ANS, YEL, glow), x=x + 16, cy=y + 20, max_w=w - 30)
    put(im, c['name'], 28, 900, c['col'], x=x + 16, cy=y + 48, max_w=w - 30)
    # 波形（右から流れてくる。いちばん右が「いま」）
    x0, x1, top, bot = wave_box(c)
    xs = np.arange(x0, x1, 0.5)
    tt = t - (x1 - xs) / SPEED
    v = rhythm_wave(c['key'], tt)
    ys = base_y(c) - v*wave_scale(c)
    edge = np.clip(np.minimum(xs - x0, x1 - xs)/24, 0, 1)
    ys = base_y(c) + (ys - base_y(c))*edge
    pts = [(px - x, py - y) for px, py in zip(xs, ys)]
    col = mix(mix(c['col'], WHITE, 0.15), (60, 70, 70), 0.2*(1 - glow))
    gl = glow_line((w, h), [pts], col, 2.8 + 0.8*glow, 0.88 + 0.12*glow, blur=(3, 7))
    im.alpha_composite(gl, (x, y))


_GRID = None


def frame(t, wm=True, highlight=True):
    global _GRID
    if _GRID is None:
        _GRID = b.grid()
    im = _GRID.copy()
    put(im, 'モニター心電図', 30, 700, (118, 226, 150), cx=540, cy=298)
    parts = [(CFG['title'][0], 52, YEL), (CFG['title'][1], 52, WHITE)]
    ims = [text_img(s_, sz, 900, c_) for s_, sz, c_ in parts]
    xx = 540 - (sum(a_.size[0] - 8 for a_, _ in ims))/2
    for (s_, sz, c_), (a_, _) in zip(parts, ims):
        put(im, s_, sz, 900, c_, x=xx, cy=350)
        xx += a_.size[0] - 8
    put(im, '上から順に答えるだけ。保存して、迷ったら見返してね', 24, 700, GREEN_SAVE, cx=540, cy=402)
    k, u = active_at(t)
    gl = [0.0]*N
    if highlight:
        gl[k] = ramp(u, 0.0, 0.25)                       # 前のカードから0.25秒で光が移る（1周してもつながる）
        gl[(k - 1) % N] = max(gl[(k - 1) % N], 1 - ramp(u, 0.0, 0.25))
    sec_on = CARDS[k]['sec'] if highlight else -1
    for hd in HEADS:
        draw_head(im, hd, hd['sec'] == sec_on or not highlight)
    for i, c in enumerate(CARDS):
        draw_card(im, c, t, gl[i])
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
        L = int(dur*sr); tt = np.arange(L)/sr
        s = amp*np.minimum(1, tt/0.004)*np.exp(-tt/dec)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr) % n
        seg = s[:min(L, n - j)]
        a[j:j+len(seg)] += seg
        if len(seg) < L:                                   # 1周の終わりをまたぐ音は頭へ
            a[:L - len(seg)] += s[len(seg):]

    for k, c in enumerate(CARDS):
        t0, t1 = k*SLOT, (k + 1)*SLOT
        x0, x1, _, _ = wave_box(c)
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
        p = os.path.join(out_dir, f'thumb_map{MAP}_v2.png')
        thumbnail().save(p); print(p); return
    if o.still is not None:
        for s in o.still:
            p = os.path.join(out_dir, f'still_map{MAP}_v2_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    out = o.out or os.path.join(out_dir, f'map{MAP}_v2{"_hq" if o.hq else ""}.mp4')
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(out_dir, f'parts_map{MAP}_v2')
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
