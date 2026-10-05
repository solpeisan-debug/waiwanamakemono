# 第28弾 心筋梗塞とST変化 まず覚えたい12パターン — ナレーション

第17〜21弾と同じ作り（1パターン1文、声で3〜4秒の「ぎゅっと版」）。数字は画面に出ているので、声では読み上げない。
**「すぐ報告」は声では言わない**（画面の赤い「→ すぐ報告・12誘導」とキャプションで伝える）。
「モニターのST変化は12誘導で確かめる」は、まとめの1文で声に出す（画面の色の文字・最後の文・キャプションにもある。左下の注記は「※II誘導のモニター（実際の速さ）」「※数値はこの波形での一例」にして、くり返しを減らした）。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第19弾の録り直し・第21弾と同じ）。

---

## 秒数（録音前の仮の版）

いまは録音前。区間の長さは「文の字数 ÷ 6字/秒 ＋ 0.75秒」以上で、拍の並びがくずれない位置にした（`make_reel28.py` の `SEG_D`）。
映像は仮で 63.9秒（冒頭 4.9秒＋12パターン 52.4秒＋一覧とまとめ 6.5秒）。録音が届いたら、声の長さに合わせて切り直す。

| パターン | 区間（秒） | 声の長さの見込み（秒） | 文 |
|---|---|---|---|
| 冒頭 | 4.9 | 4.7 | 心筋梗塞とST変化。まず覚えたいのは、この12パターン。 |
| ① | 4.8 | 3.0 | STは、基線と同じ高さ。これが基準。 |
| ② | 4.8 | 3.7 | 早い時期に、Tが高く幅広くなる。超急性期T波。 |
| ③ | 4.0 | 2.3 | STが持ち上がる、ST上昇。 |
| ④ | 4.0 | 2.7 | さらに大きいと、墓石のような形。 |
| ⑤ | 4.0 | 2.0 | 深く幅広いQ、異常Q波。 |
| ⑥ | 4.0 | 2.3 | Tが下向きになる、冠性T波。 |
| ⑦ | 4.8 | 3.3 | 水平や下り坂のST低下は、虚血のサイン。 |
| ⑧ | 4.4 | 3.2 | 上り坂のST低下は、虚血とは限らない。 |
| ⑨ | 4.48 | 3.5 | PRが下がり、STは広い範囲で上がる。心膜炎。 |
| ⑩ | 4.0 | 2.2 | 若い人に多い、早期再分極。 |
| ⑪ | 4.8 | 3.5 | 左脚ブロックでは、STの判定がむずかしい。 |
| ⑫ | 4.76 | 2.8 | 再灌流のときに出やすい、AIVR。 |
| まとめ | — | 3.5 | モニターのST変化は、12誘導で確かめる。 |
| 保存 | — | 1.7 | 保存して、見返してね |

---

## 読み上げ用（ElevenLabs に貼る）

心筋梗塞とST変化。まず覚えたいのは、この12パターン。

STは、基線と同じ高さ。これが基準。
早い時期に、Tが高く幅広くなる。超急性期T波。
STが持ち上がる、ST上昇。
さらに大きいと、墓石のような形。
深く幅広いQ、異常Q波。
Tが下向きになる、冠性T波。

水平や下り坂のST低下は、虚血のサイン。
上り坂のST低下は、虚血とは限らない。

PRが下がり、STは広い範囲で上がる。心膜炎。
若い人に多い、早期再分極。
左脚ブロックでは、STの判定がむずかしい。

再灌流のときに出やすい、AIVR。

モニターのST変化は、12誘導で確かめる。
保存して、見返してね

- 読み：ST＝エスティー、PR＝ピーアール、AIVR＝エーアイブイアール、冠性T波＝かんせいティーは、異常Q波＝いじょうキューは、再灌流＝さいかんりゅう
- くわしい説明（12誘導での見え方・鏡像変化・ST/T比・Sgarbossa など）は、画面のひとこととキャプション（とレビュー）にまかせる

---

## 並び（画面の色）

- 心筋梗塞の時間の流れ（①〜⑥）：①基準 → ②超急性期T波 → ③ST上昇 → ④墓石型ST上昇 → ⑤異常Q波 → ⑥冠性T波
  - ①は緑の「→ 比べる基準」。②③④は赤（すぐ報告・12誘導）、⑤⑥は橙（12誘導で確認）
  - ④墓石型は時間の段階ではなく「ST上昇がさらに大きい形」。声は「さらに大きいと」で、段階と取り違えないようにした
- ST低下（⑦⑧）：⑦水平・下降型（赤「すぐ報告・12誘導」）、⑧上行型（橙「12誘導で確認」）
- 心筋梗塞とまぎらわしいST上昇（⑨〜⑪）：心膜炎・早期再分極・左脚ブロック（橙「12誘導で確認」）
- 再灌流のときの不整脈（⑫）：AIVR（紫「→ 報告して観察」）
- 冒頭のフックは ②〜⑥（心筋梗塞の時間の流れ）を順に見せる

## 言い回しの注意（LITFL本文で確認。LITFL以外は使っていない）

- **大前提（12誘導で確認）**：LITFL（ST Segment）「ST segment elevation and Q-wave formation in contiguous leads」「There is usually reciprocal ST depression in the electrically opposite leads」。STEMI は「隣り合う誘導」と「鏡像変化」で判断するので、II誘導1本のモニターでは決められない。LITFL（Inferior STEMI）「ST elevation in leads II, III, aVF」：II誘導は下壁を見る誘導で、前壁の変化はモニターに出にくい（キャプション「モニターの1つの誘導だけでは判断できません」）
- **① 基準**：LITFL（ST Segment）「The ST segment is the flat, isoelectric section of the ECG between the end of the S wave (the J point) and the beginning of the T wave.」「ST- and PR-segment changes are relative to the baseline formed by the T-P segment」（Pericarditis）。画面「STは基線（TP）と同じ高さ」
- **② 超急性期T波**：LITFL（T wave）「Broad, asymmetrically peaked or 'hyperacute' T-waves (HATW) are seen in the early stages of ST-elevation MI (STEMI), and often precede the appearance of ST elevation and Q waves.」「Particular attention should be paid to their size in relation to the preceding QRS complex」。LITFL（Anterior MI）「These changes are often preceded by hyperacute T waves」。声は「最初は」ではなく「早い時期に」（often precede であって、必ず最初とは限らない）
- **③ ST上昇**：LITFL（ST Segment）「Acute STEMI may produce ST elevation with either concave, convex or obliquely straight morphology.」→ 画面は上に凸で描いたが、ひとことは形を言い切らず「J点からSTが持ち上がる」。キャプションで「下に凸やまっすぐのことも」
- **④ 墓石型**：LITFL（Anterior MI, Example 6）「Massive ST elevation with "tombstone" morphology … indicates a large territory infarction with a poor LV ejection fraction and high likelihood of cardiogenic shock and death」。LITFL（Inferior STEMI, Example 6）「Marked ST elevation in II, III and aVF with a "tombstone" morphology」
- **⑤ 異常Q波**：LITFL（Q Wave）「Q waves are considered pathological if: > 40 ms (1 mm) wide; > 2 mm deep; > 25% of depth of QRS complex」「Pathological Q waves usually indicate current or prior myocardial infarction.」→ 画面「深く幅広いQ。梗塞のあと」（Q 幅46ms・深さ3.2mm で描いた）
- **⑥ 冠性T波**：LITFL（T wave）「Pathological T wave inversion is usually symmetrical and deep (>3mm).」「Fixed T-wave inversions are seen following infarction, usually in association with pathological Q waves」→ 画面「左右対称の深い陰性T」（Q を残して描いた）
- **⑦ 水平・下降型 ST 低下**：LITFL（Myocardial Ischaemia）「Horizontal or downsloping ST depression ≥ 0.5 mm at the J-point in ≥ 2 contiguous leads indicates myocardial ischaemia」→ 声「虚血のサイン」
- **⑧ 上行型 ST 低下**：LITFL（Myocardial Ischaemia）「Upsloping ST depression is non-specific for myocardial ischaemia.」→ 声「虚血とは限らない」。ただし LITFL（ST Segment）「Upsloping ST depression in the precordial leads with prominent De Winter T waves is highly specific for occlusion of the LAD」なので、「否定できる」とは言わない（キャプション「胸痛があれば12誘導で確認」）
- **⑨ 心膜炎**：LITFL（Pericarditis）「Widespread concave ST elevation and PR depression throughout most of the limb leads … and precordial leads」「The degree of ST elevation is typically modest (0.5 – 1mm).」「Sinus tachycardia is also common」→ ST 約1mm・PR -0.7mm・107/分で描いた。「広い範囲で」は12誘導での話（画面のひとことには入れていない）
- **⑩ 早期再分極**：LITFL（BER）「a usually benign ECG pattern producing widespread ST segment elevation that is commonly seen in young, healthy patients < 50 years of age」「Notching or slurring at the J point」「ST elevation : T wave height ratio in V6 < 0.25」「Avoid diagnosing BER in patients over the age of 50」→ 声「若い人に多い」
- **⑪ 左脚ブロック**：LITFL（LBBB）「Appropriate discordance … Lateral leads with tall, broad R waves will often have associated ST-segment depression and T-wave inversion」「Any concordant ST segment change is concerning for ischaemia」。LITFL（Sgarbossa）「In patients with left bundle branch block (LBBB) or ventricular paced rhythm, infarct diagnosis based on the ECG can be difficult」→ 声「STの判定がむずかしい」
- **⑫ AIVR**：LITFL（AIVR）「Rate typically 50-120 bpm」「QRS duration > 120ms」「AIVR is classically seen in the reperfusion phase of an acute STEMI」「Usually a well-tolerated, benign, self-limiting arrhythmia」「Administration of anti-arrhythmics may cause precipitous haemodynamic deterioration and should be avoided」→ 声「再灌流のときに出やすい」、画面「→ 報告して観察」
- **まとめ**：上の「大前提」と同じ。「確かめる」と言い、「すぐ報告」とは言わない

## 声の指定

- 全体に落ち着いて、はっきり
- ②③④（急性期）は少し引きしめて。⑨⑩⑪（まぎらわしいもの）は少しやわらかく
- まとめの「モニターのST変化は、12誘導で確かめる。」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
