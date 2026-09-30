"""ウェンケバッハ編の共通部品：PRが1拍ごとに伸びて、4つめのPで抜ける（4:3）。

1周期 3.2秒（80mm）の繰り返し。尺を27周期（86.4秒）にすると、
最後のカメラ LOOP_END と最初のカメラ HOOK が同じ絵になり、リールのリピートで継ぎ目が消える。

python3 wk_core.py で間隔を検算する（画面に出す数値はこの実測値を使う）。
"""
import numpy as np
import ecg

W, H, FPS = 1080, 1920, 30
T0_MM = 13.5                    # 拍0のR頂点（世界座標 mm）

COL_N = (150, 232, 185)         # 正常洞調律（残像）
GRN = (0, 236, 100)
COL_W = (255, 170, 90)          # ウェンケバッハ（PRバー＝ゴム）
RED = (255, 92, 92)             # 抜けた拍
AMB = (255, 196, 96)
WHT = (238, 244, 240)

PP = 0.80                       # P-P間隔（秒）＝75/分
PRS = (0.18, 0.28, 0.33)        # 1周期のPR（秒）。伸び幅 +0.10 → +0.05
CYC = len(PRS)+1                # 1周期のP波の数（4:3。4つめのPは抜ける）
CYC_S = CYC*PP                  # 3.2秒
CYC_MM = CYC_S*25.0             # 80mm。方眼5mmの倍数
N_LOOP = 27                     # 27周期＝86.4秒
DUR = N_LOOP*CYC_S

P_W = dict(ecg.NORMAL)
QON = (P_W['q_dur']+P_W['r_dur'])*0.5+P_W['q_dur']*0.5    # QRS開始 → R頂点
PHALF = P_W['p_dur']*0.5                                   # P開始 → P中心


def _build(k0=-3, k1=N_LOOP+4):
    """拍0（k=0,i=0）のR頂点が0秒になるように、P・QRSを並べる。"""
    ps, rs, prs, drops, ghosts = [], [], [], [], []
    off = PRS[0]+QON
    for k in range(k0, k1):
        for i in range(CYC):
            pon = (k*CYC+i)*PP-off
            ps.append(pon+PHALF)
            if i < len(PRS):
                rs.append(pon+PRS[i]+QON)
                prs.append((pon, pon+PRS[i]))       # PRバー（P開始 → QRS開始）
            else:
                drops.append(pon+PHALF)             # 抜けた拍のP中心
                ghosts.append(pon+PRS[0]+QON)       # 来るはずだった位置（ゴースト）
    return ps, rs, prs, drops, ghosts


PS, RS, PR_BARS, DROPS, GHOSTS = _build()


def vf(ps=None, rs=None, p_amps=None, r_amps=None):
    """render(vfun=...) 用：P と QRS〜T を別々の位置に置く。"""
    ps = PS if ps is None else ps
    rs = RS if rs is None else rs
    def fn(xs):
        return ecg.waves_at(xs, P_W, ps, rs, T0_MM, p_amps=p_amps, r_amps=r_amps)
    return fn


def gf_sinus():
    """比較用の残像：同じPが全部1:1で伝わった場合（PRは最初の値のまま）。"""
    ps = PS
    rs = [p-PHALF+PRS[0]+QON for p in PS]
    def fn(xs):
        return ecg.waves_at(xs, P_W, ps, rs, T0_MM)
    return fn


def gf_ghost(amp=1.0):
    """抜けた拍のゴーストQRSだけ。赤で薄く重ねる用。"""
    def fn(xs):
        return ecg.waves_at(xs, P_W, [], GHOSTS, T0_MM, r_amps=[amp]*len(GHOSTS))
    return fn


def px(c, sec): return (T0_MM+sec*25-c['x0'])*c['ppm']
def py(c, mv): return c['y0']-mv*10*c['ppm']


def cam(ppm, ctr_mm, y0):
    return dict(ppm=float(ppm), x0=ctr_mm-(W/2)/ppm, y0=float(y0))


def lerp_cam(a, b, u):
    x0a = (T0_MM-a['x0'])*a['ppm']; x0b = (T0_MM-b['x0'])*b['ppm']
    ppm = a['ppm']*(b['ppm']/a['ppm'])**u
    xr = x0a+(x0b-x0a)*u
    return dict(ppm=ppm, x0=T0_MM-xr/ppm, y0=a['y0']+(b['y0']-a['y0'])*u)


def ctr_at(t, off=0.0):
    """t秒の画面中心（mm）。平均で紙送りと同じ 25mm/秒 で進む。off は寄り道。"""
    return HOOK_CTR+25.0*t+off


def shift(c, n=N_LOOP):
    """カメラを n 周期ぶん右へ。n=N_LOOP で最初と同じ絵になる。"""
    return dict(ppm=c['ppm'], x0=c['x0']+n*CYC_MM, y0=c['y0'])


HOOK_CTR = 30.0
HOOK = cam(20.0, HOOK_CTR, 1040.0)              # 1周期（80mm）が画面に入る寄り
LOOP_END = shift(HOOK)                           # 最後のカットの cam1 はこれ


def check():
    """間隔の検算。数値は秒 → ms。"""
    rr = np.diff(RS)
    k = next(i for i, r in enumerate(RS) if r >= -1e-9)    # 拍0
    one = rr[k:k+len(PRS)]
    print('PR      :', [round(p*1000) for p in PRS], 'ms')
    print('ΔPR     :', [round((b-a)*1000) for a, b in zip(PRS, PRS[1:])], 'ms')
    print('RR      :', [round(x*1000) for x in one], 'ms')
    pause, short = one[-1], min(one[:-1])
    print('抜けのRR:', round(pause*1000), '< 2×PP', round(2*PP*1000),
          pause < 2*PP, '/ < 2×最短RR', round(2*short*1000), pause < 2*short)
    print('心房    :', round(60/PP), '/分　心室(平均):', round(60*len(PRS)/CYC_S, 1), '/分')
    print('1周期   :', CYC_S, '秒 =', round(CYC_S*FPS), 'コマ =', CYC_MM, 'mm')
    print('全体    :', round(DUR, 1), '秒 =', round(DUR*FPS), 'コマ')
    print('ループ  : LOOP_END.x0-HOOK.x0 =', LOOP_END['x0']-HOOK['x0'],
          'mm（方眼5mmの倍数か）', (LOOP_END['x0']-HOOK['x0']) % 5 == 0)
    for s in SEAMS:
        n = s/CYC_S
        print(f'つなぎ目 {s:5.1f} 秒 = {n:.2f} 周期', '（周期の切れ目）' if abs(n-round(n)) < 1e-6 else '← ずれている')


SEAMS = (12.8, 19.2, 32.0, 44.8, 57.6, 73.6)     # hook|over|feat①|feat②|feat③|caution|end


if __name__ == '__main__':
    check()
