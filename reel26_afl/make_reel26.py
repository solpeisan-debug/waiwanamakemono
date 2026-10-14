"""第26弾 心房細動・心房粗動 まず覚えたい14パターン（第21弾と同じ作り＋この回だけの見せ方）

配置：
- 上部：①〜⑧ のミニ波形（2列×4段。心房細動のはじまり → f波 → 心拍数 → QRSの形）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと（うしろに、看護師の動きを色で）。
  波形の下に「R-R のものさし」（拍と拍のあいだの長さを横棒で。そろう＝規則的、バラバラ＝不規則）。
  帯の左上に心拍数カウンター「♥ 150 /分」（第24弾と同じ見た目。拍が中央を通る＝ピッのたびに、その拍の R-R から計算）
- 下部：⑨〜⑭ のミニ波形（2列×3段。WPW → 止まるとき（徐脈頻脈症候群）→ 心房粗動 4:1 → 2:1 → 伝導比が変わる → 1:1）
- ⑩ 徐脈頻脈症候群：止まったあとの休み（ポーズ）のあいだ、秒数がカウントアップする
- 冒頭0〜3秒：問いかけ「細動？粗動？見分けられる？」。最後：「保存して見返してね」と「何個わかった？コメントで教えてね」

見分けのポイント（画面のひとことで出す）：
- 心房細動：P波がなく、R-R が不規則（f波は粗いことも、細かくて平らに見えることもある）
- 心房粗動：のこぎり状のF波（II誘導で下向き、約300/分）。心拍数は伝導比で決まる（2:1＝150、4:1＝75）

波形は、パターンの周期でくり返す決まった形（乱数の種を固定）。
中部の帯は最初から最後まで消えない（2026-10-13）。紹介が終わると、そのパターンのコピーだけが縮んで枠へ飛び、
帯に見えている拍はその場で次のパターンの形へ変わる（関係のある並びは直接 1.0秒、関係のない病態へは基準の洞調律を通る。下の「中部の帯」）。
II誘導を想定。

使い方:
    python3 make_reel26.py              # 書き出し・60fps（--jobs 2）
    python3 make_reel26.py --still 20   # 1コマだけ
    python3 make_reel26.py --check      # 検算・タイミング表
    python3 make_reel26.py --thumb      # サムネイル（透かしなし）
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
G_MINOR = (10, 21, 17)           # 方眼の細い線（1mm＝14px）。線が多くなったぶん、前（31.5px間隔）より薄く
G_MAJOR = (27, 46, 38)           # 方眼の太い線（5mm＝70px＝0.2秒）
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (70, 82, 82)
CARD_FILL = (9, 19, 16)
CARD_EDGE = (60, 78, 72)
PURPLE = (178, 150, 240)
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)

C_AF = (110, 200, 255)           # 心房細動：はじまり・f波・心拍数（①〜⑤）
C_AFQ = (255, 196, 90)           # 心房細動：QRSの形・リズムが変わる（⑥〜⑨）
C_STOP = (255, 128, 112)         # 心房細動が止まるとき（⑩ 徐脈頻脈症候群）
C_FL = (255, 140, 196)           # 心房粗動（⑪〜⑭）

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
RR = 0.80                        # 前後の洞調律 75/分
PR = 0.16                        # P頂点 → R頂点
FF = 0.20                        # 心房粗動のF波の間隔（300/分）


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.022)


def p_ect(t):                     # PACの P'：小さく、とがって、少し二相性
    return 0.13*_g(t, 0.0, 0.015) - 0.04*_g(t, 0.032, 0.013)


def qrs_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_fast(t):                  # 速いときの幅の狭いQRS：Tが早く、少し小さい（R-R 0.36秒でも次の拍に重ならない）
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.22*_ga(t, 0.215, 0.045, 0.034))


def qrs_flutter(t):               # 心房粗動で伝わった拍：幅の狭いQRS。T波は小さく、F波に埋もれやすい
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.12*_ga(t, 0.27, 0.060, 0.042))


def qrs_11(t):                    # 1:1伝導（300/分）：幅の狭いQRS、Tはさらに早く小さい
    return (-0.08*_g(t, -0.030, 0.008) + 0.95*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.14*_ga(t, 0.125, 0.026, 0.022))


def qrs_aberrant(t):              # 変行伝導・脚ブロック（右脚ブロック型）：幅が広く、終わりのS波が幅広くなまる
    return (0.80*_ga(t, 0.0, 0.012, 0.015) - 0.42*_ga(t, 0.062, 0.022, 0.036)
            + 0.12*_ga(t, 0.30, 0.060, 0.045))


def _preex(w, a, with_t=True):
    """WPWの心房細動の1拍：副伝導路を通る幅の広いQRS（立ち上がりがなだらか＝デルタ波）、逆向きのT。
    w（幅）と a（大きさ）を拍ごとに少し変える。向き（軸）は変えない。"""
    def f(t):
        v = a*(0.30*_ga(t, -0.030*w, 0.020*w, 0.012) + 0.90*_ga(t, 0.0, 0.016*w, 0.018*w)
               - 0.12*_g(t, 0.050*w, 0.014))
        if with_t:
            v = v - 0.22*_ga(t, 0.175, 0.038, 0.030)
        return v
    return f


PREEX = {'D1': (0.92, 0.80), 'D2': (1.00, 1.00), 'D3': (1.15, 1.10)}   # (幅, 大きさ)


KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍（前後のつなぎ・①⑩の洞調律）
    'C': (qrs_normal, p_ect, 0.14),         # ① PAC（早い P'）
    'A': (qrs_normal, None, 0.0),           # 心房細動で伝わった拍（P波なし）
    'F': (qrs_flutter, None, 0.0),          # 心房粗動で伝わった拍（P波なし、T波は小さい）
    'S': (qrs_fast, None, 0.0),             # 速い心房細動の拍
    'G': (qrs_11, None, 0.0),               # 1:1伝導の拍
    'B': (qrs_aberrant, None, 0.0),         # 変行伝導・脚ブロックの拍（幅が広い）
    'D1': (_preex(*PREEX['D1']), None, 0.0),  # WPWの心房細動（幅・大きさが少しずつちがう）
    'D2': (_preex(*PREEX['D2']), None, 0.0),
    'D3': (_preex(*PREEX['D3']), None, 0.0),
}
WIDE = {'B', 'D1', 'D2', 'D3'}              # 幅の広い拍（モニター音を低く）
ALL = [(-1e9, 1e9)]                         # 全部をその色で


# --- 連続した波形（パターンの周期 L でくり返す） ------------------------------------
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


# 心房細動のf波：5〜8Hz（300〜480/分）の不規則な揺れ。LITFL：粗い f波は 0.5mm（0.05mV）より大きい、細かい f波は 0.5mm 未満
# 2026-10-14 専門医レビュー：③の細かいf波は山から谷 0.03〜0.04mV に（前は 0.056mV で、山から谷で測ると 0.5mm を少しこえていた）
F_COARSE, F_MID, F_FINE = 0.045, 0.028, 0.0068    # RMS（mV）。山の高さは RMS の約2〜2.5倍


def art_f(amp, seed):
    def f(rel, L):
        return band_noise(rel, L, 5.0, 8.0, amp, seed)
    return f


# 心房粗動のF波：II誘導で下向きの「のこぎり」。ゆっくり下がる（0.144秒）→ すばやく上がる（0.056秒）、を 0.2秒（300/分）ごとに。
# 平らな区間（基線）を作らない（LITFL Atrial Flutter：inverted flutter waves in II, III, aVF／Loss of the isoelectric baseline）。
# 2026-10-14 専門医レビュー：前の形は1周期の約60%がほぼ平らで、「平らな基線の上に下向きのP波」にも見えたので直した。
# 1周期の形を決めて、なめらかに（12倍音まで）くり返す。山から谷まで約 0.25mV
FL_DOWN = 0.72                    # 1周期のうち、下がっている割合（0.72×0.2秒＝0.144秒。残り 0.056秒で上がる）


def _flutter_coef(n_h=12):
    x = np.linspace(0, 1, 2048, endpoint=False)
    xd = np.clip(x / FL_DOWN, 0, 1)
    xu = np.clip((x - FL_DOWN) / (1 - FL_DOWN), 0, 1)
    # 下がり：はじめは少しゆるく、しだいに急に（下に凸のカーブ）。上がり：すばやく、上でなめらかに
    y = np.where(x < FL_DOWN, -(0.55*xd + 0.45*xd**2), -1.0 + (1 - (1 - xu)**2))
    c = np.fft.rfft(y) / len(x)
    return [(k, 2*c[k]) for k in range(1, n_h + 1)]


_FL_COEF = _flutter_coef()
_FL_PP = None


def flutter_wave(rel, amp=0.25, phase=0.60):
    """F波（山から谷まで amp mV）。rel=0 は、のこぎりの1周期の phase の位置。"""
    global _FL_PP
    if _FL_PP is None:
        xx = np.linspace(0, 1, 2000, endpoint=False)
        yy = sum((c*np.exp(2j*np.pi*k*xx)).real for k, c in _FL_COEF)
        _FL_PP = yy.max() - yy.min()
    x = rel / FF + phase
    y = sum((c*np.exp(2j*np.pi*k*x)).real for k, c in _FL_COEF)
    return y * amp / _FL_PP


def art_flutter(amp=0.25):
    def f(rel, L):
        return flutter_wave(rel, amp)
    return f


def rr_ev(rrs, kinds='A'):
    """R-R間隔の列 → 1周期の拍 [(R頂点の時刻, 種類)]、周期 L。kinds は1文字か、拍ごとの種類のリスト。"""
    out, t = [], 0.0
    for j, d in enumerate(rrs):
        out.append((round(t, 4), kinds if isinstance(kinds, str) else kinds[j]))
        t += d
    return out, round(t, 4)


# 各パターンの R-R（秒）
RR_COARSE = [0.62, 0.95, 0.70, 1.10, 0.58, 0.85]            # ② 平均75/分
RR_FINE = [0.80, 0.56, 1.02, 0.74, 0.66, 1.02]              # ③ 平均75/分
RR_FAST = [0.38, 0.47, 0.40, 0.55, 0.36, 0.44, 0.50, 0.40]  # ④ 平均137/分
RR_SLOW = [1.05, 1.40, 1.15, 1.60]                          # ⑤ 平均46/分
RR_ASH = [0.70, 1.12, 0.42, 0.66, 0.60, 0.78, 0.52]         # ⑥ 長い R-R（1.12）の直後の短い R-R（0.42）で来た拍が変行伝導
ASH_K = 3                                                   # ⑥ 変行伝導の拍（4つめ、2.24秒）
RR_BBB = [0.72, 0.95, 0.60, 0.88, 1.05, 0.80]               # ⑦ 平均72/分
RR_CHB = [1.25]*4                                           # ⑧ 接合部補充調律 48/分（規則的）
RR_WPW = [0.26, 0.21, 0.32, 0.24, 0.20, 0.29, 0.34, 0.23, 0.27, 0.22, 0.30, 0.25]   # ⑨ 平均230/分、最短300/分
K_WPW = ['D2', 'D1', 'D3', 'D2', 'D1', 'D3', 'D2', 'D3', 'D1', 'D2', 'D3', 'D1']
RR_VAR = [0.4, 0.8, 0.4, 0.6, 0.8, 0.4]                     # ⑬ 2:1・4:1・2:1・3:1・4:1・2:1（F-F 0.2秒の倍数）

# ① 心房細動の始まり：洞調律（75/分）3拍 → T波の終わりにPAC（早いP'）→ そこから R-R がバラバラ（平均約125/分）
PAF_SINUS = [0.0, 0.8, 1.6]
PAF_PAC = 2.06                                              # PAC の R（P' は 0.14秒前、直前の拍のT波の終わり）
RR_PAF = [0.42, 0.64, 0.38, 0.70, 0.44, 0.58]               # PAC のあとの心房細動（ものさしでバラバラが見えるよう、ばらつきを大きめに）
PAF_F0 = 1.98                                               # f波が始まる時刻
# ⑩ 徐脈頻脈症候群：心房細動（約130/分）が止まる → 洞結節の回復が遅れて長い休み（ポーズ）→ 遅い洞調律
RR_TB_AF = [0.48, 0.42, 0.56, 0.40]                         # 心房細動の R-R
TB_PAUSE = 3.20                                             # 最後の心房細動の拍 → 最初の洞調律の拍（LITFL：洞停止は 3秒超）
TB_SINUS_RR = 1.00                                          # 回復した洞調律（60/分）
TB_SINUS_N = 3                                              # 1周期の中の洞調律の拍の数（2026-10-14 2→3：タイマーを中央の基準にして、止まった値を見せる時間をとったため）


def _paf_ev():
    ev = [(t, 'N') for t in PAF_SINUS] + [(PAF_PAC, 'C')]
    t = PAF_PAC
    for d in RR_PAF:
        t = round(t + d, 4); ev.append((t, 'A'))
    return ev, round(t + 0.50, 4)                          # 最後の拍から 0.50秒で次のパターン


def _tb_ev():
    ev, t = [(0.0, 'A')], 0.0
    for d in RR_TB_AF:
        t = round(t + d, 4); ev.append((t, 'A'))
    t_last = t
    t1 = round(t_last + TB_PAUSE, 4)
    ev += [(round(t1 + j*TB_SINUS_RR, 4), 'N') for j in range(TB_SINUS_N)]
    return ev, t_last, t1, round(t1 + TB_SINUS_N*TB_SINUS_RR, 4)


EV_PAF, L_PAF = _paf_ev()
EV_TB, TB_P0, TB_P1, L_TB = _tb_ev()                       # TB_P0〜TB_P1 が休み
EV_COARSE, L_COARSE = rr_ev(RR_COARSE)
EV_FINE, L_FINE = rr_ev(RR_FINE)
EV_FAST, L_FAST = rr_ev(RR_FAST, 'S')
EV_SLOW, L_SLOW = rr_ev(RR_SLOW)
EV_ASH, L_ASH = rr_ev(RR_ASH, ['A']*ASH_K + ['B'] + ['A']*(len(RR_ASH) - ASH_K - 1))
T_ASH = EV_ASH[ASH_K][0]
EV_BBB, L_BBB = rr_ev(RR_BBB, 'B')
EV_CHB, L_CHB = rr_ev(RR_CHB)
EV_WPW, L_WPW = rr_ev(RR_WPW, K_WPW)
EV_VAR, L_VAR = rr_ev(RR_VAR, 'F')


def _window(r, a, b, e=0.08):
    """周期の中の a〜b 秒だけ 1（端は e 秒でなめらかに）。"""
    w = np.minimum(np.clip((r - a) / e, 0, 1), np.clip((b - r) / e, 0, 1))
    return w*w*(3 - 2*w)


def art_f_part(amp, seed, a, b):
    """f波を、周期の中の a〜b 秒だけ出す（①・⑩）。"""
    def f(rel, L):
        return band_noise(rel, L, 5.0, 8.0, amp, seed) * _window(np.mod(rel, L), a, b)
    return f


# 14パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、連続した波形 art、色を付ける範囲 hl
PATTERNS = [
    dict(no='①', name='心房細動の始まり', col=C_AF, hint='急にバラバラ',
         one='洞調律から、急にR-Rがバラバラ', tag='new',
         ev=EV_PAF, L=L_PAF, art=art_f_part(F_MID, 30, PAF_F0, L_PAF + 0.2), hl=[(PAF_F0 - 0.05, L_PAF + 0.3)]),
    dict(no='②', name='心房細動（f波が粗い）', col=C_AF, hint='f波が大きい',
         one='P波なし、R-Rがバラバラ', tag='new',
         ev=EV_COARSE, L=L_COARSE, art=art_f(F_COARSE, 31), hl=ALL),
    dict(no='③', name='心房細動（f波が細かい）', col=C_AF, hint='ほぼ平ら',
         one='P波なし・基線はほぼ平ら。R-Rで判断', tag='new',
         ev=EV_FINE, L=L_FINE, art=art_f(F_FINE, 32), hl=ALL),
    dict(no='④', name='頻脈性の心房細動', col=C_AF, hint='速くバラバラ',
         one='バラバラで速い（100/分超）', tag='vital',
         ev=EV_FAST, L=L_FAST, art=art_f(F_MID, 33), hl=ALL),
    dict(no='⑤', name='徐脈性の心房細動', col=C_AF, hint='遅くバラバラ',
         one='バラバラで遅い（60/分未満）', tag='vital',
         ev=EV_SLOW, L=L_SLOW, art=art_f(F_MID, 34), hl=ALL),
    dict(no='⑥', name='アシュマン現象', col=C_AFQ, hint='1拍だけ幅広い',
         one='長いR-Rのあと、早い1拍が幅広い', tag='ecg12',
         ev=EV_ASH, L=L_ASH, art=art_f(F_MID, 35), hl=[(T_ASH - 0.10, T_ASH + 0.40)]),
    dict(no='⑦', name='心房細動＋脚ブロック', col=C_AFQ, hint='全部幅広い',
         one='全部の拍が幅広く、同じ形', tag='ecg12',
         ev=EV_BBB, L=L_BBB, art=art_f(F_MID, 36), hl=ALL),
    dict(no='⑧', name='心房細動＋完全房室ブロック', col=C_AFQ, hint='規則的で遅い',
         one='f波なのに、R-Rが規則的で遅い', tag='report',
         ev=EV_CHB, L=L_CHB, art=art_f(F_COARSE, 37), hl=ALL),
    dict(no='⑨', name='WPWの心房細動', col=C_AFQ, hint='幅広く超速い',
         one='幅広く、とても速く、バラバラ', tag='report',
         ev=EV_WPW, L=L_WPW, art=art_f(F_MID, 38), hl=ALL),
    dict(no='⑩', name='徐脈頻脈症候群', col=C_STOP, hint='止まって長い休み',
         one='細動が止まったあと、長い休み', tag='report',
         ev=EV_TB, L=L_TB, art=art_f_part(F_MID, 39, -0.3, TB_P0 + 0.12), hl=ALL),
    dict(no='⑪', name='心房粗動（4:1）', col=C_FL, hint='のこぎり',
         one='のこぎり状のF波（約300/分）', tag='new',
         ev=[(0.0, 'F')], L=4*FF, art=art_flutter(), hl=ALL),
    dict(no='⑫', name='心房粗動（2:1）', col=C_FL, hint='150で規則的',
         one='150/分で規則的なら粗動を疑う', tag='vital',
         ev=[(0.0, 'F')], L=2*FF, art=art_flutter(), hl=ALL),
    dict(no='⑬', name='心房粗動（伝導比が変わる）', col=C_FL, hint='不規則な粗動',
         one='R-Rが不規則。心房細動と似る', tag='ecg12',
         ev=EV_VAR, L=L_VAR, art=art_flutter(), hl=ALL),
    dict(no='⑭', name='心房粗動（1:1）', col=C_FL, hint='とても速い',
         one='F波が全部伝わる。約300/分', tag='report',
         ev=[(0.0, 'G')], L=FF, art=art_flutter(0.16), hl=ALL),
]
PAT = {p['no']: p for p in PATTERNS}
I_ASH, I_TB, I_FL41 = 5, 9, 10                              # ⑥ アシュマン現象・⑩ 徐脈頻脈症候群・⑪ 粗動4:1 の番号（0から）


def art_apply(pat, rel, v):
    """パターンの連続した波形を足す：v + art(rel)（周期 L でくり返す）"""
    if pat.get('art'):
        v = v + pat['art'](rel, pat['L'])
    return v


N_PAT = len(PATTERNS)

# ①の紹介は、心房細動の5拍め（4.64秒）が右端の 0.35秒先に来るまで（洞調律 → PAC → バラバラ、を通して見せる）
PAF_SHOW = 4.64


def beat_wave(tau, r, kind):
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    return v


def wave_from(beats, tau):
    v = np.zeros_like(tau)
    for r, k, *_ in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, r, k)
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


# --- 中部の帯：冒頭のフック ---------------------------------------------------------
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①（洞調律 → 心房細動の始まり）が右端から入ってくる。
T_STOP, T_GO = 0.6, 2.9
FREEZE = T_GO - T_STOP
T_TITLE = 4.6                     # 冒頭の1文（声 4.42秒、0.10秒から）が入り、見出しと枠が出そろう長さ
END_HOLD = 7.55                   # 14個そろってからの時間（⑭→基準へ形が変わる 1.15秒・まとめ 4.51秒（2026-10-14 録り直し）・保存 1.38秒の2文、冒頭へ戻る時間）
HOOK = [1, 7, 8, 10, 13]          # ②粗い心房細動 → ⑧完全房室ブロック → ⑨WPW → ⑪粗動4:1 → ⑭粗動1:1
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.8, 0.38, 0.12
HANDOFF_EARLY = 0.35

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（R頂点 1mV 〜 下 0.4mV）→ R-R のものさし
CELL_W, CELL_H, CELL_PITCH = 400, 96, 104
TOP_Y = [372 + k*CELL_PITCH for k in range(4)]          # ①〜⑧（2列×4段）。見出しとともに 24px 上げた（検査役 2026-10-06）
BOT_Y = [1538 - CELL_H - (2 - k)*CELL_PITCH for k in range(3)]   # ⑨〜⑭（2列×3段）。下端 1538
_TOP_END = TOP_Y[-1] + CELL_H      # ④⑧の下端
_BOT_TOP = BOT_Y[0]                # ⑨⑫の上端
RULER_DY = 88                      # 波形の基線 → ものさし（⑥の深いS波が棒に触れないよう 72→88）
ONE_GAP = 24                       # ひとこと → 波形の上端（16→24）
# 見た目の上端（名前の字の上）〜下端（ものさしの目盛り）で余白をそろえる
_MID_H = 22 + 54 + ONE_GAP + 30 + 140 + RULER_DY + 8
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + ONE_GAP + 30 + 140
RULER_Y = F_BASE + RULER_DY
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


# --- 中部の帯（①〜⑭〜最後）：画面の波形が、その場で次の形へ変わる（2026-10-13、第25弾と同じ考え方） ------
# 帯は最初から最後まで消えない。名前が消えると、そのパターンのコピーだけが縮んで枠へ飛び、
# 帯に見えている拍は、すべていっしょに、その場で次のパターンの形へ変わる（流れは止めない）。
# - 拍の並び（Arr）：パターンごとの拍の並びを紙（τ）に固定したもの。拍には帯全体で通しの番号 k がある
# - 形が変わるあいだ（重み w：0→1）、拍 k の位置は 2つの並びの位置の内分 (1-w)·X(k) + w·Y(k)。
#   どちらの並びも k について増えていくので、内分も増えていく（拍が入れかわったり、消えたり、増えたりしない。跳ばない）。
#   次の並び Y は、形が変わるまん中の時刻に中央にいちばん近い拍が、2つの並びで同じ位置になるように置く
#   （中央の拍はそのまま流れ、まわりの拍が少しずつ寄ったり離れたりする＝心拍数・伝導比・R-R のばらつきがなめらかに変わる）
# - 拍の形は、山の高さ・位置・幅の数値を少しずつ変える（BPAR。重ねないので、山が2つに割れない）
# - f波・F波は、2つの並びの波を w でまぜる（粗い → 細かい は大きさが、粗動の 4:1 → 2:1 → … はF波が同じまま）
# - 名前・ひとこと・声が出ているあいだは、そのパターンの形そのもの
# - 進み方（関係のある並び）：次の形へ直接（MORPH_T 秒）
# - 関係のない病態へ移るところ：いったん基準の洞調律（75/分）にもどしてから（VIA_T 秒で基準へ・VIA_HOLD 秒そのまま・VIA_T 秒で次へ）
# - ⑭のあと：基準の洞調律へもどして最後の画面へ。動画の終わりが冒頭とつながる

# 拍の形（数値でまぜるための部品）。P波：2つの山 (高さ, 位置, 幅)、QRS-T：4つの山
# (q またはデルタ波, R, S, T) の (高さ, 位置, 左の幅, 右の幅)。位置は R頂点からの秒。上の qrs_… ・p_… と同じ値（check で確かめる）
_P_NONE = [(0.0, -PR, 0.022), (0.0, -PR + 0.032, 0.013)]


def _qrs_par(r=1.00, t=(0.27, 0.27, 0.060, 0.042)):
    return [(-0.08, -0.030, 0.008, 0.008), (r, 0.0, 0.011, 0.011), (-0.20, 0.028, 0.009, 0.009), t]


def _preex_par(w, a):
    return [(0.30*a, -0.030*w, 0.020*w, 0.012), (0.90*a, 0.0, 0.016*w, 0.018*w),
            (-0.12*a, 0.050*w, 0.014, 0.014), (-0.22, 0.175, 0.038, 0.030)]


BPAR = {
    'N': ([(0.15, -PR, 0.022), (0.0, -PR + 0.032, 0.013)], _qrs_par()),
    'C': ([(0.13, -0.14, 0.015), (-0.04, -0.14 + 0.032, 0.013)], _qrs_par()),
    'A': (_P_NONE, _qrs_par()),
    'F': (_P_NONE, _qrs_par(t=(0.12, 0.27, 0.060, 0.042))),
    'S': (_P_NONE, _qrs_par(t=(0.22, 0.215, 0.045, 0.034))),
    'G': (_P_NONE, _qrs_par(r=0.95, t=(0.14, 0.125, 0.026, 0.022))),
    'B': (_P_NONE, [(0.0, -0.030, 0.008, 0.008), (0.80, 0.0, 0.012, 0.015),
                    (-0.42, 0.062, 0.022, 0.036), (0.12, 0.30, 0.060, 0.045)]),
}
for _k, (_w, _a) in PREEX.items():
    BPAR[_k] = (_P_NONE, _preex_par(_w, _a))
_BP = {}


def beat_par(ka, kb, w):
    """種類 ka と kb のあいだ（w=0 で ka、w=1 で kb）の1拍の形の数値。片方にない山（高さ0）は、もう片方の位置・幅のまま大きさだけ変える。"""
    if w <= 1e-6 or ka == kb:
        return BPAR[ka]
    if w >= 1 - 1e-6:
        return BPAR[kb]
    key = (ka, kb, round(w, 4))
    if key in _BP:
        return _BP[key]
    pa, pb = BPAR[ka], BPAR[kb]
    ps = []
    for (a1, c1, s1), (a2, c2, s2) in zip(pa[0], pb[0]):
        if a1 == 0:
            c1, s1 = c2, s2
        if a2 == 0:
            c2, s2 = c1, s1
        ps.append((a1 + (a2 - a1)*w, c1 + (c2 - c1)*w, s1 + (s2 - s1)*w))
    qs = [tuple(x + (y - x)*w for x, y in zip(q1, q2)) for q1, q2 in zip(pa[1], pb[1])]
    if len(_BP) > 256:
        _BP.clear()
    _BP[key] = (ps, qs)
    return _BP[key]


def eval_par(par, tau):
    v = np.zeros_like(tau)
    for a, c, s in par[0]:
        if a != 0:
            v += a*_g(tau, c, s)
    for a, c, sl, sr in par[1]:
        if a != 0:
            v += a*_ga(tau, c, sl, sr)
    return v


# パターンの中の拍の番号 m → (R の時刻（パターンの始まりから）, 種類)。m は負でもよい（左へのばした並び）
def _loc_periodic(ev, L):
    n = len(ev)

    def f(m):
        q, j = divmod(m, n)
        return q*L + ev[j][0], ev[j][1]
    return f


def _loc_paf(m):
    """① 心房細動の始まり：左はずっと洞調律（75/分）→ PAC → そこから心房細動（R-R の列をくり返す）。"""
    if m <= len(PAF_SINUS) - 1:
        return m*RR, 'N'
    if m == len(PAF_SINUS):
        return PAF_PAC, 'C'
    q, j = divmod(m - len(PAF_SINUS) - 1, len(RR_PAF))
    return PAF_PAC + q*sum(RR_PAF) + sum(RR_PAF[:j + 1]), 'A'


TB_LAST = len(RR_TB_AF)               # ⑩ 最後の心房細動の拍の番号（このあとが休み）


def _loc_tb(m):
    """⑩ 徐脈頻脈症候群：左はずっと心房細動（R-R の列をくり返す）→ 最後の拍（m=TB_LAST）→ 休み → 洞調律 60/分がずっと。"""
    if m <= TB_LAST:
        q, j = divmod(m, len(RR_TB_AF))
        return q*sum(RR_TB_AF) + sum(RR_TB_AF[:j]), 'A'
    return TB_P1 + (m - TB_LAST - 1)*TB_SINUS_RR, 'N'


LOCAL = {None: _loc_periodic([(0.0, 'N')], RR)}      # None＝基準の洞調律
for _i, _p in enumerate(PATTERNS):
    LOCAL[_i] = _loc_periodic(_p['ev'], _p['L'])
LOCAL[0], LOCAL[I_TB] = _loc_paf, _loc_tb


def _smoothstep(x):
    x = np.clip(x, 0, 1)
    return x*x*(3 - 2*x)


def local_art(i, rel):
    """パターン i のf波・F波（rel＝パターンの始まりからの時刻）。①⑩は、片側だけ（①は PAC から右、⑩は最後の拍まで左）。"""
    if i is None:
        return None
    if i == 0:
        return band_noise(rel, L_PAF, 5.0, 8.0, F_MID, 30) * _smoothstep((rel - PAF_F0) / 0.08)
    if i == I_TB:
        return band_noise(rel, L_TB, 5.0, 8.0, F_MID, 39) * _smoothstep((TB_P0 + 0.12 - rel) / 0.08)
    pat = PATTERNS[i]
    return pat['art'](rel, pat['L'])


class Arr:
    """拍の並び（紙の上に固定）。pat：パターン番号（None＝基準の洞調律）。通しの番号 k の拍は、パターンの中の番号 k + c。
    パターンの始まり（m=0 の拍）が τ = A。"""

    def __init__(self, pat, A, c):
        self.pat, self.A, self.c = pat, A, c

    def beat(self, k):
        r, kind = LOCAL[self.pat](k + self.c)
        return self.A + r, kind

    def pos(self, k):
        return self.beat(k)[0]

    def k_lo(self, tau):
        """位置が tau 以上になる、いちばん小さい k。"""
        lo, hi = -20000, 20000
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.pos(mid) >= tau:
                hi = mid
            else:
                lo = mid
        return hi

    def art(self, tau):
        return local_art(self.pat, tau - self.A)


VO_LEN = {'①': 3.567, '②': 3.920, '③': 4.087, '④': 2.649, '⑤': 2.610, '⑥': 3.726, '⑦': 3.597,
          '⑧': 4.026, '⑨': 4.271, '⑩': 4.836, '⑪': 3.164, '⑫': 3.275, '⑬': 2.549, '⑭': 2.759}   # 声の長さ（align_vo.py で切った長さ）
# ③は 2026-10-14 に録り直した「平らに見えても、P波がなくR-Rがバラバラなら細動。」（out/vo/fix_1014_x1.2.mp3。2.830 → 4.087秒）
TITLE_VO_END = 4.52                    # 冒頭の文の終わり（0.10＋4.42）
LEAD = 0.55                            # 名前が出てから話し始めるまで（align_vo.py と同じ）
NAME_TAIL = 0.35                       # 話し終わってから名前が消えるまで
MORPH_DELAY, MORPH_T = 0.15, 1.00      # 名前が消えてから形が変わり始めるまで・直接変わる時間
VIA_T, VIA_HOLD = 0.70, 0.30           # 基準を通るとき：基準へ・基準のまま・次の形へ
NAME_AFTER = 0.15                      # 形が変わり終わってから次の名前が出るまで
# 前のパターンから直接変わる（同じ状態の中だけ。第24〜26弾の共通ルール、2026-10-14）：
#   ②〜⑤ 心房細動の f波の大きさ・心拍数（①→②→③→④→⑤）、
#   ⑫〜⑭ 心房粗動の伝導比（⑪→⑫→⑬→⑭。4:1 → 2:1 → 変わる → 1:1。F波は同じまま、QRS の数だけ変わる）
# それ以外のつなぎ目（⑤→⑥・⑥→⑦・⑦→⑧・⑧→⑨・⑨→⑩・⑩→⑪）は、灰色の「つなぎ」の洞調律（75/分）を通る。
#   ⑤→⑥・⑥→⑦ は前は直接だった（専門医レビュー 2026-10-14：⑥→⑦ が「アシュマン現象が進むと脚ブロック」と読まれうる）
DIRECT = {1, 2, 3, 4, 11, 12, 13}
ASH_ENTER = (1.4, 2.0)                 # ⑥ 幅の広い拍が右端に入るのは、名前が出てから この秒のあいだ（「長い」「短い」が声のあいだに見える）
TB_ENTER = 0.5                         # ⑩ 最後の心房細動の拍が右端に入るのは、名前が出てから この秒（左に心房細動が見えてから止まる）
TB_STOP_HOLD = 0.8                     # ⑩ 休みのタイマーが止まって（次の洞調律の拍が中央に来て）から、名前を出しておく秒


def _place(X, ypat, t0, t1, enter=None):
    """前の並び X から、形が t0〜t1 で変わる次の並び（パターン ypat）を置く。
    まん中の時刻に中央にいちばん近い X の拍と、Y の拍 m（候補を全部ためす）を同じ位置に。
    いちばん動きの小さい置き方を選ぶ。enter=(パターンの中の拍の番号の条件, 右端に入る時刻の範囲) があれば、それを先に満たす。"""
    tm = (t0 + t1) / 2
    tc = tau_c(tm)
    ks = X.k_lo(tc)
    kx = ks if abs(X.pos(ks) - tc) <= abs(X.pos(ks - 1) - tc) else ks - 1
    lo, hi = tau_c(t0) - HALF - 0.6, tau_c(t1) + HALF + 0.6
    if ypat is None:
        cands = [0]
    elif ypat == 0:
        cands = range(-6, 12)
    elif ypat == I_TB:
        cands = range(-14, TB_LAST + 1)
    else:
        cands = range(len(PATTERNS[ypat]['ev']))
    best = None
    for m in cands:
        Y = Arr(ypat, X.pos(kx) - LOCAL[ypat](m)[0], m - kx)
        k0, k1 = min(X.k_lo(lo), Y.k_lo(lo)) - 1, max(X.k_lo(hi), Y.k_lo(hi)) + 1
        cost = sum(abs(Y.pos(k) - X.pos(k)) for k in range(k0, k1 + 1)) / max(1, k1 - k0 + 1)
        miss = 0.0
        if enter is not None:            # 条件の拍のうち、右端に入る時刻がいちばん範囲に近いもの
            cond, (e0, e1) = enter
            miss = 1e9
            for q in range(-60, 61):
                mm = cond(q)
                if mm is None:
                    continue
                te_ = t_of(Y.A + LOCAL[ypat](mm)[0] - HALF)
                miss = min(miss, max(0.0, e0 - te_, te_ - e1))
        key = (round(miss, 3), cost)
        if best is None or key < best[0]:
            best = (key, Y)
    return best[1]


ARRS, CH_WIN, SHAPE_EV, BOUNDARY = [Arr(0, 0.0, 0)], [], [], []   # 並び・名前の時間・形が変わる時間 (t0, t1, X, Y)・つなぎ目の種類
for _i, _pat in enumerate(PATTERNS):
    _no = _pat['no']
    if _i == 0:
        _a = T_TITLE
        _v = max(T_TITLE + 0.30, TITLE_VO_END + 0.20)
        _b = max(_v + VO_LEN[_no] + NAME_TAIL, t_of(PAF_SHOW - HALF - HANDOFF_EARLY))
        CH_WIN.append((_a, _b))
        continue
    _t0 = CH_WIN[-1][1] + MORPH_DELAY
    _X = ARRS[-1]
    _t1 = _t0 + (MORPH_T if _i in DIRECT else 2*VIA_T + VIA_HOLD)
    _a = _t1 + NAME_AFTER
    _enter = None
    if _i == I_ASH:
        _n = len(RR_ASH)
        _enter = (lambda q, n=_n: ASH_K + q*n, (_a + ASH_ENTER[0], _a + ASH_ENTER[1]))
    elif _i == I_TB:
        _enter = (lambda q: TB_LAST if q == 0 else None, (_a + TB_ENTER - 0.25, _a + TB_ENTER + 0.25))
    if _i in DIRECT:
        _Y = _place(_X, _i, _t0, _t1, _enter)
        SHAPE_EV.append((_t0, _t1, _X, _Y))
        BOUNDARY.append(('direct', _t0, _t1))
    else:
        _N = _place(_X, None, _t0, _t0 + VIA_T)
        _t2 = _t0 + VIA_T + VIA_HOLD
        _Y = _place(_N, _i, _t2, _t1, _enter)
        SHAPE_EV += [(_t0, _t0 + VIA_T, _X, _N), (_t2, _t1, _N, _Y)]
        BOUNDARY.append(('via', _t0, _t1))
    ARRS.append(_Y)
    _v = _a + LEAD
    _b = _v + VO_LEN[_no] + NAME_TAIL
    if _i == I_TB:     # 休みのタイマーが止まり（次の洞調律の拍が中央＝ピッの位置に来たとき）、止まった値が見えるまで
        _b = max(_b, t_of(_Y.A + L_TB - HANDOFF_EARLY - HALF), t_of(_Y.A + TB_P1) + TB_STOP_HOLD)
    CH_WIN.append((_a, _b))
_t0 = CH_WIN[-1][1] + MORPH_DELAY                      # ⑭のあと：基準の洞調律へ
ARR_END = _place(ARRS[-1], None, _t0, _t0 + MORPH_T)
SHAPE_EV.append((_t0, _t0 + MORPH_T, ARRS[-1], ARR_END))
BOUNDARY.append(('end', _t0, _t0 + MORPH_T))
MORPHS = [(t0, t1) for t0, t1, *_ in SHAPE_EV]


def neutral_w(t):
    """灰色の「つなぎ」の濃さ（0〜1）。基準の洞調律を通るつなぎ目で、基準の形に近づくほど 1（基準のままのあいだは 1）。
    ⑭のあと（最後の画面）は基準の洞調律へもどり、そのまま 1。"""
    for kind, t0, t1 in BOUNDARY:
        if kind == 'via' and t0 <= t < t1:
            return min(ease((t - t0) / VIA_T), ease((t1 - t) / VIA_T))
        if kind == 'end' and t >= t0:
            return ease((t - t0) / MORPH_T)
    return 0.0


def next_label_a(t):
    """「▶ 次の例」の濃さ：基準を通るつなぎ目のあいだだけ（最後の画面へ移るところには出さない）。"""
    for kind, t0, t1 in BOUNDARY:
        if kind == 'via' and t0 <= t < t1:
            return ease((t - t0) / 0.25) * (1 - ease((t - (t1 - 0.25)) / 0.25))
    return 0.0


def state_at(t):
    """動画の時刻 t の (前の並び X, 次の並び Y, まぜる割合 w)。形が変わっていないときは X＝Y・w＝0。"""
    cur = ARRS[0]
    for t0, t1, X, Y in SHAPE_EV:
        if t < t0:
            return cur, cur, 0.0
        if t < t1:
            u = (t - t0) / (t1 - t0)
            return X, Y, u*u*(3 - 2*u)
        cur = Y
    return cur, cur, 0.0


def chain_beats(t, margin=0.9):
    """動画の時刻 t に、画面（＋左右 margin 秒）にある拍 [(R の位置 τ, X での種類, Y での種類, 通しの番号 k)]。"""
    X, Y, w = state_at(t)
    tc = tau_c(t)
    lo, hi = tc - HALF - margin, tc + HALF + margin
    k0 = min(X.k_lo(lo), Y.k_lo(lo)) - 1
    k1 = max(X.k_lo(hi), Y.k_lo(hi)) + 1
    out = []
    for k in range(k0, k1 + 1):
        rx, kx = X.beat(k)
        ry, ky = (rx, kx) if Y is X else Y.beat(k)
        r = rx + (ry - rx)*w
        if lo <= r <= hi:
            out.append((r, kx, ky, k))
    return out


def chain_wave(t, tau):
    """中部の帯の波形（動画の時刻 t の形で、画面の紙の上の時刻 tau に）。"""
    X, Y, w = state_at(t)
    v = np.zeros_like(tau)
    for r, kx, ky, _ in chain_beats(t):
        m = (tau - r > -0.5) & (tau - r < 0.75)
        if m.any():
            v[m] += eval_par(beat_par(kx, ky, w), tau[m] - r)
    for arr, wt in ((X, 1 - w), (Y, w)) if Y is not X else ((X, 1.0),):
        if wt > 1e-6:
            a = arr.art(tau)
            if a is not None:
                v += wt*a
    return v


T_END = CH_WIN[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60


def _loop_dur():
    """動画の長さ：最後の2文が入る長さ以上で、うしろの洞調律の拍の位相が冒頭とそろう（ループがつながる）いちばん短い長さ。"""
    need = T_END + FLY + END_HOLD
    ph0 = (tau_c(0.0) - ARRS[0].A) / RR
    best = None
    for n in range(int(need*FPS_LOOP), int((need + 1.0)*FPS_LOOP) + 1):
        d = n / FPS_LOOP
        e = ((tau_c(d) - ARR_END.A) / RR - ph0) % 1.0
        e = min(e, 1 - e)
        if best is None or e < best[0] - 1e-9:
            best = (e, d)
    return best[1], best[0]*RR


DUR, LOOP_ERR = _loop_dur()
WINDOWS = list(CH_WIN)                     # (名前が出る, 名前が消えて枠へ飛び始める)
PHASE = [a.A for a in ARRS]                # ミニ波形・枠へ飛ぶコピー：パターンの始まりの位置（名前が消える瞬間の帯とそろう）
# 説明・レビュー用：パターン i の「1周期の始まり」で、名前の出ているあいだに見えるもの
SEGS = []
for _i, _arr in enumerate(ARRS):
    _s = _arr.A
    if _i == I_ASH:          # 右端に入るように置いた、幅の広い拍の周期
        _ta = tau_c(WINDOWS[_i][0] + sum(ASH_ENTER) / 2) + HALF
        _s += round((_ta - _arr.A - T_ASH) / L_ASH) * L_ASH
    elif _i not in (0, I_TB):
        _s += math.floor((tau_c(WINDOWS[_i][0]) - _arr.A) / PATTERNS[_i]['L']) * PATTERNS[_i]['L']
    SEGS.append((_s, _s + PATTERNS[_i]['L']))


# --- ミニ波形の枠 -----------------------------------------------------------------
COL_X = (130, 550)
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える）
M_MV = 33.0


def cell_rect(i):
    if i < 8:
        col, row = i // 4, i % 4
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 8
        col, row = j // 3, j % 3
        x, y = COL_X[col], BOT_Y[row]
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
    """心電図用紙の方眼：細い線 14px（1mm＝0.04秒・0.1mV）、太い線 70px（5mm＝0.2秒・0.5mV）。
    太い線が、画面の中央（x=540）と中部の波形の基線（F_BASE）を通るように置く。"""
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = F_PXMM                                     # 1mm＝14px（波形と同じ目盛り。25mm/秒・10mm/mV）
    x0 = (XC % (5*pm)) - 5*pm                       # 太い線が x=540 を通る
    y0 = (round(F_BASE) % (5*pm)) - 5*pm            # 太い線が基線を通る
    for major in (False, True):                     # 細い線 → 太い線の順（太い線を上に）
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


# --- 中部の波形 --------------------------------------------------------------------
SS = 2


def chain_colors(t, tau, cur):
    """色を付けるのは、名前が出ている（＝帯がそのパターンの形そのもの）ときだけ、色を付ける範囲に。"""
    cid = np.full(len(tau), -1, dtype=int)
    X, Y, w = state_at(t)
    if cur is None or w > 0 or X.pat != cur:
        return cid
    pat = PATTERNS[cur]
    rel = tau - X.A
    if pat['hl'] is ALL:
        cid[:] = cur
    elif cur == 0:                                   # ①：PAC のあと（心房細動）から右だけ
        cid[rel >= pat['hl'][0][0]] = cur
    else:
        cid[hl_mask(pat, rel)] = cur
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


def chain_arrays(t, cur=None):
    """中部の帯：(波形, 色の番号)"""
    tau = tau_c(t) + (FX - XC) / F_PXS
    return chain_wave(t, tau), chain_colors(t, tau, cur)


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
    v = art_apply(pat, rel, wave_from(bl, rel))
    cid = np.where(hl_mask(pat, rel) | (pat['hl'] is ALL), i, -1)
    return v, cid


_HOOK = {}


def hook_targets():
    if not _HOOK:
        _HOOK['seq'] = [chain_arrays(T_STOP)] + [hook_arrays(i) for i in HOOK] + [chain_arrays(T_STOP)]
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


def draw_wave(v, cid, base_col, a, cmix=1.0):
    """cmix：パターンの色の濃さ（0 でふつうの緑。名前が出る・消えるのに合わせて、色もなめらかに）"""
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(set(np.unique(cid).tolist())):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else mix(base_col, PATTERNS[ci]['col'], cmix)
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


def featured(t, base_col, a, cur=None, cmix=1.0):
    """中部の帯。色を付けるのは、いま紹介中のパターン cur の形そのもののときだけ（形が変わるあいだは、ふつうの緑）。"""
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a)
    v, cid = chain_arrays(t, cur)
    return draw_wave(v, cid, base_col, a, cmix)


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 66, 44     # ミニ波形の帯（枠の中。基線は枠の上から 74px）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0):
    """パターン i をくり返した波形を、画面の x_lo〜x_hi に描いた RGBA（全画面サイズの一部）。
    中央 cx に来る時刻は tau_c(t)（中部の帯と同じ）。区間の始まりからの相対時刻で周期にする。"""
    pat = PATTERNS[i]
    s0 = PHASE[i]
    xs = np.arange(x_lo, x_hi + 0.5, 0.5)
    tau = tau_c(t) + (xs - cx) / pxs
    rel = tau - s0
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = art_apply(pat, rel, wave_from(bl, rel))
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
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
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
    base_y = lerp(F_BASE, oy + STRIP_BASE + MINI_DY.get(i, 0), u)
    pxs = F_PXS*(M_PXS/F_PXS)**u
    mv = F_MV*(M_MV/F_MV)**u
    half = lerp(XC, STRIP_W/2, u)
    lw = lerp(4.5, 2.2, u)
    b1 = lerp(8, 3, u); b2 = lerp(20, 7, u)
    return cx, base_y, pxs, mv, cx - half, cx + half, lw, (b1, b2)


MINI_DY = {5: -4, 6: -7, 10: -3, 11: -3, 12: -3, 13: -3}   # ミニ波形の基線を上げる（⑥⑦の深いS波、⑪〜⑭の下向きF波で下に寄るので）
MINI_LW_HL = 3.0                   # ミニ波形で、色を付ける範囲の線の太さ（ほかは 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、色を付けない範囲の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_HL, u), a_norm=lerp(1.0, MINI_A_NORM, u))
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
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17,
            a=a_all, max_w=CELL_W - 30)
    elif state == 'now':
        put(base, pat['no'], 30, 700, pat['col'], x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2))
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=CELL_W - 80)


# --- 画面 ---------------------------------------------------------------------------
TITLE = '心房細動・心房粗動'
HEADER = [(TITLE, 1.0, WHITE), (str(N_PAT), 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
QUESTION = ('細動？粗動？', '見分けられる？')    # 冒頭の問いかけ（0秒から。見出しが出る前に消す）
COMMENT = '何個わかった？コメントで教えてね'   # 最後の呼びかけ
END_SWAP = 5.10                     # 一覧がそろってから、まとめの文 → 呼びかけに入れかえるまで（秒）。まとめの声（⑭が基準へもどり終わってから 4.51秒）が終わってから入れかえる
HEADER_BASE = 348                   # 見出しのベースライン（y）
NOTE1 = '実際の速さ（前後のふつうの拍は75/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'
END_LINES = ('のこぎりがあれば粗動。', 'なくて、R-Rバラバラなら細動')   # 最後の画面（見分けのポイント。2行）
# 2026-10-14 専門医レビュー（要修正）：前は「のこぎりは粗動、R-Rバラバラは細動」。後半だけだと「R-Rがバラバラなら細動」になり、
# ⑬（伝導比が変わる粗動）と食いちがう。のこぎりを先に探す順にした
END_LINE = ''.join(END_LINES)
END_Y = (816, 865, 916)             # 最後の画面：見分けのポイント2行・「保存して見返してね」（上の枠の下端 780、帯の R の頂点 954 のあいだ）
NEUTRAL_COL = (118, 126, 128)       # 「つなぎ」の洞調律の線の色（緑・パターンの色と分ける、うすい灰色）
NEXT_LABEL = '▶ 次の例'              # 灰色のつなぎのあいだに出す小さな文字


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「心房細動・心房粗動」＋大きな黄色の「12」＋「パターン」。左右の余白（130px）に収める。"""
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


# ひとことのうしろに、見るところ・動き方を色で（ナレーションでは「すぐ報告」と言わない）
ONE_W = 806                         # ひとこと＋色の文字の幅の上限（左右に 137px 以上の余白＝安全域 130px の内側。2026-10-14 ③「ほぼ」を足したので 760→806。③は 31px）
TAGS = {
    'new': ('→ 初めてなら報告', (130, 232, 172)),      # 新しく出た心房細動・心房粗動は医師へ
    'vital': ('→ 脈拍と血圧も確認', (255, 170, 80)),    # 速い・遅い：症状と循環をみる
    'ecg12': ('→ 12誘導で確認', (178, 150, 240)),       # 幅の広いQRS・不規則な粗動：形を確かめる
    'report': ('→ すぐ報告', (255, 96, 96)),            # 危ない形
}


def draw_one(im, pat, a):
    """中部のひとこと。うしろに色の文字（TAGS）を続けて、まとめて中央ぞろえ。"""
    tag = TAGS[pat['tag']]
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        if w1 + 14 + w2 <= ONE_W or sz <= 24:
            break
        sz -= 1
    x0 = 540 - (w1 + 14 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=Y_ONE, a=a)
    put(im, tag[0], sz, 800, tag[1], x=x0 + w1 + 14, cy=Y_ONE, a=a)


def one_size(pat):
    """ひとこと＋色の文字の大きさと幅（--check 用）。"""
    tag = TAGS[pat['tag']]
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        if w1 + 14 + w2 <= ONE_W or sz <= 24:
            return sz, w1 + 14 + w2
        sz -= 1


QUESTION_Y = (392, 488)             # 冒頭の問いかけ（2行・76px）。上 250px より下、題字の上。出ているあいだはサブタイトルを消す
QUESTION_SIZE = 76
RULER_X0 = 140                      # ものさしの棒は、ラベル「R-R」の右から
RULER_DIM = (70, 112, 98)           # いま紹介中でない拍のあいだの棒
RULER_NEUTRAL = (84, 90, 92)        # 灰色の「つなぎ」の洞調律のあいだの棒


def draw_pair(im, parts, size, cy, a=1.0, gap=22):
    """色のちがう文を1行に並べて中央ぞろえ（入らないときは字を小さく）。"""
    if a <= 0.004:
        return
    sz = size
    while True:
        ws = [text_img(s_, sz, 700, c)[0].size[0] - 8 for s_, c in parts]
        if sum(ws) + gap*(len(parts) - 1) <= 820 or sz <= 24:
            break
        sz -= 1
    x = 540 - (sum(ws) + gap*(len(parts) - 1)) / 2
    for (s_, c), w_ in zip(parts, ws):
        put(im, s_, sz, 700, c, x=x, cy=cy, a=a)
        x += w_ + gap


def ruler_items(t):
    """ものさし：画面に見えている拍と拍のあいだ [(x0, x1, パターン番号 or None, R-R, 始まりの拍の種類, 始まりの拍のパターンの中の番号), …]。
    値は、いまの拍の位置（モデルの R の時刻）から。形が変わっているあいだは、パターン番号は None。"""
    tc = tau_c(t)
    X, Y, w = state_at(t)
    pure = w <= 0
    bs = chain_beats(t, margin=3.5)
    out = []
    for (r0, kx0, ky0, k0), (r1, *_) in zip(bs, bs[1:]):
        x0 = XC + (r0 - tc)*F_PXS; x1 = XC + (r1 - tc)*F_PXS
        if x1 < 0 or x0 > W:
            continue
        out.append((x0, x1, X.pat if pure else None, r1 - r0, kx0 if w < 0.5 else ky0, k0 + X.c if pure else None))
    return out


RULER_H = 8                         # 棒の太さ（6→8px）


def _dashed_bar(d, xa, xb, yc, col, dash=16, gap=9):
    x = xa
    while x < xb:
        d.rounded_rectangle((x, yc - RULER_H/2, min(x + dash, xb), yc + RULER_H/2), radius=3, fill=col)
        x += dash + gap


RULER_CLIP = {4, 7}                 # ⑤ 徐脈性・⑧ 完全房室ブロック：端で切れる棒も描く
RULER_FADE = 70                     # 切れた側をうすくする長さ（px）


def _fade_bar(lay, xa, xb, yc, col, alpha, fade_l, fade_r):
    """端で切れる棒：切れた側（fade_l／fade_r）を RULER_FADE px でうすくする。"""
    xa, xb = int(round(xa)), int(round(xb))
    w = xb - xa
    m = Image.new('L', (w, 40), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, yc - RULER_H/2, w - 1, yc + RULER_H/2), radius=3, fill=255)
    g = np.ones(w, np.float32)
    xx = np.arange(w, dtype=np.float32)
    if fade_l:
        g = np.minimum(g, 0.15 + 0.85*np.clip(xx / RULER_FADE, 0, 1))
    if fade_r:
        g = np.minimum(g, 0.15 + 0.85*np.clip((w - 1 - xx) / RULER_FADE, 0, 1))
    am = (np.asarray(m, np.float32) * g[None, :] * alpha / 255).astype(np.uint8)
    bar = Image.new('RGBA', (w, 40), col + (0,))
    bar.putalpha(Image.fromarray(am))
    lay.alpha_composite(bar, (xa, 0))


def draw_ruler(im, t, cur, a, cmix=1.0, gn=0.0):
    """R-R のものさし：拍と拍のあいだを横棒で。そろう＝規則的、バラバラ＝不規則が一目でわかる。
    両端の拍が見えている区間だけ棒を描く（端の半端な棒は描かない）。
    例外：⑩の休みは、最後の心房細動の拍から右端までのびていく点線（タイマーと同じ動き）。
    ①は洞調律の区間を暗くして「そろう → 急にバラバラ」を見せる。"""
    if a <= 0.01:
        return
    lay = Image.new('RGBA', (W, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    yc = 20
    dim = mix(RULER_DIM, RULER_NEUTRAL, gn)          # 灰色の「つなぎ」のあいだは、棒も灰色に
    for x0, x1, i, rr, k0, m0 in ruler_items(t):
        col = mix(RULER_DIM, PATTERNS[i]['col'], cmix) if (i is not None and i == cur) else dim
        if i == 0 and k0 == 'N':
            col = RULER_DIM
        is_pause = i == I_TB and m0 == TB_LAST
        if is_pause and cur == I_TB:
            # 休みの点線：最後の拍が中央を通ってから、中央までのびていく（タイマー・カウンターと同じ「中央」の基準）。
            # 休みが全部過ぎたあとも、タイマーと一緒に左へ流れるあいだは描く（左は R-R の字の右で切る）
            pc = mix(RULER_DIM, C_STOP, cmix)
            xe = min(x1, XC)
            if xe - 5 > max(x0 + 5, RULER_X0) + 4:
                _dashed_bar(d, max(x0 + 5, RULER_X0), xe - 5 if xe == x1 else xe, yc, pc + (int(235*a),))
            for xt in (x0, x1):
                if RULER_X0 - 2 <= xt <= W:
                    d.line([(xt, yc - 9), (xt, yc + 9)], fill=pc + (int(235*a),), width=3)
            continue
        if cur == I_ASH and i == I_ASH and x0 < RULER_X0 and RULER_X0 + 30 < x1 <= W - 4:
            # ⑥：長い R-R が左端で切れても、棒は左端まで描く（長い → 短い を、名前が出ているあいだ見せる）
            d.rounded_rectangle((RULER_X0, yc - RULER_H/2, x1 - 5, yc + RULER_H/2), radius=3, fill=col + (int(235*a),))
            d.line([(x1, yc - 9), (x1, yc + 9)], fill=col + (int(235*a),), width=3)
            continue
        if cur in RULER_CLIP and i == cur and (x0 < RULER_X0 or x1 > W - 4):
            # ⑤⑧：R-R が長く、両端の見える棒が1本になるコマがあるので、端で切れる棒も描く（切れた側はうすくして「画面の外へ続く」とわかるように）。
            # 2026-10-14 専門医レビュー：棒がいつも2本以上見えるように
            xa, xb = max(x0 + 5, RULER_X0), min(x1 - 5, W - 4)
            if xb - xa >= 40:
                _fade_bar(lay, xa, xb, yc, col, 235*a, x0 < RULER_X0, x1 > W - 4)
            for xt in (x0, x1):
                if RULER_X0 - 2 <= xt <= W:
                    d.line([(xt, yc - 9), (xt, yc + 9)], fill=col + (int(235*a),), width=3)
            continue
        if x0 < RULER_X0 or x1 > W - 4:
            for xt in (x0, x1):                   # 目盛りは描く
                if RULER_X0 - 2 <= xt <= W:
                    d.line([(xt, yc - 9), (xt, yc + 9)], fill=col + (int(235*a),), width=3)
            continue
        if x1 - x0 - 10 >= 4:
            d.rounded_rectangle((x0 + 5, yc - RULER_H/2, x1 - 5, yc + RULER_H/2), radius=3, fill=col + (int(235*a),))
        for xt in (x0, x1):
            d.line([(xt, yc - 9), (xt, yc + 9)], fill=col + (int(235*a),), width=3)
    im.alpha_composite(lay, (0, int(RULER_Y - yc)))
    put(im, 'R-R', 22, 700, GREY, x=72, cy=RULER_Y + 1, a=0.9*a)
    if cur == I_ASH:
        draw_ash_labels(im, t, a*cmix)


ASH_LABEL_SIZE = 20


def draw_ash_labels(im, t, a):
    """⑥：変行伝導の拍の直前の「長い」R-R と、その拍までの「短い」R-R の棒の下に小さく名札。値はモデルの R の時刻から。"""
    X, _, w = state_at(t)
    if w > 0 or X.pat != I_ASH:
        return
    tc = tau_c(t)
    n = len(PATTERNS[I_ASH]['ev'])
    q0 = math.floor((tc - X.A) / L_ASH)
    for q in range(q0 - 1, q0 + 2):                  # 画面にある、変行伝導の拍（パターンの中の番号 ASH_K + q·n）
        m = ASH_K + q*n
        rs = [X.A + LOCAL[I_ASH](mm)[0] for mm in (m - 2, m - 1, m)]   # 長い：a→b、短い：b→c
        xs = [XC + (r - tc)*F_PXS for r in rs]
        if RULER_X0 + 30 < xs[1] and xs[2] <= W - 4:
            break
    else:
        return
    col = PATTERNS[I_ASH]['col']
    for lab, xa, xb in (('長い', max(xs[0], RULER_X0), xs[1]), ('短い', xs[1], xs[2])):
        tw = text_img(lab, ASH_LABEL_SIZE, 700, col)[0].size[0] - 8
        cx = min(max((xa + xb) / 2, 72 + tw/2), W - 72 - tw/2)
        put(im, lab, ASH_LABEL_SIZE, 700, col, cx=cx, cy=RULER_Y + 24, a=a)


TIMER_SIZE = 46


def draw_pause_timer(im, t, a):
    """⑩ 休みのタイマー。カウンター・ピッという音と同じ「画面の中央」で数える（2026-10-14 専門医レビューの直し）：
    最後の心房細動の拍が中央を通ったときに 0 から数え始め、次の洞調律の拍が中央を通ったときに休みの長さ（3.2秒）で止まる。
    字は中央のすぐ左（＝もう過ぎた休みの平らな線の上）に右ぞろえで置き、止まったあとは波形と一緒に左へ流れる。
    最後の拍のT波と重ならないよう、1.1秒まで数えてから出す。字の幅は「休み 3.2秒」で固定。"""
    if a <= 0.01:
        return
    s0 = ARRS[I_TB].A
    p0, p1 = s0 + TB_P0, s0 + TB_P1
    tc = tau_c(t)
    el = min(tc, p1) - p0
    if el < 1.1:
        return
    tw = text_img(f'休み {TB_PAUSE:.1f}秒', TIMER_SIZE, 900, C_STOP)[0].size[0] - 8
    xr = XC - TIMER_GAP - max(0.0, tc - p1)*F_PXS          # 字の右端
    if xr - tw < 72:
        return
    put(im, f'休み {el:.1f}秒', TIMER_SIZE, 900, C_STOP, x=xr - tw, cy=F_BASE - 0.45*F_MV,
        a=a*ramp(el, 1.1, 0.2))


TIMER_GAP = 34                      # タイマーの字の右端と、画面の中央（拍が通る位置）のあいだ


# --- 心拍数カウンター「♥ 150 /分」（第24弾と同じ見た目・大きさ。2026-10-13） ------------------------------
# 帯の拍（R）が画面の中央を通る（＝ピッという音が鳴る）たびに、その拍とひとつ前の拍の R-R（画面の拍の位置）から計算した心拍数に変わる。
# 1拍に1回だけ変わる（モニターのように拍ごと）。
# - 置き場所：波形の帯の左上（ひとことの下、R の頂点の高さ）。ものさし・「長い／短い」・⑩のタイマー（基線の 0.45mV 上）・
#   ひとこと・枠と重ならない高さ
# - 2026-10-14 専門医レビューの直し：
#   - 後ろに角の丸い暗い板（不透明度 86%）を敷く。R 波が数字を突き抜けて読めなくならないように（前は字のまわりのぼかしだけ）
#   - 形が変わるあいだ（つなぎ目 t0〜t1）は「--」（0.2秒で切りかえ）。2つの形がまざった値・基準の洞調律の値は出さない。
#     形が変わり終わったら、次の形の値（モデルの R の位置から計算）から再開する
#   - ⑩ の休み：次の拍まで 2秒より長くあくところでは、1.2秒たったら「--」。休みのあとの最初の拍（60÷3.2秒＝19/分）も「--」のまま
#   - 「1拍ごとの値／（モニターは平均）」は ⑩ の心房細動の区間にも出す（「--」のあいだは出さない）
# - ⑧ 完全房室ブロック：心室（QRS）の数＝48/分。f波は数えない
C_HEART = (255, 92, 112)
CNT_X0 = 130                        # カウンターの左端（左の安全域）
CNT_CY = 960                        # 数字の中心の高さ。字の上下 943〜992（ひとことの下端 916、R の頂点 954、⑩のタイマーの上端 1012）
CNT_SUB = ('1拍ごとの値', '（モニターは平均）')
CNT_STALE_GAP, CNT_STALE_AFTER = 2.0, 1.2
CNT_DASH_T = 0.2                    # 「--」への切りかえの時間
IRREG = {0, 1, 2, 3, 4, 5, 6, 8, 9, 12}    # 不規則なリズム（①〜⑦・⑨・⑩の心房細動・⑬）：「1拍ごとの値」を出す
CNT_IN = T_TITLE                     # ①の名前と一緒に出す
PLATE_FILL = (4, 10, 9)              # カウンターの後ろの板
PLATE_A = 0.86
_HR = []


def cnt_out():
    """消し始める時刻：⑭のあと、基準の洞調律へ形が変わり始めて「--」になったら（最後の画面）。"""
    return BOUNDARY[-1][1] + CNT_DASH_T


def hr_crossings():
    """[(中央を通った時刻, 心拍数, 次に通るまでの秒)]。中央を通る拍（center_crossings＝ピッの音）と同じ時刻。"""
    if _HR:
        return _HR
    cr = center_crossings()
    for n, (tx, kind, k) in enumerate(cr):
        bs = {kk: r for r, _, _, kk in chain_beats(tx, margin=4.0)}
        bpm = 60.0 / (bs[k] - bs[k - 1]) if (k in bs and k - 1 in bs) else None
        nxt = cr[n + 1][0] - tx if n + 1 < len(cr) else 9.0
        _HR.append((tx, bpm, nxt))
    return _HR


def _last_cross(t):
    hc = hr_crossings()
    lo, hi = 0, len(hc)
    while lo < hi:
        mid = (lo + hi) // 2
        if hc[mid][0] <= t:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


def morph_span(t):
    """t が、形が変わるあいだ（つなぎ目 t0〜t1）なら (t0, t1)。"""
    for _, t0, t1 in BOUNDARY:
        if t0 <= t < t1:
            return t0, t1
    return None


def _model_bpm(t):
    """形が変わっていないとき、中央より左のいちばん近い拍と、その1つ前の拍の R-R（モデルの位置）からの値。"""
    X, _, _ = state_at(t)
    k = X.k_lo(tau_c(t)) - 1
    return 60.0 / (X.pos(k) - X.pos(k - 1))


def _cnt_plain(t):
    """形が変わるあいだを除いた (値 or None, 「--」の濃さ)。"""
    hc = hr_crossings()
    j = _last_cross(t)
    ends = [t1 for _, _, t1 in BOUNDARY if t1 <= t]
    if ends and (j < 0 or hc[j][0] < ends[-1]):      # 形が変わり終わってから、まだ拍が中央を通っていない
        return _model_bpm(t), 1 - ramp(t, ends[-1], CNT_DASH_T)
    if j < 0:
        return None, 1.0
    tx, bpm, nxt = hc[j]
    if bpm is None or bpm < 60.0 / CNT_STALE_GAP:      # ⑩ 休みのあとの最初の拍（19/分）は出さない
        return None, 1.0
    if nxt > CNT_STALE_GAP:                            # ⑩ 休み：1.2秒たったら「--」
        return bpm, ramp(t - tx, CNT_STALE_AFTER, 0.3)
    return bpm, 0.0


def cnt_state(t):
    """カウンターの表示：(値 or None, 「--」の濃さ 0〜1, 最後に拍が中央を通ってからの秒)。"""
    j = _last_cross(t)
    since = t - hr_crossings()[j][0] if j >= 0 else 9.0
    sp = morph_span(t)
    if sp is not None:
        val, d0 = _cnt_plain(sp[0] - 1e-4)            # 形が変わり始めたときの値が、うすくなりながら「--」へ
        return val, max(d0, ramp(t, sp[0], CNT_DASH_T)), since
    val, d = _cnt_plain(t)
    return val, (1.0 if val is None else d), since


def cnt_text(t):
    """--check・依頼文用：そのときのカウンターの表示（「75」「--」）。"""
    val, d, _ = cnt_state(t)
    return '--' if (val is None or d >= 0.5) else f'{val:.0f}'


def irreg_weight(t):
    X, Y, w = state_at(t)
    return (1 - w)*(X.pat in IRREG) + w*(Y.pat in IRREG)


def draw_heart(im, cx, cy, size, col, a):
    """ハート（2つの円＋三角）。拍ごとに明るくする（第24弾と同じ）。"""
    if a <= 0.004:
        return
    ss = 4
    n = int(size*ss)
    lay = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(lay)
    r = n*0.27
    d.ellipse((n*0.5 - 2*r, n*0.12, n*0.5, n*0.12 + 2*r), fill=255)
    d.ellipse((n*0.5, n*0.12, n*0.5 + 2*r, n*0.12 + 2*r), fill=255)
    d.polygon([(n*0.5 - 2*r + n*0.02, n*0.12 + r*1.25), (n*0.5 + 2*r - n*0.02, n*0.12 + r*1.25), (n*0.5, n*0.94)], fill=255)
    lay = lay.resize((int(size), int(size)), Image.LANCZOS)
    col_im = Image.new('RGBA', lay.size, col + (0,))
    col_im.putalpha(lay.point(lambda q: int(q*a)))
    im.alpha_composite(col_im, (int(cx - size/2), int(cy - size/2)))


CNT_BOX = (CNT_X0 - 40, CNT_CY - 60, CNT_X0 + 560, CNT_CY + 60)   # カウンターを描く範囲（板を含む）


def draw_counter(im, t, a):
    """心拍数カウンター「♥ 150 /分」。並べ方は第24弾と同じ（数字は3けたぶんの幅で右ぞろえ、ハートは数字のすぐ左）。
    後ろに角の丸い暗い板を敷く（R 波が後ろを通っても数字が読める）。"""
    if a <= 0.004:
        return
    val, dash, since = cnt_state(t)
    flash = math.exp(-since/0.18)                   # 拍の瞬間に明るく、すぐ戻る
    bx0, by0, bx1, by1 = CNT_BOX
    lay = Image.new('RGBA', (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
    w3 = text_img('888', 64, 800, WHITE)[0].size[0] - 8      # 3けたぶんの幅（数字が変わっても「/分」は動かない）
    im_u, _ = text_img('/分', 32, 700, GREY)
    hs, gap_h = 44, 14
    cy = CNT_CY - by0
    x_left = CNT_X0 - bx0
    xr = x_left + hs + gap_h + w3                    # 数字は右ぞろえ
    a_sub = irreg_weight(t)*(1 - dash)
    xs = xr + 10 + im_u.size[0] - 8 + 22             # 注記の左端
    w_sub = max(text_img(s_, 22, 600, GREY)[0].size[0] - 8 for s_ in CNT_SUB)
    x_end = xr + 10 + im_u.size[0] - 8 + a_sub*(22 + w_sub)
    # 板（注記が出るときは、のびる）
    pd = ImageDraw.Draw(lay, 'RGBA')
    pd.rounded_rectangle((x_left - 16, cy - 34, x_end + 16, cy + 38), radius=16,
                         fill=PLATE_FILL + (int(255*PLATE_A),), outline=CARD_EDGE + (90,), width=1)
    if val is not None and dash < 0.999:             # 数字（「--」へ切りかわるときは、うすくなる）
        num = f'{val:.0f}'
        wn = text_img(num, 64, 800, WHITE)[0].size[0] - 8
        put(lay, num, 64, 800, WHITE, right=xr, cy=cy + 4, a=1 - dash)
    else:
        wn = w3
    if dash > 0.001:
        wd = text_img('--', 64, 800, GREY)[0].size[0] - 8
        put(lay, '--', 64, 800, GREY, right=xr, cy=cy + 4, a=dash)
        wn = wn + (wd - wn)*dash
    draw_heart(lay, xr - wn - gap_h - hs/2, cy + 7, hs*(1 + 0.12*flash), C_HEART, (0.55 + 0.45*flash)*(1 - 0.4*dash))
    put(lay, '/分', 32, 700, GREY, x=xr + 10, cy=cy + 14)
    if a_sub > 0.004:                                # 不規則なリズム：数字の右に小さく2行
        put(lay, CNT_SUB[0], 22, 600, GREY, x=xs, cy=cy - 6, a=a_sub)
        put(lay, CNT_SUB[1], 22, 600, GREY, x=xs - 9, cy=cy + 22, a=a_sub)
    if a < 0.999:
        lay.putalpha(lay.getchannel('A').point(lambda q: int(q*a)))
    im.alpha_composite(lay, (bx0, by0))


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

    # 中部：紹介中の名前とひとこと（帯の色も、これと同じ濃さで出し入れする）
    al = 0.0
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        al = ramp(t, a_i + 0.1, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=al, max_w=820)
        draw_one(im, pat, al)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    if a_t > 0:
        a_q0 = max(1 - ramp(t, 2.0, 0.45), a_loop)
        put(im, 'モニター心電図で見分ける', 36, 500, PURPLE, cx=540, cy=560, a=a_t*(1 - a_q0))   # 問いかけと「見分け」が重なるので、問いかけのあいだは消す
        put(im, TITLE, 150, 900, WHITE, cx=540, cy=690, a=a_t, max_w=880)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    # 冒頭の問いかけ（フックの上。見出しと重ならないよう、見出しが出る前に消す）
    a_q = max(1 - ramp(t, 2.0, 0.45), a_loop)
    if a_q > 0:
        for line, cy in zip(QUESTION, QUESTION_Y):
            put(im, line, QUESTION_SIZE, 900, (255, 214, 64), cx=540, cy=cy, a=a_q, max_w=880)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        sw = ramp(t, T_END + FLY + END_SWAP, 0.4)            # 一覧がそろってから END_SWAP 秒で、コメントの呼びかけに入れかえる
        for line, cy in zip(END_LINES, END_Y):
            put(im, line, 40, 800, WHITE, cx=540, cy=cy, a=a_end*(1 - sw), max_w=820)
        put(im, COMMENT, 42, 900, (255, 214, 64), cx=540, cy=(END_Y[0] + END_Y[1])/2, a=a_end*sw, max_w=820)
        put(im, '保存して見返してね', 34, 700, GREEN, cx=540, cy=END_Y[2],
            a=ramp(t, T_END + FLY + 1.5, 0.6)*keep)

    # ⑩ 休みのタイマー（休みが右端から入ってきたら、秒数をカウントアップ）
    if cur == I_TB:
        a_i, b_i = WINDOWS[cur]
        draw_pause_timer(im, t, ramp(t, a_i + 0.1, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25)))

    # 中部の波形：最初から最後まで消さない。紹介が終わると、見えている波形のコピーだけが縮んで枠へ移り、
    # 帯の拍は、その場で次のパターンの形へ変わる（state_at）
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    # 基準を通るつなぎ目：基準の洞調律に近づくほど灰色・少しうすく（病態の一部ではない「つなぎ」。2026-10-14 第24〜26弾の共通ルール）
    gn = neutral_w(t)*keep
    base_col = mix(base_col, NEUTRAL_COL, gn)
    im.alpha_composite(featured(t, base_col, 1.0 - 0.25*gn, cur, al), (0, F_Y0))
    a_nx = next_label_a(t)
    if a_nx > 0.004:
        put(im, NEXT_LABEL, 34, 700, (168, 178, 180), cx=540, cy=Y_NAME, a=a_nx)
    draw_ruler(im, t, cur, ramp(t, T_GO, 0.5)*keep, al, gn)
    # 心拍数カウンター：①の名前が出てから、⑭のあと基準の洞調律に変わり終わるまで（形が変わるあいだも出したまま）
    draw_counter(im, t, ramp(t, CNT_IN + 0.1, 0.3)*(1 - ramp(t, cnt_out(), 0.4)))
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        # コピーはうすい状態から（帯と重なる最初の一瞬に、二重に見えないように）
        mini(im, flying, t, uu, a=cl(uu / 0.3))

    put(im, NOTE1, 22, 400, GREY, x=135, cy=1562, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 22, 400, GREY, x=135, cy=1586, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


THUMB_HERO = I_FL41                # 1枚もののサムネイルで大きく見せる波形（⑪ 心房粗動 4:1 のこぎり）


def thumbnail():
    """サムネイル（透かしなし）。14個そろった一覧に、大きなタイトルと⑪のこぎり状のF波。"""
    global _GRID
    if _GRID is None:
        _GRID = grid()
    t = T_END + FLY + 2.0
    im = _GRID.copy()
    draw_header(im, 1.0)
    for i in range(N_PAT):
        draw_cell(im, i, t, 'done', 1.0)
        mini(im, i, t, 1.0)
    put(im, 'バラバラ？ のこぎり？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 12, max_w=820)
    put(im, TITLE, 96, 900, WHITE, cx=540, cy=Y_ONE + 32, max_w=880)
    v, cid = hook_arrays(THUMB_HERO)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0)
    im.alpha_composite(wl, (0, F_Y0 + 57))         # 上の枠・小見出し・題字・波形・下の枠の4つの余白をそろえる（約39px。測って決めた）
    return im.convert('RGB')


# --- 一覧型のサムネイル（第17弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {i: (0.0, []) for i in range(N_PAT)}
THUMB_VIEW[0] = (0.6, [])                                    # 始まり：洞調律から心房細動へ
THUMB_VIEW[I_ASH] = (0.3, [(T_ASH - 0.10, T_ASH + 0.36)])    # アシュマン現象：幅の広い1拍
THUMB_VIEW[I_TB] = (1.25, [])                                # 徐脈頻脈：細動 → 長い休み → 回復した洞調律（心停止に見えないよう）
THUMB_MAX_MARKS = {I_ASH: 1}
THUMB_DESC = ['', '', '', '速くバラバラ', '遅くバラバラ', '1拍だけ幅広い', '',
              '', '幅広く超速い', '長い休み', 'のこぎり', '150で規則的', '', '300/分']


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
    v = art_apply(pat, rel, wave_from(bl, rel))
    v = v * np.clip(np.minimum(xs - x0, x1 - xs) / 6.0, 0, 1)
    ys = base_y - v*mv
    pad = 40
    size = (int(x1 - x0) + 2*pad, int(3.2*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.7*mv) - pad
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], pat['col'], 2.8, 1.0, blur=(4, 10))
    d = ImageDraw.Draw(lay)
    L = pat['L']
    n_max, n = THUMB_MAX_MARKS.get(i, 2), 0
    for k in range(-2, 6):
        for a, b in marks:
            lo, hi = a + k*L, b + k*L
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
    タイトル → 14パターンを2列×7段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, 'モニター心電図で見分ける', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, TITLE, 112, 900, WHITE, cx=540, cy=436, max_w=880)
    put(im, '見分けられる？', 60, 900, YEL, cx=540, cy=546)
    COLS = [(135, 515), (565, 945)]             # 列のあいだは50px あける（線は引かない）
    NR = (N_PAT + 1) // 2                       # 1列の段の数
    Y0, RH = 628, 852 // NR
    for i, pat in enumerate(PATTERNS):
        c, r = divmod(i, NR)
        x0, x1 = COLS[c]
        y = Y0 + r*RH
        name = f"{pat['no']} {pat['name']}"
        im_n, _ = text_img(name, 26, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 26, 800, pat['col'], x=x0, cy=y + 24, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if THUMB_DESC[i]:
            im_h, _ = text_img(THUMB_DESC[i], 18, 500, (176, 186, 186))
            assert nx + im_h.size[0] - 8 <= x1 + 4, f'{pat["no"]} のひとことが入らない'
            put(im, THUMB_DESC[i], 18, 500, (176, 186, 186), x=nx, cy=y + 26)
        lay, pos = thumb_row_wave(i, x0, x1, y + 24 + (RH - 24)*0.68, 38.0)
        im.alpha_composite(lay, pos)
        if r < NR - 1:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)], fill=(38, 54, 48, 255), width=1)
    by = Y0 + NR*RH + 24
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
def _qrs_ms(f):
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < 0.12)
    return (tt[m].max() - tt[m].min()) * 1000


def _rate(rrs):
    return 60 / (sum(rrs) / len(rrs))


def f_peak(pat, n=4000):
    """f波・F波の、山から谷までの大きさ（mV）。"""
    rel = np.linspace(0, pat['L']*4, n)
    v = pat['art'](rel, pat['L'])
    return v.max() - v.min(), np.percentile(np.abs(v), 95)


def check():
    print('パターンごとの紹介の時間（名前が出ている＝そのパターンの形そのもの）と、その前のつなぎ目')
    kinds = {'direct': '直接', 'via': '基準を通る', 'end': '基準へ'}
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        bd = ''
        if i >= 1:
            k_, t0, t1 = BOUNDARY[i - 1]
            bd = f'  ← {PATTERNS[i-1]["no"]}→{pat["no"]} {kinds[k_]} {t0:5.2f}–{t1:5.2f}s'
        print(f"{pat['no']} {pat['name']:<14} 画面 {a:5.2f}–{b:5.2f}s（{b-a:4.2f}s）{bd}")
    k_, t0, t1 = BOUNDARY[-1]
    print(f'⑭→基準の洞調律 {t0:5.2f}–{t1:5.2f}s')
    print(f'最後のパターンの終わり {T_END:.2f}s → 一覧 {T_END+FLY:.2f}〜{DUR:.2f}s（映像 {DUR:.2f}秒、ループの拍の位相のずれ {LOOP_ERR*1000:.1f}ms）')
    # 拍の形の数値（BPAR）が、もとの関数と同じか
    tt = np.arange(-0.5, 0.75, 0.0005)
    err = max(float(np.abs(eval_par(BPAR[k], tt) - beat_wave(tt, 0.0, k)).max()) for k in KINDS)
    print(f'拍の形の数値（BPAR）ともとの関数の差 最大 {err:.2e}mV')
    assert err < 1e-9
    # 名前が出ているあいだは、そのパターンの形そのもの
    for i in range(N_PAT):
        a, b = WINDOWS[i]
        for t in np.linspace(a, b, 40):
            X, Y, w = state_at(t)
            assert w == 0 and X.pat == i and Y is X, (i, t)
    # 名前が消える瞬間の帯と、枠へ飛ぶコピー（くり返しのパターン）が同じか
    diffs = []
    for i in range(N_PAT):
        b = WINDOWS[i][1]
        tau = tau_c(b) + (FX - XC) / F_PXS
        rel = tau - PHASE[i]
        pv = art_apply(PATTERNS[i], rel, wave_from(periodic_beats(PATTERNS[i], rel[0] - 1, rel[-1] + 1), rel))
        diffs.append(float(np.abs(chain_wave(b, tau) - pv).max()))
    print('名前が消える瞬間の帯とコピーの差（mV）', [round(x, 4) for x in diffs])
    # 拍が跳ばない・重ならない：1/60秒ごとに、画面の拍の位置の動き（紙送りとの差）と、となりの拍との間隔
    jump, min_rr, prev = 0.0, 9.0, {}
    for n in range(int(DUR*60)):
        t = n / 60
        if T_STOP <= t < T_GO:
            continue
        tc = tau_c(t)
        bs = chain_beats(t, margin=0.0)
        cur_ = {}
        for r, _, _, k in bs:
            cur_[k] = r
            if k in prev and n - 1 == prev[k][0]:
                jump = max(jump, abs((r - tc) - prev[k][1]) - 1/60)
        for (r0, *_), (r1, *_) in zip(bs, bs[1:]):
            min_rr = min(min_rr, r1 - r0)
        prev = {k: (n, r - tc) for k, r in cur_.items()}
    print(f'画面の拍の動き：1コマで紙送りより余分に動く最大 {jump*F_PXS:.1f}px、となりの拍との最小の間隔 {min_rr:.3f}秒')
    cr = center_crossings()
    print(f'中央を通る拍（モニター音） {len(cr)}拍')
    print('--- 心拍数カウンター（中央を通った拍ごとの表示。［ ］は形が変わるあいだ。-- は数字を出さない） ---')
    hc = hr_crossings()
    rows = []
    for tx, bpm, nxt in hc:
        if not (CNT_IN <= tx < cnt_out()):
            continue
        i = current(tx)
        lab = PATTERNS[i]['no'] if i is not None else ('～' if morph_span(tx) else '・')
        sh = cnt_text(tx + 0.02)
        if rows and rows[-1][0] == lab:
            rows[-1][1].append(sh)
        else:
            rows.append((lab, [sh]))
    for lab, vals in rows:
        print(f"  {lab} " + (' '.join(vals) if lab not in ('～', '・') else '［' + ' '.join(vals) + '］'))
    # 形が変わるあいだ（t0＋0.2秒〜t1）は、数字を出さない
    bad = [round(n/60, 2) for n in range(int(DUR*60)) if (sp := morph_span(n/60)) and n/60 >= sp[0] + CNT_DASH_T
           and cnt_text(n/60) != '--']
    print(f'  形が変わるあいだに数字が出るコマ：{len(bad)}')
    assert not bad, bad[:5]
    gaps = [nxt for tx, bpm, nxt in hc if CNT_IN <= tx < cnt_out()]
    print(f'  中央を通る間隔の最大 {max(gaps):.2f}秒（⑩の休み {TB_PAUSE:.2f}秒）。1拍に1回だけ変わる。'
          f'出ている時間 {CNT_IN + 0.1:.2f}〜{cnt_out() + 0.4:.2f}秒')
    s0 = ARRS[I_TB].A
    print(f'  ⑩ 最後の心房細動の拍が中央 {t_of(s0 + TB_P0):.2f}秒 → タイマー 0 から → 次の洞調律の拍が中央 {t_of(s0 + TB_P1):.2f}秒'
          f'（タイマー {TB_PAUSE:.1f}秒で止まる。名前は {WINDOWS[I_TB][1]:.2f}秒まで）')
    print('ひとこと＋色の文字の幅（上限 %dpx、文字 32px）' % ONE_W)
    for pat in PATTERNS:
        sz, w = one_size(pat)
        flag = '' if sz == 32 else f'  ← 字が {sz}px に縮む'
        print(f"  {pat['no']} {w:4.0f}px  {pat['one']} {TAGS[pat['tag']][0]}{flag}")
    print('名前の幅（54px、上限 820px）')
    for pat in PATTERNS:
        im_, _ = text_img(f"{pat['no']} {pat['name']}", 54, 900, pat['col'])
        print(f"  {pat['no']} {im_.size[0]-8}px")
    print('--- 波形の数値 ---')
    fc, fm, ff = f_peak(PAT['②']), f_peak(PAT['④']), f_peak(PAT['③'])
    print(f'f波（心房細動）：5〜8Hz（300〜480/分）。山から谷：粗い {fc[0]:.3f}mV、ふつう {fm[0]:.3f}mV、細かい {ff[0]:.3f}mV'
          f'（95%の点の振れ幅 粗い ±{fc[1]:.3f}、細かい ±{ff[1]:.3f}mV。LITFL：0.5mm＝0.05mV が境目）')
    paf_rr = [b[0] - a[0] for a, b in zip(EV_PAF, EV_PAF[1:])]
    print(f'① 洞調律 {60/0.8:.0f}/分 ×{len(PAF_SINUS)}拍 → PAC（R-R {PAF_PAC - PAF_SINUS[-1]:.2f}s、P\' は直前のT波の終わり）'
          f' → 心房細動 平均 {_rate(RR_PAF):.0f}/分（R-R {min(RR_PAF):.2f}〜{max(RR_PAF):.2f}s）。R-R の列 {[round(x, 2) for x in paf_rr]}')
    print(f'② 平均 {_rate(RR_COARSE):.0f}/分（R-R {min(RR_COARSE):.2f}〜{max(RR_COARSE):.2f}s）')
    print(f'③ 平均 {_rate(RR_FINE):.0f}/分（R-R {min(RR_FINE):.2f}〜{max(RR_FINE):.2f}s）')
    print(f'④ 平均 {_rate(RR_FAST):.0f}/分（{60/max(RR_FAST):.0f}〜{60/min(RR_FAST):.0f}/分）')
    print(f'⑤ 平均 {_rate(RR_SLOW):.0f}/分（{60/max(RR_SLOW):.0f}〜{60/min(RR_SLOW):.0f}/分）')
    print(f'⑥ 平均 {_rate(RR_ASH):.0f}/分。長い R-R {RR_ASH[ASH_K-2]:.2f}s → 短い R-R {RR_ASH[ASH_K-1]:.2f}s で来た拍（{T_ASH:.2f}s）が変行伝導'
          f'（QRS {_qrs_ms(qrs_aberrant):.0f}ms、ふつうの拍 {_qrs_ms(qrs_normal):.0f}ms）')
    print(f'⑦ 平均 {_rate(RR_BBB):.0f}/分、全部の拍が QRS {_qrs_ms(qrs_aberrant):.0f}ms')
    print(f'⑧ R-R {RR_CHB[0]:.2f}s で規則的（{60/RR_CHB[0]:.0f}/分、幅の狭い接合部補充調律）＋粗いf波')
    print(f'⑨ 平均 {_rate(RR_WPW):.0f}/分（{60/max(RR_WPW):.0f}〜{60/min(RR_WPW):.0f}/分）、'
          f'QRS {_qrs_ms(_preex(*PREEX["D1"], with_t=False)):.0f}〜{_qrs_ms(_preex(*PREEX["D3"], with_t=False)):.0f}ms'
          '（デルタ波つき。拍ごとに少しちがう。向きは同じ）')
    print(f'⑩ 心房細動 平均 {_rate(RR_TB_AF):.0f}/分 → 最後の拍 {TB_P0:.2f}s → 休み {TB_P1 - TB_P0:.2f}s（f波もP波もない）'
          f' → 洞調律 {60/TB_SINUS_RR:.0f}/分 ×{TB_SINUS_N}拍。タイマーの最後の値 {TB_P1 - TB_P0:.1f}秒')
    fl = f_peak(PAT['⑪'])[0]
    print(f'F波（心房粗動）：{60/FF:.0f}/分、山から谷 {fl:.2f}mV（⑭は {f_peak(PAT["⑭"])[0]:.2f}mV）')
    print(f'⑪ 4:1 → {60/(4*FF):.0f}/分　⑫ 2:1 → {60/(2*FF):.0f}/分　⑭ 1:1 → {60/FF:.0f}/分')
    print(f'⑬ 伝導比 {[round(x/FF) for x in RR_VAR]}、平均 {_rate(RR_VAR):.0f}/分（R-R は 0.2秒の倍数）')
    print('ものさし（R-R の棒の長さ、px）の例：')
    for no in ('②', '⑪', '⑬'):
        i = [p['no'] for p in PATTERNS].index(no)
        rr = [b[0] - a[0] for a, b in zip(PATTERNS[i]['ev'], PATTERNS[i]['ev'][1:])] or [PATTERNS[i]['L']]
        print(f'  {no} {[round(x*F_PXS) for x in rr]}')
    print(f'レイアウト：上の枠 {TOP_Y[0]}〜{_TOP_END}、名前 {Y_NAME:.0f}、ひとこと {Y_ONE:.0f}、基線 {F_BASE:.0f}、'
          f'ものさし {RULER_Y:.0f}、下の枠 {_BOT_TOP}〜{BOT_Y[-1] + CELL_H}（上下の余白 {_GAP:.0f}px）')


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


_CROSS = []


def center_crossings(dt=0.004):
    """中部の帯の拍（R）が画面の中央を通る時刻と、そのときの拍の種類・通しの番号 [(t, 種類, k)]。拍ごとに1回だけ（左へ通りすぎたとき）。"""
    if _CROSS:
        return _CROSS
    prev, done = {}, set()
    for n in range(int(DUR / dt) + 2):
        t = n*dt
        if T_STOP <= t < T_GO:
            continue
        tc = tau_c(t)
        _, _, w = state_at(t)
        for r, kx, ky, k in chain_beats(t, margin=-HALF + 0.4):
            d = r - tc
            if k in prev and prev[k][1] > 0 >= d and k not in done:
                tp, dp = prev[k]
                _CROSS.append((tp + (t - tp)*dp/(dp - d), kx if w < 0.5 else ky, k))
                done.add(k)
            prev[k] = (t, d)
    return _CROSS


def beeps(path, sr=44100):
    """中部の波形の R が画面の中央を通るときに「ピッ」。幅の広い拍は低い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for ts, k, _ in center_crossings():
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 720.0 if k in WIDE else 960.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel26_afl.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 11・slow）。out/reel26_afl_hq.mp4')
    o = ap.parse_args()
    crf, preset = (11, 'slow') if o.hq else (18, 'medium')   # 高画質版 CRF 10→11（2026-10-14：96.6秒になり、GitHub の 100MB をこえないように）
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel26_afl_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel26.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel26_list.png')
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
