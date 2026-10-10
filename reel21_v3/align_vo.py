"""第21弾v3 致死性不整脈 見るのは5か所：ナレーション（ElevenLabs の通し読み）を文に切り分け、映像の秒数を声に合わせる。
v2 の align_vo.py と同じ作り。【録音前】台本は下書き（narration.md）。録音が届いたら LINES を書いてから使う。

決めごと：
- 無音を手がかりに文へ切り分ける。継ぎ目は必ず無音の中で切る
- 効果音（モニター音）は声の下で最大 8dB 下げる（サイドチェイン）
- 声は Ren – Smooth & Soothing。ElevenLabs で作り、1.2倍速にしてから使う

秒数の決まり方（データで動く）：
  make_reel21v3.py の表 BLOCKS は、各文の声の長さ VOICE_LEN から組み立てる（パターン：声＋間、と次の対応を読む時間の大きいほう）。
  録音前は字数からの見積もり。このスクリプトが声を測って voice_len.json に書くと、make_reel21v3.py がそれを読み、
  表が声に合わせて組み直される（映像を書き出し直す）。

使い方:
    cp 録音.mp3 out/vo/narration_raw.mp3                          # 1.2倍速にしたもの
    python3 align_vo.py out/vo/narration_raw.mp3 --list         # 声のかたまり（無音で区切ったもの）の一覧。LINES を書く手がかり
    python3 align_vo.py out/vo/narration_raw.mp3 --measure      # 文ごとの長さを測って voice_len.json に書く
    python3 make_reel21v3.py --check && python3 make_reel21v3.py --jobs 2   # 声に合わせた秒数で書き出し直す
    python3 align_vo.py out/vo/narration_raw.mp3                # out/vo/mix.wav と配置表（声＋モニター音）
    python3 align_vo.py out/vo/narration_raw.mp3 --mux          # 映像（out/reel21_v3.mp4）に入れる → out/reel21_v3_vo.mp4
    python3 align_vo.py out/vo/narration_raw.mp3 --mux --hq     # 高画質版に入れる
    python3 align_vo.py out/vo/narration_raw.mp3 --fix out/vo/narration_fix.mp3 --mux
        # 録り直した文（FIX_LINES）だけ、--fix のファイルから差し替える
"""
import argparse
import importlib
import json
import os
import re
import subprocess
import wave

import numpy as np

import make_reel21v3 as m

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

TEXT = m.NARR
ORDER = m.NARR_ORDER        # 冒頭・場所0・（その場所のパターン）…・まとめ・保存

# 通し読みの「声のかたまり」（無音 -40dB・0.25秒以上で区切ったもの。1から数える）を、台本の文にまとめる。
# 【録音前】録音が届いたら --list でかたまりを見て、faster-whisper などの書き起こしで順番と中身を確かめてから書く。
# 例：('冒頭', [1, 2]),  ('場所0', [3, 4]),  ('モビッツII', [5, 6, 7]), …
LINES = []
# 録り直した文（--fix のファイルの声のかたまり番号。0.05秒未満のかたまり＝雑音は数えない）
FIX_LINES = {}
# 文の中の息継ぎ（無音）を、この長さまで縮める（離脱を防ぐ）。録音が届いたら間の長さを見て決める
GAP_CAP = {n: 0.45 for n in ORDER}
PAD_IN, PAD_OUT = 0.06, 0.15          # 声の前後に残す無音（無音の中で切る）
DUCK_DB = 8.0
VO_PEAK = 0.75


def ffmpeg():
    return m.ffmpeg_bin()


def load(path):
    raw = subprocess.run([ffmpeg(), '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def speech_blocks(path, noise='-40dB', d=0.25, min_len=0.0):
    log = subprocess.run([ffmpeg(), '-hide_banner', '-i', path, '-af', f'silencedetect=noise={noise}:d={d}',
                          '-f', 'null', '-'], capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', log)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', log)]
    mm = re.search(r'Duration: (\d+):(\d+):([\d.]+)', log)
    dur = 3600*float(mm.group(1)) + 60*float(mm.group(2)) + float(mm.group(3))
    blocks, prev = [], 0.0
    for a, b in zip(st, en):
        if a > prev + max(0.01, min_len):
            blocks.append((prev, a))
        prev = b
    if dur > prev + 0.05:
        blocks.append((prev, dur))
    return blocks


def cut(audio, blocks, ix, gap_cap=None):
    """声のかたまり ix をつないで1文にする。gap_cap があれば、かたまりの間の無音をその長さまで縮める
    （無音の前後を gap_cap/2 ずつ残し、まん中だけ切るので、声には触れない）。"""
    a = blocks[ix[0]-1][0] - PAD_IN
    b = blocks[ix[-1]-1][1] + PAD_OUT
    if gap_cap is None:
        return audio[max(0, int(a*SR)):int(b*SR)]
    # 2026-10-10 直した（第25弾と同じ直し）：前は無音のまん中から gap_cap ぶんを「切り取って」いた
    # （0.45〜0.9秒の間が 0.0〜0.05秒になり、小さな語尾が切れていた）。いまは、間の前後を gap_cap/2 ずつ残して、
    # まん中の余りだけを切る（＝間は gap_cap の長さになる。声の終わりの小さな音にも触れない）
    parts, t = [], a
    for j in range(len(ix) - 1):
        g0, g1 = blocks[ix[j]-1][1], blocks[ix[j+1]-1][0]
        if g1 - g0 > gap_cap:
            parts.append(audio[max(0, int(t*SR)):int((g0 + gap_cap/2)*SR)])
            t = g1 - gap_cap/2
    parts.append(audio[max(0, int(t*SR)):int(b*SR)])
    return np.concatenate(parts)


def segments(src, fix=None):
    assert LINES, 'LINES がまだ空（録音前）。--list でかたまりを見て、LINES を書く'
    assert [n for n, _ in LINES] == ORDER, 'LINES の順番が台本（NARR_ORDER）とちがう'
    blocks = speech_blocks(src)
    need = max(max(ix) for _, ix in LINES)
    assert len(blocks) == need, f'声のかたまりが {len(blocks)} 個（LINES の想定 {need} 個）。LINES を見直す'
    audio = load(src)
    segs = {name: cut(audio, blocks, ix, GAP_CAP.get(name)) for name, ix in LINES}
    if fix:
        fb = speech_blocks(fix, min_len=0.05)
        assert len(fb) == max(max(ix) for ix in FIX_LINES.values()), f'録り直しの声のかたまりが {len(fb)} 個'
        fa = load(fix)
        for name, ix in FIX_LINES.items():
            segs[name] = cut(fa, fb, ix, GAP_CAP.get(name))
    return segs


def plan(mod):
    """各文を置く時刻：表 BLOCKS の声の始まり（v0）。保存は最後のブロックの save0。"""
    starts = {b['key']: b['v0'] for b in mod.BLOCKS}
    starts['保存'] = mod.END_B['save0']
    return starts


def main():
    global m
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--list', action='store_true', help='声のかたまりの一覧を出す')
    ap.add_argument('--measure', action='store_true', help='文ごとの長さを voice_len.json に書く')
    ap.add_argument('--fix', help='録り直した文のファイル（FIX_LINES の文を差し替える）')
    ap.add_argument('--mux', action='store_true')
    ap.add_argument('--hq', action='store_true', help='高画質版（out/reel21_v3_hq.mp4）に入れる。音声 320k')
    o = ap.parse_args()

    if o.list:
        for k, (a, b) in enumerate(speech_blocks(o.src), 1):
            print(f'{k:3d}  {a:7.2f}–{b:7.2f}  ({b-a:.2f}s)')
        print('台本の文の順番：', ' → '.join(ORDER))
        return

    segs = segments(o.src, o.fix)
    lens = {n: round(len(segs[n]) / SR, 3) for n in ORDER}
    if o.measure:
        with open(m.VOICE_LEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(lens, f, ensure_ascii=False, indent=1)
        print(m.VOICE_LEN_FILE)
        m = importlib.reload(m)
        print(f'声に合わせた映像の長さ {m.DUR:.2f}秒。make_reel21v3.py --check で表を見て、書き出し直す')
        return
    if not m.VOICE_MEASURED:
        print('注意：voice_len.json がない（映像は見積もりの秒数のまま）。先に --measure')
    for n in ORDER:
        if abs(lens[n] - m.VOICE_LEN[n]) > 0.05:
            print(f'注意：{n} の声 {lens[n]:.2f}秒 ≠ 表の {m.VOICE_LEN[n]:.2f}秒（--measure をやり直す）')
    starts = plan(m)

    # 検算：重なり・パターンの声の終わりから次の強調まで 0.4秒以上
    rows, ok = [], True
    nxt_block = {b['key']: (m.BLOCKS[k+1]['start'] if k + 1 < len(m.BLOCKS) else m.DUR) for k, b in enumerate(m.BLOCKS)}
    for k, n in enumerate(ORDER):
        s0 = starts[n]; s1 = s0 + lens[n]
        note = ''
        if k + 1 < len(ORDER) and s1 + 0.05 > starts[ORDER[k+1]]:
            note = '← 次の文と重なる'; ok = False
        if n in nxt_block and n not in ('まとめ',) and s1 + 0.4 > nxt_block[n] + 1e-6:
            note += ' ← 次の場面・パターンまでの間が 0.4秒より短い'; ok = False
        if n == '保存' and s1 > m.DUR - m.LOOP_FADE:
            note += ' ← 冒頭へ戻るところにかかる'; ok = False
        rows.append((n, s0, s1, note))
    print(f'映像 {m.DUR:.2f}秒')
    for n, s0, s1, note in rows:
        print(f'{n:10s} {s0:6.2f}–{s1:6.2f}  {TEXT[n]} {note}')
    assert ok, '配置を見直す'

    n_all = int(m.DUR * SR)
    vo = np.zeros(n_all, np.float32)
    for n in ORDER:
        i0 = int(starts[n] * SR)
        seg = segs[n][:max(0, n_all - i0)]
        vo[i0:i0+len(seg)] += seg
    vo *= VO_PEAK / (np.abs(vo).max() + 1e-9)

    os.makedirs(os.path.join(HERE, 'out', 'vo'), exist_ok=True)
    bw = os.path.join(HERE, 'out', 'vo', 'beeps.wav')
    m.beeps(bw, sr=SR)
    with wave.open(bw) as w:
        bp = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    bp = np.pad(bp, (0, max(0, n_all - len(bp))))[:n_all]

    # サイドチェイン：声の大きさに合わせて、効果音を最大 8dB 下げる
    win_n = int(0.02 * SR)
    env = np.sqrt(np.convolve(vo**2, np.ones(win_n)/win_n, mode='same'))
    env = env / (env.max() + 1e-9)
    act = np.clip(env / 0.08, 0, 1)
    att, rel = 1 - np.exp(-1/(0.02*SR)), 1 - np.exp(-1/(0.25*SR))
    sm = np.zeros_like(act); y = 0.0
    step = 64
    for j in range(0, n_all, step):
        x = act[j:j+step].max()
        k = att if x > y else rel
        y += (x - y) * (1 - (1 - k)**step)
        sm[j:j+step] = y
    gain = 1 - (1 - 10**(-DUCK_DB/20)) * sm
    mix = vo * 0.95 + bp * gain
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    out = os.path.join(HERE, 'out', 'vo', 'mix.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    print(out)

    tbl = os.path.join(HERE, 'out', 'vo', 'placement.md')
    with open(tbl, 'w', encoding='utf-8') as f:
        f.write('| 秒 | 文 |\n|---|---|\n')
        for n, s0, s1, _ in rows:
            f.write(f'| {s0:.2f}–{s1:.2f} | {TEXT[n]} |\n')
    print(tbl)

    if o.mux:
        tag = '_hq' if o.hq else ''
        video = os.path.join(HERE, 'out', f'reel21_v3{tag}.mp4')
        dst = os.path.join(HERE, 'out', f'reel21_v3{tag}_vo.mp4')
        subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', video, '-i', out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k' if o.hq else '192k', '-ar', '48000',
                        '-shortest', '-movflags', '+faststart', dst], check=True)
        print(dst)


if __name__ == '__main__':
    main()
