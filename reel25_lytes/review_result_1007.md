# 第25弾「高カリウム血症とQT（電解質）まず覚えたい11パターン」AI専門医レビュー（Claude・2026-10-07）

- レビュアー：循環器内科専門医の立場（作った担当とは別のエージェント）。ファイルは読むだけで、直していない
- 見たもの：`review_request.md`、`narration.md`、`caption.txt`、`out/screen_text_reel25.txt`、
  等倍コマ `out/review_frames/01.png`〜`14.png`（全14枚）、サムネイル `out/thumb_reel25_list.png`。
  波形の細かいところは 05（③）・07（⑤）・09（⑦）・10（⑧）・12（⑩）の中部の帯を2倍に拡大して確かめた
- 根拠：LITFL ECG Library の本文を curl で取得して確かめた（Hyperkalaemia／Hypokalaemia／Hypocalcaemia／Hypercalcaemia／Hypomagnesaemia／QT Interval／U Wave／T wave）。LITFL 以外を使ったところは出典名を書いた

---

## 全体の結論

**要修正（医学的な誤り）：なし。** 波形の描き方・名前・台本の文は、LITFL の記載とよく合っている。
とくに ⑨低Ca の QTc 510ms は LITFL（Hypocalcaemia Example 3・QT Interval）の例と同じ値、④「P波なしの遅い補充調律＋QRS軽度拡大＋テントT」は LITFL Hyperkalaemia Example 4（Slow junctional rhythm / Intraventricular conduction delay / Peaked T waves）と同じ組み合わせで、よくできている。

**推奨（より良くなるもの）**を、大事な順に挙げる。

| 優先 | どこ | 内容 |
|---|---|---|
| 高 | ⑨⑩・キャプション | QTc 510／520ms を出しているのに、色の文字に「報告」がない。キャプションの「QTc 500ms 超はトルサードの危険」とつり合わない |
| 高 | ⑧ | 画面の「U波がTより大きい」が、波形で確かめられない（T波 0.04mV でほぼ見えず、1つの山にしか見えない）。⑩とまぎれやすい |
| 高 | ⑥ | 色の文字「→ 心停止に備える」は「待って準備する」と読める。サイン波はすでに脈がない（PEA）こともある。「脈を確認・応援を呼ぶ」が先 |
| 中 | ゴースト | ④⑤⑦⑧ で、うすい線のP波・T波を「患者さんの波」と見まちがえるおそれ。「うすい線＝①基準」を帯の下に出し続ける |
| 中 | キャプション | 「（進む順）」→「（よくある順。この順とはかぎらない）」、「すぐ報告」の範囲を画面とそろえる、薬の一覧に「カリウム製剤」 |
| 低 | ゲージ・終わりの文字・サムネイル | 「軽い／重い」→「はじめ／進む」、終わりの文字に「波形が」を入れる、サムネイル⑩のヒント |

ナレーション台本は、**変えなくてよい**（14文すべて医学的にOK）。

---

## 「とくに見てほしい点」ごと

### 1. 11パターンの選び方と並び（高Kの進み方の順）
- **判定：OK（キャプションに推奨1つ）**
- 理由：
  - LITFL Hyperkalaemia「An easy way to remember the **usual order** of ECG changes seen is by following the ECG trace logically – effects begin on the T wave and move forwards to the P wave / PR interval, and subsequently to the QRS complex」と合っている。サイン波は「With worsening hyperkalaemia… Development of sine wave appearance (pre-terminal rhythm)」で最後に置いてよい
  - 同ページの「Serum potassium level may not correlate closely with ECG changes. Patients with a relatively normal ECG can suffer sudden hyperkalaemia cardiac arrest.」をキャプションとまとめの文で補っており、誤解の芽はつぶせている
  - ジギタリス効果を外したのは妥当（主題がぼやけない）。低Mgをキャプションだけにしたのも妥当（LITFL Hypomagnesaemia：単独の低Mgの心電図は「exact changes difficult to ascertain」と書かれており、1パターンとして描く根拠が弱い）
  - ただしキャプションの見出し「⚠️高カリウム（**進む順**）」は「必ずこの順に進む」と読める
- 直し方（キャプション）：
  - 「⚠️高カリウム（進む順）→ …」→「⚠️高カリウム（よくある進み方。この順とはかぎりません）→ …」

### 2. ⑥サイン波の描き方・台本・色の文字
- **判定：波形と台本はOK／色の文字は推奨（優先度・高）**
- 理由：
  - 波形（08.png）：P波なし、QRSとTが区別できない1つのなめらかな波のくり返し。LITFL「sine wave appearance」に合う。拍の間隔 0.9秒（67/分）、上 0.62mV・下 0.50mV。LITFL にサイン波の心拍数の決まった値は書かれておらず、**典型的な心拍数を私は根拠をもって示せない**。ただ、67/分は不自然ではなく、VF（速く不規則）や心室粗動（250〜300/分前後のサイン波様）とまぎれない遅さなので、模式図としてはむしろ良い
  - 台本「サイン波。いつ心停止しても、おかしくない。」：LITFL「pre-terminal rhythm」に合う。前の版の「このあと」より良い
  - 色の文字「→ 心停止に備える」：誤りではないが、看護師は「まだ脈があるので準備しておく」と受け取りやすい。LITFL は悪化の先に「PEA with bizarre, wide complex rhythm」「Asystole」を並べており、モニターでサイン波に見える時点で**すでに脈が触れない（PEA）こともある**。最初にすることは「患者さんのところへ行き、反応と脈を確かめ、応援（医師・急変対応）を呼ぶ」
- 直し方：
  - 色の文字「→ 心停止に備える」→「**→ 脈を確認・応援を呼ぶ**」（赤のまま）
  - 台本はそのまま（「すぐ報告」に当たる言葉は声で言わない約束も守れる）

### 3. ④「P波消失・徐脈」を1つにまとめたこと
- **判定：OK**
- 理由：06.png。43/分、P波なし、QRS 約113ms（軽く広い）、テントT。LITFL Hyperkalaemia の「Bradyarrhythmias: … high-grade AV block with slow junctional and ventricular escape rhythms」、Example 4「Slow junctional rhythm. Intraventricular conduction delay. Peaked T waves.」と一致する。高Kの徐脈の代表の形として妥当
  - 補足：高Kの徐脈は「P波が消えたあと」だけでなく、洞徐脈・房室ブロック・遅いAFとしてどの段階でも出る（LITFL）。キャプションの「新しい徐脈・房室ブロックは、高カリウムを疑います」でここは補えているので、画面はこのままでよい
- 直し方：なし

### 4. ⑤QRS幅の拡大（約240ms、Tとつながる、P波なし）
- **判定：OK**
- 理由：07.png（拡大して確認）。R 0.62mV → 深いS → そのまま上がってとがったTにつながる形。LITFL「QRS widening with bizarre QRS morphology」、Example 1「Broad, bizarre QRS complexes — these merge with both the preceding P wave and subsequent T wave」に合う。240ms はかなり広いが、K 9 台の例（Example 1）では珍しくなく、スマホで「広い」とひと目で分かる利点が大きい。P波を描かないのも、④でP波が消えたあとという並びとして筋が通る（LITFL Example 5「Broad complex rhythm … Absent P waves」）
- 直し方：なし

### 5. ⑦⑧低K：II誘導のU波、U/T比、ST低下、「すぐ報告」
- **判定：⑦はOK／⑧は推奨（優先度・高）**
- 理由：
  - ⑦（09.png・拡大で確認）：T波が低い山、そのうしろに別の小さな山（U波 0.11mV＝1.1mm、U/T 0.8）。LITFL U Wave「prominent if they are >1-2mm or 25% of the height of the T wave」を満たす。II誘導でU波を描くことについて、LITFL は「best seen in the precordial leads V2-V3」だが、Hypokalaemia Example 2 では「ST depression and T wave inversion best noted in inferior leads / Prominent U waves」とあり、II誘導で見えることもある。模式図として許容
  - ⑧（10.png・拡大で確認）：QRSのあとSTが下がり（最大 0.12mV）、そのまま**1つの大きな山**に上がる。T波（0.04mV）は**画面ではほぼ見えない**。これは LITFL Hypokalaemia の「QU interval: The apparent pseudo-prolonged QT interval is actually the QU interval with an absent T wave」、QT Interval の「Hypokalaemia causes apparent QTc prolongation in the limb leads (due to T-U fusion)」そのもので、**波形としては正しい**。
    ただし画面のひとこと「U波が**Tより大きい**」は、見る人がTを見つけられないので確かめようがなく、⑩（T波が遅く広い）とまちがえやすい（ミニ波形どうしだと⑧と⑩はかなり似ている）
  - ⑧のPR 202ms・P波を高く（0.20mV）は LITFL「Increased P wave amplitude」「Prolongation of PR interval」に合っていて良い
  - ⑧の「→ すぐ報告」：LITFL「Potential to develop life-threatening ventricular arrhythmias, e.g. VT, VF and Torsades de Pointes」から妥当
- 直し方（⑧、どちらか）：
  - A（文字だけ直す・おすすめ）：画面のひとこと「STが下がり、U波がTより大きい」→「**STが下がり、TとU波がつながる**」。ヒント「ST低下・大きなU」はそのままでよい
  - B（波形を直す）：T波を見える大きさ（0.06〜0.08mV）か、LITFL T wave の低Kの二相性「DOWN then UP」の形にして、TとUのあいだに小さなくびれを入れる。「U波がTより大きい」はそのまま使える
  - どちらでも、キャプションの低Kの行に「U波は胸部誘導（V2〜V3）でいちばん見やすく、モニターではTとつながってQTが長く見えることも」を足すと、モニターで見えにくい点を補える（下のキャプション欄）

### 6. ⑨低Ca と ⑩薬剤などのQT延長の描き分け、QTc 510・520ms
- **判定：描き分けはOK／色の文字は推奨（優先度・高）**
- 理由：
  - ⑨（11.png）：STの平らな部分が長く、T波の形と高さは①と同じ。LITFL Hypocalcaemia「QTc prolongation primarily by prolonging the ST segment / The T wave is typically left unchanged」に合う。510ms は LITFL Example 3（QTc 510ms）と同じ
  - ⑩（12.png・拡大で確認）：QRSのすぐあとからゆっくり上がる、遅くて幅の広い低めのT。⑨の「平らなSTのあとに普通のT」とはっきり見分けられる。520ms は薬剤性QT延長として妥当
  - ただし、**どちらも QTc が 500ms を超えている**のに、色の文字は⑨「採血の値も確認」・⑩「12誘導でQTc確認」で、「報告」がない。キャプションには「QTcが500msを超えると、トルサードの危険が高まります」とあり（LITFL QT Interval「QTc > 500 is associated with an increased risk of torsades de pointes」）、看護師が「510msでも採血を見るだけでよい」と受け取るおそれがある。
    病棟での目安として、AHA/ACCF の科学的声明（Drew BJ, et al. Prevention of Torsade de Pointes in Hospital Settings. *Circulation* 2010;121:1047–1060）は、QTc 500ms 超（または基準から60ms以上の延長）を臨床的に意味のある延長として扱い、医師に知らせることをすすめている（LITFL 以外の出典）
  - 補足：低Ca単独ではトルサードは少ない（LITFL Hypocalcaemia「Torsades de pointes may occur, but is much less common than with hypokalaemia or hypomagnesaemia」）が、看護師の行動の目安は「QTc 500ms 超なら報告」でそろえるほうが安全
- 直し方（どちらか）：
  - A（おすすめ・数値はそのまま）：⑨「→ 採血の値も確認」→「**→ 報告・採血も確認**」、⑩「→ 12誘導でQTc確認」→「**→ 12誘導で確認・報告**」
  - B（色の文字をそのままにする）：⑨のQTを 480ms 前後に縮め（「STが長い。QTc 480ms」）、500ms を超えるのは⑩だけにする。⑩は「→ 12誘導で確認・報告」にする

### 7. ⑪高Ca（QTc 280ms、STがほとんどない）
- **判定：OK**
- 理由：13.png。QRSのすぐあとにT波（0.28mV）が始まり、STがない。LITFL Hypercalcaemia「The main ECG abnormality seen with hypercalcaemia is shortening of the QT interval」、QT Interval「Hypercalcaemia leads to shortening of the ST segment」、例「Marked shortening of the QTc (260ms)」。280ms は「< 350ms は異常に短い」の範囲で妥当。T波を高くしていないので、先天性QT短縮症候群（LITFL：「very short QTc with tall, peaked T waves」）とも描き分けられている
- 直し方：なし

### 8. 色の文字の割りふり（②〜⑤⑧「すぐ報告」、⑥「心停止に備える」、⑦⑨⑪「採血の値も確認」、⑩「12誘導でQTc確認」）
- **判定：②〜⑤⑦⑧⑪はOK／⑥⑨⑩は推奨（上の2・6）**
- 理由：
  - ②テント状T波だけで「すぐ報告」：**妥当**。LITFL「The earliest manifestation of hyperkalaemia is an increase in T wave amplitude」「Patients with a relatively normal ECG can suffer sudden hyperkalaemia cardiac arrest」。また、高く見えるT波は STEMI の超急性期T波（LITFL T wave：「Broad, asymmetrically peaked or 'hyperacute' T-waves … early stages of ST-elevation MI」）のこともあり、どちらであっても看護師の行動は「すぐ報告」で正しい。ただし「もとから高いT波の人」もいるので、キャプションで「**新しく**出たら」と補うとよい
  - ⑦「採血の値も確認」：LITFL Hypokalaemia の Handy tips「Check both potassium and magnesium levels in any patient with an arrhythmia」。画面はこのままでよく、キャプションでMgにふれているので十分
- 直し方：⑥は2、⑨⑩は6のとおり

### 9. 台本を1文に詰めたことで欠けて誤解を招く文はないか
- **判定：OK（台本は変えなくてよい）**
- 理由：
  - ⑥「サイン波。いつ心停止しても、おかしくない。」：LITFL「pre-terminal rhythm」に合う。色の文字を「脈を確認・応援を呼ぶ」にすれば、行動は画面で伝わる
  - まとめ「高カリウムは、波形が軽く見えても、急変することがある。」：LITFL「Patients with a relatively normal ECG can suffer sudden hyperkalaemia cardiac arrest」に合う。声には「波形が」が入っているので誤解はない
  - ⑩「薬でも、T波が幅広くなり、QTが延びる。」：耳で聞いて⑨（STが延びる）と区別できる。OK
  - ②「まず」、④「さらに」は順番を言い切る言葉だが、LITFL の usual order どおりで、キャプションで「この順とはかぎらない」を補えば足りる
- 直し方：なし（ただし終わりの画面の文字は下の「最後の一覧」を参照）

### 10. スマホで③の平たいP波、⑦のU波が読み取れるか
- **判定：OK（推奨1つ）**
- 理由：③（05.png）の平たいP（0.065mV）は高さだけなら小さいが、黄色で色分けされ、うすい線の①のP（高く、うしろの位置）と並ぶので「低く、早く始まる＝PRが長い」が分かる。⑦（09.png）のU波（1.1mm）も青で色分けされ、T波と別の山として見える。スマホの幅（1080→約390pt）だと高さは数pt だが、色で拾える
- 直し方（推奨）：⑦⑧の紹介中だけ、波の上に小さく「T」「U」の文字を出すと、どちらがU波かを迷わない（⑧は特に。上の5を参照）

### 11. 基準のゴースト（R頂点でそろえて重ねる）
- **判定：OK（推奨1つ・優先度・中）**
- 理由：R頂点でそろえたので、「Tが高い」「Pが消えた」「QRSが広い」「STが長い」「Tが早い」が1拍の中でくらべられ、教育効果が高い。④（43/分）・⑤（50/分）で基準の拍をそのパターンの拍の位置に置いたことも、心拍数は画面の数字（43/分）で伝えているので、大きな誤解はない。⑥に重ねなかったのも正しい
  - ただ、帯の下の「うすい線＝①基準」が②③のあいだだけなので、④以降は ①の枠の小さな「＝下のうすい線」しか手がかりがない。途中から見た人は、④⑤で**うすいP波を「まだP波がある」**、⑦⑧で**うすいT波を「患者さんのT波」**と読みちがえるおそれがある（06・07・09・10.png）。④「P波が見えない」と画面にうすいP波が出ているのは、とくに引っかかりやすい
- 直し方：帯の下の「うすい線＝①基準」を、⑥を除く②〜⑪のあいだ、ずっと出す（少なくとも④⑤⑦⑧）

### 12. 高Kの進み具合ゲージ（軽い → 重い、数値なし）
- **判定：OK（推奨1つ・優先度・低）**
- 理由：Kの数値を書かないのは正しい（LITFL「Serum potassium level may not correlate closely with ECG changes」）。段階が順に上がって見えることも、LITFL の usual order の範囲で、キャプションで補っている。
  ただ、②の位置に「軽い」とあると、「テント状T波＝軽症＝様子見でよい」と読む人がいるかもしれない（②の色の文字は「すぐ報告」なので打ち消されてはいる）。ゲージが示しているのは「心電図の変化の進み方」で、患者さんの危なさではない
- 直し方：ゲージの文字「軽い」→「**はじめ**」、「重い」→「**進む**」（いちばん上の「高K」はそのまま）。変えない場合でも医学的な誤りではない

---

## パターンごと

### ① 洞調律（基準）（03.png）
- **判定：OK**
- 理由：60/分、PR 177ms、QRS 80ms、QT 391ms。「QT 390ms。RRの半分より短い」は LITFL QT Interval「A useful rule of thumb is that a normal QT is less than half the preceding RR interval」どおり。60/分なので QT＝QTc（LITFL「If an ECG is fortuitously captured while the patient's heart rate is 60 bpm, the absolute QT interval should be used」）
- 直し方：なし

### ② 高K：テント状T波（04.png）
- **判定：OK**
- 理由：T波 0.76mV（7.6mm）。LITFL T wave の正常（四肢誘導 < 5mm）を超え、「Tall, narrow, symmetrically peaked」に描けている。P・QRSは①と同じで、変わったのがTだけと分かる。ほかのパターン（⑪のTは低く、STがないだけ）とまぎれない
- 直し方：なし（キャプションで「新しく出たら」を補う。下記）

### ③ 高K：PR延長・P波平坦（05.png）
- **判定：OK**
- 理由：P波 0.065mV・幅広、PR 299ms、QRS 87ms、T 0.80mV。LITFL「P wave widening/flattening, PR prolongation」に合う。テントTを残しているのも、段階が重なっていく様子として正しい
- 直し方：なし

### ④ 高K：P波消失・徐脈（06.png）
- **判定：OK（ゴーストは上の11）**
- 理由：上の3のとおり
- 直し方：なし

### ⑤ 高K：QRS幅の拡大（07.png）
- **判定：OK**
- 理由：上の4のとおり。⑥サイン波との違い（⑤はQRSのあとに平らな基線が残る）も見える
- 直し方：なし

### ⑥ 高K：サイン波（08.png）
- **判定：波形・名前・台本はOK／色の文字は推奨（高）**
- 直し方：「→ 心停止に備える」→「→ 脈を確認・応援を呼ぶ」

### ⑦ 低K：T波平低・U波（09.png）
- **判定：OK**
- 理由：上の5のとおり。ST低下 0.04mV は軽く、「T波が低く、うしろにU波」という早い段階の描き方として妥当（LITFL「The earliest ECG manifestation of hypokalaemia is a decrease in T wave amplitude」）
- 直し方：なし（任意で「T」「U」の小さな文字）

### ⑧ 低K（高度）（10.png）
- **判定：推奨（高）**
- 直し方：画面のひとこと「STが下がり、U波がTより大きい」→「STが下がり、TとU波がつながる」（または波形にTを見せる。上の5）

### ⑨ 低Ca：ST延長（11.png）
- **判定：描き方OK／色の文字は推奨（高）**
- 直し方：「→ 採血の値も確認」→「→ 報告・採血も確認」（またはQTcを480msに。上の6）

### ⑩ QT延長（薬剤など）（12.png）
- **判定：描き方OK／色の文字は推奨（高）**
- 直し方：「→ 12誘導でQTc確認」→「→ 12誘導で確認・報告」

### ⑪ 高Ca：QT短縮（13.png）
- **判定：OK**
- 理由：上の7のとおり
- 直し方：なし

### 冒頭（01・02.png）
- **判定：OK**
- 理由：問いかけとタイトルだけで、医学的な内容の誤りはない。02.png の変形中に「⑧ 低K（高度）」の名前が出ているが、フックの途中なので問題ない

### 最後の一覧（14.png）
- **判定：推奨（低）**
- 理由：画面の文字「高カリウムは、軽く見えても急変しうる」は、「症状が軽く見えても」とも読める（それも正しいが、この回は心電図の話）。声は「波形が軽く見えても」
- 直し方：「高カリウムは、軽く見えても急変しうる」→「**高カリウムは、波形が軽く見えても急変しうる**」

### サムネイル（thumb_reel25_list.png）
- **判定：推奨（低）**
- 理由：⑩のヒント「Tが遅い」は「Tの始まりが遅い＝STが長い（⑨）」とも読める。前回の台本の直し（「T波が遅れて」→「幅広くなり」）と同じ理由
- 直し方：⑩のヒント「Tが遅い」→「**Tが遅く広い**」（入らなければ「Tが広い」）

---

## キャプション

- **判定：医学的な誤りなし（推奨あり）**
- 理由と直し方：
  1. 「⚠️高カリウム（進む順）」→ 上の1のとおり「（よくある進み方。この順とはかぎりません）」
  2. 「どの段階でも、突然VF・心停止になることがあります → すぐ報告」：LITFL は「relatively normal ECG」でも心停止しうると言っている。「どの段階でも」に「心電図がほぼ正常でも」を含めると、より正確
  3. 「すぐ報告」の範囲：画面では ②〜⑤ と ⑧ が「すぐ報告」なのに、キャプションでは高Kの行にしかない。重い低K（⑧）とQTc 500ms 超（⑨⑩の推奨）にも「報告」を入れて、画面とそろえる
  4. 高Kの疑い方の薬：LITFL の Handy Tips は「ACE inhibitors, potassium-sparing diuretics and potassium supplements」。**カリウム製剤**が抜けている。日本の病棟では ARB も多い（LITFL 以外：ARB 各薬の添付文書で「高カリウム血症」は重大な副作用。必要なら各薬の添付文書で確かめてから入れる）
  5. 低Mg：LITFL Hypomagnesaemia「Patients with hypomagnesaemia often have concurrent hypokalaemia and/or hypocalcaemia」。「低カリウムと一緒に」は正しい。U波は LITFL U Wave の「Prominent U waves may be present with: … Hypomagnesaemia」で支えられる。このままでよい
  6. 「📏QTが短い → 高カルシウム」：LITFL QT Interval の短いQTの原因は「Hypercalcaemia / Congenital short QT syndrome / Digoxin effect」。この回の主題なので「高カルシウムなど」とするとよい（必須ではない）
  7. 低KのU波：モニターで見えにくい点（LITFL「best seen in the precordial leads V2-V3」、QT Interval「apparent QTc prolongation in the limb leads (due to T-U fusion)」）を一言そえる
  8. テント状T波：「新しく」出たら、を入れる（もともとT波が高い人がいるため）

- 直し方（直した全文の案。定型3行・ハッシュタグは今のまま）：

```
この波形の変化、いくつ気づける？
@nurse_polarbearden📍他の投稿をチェック
---------------------------------------------------------
▶︎こんにちは、看護師でんです。

高カリウム血症とQT、まず覚えたい11パターンをまとめました。
うすい線（①の基準）と重ねて、どこが変わったかを見てね。

⚠️高カリウム（よくある進み方。この順とはかぎりません）→ テント状T波 → PR延長・P波平坦 → P波消失・徐脈 → QRS幅の拡大 → サイン波
　どの段階でも、心電図がほぼ正常に見えても、突然VF・心停止になることがあります → 新しく出たら、すぐ報告
🧪低カリウム → T波が低い・U波・ST低下（重くなると、VT・VF・トルサードの危険 → すぐ報告）
　U波は胸部誘導（V2〜V3）でいちばん見やすく、モニターではTとつながってQTが長く見えることも
🧪低マグネシウム → 低カリウムと一緒に起きやすく、波形も似ています（QT延長・目立つU波）
📏QTが延びる → 低カルシウム（STが長い）・低カリウム・低マグネシウム・薬剤など
📏QTが短い → 高カルシウムなど

※心電図の変化とカリウム値は、きれいには一致しません。波形が変わったら、採血の値もセットで確認
※腎不全・透析中・ACE阻害薬やカリウム保持性利尿薬・カリウム製剤を使っている人の、新しい徐脈・房室ブロックは、高カリウムを疑います
※QTcが500msを超えたら報告。トルサードの危険が高まります（12誘導で確認）

何個わかったか、コメントで教えてね。
保存して、見返してね。

※数値はこの波形での一例です（II誘導）
※参考：LITFL ECG Library（Hyperkalaemia / Hypokalaemia / Hypercalcaemia / Hypocalcaemia / Hypomagnesaemia / QT Interval / U Wave）
（ここに caption_template.txt の3行）

#看護師 #看護学生 #心電図 #高カリウム血症 #電解質 #QT延長 #モニター心電図 #急変 #不整脈
```

（ARB を入れる場合は「ACE阻害薬・ARB・カリウム保持性利尿薬・カリウム製剤」。LITFL にはないので、入れるなら参考の行に出典を足すか、添付文書で確かめてから）

---

## 看護師の現場の安全の点

1. ⑥の色の文字（「心停止に備える」→「脈を確認・応援を呼ぶ」）：サイン波を見たら、まず患者さんのもとへ。脈がなければそのまま心肺蘇生（LITFL：「PEA with bizarre, wide complex rhythm」、「In any patient who has suffered a bradycardia PEA arrest, suspect and treat for hyperkalaemia」）
2. QTc 500ms 超の行動（⑨⑩）を「報告」でそろえる
3. うすい線を患者さんの波と見まちがえないように、帯の下の「うすい線＝①基準」を出し続ける
4. 「軽い」の文字（ゲージ・終わりの画面）が「様子見でよい」と読まれないようにする
5. 画面の数値は「この波形での一例」、QTは 12誘導で確かめる、Kの値と心電図は一致しない — これらはすでに画面とキャプションに入っていて良い

## ナレーション台本

**変更なし**（いまの14文のまま録音してよい）。

---

## 根拠（取得して本文を確かめたページ）
- LITFL Hyperkalaemia：https://litfl.com/hyperkalaemia-ecg-library/
- LITFL Hypokalaemia：https://litfl.com/hypokalaemia-ecg-library/
- LITFL Hypocalcaemia：https://litfl.com/hypocalcaemia-ecg-library/
- LITFL Hypercalcaemia：https://litfl.com/hypercalcaemia-ecg-library/
- LITFL Hypomagnesaemia：https://litfl.com/hypomagnesaemia-ecg-library/
- LITFL QT Interval：https://litfl.com/qt-interval-ecg-library/
- LITFL U Wave：https://litfl.com/u-wave-ecg-library/
- LITFL T wave：https://litfl.com/t-wave-ecg-library/
- LITFL 以外：Drew BJ, et al. Prevention of Torsade de Pointes in Hospital Settings: A Scientific Statement from the AHA and ACCF. *Circulation* 2010;121:1047–1060（QTc 500ms 超を報告の目安とすること）。ARB の高カリウム血症は各薬の添付文書（入れる場合は確かめてから）
- 分からなかったこと：サイン波の「典型的な心拍数」は LITFL に書かれておらず、根拠をもって示せない
