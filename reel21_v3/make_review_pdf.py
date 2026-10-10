"""第21弾v3 致死性不整脈 見るのは5か所 ― 専門医レビュー用の資料。

- out/review_frames/*.png：映像のコマを等倍（1080×1920）で（冒頭・各場面の説明・各パターン（次の対応が出そろったところ）・最後・サムネイル）
- release/review_reel21v3_frames.pdf：上のコマを1ページずつ（img2pdf・無圧縮）
- review_request.md：依頼文（目的・構成・見る場所とパターンと次の対応の表・根拠・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel21v3.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。
依頼文には、AI専門医（Claude）のレビュー結果は入れない（Gemini でのダブルチェックにもこのまま使うため）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import make_reel21v3 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REL = os.path.join(HERE, 'release')

L = 'https://litfl.com/'
SRC = {
    'LITFL AV Block: 2nd degree, Mobitz II': L + 'av-block-2nd-degree-mobitz-ii-hay-block/',
    'LITFL AV Block: 3rd degree (Complete Heart Block)': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL Premature Ventricular Complex（R on T・連発）': L + 'premature-ventricular-complex-pvc-ecg-library/',
    'LITFL Ventricular Tachycardia – Monomorphic': L + 'ventricular-tachycardia-monomorphic-ecg-library/',
    'LITFL CCC Ventricular Tachycardia': L + 'ventricular-tachycardia/',
    'LITFL Polymorphic VT and Torsades de Pointes': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
    'LITFL Ventricular Fibrillation (VF)': L + 'ventricular-fibrillation-vf-ecg-library/',
    'LITFL CCC Pulseless Electrical Activity': L + 'pulseless-electrical-activity/',
    'LITFL CCC Transcutaneous Pacing': L + 'transcutaneous-pacing/',
    '（LITFL以外）AHA 2025 Part 9: Adult Advanced Life Support（Wigginton JG, et al. Circulation 2025;152(suppl 2):S538–S577）':
        'https://www.ahajournals.org/doi/10.1161/CIR.0000000000001376',
    '（LITFL以外）ERC Guidelines 2025 Adult Advanced Life Support（Soar J, et al. Resuscitation 2025;215 Suppl 1:110769）':
        'https://cprguidelines.eu/',
    '（LITFL以外）JRC蘇生ガイドライン2020 第2章 成人の二次救命処置（日本蘇生協議会）':
        'https://www.jrc-cpr.org/wp-content/uploads/2022/07/JRC_0047-0150_ALS.pdf',
    '（LITFL以外）2022 ESC Guidelines for ventricular arrhythmias and the prevention of sudden cardiac death（Zeppenfeld K, et al. Eur Heart J 2022;43:3997–4126）':
        'https://academic.oup.com/eurheartj/article/43/40/3997/6675633',
    '（LITFL以外）Drew BJ, et al. Prevention of Torsade de Pointes in Hospital Settings: AHA/ACCF Scientific Statement（Circulation 2010;121:1047–1060）':
        'https://pmc.ncbi.nlm.nih.gov/articles/PMC3056123/',
}

# パターンごとの根拠（docs/reel21_v2_evidence.md の要点。v2 の依頼文と同じ）
EVID = {
    'モビッツII': 'ERC 2025 Fig.9（徐脈：Mobitz II は「心静止の危険」→ 経皮ペーシングなどへ）、AHA 2025 Figure 8（不安定の目安：低血圧・意識の変化・ショック徴候・胸痛・急性心不全）、LITFL Mobitz II（急に悪くなりうる・一時ペーシングの備え）',
    '完全房室ブロック': 'ERC 2025 Fig.9（幅の広いQRSの完全房室ブロックは「心静止の危険」）、AHA 2025 Figure 8、LITFL 3rd degree AV block（心室停止・突然死の危険、一時ペーシングの備え）',
    'ショートラン': 'ESC 2022（NSVT＝3拍以上・30秒未満。Table 3：12誘導、Table 8：電解質など戻せる原因を調べる）、LITFL PVC（3〜30連・100/分超＝非持続性VT。原因に低K・低Mg）',
    '単形性VT': 'AHA 2025 Part 9（不安定な幅広QRS頻拍は同期電気ショック。不安定の目安 Figure 6。心停止 Figure 2）、ERC 2025（同期電気ショックには鎮静＝医師の処置）、LITFL VT',
    '多形性VT': 'AHA 2025 Part 9（持続する多形性VTは、すぐ非同期の電気ショック。COR 1。脈があっても電気的・血行動態的に不安定とみなす）、LITFL PVT and TdP（原因は虚血が多い）',
    'トルサード': 'AHA 2025 Part 9（自然に止まってくり返しやすい。Mg は COR 2b、とくに低Kを直す）、ESC 2022 Table 9（Mg静注＋K補充、Mg値が正常でも有効）、ERC 2025 Table 6、Drew 2010（止まらない・VFになるならすぐ電気ショック）、LITFL',
    'R on T': 'LITFL PVC・PVT and TdP（QT延長でのR on Tはトルサードの引き金）、LITFL VF（VF の前に R on T が見られることがある）、Drew 2010（QT延長＋前ぶれの波形なら、薬・電解質の見直しと除細動器をすぐ使えるように）、ESC 2022 Table 3・8',
    '粗いVF': 'ERC 2025（院内：心停止にすぐ気づき、人を呼び、CPRを始め、電気ショック。反応・正常な呼吸がない、または迷えば心停止として動く）、AHA 2025 Figure 2、LITFL VF',
    '細かいVF': 'ERC 2025 Adult ALS（2015年版の「心静止か細かいVFか迷えばCPRを続ける」を改め、細かいVFでもVFと判断したら電気ショック）、LITFL VF（時間とともに粗い→細かい）',
    '心静止': 'AHA 2025 Figure 2・ERC 2025 Fig.2・JRC 2020（ショックの対象外、すぐCPR）。「電極外れ・感度の確認」は最新ガイドラインの本文には見つからず、CPRを遅らせない「並行して」の実務の確認として置いた',
    'PEA1': 'AHA 2025 Figure 2・ERC 2025 Fig.2（ショックの対象外、すぐCPR、戻せる原因（4H4T）を探す）、ERC 2025 Fig.3（反応・正常な呼吸がない、またははっきりしなければ心停止として動く）、LITFL CCC PEA、JRC 2020',
    'PEA2': '同上。LITFL CCC PEA（幅の広いQRSのPEAは代謝（高Kなど）・虚血が多い）',
}


def describe(pat):
    k = pat['key']
    return {
        'モビッツII': f'洞調律 {60/m.RR:.0f}/分、PR {m.PR:.2f}秒で一定。4つめのP波のあとQRSが抜ける（4:3）。抜けたところのR-Rは 1.60秒（P-Pの2倍）。QRSは幅の狭い形',
        '完全房室ブロック': f'P波 {60/0.68:.0f}/分と、幅の広い心室補充調律（QRS 約{m._qrs_ms(m.qrs_escape):.0f}ms）{60/1.7:.0f}/分が、関係なく別々に出る',
        'ショートラン': f'洞調律 {60/m.RR:.0f}/分のあと、PVC（QRS 約{m._qrs_ms(m.qrs_pvc):.0f}ms）が3つ（間隔 0.38秒＝{60/0.38:.0f}/分）続いて、洞調律に戻る',
        '単形性VT': f'幅の広いQRS（約{m._qrs_ms(m.qrs_vt_rs, 0.3):.0f}ms）が {60/0.32:.0f}/分で規則正しく続く',
        '多形性VT': f'幅の広いQRSが約{60*m.POLY_N/m.POLY_L:.0f}/分。大きさ（0.45〜1.15mV）と向きが1拍ごとに変わる',
        'トルサード': f'QT延長の洞調律（60/分、QT 約0.56秒）→ T波の上から始まり、約{m.TDP_F*60:.0f}/分で大きさがねじれるように変わる（ねじれの周期 1.25秒）→ {m.TDP_B-m.TDP_A:.1f}秒で自然に止まる（5.6秒ごとにくり返す）',
        'R on T': f'洞調律 {60/m.RR:.0f}/分。PVC（QRS 約{m._qrs_ms(m.qrs_pvc):.0f}ms）が直前のRから {m.RONT_C:.2f}秒（T波の頂点 0.27秒を過ぎた下り。乗られたT波の山が見える）に乗る。1回だけで洞調律に戻る（3.2秒ごとにくり返す）',
        '粗いVF': '3〜9Hz（180〜540/分）の不規則で大きな揺れ（約±0.4mV）。P・QRS・Tは見えない',
        '細かいVF': '3.5〜10Hz の不規則な小さな揺れ（約±0.08mV）',
        '心静止': 'ほぼまっすぐの線（±0.01mV のごくわずかな揺れ）',
        'PEA1': f'ふつうの形のP・QRS・T（{60/0.75:.0f}/分）。脈はない設定',
        'PEA2': f'幅の広いQRS（約{m._qrs_ms(m.qrs_escape):.0f}ms）が {60/2.0:.0f}/分。脈はない設定',
    }[k]


def key_time(i):
    """パターン i の次の対応がすべて出ていて、特徴の部分（色の範囲）がなるべく画面の真ん中にあるときの t。"""
    pat = m.PATTERNS[i]
    b = m.PAT_BLOCK[i]
    lo = b['start'] + m.TEXT_IN + m.TEXT_FADE_IN + 0.05
    hi = b['end'] - m.TEXT_FADE_OUT - 0.05
    if pat['hl'] is m.ALL:
        return min(hi, lo + 1.2)
    a0, a1 = pat['hl'][0]
    c = (a0 + a1) / 2
    best, best_d = lo, 1e9
    for t in np.arange(lo, hi, 1/60):
        rel = float(m.rel_at(i, t, m.XC))
        d = abs(((rel - c + pat['L']/2) % pat['L']) - pat['L']/2)
        if d < best_d:
            best, best_d = t, d
    return round(best*60)/60


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(REL, exist_ok=True)
    frames = [('冒頭（「致死性不整脈」「見るのは5か所」。下の波形が、そのまま場面①の1本目になる）', 1.0)]
    for s, pl in enumerate(m.PLACES):
        ob = m.OV_BLOCK[s]
        frames.append((f"{pl['no']} {pl['name']}：場所の説明（その場所の波形を全部同じ扱いで並べる）", round((ob['end'] - 0.3)*60)/60))
        for i in m.SCENE_PATS[s]:
            p = m.PATTERNS[i]
            frames.append((f"{pl['no']} {pl['name']}：{p['name']}（紹介中。次の対応が出そろったところ）", key_time(i)))
    t_end = m.END_B['save0'] + 0.8
    frames.append(('最後：5か所（場所の色・小さな波形）・問いかけ・保存', t_end))
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        if f.endswith('.png'):
            os.remove(os.path.join(fdir, f))
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ（{t:.1f}秒）：{name}')
    thumb = os.path.join(fdir, f'{len(pngs)+1:02d}.png')
    m.thumbnail().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙。透かしなし）')
    fpdf = os.path.join(REL, 'review_reel21v3_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    # 依頼文
    def nname(n):
        if n in ('冒頭', 'まとめ', '保存'):
            return n
        if n.startswith('場所'):
            pl = m.PLACES[int(n[2:])]
            return f"{pl['no']} {pl['name']}（場所の説明）"
        return '　' + next(p['name'] for p in m.PATTERNS if p['key'] == n)
    narr = '\n'.join(f"- {nname(n)}：{m.NARR[n]}" for n in m.NARR_ORDER)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    places = '\n'.join(f"- {p['no']} {p['name']}（画面の1行：「{p['ov']}」）：" + '・'.join(m.PATTERNS[i]['name'] for i in m.SCENE_PATS[j])
                       for j, p in enumerate(m.PLACES))
    rows = '\n'.join(
        f"| {p['pno']} {m.PLACES[p['place']]['name']} | {p['name']} | {p['act']} | "
        + ' ／ '.join(('　' if c else '') + s for s, c in p['lines'])
        + f" | {EVID[p['key']]} |" for p in m.PATTERNS)
    draw = '\n'.join(f"| {p['name']} | {describe(p)} |" for p in m.PATTERNS)
    tl = '\n'.join(f"| {b['start']:.1f}–{b['end']:.1f} | {name.strip()} |" for name, b in m.timing_table())
    txt = f'''あなたは循環器専門医（蘇生・不整脈）として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 目的
- 第21弾「致死性不整脈」の作り直し（v3）。12パターンを「特徴が出る場所（見る場所）」で5つに分け、見つけたあとに看護師がとる「次の対応」を付けた
- 見る人：病棟でモニター心電図を見る看護師・看護学生（急変の第一発見者になりうる）。**病院内**を想定
- ねらい：波形の名前だけでなく「どこを見れば気づけるか」と「気づいたら何をするか」を、短い時間で覚えてもらう
- 次の対応の文言は、AHA 2025・ERC 2025・JRC 2020・LITFL・ESC 2022・Drew 2010 を読んで決めた（各行の根拠は下の表）。薬の名前・K/Mg の目標値は出さない（薬・同期電気ショック・ペーシングを決めるのは医師）

## 作品の概要（v3 の構成）
- 縦 1080×1920・60fps。ナレーションは**まだ録音していない**（下の台本は下書き。秒数は字数からの見積もり）
- 冒頭：「致死性不整脈」「見るのは5か所」。下で波形が流れ、そのまま場面①の1本目になる
- 5つの場面（見る場所ごと）：上に場所の名前（場所の色）と「何を見るか」の1行。その下に、その場所の波形だけを縦に並べる（名前のラベル＋実際の速さで流れる波形）
  - はじめ（場所の説明）は、その場所の波形を全部同じ扱いで並べる
  - そのあと1つずつ紹介：いまの波形を大きく（10mm/mV）、特徴の部分を場所の色にする。ほかの波形は小さく薄くする。画面の下に「→ 次の対応」
  - 場面の切りかえは、横に押し出す（前の場面が左へ、次の場面が右から）
- 最後：5か所（場所の色・小さな波形）→「どこを見落としやすい？コメントで教えてね」→「保存して見返してね」→ 冒頭へ戻る（ループ）
- 色は見る場所ごと：① 黄 ② 橙 ③ 紫 ④ 赤 ⑤ 青
- 波形の部品にキャラクター（顔と手）を重ねた：Pくん（P波）・QRSくん（R）・Tちゃん（T波）・PVCくん。紹介中の大きな波形の上だけで、波形と一緒に流れる。
  例：モビッツII型は、伝わる拍で P と QRS が握手し、抜けたところで Pくんの手が空ぶり（「あっ」）、QRSくんが基線の下からのぞいて（「あらっ」）落ちる。
  R on T は PVCくんが Tちゃんの山に乗り（「ひゃっ」）、小さな火花と VF のきざし。④⑤（心停止）はまじめな顔だけ、心静止の線には顔を描かない。
  小物：定規（QRSの幅）、分かれ道の看板（脈あり／脈なし）、くり返しの矢印、虫めがね（「どこ？」）、稲妻、電極のプラグ（「外れ？」）、CPR の手、動かないハートと脈をみる手（「？」）
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒、1mm＝14px、背景のマス目も同じ）**。紹介中の波形は 10mm/mV（小さくした波形は 3mm/mV、場所の説明では 4〜10mm/mV）
- 画面とキャプションに「数値はこの波形での一例」と明記している

## 見る場所（5か所）と12パターン
{places}

## 見る場所・パターン・次の対応（画面の文言）と根拠
「画面の行」は、スマホの幅に収めるための改行（「　」で始まるものは、矢印なしの続きの行）。文言そのものは変えていない。

| 見る場所 | パターン | 次の対応（決めた文言） | 画面の行 | 根拠 |
|---|---|---|---|---|
{rows}

## 各パターンの描き方（モデルの値）
| パターン | 描き方 |
|---|---|
{draw}

## 秒数（仮。録音前の見積もり）
| 秒 | 場面 |
|---|---|
{tl}

## PDFのページ
{chr(10).join(index)}

## ナレーション（台本の下書き。数字と次の対応は画面にまかせ、声では全部は読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. **分け方と「何を見るか」の1行**：12パターンを5か所に割り当てたことと、各場所の1行（① Pのあとに、QRSが続いているか ② 幅が広いか、形がそろっているか ③ T波に、PVCが乗っていないか ④ QRSが見えているか ⑤ 波形がふつうでも、脈を確かめる）は正しいか。誤解を招くところはないか（たとえば ① の1行が完全房室ブロックに合っているか、④ の1行が心静止に合っているか）
2. **台本の各文**：とくに「R on T。VFのきっかけになる。」「多形性VT。形が1拍ごとに変わる。」「トルサード。ねじれるように変わり、止まっても、くり返す。」「遅く幅広いQRSでも、脈がなければPEA。」が医学的に正しく、言い過ぎ・足りないところがないか
3. **次の対応の正確さ**：各行が、病棟の看護師がまずとる動きとして正しく、足りないもの・言い過ぎがないか
4. **細かいVF**：「CPR＋電気ショック（細かくてもVFならショック）」と台本「小さな揺れでも、VFならショック。」が、ERC 2025 の改訂と合っているか。AHA 2025・JRC と食いちがって誤解を招くところはないか
5. **単形性VT・多形性VT の脈あり／脈なし**：AHA 2025（持続する多形性VTは脈があっても非同期の電気ショック）と合っているか
6. **心静止・PEA**：「反応がなければ人を呼び、すぐCPR（ショックはしない）。並行して電極外れ・感度を確認」「脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認」に問題はないか
7. **看護師だけで決めるように読めるところがないか**：薬・同期電気ショック・ペーシングは医師の判断（キャプションに明記）。「ペーシングに備えてパッド装着」「パッド装着」は準備の意味で書いた
8. **波形の描き方**：紹介中の波形で、特徴の部分（モビッツII型の抜けたP波、ショートランの3連、トルサードのねじれ、R on T のPVC）が、名前を言っているあいだ画面に見えているか。トルサードは紹介が始まってから少しあと（約{m.PATTERNS[5]['enter']:.1f}秒）に始まるようにした
9. **キャラクター**：顔・手・小物が、特徴の部分（抜けたQRS、R on T の接点、トルサードのねじれなど）を隠していないか。表情や動き（とくに ④⑤ の心停止の場面）が、誤解や不謹慎な印象を与えないか
10. **読みやすさ**：スマホの大きさで、場所の名前・「何を見るか」の1行・次の対応（字の大きさ 32px、最大3行）・小さくした波形の名前（26px）が読めるか。PDF のコマで読み違えそうなところはないか

## 返してほしい形
- 場面ごと・パターンごと（またはページごと）と、上の「とくに見てほしい点」ごとに：判定（OK／要修正／推奨）・理由・直し方（言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください
- ナレーションの台本を変えたほうがよいものは、その文を書いてください（このあと録音します）

## 出典
{srcs}
'''
    with open(os.path.join(HERE, 'review_request.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request.md'))

    lines = ['第21弾v3 致死性不整脈 見るのは5か所 ― 画面の文字', '',
             f'[冒頭 0〜{m.OV_BLOCK[0]["start"]:.1f}秒] {m.TITLE} ／ 見るのは5か所（「5」は黄色・大きく） ／ ① ② ③ ④ ⑤（場所の色）']
    for s, pl in enumerate(m.PLACES):
        ob = m.OV_BLOCK[s]
        lines.append(f"[{ob['start']:5.1f}秒〜] {pl['no']} {pl['name']}（場所の色） ／ {pl['ov']} ／ 波形のラベル："
                     + '・'.join(m.PATTERNS[i]['name'] for i in m.SCENE_PATS[s]))
        for i in m.SCENE_PATS[s]:
            b = m.PAT_BLOCK[i]
            p = m.PATTERNS[i]
            lines.append(f"  [{b['start']:5.1f}〜{b['end']:5.1f}秒] {p['name']}（大きく） ／ " + ' ／ '.join(x for x, _ in p['lines']))
    lines += [f"[{m.END_B['start']:5.1f}秒〜] 見るのは5か所 ／ " + ' ／ '.join(f"{p['no']} {p['name']}" for p in m.PLACES)
              + f' ／ {m.END_ASK} ／ {m.END_SAVE}（緑）',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', f'[右下] {m.WATERMARK}（透かし）']
    p = os.path.join(OUT, 'screen_text_reel21v3.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(p)


if __name__ == '__main__':
    main()
