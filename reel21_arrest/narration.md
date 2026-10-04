# 第21弾 心停止の波形（致死性不整脈） まず覚えたい10パターン — ナレーション

第17〜20弾と同じ作り。数字は画面に出ているので、声では読み上げない。「すぐ報告」は声では言わない。
電気ショックの適応は、画面（ひとことのうしろの色の文字）とキャプションで伝え、声ではまとめで1回だけ言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。

---

## 読み上げ用（ElevenLabs に貼る）

心停止の波形で、まず覚えたいのは、この10パターン。

幅の広いQRSが、速く規則正しく。単形性の心室頻拍。
QRSの形が、1拍ごとに変わる。多形性の心室頻拍。
ねじれるように変わる。トルサード・ド・ポワント。QT延長がきっかけです。止まらずに持続して脈がなければ、電気ショックです。
不規則で大きな揺れ。粗い心室細動。
揺れが小さい、細かい心室細動。心静止と迷ったら、CPRを続けます。

ほぼまっすぐの線、心静止。すぐにCPRを始め、並行して電極と感度も確かめて。
P波はあるのに、QRSがない。
波形はふつうに見えても、脈がない。無脈性電気活動、PEA。
遅く幅の広いQRSでも、脈がなければPEA。
胸骨圧迫中は、揺れで波形が見えません。止めて、10秒以内に短く確かめます。

電気ショックをするのは、心室細動と、脈のない心室頻拍。
保存して、見返してね

---

## 言い回しの注意（LITFL本文で確認。LITFL以外は出典を書いた）

- **電気ショックの適応**：ERC Guidelines 2021（Adult ALS）「shockable rhythms (VF/pVT) and non-shockable rhythms (asystole and PEA)」。①②③は「脈がなければショック」（脈があるVTは別の治療）
- **③ トルサード**：LITFL（Polymorphic VT and TdP）「a specific form of PVT occurring in the context of QT prolongation … QRS complexes twist around the isoelectric line」「initiated when a PVC occurs during the preceding T wave (R on T)」「often short lived and self terminating … may degenerate into VF」
- **④⑤ VF**：LITFL（Ventricular Fibrillation）「Chaotic irregular deflections of varying amplitude」「Rate 150 to 500 per minute」「Amplitude decreases with duration (coarse VF → fine VF)」
- **⑤ 迷ったら**：ERC 2021（RCEM learning の要約で確認）「If there is doubt about whether the rhythm is asystole or very fine VF … continue CPR（non-shockable arm）」
- **⑥ 心静止**：電極・誘導・感度の確認（ERC ALS の考え方）。第20弾（ノイズ）の電極外れとつながる
- **⑦ P波だけ**：P-wave asystole（ventricular standstill）。ショック適応なし。ペーシングが効くことがある（Resuscitation Council UK・救急の文献）。画面では「ショックしない・CPR」
- **⑧⑨ PEA**：LITFL CCC（Pulseless Electrical Activity）「organised or semi-organised electrical activity … not sufficient to produce a clinically detectable pulse」。幅の狭い・広いで原因の見当が変わる（Littman algorithm）
- **⑩ 胸骨圧迫中**：LITFL（ECG Motion Artefacts）の例「The high amplitude oscillations … produced by movement artefact due to chest compressions」。波形の確認のための中断は短く（Resuscitation Council UK ALS：5秒以内）

## 声の指定

- 全体に落ち着いて、はっきり
- まとめの「電気ショックをするのは…」は、ゆっくり
- 最後の「保存して、見返してね」は明るく

---

## 専門医レビュー（2026-10-04）

- ①②③「脈なしならショック」、⑤「迷ったらCPR」、⑦（ペーシングに触れない）、⑧⑨ PEA、10パターンの選び方は OK
- 【要修正→直した】③：台本に「止まらずに持続して脈がなければ、電気ショックです。」（自然に止まる描写との混乱を防ぐ）
- 【要修正→直した】⑥：台本「すぐにCPRを始め、並行して電極と感度も確かめて。」、画面のひとこと「まっすぐの線。CPRと並行して電極も確認」（CPRを遅らせない）
- 【推奨→直した】⑩：台本「10秒以内に短く確かめます」、キャプション「（10秒以内）」（JRC蘇生ガイドライン2020。RC UK は5秒以内）
- 【要修正→直した】キャプションの初動：反応確認 → なければ人を呼ぶ → 呼吸と脈の確認 → CPR（医療従事者のBLS）。出典に JRC蘇生ガイドライン2020 を追加
