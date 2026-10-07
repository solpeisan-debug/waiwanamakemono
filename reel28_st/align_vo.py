"""第28弾 波形クイズ「この波形、なに？」：ナレーション（ElevenLabs の通し読み）を文に切り分けて、映像の秒数に置き直す。
第17弾の align_vo_v2.py・第21弾の align_vo.py と同じ作り。声は答えのところだけ（カウントダウン中は声なし・モニター音だけ）。

決めごと（README）：
- 無音を手がかりに文へ切り分ける。継ぎ目は必ず無音の中で切る
- 効果音は声の下で最大 8dB 下げる（サイドチェイン）

使い方:
    python3 align_vo.py out/vo/narration_raw.wav            # out/vo/mix.wav と配置表を作る
    python3 align_vo.py out/vo/narration_raw.wav --mux      # 映像（out/reel28_quiz.mp4）に入れる
    python3 align_vo.py out/vo/narration_raw.wav --mux --hq # 高画質版（out/reel28_quiz_hq.mp4）に入れる
    python3 align_vo.py out/vo/narration_raw.wav --lens     # 各文の長さ（make_reel28_quiz.py の VO_LEN に入れる）
    python3 align_vo.py out/vo/narration_raw.wav --fix out/vo/narration_fix.mp3 --mux
        # 録り直した文（FIX_LINES）だけ、--fix のファイルから差し替える
"""
import argparse
import os
import re
import subprocess
import wave

import numpy as np

import make_reel28_quiz as m

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

# 通し読みの「声のかたまり」（無音 0.25秒以上で区切ったもの）を、台本の文にまとめる。番号は 1 から。
# 2026-10-07 の録音（Ren – Smooth & Soothing・eleven_v4、atempo=1.2 で 1.2倍速、40.27秒）は 24 かたまり：
# 冒頭は「心電図クイズ。」「この10問、全部わかる？」、各問は「答えは、〇〇。」「特徴。」の2つずつ（Whisper で順番を確かめた）
LINES = [('冒頭', [1, 2])] + [(p['no'], [2*k + 3, 2*k + 4]) for k, p in enumerate(m.PATTERNS)] + [
    ('まとめ', [2*len(m.PATTERNS) + 3]),       # 何問わかったか、コメントで教えてね。
    ('保存', [2*len(m.PATTERNS) + 4]),         # 保存して、見返してね
]
# 録り直した文（--fix のファイルの声のかたまり番号。0.05秒未満のかたまり＝雑音は数えない）
FIX_LINES = {}
# 文の中の息継ぎ（無音）を、この長さまで縮める（離脱を防ぐ）。録音が届いたら間の長さを見て決める
GAP_CAP = {n: 0.45 for n, _ in LINES}
# 「すぐ報告」は声では言わない（画面の色の文字とキャプションで伝える）。答えの文は make_reel28_quiz.py の say
TEXT = {'冒頭': '心電図クイズ。この10問、全部わかる？'}
TEXT.update({p['no']: p['say'] for p in m.PATTERNS})
TEXT.update({'まとめ': '何問わかったか、コメントで教えてね。', '保存': '保存して、見返してね'})
PAD_IN, PAD_OUT = 0.06, 0.15          # 声の前後に残す無音（無音の中で切る）
LEAD = 0.55                           # パターンの名前が出てから話し始めるまで
GAP_MIN = 0.20                        # 文と文のあいだの最小の間
DUCK_DB = 8.0
VO_PEAK = 0.75                        # 声のピーク（第17弾の声とおなじくらいの大きさ）


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
    dur = float(re.search(r'Duration: (\d+):(\d+):([\d.]+)', log).group(3)) + \
        60*float(re.search(r'Duration: (\d+):(\d+):', log).group(2))
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
    （無音の真ん中を残して切るので、声には触れない）。"""
    a = blocks[ix[0]-1][0] - PAD_IN
    b = blocks[ix[-1]-1][1] + PAD_OUT
    if gap_cap is None:
        return audio[max(0, int(a*SR)):int(b*SR)]
    parts, t = [], a
    for j in range(len(ix) - 1):
        g0, g1 = blocks[ix[j]-1][1], blocks[ix[j+1]-1][0]
        if g1 - g0 > gap_cap:
            mid = (g0 + g1) / 2
            parts.append(audio[max(0, int(t*SR)):int((mid - gap_cap/2)*SR)])
            t = mid + gap_cap/2
    parts.append(audio[max(0, int(t*SR)):int(b*SR)])
    return np.concatenate(parts)


def plan(lines_len):
    """各文を置く時刻。答えの文は、答えが出てから SAY_LEAD 秒後（カウントダウン中は声を入れない）。"""
    starts = {'冒頭': 0.10}
    for i, pat in enumerate(m.PATTERNS):
        starts[pat['no']] = m.T_REV[i] + m.SAY_LEAD
    starts['まとめ'] = m.T_END + m.FLY + 0.1
    starts['保存'] = starts['まとめ'] + lines_len['まとめ'] + 0.30
    return starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--fix', help='録り直した文のファイル（FIX_LINES の文を差し替える）')
    ap.add_argument('--mux', action='store_true')
    ap.add_argument('--hq', action='store_true', help='高画質版（out/reel28_quiz_hq.mp4）に入れる。音声 320k')
    ap.add_argument('--lens', action='store_true', help='各文の長さ（切り出したあと）を書き出すだけ')
    o = ap.parse_args()

    blocks = speech_blocks(o.src)
    need = max(max(ix) for _, ix in LINES)
    assert len(blocks) == need, f'声のかたまりが {len(blocks)} 個（台本の想定 {need} 個）。LINES を見直す'
    audio = load(o.src)

    segs, lens = {}, {}
    for name, ix in LINES:
        segs[name] = cut(audio, blocks, ix, GAP_CAP.get(name))
        lens[name] = len(segs[name]) / SR
    if o.fix:
        fb = speech_blocks(o.fix, min_len=0.05)
        assert len(fb) == max(max(ix) for ix in FIX_LINES.values()), f'録り直しの声のかたまりが {len(fb)} 個'
        fa = load(o.fix)
        for name, ix in FIX_LINES.items():
            segs[name] = cut(fa, fb, ix, GAP_CAP.get(name))
            lens[name] = len(segs[name]) / SR
    if o.lens:
        print('VO_LEN = {' + ', '.join(f"'{n}': {lens[n]:.3f}" for n, _ in LINES) + '}')
        return
    for n, v in m.VO_LEN.items():
        assert abs(v - lens[n]) < 0.002, f'{n} の長さが VO_LEN とちがう（{lens[n]:.3f} / {v}）。--lens の値を make_reel28_quiz.py に入れる'
    starts = plan(lens)

    # 検算：重なりと、言い終わりが次の場面に食いこまないか
    order = [n for n, _ in LINES]
    rows, ok = [], True
    win = {p['no']: w for p, w in zip(m.PATTERNS, m.WINDOWS)}
    if lens['冒頭'] + 0.10 > m.T_TITLE:
        print(f"冒頭の文 {lens['冒頭']:.2f}秒 が T_TITLE {m.T_TITLE} に入らない ← T_TITLE を延ばす"); ok = False
    for k, n in enumerate(order):
        s0 = starts[n]; s1 = s0 + lens[n]
        nxt = starts[order[k+1]] if k + 1 < len(order) else m.DUR - m.LOOP_FADE
        note = ''
        if s1 + 0.05 > nxt:
            note = '← 次の文と重なる'; ok = False
        if n in win and s1 > win[n][1] - 0.15:
            note += ' ← 縮み始めまでに言い終わらない（SAY_CPS か区間を直す）'; ok = False
        rows.append((n, s0, s1, note))
    print(f'映像 {m.DUR:.1f}秒')
    for n, s0, s1, note in rows:
        print(f'{n:6s} {s0:6.2f}–{s1:6.2f}  {TEXT[n]} {note}')
    assert ok, '配置を見直す'

    # 声のトラック
    n_all = int(m.DUR * SR)
    vo = np.zeros(n_all, np.float32)
    for n in order:
        i0 = int(starts[n] * SR)
        seg = segs[n][:max(0, n_all - i0)]
        vo[i0:i0+len(seg)] += seg

    # 声の大きさをそろえる（この録音は第17弾より約4dB小さい）。声のいちばん大きいところを VO_PEAK に
    vo *= VO_PEAK / (np.abs(vo).max() + 1e-9)

    # 効果音（モニター音）
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
    act = np.clip(env / 0.08, 0, 1)                         # 声があれば 1
    att, rel = 1 - np.exp(-1/(0.02*SR)), 1 - np.exp(-1/(0.25*SR))
    sm = np.zeros_like(act); y = 0.0
    step = 64                                               # 速さのため、64サンプルごとに追う
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

    # 配置表（台本用）
    tbl = os.path.join(HERE, 'out', 'vo', 'placement.md')
    with open(tbl, 'w', encoding='utf-8') as f:
        f.write('| 秒 | 文 |\n|---|---|\n')
        for n, s0, s1, _ in rows:
            f.write(f'| {s0:.2f}–{s1:.2f} | {TEXT[n]} |\n')
    print(tbl)

    if o.mux:
        tag = '_hq' if o.hq else ''
        video = os.path.join(HERE, 'out', f'reel28_quiz{tag}.mp4')
        dst = os.path.join(HERE, 'out', f'reel28_quiz{tag}_vo.mp4')
        subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', video, '-i', out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k' if o.hq else '192k', '-ar', '48000',
                        '-shortest', '-movflags', '+faststart', dst], check=True)
        print(dst)


if __name__ == '__main__':
    main()
