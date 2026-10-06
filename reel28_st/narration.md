# 第28弾 心筋梗塞とST変化 まず覚えたい10パターン — ナレーション

第17〜21弾と同じ作り（1パターン1文、声で3〜4秒の「ぎゅっと版」）。数字は画面に出ているので、声では読み上げない。
**「すぐ報告」は声では言わない**（画面の色の文字・冒頭の問いかけ「このST、すぐ報告？」・キャプションで伝える）。
「モニターのST変化は12誘導で確かめる」は、まとめの1文で声に出す（画面の色の文字・最後の文・キャプションにもある）。
「何個わかった？コメントで教えてね」は画面とキャプションだけ（声の最後は「保存して、見返してね」のまま）。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第19弾の録り直し・第21弾と同じ）。

- 2026-10-06：12パターン → 10パターンに作り直し（ユーザー承認）。墓石型は③に含め、上行型のST低下・早期再分極を外し、⑩完全房室ブロックを足した

---

## 秒数（録音前の仮の版）

いまは録音前。区間の長さは「文の字数 ÷ 6字/秒 ＋ 0.75秒」以上で、拍の並びがくずれない位置にした（`make_reel28.py` の `SEG_D`）。
映像は仮で 59.2秒（冒頭 4.9秒＋10パターン 46.6秒＋一覧とまとめ 7.7秒。冒頭の変形は 0.3秒から）。録音が届いたら、声の長さに合わせて切り直す。

| パターン | 区間（秒） | 声の長さの見込み（秒） | 文 |
|---|---|---|---|
| 冒頭 | 4.9 | 4.7 | 心筋梗塞とST変化。まず覚えたいのは、この10パターン。 |
| ① | 4.8 | 3.0 | STは、基線と同じ高さ。これが基準。 |
| ② | 4.8 | 3.8 | 早い時期に、Tが高く幅広くなる。超急性期T波。 |
| ③ | 5.6 | 4.7 | STが持ち上がる、ST上昇。大きいと、墓石のような形に。 |
| ④ | 4.0 | 2.0 | 深く幅広いQ、異常Q波。 |
| ⑤ | 4.0 | 2.3 | Tが下向きになる、冠性T波。 |
| ⑥ | 4.8 | 3.3 | 水平や下り坂のST低下は、虚血のサイン。 |
| ⑦ | 5.04 | 3.8 | PRが下がり、STは広い範囲で上がる。心膜炎。 |
| ⑧ | 4.8 | 3.5 | 左脚ブロックでは、STの判定がむずかしい。 |
| ⑨ | 4.76 | 2.8 | 再灌流のときに出やすい、AIVR。 |
| ⑩ | 4.36 | 3.5 | 下壁の梗塞で起きやすい、完全房室ブロック。 |
| まとめ | — | 3.5 | モニターのST変化は、12誘導で確かめる。 |
| 保存 | — | 1.7 | 保存して、見返してね |

---

## 読み上げ用（ElevenLabs に貼る）

心筋梗塞とST変化。まず覚えたいのは、この10パターン。

STは、基線と同じ高さ。これが基準。
早い時期に、Tが高く幅広くなる。超急性期T波。
STが持ち上がる、ST上昇。大きいと、墓石のような形に。
深く幅広いQ、異常Q波。
Tが下向きになる、冠性T波。

水平や下り坂のST低下は、虚血のサイン。

PRが下がり、STは広い範囲で上がる。心膜炎。
左脚ブロックでは、STの判定がむずかしい。

再灌流のときに出やすい、AIVR。
下壁の梗塞で起きやすい、完全房室ブロック。

モニターのST変化は、12誘導で確かめる。
保存して、見返してね

- 読み：ST＝エスティー、PR＝ピーアール、AIVR＝エーアイブイアール、冠性T波＝かんせいティーは、異常Q波＝いじょうキューは、再灌流＝さいかんりゅう、墓石＝はかいし、下壁＝かへき
- くわしい説明（12誘導での見え方・鏡像変化・ST/T比 など）は、画面のひとこと・虫眼鏡の値・キャプションにまかせる

---

## 並び（画面の色）と、この回の見せ方

- 心筋梗塞の時間の流れ（①〜⑤）：①基準 → ②超急性期T波 → ③ST上昇（大きいと墓石型）→ ④異常Q波 → ⑤冠性T波
  - ①は緑の「→ 比べる基準」。②③は赤（すぐ報告・12誘導）、④⑤は橙（12誘導で確認）
  - ②〜⑤のあいだ、上に「時間の流れ　超急性期T → ST上昇 → 異常Q波 → 冠性T」のバー（いまの段階に下線）。時間の目安は書かない
- ⑥ ST低下（水平・下降型）：赤（すぐ報告・12誘導）
- まぎらわしいST変化（⑦⑧）：心膜炎・左脚ブロック（橙「12誘導で確認」）
- 心筋梗塞のときの不整脈（⑨⑩）：AIVR（紫「→ 報告して観察」）、完全房室ブロック（赤「→ すぐ報告」）
- STの虫眼鏡：中部の帯の上の窓に1拍を拡大（1マス＝1mm の正方形）。基線の点線と矢印、右上に「ST ↑3mm」などの値（モデルから計算）
- 冒頭のフックは ②〜⑥ を順に見せ、その上に問いかけ「このST、すぐ報告？」（画面だけ）
- 最後は「モニターのST変化は、12誘導で確認」「保存して見返してね」「何個わかった？コメントで教えてね」

## 言い回しの注意（LITFL本文で確認。LITFL以外は使っていない）

- **大前提（12誘導で確認）**：LITFL（ST Segment）「ST segment elevation and Q-wave formation in contiguous leads」「There is usually reciprocal ST depression in the electrically opposite leads」。STEMI は「隣り合う誘導」と「鏡像変化」で判断するので、II誘導1本のモニターでは決められない。LITFL（Inferior STEMI）「ST elevation in leads II, III, aVF」：II誘導は下壁を見る誘導で、前壁の変化はモニターに出にくい
- **① 基準**：LITFL（ST Segment）「The ST segment is the flat, isoelectric section of the ECG between the end of the S wave (the J point) and the beginning of the T wave.」、LITFL（Pericarditis）「ST- and PR-segment changes are relative to the baseline formed by the T-P segment」→ 虫眼鏡の点線＝TP の基線
- **② 超急性期T波**：LITFL（T wave）「Broad, asymmetrically peaked or 'hyperacute' T-waves (HATW) are seen in the early stages of ST-elevation MI (STEMI), and often precede the appearance of ST elevation and Q waves.」→ 声は「早い時期に」（必ず最初とは言わない）
- **③ ST上昇（墓石型をふくむ）**：LITFL（ST Segment）「Acute STEMI may produce ST elevation with either concave, convex or obliquely straight morphology.」→ ひとことは形を言い切らない。LITFL（Anterior MI, Example 6）「Massive ST elevation with "tombstone" morphology」、LITFL（Inferior STEMI, Example 6）「Marked ST elevation in II, III and aVF with a "tombstone" morphology」→ 声「大きいと、墓石のような形に。」
- **④ 異常Q波**：LITFL（Q Wave）「Q waves are considered pathological if: > 40 ms (1 mm) wide; > 2 mm deep; > 25% of depth of QRS complex」「Pathological Q waves usually indicate current or prior myocardial infarction.」
- **⑤ 冠性T波**：LITFL（T wave）「Pathological T wave inversion is usually symmetrical and deep (>3mm).」「Fixed T-wave inversions are seen following infarction, usually in association with pathological Q waves」
- **時間の流れのバー**：LITFL（Anterior MI）「ST segment elevation with subsequent Q wave formation … These changes are often preceded by hyperacute T waves」、LITFL（T wave）「Fixed T-wave inversions are seen following infarction」。時間（何時間・何日）は LITFL で一般化した書き方が見つからなかったので書かない
- **⑥ 水平・下降型 ST 低下**：LITFL（Myocardial Ischaemia）「Horizontal or downsloping ST depression ≥ 0.5 mm at the J-point in ≥ 2 contiguous leads indicates myocardial ischaemia」→ 声「虚血のサイン」
- **⑦ 心膜炎**：LITFL（Pericarditis）「Widespread concave ST elevation and PR depression throughout most of the limb leads … and precordial leads」「The degree of ST elevation is typically modest (0.5 – 1mm).」「Sinus tachycardia is also common」→ ST 約0.9mm・PR -0.7mm・107/分で描いた
- **⑧ 左脚ブロック**：LITFL（LBBB）「Lateral leads with tall, broad R waves will often have associated ST-segment depression and T-wave inversion」「Any concordant ST segment change is concerning for ischaemia」。LITFL（Sgarbossa）「In patients with left bundle branch block (LBBB) or ventricular paced rhythm, infarct diagnosis based on the ECG can be difficult」→ 声「STの判定がむずかしい」
- **⑨ AIVR**：LITFL（AIVR）「Rate typically 50-120 bpm」「QRS duration > 120ms」「AIVR is classically seen in the reperfusion phase of an acute STEMI」「Usually a well-tolerated, benign, self-limiting arrhythmia」→ 声「再灌流のときに出やすい」、画面「→ 報告して観察」
- **⑩ 完全房室ブロック**：LITFL（Inferior STEMI）「Up to 20% of patients with inferior STEMI will develop either second- or third-degree AV block.」、LITFL（AV block: 3rd degree）「Causes … Inferior myocardial infarction」「complete AV dissociation, with independent atrial and ventricular rates」「Patients with third degree heart block are at high risk of ventricular standstill and sudden cardiac death」、Example 1「Atrial rate is ~ 85 bpm / Ventricular rate is ~ 38 bpm / … junctional escape rhythm / Marked inferior ST elevation indicates that the cause is an inferior STEMI」→ 心房 86/分・心室 38/分・接合部補充調律・下壁のST上昇で描いた。声「下壁の梗塞で起きやすい」、画面「→ すぐ報告」
- **早期再分極（外した。キャプションだけ）**：LITFL（BER）「commonly seen in young, healthy patients < 50 years of age」「it may mimic pericarditis or acute MI」→ キャプション「モニターでは区別できないので12誘導で見分けます」
- **まとめ**：上の「大前提」と同じ。「確かめる」と言い、「すぐ報告」とは言わない

## 声の指定

- 全体に落ち着いて、はっきり
- ②③（急性期）と⑩は少し引きしめて。⑦⑧（まぎらわしいもの）は少しやわらかく
- まとめの「モニターのST変化は、12誘導で確かめる。」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
