# 第26弾 心房細動・心房粗動 まず覚えたい12パターン — ナレーション

第21弾と同じ作り（1パターン1文・声で3〜4秒）。数字は画面に出ているので、声では読み上げない（伝導比の「4対1」などは名前なので読む。⑩の「150」は見分けの目安なので例外として読む）。
「すぐ報告」は声では言わない（画面の赤い「→ すぐ報告」とキャプションで伝える）。危ないもの（⑧⑫）は声では「危険」とだけ言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第21弾と同じ）。

---

## 読み上げ用（ElevenLabs に貼る）

心房細動と心房粗動。まず覚えたいのは、この12パターン。

P波がなく、R-Rがバラバラ。f波の粗い心房細動。
平らに見えても、f波の細かい心房細動。
速くてバラバラ、頻脈性の心房細動。
遅くてバラバラ、徐脈性の心房細動。

長い間隔のあと、早く来た拍が幅広い。アシュマン現象。
全部の拍が幅広い。脚ブロックを伴う心房細動。
f波なのに規則正しく遅い。完全房室ブロックを疑う。
幅広く速くバラバラ。WPWの心房細動は危険。

のこぎり状のF波。4対1の心房粗動。
150で規則正しければ、2対1の粗動を疑う。
伝導比が変わる心房粗動は、細動に似る。
F波が全部伝わる1対1は、とても危険。

R-Rがバラバラなら細動、のこぎりなら粗動。
保存して、見返してね

- 読み方：「150」は「ひゃくごじゅう」、「R-R」は「アールアール」、「f波」「F波」は「エフ波」、「WPW」は「ダブリューピーダブリュー」、「4対1」は「よんたいいち」、「1対1」は「いったいいち」
- 2026-10-05：録音前の版（区間の長さは仮）。録音が届いたら `align_vo.py` の `LINES`（声のかたまり番号）を Whisper の書き起こしで直す

## 区間の長さ（仮）と、声の長さの目安

各パターンの区間（秒）：①5.42 ②4.40 ③3.88 ④4.60 ⑤4.80 ⑥5.00 ⑦5.00 ⑧5.22 ⑨4.80 ⑩4.40 ⑪4.60 ⑫4.20（映像 68.0秒）。
声の長さの目安（区間の長さ − 0.75秒）：①4.3 ②3.6 ③3.1 ④3.8 ⑤4.0 ⑥4.2 ⑦4.2 ⑧4.4 ⑨4.0 ⑩3.6 ⑪3.8 ⑫3.4 秒。
①は冒頭の一文のあとなので、画面に出ている時間が区間より約0.35秒短い（5.07秒）。
区間は、拍の並びがくずれない位置（最後の拍からの間隔が、そのパターンの R-R になる位置）で切っている。録音後に詰めるときも同じ考え方で。

---

## 並び（画面の色）

- 心房細動のf波と心拍数（①〜④、水色）：f波が粗い → f波が細かい → 頻脈性 → 徐脈性
- 心房細動でQRSの形・リズムが変わる（⑤〜⑧、黄）：アシュマン現象 → 脚ブロック → 完全房室ブロック（R-Rが規則的）→ WPW
- 心房粗動（⑨〜⑫、桃）：4:1（F波がいちばん見やすい）→ 2:1（F波が隠れる）→ 伝導比が変わる → 1:1
- 色の文字（看護師の動き）：緑「→ 初めてなら報告」①②⑨、橙「→ 脈拍と血圧も確認」③④⑩、紫「→ 12誘導で確認」⑤⑥⑪、赤「→ すぐ報告」⑦⑧⑫

## 言い回しの注意（LITFL本文で確認）

- **① ② f波・見分けのポイント**：LITFL（Atrial Fibrillation）「Irregularly irregular rhythm」「No P waves」「Fibrillatory waves may be present and can be either fine (amplitude < 0.5mm) or coarse (amplitude > 0.5mm)」「Fibrillatory waves may mimic P waves leading to misdiagnosis」。
  ②は「平らに見えても」心房細動、と R-R の不規則で判断する（画面「基線はほぼ平ら。R-Rで判断」）
- **③ 頻脈性**：LITFL（Atrial Fibrillation）「AF is often described as having 'rapid ventricular response' once the ventricular rate is > 100 bpm」「AF is most commonly associated with a ventricular rate ~ 110 – 160」
- **④ 徐脈性**：LITFL（Atrial Fibrillation）「'Slow' AF is a term often used to describe AF with a ventricular rate < 60 bpm」「Causes of 'slow' AF include hypothermia, digoxin toxicity, and medications」
- **⑤ アシュマン現象**：LITFL（Ashman Phenomenon）「aberrant ventricular conduction, usually of RBBB morphology, which follows a short R-R interval and preceding relatively prolonged R-R interval」「Clinically on its own is asymptomatic and does not require any specific treatment」。
  声は「長い間隔のあと、早く来た拍が幅広い」（長い R-R のあと、短い R-R で来た拍）
- **⑥ 脚ブロック**：LITFL（Atrial Fibrillation）「QRS complexes usually < 120ms, unless pre-existing bundle branch block, accessory pathway, or rate-related aberrant conduction」。形は LITFL（RBBB）「QRS duration > 120ms」「Wide, slurred S wave in lateral leads」をもとに、II誘導で幅の広いS波として描いた
- **⑦ 完全房室ブロック**：LITFL（Digoxin Toxicity）「Regularised AF = AF with complete heart block and a junctional or ventricular escape rhythm」「Coarse atrial fibrillation with 3rd degree AV block and a junctional escape rhythm」。
  LITFL（3rd degree AV block）「at high risk of ventricular standstill and sudden cardiac death」。声は「疑う」までにした（モニターだけでは確定しない）
- **⑧ WPW**：LITFL（Atrial fibrillation/flutter in pre-excitation）「Rate > 200 bpm」「Irregular rhythm, with extremely high rates in some places — up to 300 bpm」「Wide QRS complexes」「Subtle beat-to-beat variation in QRS morphology」「Axis remains stable, unlike Polymorphic VT」
  「Ensuing rapid ventricular rates may result in degeneration to ventricular tachycardia (VT) or ventricular fibrillation (VF)」「The administration of AV nodal blocking drugs … may precipitate ventricular arrhythmias and cardiac arrest」
- **⑨〜⑫ 心房粗動**：LITFL（Atrial Flutter）「Regular atrial activity at ~300 bpm」「'Saw-tooth' pattern of inverted flutter waves in leads II, III, aVF」「2:1 block = 150 bpm」「4:1 block = 75 bpm」
  - ⑩：「Suspect atrial flutter with 2:1 block whenever there is a regular narrow-complex tachycardia at 150 bpm」「Flutter waves are often very difficult to see when 2:1 block is present」。
    画面の波形ではF波が見えているので、ひとことは「F波が隠れる」ではなく「150/分で規則的なら粗動を疑う」にした（2026-10-05 検査役の指摘）。⑩は区間 4.4秒に対して声がぎりぎり（目安 3.6秒）。録音が長ければ区間を 4.8秒（0.4秒の倍数）に延ばす
  - ⑪：「Variable AV conduction ratio — The ventricular response is irregular and may mimic atrial fibrillation (AF)」「the R-R intervals will be multiples of the P-P interval」
  - ⑫：「Atrial flutter with 1:1 conduction is associated with severe haemodynamic instability and progression to ventricular fibrillation」（例は 250〜300/分の幅の狭い頻拍）
- **まとめ**：LITFL（Atrial Flutter）「In contrast, atrial fibrillation will be completely irregular, with no patterns to be discerned within the R-R intervals」

## 声の指定

- 全体に落ち着いて、はっきり
- ⑧⑫の「危険」は少し強く
- まとめの「R-Rがバラバラなら細動、のこぎりなら粗動」は、ゆっくり（「細動」「粗動」を聞き分けやすく）
- 最後の「保存して、見返してね」は明るく
