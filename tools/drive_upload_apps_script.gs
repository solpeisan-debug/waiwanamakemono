/**
 * Claude（クラウドのセッション）から、完成素材（動画・サムネイル）を Google ドライブに入れるための小さな窓口。
 *
 * しくみ：Claude がこのウェブアプリに「ファイル名・大きさ・入れるフォルダ」を送ると、
 * このスクリプトが Drive の「再開可能アップロード」の受付URLを作って返す。
 * Claude はそのURLに動画を直接送る（ファイルの中身はこのスクリプトを通らない）。
 *
 * 安全のため：
 * - 合言葉（KEY）が合わないと何もしない。KEY は setup() が作り、Drive の設定ドキュメントにだけ書く
 * - 入れられるのは【みんなの看護】③シームレス波形リール案 フォルダの中だけ。1ファイル 200MB まで
 * - ファイルの削除や読み出しはできない
 *
 * 使い方（最初の1回だけ）：
 * 1. https://script.google.com で「新しいプロジェクト」→ このコードを全部貼る → 保存
 * 2. 「デプロイ」→「新しいデプロイ」→ 種類「ウェブアプリ」
 *    次のユーザーとして実行：自分 ／ アクセスできるユーザー：全員 →「デプロイ」→ 権限を承認
 * 3. 上の関数の選択で「setup」を選んで「実行」
 *    → フォルダに「99_Claude用アップロード設定（消さないでください）」ができれば完了
 */

const FOLDER_ID = '1Tcbidrst1CHnU3sXjVJi16xPWq92_tNH'; // 【みんなの看護】③シームレス波形リール案
const MAX_BYTES = 200 * 1024 * 1024;
const CONFIG_NAME = '99_Claude用アップロード設定（消さないでください）';

function setup() {
  const props = PropertiesService.getScriptProperties();
  let key = props.getProperty('KEY');
  if (!key) {
    key = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('KEY', key);
  }
  const url = ScriptApp.getService().getUrl();
  if (!url) throw new Error('先に「デプロイ」→「新しいデプロイ」でウェブアプリとして公開してください');
  const root = DriveApp.getFolderById(FOLDER_ID);
  const old = root.getFilesByName(CONFIG_NAME);
  while (old.hasNext()) old.next().setTrashed(true);
  const doc = DocumentApp.create(CONFIG_NAME);
  doc.getBody().setText('URL: ' + url + '\nKEY: ' + key);
  doc.saveAndClose();
  DriveApp.getFileById(doc.getId()).moveTo(root);
  Logger.log('設定ドキュメントを作りました: ' + url);
}

function isInside_(folder) {
  let f = folder;
  for (let i = 0; i < 10; i++) {
    if (f.getId() === FOLDER_ID) return true;
    const parents = f.getParents();
    if (!parents.hasNext()) return false;
    f = parents.next();
  }
  return false;
}

function out_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  let req;
  try {
    req = JSON.parse(e.postData.contents);
  } catch (err) {
    return out_({ error: 'bad request' });
  }
  const key = PropertiesService.getScriptProperties().getProperty('KEY');
  if (!key || req.key !== key) return out_({ error: 'forbidden' });

  const folder = DriveApp.getFolderById(req.folderId);
  if (!isInside_(folder)) return out_({ error: 'folder not allowed' });

  if (req.action === 'mkdir') {
    const found = folder.getFoldersByName(req.name);
    const sub = found.hasNext() ? found.next() : folder.createFolder(req.name);
    return out_({ id: sub.getId(), url: sub.getUrl() });
  }

  if (req.action === 'upload') {
    const size = Number(req.size);
    if (!(size > 0 && size <= MAX_BYTES)) return out_({ error: 'size not allowed' });
    const res = UrlFetchApp.fetch(
      'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,name,size,webViewLink',
      {
        method: 'post',
        contentType: 'application/json; charset=UTF-8',
        headers: {
          Authorization: 'Bearer ' + ScriptApp.getOAuthToken(),
          'X-Upload-Content-Type': req.mimeType,
          'X-Upload-Content-Length': String(size),
        },
        payload: JSON.stringify({ name: req.name, parents: [req.folderId] }),
        muteHttpExceptions: true,
      }
    );
    if (res.getResponseCode() !== 200) {
      return out_({ error: 'session', code: res.getResponseCode(), body: res.getContentText() });
    }
    const h = res.getHeaders();
    return out_({ uploadUrl: h['Location'] || h['location'] });
  }

  return out_({ error: 'unknown action' });
}
