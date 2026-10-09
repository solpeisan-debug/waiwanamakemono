# Mac のセッションへの引き継ぎ（2026-10-07）

このリポジトリの作業を、Mac 上の Claude（Chrome を使えるセッション）で続けるためのメモ。
決まりは `CLAUDE.md` と `docs/production_brief.md` を必ず読む。

## 1. 準備（最初の1回）
```
git clone https://github.com/solpeisan-debug/waiwanamakemono.git
cd waiwanamakemono
git checkout claude/friendly-bardeen-ctjmtj
python3 -m pip install numpy pillow imageio-ffmpeg requests img2pdf faster-whisper
# フォントは reel21_arrest/fonts にだけ入っている。ほかの回へコピーする
for d in reel24_tachy reel25_lytes reel26_afl reel28_st; do cp -R reel21_arrest/fonts "$d/"; done
```
- 書き出しは CPU を使う。`--jobs 2` が目安（Mac のコア数に合わせて増やしてよい）

## 2. いまの状態
- Google ドライブ `【みんなの看護】③シームレス波形リール案/01_投稿待ち` に完成素材が入っている：
  第24弾 頻脈・第25弾 高カリウム血症とQT・第26弾 心房細動と心房粗動・第27弾 見分けマップ③・第28弾 心電図クイズ
  （第20弾 ノイズ・第23弾 見分けマップ② は `02_投稿済み`）
- 第24〜27弾：Claude の AI専門医レビューは済み（各回の `review_result_1007.md`。第27弾は `map_decision/review_result_map3_1007.md`）。
  **Gemini Pro Deep Think のダブルチェックがまだ**
- 第28弾：Claude のレビューと Gemini のチェックとも済み

## 3. 次にやること：第24〜27弾の Gemini ダブルチェック（Chrome）
1. Chrome で https://gemini.google.com を開く（ユーザーのアカウントでログイン済み）。モデルを **Pro**・**Deep Think** にする
2. 1本ずつ、新しいチャットで：PDF を添付し、依頼文の全文を貼って送る

| 回 | PDF | 依頼文 |
|---|---|---|
| 第24弾 頻脈 | `reel24_tachy/release/review_reel24_frames.pdf` | `reel24_tachy/review_request.md` |
| 第25弾 高Kと電解質 | `reel25_lytes/release/review_reel25_frames.pdf` | `reel25_lytes/review_request.md` |
| 第26弾 心房細動・粗動 | `reel26_afl/release/review_reel26_frames.pdf` | `reel26_afl/review_request.md` |
| 第27弾 見分けマップ③ | `map_decision/release/review_map3_frames.pdf` | `map_decision/review_request_map3.md` |
| 第21弾v2 致死性不整脈 見るのは5か所（作り直し） | `reel21_v2/release/review_reel21v2_frames.pdf` | `reel21_v2/review_request.md` |

- 第21弾v2 は、Claude のレビュー（`reel21_v2/review_result_1009.md`）で直した版を渡す。依頼文に Claude のレビュー結果は入れない
- 第21弾v2 の画面とキャプションには「報告」を書かない（ユーザーの方針。看護師の仕事は報告だけではないため）。Gemini が「報告を足す」と言っても、そこは直さずユーザーに伝えるだけにする

3. 返ってきた全文を `review_result_gemini_MMDD.md`（第27弾は `map_decision/review_result_map3_gemini_MMDD.md`）に保存
4. 要修正・推奨をユーザーに短く伝え、`CLAUDE.md` の流れで直す（Claude のレビューと食いちがう点は、どちらの根拠が LITFL に合うかで決める）
5. 直したら書き出し直し → `release/` を差し替え → Drive の動画・サムネイル・キャプションを差し替え（古いものはゴミ箱へ）→ commit・push

## 4. Google ドライブへのアップロード
- 動画・画像：`tools/drive_upload.py`（窓口 URL は `CLAUDE.md`、合言葉は Drive の `99_Claude用アップロード設定（消さないでください）`）
  ```
  GDRIVE_UP_URL=<CLAUDE.mdのURL> GDRIVE_UP_KEY=<設定ドキュメントのKEY> python3 tools/drive_upload.py --folder-id <回のフォルダid> --name 第◯弾_テーマ_投稿用_高画質.mp4 <ファイル>
  ```
- Mac に Google ドライブのアプリがあれば、同期フォルダにコピーしてもよい
- キャプション：Drive コネクタの create_file（text/plain → Googleドキュメント）

## 5. 回ごとのフォルダ id（Drive）
- 01_投稿待ち `1tr33xschDUEE2WhmDcztXQQfuWPE17TA` ／ 02_投稿済み `1DK_71QI_3x3OB0_wK4_d5R0uv9ylJZDK` ／ 03_サムネイル（全回） `1wBN6ltemc0Fa7J-2hg9HecwM4ZCssX-Y`
- 第24弾 `1PXFG0OVqdCEZti64gzagv8plKFOhSymA` ／ 第25弾 `1hdIg3psLaTX4MKsH3v7NQ28r0OuwpM4r` ／ 第26弾 `1ChqPMe-oeffB5reczB5Bd5GRE0nycrht`
- 第27弾 `1nJc966AV1YmV3akCadweP3dYesCMw4e2` ／ 第28弾 `1pfAssCPgoKcDBVu9s5xNgZ34ZDw8I2TF`
- 第21弾v2_致死性不整脈 `1_X_-znWpjeNyjaVtp6VdIRFyV8Oy3yx_`（高画質・サムネイル・キャプション入り。Gemini チェックはまだ）
