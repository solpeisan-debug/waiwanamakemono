"""第25弾 高カリウム血症とQT（電解質） ― 専門医レビュー用の資料。

- out/review_reel25_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・11パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel25.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

from PIL import Image

import align_vo as vo
import make_reel25 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL ECG Library: Hyperkalaemia': L + 'hyperkalaemia-ecg-library/',
    'LITFL ECG Library: Hypokalaemia': L + 'hypokalaemia-ecg-library/',
    'LITFL ECG Library: Hypercalcaemia': L + 'hypercalcaemia-ecg-library/',
    'LITFL ECG Library: Hypocalcaemia': L + 'hypocalcaemia-ecg-library/',
    'LITFL ECG Library: Hypomagnesaemia': L + 'hypomagnesaemia-ecg-library/',
    'LITFL ECG Library: QT Interval': L + 'qt-interval-ecg-library/',
    'LITFL ECG Library: U Wave': L + 'u-wave-ecg-library/',
    'LITFL ECG Library: T Wave（Peaked T waves）': L + 't-wave-ecg-library/',
    'LITFL ECG Library: Digoxin Effect': L + 'digoxin-effect-ecg-library/',
}


def key_time(i):
    """パターン i の見どころが、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    if pat['hl'] is m.ALL:
        c = min(pat['L'], 2.0) / 2 + pat['L']
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2
    t = m.t_of(m.SEGS[i][0] + c + 0.25)
    a, b = m.WINDOWS[i]
    return min(max(t, a + 0.6), b - 0.2)


def _ut(kind):
    b = m.KINDS[kind]
    return b.part(m._TT, 'u').max() / b.part(m._TT, 't').max()


def _f(x):
    return f'{x:.0f}'


def describe():
    """各パターンの描き方（モデルの値から）。"""
    K = m.KINDS
    out = []
    for pat in m.PATTERNS:
        b = K[pat['kind']]
        me = m.measure(pat['kind'], pat['rr'])
        tv = b.part(m._TT, 't').max() if b.t is not None else 0.0
        rv = b.part(m._TT, 'qrs').max()
        base = f"{me['rate']:.0f}/分"
        if me['pr'] is not None:
            base += f"、PR {_f(me['pr'])}ms"
        else:
            base += '、P波なし'
        if me['qrs'] is not None:
            base += f"、QRS {_f(me['qrs'])}ms"
        if 'qt' in me:
            lab = 'QU' if b.u_fused else 'QT'
            base += f"、{lab} {_f(me['qt'])}ms（{lab}c {_f(me['qtc'])}ms）"
        k = pat['kind']
        if k == 'N':
            extra = f"T波 {tv:.2f}mV（R {rv:.2f}mV）。QT は RR（{m.RR*1000:.0f}ms）の半分より短い"
        elif k == 'T1':
            extra = f"T波が高く（{tv:.2f}mV、R の {tv/rv:.0%}）、幅が狭く、左右対称で先がとがる。P波・QRSは①と同じ"
        elif k == 'K2':
            extra = f"P波を低く（{b.p[1]:.3f}mV、①は {m.P_N[1]:.2f}mV）幅広く（σ {b.p[2]*1000:.0f}ms、①は {m.P_N[2]*1000:.0f}ms）。T波 {tv:.2f}mV"
        elif k == 'K3':
            extra = f"P波なしの遅い補充調律。QRSが少し広がる。T波 {tv:.2f}mV"
        elif k == 'K4':
            extra = f"幅が広く形のくずれたQRS（約{_f(me['qrs'])}ms、R {rv:.2f}mV・深いS）が、とがったT波（{tv:.2f}mV）とつながる。P波なし"
        elif k == 'SW':
            v = m.wave_from(m.periodic_beats(pat, -2, 6), m._TT + 2.0)
            extra = f'QRSとTが1つのなめらかな波（上 {v.max():.2f}mV・下 {-v.min():.2f}mV）になり、くり返す。P波なし'
        elif k in ('L1', 'L2'):
            uv = b.part(m._TT, 'u').max(); st = -b.part(m._TT, 'st').min()
            extra = f"T波 {tv:.2f}mV・U波 {uv:.2f}mV（U/T {uv/tv:.1f}）・ST低下 最大 {st:.2f}mV"
            if k == 'L2':
                extra += f"。P波を高く（{b.p[1]:.2f}mV）。U波がT波とつながる（QU）"
        elif k == 'C1':
            extra = f"ST部分（平らな部分）を長くし、T波の形・高さ（{tv:.2f}mV）は①と同じ"
        elif k == 'D1':
            extra = f"T波を遅く、幅広く、少し低く（{tv:.2f}mV）。STの平らな部分は目立たない（⑨とのちがい）"
        elif k == 'C2':
            extra = f"STがほとんどなく、T波（{tv:.2f}mV）がQRSのすぐあとに始まる"
        else:
            extra = ''
        out.append(f'{base}。{extra}')
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭（0秒）：問いかけ「この変化、気づける？」とタイトル', 0.0),
              ('冒頭のフック（止めた波形を変形しているところ）', hook_t)] \
        + [(f"{p['no']} {p['name']}", key_time(i)) for i, p in enumerate(m.PATTERNS)] \
        + [('最後：11個の一覧（「保存して見返してね」「何個わかった？コメントで教えてね」）', m.T_END + m.FLY + 3.2)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}')
    thumb = os.path.join(OUT, 'thumb_reel25_list.png')
    if not os.path.exists(thumb):
        m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel25_frames.pdf')
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
- 第25弾「高カリウム血症とQT（電解質）、11パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人。透析・腎不全・利尿薬の患者さんを受け持つ）
- 第17〜21弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 11パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に11個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。基準の拍は60/分（RR 1.0秒なので QTc（Bazett）＝QT）
- 上の6つは高カリウムの進み方の順（①基準 → ②テント状T波 → ③PR延長・P波平坦 → ④P波消失・徐脈 → ⑤QRS幅の拡大 → ⑥サイン波）。波形が1本につながって、段階が続けて変わっていく
- 下の5つはQTのまわり（⑦⑧低K、⑨低Ca・⑩薬剤などのQT延長、⑪高CaのQT短縮）。R on T・トルサードは前の回（第21弾）で扱ったので、ここでは「QT延長」まで。低マグネシウム血症はキャプションでふれる
- 前の版（12パターン）からジギタリス効果を外した（電解質でもQTでもなく、薬の効果なので浮くため）
- この回だけの見せ方：
  - **基準のゴースト**：②〜⑪ の紹介中（⑥サイン波は除く）、中部の帯に①基準の拍を、そのパターンの拍と同じR頂点の位置に白っぽくうすく重ねる（どこが変わったかが分かるように）。①の枠の名前のうしろに「＝下のうすい線」、②③のあいだは帯の下に「うすい線＝①基準」。⑥はとがったQRSがサイン波を突き抜けて誤解を招くので重ねない
  - **高Kの進み具合ゲージ**：②〜⑥ のあいだ、左の余白に縦のゲージ（軽い → 重い）。段階ごとに 1/5 ずつ上がり、⑥でいちばん上・赤。**Kの数値は書かない**（段階とK値は一致しないため）
  - 冒頭に問いかけ「この変化、気づける？」、最後に「何個わかった？コメントで教えてね」
- 各パターンのひとことのうしろに、看護師がすることを色の文字で出す（{'、'.join('「' + v[0] + '」' for v in m.TAGS.values())}）。ナレーションでは「すぐ報告」と言わない
- 画面とキャプションに「数値はこの波形での一例」と明記している。画面の数値（PR・QTc・心拍数）はモデルの波形から計算した値（QTの終わりは最大の下り勾配の接線と基線の交点、QTcはBazett）
- 出典はすべて LITFL ECG Library（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. 11パターンの選び方と並び（ジギタリス効果を外した、低Mgはキャプションだけ）。上の6つを「高カリウムの進み方」（LITFL の usual order：T波 → P波・PR → QRS → サイン波）として順に並べたこと。実際はこの順に進むとはかぎらず、カリウム値とも一致しない（LITFL）。この見せ方で誤解を招かないか（キャプションで「きれいには一致しない」「どの段階でも突然VF・心停止になりうる」と補っている）
2. ⑥サイン波の描き方（{60/m.RR_SW:.0f}/分・なめらかな波）と、台本「サイン波。このあと突然、心停止になりうる。」、画面の色の文字「→ 心停止に備える」。サイン波の心拍数・形はこれでよいか
3. ④「P波消失・徐脈」を1つにまとめたこと（{60/m.RR_K3:.0f}/分、P波なし、QRS 約{m.measure('K3', m.RR_K3)['qrs']:.0f}msの補充調律）。高Kの徐脈の代表の形として妥当か
4. ⑤QRS幅の拡大：QRS 約{m.measure('K4', m.RR_K4)['qrs']:.0f}ms・形がくずれてTとつながる描き方。P波を描いていない（④でP波が消えたあと、という並びのため）
5. ⑦⑧低K：モニターのII誘導でU波をこの大きさで描いたこと（LITFL：U波は V2〜V3 で最もよく見える）。⑦のU波の大きさ（U/T {_ut('L1'):.1f}、LITFL：T波の25%を超えると prominent）、⑧のU/T比・ST低下・「→ すぐ報告」は妥当か
6. ⑨低Ca（STが長く、T波の形は同じ）と ⑩薬剤などのQT延長（T波が遅く幅広い）の描き分け。QTc {m.QTC_C1}ms・{m.QTC_D1}ms の数値
7. ⑪高Ca（QTc {m.QTC_C2}ms、STがほとんどない）の描き方
8. 色の文字の割りふり：②〜⑤と⑧「すぐ報告」、⑥「心停止に備える」、⑦⑨⑪「採血の値も確認」、⑩「12誘導でQTc確認」。②テント状T波だけでも「すぐ報告」でよいか
9. 台本は、離脱を防ぐため1パターン1文（声で3〜4秒）に詰め、くわしい説明は画面のひとこととキャプションにまかせた。短くしたことで、医学的に欠けて誤解を招く文はないか（とくに ⑥、まとめ「高カリウムは、波形が軽く見えても、急変することがある」）
10. スマホの大きさで、③の平たいP波、⑦のU波が読み取れるか
11. 基準のゴースト（うすい線）：拍をR頂点でそろえて重ねたこと。とくに④（43/分）・⑤（50/分）は基準と心拍数がちがうので、基準の拍をそのパターンの拍の位置に置いている。誤解を招かないか（⑥サイン波には重ねていない）
12. 高Kの進み具合ゲージ：段階を「軽い → 重い」の5段で見せ、Kの数値は書かないこと。段階の順番どおりに重くなるように見えることで誤解を招かないか

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

    lines = [f'第25弾 高カリウム血症とQT（電解質） {m.N_PAT}パターン ― 画面の文字', '',
             f'[見出し] {m.TITLE} {m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] {m.HOOK_Q} ／ 心電図で気づく電解質 ／ {m.TITLE}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', f'[②〜⑥] 左の余白に縦のゲージ：上から「高K」「重い」・下「軽い」（数値なし）',
              f'[②〜⑪（⑥を除く）] ①の枠：① 洞調律（基準）＝下のうすい線',
              f'[②③] 帯の下：{m.GHOST_LEGEND}',
              '', f'[最後] {m.END_LINE} ／ {m.SAVE_LINE} ／ {m.COMMENT_LINE}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel25.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
