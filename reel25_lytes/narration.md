# 第25弾 高カリウム血症とQT（電解質） まず覚えたい11パターン — ナレーション

第21弾（ぎゅっと版）と同じ作り。1パターン1文（声で3〜4秒）。数字は画面に出ているので、声では読み上げない。
「すぐ報告」は声では言わない（画面の色の文字とキャプションで伝える）。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第21弾と同じ）。

## 秒数つき（録音 2026-10-07 ElevenLabs Ren – Smooth & Soothing・eleven_v4 を置いた位置）

元の録音（54.6秒）を、声の高さが変わらない atempo=1.2 で1.2倍速にした（45.5秒・無音0.25秒以上で19かたまり）。
`align_vo.py` で文に切り分け、下の秒数に置いた。継ぎ目はすべて無音の中。文の中の息継ぎは 0.45秒まで詰めた。
（2026-10-10 直した：前は `cut()` が無音のまん中から 0.45秒を切り取っていて、0.45秒より少し長い間がほぼ0になり、①「まずは基準。」のすぐあとに「この形と」が始まっていた（⑥「サイン波。」・冒頭も同じ）。いまは間を 0.45秒残す。冒頭の文が 4.01→4.36秒になったので、T_TITLE を 4.0→4.4 にした）
faster-whisper（medium）の書き起こしで、かたまりと文の対応（冒頭[1,2] ①[3,4] ②[5] ③[6,7,8] ④[9] ⑤[10] ⑥[11,12] ⑦〜⑪[13〜17] まとめ[18] 保存[19]）を確かめた。
映像は 70.1秒（2026-10-14 病態が変わるつなぎ目を灰色のつなぎで通す形にし、まとめを録り直したため。前は 67.9秒）。
まとめの文は 2026-10-14 に録り直した（`out/vo/fix_1014_x1.2.mp3`。同じ声・1.2倍速で声の高さはそのまま・1文 3.8秒）。`align_vo.py` の `--fix`（FIX_LINES）で、通し読みのまとめと差し替える：
`python3 align_vo.py out/vo/narration_raw.wav --fix out/vo/fix_1014_x1.2.mp3 --mux`（高画質版は `--hq` も）

| 秒 | 文 |
|---|---|
| 0.10–4.46 | 高カリウム血症とQT。まず覚えたいのは、この11パターン。 |
| 4.70–7.27 | まずは基準。この形とくらべていく。 |
| 9.47–12.24 | 高カリウムは、まずT波が高くとがる。 |
| 14.44–17.49 | 進むと、P波が平たく、PRが延びる。 |
| 19.69–22.14 | さらにP波が消えて、脈が遅くなる。 |
| 24.34–26.88 | QRSの幅が広がり、Tとつながる。 |
| 29.08–31.97 | サイン波。いつ心停止しても、おかしくない。 |
| 35.17–38.10 | 低カリウムでは、T波が低くなり、U波が出る。 |
| 40.30–43.25 | 重くなると、STが下がり、U波が目立つ。 |
| 46.15–49.55 | 低カルシウムは、STが長くなって、QTが延びる。 |
| 52.45–55.46 | 薬でも、T波が幅広くなり、QTが延びる。 |
| 58.36–60.71 | 高カルシウムでは、QTが短くなる。 |
| 63.01–66.76 | 高カリウムは、どの段階でも、急に心停止することがある。 |
| 67.06–68.46 | 保存して、見返してね |

- ①から最後まで、帯を消さずに、画面に見えている波形がその場で形を変える（2026-10-10）：
  形は動画の時刻だけで決まり、名前・声のあいだはそのパターンの形のまま。名前が消えると形が変わり、画面の拍がすべて同時に変わる
  （P波の高さ・幅・PR、QRSの幅と形、ST、T波、U波、拍の間隔。⑤→⑥はサイン波へ溶ける）。
  - 同じ病態の中（①→②→③→④→⑤→⑥ の高K、⑦→⑧ の低K）だけ：次の形へ直接（1.0秒）
  - それ以外（⑥→⑦、⑧→⑨、⑨→⑩、⑩→⑪、⑪→最後）：どのパターンでもない「つなぎ」の洞調律 75/分を、うすい灰色で描いて通る
    （0.6秒でつなぎへ・0.5秒そのまま・0.6秒で次の形へ）。そのあいだ名前の位置に小さく「▶ 次の例」。帯は消えず、コピーは枠へ飛ぶ。
    ⑥→⑦だけは、サイン波を形を変えずにうすくしてから灰色のつなぎを重ねて出す（0.9秒のクロスフェード）・「▶ 次の例（別の病態）」。
    ⑪→最後は「次の例」なしで、つなぎを通って①基準（60/分）へもどす（動画の終わりが冒頭とつながる。拍の位相のずれ 5ms）
    （2026-10-14 第24〜26弾の共通ルール。前は①基準（緑・60/分）を通っていた）
  拍の位置は中央を通った拍の数（位相）を積み上げて決めるので、間隔が変わるときも拍が跳んだり増えたりしない。
  名前が消えると、そのパターンだけのコピーが縮んで枠へ飛ぶ（帯はそのまま流れる）。まとめの声は、基準へもどり終わってから

---

## 読み上げ用（ElevenLabs に貼る）

高カリウム血症とQT。まず覚えたいのは、この11パターン。

まずは基準。この形とくらべていく。
高カリウムは、まずT波が高くとがる。
進むと、P波が平たく、PRが延びる。
さらにP波が消えて、脈が遅くなる。
QRSの幅が広がり、Tとつながる。
サイン波。いつ心停止しても、おかしくない。

低カリウムでは、T波が低くなり、U波が出る。
重くなると、STが下がり、U波が目立つ。
低カルシウムは、STが長くなって、QTが延びる。
薬でも、T波が幅広くなり、QTが延びる。
高カルシウムでは、QTが短くなる。

高カリウムは、どの段階でも、急に心停止することがある。
保存して、見返してね

---

## 並び（画面の色）

- 上の6つ＝高カリウムの進み方（基準 → 黄 → 橙 → 赤）：
  ①洞調律（基準）→ ②テント状T波 → ③PR延長・P波平坦 → ④P波消失・徐脈 → ⑤QRS幅の拡大 → ⑥サイン波
- 下の5つ＝QTのまわり（左の列 ⑦⑧、右の列 ⑨⑩、3段目のまん中 ⑪）：
  青 ⑦低K（T波平低・U波）・⑧低K（高度）／紫 ⑨低Ca（STが長い）・⑩QT延長（薬剤など）／ピンク ⑪高Ca（QT短縮）
- ジギタリス効果は外した（電解質でもQTでもなく、薬の効果なので浮く。2026-10-06）
- 低マグネシウム血症はキャプションでふれる（低Kと一緒に起きやすい。QTが延び、トルサードの危険。2026-10-14「波形も似る」は言いすぎなので外した）
- R on T・トルサードは第21弾にあるので、ここでは「QT延長」まで（キャプションで「QTc 500ms 超はトルサードの危険」とだけふれる）

## この回だけの見せ方

- **波の名前（2026-10-10 追加）**：①の紹介中、中部の帯の拍に P・Q・R・S・T を色分けで（P 黄・Q 水色・R 白・S 黄緑・T 橙、太字34px・暗いふちどり）。
  拍にくっつけて流す（R頂点が画面の x 210〜870 にあるあいだ）。⑦⑧では U波の上に「U」（ピンク）

- **基準のゴースト**：②〜⑪ の紹介中（⑥サイン波は除く。とがったQRSがサイン波を突き抜けて誤解を招くため）、中部の帯に①基準の拍を、そのパターンの拍と同じR頂点の位置に、白っぽくうすく重ねる。
  どこが変わったか（Tが高い、Pが消える、QRSが広い、STが長い、Tが早い など）がひと目で分かる。①の枠の名前のうしろに「＝下のうすい線」、②③のあいだは帯の下に「うすい線＝①基準」
- **高Kの心電図変化のゲージ**：②〜⑥ のあいだ、左の余白に縦のゲージ（下「はじめ」→ 上「進む」、いちばん上に見出し「高Kの／心電図／変化」）。段階が進むごとに 1/5 ずつ上がり、⑥でいちばん上・赤。
  ゲージの下に「順番どおりとはかぎらない／どの段階でも急変あり」（2026-10-14）。
  **Kの数値は書かない**（段階とK値は一致しないため。LITFL「Serum potassium level may not correlate closely with ECG changes」）
- **冒頭の問いかけ**「この変化、気づける？」（0秒から、タイトルの上）
- **最後**：「保存して見返してね」の下に「何個わかった？コメントで教えてね」（声では言わない）。キャプションの1行目も問いかけ

## 画面のひとことのうしろの色の文字（声では言わない）

| 色の文字 | パターン | 意味 |
|---|---|---|
| 緑「→ くらべる基準」 | ① | 比べるための基準 |
| 黄「→ すぐ報告」 | ②〜⑤・⑧ | 高Kのサイン、重い低K（VT・VF・トルサードの危険） |
| 赤「→ 心停止に備える」 | ⑥ | 心停止の直前（pre-terminal） |
| 青「→ 採血の値も確認」 | ⑦ | 電解質の値（K）を確かめる |
| 青「→ 報告・採血も確認」 | ⑨⑪ | QTc 500ms 超（⑨）・QTc 280ms と明らかに短い（⑪。2026-10-14） |
| 紫「→ 12誘導でQTc確認」 | ⑩ | モニターのII誘導だけで決めず、12誘導で測る |

## 言い回しの注意（LITFL本文で確認。LITFL以外は使っていない）

- **② テント状T波**：LITFL（Hyperkalaemia）「The earliest manifestation of hyperkalaemia is an increase in T wave amplitude」「Peaked T waves」。LITFL（T wave）「Tall, narrow, symmetrically peaked T-waves are characteristically seen in hyperkalaemia」
- **③ PR延長・P波平坦**：LITFL（Hyperkalaemia）「P wave widening/flattening, PR prolongation」
- **④ P波消失・徐脈**：LITFL（Hyperkalaemia）「Bradyarrhythmias: sinus bradycardia, high-grade AV block with slow junctional and ventricular escape rhythms, slow AF」、Example 5「Absent P waves」。
  Handy Tips「Suspect hyperkalaemia in any patient with a new bradyarrhythmia or AV block, especially patients with renal failure, on haemodialysis, or taking any combination of ACE inhibitors, potassium-sparing diuretics and potassium supplements」
- **⑤ QRS幅の拡大**：LITFL（Hyperkalaemia）「QRS widening with bizarre QRS morphology」、Example 1「Broad, bizarre QRS complexes — these merge with both the preceding P wave and subsequent T wave」
- **⑥ サイン波・「いつ心停止しても、おかしくない」**：LITFL（Hyperkalaemia）「With worsening hyperkalaemia… Development of sine wave appearance (pre-terminal rhythm)・Ventricular fibrillation・PEA with bizarre, wide complex rhythm・Asystole」
- **まとめ「どの段階でも、急に心停止することがある」**（2026-10-14 録り直し。前は「波形が軽く見えても、急変することがある」）：LITFL（Hyperkalaemia）「Serum potassium level may not correlate closely with ECG changes. Patients with a relatively normal ECG can suffer sudden hyperkalaemia cardiac arrest.」
- **進む順**：LITFL（Hyperkalaemia）「effects begin on the T wave and move forwards to the P wave / PR interval, and subsequently to the QRS complex」（「usual order」。いつもこの順とはかぎらない）
- **⑦⑧ 低カリウム**：LITFL（Hypokalaemia）「The earliest ECG manifestation of hypokalaemia is a decrease in T wave amplitude」「Widespread ST depression and T wave flattening/inversion」「Prominent U waves」「Apparent long QT interval due to fusion of T and U waves (= long QU interval)」「Potential to develop life-threatening ventricular arrhythmias, e.g. VT, VF and Torsades de Pointes」。
  LITFL（U Wave）「prominent if they are >1-2mm or 25% of the height of the T wave」。U波は V2〜V3 で最もよく見える（モニターのII誘導では見えにくいことがある）
- **⑨ 低カルシウム**：LITFL（Hypocalcaemia）「Hypocalcaemia causes QTc prolongation primarily by prolonging the ST segment」「The T wave is typically left unchanged」
- **⑩ 薬剤などのQT延長**：LITFL（QT Interval）「Causes of a prolonged QTc (>440ms) … Medications/Drugs」「QTc > 500 is associated with an increased risk of torsades de pointes」。
  低マグネシウムも原因（LITFL Hypomagnesaemia「associated with QT interval prolongation」）。キャプションでふれる
- **⑪ 高カルシウム**：LITFL（Hypercalcaemia）「The main ECG abnormality seen with hypercalcaemia is shortening of the QT interval」。LITFL（QT Interval）「QTc is abnormally short if < 350ms」
- **① 基準**：LITFL（QT Interval）「A useful rule of thumb is that a normal QT is less than half the preceding RR interval」

## 専門医レビュー（2026-10-06）で直したところ

要修正なし。推奨2点を台本に入れた（波形・画面・キャプションは変更なし）。
- ⑥「このあと突然、心停止になりうる」→「いつ心停止しても、おかしくない」：「このあと」だと時間の猶予があるように聞こえる。サイン波はすでに心停止の直前（pre-terminal）
- ⑩「T波が遅れて」→「T波が幅広くなり」：耳で聞くと「Tの始まりが遅れる＝STが延びる（⑨低Caと同じ）」と取られうる。画面の「T波が遅く広い」に合わせた
- ほか（11パターンの並び、数値なしの高Kゲージ、R頂点で重ねるゴースト、色の文字、まとめの一文）はOK

## 専門医レビュー（2026-10-07、Claude）

AI専門医（作った担当とは別のエージェント）が、依頼文・等倍フレーム・キャプションを LITFL 本文と照らして見た。全文は `review_result_1007.md`。
**要修正（医学的な誤り）はなし。台本の14文は変えない。** 推奨のうち、次を入れた。

- 入れたもの（画面）
  - ⑥の色の文字「→ 心停止に備える」→「→ 脈を確認・応援を呼ぶ」：サイン波の時点ですでに脈が触れない（PEA）こともある（LITFL「PEA with bizarre, wide complex rhythm」）。まず患者さんのもとへ。ひとことは幅に収めるため「QRSとTが溶けて波打つ」
  - ⑧のひとこと「STが下がり、U波がTより大きい」→「STが下がり、TとU波がつながる」：T波（0.04mV）は画面でほぼ見えず、確かめようがない。LITFL「T-U fusion」「QU interval … with an absent T wave」に合わせた（波形は変えない）
  - ⑨の色の文字「→ 採血の値も確認」→「→ 報告・採血も確認」、⑩「→ 12誘導でQTc確認」→「→ 12誘導で確認・報告」：QTc 510／520ms は 500ms を超える（LITFL QT Interval「QTc > 500 is associated with an increased risk of torsades de pointes」。報告の目安は Drew BJ, et al. Circulation 2010;121:1047–1060（AHA/ACCF の声明）による）
  - 帯の下の「うすい線＝①基準」を②〜⑪のあいだずっと出す（⑥は除く）：うすい線のP波・T波を患者さんの波と見まちがえないように。⑥のサイン波の谷が字の位置を通りすぎてから、また出す
  - 高Kゲージ「軽い／重い」→「はじめ／進む」：ゲージは心電図の変化の進み方で、患者さんの危なさではない（「軽い＝様子見」と読まれないように）
  - 最後の画面の文字「高カリウムは、波形が軽く見えても急変しうる」（声と同じく「波形が」を入れた）
  - サムネイル⑩のヒント「Tが遅い」→「Tが広い」（「Tが遅く広い」は幅に入らなかった）
- 入れたもの（キャプション）：レビューの全文案に差し替えた（高Kは「よくある進み方。この順とはかぎりません」、心電図がほぼ正常でも心停止がありうる、「新しく出たら」、重い低K・QTc 500ms 超の「報告」、U波は胸部誘導で見やすくモニターではTとつながりうる、カリウム製剤、「高カルシウムなど」）
- 入れていないもの
  - ARB（LITFL にないため。入れるなら各薬の添付文書で確かめてから）
  - ⑦⑧の波の上の「T」「U」の文字（任意の推奨。画面が混むため見送り）
  - ⑧の波形でT波を見える大きさにする案（B案）：ひとことを直す A案を選んだ
  - ⑨のQTcを 480ms に縮める案（B案）：色の文字に「報告」を足す A案を選んだ

## 専門医レビュー（2026-10-14、Claude）で直したところ

AI専門医（作った担当とは別のエージェント）のレビュー。全文は `review_result_1014-1023.md`。ユーザーの了承を得て、要修正と主な推奨を入れた。

- **要修正 M1（⑥→⑦）**：サイン波が⑤の形を通って0.7秒で正常にもどる絵になり、「サイン波が自然にもどる」と読まれる
  → 第24〜26弾の共通ルールで直した：同じ病態の中（高K ①〜⑥、低K ⑦→⑧）だけ直接変わり、それ以外のつなぎ目（⑥→⑦、⑧→⑨、⑨→⑩、⑩→⑪、⑪→最後）は、
  どのパターンでもない「つなぎ」の洞調律 75/分（うすい灰色）を通り、「▶ 次の例」を出す。⑥→⑦はサイン波の形を変えず、うすくしてから灰色のつなぎを重ねる（クロスフェード）・「▶ 次の例（別の病態）」
- **R1（優先度高）**：「この順に、ゆっくり、段階を踏んで進む」と読まれやすい
  - ゲージの見出しを「高K」→「高Kの／心電図／変化」（3行。左の余白の幅に入るように）。ゲージを少し下げた（上端 y 420→456）
  - ゲージの下に「順番どおりとはかぎらない／どの段階でも急変あり」（22px・うすい白、②〜⑥のあいだ）
  - まとめの声を録り直し：「高カリウムは、どの段階でも、急に心停止することがある。」。最後の画面の文字も「高カリウムは、どの段階でも急変しうる」
- **R2**：悪くなるほど速くなる（43→50→67/分）と「持ち直した」と見える → ⑤は④と同じ 43/分、⑥は 52/分（サイン波の山と谷を広げて RR 1.15秒を埋めた）
- **R3**：④⑤（P波なし）では、ゴーストのP波を描かない
- **R4**：⑦だけ、低いT波の上に小さめ（28px）の「T」（橙）
- **R6**：⑪の色の文字「→ 採血の値も確認」→「→ 報告・採血も確認」（⑨とそろえる。QTc 280ms は LITFL の「< 350ms で異常に短い」）
- **R9（キャプション）**：低Mg「波形も似ています」→「低カリウムと一緒に起きやすい。QTが延び、トルサードの危険が上がる（U波が目立つことも）」（LITFL Hypomagnesaemia で確認）。
  QTc の行に「または前より60ms以上延びたら」を足した（LITFL以外：AHA/ACCF Scientific Statement 2010、Drew BJ, et al. Circulation。※参考の下に出典を書いた）
- 映像は 67.9 → 70.1秒
- 入れていないもの：R5（⑧のひとこと）、R7（①のSの位置）、R8（⑦の台本「U波が出る」）、R10（サムネイル⑩の丸）、R11（コピーの道）、R12（左下の注記の位置）

## 声の指定

- 全体に落ち着いて、はっきり
- ⑥「いつ心停止しても、おかしくない」は、少し間をとって重く
- まとめ「高カリウムは、どの段階でも、急に心停止することがある」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
