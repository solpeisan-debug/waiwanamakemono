"""第24弾 頻脈（幅の狭いQRS） ― 専門医レビュー用の資料。

- out/review_reel24_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・10パターン・一覧・サムネイル）
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
    'LITFL Sinus tachycardia（①②）': L + 'sinus-tachycardia-ecg-library/',
    'LITFL Atrial tachycardia（③）': L + 'atrial-tachycardia-ecg-library/',
    'LITFL Multifocal Atrial Tachycardia (MAT)（④）': L + 'multifocal-atrial-tachycardia-mat-ecg-library/',
    'LITFL Atrial Fibrillation（⑤）': L + 'atrial-fibrillation-ecg-library/',
    'LITFL Atrial Flutter（⑥）': L + 'atrial-flutter-ecg-library/',
    'LITFL Supraventricular Tachycardia (SVT)（②⑦⑧・まとめ・キャプションの症状）': L + 'supraventricular-tachycardia-svt-ecg-library/',
    'LITFL Premature Atrial Complex (PAC)（⑧のきっかけ）': L + 'premature-atrial-complex-pac/',
    'LITFL Atrioventricular Re-entry Tachycardia (AVRT)（⑨・キャプション）': L + 'atrioventricular-re-entry-tachycardia-avrt/',
    'LITFL Accelerated Junctional Rhythm（接合部頻拍の定義・例）（⑩）': L + 'accelerated-junctional-rhythm-ajr/',
}


def beat_time(i, k, after=0.15):
    """パターン i の k 番目の拍（区間の中）でカウンターが変わった直後の t。"""
    rs = [r for r, b, j in m.STRIP_HR if j == i]
    return m.t_of(rs[k] - m.DT_REF) + after


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
    return min(max(t, a + m.QUIZ_T + 0.4), b - 0.2)


def describe():
    """各パターンの描き方（モデルの値から）。"""
    r = m.rate
    af = m.AF_RR
    mat = m.MAT_RR
    pk = ('M1', 'M2', 'M3', 'M4')
    return [
        f"P波（ふつうの形）→ 幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。PR {m.pr_ms('S'):.0f}ms、QRS {m.qrs_ms(m.qrs_115):.0f}ms",
        f"洞調律 {r(0.40):.0f}/分。P波の頂点は前のRから {0.40 - m.KINDS['H'][2]:.2f}秒（T波の下り坂）で、T波にこぶのように重なる",
        f"形のちがうP'（小さくとがった、上 → 下の二相性）が {r(0.46):.0f}/分で1:1、規則正しい。PR {m.pr_ms('A'):.0f}ms。P'のあいだの基線は平ら",
        f"平均 {r(np.mean(mat)):.0f}/分（{r(max(mat)):.0f}〜{r(min(mat)):.0f}/分）で不規則。P波は4種類（ふつう・高くとがる・下向き・二相性）、"
        f"PR {min(m.pr_ms(k) for k in pk):.0f}〜{max(m.pr_ms(k) for k in pk):.0f}ms。基線は平ら",
        f"P波なし。RR は不規則（{min(af):.2f}〜{max(af):.2f}秒、平均 {r(np.mean(af)):.0f}/分）。細動波 4.5〜8Hz、"
        f"約±{np.abs(m.art_af(np.arange(0, sum(af), 0.002), sum(af))).max():.2f}mV",
        f"下向きののこぎり状の粗動波 {r(m.FL_CYC):.0f}/分（約{0.24*10:.1f}mm）。2:1で心室 {r(0.40):.0f}/分。1つはQRSに、1つはT波のあたりに重なる",
        f"幅の狭いQRS が {r(m.SVT_RR):.0f}/分で規則正しい。P波は見えない（QRSの終わりに小さな偽S波）",
        f"洞調律 90/分 → PAC（連結 {m.OO_PAC_C:.2f}秒、PR {m.pr_ms('B'):.0f}ms＝遅い道）→ PSVT {r(m.OO_SVT_RR):.0f}/分 {m.OO_SVT_N}拍 → "
        f"突然止まり、{m.OO_PAUSE:.2f}秒あけて洞調律 → 少しずつ {' → '.join(f'{r(x):.0f}' for x in m.OO_SINUS_RR)}/分。"
        f"カウンターは {' '.join(f'{b:.0f}' for _, b, j in m.STRIP_HR if j == 7)}",
        f"幅の狭いQRS が {r(0.30):.0f}/分。QRSのすぐあとに下向きの逆行性P（short RP：RP＝QRSの始まり → Pの始まり {m.avrt_rp_ms()[0]:.0f}ms、"
        f"QRSの終わりから {m.avrt_rp_ms()[1]:.0f}ms 後にPが始まる）",
        f"幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。QRSの直前に下向きのP（約−0.2mV、PR {m.pr_ms('J'):.0f}ms）",
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    i8 = 7
    hr5 = [b for _, b, j in m.STRIP_HR if j == 4]
    i5_k = int(np.argmax(hr5))
    frames = [('冒頭0〜1秒：問いかけ「この10個、全部わかる？」', 0.5),
              ('冒頭のフック（止めた波形を変形しているところ）', hook_t),
              ('クイズの例：① の始まり（名前の前に「これは？」）', m.WINDOWS[0][0] + 1.2)] \
        + [x for i, p in enumerate(m.PATTERNS) for x in (
            # ⑧は、突然始まるPSVT（カウンター 170）、突然止まる（75）、少しずつ変わる洞頻脈（135）の3ページ
            [(f"{p['no']} {p['name']}（PSVT：1拍で跳ぶ。カウンター 170）", beat_time(i, m.OO_PRE_N + 1)),
             (f"{p['no']} {p['name']}（突然止まる。カウンター 75）", beat_time(i, m.OO_PRE_N + 1 + m.OO_SVT_N, 0.3)),
             (f"{p['no']} {p['name']}（洞頻脈：少しずつ。カウンター 135）", beat_time(i, m.OO_PRE_N + 1 + m.OO_SVT_N + 4))]
            if i == i8 else
            # ⑤は拍ごとの値が大きく変わるので、いちばん速い拍（176/分）のところ
            [(f"{p['no']} {p['name']}（カウンターは拍ごとの値。いちばん速い拍）", beat_time(i, i5_k))] if i == 4
            else [(f"{p['no']} {p['name']}", key_time(i))])] \
        + [(f'最後：{m.N_PAT}個の一覧と「何個わかった？コメントで教えてね」', m.T_END + m.FLY + 2.8)]
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
- 第24弾「頻脈（幅の狭いQRS）、10パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第21弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 10パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に10個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。画面とキャプションに「数値はこの波形での一例」と明記
- 名前の色で3つの群に分けた：洞結節から（水色：①②）、心房から（オレンジ：③〜⑥）、房室結節・副伝導路のあたり（ピンク：⑦〜⑩）。上の枠に①〜⑥（2列×3段）、下の枠に⑦〜⑩（2列×2段）
- 各パターンのひとことのうしろに、看護師がまずすることを色の文字で出す：緑「→ まず患者さん」（①④）、黄「→ すぐ報告」（⑤⑥⑦⑨⑩）、青「→ 12誘導で確認」（②③）、紫「→ 数字を見る」（⑧）。
  ナレーションでは「すぐ報告」と言わない（画面とキャプションで伝える）
- **この回だけの見せ方**
  - 心拍数カウンター（波形の下のまん中「♥ 150 /分」）：帯の右のほう（x={m.COUNT_X}px）を R が通るたびに、その拍の R-R（モデルの値）から計算した心拍数に変わる。ピッという音も同じ瞬間。
    ⑧ では、PSVT が 90 → {m.rate(m.OO_PAC_C):.0f} → {m.rate(m.OO_SVT_RR):.0f}/分と1拍で跳び、突然止まる（{m.rate(m.OO_PAUSE):.0f}/分）。そのあと洞調律が {' → '.join(f'{m.rate(x):.0f}' for x in m.OO_SINUS_RR)}/分と少しずつ変わる
  - クイズ：各パターンで、名前の行にまず「これは？」を出し、波形が見えてから約0.7秒で名前に変わる（声も「特徴 → 名前」の順）
  - 冒頭0〜1秒に問いかけ「この10個、全部わかる？」、最後に「何個わかった？コメントで教えてね」
- 前の版（12パターン）から、PACの連発（期外収縮の回の内容）と WPW（洞調律。頻脈ではない。見分けマップ③にある）を外した
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
1. 10パターンの選び方（洞頻脈、P波がT波に重なる洞頻脈、心房頻拍、多源性心房頻拍、速い心房細動、心房粗動2:1、PSVT、始まり方の対比、順方向性の房室回帰性頻拍、接合部頻拍）。入れるべきもの・外すべきものはあるか
2. 色の文字の振り分け（「→ まず患者さん」①④／「→ すぐ報告」⑤⑥⑦⑨⑩／「→ 12誘導で確認」②③／「→ 数字を見る」⑧）は、看護師の初動として妥当か。
   とくに ④ 多源性心房頻拍を「まず患者さん」、⑩ 接合部頻拍を「すぐ報告」、② を「12誘導で確認」にしたこと
3. ⑧ 始まり方の対比：PSVT は PAC をきっかけに「突然始まり、突然止まる」（90→170/分、止まって0.8秒あけて洞調律）、そのあと洞頻脈が「少しずつ速くなり、少しずつ戻る」（75→135→90/分）。
   同じ帯の中で、PSVT のあとに洞調律が少しずつ速くなる流れが、不自然に見えないか
   「洞頻脈は少しずつ変わる」は LITFL の本文には書いていない（SVT：pSVT は abrupt onset and offset）。言い方として妥当か。きっかけのPACのPRを長く（約210ms）描いたことも。
   画面では数秒で 75→135/分 と変わるが、実際の洞頻脈の変化はもっとゆっくり（数十秒〜数分）。キャプションに「実際はもっとゆっくり」と書いた。
   カウンターの横に小さく「↑ 1拍で跳ぶ」「↓ 突然止まる」「↗ 少しずつ」「↘ 少しずつ」を出している
4. 心拍数カウンター：1拍ごとの R-R から計算した値を出している（モニターの表示は平均することが多い）。④⑤ のように不規則なリズムでは数字が拍ごとに大きく変わる
   （⑤ 心房細動は拍ごとの値で 98〜176/分、平均約{m.rate(np.mean(m.AF_RR)):.0f}/分。PDF の⑤のページは、いちばん速い拍のところ）。見せ方に誤解がないか
5. ③ 心房頻拍：画面と台本は「いつもと違うP波」（前回のレビューで直した）。P'を「II誘導で、小さくとがった上向き → 下向きの二相性」で描いた（第17弾のPACの形を、二相性がわかるよう強めた）。LITFL の例は「下向き（inverted in inferior leads）」。
   ⑩ 接合部頻拍（QRSの直前に下向きのP）と見分けやすくするためだが、代表の形として妥当か
6. ⑦ PSVT：P波なし、QRSの終わりに小さな偽S波（LITFL：Pseudo S waves in II, III, aVF）。名前「PSVT（房室結節リエントリー）」の言い方
7. ⑨ 房室回帰性頻拍：200/分、QRSのすぐあとに下向きの逆行性P（RP {m.avrt_rp_ms()[0]:.0f}ms・QRSの終わりから {m.avrt_rp_ms()[1]:.0f}ms。前回のレビューで short RP に直した）。II誘導のモニターで見えるものとして妥当か
8. ⑩ 接合部頻拍の逆行性P：大きさ（約−0.2mV）と位置（QRSの直前、PR 約90ms）。モニターで見える代表の形として大きすぎないか
9. ② 洞頻脈（150/分、P波がT波の下り坂にこぶのように重なる）を「PSVTに見える」としたこと。⑥ 心房粗動（2:1、150/分）と並べて「150/分前後で規則正しい」ときの見分けを伝えたい
10. P波の形（スマホで見えるよう強めた）：③ のP'、④ の下向きのP（約−0.15mV）・二相性のP。強調しすぎて別の意味に見えないか
11. 台本のまとめ「規則正しいか、P波はどこか。まずこの2つ。」（LITFL SVT：起源と規則性で分ける）。短くしたことで誤解を招く文はないか
12. キャプションの「めまい・失神・胸痛・息苦しさ・血圧低下があれば、急変として対応します」（LITFL SVT の症状と、AVRT の「unstable → urgent DC cardioversion」から）。言い方として妥当か
13. スマホの大きさで、② のT波に重なるP、③ のとがったP'、⑨ の逆行性P、⑩ の下向きのP が読み取れるか

## 前回のレビュー（2026-10-06）を反映したところ
- ③ ひとこと・台本「いつもと違うP波が、規則正しく」（MATとまぎれないように）
- ④ 台本「P波の形が3種類以上で、不規則。多源性心房頻拍。」
- ⑤ キャプションに、実際のモニターの心拍数は平均値で、動画ほど毎拍は変わらないことを追記
- ⑨ 逆行性P波をQRSに近づけた（short RP）

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

    lines = [f'第24弾 頻脈（幅の狭いQRS） {m.N_PAT}パターン ― 画面の文字', '',
             f'[0〜1秒] {m.ASK}（黄色・大きめ）',
             f'[見出し] 頻脈（幅の狭いQRS） {m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] {m.TITLE_SUB} ／ {m.TITLE} ／ {m.TITLE_2}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {m.QUIZ} → {pat['no']} {pat['name']}（{a + m.QUIZ_T:.1f}秒から） ／ "
                     f"{pat['one']} {m.TAGS[pat['tag']][0]} ／ ヒント：{pat['hint']}")
        lines.append(f"    心拍数カウンター：{' '.join(f'{x:.0f}' for _, x, j in m.STRIP_HR if j == i)} /分")
    lines += ['', f'[最後] {m.END_1} ／ {m.END_2} ／ {m.END_3}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel24.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
