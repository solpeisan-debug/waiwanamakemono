"""見分けマップ①②（2枚組）― 専門医レビュー用の資料。

- out/review_map_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ
  （マップごとに：冒頭・例6つ（答えにたどり着いたところ）・最後の全体・サムネイル）
- review_request.md：依頼文（作品の概要・マップの中身・例の波形の数値・キャプション・見てほしい点）

例の波形の数値は、モデルの値から計算する（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import importlib
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL ECG Library（各リズムの項目）': L + 'ecg-library/',
    'LITFL VT versus SVT（幅の広い頻拍は、迷ったらVT）': L + 'vt-versus-svt-ecg-library/',
    'LITFL Atrial Flutter': L + 'atrial-flutter-ecg-library/',
    'LITFL AV Block: 2nd degree, Mobitz I / Mobitz II': L + 'av-block-2nd-degree-mobitz-i-wenckebach-phenomenon/',
    'LITFL AV Block: 3rd degree (Complete Heart Block)': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL Polymorphic VT and Torsades de Pointes': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
    'LITFL CCC Pulseless Electrical Activity': L + 'pulseless-electrical-activity/',
}
COL_NAME = {}


def load(no):
    os.environ['MAP_NO'] = str(no)
    import make_map
    m = importlib.reload(make_map)
    COL_NAME.update({m.C_RED: '赤', m.C_ORANGE: 'オレンジ', m.C_YEL: '黄', m.C_BLUE: '青', m.C_GREEN: '緑'})
    return m


def tree_text(m):
    """マップの中身を、字下げした文字で書き出す。"""
    out = []
    for r in m.ROWS:
        ind = '　　' * r['d']
        ans = f"［{r['ans']}］" if r['ans'] else ''
        if r['kind'] == 'q':
            out.append(f"{ind}{ans} {r['text']}")
        else:
            out.append(f"{ind}{ans} ■ {r['text']}（{COL_NAME.get(r['col'], '?')}）")
    return '\n'.join(out)


def rate(rr):
    return f'{60/rr:.0f}/分'


def describe(m, key):
    """例の波形（上の枠に流れるもの）の描き方。"""
    R = m.RHYTHMS[key]
    if key == 'nsr':
        return f'P波＋細いQRS、{rate(0.8)}、PR 0.16秒'
    if key == 'av1':
        return f'P波＋細いQRS、{rate(0.8)}、PR 0.30秒'
    if key == 'chb':
        return f'P波 {rate(0.6)} と、細いQRS（接合部補充調律）{rate(1.5)} が関係なく別々に出る'
    if key == 'flut':
        return f'下向きの鋸歯状波（F波）300/分、細いQRS {rate(0.4)}（2:1伝導）'
    if key == 'vt':
        return f'幅の広いQRSが {rate(0.32)} で規則正しく続く'
    if key == 'pace':
        return f'スパイク＋幅の広いQRS（II誘導で下向き、Tは上向き）{rate(1.0)}'
    if key == 'af':
        rr = m._AF_RR
        return f'P波なし、細かい基線の揺れ（f波）、R-R がバラバラ（{min(rr):.2f}〜{max(rr):.2f}秒、平均 {60/np.mean(rr):.0f}/分）'
    if key == 'pvc':
        return f'洞調律 {rate(0.8)} の中に、幅の広いPVCが直前のRから0.48秒で1拍。代償性の休み'
    if key == 'wk':
        return 'PRが 0.18 → 0.28 → 0.33秒と伸びて、4つめのP波のあとQRSが抜ける（4:3）'
    if key == 'sarr':
        rr = m._SA_RR
        return f'P波＋細いQRS、R-R が {min(rr):.2f}〜{max(rr):.2f}秒でゆっくり伸び縮み（呼吸に合わせた想定）'
    if key == 'vf':
        return '3〜9Hz の不規則な大きな揺れ（約±0.4mV）。QRSは見えない'
    if key == 'pasys':
        return f'P波だけ {rate(0.8)}。QRSはない'
    return ''


def frames_for(m, no):
    out = [(f'マップ{no}：冒頭（質問が上から順に出る）', m.T_INTRO - 0.4)]
    for k, c in enumerate(m.CASES):
        t = m.T_INTRO + k*m.CASE_D + m.reveal_t(k) + 1.0
        out.append((f"マップ{no}：例{k+1} {c['name']}（答えにたどり着いたところ）", t))
    out.append((f'マップ{no}：最後（マップ全体・保存してね）', m.T_OUTRO + 3.0))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index, sections = [], [], []
    for no in (1, 2):
        m = load(no)
        for name, t in frames_for(m, no):
            fp = os.path.join(fdir, f'{len(pngs)+1:02d}.png')
            m.frame(t).save(fp)
            pngs.append(fp); index.append(f'- {len(pngs)}ページ：{name}')
        thumb = os.path.join(OUT, f'thumb_map{no}.png')
        if not os.path.exists(thumb):
            m.thumbnail().save(thumb)
        pngs.append(thumb); index.append(f'- {len(pngs)}ページ：マップ{no}：サムネイル（投稿の表紙）')
        cases = '\n'.join(f"| {k+1} | {c['name']} | {' → '.join(m.ROWS[i]['ans'] or m.ROWS[i]['text'] for i in c['path'][1:])} | {describe(m, c['key'])} |"
                          for k, c in enumerate(m.CASES))
        cap = open(os.path.join(HERE, f'caption_map{no}.txt'), encoding='utf-8').read().strip()
        sections.append(f'''## マップ{no}「{m.CFG['title'][0]}{m.CFG['title'][1]}」（{m.DUR:.1f}秒）

### マップの中身（［ ］は前の質問への答え、■は名前、（ ）は名前の色）
```
{tree_text(m)}
```

画面の注意書き：{' ／ '.join(m.CFG['notes'])}

### 例の波形（上の枠に流れ、光る点がマップをたどる）
| 例 | 名前 | たどる答え | 描き方（モデルの値） |
|---|---|---|---|
{cases}

### キャプション
```
{cap}
```
''')
    fpdf = os.path.join(OUT, 'review_map_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。マップの中身とキャプションは、この依頼文の中にあります。

## 作品の概要
- 「見分けマップ」2枚組（①規則的な波形 ／ ②不規則・QRSなし）。縦 1080×1920・60fps・ナレーションなし（モニター音だけ）・ループ
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）。保存・シェアされる「1枚で見返せる図」をねらう
- 作り：上の枠に例の波形が流れ、光る点がマップの質問を1つずつたどって名前にたどり着く → 例を6つ → 最後にマップ全体を光らせて「保存してね」→ 冒頭に戻る
- マップは、モニター（II誘導）で見る入口の一例。画面とキャプションに「例外あり」と明記している
- 名前の色：赤＝危険・すぐ対応、オレンジ＝頻脈性の不整脈、黄＝注意、青＝徐脈・期外収縮・ペースメーカーなど、緑＝正常の範囲
- 波形はモデルで作った模式図（実際の速さ）。主な出典は LITFL ECG Library（下に一覧）。ほかの投稿の図を写したものではない（構成・言葉は独自）

## PDFのページ
{chr(10).join(index)}

{chr(10).join(sections)}
## とくに見てほしい点
1. 2枚の分け方（①規則的 ／ ②不規則・QRSなし）と、それぞれの最初の質問（①ペースメーカーのスパイク → 心拍数、②QRSはある？）は、看護師の入口として妥当か
2. マップ①：60未満で「P波なし → QRSの幅で接合部／心室補充調律」「P波あり → 毎回QRS？ → PとQRSの関係（一定＝2:1・高度房室ブロック／バラバラ＝完全房室ブロック）」の分け方
3. マップ①：60〜100 を「PRは？（0.2秒以下＝洞調律／長い＝1度房室ブロック）」だけで分けたこと。洞調律の条件（P波の形・QRS幅）を省いてよいか
4. マップ①：100以上で「幅の狭い → P波（ふつう＝洞頻脈／のこぎり状＝心房粗動／見えない＝PSVT）」「幅の広い → VT」。幅の広い頻拍をすべてVTに入れたこと（LITFL：迷ったらVT）
5. マップ②：「全部バラバラ × 広い」を「多形性VT・トルサード」にしたこと（変行伝導・脚ブロック・WPWを伴う心房細動との関係をどう扱うか）
6. マップ②：「QRSがない」の中に「P波だけの心静止」を入れたこと。PEAはマップに入れず、注意書き（波形があっても脈がなければPEA）にしたこと
7. 名前の色分け（とくに赤：心室補充調律・2:1・高度房室ブロック・完全房室ブロック・VT・VF・多形性VT・モビッツII型）は妥当か
8. 入っていないもの（多源性心房頻拍、心房粗動の不規則な伝導、WPW、接合部調律の速いもの、ブルガダ型 など）で、入口として入れるべきものはあるか
9. 例の波形（6つ×2）の描き方は代表の形として妥当か。スマホの大きさで、マップの字（とくに答えの小さい字）が読めるか

## 返してほしい形
- マップ（①②）と行ごと、または例ごとに：判定（OK／要修正／推奨）・理由・直し方（言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- LITFL 以外を根拠にするときは、出典名を書いてください

## 出典
{srcs}
'''
    with open(os.path.join(HERE, 'review_request.md'), 'w', encoding='utf-8') as f:
        f.write(txt)
    print(os.path.join(HERE, 'review_request.md'))


if __name__ == '__main__':
    main()
