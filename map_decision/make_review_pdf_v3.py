"""見分けマップ③（幅の広いQRS・v3 の形）― 専門医レビュー用の資料。

- out/review_map3_frames.pdf：映像のコマを等倍（1080×1920）で1ページずつ
  （冒頭・道すじが光った例・カードの拡大（参考）・サムネイル）
- review_request_map3.md：依頼文（作品の概要・マップの中身・各カードの波形の描き方・キャプション・見てほしい点・出典）

波形の数値（心拍数・R-R・QRS幅・PR）は、make_map_v2.py のモデルから計算する（手打ちしない）。
v1 用の make_review_pdf.py（マップ①②）はそのまま残してある。

使い方:
    python3 make_review_pdf_v3.py
"""
import os

os.environ['MAP_NO'] = '3'
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import make_map_v3 as m  # noqa: E402
import make_map as b  # noqa: E402
import make_map_v2 as v2  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'VT versus SVT': L + 'vt-versus-svt-ecg-library/',
    'Ventricular Tachycardia – Monomorphic VT': L + 'ventricular-tachycardia-monomorphic-ecg-library/',
    'Polymorphic VT and Torsades de Pointes (TdP)': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
    'Atrioventricular Re-entry Tachycardia (AVRT)': L + 'atrioventricular-re-entry-tachycardia-avrt/',
    'Atrial fibrillation/flutter in pre-excitation': L + 'atrial-fibrillation-in-pre-excitation/',
    'Atrial Fibrillation': L + 'atrial-fibrillation-ecg-library/',
    'Pre-excitation syndromes': L + 'pre-excitation-syndromes-ecg-library/',
    'Delta Wave': L + 'delta-wave-ecg-library/',
    'Right Bundle Branch Block (RBBB)': L + 'right-bundle-branch-block-rbbb-ecg-library/',
    'Left Bundle Branch Block (LBBB)': L + 'left-bundle-branch-block-lbbb-ecg-library/',
    'Accelerated Idioventricular Rhythm (AIVR)': L + 'accelerated-idioventricular-rhythm-aivr/',
    'Ventricular Escape Rhythm': L + 'ventricular-escape-rhythm-ecg-library/',
    'Hyperkalaemia ECG changes': L + 'hyperkalaemia-ecg-library/',
    'Pacemaker Rhythms – Normal Patterns': L + 'pacemaker-rhythms-normal-patterns/',
}
# 各カードの根拠（LITFL のページ名）と、ページの中で根拠にした文
BASIS = {
    'pace': ('Pacemaker Rhythms – Normal Patterns',
             'Pacing spike precedes the QRS complex. Right ventricle pacing lead placement results in a QRS morphology similar to LBBB.'),
    'vt3': ('VT versus SVT／Ventricular Tachycardia – Monomorphic VT',
            'Regular, broad complex tachycardia; Uniform QRS complexes … Very broad complexes (>160ms) … If in doubt, treat as VT!'),
    'svtbbb': ('VT versus SVT',
               'The likelihood of SVT with aberrancy is increased if: Previous ECGs show a bundle branch block pattern with identical morphology to the broad complex tachycardia'),
    'avrtw': ('Atrioventricular Re-entry Tachycardia (AVRT)／VT versus SVT',
              'In antidromic AVRT, anterograde conduction is via the accessory pathway (AP), producing a regular wide complex rhythm. '
              'This can be difficult to distinguish from ventricular tachycardia (VT)／（Antidromic AVRT の項）'
              'ECG features of AVRT with antidromic conduction: Rate usually 200-300 bpm; '
              'Wide QRS complexes due to abnormal ventricular depolarisation via AP'),
    'tdp': ('Polymorphic VT and Torsades de Pointes (TdP)',
            'QRS complexes “twist” around the isoelectric line … must have evidence of both PVT and QT prolongation'),
    'afbbb3': ('Atrial fibrillation/flutter in pre-excitation／Atrial Fibrillation',
               'LBBB usually has fixed width QRS complexes (AF の QRS は、もとの脚ブロック・副伝導路・心拍数による変行伝導がなければ < 120ms)'),
    'afwpw': ('Atrial fibrillation/flutter in pre-excitation',
              'Rate > 200 bpm; Irregular rhythm, with extremely high rates in some places — up to 300 bpm; Wide QRS complexes; Subtle beat-to-beat variation in QRS morphology'),
    'bbb': ('Right Bundle Branch Block (RBBB)／Left Bundle Branch Block (LBBB)',
            'QRS duration ≥ 120ms … RBBB：RSR’ pattern in V1-3、LBBB：Dominant S wave in V1（右か左かは胸部誘導で決める）'),
    'wpw': ('Pre-excitation syndromes／Delta Wave',
            'PR interval < 120ms; Delta wave: slurring slow rise of initial portion of the QRS; QRS prolongation > 110ms'),
    'aivr': ('Accelerated Idioventricular Rhythm (AIVR)',
             'Regular rhythm; Rate typically 50-120 bpm; QRS duration > 120ms … Rates < 50 bpm are consistent with a Ventricular Escape Rhythm. Rates > 110 bpm are consistent with Ventricular Tachycardia'),
    'vesc': ('Ventricular Escape Rhythm',
             'A ventricular rhythm with a rate of 20-40 bpm. QRS complexes are broad (≥ 120 ms)'),
    'hyperk': ('Hyperkalaemia ECG changes',
               'Peaked T waves; P wave widening/flattening, PR prolongation; Bradyarrhythmias …; QRS widening with bizarre QRS morphology／'
               'Tall, symmetrically peaked T waves (Example 2)'),
}
# 前の版（2026-10-05）からの変更点（依頼文に載せる。レビューの文そのものは載せない）
CHANGES = [
    '100以上・規則的「前から脚ブロック」→「前と同じ脚ブロック」。SVT＋変行伝導の色をオレンジ → 赤（100以上・規則的の3枚がすべて赤）',
    '100以上・不規則「とても速い」→「200以上・形がばらつく」（心房細動＋WPW）',
    '60〜100「WPW」→「WPW型（早期興奮）」、「なし」→「なし・または別々」（AIVR）',
    'VT の波形を、マップ①と同じ形（約140ms）から、幅の広い（約190ms）なだらかな単形性の形に（マップ③だけ）',
    '高カリウム血症の波形：QRS を約300ms → 約200ms、T波をすその狭い・頂点のとがった左右対称の形に',
    '画面の注意書きを3行に：3行め「※T波がとがる・QRSが広がるなら、どの心拍数でも高カリウム血症を疑う」を追加。24px・白、「迷ったらVT」は黄の太字',
    'カードの答えの字を 18〜21px → 22px に。そのため質問の箱を2〜3行にして細くし、カードを広げた（カードの左端もそろえた）',
    'キャプション：すぐ報告の範囲、高カリウム血症、心房細動＋脚ブロックとマップ②の色の関係、トルサードのねじれ、脚ブロック（胸の痛み）、'
    '洞徐脈／洞頻脈＋脚ブロックの行き先、ペースメーカー、薬の中毒、模式図（流れる速さ・マス目）の行を追加・言い換え',
]
COL_NAME = {b.C_RED: '赤', b.C_ORANGE: 'オレンジ', b.C_YEL: '黄', b.C_BLUE: '青', b.C_GREEN: '緑'}


# --- モデルの値 -----------------------------------------------------------------------------
_TAU = np.arange(-0.4, 0.6, 0.0005)
_P_HALF = 0.022*np.sqrt(2*np.log(15))           # p_sinus（σ 0.022秒）が 0.01mV を超える半分の幅


def qrs_span(v, hi=0.30, thr=0.05):
    """QRS の始まりと終わり（|v| > 0.05mV のところ。T波を外した形で測る）"""
    idx = np.where((_TAU >= -0.25) & (_TAU <= hi) & (np.abs(v) > thr))[0]
    return float(_TAU[idx[0]]), float(_TAU[idx[-1]])


def qrs_ms(kind, w=1.0):
    t = _TAU
    v, hi = {'V': (b.qrs_pvc(t), 0.12), 'W': (b.qrs_wide(t), 0.15), 'S': (b.qrs_paced(t), 0.12),
             'B': (v2.qrs_bbb(t, t_amp=0), 0.3), 'C': (v2.qrs_bbb(t, t_amp=0), 0.3),
             'D': (v2.qrs_wpw(t, t_amp=0), 0.3), 'Y': (v2.qrs_preex(t, w, t_amp=0), 0.3),
             'K': (v2.qrs_hyperk(t, t_amp=0), 0.3), 'U': (v2.qrs_vt_wide(t, t_amp=0), 0.3)}[kind]
    a, c = qrs_span(v, hi)
    return a, c, (c - a)*1000


def pr_ms(kind):
    """P波の始まり（0.01mV）→ QRS の始まり"""
    p_center = -{'B': v2.P_BBB, 'D': v2.P_WPW}[kind]
    a, _, _ = qrs_ms(kind)
    return (a - (p_center - _P_HALF))*1000


def rr_list(key):
    R = v2.RHYTHMS[key]
    ts = [e[0] for e in R['ev']] + [R['L']]
    return np.diff(ts)


def rate_txt(key):
    rr = rr_list(key)
    if rr.max() - rr.min() < 1e-6:
        return f'{60/rr[0]:.0f}/分（R-R {rr[0]:.3f}秒で一定）'
    return f'平均 {60/rr.mean():.0f}/分（R-R {rr.min():.2f}〜{rr.max():.2f}秒、{60/rr.max():.0f}〜{60/rr.min():.0f}/分）'


def describe(key):
    R = v2.RHYTHMS[key]
    if key == 'pace':
        a, c, w = qrs_ms('S')
        return f'スパイク（0.0022秒の細い線）のあとに幅の広いQRS（約{w:.0f}ms、II誘導で下向き）と上向きのT。P波なし。{rate_txt(key)}'
    if key == 'vt3':
        _, _, w = qrs_ms('U')
        return (f'同じ形の幅の広いQRS（約{w:.0f}ms。立ち上がりも下がりもなだらかで、とがりの少ない上→下の形）と小さい逆向きのTが、'
                f'規則正しく続く。P波なし。{rate_txt(key)}（単形性VT）')
    if key == 'svtbbb':
        _, _, w = qrs_ms('C')
        return f'脚ブロック型のQRS（約{w:.0f}ms、頂点に切れこみ、逆向きのT）が規則正しく続く。P波は見えない。{rate_txt(key)}'
    if key == 'avrtw':
        _, _, w = qrs_ms('Y')
        return f'立ち上がりがなだらかな幅の広いQRS（約{w:.0f}ms、副伝導路を通る形）が規則正しく続く。P波は見えない。{rate_txt(key)}'
    if key == 'tdp':
        return (f'幅の広い上下の揺れ（1拍ずつ上→下の2相）が切れ目なく続き、その大きさと向きが、{v2.qrs_torsade.__defaults__[0]:.1f}秒ごとに上向き⇄下向きへねじれるように入れかわる'
                f'（いちばん小さいところで最大の18%）。R-R も少し不規則。{rate_txt(key)}。QT延長の前の洞調律は描いていない（ずっと続く形）')
    if key == 'afbbb3':
        _, _, w = qrs_ms('C')
        return f'P波なし、細かい基線の揺れ（f波）。脚ブロック型のQRS（約{w:.0f}ms・どの拍も同じ形）が不規則に出る。{rate_txt(key)}'
    if key == 'afwpw':
        ws = [e[2] for e in R['ev']]
        w0, w1 = qrs_ms('Y', min(ws))[2], qrs_ms('Y', max(ws))[2]
        return (f'P波なし、f波。副伝導路を通る幅の広いQRSが、とても速く不規則に出る。QRS の幅が拍ごとに少しちがう'
                f'（約{w0:.0f}〜{w1:.0f}ms）。{rate_txt(key)}')
    if key == 'bbb':
        _, _, w = qrs_ms('B')
        return f'P波＋PR 約{pr_ms("B"):.0f}ms＋幅の広いQRS（約{w:.0f}ms、頂点に切れこみ）＋逆向きのT。{rate_txt(key)}。II誘導での形の一例（右脚・左脚の区別はつけていない）'
    if key == 'wpw':
        _, _, w = qrs_ms('D')
        return (f'P波＋PR 約{pr_ms("D"):.0f}ms（短い）＋デルタ波（なだらかな立ち上がり）から細いRへ。QRS 約{w:.0f}ms。'
                f'Tは少し逆向き。{rate_txt(key)}。デルタ波は小さいカードで見えるよう、少し大きめに描いた')
    if key == 'aivr':
        _, _, w = qrs_ms('W')
        return (f'P波なし。幅の広いQRS（約{w:.0f}ms）と逆向きのT。{rate_txt(key)}。心室補充調律と同じ形で、速さだけちがう'
                f'（答えは「なし・または別々」だが、波形はP波なしの形だけを描いた）')
    if key == 'vesc':
        _, _, w = qrs_ms('W')
        return f'P波なし。幅の広いQRS（約{w:.0f}ms）と逆向きのT。{rate_txt(key)}。マップ①と同じ波形'
    if key == 'hyperk':
        _, _, w = qrs_ms('K')
        tt = v2._tent(_TAU, 0.0, 0.034)
        base = np.ptp(_TAU[tt*0.85 > 0.05])*1000
        r_peak = float(v2.qrs_hyperk(_TAU, t_amp=0).max())
        return (f'平らで広いP波（0.05mV）、幅の広いQRS（約{w:.0f}ms、上→下）、そのあとにQRSより高い（0.85mV、R は {r_peak:.2f}mV）'
                f'左右対称で頂点のとがったT波（すその幅 約{base:.0f}ms・0.05mV のところ）。{rate_txt(key)}')
    return ''


# --- マップの中身（字下げ） -------------------------------------------------------------------
def tree_text(n, depth=0, out=None):
    out = [] if out is None else out
    ind = '　　'*depth
    ans = f"［{n['ans']}］ " if n['ans'] else ''
    if n['kind'] == 'q':
        out.append(f"{ind}{ans}{n['q'].replace(chr(10), '')}")
        for c in n['kids']:
            tree_text(c, depth + 1, out)
    else:
        out.append(f"{ind}{ans}■ {n['name']}（{COL_NAME.get(n['col'], '?')}）")
    return out


def path_answers(leaf):
    p = m.path_to(leaf)
    return ' → '.join(n['ans'] for n in p[1:])


# --- コマ ------------------------------------------------------------------------------------
def zoom_page(src, box, label):
    """カードの列を2倍にした参考ページ（等倍のコマでは小さい波形を見てもらうため）"""
    crop = src.crop(box)
    crop = crop.resize((crop.size[0]*2, crop.size[1]*2), Image.LANCZOS)
    page = b.grid().copy()
    page.alpha_composite(crop.convert('RGBA'), ((b.W - crop.size[0])//2, 260))
    b.put(page, label, 30, 800, b.YEL, cx=540, cy=200)
    return page.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    fdir = os.path.join(OUT, 'review_frames_map3')
    os.makedirs(fdir, exist_ok=True)
    pages = [('冒頭（0.3秒。1枚目のペースメーカー調律の道すじが光りはじめたところ）', m.frame(0.3))]
    for k in (1, 2, 3, 4, 6, 8, 11):
        c = m.LEAVES[k]
        pages.append((f"{k*m.SLOT + 1.0:.1f}秒：{k+1}枚目「{c['name']}」の道すじが光る", m.frame(k*m.SLOT + 1.0)))
    base = m.frame(9.0)
    x0 = int(min(c['x'] for c in m.LEAVES[1:])) - 8
    pages.append(('拡大（参考・2倍）：100以上の6枚（9.0秒のコマから）',
                  zoom_page(base, (x0, int(m.LEAVES[1]['y'] - m.CARD_H/2) - 2, 1008, int(m.LEAVES[6]['y'] + m.CARD_H/2) + 3),
                            '拡大（参考・2倍）：心拍数100以上')))
    pages.append(('拡大（参考・2倍）：60〜100・60未満の5枚（9.0秒のコマから）',
                  zoom_page(base, (x0, int(m.LEAVES[7]['y'] - m.CARD_H/2) - 2, 1008, int(m.LEAVES[11]['y'] + m.CARD_H/2) + 3),
                            '拡大（参考・2倍）：60〜100・60未満')))
    thumb = os.path.join(OUT, 'thumb_map3_v3.png')
    m.thumbnail().save(thumb)
    pages.append(('サムネイル（投稿の表紙・透かしなし）', Image.open(thumb).convert('RGB')))
    pngs, index = [], []
    for i, (name, im) in enumerate(pages):
        fp = os.path.join(fdir, f'{i+1:02d}.png')
        im.save(fp)
        pngs.append(fp)
        index.append(f'- {i+1}ページ：{name}')
    import img2pdf
    fpdf = os.path.join(OUT, 'review_map3_frames.pdf')
    with open(fpdf, 'wb') as f:
        f.write(img2pdf.convert(pngs))
    print(fpdf, len(pngs), 'ページ（等倍）')

    rows = '\n'.join(f"| {c['i']+1} | {c['name']}（{COL_NAME.get(c['col'], '?')}） | {path_answers(c)} | {describe(c['key'])} | {BASIS[c['key']][0]} |"
                     for c in m.LEAVES)
    basis = '\n'.join(f"- {c['name']}（{BASIS[c['key']][0]}）：{BASIS[c['key']][1]}" for c in m.LEAVES)
    cap = open(os.path.join(HERE, 'caption_map3.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- LITFL {k}：{u}' for k, u in SRC.items())
    sizes = [m.fit_group(c, int(round(c['w'])) - 26) for c in m.LEAVES]
    ans_px = '・'.join(str(v) for v in sorted({sz[0] for sz in sizes}))
    nm = sorted({sz[1] for sz in sizes})
    name_px = f'{nm[0]}〜{nm[-1]}' if len(nm) > 1 else str(nm[0])
    vt_ms, svt_ms, avrt_ms = qrs_ms('U')[2], qrs_ms('C')[2], qrs_ms('Y')[2]
    changes = '\n'.join(f'- {x}' for x in CHANGES)
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。マップの中身・波形の描き方・キャプションは、この依頼文の中にあります。

## 作品の概要
- 「見分けマップ③　幅の広いQRS」。見分けマップ①（規則的な波形）・②（不規則・QRSなし）の続き。縦 1080×1920・60fps・ナレーションなし（モニター音だけ）・{m.DUR:.0f}秒でループ
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）。保存・シェアされる「1枚で見返せる図」をねらう
- 作り：左の質問の箱から直角の線で右へ枝分かれし、枝の先に波形カード（答え＋名前＋流れる小さなモニター）。1コマ目から12枚すべての波形が流れ、{m.SLOT:.0f}秒ごとに1枚ずつ、根もとの質問からそのカードまでの道すじが光る
- マップは、モニター（II誘導）で見る入口の一例。画面の下に注意書きを3行（24px・白。「迷ったらVT」は黄の太字）
- 名前の色：赤＝危険・すぐ対応、オレンジ＝頻脈性の不整脈、黄＝注意、青＝ペースメーカーなど（マップ①②と同じ決まり）。心拍数100以上で規則的な3枚は、すべて赤
- 字の大きさ：カードの答え {ans_px}px、名前 {name_px}px、質問の箱 25px、注意書き 24px
- 波形はモデルで作った模式図。小さなカードに収めるため、流れる速さは実際より詰めている（{m.SPEED:.0f}px/秒）。主な出典は LITFL ECG Library（下に一覧）。ほかの投稿の図を写したものではない（構成・言葉は独自）

## 前の版（2026-10-05）からの変更点
{changes}

## PDFのページ
{chr(10).join(index)}

## マップの中身（［ ］は前の質問への答え、■は名前、（ ）は名前の色）
```
{chr(10).join(tree_text(m.CFG['tree']))}
```

画面の注意書き（3行）：{' ／ '.join(m.CFG['notes'])}

## 各カードの波形（モデルの値から計算）と根拠
| No. | 名前（色） | たどる答え | 描き方（モデルの値） | 根拠（LITFL） |
|---|---|---|---|---|
{rows}

QRS幅は、T波を外したモデルの形で「|電位| > 0.05mV」の始まり〜終わり。PR は P波の始まり（0.01mV）→ QRS の始まり。

### 根拠にした LITFL の文
{basis}

## キャプション
```
{cap}
```

## とくに見てほしい点
1. 分け方の順番（スパイク → 心拍数 100以上／60〜100／60未満 → リズム・P波・T波）は、看護師の入口として妥当か
2. 100以上・規則的の3枚（すべて赤）：「迷ったらこれ＝VT」「前と同じ脚ブロック＝SVT＋変行伝導」「前からWPW＝逆方向性AVRT」。
   「前と同じ」「前から」は、以前の12誘導心電図と医師が見比べる想定（キャプションに、確かめられないときはVTとして対応、と書いた）。
   カードの幅に入る長さの都合で「前と同じ形の脚ブロック」を「前と同じ脚ブロック」にした。意味が伝わるか
3. 100以上・不規則の3枚：「ねじれる＝多形性VT・トルサード（赤）」「同じ形＝心房細動＋脚ブロック（オレンジ）」「200以上・形がばらつく＝心房細動＋WPW（赤）」。
   心房細動＋脚ブロックだけオレンジにしたこと（マップ②では「心房細動＋脚ブロック・多形性VT」を1枚の赤にしている。キャプションで、新しく出たときはマップ②と同じくすぐ報告、とつないだ）
4. 60〜100：「あり・PRふつう＝脚ブロック」「あり・PR短い・デルタ波＝WPW型（早期興奮）」「なし・または別々＝AIVR（黄）」の言葉と色
5. 60未満：「P波なし＝心室補充調律」「P波平ら・T波とがる＝高カリウム血症」。高カリウム血症は60未満の枝に置き、
   ほかの心拍数のことは画面の注意書き3行め「T波がとがる・QRSが広がるなら、どの心拍数でも高カリウム血症を疑う」で補った。これで足りるか
6. 波形：VT（約{vt_ms:.0f}ms）・SVT＋変行伝導（約{svt_ms:.0f}ms）・逆方向性AVRT（約{avrt_ms:.0f}ms）の幅の関係、高カリウム血症のT波の形、WPW型のデルタ波は、代表の形として妥当か（拡大ページ 9・10）
7. 脚ブロックの波形を「切れこみのある幅の広いR＋逆向きのT」にしたこと。画面の「右脚・左脚の区別は12誘導で」で足りるか
8. キャプションの⚠️（すぐ報告の範囲・高カリウム血症・ペースメーカー・薬の中毒・洞徐脈／洞頻脈＋脚ブロックの行き先など）に、誤りや足りないものはないか。長すぎないか
9. スマホの大きさで、カードの字（答え {ans_px}px・名前 {name_px}px）と注意書き（24px）が読めるか。注意書きが投稿の説明文の表示と重ならないか（y 約1510〜1597）

## 返してほしい形
- カードごと（No.1〜12）・質問ごとに：判定（OK／要修正／推奨）・理由・直し方（言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください

## 出典
{srcs}
'''
    with open(os.path.join(HERE, 'review_request_map3.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request_map3.md'))


if __name__ == '__main__':
    main()
