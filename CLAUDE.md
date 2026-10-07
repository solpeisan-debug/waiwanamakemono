# 心電図リール（@nurse_polarbearden）の作業メモ

- 返事は日本語で書く
- **チャットで送るファイルは、毎回ちがう名前にする**：`第◯弾_テーマ_中身_MMDD-HHMM.拡張子`（日本時間）
  - 例：`第20弾_ノイズ_依頼文_1004-0129.md`、`第20弾_ノイズ_キャプション_1004-0129.txt`、
    `第20弾_ノイズ_フレーム等倍PDF_1004-0129.pdf`、`第20弾_ノイズ_サムネイル_1004-0129.png`、`第20弾_ノイズ_映像_1004-0129.mp4`
  - 各回の `out/send/` にコピーしてから送る（元のファイル名は変えない）
- キャプションの「※参考」の下・ハッシュタグの上に、`caption_template.txt`（リポジトリ直下）の3行をそのまま入れる。
  「（caption_template.txt の定型3行…）」のような目印は残さない
- チャットで送れるのは30MBまで。高画質版はGitHubの各回の `release/` に置いてリンクを渡す
  - チャットで映像を送るときは、それが「通常版（高画質版ではない）」ことと、高画質版がいつ・どこに届くかを必ず書く。
    投稿に使ってよいかも一言そえる（高画質版を待つか、通常版で出してよいか）
- **完成素材は Google ドライブにも入れる**（2026-10-07 から）：`【みんなの看護】③シームレス波形リール案`（id `1Tcbidrst1CHnU3sXjVJi16xPWq92_tNH`）
  - `01_投稿待ち`（`1tr33xschDUEE2WhmDcztXQQfuWPE17TA`）に回ごとのフォルダ `第◯弾_テーマ`：`第◯弾_テーマ_投稿用_高画質.mp4`・`第◯弾_テーマ_サムネイル.png`・`第◯弾_テーマ_キャプション`（Googleドキュメント）
  - `02_投稿済み`（`1DK_71QI_3x3OB0_wK4_d5R0uv9ylJZDK`）、`03_サムネイル（全回）`（`1wBN6ltemc0Fa7J-2hg9HecwM4ZCssX-Y`）にもサムネイル
  - 動画・画像は `tools/drive_upload.py`（ユーザーの Apps Script 窓口経由の再開可能アップロード。50MB 超も可）。
    窓口URL：`https://script.google.com/macros/s/AKfycbwz-Bfs64tE-NLql3GdvR0e1t9cb5wiMZZIAvbBHcsGOwrtfYyCx5zYbrkjJEbO9YA/exec`。
    合言葉（KEY）は Drive の `99_Claude用アップロード設定（消さないでください）` を Drive コネクタで読み、環境変数 `GDRIVE_UP_KEY` で渡す（リポジトリ・チャットに書かない）
  - キャプションは Drive コネクタの `create_file`（textContent・text/plain → Googleドキュメントに変換）。`read_file_content` では絵文字が化けて見えるが、中身は正しい（`download_file_content` の text/plain 書き出しで確かめる）
- ナレーションでは「すぐ報告」と言わない（画面の赤い「→ すぐ報告」とキャプションで伝える）
- 医学的な根拠は LITFL が第一。LITFL以外を使うときは、出典を確認して書く
- 専門医レビューには「等倍フレームPDF＋依頼文（台本・キャプション入り）」を渡す（各回の `make_review_pdf.py`）
- **AI専門医のレビューは、Claude が自分で行う**（2026-10-07 から。以前はユーザーが Gemini Pro Deep Think に手で頼んでいた）
  - 作った担当とは別の、新しいエージェントを「AI専門医」として立てる（作った人の考えを引きずらないため）。読むだけで、ファイルは直さない
  - 渡すもの：依頼文（`review_request.md`）と等倍フレーム（`out/review_frames/*.png` または PDF）。根拠は LITFL の本文を curl で確かめる
  - 返す形はこれまでの Gemini と同じ：パターンごと・「とくに見てほしい点」ごとに 判定（OK／要修正／推奨）・理由・直し方（言い換えまで）。LITFL 以外の根拠は出典名を書く
  - 結果は各回の `review_result_MMDD-HHMM.md` に残し、ユーザーに要点を伝えてから直す
  - **別会社のAI（Gemini Pro Deep Think）でのダブルチェックも Claude がやる**：Claude のレビューで直したあと、
    直した版の PDF と依頼文を、Claude が Chrome で Gemini に渡して結果をもらう（ユーザーにはさせない）。
    依頼文には Claude のレビュー結果を入れない（先入観を与えず、別の目で見てもらうため）。
    Chrome はユーザーの Mac のセッションでしか使えない。クラウドのセッションでは使えないので、手順は `docs/handoff_mac.md`
