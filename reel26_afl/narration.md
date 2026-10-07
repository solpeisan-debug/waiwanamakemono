# 第26弾 心房細動・心房粗動 まず覚えたい14パターン — ナレーション

第21弾と同じ作り（1パターン1文・声で3〜4秒）。数字は画面に出ているので、声では読み上げない（伝導比の「4対1」などは名前なので読む。⑫の「150」は見分けの目安なので例外として読む）。
「すぐ報告」は声では言わない（画面の赤い「→ すぐ報告」とキャプションで伝える）。危ないもの（⑨⑭）は声では「危険」、⑩は「失神の原因に」とだけ言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第21弾と同じ）。

---

## 秒数つき（録音 2026-10-07 ElevenLabs Ren – Smooth & Soothing を置いた位置）

元の録音 `out/vo/narration_orig.mp3`（78.8秒）を、声の高さを変えない atempo=1.2 で1.2倍速にした `out/vo/narration_raw.wav`（65.68秒）を使う。
`align_vo.py` で、無音（0.25秒以上）を手がかりに 28 かたまりへ切り分け、17文にまとめて下の秒数に置いた。継ぎ目はすべて無音の中。
文の中の息継ぎは 0.45秒まで詰めた。モニター音は声の下で最大 8dB 下げている。映像は 74.9秒。
Whisper（faster-whisper small）の書き起こしで、17文の順番と中身を確かめた（結果は下の「専門医レビュー」の最後）。

| 秒 | 文 |
|---|---|
| 0.10–4.30 | 心房細動と心房粗動。まず覚えたいのは、この14パターン。 |
| 4.90–8.13 | 洞調律から急にバラバラ。心房細動の始まり。 |
| 9.44–13.11 | P波がなく、R-Rがバラバラ。f波の粗い心房細動。 |
| 14.24–17.07 | 平らでも、R-Rがバラバラなら心房細動。 |
| 18.02–20.67 | 速くてバラバラ、頻脈性の心房細動。 |
| 21.52–24.13 | 遅くてバラバラ、徐脈性の心房細動。 |
| 25.12–28.85 | 長い間隔のあと、早く来た拍が幅広い。アシュマン現象。 |
| 29.92–33.52 | 全部の拍が幅広い。脚ブロックを伴う心房細動。 |
| 34.92–38.54 | f波なのに規則正しく遅い。完全房室ブロックを疑う。 |
| 39.92–43.86 | 幅広く速くバラバラ。WPWの心房細動は危険。 |
| 45.14–49.98 | 細動が止まったあとの長い休みは、失神の原因に。徐脈頻脈症候群。 |
| 52.20–55.03 | のこぎり状のF波。4対1の心房粗動。 |
| 56.20–59.47 | 150で規則正しければ、2対1の粗動を疑う。 |
| 60.60–63.15 | 伝導比が変わる心房粗動は、細動に似る。 |
| 64.40–67.16 | F波が全部伝わる1対1は、とても危険。 |
| 67.60–71.29 | のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動。 |
| 71.59–72.96 | 保存して、見返してね |

- 各パターンの長さ（秒）：①4.64 ②4.80 ③3.78 ④3.50 ⑤3.60 ⑥4.80 ⑦5.00 ⑧5.00 ⑨5.22 ⑩7.06 ⑪4.00 ⑫4.40 ⑬3.80 ⑭3.60
  （声の長さ＋0.75秒以上で、拍の並びがくずれない位置。⑩は休みのタイマーが 3.2秒で止まるところまで見せるため、声のあと約1.6秒あく）
- 冒頭の1文が 4.20秒（0.10〜4.30秒）なので、①が入るまで（T_TITLE）を 4.9 → 4.6秒にした
- 最後：まとめの声が終わってから（一覧がそろって 3.4秒後）、上の行が「何個わかった？コメントで教えてね」に入れかわる

---

## 読み上げ用（ElevenLabs に貼った確定版）

心房細動と心房粗動。まず覚えたいのは、この14パターン。

洞調律から急にバラバラ。心房細動の始まり。
P波がなく、R-Rがバラバラ。f波の粗い心房細動。
平らでも、R-Rがバラバラなら心房細動。
速くてバラバラ、頻脈性の心房細動。
遅くてバラバラ、徐脈性の心房細動。

長い間隔のあと、早く来た拍が幅広い。アシュマン現象。
全部の拍が幅広い。脚ブロックを伴う心房細動。
f波なのに規則正しく遅い。完全房室ブロックを疑う。
幅広く速くバラバラ。WPWの心房細動は危険。

細動が止まったあとの長い休みは、失神の原因に。徐脈頻脈症候群。

のこぎり状のF波。4対1の心房粗動。
150で規則正しければ、2対1の粗動を疑う。
伝導比が変わる心房粗動は、細動に似る。
F波が全部伝わる1対1は、とても危険。

のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動。
保存して、見返してね

- 読み方：「150」は「ひゃくごじゅう」、「R-R」は「アールアール」、「f波」「F波」は「エフ波」、「P波」は「ピーは」、「WPW」は「ダブリューピーダブリュー」、「4対1」は「よんたいいち」、「1対1」は「いったいいち」、「徐脈頻脈症候群」は「じょみゃくひんみゃくしょうこうぐん」
- 2026-10-06：12 → 14パターンに作り直し（①心房細動の始まり、⑩徐脈頻脈症候群を足した）
- 2026-10-07：専門医レビュー（Claude）を受けて ①（名前）・③・⑩・まとめ を直した確定版（下の「専門医レビュー」）
- 画面の最後に「何個わかった？コメントで教えてね」を出す（声では言わない。最後の文は「保存して、見返してね」のまま）

---

## 並び（画面の色）

- 心房細動のはじまり・f波・心拍数（①〜⑤、水色）：始まり → f波が粗い → f波が細かい → 頻脈性 → 徐脈性
- 心房細動でQRSの形・リズムが変わる（⑥〜⑨、黄）：アシュマン現象 → 脚ブロック → 完全房室ブロック（R-Rが規則的）→ WPW
- 止まるとき（⑩、赤みの橙）：徐脈頻脈症候群（止まったあとの長い休み）
- 心房粗動（⑪〜⑭、桃）：4:1（F波がいちばん見やすい）→ 2:1 → 伝導比が変わる → 1:1
- 色の文字（看護師の動き）：緑「→ 初めてなら報告」①②③⑪、橙「→ 脈拍と血圧も確認」④⑤⑫、紫「→ 12誘導で確認」⑥⑦⑬、赤「→ すぐ報告」⑧⑨⑩⑭

## この回だけの見せ方

- R-R のものさし：中部の波形の下に、拍と拍のあいだの長さを横棒で出す（棒の長さ＝モデルの R の時刻の差、350px＝1秒）。
  心房細動は棒がバラバラ、心房粗動（伝導比が一定）は棒がそろう、⑬は 0.2秒の倍数の長さが混じる、⑩は休みのところで1本だけとても長い。声ではふれない（画面で見せる）
- 休みのタイマー（⑩）：休みが 1.1秒ぶん画面に入ったところで右に出て「休み 1.1秒 → … → 3.2秒」と数え上がり、次の洞調律の拍が入ったところで止まって、波形と一緒に左へ流れる（値はモデルの休みの長さ）。
  ものさしの休みの区間は、のびていく点線（タイマーと同じ動き）
- 冒頭0〜2秒：「細動？粗動？／見分けられる？」（2行・76px。出ているあいだは「モニター心電図で見分ける」を消す）。最後：「保存して見返してね」と「何個わかった？コメントで教えてね」
- ものさしは、両端の拍が見えている区間だけ棒を描く（端の半端な棒は描かない）。①は洞調律の区間を暗くして「そろう → 急にバラバラ」を見せる

## 言い回しの注意（LITFL本文で確認）

- **① 心房細動の始まり**：LITFL の分類では「発作性」は自然に止まったかどうかで決まる（始まった瞬間には分からない）ので、名前は「心房細動の始まり」にした（2026-10-07）。LITFL（Atrial Fibrillation）「it requires an initiating event (focal atrial activity / PACs) and substrate for maintenance」「Paroxysmal AF – Self terminating episode < 7 days」。
  洞調律3拍のあと、直前のT波の終わりに早いP'（PAC）→ そこから R-R がバラバラ、と描いた
- **② ③ f波・見分けのポイント**：LITFL（Atrial Fibrillation）「Irregularly irregular rhythm」「No P waves」「Fibrillatory waves may be present and can be either fine (amplitude < 0.5mm) or coarse (amplitude > 0.5mm)」「Fibrillatory waves may mimic P waves leading to misdiagnosis」。
  ③は R-R の不規則だけでは決めない（洞不整脈・PACの頻発・多源性心房頻拍でも R-R はバラバラ）。「P波がない」を一緒に言う（画面「P波なし・基線は平ら。R-Rで判断」、台本「平らでも、R-Rがバラバラなら心房細動」）。
  LITFL（Multifocal Atrial Tachycardia）「Irregularly irregular rhythm with varying PP, PR and RR intervals」
- **④ 頻脈性**：LITFL（Atrial Fibrillation）「AF is often described as having 'rapid ventricular response' once the ventricular rate is > 100 bpm」「AF is most commonly associated with a ventricular rate ~ 110 – 160」
- **⑤ 徐脈性**：LITFL（Atrial Fibrillation）「'Slow' AF is a term often used to describe AF with a ventricular rate < 60 bpm」「Causes of 'slow' AF include hypothermia, digoxin toxicity, and medications」
- **⑥ アシュマン現象**：LITFL（Ashman Phenomenon）「aberrant ventricular conduction, usually of RBBB morphology, which follows a short R-R interval and preceding relatively prolonged R-R interval」「Clinically on its own is asymptomatic and does not require any specific treatment」。
  声は「長い間隔のあと、早く来た拍が幅広い」（長い R-R のあと、短い R-R で来た拍）
- **⑦ 脚ブロック**：LITFL（Atrial Fibrillation）「QRS complexes usually < 120ms, unless pre-existing bundle branch block, accessory pathway, or rate-related aberrant conduction」。形は LITFL（RBBB）「QRS duration > 120ms」「Wide, slurred S wave in lateral leads」をもとに、II誘導で幅の広いS波として描いた
- **⑧ 完全房室ブロック**：LITFL（Digoxin Toxicity）「Regularised AF = AF with complete heart block and a junctional or ventricular escape rhythm」「Coarse atrial fibrillation with 3rd degree AV block and a junctional escape rhythm」。
  LITFL（3rd degree AV block）「at high risk of ventricular standstill and sudden cardiac death」。声は「疑う」までにした（モニターだけでは確定しない）
- **⑨ WPW**：LITFL（Atrial fibrillation/flutter in pre-excitation）「Rate > 200 bpm」「Irregular rhythm, with extremely high rates in some places — up to 300 bpm」「Wide QRS complexes」「Subtle beat-to-beat variation in QRS morphology」「Axis remains stable, unlike Polymorphic VT」
  「Ensuing rapid ventricular rates may result in degeneration to ventricular tachycardia (VT) or ventricular fibrillation (VF)」「The administration of AV nodal blocking drugs … may precipitate ventricular arrhythmias and cardiac arrest」
- **⑩ 徐脈頻脈症候群**：LITFL（Sinus Node Dysfunction (Sick Sinus Syndrome)）「Bradycardia – tachycardia syndrome: Alternating bradycardia with paroxysmal tachycardia, often supraventricular in origin」
  「On cessation of tachyarrhythmia may be a period of delayed sinus recovery e.g. sinus pause or exit block」「If significant this period of delayed recovery may result in syncope」「Sinus Arrest — pause > 3 seconds」。
  心房細動（約130/分）が止まる → 3.2秒の休み（f波もP波もない）→ 遅い洞調律（60/分）、と描いた
- **⑪〜⑭ 心房粗動**：LITFL（Atrial Flutter）「Regular atrial activity at ~300 bpm」「'Saw-tooth' pattern of inverted flutter waves in leads II, III, aVF」「2:1 block = 150 bpm」「4:1 block = 75 bpm」
  - ⑫：「Suspect atrial flutter with 2:1 block whenever there is a regular narrow-complex tachycardia at 150 bpm」「Flutter waves are often very difficult to see when 2:1 block is present」。
    画面の波形ではF波が見えているので、ひとことは「F波が隠れる」ではなく「150/分で規則的なら粗動を疑う」にした（2026-10-05 検査役の指摘）
  - ⑬：「Variable AV conduction ratio — The ventricular response is irregular and may mimic atrial fibrillation (AF)」「the R-R intervals will be multiples of the P-P interval」
  - ⑭：「Atrial flutter with 1:1 conduction is associated with severe haemodynamic instability and progression to ventricular fibrillation」（例は 250〜300/分の幅の狭い頻拍）
- **まとめ**：LITFL（Atrial Flutter）「In contrast, atrial fibrillation will be completely irregular, with no patterns to be discerned within the R-R intervals」。
  ⑬（伝導比が変わる粗動）も R-R はバラバラなので、のこぎりを先に探す順にした（「のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動」、画面「のこぎりは粗動、R-Rバラバラは細動」）

## 声の指定

- 全体に落ち着いて、はっきり
- ⑨⑭の「危険」、⑩の「失神の原因に」は少し強く
- まとめの「のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動」は、ゆっくり（「細動」「粗動」を聞き分けやすく）
- 最後の「保存して、見返してね」は明るく

---

## 専門医レビュー（2026-10-07、Claude）

AI専門医（作った担当とは別のエージェント。読むだけ）のレビュー。全文は `review_result_1007.md`。**要修正（医学的な誤り）はなし**。推奨を次のように入れた。

- 【推奨・優先度高→直した】背景の方眼が心電図の目盛りと合っていなかった（太い線 157.5px＝0.45秒）。
  `grid()` を細い線 14px（1mm）・太い線 70px（5mm＝0.2秒）にした（シリーズ共通の直し）。太い線が画面の中央と基線を通る。線は前より薄くして、目立たなさをそろえた
- 【推奨→直した】③：画面「P波なし・基線は平ら。R-Rで判断」、台本「平らでも、R-Rがバラバラなら心房細動。」（R-R 不規則だけで決めない）
- 【推奨→直した】⑩：台本「細動が止まったあとの長い休みは、失神の原因に。」（何が止まったかを言う）
- 【推奨→直した】まとめ：台本「のこぎりなら粗動。P波がなく、R-Rがバラバラなら細動。」、画面「のこぎりは粗動、R-Rバラバラは細動」（⑬を細動と読まないよう、のこぎりを先に）
- 【推奨（軽い）→直した】①の名前「発作性心房細動の始まり」→「心房細動の始まり」（発作性かどうかは、あとで自然に止まったかで決まる）
- 【推奨→直した】⑥：長い R-R の棒が左端で消えるコマがあった。⑥だけ、左端で切れる棒も端まで描き、長い R-R と短い R-R の棒の下に「長い」「短い」を出す（区間の後半 約2.1秒、両方の名札が見える）
- 【推奨（軽い）→直した】⑨：いちばん細い拍の QRS 幅を 119 → 122ms に（幅の係数 0.90 → 0.92）
- 【推奨→キャプションで直した】橙「→ 脈拍と血圧も確認」が「報告しなくてよい」と読まれるおそれ → 🆕「どのパターンでも、初めて見つけた…は医師へ報告。血圧低下・意識の変化・胸痛・息切れがあれば、すぐ報告」
- 【推奨→キャプションに足した】⑧ ジギタリス中毒、⑨「心室細動に移ることがある」、⑬「棒の長さが数種類にかぎられる」、⑭「F波はほとんど見えず、幅広くなることも」、「P波が見えるときは心房細動ではないことがある」。※参考に Multifocal Atrial Tachycardia を足した
- 【任意→見送り】⑫「幅が狭く150/分で規則的なら粗動を疑う」は、ひとこと＋色の文字が上限 760px に入らないので今のまま（キャプションの「幅の狭い」で補う）。⑨「形も少しずつ違う」、橙の文字の言いかえも今のまま
- ③のひとことは 743px で、字が 32 → 31px に1px だけ縮む
- 書き起こし（faster-whisper small、声入りの通常版 `out/reel26_afl_vo.mp4` の音から）：17文とも台本どおりの順・置いた秒数どおり。
  「心房細動」→「シンボウサイド」、「細動が止まった」→「サイドが止まった」、「拍」→「箱」、「脚ブロック」→「足ブロック」、「伝導比」→「電動筆」、「見返してね」→「2回してね」など、
  かなの聞き取りちがいのみ（第28弾と同じ。耳で聞くと台本どおり）
