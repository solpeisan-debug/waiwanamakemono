"""第26弾 心房細動・心房粗動 ― 専門医レビュー用の資料。

- out/review_reel26_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・14パターン・一覧・サムネイル）
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
    'LITFL Sinus Node Dysfunction (Sick Sinus Syndrome)（徐脈頻脈症候群）': L + 'sinus-node-dysfunction-sick-sinus-syndrome/',
}


def key_time(i):
    """パターン i のレビュー用のコマ。ふつうは紹介の終わりの0.5秒前（中部の帯がそのパターンだけで埋まり、名前とひとことがまだ出ている）。
    色を付ける範囲があるもの（① 心房細動の始まり・⑥ アシュマン現象）は、その始まりが中央の少し右に来るとき（左に、その前が見える）。
    ⑩ 徐脈頻脈症候群は、休みが全部入って次の洞調律の拍が右端に来たとき（タイマーが止まった値）。"""
    a, b = m.WINDOWS[i]
    pat = m.PATTERNS[i]
    if i == m.I_TB:
        return m.t_of(m.SEGS[i][0] + m.TB_P1 + 0.35 - m.HALF)
    if i == m.I_ASH:      # 幅の広い拍が x≈880 に来たとき（長い R-R・短い R-R の棒と「長い」「短い」がそろって見える）
        return m.t_of(m.SEGS[i][0] + m.T_ASH - (880 - m.XC) / m.F_PXS)
    if pat['hl'] is not m.ALL:
        lo, hi = pat['hl'][0]
        t = m.t_of(m.SEGS[i][0] + lo + 0.10 - 0.30)
        return min(max(t, a + 0.6), b - 0.5)
    return b - 0.5


def timer_time():
    """⑩ のタイマーが数え上がっている途中（休みが 1.6秒ぶん入ったところ。左に心房細動の終わりが見える）。"""
    return m.t_of(m.SEGS[m.I_TB][0] + m.TB_P0 + 1.6 - m.HALF)


def describe():
    """各パターンの描き方（モデルの値から）。"""
    P = m.PAT
    fc, fm, ff = (m.f_peak(P[k])[0] for k in ('②', '④', '③'))
    fl = m.f_peak(P['⑪'])[0]
    q = m._qrs_ms
    rr = lambda x: f'{min(x):.2f}〜{max(x):.2f}秒'
    return [
        f'洞調律 {60/0.8:.0f}/分を{len(m.PAF_SINUS)}拍 → 直前のT波の終わりに早いP\'（PAC）→ そこからP波がなくなり、R-R が不規則（{rr(m.RR_PAF)}、平均{m._rate(m.RR_PAF):.0f}/分）、f波 約{fm:.2f}mV',
        f'P波なし。R-R が不規則（{rr(m.RR_COARSE)}、平均{m._rate(m.RR_COARSE):.0f}/分）。f波 5〜8Hz の不規則な揺れ、山から谷 約{fc:.2f}mV（粗い）',
        f'P波なし。R-R が不規則（{rr(m.RR_FINE)}、平均{m._rate(m.RR_FINE):.0f}/分）。f波は山から谷 約{ff:.2f}mV（細かい。基線はほぼ平ら。P波もない）',
        f'R-R 不規則で速い（平均{m._rate(m.RR_FAST):.0f}/分、{60/max(m.RR_FAST):.0f}〜{60/min(m.RR_FAST):.0f}/分）。幅の狭いQRS、f波 約{fm:.2f}mV',
        f'R-R 不規則で遅い（平均{m._rate(m.RR_SLOW):.0f}/分、{60/max(m.RR_SLOW):.0f}〜{60/min(m.RR_SLOW):.0f}/分）。f波 約{fm:.2f}mV',
        f'心房細動（平均{m._rate(m.RR_ASH):.0f}/分）。長い R-R {m.RR_ASH[m.ASH_K-2]:.2f}秒の直後、短い R-R {m.RR_ASH[m.ASH_K-1]:.2f}秒で来た1拍だけ'
        f'右脚ブロック型の幅の広いQRS（約{q(m.qrs_aberrant):.0f}ms、ふつうの拍は約{q(m.qrs_normal):.0f}ms）',
        f'心房細動（平均{m._rate(m.RR_BBB):.0f}/分、R-R 不規則）。全部の拍が同じ形の幅の広いQRS（右脚ブロック型、約{q(m.qrs_aberrant):.0f}ms）',
        f'粗いf波（約{fc:.2f}mV）なのに、R-R が {m.RR_CHB[0]:.2f}秒で規則的（{60/m.RR_CHB[0]:.0f}/分）。幅の狭い接合部補充調律（LITFL：Regularised AF）',
        f'R-R 不規則でとても速い（平均{m._rate(m.RR_WPW):.0f}/分、{60/max(m.RR_WPW):.0f}〜{60/min(m.RR_WPW):.0f}/分）。デルタ波つきの幅の広いQRS'
        f'（約{q(m._preex(*m.PREEX["D1"], with_t=False)):.0f}〜{q(m._preex(*m.PREEX["D3"], with_t=False)):.0f}ms、拍ごとに幅と大きさが少し変わる。向き＝軸は同じ）、逆向きのT',
        f'心房細動（平均{m._rate(m.RR_TB_AF):.0f}/分）が止まる → 最後の拍から {m.TB_PAUSE:.1f}秒の休み（f波もP波もない平らな線）→ 遅い洞調律 {60/m.TB_SINUS_RR:.0f}/分。'
        f'休みのあいだ「休み ◯.◯秒」がカウントアップし、{m.TB_PAUSE:.1f}秒で止まる',
        f'II誘導で下向きのF波（のこぎり状）{60/m.FF:.0f}/分、山から谷 約{fl:.2f}mV。4:1伝導で R-R {4*m.FF:.1f}秒（{60/(4*m.FF):.0f}/分）。T波は小さめ',
        f'同じF波。2:1伝導で R-R {2*m.FF:.1f}秒（{60/(2*m.FF):.0f}/分）で規則的。F波の1つはQRS・T波に重なる（実際は見えにくいことが多いので、画面は「150/分で規則的なら粗動を疑う」）',
        f'同じF波。伝導比が {"・".join(f"{round(x/m.FF)}:1" for x in m.RR_VAR)} と変わり、R-R が不規則（どれも F-F {m.FF:.1f}秒の倍数、平均{m._rate(m.RR_VAR):.0f}/分）',
        f'F波が1:1で全部伝わり、幅の狭いQRSが {60/m.FF:.0f}/分で規則的（F波は 約{m.f_peak(P["⑭"])[0]:.2f}mV、T波は小さく早い）',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭0.5秒（問いかけ「細動？粗動？／見分けられる？」）', 0.5),
              ('冒頭のフック（止めた波形を変形しているところ）', hook_t)]
    for i, p in enumerate(m.PATTERNS):
        if i == m.I_TB:
            frames.append((f"{p['no']} {p['name']}（休みのタイマーが数え上がっている途中）", timer_time()))
        frames.append((f"{p['no']} {p['name']}", key_time(i)))
    frames.append((f'最後：{m.N_PAT}個の一覧（見分けのポイント）', m.T_END + m.FLY + 2.0))
    frames.append((f'最後：{m.N_PAT}個の一覧（コメントの呼びかけに入れかわったところ）', m.T_END + m.FLY + m.END_SWAP + 0.8))
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
- 第26弾「心房細動・心房粗動、14パターン」。縦 1080×1920・60fps・ナレーション入り（下の台本で録音済み）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第21弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 14パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠（上2列×4段・下2列×3段）に移り、ミニ波形として流れ続ける → 最後に14個の一覧と見分けのポイント
- この回だけの見せ方：
  - **R-R のものさし**：波形の下に、拍と拍のあいだの長さを横棒で出す（棒の長さ＝モデルの R の時刻の差）。心房細動は棒がバラバラ、心房粗動（伝導比が一定）は棒がそろう。⑥では「長い」「短い」の名札を棒の下に出す
  - **休みのタイマー**（⑩）：休みが画面に入ってくると「休み ◯.◯秒」が数え上がり、{m.TB_PAUSE:.1f}秒で止まる
  - 冒頭に問いかけ「細動？粗動？／見分けられる？」、最後に「何個わかった？コメントで教えてね」
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。前後のつなぎは洞調律 75/分。背景の方眼は心電図用紙と同じ目盛り（細い線 1mm＝0.04秒・0.1mV、太い線 5mm＝0.2秒・0.5mV）
- 別の回（頻脈の回）では心房細動・心房粗動を代表1つずつしか扱わないので、この回でバリエーションを扱う
- 見分けのポイントを画面のひとことで出す：心房細動＝P波がなく R-R がバラバラ（②）、心房粗動＝のこぎり状のF波 約300/分（⑪）。最後の画面は「のこぎりは粗動、R-Rバラバラは細動」
- 各パターンのひとことのうしろに、看護師の動きを色の文字で出す（緑「→ 初めてなら報告」、橙「→ 脈拍と血圧も確認」、紫「→ 12誘導で確認」、赤「→ すぐ報告」）。ナレーションでは「すぐ報告」と言わない
- 名前の色：心房細動のはじまり・f波・心拍数（①〜⑤、水色）、QRSの形・リズムが変わるもの（⑥〜⑨、黄）、止まるとき（⑩、赤みの橙）、心房粗動（⑪〜⑭、桃）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library／Eponymictionary（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音済みの台本。数字は画面に出ているので、声では読まない。「すぐ報告」は声で言わない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. 14パターンの選び方と並び（はじまり → f波 → 心拍数 → QRSの形 → 止まるとき → 心房粗動）。ほかに入れるべきもの・外したほうがよいものはあるか
2. ① 心房細動の始まり：洞調律3拍 → T波の終わりのPAC → 心房細動、という描き方。色の文字「→ 初めてなら報告」でよいか
3. ⑩ 徐脈頻脈症候群：心房細動が止まったあと {m.TB_PAUSE:.1f}秒の休み（LITFL：洞停止は3秒超）→ 遅い洞調律60/分。「→ すぐ報告」、台本「細動が止まったあとの長い休みは、失神の原因に」は妥当か。休みのタイマーの見せ方で誤解はないか
4. R-R のものさし（波形の下の横棒）：心房細動＝バラバラ、心房粗動＝そろう、の見せ方で誤解はないか（⑬ 伝導比が変わる心房粗動では棒の長さが 0.2秒の倍数の数種類になる、⑧ 心房細動＋完全房室ブロックでは棒がそろう、⑥ アシュマン現象の「長い → 短い」）
5. 色の文字（看護師の動き）の割り当て。①②③⑪「→ 初めてなら報告」、④⑤⑫「→ 脈拍と血圧も確認」、⑥⑦⑬「→ 12誘導で確認」、⑧⑨⑩⑭「→ すぐ報告」。キャプションの 🆕 の行（どのパターンでも初めてなら報告、症状があればすぐ報告）とあわせて、誤解はないか
6. ② 粗いf波・③ 細かいf波の描き方（LITFL の境目 0.5mm に合わせ、粗い＝山から谷 約0.27mV、細かい＝約0.06mV）。③のひとこと「P波なし・基線は平ら。R-Rで判断」と台本「平らでも、R-Rがバラバラなら心房細動」は妥当か
7. ⑥ アシュマン現象・⑦ 脚ブロックを右脚ブロック型（II誘導で幅の広いS波）で描いたこと。⑨ WPWの心房細動との見分けが伝わるか
8. ⑧ 心房細動＋完全房室ブロック（Regularised AF）：粗いf波＋幅の狭い接合部補充調律 48/分。キャプションのジギタリス中毒の一文は妥当か
9. ⑨ WPWの心房細動の描き方と、キャプションの薬の注意（房室結節を抑える薬で、かえって速くなり、心室細動に移ることがある）
10. ⑪〜⑭ 心房粗動：F波の形（II誘導で下向きの のこぎり）、⑫ 2:1 を「150/分で規則的なら粗動を疑う」とした言い方（LITFL：Suspect atrial flutter with 2:1 block whenever there is a regular narrow-complex tachycardia at 150 bpm）、⑭ 1:1 を 300/分・幅の狭いQRSで描いたこと（キャプションで、F波がほとんど見えず幅広くなることもある、とふれている）
11. 台本は1パターン1文に詰めた。短くしたことで医学的に誤解を招く文はないか（とくに ①「洞調律から急にバラバラ」、③、⑧「完全房室ブロックを疑う」、⑩、⑬「細動に似る」、まとめ「のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動」）

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

    lines = [f'第26弾 心房細動・心房粗動 {m.N_PAT}パターン ― 画面の文字', '',
             f'[見出し] {m.TITLE} {m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 0〜2.4秒] {"／".join(m.QUESTION)}（黄・2行・{m.QUESTION_SIZE}px。出ているあいだは「モニター心電図で見分ける」を消す）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] モニター心電図で見分ける ／ {m.TITLE}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', f'[⑩ 休みのあいだ] 休み 1.1秒 → … → {m.TB_PAUSE:.1f}秒（カウントアップ）',
              '[波形の下] R-R のものさし（拍と拍のあいだの横棒。左に「R-R」）',
              '', f'[最後] {m.END_LINE} ／ 保存して見返してね　→ {m.END_SWAP:.0f}秒後に上の行が「{m.COMMENT}」（黄・42px）に入れかわる',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel26.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
