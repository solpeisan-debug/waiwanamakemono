"""第29弾 心筋梗塞の場所：ナレーション（1文1ファイル）を映像の秒数に置いて、効果音と混ぜる。
第26弾の align_vo.py が手本（効果音のサイドチェイン・声のピーク・--mux）。1文1ファイルなので切り分けはしない。

声：out/vo/lines/<名前>.mp3（ElevenLabs、1.2倍済み）。名前は make_reel29.VO_TEXT の通り
（00_3d・01_intro・02_mikata・p1〜p6・matome・hozon）。届いていない文は飛ばす（映像は見込みの長さで組んである）。
場面の長さは make_reel29 が声の長さから決める（声の前後の無音は除いて測る）。ここでは同じ値（vo_starts）に置くだけ。

使い方:
    python3 align_vo.py                      # out/vo/mix.wav と配置表（out/vo/placement.md）
    python3 align_vo.py --mux --preview      # 確認版（out/reel29_mi_preview.mp4）に入れる → _preview_vo.mp4
    python3 align_vo.py --mux                # 通常版（out/reel29_mi.mp4）→ out/reel29_mi_vo.mp4
    python3 align_vo.py --mux --hq           # 高画質版（out/reel29_mi_hq.mp4）→ out/reel29_mi_hq_vo.mp4（音声 320k）
"""
import argparse
import os
import subprocess
import wave

import numpy as np

import make_reel29 as m

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100
PAD_IN, PAD_OUT = 0.04, 0.12          # 声の前後に残す無音
DUCK_DB = 8.0
VO_PEAK = 0.75                        # 声のピーク（第21弾・第26弾と同じ）
ORDER = list(m.VO_TEXT)


def load(path):
    raw = subprocess.run([m.ffmpeg_bin(), '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mux', action='store_true')
    ap.add_argument('--hq', action='store_true')
    ap.add_argument('--preview', action='store_true')
    o = ap.parse_args()

    starts = m.vo_starts()
    segs = {}
    for n in ORDER:
        if n not in m.VO_HAVE:
            continue
        a, b = m.VO_HAVE[n]
        au = load(os.path.join(m.VO_DIR, n + '.mp3'))
        segs[n] = (au[max(0, int((a - PAD_IN)*SR)):int((b + PAD_OUT)*SR)], PAD_IN)

    # 検算：重なり・場面からはみ出さないか
    win = {f'p{i + 1}': w for i, w in enumerate(m.WINDOWS)}
    rows, ok = [], True
    for k, n in enumerate(ORDER):
        s0 = starts[n]; s1 = s0 + m.VO_LEN[n]
        nxt = min([starts[x] for x in ORDER[k + 1:]] + [m.DUR - m.LOOP_FADE])
        note = '' if n in segs else '（まだ届いていない：見込みの長さ）'
        if s1 + 0.05 > nxt:
            note += ' ← 次の文と重なる'; ok = False
        if n in win and s1 > win[n][1]:
            note += ' ← 名前が消えたあとまで話す'; ok = False
        rows.append((n, s0, s1, note))
    print(f'映像 {m.DUR:.2f}秒')
    for n, s0, s1, note in rows:
        print(f'{n:9s} {s0:6.2f}–{s1:6.2f}  {m.VO_TEXT[n]} {note}')
    assert ok, '配置を見直す'

    n_all = int(m.DUR * SR)
    vo = np.zeros(n_all, np.float32)
    for n, (seg, pad) in segs.items():
        i0 = max(0, int((starts[n] - pad) * SR))
        seg = seg[:max(0, n_all - i0)]
        vo[i0:i0 + len(seg)] += seg
    if segs:
        vo *= VO_PEAK / (np.abs(vo).max() + 1e-9)

    os.makedirs(os.path.join(HERE, 'out', 'vo'), exist_ok=True)
    sw = os.path.join(HERE, 'out', 'vo', 'sfx.wav')
    m.sfx(sw, sr=SR)
    with wave.open(sw) as w:
        bp = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
    bp = np.pad(bp, (0, max(0, n_all - len(bp))))[:n_all]

    # サイドチェイン：声の大きさに合わせて、効果音を最大 8dB 下げる（第26弾と同じ）
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
        for n, s0, s1, note in rows:
            f.write(f'| {s0:.2f}–{s1:.2f} | {m.VO_TEXT[n]}{note} |\n')
    print(tbl)

    if o.mux:
        tag = '_preview' if o.preview else ('_hq' if o.hq else '')
        video = os.path.join(HERE, 'out', f'reel29_mi{tag}.mp4')
        dst = os.path.join(HERE, 'out', f'reel29_mi{tag}_vo.mp4')
        subprocess.run([m.ffmpeg_bin(), '-v', 'error', '-y', '-i', video, '-i', out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k' if o.hq else '192k', '-ar', '48000',
                        '-shortest', '-movflags', '+faststart', dst], check=True)
        print(dst)


if __name__ == '__main__':
    main()
