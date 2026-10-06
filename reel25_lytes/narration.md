# 第25弾 高カリウム血症とQT（電解質） まず覚えたい11パターン — ナレーション

第21弾（ぎゅっと版）と同じ作り。1パターン1文（声で3〜4秒）。数字は画面に出ているので、声では読み上げない。
「すぐ報告」は声では言わない（画面の色の文字とキャプションで伝える）。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第21弾と同じ）。

**いまは録音前の版**。区間の長さ（`make_reel25.py` の `SEG_D`）は、台本の各文の長さの見込み（6字/秒くらい）＋0.75秒以上の仮の値。
映像は 60.8秒（仮）。台本は14文（冒頭＋11＋まとめ＋保存）。

---

## 読み上げ用（ElevenLabs に貼る）

高カリウム血症とQT。まず覚えたいのは、この11パターン。

まずは基準。この形とくらべていく。
高カリウムは、まずT波が高くとがる。
進むと、P波が平たく、PRが延びる。
さらにP波が消えて、脈が遅くなる。
QRSの幅が広がり、Tとつながる。
サイン波。このあと突然、心停止になりうる。

低カリウムでは、T波が低くなり、U波が出る。
重くなると、STが下がり、U波が目立つ。
低カルシウムは、STが長くなって、QTが延びる。
薬でも、T波が遅れて、QTが延びる。
高カルシウムでは、QTが短くなる。

高カリウムは、波形が軽く見えても、急変することがある。
保存して、見返してね

- 区間の長さ（仮・秒）：①4.0 ②4.0 ③4.0 ④4.2 ⑤4.8 ⑥4.5 ⑦5.0 ⑧4.0 ⑨5.0 ⑩4.0 ⑪4.0（冒頭 5.2、最後 7.2）
- 1パターンの声の長さの目安（区間の長さ − 0.75秒）：①2.9 ②3.2 ③3.2 ④3.4 ⑤4.0 ⑥3.7 ⑦4.2 ⑧3.2 ⑨4.2 ⑩3.2 ⑪3.2 秒
  （①は縮み始めが 0.35秒早く、冒頭の文のあとなので短め）
- 拍の間隔の倍数で切る：①〜③⑦〜⑪は 1.0秒、④は 1.4秒、⑤は 1.2秒、⑥は 0.9秒の倍数

---

## 並び（画面の色）

- 上の6つ＝高カリウムの進み方（基準 → 黄 → 橙 → 赤）：
  ①洞調律（基準）→ ②テント状T波 → ③PR延長・P波平坦 → ④P波消失・徐脈 → ⑤QRS幅の拡大 → ⑥サイン波
- 下の5つ＝QTのまわり（左の列 ⑦⑧、右の列 ⑨⑩、3段目のまん中 ⑪）：
  青 ⑦低K（T波平低・U波）・⑧低K（高度）／紫 ⑨低Ca（STが長い）・⑩QT延長（薬剤など）／ピンク ⑪高Ca（QT短縮）
- ジギタリス効果は外した（電解質でもQTでもなく、薬の効果なので浮く。2026-10-06）
- 低マグネシウム血症はキャプションでふれる（低Kと一緒に起きやすく、波形も似る）
- R on T・トルサードは第21弾にあるので、ここでは「QT延長」まで（キャプションで「QTc 500ms 超はトルサードの危険」とだけふれる）

## この回だけの見せ方

- **基準のゴースト**：②〜⑪ の紹介中（⑥サイン波は除く。とがったQRSがサイン波を突き抜けて誤解を招くため）、中部の帯に①基準の拍を、そのパターンの拍と同じR頂点の位置に、白っぽくうすく重ねる。
  どこが変わったか（Tが高い、Pが消える、QRSが広い、STが長い、Tが早い など）がひと目で分かる。①の枠の名前のうしろに「＝下のうすい線」、②③のあいだは帯の下に「うすい線＝①基準」
- **高Kの進み具合ゲージ**：②〜⑥ のあいだ、左の余白に縦のゲージ（下「軽い」→ 上「重い」、いちばん上に「高K」）。段階が進むごとに 1/5 ずつ上がり、⑥でいちばん上・赤。
  **Kの数値は書かない**（段階とK値は一致しないため。LITFL「Serum potassium level may not correlate closely with ECG changes」）
- **冒頭の問いかけ**「この変化、気づける？」（0秒から、タイトルの上）
- **最後**：「保存して見返してね」の下に「何個わかった？コメントで教えてね」（声では言わない）。キャプションの1行目も問いかけ

## 画面のひとことのうしろの色の文字（声では言わない）

| 色の文字 | パターン | 意味 |
|---|---|---|
| 緑「→ くらべる基準」 | ① | 比べるための基準 |
| 黄「→ すぐ報告」 | ②〜⑤・⑧ | 高Kのサイン、重い低K（VT・VF・トルサードの危険） |
| 赤「→ 心停止に備える」 | ⑥ | 心停止の直前（pre-terminal） |
| 青「→ 採血の値も確認」 | ⑦⑨⑪ | 電解質の値（K・Ca）を確かめる |
| 紫「→ 12誘導でQTc確認」 | ⑩ | モニターのII誘導だけで決めず、12誘導で測る |

## 言い回しの注意（LITFL本文で確認。LITFL以外は使っていない）

- **② テント状T波**：LITFL（Hyperkalaemia）「The earliest manifestation of hyperkalaemia is an increase in T wave amplitude」「Peaked T waves」。LITFL（T wave）「Tall, narrow, symmetrically peaked T-waves are characteristically seen in hyperkalaemia」
- **③ PR延長・P波平坦**：LITFL（Hyperkalaemia）「P wave widening/flattening, PR prolongation」
- **④ P波消失・徐脈**：LITFL（Hyperkalaemia）「Bradyarrhythmias: sinus bradycardia, high-grade AV block with slow junctional and ventricular escape rhythms, slow AF」、Example 5「Absent P waves」。
  Handy Tips「Suspect hyperkalaemia in any patient with a new bradyarrhythmia or AV block, especially patients with renal failure, on haemodialysis, or taking any combination of ACE inhibitors, potassium-sparing diuretics and potassium supplements」
- **⑤ QRS幅の拡大**：LITFL（Hyperkalaemia）「QRS widening with bizarre QRS morphology」、Example 1「Broad, bizarre QRS complexes — these merge with both the preceding P wave and subsequent T wave」
- **⑥ サイン波・「突然、心停止になりうる」**：LITFL（Hyperkalaemia）「With worsening hyperkalaemia… Development of sine wave appearance (pre-terminal rhythm)・Ventricular fibrillation・PEA with bizarre, wide complex rhythm・Asystole」
- **まとめ「波形が軽く見えても、急変することがある」**：LITFL（Hyperkalaemia）「Serum potassium level may not correlate closely with ECG changes. Patients with a relatively normal ECG can suffer sudden hyperkalaemia cardiac arrest.」
- **進む順**：LITFL（Hyperkalaemia）「effects begin on the T wave and move forwards to the P wave / PR interval, and subsequently to the QRS complex」（「usual order」。いつもこの順とはかぎらない）
- **⑦⑧ 低カリウム**：LITFL（Hypokalaemia）「The earliest ECG manifestation of hypokalaemia is a decrease in T wave amplitude」「Widespread ST depression and T wave flattening/inversion」「Prominent U waves」「Apparent long QT interval due to fusion of T and U waves (= long QU interval)」「Potential to develop life-threatening ventricular arrhythmias, e.g. VT, VF and Torsades de Pointes」。
  LITFL（U Wave）「prominent if they are >1-2mm or 25% of the height of the T wave」。U波は V2〜V3 で最もよく見える（モニターのII誘導では見えにくいことがある）
- **⑨ 低カルシウム**：LITFL（Hypocalcaemia）「Hypocalcaemia causes QTc prolongation primarily by prolonging the ST segment」「The T wave is typically left unchanged」
- **⑩ 薬剤などのQT延長**：LITFL（QT Interval）「Causes of a prolonged QTc (>440ms) … Medications/Drugs」「QTc > 500 is associated with an increased risk of torsades de pointes」。
  低マグネシウムも原因（LITFL Hypomagnesaemia「associated with QT interval prolongation」）。キャプションでふれる
- **⑪ 高カルシウム**：LITFL（Hypercalcaemia）「The main ECG abnormality seen with hypercalcaemia is shortening of the QT interval」。LITFL（QT Interval）「QTc is abnormally short if < 350ms」
- **① 基準**：LITFL（QT Interval）「A useful rule of thumb is that a normal QT is less than half the preceding RR interval」

## 声の指定

- 全体に落ち着いて、はっきり
- ⑥「このあと突然、心停止になりうる」は、少し間をとって重く
- まとめ「高カリウムは、波形が軽く見えても、急変することがある」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
