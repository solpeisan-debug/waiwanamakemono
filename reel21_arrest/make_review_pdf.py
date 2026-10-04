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
    'LITFL Ventricular Fibrillation (VF)': L + 'ventricular-fibrillation-vf-ecg-library/',
    'LITFL Polymorphic VT and Torsades de Pointes': L + 'polymorphic-vt-and-torsades-de-pointes-tdp/',
    'LITFL Ventricular Tachycardia – Monomorphic': L + 'ventricular-tachycardia-monomorphic-ecg-library/',
    'LITFL CCC Pulseless Electrical Activity': L + 'pulseless-electrical-activity/',
    'LITFL ECG Motion Artefacts（胸骨圧迫中の揺れ）': L + 'ecg-motion-artefacts-ecg-library/',
    '（LITFL以外）ERC Guidelines 2021: Adult Advanced Life Support（Soar J, et al. Resuscitation 2021;161:115-151）': 'https://cprguidelines.eu/',
    '（LITFL以外）Resuscitation Council UK: Adult advanced life support guidelines（波形確認の中断は5秒以内）': 'https://www.resus.org.uk/library/2021-resuscitation-guidelines/adult-advanced-life-support-guidelines',
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
        f'幅の広いQRS（約{m._qrs_ms(m.qrs_pvc):.0f}ms）が {60/0.32:.0f}/分で規則正しく続く',
        f'幅の広いQRSが約{60*m.POLY_N/m.POLY_L:.0f}/分。大きさ（0.45〜1.15mV）と向きが1拍ごとに変わる',
        f'QT延長の洞調律（60/分、QT 約0.56秒）→ T波の上から始まり、約{m.TDP_F*60:.0f}/分で大きさがねじれるように変わる（ねじれの周期 1.25秒）→ {m.TDP_B-m.TDP_A:.1f}秒で自然に止まる',
        '3〜9Hz（180〜540/分）の不規則で大きな揺れ（約±0.4mV）。P・QRS・Tは見えない',
        '3.5〜10Hz の不規則な小さな揺れ（約±0.08mV）',
        'ほぼまっすぐの線（±0.01mV のごくわずかな揺れ）',
        'P波が75/分。QRSはない（P波のみの心静止＝心室静止）',
        f'ふつうの形のP・QRS・T（{60/0.75:.0f}/分）。脈はない設定',
        f'幅の広いQRS（約{m._qrs_ms(m.qrs_escape):.0f}ms）が {60/2.0:.0f}/分。脈はない設定',
        f'約{60/m.CPR_T:.0f}回/分の大きく規則的な揺れが {m.CPR_B-m.CPR_A:.1f}秒 → 圧迫を止めると、下に粗いVFが見える',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [('冒頭のフック（止めた波形を変形しているところ）', hook_t)] \
        + [(f"{p['no']} {p['name']}", key_time(i)) for i, p in enumerate(m.PATTERNS)] \
        + [('最後：10個の一覧', m.T_END + m.FLY + 2.5)]
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
- 第21弾「致死性不整脈と心停止、10パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人。急変の第一発見者になりうる）
- 第17〜20弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 10パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に10個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**
- 各パターンのひとことのうしろに、電気ショックの適応を色の文字で出す（赤「→ 脈なしならショック」「→ 電気ショック」、青「→ ショックしない・CPR」、黄「→ 止めて波形を見る」）
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
1. ①②③に「脈なしならショック」と出す言い方は妥当か（脈のあるVTは同期カルディオバージョン・薬など別の治療）。看護師向けとして、どこまで書くか
2. ③ トルサードを「ショック適応（脈がなければ）」の群に入れたこと。自然に止まる描き方（LITFL：often self terminating）は妥当か
3. ⑤「心静止と迷ったら、CPRを続けます」（ERC 2021）の言い方は、看護師向けに誤解がないか
4. ⑥ 心静止の「電極と感度も確かめて」は妥当か。CPRを遅らせる心配はないか
5. ⑦ P波だけ（心室静止）を入れたことと、「ショックしない・CPR」の表示。ペーシングに触れるべきか
6. ⑧⑨ PEA：「波形はふつうに見えても、脈がない」という教え方。⑨ の描き方（30/分・幅の広いQRS）
7. ⑩ 胸骨圧迫中：「止めて、短く確かめます」とキャプションの「中断はできるだけ短く」。秒数を書くべきか
8. 10パターンの選び方（脈のあるVTとの見分け、ROSC、電気ショック直後の波形、徐脈頻脈などは入れていない）
9. キャプションの最後「まず、反応・呼吸を確認して、人を呼び、CPRを始めてください」の順番と言い方（院内の看護師向け）

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

    lines = ['第21弾 致死性不整脈と心停止 10パターン ― 画面の文字', '',
             '[見出し] 致死性不整脈と心停止 10パターン（「10」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ 致死性不整脈と心停止',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}" 
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', '[最後] 急変のときに、この10パターン ／ 保存して見返してね',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel21.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
