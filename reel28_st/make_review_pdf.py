"""第28弾 波形クイズ「この波形、なに？」 ― 専門医レビュー用の資料。

- out/review_reel28_quiz_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ
  （冒頭・各問の「出題中」と「答え」・最後・サムネイル）
- review_request.md：依頼文（概要・元の回との対応表・ナレーション・キャプション・とくに見てほしい点）
- out/screen_text_reel28_quiz.txt：画面の文字の書き出し

数値は元の回のモデル（そのまま移植した make_reel28_quiz.py）から計算する（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel28_quiz as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
# 出典：元の回の出典を引き継ぐ（その問題に関係するものだけ）
SRC = {
    'LITFL Atrial Fibrillation（Q1。第26弾・第24弾）': L + 'atrial-fibrillation-ecg-library/',
    'LITFL Sinus tachycardia（Q2。第24弾）': L + 'sinus-tachycardia-ecg-library/',
    'LITFL Premature Ventricular Complex（Q3。第17弾）': L + 'premature-ventricular-complex-pvc-ecg-library/',
    'LITFL Ventricular Fibrillation (VF)（Q4。第21弾）': L + 'ventricular-fibrillation-vf-ecg-library/',
    'LITFL AV Block: 3rd degree (Complete Heart Block)（Q5。第18弾）': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL AV Block: 2nd degree, Mobitz I (Wenckebach Phenomenon)（Q6。第18弾）': L + 'av-block-2nd-degree-mobitz-i-wenckebach-phenomenon/',
    'LITFL Hyperkalaemia（Q7。第25弾）': L + 'hyperkalaemia-ecg-library/',
    'LITFL ECG Motion Artefacts（Q8。第20弾）': L + 'ecg-motion-artefacts-ecg-library/',
    '（LITFL以外）Knight BP, et al. Clinical consequences of electrocardiographic artifact mimicking ventricular tachycardia. '
    'N Engl J Med 1999;341:1270-4（Q8。第20弾）': 'https://www.nejm.org/doi/full/10.1056/NEJM199910213411704',
    'LITFL Pacemaker Malfunction（Q9。第19弾）': L + 'pacemaker-malfunction-ecg-library/',
    'LITFL Polymorphic VT and Torsades de Pointes（Q10。第21弾）': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
}
# 元の回の名前（依頼文の対応表用。視聴者には見せない）
EP = {'reel17_ectopy': '第17弾 期外収縮', 'reel18_brady': '第18弾 徐脈', 'reel19_pacing': '第19弾 ペースメーカー',
      'reel20_artifact': '第20弾 ノイズ', 'reel21_arrest': '第21弾 致死性不整脈と心停止', 'reel24_tachy': '第24弾 頻脈',
      'reel25_lytes': '第25弾 高カリウム血症とQT', 'reel26_afl': '第26弾 心房細動・心房粗動'}
# 元の回で、ひとことのうしろに出していた色の文字（案内の色を決めた根拠）
SRC_TAG = ['緑「→ 初めてなら報告」', '緑「→ まず患者さん」', 'なし', '赤「→ 電気ショック」', '赤「→ すぐ報告」',
           'なし（名前の色は「多くは良性」の黄）', '黄「→ すぐ報告」', 'なし（⑪本物のVTだけ赤「→ すぐ報告」）',
           '赤「→ すぐ報告」', '赤「→ 脈なしならショック」']
LEVEL_JA = {'red': '赤', 'yellow': '黄', 'green': '緑'}


def describe():
    """各問の描き方（元の回のモデルの値）。"""
    return [
        f"P波なし、R-R {min(m.AF_RR)}〜{max(m.AF_RR)}秒でバラバラ（平均 {60/np.mean(m.AF_RR):.0f}/分）、粗い f波（5〜8Hz、RMS {m.F_COARSE}mV）",
        f"{60/0.52:.0f}/分、どの拍にもふつうのP波（P頂点→R頂点 0.15秒）、T波は少し早い",
        f"洞調律 {60/0.8:.0f}/分の1拍おきに PVC（直前のRから 0.48秒、QRS {m.qrs_ms(m.qrs_pvc):.0f}ms、逆向きのST-T）。休みは2拍ぶん",
        '3〜9Hz（180〜540/分）の不規則で大きな揺れ（約±0.4mV）。P・QRS・Tは見えない',
        f"P波 {60/m.CAVB_PP:.0f}/分と、幅の狭いQRS（接合部）{60/m.CAVB_RR:.0f}/分が、関係なく別々に出る（比が整数にならない）",
        'P波 75/分、PR 0.18 → 0.28 → 0.33秒と伸びて、4つめのP波のあとQRSが抜ける（4:3）',
        '60/分。T波が高く（0.82mV）、細く（幅 0.23秒）、左右対称でとがる。P波・QRSは基準と同じ',
        '洞調律 75/分の上に、4.5Hz の大きな揺れ（周期4秒のうち 0.45〜3.55秒）。揺れの中に、ふつうのQRSが同じ間隔で見える',
        f"心室ペーシング 60/分（スパイク → 幅の広い下向きのQRS {m.qrs_ms(m.qrs_paced):.0f}ms）。3拍目はスパイクのあとにQRSがない",
        f"QT延長の洞調律（60/分、QT 約0.56秒）2拍 → T波の上から、約{m.TDP_F*60:.0f}/分で大きさがねじれるように変わる → "
        f"{m.TDP_B - m.TDP_A:.2f}秒で自然に止まる",
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    frames = [('冒頭：問いかけ「10問、全部わかる？」と、変形するフック（名前は出さない）', m.HOOK_T0 + 2*m.HOOK_STEP + 0.2)]
    for i, p in enumerate(m.PATTERNS):
        a, _ = m.WINDOWS[i]
        frames.append((f"{p['no']} 出題中（カウントダウン「1」。名前・色は出さない）", a + m.CD0 + 2*m.CD_STEP + 0.2))
        frames.append((f"{p['no']} 答え：{p['name']}", m.T_REV[i] + 0.9))
    frames.append(('最後：何問正解？・保存・10問の答えの一覧', m.T_END + m.FLY + 3.2))
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}（{t:.1f}秒）')
    thumb = os.path.join(OUT, 'thumb_reel28_quiz_list.png')
    m.thumbnail_list().save(thumb)                      # いつも作り直す
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙。答えは出さない）')
    fpdf = os.path.join(OUT, 'review_reel28_quiz_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    cmp = {r[0]: r for r in m.compare_sources()}
    rows = []
    for i, (p, d) in enumerate(zip(m.PATTERNS, describe())):
        folder, _, _, src_no = p['src']
        _, _, dmax, L0, L1, ev_ok, spk_ok, _ = cmp[p['no']]
        same = '同じ' if dmax < 1e-9 and ev_ok and spk_ok and abs(L0 - L1) < 1e-9 else f'ずれ {dmax:.1e}mV'
        rows.append(f"| {p['no']} | {p['name']} | {EP[folder]} {src_no} | {p['one']} | "
                    f"{LEVEL_JA[p['level']]}「{p['guide']}」（元：{SRC_TAG[i]}） | {d} | {same} |")
    narr = '\n'.join(f"- {n}：{vo.TEXT[n]}" for n, _ in vo.LINES)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    view = [m.T_REV[i] - (m.T_SW[i] + 0.3) for i in range(m.N_PAT)]
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第28弾「波形クイズ『この波形、なに？』（総復習）」全{m.N_PAT}問。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- **これまでの回で専門医レビュー済みの波形を、クイズの形で並べ直した回**。波形のモデルは各回のプログラムから数値を変えずに移植し、
  元の回のモデルで描いた波形と1msごとに比べて、同じであることを確かめた（下の表「元の回との一致」）。名前・画面のひとことも元の回と同じ
- 見る人：看護師・看護学生。これまでの回を見た人の復習（視聴者には「第◯弾」は見せない）
- 1問の流れ（約6〜7.5秒）：「Q◯ これは？」と波形だけ → カウントダウン 3・2・1（リングが減る。0.6秒ごと）→ 答え（名前・ひとこと・案内「→ くわしくは〇〇の回」）
  → 波形が縮んで上下の枠へ（枠は答えが出るまで「Q◯ ？」だけ）。答えの前は、名前・色を出さない（波形はみどり、枠は白）
- 答えの前に波形が見えている時間は 約{view[0]+0.3:.1f}秒（0.3秒で浮かび上がり、はっきり見えるのは約{view[0]:.1f}秒。前の問題の波形を枠へ移すあいだ帯を消し、問題の波形の頭から出すため）
- 案内の色は危険度。ほかの回とそろえた：赤＝元の回で赤の「→ すぐ報告」「→ 電気ショック」「→ 脈なしならショック」、
  黄＝元の回で黄色の「→ すぐ報告」、緑＝元の回で色の文字なし、または緑（「→ まず患者さん」「→ 初めてなら報告」）
- 冒頭0〜2秒：変形するフック（5問の波形。名前は出さない）の上に問いかけ「10問、全部わかる？」。最後：「何問正解？コメントで教えてね」「保存して見返してね」と、10問の答えの一覧（枠）
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。画面とキャプションに「数値はこの波形での一例」
- 「すぐ報告」は声では言わない（画面の案内の色とキャプションで伝える）

## PDFのページ
{chr(10).join(index)}

## 元の回との対応表
| 問 | 答え（名前） | 元の回・番号 | 画面のひとこと（元の回と同じ） | 案内の色 | 描き方（元の回のモデルの値） | 元の回との一致 |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## ナレーション（録音前の台本。答えのところだけ声。カウントダウン中は声なし）
{narr}

元の回の台本からとった言い回し（くわしくは台本 narration.md の表）：Q6「PRが伸びて、伸びて、抜ける」→「PRが伸びて、抜ける」、
Q10「ねじれる、トルサード。持続して脈がなければ、ショック。」→「答えは、トルサード。ねじれる。」（後半は声で言わず、案内の赤とキャプションで）

## キャプション
```
{caption}
```

## とくに見てほしい点
1. **問題の選び方と順番**（易しい → 難しい）：Q1 心房細動 → Q2 洞頻脈 → Q3 二段脈 → Q4 粗いVF → Q5 完全房室ブロック → Q6 ウェンケバッハ →
   Q7 高K：テント状T波 → Q8 偽VT → Q9 ペーシング不全 → Q10 トルサード。順番の難しさの感覚は妥当か。
   はじめの案（12問）から、心室ペーシング（Q9 ペーシング不全の波形の中に心室ペーシングが入っていて、続けて出すと答えが重なる）と
   PSVT（頻脈の回で「P波がT波に重なる洞頻脈は PSVT に見える」と教えており、モニター1本の波形だけでは答えが1つに決まりにくい）を外して10問にした（12問だと約86秒になる）。
   ほかに入れかえたほうがよいもの（心房粗動 4:1、モビッツII型 など）はあるか
2. **答えの前に見せる波形だけで、答えが1つに決まるか**（各問の「出題中」のページ）。とくに
   Q1（心房細動：粗い f波。多源性心房頻拍・心房粗動と迷わないか）、Q2（洞頻脈：心房頻拍と迷わないか）、
   Q5（完全房室ブロック：2:1・高度房室ブロックと迷わないか。PR がばらばらに見えるか）、Q7（テント状T波：ふつうの高いT波・超急性期T波と迷わないか）、
   Q8（偽VT：揺れの中のふつうのQRSが、答えの前の約{view[0]+0.3:.1f}秒で見えるか）、Q10（トルサード：多形性VTと答えても正しいか）
3. **ひとこと・声の短縮が正しいか**：Q1 は名前「心房細動（f波が粗い）」に対して声は「心房細動」、Q7 は名前「高K：テント状T波」に対して声は「高カリウム」、
   Q8 は名前「偽VT（歯みがき）」に対して声は「ノイズ」。Q10 の声で「持続して脈がなければ、ショック」を省いたこと
4. **案内の色（危険度）の決め方**：元の回の表示から機械的に決めた（表の「案内の色」）。ただし元の回どうしで「→ すぐ報告」の色が赤（徐脈・ペースメーカー・ノイズ・心房細動）と
   黄（致死性不整脈・頻脈・高カリウム）に分かれている。Q7 高K を黄、Q3 二段脈・Q6 ウェンケバッハ・Q8 偽VT を緑にしたことは妥当か
5. キャプションの「🚨見つけたらすぐ報告：Q4・Q5・Q7・Q9・Q10（VF・脈のないトルサードは電気ショック）」「⚠️心房細動は、初めて見つけたら報告。ノイズに見えても、まず患者さんを見てください」
6. 冒頭の問いかけ「10問、全部わかる？」、最後の「何問正解？コメントで教えてね」が、医療の判断をあおる言い方になっていないか
7. カウントダウン（2.4秒）と、答えの前に波形が見えている時間（約{view[0]+0.3:.1f}秒）が、看護師・看護学生のクイズとして短すぎないか

## 返してほしい形
- 問ごとに：判定（OK／要修正／推奨）・理由・直し方（数値や言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください
- ナレーションの台本を変えたほうがよいものは、その文を書いてください（このあと録音します）

## 出典（元の回から引き継いだもの）
{srcs}
'''
    with open(os.path.join(HERE, 'review_request.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request.md'))

    lines = [f'第28弾 波形クイズ「この波形、なに？」全{m.N_PAT}問 ― 画面の文字', '',
             f'[見出し] {m.HEADER[0][0]} {m.N_PAT} 問（数字は黄色・2倍）',
             f'[冒頭 0〜2.6秒] {m.HOOK_Q}（黄）／ {m.TITLE_SUB} ／ {m.TITLE}', '[冒頭の変形] 名前は出さない', '']
    for i, p in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{m.T_REV[i]:5.1f}秒] {p['no']} これは？（カウントダウン 3・2・1）"
                     + (f" ／ {m.COUNT_NOTE}" if i == 0 else '') + f" ／ 枠：{p['no']} ？")
        lines.append(f"[{m.T_REV[i]:5.1f}〜{b:5.1f}秒] {p['name']} ／ {p['one']} ／ {p['guide']}（{LEVEL_JA[p['level']]}） ／ 枠：{p['no']} {p['name']}")
    lines += ['', f'[最後] {m.END_Q}（黄） ／ {m.END_SAVE}（緑）',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel28_quiz.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
