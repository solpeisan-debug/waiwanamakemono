# 第21弾 致死性不整脈と心停止 まず覚えたい12パターン — ナレーション

第17〜20弾と同じ作り。数字は画面に出ているので、声では読み上げない。「すぐ報告」は声では言わない（画面とキャプションで伝える）。
電気ショックの適応は、画面（ひとことのうしろの色の文字）とキャプションで伝え、声ではまとめで1回だけ言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第19弾の録り直しと同じ）。

---

## 読み上げ用（ElevenLabs に貼る）

致死性不整脈と心停止。まず覚えたいのは、この12パターン。

T波の上に乗るPVC、R on T。心室頻拍や心室細動のきっかけになることがあります。
PVCが3つ以上、速く続く。ショートラン、非持続性の心室頻拍です。
幅の広いQRSが、速く規則正しく。単形性の心室頻拍。
QRSの形が、1拍ごとに変わる。多形性の心室頻拍。
ねじれるように変わる。トルサード・ド・ポワント。QT延長がきっかけです。止まらずに持続して脈がなければ、電気ショックです。
不規則で大きな揺れ。粗い心室細動。
揺れが小さい、細かい心室細動。心静止と迷ったら、CPRを続けます。

PRは変わらず、突然QRSが抜ける。モビッツII型。完全房室ブロックに進むことがあります。
PとQRSが、別々に動く。完全房室ブロック。補充調律が止まると、心静止になります。
ほぼまっすぐの線、心静止。すぐにCPRを始め、並行して電極と感度も確かめて。

波形はふつうに見えても、脈がない。無脈性電気活動、PEA。
遅く幅の広いQRSでも、脈がなければPEA。

電気ショックをするのは、心室細動と、脈のない心室頻拍。
保存して、見返してね

---

## 並び（画面の色）

- 速くなる道（①〜⑦）：R on T → PVCの連発 → 単形性VT → 多形性VT → トルサード → 粗いVF → 細かいVF
- 遅くなる道（⑧〜⑩）：モビッツII型 → 完全房室ブロック → 心静止
- 脈がない（⑪⑫）：PEA（ふつうに見える）・PEA（遅く幅広い）
- 心停止の波形（ERC 2021・JRC 2020）は VF・無脈性VT・心静止・PEA の4つ。①②⑧⑨は心停止につながるサイン（画面は黄色の「→ すぐ報告」）

## 言い回しの注意（LITFL本文で確認。LITFL以外は出典を書いた）

- **① R on T**：LITFL（PVC）「in the context of an prolonged QTc … may predispose to malignant ventricular arrhythmias such as Torsades de Pointes by causing "R on T" phenomenon」。LITFL（PVT and TdP）「initiated when a PVC occurs during the preceding T wave (R on T)」。声は「きっかけになることがあります」（必ずではない）
- **② PVCの連発**：LITFL（PVC）「3-30 consecutive PVCs with a rate >100bpm described as non-sustained VT」。第17弾⑬と同じ言い方（「非持続性」をつけて、持続性VTと取りちがえない）
- **③〜⑤ VT・トルサード**：LITFL（PVT and TdP）「QRS complexes twist around the isoelectric line」「often short lived and self terminating … may degenerate into VF」。③〜⑤は画面で「→ 脈なしならショック」（脈があるVTは別の治療）
- **⑥⑦ VF**：LITFL（VF）「Chaotic irregular deflections of varying amplitude」「Rate 150 to 500 per minute」「Amplitude decreases with duration (coarse VF → fine VF)」
- **⑦ 迷ったら**：ERC 2021「If there is doubt about whether the rhythm is asystole or very fine VF … continue CPR」
- **⑧ モビッツII型**：LITFL（Mobitz II）「The PR interval in the conducted beats remains constant」「much more likely than Mobitz I to be associated with haemodynamic compromise, severe bradycardia and progression to 3rd degree heart block」「The risk of asystole is around 35% per year」
- **⑨ 完全房室ブロック**：LITFL（3rd degree AV block）「complete AV dissociation, with independent atrial and ventricular rates」「at high risk of ventricular standstill and sudden cardiac death」。画面は幅の広い心室補充調律 35/分（LITFL：15〜40/分・幅広）
- **⑩ 心静止**：CPRを遅らせず、並行して電極・誘導・感度を確かめる（ERC ALS の考え方。第20弾の電極外れとつながる）。P波だけの心静止（心室静止）はキャプションでだけふれる
- **⑪⑫ PEA**：LITFL CCC（Pulseless Electrical Activity）「organised or semi-organised electrical activity … not sufficient to produce a clinically detectable pulse」
- **まとめ**：ERC Guidelines 2021（Adult ALS）「shockable rhythms (VF/pVT) and non-shockable rhythms (asystole and PEA)」

## 声の指定

- 全体に落ち着いて、はっきり
- まとめの「電気ショックをするのは…」は、ゆっくり
- 最後の「保存して、見返してね」は明るく

---

## 専門医レビュー（2026-10-04、10パターン版）

- 「脈なしならショック」、「迷ったらCPR」、PEA は OK
- 【要修正→直した】トルサード：台本に「止まらずに持続して脈がなければ、電気ショックです。」（自然に止まる描写との混乱を防ぐ）
- 【要修正→直した】心静止：台本「すぐにCPRを始め、並行して電極と感度も確かめて。」、画面のひとこと「まっすぐの線。CPRと並行して電極も確認」（CPRを遅らせない）
- 【要修正→直した】キャプションの初動：反応確認 → なければ人を呼ぶ → 呼吸と脈の確認 → CPR（医療従事者のBLS）。出典に JRC蘇生ガイドライン2020 を追加

- 2026-10-04：タイトルを「心停止の波形」→「致死性不整脈と心停止」に変更。冒頭の一文は「致死性不整脈と心停止。まず覚えたいのは、この12パターン。」
- 2026-10-04：10 → 12パターンに組み替え。胸骨圧迫中（ノイズの話で、致死性不整脈ではない）と P波だけの心静止（キャプションでふれる）を外し、R on T・PVCの連発・モビッツII型・完全房室ブロックを足した。12パターン版はもう一度、専門医レビューに出す
