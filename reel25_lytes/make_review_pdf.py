"""第25弾 高カリウム血症とQT（電解質） ― 専門医レビュー用の資料。

- release/review_reel25_frames.pdf（と out/review_reel25_frames.pdf）：映像のコマを等倍（1080×1920）・無圧縮で1ページずつ。
  冒頭・11パターン（名前とひとことが出そろったところ。①は波の名前 P・Q・R・S・T、⑦⑧は U）・つなぎ目（形が変わるまん中、
  ①基準を通るところは基準の形のまま）・最後・サムネイル。コマは今のコード（make_reel25.frame）から書き出す（映像は書き出し直さない）。
  PNG は out/review_frames/
- review_request.md：依頼文（作品の概要・ページ一覧・描き方の数値・ナレーション（秒つき）・キャプション・見てほしい点）
- out/screen_text_reel25.txt：画面の文字の書き出し

画面に出す数値・依頼文の数値は、モデルの波形から計算した値を使う（手打ちしない）。

使い方:
    python3 make_review_pdf.py
"""
import glob
import os
import re

from PIL import Image

import align_vo as vo
import make_reel25 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REL = os.path.join(HERE, 'release')

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


def named(i):
    """パターン i の名前とひとことが、はっきり出ている時間 (始まり, 終わり)。"""
    a, b = m.WINDOWS[i]
    return a + 0.45, b - 0.3


def key_time(i):
    """パターン i の見どころが、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    if pat['hl'] is m.ALL:
        c = min(pat['L'], 2.0) / 2 + pat['L']
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2
    t = m.t_of(m.SEGS[i][0] + c + 0.25)
    lo, hi = named(i)
    return min(max(t, lo + 0.3), hi)


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
    """つなぎ目ごとに：(前の番号, 次の番号 or None（最後）, 'direct'／'via'／'end', [形が変わる (t0, t1, 前の形, 次の形, 'morph'／'xf')])。"""
    ev = list(m.SHAPE_EV)
    out, p = [], 0
    for i in range(1, m.N_PAT):
        if i in m.DIRECT:
            out.append((i - 1, i, 'direct', [ev[p]])); p += 1
        else:
            out.append((i - 1, i, 'via', [ev[p], ev[p + 1]])); p += 2
    out.append((m.N_PAT - 1, None, 'end', [ev[p], ev[p + 1]]))
    assert p + 2 == len(ev)
    return out


def _rate(k):
    return f'{60/m.KIND_RR[k]:.0f}'


DIRECT_WHAT = {1: 'T波が高く、細く、とがっていく（高Kのはじめ）',
               2: 'P波が低く平たくなり、PRが延びる',
               3: f"P波が消え、拍の間隔が延びる（60 → {_rate('K3')}/分）",
               4: f"QRSの幅が広がり、Tとつながる（{_rate('K3')} → {_rate('K4')}/分。速くならない）",
               5: f"QRSとTが溶けて、サイン波になる（{_rate('K4')} → {_rate('SW')}/分）",
               7: 'T波がさらに低く、STが下がり、U波がTとつながる（低Kが重くなる）'}
NS_TXT = f"つなぎの洞調律（{_rate('NS')}/分・うすい灰色。どのパターンでもない）"


def morph_frames():
    """つなぎ目のコマ：直接は形が変わるまん中、①基準を通るところは、基準へ変わるまん中・基準のまま・次へ変わるまん中。"""
    no = lambda P: m.PATTERNS[P]['no']
    out = []
    for A, B, kind, evs in boundaries():
        if kind == 'direct':
            t0, t1 = evs[0][:2]
            out.append(((t0 + t1)/2, f'つなぎ目 {no(A)}→{no(B)}（直接）：形が変わるまん中。{DIRECT_WHAT[B]}。{no(A)}のコピーは枠へ飛んでいる途中'))
        elif kind == 'via':
            (a0, a1, *_, mode), (b0, b1, *_) = evs
            lbl = m.NEXT_LABEL_SW if mode == 'xf' else m.NEXT_LABEL
            if mode == 'xf':
                out.append((a0 + 0.35*(a1 - a0), f'つなぎ目 {no(A)}→{no(B)}（つなぎを通る）：サイン波を形を変えずにうすくしていくところ（クロスフェード。サイン波が⑤のような形にもどる絵にしない）'))
                out.append((a0 + 0.45*(a1 - a0), f'つなぎ目 {no(A)}→{no(B)}（つなぎを通る）：うすくなったサイン波に、灰色のつなぎの洞調律が重なって出てくるところ。「{lbl}」'))
            else:
                out.append(((a0 + a1)/2, f'つなぎ目 {no(A)}→{no(B)}（つなぎを通る）：{no(A)} → つなぎの洞調律へ変わるまん中（色も灰色へ）。{no(A)}のコピーは枠へ飛んでいる途中'))
            out.append(((a1 + b0)/2, f'つなぎ目 {no(A)}→{no(B)}（つなぎを通る）：{NS_TXT}のまま（{b0 - a1:.1f}秒）。「{lbl}」'))
            out.append(((b0 + b1)/2, f'つなぎ目 {no(A)}→{no(B)}（つなぎを通る）：つなぎ → {no(B)} へ変わるまん中'))
        else:
            (a0, a1, *_), (b0, b1, *_) = evs
            out.append(((a1 + b0)/2, f'{no(A)}のあと：{NS_TXT}を通り、①基準（60/分）の形へもどす（最後の画面へ。冒頭とつながる）'))
    return out


def write_pdf(pngs, fpdf):
    try:
        import img2pdf
        with open(fpdf, 'wb') as f:
            f.write(img2pdf.convert(pngs))
    except ImportError:
        ims = [Image.open(q).convert('RGB') for q in pngs]
        ims[0].save(fpdf, save_all=True, append_images=ims[1:], resolution=72, quality=95, subsampling=0)


def label_window(i):
    """波の名前（①の P・Q・R・S・T、⑦⑧の U）がはっきり出ている時間（frame の draw_wave_labels と同じ出し入れ）。"""
    a, b = m.WINDOWS[i]
    return a + 0.5 + 0.4 + 0.05, b - 0.45 - 0.05


def main():
    os.makedirs(OUT, exist_ok=True)
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    frames = [(0.0, '冒頭（0秒）：問いかけ「この変化、気づける？」とタイトル'),
              (hook_t, '冒頭のフック（止めた波形を変形しているところ）')]
    for i, p in enumerate(m.PATTERNS):
        if i == 0:
            lo, hi = label_window(0)
            frames += [(lo + 0.15, f"{p['no']} {p['name']}（波の名前 P・Q・R・S・T。1つめ）"),
                       (lo + 0.15 + 0.5*m.RR, f"{p['no']} {p['name']}（波の名前 P・Q・R・S・T。拍が半拍ぶん流れたところ）")]
        elif i in (6, 7):
            lo, hi = label_window(i)
            what = '低いT波の上に「T」・U波の上に「U」' if i == 6 else 'U波の上に「U」'
            frames.append((min(max(key_time(i), lo), hi), f"{p['no']} {p['name']}（{what}）"))
        else:
            frames.append((key_time(i), f"{p['no']} {p['name']}"))
    for i in range(m.N_PAT):              # 名前とひとことが出そろっているか
        lo, hi = named(i)
        assert any(lo <= t <= hi + 1e-6 for t, _ in frames if m.current(t) == i), i
    frames += morph_frames()
    frames.append((m.T_END + m.FLY + 3.2, f'最後：{m.N_PAT}個の一覧（「保存して見返してね」「何個わかった？コメントで教えてね」）'))
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
    m.thumbnail_list().save(os.path.join(OUT, 'thumb_reel25_list.png'))
    pngs.append(thumb); index.append(f'- {len(pngs)}ページ：サムネイル（投稿の表紙）')
    for fpdf in (os.path.join(OUT, 'review_reel25_frames.pdf'), os.path.join(REL, 'review_reel25_frames.pdf')):
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
    flow = '\n'.join(f"| {no(i)} {m.PATTERNS[i]['name']} | {a:.2f}–{b:.2f} |" for i, (a, b) in enumerate(m.WINDOWS))
    bnd = []
    for A, B, kind, evs in boundaries():
        t0, t1 = evs[0][0], evs[-1][1]
        if kind == 'direct':
            bnd.append(f'| {no(A)}→{no(B)} | 直接：{DIRECT_WHAT[B]} | {t0:.2f}–{t1:.2f} |')
        elif kind == 'via':
            if evs[0][4] == 'xf':
                bnd.append(f'| {no(A)}→{no(B)} | つなぎを通る：サイン波は形を変えずにうすくし、灰色のつなぎを重ねて出す（{m.XF_T:.1f}秒のクロスフェード）・{m.VIA_HOLD:.1f}秒そのまま・{m.VIA_T:.1f}秒で{no(B)}へ。「{m.NEXT_LABEL_SW}」 | {t0:.2f}–{t1:.2f} |')
            else:
                bnd.append(f'| {no(A)}→{no(B)} | つなぎを通る（{m.VIA_T:.1f}秒でつなぎへ・{m.VIA_HOLD:.1f}秒そのまま・{m.VIA_T:.1f}秒で{no(B)}へ）。「{m.NEXT_LABEL}」 | {t0:.2f}–{t1:.2f} |')
        else:
            bnd.append(f'| {no(A)}→最後 | つなぎを通って①基準（60/分）の形へもどす（動画の終わりが冒頭とつながる）。「次の例」は出さない | {t0:.2f}–{t1:.2f} |')
    bnd = '\n'.join(bnd)
    direct_list = '、'.join(f'{no(i - 1)}→{no(i)}' for i in sorted(m.DIRECT))
    via_list = '、'.join(f'{no(i - 1)}→{no(i)}' for i in range(1, m.N_PAT) if i not in m.DIRECT)
    lab = '、'.join(f'{ch}（文字の中心が R頂点から {dt*1000:+.0f}ms・基線から {-dy/m.F_MV:+.2f}mV ぶんの高さ）' for ch, dt, dy in m.PQRST_LABELS)
    u_lab = '、'.join(f"{no(i)}：U波の頂点（R頂点から {m._u_label(m.PATTERNS[i]['kind'])[0][1]*1000:.0f}ms）の上"
                      for i in (6, 7))
    txt = f'''あなたは循環器専門医として、看護師・看護学生向けの心電図教育リール（Instagram）を医学的にレビューしてください。
添付は「映像のコマを等倍（1080×1920）で1ページずつ並べたPDF」です。ナレーションとキャプションは、この依頼文の中にあります。

## 作品の概要
- 第25弾「高カリウム血症とQT（電解質）、11パターン」。縦 1080×1920・60fps・約{m.DUR:.0f}秒・ナレーション入り（録音済み。下の秒は動画の中で声が流れる位置）
- 見る人：看護師・看護学生（病棟でモニター心電図を見る人。透析・腎不全・利尿薬の患者さんを受け持つ）
- 流れ：冒頭3秒で波形を止めて5パターンに素早く変形（フック）→ 11パターンを1つずつ紹介 → 最後に11個の一覧
- **中部の帯は最初から最後まで消えない（今回の作り）**：
  - 名前が消えると、紹介したパターンの「コピー」だけが縮んで上下の枠へ飛び、ミニ波形として流れ続ける（帯はそのまま流れる）
  - 同時に、帯に見えている拍が、その場で全部いっしょに次のパターンの形へ変わる（P波の高さ・幅・PR、QRSの幅と形、ST、T波、U波、拍の間隔。⑤→⑥はサイン波へ溶ける）。
    拍が跳んだり、消えたり、増えたりはしない
  - 同じ病態の中（{direct_list}）だけ：次の形へ直接（{m.MORPH_T:.1f}秒）。高Kは ①→②→③→④→⑤→⑥ と1本の帯の上で続けて変わる
  - それ以外のつなぎ目（{via_list}、⑪→最後）：どのパターンでもない「つなぎ」の洞調律（{_rate('NS')}/分）を、うすい灰色（パターンの色ではない）で描いて通る。
    つなぎのあいだ、名前の位置に小さく「{m.NEXT_LABEL}」（⑥のあとは「{m.NEXT_LABEL_SW}」）。⑪→最後は「次の例」なしで①基準へもどす
  - ⑥サイン波のあとだけは形を変えない：サイン波をまずうすくし、灰色のつなぎを重ねて出す（クロスフェード）。サイン波が⑤のような形にもどりながら正常になる絵にしないため
  - 動画の終わりは冒頭とつながる
  - 名前・ひとこと・声のあいだは、波形はそのパターンの形そのもの。形が変わるあいだは声なし・名前なし
- 波形はモデルで作った模式図。**II誘導・実際の速さ（25mm/秒）**。基準の拍は60/分（RR 1.0秒なので QTc（Bazett）＝QT）。背景のマス目は心電図用紙と同じ（小さいマス 0.04秒・0.1mV、大きいマス 0.2秒・0.5mV）
- 上の6つは高カリウムの進み方の順（①基準 → ②テント状T波 → ③PR延長・P波平坦 → ④P波消失・徐脈 → ⑤QRS幅の拡大 → ⑥サイン波）
- 下の5つはQTのまわり（⑦⑧低K、⑨低Ca・⑩薬剤などのQT延長、⑪高CaのQT短縮）。R on T・トルサードは前の回（第21弾）で扱ったので、ここでは「QT延長」まで。低マグネシウム血症はキャプションでふれる
- この回だけの見せ方：
  - **波の名前（今回足した）**：①の紹介中、中部の帯の拍に P・Q・R・S・T の文字を色分けで出す（P 黄・Q 水色・R 白・S 黄緑・T 橙、太字34px・暗いふちどり）。
    拍にくっつけて流す（R頂点が画面の x {m.LABEL_X0}〜{m.LABEL_X1}px にあるあいだ。端はうすく）。置き場所：{lab}。
    ⑦⑧では、U波の上に「U」（ピンク）：{u_lab}（U波の高さ・位置はモデルの値から）。⑦では、低いT波の頂点の上にも小さめ（28px）の「T」（橙）。⑧（T波がほぼない）は「U」だけ
  - **基準のゴースト**：②〜⑪ の紹介中（⑥サイン波は除く）、中部の帯に①基準の拍を、そのパターンの拍と同じR頂点の位置に白っぽくうすく重ねる（どこが変わったかが分かるように）。
    帯の下に「{m.GHOST_LEGEND}」。名前の出ているあいだだけ出し、形が変わっているあいだは出さない。⑥はとがったQRSがサイン波を突き抜けて誤解を招くので重ねない。
    ④⑤（P波なし）では、ゴーストのP波も描かない（「P波が見えない」のに、うすいPが見えないように）
  - **高Kの心電図変化のゲージ**：②〜⑥ のあいだ、左の余白に縦のゲージ（見出し「{''.join(m.GAUGE_TITLE)}」、下「はじめ」→ 上「進む」）。形が変わるのといっしょになめらかに上がり、⑥でいちばん上・赤。**Kの数値は書かない**（段階とK値は一致しないため）。
    ゲージの下に「{m.GAUGE_NOTE}」
  - 冒頭に問いかけ「この変化、気づける？」、最後に「何個わかった？コメントで教えてね」
- 各パターンのひとことのうしろに、看護師がすることを色の文字で出す（{'、'.join('「' + v[0] + '」' for v in m.TAGS.values())}）。ナレーションでは「すぐ報告」と言わない
- 画面とキャプションに「数値はこの波形での一例」と明記している。画面の数値（PR・QTc・心拍数）はモデルの波形から計算した値（QTの終わりは最大の下り勾配の接線と基線の交点、QTcはBazett）
- 出典はすべて LITFL ECG Library（下に一覧）

## 動画の流れ（秒）
| パターン | 名前の出ている時間（秒） |
|---|---|
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

## ナレーション（録音済み。数字は画面に出ているので、声では読まない）
文の中の息継ぎ（間）は 0.45秒にそろえた。まとめの文は録り直した（同じ声・1.2倍速）。
| 文 | 動画の秒 | 台本 |
|---|---|---|
{narr}

## キャプション
```
{caption}
```

## とくに見てほしい点
### 今回の作り（帯を消さずに、その場で形が変わる）・波の名前について
1. **その場で形が変わる見せ方で、誤解を招かないか**。とくに直接変わるつなぎ目（{direct_list}）：
   - ①→②→③→④→⑤→⑥：高Kの段階が1本の帯の上で続けて変わる。「この順に必ず進む」「段階とK値が対応する」「時間をかけてゆっくり進む（どこかで止まる・待てる）」と読まれないか
     （LITFL：usual order だが、この順とはかぎらず、K値とも一致しない。どの段階でも突然VF・心停止になりうる。画面ではゲージの下に「{m.GAUGE_NOTE}」、まとめの声・最後の画面でも伝えている）
   - ③→④（P波が消えて 60 → {_rate('K3')}/分）、④→⑤（QRSが広がる。{_rate('K4')}/分のまま）、⑤→⑥（サイン波へ溶ける。{_rate('SW')}/分）：心拍数の変わり方が妥当か
   - ⑦→⑧：低Kが重くなると T波がさらに低く、STが下がり、TとU波がつながる、という見せ方
2. **つなぎを通るつなぎ目**（{via_list}、⑪→最後）：灰色の「つなぎ」の洞調律（{_rate('NS')}/分）を通り、「{m.NEXT_LABEL}」を出してから次の形へ。とくに ⑥サイン波 → つなぎ → ⑦低K（サイン波はクロスフェードで消す・「{m.NEXT_LABEL_SW}」）が、
   「サイン波が自然に（または治療で）正常にもどる」「高Kのあとに低Kになる」といった経過として読まれないか。灰色のつなぎを、パターンの1つや患者さんの経過と取りちがえないか。直接でよいつなぎ目との振り分けは妥当か
3. **波の名前の置き場所（P・Q・R・S・T）**：①の帯の拍に、P（P波の上）・Q（Rの手前の小さなq の左下）・R（R頂点の右）・S（Rのあとのくぼみの右下）・T（T波の上）。
   PDF の①のページで、文字がそれぞれの波を正しく指しているか（Q と S が別の部分を指して見えないか。R を頂点の真上でなく右に置いたこと）
4. **T・U の置き場所**：⑦（T波が低く、うしろにU波）で低いT波の上に小さめの「T」、U波の頂点の上に「U」。⑧（STが下がり、TとU波がつながる）は「U」だけ。文字の位置は妥当か。
   T波とU波の取りちがえ（U波をT波と思う、QT を QU で測る）を招かないか。モニター（II誘導）で U波をこの大きさで描くこと（LITFL：V2〜V3 で最もよく見える）
5. ゲージ（見出し「{''.join(m.GAUGE_TITLE)}」、はじめ → 進む、下に「{m.GAUGE_NOTE}」）が形の変化といっしょになめらかに上がること、基準のゴースト・「{m.GHOST_LEGEND}」を形が変わるあいだは消すこと。誤解はないか
6. 名前が消えた直後、紹介したパターンのコピーが枠へ飛ぶあいだに、帯の拍は次の形へ変わり始める。コピーと帯の両方が動くことで、見分けにくくならないか（PDF のつなぎ目のページ）
7. 声と名前の時間：声は名前が出てから 0.55秒で話し始め、形が変わるあいだは声なし（上の「ナレーション」と「動画の流れ」の秒）。名前・ひとことと声の内容がずれて見えるところはないか

### パターンごと
8. 11パターンの選び方と並び（ジギタリス効果は外した、低Mgはキャプションだけ）。上の6つを「高カリウムの進み方」（LITFL の usual order：T波 → P波・PR → QRS → サイン波）として順に並べたこと
9. ⑥サイン波の描き方（{60/m.RR_SW:.0f}/分・なめらかな波）と、台本「サイン波。いつ心停止しても、おかしくない。」、画面の色の文字「→ 脈を確認・応援を呼ぶ」。サイン波の心拍数・形はこれでよいか
10. ④「P波消失・徐脈」を1つにまとめたこと（{60/m.RR_K3:.0f}/分、P波なし、QRS 約{m.measure('K3', m.RR_K3)['qrs']:.0f}msの補充調律）。高Kの徐脈の代表の形として妥当か
11. ⑤QRS幅の拡大：QRS 約{m.measure('K4', m.RR_K4)['qrs']:.0f}ms・形がくずれてTとつながる描き方。P波を描いていない（④でP波が消えたあと、という並びのため）
12. ⑦⑧低K：⑦のU波の大きさ（U/T {_ut('L1'):.1f}、LITFL：T波の25%を超えると prominent）、⑧のU/T比・ST低下・「→ すぐ報告」は妥当か
13. ⑨低Ca（STが長く、T波の形は同じ）と ⑩薬剤などのQT延長（T波が遅く幅広い）の描き分け。QTc {m.QTC_C1}ms・{m.QTC_D1}ms の数値
14. ⑪高Ca（QTc {m.QTC_C2}ms、STがほとんどない）の描き方
15. 色の文字の割りふり：②〜⑤と⑧「すぐ報告」、⑥「脈を確認・応援を呼ぶ」、⑦⑪「採血の値も確認」、⑨「報告・採血も確認」、⑩「12誘導で確認・報告」。②テント状T波だけでも「すぐ報告」でよいか
16. 台本は1パターン1文（声で3〜4秒）に詰め、くわしい説明は画面のひとこととキャプションにまかせた。短くしたことで、医学的に欠けて誤解を招く文はないか（とくに ⑥、まとめ「{vo.TEXT['まとめ']}」）
17. スマホの大きさで、③の平たいP波、⑦のU波が読み取れるか
18. 基準のゴースト（うすい線）：拍をR頂点でそろえて重ねたこと。とくに④⑤（{_rate('K3')}/分）は基準と心拍数がちがうので、基準の拍をそのパターンの拍の位置に置いている（P波は描かない）。誤解を招かないか

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

    lines = [f'第25弾 高カリウム血症とQT（電解質） {m.N_PAT}パターン ― 画面の文字', '',
             f'[見出し] {m.TITLE} {m.N_PAT}パターン（「{m.N_PAT}」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] {m.HOOK_Q} ／ 心電図で気づく電解質 ／ {m.TITLE}',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        alert = f" {m.TAGS[pat['tag']][0]}"
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']}{alert} ／ ヒント：{pat['hint']}")
    lines += ['', '[①] 帯の拍に P・Q・R・S・T（色分け）', '[⑦] 低いT波の上に T、U波の上に U', '[⑧] U波の上に U',
              f'[②〜⑥] 左の余白に縦のゲージ：上から「高Kの／心電図／変化」「進む」・下「はじめ」（数値なし）',
              f'[②〜⑥] ゲージの下：{m.GAUGE_NOTE}',
              f'[病態が変わるつなぎ目] {m.NEXT_LABEL}（⑥のあとは {m.NEXT_LABEL_SW}）',
              f'[②〜⑪（⑥を除く）] ①の枠：① 洞調律（基準）＝下のうすい線',
              f'[②〜⑪（⑥を除く）] 帯の下：{m.GHOST_LEGEND}',
              '', f'[最後] {m.END_LINE} ／ {m.SAVE_LINE} ／ {m.COMMENT_LINE}',
              f'[左下] {m.NOTE1} ／ {m.NOTE2}', '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel25.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
