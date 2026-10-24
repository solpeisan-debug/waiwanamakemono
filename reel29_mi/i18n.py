"""第29弾：画面の文字・ナレーションの文を、言語ごとの表（i18n/<lang>.json）から読む。

切り替え：環境変数 REEL29_LANG=ja|zh-TW|en（既定 ja）。
_meta：font（字体）・read_cps/read_add/read_unit（字幕を読める長さ）・electrode_colors（IEC/AHA）・vo_dir（声の置き場所）・file_suffix（出力の名前）
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.environ.get('REEL29_LANG', 'ja')
_P = os.path.join(HERE, 'i18n', f'{LANG}.json')
if not os.path.exists(_P):
    raise SystemExit(f'言語の表がない：{_P}')
_D = json.load(open(_P, encoding='utf-8'))
_JA = json.load(open(os.path.join(HERE, 'i18n', 'ja.json'), encoding='utf-8'))
META = dict(_JA['_meta'], **_D.get('_meta', {}))


def T(key):
    """表の文字。その言語の表になければ日本語の表（翻訳が抜けているときに気づけるよう、--check で知らせる）。"""
    if key in _D:
        return _D[key]
    MISSING.add(key)
    return _JA[key]


MISSING = set()


def path(rel):
    return os.path.join(HERE, rel)


def suffix():
    return META.get('file_suffix', '' if LANG == 'ja' else '_' + LANG)
