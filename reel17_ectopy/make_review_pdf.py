"""専門医レビュー用の資料：1ページ1コマのPDF ＋ 画面文言の書き出し。

ecg-reel-qc の決まり：1枚の縦長シートではなく、1ページ1コマのPDFにする（縮小で小さい文字が
読めなくなるため）。画面に出す数値は、モデルの波形から計算した値を使う。

使い方:
    python3 make_review_pdf.py      # out/review_reel17_v2.pdf と out/screen_text_reel17_v2.txt
"""
import os

import numpy as np
from PIL import Image, ImageDraw

import make_reel17_v2 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
PW, PH = 1240, 1754                       # A4・150dpi
INK = (24, 28, 30)
SUB = (90, 98, 104)
LINE = (210, 214, 216)

LITFL_PAC = 'https://litfl.com/premature-atrial-complex-pac/'
LITFL_PJC = 'https://litfl.com/premature-junctional-complex-pjc/'
LITFL_PVC = 'https://litfl.com/premature-ventricular-complex-pvc-ecg-library/'
LITFL_VT = 'https://litfl.com/ventricular-tachycardia-monomorphic-ecg-library/'
AN_PVC = 'https://www.myamericannurse.com/premature-ventricular-complexes/'

# パターンごとの根拠（LITFL本文の要旨）と、とくに見てほしい点
NOTES = {
    0: dict(src=[LITFL_PAC],
            basis=["Abnormal (non-sinus) P wave usually followed by a normal QRS (< 120 ms)",
                   "PACが洞結節をリセットし、休みは直前のR-Rの2倍にならない"],
            ask=["P'の形（小さく、少し二相性）と、休み 1.40秒（2拍ぶん 1.60秒と一致しない）でよいか"]),
    1: dict(src=[LITFL_PAC],
            basis=["P'が直前のT波に隠れ、'peaked' / 'camel hump' に見える",
                   "専門医レビュー（2026-10-02）：伝わらないPAC（0.27秒）より早いP'が伝わるのは矛盾 → T波の下り坂へ遅らせる"],
            ask=["P'を直前のRから0.32秒（T波の下り坂）、QRSを0.50秒（P'→R 0.18秒でPRが少し延びる）に置いた",
                 "P'の位置の順：③伝わらない 0.27秒 ＜ ④変行伝導 0.29秒 ＜ ②隠れる 0.32秒 ＜ ①PAC 0.44秒"]),
    2: dict(src=[LITFL_PAC],
            basis=["早すぎるPACは心室に伝わらず、P'のあとにQRSが来ない（blocked PAC）",
                   "洞結節がリセットされ、休みが続く"],
            ask=["P'をT波の頂点（直前のRから0.27秒）に置いた。伝わらない早さとして妥当か",
                 "休み 1.40秒（洞の間隔 0.80秒の約1.75倍）の見せ方でよいか"]),
    3: dict(src=[LITFL_PAC],
            basis=["早いPACは変行伝導し、多くは右脚ブロックの形（右脚の不応期が長いため）",
                   "前にP波があることでPVCと見分ける"],
            ask=["II誘導で、幅の広いQRS（約138ms）と終わりのなまったS波で描いた。右脚ブロック型の変行伝導の見え方として妥当か"]),
    4: dict(src=[LITFL_PJC],
            basis=["細いQRS。P波がないか、逆行性P波がQRSの前・中・後に出る（前なら PR < 120ms）",
                   "LITFL は「代償性休止を伴う」。専門医レビューは「心房へ逆行して洞結節をリセットし、不完全代償性になることが多い」"],
            ask=["【専門医レビューに合わせた】休みを 1.46秒（2拍ぶん 1.60秒より短い）にした。LITFL どおり2拍ぶんに戻すかは要相談",
                 "P波なし（逆行性P波はQRSに埋もれる）で描いた"]),
    5: dict(src=[LITFL_PVC],
            basis=["QRS ≥ 120ms・形が異常、ST-TはQRSと逆向き",
                   "Usually followed by a full compensatory pause（直前のR-Rの2倍）"],
            ask=["QRS 約142ms、休み 1.60秒（2拍ぶん）。ひとこと「休みは2拍ぶん」でよいか（LITFLは usually）"]),
    6: dict(src=[LITFL_PVC],
            basis=["Retrograde capture：房室結節を逆行して心房が興奮し、QRSのあとに逆向きのP波（retrograde P wave）",
                   "専門医レビュー：逆行性P波が洞結節をリセットすると、休みは不完全代償性（2拍ぶんより短い）"],
            ask=[f"PVCを0.40秒、逆行性P波を {0.40+m.RETRO_P:.2f}秒（洞のPが来る0.64秒より前）に置き、洞結節がリセットされて次の拍が1.48秒に来るようにした"]),
    7: dict(src=[LITFL_PVC],
            basis=["Multifocal：2つ以上の起源から出て、QRSの形が複数"],
            ask=["上向きのPVC（形A）と、下向きのPVC（形B・約151ms）の2種類で描いた"]),
    8: dict(src=[LITFL_PVC, AN_PVC],
            basis=["Bigeminy — every other beat is a PVC",
                   "American Nurse：PVCは脈として触れないことがあり、触診で正常の拍だけを数える"],
            ask=["ひとこと「脈は半分のことも」でよいか（いつもではない、の含みで）"]),
    9: dict(src=[LITFL_PVC], basis=["Trigeminy — every third beat is a PVC"], ask=[]),
    10: dict(src=[LITFL_PVC], basis=["Quadrigeminy — every fourth beat is a PVC"], ask=[]),
    11: dict(src=[LITFL_PVC], basis=["Couplet — two consecutive PVCs"],
              ask=["ひとこと「→ 報告」は施設の基準に合わせて変えるべきか"]),
    12: dict(src=[LITFL_PVC, LITFL_VT],
             basis=["PVCページ：3連の呼び方には幅がある。合意としては、3〜30個連続・100/分超を非持続性心室頻拍",
                    "VTページ：Non-sustained = 3つ以上連続、30秒未満で自然に止まる"],
             ask=["4連（間隔0.42秒＝約143/分）で描いた。ひとこと「3つ以上・100/分超 → 非持続性心室頻拍」でよいか"]),
    13: dict(src=[LITFL_PVC],
             basis=["Frequent PVCs は通常良性。ただしQTc延長があると R on T によりトルサードの引き金になりうる"],
             ask=["PVCを直前のRから0.27秒（T波の頂点）に置いた",
                  "ひとこと「QT延長があると危ない」でよいか"]),
}


def font(size, weight=500):
    return m.font(size, weight)


def wrap(d, text, f, width):
    lines, cur = [], ''
    for ch in text:
        if d.textlength(cur + ch, font=f) > width and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def page(img, title, sections, footer):
    pg = Image.new('RGB', (PW, PH), (255, 255, 255))
    d = ImageDraw.Draw(pg)
    # 左：コマ（縦長のまま）
    fh = 1060
    fw = int(img.size[0] * fh / img.size[1])
    pg.paste(img.resize((fw, fh), Image.LANCZOS), (60, 150))
    d.rectangle([60, 150, 60 + fw, 150 + fh], outline=LINE, width=2)
    # 上：見出し
    d.text((60, 60), title, font=font(40, 800), fill=INK)
    # 右：説明
    x, y, w = 60 + fw + 40, 150, PW - (60 + fw + 40) - 50
    for head, items in sections:
        d.text((x, y), head, font=font(26, 800), fill=INK); y += 42
        for it in items:
            for k, ln in enumerate(wrap(d, it, font(22, 500), w - 24)):
                d.text((x + (0 if k else 0), y), ('・' if k == 0 else '　') + ln, font=font(22, 500), fill=INK)
                y += 32
            y += 4
        y += 18
    d.text((60, PH - 60), footer, font=font(18, 500), fill=SUB)
    return pg


def ectopic_time(i):
    """パターン i の最初の期外収縮が、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    first = min(r for r, k in pat['beats'] if k not in ('N', 'p'))
    t = m.t_of(m.SEGS[i][0] + first + 0.25)
    a, b = m.WINDOWS[i]
    return min(max(t, a + 0.6), b - 0.2)


def beat_table(i):
    pat = m.PATTERNS[i]
    rows = []
    prev = None
    for r, k in pat['beats']:
        if k == 'p':
            rows.append(f"{r:4.2f}秒  洞のP（伝わらない・隠れる）")
            continue
        name = {'N': 'ふつうの拍', 'A': 'PAC', 'Aa': '変行伝導のPAC', 'B': "伝わらないPAC（P'のみ）",
                'J': 'PJC', 'V': 'PVC', 'Vr': 'PVC＋逆行性P', 'V2': 'PVC（形B）'}[k]
        rr = '' if prev is None else f"（前の拍から {r-prev:.2f}秒）"
        rows.append(f"{r:4.2f}秒  {name}{rr}")
        if k != 'B':
            prev = r
    rows.append(f"周期 {pat['L']:.2f}秒 × {pat['rep']}回")
    return rows


def qrs_width(f):
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); mk = (np.abs(v) > 0.05) & (tt < 0.11)
    return (tt[mk].max() - tt[mk].min()) * 1000


def main():
    os.makedirs(OUT, exist_ok=True)
    pages = []
    foot = f'第17弾 期外収縮 まず覚えたい14パターン（{m.DUR:.1f}秒）・数値はこの波形での一例・参考 LITFL ECG Library'

    # 1ページめ：全体と、とくに見てほしい点
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    pages.append(page(m.frame(hook_t), '全体（冒頭3秒のフック）', [
        ('構成', [f'0〜{m.T_GO:.1f}秒：波形を止めて、①→⑨→⑧→⑭→⑬ に素早く変形（フック）',
                  f'{m.T_TITLE:.1f}〜{m.T_END:.1f}秒：14パターンを1つずつ紹介。紹介が終わると、その波形が縮んで上下の枠へ移り、ミニ波形として流れ続ける',
                  f'{m.T_END + m.FLY:.1f}秒〜：14個の一覧と「保存して見返してね」。最後は冒頭の画面に戻り、ループでつながる',
                  '実際の速さ（25mm/秒）・心拍数75/分・II誘導を想定']),
        ('とくに見てほしい点', ['⑦ 逆行性P波つきPVCの休みの長さ（7ページめ）',
                                 '② と ③ の、P\'をT波のどこに重ねるか（3・4ページめ）',
                                 '④ 変行伝導の形、⑤ PJCを P波なしで代表させてよいか',
                                 '見出し「まず覚えたい14パターン」の選び方。間入性PVC（出典を確認できず）と、右室・左室起源（V1が必要）は入れていない']),
        ('QRS幅（モデルの波形から計算）', [f'ふつう {qrs_width(m.qrs_normal):.0f}ms', f'変行伝導 {qrs_width(m.qrs_aberrant):.0f}ms',
                                         f'PVC（形A）{qrs_width(m.qrs_pvc):.0f}ms', f'PVC（形B）{qrs_width(m.qrs_pvc2):.0f}ms']),
    ], foot))

    for i, pat in enumerate(m.PATTERNS):
        t = ectopic_time(i)
        n = NOTES[i]
        pages.append(page(m.frame(t), f"{pat['no']} {pat['name']}（{t:.1f}秒のコマ）", [
            ('画面の文字', [f"名前：{pat['no']} {pat['name']}", f"ひとこと：{pat['one']}", f"紹介前のヒント：{pat['hint']}"]),
            ('波形（R頂点の時刻）', beat_table(i)),
            ('根拠（LITFLほか）', n['basis']),
            ('見てほしい点', n['ask'] or ['とくになし']),
            ('出典', n['src']),
        ], foot))

    pages.append(page(m.frame(m.T_END + m.FLY + 2.5), '最後：14個の一覧', [
        ('画面の文字', ['1拍だけ早かったら、この14パターン', '保存して見返してね']),
        ('見てほしい点', ['ミニ波形では、期外収縮の拍だけ線を太く、ふつうの拍を少し薄くしている',
                          'スマホの大きさで、②⑤⑦の違いが読み取れるか']),
    ], foot))

    pdf = os.path.join(OUT, 'review_reel17_v2.pdf')
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=150)
    print(pdf, len(pages), 'ページ')

    # 画面文言の書き出し
    lines = ['第17弾 期外収縮 まず覚えたい14パターン ― 画面の文字', '',
             '[見出し] 期外収縮、まず覚えたい14パターン（「14」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ 期外収縮',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']} ／ ヒント：{pat['hint']}")
    lines += ['', f"[{m.T_END + m.FLY:.1f}秒〜] 1拍だけ早かったら、この14パターン ／ 保存して見返してね",
              '[左下] 実際の速さ（心拍数75/分） ／ ※数値はこの波形での一例',
              '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel17_v2.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
