"""第19弾 ペースメーカー心電図 ― 専門医レビュー用の資料。

- out/review_reel19_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・12パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel19.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel19 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL Pacemaker Rhythms – Normal Patterns': L + 'pacemaker-rhythms-normal-patterns/',
    'LITFL Pacemaker Malfunction': L + 'pacemaker-malfunction-ecg-library/',
    '偽融合の定義（LITFL以外）': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3861323 ／ https://ecgmadesimple.ca/5-4/',
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
    qn, qp, qf = m._qrs_ms(m.qrs_normal), m._qrs_ms(m.qrs_paced), m._qrs_ms(m.qrs_fusion)
    return [
        f'心房スパイク → P波 → 自分の房室結節を通って細いQRS。60/分。スパイクからRまで {ms(0.20 + m.A_SPIKE)}',
        f'心室スパイク → 幅の広いQRS（約{qp:.0f}ms、II誘導で下向き）、T波は上向き（QRSと逆向き）。P波なし。60/分',
        f'心房スパイク → P波 → 心室スパイク → 幅の広いQRS。スパイクの間隔（AV delay）{ms(0.22 + m.A_SPIKE - m.PV_DELAY)}。60/分',
        f'自分の洞調律のP波（75/分）のあと {ms(0.22 - m.PV_DELAY)} で心室スパイク → 幅の広いQRS',
        f'自分の拍（75/分・スパイクなし）が3つ → 洞調律が止まり、最後の自分の拍から {m.LRI:.1f}秒（下限の間隔）で心室ペーシング → 自分の拍が戻るとまた休む',
        f'心室ペーシングと同じで、スパイクの高さだけ {m.SPIKES["Vs"][0][1]:.2f}mV（ほかは 1.0mV で描いている）',
        f'心室ペーシング2拍 → 自分の洞調律のP波のあと、ペーシングとほぼ同時に融合収縮（QRS 約{qf:.0f}ms：自分 {qn:.0f}ms とペーシング {qp:.0f}ms の間、スパイクは {m.SPIKES["F"][0][1]:.2f}mV と短め）→ 自分の拍が続く',
        '⑦と同じ並びで、融合収縮のかわりに偽融合：自分の細いQRSの頂点にスパイクが重なるだけで、形は変わらない',
        f'心室ペーシング2拍 → スパイクだけでQRSがない → {m.LRI:.1f}秒後のスパイクでまたQRS。QRSどうしの間隔 {2*m.LRI:.1f}秒',
        f'心室ペーシング2拍 → スパイクも出ない休み {3.4 - m.LRI:.1f}秒（下限の間隔 {m.LRI:.1f}秒より長い）→ ペーシングが戻る。筋電位などのノイズは描いていない',
        f'自分の拍（75/分）があるのに、直前のRから {1.10 - 0.8:.2f}秒（T波の頂点あたり）にスパイク。心室は不応期なのでQRSはつづかない',
        f'心室ペーシングで 120/分（上限の速さの想定）。心室スパイクから {ms(m.RETRO_P + m.PV_DELAY)} に逆行性P波（ST部分）',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 1*m.HOOK_STEP + 0.2
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
    thumb = os.path.join(OUT, 'thumb_reel19_list.png')
    if not os.path.exists(thumb):
        m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel19_frames.pdf')
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)
    print(fpdf, len(pngs), 'ページ（等倍）')

    # 依頼文
    rows = '\n'.join(f"| {p['no']} {p['name']} | {p['one']}{' ＋赤で「→ すぐ報告」' if p['no'] in m.ALERT else ''} | {d} |"
                     for p, d in zip(m.PATTERNS, describe()))
    narr = '\n'.join(f"- {n}：{vo.TEXT[n]}" for n, _ in vo.LINES)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第19弾「ペースメーカー、まず覚えたい12パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第17弾（期外収縮）・第18弾（徐脈）と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に12個の一覧
- 波形はモデルで作った模式図。**II誘導・右室心尖部のリード・下限レート60/分**を想定。実際の速さ（25mm/秒）。自分の洞調律は75/分
- ペーシングスパイクは、モニターのペースメーカー表示を想定して高さ 1.0mV の縦線で描いている（⑥だけ小さい）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 主な出典は LITFL ECG Library（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない）
{narr}

- 「すぐ報告」は声では言わず、画面（⑨〜⑫のひとことのうしろに赤で「→ すぐ報告」）とキャプションで伝える

## キャプション
```
{caption}
```

## とくに見てほしい点
1. ② 右室ペーシングのQRSを、II誘導で「幅の広い下向きのQRS・上向きのT」で描いた。代表の形として妥当か
2. ④ の名前「P波に合わせるペーシング」（心房センス・心室ペース）は、看護師向けの言い方として誤解がないか
3. ⑤「自分の脈が出ていれば、ペースメーカーは休みます」と、最後の自分の拍から下限の間隔（1.0秒）でペーシングが始まる描き方は正しいか（ヒステリシスは考えていない）
4. ⑦ 融合収縮・⑧ 偽融合の形（スパイクの位置・QRSの形）は妥当か
5. ⑨ ペーシング不全・⑩ オーバーセンシング・⑪ アンダーセンシングの描き方は、モニターで見たときの典型として妥当か。とくに ⑪ でスパイクがT波の上に出て、QRSがつづかない描き方
6. ⑫ ペースメーカー頻拍（120/分・逆行性P波）の描き方と、「上限の速さで続く」という言い方
7. 「すぐ報告」を ⑨〜⑫ に付けた範囲は妥当か。⑫ に「すぐ報告」は強すぎないか、ほかに付けるべきものはないか
8. 12パターンの選び方（マグネットモード、ランナウェイ・ペースメーカー、両室ペーシング（CRT）、ICD、センサー頻拍、リードのずれ は入れていない）
9. スマホの大きさで、スパイク（とくに ⑥ の小さいスパイク、⑪ のT波の上のスパイク）が読み取れるか。誤解を招く表現はないか

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

    lines = ['第19弾 ペースメーカー まず覚えたい12パターン ― 画面の文字', '',
             '[見出し] ペースメーカー、まず覚えたい12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ ペースメーカー',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f' {m.ALERT_TXT}（赤）' if pat['no'] in m.ALERT else ''
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', '[最後] スパイクを見たら、この12パターン ／ 保存して見返してね',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel19.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
