# 第29弾 心筋梗塞の場所 ― AI専門医レビュー（2026-10-23 13:10）

- レビュー担当：Claude（作った担当とは別のエージェント。読むだけ・ファイルは直していない）
- 見たもの：`docs/reel29_spec.md`、静止画 `out/still_001.3.png`（冒頭）・`040.8`（下壁）・`049.4`（右室）・`058.7`（後壁）・`066.3`（まとめ）、`make_reel29.py` の `NORMAL`・`PATTERNS`・`_INF`（①②③は静止画がないので値で確認）
- 根拠：LITFL 本文を 2026-10-23 に curl で取得して確認（Anterior MI／Inferior STEMI／Lateral STEMI／High Lateral STEMI／Posterior MI／RV Infarction）。LITFL 以外は出典名を書いた

## 総評
医学的な骨組み（誘導・鏡像・責任血管・III＞II・V4R・V7〜V9）は LITFL と合っている。**大きな誤りはない**。
直したいのは次の3点。
1. 冒頭3Dの「12誘導は…」と「後壁 V7〜V9」の組み合わせ。V7〜V9 が12誘導に入っているように見える
2. キャプションの後壁の文「12誘導ではSTが上がらず、V1〜V3が下がるだけ」。言いすぎ
3. 冒頭のナレーションで「場所は、上がる誘導でわかる」が2回になる（3Dの場面を足すため）

ほかは「推奨」の手直し。

---

## 冒頭（問いかけ・フック）― 静止画 1.3秒
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 「ST上昇、心臓のどこ？」＋前壁中隔の点灯（V1〜V4 赤・輪切りの前壁＋中隔） | OK | V1 は rS のまま ST が上がっていて、形は自然。LITFL Anteroseptal＝V1-4 |
| フックの名前「前壁中隔？」 | OK | 「？」付きなので答えを言い切っていない |
| 台本「心筋梗塞の場所は、上がる誘導でわかる。まず6パターン。」 | 推奨 | 3D の場面で「心筋梗塞の場所は、STが上がる誘導でわかる。」と言うので、**同じ内容が2回になる**。冒頭は「まず6パターン、見ていこう。」だけにする。または3Dの2文めと1つにまとめる（下を参照） |

## 冒頭3D（追加予定：前→左→下→後ろ）
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 「後壁 V7〜V9」とナレーション「12誘導は、心臓を、いろんな向きから見ている。」 | **要修正** | V7〜V9 は12誘導に入っていない（背中に足す誘導。LITFL Posterior MI「the posterior myocardium is not directly visualised by the standard 12-lead ECG」）。この組み合わせだと「12誘導に後壁を見る誘導がある」と誤解される。⑥で言いたい「12誘導では後壁は見えない」とも食い違う。**画面の字を「後壁 V7〜V9（背中に追加）」にする**。ナレーションはそのままでよい |
| 「前壁 V1〜V4」 | 推奨 | ①の名前は「前壁中隔」、まとめでは V1・V2＝中隔、V3・V4＝前壁。3D だけ「前壁 V1〜V4」だと呼び方がずれる。**「前壁中隔 V1〜V4」**にそろえる |
| 「側壁 I・aVL・V5・V6」「下壁 II・III・aVF」 | OK | LITFL Lateral STEMI「I, aVL, V5-6」、Inferior STEMI「II, III, aVF」 |
| 3D で光らせる場所（作るときの注意） | 推奨 | (a) 心臓を前から見ると、見える面の大部分は**右室**。「前壁」は右室の前面ではなく、**前室間溝（LAD の走る溝）から左の左室前壁**を光らせる。(b)「後ろ」から見ると、見える面の上半分は**左房**。「後壁」は**左室の後ろ・基部寄り（房室間溝の下。下壁と側壁の間）**を光らせる。左房や下壁（横隔膜面）と重ねない。(c)「下」は横隔膜に接する面（下壁）を光らせる |
| 「心筋梗塞の場所は、STが上がる誘導でわかる。」 | 推奨 | LITFL Anterior MI「there is often a poor correlation between ECG features and precise infarct location」。言い切らず「**見当がつく**」とする（キャプションの言い方と同じ）。言い換え：「心筋梗塞の場所は、STが上がる誘導で、見当がつく。」 |
| 右室が3Dに出ない | OK | 4方向に絞るのはよい。右室は⑤で V4R と一緒に出るので足りる |

## 見かた（4.6〜9.2秒）
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 「となり合う誘導が、まとまって上がる。反対側は、鏡のように下がる。」 | OK | STEMI の「隣り合う2誘導以上」の考え方、LITFL の reciprocal change と合う。前壁中隔では鏡像が出にくい（LITFL「may be minimal or absent」）が、①で青が出ないので矛盾は出ない |
| 赤い字「ST上昇を見たら → 12誘導・すぐ報告」・凡例 | OK | ナレーションで「すぐ報告」と言っていないので、作業メモの方針どおり |

## ① 前壁中隔
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 波形 V1〜V4 ST上昇（0.18〜0.28mV）＋T 少し高め・鏡像なし | OK | LITFL Anteroseptal＝V1-4。I・aVL が上がらないので III・aVF の鏡像は小さいか出ない（LITFL NB） |
| 輪切り：前壁＋中隔・LAD 橙 | OK | |
| 責任血管「LAD（左前下行枝）」 | OK | LITFL「Anterior STEMI usually results from occlusion of the LAD」 |
| 看護の1行「→ 致死性不整脈（VF）に注意」 | OK（推奨あり） | 前壁梗塞は心室性期外収縮が多い（LITFL 70 vs 59%・「irritable myocardium at risk of VF」）ので正しい。ただ「注意」だけだと行動が見えにくい。看護師の行動としては「モニターをつけ続け、除細動器をすぐ使えるようにする」が標準（ESC 2017 STEMI ガイドライン：Ibanez B, et al. Eur Heart J 2018;39:119-177「ECG monitoring with defibrillator capacity … as soon as possible in all patients with suspected STEMI」・Class I）。言い換え：**「→ VFに注意。除細動器を近くに」**。VF はどの場所の梗塞でも起こるので、キャプションに「（どの場所でも起こりえます）」と足してもよい |
| 台本「V1からV4が上がれば、前壁中隔。左前下行枝、LADです。」 | OK | |

## ② 広範囲前壁
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 波形 V1〜V6・I・aVL 上昇、III −0.10・aVF −0.07 | OK | LITFL Extensive anterior＝V1-6, I＋aVL。Example 4「Minimal reciprocal ST depression in III and aVF」と同じ小ささ |
| 輪切り：前壁＋中隔＋側壁・LAD | OK | 近位 LAD は対角枝を通して側壁の前のほうも養う |
| 「LADの根もと」 | OK | LITFL Lateral STEMI「predicts a proximal LAD lesion 87% of the time」 |
| 看護の1行「→ 心不全・ショックに注意」 | OK | LITFL「high likelihood of cardiogenic shock」「Heart failure 41 vs 15%」 |
| 台本 | OK | |

## ③ 側壁
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 波形 I・aVL・V5・V6 上昇（0.16〜0.20）、III −0.14・aVF −0.09 | OK | LITFL Lateral STEMI「ST elevation in the lateral leads (I, aVL, V5-6). Reciprocal ST depression in the inferior leads (III and aVF)」。鏡像が III でいちばん深いのも High Lateral STEMI「most pronounced in lead III」と合う |
| 責任血管「LCx（回旋枝）など」・台本「回旋枝などです」 | OK | LITFL High Lateral「Occlusion of the left circumflex artery may cause ST elevation in I, aVL along with leads V5-6」。一方 Lateral STEMI には「supplied by branches of the LAD and LCx」「D1 of the LAD, OM of the LCx, or the ramus intermedius」とある。「など」でこれを含めているので誤りではない。キャプションの「回旋枝（LCx）やLADの枝」はより正確でよい。台本をもう一歩くわしくするなら「回旋枝や、LADの枝です。」（推奨・任意） |
| 看護の1行「→ 上昇が小さくても見のがさない」 | 推奨 | 内容は正しい（LITFL「stand-alone indication for emergent reperfusion」「this may be easily missed」）が、何をすればよいかが分からない。LITFL の Tip「ST depression localised to the inferior leads should prompt you to scrutinise the ECG for evidence of high lateral infarction」を行動にする。言い換え：**「→ III・aVFの低下を見たら、I・aVLを確かめる」**（長いときは「→ III・aVFが下がったら I・aVLを見る」） |

## ④ 下壁 ― 静止画 40.8秒
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 波形 II 0.20／III 0.30／aVF 0.25（III＞II）、aVL −0.20＋T陰転、I −0.07 | OK | LITFL Inferior「ST elevation in lead III > lead II」「reciprocal ST depression in lead I」＝RCA。aVL の深い鏡像も LITFL「aVL is the only lead truly reciprocal」と合う。画面では III の ST と II の ST の差が少し分かりにくいが、値は正しい（目で分かるようにしたいなら III を 0.32〜0.35 に、II を 0.18 にしてもよい・任意） |
| 輪切り：下壁 赤・RCA の弧（右室〜下壁）・I aVL 青 | OK | |
| 「RCA（右冠動脈）が多い」 | OK | LITFL「RCA in 80% / LCx in 18%」 |
| 看護の1行「→ 徐脈・房室ブロックに注意。V4Rもとる」 | OK | LITFL「Up to 20% … second- or third-degree AV block」、RV Infarction「Suspect and look for RV infarction in all patients with inferior STEMI」。看護師の行動として具体的でとてもよい |
| 台本「II、III、aVFなら、下壁。多くは右冠動脈。aVLは鏡のように下がります。」 | OK | |

## ⑤ 右室 ― 静止画 49.4秒
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 波形：下壁＋V1 ＋0.12・V4R ＋0.15 | OK | LITFL RV「ST elevation in V1」「V1 is the only standard ECG lead that looks directly at the right ventricle」「The most useful lead is V4R」。V4R の ST上昇は 1mm（0.1mV）以上が目安なので 0.15mV でよい（ESC 2017 STEMI ガイドラインの右側誘導の基準 ≥0.1mV） |
| 「← 右胸に貼る」・4段めの V4R | OK | 矢印の向き（左＝V4R）も合っている |
| 輪切り：右室の三日月＋下壁 赤・RCA | OK | 右室は RCA の右室枝で養われる。④→⑤ を直接つなぐのも LITFL「complicates up to 40% of inferior STEMIs (isolated RV infarction is extremely uncommon)」と合う |
| 「RCAの根もと」 | OK | 右室枝より手前（近位）で詰まると右室梗塞になる。LITFL の RV ページには「近位」の文はないが、Inferior STEMI に「RCA occlusion is suggested by … Signs of RV infarction: STE in V1 and V4R」とある。近位 RCA については Morris F, Brady WJ. ABC of clinical electrocardiography: Acute MI Part I. BMJ 2002;324:831-4（LITFL の参考文献） |
| 看護の1行「→ 血圧低下に注意」 | OK | LITFL「very preload sensitive … severe hypotension in response to nitrates」。画面に薬の名前を出さない方針なら、これで十分。キャプションで硝酸薬のことを書いているのもよい |
| 台本「下壁に加えて、右胸のV4Rも上がれば、右室。血圧低下に注意。」 | OK | 画面の V1 上昇は台本で言っていないが、問題ない |

## ⑥ 後壁 ― 静止画 58.7秒
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| V1〜V3：ST低下（−0.14〜−0.22）＋R 高く幅広（V2 R/S＞1）＋T 上向き | OK（推奨あり） | LITFL Posterior の4つ（Horizontal ST depression / Tall, broad R / Upright T / R/S＞1 in V2）がそろっている。ただ静止画では、ST が J点でいちばん深く、そこからなだらかに上がって T につながるので「**上向きに傾いた ST低下**」に見える。LITFL は「**Horizontal** ST depression」。J点のあと 0.06〜0.08秒ほど ST を水平にしてから T が立ち上がるようにする（推奨）。上向きに傾いた ST低下は、ほかの原因（頻脈など）でもよく見られるので、形で区別がつくようにしたい |
| V7〜V9 ＋0.10〜0.12mV・Q波なし | OK | LITFL「only 0.5 mm of ST elevation is required」。急性期として Q を出さない判断もよい |
| 「背中に貼る →」 | OK | |
| 輪切り：後壁の位置（側壁と下壁の間・右下）・赤 | OK | 短軸像（足もとから見る向き）の「下側壁（基部）」の位置で、昔の「後壁」にあたる。AHA の17区分モデル（Cerqueira MD, et al. Circulation 2002;105:539-42）と合う |
| 輪切りの青い点線の矢印「鏡像」（V1〜V3 → 内腔 → 後壁） | OK（推奨あり） | LITFL「The anteroseptal leads are directed from the anterior precordium towards the internal surface of the posterior myocardium … the typical injury pattern … becomes inverted」と同じ考えを正しく図にしている。図の中で前壁中隔と後壁がちょうど反対側にあるので、向きも合っている。ただ「鏡像」の2文字だけでは「梗塞が前から後ろへ広がる」と読まれるおそれが少しある。字を「**鏡像（前から見ると逆さ）**」にするか、ナレーションの「V1からV3が下がって」と矢印の出るときをそろえる（推奨） |
| 「RCA か LCx」 | OK | LITFL の後壁ページには血管の文がないが、Inferior STEMI「The LCx territory covers … the left posterobasal area」、Lateral STEMI「Inferior-posterior-lateral STEMI due to LCx occlusion」、Inferior STEMI「Posterior infarction due to extension of infarct area」（RCA による下壁梗塞の広がり）で裏付けられる。Morris F, Brady WJ. BMJ 2002;324:831-4 にも、後壁梗塞は RCA か LCx と書かれている |
| 看護の1行「→ V7〜V9 を追加でとる」 | OK | 行動として具体的。LITFL「confirmed by … posterior leads (V7-9)」 |
| 台本「V1からV3が下がってRが高いときは、背中のV7からV9をとる。上がれば、後壁。」 | OK | LITFL「In patients presenting with ischaemic symptoms, horizontal ST depression in V1-3 should raise the suspicion of posterior MI」。症状がある人で、という前提はキャプションにあってもよい（推奨・任意） |
| 単独の後壁の形で見せること | OK | キャプションで「下壁・側壁といっしょに起こることが多い（単独は5〜10%）」と書いているので、見せ方として妥当 |

## まとめ ― 静止画 66.3秒
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| 誘導名の色と壁の名前（V1・V2 中隔／V3・V4 前壁／I・aVL・V5・V6 側壁／II・III・aVF 下壁／V4R 右室／V7〜V9 後壁・aVR は塗らない） | OK | LITFL Anterior「Septal leads = V1-2 / Anterior leads = V3-4」。aVR を塗らないのもよい |
| 輪切りの色分け（LAD：前壁＋中隔／LCx：側壁＋後壁／RCA：下壁＋右室） | OK（推奨あり） | AHA 17区分モデルの標準的な割り当て（LAD＝前壁・前中隔、LCx＝前側壁・下側壁、RCA＝下壁・下中隔）と合っていて、解剖として妥当。ただし2点。(a) ②で「I・aVL が上がる＝LADの根もと」と教えた直後に、まとめで I・aVL が LCx の紫になるので、見る人が迷うかもしれない。LITFL も「lateral wall … supplied by branches of the LAD and LCx」。注記「※側壁はLADの枝のことも」を左下の注記に1行足す（推奨）。(b) 中隔の下のほうは RCA（後下行枝）の領域（LITFL Inferior「The RCA territory covers the medial part of the inferior wall, including the inferior septum」）。模式図なので今のままでよい（任意） |
| 後壁が LCx だけの色 | OK | ⑥で「RCA か LCx」と言い、まとめは AHA の標準の割り当て。食い違いとまでは言えない。気になるなら後壁の外側の弧を紫と青緑の2色にする（任意） |
| 「上がる誘導で、場所と血管がわかる」 | 推奨 | 冒頭と同じ理由で「わかる」は言い切りが強い。キャプションに「目安です」があるので許容範囲。言い換えるなら「上がる誘導で、場所と血管の見当がつく。」 |

## キャプション
| 項目 | 判定 | 理由・直し方 |
|---|---|---|
| ①〜⑥の一覧 | OK | LITFL と合う |
| 「🐢下壁 → 徐脈・房室ブロックが起こりやすい（約2割）」 | 推奨 | LITFL は「Up to 20%」（最大2割）。言い換え：「（最大で約2割）」 |
| 「🩸右室 → … 硝酸薬（ニトロ）で急に血圧が下がることがあるため、右室梗塞では使わない（医師の指示を確認）」 | OK | LITFL「nitrates are contraindicated」 |
| 「🔙後壁 → 12誘導ではSTが上がらず、V1〜V3が下がるだけ。V7〜V9を追加でとって確かめる」 | **要修正** | 「STが上がらず…だけ」は言いすぎ。後壁梗塞は下壁・側壁の梗塞といっしょに起こることが多く（LITFL「usually occurring in the context of inferior or lateral infarction」）、そのときは12誘導でも II・III・aVF や V5・V6 の ST は上がる。V1〜V3 は ST低下だけでなく「高いR・上向きのT」も手がかり。言い換え：**「🔙後壁 → 12誘導には後壁を正面から見る誘導がない。V1〜V3のST低下（＋高いR・上向きのT）として写るので、V7〜V9を追加でとって確かめる」** |
| 「※V4RのST上昇は…約半数で10時間以内」 | OK | LITFL「lasting less than 10 hours in 50%」 |
| 「※後壁梗塞は…単独は5〜10%」 | OK | LITFL のとおり |
| 「※側壁のST上昇は小さく見のがしやすい。III・aVFだけのST低下を見たら、I・aVLの上昇を探します」 | OK | LITFL の Tip のとおり |
| 「🚨ST上昇を見たら → 12誘導・すぐ報告（胸痛・冷や汗・息切れ・血圧低下・意識の変化も）」 | OK | |
| 「💓前壁中隔・広範囲前壁 → 致死性不整脈（VF）、心不全・ショックに注意」 | OK | ①で除細動器の一言を入れるなら「VFに備えて除細動器を近くに」と足してもよい（任意） |
| 定型3行（caption_template.txt） | OK | 一字一句同じ |

---

## とくに見てほしい点への答え
1. **看護の1行**：①②④⑤⑥は正しく、行動としても妥当。④「V4Rもとる」と⑥「V7〜V9を追加でとる」は、とくによい。①は「除細動器を近くに」を足すと行動になる（推奨）。③は「見かた」の注意なので、「III・aVFの低下を見たら、I・aVLを確かめる」に変えるのがおすすめ（推奨）
2. **後壁の見せ方と「鏡像」の矢印**：LITFL の4つの特徴と V7〜V9 0.5mm がそろっていて正しい。矢印の向き（V1〜V3 → 内腔 → 後壁）も LITFL の説明どおり。直したいのは ST低下の形を「水平」にすること（今は上向きに傾いて見える）と、「鏡像」の字を少しくわしくすること（どちらも推奨）
3. **右室**：V1の ST上昇・V4R・III＞II は LITFL どおり。「血圧低下に注意」は正しい（硝酸薬のことはキャプションで補えている）
4. **側壁の「LCx（回旋枝）など」**：OK。LITFL High Lateral の「LCx → I・aVL・V5-6」と、Lateral の「LAD の枝（D1）のことも」を「など」で含めている。台本「回旋枝などです」も OK
5. **色分け**：AHA 17区分の標準と合っていて、解剖として妥当。②との食い違いを避けるため「※側壁はLADの枝のことも」を足すのがおすすめ（推奨）
6. **誤解を招く表現**：(a) 冒頭3Dの「12誘導は…」と「後壁 V7〜V9」の組み合わせ（要修正）、(b) キャプションの後壁「STが上がらず…だけ」（要修正）、(c)「場所は…わかる」が冒頭で2回（要修正）。「わかる」の言い切りは推奨どまり

---

## 要修正だけの一覧
1. **冒頭3Dの「後壁」の字**：「後壁 V7〜V9」→「**後壁 V7〜V9（背中に追加）**」（V7〜V9 は12誘導に入っていない。ナレーション「12誘導は、心臓を、いろんな向きから見ている。」はそのままでよい）
2. **キャプションの後壁**：「🔙後壁 → 12誘導ではSTが上がらず、V1〜V3が下がるだけ。V7〜V9を追加でとって確かめる」→「**🔙後壁 → 12誘導には後壁を正面から見る誘導がない。V1〜V3のST低下（＋高いR・上向きのT）として写るので、V7〜V9を追加でとって確かめる**」
3. **冒頭のナレーションの重なり**：3Dの「心筋梗塞の場所は、STが上がる誘導でわかる。」と、その次の「心筋梗塞の場所は、上がる誘導でわかる。まず6パターン。」が同じ内容。→ 3Dは「12誘導は、心臓を、いろんな向きから見ている。心筋梗塞の場所は、STが上がる誘導で、見当がつく。」、その次は「**まず6パターン、見ていこう。**」だけにする
