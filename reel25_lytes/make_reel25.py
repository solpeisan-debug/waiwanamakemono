"""第25弾 高カリウム血症とQT（電解質） まず覚えたい11パターン（第21弾と同じ作り＋この回だけの見せ方）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。高カリウムの進み方：基準 → テント状T → PR延長・P波平坦 → P波消失・徐脈
  → QRS幅の拡大 → サイン波）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと（うしろに、対応を色で）
- 下部：⑦〜⑪ のミニ波形（左の列に⑦⑧低K、右の列に⑨⑩QTが延びる（低Ca・薬剤など）、3段目のまん中に⑪QTが短い（高Ca））

この回だけの見せ方：
- 基準のゴースト：②〜⑪ の紹介中、中部の帯に①基準の拍を、同じR頂点の位置にうすく重ねる（どこが変わったか分かるように）
- 高Kの進み具合ゲージ：②〜⑥ のあいだ、左の余白に縦のゲージ（軽い → 重い）。Kの数値は書かない（段階とK値は一致しないため）
- 冒頭の問いかけ「この変化、気づける？」、最後の「何個わかった？コメントで教えてね」

波形は、パターンの周期でくり返す決まった形。区間の端は拍の間隔がくずれない位置で切る。
II誘導・実際の速さ（25mm/秒）を想定。基準の拍は 60/分（RR 1.0秒なので、QTc（Bazett）＝QT）。
数値の根拠：LITFL ECG Library（Hyperkalaemia, Hypokalaemia, Hypercalcaemia, Hypocalcaemia, QT Interval,
Digoxin Effect, U Wave）。画面の数値はモデルの波形から計算する（手打ちしない）。

使い方:
    python3 make_reel25.py              # 書き出し・60fps
    python3 make_reel25.py --still 20   # 1コマだけ
    python3 make_reel25.py --check      # 検算・タイミング表
    python3 make_reel25.py --thumb      # サムネイル（透かしなし）
"""
import argparse
import math
import os
import subprocess
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
SLOW = 1.0                        # 実際の速さ

BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (70, 82, 82)
CARD_FILL = (9, 19, 16)
CARD_EDGE = (60, 78, 72)
PURPLE = (178, 150, 240)
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)

C_BASE = (130, 232, 172)          # 基準
C_K1 = (255, 212, 90)             # 高K：はじめ（T波・P波の変化）
C_K2 = (255, 152, 72)             # 高K：進んだ（P波消失・徐脈・QRS幅の拡大）
C_K3 = (255, 92, 112)             # 高K：心停止の直前（サイン波）
C_LOWK = (110, 200, 255)          # 低K
C_LONG = (190, 160, 255)          # QTが延びる（低Ca・薬剤など）
C_SHORT = (255, 136, 204)         # QTが短い（高Ca）。基線の緑と見分けやすいピンク

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV。R頂点を 0 とする） --------------------------------
RR = 1.00                        # 基準の洞調律 60/分（前後の洞調律も同じ）


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def tent(t, c, a, w):
    """テント状のT波：高く、幅が狭く、左右対称で、先がとがる（頂点だけごくわずかに丸める）。"""
    x = np.sqrt((t - c)**2 + 0.005**2)
    return a*np.clip(1 - x/w, 0, 1)**1.6


def qrs_normal(t):                # 幅の狭いQRS（約80ms）
    return -0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011) - 0.20*_g(t, 0.028, 0.009)


def qrs_k1(t):                    # 高K：少し幅の広がったQRS（約100ms）
    return -0.06*_g(t, -0.036, 0.010) + 0.95*_g(t, 0.0, 0.014) - 0.24*_g(t, 0.036, 0.012)


def qrs_k2(t):                    # 高K：さらに広がったQRS（P波消失のころ）
    return -0.05*_g(t, -0.040, 0.012) + 0.90*_g(t, 0.0, 0.018) - 0.26*_g(t, 0.046, 0.016)


def qrs_k3(t):                    # 高K：幅が広く、形のくずれたQRS（Tとつながる）
    return 0.62*_ga(t, 0.0, 0.030, 0.045) - 0.30*_g(t, 0.105, 0.036)


def qrs_sine(t):                  # 高K：サイン波（QRSとTが1つのなめらかな波になる）
    return 0.62*_g(t, 0.0, 0.125) - 0.50*_g(t, 0.45, 0.125)


def st_sag(t, a, c, sl, sr):      # STの低下（なだらかに下がり、終わりで戻る）
    return -a*_ga(t, c, sl, sr)


class Beat:
    """1拍の部品。p=(P頂点の時刻, 高さ, 幅)、qrs・st・t・u は関数（R頂点からの時刻 → mV）。"""

    def __init__(self, p=None, qrs=qrs_normal, st=None, t=None, u=None, u_fused=False, wide=False):
        self.p, self.qrs, self.st, self.t, self.u = p, qrs, st, t, u
        self.u_fused = u_fused     # U波がT波とつながる（QTはQU間隔として測る）
        self.wide = wide           # 幅の広いQRS（モニター音を低く）

    def part(self, tau, *names):
        v = np.zeros_like(tau)
        for n in names:
            if n == 'p':
                if self.p is not None:
                    c, a, s = self.p
                    v = v + a*_g(tau, c, s)
            else:
                f = getattr(self, n)
                if f is not None:
                    v = v + f(tau)
        return v

    def __call__(self, tau):
        return self.part(tau, 'p', 'qrs', 'st', 't', 'u')


P_N = (-0.160, 0.15, 0.022)       # 洞調律のP波（PR 約170ms）
T_N = lambda t: 0.27*_ga(t, 0.270, 0.060, 0.042)                       # noqa: E731

KINDS = {
    # ① 基準の洞調律
    'N': Beat(p=P_N, t=T_N),
    # ② 高K：テント状T波（高く、幅が狭く、左右対称）。QRS・P波はまだ同じ
    'T1': Beat(p=P_N, t=lambda t: tent(t, 0.240, 0.82, 0.115)),
    # ③ 高K：P波が低く広がり（平坦）、PRが延びる。QRSも少し広がる
    'K2': Beat(p=(-0.250, 0.065, 0.032), qrs=qrs_k1, t=lambda t: tent(t, 0.255, 0.86, 0.120)),
    # ④ 高K：P波が消える。遅い（補充調律）。QRSはさらに広がる
    'K3': Beat(qrs=qrs_k2, t=lambda t: tent(t, 0.280, 0.86, 0.130), wide=True),
    # ⑤ 高K：幅が広く形のくずれたQRSが、Tとつながる
    'K4': Beat(qrs=qrs_k3, t=lambda t: tent(t, 0.320, 0.62, 0.165), wide=True),
    # ⑥ 高K：サイン波
    'SW': Beat(qrs=qrs_sine, wide=True),
    # ⑦ 低K：T波が低く平たい、わずかなST低下、T波のうしろにU波
    'L1': Beat(p=(-0.160, 0.17, 0.022), st=lambda t: st_sag(t, 0.035, 0.17, 0.06, 0.08),
               t=lambda t: 0.13*_ga(t, 0.270, 0.060, 0.045), u=lambda t: 0.11*_g(t, 0.470, 0.045)),
    # ⑧ 低K（高度）：P波が高く、PRが少し延び、ST低下、T波は平坦、U波がT波より大きい（T-U がつながる）
    'L2': Beat(p=(-0.185, 0.20, 0.022), st=lambda t: st_sag(t, 0.12, 0.20, 0.09, 0.07),
               t=lambda t: 0.035*_g(t, 0.280, 0.040), u=lambda t: 0.22*_ga(t, 0.460, 0.065, 0.050),
               u_fused=True),
    # ⑨ 低Ca：ST部分（平らな部分）が長い。T波の形は変わらない → QT延長
    'C1': Beat(p=P_N, t=lambda t: 0.27*_ga(t, 0.385, 0.048, 0.042)),
    # ⑩ 薬剤などのQT延長：T波が遅く、幅が広い（STの平らな部分は目立たない）
    'D1': Beat(p=P_N, t=lambda t: 0.21*_ga(t, 0.375, 0.110, 0.055)),
    # ⑪ 高Ca：STがほとんどなく、T波がQRSのすぐあと → QT短縮
    'C2': Beat(p=P_N, t=lambda t: 0.28*_ga(t, 0.170, 0.045, 0.038)),
}
WIN = (-0.50, 0.95)                # 1拍の部品がある範囲（R頂点からの秒）
ALL = [(-1e9, 1e9)]               # 全部をその色で

RR_K3, RR_K4, RR_SW = 1.40, 1.20, 0.90


def beats_every(rr, n, kind):
    return [(k*rr, kind) for k in range(n)]


def hl_beats(ev, a, b):
    """拍ごとに、R頂点から a〜b 秒を色で。"""
    return [(r + a, r + b) for r, _ in ev]


def _pat(no, name, col, hint, one, tag, rr, n, kind, hl):
    ev = beats_every(rr, n, kind)
    return dict(no=no, name=name, col=col, hint=hint, one=one, tag=tag, ev=ev, L=rr*n, rr=rr, kind=kind,
                hl=ALL if hl is ALL else hl_beats(ev, *hl))


# --- 計測（モデルの波形から） -----------------------------------------------------
_TT = np.arange(WIN[0], WIN[1], 0.0005)


def qrs_on_off(b):
    q = b.part(_TT, 'qrs')
    m = (np.abs(q) > 0.05) & (_TT > -0.15) & (_TT < 0.20)
    return _TT[m].min(), _TT[m].max()


def pr_ms(b):
    """PR間隔（P波の始まり → QRSの始まり）。P波の始まりは頂点の 5% の高さ。"""
    if b.p is None:
        return None
    c, a, s = b.p
    return (qrs_on_off(b)[0] - (c - s*math.sqrt(2*math.log(20)))) * 1000


def qrs_ms(b):
    on, off = qrs_on_off(b)
    return (off - on) * 1000


def t_end(b):
    """T波の終わり：最大の下り勾配の接線と基線の交点（LITFL QT Interval：maximum slope intercept method）。
    U波がT波とつながる（u_fused）ときは U波まで含める（QU間隔）。"""
    parts = ('st', 't', 'u') if b.u_fused else ('st', 't')
    v = b.part(_TT, *parts)
    sel = _TT > qrs_on_off(b)[1]
    tt, vv = _TT[sel], v[sel]
    k = int(np.argmax(vv))                       # いちばん高い波（T、または U）の頂点
    dv = np.gradient(vv, tt)
    j = k + int(np.argmin(dv[k:]))               # その後の、いちばん急な下り
    return tt[j] - vv[j]/dv[j]


def qt_ms(b):
    return (t_end(b) - qrs_on_off(b)[0]) * 1000


def qtc_ms(b, rr):
    return qt_ms(b) / math.sqrt(rr)               # Bazett


def r10(x):
    return int(round(x / 10.0) * 10)


_B = KINDS
QT_N = r10(qt_ms(_B['N']))
PR_K2 = r10(pr_ms(_B['K2']))
QTC_C1 = r10(qtc_ms(_B['C1'], RR))
QTC_D1 = r10(qtc_ms(_B['D1'], RR))
QTC_C2 = r10(qtc_ms(_B['C2'], RR))

# 11パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、色を付ける範囲 hl
PATTERNS = [
    _pat('①', '洞調律（基準）', C_BASE, 'くらべる基準',
         f'QT {QT_N}ms。RRの半分より短い', 'base', RR, 4, 'N', ALL),
    _pat('②', '高K：テント状T波', C_K1, 'T波がとがる',
         'T波が高く、細く、左右対称', 'report', RR, 4, 'T1', (0.09, 0.40)),
    _pat('③', '高K：PR延長・P波平坦', C_K1, 'P波が平たい',
         f'P波が低く平たい。PR {PR_K2}ms', 'report', RR, 4, 'K2', (-0.36, -0.04)),
    _pat('④', '高K：P波消失・徐脈', C_K2, 'P波なし・遅い',
         f'P波が見えない。{60/RR_K3:.0f}/分と遅い', 'report', RR_K3, 3, 'K3', ALL),
    _pat('⑤', '高K：QRS幅の拡大', C_K2, '幅広いQRS',
         'QRSが幅広く、Tとつながる', 'report', RR_K4, 4, 'K4', ALL),
    _pat('⑥', '高K：サイン波', C_K3, 'なめらかな波',
         'QRSとTが溶け合い、波打つ', 'arrest', RR_SW, 5, 'SW', ALL),
    _pat('⑦', '低K：T波平低・U波', C_LOWK, 'U波が出る',
         'T波が低く、うしろにU波', 'lab', RR, 5, 'L1', (0.36, 0.60)),
    _pat('⑧', '低K（高度）', C_LOWK, 'ST低下・大きなU',
         'STが下がり、U波がTより大きい', 'report', RR, 4, 'L2', (0.05, 0.62)),
    _pat('⑨', '低Ca：ST延長', C_LONG, 'STが長い',
         f'STが長い。QTc {QTC_C1}ms', 'lab', RR, 5, 'C1', (0.05, 0.50)),
    _pat('⑩', 'QT延長（薬剤など）', C_LONG, 'T波が遅く広い',
         f'T波が遅く広い。QTc {QTC_D1}ms', 'qtc', RR, 4, 'D1', (0.06, 0.55)),
    _pat('⑪', '高Ca：QT短縮', C_SHORT, 'STがほぼない',
         f'STがほぼない。QTc {QTC_C2}ms', 'lab', RR, 4, 'C2', (0.04, 0.30)),
]

N_PAT = len(PATTERNS)
for _p in PATTERNS:
    _p['beats'] = _p['ev']

# 区間の長さ（秒）。仮の値（録音前）：台本の各文の長さの見込み（6字/秒くらい）＋0.75秒以上で、
# 拍の並びがくずれない位置（そのパターンの拍の間隔の倍数。次のパターンの最初の拍まで、そのパターンの間隔）で切る。
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {'①': 4.0, '②': 4.0, '③': 4.0, '④': 4.2, '⑤': 4.8, '⑥': 4.5,
         '⑦': 5.0, '⑧': 4.0, '⑨': 5.0, '⑩': 4.0, '⑪': 4.0}
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    assert _p['D'] >= 3.44 - 1e-9, _p['no']
    _n = _p['D'] / _p['rr']
    assert abs(_n - round(_n)) < 1e-6, f"{_p['no']} 区間が拍の間隔の倍数でない"


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        m = (tau - r > WIN[0]) & (tau - r < WIN[1])
        if m.any():
            v[m] += KINDS[k](tau[m] - r)
    return v


def periodic_beats(pat, t0, t1):
    out = []
    L = pat['L']
    k0 = int(math.floor(t0 / L)) - 1
    k1 = int(math.ceil(t1 / L)) + 1
    for k in range(k0, k1):
        for r, kind in pat['ev']:
            out.append((k*L + r, kind))
    return out


def hl_mask(pat, rel):
    """周期の中の色を付ける範囲（rel は区間の始まりからの時刻）。"""
    L = pat['L']
    r = np.mod(rel, L)
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-L, 0.0, L):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


# --- 中部の帯：11パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンをくり返して置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 5.2                     # 冒頭の1文（仮 5.2秒：「高カリウム血症とQT。まず覚えたいのは、この11パターン。」）
END_HOLD = 7.2                    # 11個そろってからの時間（まとめ・保存の2文、「何個わかった？」を読む時間と、冒頭へ戻る時間）
HOOK = [1, 3, 5, 7, 9]            # ②テント状T → ④P波消失 → ⑥サイン波 → ⑧低K（高度）→ ⑩QT延長
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < pat['D'] - 1e-9:
                beats.append((t + r, kind, i))
        t += pat['D']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -12:                     # 前：洞調律
        beats.append((k*RR, 'N', None)); k -= 1
    # うしろ：洞調律（間隔は変えない）。尺は「最後の2文が入る長さ」以上で、
    # うしろの洞調律の位相が冒頭とそろういちばん短い長さにする。こうするとループがつながる
    need = T_TITLE + end - HANDOFF_EARLY + 0.8 + END_HOLD      # 0.8 = FLY
    k = math.ceil((need - FREEZE - end) / RR - 1e-9)
    dur_target = FREEZE + end + k*RR
    tt = end
    beats.append((tt, 'N', None))
    for k in range(1, 60):
        tt += RR
        beats.append((tt, 'N', None))
    beats.sort(key=lambda b: b[0])
    return beats, segs, end, dur_target


HANDOFF_EARLY = 0.35
STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.4mV）
_TOP_END = 636 + 110               # ③⑥の下端
_BOT_TOP = 1182                    # ⑦⑨の上端（注記と⑪の枠のあいだを空ける）
# 見た目の上端（名前の字の上）〜下端（約0.4mV 下）で余白をそろえる
_MID_H = 22 + 54 + 16 + 30 + 140 + 36
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + 16 + 30 + 140
F_Y0, F_Y1 = int(F_BASE - 200), int(_BOT_TOP - 2)
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# t=T_TITLE で、パターン①の区間の始まりが画面の右端に来る（止まっていた時間を引く）
OFFSET = -HALF - (T_TITLE - FREEZE) / SLOW


def te(t):
    """波形の時計：T_STOP〜T_GO は止まる。"""
    if t < T_STOP:
        return t
    if t < T_GO:
        return T_STOP
    return t - FREEZE


def tau_c(t):
    """画面の中央にある実際の時刻。"""
    return te(t) / SLOW + OFFSET


def t_of(tau_center):
    """その時刻が画面の中央に来る t（止まっているあいだは除く）。"""
    t = (tau_center - OFFSET) * SLOW
    return t if t < T_STOP else t + FREEZE


WINDOWS = []
for _i in range(len(PATTERNS)):
    _a = T_TITLE if _i == 0 else WINDOWS[-1][1]
    # 区間の終わりが右端の少し先（0.35秒）に来た瞬間。次のパターンの最初のP波が
    # 右端に入る前に縮み始めるので、見えているのはパターン i だけになる
    _b = t_of(SEGS[_i][1] - HALF - HANDOFF_EARLY)
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60
DUR = round(_DUR_LOOP * FPS_LOOP) / FPS_LOOP


# --- ミニ波形の枠 -----------------------------------------------------------------
CELL_W, CELL_H = 400, 110
COL_X = (130, 550)
TOP_Y = [396, 516, 636]
BOT_Y = [1182, 1302, 1422]
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える）
M_MV = 33.0


def cell_rect(i):
    if i < 6:
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
    elif i < 10:                       # ⑦⑧は左の列、⑨⑩は右の列（2段）
        j = i - 6
        col, row = j // 2, j % 2
        x, y = COL_X[col], BOT_Y[row]
    else:                              # ⑪は3段目のまん中（空きが左右に片寄らないように）
        x, y = (W - CELL_W) // 2, BOT_Y[2]
    return (x, y, x + CELL_W, y + CELL_H)


# --- 道具 ---------------------------------------------------------------------
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(u):
    u = cl(u)
    return u*u*(3-2*u)


def ramp(t, t0, d=0.5):
    return ease((t - t0) / d)


def mix(a, b, u):
    return tuple(int(round(a[i] + (b[i]-a[i])*u)) for i in range(3))


_FONTS, _TXT = {}, {}


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
    _TXT[k] = (im, asc)
    return _TXT[k]


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None):
    if a <= 0.004:
        return
    im, asc = text_img(s, size, weight, col, max_w)
    if a < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel('A').point(lambda v: int(v*a)))
    w, h = im.size
    if right is not None:
        px = int(right - w + 4)
    elif x is not None:
        px = int(x - 4)
    else:
        px = int(cx - w/2)
    py = int(cy - 4 - asc*0.62)
    base.alpha_composite(im, (px, py))


def grid():
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = 31.5
    for i in range(int(W/pm) + 2):
        x = round(i*pm)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,),
               width=2 if i % 5 == 0 else 1)
    for k in range(int(H/pm) + 2):
        y = round(k*pm)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    return im


# --- 中部の波形 --------------------------------------------------------------------
SS = 2


def strip_colors(tau):
    """パターンの区間のうち、色を付ける範囲だけそのパターンの色。"""
    cid = np.full(len(tau), -1, dtype=int)
    for i, (s0, s1) in enumerate(SEGS):
        inside = (tau >= s0 - 0.35) & (tau < s1 + 0.0)
        if not inside.any():
            continue
        m = inside & hl_mask(PATTERNS[i], tau - s0)
        if PATTERNS[i]['hl'] is ALL:
            # 区間の前後を 0.22秒ずらす（次のパターンの最初のP波・QRSに色が乗らないように。
            # 全部に色を付けるパターンどうしのつなぎ目に、すき間ができないように）
            m = (tau >= s0 - 0.22) & (tau < s1 - 0.22)
        cid[m] = i
    return cid


def glow_line(size, runs, col, width, a, blur=(8, 20)):
    """runs: 点列のリスト。グロー付きの線を RGBA で返す。"""
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
        g = np.maximum(g1*0.95, g2*0.5)
        lay = Image.new('RGBA', (w, h), col + (0,))
        lay.putalpha(Image.fromarray(np.clip(g*a, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), 0.6) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


FX = np.arange(0, W + 1, 0.5)


def strip_arrays(tau_center):
    """中部の帯：(波形, 色の番号)"""
    tau = tau_center + (FX - XC) / F_PXS
    return wave_from(STRIP, tau), strip_colors(tau)


def hook_arrays(i):
    """フック用：パターン i の、色の付いた範囲が中央の少し左に来る一場面。"""
    pat = PATTERNS[i]
    if pat['hl'] is ALL:
        c = pat['L'] / 2
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2 + 0.25
    rel = c + (FX - XC) / F_PXS + pat['L']
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    cid = np.where(hl_mask(pat, rel) | (pat['hl'] is ALL), i, -1)
    return v, cid


_HOOK = {}


def hook_targets():
    if not _HOOK:
        _HOOK['seq'] = [strip_arrays(tau_c(T_STOP))] + [hook_arrays(i) for i in HOOK] \
            + [strip_arrays(tau_c(T_STOP))]
    return _HOOK['seq']


def hook_state(t):
    """止まっているあいだの (変形の前, 後, 進み具合, 表示中のパターン)。"""
    seq = hook_targets()
    times = [HOOK_T0 + k*HOOK_STEP for k in range(len(HOOK))] + [HOOK_T0 + len(HOOK)*HOOK_STEP]
    k = -1
    for n, tk in enumerate(times):
        if t >= tk:
            k = n
    if k < 0:
        return seq[0], seq[0], 1.0, None
    u = ease((t - times[k]) / HOOK_MORPH)
    shown = HOOK[k] if k < len(HOOK) else None
    return seq[k], seq[k + 1], u, shown


def draw_wave(v, cid, base_col, a):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(set(np.unique(cid).tolist())):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


SINE_I = 5                         # ⑥サイン波：ゴーストのとがったQRSがサイン波を突き抜けて誤解を招くので、出さない
GHOST_COL = (226, 236, 236)        # 基準のゴースト：白っぽく、うすく、細く（主役の波形より目立たない）
GHOST_A = 0.40
GHOST_W = 2.6


def ghost_alpha(t):
    """ゴーストを出す濃さ（0〜1）：②から最後のパターンまで。⑥のあいだは 0。"""
    a = ramp(t, WINDOWS[1][0], 0.4) * (1 - ramp(t, T_END + FLY - 0.4, 0.4))
    a6, b6 = WINDOWS[SINE_I]
    return a * (1 - ramp(t, a6, 0.3) * (1 - ramp(t, b6, 0.3)))


def ghost_arrays(tau_center, cur):
    """パターン cur の拍と同じR頂点の位置に置いた、①基準の拍。cur の区間の中だけ（mask）。"""
    tau = tau_center + (FX - XC) / F_PXS
    s0, s1 = SEGS[cur]
    gb = [(r, 'N') for r, k, i in STRIP if i == cur]
    return wave_from(gb, tau), (tau >= s0 - 0.30) & (tau < s1)


def draw_ghost(v, m, a):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    idx = np.where(m)[0]
    runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
    return glow_line((W, h), runs, GHOST_COL, GHOST_W, a*GHOST_A, blur=(3, 7))


def featured(t, base_col, a, cur=None):
    """中部の帯。色を付けるのは、いま紹介中のパターン cur の拍だけ（前のパターンの色つきの波形が、
    新しい名前の下に残らないように。ほかはふつうの緑）。冒頭のフックは変形中のパターンの色。"""
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a)
    v, cid = strip_arrays(tau_c(t))
    cid = np.where(cid == (-2 if cur is None else cur), cid, -1)
    out = draw_wave(v, cid, base_col, a)
    if cur is not None and cur >= 1 and cur != SINE_I:   # ②〜⑪（⑥サイン波は除く）：①基準をうすく下に重ねる
        lay = draw_ghost(*ghost_arrays(tau_c(t), cur), a)
        lay.alpha_composite(out)
        out = lay
    return out


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 76, 50     # ミニ波形の帯（枠の中）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30 + {4: -4, 5: -9}.get(i, 0)     # ⑤⑥は下に深い波なので、枠のまん中に来るよう少し上げる


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0):
    """パターン i をくり返した波形を、画面の x_lo〜x_hi に描いた RGBA（全画面サイズの一部）。
    中央 cx に来る時刻は tau_c(t)（中部の帯と同じ）。区間の始まりからの相対時刻で周期にする。"""
    pat = PATTERNS[i]
    s0 = SEGS[i][0]
    xs = np.arange(x_lo, x_hi + 0.5, 0.5)
    tau = tau_c(t) + (xs - cx) / pxs
    rel = tau - s0
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    ys = base_y - v*mv
    ect = np.ones(len(xs), dtype=bool) if pat['hl'] is ALL else hl_mask(pat, rel)
    y_lo = int(min(ys.min(), base_y - 1.1*mv) - 30)
    y_hi = int(max(ys.max(), base_y + 0.9*mv) + 30)
    bx0, by0 = int(x_lo) - 30, y_lo
    size = (int(x_hi - x_lo) + 60, max(4, y_hi - y_lo))
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)
                if not (flag and len(r) <= 12 and (r[0] <= 1 or r[-1] >= len(xs) - 2))] if len(idx) else []
        # ↑ 色を付けた部分が帯の端で 6px 以下（0.5px きざみで 12点）しか見えないときは描かない（端に色の点が残らないように）
        w_, a_ = ((lw_e or lw) if flag else lw), (a if flag else a*a_norm)
        if runs:
            out.alpha_composite(glow_line(size, runs, col, w_, a_, blur=blur))
    return out, (bx0, by0)


def lerp(a, b, u):
    return a + (b - a)*u


def view_params(i, u):
    """u=0 で中部の帯、u=1 で枠のミニ波形。"""
    ox, oy = cell_strip_origin(i)
    cx = lerp(XC, ox + STRIP_W/2, u)
    base_y = lerp(F_BASE, oy + STRIP_BASE, u)
    pxs = F_PXS*(M_PXS/F_PXS)**u
    mv = F_MV*(M_MV/F_MV)**u
    half = lerp(XC, STRIP_W/2, u)
    lw = lerp(4.5, 2.2, u)
    b1 = lerp(8, 3, u); b2 = lerp(20, 7, u)
    return cx, base_y, pxs, mv, cx - half, cx + half, lw, (b1, b2)


MINI_LW_ECT = 3.8                  # ミニ波形で、色を付けた部分の線の太さ（ふつうの部分は 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、ふつうの部分の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u))
    base.alpha_composite(im, pos)


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。番号とヒント）/'now'（紹介中）/'done'（ミニ波形あり）"""
    x0, y0, x1, y1 = cell_rect(i)
    pat = PATTERNS[i]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a_fill = a_all                          # 枠の中の塗り：方眼が透けすぎないよう、薄くする対象から外す
    if state in ('empty', 'now'):
        a_all = a_all * 0.5                 # ミニ波形がないものは、枠線と文字だけ薄く
    if state in ('now', 'landing'):
        pulse = 0.55 + 0.45*math.sin(t*5.0)**2
        if state == 'now':
            pulse = min(1.0, pulse*1.6)
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=pat['col'] + (int(255*pulse*a_all),), width=3)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=CARD_EDGE + (int(255*a_all),), width=2)
    base.alpha_composite(lay)
    if state in ('done', 'landing'):
        name = f"{pat['no']} {pat['name']}"
        put(base, name, 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17, a=a_all, max_w=CELL_W - 30)
        if i == 0:                           # ゴーストを出しているあいだ、①の名前のうしろに「＝うすい線」
            a_g = ghost_alpha(t)
            nw = text_img(name, 22, 700, pat['col'], max_w=CELL_W - 30)[0].size[0] - 8
            put(base, '＝下のうすい線', 22, 700, GHOST_COL, x=x0 + 14 + nw + 4, cy=y0 + 17, a=a_all*a_g*0.85)
    elif state == 'now':
        put(base, pat['no'], 30, 700, pat['col'], x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2))
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=CELL_W - 80)


# --- 画面 ---------------------------------------------------------------------------
TITLE = '高カリウム血症とQT'
HEADER = [(TITLE, 1.0, WHITE), (str(N_PAT), 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
HEADER_BASE = 372                   # 見出しのベースライン（y）
NOTE1 = '実際の速さ（基準の拍は60/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'
END_LINE = '高カリウムは、軽く見えても急変しうる'
SAVE_LINE = '保存して見返してね'
COMMENT_LINE = '何個わかった？コメントで教えてね'
HOOK_Q = 'この変化、気づける？'
HOOK_Q_Y, HOOK_NAME_Y = 433, 841       # 冒頭：問いかけ・変形中のパターン名（上から下まで間隔をそろえる）
END_Y = (Y_NAME - 40, Y_NAME + 6, Y_NAME + 48)   # 最後の3行（上の枠・下の波形との余白をそろえる）
GHOST_LEGEND = 'うすい線＝①基準'
LEGEND_Y = 1150


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「高カリウム血症とQT」＋大きな黄色の「11」＋「パターン」。左右の余白（130px）に収める。"""
    if a <= 0.004:
        return
    size = 46
    while True:
        parts = [text_img(sx, int(size*k), 800, col) for sx, k, col in HEADER]
        widths = [im.size[0] - 8 for im, _ in parts]
        total = sum(widths) + 6*(len(parts) - 1)
        if total <= W - 2*130 - 10 or size <= 24:
            break
        size -= 1
    x = (W - total) / 2
    for (im, asc), w in zip(parts, widths):
        if a < 0.999:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda q: int(q*a)))
        base.alpha_composite(im, (int(x - 4), int(HEADER_BASE - 4 - asc)))
        x += w + 6


_GRID = None


# ひとことのうしろに、看護師がすることを色で
ONE_W = 760                         # ひとこと＋色の文字の幅の上限（左右に 160px 以上の余白。端で切れて見えないように）
TAGS = {
    'base': ('→ くらべる基準', (130, 232, 172)),
    'report': ('→ すぐ報告', (255, 196, 64)),
    'arrest': ('→ 心停止に備える', (255, 96, 96)),
    'lab': ('→ 採血の値も確認', (110, 200, 255)),
    'qtc': ('→ 12誘導でQTc確認', (196, 170, 255)),
}


def draw_one(im, pat, a):
    """中部のひとこと。うしろに色の文字（TAGS）を続けて、まとめて中央ぞろえ。"""
    tag = TAGS.get(pat.get('tag'))
    if tag is None:
        put(im, pat['one'], 32, 500, (226, 232, 231), cx=540, cy=Y_ONE, a=a, max_w=820)
        return
    sz = one_size(pat)
    w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
    w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
    x0 = 540 - (w1 + 14 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=Y_ONE, a=a)
    put(im, tag[0], sz, 800, tag[1], x=x0 + w1 + 14, cy=Y_ONE, a=a)


def one_size(pat):
    """ひとこと＋色の文字が ONE_W に入る字の大きさ（32px から小さくする）。"""
    tag = TAGS[pat['tag']]
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        if w1 + 14 + w2 <= ONE_W or sz <= 24:
            return sz
        sz -= 1


# 高Kの進み具合ゲージ（②〜⑥）。左の余白（ミニ波形の枠の左、x 72〜128）に縦に。Kの数値は書かない
GAUGE_X, GAUGE_W = 96, 16
GAUGE_Y0, GAUGE_Y1 = 420, 722          # 上（重い）〜 下（軽い）
K_STAGES = [1, 2, 3, 4, 5]             # ②〜⑥ のパターン番号（0始まり）


def gauge_level(t):
    """(高さ 0〜1, 色)。段階が進むごとに 1/5 ずつ上がる（名前が出るのと同時に 0.6秒で）。"""
    lev, col = 0.0, PATTERNS[K_STAGES[0]]['col']
    for n, i in enumerate(K_STAGES, 1):
        a_i = WINDOWS[i][0] + 0.5
        if t >= a_i:
            lev = (n - 1 + ease((t - a_i) / 0.6)) / len(K_STAGES)
            col = PATTERNS[i]['col']
    return lev, col


def draw_gauge(im, t, a):
    if a <= 0.004:
        return
    lev, col = gauge_level(t)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, x1 = GAUGE_X - GAUGE_W/2, GAUGE_X + GAUGE_W/2
    d.rounded_rectangle((x0, GAUGE_Y0, x1, GAUGE_Y1), radius=8, fill=CARD_FILL + (int(230*a),),
                        outline=CARD_EDGE + (int(255*a),), width=2)
    if lev > 0.005:
        yf = GAUGE_Y1 - lev*(GAUGE_Y1 - GAUGE_Y0)
        d.rounded_rectangle((x0 + 3, yf + 3, x1 - 3, GAUGE_Y1 - 3), radius=5, fill=col + (int(255*a),))
    for k in range(1, len(K_STAGES)):        # 段階の目盛り
        y = GAUGE_Y1 - k*(GAUGE_Y1 - GAUGE_Y0)/len(K_STAGES)
        d.line([(x0 - 5, y), (x0 - 1, y)], fill=CARD_EDGE + (int(255*a),), width=2)
    if lev > 0.999:                          # ⑥：いちばん上で、赤く光る
        glow = lay.filter(ImageFilter.GaussianBlur(6))
        im.alpha_composite(glow)
    im.alpha_composite(lay)
    put(im, '高K', 21, 800, C_K1, cx=GAUGE_X, cy=GAUGE_Y0 - 54, a=a)
    put(im, '重い', 20, 700, C_K3 if lev > 0.999 else GREY, cx=GAUGE_X, cy=GAUGE_Y0 - 22, a=a)
    put(im, '軽い', 20, 700, GREY, cx=GAUGE_X, cy=GAUGE_Y1 + 24, a=a)


def frame(t):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    a_loop = ramp(t, DUR - LOOP_FADE - 0.05, LOOP_FADE - 0.05)   # 1 で冒頭と同じ画面
    keep = 1 - a_loop
    draw_header(im, ramp(t, 2.5, 0.5)*keep)

    a_cells = ramp(t, T_GO - 0.3, 0.6)*keep
    cur = current(t)
    flying = None
    for i in range(N_PAT):
        a_i, b_i = WINDOWS[i]
        if t >= b_i + FLY:
            st = 'done'
        elif b_i <= t < b_i + FLY:
            st = 'landing'
        elif cur == i:
            st = 'now'
        else:
            st = 'empty'
        if b_i <= t < b_i + FLY:
            flying = i
        draw_cell(im, i, t, st, a_cells)
        if st == 'done':
            mini(im, i, t, 1.0, a=keep)

    # 中部：紹介中の名前とひとこと
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        # 名前とひとことは、前のパターンの波形が縮んで枠へ移り、字の上を通りすぎてから出す（0.5秒）。
        # ①は前に縮む波形がなく、声もすぐ始まるので 0.1秒
        al = ramp(t, a_i + (0.1 if cur == 0 else 0.5), 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=al, max_w=820)
        draw_one(im, pat, al)

    # ②③のあいだ、帯の下に「うすい線＝①基準」
    a_leg = ramp(t, WINDOWS[1][0] + 0.5, 0.3) * (1 - ramp(t, WINDOWS[2][1] - 0.25, 0.25)) * keep
    put(im, GHOST_LEGEND, 24, 700, GHOST_COL, x=135, cy=LEGEND_Y, a=a_leg*0.9)

    # 高Kの進み具合ゲージ：②の名前が出るころから、⑥が縮んで枠に入るまで
    draw_gauge(im, t, ramp(t, WINDOWS[1][0] + 0.3, 0.4) * (1 - ramp(t, WINDOWS[5][1] + 0.3, 0.5)) * keep)

    # 冒頭：問いかけ・タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        put(im, HOOK_Q, 76, 900, (255, 214, 64), cx=540, cy=HOOK_Q_Y, a=a_t, max_w=880)
        put(im, '心電図で気づく電解質', 36, 500, PURPLE, cx=540, cy=560, a=a_t)
        put(im, TITLE, 150, 900, WHITE, cx=540, cy=690, a=a_t, max_w=880)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=HOOK_NAME_Y,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, END_LINE, 38, 800, WHITE, cx=540, cy=END_Y[0], a=a_end, max_w=820)
        put(im, SAVE_LINE, 30, 700, GREEN, cx=540, cy=END_Y[1],
            a=ramp(t, T_END + FLY + 1.8, 0.6)*keep)
        put(im, COMMENT_LINE, 30, 700, (255, 214, 64), cx=540, cy=END_Y[2],
            a=ramp(t, T_END + FLY + 2.4, 0.6)*keep)

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a_strip = min(a_strip, ramp(t, b_i + FLY - 0.1, 0.45))
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    if a_strip > 0.01:
        im.alpha_composite(featured(t, base_col, a_strip, cur), (0, F_Y0))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=1561, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=1588, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


def thumbnail():
    """サムネイル（透かしなし）。11個そろった一覧（上下の枠）のあいだに、問いかけの一文・大きなタイトルと、
    ②テント状T波の波形（中部の帯の大きさ、T波を色で）。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    global _GRID
    if _GRID is None:
        _GRID = grid()
    t = T_END + FLY + 2.0
    im = _GRID.copy()
    draw_header(im, 1.0)
    for i in range(N_PAT):
        draw_cell(im, i, t, 'done', 1.0)
        mini(im, i, t, 1.0)
    put(im, 'その波形の変化、電解質かも？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 38, max_w=820)
    put(im, TITLE, 96, 900, WHITE, cx=540, cy=Y_ONE + 4, max_w=880)
    v, cid = hook_arrays(1)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0)
    im.alpha_composite(wl, (0, F_Y0 + 50))      # タイトルの下・枠の上の余白がそろう位置（約30pxずつ）
    return im.convert('RGB')


# --- 一覧型のサムネイル（第17弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {i: (-0.45, []) for i in range(N_PAT)}
THUMB_VIEW[1] = (-0.45, [(0.10, 0.39)])                  # テント状T
THUMB_VIEW[2] = (-0.45, [(-0.34, -0.12)])                # 平たいP波
THUMB_VIEW[6] = (-0.45, [(0.38, 0.56)])                  # U波
THUMB_VIEW[7] = (-0.45, [(0.06, 0.58)])                  # ST低下と大きなU
THUMB_VIEW[8] = (-0.45, [(0.05, 0.47)])                  # 長いST
THUMB_VIEW[10] = (-0.45, [(0.04, 0.27)])                 # 短いST-T
THUMB_MAX_MARKS = {}
THUMB_DESC = ['くらべる基準', 'Tがとがる', '', '遅い', '幅広いQRS', '波打つ',
              'U波が出る', 'ST低下・大きなU', 'STが長い', 'Tが遅い', 'STがほぼない']


def dashed_ellipse(d, box, col, dash=6, gap=5, width=2):
    """点線の楕円。"""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1)/2, (y0 + y1)/2, (x1 - x0)/2, (y1 - y0)/2
    th = np.linspace(0, 2*np.pi, 721)
    pts = np.stack([cx + rx*np.cos(th), cy + ry*np.sin(th)], 1)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    idx = np.where((seg % (dash + gap)) < dash)[0]
    for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1):
        if len(r) >= 2:
            d.line([tuple(q) for q in pts[r]], fill=col + (255,), width=width)


def thumb_row_wave(i, x0, x1, base_y, mv, span=4.0):
    """パターン i を1本の色で描き、特徴のところを点線の丸で囲む（サムネイル用）。"""
    pat = PATTERNS[i]
    pxs = (x1 - x0) / span
    t0, marks = THUMB_VIEW[i]
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = t0 + (xs - x0) / pxs
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    v = v * np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(3.2*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.7*mv) - pad
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], pat['col'], 2.8, 1.0, blur=(4, 10))
    d = ImageDraw.Draw(lay)
    n_max, n = THUMB_MAX_MARKS.get(i, 2), 0
    for r, _ in sorted(bl):
        for a, b in marks:
            lo, hi = r + a, r + b
            if lo < rel[0] + 0.05 or hi > rel[-1] - 0.05 or n >= n_max:
                continue
            n += 1
            sel = (rel >= lo) & (rel <= hi)
            bx0, bx1 = x0 + (lo - t0)*pxs - 4, x0 + (hi - t0)*pxs + 4
            by0 = min(ys[sel].min() - 9, base_y - 0.45*mv)
            by1 = max(ys[sel].max() + 9, base_y + 0.35*mv)
            dashed_ellipse(d, (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy), pat['col'])
    return lay, (ox, oy)


def thumbnail_list():
    """サムネイル（透かしなし）。第17弾の一覧型と同じ作り：
    タイトル → 11パターンを2列（左：①〜⑥の6段、右：⑦〜⑪の5段。列の高さはそろえる）
    （色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく電解質', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, TITLE, 112, 900, WHITE, cx=540, cy=436, max_w=880)
    put(im, '見分けられる？', 60, 900, YEL, cx=540, cy=546)
    COLS = [(135, 515), (565, 945)]             # 列のあいだは50px あける（線は引かない）
    NRS = [6, N_PAT - 6]                        # 列ごとの段の数（左：高Kの道 ①〜⑥、右：⑦〜⑪）
    Y0, RH = 628, 852 // 6
    TOT = RH*6                                  # 2列とも同じ高さに収める
    for i, pat in enumerate(PATTERNS):
        c = 0 if i < 6 else 1
        r = i if c == 0 else i - 6
        rh = TOT / NRS[c]
        x0, x1 = COLS[c]
        y_row = Y0 + r*rh
        y = y_row + (rh - RH)/2                 # 段が高い列は、名前と波形を段のまん中に
        name = f"{pat['no']} {pat['name']}"
        im_n, _ = text_img(name, 26, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 26, 800, pat['col'], x=x0, cy=y + 24, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if THUMB_DESC[i]:
            im_h, _ = text_img(THUMB_DESC[i], 18, 500, (176, 186, 186))
            assert nx + im_h.size[0] - 8 <= x1 + 4, f'{pat["no"]} のひとことが入らない'
            put(im, THUMB_DESC[i], 18, 500, (176, 186, 186), x=nx, cy=y + 26)
        lay, pos = thumb_row_wave(i, x0, x1, y + 24 + (RH - 24)*0.64, 38.0)   # 低い波（U波・平たいP波）も見えるよう、第21弾（30）より大きく
        im.alpha_composite(lay, pos)
        if r < NRS[c] - 1:
            d.line([(x0, y_row + rh - 1), (x1, y_row + rh - 1)], fill=(38, 54, 48, 255), width=1)
    by = Y0 + TOT + 24
    d.rounded_rectangle([(230, by), (850, by + 96)], radius=18, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('まず覚えたい', 40, WHITE), (str(N_PAT), 72, YEL), ('パターン', 40, WHITE)]
    ims = [text_img(t, sz, 900, col) for t, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 70                          # 文字の下端（ベースライン）をそろえる
    for (t, sz, col), (a, asc) in zip(parts, ims):
        put(im, t, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def measure(kind, rr):
    """種類 kind（間隔 rr）の数値：心拍数・PR・QRS・QT・QTc（ms）。"""
    b = KINDS[kind]
    out = dict(rate=60/rr, pr=pr_ms(b), qrs=None if kind == 'SW' else qrs_ms(b))
    if kind not in ('K4', 'SW'):                 # QRSとTがつながるものは QT を測らない
        out['qt'] = qt_ms(b)
        out['qtc'] = qtc_ms(b, rr)
    return out


def check():
    print('パターンごとの紹介の時間')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']} {pat['name']:<14} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s  画面 {a:5.1f}–{b:5.1f}s（{b-a:4.1f}s）")
    print(f'最後のパターンの終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s')
    # 区間のつなぎ目：前のパターンの最後の拍 → 次のパターン（またはうしろの洞調律）の最初の拍
    for i, (s0, s1) in enumerate(SEGS):
        inside = [b for b in STRIP if s0 <= b[0] < s1]
        last = max(inside, key=lambda b: b[0])
        nxt = min((b for b in STRIP if b[0] >= s1 - 1e-9), key=lambda b: b[0])
        print(f"  つなぎ目 {PATTERNS[i]['no']}→ : {last[1]} {last[0]-s0:.2f} → {nxt[1]} 間隔 {nxt[0]-last[0]:.2f}s"
              f"（このパターンの間隔 {PATTERNS[i]['rr']:.2f}s）")
    print('各パターンの数値（モデルの波形から。QTの終わりは最大の下り勾配の接線と基線の交点、QTcはBazett）')
    for pat in PATTERNS:
        m = measure(pat['kind'], pat['rr'])
        s = f"{pat['no']} {pat['name']:<14} {m['rate']:4.0f}/分"
        s += f"  PR {m['pr']:4.0f}ms" if m['pr'] is not None else '  PR    -  '
        s += f"  QRS {m['qrs']:4.0f}ms" if m['qrs'] is not None else '  QRS   -  '
        if 'qt' in m:
            lab = 'QU' if KINDS[pat['kind']].u_fused else 'QT'
            s += f"  {lab} {m['qt']:4.0f}ms  {lab}c {m['qtc']:4.0f}ms"
        print(s)
    b = KINDS['N']
    print(f"① 基準：QT {qt_ms(b):.0f}ms は RR {RR*1000:.0f}ms の半分より短い（LITFL：normal QT is less than half the preceding RR）")
    for k, lab in (('T1', '②'), ('K2', '③'), ('K3', '④'), ('K4', '⑤')):
        tv = KINDS[k].part(_TT, 't').max()
        rv = KINDS[k].part(_TT, 'qrs').max()
        print(f"{lab} T波の高さ {tv:.2f}mV（R {rv:.2f}mV、T/R {tv/rv:.2f}）")
    for k, lab in (('L1', '⑦'), ('L2', '⑧')):
        bb = KINDS[k]
        tv = bb.part(_TT, 't').max(); uv = bb.part(_TT, 'u').max()
        stv = bb.part(_TT, 'st')
        print(f"{lab} T {tv:.2f}mV・U {uv:.2f}mV（U/T {uv/tv:.1f}）・ST低下 最大 {-stv.min():.2f}mV")
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:8]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])
    print(f'映像の長さ {DUR:.2f}秒')
    print('ひとこと＋色の文字の大きさ（32px が上限、ONE_W に入らないと小さくなる）')
    for pat in PATTERNS:
        tag = TAGS[pat['tag']]
        sz = one_size(pat)
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        print(f"  {pat['no']} {sz}px 幅 {w1 + 14 + w2}px  {pat['one']} {tag[0]}")
        nm = text_img(f"{pat['no']} {pat['name']}", 22, 700, pat['col'])[0].size[0] - 8
        assert nm <= CELL_W - 30, f"{pat['no']} 枠の名前が入らない"


# --- 書き出し ---------------------------------------------------------------------
def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def render_chunk(args):
    i0, i1, fps, path, crf, preset = args
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', preset,
           '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def beeps(path, sr=44100):
    """中部の波形の R が画面の中央を通るときに「ピッ」。幅の広いQRSの拍は低い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, i in STRIP:
        ts = t_of(r)
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 720.0 if KINDS[k].wide else 960.0
        L = int(0.08*sr)
        tt = np.arange(L)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*f*tt)
        j = int(ts*sr)
        a[j:j+L] += s[:max(0, min(L, n-j))]
    for k in range(len(HOOK)):                # 冒頭の変形のたびに
        ts = HOOK_T0 + k*HOOK_STEP
        L = int(0.07*sr); tt = np.arange(L)/sr
        s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.04)*np.sin(2*np.pi*720.0*tt)
        j = int(ts*sr); a[j:j+L] += s
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel25_lytes.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel25_lytes_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel25_lytes_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel25.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel25_list.png')
        thumbnail_list().save(p); print(p); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.still:
        for s in o.still:
            p = os.path.join(os.path.dirname(o.out), f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    total = int(round(DUR*o.fps))
    step = math.ceil(total / o.jobs)
    tmp = os.path.join(os.path.dirname(o.out), 'parts')
    os.makedirs(tmp, exist_ok=True)
    jobs = [(i, min(total, i+step), o.fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset)
            for j, i in enumerate(range(0, total, step))]
    with Pool(o.jobs) as pool:
        parts = pool.map(render_chunk, jobs)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    wav = os.path.join(tmp, 'beeps.wav')
    beeps(wav)
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', o.out],
                   check=True)
    print(o.out)


if __name__ == '__main__':
    main()
