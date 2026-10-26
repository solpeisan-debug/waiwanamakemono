"""第29弾の冒頭「横向き → 足もとから見上げる → 心臓へ寄る」を、字幕・札・透かしなしで書き出す（他の回で素材として使う用）。
使い方：python3 reel29_mi/tools3d/make_feet_clip.py 出力.mp4（assets3d/ が要る。最後のコマも 出力_最後のコマ.png に書き出す）
2026-10-26：Drive `素材_人体と心臓3D/追加_1024/36_足もとから心臓へ_第29弾の完成版_字幕なし.mp4` はこれで作った（1080×1920・30fps・6.03秒・音なし）。"""
import os, sys, math, subprocess
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # reel29_mi
sys.path.insert(0, R); os.chdir(R)
import make_reel29 as M
I3 = M.I3
OUT = sys.argv[1]
FPS = 30
T_A, T_B = I3.T_ROT, I3.T_Z13 + I3.Z13_D      # 回りはじめ → 心臓へ寄り終わり
HOLD = 0.5                                      # 最後の絵で止まる


def pic(t):
    if t < I3.T_H13:
        p = I3.rot_frame(t)
        ux13 = M.ease((t - I3.T_X13) / I3.X13_D)
        if ux13 > 0:
            p = M.Image.blend(p, I3.render13(I3.S13_FULL, I3.C13_FULL), ux13)
        return p.convert('RGB')
    uz = M.ease((t - I3.T_Z13) / I3.Z13_D)
    sc = math.exp(math.log(I3.S13_FULL) + (math.log(M.S13_Z) - math.log(I3.S13_FULL))*uz)
    q = (M.Q13_IN[0] + (M.Q13_Z[0] - M.Q13_IN[0])*uz, M.Q13_IN[1] + (M.Q13_Z[1] - M.Q13_IN[1])*uz)
    return I3.render13(*M.cam13_at(q, sc)).convert('RGB')


I3.ensure_v15()
n = round((T_B - T_A)*FPS)
ff = I3.ffmpeg_bin()
p = subprocess.Popen([ff, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT],
                     stdin=subprocess.PIPE)
last = None
for i in range(n + 1):
    last = pic(T_A + i/FPS)
    p.stdin.write(last.tobytes())
    if i % 30 == 0:
        print(i, '/', n, flush=True)
for _ in range(round(HOLD*FPS)):
    p.stdin.write(last.tobytes())
p.stdin.close(); p.wait()
last.save(OUT.replace('.mp4', '_最後のコマ.png'))
print('T', T_A, T_B, 'frames', n + 1 + round(HOLD*FPS))
