"""第26弾 心房細動・心房粗動 ― 専門医レビュー用の資料。

- release/review_reel26_frames.pdf（と out/review_reel26_frames.pdf）：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ。
  冒頭・14パターン（名前とひとことが出そろったところ）・心拍数カウンターのコマ（ハートが光る瞬間、⑩の休みの「--」）・
  つなぎ目（直接は形が変わるまん中。灰色の「つなぎ」を通るところは、つなぎのままのところと次へ変わるまん中）・最後・サムネイル。
  コマは今のコード（make_reel26.frame）から書き出す（映像は書き出し直さない）。PNG は out/review_frames/
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション（秒つき）・キャプション・見てほしい点）
- out/screen_text_reel26.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import glob
import os
import re

from PIL import Image

import align_vo as vo
import make_reel26 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REL = os.path.join(HERE, 'release')

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


def named(i):
    """パターン i の名前とひとことが、はっきり出ている時間 (始まり, 終わり)。"""
    a, b = m.WINDOWS[i]
    return a + 0.45, b - 0.3


def key_time(i):
    """パターン i のレビュー用のコマ。ふつうは紹介の終わりの0.5秒前（中部の帯がそのパターンだけで埋まり、名前とひとことがまだ出ている）。
    色を付ける範囲があるもの（① 心房細動の始まり・⑥ アシュマン現象）は、その始まりが中央の少し右に来るとき（左に、その前が見える）。
    ⑩ 徐脈頻脈症候群は、次の洞調律の拍が中央を通って 0.3秒（タイマーが止まった値）。"""
    a, b = m.WINDOWS[i]
    pat = m.PATTERNS[i]
    if i == m.I_TB:
        return m.t_of(m.SEGS[i][0] + m.TB_P1 + 0.30)
    if i == m.I_ASH:      # 幅の広い拍が x≈880 に来たとき（長い R-R・短い R-R の棒と「長い」「短い」がそろって見える）
        return m.t_of(m.SEGS[i][0] + m.T_ASH - (880 - m.XC) / m.F_PXS)
    if pat['hl'] is not m.ALL:
        lo, hi = pat['hl'][0]
        t = m.t_of(m.SEGS[i][0] + lo + 0.10 - 0.30)
        lo, hi = named(i)
        return min(max(t, lo + 0.2), hi)
    return b - 0.5


def timer_time():
    """⑩ のタイマーが数え上がっている途中（最後の心房細動の拍が中央を通って 1.8秒。左に心房細動の終わりが見える）。"""
    return m.t_of(m.SEGS[m.I_TB][0] + m.TB_P0 + 1.8)


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
        f'休みのあいだ「休み ◯.◯秒」がカウントアップし、{m.TB_PAUSE:.1f}秒で止まる（最後の心房細動の拍が画面の中央を通ったときに数え始め、次の洞調律の拍が中央を通ったときに止まる）',
        f'II誘導で下向きのF波（のこぎり状：{m.FL_DOWN*m.FF:.3f}秒でゆっくり下がり、{(1-m.FL_DOWN)*m.FF:.3f}秒ですばやく上がる。平らな区間なし）{60/m.FF:.0f}/分、山から谷 約{fl:.2f}mV。4:1伝導で R-R {4*m.FF:.1f}秒（{60/(4*m.FF):.0f}/分）。T波は小さめ',
        f'同じF波。2:1伝導で R-R {2*m.FF:.1f}秒（{60/(2*m.FF):.0f}/分）で規則的。F波の1つはQRS・T波に重なる（実際は見えにくいことが多いので、画面は「150/分で規則的なら粗動を疑う」）',
        f'同じF波。伝導比が {"・".join(f"{round(x/m.FF)}:1" for x in m.RR_VAR)} と変わり、R-R が不規則（どれも F-F {m.FF:.1f}秒の倍数、平均{m._rate(m.RR_VAR):.0f}/分）',
        f'F波が1:1で全部伝わり、幅の狭いQRSが {60/m.FF:.0f}/分で規則的（F波は 約{m.f_peak(P["⑭"])[0]:.2f}mV、T波は小さく早い）',
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


DIRECT_WHAT = {1: '心房細動が始まったあと、f波が粗く・心拍数が落ちつく',
               2: 'f波が小さくなる（粗い → 細かい）',
               3: '速くなる',
               4: '遅くなる',
               11: '伝導比 4:1 → 2:1（F波は同じ。QRSの数だけ変わる）',
               12: '伝導比が変わるようになる（F波は同じ）',
               13: '1:1 になる（F波が全部伝わる）'}


def boundaries():
    """つなぎ目ごとに：(前の番号, 次の番号 or None, 種類, t0, t1, 基準のまま (h0, h1) or None)。"""
    out = []
    via = [(t0, t1) for t0, t1, X, Y in m.SHAPE_EV]
    for n, (kind, t0, t1) in enumerate(m.BOUNDARY):
        A = n
        B = n + 1 if kind != 'end' else None
        hold = None
        if kind == 'via':
            h0 = t0 + m.VIA_T
            h1 = h0 + m.VIA_HOLD
            assert any(abs(a - t0) < 1e-6 and abs(b - h0) < 1e-6 for a, b in via)
            hold = (h0, h1)
        out.append((A, B, kind, t0, t1, hold))
    return out


def cnt(t):
    """そのコマのカウンターの表示（数字、または「--」）。"""
    return f'カウンター {m.cnt_text(t)}/分'


def morph_frames():
    """つなぎ目のコマ：直接は形が変わるまん中、基準を通るところは、基準へ変わるまん中・基準のまま・次へ変わるまん中。"""
    no = lambda P: m.PATTERNS[P]['no']
    out = []
    for A, B, kind, t0, t1, hold in boundaries():
        if kind == 'direct':
            out.append(((t0 + t1)/2, f'つなぎ目 {no(A)}→{no(B)}（直接）：形が変わるまん中。{DIRECT_WHAT[B]}。{no(A)}のコピーは枠へ飛んでいる途中'))
        elif kind == 'via':
            h0, h1 = hold
            out.append(((h0 + h1)/2, f'つなぎ目 {no(A)}→{no(B)}（灰色の「つなぎ」を通る）：つなぎの洞調律（75/分・灰色）のまま（{h1 - h0:.1f}秒）。「{m.NEXT_LABEL}」'))
            out.append(((h1 + t1)/2, f'つなぎ目 {no(A)}→{no(B)}（灰色の「つなぎ」を通る）：つなぎ → {no(B)} へ変わるまん中'))
        else:
            out.append(((t0 + t1)/2, f'{no(A)}のあと：灰色の基準の洞調律へもどるまん中（最後の画面へ。冒頭とつながる）'))
    return out


def write_pdf(pngs, fpdf):
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)


def hr_in(a, b):
    """a〜b に中央を通った拍ごとの、カウンターの表示（拍が通った直後）。"""
    return [m.cnt_text(t + 0.02) for t, x, _ in m.hr_crossings() if a <= t < b]


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    hc = m.hr_crossings()
    # ⑩：休みの前の最後の心房細動の拍（次まで 2秒より長い）と、休みのあとの最初の拍（「--」のまま）
    tb_a, tb_b = m.WINDOWS[m.I_TB]
    j_last = next(n for n, (t, x, nxt) in enumerate(hc) if tb_a <= t < tb_b and nxt > m.CNT_STALE_GAP)
    t_last, t_19 = hc[j_last][0], hc[j_last + 1][0]
    # ②：拍がちょうど中央を通った瞬間（ハートが光る）
    a2, b2 = named(1)
    t_flash = next(t for t, x, _ in hc if a2 <= t <= b2 - 0.1) + 0.03
    frames = [(0.5, '冒頭0.5秒（問いかけ「細動？粗動？／見分けられる？」）'),
              (hook_t, '冒頭のフック（止めた波形を変形しているところ）')]
    for i, p in enumerate(m.PATTERNS):
        if i == m.I_TB:
            frames.append((timer_time(), f"{p['no']} {p['name']}（休みのタイマーが数え上がっている途中）"))
        if i == 1:
            frames.append((t_flash, f"{p['no']} {p['name']}（拍が中央を通った瞬間：ハートが光る）"))
        if i == m.I_TB:   # タイマーが止まったところ（次の洞調律の拍が中央を通った直後）。カウンターは「--」のまま
            assert key_time(i) >= t_19
            frames.append((key_time(i), f"{p['no']} {p['name']}（タイマーが止まったところ。休みのあとの最初の拍でも、カウンターは「--」のまま）"))
        else:
            frames.append((key_time(i), f"{p['no']} {p['name']}"))
    for i in range(m.N_PAT):              # 名前とひとことが出そろっているか
        lo, hi = named(i)
        assert any(lo <= t <= hi + 1e-6 for t, _ in frames if m.current(t) == i), i
    frames += morph_frames()
    frames.append((m.T_END + m.FLY + 2.0, f'最後：{m.N_PAT}個の一覧（見分けのポイント）'))
    frames.append((m.T_END + m.FLY + m.END_SWAP + 0.8, f'最後：{m.N_PAT}個の一覧（コメントの呼びかけに入れかわったところ）'))
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
        c = cnt(t) if m.CNT_IN + 0.4 <= t <= m.cnt_out() else ''
        pngs.append(fp); index.append(f'- {k}ページ（{t:.2f}秒）：{name}' + (f'【{c}】' if c else ''))
    thumb = os.path.join(fdir, f'{len(pngs) + 1:02d}.png')
    m.thumbnail_list().save(thumb)
    m.thumbnail_list().save(os.path.join(OUT, 'thumb_reel26_list.png'))
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    for fpdf in (os.path.join(OUT, 'review_reel26_frames.pdf'), os.path.join(REL, 'review_reel26_frames.pdf')):
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
    irreg = ''.join(no(i) for i in sorted(m.IRREG))
    flow = '\n'.join(f"| {no(i)} {m.PATTERNS[i]['name']} | {a:.2f}–{b:.2f} | {' '.join(hr_in(a, b))} |"
                     f" {'あり' if i in m.IRREG else '―'} |"
                     for i, (a, b) in enumerate(m.WINDOWS))
    bnd = []
    for A, B, kind, t0, t1, hold in boundaries():
        vals = ' '.join(hr_in(t0, t1)) or '―'
        if kind == 'direct':
            bnd.append(f'| {no(A)}→{no(B)} | 直接：{DIRECT_WHAT[B]} | {t0:.2f}–{t1:.2f} | {vals} |')
        elif kind == 'via':
            bnd.append(f'| {no(A)}→{no(B)} | 灰色の「つなぎ」の洞調律（75/分）を通る（{m.VIA_T:.1f}秒でつなぎへ・{m.VIA_HOLD:.1f}秒そのまま・{m.VIA_T:.1f}秒で{no(B)}へ。「{m.NEXT_LABEL}」） | {t0:.2f}–{t1:.2f} | {vals} |')
        else:
            bnd.append(f'| {no(A)}→最後 | 灰色の基準の洞調律へもどす（動画の終わりが冒頭とつながる） | {t0:.2f}–{t1:.2f} | {vals} |')
    bnd = '\n'.join(bnd)
    direct_list = '、'.join(f'{no(A)}→{no(B)}' for A, B, kind, *_ in boundaries() if kind == 'direct')
    via_list = '、'.join(f'{no(A)}→{no(B)}' for A, B, kind, *_ in boundaries() if kind == 'via')
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍（1080×1920）で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第26弾「心房細動・心房粗動、14パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音済み。下の秒は動画の中で声が流れる位置）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人）
- 流れ：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 14パターンを1つずつ紹介 → 最後に14個の一覧と見分けのポイント
- **中部の帯は最初から最後まで消えない**：
  - 名前が消えると、紹介したパターンの「コピー」だけが縮んで上下の枠（上2列×4段・下2列×3段）へ飛び、ミニ波形として流れ続ける（帯はそのまま流れる）
  - 同時に、帯に見えている拍が、その場で全部いっしょに次の形へ変わる（P波・デルタ波・R・S・T の高さ・位置・幅、拍の位置、f波・F波の大きさ）。
    拍が跳んだり、消えたり、増えたりはしない。R-R のものさし（下の横棒）もいっしょにのび縮みする
  - **次の形へ直接変わるのは、同じ状態の中だけ**：心房細動のf波・心拍数（①→②→③→④→⑤）と、心房粗動の伝導比（⑪→⑫→⑬→⑭）。直接のつなぎ目：{direct_list}（{m.MORPH_T:.1f}秒）
  - **それ以外のつなぎ目（{via_list}）は、灰色の「つなぎ」を通る**：{m.VIA_T:.1f}秒で洞調律 75/分の形へ → {m.VIA_HOLD:.1f}秒そのまま → {m.VIA_T:.1f}秒で次の形へ。
    つなぎの洞調律は、緑でもパターンの色でもない、うすい灰色の線で描き、そのあいだは名前の位置に小さく「{m.NEXT_LABEL}」と出す（病態の経過ではなく、例と例のあいだの「つなぎ」であることを示す）
  - ⑭のあとは灰色の洞調律へもどして最後の画面へ。動画の終わりが冒頭とつながる
  - 名前・ひとこと・声のあいだは、波形はそのパターンの形そのもの。形が変わるあいだは声なし・名前なし
- この回だけの見せ方：
  - **心拍数カウンター「♥ NNN /分」**：波形の帯の左上（ひとことの下）。後ろに角の丸い暗い板（不透明度 {m.PLATE_A:.0%}）を敷き、R 波が後ろを通っても数字が読めるようにしている。
    帯の拍（R）が画面の中央を通る（ピッという音が鳴る）たびに、その拍とひとつ前の拍の R-R から計算した心拍数（1拍ごとの値）に変わり、ハートがその瞬間に光る。
    数えるのは QRS（心室）の数で、f波・F波は数えない（⑧は48/分、⑪ 4:1 は75/分、⑫ 2:1 は150/分、⑭ 1:1 は300/分）
  - **形が変わるあいだは「--」**：名前が消えて形が変わり始めると {m.CNT_DASH_T:.1f}秒で「--」になり、形が変わり終わったら、次の形の値（モデルの R-R から計算）から表示を再開する（2つの形がまざった値や、灰色のつなぎの 75/分は出さない）
  - 不規則なリズム（{irreg}。⑩は心房細動の区間）のあいだは、数字の右に小さく2行で「{m.CNT_SUB[0]}」「{m.CNT_SUB[1]}」（「--」のあいだは出さない）
  - **⑩の休みのあいだのカウンター**：中央を拍が通らないあいだ、ハートは光らない。次の拍まで {m.CNT_STALE_GAP:.0f}秒より長くあくところ（休み）では、{m.CNT_STALE_AFTER:.1f}秒たったら数字を「--」にする。
    休みのあとの最初の洞調律の拍（60÷{m.TB_PAUSE:.1f}秒）は値を出さず「--」のまま。次の拍から 60/分
  - **休みのタイマー**（⑩）：カウンター・ピッという音と同じ「画面の中央」で数える。最後の心房細動の拍が中央を通ったときに 0 から数え始め（字は 1.1秒から出す）、
    次の洞調律の拍が中央を通ったときに {m.TB_PAUSE:.1f}秒で止まる。字は中央のすぐ左（過ぎた休みの平らな線の上）に置き、止まったあとは波形と一緒に左へ流れる。ものさしの休みの点線も、中央までのびる
  - **R-R のものさし**：波形の下に、拍と拍のあいだの長さを横棒で出す（棒の長さ＝モデルの R の時刻の差）。ふつうは両端の拍が見えている区間だけ描く。
    ⑤⑧（R-R が長い）は、画面の端で切れる棒も、切れた側をうすくして描く（棒がいつも2本以上見える）。⑥では「長い」「短い」の名札を棒の下に出す
  - 冒頭に問いかけ「細動？粗動？／見分けられる？」、最後に「何個わかった？コメントで教えてね」
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。前後のつなぎは洞調律 75/分。背景の方眼は心電図用紙と同じ目盛り（細い線 1mm＝0.04秒・0.1mV、太い線 5mm＝0.2秒・0.5mV）
- 別の回（頻脈の回）では心房細動・心房粗動を代表1つずつしか扱わないので、この回でバリエーションを扱う
- 見分けのポイントを画面のひとことで出す：心房細動＝P波がなく R-R がバラバラ（②）、心房粗動＝のこぎり状のF波 約300/分（⑪）。最後の画面は2行で「{m.END_LINES[0]}」「{m.END_LINES[1]}」
- 各パターンのひとことのうしろに、看護師の動きを色の文字で出す（緑「→ 初めてなら報告」、橙「→ 脈拍と血圧も確認」、紫「→ 12誘導で確認」、赤「→ すぐ報告」）。ナレーションでは「すぐ報告」と言わない
- 名前の色：心房細動のはじまり・f波・心拍数（①〜⑤、水色）、QRSの形・リズムが変わるもの（⑥〜⑨、黄）、止まるとき（⑩、赤みの橙）、心房粗動（⑪〜⑭、桃）
- 画面とキャプションに「数値はこの波形での一例」と明記している
- 出典は LITFL ECG Library／Eponymictionary（下に一覧）

## 動画の流れ（秒）
| パターン | 名前の出ている時間（秒） | 心拍数カウンター（名前の出ているあいだに表示した値・/分） | 「1拍ごとの値」 |
|---|---|---|---|
{flow}

| つなぎ目 | 変わり方 | 形が変わる時間（秒） | そのあいだのカウンターの値（/分） |
|---|---|---|---|
{bnd}

## PDFのページ（時刻の順。【】はそのコマのカウンターの表示）
{chr(10).join(index)}

## 各パターンの描き方（モデルの値）
| パターン | 画面のひとこと ＋ 色の文字 | 描き方 |
|---|---|---|
{rows}

## ナレーション（録音済み。数字は画面に出ているので、声では読まない。「すぐ報告」は声で言わない）
| 文 | 動画の秒 | 台本 |
|---|---|---|
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
### 見せ方（帯を消さずに、その場で形が変わる）・心拍数カウンター
1. **その場で形が変わる見せ方で、誤解を招かないか**：
   - 直接変わるつなぎ目（{direct_list}）：同じ患者さんの経過（f波が小さくなる、速さが変わる、伝導比が変わる）として読まれてよいか。とくに ⑬→⑭ で「伝導比が変わる粗動は、そのうち1:1になる」と読まれないか
   - 灰色の「つなぎ」を通るつなぎ目（{via_list}）：灰色の線と「{m.NEXT_LABEL}」で、「洞調律にもどった」「洞調律から次の不整脈が始まった」という経過ではなく、例と例のあいだのつなぎだと伝わるか（PDF のつなぎ目のページ）
2. **心拍数カウンター**：1拍ごとの値を出し、形が変わるあいだと⑩の休みは「--」にしている。値・「--」の出し方、後ろの暗い板で、読みやすさ・誤解の点で問題はないか
3. **「{m.CNT_SUB[0]}{m.CNT_SUB[1]}」の言い方**：不規則なリズム（{irreg}）で、数字の右に小さく2行で出している。モニターの表示（平均）との違いがこの言い方で伝わるか。⑨ WPWの心房細動で 1拍ごとの値が最大 300/分まで出ることは妥当か
4. **規則的なものの値**：⑧ 48/分（f波は数えず、QRSの数）、⑪ 4:1 で75/分・⑫ 2:1 で150/分・⑭ 1:1 で300/分（F波の数ではなく心室の数）。看護師が「F波 300/分」と「心拍数」を取りちがえないか
5. **⑩ 休みの見せ方**：タイマー（中央で数え、{m.TB_PAUSE:.1f}秒で止まる）・ものさしの点線・カウンターの「--」が、そろって見えるか。実際のモニターの表示と誤解されないか
6. 名前が消えた直後、紹介したパターンのコピーが枠へ飛ぶあいだに、帯の拍は次の形へ変わり始める。コピーと帯の両方が動くことで、見分けにくくならないか
7. 声と名前の時間：声は名前が出てから 0.55秒で話し始め、形が変わるあいだは声なし（上の「ナレーション」と「動画の流れ」の秒）。名前・ひとことと声の内容がずれて見えるところはないか

### パターンごと
8. 14パターンの選び方と並び（はじまり → f波 → 心拍数 → QRSの形 → 止まるとき → 心房粗動）。ほかに入れるべきもの・外したほうがよいものはあるか
9. ① 心房細動の始まり：洞調律3拍 → T波の終わりのPAC → 心房細動、という描き方。色の文字「→ 初めてなら報告」でよいか
10. ② 粗いf波・③ 細かいf波の描き方（LITFL の境目 0.5mm）。③のひとこと「{m.PAT['③']['one']}」と台本「{vo.TEXT['③']}」は妥当か
11. ⑥ アシュマン現象・⑦ 脚ブロックを右脚ブロック型（II誘導で幅の広いS波）で描いたこと。⑨ WPWの心房細動との見分けが伝わるか
12. ⑧ 心房細動＋完全房室ブロック（Regularised AF）：粗いf波＋幅の狭い接合部補充調律 48/分。キャプションのジギタリス中毒の一文は妥当か
13. ⑨ WPWの心房細動の描き方と、キャプションの薬の注意（房室結節を抑える薬で、かえって速くなり、心室細動に移ることがある）
14. ⑩ 徐脈頻脈症候群：心房細動が止まったあと {m.TB_PAUSE:.1f}秒の休み（LITFL：洞停止は3秒超）→ 遅い洞調律60/分。「→ すぐ報告」、台本「{vo.TEXT['⑩']}」は妥当か
15. ⑪〜⑭ 心房粗動：F波の形（II誘導で下向きの のこぎり。ゆっくり下がり、すばやく上がる。平らな区間なし）、⑫ 2:1 を「150/分で規則的なら粗動を疑う」とした言い方、⑭ 1:1 を 300/分・幅の狭いQRSで描いたこと
16. R-R のものさし（波形の下の横棒）：心房細動＝バラバラ、心房粗動＝そろう、の見せ方で誤解はないか（⑬は 0.2秒の倍数の数種類、⑧はそろう、⑥は「長い → 短い」、⑤⑧は端で切れる棒をうすく描く）
17. 色の文字（看護師の動き）の割り当て。①②③⑪「→ 初めてなら報告」、④⑤⑫「→ 脈拍と血圧も確認」、⑥⑦⑬「→ 12誘導で確認」、⑧⑨⑩⑭「→ すぐ報告」。キャプションの 🆕 の行とあわせて、誤解はないか
18. 最後の画面「{m.END_LINES[0]}」「{m.END_LINES[1]}」と、台本のまとめ「{vo.TEXT['まとめ']}」は、⑬（伝導比が変わる粗動）や多源性心房頻拍とあわせて、誤解を招かないか
19. 台本は1パターン1文に詰めた。短くしたことで医学的に誤解を招く文はないか（とくに ①、③、⑧「完全房室ブロックを疑う」、⑩、⑬「細動に似る」、まとめ）

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

    lines = [f'第26弾 心房細動・心房粗動 {m.N_PAT}パターン ― 画面の文字', '',
             f'[見出し] {m.TITLE} {m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 0〜2.4秒] {"／".join(m.QUESTION)}（黄・2行・{m.QUESTION_SIZE}px。出ているあいだは「モニター心電図で見分ける」を消す）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] モニター心電図で見分ける ／ {m.TITLE}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
        lines.append(f"    心拍数カウンター：{' '.join(hr_in(a, b))} /分" + (f"（{m.CNT_SUB[0]}{m.CNT_SUB[1]}）" if i in m.IRREG else ''))
    lines += ['', f'[⑩ 休みのあいだ] 休み 1.1秒 → … → {m.TB_PAUSE:.1f}秒（中央で数える。字は中央のすぐ左）。カウンターは {m.CNT_STALE_AFTER:.1f}秒後に「--」、休みのあとの最初の拍も「--」',
              f'[つなぎ目（{via_list}）] 灰色の洞調律＋「{m.NEXT_LABEL}」（名前の位置・34px）。カウンターは「--」',
              '[波形の下] R-R のものさし（拍と拍のあいだの横棒。左に「R-R」。⑤⑧は端で切れる棒もうすく描く）',
              '[帯の左上] ♥ NNN /分（拍が中央を通るたびに変わる。後ろに暗い板。形が変わるあいだは「--」）',
              '', f'[最後] {m.END_LINES[0]} ／ {m.END_LINES[1]} ／ 保存して見返してね　→ {m.END_SWAP:.1f}秒後に上の2行が「{m.COMMENT}」（黄・42px）に入れかわる',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel26.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
