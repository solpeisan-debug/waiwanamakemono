# 第20弾 ノイズ（アーチファクト） まず覚えたい12パターン — ナレーション

第17〜19弾と同じ作り。数字は画面に出ているので、声では読み上げない。「すぐ報告」は声では言わない（画面とキャプションで伝える）。
名前が出てから約0.5秒後に話し始め、次のパターンの名前が出る前に言い終える。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。

---

## 読み上げ用（ElevenLabs に貼る）

ノイズで、まず覚えたいのは、この12パターン。

体が動くと、基線が大きく乱れます。体動。
力が入ると、細かいギザギザ。筋電図。
ふるえで、心房細動に見えることも。でも、R-Rは、一定です。
寒さのふるえ、シバリング。
呼吸に合わせて、基線がゆっくり揺れる。
細かく、規則正しいギザギザ。交流障害。

電極の接触が悪いと、基線が飛びます。
電極が外れると、まっすぐの線。あわてずに、まず、患者さんを見て。
電極の付けまちがいで、波形がまるごと逆さまに。
歯みがきで、心室頻拍のように見えることも。よく見ると、ふつうのQRSが隠れています。
リード線の断線で、心室細動のように見えることも。ここにも、ふつうのQRSが見えますね。
本物の心室頻拍では、ふつうのQRSが消えます。

ノイズの中に、同じ間隔のQRSが見えたら、ノイズ。まず、患者さんを見てください。
保存して、見返してね

---

## 言い回しの注意（LITFL本文で確認。LITFL以外は出典を書いた）

- **① 体動**：LITFL（ECG Motion Artefacts）「A non-compliant, mobile, talkative patient (= the most common cause)」
- **② 筋電図**：骨格筋の電気活動が混ざる（Mondal S et al. World J Cardiol 2026：skeletal muscle tremor）
- **③ ふるえ**：LITFL の例（パーキンソン病の振戦）「The irregular baseline in this ECG gives the appearance of atrial fibrillation」。実際は洞調律でP波も見える。画面は R-R 一定で描く
- **④ シバリング**：LITFL「Hypothermia (shivering)」。Mondal 2026「shivering that might be mistaken for atrial flutter or VT」
- **⑤ 呼吸の揺れ**：Mondal 2026「Baseline wander from respiration」
- **⑥ 交流障害**：Mondal 2026「Power-line interference at 50 Hz … or 60 Hz … appearing as regular sawtooth waves」（日本は東日本50Hz・西日本60Hz）
- **⑦ 接触不良**：Mondal 2026「Loose electrode contact producing intermittent baseline jumps or flatlines」
- **⑧ 電極外れ**：まっすぐの線は心静止に見える。だから「まず患者さんを見る」（Mondal 2026「Always check the patient … second, check the electrodes」）
- **⑨ 付けまちがい**：LITFL（Limb Lead Reversal）RA/LL の入れかわりで「Lead II becomes inverted」「Leads I, II, III and aVF are all completely inverted (P wave, QRS complex and T wave)」
- **⑩ 偽VT（歯みがき）**：Knight BP et al. N Engl J Med 1999;341:1270-4（偽VTで不要な治療を受けた12例）。見分け方：ノイズの中に、ふつうのQRSが洞調律の間隔で見える
- **⑪ 偽VF（断線）**：Mondal 2026「Broken lead wires mimicking ventricular fibrillation」「A conscious, talking patient is not in VF」「genuine P/QRS/T complexes often march through the noise with regular intervals」
- **⑫ 本物のVT**：比べるために入れた。ノイズとちがい、幅の広いQRSが続いて、ふつうのQRSが見えなくなる

## 声の指定

- ①〜⑥は淡々と
- ⑧「まず、患者さんを見て」と、まとめの「まず、患者さんを見てください」は、はっきり
- 最後の「保存して、見返してね」は明るく

---

## 専門医レビュー（2026-10-04）

- 要修正はなし。①②④⑤⑥⑦⑨⑫、12パターンの選び方、キャプションの「すぐ報告」の範囲は OK
- 【推奨→直した】③：「でも、R-Rは、一定です」（前半との対比）
- 【推奨→直した】⑧：「あわてずに、まず、患者さんを見て」
- 【推奨→直した】⑩：「よく見ると、ふつうのQRSが隠れています」／⑪：「ここにも、ふつうのQRSが見えますね」
- 【推奨→採らなかった】キャプションの出典「Mondal S et al. World J Cardiol 2026」を2024に、という指摘：論文のページで確認すると、受付 2025年11月7日・公開 2026年3月26日（Vol.18 No.3、DOI 10.4330/wjc.v18.i3.116299）。2026が正しいので、そのままにした
