"""第28弾 波形クイズ「この波形、なに？」 ― 専門医レビュー用の資料。

- out/review_reel28_quiz_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ
  （冒頭・各問の「出題」「ヒント」「答え」・最後・サムネイル）
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
# ヒントの文の出どころと、色付けの場所（ことばで。数値は make_reel28_quiz.py の hint_hl）
HINT_SRC = ['新しい文（考えさせる形。元の回 ②の hint は「f波が大きい」、ひとことは「P波なし、R-Rがバラバラ」）',
            '元の回 ①の hint', '元の回 ⑨の hint', '元の回 ⑥の hint',
            'ユーザーの案（元の回 ⑨の hint は「PとQRSがばらばら」）', '元の回 ⑤の hint', '元の回 ②の hint',
            'ユーザーの案（元の回 ⑨の hint は「VTに見える」）', '元の回 ⑨の hint', '元の回 ⑤の hint']
HINT_PLACE = ['全体（粗い f波と、間隔がばらつくQRS）。元の回の色付けと同じ',
              '**新**：どの拍もP波だけ（P頂点の前後0.06秒）。答えのあとは濃い水色（#38BDF8）で、線を濃く・太く。元の回は全体',
              'PVC（PVCの0.09秒前〜0.40秒後。逆向きのST-Tまで）。前回の版と同じ',
              '全体。元の回の色付けと同じ',
              '**新**：P波（P頂点の前後0.07秒。QRSにはかけない）。T波に重なるP波も色付け。QRSに隠れたP波（R頂点の前後0.06秒）は色を付けず、'
              'そのP波の時刻の、波形の一番上より上に「▼」（ヒント中は紫、答えのあとは赤。帯とミニ波形の両方）',
              '**新**：P波の始まりから QRSの始まり（R頂点の0.04秒前）まで（PR）。QRSが抜けたP波は P波だけ',
              'T波（R頂点の0.09〜0.40秒後）。前回の版と同じ',
              '**新**：揺れの中のふつうのQRS（R頂点の前後0.04秒、0.80秒ごと）と、その上に並ぶ「▼」（0.80秒ごと）。元の回は揺れの区間全体',
              'スパイクだけの拍（スパイクの0.12秒前〜0.30秒後）。元の回の色付けと同じ',
              'ねじれの区間（始まりの0.1秒前〜終わりの0.1秒後）。元の回の色付けと同じ。**新**：答えのあとは、洞調律の拍の QT（QRSの始まり〜T波の終わり）にも答えの色']


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
        frames.append((f"{p['no']} 出題（波形はみどり一色。名前・ヒントは出さない。時間のリングが減りはじめる）", a + m.HINT0 - 0.15))
        frames.append((f"{p['no']} ヒント「ヒント：{p['hint']}」と特徴の色付け（紫）。リングだけが減っていく（数字なし）", m.T_HINT[i] + 1.5))
        frames.append((f"{p['no']} 最後の3秒のカウント「1」（答えの直前）", m.T_REV[i] - 0.5))
        frames.append((f"{p['no']} 答え：{p['name']}（色付けがこの問題の色に変わる）", m.T_REV[i] + 0.9))
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
        rows.append(f"| {p['no']} | {p['name']} | {EP[folder]} {src_no} | 「ヒント：{p['hint']}」（{HINT_SRC[i]}） | {HINT_PLACE[i]} | "
                    f"{p['one']} | {LEVEL_JA[p['level']]}「{p['guide']}」（元：{SRC_TAG[i]}） | {d} | {same} |")
    narr = '\n'.join(f"- {n}：{vo.TEXT[n]}" for n, _ in vo.LINES)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    view = [m.T_REV[i] - (m.T_SW[i] + 0.3) for i in range(m.N_PAT)]
    lens = [b - a for a, b in m.WINDOWS]
    plain = m.HINT0 - m.T0_OFF
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第28弾「波形クイズ『この波形、なに？』（総復習）」全{m.N_PAT}問。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- **これまでの回で専門医レビュー済みの波形を、クイズの形で並べ直した回**。波形のモデルは各回のプログラムから数値を変えずに移植し、
  元の回のモデルで描いた波形と1msごとに比べて、同じであることを確かめた（下の表「元の回との一致」）。名前・画面のひとことも元の回と同じ
- 見る人：看護師・看護学生。これまでの回を見た人の復習（視聴者には「第◯弾」は見せない）
- 1問の流れ（{min(lens):.1f}〜{max(lens):.1f}秒）。**考える時間（波形がはっきり見え始めてから答えまで）は{m.THINK:.0f}秒**：
  0. 前の問題の波形が枠へ縮む（{m.FLY:.1f}秒）。そのあいだに帯が浮かび上がる
  1. 出題（波形がはっきり見え始めてから {plain:.1f}秒）：「Q◯ これは？」と波形だけ（みどり一色）。「これは？」の右の時間のリングが減りはじめ、{m.THINK:.0f}秒で空になる
  2. ヒント（{m.REVEAL - m.HINT0:.1f}秒）：「ヒント：〇〇」と、波形の特徴のところだけ紫の色付け。最後の{m.CD_N}秒だけ、リングの中に数字 3・2・1（{m.CD_STEP:.0f}秒ごと）
  3. 答え（声の長さ＋0.45秒）：名前・ひとこと・案内「→ くわしくは〇〇の回」と声。色付けがその問題の色に変わる
  4. 波形が縮んで上下の枠へ（枠は答えが出るまで「Q◯ ？」だけ）
- 答えの前に波形がはっきり見えている時間は {m.THINK:.0f}秒（そのうちヒントなしで見るのは {plain:.1f}秒）。前の問題の波形を枠へ移すあいだ帯を消し、問題の波形を出すため
- ヒントの色付けの紫は、答えの色（青・水色・橙・赤・黄）や危険度の色（赤・黄・緑）とは別の色にした（答えの前に、色で答えや危険度がわからないように）
- 案内の色は危険度。ほかの回とそろえた：赤＝元の回で赤の「→ すぐ報告」「→ 電気ショック」「→ 脈なしならショック」、
  黄＝元の回で黄色の「→ すぐ報告」、緑＝元の回で色の文字なし、または緑（「→ まず患者さん」「→ 初めてなら報告」）
- 冒頭0〜2秒：変形するフック（5問の波形。名前は出さない）の上に問いかけ「10問、全部わかる？」。最後：「何問正解？コメントで教えてね」「保存して見返してね」と、10問の答えの一覧（枠）
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。画面とキャプションに「数値はこの波形での一例」
- 「すぐ報告」は声では言わない（画面の案内の色とキャプションで伝える）

## 前回レビューからの変更点
前回（ヒントなし・1問 約6〜7.5秒・全体 73.8秒の版）は「要修正なし」でした。そのあと、次を変えました。
1. **答えの前に「ヒント＋特徴の色付け」の段階を足した**（ユーザーの依頼）。ヒントの文は、元の回のミニ枠に出していた hint（レビュー済み）から。
   Q1・Q5・Q8 だけユーザーの案。色付けの場所は、元の回の色付けと同じものが多いが、Q2（全体 → P波だけ）と Q8（揺れの区間全体 → 隠れたQRSだけ）は新しい
   （下の表）。答えのあとの色付け（中部の帯と、上下の枠のミニ波形）も、ヒントと同じ場所にした
2. **考える時間を{m.THINK:.0f}秒にした**（ユーザーの依頼）：波形がはっきり見え始めてから、{plain:.1f}秒でヒント、{m.THINK:.0f}秒で答え。
   時間のリングが{m.THINK:.0f}秒で空になり、最後の{m.CD_N}秒だけ数字 3・2・1。そのあと答え（声の長さ＋0.45秒）。
   全体 {m.DUR:.1f}秒（前回 73.8秒）。画面に秒数は書かない。声の長さの見込みは 7字/秒（同じ声の録音で実測 6.96字/秒）
3. **カウントの音を変えた**：モニター音「ピッ」（{m.BEEP_F:.0f}Hz、80ms）と、はっきり違う木の音「コッ」（{m.TOK_F[0]:.0f}＋{m.TOK_F[1]:.0f}Hz、約30ms）に。
   答えの瞬間は明るい「ポーン」（{m.POM_F:.0f}Hz、約0.6秒）。最後の{m.CD_N}秒のカウントのあいだはモニター音を -6dB
4. **Q8 の台本を「ふつうのQRSが隠れている。」にした**（前回は「隠れています」。ノイズの回の確定した台本に合わせた）
5. 見た目の直し（医学的な中身は変えていない）：余白・字の大きさ、上下の枠のミニ波形の大きさ（はみ出さないように問題ごとに縮小）、
   Q9・Q10 の波形の見せ始め（ヒントと答えの瞬間に、スパイクだけの拍・ねじれが画面にあるように）、キャプションに「（速いときは一時停止してね）」。
   冒頭の波形は消さずに、Q1 の波形へなめらかに変形する。問題が変わるときは、次の波形が右からすべり込む
6. **ヒントの文・色付け・画面の注意・キャプションを見直した**
   - Q1 のヒント：「P波がない・R-Rがバラバラ」（答えのひとことと同じ文だった）→「R-Rの間隔と、P波をさがして」
   - Q5 の色付け：QRSに隠れたP波の場所はQRSに色を付けず、「▼」で示す（QRSがまるごと色付きに見えないように）
   - Q2：答えのあとのP波の色を濃い水色にし、線を濃く・太く。Q6：色の終わりを QRS の始まりに。Q8：色の幅を R頂点の前後0.04秒に狭め、
     「▼」を0.80秒ごとに並べる。Q10：答えのあと QT にも色
   - Q8 の答えの画面：案内の下に「※まず患者さん（意識・脈）を見てから」（声は変えていない）
   - キャプション：「すぐ報告」の行から VF・脈のないトルサードを分け、「心停止：まず患者さんを見て、応援を呼び、CPRと電気ショック」に。
     緑の波形も「新しく出たとき・症状があるときは報告」の1行を足した。Q9 に「（捕捉不全：スパイクのあとにQRSがない）」。出典に JRC蘇生ガイドライン2020（医療従事者のBLS）

## PDFのページ
{chr(10).join(index)}

## 元の回との対応表
| 問 | 答え（名前） | 元の回・番号 | ヒント（新） | ヒントの色付けの場所（新） | 画面のひとこと（元の回と同じ） | 案内の色 | 描き方（元の回のモデルの値） | 元の回との一致 |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## ナレーション（録音前の台本。答えのところだけ声。出題・ヒント・カウントダウンのあいだは声なし）
{narr}

元の回の台本からとった言い回し（くわしくは台本 narration.md の表）：Q6「PRが伸びて、伸びて、抜ける」→「PRが伸びて、抜ける」、
Q10「ねじれる、トルサード。持続して脈がなければ、ショック。」→「答えは、トルサード。ねじれる。」（後半は声で言わず、案内の赤とキャプションで）

## キャプション
```
{caption}
```

## とくに見てほしい点（今回は、新しく足したヒントと色付けが中心です）
1. **ヒントの文が正しいか、答えの名前を明かしすぎていないか**（表の「ヒント」）。とくに
   Q1「R-Rの間隔と、P波をさがして」（新しい文）、Q4「大きくバラバラ」・Q10「ねじれる」（答えの声と同じことば）、
   Q5「PとQRSの間隔」（完全房室ブロックのヒントとして適切か）、Q8「同じ間隔のQRS」
2. **色付けと「▼」の場所が正しいか**（各問の「ヒント」「答え」のページと、最後の一覧の枠）。とくに Q2（どの拍のP波）、
   Q5（QRSに隠れたP波の「▼」、T波に重なるP波の色）、Q6（P波〜QRSの始まり）、Q8（揺れの中のふつうのQRSと「▼」）、Q10（答えのあとの QT）
3. **画面とキャプションの安全の書き方**：Q8 の「※まず患者さん（意識・脈）を見てから」、キャプションの心停止の行（VF・脈のないトルサード）と、緑の波形の報告の行
4. **ヒントを出す早さ**：波形が見え始めて {plain:.1f}秒でヒントと色付けが出る（考える時間 {m.THINK:.0f}秒のうち、ヒントを見ながら考えるのが {m.REVEAL - m.HINT0:.1f}秒）。早すぎて、自分で考える前に答えがわかってしまわないか
5. 答えで、色付けが紫から答えの色に変わる見せ方に問題がないか（Q2・Q8 は、答えのあとも色が付くのはP波・QRSだけ）
6. 前回の「推奨」で、この版に入れたほうがよいものが残っていないか

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
        lines.append(f"[{a:5.1f}〜{m.T_HINT[i]:5.1f}秒] {p['no']} これは？"
                     + (f" ／ {m.COUNT_NOTE}" if i == 0 else '') + f" ／ 枠：{p['no']} ？")
        lines.append(f"[{m.T_HINT[i]:5.1f}〜{m.T_REV[i]:5.1f}秒] {p['no']} これは？（時間のリング。最後の3秒だけ数字 3・2・1） ／ ヒント：{p['hint']}（紫）")
        lines.append(f"[{m.T_REV[i]:5.1f}〜{b:5.1f}秒] {p['name']} ／ {p['one']} ／ {p['guide']}（{LEVEL_JA[p['level']]}） ／ 枠：{p['no']} {p['name']}")
    lines += ['', f'[最後] {m.END_Q}（黄） ／ {m.END_SAVE}（緑）',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel28_quiz.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
