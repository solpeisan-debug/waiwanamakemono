"""第21弾v2 致死性不整脈 見るのは5か所 ― 専門医レビュー用の資料。

- out/review_frames/*.png：映像のコマを等倍（1080×1920）で（冒頭・12パターン・最後・サムネイル）
- release/review_reel21v2_frames.pdf：上のコマを1ページずつ（img2pdf・無圧縮）
- review_request.md：依頼文（目的・見る場所とパターンと次の対応の表・根拠・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel21v2.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。
依頼文には、AI専門医（Claude）のレビュー結果は入れない（Gemini でのダブルチェックにもこのまま使うため）。

使い方:
    python3 make_review_pdf.py
"""
import os

from PIL import Image

import align_vo as vo
import make_reel21v2 as m

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

# パターンごとの根拠（docs/reel21_v2_evidence.md の要点）
EVID = {
    'モビッツII': 'ERC 2025 Fig.9（徐脈：Mobitz II は「心静止の危険」→ 経皮ペーシングなどへ）、AHA 2025 Figure 8（不安定の目安：低血圧・意識の変化・ショック徴候・胸痛・急性心不全）、LITFL Mobitz II（急に悪くなりうる・一時ペーシングの備え）',
    '完全房室ブロック': 'ERC 2025 Fig.9（幅の広いQRSの完全房室ブロックは「心静止の危険」）、AHA 2025 Figure 8、LITFL 3rd degree AV block（心室停止・突然死の危険、一時ペーシングの備え）',
    'ショートラン': 'ESC 2022（NSVT＝3拍以上・30秒未満。Table 3：12誘導、Table 8：電解質など戻せる原因を調べる）、LITFL PVC（3〜30連・100/分超＝非持続性VT。原因に低K・低Mg）',
    '単形性VT': 'AHA 2025 Part 9（不安定な幅広QRS頻拍は同期電気ショック。不安定の目安 Figure 6。心停止 Figure 2）、ERC 2025（同期電気ショックには鎮静＝医師の処置）、LITFL VT',
    '多形性VT': 'AHA 2025 Part 9（持続する多形性VTは、すぐ非同期の電気ショック。COR 1。脈があっても電気的・血行動態的に不安定とみなす）、LITFL PVT and TdP（原因は虚血が多い）',
    'トルサード': 'AHA 2025 Part 9（自然に止まってくり返しやすい。Mg は COR 2b、とくに低Kを直す）、ESC 2022 Table 9（Mg静注＋K補充、Mg値が正常でも有効）、ERC 2025 Table 6、Drew 2010（止まらない・VFになるならすぐ電気ショック）、LITFL',
    'R on T': 'LITFL PVC・PVT and TdP（QT延長でのR on Tはトルサードの引き金）、Drew 2010（QT延長＋前ぶれの波形なら、薬・電解質の見直しと除細動器をすぐ使えるように）、ESC 2022 Table 3・8',
    '粗いVF': 'ERC 2025（院内：心停止にすぐ気づき、人を呼び、CPRを始め、電気ショック。反応・正常な呼吸がない、または迷えば心停止として動く）、AHA 2025 Figure 2、LITFL VF',
    '細かいVF': 'ERC 2025 Adult ALS（2015年版の「心静止か細かいVFか迷えばCPRを続ける」を改め、細かいVFでもVFと判断したら電気ショック。迷うときもショック／5秒で判断できなければ除細動器の自動解析にまかせる）、LITFL VF（時間とともに粗い→細かい）',
    '心静止': 'AHA 2025 Figure 2・ERC 2025 Fig.2・JRC 2020（ショックの対象外、すぐCPR）。「電極外れ・感度の確認」は最新ガイドラインの本文には見つからず、CPRを遅らせない「並行して」の実務の確認として置いた',
    'PEA1': 'AHA 2025 Figure 2・ERC 2025 Fig.2（ショックの対象外、すぐCPR、戻せる原因（4H4T）を探す）、ERC 2025 Fig.3（反応・正常な呼吸がない、またははっきりしなければ心停止として動く）、LITFL CCC PEA、JRC 2020',
    'PEA2': '同上。LITFL CCC PEA（幅の広いQRSのPEAは代謝（高Kなど）・虚血が多い）',
}


def describe(pat):
    """パターンの描き方（モデルの値から）。"""
    k = pat['key']
    return {
        'モビッツII': f'洞調律 {60/m.RR:.0f}/分、PR {m.PR:.2f}秒で一定。4つめのP波のあとQRSが抜ける（4:3）。抜けたところのR-Rは 1.60秒（P-Pの2倍）。QRSは幅の狭い形',
        '完全房室ブロック': f'P波 {60/0.68:.0f}/分と、幅の広い心室補充調律（QRS 約{m._qrs_ms(m.qrs_escape):.0f}ms）{60/1.7:.0f}/分が、関係なく別々に出る',
        'ショートラン': f'洞調律 {60/m.RR:.0f}/分のあと、PVC（QRS 約{m._qrs_ms(m.qrs_pvc):.0f}ms）が3つ（間隔 0.38秒＝{60/0.38:.0f}/分）続いて、洞調律に戻る',
        '単形性VT': f'幅の広いQRS（約{m._qrs_ms(m.qrs_pvc):.0f}ms）が {60/0.32:.0f}/分で規則正しく続く',
        '多形性VT': f'幅の広いQRSが約{60*m.POLY_N/m.POLY_L:.0f}/分。大きさ（0.45〜1.15mV）と向きが1拍ごとに変わる',
        'トルサード': f'QT延長の洞調律（60/分、QT 約0.56秒）→ T波の上から始まり、約{m.TDP_F*60:.0f}/分で大きさがねじれるように変わる（ねじれの周期 1.25秒）→ {m.TDP_B-m.TDP_A:.1f}秒で自然に止まる',
        'R on T': f'洞調律 {60/m.RR:.0f}/分。PVC（QRS 約{m._qrs_ms(m.qrs_pvc):.0f}ms）が直前のRから 0.27秒（T波の頂点）に乗る。1回だけで洞調律に戻る（3.2秒ごとにくり返す）。区間の終わりでは、2つめのR on T のあと 0.53秒で粗いVFへつながる',
        '粗いVF': '3〜9Hz（180〜540/分）の不規則で大きな揺れ（約±0.4mV）。P・QRS・Tは見えない',
        '細かいVF': '3.5〜10Hz の不規則な小さな揺れ（約±0.08mV）',
        '心静止': 'ほぼまっすぐの線（±0.01mV のごくわずかな揺れ）',
        'PEA1': f'ふつうの形のP・QRS・T（{60/0.75:.0f}/分）。脈はない設定',
        'PEA2': f'幅の広いQRS（約{m._qrs_ms(m.qrs_escape):.0f}ms）が {60/2.0:.0f}/分。脈はない設定',
    }[k]


def key_time(i):
    """パターン i の見る場所・名前・次の対応がすべて出ていて、中部の帯がそのパターンだけのときの t。
    区間の終わりの少し前（右端が区間の終わりの 0.7秒手前）。トルサードはねじれ全体、R on T は1つめのR on T が見える位置まで戻す。"""
    a, b = m.WINDOWS[i]
    back = {'トルサード': 0.95, 'R on T': 1.2}.get(m.PATTERNS[i]['key'], 0.35)
    return b - back


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(REL, exist_ok=True)
    hook_t = m.HOOK_T0 + 2*m.HOOK_STEP + 0.25          # 冒頭の変形：③ T波の上（R on T）が出ているところ
    end_t = m.T_END + 5.0                               # 最後：5か所の一覧・問いかけ・保存が出そろったところ
    frames = [('冒頭のフック（止めた波形を、5か所の代表に変形しているところ。いまは ③ T波の上／R on T）', hook_t)] \
        + [(f"{p['pno']} {p['name']}（見る場所{p['pno']} {m.PLACES[p['place']]['name']}）", key_time(i))
           for i, p in enumerate(m.PATTERNS)] \
        + [('最後：12個の一覧と、5か所のまとめ・問いかけ・保存', end_t)]
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
    fpdf = os.path.join(REL, 'review_reel21v2_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    # 依頼文
    narr = '\n'.join(f"- {n if n in ('冒頭', 'まとめ', '保存') else next(p['name'] for p in m.PATTERNS if p['key'] == n)}：{vo.TEXT[n]}"
                     for n in vo.ORDER)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    places = '\n'.join(f"- {p['no']} {p['name']}：" + '・'.join(q['name'] for q in m.PATTERNS if q['place'] == j)
                       for j, p in enumerate(m.PLACES))
    rows = '\n'.join(
        f"| {p['pno']} {m.PLACES[p['place']]['name']} | {p['name']} | {p['act']} | "
        + ' ／ '.join(('　' if c else '') + s for s, c in p['lines'])
        + f" | {EVID[p['key']]} |" for p in m.PATTERNS)
    draw = '\n'.join(f"| {p['name']} | {describe(p)} |" for p in m.PATTERNS)
    txt = f'''あなたは循環器専門医（蘇生・不整脈）として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 目的
- 第21弾「致死性不整脈」の作り直し（v2）。12パターンを「特徴が出る場所（見る場所）」で5つに分け、見つけたあとに看護師がとる「次の対応」を1つずつ付けた
- 見る人：病棟でモニター心電図を見る看護師・看護学生（急変の第一発見者になりうる）。**病院内**を想定
- ねらい：波形の名前だけでなく「どこを見れば気づけるか」と「気づいたら何をするか」を、短い時間で覚えてもらう
- 次の対応の文言は、AHA 2025・ERC 2025・JRC 2020・LITFL・ESC 2022・Drew 2010 を読んで決めた（各行の根拠は下の表）。薬の名前・K/Mg の目標値は出さない（薬・同期電気ショック・ペーシングを決めるのは医師）

## 作品の概要
- 縦 1080×1920・60fps・ナレーション入り（**録音前**。下の台本で録る。秒数は見積もりの仮の値）
- 第21弾と同じ作り：冒頭で波形を止めて、5か所の代表に素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に5か所のまとめ
- 紹介中の画面：見る場所（小さく、場所の色）→ パターンの名前（大きく、場所の色）→ 次の対応（→ …、最大3行）→ 波形
- 色は見る場所ごと：① 黄 ② 橙 ③ 紫 ④ 赤 ⑤ 青（電気ショックの種類による色分けはやめた）
- 前の版にあった、ひとこと・色の文字（すぐに医師へ知らせる旨の黄色い表示・「→ 脈なしならショック」など）は外し、決めた文言の「次の対応」に置きかえた
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒、1mm＝14px、背景のマス目も同じ）**
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

## PDFのページ
{chr(10).join(index)}

## ナレーション（録音前の台本。1パターン1文。数字と次の対応は画面にまかせ、声では全部は読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. **分け方**：12パターンを5か所（① PとQRSのつながり ② QRSの幅と形 ③ T波の上 ④ QRSがない ⑤ 波形では分からない）に割り当てたことは正しいか。とくに、トルサードを②（QRSの幅と形）、R on T を③（T波の上）として1つで立てたこと、心静止を④（QRSがない）、PEA を⑤（波形では分からない）にしたことに、誤解を招くところはないか
2. **次の対応の正確さ**：各行が、病棟の看護師がまずとる動きとして正しく、足りないもの・言い過ぎがないか（徐脈の「意識・血圧・胸痛・息苦しさ等確認。要すればペーシングのパッド着用」、ショートランの「症状を見て、12誘導。QT、K・Mgなどを確認」、R on T の「除細動器を近くに」など）
3. **細かいVF**：「CPR＋電気ショック（細かくてもVFならショック）」と台本「小さな揺れでも、VFならショック。」が、ERC 2025 の改訂（細かいVFでも、VFと判断したら電気ショック。迷うときもショック）と合っているか。AHA 2025・JRC と食いちがって誤解を招くところはないか
4. **単形性VT・多形性VT の脈あり／脈なし**：単形性VT は「脈あり：意識・血圧・胸痛・息苦しさ等確認。要すればパッド着用 ／ 脈なしなら人を呼ぶ。CPR＋電気ショック」、多形性VT は「脈なし：CPR＋電気ショック ／ 脈あり：人を呼び、要すればパッド着用（続けば脈があってもショック）」。AHA 2025（持続する多形性VTは脈があっても非同期の電気ショック）と合っているか。単形性VT の台本「脈のあるなしで、動きが分かれる。」で足りるか
5. **トルサード**：「脈なし：CPR＋電気ショック ／ 止まっても12誘導。QT、K・Mgなどを確認」。止まってもくり返しやすいこと、Mg の値が正常でも Mg が使われることとの関係で、誤解を招かないか。台本「止まっても、QTを確認。」
6. **PEA**：「脈なしなら人を呼ぶ。すぐCPR（ショックはしない）、原因（4H4T）を確認」。4H4T を看護師が「確認」する、という言い方は妥当か（原因に関わる情報を集めて伝える、の意味）
7. **心静止**：「人を呼び、すぐCPR（ショックはしない）。並行して電極外れ・感度を確認」。電極・感度の確認は最新ガイドラインの本文には見つからなかったが、CPRを遅らせない「並行して」の実務の確認として置いた。問題はないか
8. **看護師だけで決めるように読めるところがないか**：薬・同期電気ショック・ペーシングは医師の判断（キャプションに明記）。「要すればペーシングのパッド着用」「要すればパッド着用」の「要すれば」が、看護師がひとりでペーシング・電気ショックを決めるように読めないか。電気ショックの実施は施設の決まりによる（キャプションに明記）
9. **波形の描き方**：モビッツII型を幅の狭いQRSで描いたこと（ERC が心静止の危険としてあげる完全房室ブロックは、幅の広いQRSで描いた）、R on T・ショートラン・多形性VT・トルサード・VF の描き方
10. **読みやすさ**：スマホの大きさで、次の対応（字の大きさ 32px、最大3行）が読めるか。PDF のコマで読み違えそうなところはないか
11. **台本**：短くしたことで、医学的に欠けて誤解を招く文はないか

## 返してほしい形
- パターンごと（またはページごと）と、上の「とくに見てほしい点」ごとに：判定（OK／要修正／推奨）・理由・直し方（言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください
- ナレーションの台本を変えたほうがよいものは、その文を書いてください（このあと録音します）

## 出典
{srcs}
'''
    with open(os.path.join(HERE, 'review_request.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request.md'))

    lines = ['第21弾v2 致死性不整脈 見るのは5か所 ― 画面の文字', '',
             '[見出し] 致死性不整脈 見るのは5か所（「5」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] {m.TITLE} ／ 見るのは5か所（「5」は黄色）',
             '[冒頭の変形で出る見る場所・名前] ' + ' → '.join(
                 f"{m.PLACES[m.PATTERNS[i]['place']]['no']} {m.PLACES[m.PATTERNS[i]['place']]['name']}：{m.PATTERNS[i]['name']}"
                 for i in m.HOOK),
             '[まだ紹介していない枠] 見る場所の番号と名前（薄く）', '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {m.place_label(pat)} ／ {pat['name']} ／ "
                     + ' ／ '.join(s for s, _ in pat['lines']) + f" ／ 枠：{m.cell_title(pat)}")
    lines += ['', '[最後] ' + ' ／ '.join(f"{p['no']} {p['name']}" for p in m.PLACES)
              + f' ／ {m.END_ASK} ／ {m.END_SAVE}（緑）',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', f'[右下] {m.WATERMARK}（透かし）']
    p = os.path.join(OUT, 'screen_text_reel21v2.txt')
    with open(p, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(p)


if __name__ == '__main__':
    main()
