"""第18弾 徐脈 ― 専門医レビュー用の資料：1ページ1コマのPDF ＋ 画面文言の書き出し。

ecg-reel-qc の決まり：1枚の縦長シートではなく、1ページ1コマのPDFにする（縮小で小さい文字が
読めなくなるため）。画面に出す数値は、モデルの波形から計算した値を使う。

使い方:
    python3 make_review_pdf.py      # out/review_reel18.pdf と out/screen_text_reel18.txt
"""
import os

import numpy as np
from PIL import Image, ImageDraw

import make_reel18 as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
PW, PH = 1240, 1754                       # A4・150dpi
INK = (24, 28, 30)
SUB = (90, 98, 104)
LINE = (210, 214, 216)

L = 'https://litfl.com/'
SRC = dict(nsr=L+'normal-sinus-rhythm-ecg-library/', snd=L+'sinus-node-dysfunction-sick-sinus-syndrome/',
           sab=L+'sinoatrial-exit-block-ecg-library/', av1=L+'first-degree-heart-block-ecg-library/',
           wk=L+'av-block-2nd-degree-mobitz-i-wenckebach-phenomenon/', m2=L+'av-block-2nd-degree-mobitz-ii-hay-block/',
           fix=L+'av-block-2nd-degree-fixed-ratio-blocks/', chb=L+'av-block-3rd-degree-complete-heart-block/',
           jer=L+'junctional-escape-rhythm-ecg-library/', ver=L+'ventricular-escape-rhythm-ecg-library/',
           af=L+'atrial-fibrillation-ecg-library/')

NOTES = {
    0: dict(src=[SRC['nsr']], basis=['Sinus bradycardia = sinus rhythm with resting heart rate < 60 bpm in adults'],
            ask=['45/分で描いた。ひとこと「P→QRSはふつう。60/分より遅い」でよいか']),
    1: dict(src=[SRC['snd'], SRC['sab']],
            basis=['洞機能不全の心電図：Sinus Arrest — pause > 3 seconds',
                   '洞停止はペースメーカー細胞（P cells）が興奮をつくれない。洞房ブロックは伝えられない'],
            ask=['休み 3.3秒（直前のP-P 0.80秒の4.12倍で、倍数にしていない）。洞房ブロックとの対比として妥当か',
                 '補充収縮は描いていない（純粋な休みとして見せる）']),
    2: dict(src=[SRC['sab']],
            basis=['2度II型の洞房ブロック：P波がときどき抜け、抜けをはさむ休みは直前のP-Pのちょうど倍数'],
            ask=['II型（休み 1.60秒＝0.80秒の2倍）を代表にした。I型（P-Pがだんだん短くなる）は描いていない']),
    3: dict(src=[SRC['av1']], basis=['PR interval > 200ms。単独なら良性で治療は不要'],
            ask=[f'PR 約{m._pr_ms(m.PR_LONG):.0f}ms（ふつうの拍は約{m._pr_ms(m.PR):.0f}ms）で描いた']),
    4: dict(src=[SRC['wk']],
            basis=['PRが少しずつ伸びて、伝わらないP波。抜ける直前のPRが最長、直後が最短',
                   'R-Rは周期の中でだんだん短くなる。多くは良性で、3度に進むことは少ない'],
            ask=[f'4:3（PR 約{m._pr_ms(.18):.0f} → {m._pr_ms(.28):.0f} → {m._pr_ms(.33):.0f}ms、R-R 0.90 → 0.85 → 1.45秒）']),
    5: dict(src=[SRC['m2']],
            basis=['PRは一定のまま、ときどきP波が伝わらない。抜けをはさむR-Rは直前のちょうど倍数',
                   '約75%でQRSが広い（ヒス束より下）。モビッツIより血行動態の悪化・完全房室ブロックへの進行が多い'],
            ask=['【要確認】QRSを細く描いている（約25%のヒス束内ブロックの形）。代表として広いQRSにすべきか',
                 'ひとこと／声「危険です」でよいか']),
    6: dict(src=[SRC['fix']], basis=['2:1は、モビッツIでもモビッツIIでも起こる。1枚の心電図では決められないことがある',
                                     '伝わらないP波がT波の終わりに重なる'],
            ask=['伝わらないP波を直前のRから0.62秒（T波のあと）に置いた。ひとこと「型は決められない」でよいか']),
    7: dict(src=[SRC['fix'], SRC['chb']], basis=['高度房室ブロック：P:QRS が 3:1 以上。ときどきは伝わる（完全房室ブロックとの違い）'],
            ask=['3:1（心房90/分、心室30/分）で描いた']),
    8: dict(src=[SRC['chb']], basis=['完全な房室解離。心房と心室が別々のリズム。補充調律で保たれる',
                                     '心室停止・突然死のリスクが高い'],
            ask=['心房 約84/分、心室 約47/分（接合部・細いQRS）。比が整数にならないようにして、PRが毎回ちがうように見せた']),
    9: dict(src=[SRC['jer']], basis=['接合部補充調律：40〜60/分、QRS < 120ms、先行する心房活動と関係がない'],
            ask=['48/分・P波なしで描いた（逆行性P波は描いていない）']),
    10: dict(src=[SRC['ver']], basis=['心室補充調律：20〜40/分、QRS ≥ 120ms（左脚・右脚ブロック型）'],
             ask=[f'30/分・QRS 約{m._qrs_ms(m.qrs_escape):.0f}ms（II誘導の想定）で描いた']),
    11: dict(src=[SRC['af']], basis=["心拍数60/分未満の心房細動を 'slow' AF と呼ぶ。原因に低体温・ジゴキシン中毒・薬",
                                     'Irregularly irregular・P波なし・細動波（細かいもの < 0.5mm）'],
             ask=['平均50/分、R-R 0.80〜1.40秒、細動波は約0.5mm で描いた']),
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
    """パターン i の色の付いた範囲が、中部の帯の中央を少し過ぎたあたりに来る t。"""
    pat = m.PATTERNS[i]
    if pat['hl'] is m.ALL:
        c = pat['L'] / 2
    else:
        a, b = pat['hl'][-1]
        c = (a + b) / 2
    t = m.t_of(m.SEGS[i][0] + c + 0.25)
    a, b = m.WINDOWS[i]
    return min(max(t, a + 0.6), b - 0.2)


def beat_table(i):
    pat = m.PATTERNS[i]
    name = {'N': 'P＋QRS（ふつうのPR）', 'L': 'P＋QRS（PRが長い）', 'P': 'P波だけ',
            'Q': '細いQRS（P波なし）', 'W': '幅の広いQRS'}
    rows = [f"{r:4.2f}秒  {name[k]}" for r, k in pat['ev']]
    if len(rows) > 9:
        rows = rows[:8] + [f'…ほか {len(rows)-8}個']
    rows.append(f"周期 {pat['L']:.2f}秒 × {pat['rep']}回")
    return rows


def qrs_width(f):
    tt = np.arange(-0.2, 0.2, 0.0005)
    v = f(tt); mk = (np.abs(v) > 0.05) & (tt < 0.11)
    return (tt[mk].max() - tt[mk].min()) * 1000


def main():
    os.makedirs(OUT, exist_ok=True)
    pages = []
    foot = f'第18弾 徐脈 まず覚えたい12パターン（{m.DUR:.1f}秒）・数値はこの波形での一例・参考 LITFL ECG Library'

    # 1ページめ：全体と、とくに見てほしい点
    hook_t = m.HOOK_T0 + 3*m.HOOK_STEP + 0.2
    pages.append(page(m.frame(hook_t), '全体（冒頭3秒のフック）', [
        ('構成', [f'0〜{m.T_GO:.1f}秒：波形を止めて、②→⑤→⑦→⑨→⑪ に素早く変形（フック）',
                  f'{m.T_TITLE:.1f}〜{m.T_END:.1f}秒：12パターンを1つずつ紹介。紹介が終わると、その波形が縮んで上下の枠へ移り、ミニ波形として流れ続ける',
                  f'{m.T_END + m.FLY:.1f}秒〜：14個の一覧と「保存して見返してね」。最後は冒頭の画面に戻り、ループでつながる',
                  '実際の速さ（25mm/秒）・ふつうの拍は75/分・II誘導を想定']),
        ('とくに見てほしい点', ['⑥ モビッツII型のQRSを細く描いてよいか（7ページめ）',
                                 '② 洞停止と ③ 洞房ブロックの対比（休みが倍数か）',
                                 '⑦ 2:1 の伝わらないP波の位置、⑨ 完全房室ブロックの心房・心室の速さ',
                                 '見出し「まず覚えたい12パターン」の選び方。徐脈頻脈症候群、I型の洞房ブロックは入れていない']),
        ('QRS幅（モデルの波形から計算）', [f'ふつう {qrs_width(m.qrs_normal):.0f}ms', f'心室補充調律 {qrs_width(m.qrs_escape):.0f}ms']),
    ], foot))

    for i, pat in enumerate(m.PATTERNS):
        t = ectopic_time(i)
        n = NOTES[i]
        pages.append(page(m.frame(t), f"{pat['no']} {pat['name']}（{t:.1f}秒のコマ）", [
            ('画面の文字', [f"名前：{pat['no']} {pat['name']}", f"ひとこと：{pat['one']}", f"紹介前のヒント：{pat['hint']}"]),
            ('波形（1周期の出来事）', beat_table(i)),
            ('根拠（LITFLほか）', n['basis']),
            ('見てほしい点', n['ask'] or ['とくになし']),
            ('出典', n['src']),
        ], foot))

    pages.append(page(m.frame(m.T_END + m.FLY + 2.5), '最後：12個の一覧', [
        ('画面の文字', ['遅いと思ったら、この12パターン', '保存して見返してね']),
        ('見てほしい点', ['ミニ波形では、見どころ（休み・伝わらないP波・PR）だけ線を太く、色を付けている',
                          'スマホの大きさで、⑥⑦⑧の伝わらないP波が読み取れるか']),
    ], foot))

    pdf = os.path.join(OUT, 'review_reel18.pdf')
    pages[0].save(pdf, save_all=True, append_images=pages[1:], resolution=150)
    print(pdf, len(pages), 'ページ')

    # 画面文言の書き出し
    lines = ['第18弾 徐脈 まず覚えたい12パターン ― 画面の文字', '',
             '[見出し] 徐脈、まず覚えたい12パターン（「12」は黄色・2倍）',
             f'[冒頭 0〜{m.T_GO:.1f}秒] 心電図で気づく ／ 徐脈',
             '[冒頭の変形で出る名前] ' + ' → '.join(f"{m.PATTERNS[i]['no']} {m.PATTERNS[i]['name']}" for i in m.HOOK), '']
    for i, pat in enumerate(m.PATTERNS):
        a, b = m.WINDOWS[i]
        lines.append(f"[{a:5.1f}〜{b:5.1f}秒] {pat['no']} {pat['name']} ／ {pat['one']} ／ ヒント：{pat['hint']}")
    lines += ['', f"[{m.T_END + m.FLY:.1f}秒〜] 遅いと思ったら、この12パターン ／ 保存して見返してね",
              '[左下] 実際の速さ（ふつうの拍は75/分） ／ ※数値はこの波形での一例',
              '[右下] @nurse_polarbearden（透かし）']
    txt = os.path.join(OUT, 'screen_text_reel18.txt')
    with open(txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(txt)


if __name__ == '__main__':
    main()
