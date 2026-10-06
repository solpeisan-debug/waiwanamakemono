# 第26弾 心房細動・心房粗動 まず覚えたい14パターン — ナレーション

第21弾と同じ作り（1パターン1文・声で3〜4秒）。数字は画面に出ているので、声では読み上げない（伝導比の「4対1」などは名前なので読む。⑫の「150」は見分けの目安なので例外として読む）。
「すぐ報告」は声では言わない（画面の赤い「→ すぐ報告」とキャプションで伝える）。危ないもの（⑨⑭）は声では「危険」、⑩は「失神の原因に」とだけ言う。
録音したら `align_vo.py` で文に切り分け、紹介の時間に置き直す。各パターンの長さは、声に合わせて詰める。
声は Ren – Smooth & Soothing（第21弾と同じ）。

---

## 読み上げ用（ElevenLabs に貼る）

心房細動と心房粗動。まず覚えたいのは、この14パターン。

洞調律から急にバラバラ。発作性心房細動の始まり。
P波がなく、R-Rがバラバラ。f波の粗い心房細動。
平らに見えても、f波の細かい心房細動。
速くてバラバラ、頻脈性の心房細動。
遅くてバラバラ、徐脈性の心房細動。

長い間隔のあと、早く来た拍が幅広い。アシュマン現象。
全部の拍が幅広い。脚ブロックを伴う心房細動。
f波なのに規則正しく遅い。完全房室ブロックを疑う。
幅広く速くバラバラ。WPWの心房細動は危険。

止まったあとの長い休みは、失神の原因に。徐脈頻脈症候群。

のこぎり状のF波。4対1の心房粗動。
150で規則正しければ、2対1の粗動を疑う。
伝導比が変わる心房粗動は、細動に似る。
F波が全部伝わる1対1は、とても危険。

R-Rがバラバラなら細動、のこぎりなら粗動。
保存して、見返してね

- 読み方：「150」は「ひゃくごじゅう」、「R-R」は「アールアール」、「f波」「F波」は「エフ波」、「WPW」は「ダブリューピーダブリュー」、「4対1」は「よんたいいち」、「1対1」は「いったいいち」、「徐脈頻脈症候群」は「じょみゃくひんみゃくしょうこうぐん」
- 2026-10-06：12 → 14パターンに作り直し（①発作性心房細動の始まり、⑩徐脈頻脈症候群を足した）。録音前の版（区間の長さは仮）
- 画面の最後は、一覧がそろって3秒後に「R-Rバラバラは細動、のこぎりは粗動」→「何個わかった？コメントで教えてね」（黄）に入れかわる（声では言わない。最後の文は「保存して、見返してね」のまま）

## 区間の長さ（仮）と、声の長さの目安

各パターンの区間（秒）：①5.72 ②5.42 ③4.40 ④3.88 ⑤4.60 ⑥4.80 ⑦5.00 ⑧5.00 ⑨5.22 ⑩7.06 ⑪4.80 ⑫4.80 ⑬4.60 ⑭4.20（映像 81.2秒）。
声の長さの目安（画面に出ている時間 − 0.75秒）：①4.6 ②4.7 ③3.6 ④3.1 ⑤3.8 ⑥4.0 ⑦4.2 ⑧4.2 ⑨4.4 ⑩6.3 ⑪4.0 ⑫4.0 ⑬3.8 ⑭3.4 秒。
①は冒頭の一文のあとなので、画面に出ている時間が区間より約0.35秒短い（5.37秒）。
⑩は「休み」が画面に入ってきて秒数が数え上がるのを見せるため、長め（7.06秒）。声は休みのあいだに言い終わる。
区間は、拍の並びがくずれない位置（最後の拍からの間隔が、そのパターンの R-R になる位置）で切っている。録音後に詰めるときも同じ考え方で。

---

## 並び（画面の色）

- 心房細動のはじまり・f波・心拍数（①〜⑤、水色）：発作性の始まり → f波が粗い → f波が細かい → 頻脈性 → 徐脈性
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

- **① 発作性心房細動の始まり**：LITFL（Atrial Fibrillation）「it requires an initiating event (focal atrial activity / PACs) and substrate for maintenance」「Paroxysmal AF – Self terminating episode < 7 days」。
  洞調律3拍のあと、直前のT波の終わりに早いP'（PAC）→ そこから R-R がバラバラ、と描いた
- **② ③ f波・見分けのポイント**：LITFL（Atrial Fibrillation）「Irregularly irregular rhythm」「No P waves」「Fibrillatory waves may be present and can be either fine (amplitude < 0.5mm) or coarse (amplitude > 0.5mm)」「Fibrillatory waves may mimic P waves leading to misdiagnosis」。
  ③は「平らに見えても」心房細動、と R-R の不規則で判断する（画面「基線はほぼ平ら。R-Rで判断」）
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
- **まとめ**：LITFL（Atrial Flutter）「In contrast, atrial fibrillation will be completely irregular, with no patterns to be discerned within the R-R intervals」

## 声の指定

- 全体に落ち着いて、はっきり
- ⑨⑭の「危険」、⑩の「失神の原因に」は少し強く
- まとめの「R-Rがバラバラなら細動、のこぎりなら粗動」は、ゆっくり（「細動」「粗動」を聞き分けやすく）
- 最後の「保存して、見返してね」は明るく
