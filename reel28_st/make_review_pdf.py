"""第28弾 心筋梗塞とST変化 ― 専門医レビュー用の資料。

- out/review_reel28_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・10パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel28.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel28 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL The ST Segment（ST上昇・ST低下の原因と形）': L + 'st-segment-ecg-library/',
    'LITFL T wave（Hyperacute T waves・Inverted T waves）': L + 't-wave-ecg-library/',
    'LITFL Q Wave（Pathological Q waves）': L + 'q-wave-ecg-library/',
    'LITFL Anterior Myocardial Infarction（hyperacute T → ST上昇 → Q波、tombstoning）': L + 'anterior-myocardial-infarction-ecg-library/',
    'LITFL Inferior STEMI（II・III・aVF、tombstone、経過）': L + 'inferior-stemi-ecg-library/',
    'LITFL Myocardial Ischaemia（ST低下の形・T波の陰転）': L + 'myocardial-ischaemia-ecg-library/',
    'LITFL Pericarditis': L + 'pericarditis-ecg-library/',
    'LITFL Benign Early Repolarisation（キャプションの「12誘導で見分ける」）': L + 'benign-early-repolarisation-ecg-library/',
    'LITFL Left Bundle Branch Block (LBBB)': L + 'left-bundle-branch-block-lbbb-ecg-library/',
    'LITFL Sgarbossa Criteria': L + 'sgarbossa-criteria-ecg-library/',
    'LITFL Accelerated Idioventricular Rhythm (AIVR)': L + 'accelerated-idioventricular-rhythm-aivr/',
    'LITFL AV block: 3rd degree (complete heart block)': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL OMI: Replacing the STEMI misnomer（hyperacute T・連続した心電図）': L + 'omi-replacing-the-stemi-misnomer/',
}


KEY_REL = {8: 1.64 + 0.45,           # ⑨ AIVR：洞調律の2拍と、幅の広い拍に変わるところが同じコマに入るように
           9: m.CHB_Q0 + m.CHB_RR + 0.6}   # ⑩ 完全房室ブロック：QRS 2つと、そのあいだの P 波


def key_time(i):
    """パターン i の見どころが、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    if i in KEY_REL:
        c = KEY_REL[i]
    elif pat['hl'] is m.ALL:
        c = min(pat['L'], 2.0) / 2 + pat['L']
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2
    t = m.t_of(m.SEGS[i][0] + c + 0.25)
    a, b = m.WINDOWS[i]
    return min(max(t, a + 0.6), b - 0.2)


def ms(x):
    return f'{x*1000:.0f}ms'


def describe():
    """各パターンの描き方（モデルの値から。1mm = 0.1mV、ST は TP＝基線からの高さ）。"""
    q = m.measure()
    mm = lambda v: f'{v*10:+.1f}mm'
    return [
        f"洞調律 {m.rate(m.RR):.0f}/分、PR {m._pr_ms(m.PR):.0f}ms、QRS {q['N']['qrs']:.0f}ms。J点 {mm(q['N']['st_j'])}（基線と同じ）、T {q['N']['t_max']*10:.1f}mm。ST部分だけ白に近い色",
        f"T {q['H']['t_max']*10:.1f}mm（R {q['H']['r']*10:.1f}mm の {q['H']['t_max']/q['H']['r']*100:.0f}%）、幅広く左右非対称。R は少し低い。J点 {mm(q['H']['st_j'])}（ST上昇はまだ小さい）",
        f"J点 {mm(q['E']['st_j'])}、J+60ms {mm(q['E']['st60'])}。上に凸の ST がそのまま T（頂点 {q['E']['t_max']*10:.1f}mm）につながる。R {q['E']['r']*10:.1f}mm。墓石型は波形では描かず、ひとことと台本でふれる",
        f"Q 幅 {q['Q']['q_ms']:.0f}ms・深さ {q['Q']['q_mv']*10:.1f}mm（R {q['Q']['r']*10:.1f}mm。Q は QRS の高さの {q['Q']['q_mv']/(q['Q']['q_mv']+q['Q']['r'])*100:.0f}%）。ST は J+60ms {mm(q['Q']['st60'])} とまだ少し高く、T の終わりが下向き（{mm(q['Q']['t_min'])}）",
        f"Q 幅 {q['I']['q_ms']:.0f}ms・深さ {q['I']['q_mv']*10:.1f}mm が残り、ST は基線（J点 {mm(q['I']['st_j'])}）。左右対称の深い陰性T（{mm(q['I']['t_min'])}）",
        f"{m.rate(m.RR):.0f}/分。J点 {mm(q['D']['st_j'])}、J+80ms {mm(q['D']['st80'])} で水平に低下、そのあと T（{q['D']['t_max']*10:.1f}mm）",
        f"{m.rate(0.56):.0f}/分（洞頻脈）。PR部分 {mm(q['C']['pr_seg'])}、ST は下に凸で J点 {mm(q['C']['st_j'])}・J+60ms {mm(q['C']['st60'])}。T {q['C']['t_max']*10:.1f}mm（ST/T {q['C']['st_j']/q['C']['t_max']:.2f}）",
        f"{m.rate(m.RR):.0f}/分、P波あり。幅の広い（{q['L']['qrs']:.0f}ms）ノッチのある R、ST（J+60ms {mm(q['L']['st60'])}）と T（{mm(q['L']['t_min'])}）は QRS と逆向き",
        f"洞調律 {m.rate(0.86):.0f}/分の2拍のあと、幅の広いQRS（{q['V']['qrs']:.0f}ms・P波なし）が {m.rate(m.AIVR_RR):.0f}/分で4拍 → 洞調律に戻る（1周期 {m.PATTERNS[8]['L']:.2f}秒）",
        f"P波 {m.rate(m.CHB_PP):.0f}/分と、幅の狭い接合部補充調律 {m.rate(m.CHB_RR):.0f}/分（QRS {q['J']['qrs']:.0f}ms、下壁のST上昇 J点 {mm(q['J']['st_j'])}）が別々に出る。"
        f"P が QRS の直前・ST の上・QRS のあいだに来る（PR がばらばら）。LITFL の例（心房 ~85/分・心室 ~38/分・接合部補充調律・下壁のST上昇）に合わせた",
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭のフック（問いかけと、止めた波形を変形しているところ）', hook_t)] \
        + [(f"{p['no']} {p['name']}", key_time(i)) for i, p in enumerate(m.PATTERNS)] \
        + [('最後：10個の一覧（保存・何個わかった？）', m.T_END + m.FLY + 2.5)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}')
    thumb = os.path.join(OUT, 'thumb_reel28_list.png')
    m.thumbnail_list().save(thumb)                       # いつも作り直す（古いサムネイルを入れない）
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel28_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    # 依頼文
    narr = '\n'.join(f"- {n}：{vo.TEXT[n]}" for n, _ in vo.LINES)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    tagtxt = {k: v[0] for k, v in m.TAGS.items()}
    rows = '\n'.join(f"| {p['no']} {p['name']} | {p['one']} ＋「{tagtxt[p['tag']]}」 | {m.mag_readout(i)} | {d} |"
                     for i, (p, d) in enumerate(zip(m.PATTERNS, describe())))
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第28弾「心筋梗塞とST変化、10パターン」（前回の12パターン版から作り直し）。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人。胸痛の患者のモニター変化に最初に気づきうる）
- 第17〜21弾と同じ作り：冒頭3秒で波形を止めて5パターン（②〜⑥）に素早く変形（フック）→ 10パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に10個の一覧
- この回だけの見せ方：
  - **STの虫眼鏡**：中部の帯の上の窓に、1拍を拡大して描く（⑨は左に洞調律・右にAIVRを並べて約2.9秒、⑩は約2.3秒。倍率は 1mm＝14〜20px、⑨⑩は全体を入れるため 8〜10px）。前のパターンが枠に着地してから出す。窓の中は 1mm（たて0.1mV・よこ0.04秒）の正方形の方眼、基線（TP）の点線、ST などの位置の矢印。右上に値（「ST ↑3mm」など。モデルの波形から計算、1mm 以上は 0.5mm きざみ）
  - **時間の流れのバー**：②〜⑤のあいだ、上に「超急性期T → ST上昇 → 異常Q波 → 冠性T」を出し、いまの段階に下線。時間の目安（何時間・何日）は書いていない
- 再生を伸ばすしかけ：冒頭0〜2.4秒に問いかけ「このST、すぐ報告？」、最後に「保存して見返してね」「何個わかった？コメントで教えてね」
- 波形はモデルで作った模式図。**II誘導のモニター・実際の速さ（25mm/秒）**。各拍の特徴のところ（ST-T・Q など）だけ、いま紹介中のパターンの色（左に残っている前のパターンの拍は緑）。左下の注記は「※II誘導のモニター（実際の速さ）」「※数値はこの波形での一例」
- **大前提：モニター（II誘導の1つ）だけでは ST 変化は判断できない**。画面の色の文字（赤「→ すぐ報告・12誘導」、橙「→ 12誘導で確認」）、最後の文「モニターのST変化は、12誘導で確認」、キャプションで伝えている
- その他の色の文字：①「→ 比べる基準」（緑）、⑨「→ 報告して観察」（紫）、⑩「→ すぐ報告」（赤）。ナレーションでは「すぐ報告」と言わない（画面とキャプションで伝える）
- 並び：①〜⑤ 心筋梗塞の時間の流れ（基準 → 超急性期T波 → ST上昇（大きいと墓石型）→ 異常Q波 → 冠性T波）、⑥ ST低下（虚血）、⑦⑧ まぎらわしいST変化（心膜炎・左脚ブロック）、⑨⑩ 心筋梗塞のときの不整脈（AIVR・完全房室ブロック）
- 前回から外したもの：墓石型（③に含めた）、上行型のST低下（「虚血とは限らない」が安心材料に取られるおそれ）、早期再分極（II誘導1本では区別できない。キャプションで「12誘導で見分ける」とふれた）。足したもの：⑩完全房室ブロック
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library（下に一覧）。LITFL 以外は使っていない

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 虫眼鏡の値（モデルから計算） | 描き方（1mm = 0.1mV。ST は TP＝基線からの高さ） |
|---|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. 「すぐ報告・12誘導」（②③⑥）、「12誘導で確認」（④⑤⑦⑧）、「報告して観察」（⑨）、「すぐ報告」（⑩）の分け方。とくに ④異常Q波（ST がまだ少し高い形で描いた）、⑧左脚ブロック（新しい左脚ブロック＋胸痛）をどう扱うか
2. STの虫眼鏡の値と描き方。①「ST 0mm（基線と同じ）」、②「T ↑7mm」、③「ST ↑3mm」（J点で測った）、④「Q ↓3mm」、⑤「T ↓3.5mm」、⑥「ST ↓1.5mm」（J+60ms）、⑦「PR ↓0.7mm　ST ↑0.9mm」、⑧「ST ↓2mm　QRSと逆向き」、⑨「QRS 0.15秒（幅広）」、⑩「P 86/分・QRS 38/分」。ST を測る点（J点か J+60ms か）と、値の出し方（0.5mm きざみ、1mm 未満は 0.1mm）で誤解がないか
3. 時間の流れのバー（超急性期T → ST上昇 → 異常Q波 → 冠性T）。時間の目安は書かなかった。この順番の示し方で誤解がないか（Q波は早く出ることもある、ST上昇と冠性Tが同時にあることもある、など）
4. ③ ST上昇：上に凸で描いた（LITFL：STEMI の ST 上昇は concave・convex・obliquely straight のどれもある）。墓石型は ひとこと「大きいと墓石型」と台本「大きいと、墓石のような形に。」でふれるだけにした
5. ② 超急性期T波：T 6.8mm（R の約77%）、幅広く左右非対称、ST はほぼ基線。台本「早い時期に、Tが高く幅広くなる。」は言いすぎでないか（LITFL：often precede the appearance of ST elevation and Q waves）
6. ⑥ 水平型 ST 低下（1.5mm）を「虚血のサイン → すぐ報告・12誘導」としたこと。鏡像変化（ほかの誘導の ST 上昇の裏返し）のこともある点にふれるべきか
7. ⑦ 心膜炎（107/分、PR -0.7mm、ST +0.9mm 下に凸）。「広い範囲」は12誘導の話で、II誘導1本では見分けにくい。画面「PR低下＋下に凸のST上昇」と言い切ってよいか
8. ⑧ 左脚ブロック：II誘導で、幅の広いノッチのある R と、逆向き（下がる）ST-T で描いた。II誘導の左脚ブロックの形として妥当か（軸によって変わる）
9. ⑨ AIVR：洞調律 70/分のあと、幅の広い QRS が 77/分で4拍 → 洞調律。P波（房室解離）は描いていない。「報告して観察」でよいか
10. ⑩ 完全房室ブロック（新しく足した）：心房 86/分、幅の狭い接合部補充調律 38/分、QRS には下壁のST上昇（LITFL の例に合わせた）。「→ すぐ報告」、ひとこと「PとQRSが別々。下壁梗塞で」、台本「下壁の梗塞で起きやすい、完全房室ブロック。」（LITFL Inferior STEMI：Up to 20% … second- or third-degree AV block）。下壁梗塞の房室ブロックはアトロピンに反応しやすく一過性が多い（LITFL）が、その点を入れるべきか
11. 冒頭の問いかけ「このST、すぐ報告？」（画面だけ。声では言わない）と、最後の「何個わかった？コメントで教えてね」、キャプション1行目「このST変化、すぐ報告？それとも12誘導で確認？」。医療の判断をあおる言い方になっていないか
12. スマホの大きさで、虫眼鏡の字（右上の値 30px、見出し 20px、「基線」20px）が読めるか

## 返してほしい形
- パターン番号（またはページ）ごとに：判定（OK／要修正／推奨）・理由・直し方（数値や言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください
- ナレーションの台本を変えたほうがよいものは、その文を書いてください（このあと録音します）

## 出典
{srcs}
'''
    with open(os.path.join(HERE, 'review_request.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request.md'))

    lines = ['第28弾 心筋梗塞とST変化 10パターン ― 画面の文字', '',
             '[見出し] 心筋梗塞とST変化 10パターン（「10」は黄色・2倍）',
             f'[冒頭 0〜2.4秒の問いかけ] {m.HOOK_Q}',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ 心筋梗塞とST変化',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}"
                     f" ／ 虫眼鏡：{m.mag_title(i)}「{m.mag_readout(i)}」")
    lines += ['', '[②〜⑤のあいだ] 時間の流れ ' + ' → '.join(m.TIME_STAGES) + '（いまの段階に下線）',
              f'[最後] {m.END_LINE} ／ 保存して見返してね ／ {m.END_Q}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel28.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
