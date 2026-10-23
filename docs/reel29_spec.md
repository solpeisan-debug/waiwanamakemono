# 第29弾 心筋梗塞の場所 ― 設計（2026-10-23 試作・静止画まで）

- フォルダ：`reel29_mi/`（`make_reel29.py`。`--check`・`--still T`・`--sheet`）
- 状態：**設計と静止画の試作まで**。動画の書き出し・録音はまだ。秒数は仮の値で、録音したら声に合わせて決め直す
- 1080×1920・60fps。全体 **約73秒**（6パターン × 約9.3秒＋冒頭9.2秒＋まとめ8.8秒）

## 1. 参考リールより「よりよく」したところ

| 参考リールの弱いところ | この回 |
|---|---|
| 4誘導だけで、パターンごとに誘導がばらばら | **実際の12誘導の並び（3段×4列）をずっと出したまま**、ST上昇の誘導だけ ST を赤く塗る。鏡像の ST低下は青。「となり合う誘導がまとまって光る」が見える |
| 心臓の絵が細かすぎて壁が読みにくい | **左室の輪切り＋右室の三日月**の図。中隔・前壁・側壁・後壁・下壁・右室の6か所だけ。まわりに「その壁を見ている誘導」の名前。冠動脈は3色の線（LAD 橙・LCx 紫・RCA 青緑） |
| 看護師が何をするかがない | パターンごとに**看護の1行「→ 〜」**。冒頭に「ST上昇を見たら → 12誘導・すぐ報告」（赤） |
| 速い（28秒） | 1パターン 約9.3秒。1誘導に1拍だけ。紙と同じ目盛り（拡大なし） |
| 追加の誘導がどこにあるか分からない | 右室・後壁のときだけ、**4段めに V4R・V7〜V9 が出る**（「← 右胸に貼る」「背中に貼る →」） |

## 2. パターン表（LITFL で確かめた内容）

| # | 場所 | ST上昇（赤） | 鏡像の ST低下（青） | 責任血管（画面） | 看護の1行（画面） |
|---|---|---|---|---|---|
| ① | 前壁中隔 | V1〜V4 | なし（I・aVL が上がらないときは出にくい） | LAD（左前下行枝） | → 致死性不整脈（VF）に注意 |
| ② | 広範囲前壁 | V1〜V6・I・aVL | III・aVF（小さい） | LADの根もと | → 心不全・ショックに注意 |
| ③ | 側壁 | I・aVL・V5・V6 | III・aVF | LCx（回旋枝）など | → 上昇が小さくても見のがさない |
| ④ | 下壁 | II・III・aVF（III＞II） | aVL（と I） | RCA（右冠動脈）が多い | → 徐脈・房室ブロックに注意。V4Rもとる |
| ⑤ | 右室（＋下壁） | II・III・aVF・V1・**V4R** | aVL・I | RCAの根もと | → 血圧低下に注意 |
| ⑥ | 後壁 | **V7〜V9**（背中の誘導） | V1〜V3（水平な ST低下＋高く幅のある R＋上向きの T） | RCA か LCx | → V7〜V9 を追加でとる |

共通の赤い字（冒頭の「見かた」で1回）：**ST上昇を見たら → 12誘導・すぐ報告**（ナレーションでは言わない）

### 「中隔」を独立させず「前壁中隔」にした理由
- LITFL Anterior STEMI は名前の付け方を Septal＝V1–2、Anterior＝V2–5、**Anteroseptal＝V1–4** としたうえで、
  「there is often a poor correlation between ECG features and precise infarct location」と書いている（誘導で細かく分けても、実際の場所とはずれやすい）
- LITFL ECG Lead positioning の誘導の分け方は **Inferior (II, III, aVF)／Lateral (I, aVL, V5, V6)／Anterior (V1–4)** の3つ
- 看護師が「まず覚える」には、V1〜V4 をひとまとまりにするほうが分かりやすく、日本の教科書の「前壁中隔梗塞」とも合う
- まとめの画面では、V1・V2＝中隔、V3・V4＝前壁 と分けて書く（LITFL の Septal leads / Anterior leads）
- → 6パターン（参考の7から「中隔」と「前壁」を1つに）。**でんさんに確認したい点①**

### 画面の波形の値（mV。`make_reel29.py` の `NORMAL`・`PATTERNS`）
- 正常の形：誘導ごとに P・q・R・S・T を典型の形に（aVR は下向き、V1 は rS、V4〜V6 で R が高くなる）。3段に並べてぶつからない低めの高さ
- ST上昇：0.15〜0.30mV（1.5〜3mm）。前胸部は T も少し高く（超急性期の T）。下壁は III＞II（RCA）
- 鏡像：aVL −0.20mV＋T 陰転、III −0.10〜−0.14mV
- 後壁：V1〜V3 で ST −0.14〜−0.22mV（水平）、R を高く幅広く（V2 で R/S＞1）、T は上向き。V7〜V9 は ＋0.10〜0.12mV（LITFL：0.5mm で診断）
- 右室：V4R ＋0.15mV、V1 ＋0.12mV
- Q波は出さない（急性期の形として。キャプションにも書かない）

## 3. ナレーション台本（Ren・1.2倍。「すぐ報告」は言わない）

| 場面 | 文 | 見込み |
|---|---|---|
| 冒頭（0.1秒〜） | 心筋梗塞の場所は、上がる誘導でわかる。まず6パターン。 | 約4.2秒 |
| 見かた（4.6秒〜） | となり合う誘導が、まとまって上がる。反対側は、鏡のように下がる。 | 約4.3秒 |
| ① | V1からV4が上がれば、前壁中隔。左前下行枝、LADです。 | 約4.8秒 |
| ② | V1からV6、IとaVLまで上がれば、広範囲前壁。LADの根もとです。 | 約5.3秒 |
| ③ | IとaVL、V5とV6なら、側壁。回旋枝、LCxなどです。 | 約4.6秒 |
| ④ | II、III、aVFなら、下壁。多くは右冠動脈。aVLは鏡のように下がります。 | 約5.6秒 |
| ⑤ | 下壁に加えて、右胸のV4Rも上がれば、右室。血圧低下に注意。 | 約5.0秒 |
| ⑥ | V1からV3が下がってRが高いときは、背中のV7からV9をとる。上がれば、後壁。 | 約5.8秒 |
| まとめ | 上がる誘導で、場所と血管がわかる。 | 約2.8秒 |
| 保存 | 保存して、見返してね。 | 約1.4秒 |

- 読み：I＝いち、II＝に、III＝さん、aVF＝エーブイエフ、V4R＝ブイよんアール、LCx＝エルシーエックス（録音時に ElevenLabs の読みを確かめる。ローマ数字は「いち・に・さん」とかなで渡す）
- 名前が出てから 0.55秒で話し始める。1パターンの「形がそのまま」の長さは 7.6秒（声 6.7秒まで入る）

## 4. タイムライン（`--check` の値。仮）

| 秒 | 中身 |
|---|---|
| 0.0〜2.4 | 問いかけ「ST上昇、心臓のどこ？」（見出しの位置・黄 66px） |
| 0.7〜3.65 | フック：12誘導と輪切りが、その場で 前壁中隔 → 下壁 → 側壁 と光る（0.3秒で変わる・0.55秒そのまま）。名前は「前壁中隔？」など小さく |
| 2.4〜 | 見出し「心筋梗塞の場所 6 パターン」 |
| 4.6〜9.2 | 見かた：「となり合う誘導が、まとまって上がる」＋赤「ST上昇を見たら → 12誘導・すぐ報告」。4段めに凡例「赤＝ST上昇　青＝反対側のST低下（鏡像）」 |
| 9.90–17.50 | ① 前壁中隔 |
| 19.20–26.80 | ② 広範囲前壁 |
| 28.50–36.10 | ③ 側壁 |
| 37.80–45.40 | ④ 下壁 |
| 45.40–46.40 | ④ → ⑤ は**直接**変わる（V4R の段が出て、V1・V4R が上がり、右室が赤くなる） |
| 46.40–54.00 | ⑤ 右室 |
| 55.70–63.30 | ⑥ 後壁（V7〜V9 の段。V4R の段は消える） |
| 63.30–64.30 | ⑥ → まとめ（ST がもどり、色分けが出る） |
| 64.30–72.30 | まとめ：12誘導の誘導名と輪切りを血管の色で塗り分け、各誘導に壁の名前。「上がる誘導で、場所と血管がわかる」→「保存して見返してね」→「何個わかった？コメントで教えてね」 |
| 72.30–73.05 | 冒頭の画面へもどる（ループ） |

- パターンの中の動き：灰色の正常から 0.7秒で形が変わる → 0.1秒後に名前 → 1.6秒後に看護の1行 → 7.6秒で名前が消える → 0.7秒で灰色の正常へ・0.3秒そのまま（「▶ 次の例」）→ 次へ
- つなぎ目のルール（2026-10-14）：別のパターンへは灰色の正常を通す。**例外は ④→⑤ だけ**（右室梗塞は下壁梗塞に加わって起こる：LITFL「RV infarction complicates up to 40% of inferior STEMIs (isolated RV infarction is extremely uncommon)」）。**でんさんに確認したい点③**
- 全体 73秒。目安の 75〜90秒より少し短いが、1パターン 9.3秒（目安 8〜9秒）を守った結果。録音後に声に合わせて伸び縮みする

## 5. 画面の配置（y 座標）

| y | もの |
|---|---|
| 300〜360 | 見出し（ベースライン 358、50px・「6」は 75px）／冒頭は問いかけ（cy 333） |
| 372〜1100 | 12誘導の紙：段の上端 372・段の間隔 182px（13mm）・基線 484／666／848、4段め（追加の誘導）の基線 1030。列は x 100／330／560／790（幅 230px＝0.657秒、1拍）。誘導名は各列の左上（1列めは x135＝安全域の内側）30px |
| 980 | 4段めが空いているとき：凡例（28px） |
| 990 | 「← 右胸に貼る」（2列め）／「背中に貼る →」（1列め） |
| 1039〜1104 | 透かし（cy 1062・中央・64px・太さ800・白16%）。4段めの基線の下（追加の誘導の ST は基線より上なので重ならない） |
| 1146 | パターンの名前（54px・白）＋責任血管（38px・血管の色） |
| 1206 | 看護の1行（36px・緑）／見かたの赤い字／まとめの「保存して見返してね」 |
| 1250〜1585 | 輪切り：左室の中心 (470, 1420)、内腔 62px・外側 112px、右室は中心を左へ 90px・半径 110・壁 24px。誘導名 27px（V1〜V4 上、I aVL 右上、V5 V6 右、V7〜V9 右下、II III aVF 下、V4R 左）。壁の名前 24px。血管の見本 x772（LAD・LCx・RCA） |
| 1558・1586 | 注記「※波形は一例」「※心臓は輪切りの模式図」（左下・22px） |

- 右下（x 900 以上・y 1100〜1600）には何も置かない。名前・看護の1行は幅 720px 以内（x 180〜900）
- 方眼は 1mm＝14px の正方形（25mm/秒・10mm/mV）。拡大していないので「※拡大表示」は付けない
- 輪切りの向き：CT と同じ「足もとから見た」向き（左が右室＝体の右、右が側壁＝体の左、上が前壁）。前胸部誘導（水平面）と四肢誘導（前額面）を1枚にまとめた模式図なので、注記で「模式図」と書く
- 後壁のとき：V1〜V3 から内腔を通って後壁へ、青い点線の矢印と「鏡像」（前から見た後壁は反対向きに写る）

## 6. キャプション案

```
ST上昇、心臓のどこ？12誘導で梗塞の場所がわかりますか？
@nurse_polarbearden📍他の投稿をチェック
---------------------------------------------------------
▶︎こんにちは、看護師でんです。

心筋梗塞は、ST上昇の誘導で「心臓のどこか」「どの血管か」の見当がつきます。
まず覚えたい6パターンをまとめました。

🔍見かた
となり合う誘導が、まとまって上がる → そこが梗塞の場所
反対側の誘導は、鏡のように下がる（鏡像）

① 前壁中隔 → V1〜V4／左前下行枝（LAD）
② 広範囲前壁 → V1〜V6・I・aVL／LADの根もと（近位）
③ 側壁 → I・aVL・V5・V6／回旋枝（LCx）やLADの枝
④ 下壁 → II・III・aVF（鏡像はaVL）／右冠動脈（RCA）が多い（LCxのことも）
⑤ 右室 → 下壁に加えて V1・V4R／RCAの根もと（近位）
⑥ 後壁 → V1〜V3のST低下と高いR、背中のV7〜V9でST上昇／RCAかLCx

🚨ST上昇を見たら → 12誘導・すぐ報告（胸痛・冷や汗・息切れ・血圧低下・意識の変化も）
💓前壁中隔・広範囲前壁 → 致死性不整脈（VF）、心不全・ショックに注意
🐢下壁 → 徐脈・房室ブロックが起こりやすい（最大で約2割）。右側誘導（V4R）もとる
🩸右室 → 血圧が下がりやすい。硝酸薬（ニトロ）で急に血圧が下がることがあるため、右室梗塞では使わない（医師の指示を確認）
🔙後壁 → 12誘導には後壁を正面から見る誘導がない。V1〜V3のST低下（＋高いR・上向きのT）として写るので、V7〜V9を追加でとって確かめる

※V4RのST上昇は時間がたつと消えやすい（約半数で10時間以内）。下壁梗塞を見たら早めにとります
※後壁梗塞は、下壁・側壁の梗塞といっしょに起こることが多いです（単独は5〜10%）
※側壁のST上昇は小さく見のがしやすい。III・aVFだけのST低下を見たら、I・aVLの上昇を探します
※誘導と場所・血管の対応は目安です（血管の走り方には個人差があります）

保存して、見返してね。
何個わかったか、コメントで教えてね。

※波形は一例です。心臓の図は輪切りの模式図です
※参考：LITFL ECG Library（Anterior STEMI / Lateral STEMI / High Lateral STEMI / Inferior STEMI / Right Ventricular Infarction / Posterior Myocardial Infarction / ECG Lead positioning）

📌保存・シェアは大歓迎です
🚫画像・動画の無断転載、素材としての使用はご遠慮ください
✉️ご相談はDMへどうぞ

#看護師 #看護学生 #心電図 #12誘導心電図 #心筋梗塞 #急性冠症候群 #ST上昇 #循環器 #急変 #国試
```

- 薬の名前は画面に出さない。右室の「硝酸薬」はキャプションだけ（LITFL の文）
- 「医師の指示を確認」は第21弾の方針（「報告」と書かない）とは別。ほかの回と同じく「すぐ報告」を使う（第24〜26弾と同じ）

## 7. 根拠（LITFL。2026-10-23 に curl で本文を確かめた）

| 内容 | ページ | 本文 |
|---|---|---|
| 前壁の誘導の名前・V1〜V4＝前壁中隔 | https://litfl.com/anterior-myocardial-infarction-ecg-library/ | 「Septal leads = V1-2 / Anterior leads = V3-4 / Lateral leads = V5-6 … Anteroseptal = V1-4 … Extensive anterior / anterolateral = V1-6, I + aVL」「there is often a poor correlation between ECG features and precise infarct location」 |
| 前壁＝LAD・予後が悪い・心不全・心室性不整脈 | 同上 | 「Anterior STEMI usually results from occlusion of the left anterior descending artery (LAD)」「Heart failure (41 vs 15%) / Significant ventricular ectopic activity (70 vs 59%)」「multifocal ventricular ectopy, indicating an "irritable" myocardium at risk of ventricular fibrillation」 |
| 前壁の鏡像は小さいことがある | 同上 | 「the magnitude of reciprocal change in inferior leads is determined by the magnitude of ST elevation in I and aVL … may be minimal or absent」 |
| 広範囲前壁＝近位LAD・ショック | 同上／https://litfl.com/lateral-stemi-ecg-library/ | 「proximal LAD occlusion and indicates a large territory infarction with a poor LV ejection fraction and high likelihood of cardiogenic shock and death」「ST elevation in the precordial leads plus the high lateral leads (I and aVL) is strongly suggestive of an acute proximal LAD occlusion」 |
| 側壁の誘導・鏡像・血管 | https://litfl.com/lateral-stemi-ecg-library/ | 「ST elevation in the lateral leads (I, aVL, V5-6). Reciprocal ST depression in the inferior leads (III and aVF)」「branches of the left anterior descending (LAD) and left circumflex (LCx) arteries」「Lateral STEMI is a stand-alone indication for emergent reperfusion」「Tip: ST depression localised to the inferior leads should prompt you to scrutinise the ECG for evidence of high lateral infarction」 |
| 高位側壁 | https://litfl.com/high-lateral-stemi-ecg-library/ | 「Occlusion of the left circumflex artery may cause ST elevation in I, aVL along with leads V5-6」 |
| 下壁の誘導・鏡像 aVL | https://litfl.com/inferior-stemi-ecg-library/ | 「ST elevation in leads II, III, aVF … Reciprocal ST depression in aVL」「aVL is the only lead truly reciprocal to the inferior wall」 |
| 下壁の血管 | 同上 | 「Dominant right coronary artery (RCA) in 80% of cases / Dominant left circumflex artery (LCx) in 18%」「RCA occlusion is suggested by: ST elevation in lead III > lead II / Presence of reciprocal ST depression in lead I」 |
| 下壁の徐脈・房室ブロック・右室 | 同上 | 「Up to 20% of patients with inferior STEMI will develop either second- or third-degree AV block」「Concomitant right ventricular infarction (40% of patients); these patients may develop severe hypotension in response to nitrates」 |
| 右室の誘導・V4R | https://litfl.com/right-ventricular-infarction-ecg-library/ | 「In patients with inferior STEMI, RV infarction is suggested by: ST elevation in V1 … ST elevation in III > II」「The most useful lead is V4R」「ST elevation in V4R has a sensitivity of 88%」 |
| 右室＝血圧低下・硝酸薬 | 同上 | 「very preload sensitive … can develop severe hypotension in response to nitrates … nitrates are contraindicated」「isolated RV infarction is extremely uncommon」 |
| V4R は早く消える | 同上 | 「ST elevation in the right-sided leads is a transient phenomenon, lasting less than 10 hours in 50% of patients」 |
| 後壁の形・V7〜V9 | https://litfl.com/posterior-myocardial-infarction-ecg-library/ | 「Horizontal ST depression / Tall, broad R waves (>30ms) / Upright T waves / Dominant R wave (R/S ratio > 1) in V2」「Posterior infarction is confirmed by the presence of ST elevation and Q waves in the posterior leads (V7-9)」「only 0.5 mm of ST elevation is required」 |
| 後壁は単独が少ない | 同上 | 「usually occurring in the context of inferior or lateral infarction. Isolated posterior MI is less common (5-10% of infarcts)」 |
| 後壁の血管（RCA か LCx） | https://litfl.com/inferior-stemi-ecg-library/ ／ lateral-stemi | 「The LCx territory covers the lateral part of the inferior wall and the left posterobasal area」「Inferior-posterior-lateral STEMI due to LCx occlusion」。後壁は優位な RCA か LCx（LITFL の明記は下壁・側壁のページ。後壁ページには血管の明記なし → **レビューで確認**） |
| 誘導の分け方・V4R・V7〜V9 の位置 | https://litfl.com/ecg-lead-positioning/ | 「Inferior (II, III, aVF) Lateral (I, aVL, V5, V6) Anterior (V1–4)」「V4R … 5th right intercostal space in the mid-clavicular line」「V7 – Left posterior axillary line … V8 – Tip of the left scapula … V9 – Left paraspinal region」 |

## 8. 迷ったこと・レビューで見てほしい点
- 中隔と前壁を1つ（前壁中隔）にしたこと（上の理由）
- 後壁を**単独**の形で見せること（LITFL では単独は 5〜10%。下壁＋後壁で見せると「④と同じ」に見えて、V1〜V3 の ST低下が主役にならない）。キャプションで「いっしょに起こることが多い」と書く
- ③側壁の看護の1行「上昇が小さくても見のがさない」：LITFL の「stand-alone indication for emergent reperfusion」「Tip: … scrutinise … high lateral」から。行動というより「見かた」なので、ほかの案があれば
- ①前壁中隔の「致死性不整脈（VF）に注意」：LITFL の心室性期外収縮・VF の注意から（前壁に多い）。急性心筋梗塞ではどの場所でも VF は起こりうる → キャプションでは①②まとめて書いた
- ⑥の責任血管「RCA か LCx」の根拠は下壁・側壁のページ（後壁ページには明記なし）
- 輪切りの図は、前胸部誘導（水平面）と四肢誘導（前額面）を1枚にまとめた模式図。「後壁」は今の呼び方では「下側壁（基部）」にあたる（LITFL は posterior の名前で説明しているので、画面も「後壁」）

## 9. 次にやること
1. でんさんの確認（下の3点）
2. ナレーションを録音（Ren・1.2倍）→ 区間を声に合わせる
3. `make_review_pdf.py`・`review_request.md`（等倍フレームPDF）→ AI専門医レビュー（別エージェント）
4. 書き出し（`--jobs 2` を足す）・サムネイル（`--thumb` を足す。透かしなし）・キャプション・Drive

### でんさんに決めてもらいたいこと
1. **パターンは6つ（前壁中隔にまとめる）でよいか** → おすすめ：6つ（LITFL の分け方と同じ・ゆっくり見せられる）
2. **後壁は単独の形で見せてよいか**（実際は下壁・側壁といっしょが多い）→ おすすめ：単独で見せて、キャプションに一言
3. **④下壁 → ⑤右室 だけ、灰色の正常を通さず直接変えてよいか**（右室は下壁に加わるものなので）→ おすすめ：直接

## 冒頭の3D（2026-10-23 夕方から。前の「その場で光るフック」はやめた）
`reel29_mi/intro3d.py`。0〜8.5秒。背景は絵そのもの（暗い青）、透かしは全コマ。
| 秒 | 素材 | 中身 |
|---|---|---|
| 0.00〜1.10 | 03 全身 → 心臓へ寄る（倍率は対数）。0.68〜1.10 に 04 へ重ねて切り替え（心臓の中心と幅を8章の値で合わせる） | 問いかけ「ST上昇、心臓のどこ？」（上部・影つき、〜2.05秒）。低いウーシュ |
| 1.10〜1.85 | 04（前） | 「前壁 V1〜V4」＋前の面にやわらかい光 |
| 1.85〜2.95 | 動画10（0〜3秒・3〜5秒は早送り・5〜8秒） | 04→動画の頭・動画の終わり→07 は重ねて切り替え |
| 2.95〜3.70 | 07（左） | 「側壁 I・aVL・V5・V6」（光は心尖が真下向きなのに合わせて縦長） |
| 3.70〜4.75 | 動画11（0〜6.5秒、6.5〜6.75秒のあいだに 08 へ重ねて切り替え） | |
| 4.75〜5.50 | 08（下） | 「下壁 II・III・aVF」（横隔膜に乗った面） |
| 5.50〜6.60 | 動画12（2〜6秒の大回りを早送り） | |
| 6.60〜7.35 | 09（後ろ） | 「後壁 V7〜V9」 |
| 7.35〜8.50 | 09 が縮みながら輪切りの図の位置へ（外側から消える） | 12誘導の枠が下から上へふわっと、輪切りが重なって出る → 見出し |
- 動画は前後のコマを混ぜない（1コマずつ、コマを飛ばして速さを変える）。止まっているあいだもゆっくり寄りつづける（5.5%）
- 冠動脈は絵のものを使わず、描かない（光だけ）

## タイムライン（2026-10-23 夕方から：声の長さで決める）
- 声：`out/vo/lines/*.mp3`（1.2倍済み、1文1ファイル）。届いていない文は見込みの長さ（上の台本）
- 00_3d は 1.15秒から、01_intro は 00 の 0.30秒あと、02_mikata は 3D の終わり＋0.35秒（か 01 の 0.30秒あと）
- 各パターン：名前が出て 0.55秒後に話し始め、話し終わってから 1.25秒（最低 5.6秒）
- まとめ：頭から 0.10秒で matome、「保存して見返してね」と hozon は matome の 0.35秒あと（最低 3.0秒）
- 書き出し：`--preview`（540×960・30fps）／`--render`（60fps・CRF 18）／`--hq`（CRF 11）／`--thumb`。声は `align_vo.py --mux [--preview|--hq]`

## 冒頭の3D素材（2026-10-23 取り込み）
- 元：Drive `【みんなの看護】③シームレス波形リール案/00_素材/素材_人体と心臓3D`（フォルダ id `13yaZv4D5dhHOds1bn_fZdFM4Bi7PbWUv`）。説明書は同じフォルダの `取扱説明書.md`（8章が第29弾用の 07〜12）
- 置き場所：`reel29_mi/assets3d/`（146MB。git には入れない＝.gitignore。新しいセッションでは Drive から取り直す）
- 取り直し方：`curl -L "https://drive.usercontent.google.com/download?id=<ファイルid>&export=download&confirm=t" -o <名前>`（フォルダの共有が「リンクを知っている全員」のときだけ。今は元に戻してあるので、でんさんに一時的に開けてもらう）

## 2026-10-23 夜：ナレーションなし・字幕で見せる（でんさんの指示）＋AI専門医レビューの直し
- **声は使わない**（`align_vo.py`・`out/vo/` は使わない。`make_reel29.py` から声の長さの計算を外した）。効果音（モニター音・ウーシュ）は残す
- タイムラインは「字幕を読める長さ」：日本語 6.5文字/秒＋0.8秒（`read_t`）。1パターンの長さ＝max(6.5秒, 0.6＋名前・血管・看護の1行・字幕の合計を読む長さ)。全体 約88.3秒
- 字幕：白・42px（720px に入らないときだけ 41px）・暗い帯、**いつも y1266**（看護の1行の下・輪切りの上）。名前・血管・看護の1行と同じことは書かない
  - 3D：「12誘導は、心臓を色々な向きから見る」→「STが上がる誘導で、場所の見当がつく」（1行 720px に入るように短くした）
  - 見かた：名前の行は「見かた」、字幕「となり合う誘導が、まとまって上がる」→「反対側の誘導は、鏡のように下がる」
  - ①「V1〜V4 が上がる」②「V1〜V6・I・aVL まで上がる」③「I・aVL・V5・V6 が上がる」④「II・III・aVF が上がる／aVL が下がる」⑤「下壁に加えて、右胸の V4R も上がる」⑥「V1〜V3 が下がって R が高い」→「→ 背中の V7〜V9 で上がる」
  - まとめ：名前の行は「まとめ」、字幕「上がる誘導で、場所と血管がわかる」
- 輪切りの図は字幕の場所をあけるため 0.82倍・中心 (540, 1452) に。3D の名前の札は y1160（名前の行の高さ）
- 3D の回り込み1本 1.10秒 → 1.45秒、止まる所 0.75 → 0.85秒。冒頭は 9.9秒（`intro3d.SEQ`）
- レビューの直し：3D の札「前壁中隔 V1〜V4」「後壁 V7〜V9（背中に追加）」、光（前＝LAD の溝より左の左室前壁、後ろ＝左室の後ろの基部寄り）、①看護「→ VFに注意。除細動器を近くに」、③看護「→ III・aVFが下がったら、I・aVLも見る」（「…I・aVLも確かめる」は 36px で 762px と入らないので、レビューの短い言い方）、⑥ V1〜V3 の ST を水平に（`st_flat`：J点のあと約0.08秒水平・T を 0.022秒遅らせる）、「鏡像（前から見ると逆さ）」、まとめの左下に「※側壁はLADの枝のことも」、キャプション（`reel29_mi/caption.txt`）

## 2026-10-23 夜（確認版③）：配置の整理・3D → 輪切りをシームレスに
- 上から：①名前（y336。冒頭〜見かたは「心筋梗塞の場所 6パターン」、①から番号と名前＋血管）→ ②説明の枠（x80〜1000・y380〜488、角丸・細い線。1行め＝字幕 34px 白、2行め＝看護の1行など 32px）→ ③12誘導（x80〜1000、段の上端 500・段の間隔 168px＝12mm、基線 612/780/948/1116）→ 凡例「赤＝ST上昇　青＝鏡像」（y1182・26px）→ 透かし（y1236・中央64px・800・白16%・全コマ同じ）→ ④輪切り（中心 540,1456）
- 段の間隔を 12mm にしたので、ぶつからないよう正常の V1・V2 の S を −0.52・−0.50mV、①②の V2・V3 の T の足し分を 0.06 に
- 3D：前（04）→ 左（07）→ 後ろ（動画11 の154コマめ＝背面）→ 下（08）。08 は輪切り（足もとから見た向き）と同じ向き。3D の札は y1340、字幕は心臓の下の枠（y1400〜1462・同じ見た目）
- 08 で止まったら、輪切りの図（字なし・2倍の細かさ）を 08 の心臓と同じ位置・同じ大きさ（心臓の幅の0.85）で重ねて 0.6秒で絵を消す → 0.8秒で縮みながら下の定位置へ（見出し・枠・12誘導が出る）。`intro3d.T_FIN/XF_D/MV_D`、`make_reel29.fin_frame`
- ③の看護の1行は枠の中（32px・820px まで）に入るので「→ III・aVFの低下を見たら、I・aVLも確かめる」に戻した。3D の字幕も指定どおりの文に戻した

## 2026-10-23 夜（確認版④・静止画だけ。動画はでんさんの OK のあと）
- 縦の割り振り（1080×1920・px）：名前 316〜368／説明の枠 390〜488／12誘導4段 508〜1050（段の上端 493・段の間隔 140＝10mm・基線 593/733/873/1013、波形は振幅 0.78倍 `AMP`）／凡例 1072〜1098／輪切り（字込み）1120〜1584。かたまりの間は 22・20・22・22px
- 4段め（V4R・V7〜V9）はいつも出す（使わないときは灰色＋「追加の誘導」）。「V4R＝右胸に貼る」「V7〜V9＝背中に貼る」は凡例の行の左に、そのときだけ
- 透かしは12誘導の2段めと3段めのあいだ（cy714・外枠 691〜756。誘導名と重ならない・波形とは重なる）。3D も同じ位置
- 輪切りは最初の大きさの 1.35倍（中心 470,1345）。左上に「足もとから見た図（輪切りの模式図）」、左下に「※波形は一例」
- 3D：前（04）→ 左（07）→ 後ろ（09。動画11 の背中側から重ねて切り替え）→ 下（08。動画12 の逆再生）。止まるたびに、その壁（光らせる場所）へ寄る（`intro3d.cam_main`・`ZOOM`）。08 は胸全体を 0.35秒見せてから下の面へ寄る
- 向きの目印（左上）：足もとから見た胴体（上＝前・下＝背中）と目の矢印。「前から／左から／後ろから／足もとから見上げる」。後ろ→下の動画の前半で矢印が足もと（⊙）へ回ってから絵が切り替わる
- 3D → 輪切り：切り口の線（0.5秒）→ 筋肉の赤い輪切りを 08 の心臓に重ね、絵を消す（0.6秒）→ 塗りが図へ・区画の名前（0.6秒）→ 縮みながら定位置へ（0.8秒）。冒頭は 11.5秒
