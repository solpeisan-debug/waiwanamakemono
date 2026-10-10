# 第24弾 頻脈（幅の狭いQRS） まず覚えたい10パターン — ナレーション

第21弾と同じ作り（1パターン1文・声で3〜4秒。⑧だけ2文で約5秒）。数字は画面に出ているので、声では読み上げない。
**「すぐ報告」は声では言わない**（画面の色の文字「→ すぐ報告」とキャプションで伝える）。
「→ まず患者さん」「→ 12誘導で確認」「→ 数字を見る」も画面とキャプションにまかせる。声は波形の見分け方だけを言う。
画面はクイズ形式：はじめに「これは？」を出し、波形が見えてから約0.7秒で名前に変わる。声も「特徴 → 名前」の順にしている。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第19・21弾と同じ）。

---

## 秒数つき（録音 2026-10-07 ElevenLabs Ren – Smooth & Soothing を、atempo=1.2 で1.2倍速にして置いた位置）

元の録音 `out/vo/narration_orig.mp3`（61.4秒）を、声の高さを変えずに1.2倍速にした `out/vo/narration_raw.wav`（51.20秒）を使った。
`align_vo.py` で、無音（0.25秒以上）を手がかりに 25 かたまりに切り分け、13文にまとめて下の秒数に置いた。継ぎ目はすべて無音の中。
文の中の息継ぎは 0.45秒まで詰めた（2026-10-10：詰め方のまちがいで 0.01〜0.26秒になり、④⑨の語尾が切れていたのを直して置き直した）。モニター音は声の下で最大 8dB 下げている。映像は 58.2秒。
⑧ は区間が長い（9.6秒）ので、「突然始まり…PSVT」がカウンターの跳ぶところに、「少しずつ変わるなら…」が洞調律の少しずつ変わるところに重なるよう、PAC がカウンターの位置を通る 0.5秒前から話し始める。

| 秒 | 文 |
|---|---|
| 0.10–4.51 | 幅の狭いQRSの頻脈。まず覚えたいのは、この10パターン。 |
| 4.80–7.89 | どの拍にも、ふつうのP波。洞頻脈。 |
| 8.34–12.20 | PSVTに見えても、P波がT波に重なる洞頻脈。 |
| 13.14–16.77 | いつもと違うP波が、規則正しく。心房頻拍。 |
| 17.28–21.46 | P波の形が3種類以上で、不規則。多源性心房頻拍。 |
| 21.89–24.87 | P波がなく、バラバラ。速い心房細動。 |
| 25.34–28.45 | のこぎりの波が隠れる、心房粗動の2対1。 |
| 29.37–32.86 | 規則正しく速く、P波が見えない。PSVT。 |
| 36.17–41.49 | 突然始まり、突然止まるのはPSVT。少しずつ変わるなら、洞頻脈が多い。 |
| 43.27–47.54 | QRSのすぐあとに逆向きのP波。房室回帰性頻拍。 |
| 48.07–51.82 | QRSの直前に逆向きのP。接合部頻拍。 |
| 52.20–55.53 | 規則正しいか、P波はどこか。まずこの2つ。 |
| 55.83–57.25 | 保存して、見返してね |

- 各パターンの長さ（秒）：①3.64 ②4.8 ③4.14 ④4.61 ⑤3.45 ⑥4.03 ⑦4.29 ⑧9.61 ⑨4.80 ⑩4.53（声の長さ＋0.75秒以上で、拍の並びがくずれない位置）。T_TITLE 4.5、END_HOLD 5.0
- 書き起こし（faster-whisper small）：13文とも台本どおりの順で、全部入っている。同じ音の別の字になったところ（「頻脈」→「品脈」、「拍」→「箱」、「心房」→「心臀」など）は Whisper の聞きちがえ

---

## 読み上げ用（ElevenLabs に貼る）

幅の狭いQRSの頻脈。まず覚えたいのは、この10パターン。

どの拍にも、ふつうのP波。洞頻脈。
PSVTに見えても、P波がT波に重なる洞頻脈。
いつもと違うP波が、規則正しく。心房頻拍。
P波の形が3種類以上で、不規則。多源性心房頻拍。
P波がなく、バラバラ。速い心房細動。
のこぎりの波が隠れる、心房粗動の2対1。

規則正しく速く、P波が見えない。PSVT。
突然始まり、突然止まるのはPSVT。少しずつ変わるなら、洞頻脈が多い。
QRSのすぐあとに逆向きのP波。房室回帰性頻拍。
QRSの直前に逆向きのP。接合部頻拍。

規則正しいか、P波はどこか。まずこの2つ。
保存して、見返してね

- 読み方：PSVT＝ピーエスブイティー、2対1＝にたいいち
- 「房室回帰性頻拍」は ElevenLabs で読みがゆれたら「ぼうしつかいきせいひんぱく」とかなで入れる
- ⑧は、画面の心拍数カウンターの変わり方（PSVT 90→167→170 → 突然止まる → 洞調律 75→90→105→120→135→120→105）に合わせて「突然」→「少しずつ」の順
- ⑧の洞頻脈は、画面では数秒で変わるが、実際の変化はもっとゆっくり（数十秒〜数分）。キャプションと依頼文に書いた

---

## 並び（画面の色）

- 洞結節から（水色）：① 洞頻脈、② 洞頻脈（P波がT波に重なる）
- 心房から（オレンジ）：③ 心房頻拍 → ④ 多源性心房頻拍 → ⑤ 心房細動（速い）→ ⑥ 心房粗動（2:1）
- 房室結節・副伝導路のあたり（ピンク）：⑦ PSVT（房室結節リエントリー）→ ⑧ 始まり方（PSVTと洞頻脈）→ ⑨ 房室回帰性頻拍（順方向性）→ ⑩ 接合部頻拍
- 外したもの：PACの連発（期外収縮の回の内容）、WPW（洞調律。頻脈ではない。見分けマップ③にある）
- 心房細動・心房粗動のくわしいバリエーションは第26弾。幅の広いQRSの頻拍は第27弾（見分けマップ③）

## 画面の色の文字（ひとことのうしろ）

- **→ まず患者さん**（緑）：①④。波形そのものより、原因と患者さんの状態を見る
- **→ すぐ報告**（黄）：⑤⑥⑦⑨⑩。持続する上室性の頻拍。医師に知らせる（声では言わない）
- **→ 12誘導で確認**（青）：②③。P波の形・位置は12誘導で確かめる
- **→ 数字を見る**（紫）：⑧。心拍数カウンターが少しずつ変わるか、1拍で跳ぶか

## この回だけの見せ方

- **心拍数カウンター**（波形の下のまん中「♥ 150 /分」）：帯の右のほう（x=940）を R が通るたびに、その拍の R-R から計算した心拍数に変わる（モデルの値。手打ちしない）。ピッという音も同じ瞬間。⑧だけ、横に小さく「↑ 1拍で跳ぶ」「↓ 突然止まる」「↗ 少しずつ」「↘ 少しずつ」
- **クイズ**：名前の行に「これは？」→ 名前

## 言い回しの注意（LITFL本文で確認）

- **① 洞頻脈**：LITFL（Sinus tachycardia）「Sinus rhythm with resting heart rate (HR) > 100 bpm in adults」「Sinus tachycardia is usually a secondary condition」。原因の例：「Pain」「Hypovolaemia」「Hypoxia」「Sepsis, pyrexia」「Anaemia」など → 画面「→ まず患者さん」
- **② 洞頻脈（P波がT波に重なる）**：LITFL（Sinus tachycardia）「With very fast heart rates the P waves may be hidden in the preceding T wave, producing a ‘camel hump’ appearance」。LITFL（SVT）の SVT の分類に「Sinus tachycardia」が入っている（「Regular Atrial」）
- **③ 心房頻拍**：LITFL（Atrial tachycardia）「originating from a single ectopic focus within the atria but outside of the sinus node」「Abnormal P wave morphology and axis (e.g. inverted in inferior leads)」「Unifocal, identical P waves」「Isoelectric baseline (unlike atrial flutter)」
  - モデルでは、II誘導で、小さくとがった上向き → 下向きの二相性のP'（第17弾のPACの形を、二相性がわかるよう強めた）で描いた。LITFL の例は「下向き」なので、レビューで確認
- **④ 多源性心房頻拍**：LITFL（MAT）「Irregularly irregular rhythm with varying PP, PR and RR intervals」「At least 3 distinct P-wave morphologies in the same lead」「Most commonly seen in patients with severe COPD or congestive heart failure」「Tends to resolve following treatment of the underlying disorder」 → 画面「→ まず患者さん」
- **⑤ 心房細動（速い）**：LITFL（Atrial fibrillation）「Irregularly irregular rhythm」「No P waves」「Absence of an isoelectric baseline」「AF is often described as having ‘rapid ventricular response’ once the ventricular rate is > 100 bpm」
- **⑥ 心房粗動（2:1）**：LITFL（Atrial flutter）「“Saw-tooth” pattern of inverted flutter waves in leads II, III, aVF」「The most common AV ratio is 2:1, resulting in a ventricular rate of ~150 bpm」「Narrow complex tachycardia at 150 bpm (range 130-170)? Yes -> Suspect flutter!」
- **⑦ PSVT（房室結節リエントリー）**：LITFL（SVT）「Regular tachycardia ~140-280 bpm」「P waves are often hidden – being embedded in the QRS complexes」「Pseudo S waves may be seen in leads II, III or aVF」
- **⑧ 始まり方（PSVTは突然・洞頻脈は少しずつ）**：LITFL（SVT）「Paroxysmal SVT (pSVT) describes an SVT with abrupt onset and offset」「if a premature atrial contraction (PAC) arrives while the fast pathway is still refractory, the electrical impulse will be directed solely down the slow pathway」（きっかけのPACは遅い道を通るので PR が長い）。LITFL（PAC）「a PAC may be the trigger for the onset of a re-entry tachyarrhythmia — e.g. Atrial fibrillation, atrial flutter, AVNRT, AVRT」。（「洞頻脈は少しずつ速くなる・遅くなる」ことは LITFL の本文に書いていない。一般的な説明として使い、レビューで確認）
- **⑨ 房室回帰性頻拍（順方向性）**：LITFL（AVRT）「In orthodromic AVRT, anterograde conduction is via the AV node, producing a regular narrow complex rhythm」「Retrograde P waves are usually visible, with a long RP interval」「In AVRT, retrograde P waves occur later, with a long RP interval > 70 msec」「Rate usually 200-300 bpm」
- **⑩ 接合部頻拍**：LITFL（Accelerated junctional rhythm）「Junctional Tachycardia: > 100 bpm」「Retrograde P waves may be present and can appear before, during or after the QRS complex. They are usually inverted in inferior leads」「Short PR interval (< 120 ms) indicates a junctional rather than atrial focus」。原因の例「Digoxin toxicity (= the classic cause of AJR)」
- **まとめ**：LITFL（SVT）「SVTs can be classified based on: Site of origin (atria or AV node) or; Regularity (regular or irregular)」（箇条書きをつないだ）→「規則正しいか、P波はどこか」
- **キャプションの「急変として対応」**：LITFL（SVT）の症状「Presyncope or syncope due to a transient fall in blood pressure」「Chest pain」「Dyspnoea」、LITFL（AVRT）「patients that are unstable due to this rhythm require urgent DC cardioversion」

## 専門医レビュー（2026-10-06、10パターン版）

- 要修正なし。推奨4点を反映した。⑧の「突然／少しずつ」は LITFL の文言がなくてもよい、とのこと
- 【推奨→直した】③ 心房頻拍：画面のひとことと台本を「形のちがうP波」→「いつもと違うP波」に（④ MAT の「P波の形が3種類以上」とまぎれないように。1種類の、ふだんと違うP波）
- 【推奨→直した】④ 多源性心房頻拍：台本を「P波の形が3種類以上で、不規則。多源性心房頻拍。」に（不規則であることも声で言う）
- 【推奨→直した】⑤ 心房細動：キャプションに「（※実際のモニターの心拍数は平均値が出るため、不規則な脈でも動画ほど毎拍は激しく変わりません。波形の間隔のバラつきに注目してください）」を足した（カウンターは拍ごとの値なので）
- 【推奨→直した】⑨ 房室回帰性頻拍：逆行性P波をQRSに近づけ、short RP の頻拍に。RP（QRSの始まり → Pの始まり）112ms、QRSの終わりから 26ms 後にPが始まる（目標 100〜140ms・20〜50ms）。200/分のまま。P波は細め（σ 16ms）にして、QRSのすぐあとの切れこみとして見えるようにした

## 専門医レビュー（2026-10-07、Claude）

AI専門医（作った担当とは別の Claude エージェント）のレビュー。全文は `review_result_1007.md`。波形・名前・ひとこと・台本に医学的な誤りはなし。
- 【要修正→直した】背景のマス目を心電図用紙と同じにした（小さいマス 14px＝0.04秒・0.1mV、大きいマス 70px＝0.2秒・0.5mV。波形は 1mm＝14px のまま）。前は大きいマス1つが0.45秒で、「300÷大きいマス」で数えると心拍数をまちがえるため。中部の帯の基線が太い線に乗るようにした
- 【推奨→直した】① 台本を「どの拍にも、ふつうのP波。洞頻脈。」に（「P波がある」だけだと③⑩にもあてはまる）
- 【推奨→直した】⑧ 画面のひとこと「突然はPSVT、少しずつは洞頻脈が多い」、台本「…少しずつ変わるなら、洞頻脈が多い。」（自動能の心房頻拍・接合部頻拍も少しずつ変わることがあるので、言い切らない）。
  洞調律が少しずつ変わるところで、カウンターの下に小さく「別の場面の例・実際はもっとゆっくり」（PSVTの続きではないこと、実際の速さ）
- 【推奨→直した】④⑤ のあいだ、カウンターの下に小さく「1拍ごとの値（モニターは平均）」
- 【推奨→直した】② T波の肩のP波のこぶを見やすく：レビューの案は「P波の頂点を前のRから 0.28→0.30秒」だが、150/分ではPRが約0.115秒に短くなるので、
  P波は動かさず（PR 132ms・150/分のまま）、T波の頂点を 0.215→0.195秒に早めて、T波とP波の間を同じだけ（0.02秒）広げた
- 【推奨→直した】最後の画面を「幅の狭い速い脈は、この10パターン」に
- 【推奨→直した】キャプション：「まず患者さん」「12誘導で確認」にも「医師に報告」、「迷ったら心房細動と考えて報告」、PSVTの中身と⑦⑨⑩の見分けにくさ、心房頻拍のP波の形、多源性心房頻拍（COPDの悪化や心不全）、幅の広いQRSは心室頻拍を先に、「どの頻脈でも…人を呼び、すぐ医師に知らせます」

## 声の指定

- 全体に落ち着いて、はっきり
- まとめの「規則正しいか、P波はどこか」は、ゆっくり
- 最後の「保存して、見返してね」は明るく
