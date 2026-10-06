"""第20弾 ノイズ（アーチファクト） ― 専門医レビュー用の資料。

- out/review_reel20_frames.pdf：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ（冒頭・11パターン（▲・ノイズを消すと…も）・一覧・サムネイル）
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
    'LITFL ECG Motion Artefacts（①③・シバリングの一文）': L + 'ecg-motion-artefacts-ecg-library/',
    'LITFL Limb Lead Reversal（⑧）': L + 'ecg-limb-lead-reversal-ecg-library/',
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
    t = min(max(t, a + 0.9), b - 0.2)
    if pat['no'] in m.REVEAL_PATS:                 # ノイズを消す前（ノイズが見えているところ）
        t = min(t, m.reveal_times(i)[0] - 0.1)
    return t


def reveal_time(i):
    """「ノイズを消すと…」で、ノイズが消えているあいだのまん中。"""
    t0, t1, t2, t3 = m.reveal_times(i)
    return (t1 + t2) / 2


def describe():
    """各パターンの描き方（モデルの値から）。下の心臓のリズムは、⑪以外ずっと洞調律75/分。"""
    rr9 = np.diff(m.mark_beats(m.IDX['⑨']))
    rr10 = np.diff(m.mark_beats(m.IDX['⑩']))
    i11 = m.IDX['⑪']
    return [
        '洞調律の上に、0.6〜3Hzの大きくゆっくりした揺れ（約0.34mV）と、ときどき鋭い振れ（0.55〜0.75mV）。ふつうのQRSはそのまま見える。後半で「ノイズを消すと…」',
        '洞調律の上に、20〜60Hzの細かく速いギザギザ（約0.1mV）。後半で「ノイズを消すと…」',
        '洞調律の上に、4.5〜8Hzの細かい不規則な揺れ（約0.06mV）。P波が見えにくく心房細動に見えるが、R-Rは0.80秒で一定',
        '洞調律の基線が、周期4.0秒（15回/分）で±0.38mVゆっくり上下',
        '洞調律の上に、50Hzの規則正しい細かいギザギザ（±0.06mV）',
        '基線の段差（0.45〜0.65mV、そのあと約0.2秒でゆっくり戻る）と、0.15〜0.2秒の一瞬のとぎれ',
        'まっすぐの線が2.7秒（そのあいだも心臓は動いている想定）。外れる・付け直す瞬間に小さな振れ',
        'II誘導のP波・QRS・T波がまるごと逆さま（RAとLLの入れかわりを想定、LITFL）',
        f'約4.5Hz（約270/分）の大きな揺れ（約±0.6mV）。中にふつうのQRS（1.0mV）が見える。'
        f'その下に緑の▲を順に付け、間隔のものさし（{"・".join(f"{x:.2f}" for x in sorted(set(np.round(rr9, 2))))}秒）。後半で「ノイズを消すと…」',
        f'3〜7Hzの不規則で大きな揺れ（強弱あり）。中にふつうのQRSが見え、同じく▲とものさし（{"・".join(f"{x:.2f}" for x in sorted(set(np.round(rr10, 2))))}秒）。後半で「ノイズを消すと…」',
        f'本物の心室頻拍：{60/0.32:.0f}/分の幅の広いQRS（約{m.qrs_ms(m.qrs_pvc):.0f}ms）が8拍。そのあいだ、ふつうのQRSは見えない。'
        f'前後の洞調律の拍（区間の {", ".join(f"{r - m.SEGS[i11][0]:.1f}" for r in m.mark_beats(i11))}秒）にだけ▲、VTのあいだは赤の点線で「{m.NO_QRS_TXT}」',
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 2*m.HOOK_STEP + 0.2
    i11 = m.IDX['⑪']
    pages = []
    for i, p in enumerate(m.PATTERNS):
        nm = f"{p['no']} {p['name']}"
        if p['no'] in m.MARK_PATS:
            pages.append((f'{nm}（隠れたQRSの▲と、間隔のものさし）', key_time(i)))
        else:
            pages.append((nm, key_time(i)))
        if p['no'] in m.REVEAL_PATS:
            pages.append((f'{nm}（ノイズを消すと…：下の洞調律）', reveal_time(i)))
        if p['no'] == m.NO_QRS_PAT:
            pages[-1] = (f'{nm}（▲が付かない：赤の点線「{m.NO_QRS_TXT}」）', m.WINDOWS[i][1] - 0.6)
    frames = [('冒頭0〜1秒：問いかけ「このVT、本物？」（偽VTが流れる）', 0.5),
              ('冒頭のフック（答えのタイトル「ノイズ」と、止めた波形を変形しているところ）', hook_t)] \
        + pages \
        + [(f'最後：{m.N_PAT}個の一覧と「何個わかった？コメントで教えてね」', m.T_END + m.FLY + 2.8)]
    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    for f in os.listdir(fdir):
        if f.endswith('.png'):
            os.remove(os.path.join(fdir, f))
    pngs, index = [], []
    for k, (name, t) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        m.frame(t).save(fp)
        pngs.append(fp); index.append(f'- {k}ページ：{name}（{t:.1f}秒）')
    thumb = os.path.join(OUT, 'thumb_reel20_list.png')
    m.thumbnail_list().save(thumb)
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙・透かしなし）')
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
    def tagtxt(p):
        tg = m.TAGS.get(p['tag'])
        return f' ＋赤で「{tg[0]}」' if tg else ''
    rows = '\n'.join(f"| {p['no']} {p['name']} | {p['one']}{tagtxt(p)} | {d} |"
                     for p, d in zip(m.PATTERNS, describe()))
    narr = '\n'.join(f"- {n}：{vo.TEXT[n]}" for n, _ in vo.LINES)
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    segd = ' '.join(f"{p['no']}{p['D']:.1f}" for p in m.PATTERNS)
    rv = '、'.join(f"{no} {m.reveal_times(m.IDX[no])[1]:.1f}〜{m.reveal_times(m.IDX[no])[2]:.1f}秒" for no in m.REVEAL_PATS)
    mk = '、'.join(f"{no} " + ' '.join(f'{m.t_of(r - m.DT_REF):.1f}' for r in m.mark_beats(m.IDX[no])
                                       if m.WINDOWS[m.IDX[no]][0] <= m.t_of(r - m.DT_REF) < m.WINDOWS[m.IDX[no]][1]) + '秒'
                  for no in m.MARK_PATS)
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第20弾「ノイズ（アーチファクト）、まず覚えたい{m.N_PAT}パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音前。下の台本で録る）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 第21・24弾と同じ作り：冒頭で波形を止めて素早く変形（フック）→ {m.N_PAT}パターンを1つずつ紹介 → 紹介が終わった波形は縮んで上下の枠に移り、ミニ波形として流れ続ける → 最後に{m.N_PAT}個の一覧
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。下の心臓のリズムは、⑪以外ずっと**洞調律75/分**で、その上にノイズを重ねている
- ⑪だけ、比べるための「本物の心室頻拍」（ひとことのうしろに赤で「→ すぐ報告」）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library と、LITFL以外の2本（下に一覧）

## 前回レビュー（2026-10-04、12パターン版・要修正なし）からの変更点
1. **④シバリングを外した（12 → {m.N_PAT}パターン）**。②筋電図・③ふるえと同じ「筋肉のふるえ」の仲間で、画面の見た目もほぼ同じだから。
   キャプションに「寒さのふるえ（シバリング）も同じように乱れます」と一文で残した（LITFL ECG Motion Artefacts「Motion artefact due to tremor or shivering…」「Hypothermia (shivering)」）。
   番号を①〜⑪に振り直した（旧⑤〜⑫ → 新④〜⑪）。上の枠 ①〜⑥（2列×3段）、下の枠 ⑦⑧（左）・⑨⑩（右）、⑪本物のVT は3段目に横長
2. **台本を1パターン1文（声で3〜4秒）に詰めた**（約108秒 → 約{m.DUR:.0f}秒）。前回の推奨で直した言い回し（③の対比、⑦「あわてず、まず患者さんを見て」、⑨⑩「ふつうのQRSが隠れている／見える」）は残した。
   まとめは「同じ間隔のQRSが見えたらノイズ。でも、まず患者さんを見て。」に短くした
3. **この回だけの見せ方を足した**（数値はモデルの拍の時刻から計算）
   - 「隠れたQRS」マーカー：⑨偽VT・⑩偽VF の紹介中、ノイズの下にある洞調律のQRSが帯の右のほうを通るたびに、波形の下に緑の▲を順に付け（細い点線でQRSとつなぐ）、
     となりの▲とのあいだに間隔のものさし「0.80秒」を引く（▲が付く時刻：{mk}）。
     ⑪本物のVTでは、幅の広いQRSのあいだに▲が付かず、赤の点線で「{m.NO_QRS_TXT}」（前後の洞調律の拍にだけ▲）
   - 「ノイズを消すと…」：①②⑨⑩ の紹介の後半で、ノイズをすっと薄くして下の洞調律を約{m.REV_HOLD:.1f}秒見せ、また戻す（{rv}）
   - 冒頭0〜1秒に大きな問いかけ「このVT、本物？」（そのあいだ⑨の偽VTが流れる）→ 答えのタイトル「ノイズ」。最後に「何個わかった？コメントで教えてね」（画面の字だけ）
4. キャプションを第21・24弾の短い形にした（1行目を問いかけ、最後にコメントのお願い）
5. 画面の言い回し：⑪のひとことを「ふつうのQRSが消え、幅広いQRSが続く」に（字が小さくならない長さに）。左下の注記を「実際の速さ（II誘導・ふつうの拍は75/分）」に

## PDFのページ
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音前の台本。1パターン1文・声で3〜4秒。数字は画面に出ているので、声では読まない）
{narr}

- 「すぐ報告」は声では言わず、画面（⑪のひとことのうしろに赤で「→ すぐ報告」）とキャプションで伝える
- 区間の長さ（仮・秒）：{segd}

## キャプション
```
{caption}
```

## とくに見てほしい点
1. ④シバリングを外したこと。{m.N_PAT}パターンの選び方として、ほかに外すもの・入れるべきものはあるか（胸骨圧迫中の波形、電気メス、パルスタップ、T波のダブルカウントなどは入れていない）
2. 「隠れたQRS」の▲とものさし（⑨⑩）：ノイズの中のふつうのQRSに、同じ間隔（0.80秒）で▲を付ける見せ方は、「同じ間隔のQRSが見えたらノイズ」の教え方として妥当か。
   実際のモニターでは、ノイズの中のQRSが常にきれいに見えるとはかぎらない。▲で「必ず見つかる」と受け取られる心配はないか
3. ⑪本物のVT：幅の広いQRSのあいだを「{m.NO_QRS_TXT}」とした言い方。VTのとき房室解離で洞調律が続いていることもあるが、ふつうのQRSとしては見えない、という意味で誤解はないか
4. 「ノイズを消すと…」（①②⑨⑩）：ノイズを消すと洞調律が出てくる見せ方が、「ノイズは消せば済む」「波形を加工してよい」と受け取られないか。①体動・②筋電図にも入れてよいか
5. 冒頭の問いかけ「このVT、本物？」で偽VT（歯みがき）を流し、すぐ答えのタイトル「ノイズ」を出す流れ。VTを軽く見る印象にならないか
6. 短くした台本：③「ふるえは心房細動に見えても、R-Rは一定。」、⑦「電極外れでまっすぐの線。あわてず、まず患者さんを見て。」、
   ⑨「歯みがきの偽VT。ふつうのQRSが隠れている。」、⑩「断線の偽VF。ここにも、ふつうのQRSが見える。」、
   まとめ「同じ間隔のQRSが見えたらノイズ。でも、まず患者さんを見て。」。短くしたことで誤解を招く文はないか
7. キャプションの「すぐ報告」の範囲と、「迷ったら、ノイズと決めつけずに報告」、シバリングの一文
8. スマホの大きさで、⑨⑩のノイズの中のQRSと▲が読み取れるか

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

    lines = [f'第20弾 ノイズ まず覚えたい{m.N_PAT}パターン ― 画面の文字', '',
             f'[0〜{m.ASK_END:.1f}秒] {m.ASK}（黄色・大きめ。偽VTが流れる）',
             f'[見出し] ノイズ、まず覚えたい{m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 {m.ASK_END:.1f}〜{m.T_GO:.1f}秒] {m.TITLE_SUB} ／ {m.TITLE} ／ {m.TITLE_2}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        tg = m.TAGS.get(pat['tag'])
        alert = f' {tg[0]}（赤）' if tg else ''
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
        if pat['no'] in m.MARK_PATS:
            lines.append('    波形の下：緑の▲ と ものさし「0.80秒」')
        if pat['no'] == m.NO_QRS_PAT:
            lines.append(f'    波形の下：赤の点線「{m.NO_QRS_TXT}」（前後の洞調律の拍にだけ▲）')
        if pat['no'] in m.REVEAL_PATS:
            t0, t1, t2, t3 = m.reveal_times(i)
            lines.append(f'    {t1:.1f}〜{t2:.1f}秒：{m.REVEAL_TXT}（緑）')
    lines += ['', f'[最後] {m.END_1} ／ {m.END_2} ／ {m.END_3}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel20.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
