"""第28弾 波形クイズ「この波形、なに？」（総復習）全10問

これまでの回（期外収縮・徐脈・ペースメーカー・ノイズ・致死性不整脈と心停止・頻脈・高カリウム血症とQT・
心房細動と心房粗動）の波形から10問。易しいものから順に、だんだん難しく。
波形のモデルは各回の make_reelNN.py から数値を変えずに移植した（元の回は専門医レビュー済み）。
`--check` で、元の回のモデルと同じ波形になることを1周期ずつ確かめる。視聴者に「第◯弾」は見せない。

1問の流れ（WINDOWS[i] = (a, b)）：
- a        ：前の問題の波形が枠へ縮んで移る（FLY 0.8秒）。そのあいだ帯は消す
- a+SW     ：この問題の波形が、右から 0.3秒ですべり込む（帯の時計をここで跳ばす。前の問題の波形は見せない）
             Q1 だけは帯を消さず、冒頭から流れている洞調律を a+0.4〜a+0.8 で Q1 の波形へ変形する
- a+0.62   ：「Q◯ これは？」が出る（前の波形が移り終わるころ）
- a+0.8 = t0：波形がはっきり見え始める。時間のリング（「これは？」の右）が減りはじめ、7秒（THINK）で空になる
- t0+1.5   ：ヒント。「ヒント：〇〇」と、波形の特徴のところ（hint_hl）だけ紫に。名前・答えの色は出さない（枠は「Q◯ ？」）
- t0+4.0   ：最後の3秒だけ、リングの中に数字 3・2・1（1秒ごと、音は木の「コッ」。モニター音は -6dB）
- t0+7.0   ：答え（a+7.8。名前・ひとこと・「→ くわしくは〇〇の回」）。特徴の紫がその問題の色に変わる。音「ポーン」。声「答えは、…」
- b        ：答えの声のあと。波形が縮んで枠へ移る（次の問題の a）

配置：
- 上部：Q1〜Q6 のミニ波形の枠（2列×3段）　下部：Q7〜Q10（2列×2段）。答えが出るまでは「Q◯ ？」だけ
- 中部：問題（「Q◯ これは？」とカウントダウンのリング）／答え（名前・ひとこと・案内）と、流れる帯
- 冒頭：変形するフック（名前は出さない）の上に「10問、全部わかる？」
- 最後：「何問正解？コメントで教えてね」「保存して見返してね」と、10問の答えの一覧（枠）
II誘導・実際の速さ（25mm/秒）。

使い方:
    python3 make_reel28_quiz.py              # 書き出し・60fps（CPU 4つなので --jobs 2）
    python3 make_reel28_quiz.py --still 20   # 1コマだけ
    python3 make_reel28_quiz.py --check      # 検算（元の回との一致・タイミング表・字の幅）
    python3 make_reel28_quiz.py --thumb      # サムネイル（透かしなし）
"""
import argparse
import importlib
import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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
YEL = (255, 214, 64)

# 答えの案内（「→ くわしくは〇〇の回」）の色＝危険度。ほかの回と意味をそろえる：
#   赤＝元の回で赤の「→ すぐ報告」「→ 電気ショック」「→ 脈なしならショック」
#   黄＝元の回で黄色の「→ すぐ報告」
#   緑＝元の回で色の文字なし、または緑（「→ まず患者さん」「→ 初めてなら報告」）
LEVEL = {'red': (255, 96, 96), 'yellow': (255, 196, 64), 'green': (130, 232, 172)}

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# =====================================================================================
# 波形の部品（実際の時間・秒、mV。R頂点を 0 とする）。各回の make_reelNN.py から、数値を変えずに移植
# =====================================================================================
RR = 0.80                        # 前後の洞調律 75/分
PR = 0.16                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):                   # 第17〜21・24・26弾 共通
    return 0.15*_g(t, 0.0, 0.022)


def qrs_normal(t):                # 第17〜21・26弾 共通（幅の狭いQRS＋T）
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_pvc(t):                   # 第17弾 PVC（形A）：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def qrs_rate(tc, ta=0.27):        # 第24弾：幅の狭いQRS＋T。T波の頂点 tc は心拍数が速いほど早い
    k = tc / 0.27

    def f(t):
        return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
                - 0.20*_g(t, 0.028, 0.009) + ta*_ga(t, tc, 0.060*k, 0.042*k))
    return f


qrs_115 = qrs_rate(0.235)         # 第24弾 洞頻脈（115/分）


def qrs_paced(t):                 # 第19弾 右室ペーシング（II誘導）：幅の広い下向きのQRS、上向きのT
    return (-0.78*_ga(t, 0.0, 0.030, 0.036) + 0.08*_g(t, 0.072, 0.016)
            + 0.32*_ga(t, 0.30, 0.075, 0.055))


PV_DELAY = 0.075                  # 第19弾 心室スパイク → ペーシングQRSの谷


def qrs_longqt(t):                # 第21弾 QT延長の洞調律：Tが遅く、幅が広い（QT 約0.56秒）
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.24*_ga(t, 0.40, 0.085, 0.060))


def tent(t, c, a, w):             # 第25弾 テント状のT波：高く、幅が狭く、左右対称で、先がとがる
    x = np.sqrt((t - c)**2 + 0.005**2)
    return a*np.clip(1 - x/w, 0, 1)**1.6


def qrs_normal25(t):              # 第25弾 幅の狭いQRS（T波は別）
    return -0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011) - 0.20*_g(t, 0.028, 0.009)


def beat_t1(t):                   # 第25弾 ② 高K：テント状T波（P波・QRSは基準と同じ）
    return 0.15*_g(t, -0.160, 0.022) + qrs_normal25(t) + tent(t, 0.240, 0.82, 0.115)


def _mk(q, p, pr):
    """(QRSの形, P波の形, P頂点 → R頂点) → 1拍の波形。"""
    def f(tau):
        v = np.zeros_like(tau)
        if q is not None:
            v = v + q(tau)
        if p is not None:
            v = v + p(tau + pr)
        return v
    return f


# 拍の種類 → (1拍の波形, 範囲の始まり, 終わり)。範囲は R頂点からの秒（元の回と同じ）
_W = (-0.75, 0.75)
KINDS = {
    'n': (_mk(qrs_normal, p_sinus, PR), *_W),          # 前後の洞調律（第21弾 'N' と同じ）
    'af': (_mk(qrs_normal, None, 0.0), *_W),           # 第26弾 'A'：心房細動で伝わった拍（P波なし）
    'st': (_mk(qrs_115, p_sinus, 0.15), *_W),          # 第24弾 'S'：洞頻脈
    'n17': (_mk(qrs_normal, p_sinus, PR), *_W),        # 第17弾 'N'
    'v17': (_mk(qrs_pvc, None, 0.0), *_W),             # 第17弾 'V'：PVC
    'p17': (_mk(None, p_sinus, PR), *_W),              # 第17弾 'p'：伝わらなかった洞のP（PVCに隠れる）
    'p18': (_mk(None, p_sinus, 0.0), *_W),             # 第18弾 'P'：P波だけ（時刻は P頂点）
    'q18': (_mk(qrs_normal, None, 0.0), *_W),          # 第18弾 'Q'：P波のない細いQRS
    't25': (beat_t1, -0.50, 0.95),                     # 第25弾 'T1'
    'n20': (_mk(qrs_normal, p_sinus, PR), *_W),        # 第20弾 'N'
    'v19': (_mk(qrs_paced, None, 0.0), *_W),           # 第19弾 'V'：心室ペーシング
    's19': (_mk(None, None, 0.0), *_W),                # 第19弾 'S'：スパイクだけ（QRSがつづかない）
    'q21': (_mk(qrs_longqt, p_sinus, PR), *_W),        # 第21弾 'Q'：QT延長の洞調律
}
SPIKES = {'v19': [(-PV_DELAY, 1.0)], 's19': [(0.0, 1.0)]}   # 第19弾と同じ
WIDE = {'v17', 'v19'}                                 # 幅の広い拍（モニター音を低く）
NO_BEEP = {'p17', 'p18', 's19'}                       # QRS のない出来事（モニター音なし）
ALL = [(-1e9, 1e9)]                                   # 全部をその色で


# --- 連続した波形（パターンの周期 L でくり返す）。第20・21・24・26弾 共通の band_noise ------------------------
def _rs(seed):
    return np.random.RandomState(seed)


def band_noise(rel, L, f_lo, f_hi, amp, seed, n_max=400):
    """f_lo〜f_hi Hz の帯域の不規則な揺れ。周期 L でくり返す（周波数は 1/L の整数倍）。RMSが amp。"""
    rs = _rs(seed)
    ks = np.arange(max(1, int(np.ceil(f_lo*L))), int(f_hi*L) + 1)
    if len(ks) > n_max:
        ks = np.sort(rs.choice(ks, n_max, replace=False))
    a = rs.normal(0, 1, len(ks)); ph = rs.uniform(0, 2*np.pi, len(ks))
    out = np.zeros_like(rel)
    for k, ak, pk in zip(ks, a, ph):
        out += ak*np.sin(2*np.pi*k*rel/L + pk)
    return out * amp / np.sqrt(np.sum(a**2)/2 + 1e-9)


def burst(rel, L, a, b, edge=0.25):
    """周期の中の a〜b 秒だけ1になる窓（端は edge 秒でなめらかに）。第20・21弾 共通。"""
    r = np.mod(rel, L)
    up = np.clip((r - a) / edge, 0, 1); dn = np.clip((b - r) / edge, 0, 1)
    w = np.minimum(up, dn)
    return w*w*(3 - 2*w)


F_COARSE = 0.045                  # 第26弾 粗い f波（RMS mV）


def art_af_coarse(rel, L):        # 第26弾 ② 心房細動（f波が粗い）：5〜8Hz の不規則な揺れ
    return band_noise(rel, L, 5.0, 8.0, F_COARSE, 31)


def art_vf_coarse(rel, L):        # 第21弾 ⑥ 粗いVF：3〜9Hzの不規則で大きな揺れ
    env = 0.75 + 0.25*np.sin(2*np.pi*rel/L)
    return env*band_noise(rel, L, 3.0, 9.0, 0.42, 24)


def brush_raw(rel, L):            # 第20弾 ⑨ 偽VT（歯みがき）の揺れ：4〜5Hzの大きな揺れ
    r = rel
    return (0.58*np.sin(2*np.pi*round(4.5*L)*r/L) + 0.14*np.sin(2*np.pi*round(9*L)*r/L + 0.9)
            + 0.08*np.sin(2*np.pi*round(4.75*L)*r/L + 2.1))


def art_brush(rel, L):            # 第20弾 ⑨：中にふつうのQRSが同じ間隔で見える
    return burst(rel, L, 0.45, 3.55, 0.2) * brush_raw(rel, L)


TDP_A, TDP_B = 1.40, 3.95         # 第21弾 ⑤ 周期の中のトルサードの区間（秒）
TDP_F = 4.0                       # 約240/分


def art_tdp(rel, L):              # 第21弾 ⑤ トルサード：QT延長の洞調律 → T波の上から、ねじれる → 自然に止まる
    r = np.mod(rel, L)
    m = (r >= TDP_A - 0.1) & (r <= TDP_B + 0.1)
    out = np.zeros_like(rel)
    if m.any():
        x = r[m] - TDP_A
        dur = TDP_B - TDP_A
        env = np.sin(np.pi*np.clip(x/dur, 0, 1))**0.6
        twist = np.cos(2*np.pi*x/1.25)
        car = np.sin(2*np.pi*TDP_F*x - 0.4) + 0.35*np.sin(4*np.pi*TDP_F*x)
        out[m] = 0.95*env*twist*car * (x >= 0)
    return out


def gain_tdp(rel, L):             # 第21弾 ⑤ トルサードのあいだは洞調律の拍を消す
    r = np.mod(rel, L)
    return np.where((r >= TDP_A - 0.02) & (r < TDP_B + 0.05), 0.0, 1.0)


def _cavb():                      # 第18弾 ⑨ 完全房室ブロック：心房 約84/分、心室 約47/分（接合部）
    pp, rr = 6.4/9, 1.28
    ev = [(k*pp, 'p18') for k in range(9)] + [(0.40 + m*rr, 'q18') for m in range(5)]
    hl = [(k*pp - 0.07, k*pp + 0.07) for k in range(9)]
    return sorted(ev), hl


_CAVB_EV, _CAVB_HL = _cavb()
CAVB_PP, CAVB_RR = 6.4/9, 1.28


def _cavb_hint():
    """Q5 の色付け（専門医レビュー 2026-10-07 の要修正）：QRSに重なるP波（R頂点の前後0.06秒）は色付けから外し、
    そのP波の時刻に「▼」を置く。ほかのP波（T波に重なるものも）は P頂点の前後0.07秒。QRS（R頂点の前後0.055秒）には色をかけない。"""
    L = 6.4
    R = [r for r, k in _CAVB_EV if k == 'q18']
    P = [r for r, k in _CAVB_EV if k == 'p18']
    hl, mk = [], []
    for p in P:
        d = min(((p - r + L/2) % L - L/2 for r in R), key=abs)
        if abs(d) <= 0.06:
            mk.append(p)
            continue
        a, b = p - 0.07, p + 0.07
        if 0 < d < 0.07 + 0.055:                       # QRSのすぐうしろのP波：QRSの終わりから
            a = max(a, p - d + 0.055)
        if -(0.07 + 0.055) < d < 0:                    # QRSのすぐ前のP波：QRSの始まりまで
            b = min(b, p - d - 0.055)
        hl.append((round(a, 4), round(b, 4)))
    return hl, mk


_CAVB_HINT, _CAVB_MARK = _cavb_hint()
LRI = 1.0                         # 第19弾 下限レート 60/分 の間隔
AF_RR = [0.62, 0.95, 0.70, 1.10, 0.58, 0.85]          # 第26弾 RR_COARSE（平均75/分）
AF_EV = [(round(float(sum(AF_RR[:k])), 4), 'af') for k in range(len(AF_RR))]

# =====================================================================================
# 10問。易しい順。名前・ひとことは元の回と同じ。say は答えの声（元の回のレビュー済みの台本の言い回しから）。
# src：(フォルダ, モジュール, パターンの番号（0から）, 元の回での番号と名前)。--check で元の回の波形と比べる
# =====================================================================================


def _q(no, name, col, level, theme, one, say, ev, L, hl, src, art=None, gain=None, hint=None, hint_hl=None,
       ans_extra=(), marks=(), note=None, mini_lw=None):
    hh = hl if hint_hl is None else hint_hl
    ah = hh if (hh is ALL or not ans_extra) else sorted(list(hh) + list(ans_extra))
    return dict(no=no, name=name, col=col, level=level, theme=theme, guide=f'→ くわしくは{theme}の回',
                one=one, say=say, ev=ev, L=L, hl=hl, src=src, art=art, gain=gain,
                hint=hint, hint_hl=hh, ans_hl=ah, marks=list(marks), note=note, mini_lw=mini_lw, strong=mini_lw is not None)


# ヒント（答えの前に出す。答えの名前は書かない）と、色を付ける特徴の場所（周期の中の秒）。
# 文は元の回の hint（レビュー済み）から。Q1・Q5・Q8 はユーザーの案。hint_hl を書いていない問題は、色の場所も元の回と同じ（hl）
HINT = {
    'Q1': 'R-Rの間隔と、P波をさがして',    # 専門医レビュー 2026-10-07 の推奨（答えのひとことと同じ文にしない）。元の回 ②は「f波が大きい」
    'Q2': 'Pがそろう',                     # 第24弾 ① hint
    'Q3': '1拍おき',                       # 第17弾 ⑨ hint
    'Q4': '大きくバラバラ',                 # 第21弾 ⑥ hint
    'Q5': 'PとQRSの間隔',                  # ユーザーの案（元の回 ⑨「PとQRSがばらばら」）
    'Q6': 'PRが伸びて抜ける',               # 第18弾 ⑤ hint
    'Q7': 'T波がとがる',                    # 第25弾 ② hint
    'Q8': '同じ間隔のQRS',                  # ユーザーの案（元の回 ⑨「VTに見える」）
    'Q9': 'スパイクだけ',                   # 第19弾 ⑨ hint
    'Q10': 'ねじれる',                      # 第21弾 ⑤ hint
}


PATTERNS = [
    _q('Q1', '心房細動（f波が粗い）', (110, 200, 255), 'green', '心房細動',
       'P波なし、R-Rがバラバラ', '答えは、心房細動。R-Rがバラバラ。',
       AF_EV, round(sum(AF_RR), 4), ALL, ('reel26_afl', 'make_reel26', 1, '② 心房細動（f波が粗い）'), art=art_af_coarse),
    _q('Q2', '洞頻脈', (56, 189, 248), 'green', '頻脈',             # 濃い水色 #38BDF8（レビュー 2026-10-07：P波の色を見分けやすく）
       'どの拍にも、ふつうのP波', '答えは、洞頻脈。どの拍にもP波がある。',
       [(k*0.52, 'st') for k in range(8)], 4.16, ALL, ('reel24_tachy', 'make_reel24', 0, '① 洞頻脈'),
       hint_hl=[(k*0.52 - 0.15 - 0.06, k*0.52 - 0.15 + 0.06) for k in range(8)], mini_lw=4.6),  # どの拍のP波（P頂点 ±0.06秒）
    _q('Q3', '二段脈', (255, 152, 72), 'green', '期外収縮',
       '1拍おきにPVC。脈は半分のことも', '答えは、二段脈。1拍おきにPVC。',
       [(0, 'n17'), (.48, 'v17'), (.8, 'p17')], 1.6, [(0.48 - 0.09, 0.48 + 0.40)],
       ('reel17_ectopy', 'make_reel17_v2', 8, '⑨ 二段脈')),
    _q('Q4', '粗いVF', (255, 92, 112), 'red', '致死性不整脈',
       '不規則で大きな揺れ。QRSが見えない', '答えは、粗いVF。大きくバラバラ。',
       [], 4.0, ALL, ('reel21_arrest', 'make_reel21', 5, '⑥ 粗いVF'), art=art_vf_coarse),
    _q('Q5', '完全房室ブロック', (255, 92, 112), 'red', '徐脈',
       'PとQRSが別々に動く。PRが毎回ちがう', '答えは、完全房室ブロック。PとQRSが、別々に動く。',
       _CAVB_EV, 6.4, _CAVB_HL, ('reel18_brady', 'make_reel18', 8, '⑨ 完全房室ブロック'),
       hint_hl=_CAVB_HINT, marks=_CAVB_MARK),
    _q('Q6', 'ウェンケバッハ', (255, 212, 90), 'green', '徐脈',
       'PRが少しずつ伸びて、QRSが1つ抜ける', '答えは、ウェンケバッハ。PRが伸びて、抜ける。',
       [(0, 'p18'), (.18, 'q18'), (.8, 'p18'), (1.08, 'q18'), (1.6, 'p18'), (1.93, 'q18'), (2.4, 'p18')], 3.2,
       [(-0.06, 0.20), (0.74, 1.10), (1.54, 1.95), (2.32, 2.50)], ('reel18_brady', 'make_reel18', 4, '⑤ ウェンケバッハ'),
       hint_hl=[(-0.06, 0.18 - 0.04), (0.74, 1.08 - 0.04), (1.54, 1.93 - 0.04), (2.32, 2.50)]),   # P波〜QRSの始まり（R頂点の0.04秒前）
    _q('Q7', '高K：テント状T波', (255, 212, 90), 'yellow', '高カリウム',
       'T波が高く、細く、左右対称', '答えは、高カリウム。T波が高くとがる。',
       [(k*1.0, 't25') for k in range(4)], 4.0, [(k*1.0 + 0.09, k*1.0 + 0.40) for k in range(4)],
       ('reel25_lytes', 'make_reel25', 1, '② 高K：テント状T波')),
    _q('Q8', '偽VT（歯みがき）', (255, 152, 72), 'green', 'ノイズ',
       'VTに見えても、ふつうのQRSが同じ間隔', '答えは、ノイズ。ふつうのQRSが隠れている。',
       [(k*RR, 'n20') for k in range(5)], 4.0, [(0.45, 3.55)], ('reel20_artifact', 'make_reel20', 8, '⑨ 偽VT（歯みがき）'),
       art=art_brush, hint_hl=[(k*RR - 0.04, k*RR + 0.04) for k in range(5)],          # 同じ間隔のQRS（R頂点の前後0.04秒）
       marks=[k*RR for k in range(5)], note='※まず患者さん（意識・脈）を見てから'),
    _q('Q9', 'ペーシング不全', (255, 92, 112), 'red', 'ペースメーカー',
       'スパイクのあとに、QRSがない', '答えは、ペーシング不全。スパイクのあとに、QRSがない。',
       [(0, 'v19'), (LRI, 'v19'), (2*LRI, 's19'), (3*LRI, 'v19')], 4*LRI, [(2*LRI - 0.12, 2*LRI + 0.30)],
       ('reel19_pacing', 'make_reel19', 8, '⑨ ペーシング不全')),
    _q('Q10', 'トルサード・ド・ポワント', (255, 152, 72), 'red', '致死性不整脈',
       'ねじれる。QT延長がきっかけ', '答えは、トルサード。ねじれる。',
       [(0, 'q21'), (1.0, 'q21'), (4.6, 'q21')], 5.6, [(TDP_A - 0.1, TDP_B + 0.1)],
       ('reel21_arrest', 'make_reel21', 4, '⑤ トルサード・ド・ポワント'), art=art_tdp, gain=gain_tdp,
       ans_extra=[(r - 0.043, r + 0.533) for r in (0.0, 1.0, 4.6)]),     # 答えのあと：洞調律の拍の QT（QRSの始まり〜T波の終わり）
]
N_PAT = len(PATTERNS)
for _p in PATTERNS:
    _p['beats'] = _p['ev']
    _p['hint'] = HINT[_p['no']]


def art_apply(pat, rel, v):
    """パターンのノイズと倍率：gain(rel)*v + art(rel)（周期 L でくり返す）。"""
    L = pat['L']
    if pat.get('gain'):
        v = pat['gain'](rel, L) * v
    if pat.get('art'):
        v = v + pat['art'](rel, L)
    return v


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        f, lo, hi = KINDS[k]
        m = (tau - r > lo) & (tau - r < hi)
        if m.any():
            v[m] += f(tau[m] - r)
    return v


def spike_times(beats):
    """拍の列 → スパイクの列 [(時刻, 高さ), …]"""
    out = []
    for r, k, *_ in beats:
        for dt, amp in SPIKES.get(k, ()):
            out.append((r + dt, amp))
    return out


def periodic_beats(pat, t0, t1):
    out = []
    L = pat['L']
    k0 = int(math.floor(t0 / L)) - 1
    k1 = int(math.ceil(t1 / L)) + 1
    for k in range(k0, k1):
        for r, kind in pat['ev']:
            out.append((k*L + r, kind))
    return out


def hl_mask(pat, rel, key='hint_hl'):
    """周期の中の色を付ける範囲（rel は区間の始まりからの時刻）。ヒントと答えで同じ場所（hint_hl）に色を付ける。"""
    L = pat['L']
    r = np.mod(rel, L)
    m = np.zeros(len(rel), dtype=bool)
    if pat[key] is ALL:
        return np.ones(len(rel), dtype=bool)
    for a, b in pat[key]:
        for sh in (-L, 0.0, L):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


# =====================================================================================
# 時間の流れ
# =====================================================================================
T_STOP, T_GO = 0.25, 2.6          # 冒頭：波形を止めて、5つの問題の波形に変形（名前は出さない）
FREEZE = T_GO - T_STOP
T_TITLE = 3.6                     # 冒頭の1文「心電図クイズ。この10問、全部わかる？」（仮 約3.0秒）が入る長さ
HOOK = [9, 3, 0, 7, 4]            # Q10トルサード → Q4 VF → Q1 心房細動 → Q8 偽VT → Q5 完全房室ブロック
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.3, 0.38, 0.12
SW = 0.5                          # a から、帯の時計を跳ばす（この問題の波形を出す）まで
T0_OFF = 0.8                      # 波形がはっきり見え始める時刻 t0（a から）：帯は a+0.5 から 0.3秒で浮かぶ。前の波形が縮む 0.8秒のあと
THINK = 7.0                       # 考える時間：t0 から答えまで 7秒（時間のリングが t0 から減りはじめ、7秒で空になる）
HINT0 = T0_OFF + 1.5              # ヒント（「ヒント：〇〇」と特徴の紫の色付け）：t0 の 1.5秒後（a から 2.3秒）
REVEAL = T0_OFF + THINK           # 答えを出す時刻（a から 7.8秒）
CD_STEP, CD_N = 1.0, 3            # 最後の3秒だけ数字「3・2・1」と「コッ」（1秒ごと）
CD0 = REVEAL - CD_STEP*CD_N       # 数字「3」が出る時刻（a から 4.8秒）
SAY_CPS = 7.0                     # 声の長さの見込み：同じ声（Ren）の第20弾の録音で実測 6.96字/秒（13文、6.1〜8.2）。録音後に決め直す
SAY_LEAD, SAY_TAIL = 0.15, 0.30   # 答えが出てから話し始めるまで／言い終わってから縮み始めるまで
FLY = 0.8                         # 中部から枠へ縮んで移る時間
END_HOLD = 6.0                    # 10個そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
LOOP_FADE = 0.75                  # 最後に冒頭の画面へ戻す時間
PRE = 0.6                         # 帯に出すとき、区間の頭から先へ進めておく（ノイズの入りの 0.2秒を見せない）
PRE_END = 0.4


# 帯に出すとき、区間の頭からどれだけ進めておくか（周期の中のどこから見せるか）。ふつうは PRE。
# 画面の左はしの時刻（周期の中）は pre + (t - a - 0.5)。答えの瞬間（a+7.8）の画面は pre+7.3 〜 pre+10.39。
# Q9 ペーシング不全は周期 4秒（スパイクだけの拍は 2.0・6.0・10.0秒）。1.1秒から見せると、ヒントのとき右はしに 6.0秒の拍が入り、
#    答えの瞬間に 10.0秒の拍が画面のまん中（x 約560）にある
# Q10 トルサードは周期 5.6秒（ねじれ 1.40〜3.95・7.00〜9.55・12.60〜15.15秒）。5.0秒から見せると、波形が見え始めるとき右半分で
#    1回目のねじれが始まり（ヒントのとき全体が画面に入る）、答えの瞬間に2回目のねじれの始まり（T波の上）から終わりまでが入る
PRE_OF = {8: 1.1, 9: 5.0}


def pre_of(i):
    return PRE_OF.get(i, PRE)


# 録音した声の、各文の長さ（秒。align_vo.py で切り出したあと＝前 0.06秒・うしろ 0.15秒の無音をふくむ）。
# 2026-10-07 の録音（Ren – Smooth & Soothing・eleven_v4、1.2倍速）。`python3 align_vo.py out/vo/narration_raw.wav --lens` の値。
# 答えのあとの長さ（声 ＋ 0.45秒）はこれに合わせる。考える時間 7秒は変えない
VO_LEN = {'冒頭': 2.720, 'Q1': 3.353, 'Q2': 3.176, 'Q3': 3.270, 'Q4': 2.981, 'Q5': 4.351, 'Q6': 3.216, 'Q7': 2.829,
          'Q8': 3.080, 'Q9': 3.600, 'Q10': 1.928, 'まとめ': 2.003, '保存': 1.388}


def say_len(i):
    no = PATTERNS[i]['no']
    return VO_LEN[no] if no in VO_LEN else len(PATTERNS[i]['say']) / SAY_CPS


WINDOWS, T_REV, T_HINT = [], [], []
_t = T_TITLE
for _i in range(N_PAT):
    _b = _t + REVEAL + SAY_LEAD + say_len(_i) + SAY_TAIL
    WINDOWS.append((_t, _b)); T_REV.append(_t + REVEAL); T_HINT.append(_t + HINT0)
    _t = _b
T_END = WINDOWS[-1][1]
T_SW = [a + SW for a, _ in WINDOWS]
T_SW_END = T_END + SW

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
XC = W / 2
HALF = XC / F_PXS                 # 画面の半分が実際の何秒か

# 区間の長さ（帯の上の長さ）：帯に出ているあいだ（跳ばしてから、次に跳ばすまで）この問題の波形だけが見える長さ。
# つなぎ目は画面に出ない（帯の時計を跳ばすので）。どれも周期でくり返す波形なので、どこで切ってもよい
for _i, _p in enumerate(PATTERNS):
    _p['D'] = round(pre_of(_i) + 2*HALF + (WINDOWS[_i][1] + SW - T_SW[_i]) + 0.4, 3)


def _strip():
    beats, segs, t = [], [], 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < pat['D'] - 1e-9:
                beats.append((t + r, kind, i))
        t += pat['D']
        segs.append((s0, t))
    end = t
    k = -1
    while k*RR > -14:                     # 前：洞調律
        beats.append((k*RR, 'n', None)); k -= 1
    for k in range(0, 40):                # うしろ：洞調律
        beats.append((end + k*RR, 'n', None))
    beats.sort(key=lambda b: b[0])
    return beats, segs, end


STRIP, SEGS, STRIP_END = _strip()
STRIP_SPK = spike_times(STRIP)
# 冒頭：Q1 の帯に跳ぶまで、前の洞調律だけが見える（Q1 の区間の頭は、跳ぶ瞬間に画面の右はしより 0.5秒先）
OFFSET = -HALF - (T_SW[0] - FREEZE) - 0.5


def tau_pat(i, t):
    """問題 i の波形の時計（帯に出ているあいだ、枠へ移るあいだ、枠の中）。跳ばした瞬間、画面の左はしが区間の頭＋PRE。"""
    return SEGS[i][0] + pre_of(i) + HALF + (t - T_SW[i])


# 冒頭 → Q1：帯は消さない。冒頭から流れている洞調律を、Q1 の波形へ 0.4秒でなめらかに変形する（a+0.4〜a+0.8）
Q1_MORPH0 = WINDOWS[0][0] + T0_OFF - 0.4
Q1_MORPH1 = WINDOWS[0][0] + T0_OFF
# Q2 以降：前の波形が枠へ縮むあいだ（0.5秒）帯を消し、次の波形を右から 0.3秒ですべり込ませる（a+0.5〜a+0.8）
SLIDE = 0.3
STARTS = [Q1_MORPH1] + T_SW[1:]       # 帯の時計が、その問題の波形に切りかわる時刻


def tau_c(t):
    """画面の中央にある実際の時刻（帯の時計）。冒頭は止まる・問題ごとに跳ぶ（Q1 は変形のあと）。"""
    if t < T_STOP:
        return OFFSET + t
    if t < T_GO:
        return OFFSET + T_STOP
    if t < STARTS[0]:
        return OFFSET + t - FREEZE
    if t >= T_SW_END:
        return STRIP_END + PRE_END + HALF + (t - T_SW_END)
    i = max(k for k in range(N_PAT) if STARTS[k] <= t)
    return tau_pat(i, t)


def pieces():
    """帯の時計の直線の区切り [(t0, t1)]（モニター音の計算用。止まっているあいだは除く）。"""
    edges = [0.0, T_STOP, T_GO] + STARTS + [T_SW_END, 1e9]
    out = []
    for a, b in zip(edges, edges[1:]):
        if a == T_STOP:
            continue
        out.append((a, b))
    return out


def strip_alpha(t):
    """中部の帯の濃さ。冒頭からQ1へは消さない（変形）。Q2 以降は、前の波形が枠へ移るあいだだけ消す。"""
    for h0, s in zip([b for _, b in WINDOWS], T_SW[1:] + [T_SW_END]):
        if h0 <= t < s:
            return 0.0
    return 1.0


def strip_dx(t):
    """次の波形が右からすべり込むときの、帯の横のずれ（px）。0 でふつうの位置。"""
    for s in T_SW[1:] + [T_SW_END]:
        if s <= t < s + SLIDE:
            return int(round((1 - ease((t - s) / SLIDE)) * W))
    return 0


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def _loop_dur():
    """10個そろったあと END_HOLD 秒ほど置き、最後のコマの次が t=0 のコマになる長さ（うしろの洞調律と冒頭の洞調律の位相をそろえる）。"""
    base = T_END + FLY + END_HOLD
    best = None
    for n in range(int(base*60), int((base + RR + 0.5)*60)):
        d = n / 60
        ph = ((tau_c(d) - STRIP_END) - tau_c(0.0)) % RR
        err = min(ph, RR - ph)
        if best is None or err < best[0] - 1e-9:
            best = (err, d)
    return best[1]


DUR = _loop_dur()

# =====================================================================================
# 配置
# =====================================================================================
CELL_W, CELL_H = 400, 110
COL_X = (130, 550)
TOP_Y = [344, 464, 584]           # Q1〜Q6（2列×3段）。波形が大きい（上 約1.5mV・下 約1.2mV）ので、見出しとともに 20px 上げた
BOT_Y = [1300, 1420]              # Q7〜Q10（2列×2段。下端 1530。注意書きを 1600 の内側に）
CELL_FILL = 225
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px
M_MV = 33.0
_TOP_END = TOP_Y[-1] + CELL_H     # 714
_BOT_TOP = BOT_Y[0]               # 1300


def _amp_range():
    """10問の波形の、いちばん上・いちばん下（mV）。帯の高さを決める。"""
    hi, lo = 1.0, -0.4
    for pat in PATTERNS:
        rel = np.arange(0, pat['L'], 0.002)
        v = art_apply(pat, rel, wave_from(periodic_beats(pat, -1, pat['L'] + 1), rel))
        hi, lo = max(hi, float(v.max())), min(lo, float(v.min()))
    return hi, lo


WAVE_HI, WAVE_LO = _amp_range()
# 中部のかたまり：名前（50px）→ ひとこと（30px）→ 案内（28px）→ 波形（上 WAVE_HI 〜 下 WAVE_LO）。上下の余白をそろえる
_MID_H = 34 + 46 + 30 + 14 + 28 + 14 + (WAVE_HI - WAVE_LO)*F_MV   # 名前の位置を決める見積もり（直す前と同じ）
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 34
Y_ONE = Y_NAME + 56
Y_GUIDE = Y_ONE + 46
# 帯の基線：いちばん下（VF・トルサードの谷）が下の枠の 22px 上に来る位置。ふつうの波形が上に寄りすぎないように、
# 上の余り（案内の字とのあいだ）より下を詰める。いちばん上（歯みがきの山）は案内の字の下 30px 以上
F_BASE = _BOT_TOP - 22 + WAVE_LO*F_MV
assert F_BASE - WAVE_HI*F_MV >= Y_GUIDE + 30, '帯の上が案内の字に近すぎる'
F_Y0, F_Y1 = int(F_BASE - WAVE_HI*F_MV - 24), int(_BOT_TOP - 2)
RING_R = 32                        # カウントダウンのリング：「Q◯ これは？」の右に並べる
Y_RING = Y_NAME + 2
Y_HINT = Y_NAME + 66               # 「ヒント：〇〇」（36px）。下の帯（いちばん上 約900）とのあいだ 50px 以上
HINT_COL = (236, 120, 255)
NOTE_UP = (26, 32, 40)             # 注意の1行（Q8）があるとき、名前・ひとこと・案内を上げる量（px）
NOTE_DY = 32                       # 案内の中心 → 注意の行の中心         # ヒントの色付け：答えの色（青・水色・橙・赤・黄）と危険度の色（赤・黄・緑）のどれともちがう紫

HEADER = [('この波形、なに？', 1.0, WHITE), (str(N_PAT), 2.0, YEL), ('問', 1.0, WHITE)]
HEADER_BASE = 322                 # 「10」の上端 約255（上 250px より下）
HOOK_Q = f'{N_PAT}問、全部わかる？'
TITLE_SUB, TITLE = '心電図クイズ', 'この波形、なに？'
END_Q = '何問正解？コメントで教えてね'
END_SAVE = '保存して見返してね'
COUNT_NOTE = '正解の数を数えてね'
NOTE1 = '※II誘導のモニター（実際の速さ）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'


def cell_rect(i):
    if i < 6:
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 6
        col, row = j // 2, j % 2
        x, y = COL_X[col], BOT_Y[row]
    return (x, y, x + CELL_W, y + CELL_H)


# =====================================================================================
# 道具（第21弾と同じ）
# =====================================================================================
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


def text_w(s, size, weight, max_w=None):
    return text_img(s, size, weight, WHITE, max_w)[0].size[0] - 8


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


# =====================================================================================
# 波形を描く（第21弾と同じ作り）
# =====================================================================================
SS = 2


def strip_colors(tau, key='hint_hl'):
    """パターンの区間のうち、色を付ける範囲だけそのパターンの番号（色を付けるかは featured で決める）。"""
    cid = np.full(len(tau), -1, dtype=int)
    for i, (s0, s1) in enumerate(SEGS):
        inside = (tau >= s0) & (tau < s1)
        if not inside.any():
            continue
        m = inside & hl_mask(PATTERNS[i], tau - s0, key)
        cid[m] = i
    return cid


ART_EDGE = 0.2                    # 区間の端で、ノイズ・倍率をなめらかに切りかえる長さ（秒）


def strip_art(tau, v):
    out = v.copy()
    for i, (s0, s1) in enumerate(SEGS):
        pat = PATTERNS[i]
        if not (pat.get('art') or pat.get('gain')):
            continue
        m = (tau > s0 - 1e-9) & (tau < s1)
        if not m.any():
            continue
        tt = tau[m]
        e = np.minimum(np.clip((tt - s0) / ART_EDGE, 0, 1), np.clip((s1 - tt) / ART_EDGE, 0, 1))
        e = e*e*(3 - 2*e)
        rel = tt - s0
        L = pat['L']
        g = pat['gain'](rel, L) if pat.get('gain') else 1.0
        n = pat['art'](rel, L) if pat.get('art') else 0.0
        out[m] = v[m] * (1 + e*(g - 1)) + e*n
    return out


def glow_line(size, runs, col, width, a, blur=(8, 20), white=0.6):
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
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), white) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


FX = np.arange(0, W + 1, 0.5)

# スパイクは波形の線より少し太く、明るく描く（第19弾の専門医レビュー 2026-10-03 と同じ）
SPIKE_W = 1.35
SPIKE_W_MIN = 3.2
SPIKE_LIGHT = 0.35


def spike_layer(size, runs, col, lw, a, blur):
    return glow_line(size, runs, mix(col, (255, 255, 255), SPIKE_LIGHT), max(lw*SPIKE_W, SPIKE_W_MIN), a, blur=blur)


def spike_runs(spk, xs, ys, mv, x_off=0.0, y_off=0.0):
    out = []
    for x, amp, *_ in spk:
        yb = float(np.interp(x, xs, ys))
        out.append([(x - x_off, yb + 0.12*amp*mv - y_off), (x - x_off, yb - amp*mv - y_off)])
    return out


def strip_arrays(tau_center, key='hint_hl'):
    tau = tau_center + (FX - XC) / F_PXS
    spk = []
    for ts, amp in STRIP_SPK:
        x = XC + (ts - tau_center) * F_PXS
        if -10 <= x <= W + 10:
            spk.append((x, amp, int(strip_colors(np.array([ts]), key)[0])))
    return strip_art(tau, wave_from(STRIP, tau)), strip_colors(tau, key), spk


MARK_W, MARK_H, MARK_GAP = 20, 14, 6   # 「▼」（中部の帯）。ミニ波形では MINI_MARK の大きさ
MINI_MARK = (10, 8, 4)


def mark_xs(pat, rel0, rel1, x0, pxs):
    """周期の中の時刻 marks → 画面の x（rel0〜rel1 のあいだ）。"""
    L = pat['L']
    out = []
    for m_ in pat['marks']:
        k0 = math.floor((rel0 - m_) / L)
        for k in range(k0, k0 + int((rel1 - rel0) / L) + 3):
            r = m_ + k*L
            if rel0 <= r <= rel1:
                out.append(x0 + (r - rel0)*pxs)
    return out


def draw_marks(img, xs_m, xs, ys, col, a, size, win_px):
    """波形の一番上（x の前後 win_px）より上に「▼」。img は RGBA、xs・ys は img の座標。"""
    w, h, gap = size
    d = ImageDraw.Draw(img, 'RGBA')
    for x in xs_m:
        sel = (xs >= x - win_px) & (xs <= x + win_px)
        if not sel.any():
            continue
        top = float(ys[sel].min()) - gap
        d.polygon([(x - w/2, top - h), (x + w/2, top - h), (x, top)], fill=col + (int(255*a),))


def hook_arrays(i):
    """フック用：パターン i の一場面（色は付けない＝答えを明かさない）。"""
    pat = PATTERNS[i]
    c = pat['L'] / 2 if pat['hl'] is ALL else (pat['hl'][-1][0] + pat['hl'][-1][1]) / 2 + 0.25
    rel = c + (FX - XC) / F_PXS + pat['L']
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    spk = [(XC + (ts - c - pat['L']) * F_PXS, amp, -1) for ts, amp in spike_times(bl) if rel[0] <= ts <= rel[-1]]
    return v, np.full(len(rel), -1, dtype=int), spk


_HOOK = {}


def hook_targets():
    if not _HOOK:
        _HOOK['seq'] = [strip_arrays(tau_c(T_STOP))] + [hook_arrays(i) for i in HOOK] + [strip_arrays(tau_c(T_STOP))]
    return _HOOK['seq']


def hook_state(t):
    seq = hook_targets()
    times = [HOOK_T0 + k*HOOK_STEP for k in range(len(HOOK) + 1)]
    k = -1
    for n, tk in enumerate(times):
        if t >= tk:
            k = n
    if k < 0:
        return seq[0], seq[0], 1.0
    return seq[k], seq[k + 1], ease((t - times[k]) / HOOK_MORPH)


def draw_wave(v, cid, base_col, a, spk=(), hl_col=None):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(set(np.unique(cid).tolist()) | {c for *_, c in spk}):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else (hl_col or PATTERNS[ci]['col'])
        if runs:
            strong = ci >= 0 and PATTERNS[ci].get('strong')   # Q2：色の付いたP波を濃く・太く（緑と見分けやすく）
            out.alpha_composite(glow_line((W, h), runs, col, 6.0 if strong else 4.5, a, white=0.15 if strong else 0.6))
        sr = spike_runs([q for q in spk if q[2] == ci], FX, ys, F_MV)
        if sr:
            out.alpha_composite(spike_layer((W, h), sr, col, 4.5, a, (8, 20)))
    return out


def featured(t, base_col, a, cur=None):
    """中部の帯。色を付けるのは、いまの問題（cur）の特徴のところ（hint_hl）だけ。
    出題中はみどりだけ → ヒントで紫（HINT_COL）→ 答えでその問題の色へ。"""
    if T_STOP <= t < T_GO:
        (v0, c0, s0), (v1, c1, s1), u = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, np.full(len(v0), -1, dtype=int), base_col, a, s1 if u >= 0.5 else s0)
    if Q1_MORPH0 <= t < Q1_MORPH1:                  # 冒頭の洞調律 → Q1 の波形（色はみどりのまま）
        v0, _, _ = strip_arrays(OFFSET + t - FREEZE)
        v1, _, _ = strip_arrays(tau_pat(0, t))
        u = ease((t - Q1_MORPH0) / (Q1_MORPH1 - Q1_MORPH0))
        return draw_wave(v0 + (v1 - v0)*u, np.full(len(v0), -1, dtype=int), base_col, a)
    key = 'ans_hl' if (cur is not None and t >= T_REV[cur]) else 'hint_hl'   # 答えのあとは ans_hl（Q10 は QT も）
    v, cid, spk = strip_arrays(tau_c(t), key)
    c = cur if (cur is not None and t >= T_HINT[cur]) else -999
    cid = np.where(cid == c, cid, -1)
    spk = [(x, amp, ci if ci == c else -1) for x, amp, ci in spk]
    hl_col = None
    if c >= 0:
        hl_col = mix(mix(base_col, HINT_COL, ramp(t, T_HINT[c], 0.25)), PATTERNS[c]['col'], ramp(t, T_REV[c], 0.3))
    out = draw_wave(v, cid, base_col, a, spk, hl_col)
    if c >= 0 and PATTERNS[c]['marks']:            # 「▼」：Q5 はQRSに隠れたP波、Q8 は同じ間隔のQRS
        tc = tau_c(t)
        s0 = SEGS[c][0]
        rel0 = tc - HALF - s0
        xm = mark_xs(PATTERNS[c], rel0, rel0 + W / F_PXS, 0.0, F_PXS)
        draw_marks(out, xm, FX, F_BASE - F_Y0 - v*F_MV, hl_col, a*ramp(t, T_HINT[c], 0.25), (MARK_W, MARK_H, MARK_GAP), 0.05*F_PXS)
    return out


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 76, 50     # ミニ波形の帯（枠の中）
STRIP_W_R = 900 - (COL_X[1] + 10)                      # 右の列は波形の右端を x 900 まで（透かしの列に入れない）


def strip_w(i):
    return STRIP_W if cell_rect(i)[0] == COL_X[0] else STRIP_W_R


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


def _mini_scale():
    """問題ごとのミニ波形の大きさと基線：上下の幅を 64px 以内にし、枠の名前の下（y0+33）〜枠の下（y0+107）のまん中に置く。
    上はペースメーカーのスパイクの先（1mV）も含める。"""
    mvs, bases = [], []
    for pat in PATTERNS:
        rel = np.arange(0, pat['L'], 0.002)
        bl = periodic_beats(pat, -1, pat['L'] + 1)
        v = art_apply(pat, rel, wave_from(bl, rel))
        hi, lo = float(v.max()), float(v.min())
        for ts, amp in spike_times(bl):
            if 0 <= ts < pat['L']:
                hi = max(hi, float(np.interp(ts, rel, v)) + amp)
        room = (MINI_MARK[1] + MINI_MARK[2]) if pat['marks'] else 0     # 「▼」の場所を上にあける
        mv = min(M_MV, (64.0 - room)/(hi - lo))
        mvs.append(mv); bases.append(40.5 + room/2 + (hi + lo)/2*mv)
    return mvs, bases


MINI_MV, MINI_BASE = _mini_scale()


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0, plain=False):
    """問題 i の波形を、画面の x_lo〜x_hi に描いた RGBA。中央 cx に来る時刻は tau_pat(i, t)。plain は色なし（サムネイル）。"""
    pat = PATTERNS[i]
    s0 = SEGS[i][0]
    xs = np.arange(x_lo, x_hi + 0.5, 0.5)
    tau = tau_pat(i, t) + (xs - cx) / pxs
    rel = tau - s0
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    ys = base_y - v*mv
    if plain:
        ect = np.zeros(len(xs), dtype=bool)
    else:
        ect = hl_mask(pat, rel, 'ans_hl')
    y_lo = int(min(ys.min(), base_y - 1.1*mv) - 30)
    y_hi = int(max(ys.max(), base_y + 0.9*mv) + 30)
    bx0, by0 = int(x_lo) - 30, y_lo
    size = (int(x_hi - x_lo) + 60, max(4, y_hi - y_lo))
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    spk = []
    for ts, amp in spike_times(bl):
        if rel[0] <= ts <= rel[-1]:
            on = (not plain) and bool(hl_mask(pat, np.array([ts]), 'ans_hl')[0])
            spk.append((xs[0] + (ts - rel[0]) * pxs, amp, on))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        w_, a_ = (((pat['mini_lw'] or lw_e or lw) if lw < 4.0 else (lw_e or lw)) if flag else lw), (a if flag else a*a_norm)
        if runs:
            strong = flag and pat.get('strong') and not plain
            out.alpha_composite(glow_line(size, runs, col, w_, a_, blur=blur, white=0.15 if strong else 0.6))
        sr = spike_runs([q for q in spk if q[2] == flag], xs, ys, mv, bx0, by0)
        if sr:
            out.alpha_composite(spike_layer(size, sr, col, w_, a_, blur))
    if pat['marks'] and not plain:
        k = mv / F_MV
        sz = tuple(lerp(mn, mx, (k - MINI_MV[i]/F_MV)/(1 - MINI_MV[i]/F_MV)) for mn, mx in zip(MINI_MARK, (MARK_W, MARK_H, MARK_GAP)))
        xm = mark_xs(pat, rel[0], rel[-1], xs[0], pxs)
        draw_marks(out, [x - bx0 for x in xm], xs - bx0, ys - by0, pat['col'], a, sz, 0.05*pxs)
    return out, (bx0, by0)


def lerp(a, b, u):
    return a + (b - a)*u


def view_params(i, u):
    """u=0 で中部の帯、u=1 で枠のミニ波形。"""
    ox, oy = cell_strip_origin(i)
    sw = strip_w(i)
    cx = lerp(XC, ox + sw/2, u)
    base_y = lerp(F_BASE, oy + MINI_BASE[i], u)
    pxs = F_PXS*(M_PXS/F_PXS)**u
    mv = F_MV*(MINI_MV[i]/F_MV)**u
    half = lerp(XC, sw/2, u)
    lw = lerp(4.5, 2.2, u)
    b1 = lerp(8, 3, u); b2 = lerp(20, 7, u)
    return cx, base_y, pxs, mv, cx - half, cx + half, lw, (b1, b2)


MINI_LW_ECT = 3.8
MINI_A_NORM = 0.72


def mini(base, i, t, u=1.0, a=1.0, plain=False):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u), plain=plain)
    if u >= 1.0:                                   # 枠からはみ出す大きな波形（VF・トルサード・歯みがき）は枠の中で切る
        x0, y0, x1, y1 = cell_rect(i)
        clip = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        clip.alpha_composite(im, pos)
        box = (x0 + 3, y0 + 33, x1 - 3, y1 - 3)
        base.alpha_composite(clip.crop(box), (box[0], box[1]))
        return
    base.alpha_composite(im, pos)


def cell_state(i, t):
    a_i, b_i = WINDOWS[i]
    if t >= b_i + FLY:
        return 'done'
    if b_i <= t < b_i + FLY:
        return 'landing'
    if t >= T_REV[i] and t < b_i:
        return 'revealed'
    if a_i <= t < T_REV[i]:
        return 'now'
    return 'empty'


def draw_cell(base, i, t, state, a_all, plain=False):
    """state：'empty'（まだ）・'now'（出題中）＝「Q◯ ？」だけ／'revealed'（答えが出た）・'landing'・'done' ＝名前。"""
    x0, y0, x1, y1 = cell_rect(i)
    pat = PATTERNS[i]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a_fill = a_all
    if state in ('empty', 'now'):
        a_all = a_all * (0.5 if state == 'empty' else 1.0)
    if state in ('now', 'revealed', 'landing'):
        pulse = min(1.0, (0.55 + 0.45*math.sin(t*5.0)**2)*1.4)
        edge = WHITE if state == 'now' else pat['col']        # 答えの前は白（色で答えを明かさない）
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=edge + (int(255*pulse*a_all),), width=3)
    else:
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=CARD_FILL + (int(CELL_FILL*a_fill),),
                            outline=CARD_EDGE + (int(255*a_all),), width=2)
    base.alpha_composite(lay)
    if state in ('done', 'landing', 'revealed') and not plain:
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17, a=a_all, max_w=CELL_W - 30)
    elif state in ('done', 'landing'):                         # サムネイル：番号だけ
        put(base, f"{pat['no']}", 22, 700, WHITE, x=x0 + 14, cy=y0 + 17, a=a_all)
    else:
        put(base, f"{pat['no']} ？", 30, 800, WHITE if state == 'now' else DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)


# =====================================================================================
# 画面
# =====================================================================================
def draw_header(base, a):
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


def draw_question(im, i, t):
    """「Q◯ これは？」と、その右のカウントダウンのリング（3・2・1）。ヒントの段階で「ヒント：〇〇」。"""
    a_i, _ = WINDOWS[i]
    a = ramp(t, a_i + 0.62, 0.2) * (1 - ramp(t, T_REV[i] - 0.12, 0.12))   # 前の波形が枠へ移り終わってから（帯とほぼ同時）
    if a <= 0.004:
        return
    q, w1 = PATTERNS[i]['no'], text_w(PATTERNS[i]['no'], 52, 900)
    w2 = text_w('これは？', 56, 900)
    r = RING_R
    gap = 20
    x0 = 540 - (w1 + gap + w2 + gap + 2*r) / 2          # リングの場所も入れて、まん中にそろえる
    put(im, q, 52, 900, YEL, x=x0, cy=Y_NAME, a=a)
    put(im, 'これは？', 56, 900, WHITE, x=x0 + w1 + gap, cy=Y_NAME, a=a)
    h0 = a_i + HINT0
    a_h = a * ramp(t, h0, 0.25)
    if i == 0:                                         # 1問目だけ：正解の数を数えるように（ヒントが出るまで）
        put(im, COUNT_NOTE, 24, 500, GREY, cx=540, cy=Y_HINT, a=a*(1 - ramp(t, h0 - 0.2, 0.2)))
    if a_h > 0.004:
        put(im, f"ヒント：{PATTERNS[i]['hint']}", 36, 800, HINT_COL, cx=540, cy=Y_HINT, a=a_h, max_w=820)
    # 時間のリング：t0 から減りはじめ、7秒（THINK）で空になる。数字は最後の3秒だけ（3・2・1）
    t0 = a_i + T0_OFF
    u = cl((t - t0) / THINK)                           # 0 → 1
    rx = x0 + w1 + gap + w2 + gap + r - 8
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = (rx - r, Y_RING - r, rx + r, Y_RING + r)
    d.ellipse(box, outline=(70, 86, 82, int(255*a)), width=6)
    if u < 1:
        d.arc(box, -90, -90 + 360*(1 - u), fill=YEL + (int(255*a),), width=7)
    im.alpha_composite(lay)
    c0 = a_i + CD0
    if t >= c0:
        n = CD_N - min(CD_N - 1, int((t - c0) // CD_STEP))
        k = (t - c0) % CD_STEP / CD_STEP
        put(im, str(n), 40, 900, WHITE, cx=rx, cy=Y_RING + 2, a=a*ramp(t, c0, 0.1)*(1 - 0.35*ease(k)))


def draw_answer(im, i, t):
    pat = PATTERNS[i]
    _, b_i = WINDOWS[i]
    a = ramp(t, T_REV[i], 0.2) * (1 - ramp(t, b_i - 0.25, 0.25))
    if a <= 0.004:
        return
    if pat['note']:                                # 注意の1行を足す問題（Q8）：3行を少し上に詰めて、案内の下に入れる
        yn, yo, yg = Y_NAME - NOTE_UP[0], Y_ONE - NOTE_UP[1], Y_GUIDE - NOTE_UP[2]
    else:
        yn, yo, yg = Y_NAME, Y_ONE, Y_GUIDE
    put(im, pat['name'], 50, 900, pat['col'], cx=540, cy=yn, a=a, max_w=820)
    put(im, pat['one'], 30, 500, (226, 232, 231), cx=540, cy=yo, a=a, max_w=820)
    put(im, pat['guide'], 28, 800, LEVEL[pat['level']], cx=540, cy=yg, a=a, max_w=820)
    if pat['note']:
        put(im, pat['note'], 24, 700, (236, 241, 240), cx=540, cy=yg + NOTE_DY, a=a, max_w=820)


_GRID = None


def frame(t):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    keep = 1 - ramp(t, DUR - 0.80, 0.35)          # 冒頭へ戻る：クイズの画面を先に消してから
    a_loop = ramp(t, DUR - 0.40, 0.35)            # 冒頭の字を出す（二重にしない）
    draw_header(im, ramp(t, 2.35, 0.35)*keep)

    a_cells = ramp(t, 2.3, 0.4)*keep
    cur = current(t)
    states = [cell_state(i, t) for i in range(N_PAT)]
    flying = states.index('landing') if 'landing' in states else None
    if flying is not None:                         # 縮んで移る波形は、自分の枠の上・ほかの枠の下を通る
        draw_cell(im, flying, t, 'landing', a_cells)
        mini(im, flying, t, ease((t - WINDOWS[flying][1]) / FLY))
    for i in range(N_PAT):
        if i == flying:
            continue
        draw_cell(im, i, t, states[i], a_cells)
        if states[i] == 'done':
            mini(im, i, t, 1.0, a=keep)

    if cur is not None:
        draw_question(im, cur, t)
        draw_answer(im, cur, t)

    # 冒頭：問いかけとタイトル（変形中の名前は出さない）
    a_t = max(1 - ramp(t, 2.0, 0.35), a_loop)
    if a_t > 0:
        put(im, HOOK_Q, 72, 900, YEL, cx=540, cy=520, a=a_t, max_w=880)
        put(im, TITLE_SUB, 36, 500, PURPLE, cx=540, cy=670, a=a_t)
        put(im, TITLE, 150, 900, WHITE, cx=540, cy=800, a=a_t, max_w=880)

    # 最後：コメントのお願い → 保存（声の順）
    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, END_Q, 52, 900, YEL, cx=540, cy=803, a=a_end, max_w=820)
        put(im, END_SAVE, 44, 700, GREEN, cx=540, cy=866, a=ramp(t, T_END + FLY + 2.4, 0.6)*keep)

    a_strip = strip_alpha(t)
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    if a_strip > 0.01:
        lay = featured(t, base_col, a_strip, cur)
        dx = strip_dx(t)
        if dx < W:
            im.alpha_composite(lay.crop((0, 0, W - dx, lay.size[1])), (dx, F_Y0))

    put(im, NOTE1, 24, 400, GREY, x=135, cy=1554, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=1580, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 184, cy=1570, a=0.42)
    return im.convert('RGB')


# =====================================================================================
# サムネイル（透かしなし。答えは出さない）
# =====================================================================================
# 一覧型（第17弾と同じ作り）：見せ始めの時刻（周期の中）。答えの名前は出さず「Q◯」だけ
THUMB_T0 = {i: -0.3 for i in range(N_PAT)}
THUMB_T0.update({3: 0.2, 4: 0.0, 5: -0.2, 7: 0.1, 8: 0.5, 9: 0.9})


def thumb_row_wave(i, x0, x1, y_top, y_bot, mv, span=3.0, lw=3.0):
    """一覧型サムネイルの1行の波形：y_top〜y_bot の上下まん中に、波形（スパイクの先を含む）の (いちばん上＋いちばん下)/2 を置く。"""
    pat = PATTERNS[i]
    pxs = (x1 - x0) / span
    t0 = THUMB_T0[i]
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = t0 + (xs - x0) / pxs
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
    v = v * np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    spk = [(x0 + (ts - t0)*pxs, amp) for ts, amp in spike_times(bl) if rel[0] + 0.03 <= ts <= rel[-1] - 0.03]
    hi = max([float(v.max())] + [1.0 for _ in spk])
    lo = float(v.min())
    base_y = (y_top + y_bot) / 2 + (hi + lo) / 2 * mv
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(4.0*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 2.0*mv) - pad
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], WAVE_GREEN, lw, 1.0, blur=(4, 10))
    sr = spike_runs(spk, xs, ys, mv, ox, oy)
    if sr:
        lay.alpha_composite(spike_layer(size, sr, WAVE_GREEN, lw, 1.0, (4, 10)))
    return lay, (ox, oy)


def thumbnail_list():
    """タイトル → 10問を2列×5段（「Q◯」と波形）→ 下の枠「全10問、何問わかる？」。中身は y 262〜1662（余白を大きく使う）。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    d.line([(505, 264), (575, 264)], fill=(255, 92, 84, 255), width=5)
    put(im, TITLE_SUB, 38, 700, (118, 226, 150), cx=540, cy=310)
    put(im, TITLE, 146, 900, WHITE, cx=540, cy=416, max_w=900)
    put(im, '全部わかる？', 70, 900, YEL, cx=540, cy=540)
    COLS = [(96, 520), (560, 984)]
    NR = (N_PAT + 1) // 2
    Y0, RH = 600, 189
    for i, pat in enumerate(PATTERNS):
        c, r = divmod(i, NR)
        x0, x1 = COLS[c]
        y = Y0 + r*RH
        put(im, pat['no'], 34, 900, YEL, x=x0, cy=y + 28)
        lay, pos = thumb_row_wave(i, x0, x1, y + 52, y + RH - 8, 54.0)
        im.alpha_composite(lay, pos)
        if r < NR - 1:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)], fill=(38, 54, 48, 255), width=1)
    by = Y0 + NR*RH + 17
    d.rounded_rectangle([(210, by), (870, by + 100)], radius=20, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('全', 44, WHITE), (str(N_PAT), 80, YEL), ('問、何問わかる？', 44, WHITE)]
    ims = [text_img(s, sz, 900, col) for s, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 74
    for (s, sz, col), (a, asc) in zip(parts, ims):
        put(im, s, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# =====================================================================================
# 検算
# =====================================================================================
_SRC_MOD = {}


def src_module(folder, mod):
    k = (folder, mod)
    if k not in _SRC_MOD:
        path = os.path.join(ROOT, folder)
        sys.path.insert(0, path)
        try:
            _SRC_MOD[k] = importlib.import_module(mod)
        finally:
            sys.path.remove(path)
    return _SRC_MOD[k]


def src_wave(i, rel):
    """元の回のモデルで、同じパターンを1周期ぶん描いた波形と、スパイクの時刻。"""
    folder, mod, idx, _ = PATTERNS[i]['src']
    m = src_module(folder, mod)
    pat = m.PATTERNS[idx]
    bl = m.periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = m.wave_from(bl, rel)
    if hasattr(m, 'art_apply'):
        v = m.art_apply(pat, rel, v)
    if pat.get('fib'):
        v = v + m.fwave(rel, pat['L'])
    spk = m.spike_times(bl) if hasattr(m, 'spike_times') else []
    return v, pat, spk


def compare_sources():
    """10問それぞれ、元の回のモデルとの最大のずれ（mV）・周期・拍の時刻・スパイク。"""
    rows = []
    for i, pat in enumerate(PATTERNS):
        rel = np.arange(0.0, 2*pat['L'], 0.001)
        v = art_apply(pat, rel, wave_from(periodic_beats(pat, rel[0] - 1, rel[-1] + 1), rel))
        v0, sp, spk0 = src_wave(i, rel)
        spk = spike_times(periodic_beats(pat, rel[0] - 1, rel[-1] + 1))
        ev0 = [round(float(r), 4) for r, *_ in (sp.get('ev') or sp.get('beats'))]
        ev = [round(float(r), 4) for r, *_ in pat['ev']]
        rows.append((pat['no'], pat['src'][3], float(np.abs(v - v0).max()), sp['L'], pat['L'], ev0 == ev,
                     sorted(round(a, 4) for a, _ in spk0) == sorted(round(a, 4) for a, _ in spk), sp['name']))
    return rows


def qrs_ms(f):
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < 0.12)
    return (tt[m].max() - tt[m].min()) * 1000


def check():
    print('問題ごとの時間（a：問題が出る／答え：答えが出る／b：縮み始める）')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']:>3} {pat['name']:<16} a {a:5.1f}  帯 {T_SW[i]:5.1f}  答え {T_REV[i]:5.1f}  b {b:5.1f}"
              f"（{b - a:4.1f}秒）声 {say_len(i):3.1f}秒（{len(pat['say'])}字）  帯の区間 {pat['D']:.2f}s 周期 {pat['L']:.2f}s")
    print(f'最後の問題の終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s（全体 {DUR:.1f}s）')
    print(f'波形の高さ：上 {WAVE_HI:+.2f}mV 下 {WAVE_LO:+.2f}mV → 帯 y {F_BASE - WAVE_HI*F_MV:.0f}〜{F_BASE - WAVE_LO*F_MV:.0f}'
          f'（名前 {Y_NAME:.0f}・ひとこと {Y_ONE:.0f}・案内 {Y_GUIDE:.0f}・ヒント {Y_HINT:.0f}）')
    print('元の回のモデルとのくらべ（1周期×2、1ms ごと）')
    for no, src, dmax, L0, L1, ev_ok, spk_ok, name0 in compare_sources():
        print(f'  {no:>3} ← {src}（元の名前「{name0}」）：ずれ最大 {dmax:.2e} mV、周期 {L0} / {L1}、'
              f'拍の時刻 {"同じ" if ev_ok else "ちがう"}、スパイク {"同じ" if spk_ok else "ちがう"}')
    print('値（モデルから）')
    print(f'  Q1 心房細動：R-R {min(AF_RR)}〜{max(AF_RR)}秒（平均 {60/np.mean(AF_RR):.0f}/分）、f波 RMS {F_COARSE}mV')
    print(f'  Q2 洞頻脈：{60/0.52:.0f}/分、PR（P頂点→R頂点）0.15秒')
    print(f'  Q3 二段脈：洞調律 {60/0.8:.0f}/分、PVC は直前のRから 0.48秒、QRS {qrs_ms(qrs_pvc):.0f}ms、休みは2拍ぶん（1.60秒）')
    print('  Q4 粗いVF：3〜9Hz（180〜540/分）、約±0.4mV')
    print(f'  Q5 完全房室ブロック：心房 {60/CAVB_PP:.0f}/分、心室 {60/CAVB_RR:.0f}/分（接合部・幅の狭いQRS）')
    print('  Q6 ウェンケバッハ：PR 0.18 → 0.28 → 0.33秒、4つめのPが抜ける（4:3）')
    print('  Q7 高K：60/分、T波 0.82mV（幅 0.23秒・左右対称）')
    print('  Q8 偽VT：洞調律 75/分の上に 4.5Hz の揺れ（0.45〜3.55秒）')
    print(f'  Q9 ペーシング不全：60/分の心室ペーシング、3拍目はスパイクだけ（QRS {qrs_ms(qrs_paced):.0f}ms）')
    print(f'  Q10 トルサード：QT延長の洞調律（60/分）→ {TDP_B - TDP_A:.2f}秒、約{TDP_F*60:.0f}/分 → 自然に止まる')
    print('字の幅（上限 820px。入らないと小さくなる）')
    for pat in PATTERNS:
        ws = [text_w(pat['name'], 50, 900), text_w(pat['one'], 30, 500), text_w(pat['guide'], 28, 800)]
        flag = '' if max(ws) <= 820 else '  ← 小さくなる'
        print(f"  {pat['no']:>3} 名前 {ws[0]:4d}px ひとこと {ws[1]:4d}px 案内 {ws[2]:4d}px{flag}  {pat['guide']}")
    print('ヒント（36px、上限 820px）と色付けの場所（周期の中の秒）')
    for pat in PATTERNS:
        hl = '全体' if pat['hint_hl'] is ALL else '・'.join(f'{x:.2f}〜{y:.2f}' for x, y in pat['hint_hl'])
        print(f"  {pat['no']:>3} 「ヒント：{pat['hint']}」 {text_w('ヒント：' + pat['hint'], 36, 800)}px  色：{hl}")
    print('枠の名前（上限 370px）：', ', '.join(f"{p['no']} {text_w(p['no'] + ' ' + p['name'], 22, 700)}" for p in PATTERNS))


# =====================================================================================
# 書き出し
# =====================================================================================
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


# 音（3種類。ピッとカウントの音を、高さも音色もはっきり分ける）
#   モニター音「ピッ」：正弦波 960Hz（幅の広い拍は 720Hz）、80ms、減衰 45ms、ピーク 0.20
#   カウント「コッ」  ：木の音。420Hz＋1180Hz の短い減衰（14ms・6ms）＋2ms の雑音のクリック、60ms、ピーク 約0.22
#   答え「ポーン」    ：明るいベル。1568Hz（ソ）＋倍音 3136・4704Hz、0.9秒、減衰 0.28秒、ピーク 約0.18（ピッより高く、長く響く）
BEEP_F, BEEP_F_WIDE, BEEP_AMP, BEEP_DUR, BEEP_TAU = 960.0, 720.0, 0.20, 0.08, 0.045
TOK_F = (420.0, 1180.0)
POM_F = 1568.0
DUCK = 0.5                        # 最後の3秒（数字「3・2・1」と「コッ」）のあいだ、モニター音を -6dB


def _tone(a, sr, ts, f, amp=0.2, dur=0.08, tau=0.045):
    n = len(a)
    L = int(dur*sr)
    tt = np.arange(L)/sr
    s = amp*np.minimum(1, tt/0.004)*np.exp(-tt/tau)*np.sin(2*np.pi*f*tt)
    _add(a, sr, ts, s)


def _add(a, sr, ts, s):
    n, L = len(a), len(s)
    j = int(ts*sr)
    if 0 <= j < n:
        a[j:j+L] += s[:max(0, min(L, n-j))]


def tok_wave(sr=44100):
    """カウントの「コッ」（木の音）。"""
    tt = np.arange(int(0.06*sr))/sr
    att = np.minimum(1, tt/0.0008)
    s = (np.exp(-tt/0.014)*np.sin(2*np.pi*TOK_F[0]*tt) + 0.45*np.exp(-tt/0.006)*np.sin(2*np.pi*TOK_F[1]*tt))*att
    nz = np.random.RandomState(7).normal(0, 1, len(tt))
    nz = np.diff(np.concatenate([[0.0], nz]))*np.exp(-tt/0.002)            # 高い音だけの短い雑音（打った瞬間）
    s = s + 0.25*nz
    return 0.22*s/np.abs(s).max()


def pom_wave(sr=44100):
    """答えの「ポーン」（明るいベル）。"""
    tt = np.arange(int(0.9*sr))/sr
    att = np.minimum(1, tt/0.006)
    s = (np.sin(2*np.pi*POM_F*tt) + 0.35*np.exp(-tt/0.15)*np.sin(2*np.pi*2*POM_F*tt)
         + 0.12*np.exp(-tt/0.08)*np.sin(2*np.pi*3*POM_F*tt))*att*np.exp(-tt/0.28)
    return 0.18*s/np.abs(s).max()


def beep_wave(f=BEEP_F, sr=44100):
    """モニターの「ピッ」（_tone と同じ形）。"""
    a = np.zeros(int(BEEP_DUR*sr) + 1, dtype=np.float64)
    _tone(a, sr, 0.0, f, BEEP_AMP, BEEP_DUR, BEEP_TAU)
    return a


def beep_events():
    """モニター音：中部の帯の R が画面の中央を通るとき（帯が出ているときだけ）。[(時刻, 周波数)]"""
    out = []
    for t0, t1 in pieces():
        tau0 = tau_c(t0 + 1e-6)
        for r, k, i in STRIP:
            if k in NO_BEEP:
                continue
            ts = t0 + (r - tau0)
            if not (t0 <= ts < t1) or ts > DUR - 0.3:
                continue
            if strip_alpha(ts) < 0.5:
                continue
            if i is not None and PATTERNS[i].get('gain') is not None:
                g = PATTERNS[i]['gain'](np.array([r - SEGS[i][0]]), PATTERNS[i]['L'])[0]
                if abs(g) < 0.5:                       # トルサードのあいだは、モニターが拍を数えない
                    continue
            out.append((ts, BEEP_F_WIDE if k in WIDE else BEEP_F))
    return out


def beeps(path, sr=44100):
    """モニター音「ピッ」（ヒントとカウントダウンのあいだは -6dB）＋カウント「コッ」（3・2・1）＋答え「ポーン」。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for ts, f in beep_events():
        duck = any(WINDOWS[i][0] + CD0 <= ts < T_REV[i] for i in range(N_PAT))
        _tone(a, sr, ts, f, amp=BEEP_AMP*(DUCK if duck else 1.0), dur=BEEP_DUR, tau=BEEP_TAU)
    for k in range(len(HOOK)):                         # 冒頭の変形のたびに
        _tone(a, sr, HOOK_T0 + k*HOOK_STEP, 720.0, dur=0.07, tau=0.04)
    tok, pom = tok_wave(sr), pom_wave(sr)
    for i in range(N_PAT):
        for k in range(CD_N):                          # カウントダウン：木の音「コッ」
            _add(a, sr, WINDOWS[i][0] + CD0 + k*CD_STEP, tok)
        _add(a, sr, T_REV[i], pom)                     # 答え：明るい「ポーン」
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def sound_figure(path, sr=44100):
    """音のちがいを図に：上＝3つの音の波形（同じ時間・同じ縦軸）、中＝周波数（スペクトル）、下＝1問ぶんの音の並び。"""
    Wf, Hf = 1600, 1420
    im = Image.new('RGB', (Wf, Hf), (12, 18, 16))
    d = ImageDraw.Draw(im)
    sounds = [('モニター「ピッ」 960Hz（幅の広い拍 720Hz）', beep_wave(), (130, 232, 172)),
              ('カウント「コッ」 木の音 420＋1180Hz', tok_wave(), (255, 214, 64)),
              ('答え「ポーン」 ベル 1568Hz＋倍音', pom_wave(), (236, 120, 255))]
    put(im := im.convert('RGBA'), '音のちがい（第28弾 クイズ）', 40, 800, WHITE, x=40, cy=40)
    d = ImageDraw.Draw(im)
    # 上：波形（0〜300ms、縦は ±0.25）
    x0, x1, yt = 60, Wf - 40, 90
    rowh = 150
    for k, (nm, w, col) in enumerate(sounds):
        yc = yt + rowh*k + rowh/2 + 20
        put(im, nm, 24, 700, col, x=x0, cy=yt + rowh*k + 18)
        d.line([(x0, yc), (x1, yc)], fill=(50, 64, 60), width=1)
        n = int(0.30*sr)
        ww = np.zeros(n); ww[:min(n, len(w))] = w[:n]
        xs = x0 + np.arange(n)/n*(x1 - x0)
        ys = yc - ww/0.25*(rowh/2 - 25)
        d.line(list(zip(xs.tolist(), ys.tolist())), fill=col, width=1)
    for ms in range(0, 301, 50):
        x = x0 + ms/300*(x1 - x0)
        put(im, f'{ms}ms', 18, 500, GREY, cx=x, cy=yt + rowh*3 + 30)
    # 中：スペクトル（0〜4kHz、dB）
    ys0 = yt + rowh*3 + 70
    hs = 380
    put(im, '周波数（スペクトル、0〜5000Hz。縦は dB、それぞれの最大を 0dB、-40dB まで）', 24, 700, WHITE, x=x0, cy=ys0)
    top, bot = ys0 + 30, ys0 + 30 + hs - 60
    d.rectangle([x0, top, x1, bot], outline=(50, 64, 60))
    for f in range(0, 5001, 500):
        x = x0 + f/5000*(x1 - x0)
        d.line([(x, top), (x, bot)], fill=(30, 42, 38))
        put(im, f'{f}', 18, 500, GREY, cx=x, cy=bot + 16)
    for nm, w, col in sounds:
        N = 1 << 16
        sp = np.abs(np.fft.rfft(w, N)); fr = np.fft.rfftfreq(N, 1/sr)
        db = 20*np.log10(sp/sp.max() + 1e-9)
        m_ = fr <= 5000
        xs = x0 + fr[m_]/5000*(x1 - x0); yy = top + np.clip(-db[m_], 0, 40)/40*(bot - top)
        d.line(list(zip(xs.tolist(), yy.tolist())), fill=col, width=2)
    # 下：Q2 の1問ぶんの音（声なし）
    yb = bot + 60
    i = 1
    a_i, b_i = WINDOWS[i]
    t0, t1 = a_i, b_i
    put(im, f'Q2 の1問ぶんの音（{t1 - t0:.1f}秒。最後の3秒のカウントのあいだはピッを -6dB）', 24, 700, WHITE, x=x0, cy=yb)
    tr = np.zeros(int(DUR*sr), dtype=np.float32)
    tmp = os.path.join(os.path.dirname(path), '_fig.wav')
    beeps(tmp, sr)
    with wave.open(tmp) as wv:
        tr = np.frombuffer(wv.readframes(wv.getnframes()), dtype=np.int16).astype(np.float32)/32767
    os.remove(tmp)
    seg = tr[int(t0*sr):int(t1*sr)]
    yc = yb + 170
    hh = 110
    put(im, '波形が見え始めて1.5秒でヒント → 最後の3秒でカウント 3 → 2 → 1（コッ）→ 答え（ポーン）', 20, 600, YEL, x=x0, cy=yb + 30)
    cd = a_i + CD0
    for tt, lab, c in [(T_HINT[i] - t0, 'ヒント', (236, 120, 255)), (cd - t0, '3', YEL), (cd - t0 + CD_STEP, '2', YEL),
                       (cd - t0 + 2*CD_STEP, '1', YEL), (T_REV[i] - t0, '答え', (236, 120, 255))]:
        x = x0 + tt/(t1 - t0)*(x1 - x0)
        d.line([(x, yc - hh - 10), (x, yc + hh)], fill=(70, 70, 50))
        put(im, lab, 20, 700, c, x=x + 4, cy=yc - hh - 4)
    step = max(1, len(seg)//(x1 - x0))
    for px in range(x1 - x0):
        ch = seg[px*step:(px + 1)*step]
        if len(ch):
            d.line([(x0 + px, yc - ch.max()/0.25*hh), (x0 + px, yc - ch.min()/0.25*hh)], fill=(200, 210, 205))
    for sec in range(0, int(t1 - t0) + 1):
        x = x0 + sec/(t1 - t0)*(x1 - x0)
        put(im, f'{sec}s', 18, 500, GREY, cx=x, cy=yc + hh + 18)
    im.convert('RGB').save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel28_quiz.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--sounds', action='store_true', help='音のちがいの図 out/sounds_reel28_quiz.png')
    ap.add_argument('--jobs', type=int, default=2)             # CPU は4つ。ほかの作業と分けあうので 2
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel28_quiz_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel28_quiz_hq.mp4')
    if o.check:
        check(); return
    if o.sounds:
        print(sound_figure(os.path.join(HERE, 'out', 'sounds_reel28_quiz.png'))); return
    os.makedirs(os.path.dirname(o.out), exist_ok=True)
    if o.thumb:
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel28_quiz_list.png')
        thumbnail_list().save(p); print(p); return
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
                    '-movflags', '+faststart', o.out], check=True)
    print(o.out)


if __name__ == '__main__':
    main()
