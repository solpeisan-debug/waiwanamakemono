# 第24弾 頻脈（幅の狭いQRS） まず覚えたい12パターン — ナレーション

第21弾と同じ作り（1パターン1文・声で3〜4秒）。数字は画面に出ているので、声では読み上げない。
**「すぐ報告」は声では言わない**（画面の色の文字「→ すぐ報告」とキャプションで伝える）。
「→ まず患者さん」「→ 12誘導で確認」も画面とキャプションにまかせる。声は波形の見分け方だけを言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第19・21弾と同じ）。

---

## 録音前の版（区間の長さは仮）

- 各パターンの区間（秒・仮）：①4.16 ②4.46 ③4.60 ④5.08 ⑤3.80 ⑥4.43 ⑦4.29 ⑧5.6 ⑨5.1 ⑩4.5 ⑪4.68 ⑫5.3（映像 67.1秒）
- 文の長さの見込み（約8モーラ/秒）＋0.75秒以上になるよう、拍の並びがくずれない位置で切った
- 1パターンの声の長さの目安（区間の長さ − 0.75秒）：①3.4 ②3.7 ③3.9 ④4.3 ⑤3.1 ⑥3.7 ⑦3.5 ⑧4.9 ⑨4.4 ⑩3.8 ⑪3.9 ⑫4.6 秒
- 冒頭の一文は 4.9秒まで（`T_TITLE`）。録音が届いたら、長さに合わせて直す

---

## 読み上げ用（ElevenLabs に貼る）

幅の狭いQRSの頻脈。まず覚えたいのは、この12パターン。

どの拍にもP波がある、洞頻脈。
形のちがうP波が3つ続く、PACの連発。
形のちがうP波が、規則正しく。心房頻拍。
P波の形が3種類以上、多源性心房頻拍。
P波がなく、バラバラ。速い心房細動。
のこぎりの波が隠れる、心房粗動の2対1。

規則正しく速く、P波が見えない。PSVT。
PACをきっかけに突然始まり、突然止まる。
QRSのすぐあとに逆向きのP波。房室回帰性頻拍。
PRが短く、デルタ波がある。WPW。
QRSの直前に逆向きのP。接合部頻拍。

P波がT波に隠れると、洞頻脈もPSVTに見える。

規則正しいか、P波はどこか。まずこの2つ。
保存して、見返してね

- 読み方：PAC＝ピーエーシー、PSVT＝ピーエスブイティー、WPW＝ダブリューピーダブリュー、2対1＝にたいいち
- 「房室回帰性頻拍」は ElevenLabs で読みがゆれたら「ぼうしつかいきせいひんぱく」とかなで入れる

---

## 並び（画面の色）

- 洞結節から（水色）：① 洞頻脈、⑫ P波が隠れた洞頻脈
- 心房から（オレンジ）：② PACの連発 → ③ 心房頻拍 → ④ 多源性心房頻拍 → ⑤ 心房細動（速い）→ ⑥ 心房粗動（2:1）
- 房室結節・副伝導路のあたり（ピンク）：⑦ PSVT（房室結節リエントリー）→ ⑧ 始まりと終わり → ⑨ 房室回帰性頻拍（順方向性）→ ⑩ WPW（洞調律のとき）→ ⑪ 接合部頻拍
- 心房細動・心房粗動のくわしいバリエーション（f波の粗い・細かい、伝導比、変行伝導）は第26弾。ここでは代表の1つずつ
- 幅の広いQRSの頻拍（VT、逆方向性の房室回帰性頻拍、変行伝導など）は第27弾（見分けマップ③）

## 画面の色の文字（ひとことのうしろ）

- **→ まず患者さん**（緑）：①②④。波形そのものより、原因と患者さんの状態を見る
- **→ すぐ報告**（黄）：⑤⑥⑦⑨⑪。持続する上室性の頻拍。医師に知らせる（声では言わない）
- **→ 12誘導で確認**（青）：③⑧⑩⑫。P波の形・向き、PR、デルタ波は12誘導で確かめる

## 言い回しの注意（LITFL本文で確認）

- **① 洞頻脈**：LITFL（Sinus tachycardia）「Sinus rhythm with resting heart rate (HR) > 100 bpm in adults」「Sinus tachycardia is usually a secondary condition」。原因の例：「Pain」「Hypovolaemia」「Hypoxia」「Sepsis, pyrexia」「Anaemia」など → 画面「→ まず患者さん」
- **② PACの連発**：LITFL（PAC）「Abnormal (non-sinus) P wave usually followed by a normal QRS complex」「Triplet — three consecutive PACs」「a PAC may be the trigger for the onset of a re-entry tachyarrhythmia — e.g. Atrial fibrillation, atrial flutter, AVNRT, AVRT」。原因の例：「Anxiety」「Excess caffeine」「Hypokalaemia」「Hypomagnesaemia」
  - 「PACの3連＝上室性のショートラン」とは LITFL に書いていないので、画面・声では「3つ続く」とだけ言う
- **③ 心房頻拍**：LITFL（Atrial tachycardia）「originating from a single ectopic focus within the atria but outside of the sinus node」「Abnormal P wave morphology and axis (e.g. inverted in inferior leads)」「Unifocal, identical P waves」「Isoelectric baseline (unlike atrial flutter)」
  - モデルでは、II誘導で、小さくとがった上向き → 下向きの二相性のP'（第17弾のPACの形を、二相性がわかるよう強めた）で描いた。LITFL の例は「下向き」なので、レビューで確認
- **④ 多源性心房頻拍**：LITFL（MAT）「Irregularly irregular rhythm with varying PP, PR and RR intervals」「At least 3 distinct P-wave morphologies in the same lead」「Most commonly seen in patients with severe COPD or congestive heart failure」「Tends to resolve following treatment of the underlying disorder」 → 画面「→ まず患者さん」
- **⑤ 心房細動（速い）**：LITFL（Atrial fibrillation）「Irregularly irregular rhythm」「No P waves」「Absence of an isoelectric baseline」「AF is often described as having ‘rapid ventricular response’ once the ventricular rate is > 100 bpm」
- **⑥ 心房粗動（2:1）**：LITFL（Atrial flutter）「“Saw-tooth” pattern of inverted flutter waves in leads II, III, aVF」「The most common AV ratio is 2:1, resulting in a ventricular rate of ~150 bpm」「Narrow complex tachycardia at 150 bpm (range 130-170)? Yes -> Suspect flutter!」
- **⑦ PSVT（房室結節リエントリー）**：LITFL（SVT）「Regular tachycardia ~140-280 bpm」「P waves are often hidden – being embedded in the QRS complexes」「Pseudo S waves may be seen in leads II, III or aVF」
- **⑧ 始まりと終わり**：LITFL（SVT）「Paroxysmal SVT (pSVT) describes an SVT with abrupt onset and offset」「if a premature atrial contraction (PAC) arrives while the fast pathway is still refractory, the electrical impulse will be directed solely down the slow pathway」（きっかけのPACは遅い道を通るので PR が長い）。LITFL（AVRT）「Wolff-Parkinson-White (WPW) pattern is now evident on the baseline ECG; this confirms that the initial rhythm was orthodromic AVRT」 → 止まったあとの12誘導
- **⑨ 房室回帰性頻拍（順方向性）**：LITFL（AVRT）「In orthodromic AVRT, anterograde conduction is via the AV node, producing a regular narrow complex rhythm」「Retrograde P waves are usually visible, with a long RP interval」「In AVRT, retrograde P waves occur later, with a long RP interval > 70 msec」「Rate usually 200-300 bpm」
- **⑩ WPW（洞調律）**：LITFL（Pre-excitation syndromes）「PR interval < 120ms」「Delta wave: slurring slow rise of initial portion of the QRS」「QRS prolongation > 110ms」「Discordant ST-segment and T-wave changes」
  - 「WPW症候群」は副伝導路＋頻脈発作がそろったときの名前（LITFL「WPW Syndrome refers to the presence of a congenital accessory pathway (AP) and episodes of tachyarrhythmias」）。画面は「WPW（洞調律のとき）」とし、「症候群」とは言わない
- **⑪ 接合部頻拍**：LITFL（Accelerated junctional rhythm）「Junctional Tachycardia: > 100 bpm」「Retrograde P waves may be present and can appear before, during or after the QRS complex. They are usually inverted in inferior leads」「Short PR interval (< 120 ms) indicates a junctional rather than atrial focus」。原因の例「Digoxin toxicity (= the classic cause of AJR)」
- **⑫ P波が隠れた洞頻脈**：LITFL（Sinus tachycardia）「With very fast heart rates the P waves may be hidden in the preceding T wave, producing a ‘camel hump’ appearance」。LITFL（SVT）の SVT の分類に「Sinus tachycardia」が入っている（「Regular Atrial」）
- **まとめ**：LITFL（SVT）「SVTs can be classified based on: Site of origin (atria or AV node) or; Regularity (regular or irregular)」（箇条書きをつないだ）→「規則正しいか、P波はどこか」
- **キャプションの「急変として対応」**：LITFL（SVT）の症状「Presyncope or syncope due to a transient fall in blood pressure」「Chest pain」「Dyspnoea」、LITFL（AVRT）「patients that are unstable due to this rhythm require urgent DC cardioversion」

## 声の指定

- 全体に落ち着いて、はっきり
- まとめの「規則正しいか、P波はどこか」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
