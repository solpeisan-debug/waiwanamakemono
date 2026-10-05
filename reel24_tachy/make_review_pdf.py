"""第21弾 致死性不整脈と心停止 ― 専門医レビュー用の資料。

- out/review_reel21_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・12パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel21.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel21 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL Premature Ventricular Complex（R on T・連発）': L + 'premature-ventricular-complex-pvc-ecg-library/',
    'LITFL Ventricular Tachycardia – Monomorphic': L + 'ventricular-tachycardia-monomorphic-ecg-library/',
    'LITFL Polymorphic VT and Torsades de Pointes': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
    'LITFL Ventricular Fibrillation (VF)': L + 'ventricular-fibrillation-vf-ecg-library/',
    'LITFL AV Block: 2nd degree, Mobitz II': L + 'av-block-2nd-degree-mobitz-ii-hay-block/',
    'LITFL AV Block: 3rd degree (Complete Heart Block)': L + 'av-block-3rd-degree-complete-heart-block/',
    'LITFL CCC Pulseless Electrical Activity': L + 'pulseless-electrical-activity/',
    '（LITFL以外）ERC Guidelines 2021: Adult Advanced Life Support（Soar J, et al. Resuscitation 2021;161:115-151）': 'https://cprguidelines.eu/',
    '（LITFL以外）JRC蘇生ガイドライン2020（日本蘇生協議会）：医療従事者の BLS': 'https://www.jrc.or.jp/guideline/',
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


def ms(x):
    return f'{x*1000:.0f}ms'


def describe():
    """各パターンの描き方（モデルの値から）。"""
    return [
        f'洞調律 {60/0.8:.0f}/分。PVC（QRS 約{m._qrs_ms(m.qrs_pvc):.0f}ms）が直前のRから 0.27秒（T波の頂点）に乗る。1回だけで洞調律に戻る',
        f'洞調律 {60/0.8:.0f}/分のあと、PVCが3つ（間隔 0.38秒＝{60/0.38:.0f}/分）続いて、洞調律に戻る',
        f'幅の広いQRS（約{m._qrs_ms(m.qrs_pvc):.0f}ms）が {60/0.32:.0f}/分で規則正しく続く',
        f'幅の広いQRSが約{60*m.POLY_N/m.POLY_L:.0f}/分。大きさ（0.45〜1.15mV）と向きが1拍ごとに変わる',
        f'QT延長の洞調律（60/分、QT 約0.56秒）→ T波の上から始まり、約{m.TDP_F*60:.0f}/分で大きさがねじれるように変わる（ねじれの周期 1.25秒）→ {m.TDP_B-m.TDP_A:.1f}秒で自然に止まる',
        '3〜9Hz（180〜540/分）の不規則で大きな揺れ（約±0.4mV）。P・QRS・Tは見えない',
        '3.5〜10Hz の不規則な小さな揺れ（約±0.08mV）',
        f'洞調律 {60/0.8:.0f}/分、PR {m.PR:.2f}秒で一定。4つめのP波のあとQRSが抜ける（4:3）。抜けたところのR-Rは 1.60秒（P-Pの2倍）',
        f'P波 {60/0.68:.0f}/分と、幅の広い心室補充調律（QRS 約{m._qrs_ms(m.qrs_escape):.0f}ms）{60/1.7:.0f}/分が、関係なく別々に出る',
        'ほぼまっすぐの線（±0.01mV のごくわずかな揺れ）',
        f'ふつうの形のP・QRS・T（{60/0.75:.0f}/分）。脈はない設定',
        f'幅の広いQRS（約{m._qrs_ms(m.qrs_escape):.0f}ms）が {60/2.0:.0f}/分。脈はない設定',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭のフック（止めた波形を変形しているところ）', hook_t)] \
        + [(f"{p['no']} {p['name']}", key_time(i)) for i, p in enumerate(m.PATTERNS)] \
        + [('最後：12個の一覧', m.T_END + m.FLY + 2.5)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}')
    thumb = os.path.join(OUT, 'thumb_reel21_list.png')
    if not os.path.exists(thumb):
        m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel21_frames.pdf')
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
- 第21弾「致死性不整脈と心停止、12パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人。急変の第一発見者になりうる）
- 第17〜20弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に12個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**
- 各パターンのひとことのうしろに、対応を色の文字で出す（赤「→ 脈なしならショック」「→ 電気ショック」、青「→ ショックしない・CPR」、黄「→ すぐ報告」）
- 名前の色で3つの群に分けている：速くなる道（①〜⑦）、遅くなる道（⑧〜⑩）、脈がない（⑪⑫）。①②⑧⑨は「心停止につながるサイン」として黄色
- 前回（10パターン版）のレビューを反映したうえで、タイトルを「致死性不整脈と心停止」に変え、12パターンに組み替えた（胸骨圧迫中・P波だけの心静止を外し、R on T・PVCの連発・モビッツII型・完全房室ブロックを足した）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library／CCC と、LITFL以外のガイドライン（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 電気ショックの表示 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない）
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. タイトル「致死性不整脈と心停止」と、冒頭の一文「致死性不整脈と心停止。まず覚えたいのは、この12パターン。」。心停止の波形（VF・無脈性VT・心静止・PEA）と、そこにつながる不整脈を1本にまとめる言い方として誤解がないか
2. 12パターンの選び方。①R on T・②PVCの連発・⑧モビッツII型・⑨完全房室ブロック を「心停止につながるサイン（すぐ報告）」として足したことは妥当か。ほかに入れるべきもの（洞停止、徐脈頻脈、ブルガダ型、QT延長そのもの など）はあるか
3. 台本は、離脱を防ぐため1パターン1文（声で3〜4秒）に詰め、くわしい説明は画面のひとこととキャプションにまかせた。短くしたことで、医学的に欠けて誤解を招く文はないか（とくに ⑤「持続して脈がなければ、ショック」、⑦「心静止と迷ったら、CPR」、⑩「すぐCPR、並行して電極も確認」、まとめ「ショックするのは、VFと、脈のないVT」）
4. ① R on T：PVCを直前のRから0.27秒（T波の頂点）に置いた描き方と、画面「VFのきっかけに」（LITFL：QT延長の状況でトルサードの引き金）。② PVCの連発：3連（158/分）を「ショートラン」と呼び、キャプションで「＝非持続性の心室頻拍」とすること
5. ⑧ モビッツII型：4:3、PR 0.16秒一定、幅の狭いQRSで描いた（キャプションに「実際はQRS幅が広いことが多い」）。代表の形として妥当か
6. ⑨ 完全房室ブロック：心房88/分・幅の広い補充調律35/分の描き方
7. ⑧⑨を「すぐ報告」にしたこと（ショック・CPRの表示ではない）。徐脈のアルゴリズム（アトロピン・ペーシング）に触れるべきか
8. 前回のレビューで直したところ（⑤トルサードの台本、⑩心静止の台本と画面、キャプションの初動の順番）が、12パターン版でも正しく残っているか
9. スマホの大きさで、① のT波の上のPVC、⑧ の抜けたP波が読み取れるか。誤解を招く表現はないか

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

    lines = ['第21弾 致死性不整脈と心停止 12パターン ― 画面の文字', '',
             '[見出し] 致死性不整脈と心停止 12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ 致死性不整脈と心停止',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', '[最後] 急変のまえに、この12パターン ／ 保存して見返してね',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel21.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
