"""第24弾 頻脈（幅の狭いQRS） ― 専門医レビュー用の資料。

- release/review_reel24_frames.pdf（と out/review_reel24_frames.pdf）：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ。
  冒頭・10パターン（名前とひとことが出そろったところ）・つなぎ目（形が変わるまん中、中立の形を通るところは中立の形のまま）・最後・サムネイル。
  コマは今のコード（make_reel24.frame）から書き出す（映像は書き出し直さない）。PNG は out/review_frames/
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション（秒つき）・キャプション・見てほしい点）
- out/screen_text_reel24.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import glob
import os
import re

import numpy as np
from PIL import Image

import align_vo as vo
import make_reel24 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REL = os.path.join(HERE, 'release')

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
    """パターン i の k 番目の拍（名前の出ているあいだ）でカウンターが変わった直後の t。"""
    rs = [t for t, kk, b, j in m.crossings() if j == i]
    return rs[k] + after


def pac_index(i):
    """⑧：名前の出ているあいだにカウンターを通った拍のうち、きっかけのPACの順番。"""
    rs = [t for t, kk, b, j in m.crossings() if j == i]
    return min(range(len(rs)), key=lambda n: abs(rs[n] - m.PAC_CROSS))


def named(i):
    """パターン i の名前（「これは？」のあとの名前）とひとことが、どちらもはっきり出ている時間 (始まり, 終わり)。"""
    a, b = m.WINDOWS[i]
    return a + m.QUIZ_T + 0.05, b - 0.3


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
    lo, hi = named(i)
    return min(max(t, lo + 0.3), hi)


def describe():
    """各パターンの描き方（モデルの値から）。"""
    r = m.rate
    af = m.AF_RR
    mat = m.MAT_RR
    pk = ('M1', 'M2', 'M3', 'M4')
    return [
        f"P波（ふつうの形）→ 幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。PR {m.pr_ms('S'):.0f}ms、QRS {m.qrs_ms(m.qrs_115):.0f}ms",
        f"洞調律 {r(0.40):.0f}/分、PR {m.pr_ms('H'):.0f}ms。T波の頂点は Rから 0.195秒、P波の頂点は前のRから {0.40 - m.KINDS['H'][2]:.2f}秒（T波の下り坂）で、"
        f"T波の肩にこぶのように重なる",
        f"形のちがうP'（小さくとがった、上 +0.16mV → 下 −0.08mV の二相性）が {r(0.46):.0f}/分で1:1、規則正しい。PR {m.pr_ms('A'):.0f}ms。"
        f"T波の頂点は Rから 0.195秒で、T波の終わりと P'のあいだに短い平らなところがある。P'のあいだの基線は平ら",
        f"平均 {r(np.mean(mat)):.0f}/分（{r(max(mat)):.0f}〜{r(min(mat)):.0f}/分）で不規則。P波は4種類（ふつう・高くとがる・下向き・二相性）、"
        f"PR {min(m.pr_ms(k) for k in pk):.0f}〜{max(m.pr_ms(k) for k in pk):.0f}ms。基線は平ら",
        f"P波なし。RR は不規則（{min(af):.2f}〜{max(af):.2f}秒、平均 {r(np.mean(af)):.0f}/分）。細動波 {m.AF_FLO:g}〜{m.AF_FHI:g}Hz"
        f"（QRSの直前に P波に似た丸いこぶが来ないように乱数を選んだ）、"
        f"約±{np.abs(m.art_af(np.arange(0, sum(af), 0.002), sum(af))).max():.2f}mV",
        f"下向きののこぎり状の粗動波 {r(m.FL_CYC):.0f}/分（約{0.24*10:.1f}mm）。2:1で心室 {r(0.40):.0f}/分。1つはQRSに、1つはT波のあたりに重なる",
        f"幅の狭いQRS が {r(m.SVT_RR):.0f}/分で規則正しい。P波は見えない（QRSの終わりに小さな偽S波）",
        f"洞調律 90/分 → PAC（連結 {m.OO_PAC_C:.2f}秒、PR {m.pr_ms('B'):.0f}ms＝遅い道）→ PSVT {r(m.OO_SVT_RR):.0f}/分 {m.OO_SVT_N}拍 → "
        f"突然止まり、{m.OO_PAUSE:.2f}秒あけて洞調律 → 少しずつ {' → '.join(f'{r(x):.0f}' for x in m.OO_SINUS_RR)}/分。"
        f"カウンターは {' '.join(f'{b:.0f}' for _, _, b, j in m.crossings() if j == 7)}",
        f"幅の狭いQRS が {r(0.30):.0f}/分。QRSのすぐあとに下向きの逆行性P（short RP：RP＝QRSの始まり → Pの始まり {m.avrt_rp_ms()[0]:.0f}ms、"
        f"QRSの終わりから {m.avrt_rp_ms()[1]:.0f}ms 後にPが始まる）",
        f"幅の狭いQRS が {r(0.52):.0f}/分で規則正しい。QRSの直前に下向きのP（約−0.2mV、PR {m.pr_ms('J'):.0f}ms）",
    ]


def narration_rows():
    """narration.md の「秒数つき」の表（声を置いた秒）を、align_vo.py の文の名前と組にする：[(名前, 始まり, 終わり, 文)]。"""
    rows = []
    with open(os.path.join(HERE, 'narration.md'), encoding='utf-8') as f:
        for line in f:
            mm = re.match(r'^\|\s*(\d+\.\d+)\s*[–-]\s*(\d+\.\d+)\s*\|\s*(.+?)\s*\|\s*$', line)
            if mm:
                rows.append((float(mm.group(1)), float(mm.group(2)), mm.group(3)))
    names = [n for n, _ in vo.LINES]
    assert len(rows) == len(names), (len(rows), len(names))
    out = []
    for n, (a, b, s) in zip(names, rows):
        if s.rstrip('。') != vo.TEXT[n].rstrip('。'):
            print('注意：narration.md の表と align_vo.TEXT がちがう', n, s, vo.TEXT[n])
        out.append((n, a, b, s))
    return out


def boundaries():
    """つなぎ目ごとに：(前の番号, 次の番号 or None（最後）, 'direct'／'via'／'end', [形が変わる (t0, t1, A, B)])。
    冒頭の 中立の形 → ① は除く。"""
    ev = [e for e in m.SHAPE_EV if e[0] >= m.T_TITLE]
    out, p = [], 0
    for i in range(1, m.N_PAT):
        if i in m.DIRECT:
            out.append((i - 1, i, 'direct', [ev[p]])); p += 1
        else:
            out.append((i - 1, i, 'via', [ev[p], ev[p + 1]])); p += 2
    out.append((m.N_PAT - 1, None, 'end', [ev[p]]))
    assert p + 1 == len(ev)
    return out


DIRECT_WHAT = {1: '同じ洞頻脈が速くなる（115 → 150/分、P波がT波の下り坂へ）'}
NEU = '中立の形（ふつうの洞調律 75/分・うすい灰色の帯・「▶ 次の例」）'


def morph_frames():
    """つなぎ目のコマ：直接は形が変わるまん中、中立の形を通るところは、中立の形へ変わるまん中・中立の形のまま・次へ変わるまん中。"""
    no = lambda P: m.PATTERNS[P]['no']
    out = []
    for A, B, kind, evs in boundaries():
        if kind == 'direct':
            t0, t1 = evs[0][:2]
            out.append(((t0 + t1)/2, f'つなぎ目 {no(A)}→{no(B)}（直接）：形が変わるまん中。{DIRECT_WHAT[B]}'))
        elif kind == 'via':
            (a0, a1, *_), (b0, b1, *_) = evs
            out.append(((a0 + a1)/2, f'つなぎ目 {no(A)}→{no(B)}（中立の形を通る）：{no(A)} → 中立の形へ変わるまん中'))
            out.append(((a1 + b0)/2, f'つなぎ目 {no(A)}→{no(B)}（中立の形を通る）：{NEU}のまま（{b0 - a1:.1f}秒）'))
            out.append(((b0 + b1)/2, f'つなぎ目 {no(A)}→{no(B)}（中立の形を通る）：中立の形 → {no(B)} へ変わるまん中'))
        else:
            t0, t1 = evs[0][:2]
            out.append(((t0 + t1)/2, f'{no(A)}のあと：中立の形へもどるまん中（最後の画面へ。冒頭とつながる）'))
    return out


def write_pdf(pngs, fpdf):
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)


def hr_list(i):
    return [round(b) for _, _, b, j in m.crossings() if j == i]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    i8 = 7
    k8 = pac_index(i8)
    # ⑤：名前とひとことが出ているあいだで、いちばん速い拍（カウンターは拍ごとの値）
    lo5, hi5 = named(4)
    cr5 = [(b, t) for t, _, b, j in m.crossings() if j == 4 and lo5 <= t + 0.15 <= hi5]
    b5, t5 = max(cr5)
    frames = [(0.5, '冒頭0〜1秒：問いかけ「この10個、全部わかる？」'),
              (hook_t, '冒頭のフック（止めた波形を変形しているところ）'),
              (m.WINDOWS[0][0] + 1.2, 'クイズの例：① の始まり（名前の前に「これは？」。カウンターは名前の行が出ているあいだだけ）')]
    for i, p in enumerate(m.PATTERNS):
        if i == i8:
            # ⑧は、突然始まるPSVT（カウンター 170）、突然止まる（75）、少しずつ変わる洞頻脈（135）の3ページ
            frames += [(beat_time(i, k8 + 1), f"{p['no']} {p['name']}（PSVT：1拍で跳ぶ。カウンター 170）"),
                       (beat_time(i, k8 + m.OO_SVT_N + 1, 0.3), f"{p['no']} {p['name']}（突然止まる。カウンター 75）"),
                       (beat_time(i, k8 + m.OO_SVT_N + 5), f"{p['no']} {p['name']}（洞頻脈：少しずつ。カウンター 135。「別の場面の例・実際はもっとゆっくり」）")]
        elif i == 4:
            frames.append((t5 + 0.15, f"{p['no']} {p['name']}（カウンターは拍ごとの値。名前が出ているあいだでいちばん速い拍 {b5:.0f}/分。「1拍ごとの値（モニターは平均）」）"))
        elif i == 3:
            frames.append((key_time(i), f"{p['no']} {p['name']}（「1拍ごとの値（モニターは平均）」）"))
        else:
            frames.append((key_time(i), f"{p['no']} {p['name']}"))
    # コピーが枠へ飛ぶところ（⑧：下の段へ。ほかの枠のうしろを通る）・冒頭の 中立の形 → ①
    frames.append((m.WINDOWS[7][1] + 0.4, '⑧のコピーが枠へ飛ぶ途中（コピーはほかの枠のうしろを通る。帯の形はまだ変わらない）'))
    frames.append((sum(m.OPEN_MORPH)/2, '冒頭：中立の形（ふつうの洞調律 75/分）→ ①の形へ変わるまん中（①の名前が出る前）'))
    for i in range(m.N_PAT):              # 名前とひとことが出そろっているか
        lo, hi = named(i)
        assert any(lo <= t <= hi + 1e-6 for t, _ in frames if m.current(t) == i), i
    frames += morph_frames()
    frames.append((m.T_END + m.FLY + 2.8, f'最後：{m.N_PAT}個の一覧と「何個わかった？コメントで教えてね」'))
    frames.sort(key=lambda x: x[0])

    fdir = os.path.join(OUT, 'review_frames')
    os.makedirs(fdir, exist_ok=True)
    for q in glob.glob(os.path.join(fdir, '*.png')):
        os.remove(q)
    pngs, index = [], []
    for k, (t, name) in enumerate(frames, 1):
        fp = os.path.join(fdir, f'{k:02d}.png')
        im = m.frame(t)
        assert im.size == (1080, 1920)
        im.save(fp)
        pngs.append(fp); index.append(f'- {k}ページ（{t:.2f}秒）：{name}')
    thumb = os.path.join(fdir, f'{len(pngs) + 1:02d}.png')
    m.thumbnail_list().save(thumb)
    m.thumbnail_list().save(os.path.join(OUT, 'thumb_reel24_list.png'))
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙・透かしなし）')
    print('ページ数', len(pngs))
    for fpdf in (os.path.join(OUT, 'review_reel24_frames.pdf'), os.path.join(REL, 'review_reel24_frames.pdf')):
        write_pdf(pngs, fpdf)
        print(fpdf, len(pngs), 'ページ（等倍）')

    # 依頼文
    narr = '\n'.join(f"| {n} | {a:.2f}–{b:.2f} | {s} |" for n, a, b, s in narration_rows())
    caption = open(os.path.join(HERE, 'caption.txt'), encoding='utf-8').read().strip()
    srcs = '\n'.join(f'- {k}：{u}' for k, u in SRC.items())
    tagtxt = {k: v[0] for k, v in m.TAGS.items()}
    rows = '\n'.join(f"| {p['no']} {p['name']} | {p['one']} ＋「{tagtxt[p['tag']]}」 | {d} |"
                     for p, d in zip(m.PATTERNS, describe()))
    no = lambda P: m.PATTERNS[P]['no']
    flow = []
    for i, (a, b) in enumerate(m.WINDOWS):
        flow.append(f"| {no(i)} {m.PATTERNS[i]['name']} | 名前の行 {a:.2f}–{b:.2f}（「これは？」→ 名前 {a + m.QUIZ_T:.2f}） | "
                    f"{' '.join(str(x) for x in hr_list(i))} |")
    flow = '\n'.join(flow)
    bnd = []
    for A, B, kind, evs in boundaries():
        t0, t1 = evs[0][0], evs[-1][1]
        if kind == 'direct':
            bnd.append(f'| {no(A)}→{no(B)} | 直接：{DIRECT_WHAT[B]} | {t0:.2f}–{t1:.2f} |')
        elif kind == 'via':
            bnd.append(f'| {no(A)}→{no(B)} | 中立の形を通る（{m.VIA_T:.1f}秒で中立の形へ・{m.VIA_HOLD:.1f}秒そのまま・{m.VIA_T:.1f}秒で{no(B)}へ） | {t0:.2f}–{t1:.2f} |')
        else:
            bnd.append(f'| {no(A)}→最後 | 中立の形へもどす（冒頭の帯も中立の形なので、動画の終わりが冒頭とつながる） | {t0:.2f}–{t1:.2f} |')
    bnd = '\n'.join(bnd)
    direct_list = '、'.join(f'{no(i - 1)}→{no(i)}' for i in sorted(m.DIRECT))
    via_list = '、'.join(f'{no(i - 1)}→{no(i)}' for i in range(1, m.N_PAT) if i not in m.DIRECT)
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍（1080×1920）で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第24弾「頻脈（幅の狭いQRS）、10パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音済み。下の秒は動画の中で声が流れる位置）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 流れ：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 10パターンを1つずつ紹介 → 最後に10個の一覧
- **中部の帯は最初から最後まで消えない（今回の作り）**：
  - 名前が消えると、紹介したパターンの「コピー」だけが縮んで上下の枠へ飛び、ミニ波形として流れ続ける（帯はそのまま流れる）。
    コピーは、ほかの枠のうしろを通る（ほかの枠の名前・ミニ波形の上に重ならない）
  - コピーがほぼ枠に着いてから（名前が消えて {m.MORPH_DELAY:.1f}秒後）、帯に見えている拍が、その場で全部いっしょに形を変える（P波の形・向き・PR、偽S波・逆行性P、T波、拍の間隔と不規則さ、細動波・粗動波の大きさ）。
    形は山の高さ・位置・幅の数値を少しずつ変えるので、こぶが2つになったりしない。拍が跳んだり、消えたり、増えたりもしない
  - その場で直接変わるのは、同じ病態の中だけ（{direct_list}：同じ洞頻脈が速くなる。{m.MORPH_T:.1f}秒）
  - ほかのつなぎ目（{via_list}）は、すべて中立の形を通る：ふつうの洞調律 75/分を、うすい灰色・少し暗い帯で描き（どのパターンの色でもない）、
    {m.VIA_T:.1f}秒で中立の形へ・{m.VIA_HOLD:.1f}秒そのまま・{m.VIA_T:.1f}秒で次の形へ。そのあいだ、名前の行の位置に小さく「{m.NEXT_LABEL}」と出す（「前のリズムが次のリズムに変わる」と読まれないように）
  - 冒頭の帯も中立の形で、①の名前が出る前に①の形へ変わる。⑩のあとは中立の形へもどして最後の画面へ（動画の終わりが冒頭とつながる）
  - 名前・ひとこと・声のあいだは、波形はそのパターンの形そのもの。形が変わるあいだは声なし・名前なし
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。画面とキャプションに「数値はこの波形での一例」と明記
- 背景のマス目は心電図用紙と同じ（小さいマス 0.04秒・0.1mV、大きいマス 0.2秒・0.5mV）。中部の帯の基線は太い線の上
- 名前の色で3つの群に分けた：洞結節から（水色：①②）、心房から（オレンジ：③〜⑥）、房室結節・副伝導路のあたり（ピンク：⑦〜⑩）。上の枠に①〜⑥（2列×3段）、下の枠に⑦〜⑩（2列×2段）
- 各パターンのひとことのうしろに、看護師がまずすることを色の文字で出す：緑「→ まず患者さん」（①④）、黄「→ すぐ報告」（⑤⑥⑦⑨⑩）、青「→ 12誘導で確認」（②③）、紫「{m.TAGS['rate'][0]}」（⑧）。
  ナレーションでは「すぐ報告」と言わない（画面とキャプションで伝える）
- **この回だけの見せ方**
  - 心拍数カウンター（波形の下のまん中「♥ 150 /分」）：帯の右のほう（x={m.COUNT_X}px）を R が通るたびに、その拍の R-R（モデルの値）から計算した心拍数に変わる。ハートはその瞬間に光る。ピッという音も同じ瞬間。
    **名前の行（「これは？」と名前）が出ているあいだだけ出す**（形が変わっているあいだは出さない。混ざった形の心拍数を見せないため）。
    ⑧ では、PSVT が 90 → {m.rate(m.OO_PAC_C):.0f} → {m.rate(m.OO_SVT_RR):.0f}/分と1拍で跳び、突然止まる（{m.rate(m.OO_PAUSE):.0f}/分）。そのあと洞調律が {' → '.join(f'{m.rate(x):.0f}' for x in m.OO_SINUS_RR)}/分と少しずつ変わる
  - ④⑤ のあいだ、カウンターの下に小さく「{m.CNT_SUB_IRREG}」。⑧ の洞調律が少しずつ変わるところでは「{m.CNT_SUB_GRAD}」
  - クイズ：各パターンで、名前の行にまず「これは？」を出し、{m.QUIZ_T:.1f}秒後に名前に変わる（声も「特徴 → 名前」の順）
  - 冒頭0〜1秒に問いかけ「この10個、全部わかる？」、最後に「何個わかった？コメントで教えてね」
- 心房細動・心房粗動のくわしいバリエーション（f波の粗い・細かい、伝導比、変行伝導）は別の回（第26弾）で扱うので、ここでは代表の1つずつ。幅の広いQRSの頻拍も別の回（第27弾）
- 出典は LITFL ECG Library（下に一覧）。LITFL 以外の資料は使っていない

## 動画の流れ（秒）
| パターン | 名前の出ている時間（秒） | 心拍数カウンター（名前の行が出ているあいだに表示した値・/分） |
|---|---|---|
{flow}

| つなぎ目 | 変わり方 | 形が変わる時間（秒） |
|---|---|---|
{bnd}

## PDFのページ（時刻の順）
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音済み。1パターン1文・数字は画面に出ているので、声では読まない）
| 文 | 動画の秒 | 台本 |
|---|---|---|
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
### 今回の作り（帯を消さずに、その場で形が変わる）について
1. **その場で形が変わる見せ方で、誤解を招かないか**。直接変わるのは ①→②（洞頻脈 115/分 → 150/分、P波がT波に重なる）だけ。同じ洞頻脈が速くなる、という見せ方として妥当か
2. **中立の形を通すつなぎ目**（{via_list}）：ふつうの洞調律 75/分（うすい灰色の帯）にもどし、「{m.NEXT_LABEL}」を出してから次の形へ変えている。
   「前のリズムがふつうの洞調律にもどり、次のリズムが始まった」という実際の経過として読まれないか。見た目（灰色・暗さ・「{m.NEXT_LABEL}」の字）で「紹介中ではない」ことが伝わるか（PDF のつなぎ目のページ）
3. 心拍数カウンターを、名前の行が出ているあいだだけ出し、形が変わっているあいだは消したこと（混ざった形の心拍数は出さない）。カウンターの値（上の「動画の流れ」の表）に、おかしなものはないか
   （④⑤ は拍ごとの値なので、④ {min(hr_list(3))}〜{max(hr_list(3))}/分、⑤ {min(hr_list(4))}〜{max(hr_list(4))}/分と大きく変わる）
4. 名前が消えると、紹介したパターンのコピーが枠へ飛び（{m.FLY:.1f}秒）、ほぼ着いてから（{m.MORPH_DELAY:.1f}秒後）帯の形が変わり始める。コピーはほかの枠のうしろを通る。見分けにくいところはないか（PDF のつなぎ目のページ）
5. 声と名前の時間：「これは？」の行が出てから 0.55秒（①だけ 0.30秒、⑧は PAC がカウンターを通る 0.5秒前）で話し始め、名前は「これは？」から {m.QUIZ_T:.1f}秒で出る。形が変わるあいだは声なし（上の「ナレーション」と「動画の流れ」の秒）。名前・ひとことと声の内容がずれて見えるところはないか

### パターンごと
6. 10パターンの選び方（洞頻脈、P波がT波に重なる洞頻脈、心房頻拍、多源性心房頻拍、速い心房細動、心房粗動2:1、PSVT、始まり方の対比、順方向性の房室回帰性頻拍、接合部頻拍）。入れるべきもの・外すべきものはあるか
7. 色の文字の振り分け（「→ まず患者さん」①④／「→ すぐ報告」⑤⑥⑦⑨⑩／「→ 12誘導で確認」②③／「{m.TAGS['rate'][0]}」⑧）は、看護師の初動として妥当か。
   とくに ④ 多源性心房頻拍を「まず患者さん」、⑩ 接合部頻拍を「すぐ報告」、② を「12誘導で確認」にしたこと
8. ⑧ 始まり方の対比：PSVT は PAC をきっかけに「突然始まり、突然止まる」（90→170/分、止まって{m.OO_PAUSE:.1f}秒あけて洞調律）、そのあと洞調律が「少しずつ速くなり、少しずつ戻る」（75→135→90/分）。
   画面のひとことは「突然はPSVT、少しずつは洞頻脈が多い」、台本は「…少しずつ変わるなら、洞頻脈が多い。」（言い切らない）。
   洞調律が少しずつ変わるところでは、カウンターの下に小さく「{m.CNT_SUB_GRAD}」と出している（PSVTの続きではないこと、実際の変化は数十秒〜数分）。
   カウンターの横に小さく「↑ 1拍で跳ぶ」「↓ 突然止まる」「↗ 少しずつ」「↘ 少しずつ」。きっかけのPACのPRを長く（約{m.pr_ms('B'):.0f}ms）描いたことも。この見せ方に誤解がないか
9. 心拍数カウンター：1拍ごとの R-R から計算した値を出している（モニターの表示は平均することが多い）。④⑤ のあいだは、カウンターの下に小さく「{m.CNT_SUB_IRREG}」と出している
   （⑤ 心房細動は拍ごとの値で {min(hr_list(4))}〜{max(hr_list(4))}/分、平均約{m.rate(np.mean(m.AF_RR)):.0f}/分）。この言い方で、モニターの値との違いが伝わるか。キャプションにも、実際のモニターは平均値と書いた
10. ③ 心房頻拍：画面と台本は「いつもと違うP波」。P'を「II誘導で、小さくとがった上向き → 下向きの二相性」で描き、T波の終わりと離した。LITFL の例は「下向き（inverted in inferior leads）」。
   ⑩ 接合部頻拍（QRSの直前に下向きのP）と見分けやすくするためだが、代表の形として妥当か
11. ⑦ PSVT：P波なし、QRSの終わりに小さな偽S波（LITFL：Pseudo S waves in II, III, aVF）。名前「{m.PATTERNS[6]['name']}」の言い方（キャプションでは「房室結節リエントリー性頻拍（AVNRT・⑦）」）
12. ⑨ 房室回帰性頻拍：200/分、QRSのすぐあとに下向きの逆行性P（RP {m.avrt_rp_ms()[0]:.0f}ms・QRSの終わりから {m.avrt_rp_ms()[1]:.0f}ms）。II誘導のモニターで見えるものとして妥当か
13. ⑩ 接合部頻拍の逆行性P：大きさ（約−0.2mV）と位置（QRSの直前、PR 約{m.pr_ms('J'):.0f}ms）。モニターで見える代表の形として大きすぎないか
14. ② 洞頻脈（150/分、P波がT波の下り坂にこぶのように重なる）を「PSVTに見える」としたこと。⑥ 心房粗動（2:1、150/分）と並べて「150/分前後で規則正しい」ときの見分けを伝えたい
15. P波の形（スマホで見えるよう強めた）：③ のP'、④ の下向きのP（約−0.15mV）・二相性のP。強調しすぎて別の意味に見えないか
16. 台本のまとめ「規則正しいか、P波はどこか。まずこの2つ。」（LITFL SVT：起源と規則性で分ける）。短くしたことで誤解を招く文はないか
17. キャプションの「めまい・失神・意識の変化・胸痛・息苦しさ・血圧低下があれば、急変として人を呼び、すぐ医師に知らせます」（LITFL SVT の症状と、AVRT の「unstable → urgent DC cardioversion」から）。言い方として妥当か
18. スマホの大きさで、② のT波に重なるP、③ のとがったP'、⑨ の逆行性P、⑩ の下向きのP が読み取れるか

## 返してほしい形
- パターン番号（またはページ）ごとに：判定（OK／要修正／推奨）・理由・直し方（数値や言い換えまで具体的に）
- 「要修正」は医学的に誤りのもの、「推奨」はより良くなるもの、と分けてください
- 上の「とくに見てほしい点」の番号ごとにも、判定・理由・直し方をください
- LITFL 以外を根拠にするときは、出典名を書いてください
- ナレーションの台本を変えたほうがよいものは、その文を書いてください

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
        lines.append(f"    心拍数カウンター：{' '.join(str(x) for x in hr_list(i))} /分")
    lines += ['', f'[④⑤ カウンターの下] {m.CNT_SUB_IRREG}', f'[⑧ 少しずつのところ・カウンターの下] {m.CNT_SUB_GRAD}',
              '', f'[最後] {m.END_1} ／ {m.END_2} ／ {m.END_3}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel24.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
