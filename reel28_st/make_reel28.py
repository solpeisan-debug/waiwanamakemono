"""第28弾 心筋梗塞とST変化 まず覚えたい10パターン（第17〜21弾と同じ作り＋この回だけの「STの虫眼鏡」「時間の流れのバー」）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。心筋梗塞の時間の流れ：基準 → 超急性期T → ST上昇 → 異常Q → 冠性T、⑥ST低下）
- 中部：時間の流れのバー（②〜⑤のあいだ）→ 名前・ひとこと（うしろに対応を色で）→ STの虫眼鏡（1拍を拡大し、
  基線の点線・矢印・「ST ↑3mm」などの値をモデルから計算して出す）→ いま紹介中の波形（大きく流れる）
- 下部：⑦〜⑩ のミニ波形（2列×2段。心膜炎・左脚ブロック、心筋梗塞のときの不整脈：AIVR・完全房室ブロック）
- 冒頭 0〜2.4秒：変形するフックの上に問いかけ「このST、すぐ報告？」。最後：「保存して見返してね」と「何個わかった？」

波形は、パターンの周期でくり返す決まった形。各拍の特徴のところ（ST-T など）だけ、いま紹介中のパターンの色にする。
II誘導のモニター・実際の速さ（25mm/秒）を想定。モニターだけでは ST 変化は判断できないので、
色の文字（「→ 12誘導で確認」など）・最後の文・キャプションで「12誘導で確認」を出す。

使い方:
    python3 make_reel28.py              # 書き出し・60fps（CPU 4つなので --jobs 2）
    python3 make_reel28.py --still 20   # 1コマだけ
    python3 make_reel28.py --check      # 検算・タイミング表・ひとことの幅
    python3 make_reel28.py --thumb      # サムネイル（透かしなし）
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

C_BASE = (240, 244, 243)         # ① 基準（いつもの形）。緑の線と見分けられるよう白に近く（ST の部分だけこの色）
C_ACUTE = (255, 92, 112)         # ②③ 心筋梗塞の急性期（すぐ報告・12誘導）
C_OLD = (255, 152, 72)           # ④⑤ 時間がたったあと（異常Q・冠性T）
C_DEP = (255, 212, 90)           # ⑥ ST低下（虚血）
C_MIM = (110, 200, 255)          # ⑦⑧ 心筋梗塞とまぎらわしいST変化（心膜炎・左脚ブロック）
C_REP = (196, 162, 255)          # ⑨⑩ 心筋梗塞のときの不整脈（AIVR・完全房室ブロック）

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
# II誘導のモニターを想定。ST の高さは TP（基線）からの高さ。1mm = 0.1mV。
RR = 0.80                        # 洞調律 75/分
PR = 0.16                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def _win(t, a, b, ea, eb):
    """a〜b 秒で 1 になる窓。立ち上がり ea 秒・立ち下がり eb 秒（なめらか）。"""
    u = np.clip((t - a) / ea, 0, 1); d = np.clip((b - t) / eb, 0, 1)
    u = u*u*(3 - 2*u); d = d*d*(3 - 2*d)
    return np.minimum(u, d)


def _dome(t, j, pk, end, a_j, a_pk):
    """J点（j 秒・a_j mV）から上に凸に頂点（pk 秒・a_pk mV）まで上がり、end 秒で基線に戻る ST-T。"""
    up = np.clip((t - j) / 0.014, 0, 1); up = up*up*(3 - 2*up)
    x = np.clip((t - j) / (pk - j), 0, 1)
    rise = a_j + (a_pk - a_j)*np.sin(0.5*np.pi*x)
    y = np.clip((t - pk) / (end - pk), 0, 1)
    fall = a_pk*(1 - y*y*(3 - 2*y))
    return up*np.where(t < pk, rise, fall)


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.022)


def _qrs(t, r=1.00, q=0.08, s=0.20):
    """幅の狭い QRS（小さな q・R・s）。"""
    return -q*_g(t, -0.030, 0.008) + r*_g(t, 0.0, 0.011) - s*_g(t, 0.028, 0.009)


def _q_deep(t, r):
    """異常Q波：幅 40ms 以上・深さ 0.32mV（2mm 以上。R 0.42〜0.45mV に対して QRS の 25% 以上）。"""
    return -0.32*_ga(t, -0.016, 0.013, 0.010) + r*_g(t, 0.016, 0.009) - 0.05*_g(t, 0.038, 0.008)


def qrs_normal(t):               # ① 基準：ST は基線（TP）と同じ高さ
    return _qrs(t) + 0.27*_ga(t, 0.27, 0.060, 0.042)


def qrs_hyperacute(t):           # ② 超急性期T波：T が高く幅広く、左右非対称。R は少し低い。ST はほぼ基線
    return (_qrs(t, r=0.88, s=0.14) + 0.04*_win(t, 0.03, 0.20, 0.02, 0.08)
            + 0.68*_ga(t, 0.26, 0.075, 0.048))


def qrs_ste(t):                  # ③ ST上昇（⑩ 完全房室ブロックの接合部補充調律にも使う＝下壁梗塞）：J点 約0.3mV、上に凸の ST がそのまま T につながる
    return _qrs(t, r=0.85, s=0.10) + _dome(t, 0.024, 0.20, 0.33, 0.27, 0.46)


def qrs_qwave(t):                # ④ 異常Q波：深く幅広い Q、ST はまだ少し高い、T の終わりが下向き
    return (_q_deep(t, 0.42) + 0.13*_win(t, 0.035, 0.24, 0.012, 0.10) - 0.12*_g(t, 0.33, 0.035))


def qrs_ctw(t):                  # ⑤ 冠性T波：Q が残り、ST は基線、左右対称の深い陰性T（約0.36mV）
    return _q_deep(t, 0.45) - 0.36*_g(t, 0.27, 0.050)


def qrs_stdep_h(t):              # ⑥ 水平型ST低下：J点から 0.15mV 下がったまま水平、そのあと T
    return (_qrs(t) - 0.15*_win(t, 0.030, 0.19, 0.010, 0.06) + 0.20*_ga(t, 0.28, 0.05, 0.04))


def qrs_peri(t):                 # ⑦ 心膜炎：PR 部分が 0.07mV 下がり、ST は下に凸で 0.10mV 上がる（頻脈）
    return (_qrs(t) - 0.07*_win(t, -0.12, -0.035, 0.03, 0.010)
            + 0.10*_win(t, 0.03, 0.22, 0.02, 0.08) + 0.24*_ga(t, 0.22, 0.05, 0.035))


def qrs_lbbb(t):                 # ⑧ 左脚ブロック：幅広い・ノッチのある R、ST-T は QRS と逆向き（下がる）
    return (0.68*_ga(t, -0.014, 0.018, 0.013) + 0.74*_ga(t, 0.024, 0.013, 0.018)
            - 0.12*_win(t, 0.062, 0.30, 0.025, 0.10) - 0.24*_ga(t, 0.27, 0.08, 0.05))


def qrs_pvc(t):                  # ⑨ AIVR の1拍：幅の広い QRS、逆向きの ST-T（第21弾の形の 0.85倍。帯の下が枠にくっつかないように）
    return 0.85*(0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
                 - 0.38*_ga(t, 0.25, 0.058, 0.045))


KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍（基準）
    'H': (qrs_hyperacute, p_sinus, PR),     # 超急性期T波
    'E': (qrs_ste, p_sinus, PR),            # ST上昇
    'Q': (qrs_qwave, p_sinus, PR),          # 異常Q波
    'I': (qrs_ctw, p_sinus, PR),            # 冠性T波
    'D': (qrs_stdep_h, p_sinus, PR),        # 水平型ST低下
    'C': (qrs_peri, p_sinus, PR),           # 心膜炎
    'L': (qrs_lbbb, p_sinus, PR),           # 左脚ブロック
    'V': (qrs_pvc, None, 0.0),              # 心室の拍（AIVR）
    'J': (qrs_ste, None, 0.0),              # 接合部補充調律の拍（幅の狭いQRS＋下壁のST上昇。P波とは無関係）
    'P': (None, p_sinus, 0.0),              # P波だけ（完全房室ブロック）
}
SPIKES = {}                                 # この回はペーシングスパイクなし
ALL = [(-1e9, 1e9)]                         # 全部をその色で


def _each(beats, a, b):
    """拍ごとに、R頂点から a〜b 秒の範囲（色を付ける範囲）。"""
    return [(r + a, r + b) for r, _ in beats]


def _reg(kind, rr, n):
    return [(k*rr, kind) for k in range(n)]


# 10パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、色を付ける範囲 hl（この回は連続した波形・ノイズなし。拍だけ）
# ①〜⑤：心筋梗塞の時間の流れ（基準 → 超急性期T → ST上昇（大きいと墓石型）→ 異常Q → 冠性T）
# ⑥：ST低下（虚血）　⑦⑧：ST上昇・ST変化がまぎらわしいもの　⑨⑩：心筋梗塞のときの不整脈
# mag：STの虫眼鏡（中部の帯の上の窓）。ref＝周期の中の、拡大する拍の R の時刻。c＝窓のまん中の時刻（ref からの秒）。
#      mm＝1mm の大きさ（px。たて 0.1mV・よこ 0.04秒が同じ大きさの正方形＝「1マス＝1mm」。中部の帯は 14px）、
#      base＝窓の描画域の上から基線までの px。
#      marks：('v', 名前, 時刻) 基線からその時刻の波形までの矢印と「名前 ↑2mm」。時刻は数値（ref からの秒）か
#             'J'（J点）'J60'（J点+60ms）'Tmax' 'Tmin' 'Qmin'（モデルから計算）。4つめは矢印の横のずらし（px。値は変えない）
#             ('w', 名前) QRS の幅のかっこ（始まり〜J点）と「名前 0.15秒」
#             ('p', [時刻…]) P波の上に「P」　('t', 文) 値のうしろに一言
_E = {k: _reg(k, RR, 6) for k in 'NHQIDL'}
_C = _reg('C', 0.56, 9)                     # 107/分（9拍＝5.04秒）
_E3 = _reg('E', RR, 7)                      # ③ は台本が長い（墓石型にもふれる）ので 7拍＝5.6秒
AIVR_RR = 0.78                              # 77/分（洞調律 70/分より少し速い）
_A = [(0.0, 'N'), (0.86, 'N')] + [(1.64 + k*AIVR_RR, 'V') for k in range(4)]
# ⑩ 完全房室ブロック（下壁梗塞。LITFL の例：心房 ~85/分・心室 ~38/分・接合部補充調律・下壁のST上昇）
CHB_PP, CHB_RR, CHB_Q0 = 0.70, 1.575, 0.40  # 心房 86/分、心室 38/分。周期 6.3秒（P 9個・QRS 4個）
_H = [(k*CHB_PP, 'P') for k in range(9)] + [(CHB_Q0 + k*CHB_RR, 'J') for k in range(4)]
_CHB_REF = CHB_Q0 + CHB_RR                  # 拡大する QRS（2つめ）
PATTERNS = [
    dict(no='①', name='基準の洞調律', col=C_BASE, hint='いつもの形',
         one='STは基線（TP）と同じ高さ', tag='base',
         ev=_E['N'], L=4.8, hl=_each(_E['N'], 0.035, 0.17),
         mag=dict(subj='ST', ref=0.8, c=0.12, mm=16, base=76, marks=[('v', 'ST', 'J60')])),
    dict(no='②', name='超急性期T波', col=C_ACUTE, hint='Tが大きい',
         one='Tが高く幅広い。早期のサイン', tag='urgent',
         ev=_E['H'], L=4.8, hl=_each(_E['H'], 0.04, 0.40),
         mag=dict(subj='T', ref=0.8, c=0.12, mm=16, base=104, lab_t=-0.31, marks=[('v', 'T', 'Tmax')])),
    dict(no='③', name='ST上昇', col=C_ACUTE, hint='STが上がる',
         one='STが上がる。大きいと墓石型', tag='urgent',
         ev=_E3, L=5.6, hl=_each(_E3, 0.02, 0.36),
         mag=dict(subj='ST', ref=0.8, c=0.12, mm=16, base=106, lab_t=0.50, marks=[('v', 'ST', 'J', 10)])),
    dict(no='④', name='異常Q波', col=C_OLD, hint='深いQ',
         one='深く幅広いQ。梗塞のあと', tag='check',
         ev=_E['Q'][:5], L=4.0, hl=_each(_E['Q'][:5], -0.05, 0.035),
         mag=dict(subj='Q', ref=0.8, c=0.08, mm=14, base=66, lab_t=0.52, marks=[('v', 'Q', 'Qmin', -14)])),
    dict(no='⑤', name='冠性T波', col=C_OLD, hint='Tが下向き',
         one='左右対称の深い陰性T', tag='check',
         ev=_E['I'][:5], L=4.0, hl=_each(_E['I'][:5], 0.10, 0.42),
         mag=dict(subj='T', ref=0.8, c=0.12, mm=16, base=40, lab_t=-0.33, marks=[('v', 'T', 'Tmin')])),
    dict(no='⑥', name='ST低下（水平・下降型）', col=C_DEP, hint='水平・下り坂',
         one='水平に下がる。虚血のサイン', tag='urgent',
         ev=_E['D'], L=4.8, hl=_each(_E['D'], 0.025, 0.22),
         mag=dict(subj='ST', ref=0.8, c=0.10, mm=20, base=62, lab_t=0.52, marks=[('v', 'ST', 'J60')])),
    dict(no='⑦', name='急性心膜炎', col=C_MIM, hint='PRも下がる',
         one='PR低下＋下に凸のST上昇', tag='check',
         ev=_C, L=5.04, hl=_each(_C, -0.12, -0.035) + _each(_C, 0.03, 0.30),
         mag=dict(subj='PRとST', ref=0.56, c=0.02, mm=20, base=70, lab='below',
                  marks=[('v', 'PR', -0.07), ('v', 'ST', 'J')])),
    dict(no='⑧', name='左脚ブロック', col=C_MIM, hint='幅広QRS',
         one='幅広QRS。STは逆向きが基本', tag='check',
         ev=_E['L'], L=4.8, hl=ALL,
         mag=dict(subj='ST', ref=0.8, c=0.12, mm=16, base=54, lab='below',
                  marks=[('v', 'ST', 'J60'), ('t', 'QRSと逆向き')])),
    dict(no='⑨', name='AIVR（促進心室固有調律）', col=C_REP, hint='幅広・再灌流',
         one='再灌流で出やすい幅広リズム', tag='report',
         ev=_A, L=round(1.64 + 4*AIVR_RR, 2), hl=_each(_A[2:], -0.08, 0.45),
         mag=dict(subj='QRS', ref=1.64, c=-0.30, mm=8, base=78, lab_t=-1.06, marks=[('w', 'QRS')])),   # 左に洞調律の細いQRS、右にAIVRの幅広QRS
    dict(no='⑩', name='完全房室ブロック', col=C_REP, hint='PとQRSが別々',
         one='PとQRSが別々。下壁梗塞で', tag='now',
         ev=_H, L=round(9*CHB_PP, 2), D=4.36, hl=ALL,
         mag=dict(subj='PとQRS', title='P と QRS　1マス＝1mm', ref=_CHB_REF, c=CHB_RR/2, mm=10, base=92, lab='below',
                  marks=[('p', [r - _CHB_REF + n*9*CHB_PP for r, k in _H if k == 'P' for n in (-1, 0, 1)]),
                         ('t', f'P {60/CHB_PP:.0f}/分・QRS {60/CHB_RR:.0f}/分')])),
]


N_PAT = len(PATTERNS)
for _p in PATTERNS:
    _p['beats'] = _p['ev']

# 区間の長さ（秒）。仮の値（録音前）：台本の文の長さの見込み（6字/秒）＋0.75秒以上で、
# 拍の並びがくずれない位置（周期 L の終わり＝次の拍まで、そのパターンの R-R 間隔）で切る。
# - ①②⑥⑧ 4.8：75/分の6拍　- ③ 5.6：75/分の7拍　- ④⑤ 4.0：75/分の5拍　- ⑦ 5.04：107/分の9拍
# - ⑨ 4.76：洞調律2拍＋AIVR 4拍（最後の拍から次まで 0.78秒）
# - ⑩ 4.36：周期 6.3秒の途中。最後の QRS（3.55秒）から次の洞調律まで 0.81秒。次の洞調律の P 波（4.20秒）は
#   心房のリズム（0.70秒ごと）の続きになるので、⑩ の 4.20秒の P 波は落とす（_strip）
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {p['no']: p.get('D', p['L']) for p in PATTERNS}
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    assert _p['D'] >= 3.44 - 1e-9, _p['no']


def beat_wave(tau, r, kind):
    q, p, pr = KINDS[kind]
    v = np.zeros_like(tau)
    if q is not None:
        v += q(tau)
    if p is not None:
        v += p(tau + pr)
    return v


def spike_times(beats):
    """拍の列 → スパイクの列 [(時刻, 高さ), …]"""
    out = []
    for r, k, *_ in beats:
        for dt, amp in SPIKES.get(k, ()):
            out.append((r + dt, amp))
    return out


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


# --- 中部の帯：10パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンを rep 回くり返して置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭のフック：流れている波形を T_STOP で止め、その場で5つのパターンに素早く変形し、
# 元の波形に戻ってから T_GO でまた流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.25, 2.9           # 問いかけ（0秒〜）のあいだに変形が始まるよう、止めるのを 0.6→0.25秒に
FREEZE = T_GO - T_STOP
T_TITLE = 4.9                     # 冒頭の1文（4.9秒）が入り、見出しと枠が出そろう長さ
END_HOLD = 6.5                    # 10個そろってからの時間（まとめ・保存の2文、「何個わかった？」を読む間、冒頭へ戻る時間）
HOOK = [1, 2, 3, 4, 5]            # ②超急性期T → ③ST上昇 → ④異常Q → ⑤冠性T（心筋梗塞の時間の流れ）→ ⑥ST低下
HOOK_T0, HOOK_STEP, HOOK_MORPH = 0.3, 0.38, 0.12


def _strip():
    beats = []        # (R時刻, 種類, パターン番号 or None)
    segs = []
    t = 0.0
    for i, pat in enumerate(PATTERNS):
        s0 = t
        for r, kind in periodic_beats(pat, 0.0, pat['D']):
            if -1e-9 <= r < pat['D'] - 1e-9:
                if kind == 'P' and r > pat['D'] - 0.2:     # 次の洞調律の P 波と重なるので落とす（⑩）
                    continue
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
STRIP_SPK = spike_times(STRIP)          # 中部の帯のスパイク [(時刻, 高さ)]

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# 中部のかたまり（上から）：時間の流れのバー（22px）→ 名前（54px）→ ひとこと（32px）→ STの虫眼鏡（窓 170px）
# → 波形（R頂点 1mV 〜 下 約0.4mV。AIVR の S は 約0.5mV）
_TOP_END = 604 + 110               # ③⑥の下端
_BOT_TOP = 1308                    # ⑦⑨の上端
# バーのある回（②〜⑤）とない回で、名前・ひとこと・窓の高さを分ける（上の枠〜窓の上下の余白をそろえる。検査役 2026-10-06）
STACK_BAR = dict(bar=744, name=806, one=860, mag=892)
STACK_NOBAR = dict(bar=None, name=777, one=831, mag=871)
BAR_CY = STACK_BAR['bar']
Y_NAME, Y_ONE = STACK_BAR['name'], STACK_BAR['one']     # フック・サムネイルなどはこの高さを使う
MAG_X0, MAG_X1 = 240, 840          # STの虫眼鏡の窓
MAG_H = 170
MAG_Y0 = STACK_BAR['mag']
MAG_Y1 = MAG_Y0 + MAG_H
F_BASE = 1225                      # 帯は動かさない。窓の下（バーあり 1062）〜R頂点 と、帯の底（約0.43mV）〜下の枠 をそろえる


def stack_y(cur):
    return STACK_BAR if cur in (1, 2, 3, 4) else STACK_NOBAR
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
    # 区間の終わりが右端の少し先（0.35秒）に来た瞬間。次のパターンの最初のP波・細動波が
    # 右端に入る前に縮み始めるので、見えているのはパターン i だけになる
    _b = t_of(SEGS[_i][1] - HALF - HANDOFF_EARLY)
    WINDOWS.append((_a, _b))
T_END = WINDOWS[-1][1]
FLY = 0.8                                  # 中部から枠へ縮んで移る時間
LOOP_FADE = 0.75                           # 最後に冒頭の画面へ戻す時間
FPS_LOOP = 60
DUR_TARGET = round(_DUR_LOOP * FPS_LOOP) / FPS_LOOP


DUR = DUR_TARGET


# --- ミニ波形の枠 -----------------------------------------------------------------
CELL_W, CELL_H = 400, 110
COL_X = (130, 550)
TOP_Y = [364, 484, 604]            # ①〜⑥（2列×3段）
BOT_Y = [1308, 1428]               # ⑦〜⑩（2列×2段。下端 1538 は第21弾と同じ）
CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える。洞停止・完全房室ブロック用）
M_MV = 33.0


def cell_rect(i):
    if i < 6:
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
    else:
        j = i - 6
        col, row = j // 2, j % 2
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
            m = (tau >= s0 - 0.20) & (tau < s1)
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
    """中部の帯：(波形, 色の番号, スパイク [(x, 高さ, 色の番号)])"""
    tau = tau_center + (FX - XC) / F_PXS
    spk = []
    for ts, amp in STRIP_SPK:
        x = XC + (ts - tau_center) * F_PXS
        if -10 <= x <= W + 10:
            spk.append((x, amp, int(strip_colors(np.array([ts]))[0])))
    return wave_from(STRIP, tau), strip_colors(tau), spk


# スパイクは波形の線より少し太く、明るく描く（SNSで圧縮されても細い線が消えないように。専門医レビュー 2026-10-03）
SPIKE_W = 1.35                   # 波形の線の太さに対する倍率
SPIKE_W_MIN = 3.2                # 最小の太さ（px）
SPIKE_LIGHT = 0.35               # 白に寄せる割合


def spike_layer(size, runs, col, lw, a, blur):
    return glow_line(size, runs, mix(col, (255, 255, 255), SPIKE_LIGHT), max(lw*SPIKE_W, SPIKE_W_MIN), a, blur=blur)


def spike_runs(spk, xs, ys, mv, x_off=0.0, y_off=0.0):
    """スパイクを縦の線（点列）にする。根元は波形の高さ、少し下から上へ。"""
    out = []
    for x, amp, *_ in spk:
        yb = float(np.interp(x, xs, ys))
        out.append([(x - x_off, yb + 0.12*amp*mv - y_off), (x - x_off, yb - amp*mv - y_off)])
    return out


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
    spk = []
    for ts, amp in spike_times(bl):
        if rel[0] <= ts <= rel[-1]:
            x = XC + (ts - c - pat['L']) * F_PXS
            on = pat['hl'] is ALL or bool(hl_mask(pat, np.array([ts]))[0])
            spk.append((x, amp, i if on else -1))
    return v, cid, spk


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


def draw_wave(v, cid, base_col, a, spk=()):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(set(np.unique(cid).tolist()) | {c for *_, c in spk}):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
        sr = spike_runs([q for q in spk if q[2] == ci], FX, ys, F_MV)
        if sr:
            out.alpha_composite(spike_layer((W, h), sr, col, 4.5, a, (8, 20)))
    return out


def featured(t, base_col, a, cur=None):
    """中部の帯。色を付けるのは「いま紹介中のパターン（cur）」だけ。区間の始まりのあいだ、
    左に残っている前のパターンの拍は緑に戻す（となりどうしが同じ色のとき、新しい名前の下に
    前のパターンの色が残って見えないように。検査役の指摘 2026-10-06）。"""
    if T_STOP <= t < T_GO:
        (v0, c0, s0), (v1, c1, s1), u, _ = hook_state(t)
        return draw_wave(v0 + (v1 - v0)*u, c1 if u >= 0.5 else c0, base_col, a, s1 if u >= 0.5 else s0)
    v, cid, spk = strip_arrays(tau_c(t))
    c = -1 if cur is None else cur
    cid = np.where(cid == c, cid, -1)
    spk = [(x, amp, ci if ci == c else -1) for x, amp, ci in spk]
    return draw_wave(v, cid, base_col, a, spk)


STRIP_W, STRIP_H, STRIP_BASE = CELL_W - 20, 76, 50     # ミニ波形の帯（枠の中）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 30


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
    spk = []
    for ts, amp in spike_times(bl):
        if rel[0] <= ts <= rel[-1]:
            on = pat['hl'] is ALL or bool(hl_mask(pat, np.array([ts]))[0])
            spk.append((xs[0] + (ts - rel[0]) * pxs, amp, on))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = ect == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - by0)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        w_, a_ = ((lw_e or lw) if flag else lw), (a if flag else a*a_norm)
        if runs:
            out.alpha_composite(glow_line(size, runs, col, w_, a_, blur=blur))
        sr = spike_runs([q for q in spk if q[2] == flag], xs, ys, mv, bx0, by0)
        if sr:
            out.alpha_composite(spike_layer(size, sr, col, w_, a_, blur))
    return out, (bx0, by0)


def lerp(a, b, u):
    return a + (b - a)*u


# ミニ波形の基線の上下のずらし（px）。④⑤は R が低く下向きの Q・T が深いので、枠の中で下に寄って見える。
# 約9px 上げて、波形の上下のすき間をそろえる（④⑤）（検査役の推奨 2026-10-06）
MINI_DY = {3: -9, 4: -9}


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


MINI_LW_ECT = 3.8                  # ミニ波形で、色を付けた部分（ST-T など）の線の太さ（ほかは 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、ふつうの拍の濃さ


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
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 17,
            a=a_all, max_w=CELL_W - 30)
    elif state == 'now':
        put(base, pat['no'], 30, 700, pat['col'], x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2))
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=CELL_W - 80)


# --- 画面 ---------------------------------------------------------------------------
HEADER = [('心筋梗塞とST変化', 1.0, WHITE), ('10', 2.0, (255, 214, 64)), ('パターン', 1.0, WHITE)]
HEADER_BASE = 342                   # 見出しのベースライン（y）。「10」の上端 約274（上 250px より下）
NOTE1 = '※II誘導のモニター（実際の速さ）'           # 「12誘導で確認」は色の文字・最後の文・キャプションで
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'
END_LINE = 'モニターのST変化は、12誘導で確認'
HOOK_Q = 'このST、すぐ報告？'                   # 冒頭の問いかけ（フックの上）
END_Q = '何個わかった？コメントで教えてね'     # 最後の問いかけ（保存のとなり）


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「心筋梗塞とST変化」＋大きな黄色の「12」＋「パターン」。左右の余白（130px）に収める。"""
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


# ひとことのうしろに、対応を色で。モニター（II誘導）だけでは ST 変化は判断できないので、ST の話は「12誘導」へつなぐ
ONE_W = 760                         # ひとこと＋色の文字の幅の上限（左右に 160px 以上の余白。端で切れて見えないように）
TAGS = {
    'base': ('→ 比べる基準', (130, 232, 172)),           # ① いつもの形（変化はこれと比べる）
    'urgent': ('→ すぐ報告・12誘導', (255, 96, 96)),     # ②③⑥ 急性の心筋梗塞・虚血を疑う形
    'check': ('→ 12誘導で確認', (255, 176, 72)),         # ④⑤⑦⑧ モニターでは決められない
    'report': ('→ 報告して観察', (196, 170, 255)),       # ⑨ AIVR（多くは自然におさまる）
    'now': ('→ すぐ報告', (255, 96, 96)),                # ⑩ 完全房室ブロック（心室停止の危険）
}


# --- STの虫眼鏡（この回だけ）：中部の帯の上の窓に、1拍（⑩は約1.5秒）を拡大して描く ---------------------
# 窓の中：1mm（0.1mV・0.04秒）のうすい方眼、基線（TP）の点線、ST などの位置の矢印。右上に値（モデルから計算）。
MAG_PAD, MAG_HEAD = 14, 40          # 窓の左右の余白、上の見出しの行の高さ
_MAG = {}


def _mag_area():
    return MAG_X0 + MAG_PAD, MAG_Y0 + MAG_HEAD, MAG_X1 - MAG_PAD, MAG_Y1 - 6


def _ref_kind(pat):
    m = pat['mag']
    return [k for r, k in pat['ev'] if abs(r - m['ref']) < 1e-6][0]


def _mag_time(pat, key):
    """虫眼鏡の印の時刻（拡大する拍の R からの秒）。数値はそのまま、文字はモデルから計算。"""
    if not isinstance(key, str):
        return key
    f = KINDS[_ref_kind(pat)][0]
    j = _j_time(f)
    if key == 'J':
        return j
    if key == 'J60':
        return j + 0.06
    tt = np.arange(-0.10, 0.50, 0.0005)
    v = f(tt)
    if key in ('Tmax', 'Tmin'):
        late = tt > j + 0.04
        return float(tt[late][np.argmax(v[late]) if key == 'Tmax' else np.argmin(v[late])])
    if key == 'Qmin':
        early = tt < 0.0
        return float(tt[early][np.argmin(v[early])])
    raise KeyError(key)


def _mag_value(pat, t_rel):
    """拡大している波形の、その時刻の高さ（mV。基線＝TP からの高さ）。"""
    tau = np.array([pat['mag']['ref'] + t_rel])
    bl = periodic_beats(pat, tau[0] - 1, tau[0] + 1)
    return float(wave_from(bl, tau)[0])


def _mm(v):
    """mV → mm。1mm 以上は 0.5mm きざみ、1mm 未満は 0.1mm きざみ（心膜炎の PR 低下・ST 上昇は 1mm 未満）。"""
    x = abs(v)*10
    if x < 0.25:                                          # 0.25mm 未満は「0mm（基線と同じ）」
        return 0
    return round(x*2)/2 if x >= 0.95 else round(x, 1)


def mag_title(i):
    m = PATTERNS[i]['mag']
    return m.get('title', '拡大　1マス＝1mm')       # 何を見るかは右の値（「ST ↑3mm」など）でわかる


def mag_marks(i):
    """('v', 名前, 時刻, 値mV, 横のずらしpx) / ('w', 名前, 始まり, 終わり, 秒) / ('p', [時刻]) / ('t', 文)"""
    pat = PATTERNS[i]
    out = []
    for mk in pat['mag']['marks']:
        if mk[0] == 'v':
            tr = _mag_time(pat, mk[2])
            out.append(('v', mk[1], tr, _mag_value(pat, tr), mk[3] if len(mk) > 3 else 0))
        elif mk[0] == 'w':
            f = KINDS[_ref_kind(pat)][0]
            tt = np.arange(-0.12, 0.2, 0.0005)
            on = float(tt[np.abs(f(tt)) > 0.03].min())
            j = _j_time(f)
            out.append(('w', mk[1], on, j, j - on))
        else:
            out.append(mk)
    return out


def mag_readout(i):
    parts = []
    for mk in mag_marks(i):
        if mk[0] == 'v':
            x = _mm(mk[3])
            parts.append(f"{mk[1]} 0mm（基線と同じ）" if x == 0 else f"{mk[1]} {'↑' if mk[3] > 0 else '↓'}{x:g}mm")
        elif mk[0] == 'w':
            parts.append(f"{mk[1]} {mk[4]:.2f}秒（幅広）")
        elif mk[0] == 't':
            parts.append(mk[1])
    return '　'.join(parts)


def _dashed_hline(d, x0, x1, y, col, dash=10, gap=7, width=2):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=col, width=width)
        x += dash + gap


def _mag_layer(i):
    """窓の絵（RGBA、窓の大きさ）。毎コマ同じなので作りおきする。"""
    if i in _MAG:
        return _MAG[i]
    pat = PATTERNS[i]
    m = pat['mag']
    w, h = MAG_X1 - MAG_X0, MAG_Y1 - MAG_Y0
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=18, fill=CARD_FILL + (242,), outline=pat['col'] + (140,), width=2)
    # 見出し：虫眼鏡の印＋「STを拡大 1マス＝1mm」、右に値
    d.ellipse((14, 11, 30, 27), outline=(176, 186, 186, 255), width=3)
    d.line([(28, 25), (36, 33)], fill=(176, 186, 186, 255), width=4)
    put(lay, mag_title(i), 22, 500, (176, 186, 186), x=44, cy=23)
    tw = text_img(mag_title(i), 22, 500, (176, 186, 186))[0].size[0] - 8
    rd = mag_readout(i)
    put(lay, rd, 30, 900, pat['col'], right=w - 16, cy=24, max_w=w - 44 - tw - 40)
    # 描画域
    px0, py0, px1, py1 = [v - o for v, o in zip(_mag_area(), (MAG_X0, MAG_Y0, MAG_X0, MAG_Y0))]
    pw, ph = px1 - px0, py1 - py0
    plot = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
    dp = ImageDraw.Draw(plot)
    mvpx = m['mm']*10                                     # 1mV の高さ（px）
    pxs = m['mm']/0.04                                    # 1秒の長さ（px）
    span = pw / pxs
    t0 = m['c'] - span/2
    yb = m['base']
    # 1mm の方眼（0.1mV・0.04秒）
    k0 = -int(yb / (0.1*mvpx)) - 1
    for k in range(k0, int((ph - yb) / (0.1*mvpx)) + 2):
        y = yb + k*0.1*mvpx
        dp.line([(0, y), (pw, y)], fill=(40, 66, 56, 255) if k % 5 else (58, 90, 76, 255), width=1)
    n0 = int(math.floor(t0 / 0.04))
    for n in range(n0, n0 + int(span / 0.04) + 2):
        x = (n*0.04 - t0) * pxs
        dp.line([(x, 0), (x, ph)], fill=(40, 66, 56, 255) if n % 5 else (58, 90, 76, 255), width=1)
    # 波形（特徴の部分はパターンの色）
    xs = np.arange(0, pw + 0.5, 0.5)
    rel = m['ref'] + t0 + xs / pxs
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    v = wave_from(bl, rel)
    ys = yb - v*mvpx
    on = np.ones(len(xs), dtype=bool) if pat['hl'] is ALL else hl_mask(pat, rel)
    # 基線（TP）の点線と「基線」
    _dashed_hline(dp, 0, pw, yb, (214, 222, 222, 230))
    for flag, col in ((False, WAVE_GREEN), (True, pat['col'])):
        sel = on == flag
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        if runs:
            plot.alpha_composite(glow_line((pw, ph), runs, col, 4.0, 1.0, blur=(5, 12)))
    # 「基線」の字：ふつうは右はしの点線の上。波形と重なる回は、点線の下（lab='below'）か、時刻 lab_t の上
    lab_y = yb + 16 if m.get('lab') == 'below' else yb - 14
    if m.get('lab_t') is not None:
        put(plot, '基線', 20, 700, (214, 222, 222), cx=(m['lab_t'] - t0) * pxs, cy=lab_y)
    else:
        put(plot, '基線', 20, 700, (214, 222, 222), right=pw - 6, cy=lab_y)
    # 印
    arrow_col = mix(pat['col'], (255, 255, 255), 0.35)
    marks = mag_marks(i)
    n_v = sum(1 for mk in marks if mk[0] == 'v' and _mm(mk[3]) > 0)
    for mk in marks:
        if mk[0] == 'v' and _mm(mk[3]) > 0:
            x = (mk[2] - t0) * pxs + mk[4]
            yv = yb - mk[3]*mvpx
            sgn = 1 if yv > yb else -1                       # 下向き 1、上向き -1
            dp.line([(x, yb), (x, yv - sgn*9)], fill=arrow_col + (255,), width=4)
            dp.polygon([(x, yv), (x - 8, yv - sgn*12), (x + 8, yv - sgn*12)], fill=arrow_col + (255,))
            if n_v > 1:                                      # 矢印が2つあるときは、どちらが何かを小さく
                put(plot, mk[1], 20, 800, arrow_col, cx=x + 18, cy=yv + sgn*16)
        elif mk[0] == 'w':                                   # QRS の幅：始まり〜J点にうすい帯、基線の高さにかっこ
            x0 = (mk[2] - t0) * pxs; x1 = (mk[3] - t0) * pxs
            band = Image.new('RGBA', (pw, ph), (0, 0, 0, 0))
            ImageDraw.Draw(band).rectangle((x0, 0, x1, ph), fill=pat['col'] + (40,))
            plot = Image.alpha_composite(band, plot)
            dp = ImageDraw.Draw(plot)
            y = yb
            dp.line([(x0, y), (x1, y)], fill=arrow_col + (255,), width=3)
            for x in (x0, x1):
                dp.line([(x, y - 9), (x, y + 9)], fill=arrow_col + (255,), width=3)
        elif mk[0] == 'p':
            for tp in mk[1]:
                x = (tp - t0) * pxs
                if not 10 <= x <= pw - 10:                   # 窓の外の P は描かない
                    continue
                put(plot, 'P', 20, 800, arrow_col, cx=x, cy=yb - 0.15*mvpx - 16)
    # 描画域の上 14px はうすく消す（見出しの真下で R がぷつんと切れて見えないように）
    a_ch = np.asarray(plot.getchannel('A'), dtype=np.float32)
    fade = np.clip(np.arange(ph, dtype=np.float32) / 14.0, 0, 1)[:, None]
    plot.putalpha(Image.fromarray((a_ch*fade).astype(np.uint8)))
    lay.alpha_composite(plot, (px0, py0))
    _MAG[i] = lay
    return lay


def draw_mag(im, i, a, y0):
    if a <= 0.004:
        return
    lay = _mag_layer(i)
    if a < 0.999:
        lay = lay.copy()
        lay.putalpha(lay.getchannel('A').point(lambda q: int(q*a)))
    im.alpha_composite(lay, (MAG_X0, y0))


# --- 時間の流れのバー（②〜⑤のあいだ）。時間の目安（何時間など）は書かない ---------------------------
TIME_STAGES = ['超急性期T', 'ST上昇', '異常Q波', '冠性T']    # ②③④⑤


def draw_time_bar(im, t, cur):
    a = ramp(t, WINDOWS[1][0] + 0.1, 0.3) * (1 - ramp(t, WINDOWS[4][1] - 0.25, 0.25))
    if a <= 0.004:
        return
    if cur in (1, 2, 3, 4):
        st = cur - 1
    else:
        st = 0 if t < WINDOWS[1][0] + 1 else 3
    items = [('時間の流れ', 22, 500, (150, 160, 162), 18)]
    for k, lab in enumerate(TIME_STAGES):
        if k:
            items.append(('→', 24, 500, (110, 124, 122), 10))
        on = k == st
        items.append((lab, 28 if on else 26, 800 if on else 500, PATTERNS[k + 1]['col'] if on else (120, 134, 132), 10))
    ws = [text_img(s_, sz, wt, col)[0].size[0] - 8 for s_, sz, wt, col, _ in items]
    total = sum(ws) + sum(g for *_, g in items[:-1])
    x = 540 - total / 2
    d = ImageDraw.Draw(im, 'RGBA')
    k = 0
    for (s_, sz, wt, col, g), w_ in zip(items, ws):
        put(im, s_, sz, wt, col, x=x, cy=BAR_CY, a=a)
        if s_ in TIME_STAGES:
            if TIME_STAGES.index(s_) == st:
                d.rounded_rectangle((x, BAR_CY + 18, x + w_, BAR_CY + 22), radius=2,
                                    fill=PATTERNS[st + 1]['col'] + (int(255*a),))
        x += w_ + g


def draw_one(im, pat, a, y_one=Y_ONE):
    """中部のひとこと。うしろに色の文字（TAGS）を続けて、まとめて中央ぞろえ。"""
    tag = TAGS.get(pat.get('tag'))
    if tag is None:
        put(im, pat['one'], 32, 500, (226, 232, 231), cx=540, cy=y_one, a=a, max_w=820)
        return
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8
        if w1 + 14 + w2 <= ONE_W or sz <= 24:
            break
        sz -= 1
    x0 = 540 - (w1 + 14 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=y_one, a=a)
    put(im, tag[0], sz, 800, tag[1], x=x0 + w1 + 14, cy=y_one, a=a)


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
        al = ramp(t, a_i + 0.1, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        sy = stack_y(cur)
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=sy['name'], a=al, max_w=820)
        draw_one(im, pat, al, sy['one'])
        # 虫眼鏡は、前のパターンが枠に着地したあと（FLY のあと）に出す
        a_mag = ramp(t, a_i + (FLY - 0.1 if cur > 0 else 0.1), 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
    draw_time_bar(im, t, cur)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = max(1 - ramp(t, T_GO - 0.5, 0.5), a_loop)
    a_q = max(1 - ramp(t, 2.1, 0.35), a_loop)       # 問いかけ：0秒から（フックのあいだ）出し、見出しが出るまえに消す
    if a_q > 0:
        put(im, HOOK_Q, 72, 900, (255, 214, 64), cx=540, cy=520, a=a_q, max_w=820)   # 冒頭の字は全部 +110px（問いかけが波形に近くなるように）
    if a_t > 0:
        put(im, '心電図で気づく', 36, 500, PURPLE, cx=540, cy=670, a=a_t)
        put(im, '心筋梗塞とST変化', 150, 900, WHITE, cx=540, cy=800, a=a_t, max_w=880)
        if T_STOP <= t < T_GO:
            _, _, u, shown = hook_state(t)
            if shown is not None:
                pat = PATTERNS[shown]
                put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE + 100,
                    a=a_t*ramp(u, 0.3, 0.4), max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, END_LINE, 42, 800, WHITE, cx=540, cy=Y_NAME + 25, a=a_end, max_w=820)   # 3行を +25px（上下の余白をそろえる）
        a_save = ramp(t, T_END + FLY + 1.5, 0.6)*keep
        put(im, '保存して見返してね', 36, 700, GREEN, cx=540, cy=Y_ONE + 25, a=a_save)
        put(im, END_Q, 36, 700, (255, 214, 64), cx=540, cy=Y_ONE + 83, a=a_save, max_w=820)

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
    if cur is not None:                               # 虫眼鏡は波形のあと（R のグローの上）に描く
        draw_mag(im, cur, a_mag, stack_y(cur)['mag'])

    put(im, NOTE1, 24, 400, GREY, x=135, cy=1560, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=1587, a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1570, a=0.42)   # 下の字が 1600px より上に入るよう 1576→1570
    return im.convert('RGB')


def thumbnail():
    """サムネイル（透かしなし）。10個そろった一覧に、大きな「心筋梗塞とST変化」と③ST上昇の波形。
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
    put(im, 'モニターのST、どう見る？', 38, 700, (226, 232, 231), cx=540, cy=Y_NAME - 28, max_w=820)
    put(im, '心筋梗塞とST変化', 96, 900, WHITE, cx=540, cy=Y_ONE + 14, max_w=880)
    v, cid, spk = hook_arrays(2)
    wl = draw_wave(v, cid, WAVE_GREEN, 1.0, spk)
    im.alpha_composite(wl, (0, F_Y0 - 46))          # 大きなタイトルと下の枠のまん中（10パターンの配置）
    return im.convert('RGB')


# --- 一覧型のサムネイル（第17弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {i: (-0.5, []) for i in range(N_PAT)}          # 最初の拍が左端から 0.5秒のところ
THUMB_VIEW[1] = (-0.5, [(0.80 + 0.06, 0.80 + 0.40)])         # 超急性期T：大きなT（2拍目）
THUMB_VIEW[3] = (-0.5, [(0.80 - 0.06, 0.80 + 0.03)])         # 異常Q波（2拍目）
THUMB_VIEW[4] = (-0.5, [(0.80 + 0.12, 0.80 + 0.42)])         # 冠性T：下向きのT（2拍目）
THUMB_VIEW[5] = (-0.5, [(0.80 + 0.02, 0.80 + 0.22)])         # 水平型ST低下：J点からの水平な低下（2拍目）
THUMB_VIEW[6] = (-0.5, [(0.56 - 0.14, 0.56 - 0.02)])         # 心膜炎：PR低下（2拍目の前。少し広め）
THUMB_VIEW[8] = (1.0, [])                                    # AIVR：洞調律のあと、幅の広い拍が続く
THUMB_VIEW[9] = (CHB_Q0 - 0.15, [])                          # 完全房室ブロック：P と QRS が別々。QRS を3つ見せる（この行だけ 3.4秒）
THUMB_SPAN = {9: 3.4}
THUMB_MAX_MARKS = {1: 1, 3: 1, 4: 1, 5: 1, 6: 1}
THUMB_DESC = ['STは基線', 'Tが大きい', 'STが上がる', '深いQ', 'Tが下向き',
              '', 'PRも下がる', '逆向きのST', '', 'PとQRSが別々']


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
    spk = [(x0 + (ts - t0)*pxs, amp) for ts, amp in spike_times(bl) if rel[0] + 0.03 <= ts <= rel[-1] - 0.03]
    lay = glow_line(size, [list(zip(xs - ox, ys - oy))], pat['col'], 2.8, 1.0, blur=(4, 10))
    sr = spike_runs(spk, xs, ys, mv, ox, oy)
    if sr:
        lay.alpha_composite(spike_layer(size, sr, pat['col'], 2.8, 1.0, (4, 10)))
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
            for xs_, amp in spk:                      # 丸の中のスパイクの先まで囲む
                if bx0 <= xs_ <= bx1:
                    by0 = min(by0, float(np.interp(xs_, xs, ys)) - amp*mv - 6)
            by1 = max(ys[sel].max() + 9, base_y + 0.35*mv)
            dashed_ellipse(d, (bx0 - ox, by0 - oy, bx1 - ox, by1 - oy), pat['col'])
    return lay, (ox, oy)


def thumbnail_list():
    """サムネイル（透かしなし）。第17弾の一覧型と同じ作り：
    タイトル → 10パターンを2列×5段（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    YEL = (255, 196, 64)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, '心筋梗塞とST変化', 112, 900, WHITE, cx=540, cy=436, max_w=880)
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
        # ST の変化は小さいので、第21弾（30px/mV・4秒）より大きく。10パターン（1列5段）で段が高くなったぶん
        # 52 → 60px/mV、基線の位置 0.66 → 0.62（名前の下 約17px から R の頂点）
        lay, pos = thumb_row_wave(i, x0, x1, y + 24 + (RH - 24)*0.62, 60.0, span=THUMB_SPAN.get(i, 3.0))
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
def _pr_ms(prc):
    """P頂点→R頂点 prc のときの PR間隔（P波の始まり → QRSの始まり、ms）。"""
    tt = np.arange(-0.6, 0.2, 0.0005)
    p = p_sinus(tt + prc); q = qrs_normal(tt)
    p_on = tt[p > 0.05*p.max()].min()
    q_on = tt[(np.abs(q) > 0.05) & (tt < 0.1)].min()
    return (q_on - p_on) * 1000


_TT = np.arange(-0.25, 0.60, 0.0005)


def _j_time(f):
    """J点（QRSの終わり）：R頂点のあと、傾きが 12ms 続けて 3mV/秒 未満になる最初の時刻。"""
    v = f(_TT); dv = np.abs(np.gradient(v, _TT))
    t_r = _TT[np.argmax(np.where(np.abs(_TT) < 0.05, v, -9))]
    n = int(0.012 / 0.0005)
    for k in np.where(_TT > t_r + 0.005)[0]:
        if dv[k:k+n].max() < 3.0:
            return float(_TT[k])
    return float('nan')


def _qrs_ms(f):
    """QRS幅（ms）：始まり（|v| > 0.03mV）〜 J点。"""
    v = f(_TT)
    on = _TT[(np.abs(v) > 0.03) & (_TT > -0.12)].min()
    return (_j_time(f) - on) * 1000


def _at(f, t):
    return float(f(np.array([t]))[0])


def measure():
    """各パターンの ST・T・Q などの値（モデルの波形から計算。画面・依頼文の数値はここから）。"""
    out = {}
    for k, (f, _, _) in KINDS.items():
        if f is None:
            continue
        j = _j_time(f)
        v = f(_TT)
        late = _TT > j + 0.04
        out[k] = dict(j=j, st_j=_at(f, j), st60=_at(f, j + 0.06), st80=_at(f, j + 0.08),
                      qrs=_qrs_ms(f), r=float(v[np.abs(_TT) < 0.05].max()),
                      t_max=float(v[late].max()), t_min=float(v[late].min()))
    for k in 'QI':                                        # 異常Q波：Q の幅・深さ
        f = KINDS[k][0]; v = f(_TT)
        neg = (v < -0.02) & (_TT < 0.005) & (_TT > -0.08)
        out[k]['q_ms'] = (_TT[neg].max() - _TT[neg].min()) * 1000
        out[k]['q_mv'] = float(-v[neg].min())
    out['C']['pr_seg'] = _at(qrs_peri, -0.065)            # PR 部分の高さ（P波の終わりとQRSのあいだ）
    return out


def rate(rr):
    return 60 / rr


def check():
    print('パターンごとの紹介の時間')
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        print(f"{pat['no']} {pat['name']:<14} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s  画面 {a:5.1f}–{b:5.1f}s（{b-a:4.1f}s）")
    print(f'最後のパターンの終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s（全体 {DUR:.1f}s）')
    # 区間のつなぎ目：前のパターンの最後の拍 → 次のパターン（またはうしろの洞調律）の最初の拍
    for i, (s0, s1) in enumerate(SEGS):
        inside = sorted(b for b in STRIP if s0 <= b[0] < s1)
        last = inside[-1]
        rr_in = sorted(set(round(y[0] - x[0], 3) for x, y in zip(inside, inside[1:])))
        nxt = min((b for b in STRIP if b[0] >= s1 - 1e-9), key=lambda b: b[0])
        print(f"  つなぎ目 {PATTERNS[i]['no']}→ : 区間の中のR-R {rr_in} / 最後の拍 {last[1]} {last[0]-s0:.2f}"
              f" → 次 {nxt[1]} 間隔 {nxt[0]-last[0]:.2f}s")
    m = measure()
    print('値（1mm = 0.1mV。ST は TP＝基線からの高さ。J点はモデルから計算）')
    print(f"① 基準：{rate(RR):.0f}/分、PR {_pr_ms(PR):.0f}ms、QRS {m['N']['qrs']:.0f}ms、J点 {m['N']['st_j']:+.2f}mV、T {m['N']['t_max']:.2f}mV")
    print(f"② 超急性期T：T {m['H']['t_max']:.2f}mV（R {m['H']['r']:.2f}mV の {m['H']['t_max']/m['H']['r']*100:.0f}%）、J点 {m['H']['st_j']:+.2f}mV")
    print(f"③ ST上昇：J点 {m['E']['st_j']:+.2f}mV、J+60ms {m['E']['st60']:+.2f}mV、頂点 {m['E']['t_max']:.2f}mV、R {m['E']['r']:.2f}mV")
    print(f"④ 異常Q：Q 幅 {m['Q']['q_ms']:.0f}ms・深さ {m['Q']['q_mv']:.2f}mV（R {m['Q']['r']:.2f}mV、QRS の {m['Q']['q_mv']/(m['Q']['q_mv']+m['Q']['r'])*100:.0f}%）、"
          f"J+60ms {m['Q']['st60']:+.2f}mV、Tの終わり {m['Q']['t_min']:+.2f}mV")
    print(f"⑤ 冠性T：Q 幅 {m['I']['q_ms']:.0f}ms・深さ {m['I']['q_mv']:.2f}mV、陰性T {m['I']['t_min']:+.2f}mV（左右対称）、J点 {m['I']['st_j']:+.2f}mV")
    print(f"⑥ 水平型ST低下：J点 {m['D']['st_j']:+.2f}mV、J+60ms {m['D']['st60']:+.2f}mV、J+80ms {m['D']['st80']:+.2f}mV、T {m['D']['t_max']:.2f}mV")
    print(f"⑦ 心膜炎：{rate(0.56):.0f}/分、PR部分 {m['C']['pr_seg']:+.2f}mV、J点 {m['C']['st_j']:+.2f}mV、"
          f"J+60ms {m['C']['st60']:+.2f}mV、T {m['C']['t_max']:.2f}mV（ST/T {m['C']['st_j']/m['C']['t_max']:.2f}。LITFL：心膜炎 > 0.25）")
    print(f"⑧ 左脚ブロック：QRS {m['L']['qrs']:.0f}ms、J+60ms {m['L']['st60']:+.2f}mV、T {m['L']['t_min']:+.2f}mV")
    print(f"⑨ AIVR：洞調律 {rate(0.86):.0f}/分 → 幅の広いQRS（{m['V']['qrs']:.0f}ms）{rate(AIVR_RR):.0f}/分が4拍 → 洞調律")
    print(f"⑩ 完全房室ブロック：心房 {rate(CHB_PP):.0f}/分、心室 {rate(CHB_RR):.0f}/分（接合部補充調律・幅の狭いQRS {m['J']['qrs']:.0f}ms、"
          f"下壁のST上昇 J点 {m['J']['st_j']:+.2f}mV）。周期 {9*CHB_PP:.1f}秒、区間 {PATTERNS[9]['D']:.2f}秒")
    print('虫眼鏡の値（窓の右上に出す字）')
    for i, pat in enumerate(PATTERNS):
        print(f"  {pat['no']} {mag_title(i)} ／ {mag_readout(i)}")
    print('ひとこと＋色の文字の幅（上限 ONE_W = %dpx。32px で入らないと字が小さくなる）' % ONE_W)
    for pat in PATTERNS:
        tag = TAGS[pat['tag']]
        w1 = text_img(pat['one'], 32, 500, (226, 232, 231))[0].size[0] - 8
        w2 = text_img(tag[0], 32, 800, tag[1])[0].size[0] - 8
        w = w1 + 14 + w2
        print(f"  {pat['no']} {w:4d}px {'OK' if w <= ONE_W else '← 字が小さくなる'}  {pat['one']} {tag[0]}")
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:8]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])


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
    """中部の波形の R が画面の中央を通るときに「ピッ」。心室の拍は低い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, i in STRIP:
        ts = t_of(r)
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 720.0 if k == 'V' else 960.0        # 心室の拍（AIVR）は低い音
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel28_st.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)             # CPU は4つ。ほかの作業と分けあうので 2
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel28_st_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel28_st_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel28.png')
        thumbnail().save(p); print(p)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel28_list.png')
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
