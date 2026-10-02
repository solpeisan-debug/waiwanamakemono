"""ナレーション（ElevenLabs の通し読み）を文に切り分けて、映像の秒数に置き直す。

決めごと（README）：
- 無音を手がかりに文へ切り分ける。継ぎ目は必ず無音の中で切る
- 効果音は声の下で最大 8dB 下げる（サイドチェイン）

使い方:
    python3 align_vo_v2.py out/vo/narration_raw.mp3      # out/vo/mix.wav と配置表を作る
    python3 align_vo_v2.py out/vo/narration_raw.mp3 --mux  # 映像（out/reel17_ectopy_v2.mp4）に入れる
    python3 align_vo_v2.py out/vo/narration_raw.mp3 --fix out/vo/narration_fix.mp3 --mux
        # 録り直した文（FIX_LINES）だけ、--fix のファイルから差し替える
"""
import argparse
import os
import re
import subprocess
import wave

import numpy as np

import make_reel17_v2 as m

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 44100

# 通し読みの「声のかたまり」（無音 0.25秒以上で区切ったもの）を、台本の文にまとめる。
# 番号は 1 から。Whisper の書き起こしで順番と中身を確認済み。
LINES = [
    ('冒頭1', [1]),            # 1拍だけ、早い。
    ('冒頭2', [2]),            # 期外収縮は、形も、並び方も、いろいろ。
    ('冒頭3', [3]),            # まず覚えたいのは、この14パターン。
    ('①', [4, 5, 6]),         # 心房から早く来るのが、PAC。P波の形がちがいます。
    ('②', [7, 8]),
    ('③', [9]),
    ('④', [10, 11]),
    ('⑤', [12, 13, 14]),
    ('⑥', [15, 16, 17]),
    ('⑦', [18]),
    ('⑧', [19]),
    ('⑨', [20, 21]),
    ('⑩', [22]),
    ('⑪', [23]),
    ('⑫', [24]),
    ('⑬', [25, 26]),
    ('⑭', [27]),
    ('まとめ', [28]),          # 1拍だけ早かったら、形と並び方を見てください。
    ('保存', [29]),            # 保存して、見返してね
]
# 録り直し（2026-10-02 専門医レビュー）：②と⑬。--fix のファイルの声のかたまり番号
# （0.05秒未満のかたまり＝雑音は数えない）。Whisper で確認済み。
FIX_LINES = {
    '②': [1],                 # P波がT波に重なると、Tの形が変わります。
    '⑬': [2, 3, 4],           # 3つ以上、速く続けば、非持続性心室頻拍。／ショートランとも呼びます。／すぐ報告です。
}
# 文の中の息継ぎ（無音）を、この長さまで縮める。⑬の録り直しは息継ぎが 0.5〜0.6秒と長いので詰める
GAP_CAP = {'⑬': 0.35}
TEXT = {
    '冒頭1': '1拍だけ、早い。', '冒頭2': '期外収縮は、形も、並び方も、いろいろ。',
    '冒頭3': 'まず覚えたいのは、この14パターン。',
    '①': '心房から早く来るのが、PAC。P波の形がちがいます。',
    '②': 'P波がT波に重なると、Tの形が変わります。',
    '③': '早すぎると心室に伝わらず、休みに見えます。',
    '④': 'P波があるのに、QRSが広い。これが、変行伝導。',
    '⑤': 'P波がなく、細いQRSが早く来る。接合部からです。',
    '⑥': '心室から来るのが、PVC。QRSが広く、休みは2拍ぶん。',
    '⑦': 'QRSのあとに、逆向きのP波が出ることもあります。',
    '⑧': '形が2種類以上なら、多源性。',
    '⑨': '1拍おきなら、二段脈。脈は、指で数えます。',
    '⑩': '2拍おきなら、三段脈。', '⑪': '3拍おきなら、四段脈。', '⑫': '2つ続いたら、報告。',
    '⑬': '3つ以上、速く続けば、非持続性心室頻拍。ショートランとも呼びます。すぐ報告です。',
    '⑭': 'T波に乗るPVCは、QT延長があると危険です。',
    'まとめ': '1拍だけ早かったら、形と並び方を見てください。', '保存': '保存して、見返してね',
}
PAD_IN, PAD_OUT = 0.06, 0.15          # 声の前後に残す無音（無音の中で切る）
LEAD = 0.55                           # パターンの名前が出てから話し始めるまで
GAP_MIN = 0.20                        # 文と文のあいだの最小の間
DUCK_DB = 8.0


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
    parts.append(audio[int(t*SR):int(b*SR)])
    return np.concatenate(parts)


def plan(lines_len):
    """各文を置く時刻。"""
    starts = {}
    starts['冒頭1'] = 0.10
    starts['冒頭2'] = starts['冒頭1'] + lines_len['冒頭1'] + GAP_MIN
    starts['冒頭3'] = starts['冒頭2'] + lines_len['冒頭2'] + GAP_MIN
    for i, pat in enumerate(m.PATTERNS):
        starts[pat['no']] = m.WINDOWS[i][0] + LEAD
    # ①は冒頭3のあと
    starts['①'] = max(starts['①'], starts['冒頭3'] + lines_len['冒頭3'] + GAP_MIN)
    starts['まとめ'] = m.T_END + 0.15
    starts['保存'] = starts['まとめ'] + lines_len['まとめ'] + 0.30
    return starts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('--fix', help='録り直した文のファイル（FIX_LINES の文を差し替える）')
    ap.add_argument('--mux', action='store_true')
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
        video = os.path.join(HERE, 'out', 'reel17_ectopy_v2.mp4')
        dst = os.path.join(HERE, 'out', 'reel17_ectopy_v2_vo.mp4')
        subprocess.run([ffmpeg(), '-v', 'error', '-y', '-i', video, '-i', out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', dst], check=True)
        print(dst)


if __name__ == '__main__':
    main()
