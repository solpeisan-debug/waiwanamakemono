# 第21弾 v2「この波形を見たら、看護師が次にすること」根拠の確認

確かめた日：2026-10-09（日本時間）
担当：循環器・蘇生の文献調査（Claude）

- 本文を実際に開いて読んだ文献だけを根拠にしています。開けなかったものは「4. 確かめられなかったこと」に書きました。
- 英語はそのまま短く引用し、日本語の要約を添えています。COR／LOE は AHA の推奨の強さ（COR 1＝推奨、2a＝妥当、2b＝考慮してよい、3＝しない）とエビデンスの水準です。

---

## 1. 文献の一覧

| # | 正式名 | 版・年 | URL | 確かめた日・読み方 |
|---|---|---|---|---|
| A1 | Wigginton JG, et al. **Part 9: Adult Advanced Life Support: 2025 American Heart Association Guidelines for Cardiopulmonary Resuscitation and Emergency Cardiovascular Care.** Circulation. 2025;152(suppl 2):S538–S577. DOI 10.1161/CIR.0000000000001376 | AHA 2025（2025-10-21 掲載） | 公式：https://www.ahajournals.org/doi/10.1161/CIR.0000000000001376 ／ 本文を読んだ写し：https://sae-emergencias.org.ar/wp-content/uploads/2026/04/Part-9-Adult-Advanced-Life-Support-AHA-2025.pdf | 2026-10-09。公式サイトはこの環境から 403 で開けず、ahajournals の透かし入りの写し（全40ページ）を読んだ。アルゴリズム図（Figure 2 心停止、Figure 6 脈のある頻拍、Figure 8 脈のある徐脈）も画像で確認 |
| A2 | **Highlights of the 2025 American Heart Association Guidelines for CPR and ECC**（Heart and Stroke Foundation of Canada edition） | 2025 | https://cpr.heartandstroke.ca/resource/GuidelinesHighlightsEN2025 （AHA 公式版：https://cpr.heart.org/-/media/CPR-Files/2025-documents-for-cpr-heart-edits-posting/Resuscitation-Science/252500_Hghlghts_2025ECCGuidelines.pdf は 403） | 2026-10-09。カナダ版は「*」の部分だけがカナダ独自で、ほかは AHA 版と同じと本文に明記 |
| E1 | Soar J, Böttiger BW, et al. **European Resuscitation Council Guidelines 2025 Adult Advanced Life Support.** Resuscitation. 2025;215 Suppl 1:110769. DOI 10.1016/j.resuscitation.2025.110769 | ERC 2025（2025-10） | ERC：https://cprguidelines.eu/ ／ 本文を読んだ写し：https://certifico.com/component/attachments/download/45831 | 2026-10-09。journal 版 PDF（63ページ）の写し。resuscitationjournal.com・sciencedirect は 403。Fig.2（ALS）、Fig.3（院内）、Fig.8（頻拍）、Fig.9（徐脈）も画像で確認。不整脈（peri-arrest arrhythmias）はこの ALS 章の中にある |
| J1 | 日本蘇生協議会（監修）**JRC蘇生ガイドライン2025** | 2025（書籍版 2026-07-13 発刊、医学書院） | https://www.jrc-cpr.org/jrc-guideline-2025/ | 2026-10-09。最終版は書籍のみで、本文（第2章 ALS）は読めなかった。発刊の経緯（2025-10-23 パブリックコメント版公開 → 2026-03 予定が 7 月に延期 → 2026-07-13 発刊）は JRC のお知らせで確認 |
| J2 | 日本蘇生協議会 **JRC蘇生ガイドライン2020 第2章 成人の二次救命処置** | 2020（PDF 無料公開） | https://www.jrc-cpr.org/wp-content/uploads/2022/07/JRC_0047-0150_ALS.pdf | 2026-10-09。日本語の言い回しの確認に使用 |
| L1 | LITFL ECG Library：AV block 2nd degree Mobitz II（Hay block） | 本文の日付は未記載 | https://litfl.com/av-block-2nd-degree-mobitz-ii-hay-block/ | 2026-10-09 curl |
| L2 | LITFL ECG Library：AV block 3rd degree（complete heart block） | 同上 | https://litfl.com/av-block-3rd-degree-complete-heart-block/ | 同上 |
| L3 | LITFL ECG Library：Premature Ventricular Complex（PVC） | 同上 | https://litfl.com/premature-ventricular-complex-pvc-ecg-library/ | 同上 |
| L4 | LITFL ECG Library：Ventricular Tachycardia – Monomorphic | 同上 | https://litfl.com/ventricular-tachycardia-monomorphic-ecg-library/ | 同上 |
| L5 | LITFL ECG Library：Polymorphic VT and Torsades de Pointes（TdP） | 同上 | https://litfl.com/polymorphic-vt-and-torsades-de-pointes-tdp/ | 同上 |
| L6 | LITFL ECG Library：Ventricular Fibrillation（VF） | 同上 | https://litfl.com/ventricular-fibrillation-vf-ecg-library/ | 同上 |
| L7 | LITFL CCC：Ventricular Tachycardia | Chris Nickson | https://litfl.com/ventricular-tachycardia/ | 同上 |
| L8 | LITFL CCC：Pulseless Electrical Activity（PEA） | 同上 | https://litfl.com/pulseless-electrical-activity/ | 同上 |
| L9 | LITFL CCC：Transcutaneous Pacing | Chris Nickson, 2020-11-03 | https://litfl.com/transcutaneous-pacing/ | 同上 |
| L10 | LITFL CCC：Hypokalaemia / Hypomagnesaemia / Magnesium | 同上 | https://litfl.com/hypokalaemia/ ほか | 同上 |
| S1 | Zeppenfeld K, et al. **2022 ESC Guidelines for the management of patients with ventricular arrhythmias and the prevention of sudden cardiac death.** Eur Heart J. 2022;43:3997–4126. DOI 10.1093/eurheartj/ehac262 | ESC 2022 | 公式：https://academic.oup.com/eurheartj/article/43/40/3997/6675633 （403）／ 読んだ写し：https://iris.unipv.it/handle/11571/1472843 （大学リポジトリの journal 版 PDF） | 2026-10-09 |
| S2 | Drew BJ, et al. **Prevention of Torsade de Pointes in Hospital Settings: A Scientific Statement From the AHA and the ACCF.** Circulation. 2010;121:1047–1060. | AHA/ACCF 2010（米国クリティカルケア看護師協会 AACN が承認） | https://pmc.ncbi.nlm.nih.gov/articles/PMC3056123/ | 2026-10-09 |

注：LITFL の CCC には「Torsades」「Asystole」「R on T」の単独ページが見つからず（URL を推測すると 403）、上の ECG Library と CCC のページで代わりに確かめました。

---

## 2. パターンごとの表

判定の書き方：**そのままでよい**／**直したほうがよい**／**根拠が見つからない**（一部だけのときは、その部分を書きます）

### ① PとQRSのつながり

#### モビッツII型
- **いまの下書き**：意識・血圧を見て、すぐ報告。ペーシングの準備
- **根拠**
  - ERC 2025 Fig.9（徐脈アルゴリズム）：生命をおびやかす徴候は "1. Shock 2. Syncope 3. Myocardial ischaemia 4. Severe heart failure"。徴候がなくても "Risk of asystole? … Mobitz II atrio-ventricular block … Complete heart block with broad QRS … Ventricular pause > 3s" が YES なら "Transcutaneous pacing" を含む "interim measures" と "Seek expert help / Arrange transvenous pacing" へ進む。
    → モビッツII型は、症状がなくても「心静止になりやすい」として、ペーシングの準備と専門医への連絡に進む。
  - ERC 2025 本文："Do not give atropine to patients with high-degree atrioventricular block and wide QRS. It is ineffective and may worsen the block." "Immediate pacing is indicated especially when the block is at or below the His-Purkinje level."
    → 幅の広いQRSの高度房室ブロックにはアトロピンが効かず、悪くすることもある。ヒス束より下のブロックではすぐのペーシングが必要。
  - AHA 2025 Part 9（徐脈）：COR 2b "If bradycardia is unresponsive to atropine, … transcutaneous pacing may be effective while the adult patient is prepared for emergent transvenous temporary pacing"／COR 2b "Immediate pacing might be considered in unstable adult patients with high-degree AV block when IV/IO access is not available."
    → AHA ではアトロピンが先で、効かなければ経皮ペーシング。点滴がとれない不安定な高度房室ブロックではすぐペーシングも考える。
  - AHA 2025 Figure 8：不安定の目安は "Hypotension? Acutely altered mental status? Signs of shock? Ischemic chest discomfort? Acute heart failure?"。徴候がなければ "Obtain 12-lead ECG / Observe"。
  - LITFL（L1）："Mobitz II mandates immediate admission for cardiac monitoring, backup temporary pacing and ultimately insertion of a permanent pacemaker" "Onset of haemodynamic instability may be sudden and unexpected" "The risk of asystole is around 35% per year"。
    → モビッツII型は、すぐのモニター・一時ペーシングの備え・最終的なペースメーカーが必要。急に悪くなることがある。
- **判定**：大筋は**そのままでよい**。ただし「意識・血圧」だけでは、AHA・ERC が挙げる不安定の徴候（胸痛・息苦しさ＝心不全・ショックの徴候）が足りないので、**直したほうがよい**（小さな直し）。
- **直した案**
  → 意識・血圧・胸痛・息苦しさを見て、すぐ報告。経皮ペーシングの準備（パッド）

#### 完全房室ブロック
- **いまの下書き**：意識・血圧を見て、すぐ報告。ペーシングの準備
- **根拠**
  - ERC 2025 Fig.9："Complete heart block with broad QRS" は "Risk of asystole" に入る（上と同じ流れ）。
  - LITFL（L2）："Patients with third degree heart block are at high risk of ventricular standstill and sudden cardiac death. They require urgent admission for cardiac monitoring, backup temporary pacing and usually insertion of a permanent pacemaker"。ただし狭いQRSの補充調律（下壁梗塞など房室結節レベル）は "more likely to respond to atropine and has a better overall prognosis"。
    → 完全房室ブロックは心室停止・突然死の危険が高く、ペーシングの備えが必要。狭いQRSのものはアトロピンが効きやすく、予後もよい。
  - AHA 2025：モビッツII型と同じ（不安定ならアトロピン → 経皮ペーシング／経静脈ペーシング）。
- **判定**：**そのままでよい**（モビッツII型と同じ小さな直しを推奨）。ERC が「心静止の危険」とはっきり書いているのは**幅の広いQRS**の完全房室ブロックなので、言い切るなら幅の広いQRSの例を見せるほうが安全です。
- **直した案**
  → 意識・血圧・胸痛・息苦しさを見て、すぐ報告。経皮ペーシングの準備（パッド）

### ② QRSの幅と形

#### ショートラン（PVC 3連発以上＝非持続性VT）
- **いまの下書き**：患者さんを見て報告。K・Mgを確認
- **根拠**
  - ESC 2022 の定義："Non-sustained ventricular tachycardia (NSVT): Run of consecutive ventricular beats persisting for 3 beats to 30 s." VT は "≥3 consecutive beats with a rate >100 b.p.m."
    → 非持続性VT＝心室から3拍以上、30秒未満。心拍数100/分を超えるもの。
  - LITFL（L3）："3-30 consecutive PVCs with a rate >100bpm described as non-sustained VT (ventricular rhythm if rate <100bpm)"。原因に "Hypokalaemia, Hypomagnesaemia, Digoxin toxicity, Myocardial ischemia"。
  - ESC 2022 Recommendation Table 3（I, C）："In patients with newly documented VA (frequent PVCs, NSVT, SMVT), a baseline 12-lead ECG, recording of the VA on 12-lead ECG, whenever possible, and an echocardiogram are recommended as first-line evaluation."
    → 新しく見つかった心室性不整脈には、12誘導心電図（できれば不整脈そのものも記録）と心エコーを勧める。
  - ESC 2022 Recommendation Table 8（I, C）："Investigation for reversible causes (e.g. electrolyte imbalances, ischaemia, hypoxaemia, fever) is recommended in patients with VA." "Withdrawal of offending agents is recommended whenever drug-induced VAs are suspected."（I, B）
    → 電解質の異常・虚血・低酸素・発熱などの「戻せる原因」を調べる。薬が原因と疑えば中止する（中止は医師の判断）。
  - ESC 2022 本文："Cardioversion is not indicated in patients with repetitive NSVTs."
    → くり返す非持続性VTには電気ショックはしない。
- **判定**：**そのままでよい**。K・Mg には根拠があります。12誘導を足すとさらに根拠に沿います。
- **直した案**
  → 患者さんを見て報告。12誘導とK・Mgを確認

#### 単形性VT
- **いまの下書き**：まず脈を確認。脈あり：すぐ報告・除細動器を準備／脈なし：人を呼び、CPR＋電気ショック
- **根拠**
  - AHA 2025（WCT）：COR 1 "Synchronized cardioversion is recommended for acute treatment of adult patients with hemodynamically unstable wide-complex tachycardia." 不安定の例は "systolic blood pressure <80 mm Hg or altered mentation"。"Hemodynamically stable patients with WCT allow the professional time to obtain a 12-lead electrocardiogram, place an IV, and administer IV drugs"。
    → 不安定なら同期電気ショック。安定なら12誘導・点滴・薬の時間がある。
  - AHA 2025 Figure 6：不安定の目安 "Hypotension? Acutely altered mental status? Signs of shock? Ischemic chest discomfort? Acute heart failure?"、最初に "12-lead ECG, if available"。
  - ERC 2025："Electrical cardioversion is recommended for stable patients with monomorphic VT who have structural heart disease or when it is unclear whether there is underlying heart muscle damage." "Conscious patients require careful anaesthesia or sedation before attempting synchronised cardioversion"。
    → ERC では、安定していても心臓病があれば（わからなければ）電気ショックを勧める。意識のある人には鎮静が要る＝医師の処置。
  - AHA 2025 心停止（Figure 2・除細動 COR 1）：VF/pVT は電気ショック。ERC 2025 Fig.3（院内）："Call for help / Start chest compressions / Call resuscitation team / Collect resuscitation equipment"、"apply pads / turn on AED and follow prompts"。
  - LITFL（L4）："Prompt recognition and initiation of treatment (e.g. electrical cardioversion) is required in all cases of VT." "Haemodynamically unstable — e.g hypotension, chest pain, cardiac failure, decreased conscious level"。
- **判定**：**そのままでよい**。脈ありのときに「不安定の徴候を見る」「（安定なら）12誘導」を足すとガイドラインどおりになります。
- **直した案**
  → まず脈。脈あり：意識・血圧・胸痛を見て、すぐ報告・除細動器のパッドを貼る（安定なら12誘導）
  → 脈なし：人を呼び、CPR＋電気ショック

#### 多形性VT
- **いまの下書き**：まず脈を確認。脈なし：CPR＋電気ショック
- **根拠**
  - AHA 2025（多形性VT）COR 1, B-NR："Immediate unsynchronized shock is recommended for adults with sustained polymorphic ventricular tachycardia." 補足文："Regardless of the underlying QT interval, all forms of polymorphic VT are considered hemodynamically and electrically unstable." "polymorphic VT cannot be synchronized reliably … and requires high-energy (maximum manufacturer's setting) unsynchronized shock. Assessment of a patient's mental status is important when the appropriateness of sedation is considered before defibrillation."
    → 続く多形性VTは、**脈があっても**すぐ非同期の電気ショック（除細動）の適応。意識があれば鎮静を考える（＝医師の判断）。
  - AHA 2025 COR 2b："IV lidocaine, amiodarone, and measures to treat myocardial ischemia may be considered to treat recurrences of polymorphic VT in adults in the absence of a prolonged QT interval." COR 3："Routine use of magnesium is not recommended for the treatment of polymorphic VT in adults with a normal QT interval."
    → QTが長くない多形性VTは虚血が原因のことが多く、Mgはルーチンには使わない。
  - LITFL（L5）："The most common cause of PVT is myocardial ischaemia/infarction."
- **判定**：**直したほうがよい**。「脈あり」の行がないため、脈があれば様子を見てよいように読めてしまいます。AHA 2025 では、続く多形性VTは脈があっても電気ショックの対象です。
- **直した案**
  → まず脈。脈なし：CPR＋電気ショック
  → 脈あり：人を呼び、除細動器のパッドを貼る（続けば脈があっても電気ショック）

#### トルサード（トルサードドポワント）
- **いまの下書き**：まず脈を確認。脈なし：CPR＋電気ショック／止まっても報告（QT・Mgを確認）
- **根拠**
  - AHA 2025 COR 2b, C-LD："Magnesium may be considered for treatment of adults with recurrences of polymorphic ventricular tachycardia associated with a long QT interval (torsades de pointes)." 補足文："Torsades de pointes typically presents in a recurring pattern of self-terminating, hemodynamically unstable polymorphic VT … Termination of torsades by defibrillation may not prevent its recurrence" "Correcting electrolyte abnormalities, particularly hypokalemia, is also advisable."
    → トルサードは自然に止まってはくり返すことが多い。電気ショックで止めても再発を防げない。Mgを考える。とくに低Kを直す。
  - ESC 2022 Recommendation Table 9（I, C）："Intravenous magnesium with supplementation of potassium is recommended in patients with TdP." 本文："Intravenous magnesium is an effective therapy for TdP even in the absence of hypomagnesaemia."
    → トルサードにはMg静注＋K補充を推奨。**血中Mgが低くなくても**効く。
  - ERC 2025 Table 6："Magnesium can suppress episodes of TdP without necessarily shortening QT, even when serum magnesium concentration is normal … Magnesium 8 mmol IV over 10 min." 本文："For patients with polymorphic VT, precipitating factors should be sought and removed. In case there is a prolongation of the QTc interval at baseline, IV Mg2+ and K+ infusion might help."
  - Drew 2010："For patients with TdP that does not terminate spontaneously or that degenerates into ventricular fibrillation, immediate direct-current cardioversion should be performed." "Magnesium sulfate 2 g can be infused intravenously as a first-line agent to terminate TdP irrespective of the serum magnesium level."
  - LITFL（L5）："TdP is often short lived and self terminating, however can be associated with haemodynamic instability and collapse. TdP may also degenerate into ventricular fibrillation (VF)"
  - JRC 2020（言い回し）：「後天性QT延長に伴う多形性VTは，マグネシウムの静脈内投与での治療効果が期待できる」。
- **判定**：「止まっても報告」「QTを確認」は**そのままでよい**（根拠が強い）。ただし2点**直したほうがよい**。
  1. 「Mgを確認」だけだと「Mgが正常ならMgは要らない」と読めるおそれがあります。ESC・ERC・Drew はいずれも「血中Mgが正常でもMgは効く」と書いています。K（とくに低K）のほうがガイドラインでは前に出ています。
  2. 脈があって止まらないときの行がありません（AHA の多形性VT COR 1、Drew 2010 の「止まらなければすぐ電気ショック」）。
- **直した案**
  → まず脈。脈なし：CPR＋電気ショック／脈あり：人を呼び、除細動器のパッドを貼る
  → 止まっても報告（12誘導でQT、K・Mg、QTをのばす薬）

### ③ T波の上

#### R on T
- **いまの下書き**：すぐ報告。12誘導とK・Mgを確認、除細動器を近くに
- **根拠**
  - LITFL（L5）："TdP is initiated when a PVC occurs during the preceding T wave, known as 'R on T' phenomenon"。Example 5："The QT interval is markedly prolonged … with each PVC falling on the preceding T wave (= 'R on T' phenomenon). This ECG is extremely high risk for TdP"。
  - LITFL（L3）："Frequent PVCs are usually benign, except in the context of an prolonged QTc, when they may predispose to malignant ventricular arrhythmias such as Torsades de Pointes by causing 'R on T' phenomenon"。
  - LITFL（L6）：虚血性心疾患では VF の前ぶれに "Premature ventricular contractions (PVCs) … R on T phenomenon … QT prolongation" がある。
  - ESC 2022 の定義："Short-coupled PVC: A PVC that interrupts the T-wave of the preceding conducted beat."
  - Drew 2010（院内のトルサード予防）：QTc が 500 ms を超える、または薬の前より 60 ms 以上のびたときで、ほかの前ぶれ（"new-onset ventricular ectopy, couplets and nonsustained polymorphic ventricular tachycardia initiated in the beat after a pause" など）があれば "prompt action is indicated. Appropriate actions include alternative pharmacotherapy; assessment of potentially aggravating drug-drug interactions, bradyarrhythmias, or electrolyte abnormalities; and the ready availability of an external defibrillator."
    → QTがのびて前ぶれの波形が出たら、すぐ動く。薬の見直し・電解質の確認・**除細動器をすぐ使えるように**。
  - ESC 2022 Table 3・8：12誘導、電解質など戻せる原因を調べる（上のショートランと同じ）。
- **判定**：「12誘導」「K・Mg」「除細動器を近くに」は**そのままでよい**（Drew 2010 にほぼそのままの文がある）。ただし「すぐ報告」の強さは**QTが長いとき**にとくに根拠があるので、QTを見ることを入れると正確になります。
- **直した案**
  → すぐ報告。12誘導でQT、K・Mgを確認、除細動器を近くに

### ④ QRSがない

#### 粗いVF
- **いまの下書き**：反応を確認し、人を呼んでCPR＋電気ショック
- **根拠**
  - ERC 2025（院内）："All hospital staff should be able to recognise cardiac arrest rapidly, call for help, start CPR and defibrillate (attach an AED and follow the AED prompts, or use a manual defibrillator)." Fig.3："Signs of life? Check for responsiveness and normal breathing … NO or any doubt → CARDIAC ARREST"。
    → 院内のすべての職員が、心停止にすぐ気づき、人を呼び、CPRを始め、AED（または手動の除細動器）で電気ショックできるようにする。反応・正常な呼吸がない、または**迷ったら心停止として動く**。
  - AHA 2025 Part 9 COR 1："defibrillators … are recommended to treat tachyarrhythmias requiring a shock such as ventricular fibrillation or pulseless ventricular tachycardia." Figure 2："Start CPR … Attach monitor/defibrillator"。
  - LITFL（L6）："VF should never be diagnosed from the 12-lead ECG!"（VFらしく見える波形でも、まず患者を見る理由になる）
- **判定**：**そのままでよい**。「AED」の語を入れると病棟の動きとして具体的になります（任意）。
- **直した案**（任意）
  → 反応を確認し、人を呼んでCPR＋AED（電気ショック）

#### 細かいVF
- **いまの下書き**：CPR＋電気ショック（心静止と迷えば、CPRを続ける）
- **根拠**
  - ERC 2025（表1、2021 との比較欄）："The 2015 ERC ALS Guideline stated that if there is doubt about whether the rhythm is asystole or extremely fine VF, do not attempt defibrillation; instead, continue chest compressions and ventilation. We wish to clarify that when the rhythm is clearly judged to be VF a shock should be given. Immediate defibrillation of (ventricular fibrillation) VF of any amplitude (even fine VF) should be attempted."
    → 2015年版の「心静止か細かいVFか迷えばショックせずCPRを続ける」を改め、**VFと判断したら、細かいVFでも電気ショック**とした。
  - ERC 2025 本文："A shock should be given if the ALS provider is in doubt whether fine VF or asystole are displayed on the monitor. … If rescuers are not confident in making shockable versus non-shockable rhythm decisions rapidly (within 5 s) during a resuscitation attempt they should use the defibrillator in an AED mode."
    → **細かいVFか心静止か迷ったら、ショックする**。5秒以内に判断する自信がなければ、除細動器を**AEDモード**にして機械に解析させる。
  - AHA 2025 Part 9：細かいVFと心静止の区別についての推奨文は、本文を検索しても見つからなかった（"fine"・"amplitude" の語なし）。"The effectiveness of VF waveform analysis to guide the acute management … has not been established"（COR 2b）のみ。
  - JRC 2020 ALS：細かいVFと心静止の区別について書いた文は見つからなかった。
  - LITFL（L6）："Amplitude decreases with duration (coarse VF –> fine VF)" "ultimately degenerating into asystole"。
- **判定**：**直したほうがよい（いちばん大事）**。「心静止と迷えば、CPRを続ける」は **ERC 2015 の文言**で、**ERC 2025 ではっきり改められた**（迷えばショック、自信がなければ AED モード）。いまの下書きは最新の ERC と逆のことを言っています。AHA 2025 にはこの点の推奨がなく、JRC 2025 は本文を確かめられませんでした。
- **直した案**
  → CPR＋電気ショック（心静止と迷えば、AEDの解析にまかせる）
  （病棟の看護師がとる動きとしては「AEDに判断させる」が、ERC 2025 の "use the defibrillator in an AED mode" とも合い、施設の差にも左右されにくい言い方です）

#### 心静止
- **いまの下書き**：すぐCPR。並行して電極と感度を確認（ショックはしない）
- **根拠**
  - ERC 2025 Fig.2：非ショック適応（PEA, Asystole）は "Give adrenaline every 3-5 minutes / Immediately resume chest compressions for 2 minutes"。本文："Whenever a diagnosis of asystole is made start CPR, and when chest compressions are paused for a rhythm check look at the ECG carefully for the presence of P waves because this may respond to cardiac pacing." "Do not attempt pacing for asystole unless P waves are present"。
    → 心静止ならまずCPR。リズムチェックでP波が残っていないか見る（P波があればペーシングが効くことがある）。
  - AHA 2025 Figure 2：Asystole/PEA → "Epinephrine ASAP"、"CPR 2 min"、ショックの枝なし。COR 3（No Benefit）："Routine use of electrical pacing is not recommended during the resuscitation of an established adult cardiac arrest."
  - JRC 2020：「無脈性電気活動（PEA）や心静止であれば，ただちに胸骨圧迫からCPRを再開し2分間行う」。
  - 「電極と感度を確認」：**AHA 2025・ERC 2025・JRC 2020 の本文では見つからなかった**（AHA 2010 以前の ACLS 教材にあった「フラットラインの確認」に当たる内容と思われるが、原典を確かめられなかった）。
- **判定**：「すぐCPR」「ショックはしない」は**そのままでよい**。「並行して電極と感度を確認」は**根拠が見つからない**（最新ガイドラインの本文には無い）。ただし、CPRを遅らせない「並行して」の書き方なので、実務の確認として置くのは差し支えないと考えます。ガイドラインに書いてあるように見せない言い方にするのが安全です。「人を呼ぶ」が無いので足したほうがよいです。
- **直した案**
  → 人を呼び、すぐCPR（ショックはしない）
  → 並行して、電極外れ・感度も確認

### ⑤ 波形では分からない

#### PEA（ふつうに見える／遅く幅広い）
- **いまの下書き**：脈がなければ、すぐCPR（ショックはしない）
- **根拠**
  - AHA 2025 Figure 2：Asystole/PEA → "Epinephrine ASAP" → "CPR 2 min … Treat reversible causes"。"Reversible Causes：Hypovolemia, Hypoxia, Hydrogen ion (acidosis), Hypo-/hyperkalemia, Hypothermia, Tension pneumothorax, Tamponade, cardiac, Toxins, Thrombosis, pulmonary, Thrombosis, coronary"。
  - ERC 2025 Fig.2："Identify & treat reversible causes：Hypoxia, Hypovolaemia, Hyper-hypokalaemia / metabolic, Hypothermia, hyperthermia, Toxins, Tamponade (cardiac), Tension pneumothorax, Thrombosis (coronary / pulmonary)"。
  - ERC 2025 Fig.3："Signs of life? … NO or any doubt → CARDIAC ARREST"（脈がはっきりしなければ心停止として動く）。
  - LITFL（L8）："Need to seek and treat the underlying cause" "The causes of PEA are widely thought of as the 4Hs and 4Ts"、Littman の考え方："Narrow-complex PEA is generally due to mechanical problems … Wide-complex PEA is typically due to metabolic problems, or ischemia and left ventricular failure"。"studies suggest that first responders are poor at accurately performing pulse checks during cardiac arrests"。
    → PEAは原因（4H4T）を探して治すことが要。狭いQRSは機械的な原因（タンポナーデ・緊張性気胸・肺塞栓・循環血液量減少）、幅広いQRSは代謝（高Kなど）・虚血が多い。脈の確認は難しい。
  - JRC 2020：「蘇生の全ての段階において，心停止の可逆的な原因の検索と是正が求められる．原因検索は心停止に至った状況や既往歴，身体所見等から行う」。
- **判定**：**そのままでよい**。ただし「人を呼ぶ」と「原因（4H4T）」が抜けています。看護師は原因を治す人ではありませんが、直前の様子・出血・SpO2・K・体温・薬などの情報を集めて伝えることは原因検索の一部です。
- **直した案**
  → 脈がなければ、人を呼び、すぐCPR（ショックはしない）
  → 原因（4H4T）につながる情報を伝える

---

## 3. 全体として気をつけること

### 3-1. 看護師がすること／医師がすること の分け方
- どのガイドラインも「看護師」「医師」で役割を分けては書いていません（AHA・ERC は「health care professionals」「ALS providers」「hospital staff」と書く）。そのうえで、本文から言えることは次のとおりです。
  - **病棟の誰もがすること**（ERC 2025）："recognise cardiac arrest rapidly, call for help, start CPR and defibrillate (attach an AED and follow the AED prompts, or use a manual defibrillator)"。脈のある急変では Fig.3 の "Call resuscitation / medical emergency team … ABCDE assessment … Attach monitoring … Obtain IV access" と、蘇生チームへの SBAR での引き継ぎ。
  - **鎮静や判断が要るもの**：同期電気ショック（"Conscious patients require careful anaesthesia or sedation"＝ERC）、経皮ペーシング（"often painful in the conscious patient and procedural tolerance may necessitate sedation"＝AHA）、薬（アトロピン・アドレナリン・アミオダロン・Mg）は、鎮静・薬の指示が要るので医師の判断として描くのが安全です。
  - **手動の除細動器**：ERC 2025 は "Manual defibrillators should only be used by rescuers who can quickly and accurately identify a cardiac arrest rhythm (within 5 s)"。自信がなければ AED モード。看護師が手動で除細動するかは**施設の手順と教育による**（日本の法令上の扱いは今回確かめていません）。リールでは「電気ショック（AED）」と書くのが無難です。
- **「ペーシングの準備」は看護師の動きとして書いてよいか**：書いてよいと考えます。ERC Fig.9 はモビッツII型・幅広QRSの完全房室ブロックを「心静止の危険」とし、経皮ペーシングへ進む流れです。準備（経皮ペーシングのできる除細動器を持ってくる、パッドを貼る、モニターをつなぐ）は医師の判断を待たずにできる「先回り」です。ペーシングを始める・出力を決める・鎮静するのは医師、と分けて見せるとよいです。言い方は「ペーシングの準備（パッド）」など、準備であることがわかるものに。
- **「除細動器を近くに」**：Drew 2010 の "the ready availability of an external defibrillator" がほぼそのままの根拠です（QT延長＋前ぶれ波形のとき）。
- **「12誘導」**：AHA 2025 Figure 6・8、ERC 2025 Fig.8・9（"Record 12-lead ECG"）、ESC 2022 Table 3（I, C）。看護師がとってよいものとして描いてよいです。
- **「K・Mg」**：ESC 2022 Table 8（I, C、電解質など戻せる原因を調べる）、AHA 2025（トルサードでとくに低Kを直す）、ESC 2022 Table 9（トルサードに Mg＋K）。看護師の動きは「採血して値を確認・報告」までで、補正は医師の指示です。

### 3-2. 言い切ってよいところ
- VF・脈のないVT → 人を呼ぶ・CPR・電気ショック（AED）（AHA・ERC・JRC 共通）
- 心静止・PEA → ショックはしない、すぐCPR（AHA・ERC・JRC 共通）
- 脈があるかはっきりしなければ心停止として動く（ERC Fig.3 "NO or any doubt"）
- トルサードは止まっても再発しやすいので報告（AHA 2025・LITFL）
- 続く多形性VTは、脈があっても電気ショックの適応（AHA 2025 COR 1）

### 3-3. 施設の手順・状況によるところ（言い切りすぎない）
- 細かいVFか心静止か迷うときの扱い：ERC 2025 は「迷えばショック／AEDモード」に改めたが、AHA 2025 には該当する推奨がなく、JRC 2025 は本文未確認。「AEDの解析にまかせる」がどの立場とも矛盾しにくい言い方です。
- 単形性VTで安定しているときの電気ショック：ERC は心臓病があれば勧めるが、AHA は迷走神経刺激・薬が先で、効かなければ同期電気ショック。看護師の動きとしては「報告・パッド・12誘導」までにとどめれば差は出ません。
- モビッツII型・完全房室ブロック：AHA はアトロピンが先、ERC は幅広QRSの高度房室ブロックにアトロピンを使わない。薬の名前は出さないのが安全です。
- 手動の除細動器を看護師が使うか、院内の急変コール（番号・名前）：施設ごとに違う。
- 院内の急変コール・RRT（迅速対応チーム）を呼ぶ基準：施設ごと。

### 3-4. 用語・言い回し（日本語）
- JRC 2020 の言い方：「VF/無脈性VT」「無脈性電気活動（PEA）」「心静止」「電気ショック」「可逆的な原因の検索と是正」「トルサードドポワント」。下書きの「電気ショック」は JRC と同じで問題ありません。
- 「ショートラン」は日本の臨床の通称で、ガイドラインの用語は「非持続性心室頻拍（NSVT）」。下書きどおり併記がよいです。定義は「3拍以上・30秒未満・100/分超」（ESC 2022・LITFL）。

### 3-5. 抜けている大事な動き（まとめ）
1. **不安定の徴候**：意識・血圧に加えて、胸痛（虚血）・息苦しさ（心不全）・ショックの徴候（冷汗・末梢冷感など）（AHA Figure 6・8、ERC Fig.8・9）。
2. **心停止の「人を呼ぶ・AED」**：粗いVF以外の心停止の行（心静止・PEA・脈のないVT）にも「人を呼ぶ」を入れる（ERC 2025 院内アルゴリズム）。
3. **PEAの原因（4H4T）**：AHA・ERC のアルゴリズム図の両方にある。
4. **多形性VT・トルサードで脈があるとき**：パッドを貼る・続けば電気ショック。
5. **細かいVF**：迷えば AED モード（ERC 2025 の改訂）。

---

## 4. 確かめられなかったこと

1. **AHA・ERC の公式サイトの本文**：ahajournals.org、cpr.heart.org、resuscitationjournal.com、sciencedirect.com、academic.oup.com、escardio.org は、この環境から 403 で開けませんでした。AHA 2025 Part 9・ERC 2025 ALS・ESC 2022 は、第三者サイト・大学リポジトリにある journal 版 PDF の写しで本文を読みました（AHA は ahajournals の透かし、ERC は Resuscitation 誌の版面、ESC は OUP の透かし入り）。公式版と一字一句同じかは確かめていません。
2. **JRC蘇生ガイドライン2025 の本文**：最終版は書籍（2026-07-13 発刊、医学書院）のみで、ALS の章（徐脈・頻拍・細かいVF・トルサードの扱い、日本語の言い回し）は読めませんでした。パブリックコメント版（2025-10）の PDF も見つけられませんでした。日本語の言い回しは JRC 2020 で確かめています。
3. **心静止で「電極（誘導）と感度を確かめる」**：AHA 2025 Part 9・ERC 2025 ALS・JRC 2020 ALS の本文では見つかりませんでした。以前の AHA ACLS 教材にあった内容と思われますが、原典は確かめていません。
4. **AHA 2025 で「細かいVFか心静止か迷うとき」**：該当する推奨を見つけられませんでした（本文に "fine" "amplitude" の語なし）。ERC 2015 の「迷えばCPRを続ける」の原文は、ERC 2025 の中の引用で確認しただけで、2015 年版の原本は開いていません。
5. **AHA 2025 BLS（Part 7）での脈の確認時間（10秒以内など）**：今回は開いていません。脈の確認は ERC 2025 Fig.3（"NO or any doubt"）で確かめました。
6. **Mg の目標値**：確かめられませんでした。K は Drew 2010 に "Repletion of potassium to supratherapeutic levels of 4.5 to 5 mmol/L may also be considered, although there is little evidence to support this practice (Class IIb, Level of Evidence: C)"（トルサードのとき）がありますが、根拠は弱いと本文に書かれています。リールに数値を出すのはおすすめしません。
7. **LITFL の単独ページ**（R on T、Asystole、トルサードの CCC ページ）：見つからず、ECG Library の該当項目（PVC・TdP・VF）と CCC（VT・PEA・Transcutaneous Pacing）で代わりに確かめました。
8. **日本の法令で、看護師が手動の除細動器・経皮ペーシングをどこまでしてよいか**：調べていません。リールでは「施設の手順による」とし、言い切らないのが安全です。
9. **ESC 2022 の Essential Messages**（短い公式要約）：403 で開けず、本編で確かめました。
