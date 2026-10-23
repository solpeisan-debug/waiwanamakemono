"""第29弾 心筋梗塞の場所（ST上昇の誘導 → 梗塞の場所 → 責任冠動脈）6パターン ― 試作（静止画まで）

配置（1080×1920・60fps。文字は左右130px・上300px・下1600px の内側）：
- 上（y 300〜360）：見出し「心筋梗塞の場所 6パターン」（冒頭0〜2.4秒は問いかけ）
- 上部（y 372〜1100）：実際の12誘導の並び（3段×4列：I aVR V1 V4 ／ II aVL V2 V5 ／ III aVF V3 V6）。
  各誘導は1拍だけ（25mm/秒・10mm/mV、方眼は1mm＝14px の正方形＝紙と同じ。拡大なし）。
  ST上昇の誘導は ST の部分を赤く塗り、鏡像の ST低下は青く塗る。誘導名も同じ色。
  4段め（追加の誘導）は、右室（V4R）・後壁（V7〜V9）のときだけ出る。ふだんは色の見かた（凡例）を置く
- 中（y 1100〜1230）：パターンの名前と責任血管、看護の1行「→ 〜」
- 下（y 1240〜1600）：心臓の輪切り（左室の短軸＋右室の三日月）。中隔・前壁・側壁・後壁・下壁・右室。
  まわりに「どの誘導がその壁を見ているか」の誘導名。梗塞の壁を赤く塗り、責任血管（LAD・LCx・RCA）の線を光らせる
- 透かし：中央・64px・太さ800・白16%。4段め（追加の誘導）の基線の下（どの文字とも重ならない高さ）。全コマ同じ位置

形の変わり方（シームレス）：12誘導の枠と輪切りの図は消さない。ST・T・R の高さ、壁の塗り、誘導名の色を
数値で補間して、その場で形を変える。別のパターンへは、いったん灰色の「正常」にもどして（▶ 次の例）から次へ。
④下壁 → ⑤右室 だけは直接（右室梗塞は下壁梗塞に加わって起こる。LITFL：isolated RV infarction is extremely uncommon）。

使い方:
    python3 make_reel29.py --check          # 検算（タイムライン・字の幅・安全域・重なり・波形の高さ）
    python3 make_reel29.py --still 1.2 40   # 1コマずつ（out/still_XXX.X.png）
    python3 make_reel29.py --sheet          # 確認用の5枚と、5枚を並べた一覧（out/）
"""
import argparse
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import intro3d as I3

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 130, W - 130, 300, 1600
IG_ZONE = (900, 1100, W, 1600)            # 右下：インスタのボタン（大事な文字を置かない）

# --- 色（第26弾にそろえる） ---------------------------------------------------------
BG = (2, 7, 6)
G_MINOR = (10, 21, 17)
G_MAJOR = (27, 46, 38)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
LABEL_GREY = (176, 188, 186)            # ふだんの誘導名
TOKEN_DIM = (104, 118, 116)             # 輪切りのまわりの誘導名（関係ないとき）
DIM = (70, 82, 82)
PURPLE = (178, 150, 240)
GREEN = (130, 232, 172)
YELLOW = (255, 214, 64)
WAVE_GREEN = (40, 214, 128)
NEUTRAL_COL = (118, 126, 128)           # 「つなぎ」の正常（灰色）
RED = (255, 84, 84)                     # ST上昇
BLUE = (96, 156, 255)                   # 鏡像の ST低下
C_LAD = (255, 190, 70)                  # 左前下行枝
C_LCX = (196, 150, 255)                 # 回旋枝
C_RCA = (64, 214, 200)                  # 右冠動脈
VES_COL = {'LAD': C_LAD, 'LCX': C_LCX, 'RCA': C_RCA}
VES_NAME = {'LAD': 'LAD', 'LCX': 'LCx', 'RCA': 'RCA'}

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 紙の目盛り（第24弾〜と同じ：1mm＝14px、25mm/秒、10mm/mV） ------------------------
PXMM = 14.0
PXS = 25 * PXMM                          # 実際の1秒 = 350px
PXMV = 10 * PXMM                         # 1mV = 140px

# --- 12誘導の枠 ---------------------------------------------------------------------
LAYOUT = [['I', 'aVR', 'V1', 'V4'],
          ['II', 'aVL', 'V2', 'V5'],
          ['III', 'aVF', 'V3', 'V6']]
EXTRA = {'V4R': 0, 'V7': 1, 'V8': 2, 'V9': 3}   # 4段め（追加の誘導）の列
PANEL_X0, COL_W = 80, 230                # 4列 × 230px（＝0.657秒。1拍がちょうど入る）。x80〜1000＝左右の余白 80 でそろえる（説明の枠も同じ）
ROW_TOP0, ROW_PITCH, ROW_UP = 493, 140, 100      # 段の上端・段の間隔（10mm）・段の上端→基線（確認版④：4段を 505〜1090 に）
BASES = [ROW_TOP0 + ROW_UP + k*ROW_PITCH for k in range(4)]   # 基線 593, 733, 873, 1013（4段め＝追加の誘導。いつも出す）
PANEL_Y1 = BASES[3] + 70
TAU0 = -0.24                             # 枠の左端の時刻（R頂点＝0）。R は枠の左から 84px
TAU1 = TAU0 + COL_W / PXS
WALL_LABEL_DX = 112                      # まとめ：枠の中の壁の名前（R波の右）


def col_x(c):
    return PANEL_X0 + c*COL_W


def lead_cell(name):
    """誘導の (列, 段)。"""
    for r, row in enumerate(LAYOUT):
        if name in row:
            return row.index(name), r
    return EXTRA[name], 3


ALL_LEADS = [n for row in LAYOUT for n in row] + list(EXTRA)

# --- 1拍の形（実際の時間・秒、mV） -------------------------------------------------
# 誘導ごとのふつうの形：P・q・R・S・T の高さ（mV）。モニターや教科書の典型にそろえた低めの値
# （12誘導を3段に並べて、上下の段の波形がぶつからない高さ。--check で確かめる）
NORMAL = {
    #        P      q      R      S      T
    'I':   (0.08, -0.04, 0.55, -0.08, 0.20),
    'II':  (0.12, -0.04, 0.75, -0.12, 0.25),
    'III': (0.04, -0.04, 0.40, -0.12, 0.10),
    'aVR': (-0.09, 0.00, 0.08, -0.50, -0.20),
    'aVL': (0.04, -0.04, 0.30, -0.15, 0.08),
    'aVF': (0.08, -0.04, 0.55, -0.12, 0.17),
    'V1':  (0.06, 0.00, 0.15, -0.52, 0.06),
    'V2':  (0.07, 0.00, 0.28, -0.50, 0.25),
    'V3':  (0.07, 0.00, 0.45, -0.45, 0.25),
    'V4':  (0.07, 0.00, 0.75, -0.30, 0.32),
    'V5':  (0.07, -0.05, 0.75, -0.15, 0.26),
    'V6':  (0.07, -0.05, 0.62, -0.08, 0.22),
    'V7':  (0.05, -0.04, 0.45, -0.08, 0.15),
    'V8':  (0.04, -0.04, 0.35, -0.10, 0.12),
    'V9':  (0.04, -0.04, 0.28, -0.10, 0.10),
    'V4R': (0.05, 0.00, 0.15, -0.35, 0.06),
}
AMP = 0.78                               # 確認版④：4段を 505〜1090 に入れるため、波形の振幅を 0.78倍（紙の目盛りはそのまま）
J_T = 0.045                              # J点（R頂点からの秒）
ST_FILL = (0.045, 0.255)                 # ST を塗る範囲（J点〜T波の立ち上がり）
ST_LINE = (0.035, 0.30)                  # 線の色を変える範囲


def _g(t, c, s):
    return np.exp(-0.5*((t - c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t - c)/s)**2)


def _ss(x):
    x = np.clip(x, 0, 1)
    return x*x*(3 - 2*x)


def st_plateau(tau):
    """ST の持ち上がり（または下がり）の形：J点で立ち上がり、T波のうしろでもどる。高さ 1。"""
    return _ss((tau - 0.028) / 0.030) * (1 - _ss((tau - 0.285) / 0.115))


def st_flat(tau):
    """水平な ST（後壁の V1〜V3）：S のすぐあとから平らにして、T の立ち上がりまで J点から 0.08秒ほど水平に。"""
    return _ss((tau - 0.040) / 0.035) * (1 - _ss((tau - 0.285) / 0.115))


def beat(lead, par, tau):
    """1拍（R頂点＝0）。par＝(st, dT, dR, dS, rw, flat)：ST のずれ・T・R・S の高さの足し分・R の幅の倍率・水平な ST（0〜1）。"""
    p, q, r, s, t = NORMAL[lead]
    st, dT, dR, dS, rw, fl = par
    v = p*_g(tau, -0.160, 0.022)
    v += q*_g(tau, -0.026, 0.008)
    v += (r + dR)*_ga(tau, 0.0, 0.011*rw, 0.012*rw)
    v += (s + dS)*_g(tau, 0.028 + 0.010*(rw - 1), 0.010*rw)
    v += (t + dT)*_ga(tau, 0.270 + 0.022*fl, 0.060 - 0.008*fl, 0.042)
    v += st*((1 - fl)*st_plateau(tau) + fl*st_flat(tau))
    return v*AMP


# --- パターン（LITFL で確かめた誘導。docs/reel29_spec.md の表） ------------------------
# leads：{誘導: (ST のずれ mV, T の足し分, R の足し分, S の足し分, R の幅の倍率)}。書かない誘導は正常
# seg：梗塞の壁（輪切りで赤く塗る）、ves：責任血管（1＝はっきり、0.6＝どちらか）
SEGS = ['ant', 'sep', 'lat', 'post', 'inf', 'rv']
SEG_NAME = {'ant': '前壁', 'sep': '中隔', 'lat': '側壁', 'post': '後壁', 'inf': '下壁', 'rv': '右室'}
SEG_VES = {'ant': 'LAD', 'sep': 'LAD', 'lat': 'LCX', 'post': 'LCX', 'inf': 'RCA', 'rv': 'RCA'}
LEAD_WALL = {'V1': 'sep', 'V2': 'sep', 'V3': 'ant', 'V4': 'ant', 'I': 'lat', 'aVL': 'lat', 'V5': 'lat', 'V6': 'lat',
             'II': 'inf', 'III': 'inf', 'aVF': 'inf', 'V7': 'post', 'V8': 'post', 'V9': 'post', 'V4R': 'rv'}

_INF = {'II': (0.20, 0.08, 0, 0, 1), 'III': (0.30, 0.10, 0, 0, 1), 'aVF': (0.25, 0.09, 0, 0, 1),
        'aVL': (-0.20, -0.14, 0, 0, 1), 'I': (-0.07, -0.03, 0, 0, 1)}
PATTERNS = [
    dict(no='①', key='asep', name='前壁中隔', ves='LAD', vtxt='LAD（左前下行枝）',
         nurse='→ VFに注意。除細動器を近くに', sub=['V1〜V4 が上がる'],
         leads={'V1': (0.18, 0.05, 0, 0, 1), 'V2': (0.28, 0.06, 0, 0, 1),
                'V3': (0.28, 0.06, 0, 0, 1), 'V4': (0.22, 0.08, 0, 0, 1)},
         seg={'ant': 1, 'sep': 1}, vesw={'LAD': 1}),
    dict(no='②', key='ext', name='広範囲前壁', ves='LAD', vtxt='LADの根もと',
         nurse='→ 心不全・ショックに注意', sub=['V1〜V6・I・aVL まで上がる'],
         leads={'V1': (0.20, 0.05, 0, 0, 1), 'V2': (0.30, 0.06, 0, 0, 1), 'V3': (0.30, 0.06, 0, 0, 1),
                'V4': (0.28, 0.08, 0, 0, 1), 'V5': (0.24, 0.10, 0, 0, 1), 'V6': (0.18, 0.06, 0, 0, 1),
                'I': (0.15, 0.05, 0, 0, 1), 'aVL': (0.15, 0.06, 0, 0, 1),
                'III': (-0.10, -0.04, 0, 0, 1), 'aVF': (-0.07, -0.03, 0, 0, 1)},
         seg={'ant': 1, 'sep': 1, 'lat': 1}, vesw={'LAD': 1}),
    dict(no='③', key='lat', name='側壁', ves='LCX', vtxt='LCx（回旋枝）など',
         nurse='→ III・aVFの低下を見たら、I・aVLも確かめる', sub=['I・aVL・V5・V6 が上がる'],
         leads={'I': (0.16, 0.05, 0, 0, 1), 'aVL': (0.18, 0.06, 0, 0, 1),
                'V5': (0.20, 0.08, 0, 0, 1), 'V6': (0.18, 0.06, 0, 0, 1),
                'III': (-0.14, -0.06, 0, 0, 1), 'aVF': (-0.09, -0.04, 0, 0, 1)},
         seg={'lat': 1}, vesw={'LCX': 1}),
    dict(no='④', key='inf', name='下壁', ves='RCA', vtxt='RCA（右冠動脈）が多い',
         nurse='→ 徐脈・房室ブロックに注意。V4Rもとる', sub=['II・III・aVF が上がる／aVL が下がる'],
         leads=dict(_INF),
         seg={'inf': 1}, vesw={'RCA': 1}),
    dict(no='⑤', key='rv', name='右室', ves='RCA', vtxt='RCAの根もと',
         nurse='→ 血圧低下に注意', sub=['下壁に加えて、右胸の V4R も上がる'],
         leads=dict(_INF, **{'V1': (0.12, 0.04, 0, 0, 1), 'V4R': (0.15, 0.05, 0, 0, 1)}),
         seg={'inf': 1, 'rv': 1}, vesw={'RCA': 1}, x_rv=1),
    dict(no='⑥', key='post', name='後壁', ves='RCA', vtxt=[('RCA', C_RCA), ('か', (200, 210, 208)), ('LCx', C_LCX)],
         nurse='→ V7〜V9 を追加でとる', sub=['V1〜V3 が下がって R が高い', '→ 背中の V7〜V9 で上がる'],
         leads={'V1': (-0.14, 0.12, 0.25, 0.35, 1.5, 1), 'V2': (-0.22, 0.06, 0.32, 0.40, 1.5, 1),
                'V3': (-0.16, 0.00, 0.15, 0.15, 1.3, 1),
                'V7': (0.12, 0.04, 0, 0, 1), 'V8': (0.12, 0.04, 0, 0, 1), 'V9': (0.10, 0.03, 0, 0, 1)},
         seg={'post': 1}, vesw={'RCA': 0.75, 'LCX': 0.75}, x_post=1, mirror=1),
]
I_INF, I_RV = 3, 4
N_PAT = len(PATTERNS)

# --- 状態（数値の並び。補間で形を変える） ------------------------------------------
_PAR0 = (0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
NPAR = len(_PAR0)
KEYS = ([('lead', n, k) for n in ALL_LEADS for k in range(NPAR)] + [('seg', s) for s in SEGS] +
        [('ves', v) for v in VES_COL] + [('tint',), ('grey',), ('mirror',), ('x_rv',), ('x_post',), ('dimwave',)])
KI = {k: i for i, k in enumerate(KEYS)}


def mk_state(leads=None, seg=None, vesw=None, **kw):
    v = np.zeros(len(KEYS))
    for n in ALL_LEADS:
        par = tuple((leads or {}).get(n, _PAR0))
        par = par + _PAR0[len(par):]
        for k in range(NPAR):
            v[KI[('lead', n, k)]] = par[k]
    for s, a in (seg or {}).items():
        v[KI[('seg', s)]] = a
    for s, a in (vesw or {}).items():
        v[KI[('ves', s)]] = a
    for k, a in kw.items():
        v[KI[(k,)]] = a
    return v


STATES = {'N': mk_state(), 'G': mk_state(grey=1)}
for _i, _p in enumerate(PATTERNS):
    STATES[_i] = mk_state(_p['leads'], _p['seg'], _p['vesw'], x_rv=_p.get('x_rv', 0),
                          x_post=_p.get('x_post', 0), mirror=_p.get('mirror', 0))
STATES['S'] = mk_state(seg={}, vesw={'LAD': 1, 'LCX': 1, 'RCA': 1}, tint=1, x_rv=1, x_post=1, dimwave=1)


class St:
    """補間した状態を読みやすく。"""

    def __init__(self, v):
        self.v = v

    def par(self, lead):
        i = KI[('lead', lead, 0)]
        return tuple(self.v[i:i + NPAR])

    def __getattr__(self, k):
        return self.v[KI[(k,)]]

    def seg(self, s):
        return self.v[KI[('seg', s)]]

    def ves(self, s):
        return self.v[KI[('ves', s)]]


def red_w(st):
    return float(np.clip(st / 0.10, 0, 1))


def blue_w(st):
    return float(np.clip(-st / 0.06, 0, 1))


def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


# --- タイムライン（2026-10-23 夜から：ナレーションなし。字幕を読める長さで決める） ----------------
# 読む速さ：日本語 1秒に約6.5文字＋0.8秒（でんさんの指示）。空白は数えない
READ_CPS, READ_ADD = 6.5, 0.8


def read_t(*ss):
    return sum(len(x.replace(' ', '').replace('　', '')) for x in ss) / READ_CPS + READ_ADD


SUB_LEAD = 0.4                            # 名前が出てから字幕が出るまで
VIA_T, VIA_HOLD, DIRECT_T = 0.50, 0.15, 1.00
HOLD_MIN = 6.5                            # 1パターンの形がそのまま見えている長さの最低


def _pat_texts(p):
    v = p['vtxt'] if isinstance(p['vtxt'], str) else ''.join(x for x, _ in p['vtxt'])
    return [p['no'] + p['name'], v, p['nurse']] + p['sub']


HOLDS = [max(HOLD_MIN, SUB_LEAD + read_t(*_pat_texts(p))) for p in PATTERNS]
INTRO_END = I3.INTRO_END                  # 冒頭の3D（0〜9.9秒）
SUB_3D = [('12誘導は、心臓をいろんな向きから見ている', 0.30 + I3.T0, 4.33 + I3.T0),      # 6.5文字/秒＋0.8秒
          ('STが上がる誘導で、梗塞の場所の見当がつく', 4.38 + I3.T0, 8.41 + I3.T0),
          ('足もとから、頭のほうを見上げる', I3.T_EX2 + 0.2, I3.T_H13 - 0.05),   # 目が足もとへ回る〜人体が回る
          ('この向きのまま輪切りにする', I3.T_H13 + 0.1, I3.T_MV)]       # 13 で止まる〜寄る〜輪切りを重ねる〜図の塗り（説明の場面の字は intro3d）
# 「見かた」の場面はやめた（でんさん「イラストになってから動きがないのが嫌。すぐ①へ」）。輪切りが着いたらすぐ①へ。
# 見かたの内容は、最後のまとめに 2段で入れる
HOW0 = HOW1 = INTRO_END + 0.25
HOW_SUBS = ['となり合う誘導が、まとまって上がる', '反対側の誘導は、鏡のように下がる']
SUM_LINE = '上がる誘導で、場所と血管がわかる'
# まとめ：A（1行め・2行め＝見かた）→ B（1行め＝上がる誘導で…、2行め＝赤「ST上昇を見たら → 12誘導・すぐ報告」）→ 保存 → コメント
SUM_A = read_t(*HOW_SUBS)
SUM_B = read_t(SUM_LINE, 'ST上昇を見たら→12誘導・すぐ報告')
SAVE_T = SUM_A + SUM_B                    # まとめの頭から「保存して見返してね」まで
COMMENT_T = SAVE_T + 2.0
SUM_HOLD = COMMENT_T + 1.6
LOOP_FADE = 0.75


def _build():
    kf = [(0.0, 'N')]
    win = []                              # (名前が出る, 名前が消える, パターン番号)
    t = HOW1
    kf.append((t, 'N'))
    for i in range(N_PAT):
        if i == I_RV:                     # ④ → ⑤ は直接（下壁に右室が加わる）
            t0 = t
            t = t0 + DIRECT_T
        else:
            t = t + VIA_T
        kf.append((t, i))
        a = t
        t = a + HOLDS[i]
        kf.append((t, i))
        win.append((a, t, i))
        if i + 1 == I_RV:
            continue
        if i == N_PAT - 1:
            break
        t += VIA_T; kf.append((t, 'G'))
        t += VIA_HOLD; kf.append((t, 'G'))
    t += DIRECT_T; kf.append((t, 'S'))
    sum0 = t
    t += SUM_HOLD; kf.append((t, 'S'))
    t += LOOP_FADE; kf.append((t, 'N'))
    return kf, win, sum0, t


KF, WINDOWS, SUM0, DUR = _build()


def _subs():
    """字幕（文字, 出る, 消える）。位置はいつも同じ（SUB_Y）。"""
    out = list(SUB_3D)
    for a, b, i in WINDOWS:
        ss = PATTERNS[i]['sub']
        t0, t1 = a + SUB_LEAD, b - 0.05
        tot = sum(read_t(x) for x in ss)
        span = t1 - t0
        for x in ss:
            d = span * read_t(x) / tot
            out.append((x, t0, t0 + d - (0.1 if len(ss) > 1 else 0)))
            t0 += d
    out.append((HOW_SUBS[0], SUM0 - 0.2, SUM0 + SUM_A - 0.1))
    out.append((SUM_LINE, SUM0 + SUM_A, DUR - LOOP_FADE*0.5))
    return out


SUBS = [x + ('3d' if k < len(SUB_3D) else 'box',) for k, x in enumerate(_subs())]


# --- 輪切りの図のまわりの誘導（胸の電極・四肢誘導の札）に色がつく瞬間：2回点滅＋「ピピッ」（でんさん） --------------
# 音は sfx/blink_fonfon.mp3（でんさんが用意した著作権フリーの音）。波形は音のかたまりが1つ（0.08秒から立ち上がり、
# 0.21秒でいちばん大きく、0.5秒ほどで消える）なので、点滅も1回。光るいちばん明るい瞬間を、音のいちばん大きい所にそろえる
FLASH_SFX = os.path.join(HERE, 'sfx', 'blink_fonfon.mp3')
FLASH_PEAK_T, FLASH_UP, FLASH_DOWN = 0.21, 0.21, 0.40
FLASH_D = FLASH_UP + FLASH_DOWN
_FL = None


def _hot(st_par):
    return max(red_w(st_par), blue_w(st_par))


def get_flashes():
    """[(時刻, 誘導の並び)]。各パターンで、新しく色がつく誘導の色が半分をこえる時刻。"""
    global _FL
    if _FL is not None:
        return _FL
    names = list(ELEC_ANG) + [n for g in LIMB_TAGS for n in g[0]]
    out = []
    prev = set()
    for k, (a, b, i) in enumerate(WINDOWS):
        cur = {n for n in names if _hot(STATES[i][KI[('lead', n, 0)]]) >= 0.5}
        new = sorted(cur - (prev if i == I_RV else set()))   # ④→⑤ は直接なので、新しく加わった誘導だけ
        prev = cur
        if not new:
            continue
        t0 = a - (DIRECT_T if i == I_RV else VIA_T)
        for t in np.arange(t0, a + 0.6, 0.01):
            if max(_hot(state_at(t).par(n)[0]) for n in new) >= 0.5:
                out.append((float(t), tuple(new))); break
    _FL = out
    return out


def flash_amp(t):
    for t0, leads in get_flashes():
        if t0 <= t < t0 + FLASH_D:
            u = t - t0
            return (ease(u/FLASH_UP) if u < FLASH_UP else 1 - ease((u - FLASH_UP)/FLASH_DOWN)), leads
    return 0.0, ()


def draw_flash(im, t, s):
    f, leads = flash_amp(t)
    if f <= 0.004 or im is None:
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay, 'RGBA')
    for n in leads:
        col = mix(lead_col(n, s), WHITE, 0.35)
        if n in ELEC_ANG:
            x, y = ch_pt(ELEC_ANG[n])
            r = 16 + 10*f
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(150*f),))
            lx, ly = ch_pt(ELEC_ANG[n], 26)
            dx, dy = ELEC_LAB.get(n, (0, 0))
            d.rounded_rectangle([lx + dx - 26, ly + dy - 18, lx + dx + 26, ly + dy + 16], radius=10, fill=col + (int(110*f),))
        else:
            for names, pos, _ in LIMB_TAGS:
                if n in names:
                    ws = sum(text_w(m_, 24, 800) for m_ in names) + 8*(len(names) - 1)
                    d.rounded_rectangle([pos[0] - ws/2 - 14, pos[1] - 22, pos[0] + ws/2 + 14, pos[1] + 20], radius=12,
                                        fill=col + (int(120*f),), outline=col + (int(240*f),), width=3)
    lay = lay.filter(ImageFilter.GaussianBlur(3))
    im.alpha_composite(lay)


def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(u):
    u = cl(u)
    return u*u*(3 - 2*u)


def ramp(t, t0, d=0.5):
    return ease((t - t0) / d)


def mix(a, b, u):
    return tuple(int(round(a[i] + (b[i] - a[i])*u)) for i in range(3))


def state_at(t):
    for (t0, a), (t1, b) in zip(KF, KF[1:]):
        if t0 <= t < t1:
            u = 0.0 if a == b else ease((t - t0) / (t1 - t0))
            return St(STATES[a]*(1 - u) + STATES[b]*u)
    return St(STATES[KF[-1][1]])


def current(t):
    for a, b, i in WINDOWS:
        if a <= t < b:
            return i, a, b
    return None, None, None


# --- 道具（第26弾と同じ put / text_img。--check 用に字の外枠を記録する） ----------------
_FONTS, _TXT = {}, {}
REC = None                                # --check のとき：[(文字, 外枠, 濃さ, 種類)]


def font(size, weight):
    k = (size, weight)
    if k not in _FONTS:
        f = ImageFont.truetype(FONT, size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        _FONTS[k] = f
    return _FONTS[k]


def text_img(s, size, weight, col, max_w=None):
    k = (s, size, weight, col, max_w)
    if k in _TXT:
        return _TXT[k]
    sz = size
    while True:
        f = font(sz, weight)
        x0, y0, x1, y1 = f.getbbox(s)
        if max_w is None or (x1 - x0) <= max_w or sz <= 16:
            break
        sz -= 1
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (x1 - x0 + 8, asc + desc + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - x0, 4), s, font=f, fill=col + (255,))
    _TXT[k] = (im, asc, (4, 4 + y0, 4 + x1 - x0, 4 + y1), sz)
    return _TXT[k]


def text_w(s, size, weight):
    return text_img(s, size, weight, WHITE)[0].size[0] - 8


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None, kind='text'):
    if a <= 0.004:
        return
    im, asc, gb, sz = text_img(s, size, weight, col, max_w)
    w, h = im.size
    if right is not None:
        px = int(right - w + 4)
    elif x is not None:
        px = int(x - 4)
    else:
        px = int(cx - w/2)
    py = int(cy - 4 - asc*0.62)
    if REC is not None:
        REC.append((s, (px + gb[0], py + gb[1], px + gb[2], py + gb[3]), a, kind, sz))
    if base is None:
        return
    if a < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel('A').point(lambda v: int(v*a)))
    base.alpha_composite(im, (px, py))


def put_parts(base, parts, cy, a=1.0, max_w=720, gap=16, kind='text', right=None):
    """色・大きさのちがう文を1行に並べて中央ぞろえ。parts＝[(文字, 大きさ, 太さ, 色)]。入らないときは全部を同じ割合で小さく。"""
    k = 1.0
    while True:
        ws = [text_w(s, int(sz*k), wt) for s, sz, wt, _ in parts]
        tot = sum(ws) + gap*(len(parts) - 1)
        if tot <= max_w or k < 0.6:
            break
        k -= 0.02
    x = 540 - tot/2 if right is None else right - tot
    for (s, sz, wt, c), w_ in zip(parts, ws):
        put(base, s, int(sz*k), wt, c, x=x, cy=cy, a=a, kind=kind)
        x += w_ + gap


# --- 方眼（1mm＝14px の正方形。太い線が x=540 と 1段めの基線を通る） ----------------------
_GRID = None


def grid():
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = PXMM
    x0 = (540 % (5*pm)) - 5*pm
    y0 = (BASES[0] % (5*pm)) - 5*pm
    for major in (False, True):
        i = 0
        while x0 + i*pm <= W + 1:
            if (i % 5 == 0) == major:
                x = round(x0 + i*pm)
                d.line([(x, 0), (x, H)], fill=(G_MAJOR if major else G_MINOR) + (255,), width=2 if major else 1)
            i += 1
        k = 0
        while y0 + k*pm <= H + 1:
            if (k % 5 == 0) == major:
                y = round(y0 + k*pm)
                d.line([(0, y), (W, y)], fill=(G_MAJOR if major else G_MINOR) + (255,), width=2 if major else 1)
            k += 1
    return im


# --- 線（グロー付き。第26弾の glow_line を小さな枠ごとに） --------------------------------
SS = 2


def glow_line(size, runs, col, width, a, blur=(5, 13)):
    w, h = size
    core = Image.new('L', (w*SS, h*SS), 0)
    dc = ImageDraw.Draw(core)
    for pts in runs:
        if len(pts) >= 2:
            dc.line([(x*SS, y*SS) for x, y in pts], fill=255, width=int(width*SS), joint='curve')
    core = core.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if blur:
        g1 = np.asarray(core.filter(ImageFilter.GaussianBlur(blur[0])), dtype=np.float32)
        g2 = np.asarray(core.filter(ImageFilter.GaussianBlur(blur[1])), dtype=np.float32)
        g = np.maximum(g1*0.9, g2*0.45)
        lay = Image.new('RGBA', (w, h), col + (0,))
        lay.putalpha(Image.fromarray(np.clip(g*a, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), 0.55) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


# --- 12誘導の描画 -----------------------------------------------------------------
CELL_PAD_Y = 40                          # 枠ごとの絵の上下の余白（グローがはみ出すぶん）
TAU = np.linspace(TAU0 + 0.012, TAU1 - 0.012, 400)


def lead_alpha(name, s):
    return 1.0                           # 4段め（追加の誘導）もいつも出す


def extra_on(name, s):
    """追加の誘導が「使われている」度合い（0＝灰色の正常）。"""
    if name == 'V4R':
        return float(s.x_rv)
    if name in ('V7', 'V8', 'V9'):
        return float(s.x_post)
    return 1.0


def lead_label_col(name, s):
    st = s.par(name)[0]
    c = mix(LABEL_GREY, RED, red_w(st))
    c = mix(c, BLUE, blue_w(st))
    if s.tint > 0 and name in LEAD_WALL:
        c = mix(c, VES_COL[SEG_VES[LEAD_WALL[name]]], s.tint)
    return c


def label_x(name):
    c, _ = lead_cell(name)
    return max(col_x(c) + 14, SAFE_L + 5)


def draw_cell(im, name, s, fast=False):
    a = lead_alpha(name, s)
    if a <= 0.004:
        return
    c, r = lead_cell(name)
    x0, base = col_x(c), BASES[r]
    top = base - ROW_UP
    par = s.par(name)
    st = par[0]
    rw, bw = red_w(st), blue_w(st)
    hl_col = RED if rw >= bw else BLUE
    hl = max(rw, bw)
    # 誘導名（＋まとめのときは見ている壁の名前）
    lx = label_x(name)
    put(im, name, 30, 800, lead_label_col(name, s), x=lx, cy=top + 24, a=a)
    if s.tint > 0.004 and name in LEAD_WALL:
        wall = LEAD_WALL[name]
        # R波（枠の左から 84px）の右に置く（波形と字を重ねない）
        wx = max(x0 + WALL_LABEL_DX, lx + text_w(name, 30, 800) + 12)
        put(im, SEG_NAME[wall], 24, 800, VES_COL[SEG_VES[wall]], x=wx, cy=top + 25, a=a*s.tint)
    if fast:
        return
    v = beat(name, par, TAU)
    xs = x0 + (TAU - TAU0)*PXS
    ys = base - v*PXMV
    oy = top - CELL_PAD_Y
    hh = ROW_PITCH + 2*CELL_PAD_Y
    lay = Image.new('RGBA', (COL_W, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    lx_ = xs - x0
    ly_ = ys - oy
    bl = base - oy
    if hl > 0.004:
        # ST の部分を塗る（基線と波形のあいだ）・基線の点線
        # 右端（T波の立ち上がり）では、なだらかに消す
        fx = np.arange(int(lx_[np.searchsorted(TAU, ST_FILL[0])]), int(lx_[np.searchsorted(TAU, ST_FILL[1])]) + 1)
        fy = np.interp(fx, lx_, ly_)
        ft = TAU0 + 0.012 + (fx - lx_[0]) / PXS
        fw = 1 - _ss((ft - (ST_FILL[1] - 0.06)) / 0.06)
        for xx, yy, ww in zip(fx, fy, fw):
            if abs(yy - bl) > 1:
                d.line([(xx, yy), (xx, bl)], fill=hl_col + (int(110*hl*a*ww),), width=1)
        for xx in np.arange(6, COL_W - 6, 9):
            d.line([(xx, bl), (xx + 4, bl)], fill=hl_col + (int(200*hl*a),), width=2)
    im.alpha_composite(lay, (x0, oy))
    gr = max(s.grey, 1 - extra_on(name, s))
    base_col = mix(WAVE_GREEN, NEUTRAL_COL, gr)
    wa = a*(1.0 - 0.25*gr)*(1.0 - 0.55*s.dimwave)
    pts = list(zip(lx_, ly_))
    im.alpha_composite(glow_line((COL_W, hh), [pts], base_col, 3.0, wa), (x0, oy))
    if hl > 0.004:
        m = (TAU >= ST_LINE[0]) & (TAU <= ST_LINE[1])
        pts2 = list(zip(lx_[m], ly_[m]))
        im.alpha_composite(glow_line((COL_W, hh), [pts2], hl_col, 3.4, a*hl, blur=(4, 10)), (x0, oy))


def draw_panel(im, s, fast=False):
    # 列の切れ目（12誘導の紙の「誘導が切りかわる印」）
    if not fast:
        d = ImageDraw.Draw(im, 'RGBA')
        for r in range(4):
            for c in range(1, 4):
                x = col_x(c)
                al = 1.0
                d.line([(x, BASES[r] - 14), (x, BASES[r] + 14)], fill=(120, 140, 134, int(200*al)), width=2)
    for n in ALL_LEADS:
        draw_cell(im, n, s, fast)


# --- 4段め（追加の誘導）の説明・ふだんの凡例 ----------------------------------------
EXTRA_NOTE_Y = BASES[3] - 40             # 「← 右胸に貼る」「背中に貼る →」
LEGEND_Y = 1084                          # 凡例：12誘導のすぐ下（小さく）


def draw_extra_notes(im, s):
    # 説明は追加の誘導が半分以上出てから・まとめ（tint）が始まったらすぐ消す。凡例は追加の誘導が出始めたらすぐ消す（重ねない）
    # 4段めの誘導名の行（V4R の右）：ふだんは「追加の誘導」、右室のときは「← 右胸に貼る」、後壁のときは「背中に貼る →」
    k = cl(1 - 3*s.tint)
    x = label_x('V4R') + text_w('V4R', 30, 800) + 10
    cy = BASES[3] - ROW_UP + 24
    a_r, a_p = cl((s.x_rv - 0.5)/0.5)*k, cl((s.x_post - 0.5)/0.5)*k
    put(im, '追加の誘導', 20, 700, GREY, x=x, cy=cy, a=cl(1 - 2*max(s.x_rv, s.x_post))*cl(1 - 8*s.tint))
    # どこに貼るか：凡例の行の左（右室・後壁のときだけ）
    put(im, 'V4R＝右胸に貼る', 22, 800, RED, x=SAFE_L + 5, cy=LEGEND_Y, a=a_r)
    put(im, 'V7〜V9＝背中に貼る', 22, 800, RED, x=SAFE_L + 5, cy=LEGEND_Y, a=a_p)
    a_leg = cl(1 - 3*s.tint)
    if a_leg > 0.004:
        put_parts(im, [('赤＝ST上昇', 26, 800, RED), ('青＝鏡像', 26, 800, BLUE)], LEGEND_Y, a=a_leg, gap=30, right=890)   # 右寄せ（右下のボタン x900 より左）


# --- 心臓の輪切り（左室の短軸＋右室の三日月。足もとから見た向き：左が右室、右が側壁） -----------
# 2026-10-23 夜：字幕（y1266）の場所をあけるため、0.82倍にして下へ（まん中に）
# 確認版④：12誘導のすぐ下（1126〜1572）に大きく（最初の大きさの 1.35倍）
HX, HY = 470, 1345                       # 左室の中心
R_IN, R_OUT = 84, 151                    # 左室の内腔・外側
RV_D, RV_R, RV_WALL = 122, 149, 32       # 右室：中心を左へ 122px、半径 149、壁の厚さ 32
# 壁の角度（度。右＝0、反時計回り＝上が 90）
SEG_ANG = {'lat': (-15, 50), 'ant': (50, 125), 'sep': (125, 215), 'inf': (215, 290), 'post': (290, 345)}
SEG_LABEL = {'ant': (88, None), 'sep': (170, None), 'inf': (252, None), 'post': (318, None), 'lat': (17, None)}
HBOX = (130, 1103, 950, 1600)            # 輪切りを描く範囲
RV_LABEL = (HX - R_OUT - 3 - (RV_D + RV_R - RV_WALL - R_OUT - 3)/2 + 4, HY + 2)   # 右室の三日月の中
# 誘導名のまとまり（角度、中心からの距離、誘導）
TOKENS = [
    ('ant', 100, 214, ['V1', 'V2', 'V3', 'V4']),
    ('hl', 40, 236, ['I', 'aVL']),
    ('lat', 0, 238, ['V5', 'V6']),
    ('post', -42, 244, ['V7', 'V8', 'V9']),
    ('inf', -90, 200, ['II', 'III', 'aVF']),
    ('rv', 180, 302, ['V4R']),
]
TOK_SIZE, TOK_GAP = 27, 9
VES_LEGEND_X, VES_LEGEND_Y = 778, (1289, 1333, 1377)


def _pol(ang, r, cx=HX, cy=HY):
    a = math.radians(ang)
    return cx + r*math.cos(a), cy - r*math.sin(a)


def _seg_of(angle_deg):
    a = (angle_deg + 360) % 360
    for k, (a0, a1) in SEG_ANG.items():
        lo, hi = a0 % 360, a1 % 360
        if (lo <= hi and lo <= a < hi) or (lo > hi and (a >= lo or a < hi)):
            return k
    return 'lat'


_HEART_GEO = None


def heart_geo():
    """輪切りの画素ごとの壁の番号（SS 倍の格子）。"""
    global _HEART_GEO
    if _HEART_GEO is not None:
        return _HEART_GEO
    x0, y0, x1, y1 = HBOX
    ys, xs = np.mgrid[0:(y1 - y0)*SS, 0:(x1 - x0)*SS]
    X = x0 + (xs + 0.5)/SS
    Y = y0 + (ys + 0.5)/SS
    dx, dy = X - HX, -(Y - HY)
    r1 = np.hypot(dx, dy)
    ang = (np.degrees(np.arctan2(dy, dx)) + 360) % 360
    r2 = np.hypot(X - (HX - RV_D), Y - HY)
    ids = np.full(X.shape, -1, dtype=np.int8)
    ring = (r1 >= R_IN) & (r1 <= R_OUT)
    for j, k in enumerate(SEGS[:5]):
        a0, a1 = SEG_ANG[k]
        lo, hi = a0 % 360, a1 % 360
        m = (ang >= lo) & (ang < hi) if lo <= hi else ((ang >= lo) | (ang < hi))
        ids[ring & m] = j
    rv = (r2 <= RV_R) & (r1 >= R_OUT + 3)
    ids[rv & (r2 >= RV_R - RV_WALL)] = 5
    ids[rv & (r2 < RV_R - RV_WALL)] = 6          # 右室の内腔
    # 線：左室の外側・内側、右室の外側、壁の切れ目
    edge = (np.abs(r1 - R_OUT) < 1.3) | (np.abs(r1 - R_IN) < 1.3) | ((np.abs(r2 - RV_R) < 1.3) & (r1 >= R_OUT + 2))
    edge |= rv & (np.abs(r1 - (R_OUT + 3)) < 1.3)
    edge |= rv & (np.abs(r2 - (RV_R - RV_WALL)) < 1.2)
    for k, (a0, a1) in SEG_ANG.items():
        for aa in (a0,):
            ad = np.radians(aa)
            dist = np.abs(-dx*np.sin(ad) + dy*np.cos(ad))
            along = dx*np.cos(ad) + dy*np.sin(ad)
            edge |= ring & (dist < 1.2) & (along > 0)
    _HEART_GEO = (ids, edge)
    return _HEART_GEO


TISSUE = (30, 46, 42)
CAVITY = (6, 13, 12)
TISSUE_EDGE = (112, 134, 128)


def seg_col(k, s):
    c = mix(TISSUE, VES_COL[SEG_VES[k]], 0.52*s.tint)
    return mix(c, RED, 0.88*s.seg(k))


def draw_heart(im, s, fast=False):
    x0, y0, x1, y1 = HBOX
    if not fast:
        ids, edge = heart_geo()
        h, w = ids.shape
        rgba = np.zeros((h, w, 4), dtype=np.float32)
        for j, k in enumerate(SEGS):
            m = ids == j
            rgba[m, :3] = seg_col(k, s)
            rgba[m, 3] = 255
        rgba[ids == 6, :3] = CAVITY
        rgba[ids == 6, 3] = 235
        rgba[edge, :3] = TISSUE_EDGE
        rgba[edge, 3] = 235
        lay = Image.fromarray(rgba.astype(np.uint8), 'RGBA').resize((x1 - x0, y1 - y0), Image.LANCZOS)
        # 梗塞の壁のグロー
        inf = np.zeros((h, w), dtype=np.float32)
        for j, k in enumerate(SEGS):
            inf[ids == j] = s.seg(k)
        if inf.max() > 0.004:
            g = Image.fromarray(np.clip(inf*255, 0, 255).astype(np.uint8)).resize((x1 - x0, y1 - y0), Image.LANCZOS)
            g = np.asarray(g.filter(ImageFilter.GaussianBlur(12)), dtype=np.float32)
            gl = Image.new('RGBA', (x1 - x0, y1 - y0), RED + (0,))
            gl.putalpha(Image.fromarray(np.clip(g*0.75, 0, 255).astype(np.uint8)))
            im.alpha_composite(gl, (x0, y0))
        draw_chest(im)
        im.alpha_composite(lay, (x0, y0))
        draw_vessels(im, s)
        if s.mirror > 0.004:
            draw_mirror(im, s)
    # 壁の名前
    for k, (ang, _) in SEG_LABEL.items():
        px, py = _pol(ang, (R_IN + R_OUT)/2)
        col = mix((198, 210, 206), WHITE, s.seg(k))
        put(im, SEG_NAME[k], 28, 800, col, cx=px, cy=py + 2)
    put(im, '右室', 28, 800, mix((198, 210, 206), WHITE, s.seg('rv')), cx=RV_LABEL[0], cy=RV_LABEL[1])   # 右室の三日月の中（中隔の字と離す）
    # 胸部の電極（実際に貼る場所）と、四肢誘導（見ている向き）
    draw_electrodes(im, s, fast)
    for names, pos, tip in LIMB_TAGS:
        draw_limb_tag(im, s, names, pos, tip, fast)
    # 血管の見本
    for j, v in enumerate(('LAD', 'LCX', 'RCA')):
        a = 0.45 + 0.55*max(s.ves(v), s.tint)
        col = mix(DIM, VES_COL[v], a)
        y = VES_LEGEND_Y[j]
        if not fast:
            d = ImageDraw.Draw(im, 'RGBA')
            d.line([(VES_LEGEND_X, y), (VES_LEGEND_X + 26, y)], fill=col + (255,), width=6)
        put(im, VES_NAME[v], 28, 800, col, x=VES_LEGEND_X + 36, cy=y)


# --- 胸の断面（足もとから見た向き：上＝前・画面の右＝患者の左）と、電極の実際の位置（LITFL ECG Lead positioning） ---
NOTE_X = 702                              # 注記：輪切りの右下（胸の輪郭の外・右下のボタン x900 より左）
CH_C, CH_RX, CH_RY = (430, 1352), 285, 205        # 胸の輪郭（楕円）。上のまん中＝胸骨、下のまん中＝背骨
# 楕円の上の角度（度。右＝0＝患者の左の真横、上＝90＝胸骨）
ELEC_ANG = {'V1': 96, 'V2': 84, 'V3': 72, 'V4': 58, 'V5': 36, 'V6': 0,      # V1 胸骨の右縁・V2 左縁（第4肋間）、V3 V2とV4の中間、
            'V7': -38, 'V8': -62, 'V9': -80, 'V4R': 122}                    # V4 左鎖骨中線・V5 前腋窩線・V6 中腋窩線（第5肋間）、
#                                                                            V7 後腋窩線・V8 肩甲骨の下の角・V9 背骨の左（V6 と同じ高さ）、V4R 右鎖骨中線
ELEC_LAB = {'V8': (14, 8), 'V9': (30, -6)}        # 名前の置き場所の調整（dx, dy）。ふつうは外向きに 26px
LIMB_TAGS = [(['I', 'aVL'], (792, 1222), 20), (['II', 'III', 'aVF'], (232, 1578), -112)]   # 四肢誘導：名前の位置・矢印の先（胸の輪郭の角度）


def ch_pt(ang, d=0.0):
    a = math.radians(ang)
    x, y = CH_C[0] + CH_RX*math.cos(a), CH_C[1] - CH_RY*math.sin(a)
    nx, ny = math.cos(a)/CH_RX, -math.sin(a)/CH_RY
    L = math.hypot(nx, ny)
    return x + d*nx/L, y + d*ny/L


def lead_col(n, s, dim=TOKEN_DIM):
    st = s.par(n)[0]
    col = mix(dim, RED, red_w(st))
    col = mix(col, BLUE, blue_w(st))
    if s.tint > 0 and n in LEAD_WALL:
        col = mix(col, VES_COL[SEG_VES[LEAD_WALL[n]]], s.tint)
    return col


def draw_chest(im):
    d = ImageDraw.Draw(im, 'RGBA')
    cx, cy = CH_C
    d.ellipse([cx - CH_RX, cy - CH_RY, cx + CH_RX, cy + CH_RY], outline=(96, 120, 114, 210), width=3)
    d.rounded_rectangle([cx - 22, cy - CH_RY + 4, cx + 22, cy - CH_RY + 20], radius=6, fill=(96, 120, 114, 200))   # 胸骨
    d.ellipse([cx - 20, cy + CH_RY - 52, cx + 20, cy + CH_RY - 14], fill=(96, 120, 114, 200))                   # 背骨（椎体）
    d.polygon([(cx - 7, cy + CH_RY - 16), (cx + 7, cy + CH_RY - 16), (cx, cy + CH_RY - 2)], fill=(96, 120, 114, 200))


def draw_electrodes(im, s, fast=False):
    for n, ang in ELEC_ANG.items():
        col = lead_col(n, s, (150, 166, 162))
        hot = max(red_w(s.par(n)[0]), blue_w(s.par(n)[0]))
        if not fast:
            d = ImageDraw.Draw(im, 'RGBA')
            x, y = ch_pt(ang)
            if hot > 0.05:
                g = 12 + 6*hot
                d.ellipse([x - g, y - g, x + g, y + g], fill=col + (int(90*hot),))
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=(236, 241, 240, 255), outline=col + (255,), width=2)
            ec = I3.ELEC_COLORS.get(n)
            if ec:                           # 電極の色（IEC：V1 赤・V2 黄・V3 緑・V4 茶・V5 黒・V6 紫）。白いふち＋まん中の金具
                ri = 5 if n == 'V5' else 6
                d.ellipse([x - ri, y - ri, x + ri, y + ri], fill=ec + (255,))
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(170, 176, 178, 255))
            else:
                d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col + (255,))
        lx, ly = ch_pt(ang, 26)
        dx, dy = ELEC_LAB.get(n, (0, 0))
        put(im, n, TOK_SIZE, 800, col, cx=lx + dx, cy=ly + dy)


def draw_limb_tag(im, s, names, pos, tip_ang, fast=False):
    """四肢誘導（胸の電極ではない）：角丸の札＋「見ている向き」の矢印。"""
    ws = [text_w(n, 24, 800) for n in names]
    tot = sum(ws) + 8*(len(names) - 1)
    x0 = pos[0] - tot/2
    if not fast:
        d = ImageDraw.Draw(im, 'RGBA')
        d.rounded_rectangle([x0 - 10, pos[1] - 18, x0 + tot + 10, pos[1] + 16], radius=10, outline=(120, 140, 136, 200), width=2)
        tx, ty = ch_pt(tip_ang, 6)
        sx, sy = (x0 - 10, pos[1]) if tx < x0 else ((pos[0], pos[1] - 18) if ty < pos[1] else (pos[0] + tot/2*0 , pos[1] - 18))
        ux, uy = tx - sx, ty - sy
        L = math.hypot(ux, uy); ux, uy = ux/L, uy/L
        c = (150, 166, 162, 230)
        d.line([(sx, sy), (tx - ux*10, ty - uy*10)], fill=c, width=3)
        d.polygon([(tx, ty), (tx - ux*14 - uy*7, ty - uy*14 + ux*7), (tx - ux*14 + uy*7, ty - uy*14 - ux*7)], fill=c)
    x = x0
    for n, w_ in zip(names, ws):
        put(im, n, 24, 800, lead_col(n, s), x=x, cy=pos[1])
        x += w_ + 8


def draw_tokens(im, s, gk, ang, r, names):
    cx, cy = _pol(ang, r)
    ws = [text_w(n, TOK_SIZE, 800) for n in names]
    tot = sum(ws) + TOK_GAP*(len(names) - 1)
    x = cx - tot/2
    act = 0.0
    for n, w_ in zip(names, ws):
        st = s.par(n)[0]
        a_lead = 1.0
        if n == 'V4R':
            a_lead = 0.55 + 0.45*s.x_rv
        elif n in ('V7', 'V8', 'V9'):
            a_lead = 0.55 + 0.45*s.x_post
        col = mix(TOKEN_DIM, RED, red_w(st))
        col = mix(col, BLUE, blue_w(st))
        if s.tint > 0 and n in LEAD_WALL:
            col = mix(col, VES_COL[SEG_VES[LEAD_WALL[n]]], s.tint)
        act = max(act, red_w(st), blue_w(st))
        put(im, n, TOK_SIZE, 800, col, x=x, cy=cy, a=a_lead)
        x += w_ + TOK_GAP


def _arc_pts(cx, cy, r, a0, a1, n=60):
    return [_pol(a0 + (a1 - a0)*k/n, r, cx, cy) for k in range(n + 1)]


VES_ARCS = {
    'LAD': [(HX, HY, R_OUT + 9, 52, 123)],
    'LCX': [(HX, HY, R_OUT + 9, -58, 48)],
    'RCA': [(HX - RV_D, HY, RV_R + 8, 118, 242), (HX, HY, R_OUT + 9, 238, 292)],
}


def draw_vessels(im, s):
    """責任血管：壁の外側の色の線（その血管が血を送る範囲）。関係ないときはうすく。"""
    x0, y0, x1, y1 = HBOX
    for v, arcs in VES_ARCS.items():
        a = 0.30 + 0.70*max(s.ves(v), s.tint)
        wd = 5 + 3*s.ves(v)
        runs = [[(px - x0, py - y0) for px, py in _arc_pts(*arc)] for arc in arcs]
        blur = (4, 10) if s.ves(v) > 0.05 else None
        im.alpha_composite(glow_line((x1 - x0, y1 - y0), runs, VES_COL[v], wd, a, blur=blur), (x0, y0))


def draw_mirror(im, s):
    """後壁：前から見る V1〜V3 は、後壁を「反対側から」見る（鏡うつし）。点線の矢印で。"""
    d = ImageDraw.Draw(im, 'RGBA')
    p0, p1 = MIRROR_P0, MIRROR_P1
    n = 15
    a = s.mirror
    col = BLUE + (int(235*a),)
    for k in range(n - 1):
        if k % 2:
            continue
        u0, u1 = k/n, (k + 1)/n
        d.line([(p0[0] + (p1[0] - p0[0])*u0, p0[1] + (p1[1] - p0[1])*u0),
                (p0[0] + (p1[0] - p0[0])*u1, p0[1] + (p1[1] - p0[1])*u1)], fill=col, width=4)
    # 矢じり（後壁に向かって）
    ux, uy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(ux, uy); ux, uy = ux/L, uy/L
    tip = p1
    b0 = (tip[0] - 16*ux - 8*uy, tip[1] - 16*uy + 8*ux)
    b1 = (tip[0] - 16*ux + 8*uy, tip[1] - 16*uy - 8*ux)
    d.polygon([tip, b0, b1], fill=col)


# 鏡像の点線：V1 の字の下から、前壁と中隔の切れ目（125°）を通り、内腔を抜けて後壁へ（壁の名前の字を避ける）
MIRROR_P0 = (466, 1176)                   # V2 の電極の下から
MIRROR_P1 = _pol(-40, R_IN + 4)
MIRROR_LABEL = (NOTE_X, 1150)                # 右端。輪切りの左上（V1〜V4 の左・右室の上）


# --- 文字 -------------------------------------------------------------------------
TITLE = '心筋梗塞の場所'
HEADER = [(TITLE, 1.0, WHITE), (str(N_PAT), 1.5, YELLOW), ('パターン', 1.0, WHITE)]
HEADER_BASE = 362
QUESTION = 'ST上昇、心臓のどこ？'
NAME_CY = 340                            # いちばん上：見出し／パターンの番号と名前＋血管
TXT_Y1 = NAME_CY                         # （サムネイル用）
BOX = (80, 390, 1000, 488)               # 説明の枠（毎回同じ）：12誘導の左右の端と同じ x80〜1000
BOX_L1, BOX_L2 = 422, 458                # 枠の中：1行め＝字幕（上がる／下がる誘導）、2行め＝看護の1行など
BOX3D = (80, 1400, 1000, 1462)           # 3D のときの枠（心臓の下。同じ見た目・1行）
SUB_SIZE, NURSE_SIZE, BOX_MAXW = 34, 32, 820
SUM_LABEL = 'まとめ'
REPORT = [('ST上昇を見たら', NURSE_SIZE, 800, WHITE), ('→ 12誘導・すぐ報告', NURSE_SIZE, 900, RED)]
SAVE = '保存して見返してね'
COMMENT = '何個わかった？コメントで教えてね'
NEXT_LABEL = '▶ 次の例'
NOTES = ('※波形は一例',)
SLICE_NOTE = ('足もとから見た図', '（輪切りの模式図）')   # 輪切りの左上。本編のあいだずっと
SUM_NOTE = '※側壁はLADの枝のことも'          # まとめのときだけ（左下の注記の上）
WATERMARK = '@nurse_polarbearden'
WM_SIZE, WM_WEIGHT, WM_A = 64, 800, 0.16
WM_CY = 714                              # 凡例（y1182）と輪切り（上端 y1311）のあいだ（字の上下は cy-23〜cy+41）。全コマ同じ


def draw_header(base, a):
    if a <= 0.004:
        return
    size = 50
    parts = [text_img(sx, int(size*k), 900, col) for sx, k, col in HEADER]
    widths = [p[0].size[0] - 8 for p in parts]
    total = sum(widths) + 8*(len(parts) - 1)
    x = (W - total) / 2
    for (im_, asc, gb, sz), w_ in zip(parts, widths):
        if REC is not None:
            py = int(HEADER_BASE - 4 - asc)
            REC.append(('見出し', (int(x - 4) + gb[0], py + gb[1], int(x - 4) + gb[2], py + gb[3]), a, 'text', sz))
        if base is not None:
            if a < 0.999:
                im_ = im_.copy(); im_.putalpha(im_.getchannel('A').point(lambda q: int(q*a)))
            base.alpha_composite(im_, (int(x - 4), int(HEADER_BASE - 4 - asc)))
        x += w_ + 8


def vtxt_parts(p):
    """名前のうしろの責任血管（1色か、色のちがう語の並び）。"""
    v = p['vtxt']
    if isinstance(v, str):
        return [(v, 38, 800, VES_COL[p['ves']])]
    return [(x, 38, 800, c) for x, c in v]


BOARD_A = 0.40                            # 札・枠の背景の不透明度（下の絵が透ける。字は 100%）


def rrect_overlay(im, box, radius, fill, outline=None, width=2):
    """半透明の角丸の板を重ねる（RGBA の絵に ImageDraw で直接描くと半透明にならないので、別の板に描いてから重ねる）。"""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.size[0] - 1, x1), min(im.size[1] - 1, y1)
    if x1 <= x0 or y1 <= y0:
        return
    lay = Image.new('RGBA', (x1 - x0 + 1, y1 - y0 + 1), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([0, 0, x1 - x0, y1 - y0], radius=radius, fill=fill, outline=outline, width=width)
    im.alpha_composite(lay, (x0, y0))


def draw_box(im, box, a):
    """説明の枠：角丸・細い線・半透明の背景。中身が変わっても動かない。"""
    if im is None or a <= 0.004:
        return
    rrect_overlay(im, box, 18, (8, 18, 16, int(255*BOARD_A*a)), (120, 146, 138, int(200*a)), 2)


def draw_texts(im, t, s):
    a_loop = ramp(t, DUR - LOOP_FADE, LOOP_FADE)
    t_in = I3.T_MV + 0.25         # 輪切りが下へ動きはじめたら、見出し・枠が出る
    # 見出し（3D のあと〜見かた）。①からはパターンの名前に入れ替わる
    draw_header(im, ramp(t, t_in, 0.5)*(1 - ramp(t, WINDOWS[0][0] - 0.35, 0.3)))
    draw_box(im, BOX, ramp(t, t_in, 0.5)*(1 - a_loop))
    # 見かた（1行め＝字幕、2行め＝赤い字）
    # パターン
    i, a, b = current(t)
    if i is not None:
        p = PATTERNS[i]
        al = ramp(t, a + 0.1, 0.3)*(1 - ramp(t, b - 0.25, 0.25))
        put_parts(im, [(f"{p['no']} {p['name']}", 54, 900, WHITE)] + vtxt_parts(p), NAME_CY, a=al, gap=14, max_w=BOX_MAXW)
        aln = ramp(t, a + 1.6, 0.4)*(1 - ramp(t, b - 0.25, 0.25))
        put(im, p['nurse'], NURSE_SIZE, 800, GREEN, cx=540, cy=BOX_L2, a=aln, max_w=BOX_MAXW)
    # つなぎ（灰色の正常）
    if s.grey > 0.6:
        put(im, NEXT_LABEL, 34, 700, (168, 178, 180), cx=540, cy=NAME_CY, a=ease((s.grey - 0.6)/0.4))
    # まとめ
    if t >= SUM0 - 0.5:
        ka = 1 - a_loop
        sw = ramp(t, SUM0 + COMMENT_T, 0.4)
        put(im, SUM_LABEL, 54, 900, WHITE, cx=540, cy=NAME_CY, a=ramp(t, SUM0 - 0.2, 0.4)*ka)
        put(im, HOW_SUBS[1], NURSE_SIZE, 800, WHITE, cx=540, cy=BOX_L2, a=ramp(t, SUM0 + 0.6, 0.4)*(1 - ramp(t, SUM0 + SUM_A - 0.3, 0.3))*ka, max_w=BOX_MAXW)
        put_parts(im, REPORT, BOX_L2, a=ramp(t, SUM0 + SUM_A + 0.3, 0.4)*(1 - ramp(t, SUM0 + SAVE_T - 0.3, 0.3))*ka, gap=12, max_w=BOX_MAXW)
        put(im, SAVE, NURSE_SIZE, 800, GREEN, cx=540, cy=BOX_L2, a=ramp(t, SUM0 + SAVE_T, 0.4)*(1 - ramp(t, SUM0 + COMMENT_T - 0.3, 0.3))*ka)
        put(im, COMMENT, NURSE_SIZE, 900, YELLOW, cx=540, cy=BOX_L2, a=sw*ka, max_w=BOX_MAXW)
    # 後壁：鏡うつし
    if s.mirror > 0.004:
        put(im, '鏡像（前から', 20, 800, BLUE, x=MIRROR_LABEL[0], cy=MIRROR_LABEL[1], a=s.mirror)
        put(im, '見ると逆さ）', 20, 800, BLUE, x=MIRROR_LABEL[0], cy=MIRROR_LABEL[1] + 23, a=s.mirror)


def draw_notes(im, s=None):
    # 注記：輪切りの右下。胸の輪郭・V7 の字から離し（x726〜）、見出し2行＋すき間＋注記で、まわりに余白をとる
    nx = 726
    lines = [(SLICE_NOTE[0], 700, LABEL_GREY, 1466), (SLICE_NOTE[1], 400, GREY, 1487),
             ('※電極は胸の高さを', 400, GREY, 1513), ('　まとめて1枚に', 400, GREY, 1533), (NOTES[0], 400, GREY, 1554)]
    for n, wt, c, y in lines:
        put(im, n, 18, wt, c, x=nx, cy=y, a=0.9)
    if s is not None and s.tint > 0.004:      # まとめのときだけ。胸の輪郭より下（y1571〜）なので、1行で左から
        put(im, '※側壁はLADの枝のことも', 18, 400, GREY, x=648, cy=1581, a=0.85*s.tint)
    # 方向の字（足もとから見た向き）
    dc = (200, 210, 208)
    put(im, '↑ 前', 20, 700, dc, cx=330, cy=1118, a=0.8)
    put(im, '↓ 背中', 20, 700, dc, cx=420, cy=1580, a=0.8)
    put(im, '← 体の右', 20, 700, dc, x=SAFE_L + 5, cy=1200, a=0.8)
    put(im, '体の左 →', 20, 700, dc, right=900, cy=1414, a=0.8)


BAND3D = (0, 1280, W, 1470)               # 3D の場面：壁の名前＋誘導の行と字幕の行をまとめた1本の帯（左右の端まで・角丸なし）


def sub3d_alpha(t):
    return max([ramp(t, t0, 0.25)*(1 - ramp(t, t1 - 0.2, 0.2)) for txt, t0, t1, w in SUBS if w == '3d'] + [0.0])


def band3d(im, t, a_label=0.0):
    a = max(a_label, sub3d_alpha(t))
    if im is None or a <= 0.004:
        return
    lay = Image.new('RGBA', (BAND3D[2] - BAND3D[0], BAND3D[3] - BAND3D[1]), (0, 6, 20, int(255*BOARD_A*a)))
    im.alpha_composite(lay, BAND3D[:2])


def draw_subtitle(im, t):
    """字幕（白・34px）。ふだんは説明の枠の1行め。3D のときは帯（BAND3D）の下の行。"""
    if t >= I3.T_FIN and im is not None:
        band3d(im, t)                        # 3D の後半（説明の場面〜輪切り）は札がないので、字幕だけで帯を出す
    for txt, t0, t1, where in SUBS:
        a = ramp(t, t0, 0.25)*(1 - ramp(t, t1 - 0.2, 0.2))
        if a <= 0.004:
            continue
        if where == '3d':
            cy = (BOX3D[1] + BOX3D[3]) / 2
        else:
            cy = BOX_L1
        put(im, txt, SUB_SIZE, 800, WHITE, cx=540, cy=cy, a=a, max_w=BOX_MAXW, kind='sub')


_SCACHE = {}


def static_layer(s):
    """文字以外（12誘導・4段めの説明・輪切り・注記）を、透明の下地に描いたもの。状態が同じなら使い回す（書き出しを速く）。"""
    key = np.round(s.v, 5).tobytes()
    if key in _SCACHE:
        return _SCACHE[key]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw_panel(lay, s)
    draw_extra_notes(lay, s)
    draw_heart(lay, s)
    draw_notes(lay, s)
    if len(_SCACHE) > 6:
        _SCACHE.clear()
    _SCACHE[key] = lay
    return lay


def _mul_alpha(lay, a):
    if a >= 0.999:
        return lay
    lay = lay.copy()
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v*a)))
    return lay


FIN_SPLIT = 1101                          # 3D の終わり：上（12誘導）と下（輪切り）で出かたを変える
HEART_C = (HX - (RV_D + RV_R - R_OUT)/2, HY)   # 輪切りの図（右室の左端〜左室の右端）のまん中
HEART_W = RV_D + RV_R + R_OUT             # その幅（256px）。08 の心臓の幅に合わせて重ねる
def _heart_rgba(kind):
    """輪切りの図だけ（誘導名・字なし）を SS 倍の細かさで。kind='plain'＝図の塗り、'muscle'＝3D に似せた筋肉の赤（中間の絵）。"""
    s = St(STATES['N'])
    ids, edge = heart_geo()
    h, w = ids.shape
    rgba = np.zeros((h, w, 4), dtype=np.float32)
    if kind == 'plain':
        for j, k in enumerate(SEGS):
            m = ids == j
            rgba[m, :3] = seg_col(k, s)
            rgba[m, 3] = 255
        rgba[ids == 6, :3] = CAVITY
        rgba[ids == 6, 3] = 235
        rgba[edge, :3] = TISSUE_EDGE
        rgba[edge, 3] = 235
    else:
        x0, y0 = HBOX[:2]
        ys, xs = np.mgrid[0:h, 0:w]
        X, Y = x0 + (xs + 0.5)/SS, y0 + (ys + 0.5)/SS
        r1 = np.hypot(X - HX, Y - HY)
        # 光は左上から：明るい赤〜暗い赤のグラデーション＋つや
        lx = ((X - HX)*-0.6 + (Y - HY)*-0.8) / (RV_D + RV_R)
        shade = np.clip(0.55 + 0.45*lx, 0, 1)[..., None]
        dark, light = np.array([96, 14, 24], np.float32), np.array([228, 92, 96], np.float32)
        col = dark + (light - dark)*shade
        spec = np.clip(1 - np.hypot(X - (HX - 60), Y - (HY - 70))/90, 0, 1)[..., None]**2
        col = col + (np.array([255, 210, 205], np.float32) - col)*0.45*spec
        lv = (ids >= 0) & (ids <= 4)
        rgba[lv, :3] = col[lv]
        rgba[lv, 3] = 255
        rv = ids == 5
        rgba[rv, :3] = (col[rv]*0.8 + np.array([235, 140, 140], np.float32)*0.2)
        rgba[rv, 3] = 255
        cav = (ids == 6) | (r1 < R_IN)
        rgba[cav, :3] = (34, 6, 10)
        rgba[cav, 3] = 240
    lay = Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), 'RGBA')
    return lay                            # 血管の線は付けない（中間の絵と同じ外形のまま色だけ変える。血管は定位置で図といっしょに出る）


_BIGS, _PH = {}, None


def heart_big(kind='plain'):
    if kind not in _BIGS:
        _BIGS[kind] = _heart_rgba(kind)
    return _BIGS[kind]


def place_big(k, p, kind='plain'):
    """heart_big を、画面で（輪切りのまん中＝p、大きさ＝定位置の (kx, ky) 倍）に置いた全画面の RGBA。"""
    kx, ky = k
    x0, y0 = HBOX[:2]
    co = (SS/kx, 0, SS*(HEART_C[0] - x0 - p[0]/kx), 0, SS/ky, SS*(HEART_C[1] - y0 - p[1]/ky))
    return heart_big(kind).transform((W, H), Image.AFFINE, co, resample=Image.BICUBIC)


# 08 の寄り終わり（T_FIN）の絵で、心室のかたまり（大血管・下の静脈を除く赤い所）の外形を色で測った値（画面の px）：
#   左端（右室側）x18・右端（左室側）x1050・上端 y392・下端 y1152 → 輪切りの図（右室の左端〜左室の右端 422px・高さ 302px）を
#   この外形にぴったり重ねる：中心 (534, 772)、横 1032/422＝2.445倍、縦 760/302＝2.517倍
FIN_FIT = ((534.0, 772.0), (2.445, 2.517))


# 13（足もとから）：入ってきたとき（心臓が全身 14 の心臓と同じあたり）→ 心臓へ寄ったところ（輪切りが定位置とほぼ同じ大きさ）
_h13 = I3.HEART13
Q13_IN = (I3.S13_FULL*I3.HEART13[0][0] + I3.C13_FULL[0], I3.S13_FULL*I3.HEART13[0][1] + I3.C13_FULL[1])   # 13 で止まったときの心室のまん中
Q13_Z, S13_Z = (470.0, 1050.0), HEART_W*1.0/_h13[1][0]   # 寄ったところ：心室の幅＝輪切りの幅（422px）
FIT13 = (Q13_Z, (S13_Z*_h13[1][0] / HEART_W, S13_Z*_h13[1][1] / (2*R_OUT)))   # 心室の外形（x605〜907・y197〜433）に合わせる


def cam13_at(q, sc):
    (hx, hy), _ = _h13
    return sc, (q[0] - sc*hx, q[1] - sc*hy)


def fin_frame(t, s):
    """T_FIN〜INTRO_END：
    1. 08（前下から）の心臓が小さくなりながら、全身 14 の心臓へ重なる（EX1）・全身がはっきり（EX1H）
    2. 胸の前の目が足もとの下へ回って上を向き、視線が心臓までのびる（EX2）
    3. 視線にそって画面が下から上へ流れ、13（足もとから）が入って止まる（EX3・H13） 4. 13 の心臓へ寄る（Z13）
    5. 13 の心室の外形に筋肉の赤い輪切りを重ね、13 を消す（OV） 6. 同じ位置・大きさで図の塗りへ（RC） 7. 定位置へ（MV）"""
    global _PH
    if _PH is None:
        _PH = I3.photo08()
    photo, pc, pw = _PH
    (p08, k08) = FIN_FIT
    w08 = HEART_W*k08[0]
    hx14, hy14, hw14 = I3.heart14_screen()
    u1 = ease((t - I3.T_FIN) / I3.EX1_D)
    ux15 = ease((t - I3.T_X15) / I3.X15_D)
    ux13 = ease((t - I3.T_X13) / I3.X13_D)
    uz = ease((t - I3.T_Z13) / I3.Z13_D)
    uo = (t - I3.T_OV) / I3.OV_D
    u2 = (t - I3.T_RC) / I3.RC_D
    e3 = ease((t - I3.T_MV) / I3.MV_D)
    im = _GRID.copy()
    dy = 0.0
    if t < I3.T_ROT:
        # 1. 心臓の位置で 08 と 14 をつなぐ（心臓の幅は対数で、位置は直線で）
        hw = math.exp(math.log(w08) + (math.log(hw14) - math.log(w08))*u1)
        q = (p08[0] + (hx14 - p08[0])*u1, p08[1] + (hy14 - p08[1])*u1)
        pic = I3.render_locked(I3.render14(I3.S14, I3.C14), (hx14, hy14), hw14, q, hw)
        a14 = ease((u1 - 0.25) / 0.6)
        pic = pic.convert('RGBA')
        if a14 < 1:
            # 08 は心臓のまわりだけを、やわらかい丸で残して 14 に重ねる（絵の四角い端を見せない）
            p8 = I3.render_locked(photo, p08, w08, q, hw).convert('RGBA')
            yy, xx = np.mgrid[0:H//8, 0:W//8]
            rr = np.hypot(xx*8 - q[0], yy*8 - q[1]) / max(hw*0.75, 1)
            msk = np.clip(1.6 - rr, 0, 1)*(1 - a14)
            p8.putalpha(Image.fromarray((msk*255).astype(np.uint8)).resize((W, H), Image.BILINEAR))
            pic.alpha_composite(p8)
        if ux15 > 0:                      # 3. 14 → 回る動画の最初のコマ（位置・大きさを合わせて重ねる）
            pic = Image.blend(pic.convert('RGB'), I3.rot_frame(I3.T_ROT), ux15).convert('RGBA')
    elif t < I3.T_H13:
        pic = I3.rot_frame(t)             # 4. 人体が回る
        if ux13 > 0:                      # 5. 最後のコマ → 13（位置・大きさを合わせて重ねる）
            pic = Image.blend(pic, I3.render13(I3.S13_FULL, I3.C13_FULL), ux13)
        pic = pic.convert('RGBA')
    else:
        sc = math.exp(math.log(I3.S13_FULL) + (math.log(S13_Z) - math.log(I3.S13_FULL))*uz)
        q13 = (Q13_IN[0] + (Q13_Z[0] - Q13_IN[0])*uz, Q13_IN[1] + (Q13_Z[1] - Q13_IN[1])*uz)
        pic = I3.render13(*cam13_at(q13, sc)).convert('RGBA')
    if t < I3.T_H13:
        pic.alpha_composite(I3.explain_layer(sys.modules[__name__], t, dy=dy))
    fa = 1 - ease(uo)
    if fa > 0.004:
        im = Image.blend(im, pic.convert('RGB').convert('RGBA'), fa)
    (p0, k0) = FIT13
    k = (math.exp(math.log(k0[0])*(1 - e3)), math.exp(math.log(k0[1])*(1 - e3)))
    p = (p0[0] + (HEART_C[0] - p0[0])*e3, p0[1] + (HEART_C[1] - p0[1])*e3)
    u3 = (t - I3.T_MV) / I3.MV_D
    am = ease(uo)
    if am > 0.004:
        if u2 < 1:
            im.alpha_composite(_mul_alpha(place_big(k, p, 'muscle'), am*(1 - ease(u2))))
        if u2 > 0:
            im.alpha_composite(_mul_alpha(place_big(k, p, 'plain'), ease(u2)))
    # 区画の名前（図の塗りになるあいだに出て、図といっしょに動く）
    an = ease(u2 / 0.35)*(1 - ease((u3 - 0.75) / 0.25))
    if an > 0.004:
        for kk, (ang, _) in SEG_LABEL.items():
            fx, fy = _pol(ang, (R_IN + R_OUT)/2)
            put(im, SEG_NAME[kk], 28, 800, (198, 210, 206), cx=p[0] + k[0]*(fx - HEART_C[0]), cy=p[1] + k[1]*(fy + 2 - HEART_C[1]), a=an)
        put(im, '右室', 28, 800, (198, 210, 206), cx=p[0] + k[0]*(RV_LABEL[0] - HEART_C[0]), cy=p[1] + k[1]*(RV_LABEL[1] - HEART_C[1]), a=an)
    lay = static_layer(s)
    im.alpha_composite(_mul_alpha(lay.crop((0, 0, W, FIN_SPLIT)), ease((u3 - 0.35) / 0.65)))
    im.alpha_composite(_mul_alpha(lay.crop((0, FIN_SPLIT, W, H)), ease((u3 - 0.70) / 0.30)), (0, FIN_SPLIT))
    I3.view_icon(sys.modules[__name__], im, t)
    I3.dir_labels(sys.modules[__name__], im, t)
    return im


def watermark(im):
    # 透かし（シリーズ共通：中央・64px・太さ800・白16%・全コマ同じ位置）。3D の場面にも入れる
    put(im, WATERMARK, WM_SIZE, WM_WEIGHT, WHITE, cx=540, cy=WM_CY, a=WM_A, kind='wm')


def frame(t, fast=False, wm=True):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    s = state_at(t)
    if t < I3.T_FIN:                      # 冒頭の3D
        im = I3.intro_frame(sys.modules[__name__], t, base_only=fast)
        draw_subtitle(im, t)
        if wm:
            watermark(im)
        return None if fast else im.convert('RGB')
    if fast:
        im_ = None
        if t >= INTRO_END - 0.3:          # 3D → 輪切りのあいだは、図の字はまだ出ていない
            draw_panel(im_, s, fast=True)
            draw_extra_notes(im_, s)
            draw_heart(im_, s, fast=True)
            draw_notes(im_, s)
        if t < INTRO_END:
            I3.view_icon(sys.modules[__name__], None, t)
            I3.dir_labels(sys.modules[__name__], None, t)
        draw_texts(im_, t, s)
        draw_subtitle(im_, t)
        watermark(im_)
        return None
    if t < INTRO_END:                     # 3D → 輪切りの図・12誘導
        im = fin_frame(t, s)
    else:
        im = _GRID.copy()
        im.alpha_composite(static_layer(s))
    draw_flash(im, t, s)
    draw_texts(im, t, s)
    draw_subtitle(im, t)
    lf = ramp(t, DUR - 0.5, 0.5)          # ループ：最後に冒頭の絵へもどる
    if lf > 0.004:
        im = Image.blend(im, I3.intro_frame(sys.modules[__name__], 0.0), lf)
    if wm:
        watermark(im)
    return im.convert('RGB')


# --- 検算 -------------------------------------------------------------------------
def _ov(a, b, m=2):
    return not (a[2] + m <= b[0] or b[2] + m <= a[0] or a[3] + m <= b[1] or b[3] + m <= a[1])


def check():
    global REC
    print(f'長さ {DUR:.2f} 秒（60fps で {int(round(DUR*60))} コマ）')
    print('\n[タイムライン] 名前が出ている区間（声は仮。1.2倍で読んで収まる長さ）')
    for a, b, i in WINDOWS:
        p = PATTERNS[i]
        print(f"  {p['no']} {p['name']:6s} {a:6.2f}–{b:6.2f}（{b - a:.2f}秒・読む長さ {SUB_LEAD + read_t(*_pat_texts(p)):.2f}）  看護の1行 {a + 1.6:6.2f}〜")
    print(f'  まとめ {SUM0:6.2f}–{SUM0 + SUM_HOLD:6.2f}・冒頭へもどる {DUR - LOOP_FADE:.2f}–{DUR:.2f}')
    per = [WINDOWS[k + 1][0] - WINDOWS[k][0] for k in range(N_PAT - 1)]
    print('  1パターンの間隔（名前が出る→次の名前が出る）：' + '・'.join(f'{x:.2f}' for x in per))

    print(f'\n[波形の高さ] 上下の段がぶつからないか（下の段の上向き＋上の段の下向き ≤ 段の間隔 {ROW_PITCH}px − 8）')
    bad = 0
    for key in list(range(N_PAT)) + ['N', 'S']:
        s = St(STATES[key])
        ext = {}
        for n in ALL_LEADS:
            v = beat(n, s.par(n), TAU)
            ext[n] = (v.max()*PXMV, -v.min()*PXMV)
            if ext[n][0] > ROW_UP - 4:
                print(f'  ！{key} {n} 上向き {ext[n][0]:.0f}px（段の上端まで {ROW_UP}px）'); bad += 1
        for c in range(4):
            for r in range(3):
                up_n = LAYOUT[r][c] if r < 3 else None
                lo_n = LAYOUT[r + 1][c] if r < 2 else [k for k, cc in EXTRA.items() if cc == c][0]
                tot = ext[up_n][1] + ext[lo_n][0]
                if tot > ROW_PITCH - 8:
                    print(f'  ！{key} {up_n}↓{ext[up_n][1]:.0f} + {lo_n}↑{ext[lo_n][0]:.0f} = {tot:.0f}px'); bad += 1
    print('  OK' if not bad else f'  {bad} か所')

    print('\n[字の幅] 看護の1行・名前の行（max 720px。右下のボタン x900 にかからない幅）')
    for p in PATTERNS:
        w1 = text_w(f"{p['no']} {p['name']}", 54, 900) + sum(14 + text_w(x[0], 38, 800) for x in vtxt_parts(p))
        w2 = text_w(p['nurse'], NURSE_SIZE, 800)
        print(f"  {p['no']} 名前＋血管 {w1:4d}px  看護 {w2:4d}px {'！' if max(w1, w2) > BOX_MAXW else ''}")

    print('\n[字幕] 文字・出ている長さ（読む長さ＝6.5文字/秒＋0.8秒）・幅（max 720px）')
    for txt, t0, t1, _ in SUBS:
        w_ = text_w(txt, SUB_SIZE, 800)
        print(f"  {t0:6.2f}–{t1:6.2f}（{t1 - t0:.2f}秒／読む {read_t(txt):.2f}）{w_:4d}px {'！幅' if w_ > BOX_MAXW else ''}{'！短い' if t1 - t0 < read_t(txt) - 0.05 else ''}  {txt}")
    print('\n[安全域・重なり] 0.1秒ごとに、出ている字の外枠を調べる')
    issues = {}
    n_frames = int(DUR/0.1) + 1
    for k in range(n_frames):
        t = k*0.1
        REC = []
        frame(t, fast=True)
        items = [r for r in REC if r[2] > 0.05]
        for s_, bb, a, kind, sz in items:
            if kind == 'wm':
                continue
            if bb[0] < SAFE_L or bb[2] > SAFE_R or bb[1] < SAFE_T or bb[3] > SAFE_B:
                issues.setdefault(('はみ出し', s_), []).append((t, bb))
            if bb[2] > IG_ZONE[0] and bb[3] > IG_ZONE[1] and bb[1] < IG_ZONE[3]:
                issues.setdefault(('右下のボタン', s_), []).append((t, bb))
            if sz < 18:
                issues.setdefault(('小さい字', s_), []).append((t, sz))
        for x in range(len(items)):
            for y in range(x + 1, len(items)):
                A, B = items[x], items[y]
                if A[3] == 'fade' and B[3] == 'fade':     # 同じ場所で入れ替わる字（向きの目印の字）
                    continue
                if _ov(A[1], B[1]):
                    key = ('重なり', A[0] + ' ／ ' + B[0])
                    issues.setdefault(key, []).append((t, A[1], B[1]))
    REC = None
    if not issues:
        print('  OK（はみ出し・右下・重なり・透かしの重なり なし）')
    for (kind, s_), v in issues.items():
        print(f'  ！{kind}：{s_}  {v[0][0]:.1f}〜{v[-1][0]:.1f}秒（{len(v)}コマ） {v[0][1:]}')
    wmb = None
    REC = []
    frame(0.0, fast=True)
    wmb = [r for r in REC if r[3] == 'wm'][0][1]
    REC = None
    print(f'\n透かしの外枠 {wmb}（中央 {(wmb[0] + wmb[2])/2:.0f}）')


# --- 確認用の静止画 ------------------------------------------------------------------
def sheet_times():
    w = {i: (a, b) for a, b, i in WINDOWS}
    return [('冒頭', 1.30), ('下壁', w[I_INF][0] + 3.0), ('右室', w[I_RV][0] + 3.0),
            ('後壁', w[N_PAT - 1][0] + 3.0), ('まとめ', SUM0 + 2.0)]


def make_sheet(out_dir, stamp=None):
    import subprocess
    os.makedirs(out_dir, exist_ok=True)
    ims = []
    for lab, t in sheet_times():
        im = frame(t)
        p = os.path.join(out_dir, f'still_{t:05.1f}.png')
        im.save(p); print(p, lab)
        ims.append((lab, t, im))
    sc = 0.42
    tw, th = int(W*sc), int(H*sc)
    pad, head = 16, 54
    sh = Image.new('RGB', (pad + len(ims)*(tw + pad), head + th + pad), (24, 28, 28))
    d = ImageDraw.Draw(sh)
    for k, (lab, t, im) in enumerate(ims):
        x = pad + k*(tw + pad)
        sh.paste(im.resize((tw, th), Image.LANCZOS), (x, head))
        d.text((x + 4, 12), f'{lab}  {t:.1f}秒', font=font(28, 700), fill=(230, 236, 234))
    p = os.path.join(out_dir, 'sheet_reel29.png')
    sh.save(p); print(p)
    if stamp is None:
        stamp = subprocess.run(['date', '+%m%d-%H%M'], capture_output=True, text=True,
                               env=dict(os.environ, TZ='Asia/Tokyo')).stdout.strip()
    send = os.path.join(out_dir, 'send', f'第29弾_心筋梗塞の場所_試作_{stamp}.png')
    os.makedirs(os.path.dirname(send), exist_ok=True)
    sh.save(send); print(send)


# --- 書き出し（第26弾と同じ：ffmpeg へパイプ、--jobs で分けて連結） -------------------------
def render_chunk(args):
    i0, i1, fps, path, crf, preset, scale = args
    I3.ensure_frames()
    vf = ['-vf', f'scale={scale[0]}:{scale[1]}:flags=lanczos'] if scale else []
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-'] + vf + ['-c:v', 'libx264', '-preset', preset,
           '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def _whoosh(n_len, sr, f_lo, f_hi, seed):
    """低いウーシュ：雑音を帯域で絞り、ふくらんで消える形にする。"""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n_len)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n_len, 1/sr)
    X *= np.exp(-0.5*((np.log(np.maximum(f, 1)) - np.log(math.sqrt(f_lo*f_hi)))/0.55)**2)
    y = np.fft.irfft(X, n_len)
    tt = np.arange(n_len)/n_len
    env = np.sin(np.pi*np.clip(tt, 0, 1))**1.6 * (0.6 + 0.4*tt)
    y = y*env
    return y / (np.abs(y).max() + 1e-9)


# --- ナレーション（2026-10-23 夜：でんさん「簡単につける」）。out/vo/lines/*.mp3（1.2倍済み）を字幕の出る時刻に置く ---
VO_DIR = os.path.join(HERE, 'out', 'vo', 'lines')
VO_DUCK_DB, VO_PEAK = 8.0, 0.75


def vo_starts():
    """声の話しはじめ（前の無音は除いて置く）。今の字幕の出る時刻に合わせる。"""
    st = {'n01': SUB_3D[0][1], 'n02': SUB_3D[1][1], 'n03': SUB_3D[2][1], 'n04': SUB_3D[3][1],
          'm1': SUM0 - 0.2, 'm2': SUM0 + SUM_A}
    for a, b, i in WINDOWS:
        st[f'p{i + 1}'] = a + SUB_LEAD
    return st


def _load_mp3(path, sr):
    raw = subprocess.run([ffmpeg_bin(), '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def vo_track(n, sr):
    if not os.path.isdir(VO_DIR):
        return None
    vo = np.zeros(n, np.float32)
    got = False
    for name, t0 in vo_starts().items():
        p = os.path.join(VO_DIR, name + '.mp3')
        if not os.path.exists(p):
            continue
        x = _load_mp3(p, sr)
        env = np.abs(x)
        thr = 0.03*env.max()
        nz = np.nonzero(env > thr)[0]
        if len(nz) == 0:
            continue
        x = x[max(0, nz[0] - int(0.03*sr)):]          # 前の無音を除く（30ms 残す）
        i0 = int(t0*sr)
        L = max(0, min(len(x), n - i0))
        vo[i0:i0 + L] += x[:L]
        got = True
        print(f'  声 {name}: {t0:6.2f}秒〜 {len(x)/sr:.2f}秒')
    if not got:
        return None
    return vo*VO_PEAK/(np.abs(vo).max() + 1e-9)


def sfx(path, sr=44100):
    """効果音：3D の寄り・回り込みに低いウーシュ、12誘導が出てからモニター音（75/分）。音量は第26弾と同じ（0.2）。"""
    import wave
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)

    def add(sig, t0, g):
        j = int(t0*sr)
        L = max(0, min(len(sig), n - j))
        a[j:j+L] += (g*sig[:L]).astype(np.float32)
    add(_whoosh(int(1.25*sr), sr, 90, 420, 1), I3.T0, 0.30)              # 全身 → 心臓へ寄る
    for k, (kind, src, t0, t1) in enumerate(I3.SEQ):
        if kind == 'orbit':
            add(_whoosh(int((t1 - t0 + 0.2)*sr), sr, 120, 520, 2 + k), t0 - 0.05, 0.16)
    add(_whoosh(int((I3.FIN_D + 0.2)*sr), sr, 100, 450, 9), I3.T_FIN - 0.05, 0.20)
    L = int(0.08*sr)
    tt = np.arange(L)/sr
    beep = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*960.0*tt)
    tb = INTRO_END - 0.10
    while tb < DUR - 0.6:
        add(beep, tb, 1.0)
        tb += 0.8
    # 輪切りの誘導に色がつく瞬間の音（点滅が始まる瞬間に1回。0.73秒で切って終わり30msをフェード、ピーク 0.22）。
    # 声のあいだはサイドチェインで下がる
    if os.path.exists(FLASH_SFX):
        fs = _load_mp3(FLASH_SFX, sr)[:int(0.73*sr)].copy()
        nf = int(0.03*sr)
        fs[-nf:] *= np.linspace(1, 0, nf)
        fs *= 1/(np.abs(fs).max() + 1e-9)
        for t0, _ in get_flashes():
            add(fs, t0, 0.22)                 # ピーク 0.22（0.45 から約 −6dB）
    vo = vo_track(n, sr)
    if vo is not None:
        # サイドチェイン（第26弾 align_vo.py と同じ）：声の大きさに合わせて、効果音を最大 8dB 下げる
        win_n = int(0.02*sr)
        env = np.sqrt(np.convolve(vo**2, np.ones(win_n)/win_n, mode='same'))
        env = env / (env.max() + 1e-9)
        act = np.clip(env / 0.08, 0, 1)
        att, rel = 1 - np.exp(-1/(0.02*sr)), 1 - np.exp(-1/(0.25*sr))
        sm = np.zeros_like(act); y = 0.0
        step = 64
        for j in range(0, n, step):
            x = act[j:j+step].max()
            k = att if x > y else rel
            y += (x - y)*(1 - (1 - k)**step)
            sm[j:j+step] = y
        gain = 1 - (1 - 10**(-VO_DUCK_DB/20))*sm
        a = vo*0.95 + a*gain
        pk = np.abs(a).max()
        if pk > 0.98:
            a *= 0.98/pk
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def export(fps, out, crf, preset, jobs, scale=None):
    I3.ensure_frames()
    total = int(round(DUR*fps))
    step = math.ceil(total / jobs)
    tmp = os.path.join(os.path.dirname(out), 'parts_' + os.path.splitext(os.path.basename(out))[0])
    os.makedirs(tmp, exist_ok=True)
    js = [(i, min(total, i + step), fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset, scale)
          for j, i in enumerate(range(0, total, step))]
    with Pool(jobs) as pool:
        parts = pool.map(render_chunk, js)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    wav = os.path.join(tmp, 'sfx.wav')
    sfx(wav)
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', out], check=True)
    print(out, f'{DUR:.2f}秒')


def thumbnail():
    """サムネイル（透かしなし）：「心筋梗塞の場所 6パターン」＋12誘導（④下壁の形）＋輪切り。"""
    w = {i: (a, b) for a, b, i in WINDOWS}
    t = w[1][0] + 3.0                     # ② 広範囲前壁（赤と青の両方が出る）
    s = state_at(t)
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()
    im.alpha_composite(static_layer(s))
    # 上の帯に大きな題
    d = ImageDraw.Draw(im, 'RGBA')
    d.rectangle([0, 0, W, 360], fill=BG + (255,))
    put(im, '心筋梗塞の場所', 104, 900, WHITE, cx=540, cy=180, max_w=820)
    put_parts(im, [('ST上昇の誘導で', 48, 800, YELLOW), ('6', 80, 900, YELLOW), ('パターン', 48, 800, YELLOW)], 300,
              max_w=820, gap=10)
    # 名前の行のかわりに大きく
    put_parts(im, [('② 広範囲前壁', 54, 900, WHITE), ('LADの根もと', 38, 800, C_LAD)], 430, gap=14)   # 説明の枠の位置（上の題と重ねない）
    return im.convert('RGB')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--preview', action='store_true', help='確認版（540×960・30fps・速い）：out/reel29_mi_preview.mp4')
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 11・slow）：out/reel29_mi_hq.mp4')
    ap.add_argument('--hq30', action='store_true', help='高画質（30fps・CRF 16・veryfast。急ぎ）：release/reel29_mi_hq.mp4')
    ap.add_argument('--render', action='store_true', help='通常版（1080×1920・60fps・CRF 18）：out/reel29_mi.mp4')
    ap.add_argument('--jobs', type=int, default=4)
    o = ap.parse_args()
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    if o.check:
        check(); return
    if o.sheet:
        make_sheet(out); return
    if o.thumb:
        p = os.path.join(out, 'reel29_mi_thumb.png')
        thumbnail().save(p); print(p); return
    if o.still:
        I3.ensure_frames()
        for t in o.still:
            p = os.path.join(out, f'still_{t:05.1f}.png')
            frame(t).save(p); print(p)
        return
    if o.preview:
        export(30, os.path.join(out, 'reel29_mi_preview.mp4'), 23, 'veryfast', o.jobs, scale=(540, 960)); return
    if o.hq30:
        os.makedirs(os.path.join(HERE, 'release'), exist_ok=True)
        export(30, os.path.join(HERE, 'release', 'reel29_mi_hq.mp4'), 16, 'veryfast', o.jobs); return
    if o.hq:
        export(60, os.path.join(out, 'reel29_mi_hq.mp4'), 11, 'slow', o.jobs); return
    if o.render:
        export(60, os.path.join(out, 'reel29_mi.mp4'), 18, 'medium', o.jobs); return
    ap.print_help()


if __name__ == '__main__':
    main()
