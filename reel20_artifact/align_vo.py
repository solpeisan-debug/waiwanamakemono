"""第20弾 ノイズ：ナレーション（ElevenLabs の通し読み）を文に切り分けて、映像の秒数に置き直す。
第21・24弾の align_vo.py と同じ作り。

決めごと（README）：
- 無音を手がかりに文へ切り分ける。継ぎ目は必ず無音の中で切る
- 効果音は声の下で最大 8dB 下げる（サイドチェイン）

使い方:
    cp 録音.mp3 out/vo/narration_raw.mp3
    python3 align_vo.py out/vo/narration_raw.mp3            # out/vo/mix.wav と配置表を作る
    python3 align_vo.py out/vo/narration_raw.mp3 --mux      # 映像（out/reel20_artifact.mp4）に入れる
    python3 align_vo.py out/vo/narration_raw.mp3 --mux --hq # 高画質版（out/reel20_artifact_hq.mp4）に入れる
    python3 align_vo.py out/vo/narration_raw.mp3 --fix out/vo/narration_fix.mp3 --mux
        # 録り直した文（FIX_LINES）だけ、--fix のファイルから差し替える
"""
import argparse
import os
import re
import subprocess
import wave

import numpy as np

import make_reel20 as m

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

# 通し読みの「声のかたまり」（無音 0.25秒以上で区切ったもの）を、台本の文にまとめる。
# 番号は 1 から。録音が届いたら、Whisper の書き起こしで順番と中身を確かめて直す
# （読点で 0.25秒以上の間があると、1つの文が2つ以上のかたまりになる）。
LINES = [
    ('冒頭', [1]),             # ノイズで、まず覚えたいのは、この11パターン。（仮：録音が届いたら直す）
    ('①', [2]), ('②', [3]), ('③', [4]), ('④', [5]), ('⑤', [6]), ('⑥', [7]),
    ('⑦', [8]), ('⑧', [9]), ('⑨', [10]), ('⑩', [11]), ('⑪', [12]),
    ('まとめ', [13]),          # 同じ間隔のQRSが見えたらノイズ。でも、まず患者さんを見て。
    ('保存', [14]),            # 保存して、見返してね
]
# 録り直した文（--fix のファイルの声のかたまり番号。0.05秒未満のかたまり＝雑音は数えない）
FIX_LINES = {}
# 文の中の息継ぎ（無音）を、この長さまで縮める（離脱を防ぐ）。録音（Ren – Smooth & Soothing）が届いたら間の長さを見て決める
GAP_CAP = {n: 0.45 for n, _ in LINES}
# 台本（narration.md の「読み上げ用」と同じ。「すぐ報告」は声では言わない。数字も読まない）
TEXT = {
    '冒頭': 'ノイズで、まず覚えたいのは、この11パターン。',
    '①': '体が動くと、基線が大きく乱れる。体動。',
    '②': '力が入ると、細かいギザギザ。筋電図。',
    '③': 'ふるえは心房細動に見えても、R-Rは一定。',
    '④': '呼吸に合わせて、基線がゆっくり揺れる。',
    '⑤': '細かく規則正しいギザギザ。交流障害。',
    '⑥': '接触が悪いと、基線が飛ぶ。',
    '⑦': '電極外れでまっすぐの線。あわてず、まず患者さんを見て。',
    '⑧': '付けまちがいで、波形がまるごと逆さまに。',
    '⑨': '歯みがきの偽VT。ふつうのQRSが隠れている。',
    '⑩': '断線の偽VF。ここにも、ふつうのQRSが見える。',
    '⑪': '本物のVTでは、ふつうのQRSが消える。',
    'まとめ': '同じ間隔のQRSが見えたらノイズ。でも、まず患者さんを見て。',
    '保存': '保存して、見返してね',
}
PAD_IN, PAD_OUT = 0.06, 0.15          # 声の前後に残す無音（無音の中で切る）
LEAD = 0.55                           # パターンの名前が出てから話し始めるまで
GAP_MIN = 0.20                        # 文と文のあいだの最小の間
DUCK_DB = 8.0
VO_PEAK = 0.75                        # 声のピーク（第17・21弾の声とおなじくらいの大きさ）


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
    """各文を置く時刻。"""
    starts = {'冒頭': 0.10}
    for i, pat in enumerate(m.PATTERNS):
        starts[pat['no']] = m.WINDOWS[i][0] + LEAD
    # ①は冒頭のあと。①の区間は縮み始めが 0.35秒早いぶん短いので、名前が出たらすぐ（0.3秒）話し始める
    starts['①'] = max(m.WINDOWS[0][0] + 0.30, starts['冒頭'] + lines_len['冒頭'] + GAP_MIN)
    starts['まとめ'] = m.T_END + 0.15
    starts['保存'] = starts['まとめ'] + lines_len['まとめ'] + 0.30
    return starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--fix', help='録り直した文のファイル（FIX_LINES の文を差し替える）')
    ap.add_argument('--mux', action='store_true')
    ap.add_argument('--hq', action='store_true', help='高画質版（out/reel20_artifact_hq.mp4）に入れる。音声 320k')
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
    starts = plan(lens)

    # 検算：重なりと、言い終わりが次の場面に食いこまないか
    order = [n for n, _ in LINES]
    rows, ok = [], True
    win = {p['no']: w for p, w in zip(m.PATTERNS, m.WINDOWS)}
    for k, n in enumerate(order):
        s0 = starts[n]; s1 = s0 + lens[n]
        nxt = starts[order[k+1]] if k + 1 < len(order) else m.DUR - m.LOOP_FADE
        note = ''
        if s1 + 0.05 > nxt:
            note = '← 次の文と重なる'; ok = False
        if n in win and s1 > win[n][1] + m.FLY:
            note += ' ← 次のパターンまで食いこむ'; ok = False
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

    # 声の大きさをそろえる。声のいちばん大きいところを VO_PEAK に
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
        video = os.path.join(HERE, 'out', f'reel20_artifact{tag}.mp4')
        dst = os.path.join(HERE, 'out', f'reel20_artifact{tag}_vo.mp4')
        subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', video, '-i', out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k' if o.hq else '192k', '-ar', '48000',
                        '-shortest', '-movflags', '+faststart', dst], check=True)
        print(dst)


if __name__ == '__main__':
    main()
