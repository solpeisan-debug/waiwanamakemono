"""完成素材（動画・サムネイルなど）を Google ドライブに入れる。

Drive 側の窓口は tools/drive_upload_apps_script.gs（ユーザーの Apps Script ウェブアプリ）。
窓口の URL と合言葉は、Drive の「99_Claude用アップロード設定」ドキュメントにある（リポジトリには書かない）。
コネクタで読んで、環境変数で渡す：

    GDRIVE_UP_URL=... GDRIVE_UP_KEY=... python3 tools/drive_upload.py --folder-id <id> ファイル...
    GDRIVE_UP_URL=... GDRIVE_UP_KEY=... python3 tools/drive_upload.py --parent-id <id> --mkdir 第28弾_心電図クイズ ファイル...

--name を付けると、Drive での名前を変えられる（ファイル1つのとき）。
ファイルの中身は窓口を通らず、Drive の再開可能アップロードに 8MB ずつ直接送る。
"""
import argparse
import json
import mimetypes
import os
import sys

import requests

CHUNK = 32 * 256 * 1024          # 8MB（256KB の倍数）


def call(action, **kw):
    url, key = os.environ['GDRIVE_UP_URL'], os.environ['GDRIVE_UP_KEY']
    r = requests.post(url, data=json.dumps(dict(key=key, action=action, **kw)),
                      headers={'Content-Type': 'application/json'}, timeout=120)
    r.raise_for_status()
    out = r.json()
    if 'error' in out:
        sys.exit(f'窓口のエラー: {out}')
    return out


def upload(path, folder_id, name=None):
    name = name or os.path.basename(path)
    size = os.path.getsize(path)
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    session = call('upload', folderId=folder_id, name=name, size=size, mimeType=mime)['uploadUrl']
    with open(path, 'rb') as f:
        pos = 0
        while pos < size:
            data = f.read(CHUNK)
            end = pos + len(data) - 1
            r = requests.put(session, data=data, timeout=600,
                             headers={'Content-Length': str(len(data)),
                                      'Content-Range': f'bytes {pos}-{end}/{size}'})
            if r.status_code in (200, 201):
                info = r.json()
                print(f"OK {name}  {int(info.get('size', size))/1e6:.1f}MB  {info.get('webViewLink', '')}")
                return info
            if r.status_code != 308:
                sys.exit(f'アップロードのエラー {r.status_code}: {r.text[:500]}')
            rng = r.headers.get('Range')            # 例 bytes=0-8388607
            pos = int(rng.split('-')[1]) + 1 if rng else 0
            f.seek(pos)
            print(f'  {name}: {pos/1e6:.0f}/{size/1e6:.0f}MB', flush=True)
    sys.exit(f'{name}: 最後まで送れなかった')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--folder-id')
    ap.add_argument('--parent-id')
    ap.add_argument('--mkdir', help='--parent-id の中に、この名前のフォルダを作って（あれば使って）入れる')
    ap.add_argument('--name')
    o = ap.parse_args()
    folder = o.folder_id
    if o.mkdir:
        folder = call('mkdir', folderId=o.parent_id, name=o.mkdir)['id']
        print('フォルダ', o.mkdir, folder)
    assert folder, '--folder-id か --parent-id と --mkdir を指定する'
    for p in o.files:
        upload(p, folder, o.name if len(o.files) == 1 else None)


if __name__ == '__main__':
    main()
