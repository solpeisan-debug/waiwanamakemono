"""第26弾 心房細動・心房粗動 ― 専門医レビュー用の資料。

- out/review_reel26_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・12パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel26.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

from PIL import Image

import align_vo as vo
import make_reel26 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL Atrial Fibrillation': L + 'atrial-fibrillation-ecg-library/',
    'LITFL Atrial Flutter': L + 'atrial-flutter-ecg-library/',
    'LITFL Ashman Phenomenon（Eponymictionary）': L + 'ashman-phenomenon/',
    'LITFL Atrial fibrillation/flutter in pre-excitation': L + 'atrial-fibrillation-in-pre-excitation/',
    'LITFL Digoxin Toxicity（Regularised AF）': L + 'digoxin-toxicity-ecg-library/',
    'LITFL AV block: 3rd degree (complete heart block)': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL Right Bundle Branch Block (RBBB)': L + 'right-bundle-branch-block-rbbb-ecg-library/',
}


def key_time(i):
    """パターン i のレビュー用のコマ。ふつうは紹介の終わりの0.5秒前（中部の帯がそのパターンだけで埋まり、名前とひとことがまだ出ている）。
    色を付ける範囲があるもの（⑤ アシュマン現象）は、その拍が中央の少し右（＋0.3秒）に来るとき（左に、その前の長い R-R が見える）。"""
    a, b = m.WINDOWS[i]
    pat = m.PATTERNS[i]
    if pat['hl'] is not m.ALL:
        lo, hi = pat['hl'][0]
        t = m.t_of(m.SEGS[i][0] + lo + 0.10 - 0.30)
        return min(max(t, a + 0.6), b - 0.5)
    return b - 0.5


def describe():
    """各パターンの描き方（モデルの値から）。"""
    fc, fm, ff = (m.f_peak(m.PATTERNS[k])[0] for k in (0, 2, 1))
    fl = m.f_peak(m.PATTERNS[8])[0]
    q = m._qrs_ms
    rr = lambda x: f'{min(x):.2f}〜{max(x):.2f}秒'
    return [
        f'P波なし。R-R が不規則（{rr(m.RR_COARSE)}、平均{m._rate(m.RR_COARSE):.0f}/分）。f波 5〜8Hz の不規則な揺れ、山から谷 約{fc:.2f}mV（粗い）',
        f'P波なし。R-R が不規則（{rr(m.RR_FINE)}、平均{m._rate(m.RR_FINE):.0f}/分）。f波は山から谷 約{ff:.2f}mV（細かい。基線はほぼ平ら）',
        f'R-R 不規則で速い（平均{m._rate(m.RR_FAST):.0f}/分、{60/max(m.RR_FAST):.0f}〜{60/min(m.RR_FAST):.0f}/分）。幅の狭いQRS、f波 約{fm:.2f}mV',
        f'R-R 不規則で遅い（平均{m._rate(m.RR_SLOW):.0f}/分、{60/max(m.RR_SLOW):.0f}〜{60/min(m.RR_SLOW):.0f}/分）。f波 約{fm:.2f}mV',
        f'心房細動（平均{m._rate(m.RR_ASH):.0f}/分）。長い R-R {m.RR_ASH[m.ASH_K-2]:.2f}秒の直後、短い R-R {m.RR_ASH[m.ASH_K-1]:.2f}秒で来た1拍だけ'
        f'右脚ブロック型の幅の広いQRS（約{q(m.qrs_aberrant):.0f}ms、ふつうの拍は約{q(m.qrs_normal):.0f}ms）',
        f'心房細動（平均{m._rate(m.RR_BBB):.0f}/分、R-R 不規則）。全部の拍が同じ形の幅の広いQRS（右脚ブロック型、約{q(m.qrs_aberrant):.0f}ms）',
        f'粗いf波（約{fc:.2f}mV）なのに、R-R が {m.RR_CHB[0]:.2f}秒で規則的（{60/m.RR_CHB[0]:.0f}/分）。幅の狭い接合部補充調律（LITFL：Regularised AF）',
        f'R-R 不規則でとても速い（平均{m._rate(m.RR_WPW):.0f}/分、{60/max(m.RR_WPW):.0f}〜{60/min(m.RR_WPW):.0f}/分）。デルタ波つきの幅の広いQRS'
        f'（約{q(m._preex(*m.PREEX["D1"], with_t=False)):.0f}〜{q(m._preex(*m.PREEX["D3"], with_t=False)):.0f}ms、拍ごとに幅と大きさが少し変わる。向き＝軸は同じ）、逆向きのT',
        f'II誘導で下向きのF波（のこぎり状）{60/m.FF:.0f}/分、山から谷 約{fl:.2f}mV。4:1伝導で R-R {4*m.FF:.1f}秒（{60/(4*m.FF):.0f}/分）。T波は小さめ',
        f'同じF波。2:1伝導で R-R {2*m.FF:.1f}秒（{60/(2*m.FF):.0f}/分）で規則的。F波の1つはQRS・T波に重なる（実際は見えにくいことが多いので、画面は「150/分で規則的なら粗動を疑う」）',
        f'同じF波。伝導比が {"・".join(f"{round(x/m.FF)}:1" for x in m.RR_VAR)} と変わり、R-R が不規則（どれも F-F {m.FF:.1f}秒の倍数、平均{m._rate(m.RR_VAR):.0f}/分）',
        f'F波が1:1で全部伝わり、幅の狭いQRSが {60/m.FF:.0f}/分で規則的（F波は 約{m.f_peak(m.PATTERNS[11])[0]:.2f}mV、T波は小さく早い）',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭のフック（止めた波形を変形しているところ）', hook_t)] \
        + [(f"{p['no']} {p['name']}", key_time(i)) for i, p in enumerate(m.PATTERNS)] \
        + [('最後：12個の一覧（見分けのポイント）', m.T_END + m.FLY + 3.0)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}')
    thumb = os.path.join(OUT, 'thumb_reel26_list.png')
    m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel26_frames.pdf')
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
    rows = '\n'.join(f"| {p['no']} {p['name']} | {p['one']} ＋「{tagtxt[p['tag']]}」 | {d} |"
                     for p, d in zip(m.PATTERNS, describe()))
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第26弾「心房細動・心房粗動、12パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第21弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に12個の一覧と見分けのポイント
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。前後のつなぎは洞調律 75/分
- 別の回（頻脈の回）では心房細動・心房粗動を代表1つずつしか扱わないので、この回でバリエーションを扱う
- 見分けのポイントを画面のひとことで出す：心房細動＝P波がなく R-R がバラバラ（①）、心房粗動＝のこぎり状のF波 約300/分（⑨）。最後の画面は「R-Rバラバラは細動、のこぎりは粗動」
- 各パターンのひとことのうしろに、看護師の動きを色の文字で出す（緑「→ 初めてなら報告」、橙「→ 脈拍と血圧も確認」、紫「→ 12誘導で確認」、赤「→ すぐ報告」）。ナレーションでは「すぐ報告」と言わない
- 名前の色で3つの群に分けている：心房細動のf波と心拍数（①〜④、水色）、心房細動でQRSの形・リズムが変わるもの（⑤〜⑧、黄）、心房粗動（⑨〜⑫、桃）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library／Eponymictionary（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない。「すぐ報告」は声で言わない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. 12パターンの選び方と並び（心房細動8・心房粗動4）。ほかに入れるべきもの（心房細動＋PVC、粗動の3:1、ジギタリス効果 など）や、外したほうがよいものはあるか
2. 色の文字（看護師の動き）の割り当て。とくに ①②⑨「→ 初めてなら報告」（新しく見つけた心房細動・心房粗動は医師へ。急ぎではない、という意味）、③④⑩「→ 脈拍と血圧も確認」、⑤⑥⑪「→ 12誘導で確認」、⑦⑧⑫「→ すぐ報告」は妥当か。④徐脈性や⑩2:1 を「すぐ報告」にすべきか
3. ① 粗いf波・② 細かいf波の描き方。LITFL の境目（0.5mm）に合わせ、粗い＝山から谷 約0.27mV、細かい＝約0.06mV にした。モニター（II誘導）で②を「心房細動」と言ってよいか（R-R の不規則で判断、と画面に出している）
4. ⑤ アシュマン現象：長い R-R → 短い R-R の拍だけ右脚ブロック型にした描き方と、II誘導での形（幅の広いS波）。「→ 12誘導で確認」（PVCとの区別）でよいか
5. ⑥ 脚ブロックを伴う心房細動を、右脚ブロック型で描いたこと（II誘導）。⑧ WPWの心房細動との見分け（形が全部同じ・速さがふつう）が伝わるか
6. ⑦ 心房細動＋完全房室ブロック（Regularised AF）：粗いf波＋幅の狭い接合部補充調律 48/分。LITFL ではジギタリス中毒の代表的な形とされる。キャプションでジギタリスにふれるべきか
7. ⑧ WPWの心房細動：平均230/分・最短300/分、デルタ波つきの幅広いQRSで、幅と大きさが拍ごとに少し変わる描き方。キャプションの「房室結節を抑える薬が危険になることがある」という書き方は看護師向けとして妥当か
8. ⑨〜⑫ 心房粗動：F波の形（II誘導で下向きの のこぎり）、⑩ 2:1 を「150/分で規則的なら粗動を疑う」とした言い方（LITFL：Suspect atrial flutter with 2:1 block whenever there is a regular narrow-complex tachycardia at 150 bpm）、⑪ 伝導比が変わると心房細動に似る、⑫ 1:1 を 300/分・幅の狭いQRSで描いたこと（実際は変行伝導で幅が広くなることもある）
9. 台本は1パターン1文に詰めた。短くしたことで医学的に誤解を招く文はないか（とくに ②「平らに見えても、f波の細かい心房細動」、⑦「完全房室ブロックを疑う」、⑪「細動に似る」、まとめ「R-Rがバラバラなら細動、のこぎりなら粗動」）
10. スマホの大きさで、① と ② のf波のちがい、⑨ のF波、⑤ の幅の広い1拍、⑦ の規則的なR-R が読み取れるか

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

    lines = ['第26弾 心房細動・心房粗動 12パターン ― 画面の文字', '',
             f'[見出し] {m.TITLE} 12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] モニター心電図で見分ける ／ {m.TITLE}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', f'[最後] {m.END_LINE} ／ 保存して見返してね',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel26.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
