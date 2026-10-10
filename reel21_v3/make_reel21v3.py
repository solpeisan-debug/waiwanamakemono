"""第21弾v3 致死性不整脈 見るのは5か所（波形は v2 と同じ。見せ方を「見る場所ごとの場面」に作り直した）

決まった中身は docs/reel21_v2_spec.md（次の対応の文言はそのまま使う）、根拠は docs/reel21_v2_evidence.md。
波形の定義（ev・art・gain・hl）は reel21_v2/make_reel21v2.py と同じ（ここに写した）。

構成（12個の一覧はやめた）：
1. 冒頭（0〜約3秒）：「致死性不整脈」「見るのは5か所」（大きな黄色の「5」）。下で波形が流れ、そのまま場面①の1本目になる
2. 5つの場面（見る場所ごと。① → ⑤）
   - 上：場所の名前（大きく、場所の色）と、その下に「何を見るか」の1行
   - 中：その場所の波形を縦に並べる（名前のラベル＋実際の速さで流れる波形。25mm/秒・横 1mm＝14px）
   - はじめ（場所の説明）は全部を同じ扱いで。そのあと1つずつ紹介：いまの波形は大きく（10mm/mV）、特徴の部分を場所の色で。
     ほかは小さく薄く（アコーディオン）
   - 下：いまのパターンの「→ 次の対応」（固定の場所）
   - 場面のつなぎ目は、前の場面が上へ抜けて薄くなり、次の場面が下から上がってくる（何もない画面にはしない）
3. 最後：5か所（場所の色・小さな波形つき）→「どこを見落としやすい？コメントで教えてね」→「保存して見返してね」（緑）
   → 冒頭の画面へ戻る（ループ）

秒数は、表 BLOCKS（冒頭・場所の説明・パターン・最後）から決める。
【仮の秒数】ナレーションは録音前。いまは台本の字数から声の長さを見積もっている（1.2倍速で 約9字/秒）。
録音が届いたら align_vo.py で声の長さを測り、voice_len.json に書く → この表が声に合わせて組み直される。

使い方:
    python3 make_reel21v3.py --check      # 検算・秒数の表・字の幅と重なり
    python3 make_reel21v3.py --still 20   # 1コマだけ（out/still_020.0.png）
    python3 make_reel21v3.py --thumb      # サムネイル（透かしなし）
    python3 make_reel21v3.py --jobs 2     # 書き出し・60fps（音なし。out/reel21_v3.mp4）
    python3 make_reel21v3.py --hq         # 高画質（out/reel21_v3_hq.mp4）
    python3 make_reel21v3.py --preview    # スマホ確認用の軽い版（540×960・30fps。out/preview_low.mp4）
"""
import argparse
import json
import math
import os
import subprocess
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920

BG = (2, 7, 6)
G_MINOR = (13, 26, 21)
G_MAJOR = (34, 56, 46)
WHITE = (236, 241, 240)
GREY = (150, 160, 162)
DIM = (70, 82, 82)
LIGHT = (226, 232, 231)
OPEN_COL = (176, 186, 190)        # 冒頭の波形の色（色のない明るい灰色。場面①で緑＋場所の色になる）
GREEN = (130, 232, 172)
WAVE_GREEN = (40, 214, 128)
YEL = (255, 214, 64)

FONT = os.environ.get('REEL_FONT', os.path.join(HERE, 'fonts', 'NotoSansJP.ttf'))

# --- 見る場所（5か所）。色は場所ごと。ov＝何を見るか（画面の1行）、narr＝場所の説明のナレーション ----------
PLACES = [
    dict(no='①', name='PとQRSのつながり', col=(255, 212, 90),
         ov='Pのあとに、QRSが続いているか',
         narr='1つめは、PとQRSのつながり。Pのあとに、QRSが続いているか。'),
    dict(no='②', name='QRSの幅と形', col=(255, 152, 72),
         ov='幅が広いか、形がそろっているか',
         narr='2つめは、QRSの幅と形。幅が広いか、形がそろっているか。'),
    dict(no='③', name='T波の上', col=(200, 150, 255),
         ov='T波に、PVCが乗っていないか',
         narr='3つめは、T波の上。T波に、PVCが乗っていないか。'),
    dict(no='④', name='QRSがない', col=(255, 92, 112),
         ov='QRSが見えているか',
         narr='4つめは、QRSがない。QRSが見えているか。'),
    dict(no='⑤', name='波形では分からない', col=(110, 200, 255),
         ov='波形がふつうでも、脈を確かめる',
         narr='最後は、波形では分からない。波形がふつうでも、脈を確かめる。'),
]

# --- 波形の部品（実際の時間・秒、mV）。reel21_v2 と同じ ------------------------------
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


def qrs_pvc(t):                   # PVC（形A）：幅の広いQRS、逆向きのST-T
    return (0.95*_ga(t, 0.0, 0.020, 0.015) - 0.55*_g(t, 0.050, 0.019)
            - 0.38*_ga(t, 0.25, 0.058, 0.045))


def qrs_vt_rs(t):                 # 単形性VTのQRS（R＋S）。幅 約190ms
    return 0.95*_ga(t, 0.0, 0.026, 0.021) - 0.55*_g(t, 0.070, 0.025)


def qrs_vt(t):                    # 単形性VTの1拍：幅の広いQRS＋逆向きのST-T
    return qrs_vt_rs(t) - 0.38*_ga(t, 0.27, 0.058, 0.045)


def qrs_pvc2(t):                  # PVC（形B）：下向きのQRS、上向きのT（多形性VT用）
    return (-0.80*_ga(t, 0.01, 0.022, 0.026) + 0.25*_g(t, 0.075, 0.020)
            + 0.36*_ga(t, 0.26, 0.060, 0.045))


def qrs_longqt(t):                # QT延長の洞調律：Tが遅く、幅が広い（QT 約0.56秒）
    return (-0.08*_g(t, -0.030, 0.008) + 1.00*_g(t, 0.0, 0.011)
            - 0.20*_g(t, 0.028, 0.009) + 0.24*_ga(t, 0.40, 0.085, 0.060))


def qrs_escape(t):                # 遅く幅の広いQRS（120ms以上）、逆向きのT
    return (0.70*_ga(t, 0.0, 0.030, 0.034) - 0.18*_g(t, 0.085, 0.022)
            - 0.32*_ga(t, 0.34, 0.075, 0.055))


KINDS = {
    'N': (qrs_normal, p_sinus, PR),         # 洞調律の1拍（PEAでも同じ形）
    'Q': (qrs_longqt, p_sinus, PR),         # QT延長の洞調律
    'V': (qrs_pvc, None, 0.0),              # PVC（幅の広いQRS。ショートラン・R on T）
    'X': (qrs_vt, None, 0.0),               # 単形性VTの1拍（もっと幅の広いQRS）
    'W': (qrs_escape, None, 0.0),           # 遅く幅の広いQRS
    'P': (None, p_sinus, 0.0),              # P波だけ
}
ALL = [(-1e9, 1e9)]                         # 全部をその色で


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


# 多形性VT：幅の広いQRSが約230/分で、形・大きさ・向きが1拍ごとに変わる
POLY_N, POLY_L = 15, 4.0
_rs2 = _rs(21)
POLY = [(k*POLY_L/POLY_N + _rs2.uniform(-0.03, 0.03), _rs2.uniform(0.45, 1.15)*(1 if _rs2.rand() < 0.6 else -1),
         _rs2.randint(2)) for k in range(POLY_N)]


def art_poly(rel, L):
    r = np.mod(rel, L)
    out = np.zeros_like(rel)
    for c, a, kind in POLY:
        f = qrs_pvc if kind == 0 else qrs_pvc2
        for sh in (-L, 0.0, L):
            m = np.abs(r - c - sh) < 0.35
            if m.any():
                out[m] += a*f(r[m] - c - sh)
    return out


# トルサード：QT延長の洞調律 → T波の上のPVC（R on T）から、QRSの大きさがねじれるように変わる → 自然に止まる
TDP_A, TDP_B = 1.40, 3.95                  # 周期の中のトルサードの区間（秒）
TDP_F = 4.0                                # 約240/分


def art_tdp(rel, L):
    r = np.mod(rel, L)
    m = (r >= TDP_A - 0.1) & (r <= TDP_B + 0.1)
    out = np.zeros_like(rel)
    if m.any():
        x = r[m] - TDP_A
        dur = TDP_B - TDP_A
        env = np.sin(np.pi*np.clip(x/dur, 0, 1))**0.6                     # だんだん大きく → 小さく
        twist = np.cos(2*np.pi*x/1.25)                                     # 向きがゆっくり反転（ねじれ）
        car = np.sin(2*np.pi*TDP_F*x - 0.4) + 0.35*np.sin(4*np.pi*TDP_F*x)  # 幅の広いQRSが続く形
        out[m] = 0.95*env*twist*car * (x >= 0)
    return out


def gain_tdp(rel, L):                      # トルサードのあいだは洞調律の拍を消す
    r = np.mod(rel, L)
    return np.where((r >= TDP_A - 0.02) & (r < TDP_B + 0.05), 0.0, 1.0)


def art_vf_coarse(rel, L):                 # 粗いVF：3〜9Hzの不規則で大きな揺れ
    env = 0.75 + 0.25*np.sin(2*np.pi*rel/L)
    return env*band_noise(rel, L, 3.0, 9.0, 0.42, 24)


def art_vf_fine(rel, L):                   # 細かいVF：同じ揺れが小さい
    return band_noise(rel, L, 3.5, 10.0, 0.075, 25)


def art_asys(rel, L):                      # 心静止：ほぼまっすぐ（ごくわずかな基線のゆれ）
    return band_noise(rel, L, 0.25, 1.5, 0.012, 26)


RONT_C = 0.36                     # R on T：直前のRから PVC の頂点まで（秒）。T波の頂点（0.27秒）を過ぎた下りに乗る


# --- 12パターン（見る場所の順） --------------------------------------------------
# act：次の対応（docs/reel21_v2_spec.md の文言そのまま。「 ／ 」で2つの対応）。
# lines：画面での行の分け方（v2 と同じ）。(文字, 続きの行か)。続きの行は矢印なしで字下げ。--check で act に戻ることを確かめる。
# narr：ナレーション（下書き。録音前。narration.md と同じ）。
# 波形：1周期ぶんの拍（R頂点の時刻, 種類）と周期 L、連続した波形 art・倍率 gain、色を付ける範囲 hl（v2 と同じ）
# enter：特徴の部分（hl の始まり）が画面の右端に入ってくる時刻（紹介の始まりから・秒）。名前を言っているあいだに見えるように。
#        トルサードは、紹介が始まってから少しあとに始まるように（すぐ始まらない）
PATTERNS = [
    dict(key='モビッツII', place=0, name='モビッツII型',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='モビッツII型。PRは一定のまま、突然QRSが抜ける。',
         ev=[(0.16, 'N'), (0.96, 'N'), (1.76, 'N'), (2.4, 'P')], L=3.2, hl=[(2.30, 2.52)], enter=0.75),
    dict(key='完全房室ブロック', place=0, name='完全房室ブロック',
         act='→ 意識・血圧・胸痛・息苦しさ等確認。ペーシングに備えてパッド装着',
         lines=[('→ 意識・血圧・胸痛・息苦しさ等確認。', False), ('ペーシングに備えてパッド装着', True)],
         narr='完全房室ブロック。PとQRSが、別々に動く。',
         ev=[(k*0.68, 'P') for k in range(10)] + [(0.3 + k*1.7, 'W') for k in range(4)], L=6.8, hl=ALL),
    dict(key='ショートラン', place=1, name='ショートラン',
         act='→ 症状を見て、12誘導。QT、K・Mgなどを確認',
         lines=[('→ 症状を見て、12誘導。QT、K・Mgなどを確認', False)],
         narr='ショートラン。幅広いQRSが3つ以上続いて、自然に止まる。',
         ev=[(0, 'N'), (0.8, 'N'), (1.28, 'V'), (1.66, 'V'), (2.04, 'V'), (3.2, 'N')], L=4.0, hl=[(1.19, 2.46)],
         enter=0.6),
    dict(key='単形性VT', place=1, name='単形性VT',
         act='→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。パッド装着 ／ → 脈なしなら人を呼ぶ。CPR＋電気ショック',
         lines=[('→ 脈あり：意識・血圧・胸痛・息苦しさ等確認。', False), ('パッド装着', True),
                ('→ 脈なしなら人を呼ぶ。CPR＋電気ショック', False)],
         narr='単形性VT。速く、幅広く、同じ形。脈のあるなしで、動きが分かれる。',
         ev=[(k*0.32, 'X') for k in range(15)], L=4.8, hl=ALL),
    dict(key='多形性VT', place=1, name='多形性VT',
         act='→ 脈なし：CPR＋電気ショック ／ → 脈あり：人を呼び、パッド装着（続けば脈があってもショック）',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 脈あり：人を呼び、パッド装着', False),
                ('（続けば脈があってもショック）', True)],
         narr='多形性VT。形が1拍ごとに変わる。',
         ev=[], L=POLY_L, art=art_poly, hl=ALL),
    dict(key='トルサード', place=1, name='トルサード・ド・ポワント',
         act='→ 脈なし：CPR＋電気ショック ／ → 止まっても12誘導。QT、K・Mgなどを確認',
         lines=[('→ 脈なし：CPR＋電気ショック', False), ('→ 止まっても12誘導。QT、K・Mgなどを確認', False)],
         narr='トルサード。ねじれるように変わり、止まっても、くり返す。',
         ev=[(0, 'Q'), (1.0, 'Q'), (4.6, 'Q')], L=5.6, art=art_tdp, gain=gain_tdp,
         hl=[(TDP_A - 0.1, TDP_B + 0.1)], enter=0.85),
    dict(key='R on T', place=2, name='R on T',
         act='→ 12誘導。QT、K・Mgなどを確認。除細動器を近くに',
         lines=[('→ 12誘導。QT、K・Mgなどを確認。', False), ('除細動器を近くに', True)],
         narr='R on T。VFのきっかけになる。',
         ev=[(0, 'N'), (0.8, 'N'), (0.8 + RONT_C, 'V'), (2.4, 'N')], L=3.2, hl=[(0.8 + 0.14, 0.8 + RONT_C + 0.42)],
         enter=0.5),
    dict(key='粗いVF', place=3, name='粗いVF',
         act='→ 反応を確認し、人を呼んでCPR＋電気ショック',
         lines=[('→ 反応を確認し、人を呼んでCPR＋電気ショック', False)],
         narr='粗いVF。大きくバラバラ。',
         ev=[], L=4.0, art=art_vf_coarse, hl=ALL),
    dict(key='細かいVF', place=3, name='細かいVF',
         act='→ CPR＋電気ショック（細かくてもVFならショック）',
         lines=[('→ CPR＋電気ショック', False), ('（細かくてもVFならショック）', True)],
         narr='細かいVF。小さな揺れでも、VFならショック。',
         ev=[], L=4.0, art=art_vf_fine, hl=ALL),
    dict(key='心静止', place=3, name='心静止',
         act='→ 反応がなければ人を呼び、すぐCPR（ショックはしない）。並行して電極外れ・感度を確認',
         lines=[('→ 反応がなければ人を呼び、', False), ('すぐCPR（ショックはしない）。', True),
                ('並行して電極外れ・感度を確認', True)],
         narr='心静止。ほぼまっすぐ。反応がなければ、すぐCPR。',
         ev=[], L=4.0, art=art_asys, hl=ALL),
    dict(key='PEA1', place=4, name='PEA（ふつうに見える）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='PEA。ふつうに見えても、脈がない。',
         ev=[(k*0.75, 'N') for k in range(6)], L=4.5, hl=ALL),
    dict(key='PEA2', place=4, name='PEA（遅く幅広い）',
         act='→ 脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認',
         lines=[('→ 脈なしなら人を呼ぶ。', False), ('すぐCPR（ショックはしない）、', True), ('原因（4H4T）を確認', True)],
         narr='遅く幅広いQRSでも、脈がなければPEA。',
         ev=[(0.3, 'W'), (2.3, 'W')], L=4.0, hl=ALL),
]
for _p in PATTERNS:
    _pl = PLACES[_p['place']]
    _p['col'] = _pl['col']
    _p['pno'] = _pl['no']
N_PAT = len(PATTERNS)
SCENE_PATS = [[i for i, p in enumerate(PATTERNS) if p['place'] == s] for s in range(len(PLACES))]

NARR_OPEN = '致死性不整脈、見るのは5か所。'
NARR_END = '見るのは5か所。どこを見落としやすい？コメントで教えてね。'
NARR_SAVE = '保存して、見返してね。'
# ナレーションの文（align_vo.py の切り分けの単位）。キー：冒頭／場所0〜4／パターンの key／まとめ／保存
NARR = {'冒頭': NARR_OPEN}
for _s, _pl in enumerate(PLACES):
    NARR[f'場所{_s}'] = _pl['narr']
    for _i in SCENE_PATS[_s]:
        NARR[PATTERNS[_i]['key']] = PATTERNS[_i]['narr']
NARR['まとめ'] = NARR_END
NARR['保存'] = NARR_SAVE
NARR_ORDER = list(NARR.keys())


# --- 声の長さ（秒） -------------------------------------------------------------------
# 【仮】録音前は台本の字数から見積もる（1.2倍速で 約9字/秒。英字は1字＝2字ぶん、数字は1.5字ぶん、読点 0.2秒、文の中の句点 0.35秒）。
# 録音が届いたら align_vo.py が voice_len.json に測った長さを書き、そちらを使う。
CPS = 9.0
VOICE_LEN_FILE = os.path.join(HERE, 'voice_len.json')


def est_voice(s):
    n, pause = 0.0, 0.0
    body = s.rstrip('。？')
    for ch in body:
        if ch in '、':
            pause += 0.20
        elif ch in '。？':
            pause += 0.35
        elif ch == ' ':
            continue
        elif ch.isascii() and ch.isalpha():
            n += 2.0
        elif ch.isdigit():
            n += 1.5
        else:
            n += 1.0
    return round(n / CPS + pause, 2)


VOICE_LEN = {k: est_voice(v) for k, v in NARR.items()}
VOICE_MEASURED = False
if os.path.exists(VOICE_LEN_FILE):
    with open(VOICE_LEN_FILE, encoding='utf-8') as _f:
        _vl = json.load(_f)
    VOICE_LEN.update({k: float(v) for k, v in _vl.items() if k in VOICE_LEN})
    VOICE_MEASURED = True


def act_chars(pat):
    """次の対応の字数（矢印・空白・区切りの ／ は数えない）。"""
    return len(pat['act'].replace('→', '').replace('／', '').replace(' ', ''))


# --- 秒数の表（BLOCKS） ---------------------------------------------------------------
# 各ブロック：kind（open／ov／pat／end）、key（NARR のキー）、start・dur（秒）、voice（声の始まり・長さ）
# - open：冒頭。声は OPEN_LEAD 秒から。長さは OPEN_MIN 以上
# - ov：場所の説明。前の場面からの切りかえ（XF 秒）の真ん中が始まり。声は LEAD_OV 秒から、言い終わって GAP_OV 秒で1つめのパターンへ
# - pat：パターンの紹介。いまの波形が大きくなり（ACC 秒）、声は LEAD_PAT 秒から。言い終わって GAP_PAT 秒（≥0.4秒）あけて次へ。
#        次の対応は TEXT_IN 秒から出し（0.3秒で）、終わりの 0.25秒で消す。全部見えている時間が「1字 READ_S_PER_CHAR 秒（最低 READ_MIN）」以上
# - end：最後。声「見るのは5か所…」は END_LEAD から、「保存して…」はそのあと END_GAP。言い終わって END_HOLD、最後の LOOP_FADE で冒頭へ戻る
OPEN_LEAD, OPEN_MIN, OPEN_GAP = 0.10, 3.0, 0.6
LEAD_OV, GAP_OV, OV_MIN = 0.40, 0.55, 2.8
LEAD_PAT, GAP_PAT, PAT_MIN = 0.45, 0.65, 4.0
TEXT_IN, TEXT_FADE_IN, TEXT_FADE_OUT = 0.50, 0.30, 0.25
READ_S_PER_CHAR, READ_MIN = 0.11, 4.0
END_LEAD, END_GAP, END_HOLD = 0.35, 0.35, 1.2
LOOP_FADE = 0.75
FPS_GRID = 60


def _q(x):
    """コマ（1/60秒）にそろえる。"""
    return math.ceil(x*FPS_GRID - 1e-6) / FPS_GRID


def read_need(i):
    return max(READ_MIN, READ_S_PER_CHAR*act_chars(PATTERNS[i]))


def build_blocks():
    blocks, t = [], 0.0

    def add(kind, key, dur, lead, **kw):
        nonlocal t
        dur = _q(dur)
        blocks.append(dict(kind=kind, key=key, start=t, dur=dur, end=t + dur,
                           v0=t + lead, vlen=VOICE_LEN[key], **kw))
        t += dur

    add('open', '冒頭', max(OPEN_MIN, OPEN_LEAD + VOICE_LEN['冒頭'] + OPEN_GAP), OPEN_LEAD)
    for s in range(len(PLACES)):
        add('ov', f'場所{s}', max(OV_MIN, LEAD_OV + VOICE_LEN[f'場所{s}'] + GAP_OV), LEAD_OV, scene=s)
        for i in SCENE_PATS[s]:
            key = PATTERNS[i]['key']
            d_voice = LEAD_PAT + VOICE_LEN[key] + GAP_PAT
            d_read = TEXT_IN + TEXT_FADE_IN + read_need(i) + TEXT_FADE_OUT
            add('pat', key, max(PAT_MIN, d_voice, d_read), LEAD_PAT, scene=s, pat=i,
                d_voice=d_voice, d_read=d_read)
    v_end, v_save = VOICE_LEN['まとめ'], VOICE_LEN['保存']
    add('end', 'まとめ', END_LEAD + v_end + END_GAP + v_save + END_HOLD + LOOP_FADE, END_LEAD,
        save0=None)
    b = blocks[-1]
    b['save0'] = b['v0'] + v_end + END_GAP
    return blocks, t


BLOCKS, DUR = build_blocks()
PAT_BLOCK = {b['pat']: b for b in BLOCKS if b['kind'] == 'pat'}
OV_BLOCK = {b['scene']: b for b in BLOCKS if b['kind'] == 'ov'}
OPEN_B = BLOCKS[0]
END_B = BLOCKS[-1]


def scene_span(s):
    """場面 s の [場所の説明の始まり, 最後のパターンの終わり]。"""
    return OV_BLOCK[s]['start'], PAT_BLOCK[SCENE_PATS[s][-1]]['end']


# --- 波形（周期 L でくり返す） -----------------------------------------------------
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
    for r, k in beats:
        m = np.abs(tau - r) < 0.75
        if m.any():
            v[m] += beat_wave(tau[m] - r, k)
    return v


def periodic_beats(pat, t0, t1):
    out = []
    L = pat['L']
    for k in range(int(math.floor(t0 / L)) - 1, int(math.ceil(t1 / L)) + 1):
        for r, kind in pat['ev']:
            out.append((k*L + r, kind))
    return out


def art_apply(pat, rel, v):
    L = pat['L']
    if pat.get('gain'):
        v = pat['gain'](rel, L) * v
    if pat.get('art'):
        v = v + pat['art'](rel, L)
    return v


def hl_mask(pat, rel):
    if pat['hl'] is ALL:
        return np.ones(len(rel), dtype=bool)
    r = np.mod(rel, pat['L'])
    m = np.zeros(len(rel), dtype=bool)
    for a, b in pat['hl']:
        for sh in (-pat['L'], 0.0, pat['L']):
            m |= (r + sh >= a) & (r + sh <= b)
    return m


def pattern_wave(i, rel):
    pat = PATTERNS[i]
    bl = periodic_beats(pat, rel.min() - 1, rel.max() + 1)
    return art_apply(pat, rel, wave_from(bl, rel))


_EXT = {}


def extent(i):
    """1周期の波形のいちばん上・下（mV）。"""
    if i not in _EXT:
        rel = np.arange(0, PATTERNS[i]['L'], 0.002)
        v = pattern_wave(i, rel)
        _EXT[i] = (max(0.15, float(v.max())), min(-0.15, float(v.min())))
    return _EXT[i]


# 流れる帯：1mm = 14px、25mm/秒 → 実際の1秒 = 350px。新しい波形は右から入り、左へ流れる
F_PXMM = 14.0
F_PXS = 25 * F_PXMM
F_MV = 10 * F_PXMM                # 10mm/mV（いま紹介中の波形）
XC = W / 2


def phase_of(i):
    """帯 i の位相：画面の x、時刻 t の点は、パターンの rel = t + PHASE[i] + (x − W)/F_PXS。
    特徴の部分（hl の始まり）が、紹介の始まりから enter 秒で右端に入ってくるようにする。"""
    pat = PATTERNS[i]
    b = PAT_BLOCK[i]
    if pat['hl'] is ALL:
        return -b['start']           # 連続した波形：紹介の始まりで周期の頭が右端に
    return pat['hl'][0][0] - (b['start'] + pat['enter'])


PHASE = {i: phase_of(i) for i in range(N_PAT)}


def rel_at(i, t, x):
    return t + PHASE[i] + (np.asarray(x, dtype=float) - W) / F_PXS


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


def lerp(a, b, u):
    return a + (b - a)*u


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


# 閉じかっこのすぐあとの句読点（「）。」「）、」）は、全角の空きで離れて見えるので詰める（v2 と同じ）
KERN_PAIRS = ('）。', '）、')
KERN = 0.45


def _layout(f, s, sz):
    pieces, start = [], 0
    for i in range(len(s) - 1):
        if s[i:i+2] in KERN_PAIRS:
            pieces.append(s[start:i+1]); start = i + 1
    pieces.append(s[start:])
    offs, x = [], 0.0
    for j, pc in enumerate(pieces):
        offs.append(x)
        x += f.getlength(pc) - (KERN*sz if j + 1 < len(pieces) else 0.0)
    boxes = [f.getbbox(pc) for pc in pieces]
    x0 = min(o + b[0] for o, b in zip(offs, boxes)); x1 = max(o + b[2] for o, b in zip(offs, boxes))
    y0 = min(b[1] for b in boxes); y1 = max(b[3] for b in boxes)
    return pieces, offs, (int(math.floor(x0)), y0, int(math.ceil(x1)), y1)


def text_img(s, size, weight, col, max_w=None):
    k = (s, size, weight, col, max_w)
    if k in _TXT:
        return _TXT[k]
    sz = size
    while True:
        f = font(sz, weight)
        pieces, offs, (x0, y0, x1, y1) = _layout(f, s, sz)
        if max_w is None or (x1 - x0) <= max_w or sz <= 16:
            break
        sz -= 1
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (x1 - x0 + 8, asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for pc, o in zip(pieces, offs):
        d.text((4 - x0 + o, 4), pc, font=f, fill=col + (255,))
    if len(_TXT) > 4000:
        _TXT.clear()
    _TXT[k] = (im, asc)
    return _TXT[k]


def text_w(s, size, weight):
    return text_img(s, size, weight, WHITE)[0].size[0] - 8


def put(base, s, size, weight, col, cx=None, cy=None, x=None, a=1.0, max_w=None, right=None):
    """文字を置く。薄くするときは alpha を掛けてから合成する（PIL の fill のアルファは効かないため）。"""
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
    """put(cy=…) で置いたときの、字の上端・下端（y）。"""
    im, asc = text_img(s, size, weight, WHITE, max_w)
    bb = im.getchannel('A').getbbox()
    py = int(cy - 4 - asc*0.62)
    return py + bb[1], py + bb[3]


def parts_layout(parts, size, max_w):
    while True:
        ims = [text_img(sx, int(size*k), 800, col) for sx, k, col in parts]
        widths = [im.size[0] - 8 for im, _ in ims]
        total = sum(widths) + 6*(len(ims) - 1)
        if total <= max_w or size <= 24:
            return ims, widths, total, size
        size -= 1


MARGIN = 130


def draw_parts(base, parts, size, baseline, a, max_w=W - 2*MARGIN - 10):
    """大きさのちがう字をベースラインでそろえて、中央に並べる（「見るのは5か所」）。"""
    if a <= 0.004:
        return
    ims, widths, total, _ = parts_layout(parts, size, max_w)
    x = (W - total) / 2
    for (im, asc), w in zip(ims, widths):
        if a < 0.999:
            im = im.copy(); im.putalpha(im.getchannel('A').point(lambda q: int(q*a)))
        base.alpha_composite(im, (int(x - 4), int(baseline - 4 - asc)))
        x += w + 6


def parts_top(parts, size, baseline):
    ims, widths, total, sz = parts_layout(parts, size, W - 2*MARGIN - 10)
    return min(baseline - 4 - asc + im.getchannel('A').getbbox()[1] for im, asc in ims), total


GRID_Y0 = 0                        # マス目の太い線は y = 70 の倍数（波形の基線をここにそろえる）


def grid():
    """背景のマス目：波形と同じ 1mm＝14px（25mm/秒・10mm/mV）。小さいマス 14px、大きいマス 70px（太い線）。"""
    im = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    pm = F_PXMM
    for i in range(int(W/pm) + 2):
        x = round(i*pm)
        d.line([(x, 0), (x, H)], fill=(G_MAJOR if i % 5 == 0 else G_MINOR) + (255,),
               width=2 if i % 5 == 0 else 1)
    for k in range(-1, int(H/pm) + 2):
        y = round(GRID_Y0 + k*pm)
        d.line([(0, y), (W, y)], fill=(G_MAJOR if k % 5 == 0 else G_MINOR) + (255,),
               width=2 if k % 5 == 0 else 1)
    return im


# --- 線を描く --------------------------------------------------------------------
SS = 2
BLUR = (7, 18)


def glow_line(size, runs, col, width, a, glow=1.0):
    """runs: 点列のリスト。グロー付きの線を RGBA で返す。glow=0 で芯の線だけ。"""
    w, h = size
    core = Image.new('L', (w*SS, h*SS), 0)
    dc = ImageDraw.Draw(core)
    for pts in runs:
        if len(pts) >= 2:
            dc.line([(x*SS, y*SS) for x, y in pts], fill=255, width=max(1, int(round(width*SS))), joint='curve')
    core = core.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if glow*a > 0.02:
        g1 = np.asarray(core.filter(ImageFilter.GaussianBlur(BLUR[0])), dtype=np.float32)
        g2 = np.asarray(core.filter(ImageFilter.GaussianBlur(BLUR[1])), dtype=np.float32)
        g = np.maximum(g1*0.95, g2*0.5)
        lay = Image.new('RGBA', (w, h), col + (0,))
        lay.putalpha(Image.fromarray(np.clip(g*a*glow, 0, 255).astype(np.uint8)))
        out.alpha_composite(lay)
    lay2 = Image.new('RGBA', (w, h), mix(col, (255, 255, 255), 0.6*(0.4 + 0.6*glow)) + (0,))
    lay2.putalpha(core.point(lambda q: int(q*a)))
    out.alpha_composite(lay2)
    return out


def draw_strip(base, i, t, st, x0=0, x1=W, col_all=None):
    """帯 i（パターン i をくり返した波形）を、状態 st（基線 y・倍率 g・濃さ a・線の太さ lw・グロー glow・
    特徴の色の強さ hl・緑の強さ green）で描く。col_all があれば全部をその色で。"""
    a = st['a']
    if a <= 0.01:
        return
    pat = PATTERNS[i]
    xs = np.arange(x0, x1 + 0.5, 0.5)
    rel = rel_at(i, t, xs)
    v = pattern_wave(i, rel)
    ys = st['base'] - v*st['g']
    pad = 26
    y_lo = int(math.floor(ys.min())) - pad
    y_hi = int(math.ceil(ys.max())) + pad
    bx0 = int(x0) - pad
    size = (int(x1 - x0) + 2*pad, max(4, y_hi - y_lo))
    lay = Image.new('RGBA', size, (0, 0, 0, 0))
    base_col = mix(OPEN_COL, WAVE_GREEN, st['green'])
    if col_all is not None:
        groups = [(np.ones(len(xs), bool), col_all)]
    else:
        m = hl_mask(pat, rel)
        hl_col = mix(base_col, pat['col'], st['hl'])
        groups = [(~m, base_col), (m, hl_col)]
    for sel0, col in groups:
        if not sel0.any():
            continue
        sel = sel0 | np.roll(sel0, 1) | np.roll(sel0, -1)
        idx = np.where(sel)[0]
        runs = [list(zip(xs[r] - bx0, ys[r] - y_lo)) for r in np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)]
        lay.alpha_composite(glow_line(size, runs, col, st['lw'], a, st['glow']))
    base.alpha_composite(lay, (bx0, y_lo))


# --- 場面の並べ方（アコーディオン） ---------------------------------------------------
TITLE_CY, TITLE_SZ = 340, 54       # 場所の名前
OVL_CY, OVL_SZ = 410, 34           # 何を見るか（1行）
STACK_Y0, STACK_Y1 = 446, 1380     # 波形を並べる範囲
ACT_Y0, ACT_PITCH, ACT_SZ = 1418, 44, 32   # 次の対応（最大3行）の1行目の字の中心・行の間隔・字の大きさ
ACT_W = 760                        # 次の対応の幅の上限
LBL = {  # ラベル（パターンの名前）：字の大きさ・太さ・行の高さ・波との余白
    'ov': dict(sz=34, wt=800, h=46, pad=12),
    'hi': dict(sz=46, wt=900, h=60, pad=14),
    'co': dict(sz=26, wt=700, h=34, pad=6),
}
STRIP_GAP = 10
OV_GAINS = (F_MV, F_MV*0.5, F_MV*0.4, F_MV*0.3)    # 場所の説明のときの倍率（入るいちばん大きいもの）
CO_GAINS = (F_MV*0.3, F_MV*0.25, F_MV*0.2)          # 小さくした波形の倍率
OPEN_BASE = 1050                   # 冒頭の波形の基線（太い線の上）
LABEL_X = 135


def _snap_up(y, step):
    return GRID_Y0 + math.ceil((y - GRID_Y0) / step - 1e-9) * step


def _stack(items):
    """items: [(パターン, 種類 'ov'/'hi'/'co', 倍率)] → 各帯の基線・ラベルの中心と、下端。
    10mm/mV と 5mm/mV の帯は基線を太い線（70px）に、ほかは細い線（14px）にのせる。"""
    y = STACK_Y0
    out = []
    for i, kind, g in items:
        L_ = LBL[kind]
        vmax, vmin = extent(i)
        up, down = vmax*g, -vmin*g
        step = 70 if g in (F_MV, F_MV*0.5) else 14
        base = _snap_up(y + L_['h'] + L_['pad'] + up, step)
        lbl_cy = base - up - L_['pad'] - L_['h']/2 + 2
        out.append(dict(i=i, kind=kind, g=g, base=base, lbl_cy=lbl_cy))
        y = base + down + L_['pad'] + STRIP_GAP
    return out, y - STRIP_GAP


def _fit(items_fn, gain_list):
    for g in gain_list:
        out, bot = _stack(items_fn(g))
        if bot <= STACK_Y1:
            return out, bot
    return out, bot


_LAYOUT = {}


def scene_layout(s, mode):
    """場面 s の並べ方。mode：'ov'（場所の説明。全部同じ扱い）／パターン番号（その帯を大きく、ほかを小さく）。
    かたまりを縦の真ん中へ、太い線の間隔（70px）ごとに動かす（基線は線の上のまま）。"""
    k = (s, mode)
    if k in _LAYOUT:
        return _LAYOUT[k]
    pats = SCENE_PATS[s]
    if mode == 'ov':
        out, bot = _fit(lambda g: [(i, 'ov', g) for i in pats], OV_GAINS)
    else:
        out, bot = _fit(lambda g: [(i, 'hi' if i == mode else 'co', F_MV if i == mode else g) for i in pats], CO_GAINS)
    top = min(o['lbl_cy'] - LBL[o['kind']]['h']/2 for o in out)
    shift = math.floor(((STACK_Y1 - bot) - (top - STACK_Y0)) / 2 / 70) * 70
    shift = max(-(top - STACK_Y0) // 70 * 70, min(shift, (STACK_Y1 - bot) // 70 * 70))
    res = {}
    for o in out:
        kind = o['kind']
        L_ = LBL[kind]
        i = o['i']
        st = dict(base=o['base'] + shift, g=o['g'], lbl_cy=o['lbl_cy'] + shift, green=1.0,
                  lbl_sz=L_['sz'], lbl_wt=L_['wt'], kind=kind)
        if kind == 'hi':
            st.update(a=1.0, lw=4.5, glow=1.0, hl=1.0, lbl_a=1.0, lbl_col=PATTERNS[i]['col'])
        elif kind == 'ov':
            st.update(a=1.0, lw=3.6, glow=0.6, hl=1.0, lbl_a=1.0, lbl_col=mix(LIGHT, PATTERNS[i]['col'], 0.55))
        else:
            st.update(a=0.38, lw=2.4, glow=0.0, hl=0.8, lbl_a=0.55, lbl_col=GREY)
        res[i] = st
    _LAYOUT[k] = res
    return res


def open_layout():
    """冒頭：場面①の1本目（モビッツII型）が画面の真ん中を灰色で流れ、2本目はまだ出ない。"""
    ov = scene_layout(0, 'ov')
    res = {}
    for n, i in enumerate(SCENE_PATS[0]):
        st = dict(ov[i])
        if n == 0:
            st.update(base=OPEN_BASE, g=F_MV, a=1.0, lw=4.5, glow=1.0, hl=0.0, green=0.0, lbl_a=0.0,
                      lbl_cy=ov[i]['lbl_cy'] + (OPEN_BASE - ov[i]['base']))
        else:
            st.update(a=0.0, lbl_a=0.0, base=ov[i]['base'] + 60, lbl_cy=ov[i]['lbl_cy'] + 60)
        res[i] = st
    return res


NUM_KEYS = ('base', 'g', 'lbl_cy', 'green', 'a', 'lw', 'glow', 'hl', 'lbl_a', 'lbl_sz')


def lerp_state(s0, s1, u):
    st = dict(s1)
    for k in NUM_KEYS:
        st[k] = lerp(s0[k], s1[k], u)
    st['lbl_col'] = mix(s0['lbl_col'], s1['lbl_col'], u)
    st['lbl_sz'] = int(round(st['lbl_sz']))
    st['lbl_wt'] = s1['lbl_wt'] if u >= 0.5 else s0['lbl_wt']
    return st


ACC = 0.5                         # アコーディオンの動き（秒）
OPEN_MOVE = 0.8                   # 冒頭の波形が場面①の1本目の位置へ動く（秒）


def scene_states(s, t):
    """場面 s の各帯の状態（時刻 t）。"""
    ov_b = OV_BLOCK[s]
    modes = [(ov_b['start'], 'ov', OPEN_MOVE if s == 0 else 0.0)] + \
        [(PAT_BLOCK[i]['start'], i, ACC) for i in SCENE_PATS[s]]
    if s == 0:
        prev = open_layout()
    else:
        prev = None
    cur = prev
    for t0, mode, dur in modes:
        if t < t0:
            break
        lay = scene_layout(s, mode)
        if prev is not None and dur > 0 and t < t0 + dur:
            u = ease((t - t0) / dur)
            cur = {i: lerp_state(prev[i], lay[i], u) for i in lay}
        else:
            cur = lay
        prev = lay
    if cur is None:
        cur = scene_layout(s, 'ov')
    return cur


def draw_scene(base, s, t, a=1.0, dy=0.0, t_wave=None):
    """場面 s：場所の名前・何を見るか・波形の帯とラベル。a・dy は場面の切りかえ用（全体の濃さ・縦のずれ）。"""
    tw = t if t_wave is None else t_wave
    states = scene_states(s, t)
    for i, st in states.items():
        st = dict(st)
        st['a'] *= a
        st['base'] += dy
        draw_strip(base, i, tw, st)
        la = st['lbl_a'] * a
        if la > 0.01:
            put(base, PATTERNS[i]['name'], st['lbl_sz'], st['lbl_wt'], st['lbl_col'], x=LABEL_X,
                cy=st['lbl_cy'] + dy, a=la, max_w=W - 2*MARGIN)


def draw_scene_head(base, s, a, dy=0.0):
    pl = PLACES[s]
    put(base, f"{pl['no']} {pl['name']}", TITLE_SZ, 900, pl['col'], cx=XC, cy=TITLE_CY + dy, a=a, max_w=W - 2*MARGIN)
    put(base, pl['ov'], OVL_SZ, 600, LIGHT, cx=XC, cy=OVL_CY + dy, a=a*0.95, max_w=W - 2*MARGIN)


# --- 次の対応 --------------------------------------------------------------------
def act_layout(pat):
    """[(文字, 左端x, 字の中心y, 続きの行か)] と幅。行のかたまりを中央に置き、行は左ぞろえ。続きの行は矢印のぶん字下げ。"""
    ind = text_w('→ ', ACT_SZ, 600) + 4
    ws = [text_w(s, ACT_SZ, 600) + (ind if cont else 0) for s, cont in pat['lines']]
    x0 = XC - max(ws) / 2
    return [(s, x0 + (ind if cont else 0), ACT_Y0 + k*ACT_PITCH, cont) for k, (s, cont) in enumerate(pat['lines'])], max(ws)


def draw_act(im, pat, a):
    rows, _ = act_layout(pat)
    for s, x, cy, cont in rows:
        if not cont and s.startswith('→ '):
            put(im, '→', ACT_SZ, 800, pat['col'], x=x, cy=cy, a=a)
            put(im, s[2:], ACT_SZ, 600, LIGHT, x=x + text_w('→ ', ACT_SZ, 600) + 4, cy=cy, a=a)
        else:
            put(im, s, ACT_SZ, 600, LIGHT, x=x, cy=cy, a=a)


def act_alpha(i, t):
    b = PAT_BLOCK[i]
    return ramp(t, b['start'] + TEXT_IN, TEXT_FADE_IN) * (1 - ramp(t, b['end'] - TEXT_FADE_OUT, TEXT_FADE_OUT))


# --- 冒頭・最後・サムネイル --------------------------------------------------------
TITLE = '致死性不整脈'
TITLE_SUB = [('見るのは', 1.0, WHITE), ('5', 1.8, YEL), ('か所', 1.0, WHITE)]
OPEN_TITLE_CY, OPEN_TITLE_SZ = 560, 130
OPEN_SUB_BASE, OPEN_SUB_SZ = 790, 72
OPEN_DOTS_CY = 868                  # 「① ② ③ ④ ⑤」（場所の色）
END_HEAD = [('見るのは', 1.0, WHITE), ('5', 1.8, YEL), ('か所', 1.0, WHITE)]
END_ASK = 'どこを見落としやすい？コメントで教えてね'
END_SAVE = '保存して見返してね'
NOTE1 = '実際の速さ（25mm/秒）'
NOTE2 = '※数値はこの波形での一例'
NOTE_CY = (1560, 1586)
WATERMARK = '@nurse_polarbearden'
REP = [0, 3, 6, 7, 10]              # 場所ごとの代表の波形：モビッツII型・単形性VT・R on T・粗いVF・PEA（ふつうに見える）


def place_rows(base, t, y0, pitch, lbl_sz, wave_h, a_list, x0=LABEL_X, x1=W - MARGIN, t_static=None):
    """5か所を、場所の色の名前＋小さな波形（実際の速さ 25mm/秒、高さ wave_h に入る倍率・最大 5mm/mV）で並べる。"""
    for s, pl in enumerate(PLACES):
        a = a_list[s]
        if a <= 0.01:
            continue
        top = y0 + s*pitch
        put(base, f"{pl['no']} {pl['name']}", lbl_sz, 800, pl['col'], x=x0, cy=top + lbl_sz*0.55, a=a)
        i = REP[s]
        vmax, vmin = extent(i)
        g = min(F_MV*0.5, (wave_h - 8) / (vmax - vmin))
        wy0 = top + lbl_sz*1.15 + 4
        bl = wy0 + 4 + vmax*g
        tt = t if t_static is None else t_static[s]
        draw_strip(base, i, tt, dict(base=bl, g=g, a=a, lw=3.0, glow=0.5, hl=1.0, green=1.0), x0=x0, x1=x1,
                   col_all=pl['col'])


END_ROW_Y0, END_ROW_PITCH, END_ROW_LBL, END_ROW_WAVE = 452, 158, 40, 96
END_HEAD_BASE = 390
END_ASK_CY, END_SAVE_CY = 1300, 1378


def end_times():
    b = END_B
    t_list = [b['start'] + 0.15 + 0.12*s for s in range(len(PLACES))]
    t_ask = b['v0'] + max(0.6, VOICE_LEN['まとめ']*0.32)        # 「見るのは5か所。」を言い終わるころ
    return t_list, t_ask, b['save0'] - 0.1


def draw_end(im, t, a):
    if a <= 0.004:
        return
    t_list, t_ask, t_save = end_times()
    draw_parts(im, END_HEAD, 60, END_HEAD_BASE, a*ramp(t, END_B['start'], 0.4))
    place_rows(im, t, END_ROW_Y0, END_ROW_PITCH, END_ROW_LBL, END_ROW_WAVE,
               [a*ramp(t, t0, 0.35) for t0 in t_list])
    put(im, END_ASK, 38, 800, WHITE, cx=XC, cy=END_ASK_CY, a=a*ramp(t, t_ask, 0.4), max_w=W - 2*MARGIN)
    put(im, END_SAVE, 46, 900, GREEN, cx=XC, cy=END_SAVE_CY, a=a*ramp(t, t_save, 0.4), max_w=W - 2*MARGIN)


def draw_open_text(im, a):
    if a <= 0.004:
        return
    put(im, TITLE, OPEN_TITLE_SZ, 900, WHITE, cx=XC, cy=OPEN_TITLE_CY, a=a, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE, a)
    dots = [pl['no'] for pl in PLACES]
    gap = 96
    for k, (pl, s) in enumerate(zip(PLACES, dots)):
        put(im, s, 50, 800, pl['col'], cx=XC + (k - 2)*gap, cy=OPEN_DOTS_CY, a=a)


_GRID = None
XF = 0.7                          # 場面の切りかえ（秒）。前の場面が上へ抜け、次の場面が下から上がる
SLIDE = 70


def frame(t, watermark=True):
    global _GRID
    if _GRID is None:
        _GRID = grid()
    im = _GRID.copy()

    a_loop = ramp(t, DUR - LOOP_FADE, LOOP_FADE)          # 1 で冒頭と同じ画面
    # 冒頭の文字：0〜 出ていて、場面①の始まりで消える。最後の LOOP_FADE で戻る
    ov0 = OV_BLOCK[0]['start']
    a_open = 1 - ramp(t, ov0 - 0.35, 0.5)
    draw_open_text(im, max(a_open, a_loop))

    # 場面
    for s in range(len(PLACES)):
        s0, s1 = scene_span(s)
        if s == 0:
            u_in = 1.0
            a_head = ramp(t, s0, 0.45)
            dy_in = 0.0
        else:
            u_in = ease((t - (s0 - XF/2)) / XF)
            a_head = u_in
            dy_in = SLIDE*(1 - u_in)
        u_out = ease((t - (s1 - XF/2)) / XF)
        a = u_in * (1 - u_out)
        if a <= 0.004:
            continue
        dy = dy_in - SLIDE*u_out
        draw_scene(im, s, t, a, dy)
        draw_scene_head(im, s, a_head*(1 - u_out), dy)
    # 冒頭へ戻るところ：冒頭の波形（場面①の1本目、冒頭の位置）を t − DUR の時刻で
    if a_loop > 0.004:
        st = dict(open_layout()[SCENE_PATS[0][0]])
        st['a'] = a_loop
        draw_strip(im, SCENE_PATS[0][0], t - DUR, st)

    # 次の対応
    for i, b in PAT_BLOCK.items():
        if b['start'] <= t < b['end']:
            draw_act(im, PATTERNS[i], act_alpha(i, t))

    # 最後
    a_end = ease((t - (END_B['start'] - XF/2)) / XF) * (1 - a_loop)
    draw_end(im, t, a_end)

    put(im, NOTE1, 24, 400, GREY, x=135, cy=NOTE_CY[0], a=0.85)
    put(im, NOTE2, 24, 400, GREY, x=135, cy=NOTE_CY[1], a=0.85)
    if watermark:
        put(im, WATERMARK, 28, 500, WHITE, right=W - 130, cy=1576, a=0.42)
    return im.convert('RGB')


# --- サムネイル ---------------------------------------------------------------------
THUMB_TITLE_CY, THUMB_TITLE_SZ = 400, 124
THUMB_SUB_BASE, THUMB_SUB_SZ = 590, 74
THUMB_ROW_Y0, THUMB_ROW_PITCH, THUMB_ROW_LBL, THUMB_ROW_WAVE = 654, 186, 44, 118


def thumb_times():
    """サムネイルの波形：特徴の部分が帯の真ん中に来る時刻（場所ごと）。"""
    xm = (LABEL_X + W - MARGIN) / 2
    out = []
    for s in range(len(PLACES)):
        i = REP[s]
        pat = PATTERNS[i]
        c = pat['L'] / 2 if pat['hl'] is ALL else sum(pat['hl'][0]) / 2
        out.append(c - PHASE[i] - (xm - W) / F_PXS)
    return out


def thumbnail():
    """サムネイル（透かしなし）。大きな「致死性不整脈」「見るのは5か所」と、5か所（場所の色）それぞれに代表の小さな波形。
    プロフィールのグリッド（中央 1080×1350、y 285〜1635）に要素が収まる。"""
    im = grid()
    put(im, TITLE, THUMB_TITLE_SZ, 900, WHITE, cx=XC, cy=THUMB_TITLE_CY, max_w=W - 2*MARGIN)
    draw_parts(im, TITLE_SUB, THUMB_SUB_SZ, THUMB_SUB_BASE, 1.0)
    place_rows(im, 0.0, THUMB_ROW_Y0, THUMB_ROW_PITCH, THUMB_ROW_LBL, THUMB_ROW_WAVE, [1.0]*5,
               t_static=thumb_times())
    return im.convert('RGB')


# --- 検算 ------------------------------------------------------------------------
def _qrs_ms(f, lim=0.12):
    tt = np.arange(-0.2, 0.3, 0.0005)
    v = f(tt); m = (np.abs(v) > 0.05) & (tt < lim)
    return (tt[m].max() - tt[m].min()) * 1000


def screen_strings():
    out = [TITLE] + [s for s, _, _ in TITLE_SUB] + [END_ASK, END_SAVE, NOTE1, NOTE2]
    for p in PLACES:
        out += [f"{p['no']} {p['name']}", p['ov']]
    for p in PATTERNS:
        out += [p['name']] + [s for s, _ in p['lines']]
    return out


# 出さない言葉（spec の「出さないもの」＋第◯弾の表示）。この字そのものをコードに書かないよう、文字コードで持つ
NG_WORDS = ['報告', 'AED', '着用', '第']


def act_from_lines(pat):
    acts = []
    for s, cont in pat['lines']:
        if cont:
            acts[-1] += s
        else:
            acts.append(s)
    return ' ／ '.join(acts)


def timing_table():
    rows = []
    for b in BLOCKS:
        if b['kind'] == 'open':
            name = '冒頭'
        elif b['kind'] == 'ov':
            pl = PLACES[b['scene']]
            name = f"{pl['no']} {pl['name']}（場所の説明）"
        elif b['kind'] == 'pat':
            name = f"　{PATTERNS[b['pat']]['name']}"
        else:
            name = '最後（5か所・問いかけ・保存）'
        rows.append((name, b))
    return rows


def check():
    ok = True
    print(f"映像 {DUR:.2f}秒（{round(DUR*60)}コマ）"
          f"{'（声の長さは録音から）' if VOICE_MEASURED else '（仮：声の長さは台本の字数からの見積もり）'}")
    print('秒数の表（BLOCKS）')
    print('  ブロック                          始まり   長さ   声（始まり–終わり）  次まで  下限（声／読む）')
    for k, (name, b) in enumerate(timing_table()):
        v1 = b['v0'] + b['vlen']
        nxt = BLOCKS[k+1]['start'] if k + 1 < len(BLOCKS) else DUR
        gap = nxt - v1
        extra = ''
        if b['kind'] == 'pat':
            extra = f"  声{b['d_voice']:.2f}／読む{b['d_read']:.2f}（{act_chars(PATTERNS[b['pat']])}字）"
            if gap < 0.4 - 1e-9:
                extra += '  ← 間が短い'; ok = False
        print(f"  {name:<30} {b['start']:6.2f} {b['dur']:6.2f}   {b['v0']:6.2f}–{v1:6.2f}     {gap:5.2f}{extra}")
        if b['kind'] == 'end':
            print(f"     （保存の声 {b['save0']:.2f}–{b['save0'] + VOICE_LEN['保存']:.2f}、冒頭へ戻る {DUR - LOOP_FADE:.2f}–{DUR:.2f}）")
    # 声と次の声の間（パターンの声の終わり → 次のパターンの強調）
    # 文言
    spec_path = os.path.join(HERE, '..', 'docs', 'reel21_v2_spec.md')
    spec = open(spec_path, encoding='utf-8').read() if os.path.exists(spec_path) else None
    print('次の対応（画面の行）')
    for pat in PATTERNS:
        back = act_from_lines(pat)
        if back != pat['act']:
            print(f"  ✗ {pat['name']}：行をつなぐと文言とちがう：{back}"); ok = False
        if spec is not None and pat['act'] not in spec:
            print(f"  ✗ {pat['name']}：spec に同じ文言がない：{pat['act']}"); ok = False
        rows, wmax = act_layout(pat)
        x0 = min(x for _, x, _, _ in rows)
        bot = max(text_box(s, ACT_SZ, 600, cy)[1] for s, _, cy, _ in rows)
        flag = '' if (wmax <= ACT_W and x0 >= 160 - 1 and bot <= 1545) else '  ← 幅が広い・下が近い'
        ok &= not flag
        print(f"  {pat['name']}：{len(rows)}行 幅{wmax:.0f}px 左{x0:.0f}px 下端{bot}{flag}")
        for s, x, cy, cont in rows:
            print(f"      {'  ' if cont else ''}{s}")
    for s in screen_strings() + list(NARR.values()):
        if any(w in s for w in NG_WORDS):
            print(f'  ✗ 出してはいけない言葉：{s}'); ok = False
    if any('すぐ報' in s for s in NARR.values()):
        ok = False
    # 上の安全域
    tt = text_box(f"{PLACES[0]['no']} {PLACES[0]['name']}", TITLE_SZ, 900, TITLE_CY)
    ob = text_box(PLACES[0]['ov'], OVL_SZ, 600, OVL_CY)
    print(f'場所の名前 y {tt[0]}〜{tt[1]}、何を見るか y {ob[0]}〜{ob[1]}（上 300 以上、波形の範囲 {STACK_Y0}〜）')
    ok &= tt[0] >= 300 and ob[1] < STACK_Y0
    for p in PLACES:
        for s_, sz, wt in ((f"{p['no']} {p['name']}", TITLE_SZ, 900), (p['ov'], OVL_SZ, 600)):
            if text_w(s_, sz, wt) > W - 2*MARGIN:
                print(f'  ✗ 広い：{s_}'); ok = False
    # 並べ方：範囲に入るか・ラベルと上の帯の波が重ならないか・基線がマス目の線の上か
    print(f'並べ方（範囲 y {STACK_Y0}〜{STACK_Y1}。基線：10・5mm/mV は太い線＝70の倍数）')
    for s in range(len(PLACES)):
        for mode in ['ov'] + SCENE_PATS[s]:
            lay = scene_layout(s, mode)
            desc, prev_bot = [], None
            for i in SCENE_PATS[s]:
                st = lay[i]
                vmax, vmin = extent(i)
                L_ = LBL[st['kind']]
                lt, lb = text_box(PATTERNS[i]['name'], st['lbl_sz'], st['lbl_wt'], st['lbl_cy'], max_w=W - 2*MARGIN)
                wt_, wb_ = st['base'] - vmax*st['g'], st['base'] - vmin*st['g']
                bad = lt < STACK_Y0 - 4 or wb_ > STACK_Y1 or lb > wt_ - 3 or (prev_bot is not None and lt < prev_bot + 3)
                grid_ok = (st['base'] - GRID_Y0) % (70 if st['g'] in (F_MV, F_MV*0.5) else 14) == 0
                if bad or not grid_ok:
                    ok = False
                desc.append(f"{PATTERNS[i]['name']}[{st['kind']} {st['g']/F_PXMM:.1f}mm/mV 字{lt}〜{lb} 波{wt_:.0f}〜{wb_:.0f}"
                            f" 基線{st['base']:.0f}{'' if grid_ok else '✗線'}]{' ✗' if bad else ''}")
                prev_bot = wb_
            mname = '説明' if mode == 'ov' else PATTERNS[mode]['name']
            print(f"  {PLACES[s]['no']} {mname}：" + ' / '.join(desc))
    # 冒頭
    ttop = text_box(TITLE, OPEN_TITLE_SZ, 900, OPEN_TITLE_CY)
    stop, sw = parts_top(TITLE_SUB, OPEN_SUB_SZ, OPEN_SUB_BASE)
    vmax0 = extent(SCENE_PATS[0][0])[0]
    dots = text_box('①', 50, 800, OPEN_DOTS_CY)
    print(f'冒頭：タイトル y {ttop[0]}〜{ttop[1]}、見るのは5か所 上端 {stop}（幅 {sw}）、①〜⑤ {dots[0]}〜{dots[1]}、'
          f'波の上端 {OPEN_BASE - vmax0*F_MV:.0f}')
    ok &= ttop[1] < stop and dots[1] < OPEN_BASE - vmax0*F_MV - 6 and ttop[0] >= 300
    # 最後
    eh, _ = parts_top(END_HEAD, 60, END_HEAD_BASE)
    last = END_ROW_Y0 + 4*END_ROW_PITCH + END_ROW_LBL*1.15 + 4 + END_ROW_WAVE
    ask = text_box(END_ASK, 38, 800, END_ASK_CY); sv = text_box(END_SAVE, 46, 900, END_SAVE_CY)
    print(f'最後：見出し上端 {eh}、5か所 {END_ROW_Y0}〜{last:.0f}、問いかけ {ask[0]}〜{ask[1]}、保存 {sv[0]}〜{sv[1]}')
    ok &= eh >= 300 and last < ask[0] - 6 and sv[1] <= 1530
    # 次の対応と注記
    n1, n2 = text_box(NOTE1, 24, 400, NOTE_CY[0]), text_box(NOTE2, 24, 400, NOTE_CY[1])
    print(f'注記：{n1[0]}〜{n2[1]}（1600 以下）')
    ok &= n2[1] <= 1600
    # サムネイル
    th = text_box(TITLE, THUMB_TITLE_SZ, 900, THUMB_TITLE_CY)
    tlast = THUMB_ROW_Y0 + 4*THUMB_ROW_PITCH + THUMB_ROW_LBL*1.15 + 4 + THUMB_ROW_WAVE
    print(f'サムネイル：タイトル上端 {th[0]}、5か所の下端 {tlast:.0f}（285〜1635）')
    ok &= th[0] >= 285 and tlast <= 1635
    # 特徴の部分が名前を言っているあいだに見えるか
    print('特徴の部分（色の範囲）が見えている時間（紹介の始まりから）')
    for i, pat in enumerate(PATTERNS):
        if pat['hl'] is ALL:
            continue
        b = PAT_BLOCK[i]
        ts = np.arange(b['start'], b['end'], 0.02)
        vis = []
        for t in ts:
            rel = rel_at(i, t, np.array([0.0, W]))
            # 画面に入っている色の範囲
            xs = np.arange(0, W, 4.0)
            vis.append(hl_mask(pat, rel_at(i, t, xs)).any())
        vis = np.array(vis)
        first = ts[vis][0] - b['start'] if vis.any() else None
        v_name = (b['v0'], b['v0'] + min(1.2, b['vlen']))
        seen = all(vis[(ts >= v_name[0]) & (ts <= v_name[1])])
        print(f"  {pat['name']}：右端に入る {first:.2f}秒、名前を言うあいだ（{v_name[0]-b['start']:.2f}〜{v_name[1]-b['start']:.2f}秒）"
              f"{'見えている' if seen else '✗ 見えない'}、見えている割合 {vis.mean()*100:.0f}%")
        ok &= seen and first >= 0.3
    print('モデルの値')
    print(f'  モビッツII型：PR {PR:.2f}秒で一定、4つめのP波が伝わらない（4:3）')
    print(f'  完全房室ブロック：心房 {60/0.68:.0f}/分、心室 {60/1.7:.0f}/分（QRS {_qrs_ms(qrs_escape):.0f}ms）')
    print(f'  単形性VT：{60/0.32:.0f}/分、QRS幅 {_qrs_ms(qrs_vt_rs, 0.3):.0f}ms（PVC {_qrs_ms(qrs_pvc):.0f}ms）')
    print(f'  多形性VT：約{60*POLY_N/POLY_L:.0f}/分　トルサード：{TDP_B-TDP_A:.2f}秒、約{TDP_F*60:.0f}/分')
    print(f'  R on T：PVCは直前のRから {RONT_C:.2f}秒')
    print('OK' if ok else '✗ 見直す')
    return ok


# --- 書き出し ---------------------------------------------------------------------
def ffmpeg_bin():
    p = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
    if os.path.exists(p):
        return p
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return 'ffmpeg'


def render_chunk(args):
    i0, i1, fps, path, crf, preset, vf = args
    cmd = [ffmpeg_bin(), '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(fps), '-i', '-']
    if vf:
        cmd += ['-vf', vf]
    cmd += ['-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-profile:v', 'high', '-pix_fmt', 'yuv420p', path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(i0, i1):
        p.stdin.write(frame(n / fps).tobytes())
    p.stdin.close()
    p.wait()
    return path


def focus_strip(t):
    """モニター音を鳴らす帯：冒頭は1本目、場所の説明はその場面の1本目、紹介中はそのパターン。最後は鳴らさない。"""
    for b in BLOCKS:
        if b['start'] <= t < b['end']:
            if b['kind'] == 'open':
                return SCENE_PATS[0][0]
            if b['kind'] == 'ov':
                return SCENE_PATS[b['scene']][0]
            if b['kind'] == 'pat':
                return b['pat']
    return None


def beeps(path, sr=44100):
    """いまの帯の R（QRS）が画面の中央を通るときに「ピッ」。心室の拍は低い音。トルサードで消した拍は鳴らさない。"""
    n = int(DUR*sr)
    a = np.zeros(n, dtype=np.float32)
    for i, pat in enumerate(PATTERNS):
        if not pat['ev']:
            continue
        L = pat['L']
        # 中央を通る時刻：rel_at(i, t, XC) = r + kL
        off = PHASE[i] + (XC - W) / F_PXS
        for k in range(int(-off // L) - 2, int((DUR - off) // L) + 2):
            for r, kind in pat['ev']:
                if KINDS[kind][0] is None:
                    continue
                if pat.get('gain') is not None and pat['gain'](np.array([r]), L)[0] < 0.5:
                    continue
                ts = r + k*L - off
                if not (0 <= ts < DUR - 0.1) or focus_strip(ts) != i:
                    continue
                f = 960.0 if kind in ('N', 'Q') else 720.0
                Ln = int(0.08*sr)
                tt = np.arange(Ln)/sr
                s = 0.2*np.minimum(1, tt/0.004)*np.exp(-tt/0.045)*np.sin(2*np.pi*f*tt)
                j = int(ts*sr)
                a[j:j+Ln] += s[:max(0, min(Ln, n-j))]
    pcm = (np.clip(a, -1, 1)*32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def render(out, fps, jobs, crf, preset, vf=None):
    total = int(round(DUR*fps))
    step = math.ceil(total / jobs)
    tmp = os.path.join(os.path.dirname(out), 'parts_' + os.path.splitext(os.path.basename(out))[0])
    os.makedirs(tmp, exist_ok=True)
    args = [(i, min(total, i+step), fps, os.path.join(tmp, f'p{j:02d}.mp4'), crf, preset, vf)
            for j, i in enumerate(range(0, total, step))]
    with Pool(jobs) as pool:
        parts = pool.map(render_chunk, args)
    lst = os.path.join(tmp, 'list.txt')
    with open(lst, 'w') as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    subprocess.run([ffmpeg_bin(), '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-c:v', 'copy', '-movflags', '+faststart', out], check=True)
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'reel21_v3.mp4'))
    ap.add_argument('--still', type=float, nargs='*')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--thumb', action='store_true')
    ap.add_argument('--jobs', type=int, default=2)
    ap.add_argument('--hq', action='store_true', help='高画質（CRF 10・slow）。out/reel21_v3_hq.mp4')
    ap.add_argument('--preview', action='store_true', help='スマホ確認用（540×960・30fps）。out/preview_low.mp4')
    o = ap.parse_args()
    if o.check:
        assert check(); return
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    if o.thumb:
        p = os.path.join(HERE, 'out', 'thumb_reel21v3.png')
        thumbnail().save(p); print(p); return
    if o.still:
        for s in o.still:
            p = os.path.join(HERE, 'out', f'still_{s:05.1f}.png')
            frame(s).save(p); print(p)
        return
    if o.preview:
        render(os.path.join(HERE, 'out', 'preview_low.mp4'), 30, o.jobs, 26, 'veryfast',
               vf='scale=540:960:flags=lanczos')
        return
    crf, preset = (10, 'slow') if o.hq else (18, 'medium')
    out = o.out
    if o.hq and out == ap.get_default('out'):
        out = os.path.join(HERE, 'out', 'reel21_v3_hq.mp4')
    render(out, o.fps, o.jobs, crf, preset)


if __name__ == '__main__':
    main()
