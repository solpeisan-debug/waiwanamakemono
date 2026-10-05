"""第24弾 頻脈（幅の狭いQRS） ― 専門医レビュー用の資料。

- out/review_reel24_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・12パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel24.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel24 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL Sinus tachycardia（①⑫）': L + 'sinus-tachycardia-ecg-library/',
    'LITFL Premature Atrial Complex（PAC）（②⑧）': L + 'premature-atrial-complex-pac/',
    'LITFL Atrial tachycardia（③）': L + 'atrial-tachycardia-ecg-library/',
    'LITFL Multifocal Atrial Tachycardia (MAT)（④）': L + 'multifocal-atrial-tachycardia-mat-ecg-library/',
    'LITFL Atrial Fibrillation（⑤）': L + 'atrial-fibrillation-ecg-library/',
    'LITFL Atrial Flutter（⑥）': L + 'atrial-flutter-ecg-library/',
    'LITFL Supraventricular Tachycardia (SVT)（⑦⑧・まとめ・キャプションの症状）': L + 'supraventricular-tachycardia-svt-ecg-library/',
    'LITFL Atrioventricular Re-entry Tachycardia (AVRT)（⑧⑨・キャプション）': L + 'atrioventricular-re-entry-tachycardia-avrt/',
    'LITFL Pre-excitation Syndromes（WPW）（⑩）': L + 'pre-excitation-syndromes-ecg-library/',
    'LITFL Accelerated Junctional Rhythm（接合部頻拍の定義・例）（⑪）': L + 'accelerated-junctional-rhythm-ajr/',
}


def key_time(i, c=None):
    """パターン i の見どころ（区間の始まりからの時刻 c）が、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    if c is not None:
        pass
    elif pat['hl'] is m.ALL:
        c = min(pat['L'], 2.0) / 2 + pat['L']
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2
    t = m.t_of(m.SEGS[i][0] + c + 0.25)
    a, b = m.WINDOWS[i]
    return min(max(t, a + 0.6), b - 0.2)


def describe():
    """各パターンの描き方（モデルの値から）。"""
    r = m.rate
    af = m.AF_RR
    mat = m.MAT_RR
    return [
        f"P波（ふつうの形）→ 幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。PR {m.pr_ms('S'):.0f}ms、QRS {m.qrs_ms(m.qrs_115):.0f}ms",
        f"洞調律 75/分 → 形のちがうP'（小さくとがった、上 → 下の二相性）のPACが3つ（連結 0.48秒、間隔 0.44秒＝{r(0.44):.0f}/分、PR {m.pr_ms('A'):.0f}ms）"
        f" → 0.85秒あけて洞調律に戻る",
        f"PACと同じ形のP'が {r(0.46):.0f}/分で1:1、規則正しい。PR {m.pr_ms('A'):.0f}ms。P'のあいだの基線は平ら",
        f"平均 {r(np.mean(mat)):.0f}/分（{r(max(mat)):.0f}〜{r(min(mat)):.0f}/分）で不規則。P波は4種類（ふつう・高くとがる・下向き・二相性）、"
        f"PR {min(m.pr_ms(k) for k in ('M1', 'M2', 'M3', 'M4')):.0f}〜{max(m.pr_ms(k) for k in ('M1', 'M2', 'M3', 'M4')):.0f}ms。基線は平ら",
        f"P波なし。RR は不規則（{min(af):.2f}〜{max(af):.2f}秒、平均 {r(np.mean(af)):.0f}/分）。細動波 4.5〜8Hz、"
        f"約±{np.abs(m.art_af(np.arange(0, sum(af), 0.002), sum(af))).max():.2f}mV",
        f"下向きののこぎり状の粗動波 {r(m.FL_CYC):.0f}/分（約{0.24*10:.1f}mm）。2:1で心室 {r(0.40):.0f}/分。1つはQRSに、1つはT波のあたりに重なる",
        f"幅の狭いQRS が {r(m.SVT_RR):.0f}/分で規則正しい。P波は見えない（QRSの終わりに小さな偽S波）",
        f"洞調律 80/分 → PAC（連結 0.45秒、PR {m.pr_ms('B'):.0f}ms＝遅い道）→ PSVT {r(m.SVT_RR):.0f}/分 {m.ON_N}拍 → 突然止まり、"
        f"{m.ON_RESUME - m.ON_STOP:.2f}秒あけて洞調律",
        f"幅の狭いQRS が {r(0.30):.0f}/分。QRSのあと {m.AVRT_RP*1000:.0f}ms に下向きの逆行性P（STの上・T波の始まりの切れこみ）",
        f"洞調律 {r(0.75):.0f}/分。PR {m.pr_ms('X'):.0f}ms、デルタ波でQRSの立ち上がりがなだらか、QRS {m.qrs_ms(m.qrs_wpw):.0f}ms。"
        f"T波はQRSと逆向き（浅く下向き）",
        f"幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。QRSの直前に下向きのP（PR {m.pr_ms('J'):.0f}ms）",
        f"洞調律 {r(0.40):.0f}/分。P波の頂点は前のRから {0.40 - m.KINDS['H'][2]:.2f}秒（T波の下り坂）で、T波にこぶのように重なる",
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭のフック（止めた波形を変形しているところ）', hook_t)] \
        + [x for i, p in enumerate(m.PATTERNS) for x in (
            # ⑧は、始まり（洞調律 → PAC → PSVT）と終わり（突然止まる → 間）を2ページに分ける
            [(f"{p['no']} {p['name']}（始まり）", key_time(i, m.ON_PAC + 0.65)),
             (f"{p['no']} {p['name']}（終わり）", m.WINDOWS[i][1] - 0.2)] if p['no'] == '⑧'
            else [(f"{p['no']} {p['name']}", key_time(i))])] \
        + [('最後：12個の一覧', m.T_END + m.FLY + 2.5)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}（{t:.1f}秒）')
    thumb = os.path.join(OUT, 'thumb_reel24_list.png')
    m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙・透かしなし）')
    fpdf = os.path.join(OUT, 'review_reel24_frames.pdf')
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
- 第24弾「頻脈（幅の狭いQRS）、12パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第21弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に12個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。画面とキャプションに「数値はこの波形での一例」と明記
- 名前の色で3つの群に分けた：洞結節から（水色：①⑫）、心房から（オレンジ：②〜⑥）、房室結節・副伝導路のあたり（ピンク：⑦〜⑪）
- 各パターンのひとことのうしろに、看護師がまずすることを色の文字で出す：緑「→ まず患者さん」（①②④）、黄「→ すぐ報告」（⑤⑥⑦⑨⑪）、青「→ 12誘導で確認」（③⑧⑩⑫）。
  ナレーションでは「すぐ報告」と言わない（画面とキャプションで伝える）
- 心房細動・心房粗動のくわしいバリエーション（f波の粗い・細かい、伝導比、変行伝導）は別の回（第26弾）で扱うので、ここでは代表の1つずつ。幅の広いQRSの頻拍も別の回（第27弾）
- 出典は LITFL ECG Library（下に一覧）。LITFL 以外の資料は使っていない

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。1パターン1文・声で3〜4秒。数字は画面に出ているので、声では読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. 12パターンの選び方。ユーザーの候補（洞頻脈、速い心房細動、心房粗動2:1、PSVT、順方向性の房室回帰性頻拍、心房頻拍、多源性心房頻拍、接合部頻拍、WPW、PSVTの始まりと終わり、見分けにくい例）に、② PACの連発（3連）を足して12にした。
   入れるべきもの・外すべきものはあるか（例：洞結節リエントリー頻拍、ブロックを伴う心房頻拍、不適切洞頻脈 など）
2. 色の文字の振り分け（「→ まず患者さん」①②④／「→ すぐ報告」⑤⑥⑦⑨⑪／「→ 12誘導で確認」③⑧⑩⑫）は、看護師の初動として妥当か。
   とくに ② PACの連発・④ 多源性心房頻拍を「まず患者さん」、⑪ 接合部頻拍を「すぐ報告」、③ 心房頻拍を「12誘導で確認」にしたこと
3. ③ 心房頻拍：P'を「II誘導で、小さくとがった上向き → 下向きの二相性」で描いた（第17弾のPACの形を、二相性がわかるよう強めた）。LITFL の例は「下向き（inverted in inferior leads）」。
   ⑪ 接合部頻拍（QRSの直前に下向きのP、PR 約80ms）と見分けやすくするためだが、代表の形として妥当か
4. ⑦ PSVT：P波なし、QRSの終わりに小さな偽S波（LITFL：Pseudo S waves in II, III, aVF）。名前「PSVT（房室結節リエントリー）」の言い方
5. ⑧ 始まりと終わり：きっかけのPACのPRを長く（約240ms）描いた（遅い道を通る）。止まったあと約1秒あけて洞調律に戻る描き方。
   画面「→ 12誘導で確認」とキャプション「PSVTが止まったあと（WPWが見えることも）」（LITFL AVRT：止まったあとの12誘導でWPWパターンが見えて、順方向性の房室回帰性頻拍とわかる例）
6. ⑨ 房室回帰性頻拍：200/分、QRSのあと約115msに下向きの逆行性P（T波の始まりの切れこみ）。II誘導のモニターで見えるものとして妥当か
7. ⑩ WPW：洞調律で PR 約100ms・デルタ波・QRS 約130ms・T波は浅く下向き。「WPW（洞調律のとき）」という名前（「WPW症候群」とは言っていない）。
   頻脈の回に「頻脈ではない波形」を入れたことに誤解がないか
8. ⑫ P波が隠れた洞頻脈（150/分、P波がT波の下り坂にこぶのように重なる）を「PSVTに見える」としたこと。⑥ 心房粗動（2:1、150/分）と並べて「150/分前後で規則正しい」ときの見分けを伝えたい
9. 台本のまとめ「規則正しいか、P波はどこか。まずこの2つ。」（LITFL SVT：起源と規則性で分ける）。短くしたことで誤解を招く文はないか
10. キャプションの「めまい・失神・胸痛・息苦しさ・血圧低下があれば、急変として対応します」（LITFL SVT の症状と、AVRT の「unstable → urgent DC cardioversion」から）。言い方として妥当か
11. ⑪ 接合部頻拍の逆行性P：大きさ（約−0.2mV）と位置（QRSの直前、PR 約90ms）。モニターで見える代表の形として大きすぎないか
12. P波の形（スマホで見えるよう、検査のあとで強めた）：③ のP'（とがった上向き → 下向きの二相性）、④ の下向きのP（約−0.15mV）・二相性のP、⑩ のデルタ波（立ち上がりのなだらかな部分を大きく。QRS 約140ms）。強調しすぎて別の意味に見えないか
13. スマホの大きさで、② のP'、③ のとがったP'、⑨ の逆行性P、⑩ のデルタ波、⑪ の下向きのP、⑫ のT波に重なるP が読み取れるか

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

    lines = ['第24弾 頻脈（幅の狭いQRS） 12パターン ― 画面の文字', '',
             '[見出し] 頻脈（幅の狭いQRS） 12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] {m.TITLE_SUB} ／ {m.TITLE} ／ {m.TITLE_2}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']} {m.TAGS[pat['tag']][0]} ／ ヒント：{pat['hint']}")
    lines += ['', f'[最後] {m.END_1} ／ {m.END_2}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel24.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
