"""第20弾 ノイズ（アーチファクト） まず覚えたい11パターン（第24弾と同じ作り）

配置：
- 上部：①〜⑥ のミニ波形（2列×3段。左の列が患者の動き：①体動 ②筋電図 ③ふるえ、
  右の列が呼吸・電気・電極：④呼吸の揺れ ⑤交流障害 ⑥電極の接触不良）
- 中部：いま紹介中の波形（大きく流れる）と、名前・ひとこと（⑪だけ、うしろに赤で「→ すぐ報告」）
- 下部：⑦〜⑪ のミニ波形（左の列が電極：⑦電極外れ ⑧付けまちがい、右の列が不整脈に見えるノイズ：⑨偽VT ⑩偽VF。
  ⑪本物のVT は3段目に横長で、偽物2つの下に置く）
- 冒頭0〜1秒に問いかけ「このVT、本物？」（そのあいだ偽VTが流れる）→ 答えのタイトル「ノイズ」、
  最後に「何個わかった？コメントで教えてね」

この回だけの見せ方（どちらもモデルの拍の時刻から計算する）：
- 「隠れたQRS」マーカー：⑨⑩ の紹介中、ノイズの下にある洞調律のQRSが帯の右のほう（x = MARK_X）を通るたびに、
  波形の下に緑の▲を付け、となりの▲とのあいだに間隔のものさし（「0.80秒」）を引く。
  ⑪ 本物のVT では、幅の広いQRSのあいだに▲が付かず、赤の点線で「ふつうのQRSなし」
- 「ノイズを消すと…」：①②⑨⑩ の紹介の後半で、ノイズをすっと薄くして下の洞調律を見せ、また戻す

下の心臓のリズムは、ずっと洞調律（75/分）。⑪だけ本物の心室頻拍。
ノイズは、パターンの周期でくり返す決まった形（乱数の種を固定）。区間の端は0.2秒でなめらかに足し引きする。
II誘導を想定。

使い方:
    python3 make_reel20.py --jobs 2     # 書き出し・60fps（CPUは4つなので --jobs 2）
    python3 make_reel20.py --still 20   # 1コマだけ
    python3 make_reel20.py --check      # 検算・タイミング表・字の幅
    python3 make_reel20.py --thumb      # サムネイル（透かしなし）
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

C_MOVE = (110, 200, 255)         # 患者の動き
C_ENV = (190, 160, 255)          # 呼吸・電気
C_ELEC = (255, 212, 90)          # 電極
C_FAKE = (255, 152, 72)          # 不整脈に見えるノイズ
C_TRUE = (255, 92, 112)          # 本物
C_MARK = (120, 240, 160)         # 隠れたQRSの▲（ふつうのQRS＝緑）

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 波形の部品（実際の時間・秒、mV） ---------------------------------------
RR = 0.80                        # 洞調律 75/分
PR = 0.16                        # P頂点 → R頂点


def _g(t, c, s):
    return np.exp(-0.5*((t-c)/s)**2)


def _ga(t, c, sl, sr):
    s = np.where(t < c, sl, sr)
    return np.exp(-0.5*((t-c)/s)**2)


def p_sinus(t):
    return 0.15*_g(t, 0.0, 0.022)


def qrs_normal(t):
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.27*_ga(t, 0.27, 0.060, 0.042))


def qrs_pvc(t):                   # 心室の拍：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍
    'V': (qrs_pvc, None, 0.0),              # 心室頻拍の1拍（幅の広いQRS）
}
ALL = [(-1e9, 1e9)]                         # 全部をその色で


# --- ノイズ（パターンの周期 L でくり返す） ---------------------------------------------
def _rs(seed):
    return np.random.RandomState(seed)


def band_noise(rel, L, f_lo, f_hi, amp, seed, n_max=400):
    """f_lo〜f_hi Hz の帯域ノイズ。周期 L でくり返す（周波数は 1/L の整数倍）。振幅のRMSが amp。"""
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
    """周期の中の a〜b 秒だけ1になる窓（端は edge 秒でなめらかに）。"""
    r = np.mod(rel, L)
    up = np.clip((r - a) / edge, 0, 1); dn = np.clip((b - r) / edge, 0, 1)
    w = np.minimum(up, dn)
    return w*w*(3 - 2*w)


def art_motion(rel, L):          # ① 体動：大きくゆっくりした揺れ＋ときどき鋭い振れ
    w = burst(rel, L, 0.6, 3.2)
    slow = band_noise(rel, L, 0.6, 3.0, 0.42, 11)
    sharp = np.zeros_like(rel)
    for c, h in ((1.05, 0.75), (1.9, -0.6), (2.65, 0.55)):
        sharp += h*_g(np.mod(rel, L), c, 0.035)
    return w*(slow + sharp)


def art_emg(rel, L):             # ② 筋電図：細かく速いギザギザ（20〜60Hz）
    return burst(rel, L, 0.5, 3.4) * band_noise(rel, L, 20, 60, 0.10, 12, n_max=600)


def art_tremor(rel, L):          # ③ ふるえ（振戦）：4〜8Hzの細かい揺れ。P波が見えず、心房細動に見える（LITFL：パーキンソン病の振戦）
    return band_noise(rel, L, 4.5, 8.0, 0.055, 13)


def art_resp(rel, L):            # ④ 呼吸：基線がゆっくり上下（15回/分）
    return 0.38*np.sin(2*np.pi*rel/L)


def art_hum(rel, L):             # ⑤ 交流障害：50Hzの規則正しい細かいギザギザ
    return 0.06*np.sin(2*np.pi*round(50*L)*rel/L)


def art_loose(rel, L):           # ⑥ 接触不良：基線が飛ぶ・一瞬とぎれる
    r = np.mod(rel, L)
    out = np.zeros_like(rel)
    for c, h in ((0.95, 0.65), (2.05, -0.55), (2.75, 0.45)):
        out += h*np.where(r >= c, np.exp(-(r - c)/0.18), 0)     # 段差のあと、ゆっくり戻る
    return out


def gain_loose(rel, L):
    r = np.mod(rel, L)
    g = np.ones_like(rel)
    for a, b in ((1.25, 1.45), (2.35, 2.5)):
        g = np.where((r >= a) & (r < b), 0.0, g)                 # 一瞬とぎれる
    return g


def gain_off(rel, L):            # ⑦ 電極外れ：まっすぐの線（心臓は動いている）
    r = np.mod(rel, L)
    return np.where((r >= 1.05) & (r < 3.75), 0.0, 1.0)


def art_off(rel, L):             # 外れる瞬間・付け直す瞬間の小さな振れ
    r = np.mod(rel, L)
    return 0.5*_g(r, 1.05, 0.012) - 0.35*_g(r, 3.75, 0.012)


def gain_inv(rel, L):            # ⑧ 付けまちがい（RAとLLの入れかわり）：II誘導がまるごと逆さま
    return -np.ones_like(rel)


def brush_raw(rel, L):
    """⑨ 偽VT（歯みがき）の揺れそのもの：4〜5Hzの大きな揺れ（冒頭の問いかけでは、窓をかけずにこれを流す）。"""
    r = rel
    return (0.58*np.sin(2*np.pi*round(4.5*L)*r/L) + 0.14*np.sin(2*np.pi*round(9*L)*r/L + 0.9)
            + 0.08*np.sin(2*np.pi*round(4.75*L)*r/L + 2.1))


def art_brush(rel, L):           # ⑨ 偽VT（歯みがき）：中にふつうのQRSが同じ間隔で見える
    return burst(rel, L, 0.45, 3.55, 0.2) * brush_raw(rel, L)


def art_wire(rel, L):            # ⑩ 偽VF（リード線の断線・こすれ）：3〜7Hzの不規則で大きな揺れ
    env = 0.7 + 0.3*np.sin(2*np.pi*2*rel/L + 0.5)
    return burst(rel, L, 0.45, 3.55, 0.2) * env * band_noise(rel, L, 3, 7, 0.36, 17)


# 11パターン：1周期ぶんの拍（R頂点の時刻, 種類）と周期の長さ L、ノイズ art・倍率 gain（周期の中の関数）、
# 色を付ける範囲 hl（周期の中の時刻）、tag：ひとことのうしろの色の文字（TAGS。なければ None）
# ④シバリングは外した（②筋電図・③ふるえと同じ「筋肉のふるえ」の仲間で、見た目もほぼ同じ。キャプションに一文で残す）
_SINUS = [(k*RR, 'N') for k in range(5)]     # 4.0秒 = 洞調律5拍
PATTERNS = [
    dict(no='①', name='体動', col=C_MOVE, hint='大きく乱れる',
         one='体が動くと、基線が大きく乱れる', tag=None,
         ev=_SINUS, L=4.0, art=art_motion, hl=[(0.6, 3.2)]),
    dict(no='②', name='筋電図', col=C_MOVE, hint='細かいギザギザ',
         one='力が入ると、細かく速いギザギザ', tag=None,
         ev=_SINUS, L=4.0, art=art_emg, hl=[(0.5, 3.4)]),
    dict(no='③', name='ふるえ（振戦）', col=C_MOVE, hint='心房細動に見える',
         one='心房細動に見えても、R-Rは一定', tag=None,
         ev=_SINUS, L=4.0, art=art_tremor, hl=ALL),
    dict(no='④', name='呼吸の揺れ', col=C_ENV, hint='基線が上下',
         one='呼吸に合わせて、基線がゆっくり上下', tag=None,
         ev=_SINUS, L=4.0, art=art_resp, hl=ALL),
    dict(no='⑤', name='交流障害', col=C_ENV, hint='規則正しいギザギザ',
         one='電気機器の影響。細かく規則正しいギザギザ', tag=None,
         ev=_SINUS, L=4.0, art=art_hum, hl=ALL),
    dict(no='⑥', name='電極の接触不良', col=C_ELEC, hint='基線が飛ぶ',
         one='基線が飛ぶ・一瞬とぎれる', tag=None,
         ev=_SINUS, L=4.0, art=art_loose, gain=gain_loose, hl=[(0.85, 3.3)]),
    dict(no='⑦', name='電極外れ', col=C_ELEC, hint='まっすぐの線',
         one='まっすぐの線。まず患者さんを見る', tag=None,
         ev=[(k*RR, 'N') for k in range(6)], L=4.8, art=art_off, gain=gain_off, hl=[(0.95, 3.85)]),
    dict(no='⑧', name='電極の付けまちがい', col=C_ELEC, hint='波形が逆さま',
         one='P波・QRS・T波が、まるごと逆さま', tag=None,
         ev=_SINUS, L=4.0, gain=gain_inv, hl=ALL),
    dict(no='⑨', name='偽VT（歯みがき）', col=C_FAKE, hint='VTに見える',
         one='VTに見えても、ふつうのQRSが同じ間隔で見える', tag=None,
         ev=_SINUS, L=4.0, art=art_brush, hl=[(0.45, 3.55)]),
    dict(no='⑩', name='偽VF（断線）', col=C_FAKE, hint='VFに見える',
         one='VFに見えても、ふつうのQRSが同じ間隔で見える', tag=None,
         ev=_SINUS, L=4.0, art=art_wire, hl=[(0.45, 3.55)]),
    dict(no='⑪', name='本物のVT', col=C_TRUE, hint='ふつうのQRSが消える',
         one='ふつうのQRSが消え、幅広いQRSが続く', tag='report',
         ev=[(0, 'N')] + [(0.62 + k*0.32, 'V') for k in range(8)] + [(3.2, 'N'), (4.0, 'N')], L=4.8,
         hl=[(0.50, 3.0)]),
]


def art_apply(pat, rel, v, quiet=0.0):
    """パターンのノイズと倍率をかける：gain(rel)*v + art(rel)*(1-quiet)（周期 L でくり返す）"""
    L = pat['L']
    if pat.get('gain'):
        v = pat['gain'](rel, L) * v
    if pat.get('art'):
        v = v + pat['art'](rel, L) * (1 - quiet)
    return v


N_PAT = len(PATTERNS)
IDX = {p['no']: i for i, p in enumerate(PATTERNS)}

# 区間の長さ（秒）。仮の値（録音前）：台本の各文の長さの見込み（6字/秒）＋0.75秒以上で、拍の並びがくずれない位置で切る。
# - 洞調律の上のノイズ（①〜⑥⑧〜⑩）は、洞調律の拍の位置（0.80秒の倍数）で切る。次のパターンの最初の拍まで 0.80秒
# - ⑦ 5.6：電極外れの周期 4.8秒＋1拍（まっすぐの線のあと、洞調律に戻ってから切る）
# - ⑪ 4.8：1周期（本物のVT が止まって洞調律に戻り、ふつうのQRSが2拍。うしろの洞調律まで 0.80秒）
# - ①⑨⑩ は長め：①は最初の区間（縮み始めが0.35秒早い）、⑨⑩は「隠れたQRS」の▲と「ノイズを消すと…」を見せる時間
# 縮んで枠へ移るとき見えている3.1秒（区間の終わりの0.35秒手前まで）がそのパターンだけになるよう、3.44秒以上
SEG_D = {'①': 4.8, '②': 4.0, '③': 4.8, '④': 4.0, '⑤': 4.0, '⑥': 4.0,
         '⑦': 5.6, '⑧': 4.8, '⑨': 5.6, '⑩': 5.6, '⑪': 4.8}
for _p in PATTERNS:
    _p['D'] = SEG_D[_p['no']]
    assert _p['D'] >= 3.44 - 1e-9, _p['no']


def beat_wave(tau, kind):
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
            v[m] += beat_wave(tau[m] - r, k)
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


# --- 中部の帯：全パターンをつないだ1本の波形 ---------------------------------
# パターン i は、実際の時刻 [SEGS[i][0], SEGS[i][1]) にそのパターンを置く。
# 紹介の終わり＝区間の終わりが画面の右端に来たとき。このとき画面に見えているのは
# パターン i だけなので、それをそのまま縮めて枠へ運ぶと、ミニ波形とつながる。
# 冒頭：0秒から偽VT（⑨）が流れ、大きな問いかけ「このVT、本物？」。HOOK_T0 で止めて、
# その場で残りの4パターンに素早く変形し、洞調律に戻ってから T_GO で流す。T_TITLE でパターン①が右端から入ってくる。
T_STOP, T_GO = 0.0, 3.0           # 帯の時計は 0秒から T_GO まで止まる（そのあいだは冒頭の変形を見せる）
FREEZE = T_GO - T_STOP
T_TITLE = 4.9                     # 冒頭の1文（仮 4.9秒）が入り、見出しと枠が出そろう長さ
END_HOLD = 5.7                    # 全部そろってからの時間（まとめ・保存の2文と、冒頭へ戻る時間）
HOOK = [8, 9, 6, 0, 2]            # ⑨偽VT（問いかけのあいだ流れる）→ ⑩偽VF → ⑦電極外れ → ①体動 → ③ふるえ
HOOK_T0, HOOK_STEP, HOOK_MORPH = 1.30, 0.38, 0.12
HANDOFF_EARLY = 0.35


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
    # うしろの洞調律の位相が冒頭とそろういちばん短い長さにする
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


STRIP, SEGS, STRIP_END, _DUR_LOOP = _strip()

# 中部の帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM
# ミニ波形の枠（11個：上 2列×3段、下 2列×2段＋横長1つ）
CELL_W, CELL_H = 400, 106
CELL_GAP = 8
COL_X = (130, 550)
WIDE_W = COL_X[1] + CELL_W - COL_X[0]        # ⑪の横長の枠（2列ぶん）
TOP_Y = [364 + k*(CELL_H + CELL_GAP) for k in range(3)]
BOT_Y = [1528 - CELL_H - k*(CELL_H + CELL_GAP) for k in (2, 1, 0)]   # 下端は 1528（下の注記と 17px あける）
# 中部のかたまり：名前（54px）→ ひとこと（32px）→ 波形（上はノイズの山 WAVE_UP mV、下は 1.0mV。
# 下の 1.0mV は⑧の逆さまのR、⑨⑩⑪では「隠れたQRS」の▲とものさしの行）
WAVE_UP, WAVE_DN = 1.62, 1.0
_TOP_END = TOP_Y[-1] + CELL_H                # 上の枠の下端
_BOT_TOP = BOT_Y[0]                          # 下の枠の上端
_MID_H = 22 + 54 + 16 + 8 + WAVE_UP*F_MV + WAVE_DN*F_MV
_GAP = (_BOT_TOP - _TOP_END - _MID_H) / 2
Y_NAME = _TOP_END + _GAP + 22
Y_ONE = Y_NAME + 54
F_BASE = Y_ONE + 16 + 8 + WAVE_UP*F_MV
MARK_Y = F_BASE + 126                        # ▲とものさしの行（⑨⑩の谷 約0.8mV＝112px の下）
F_Y0, F_Y1 = int(F_BASE - WAVE_UP*F_MV - 30), int(_BOT_TOP - 2)
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


# --- この回だけの見せ方 ① 「隠れたQRS」マーカー --------------------------------------
# 帯の右のほう（x = MARK_X）を洞調律の R が通った瞬間に、その下へ緑の▲を付ける（ピッという音も同じ瞬間）。
# となりの▲が付いたら、2つのあいだに間隔のものさし（R-R、モデルの拍の時刻の差）を引く。
MARK_X = 900
DT_REF = (MARK_X - XC) / F_PXS              # 画面の中央から▲を付ける位置までの、実際の時間（秒）
MARK_PATS = ('⑨', '⑩')                      # ▲を付けるパターン
NO_QRS_PAT = '⑪'                            # ▲が付かない対比（本物のVT）
NO_QRS_TXT = 'ふつうのQRSなし'


def mark_beats(i):
    """パターン i の区間の中の、洞調律の拍（R時刻）。"""
    return [r for r, k, j in STRIP if j == i and k == 'N']


# --- この回だけの見せ方 ② 「ノイズを消すと…」 ----------------------------------------
# 紹介の終わり（縮み始め）の REV_LEAD 秒前から、ノイズを REV_FADE 秒で消し、REV_HOLD 秒そのまま、REV_FADE 秒で戻す
REVEAL_PATS = ('①', '②', '⑨', '⑩')
REV_LEAD, REV_FADE, REV_HOLD = 2.2, 0.35, 0.9
REVEAL_TXT = 'ノイズを消すと…'


def reveal_times(i):
    b = WINDOWS[i][1]
    t0 = b - REV_LEAD
    return t0, t0 + REV_FADE, t0 + REV_FADE + REV_HOLD, t0 + 2*REV_FADE + REV_HOLD


def quiet_at(t, i):
    """パターン i のノイズを消している割合（0〜1）。"""
    if i is None or PATTERNS[i]['no'] not in REVEAL_PATS:
        return 0.0
    t0, t1, t2, t3 = reveal_times(i)
    return ramp(t, t0, REV_FADE) * (1 - ramp(t, t2, REV_FADE))


def reveal_label_a(t, i):
    if i is None or PATTERNS[i]['no'] not in REVEAL_PATS:
        return 0.0
    t0, t1, t2, t3 = reveal_times(i)
    return ramp(t, t0 + 0.15, 0.25) * (1 - ramp(t, t2 - 0.05, 0.25))


def cell_rect(i):
    if i < 6:                          # 上：左の列 ①②③、右の列 ④⑤⑥
        col, row = i // 3, i % 3
        x, y = COL_X[col], TOP_Y[row]
        return (x, y, x + CELL_W, y + CELL_H)
    if i < 10:                         # 下：左の列 ⑦⑧、右の列 ⑨⑩
        j = i - 6
        col, row = j // 2, j % 2
        x, y = COL_X[col], BOT_Y[row]
        return (x, y, x + CELL_W, y + CELL_H)
    return (COL_X[0], BOT_Y[2], COL_X[0] + WIDE_W, BOT_Y[2] + CELL_H)   # ⑪：3段目に横長


CELL_FILL = 225                    # 枠の中の塗りの濃さ（0〜255）。方眼をうっすら残す
M_PXS = 66.0                      # ミニ波形：実際の1秒 = 66px（約5.8秒ぶんが見える。横長の枠は約12秒）
M_MV = 33.0


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


def fit_size(s, size, weight, max_w):
    """max_w に入るまで縮めたときの字の大きさ（--check 用）。"""
    sz = size
    while sz > 16:
        x0, _, x1, _ = font(sz, weight).getbbox(s)
        if x1 - x0 <= max_w:
            break
        sz -= 1
    return sz


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


def text_box(s, size, weight, cy, max_w=None):
    """put(cy=…) で描いたときの字の上端・下端（y）。--check 用。"""
    im, asc = text_img(s, size, weight, WHITE, max_w)
    py = int(cy - 4 - asc*0.62)
    bb = im.getchannel('A').getbbox()
    return py + bb[1], py + bb[3]


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


ART_EDGE = 0.2                    # 区間の端で、ノイズ・倍率をなめらかに切りかえる長さ（秒）


def strip_art(tau, v, quiet=None):
    """中部の帯：区間ごとに、そのパターンのノイズと倍率をかける（区間の端 ART_EDGE 秒でなめらかに）。
    quiet = (パターン番号, 割合)：そのパターンのノイズだけ薄くする（「ノイズを消すと…」）。"""
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
        q = quiet[1] if quiet is not None and quiet[0] == i else 0.0
        g = pat['gain'](rel, L) if pat.get('gain') else 1.0
        n = pat['art'](rel, L) * (1 - q) if pat.get('art') else 0.0
        out[m] = v[m] * (1 + e*(g - 1)) + e*n
    return out


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


def strip_arrays(tau_center, quiet=None):
    """中部の帯：(波形, 色の番号)"""
    tau = tau_center + (FX - XC) / F_PXS
    return strip_art(tau, wave_from(STRIP, tau), quiet), strip_colors(tau)


def hook_arrays(i, shift=0.0, raw=False):
    """フック用：パターン i の、色の付いた範囲が中央の少し左に来る一場面。
    shift：その場面から何秒ずらすか（冒頭で流すとき）。raw：⑨の揺れを窓なしで（画面いっぱいVTに見える）。"""
    pat = PATTERNS[i]
    if pat['hl'] is ALL:
        c = pat['L'] / 2
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2 + 0.25
    rel = c + shift + (FX - XC) / F_PXS + pat['L']
    bl = periodic_beats(pat, rel[0] - 1, rel[-1] + 1)
    if raw:
        v = wave_from(bl, rel) + brush_raw(rel, pat['L'])
        cid = np.full(len(rel), i)
    else:
        v = art_apply(pat, rel, wave_from(bl, rel))
        cid = np.where(hl_mask(pat, rel) | (pat['hl'] is ALL), i, -1)
    return v, cid


def hook_first(t):
    """冒頭0秒〜HOOK_T0：問いかけのあいだ流れる偽VT（HOOK_T0 で止まる）。"""
    return hook_arrays(HOOK[0], shift=min(t, HOOK_T0) - HOOK_T0, raw=True)


_HOOK = {}


def hook_targets():
    if not _HOOK:
        _HOOK['seq'] = [hook_first(HOOK_T0)] + [hook_arrays(i) for i in HOOK[1:]] \
            + [strip_arrays(tau_c(T_STOP))]
    return _HOOK['seq']


def hook_state(t):
    """冒頭の (変形の前, 後, 進み具合, 表示中のパターン)。HOOK_T0 までは偽VTが流れる。"""
    seq = hook_targets()
    times = [HOOK_T0 + k*HOOK_STEP for k in range(len(HOOK))]     # seq[k] → seq[k+1] に変形する時刻
    if t < times[0]:
        f = hook_first(t)
        return f, f, 1.0, HOOK[0]
    k = max(n for n, tk in enumerate(times) if t >= tk)
    u = ease((t - times[k]) / HOOK_MORPH)
    shown = HOOK[k + 1] if k + 1 < len(HOOK) else None
    return seq[k], seq[k + 1], u, shown


def draw_wave(v, cid, base_col, a):
    h = F_Y1 - F_Y0
    ys = F_BASE - F_Y0 - v*F_MV
    out = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    for ci in sorted(np.unique(cid).tolist()):
        sel = cid == ci
        sel = sel | np.roll(sel, 1) | np.roll(sel, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(FX[r], ys[r])) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)] if len(idx) else []
        col = base_col if ci < 0 else PATTERNS[ci]['col']
        if runs:
            out.alpha_composite(glow_line((W, h), runs, col, 4.5, a))
    return out


def featured(t, cur=None, a_loop=0.0):
    """中部の帯の (波形, 色の番号)。色を付けるのは、いま紹介中のパターン cur の拍だけ（前のパターンの残りはふつうの緑）。
    最後に冒頭へ戻るとき（a_loop）は、冒頭の偽VTへ変形する。"""
    if T_STOP <= t < T_GO:
        (v0, c0), (v1, c1), u, _ = hook_state(t)
        return v0 + (v1 - v0)*u, (c1 if u >= 0.5 else c0)
    v, cid = strip_arrays(tau_c(t), (cur, quiet_at(t, cur)) if cur is not None else None)
    cid = np.where(cid == cur, cid, -1) if cur is not None else np.full_like(cid, -1)
    if a_loop > 0:
        v0, c0 = hook_first(0.0)
        u = ease(a_loop)
        v = v + (v0 - v)*u
        cid = c0 if u >= 0.5 else cid
    return v, cid


def cell_strip_w(i):
    x0, _, x1, _ = cell_rect(i)
    return x1 - x0 - 20


STRIP_BASE = 49                    # ミニ波形の基線（枠の中の帯の上端から）


def cell_strip_origin(i):
    x0, y0, _, _ = cell_rect(i)
    return x0 + 10, y0 + 28


def pattern_view(i, t, cx, base_y, pxs, mv, x_lo, x_hi, lw, blur, a=1.0, lw_e=None, a_norm=1.0):
    """パターン i をくり返した波形を、画面の x_lo〜x_hi に描いた RGBA（全画面サイズの一部）。
    中央 cx に来る時刻は tau_c(t)（中部の帯と同じ）。区間の始まりからの相対時刻で周期にする。"""
    pat = PATTERNS[i]
    s0 = SEGS[i][0]
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
    sw = cell_strip_w(i)
    cx = lerp(XC, ox + sw/2, u)
    base_y = lerp(F_BASE, oy + STRIP_BASE, u)
    pxs = F_PXS*(M_PXS/F_PXS)**u
    mv = F_MV*(M_MV/F_MV)**u
    half = lerp(XC, sw/2, u)
    lw = lerp(4.5, 2.2, u)
    b1 = lerp(8, 3, u); b2 = lerp(20, 7, u)
    return cx, base_y, pxs, mv, cx - half, cx + half, lw, (b1, b2)


MINI_LW_ECT = 3.8                  # ミニ波形で、色を付けた範囲の線の太さ（ほかは 2.2）
MINI_A_NORM = 0.72                 # ミニ波形で、色を付けていない範囲の濃さ


def mini(base, i, t, u=1.0, a=1.0):
    cx, by, pxs, mv, xl, xh, lw, bl = view_params(i, u)
    im, pos = pattern_view(i, t, cx, by, pxs, mv, xl, xh, lw, bl, a=a,
                           lw_e=lerp(4.5, MINI_LW_ECT, u), a_norm=lerp(1.0, MINI_A_NORM, u))
    base.alpha_composite(im, pos)


def draw_cell(base, i, t, state, a_all):
    """state: 'empty'（まだ。番号とヒント）/'now'（紹介中）/'landing'（枠へ移るところ）/'done'（ミニ波形あり）"""
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
        put(base, f"{pat['no']} {pat['name']}", 22, 700, pat['col'], x=x0 + 14, cy=y0 + 16,
            a=a_all, max_w=CELL_W - 30)
    elif state == 'now':
        put(base, pat['no'], 30, 700, pat['col'], x=x0 + 16, cy=y0 + CELL_H/2, a=min(1.0, a_all*2))
    else:
        put(base, pat['no'], 30, 700, DIM, x=x0 + 16, cy=y0 + CELL_H/2, a=a_all)
        put(base, f"ヒント：{pat['hint']}", 24, 500, (120, 134, 132), x=x0 + 64, cy=y0 + CELL_H/2,
            a=a_all, max_w=x1 - x0 - 80)


# --- 画面 ---------------------------------------------------------------------------
YEL = (255, 214, 64)
HEADER = [('ノイズ、まず覚えたい', 1.0, WHITE), (str(len(PATTERNS)), 2.0, YEL), ('パターン', 1.0, WHITE)]
HEADER_BASE = 342                   # 見出しのベースライン（y）
TITLE_SUB = '心電図で気づく'
TITLE = 'ノイズ'
TITLE_2 = 'アーチファクト'
END_1 = f'アラームが鳴ったら、この{len(PATTERNS)}パターン'
END_2 = '保存して見返してね'
END_3 = '何個わかった？コメントで教えてね'
ASK = 'このVT、本物？'                  # 冒頭0〜1秒の問いかけ（そのあいだ偽VTが流れる）
ASK_END = 1.05                       # 問いかけを消しはじめる時刻（答えのタイトル「ノイズ」と入れかわる）
NOTE1 = '実際の速さ（II誘導・ふつうの拍は75/分）'
NOTE2 = '※数値はこの波形での一例'
WATERMARK = '@nurse_polarbearden'
# 冒頭のタイトル（小さい字・大きい字・その下）と問いかけの y。ノート2行の y（字の下が 1600 より上）
TITLE_Y = (452, 572, 700)
ASK_Y = 572
NOTE_Y = (1557, 1584)


def current(t):
    for i, (a, b) in enumerate(WINDOWS):
        if a <= t < b:
            return i
    return None


def draw_header(base, a):
    """「ノイズ、まず覚えたい」＋大きな黄色の「11」＋「パターン」。左右の余白（130px）に収める。"""
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


# ひとことのうしろの色の文字。この回は⑪本物のVTだけ、赤で「→ すぐ報告」（第18弾の専門医レビューにならう。ナレーションでは言わない）
ONE_W = 760                         # ひとこと＋色の文字の幅の上限（左右に 160px 以上の余白。端で切れて見えないように）
TAGS = {
    'report': ('→ すぐ報告', (255, 96, 96)),
}


def one_layout(pat):
    """ひとこと＋色の文字の字の大きさと幅。ONE_W に入るまで縮める（--check でも使う）。"""
    tag = TAGS.get(pat['tag'])
    sz = 32
    while True:
        w1 = text_img(pat['one'], sz, 500, (226, 232, 231))[0].size[0] - 8
        w2 = (text_img(tag[0], sz, 800, tag[1])[0].size[0] - 8 + 14) if tag else 0
        if w1 + w2 <= ONE_W or sz <= 24:
            break
        sz -= 1
    return sz, w1, w2


def draw_one(im, pat, a):
    """中部のひとこと。色の文字（TAGS）があれば続けて、まとめて中央ぞろえ。"""
    tag = TAGS.get(pat['tag'])
    sz, w1, w2 = one_layout(pat)
    x0 = 540 - (w1 + w2) / 2
    put(im, pat['one'], sz, 500, (226, 232, 231), x=x0, cy=Y_ONE, a=a)
    if tag:
        put(im, tag[0], sz, 800, tag[1], x=x0 + w1 + 14, cy=Y_ONE, a=a)


def x_of(tau, t):
    """実際の時刻 tau の、中部の帯での x。"""
    return XC + (tau - tau_c(t)) * F_PXS


def wave_y(v, x):
    """中部の帯の波形の、x での y（画面の座標）。"""
    return F_BASE - float(np.interp(x, FX, v)) * F_MV


def draw_markers(im, t, cur, v, a):
    """⑨⑩：隠れたQRSの▲と、間隔のものさし。⑪：幅の広いQRSのあいだに「ふつうのQRSなし」。"""
    if cur is None or a <= 0.004:
        return
    pat = PATTERNS[cur]
    ref = tau_c(t) + DT_REF                      # この時刻より前の R は、もう▲が付いている
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    labels = []
    if pat['no'] in MARK_PATS:
        rs = [r for r in mark_beats(cur) if r <= ref]
        prev = None
        for r in rs:
            x = x_of(r, t)
            pop = ease((ref - r) / 0.15)                 # 付いた瞬間に、少し上から落ちてくる
            if -20 <= x <= W + 20:
                ty = MARK_Y - 8 - 10*(1 - pop)
                aa = int(255*a*pop)
                d.polygon([(x, ty), (x - 9, ty + 15), (x + 9, ty + 15)], fill=C_MARK + (aa,))
                # ▲の上から、波形の下（その R の前後で、いちばん低いところ）まで、細い点線
                xs_ = np.arange(x - 10, x + 10.5, 0.5)
                y_bot = max(wave_y(v, xx) for xx in xs_) + 10
                yy = ty - 6
                while yy > y_bot:
                    d.line([(x, yy), (x, max(y_bot, yy - 5))], fill=C_MARK + (int(aa*0.55),), width=2)
                    yy -= 10
            if prev is not None:
                x0, x1 = x_of(prev, t) + 14, x - 14
                grow = ease((ref - r) / 0.25)
                xe = x0 + (x1 - x0)*grow
                if xe > -20 and x0 < W + 20:
                    rr = r - prev
                    txt = f'{rr:.2f}秒'
                    tw = text_img(txt, 24, 700, WHITE)[0].size[0] - 8
                    xm = (x0 + x1) / 2
                    ca = int(200*a)
                    # 線はラベルのところをあける
                    for xa, xb in ((x0, min(xe, xm - tw/2 - 10)), (max(x0, xm + tw/2 + 10), xe)):
                        if xb > xa:
                            d.line([(xa, MARK_Y), (xb, MARK_Y)], fill=GREY + (ca,), width=2)
                    d.line([(x0, MARK_Y - 7), (x0, MARK_Y + 7)], fill=GREY + (ca,), width=2)
                    if grow >= 0.999:
                        d.line([(x1, MARK_Y - 7), (x1, MARK_Y + 7)], fill=GREY + (ca,), width=2)
                    labels.append((txt, xm, a*ramp(ref - r, 0.15, 0.2)))
            prev = r
    elif pat['no'] == NO_QRS_PAT:
        s0 = SEGS[cur][0]
        rs = [r for r in mark_beats(cur) if r <= ref]
        for r in rs:                                     # VTの前後の洞調律の拍には▲
            x = x_of(r, t)
            pop = ease((ref - r) / 0.15)
            if -20 <= x <= W + 20:
                ty = MARK_Y - 8 - 10*(1 - pop)
                d.polygon([(x, ty), (x - 9, ty + 15), (x + 9, ty + 15)], fill=C_MARK + (int(255*a*pop),))
        a0, b0 = pat['hl'][0]
        xa, xb = x_of(s0 + a0, t), x_of(s0 + b0, t)
        xe = min(xb, MARK_X)
        if xe > xa:                                      # 幅の広いQRSが通ったところまで、赤の点線をのばす
            xx = xa
            while xx < xe:
                d.line([(xx, MARK_Y), (min(xe, xx + 10), MARK_Y)], fill=C_TRUE + (int(230*a),), width=3)
                xx += 18
            xm = x_of(s0 + (a0 + b0)/2, t)
            if xm <= MARK_X - 60:
                labels.append((NO_QRS_TXT, xm, a*ramp(MARK_X - 60 - xm, 0, 60)))
    im.alpha_composite(lay)
    for txt, xm, la in labels:
        col = C_TRUE if txt == NO_QRS_TXT else WHITE
        tw = text_img(txt, 24, 700, col)[0].size[0] - 8
        if txt == NO_QRS_TXT:                            # 赤の点線の上に、黒い下地をしいて読みやすく
            bg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(bg).rounded_rectangle((xm - tw/2 - 10, MARK_Y - 17, xm + tw/2 + 10, MARK_Y + 17),
                                                 radius=8, fill=BG + (int(235*la),))
            im.alpha_composite(bg)
        put(im, txt, 24, 700, col, cx=xm, cy=MARK_Y + 1, a=la)


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
    al = 0.0
    if cur is not None:
        a_i, b_i = WINDOWS[cur]
        pat = PATTERNS[cur]
        # 前のパターンが上の枠（①〜⑥）へ移るときは、縮んで上へ動くミニ波形と重ならないよう、出始めを遅らせる
        t0 = a_i + (0.45 if 0 < cur <= 6 else 0.1)
        al = ramp(t, t0, 0.3) * (1 - ramp(t, b_i - 0.25, 0.25))
        put(im, f"{pat['no']} {pat['name']}", 54, 900, pat['col'], cx=540, cy=Y_NAME, a=al, max_w=820)
        draw_one(im, pat, al)

    # 冒頭0〜1秒：大きな問いかけ（そのあいだ偽VTが流れる）→ 答えのタイトル「ノイズ」に入れかわる
    a_ask = max(1 - ramp(t, ASK_END, 0.3), a_loop)
    put(im, ASK, 100, 900, YEL, cx=540, cy=ASK_Y, a=a_ask, max_w=820)

    # 冒頭：タイトルと、変形中のパターン名
    a_t = ramp(t, ASK_END + 0.1, 0.3) * (1 - ramp(t, T_GO - 0.5, 0.5))
    if a_t > 0:
        put(im, TITLE_SUB, 36, 500, PURPLE, cx=540, cy=TITLE_Y[0], a=a_t)
        put(im, TITLE, 150, 900, WHITE, cx=540, cy=TITLE_Y[1], a=a_t, max_w=880)
        put(im, TITLE_2, 52, 800, WHITE, cx=540, cy=TITLE_Y[2], a=a_t, max_w=880)
    if T_STOP <= t < T_GO:
        _, _, u, shown = hook_state(t)
        if shown is not None:
            pat = PATTERNS[shown]
            a_nm = a_t if shown == HOOK[0] else a_t*ramp(u, 0.3, 0.4)
            put(im, f"{pat['no']} {pat['name']}", 44, 900, pat['col'], cx=540, cy=Y_ONE - 10,
                a=a_nm, max_w=820)

    a_end = ramp(t, T_END + FLY, 0.6)*keep
    if a_end > 0:
        put(im, END_1, 42, 800, WHITE, cx=540, cy=Y_NAME, a=a_end, max_w=820)
        put(im, END_2, 36, 700, GREEN, cx=540, cy=Y_ONE,
            a=ramp(t, T_END + FLY + 1.5, 0.6)*keep)
        put(im, END_3, 40, 800, YEL, cx=540, cy=F_BASE + 100,   # 波形の下（S波の底 約0.2mV）と下の枠のあいだ
            a=ramp(t, T_END + FLY + 2.0, 0.6)*keep, max_w=820)

    # 中部の波形：紹介が終わった瞬間に、見えている波形がそのまま縮んで枠へ移る。
    # 中部の帯はそのあいだ消して、次のパターンの途中から戻す。
    a_strip = 1.0
    for i in range(N_PAT):
        b_i = WINDOWS[i][1]
        if b_i <= t < b_i + FLY + 0.35:
            a_strip = min(a_strip, ramp(t, b_i + FLY - 0.1, 0.45))
    base_col = mix(PURPLE, WAVE_GREEN, ramp(t, T_GO - 0.4, 0.8)*keep)
    v = None
    if a_strip > 0.01:
        v, cid = featured(t, cur, a_loop)
        im.alpha_composite(draw_wave(v, cid, base_col, a_strip), (0, F_Y0))
    if v is not None:
        draw_markers(im, t, cur, v, al*a_strip)
        a_rv = reveal_label_a(t, cur)
        if a_rv > 0:
            put(im, REVEAL_TXT, 30, 700, C_MARK, cx=540, cy=F_BASE - 1.32*F_MV, a=a_rv*al)
    if flying is not None:
        uu = ease((t - WINDOWS[flying][1]) / FLY)
        mini(im, flying, t, uu)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=NOTE_Y[0], a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_Y[1], a=0.85*ramp(t, T_GO, 0.5)*keep)
    put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


# --- 一覧型のサムネイル（第24弾と同じ作り） ---------------------------------------
# パターンごとに (見せ始めの時刻, 点線の丸で囲む範囲[周期の中の時刻])。丸のないものは全体が特徴
THUMB_VIEW = {i: (0.0, []) for i in range(len(PATTERNS))}
THUMB_VIEW[IDX['⑨']] = (0.0, [(1.6 - 0.10, 1.6 + 0.10)])     # 偽VT：中に見えるふつうのQRS
THUMB_VIEW[IDX['⑩']] = (0.0, [(1.6 - 0.10, 1.6 + 0.10)])     # 偽VF：中に見えるふつうのQRS
THUMB_MAX_MARKS = {}
THUMB_DESC = ['大きく乱れる', '細かいギザギザ', 'AFに見える', '基線が上下', '規則正しい',
              '基線が飛ぶ', 'まっすぐ', '逆さま', 'QRSが見える', 'QRSが見える', 'ふつうのQRSが消える']


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
    size = (int(x1 - x0) + 2*pad, int(3.4*mv) + 2*pad)
    ox, oy = int(x0) - pad, int(base_y - 1.8*mv) - pad
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
    """サムネイル（透かしなし）。第24弾の一覧型と同じ作り：
    タイトル → ①〜⑩を2列×5段（左の列 ①〜⑤ 体・呼吸・電気、右の列 ⑥〜⑩ 電極・不整脈に見えるノイズ）
    ＋⑪本物のVT を6段目に横長（色つきの名前・ひとこと・波形・点線の丸）→ 下の枠。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    d = ImageDraw.Draw(im, 'RGBA')
    RED = (255, 92, 84)
    d.line([(510, 300), (570, 300)], fill=RED + (255,), width=4)
    put(im, '心電図で気づく', 34, 700, (118, 226, 150), cx=540, cy=342)
    put(im, 'ノイズ', 126, 900, WHITE, cx=540, cy=436, max_w=880)
    put(im, f'{N_PAT}個、全部わかる？', 60, 900, (255, 196, 64), cx=540, cy=546)
    COLS = [(135, 515), (565, 945)]             # 列のあいだは50px あける（線は引かない）
    NR = 6                                      # 段の数（6段目は⑪の横長）
    Y0, RH = 628, 852 // NR
    for i, pat in enumerate(PATTERNS):
        if i < 10:
            c, r = divmod(i, 5)
            x0, x1 = COLS[c]
            span = 4.0
        else:
            r = 5
            x0, x1 = COLS[0][0], COLS[1][1]
            span = 4.0 * (x1 - x0) / (COLS[0][1] - COLS[0][0])
        y = Y0 + r*RH
        name = f"{pat['no']} {pat['name']}"
        im_n, _ = text_img(name, 26, 800, pat['col'], max_w=x1 - x0)
        put(im, name, 26, 800, pat['col'], x=x0, cy=y + 24, max_w=x1 - x0)
        nx = x0 + im_n.size[0] + 8
        if THUMB_DESC[i]:
            im_h, _ = text_img(THUMB_DESC[i], 18, 500, (176, 186, 186))
            assert nx + im_h.size[0] - 8 <= x1 + 4, f'{pat["no"]} のひとことが入らない'
            put(im, THUMB_DESC[i], 18, 500, (176, 186, 186), x=nx, cy=y + 26)
        lay, pos = thumb_row_wave(i, x0, x1, y + 24 + (RH - 24)*0.62, 40.0, span=span)
        im.alpha_composite(lay, pos)
        if r < NR - 1:
            d.line([(x0, y + RH - 1), (x1, y + RH - 1)] if i < 10 else [], fill=(38, 54, 48, 255), width=1)
    by = Y0 + NR*RH + 24
    d.rounded_rectangle([(230, by), (850, by + 96)], radius=18, fill=(16, 22, 21, 255),
                        outline=(70, 84, 80, 255), width=2)
    parts = [('まず覚えたい', 40, WHITE), (str(N_PAT), 72, (255, 196, 64)), ('パターン', 40, WHITE)]
    ims = [text_img(t, sz, 900, col) for t, sz, col in parts]
    tw = sum(a.size[0] - 8 for a, _ in ims) + 8
    x = 540 - tw/2
    base_line = by + 70                          # 文字の下端（ベースライン）をそろえる
    for (t, sz, col), (a, asc) in zip(parts, ims):
        put(im, t, sz, 900, col, x=x, cy=base_line - 0.38*asc)
        x += a.size[0] - 8
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def qrs_ms(f):
    """QRS幅（|v| > 0.05mV の範囲、R頂点の前後 0.12秒以内、ms）。"""
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < 0.12)
    return (tt[m].max() - tt[m].min()) * 1000


# 台本（align_vo.TEXT と同じ）。区間の長さの見込みに使う
def _script():
    try:
        import align_vo
        return align_vo.TEXT
    except Exception:
        return {}


def check():
    print(f'映像 {DUR:.1f}秒（目安 60〜65秒）')
    print('パターンごとの紹介の時間（声の見込み＝台本の字数÷6字/秒。区間の長さ − 0.75秒 以内か）')
    txt = _script()
    for i, pat in enumerate(PATTERNS):
        a, b = WINDOWS[i]
        s = txt.get(pat['no'], '')
        est = len(s) / 6.0
        ok = '' if est + 0.75 <= pat['D'] + 1e-9 else '  ★区間が短い'
        print(f"{pat['no']} {pat['name']:<10} 周期{pat['L']:.2f}s 区間{pat['D']:.2f}s  画面 {a:5.1f}–{b:5.1f}s（{b-a:4.1f}s）"
              f"  声の見込み {est:.1f}s（{len(s)}字）{ok}")
    print(f"区間の合計 {sum(SEG_D.values()):.1f}s。最後のパターンの終わり {T_END:.1f}s → 一覧 {T_END+FLY:.1f}〜{DUR:.1f}s")
    # 区間のつなぎ目：前のパターンの最後の拍 → 次のパターン（またはうしろの洞調律）の最初の拍
    for i, (s0, s1) in enumerate(SEGS):
        inside = [b for b in STRIP if s0 <= b[0] < s1]
        last = max(inside, key=lambda b: b[0])
        nxt = min((b for b in STRIP if b[0] >= s1 - 1e-9), key=lambda b: b[0])
        own = sorted(b[0] for b in inside)
        rr = np.diff(own)
        print(f"  つなぎ目 {PATTERNS[i]['no']}→ : 最後の拍 {last[1]} {last[0]-s0:.2f} → {nxt[1]} 間隔 {nxt[0]-last[0]:.2f}s"
              f"（区間の中の RR {rr.min():.2f}〜{rr.max():.2f}s）")
    print('--- 各パターンの数値（モデルから） ---')
    print('下の心臓のリズム：洞調律 75/分（⑪だけ本物の心室頻拍）')
    print('③ ふるえ：4.5〜8Hz の細かい不規則な揺れ（約0.06mV）。P波が見えにくいが、R-R 0.80秒で一定')
    print('④ 呼吸の揺れ：周期 4.0秒（15回/分）、±0.38mV')
    print('⑤ 交流障害：50Hz、±0.06mV')
    print('⑦ 電極外れ：まっすぐの線 2.7秒（そのあいだも心臓は動いている）')
    print('⑧ 付けまちがい：II誘導のP波・QRS・T波がまるごと逆さま（RAとLLの入れかわり、LITFL）')
    print('⑨ 偽VT：揺れ 約4.5Hz（約270/分）、約±0.6mV（QRSは1.0mV）。中のふつうのQRSは0.80秒ごと')
    print('⑩ 偽VF：3〜7Hzの不規則な揺れ。中のふつうのQRSは0.80秒ごと')
    print(f'⑪ 本物のVT：{60/0.32:.0f}/分、8拍、QRS幅 {qrs_ms(qrs_pvc):.0f}ms（ふつうのQRS {qrs_ms(qrs_normal):.0f}ms）')
    print('--- 波形の高さ（中部の帯。レイアウトの上限 上 %.2fmV・下 %.2fmV） ---' % (WAVE_UP, WAVE_DN))
    for i, pat in enumerate(PATTERNS):
        s0, s1 = SEGS[i]
        tau = np.arange(s0, s1, 0.001)
        v = strip_art(tau, wave_from(STRIP, tau))
        flag = '  ★はみ出す' if v.max() > WAVE_UP + 1e-6 or v.min() < -WAVE_DN - 1e-6 else ''
        print(f"  {pat['no']} 上 {v.max():.2f} 下 {v.min():.2f}{flag}")
    print('--- 隠れたQRSの▲（この回だけ） ---')
    for no in MARK_PATS:
        i = IDX[no]
        rs = mark_beats(i)
        ts = [t_of(r - DT_REF) for r in rs]
        vis = [f'{x:.1f}' for x in ts if WINDOWS[i][0] <= x < WINDOWS[i][1]]
        print(f"  {no} 洞調律の拍 {len(rs)}個、間隔 {', '.join(f'{d:.2f}' for d in np.diff(rs))}秒。▲が付く時刻 {' '.join(vis)}s"
              f"（紹介 {WINDOWS[i][0]:.1f}–{WINDOWS[i][1]:.1f}s）")
        tau = np.arange(SEGS[i][0], SEGS[i][1], 0.001)
        v = strip_art(tau, wave_from(STRIP, tau))
        print(f"     波形の谷 {v.min():.2f}mV → y {F_BASE - v.min()*F_MV:.0f}、▲の上端 y {MARK_Y - 8:.0f}")
    i = IDX[NO_QRS_PAT]
    rs = mark_beats(i)
    print(f"  {NO_QRS_PAT} 洞調律の拍（▲）は区間の {', '.join(f'{r - SEGS[i][0]:.2f}' for r in rs)}秒だけ。"
          f"幅の広いQRSのあいだ（{PATTERNS[i]['hl'][0][0]:.2f}〜{PATTERNS[i]['hl'][0][1]:.2f}秒）は▲なし・赤の点線「{NO_QRS_TXT}」")
    print('--- ノイズを消すと…（この回だけ） ---')
    for no in REVEAL_PATS:
        i = IDX[no]
        t0, t1, t2, t3 = reveal_times(i)
        print(f"  {no} 消しはじめ {t0:.2f}s → 消えている {t1:.2f}〜{t2:.2f}s → 戻る {t3:.2f}s（縮み始め {WINDOWS[i][1]:.2f}s）")
    tr = [b[0] for b in STRIP if b[0] >= STRIP_END - 1e-9][:8]
    print('うしろの洞調律の間隔', [round(y - x, 3) for x, y in zip(tr, tr[1:])])
    print('--- 配置（y） ---')
    print(f"  見出し {HEADER_BASE}、上の枠 {TOP_Y[0]}〜{_TOP_END}、名前 {Y_NAME:.0f}、ひとこと {Y_ONE:.0f}、基線 {F_BASE:.0f}、"
          f"▲の行 {MARK_Y:.0f}、下の枠 {_BOT_TOP}〜{BOT_Y[-1] + CELL_H}、余白 {_GAP:.1f}px（上下）")
    nb = text_box(NOTE2, 24, 400, NOTE_Y[1])[1]
    wb = text_box(WATERMARK, 28, 500, 1576)[1]
    nt = text_box(NOTE1, 24, 400, NOTE_Y[0])[0]
    print(f"  注記 {nt}〜{nb}・透かしの下端 {wb}（1600 以下か：{'OK' if max(nb, wb) <= 1600 else '★'}）")
    one_bot = text_box(PATTERNS[0]['one'], 32, 500, Y_ONE)[1]
    print(f"  ひとことの下端 {one_bot} ／ 波形の上の上限 {F_BASE - WAVE_UP*F_MV:.0f}")
    print('--- 字の幅 ---')
    for pat in PATTERNS:
        sz, w1, w2 = one_layout(pat)
        nm = fit_size(f"{pat['no']} {pat['name']}", 54, 900, 820)
        cell = fit_size(f"{pat['no']} {pat['name']}", 22, 700, CELL_W - 30)
        hint = fit_size(f"ヒント：{pat['hint']}", 24, 500, cell_rect(IDX[pat['no']])[2] - cell_rect(IDX[pat['no']])[0] - 80)
        warn = []
        if sz < 32: warn.append(f'ひとこと {sz}px に縮む')
        if nm < 54: warn.append(f'名前 {nm}px')
        if cell < 22: warn.append(f'枠の名前 {cell}px')
        if hint < 24: warn.append(f'ヒント {hint}px')
        if min(cell, hint) < 18: warn.append('★18px未満')
        print(f"  {pat['no']} ひとこと＋色 {w1 + w2}px（上限 {ONE_W}）{'  ' + '・'.join(warn) if warn else ''}")
    for s, sz in ((ASK, 100), (END_1, 42), (END_3, 40)):
        print(f"  「{s}」 {fit_size(s, sz, 900 if sz == 100 else 800, 820)}px（{sz}px のつもり）")


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
    """中部の波形の R が帯の右のほう（MARK_X。▲が付く位置）を通るときに「ピッ」。心室の拍は低い音。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for r, k, i in STRIP:
        ts = t_of(r - DT_REF)
        if i is not None and PATTERNS[i].get('gain') is not None:
            g = PATTERNS[i]['gain'](np.array([r - SEGS[i][0]]), PATTERNS[i]['L'])[0]
            if abs(g) < 0.5:                  # 電極外れ・とぎれのあいだは、モニターが拍を数えない
                continue
        if not (0.0 <= ts <= DUR - 0.3) or (T_STOP <= ts < T_GO):
            continue
        f = 960.0 if k == 'N' else 720.0
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
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel20_artifact.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel20_artifact_hq.mp4')
    o = ap.parse_args()
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    if o.hq and o.out == ap.get_default('out'):
        o.out = os.path.join(HERE, 'out', 'reel20_artifact_hq.mp4')
    if o.check:
        check(); return
    if o.thumb:
        os.makedirs(os.path.dirname(o.out), exist_ok=True)
        p = os.path.join(os.path.dirname(o.out), 'thumb_reel20_list.png')
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
