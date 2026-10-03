"""第20弾 ノイズ（アーチファクト） ― 専門医レビュー用の資料。

- out/review_reel20_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・12パターン・一覧・サムネイル）
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション・キャプション・見てほしい点）
- out/screen_text_reel20.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import os

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel20 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

L = 'https://litfl.com/'
SRC = {
    'LITFL ECG Motion Artefacts': L + 'ecg-motion-artefacts-ecg-library/',
    'LITFL Limb Lead Reversal': L + 'ecg-limb-lead-reversal-ecg-library/',
    '（LITFL以外）Mondal S, et al. Electrocardiographic artifacts in clinical practice. World J Cardiol 2026;18(3):116299':
        'https://www.wjgnet.com/1949-8462/full/v18/i3/116299.htm',
    '（LITFL以外）Knight BP, et al. Clinical consequences of electrocardiographic artifact mimicking ventricular tachycardia. N Engl J Med 1999;341:1270-4':
        'https://www.nejm.org/doi/full/10.1056/NEJM199910213411704',
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
    """各パターンの描き方（モデルの値から）。下の心臓のリズムは、⑫以外ずっと洞調律75/分。"""
    return [
        '洞調律の上に、0.6〜3Hzの大きくゆっくりした揺れ（約0.4mV）と、ときどき鋭い振れ（0.55〜0.75mV）。ふつうのQRSはそのまま見える',
        '洞調律の上に、20〜60Hzの細かく速いギザギザ（約0.1mV）',
        '洞調律の上に、4.5〜8Hzの細かい不規則な揺れ（約0.06mV）。P波が見えにくく心房細動に見えるが、R-Rは0.80秒で一定',
        '洞調律の上に、6〜10Hzの不規則な揺れ（約0.16mV、強弱あり）',
        '洞調律の基線が、周期4.0秒（15回/分）で±0.38mVゆっくり上下',
        '洞調律の上に、50Hzの規則正しい細かいギザギザ（±0.06mV）',
        '基線の段差（0.45〜0.65mV、そのあと約0.2秒でゆっくり戻る）と、0.15〜0.2秒の一瞬のとぎれ',
        'まっすぐの線が2.7秒（そのあいだも心臓は動いている想定）。外れる・付け直す瞬間に小さな振れ',
        'II誘導のP波・QRS・T波がまるごと逆さま（RAとLLの入れかわりを想定、LITFL）',
        '約4.5Hz（約270/分）の大きな揺れ（約±0.6mV）。中にふつうのQRS（1.0mV）が0.80秒ごとに見える',
        '3〜7Hzの不規則で大きな揺れ（強弱あり）。中にふつうのQRSが0.80秒ごとに見える',
        f'本物の心室頻拍：{60/0.32:.0f}/分の幅の広いQRS（約{m._qrs_ms(m.qrs_pvc):.0f}ms）が8拍。そのあいだ、ふつうのQRSは見えない',
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
    thumb = os.path.join(OUT, 'thumb_reel20_list.png')
    if not os.path.exists(thumb):
        m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    fpdf = os.path.join(OUT, 'review_reel20_frames.pdf')
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
- 第20弾「ノイズ（アーチファクト）、まず覚えたい12パターン」。縦 1080×1920・60fps・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第17〜19弾と同じ作り：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 12パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に12個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。下の心臓のリズムは、⑫以外ずっと**洞調律75/分**で、その上にノイズを重ねている
- ⑫だけ、比べるための「本物の心室頻拍」
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library と、LITFL以外の2本（下に一覧）

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。数字は画面に出ているので、声では読まない）
{narr}

- 「すぐ報告」は声では言わず、画面（⑫のひとことのうしろに赤で「→ すぐ報告」）とキャプションで伝える

## キャプション
```
{caption}
```

## とくに見てほしい点
1. ③「ふるえで、心房細動に見えることも。R-Rは、一定です」：R-Rが一定なら心房細動ではない、と受け取られる言い方で問題ないか（房室ブロックを伴う心房細動などの例外をどこまで気にするか）
2. ⑥ 交流障害を「電気機器の影響」としたのは妥当か（日本は50Hz／60Hz）
3. ⑧ 電極外れ：「まっすぐの線。まず患者さんを見る」で、本物の心静止を見逃させる心配はないか
4. ⑨ 付けまちがいを「波形がまるごと逆さま」（RAとLLの入れかわり）で代表させてよいか。病棟のモニターでの起こりやすさ
5. ⑩ 偽VT・⑪ 偽VF：「ノイズの中に、同じ間隔でふつうのQRSが見えたらノイズ」という見分け方の教え方は妥当か。⑪を「リード線の断線」としたのは妥当か
6. ⑫ 本物のVTを比べるために入れたことと、「ふつうのQRSが消える」という言い方
7. キャプションの「すぐ報告」の範囲と、「迷ったら、ノイズと決めつけずに報告」という書き方
8. 12パターンの選び方（胸骨圧迫中の波形、電気メス、パルスタップ、T波のダブルカウントなどは入れていない）
9. スマホの大きさで、⑩⑪のノイズの中のQRSが読み取れるか。誤解を招く表現はないか

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

    lines = ['第20弾 ノイズ まず覚えたい12パターン ― 画面の文字', '',
             '[見出し] ノイズ、まず覚えたい12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ ノイズ',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f' {m.ALERT_TXT}（赤）' if pat['no'] in m.ALERT else ''
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', '[最後] アラームが鳴ったら、この12パターン ／ 保存して見返してね',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel20.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
