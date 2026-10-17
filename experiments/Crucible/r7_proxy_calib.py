# Round 6 (Q1, fine-tuning as team reads arrive): is the expert proxy a *biased* teacher once the team's own
# habits are known, and can the wave-1 report's measured habits calibrate it?
# Per case: truth T = the ImageCAS mask split by ImageCAS-X names (= the projected proxy, Atlas's training label
# before team reads). The "team" is simulated with r5_corr.py's read generator in three regimes (indep, team_bias,
# annot_bias). Pass 1 measures the team's habits the way segtrain.reads does on a wave (median geodesic carina offset
# against the proxy's carina; median truncation radius), pooled over the wave. Pass 2 builds a CALIBRATED proxy: T with
# the team's median carina shift and its median truncation radius applied (no random slips). Scored with tF1 @1.5 mm
# against the two real reads A, B (A10, the decisive score) and against T:
#   proxy T | calibrated proxy | read-mode (what a model trained on many team reads converges to) | inter-read.
# Usage: python r7_proxy_calib.py NCASES K
import sys, os, json, numpy as np
sys.argv_saved = list(sys.argv); sys.argv = ['x', 'indep', '1', '2']
exec(open('/home/user/Asclepius/experiments/Crucible/r5_corr.py').read().split("if __name__")[0])
sys.argv = sys.argv_saved
sys.path.insert(0, '/home/user/Asclepius/src')
from segtrain import reads as RD  # noqa: E402
sealed = json.load(open('/home/user/Asclepius/trillium/sealed_test.json'))
SEALED = set(sealed['sealed_icx_test']) | set(sealed['sealed_quality0'])
OUT7 = SCR + '/work/Crucible/r7calib'; os.makedirs(OUT7, exist_ok=True)


def calibrated(cs, sh, rt):
    R = cs.T.copy()
    if sh > 0: R[np.isin(R, (2, 3)) & (cs.d_lm <= sh)] = 1
    elif sh < 0:
        sel = (R == 1) & (cs.d_23 <= -sh); R[sel] = cs.T[tuple(cs.ind23)][sel]
    lab, _ = ndi.label(cs.m & (cs.rl >= rt), S26)
    rc = {lab[tuple(r)] for r in cs.roots if lab[tuple(r)] > 0}
    R[~np.isin(lab, list(rc))] = 0
    return R


if __name__ == '__main__':
    N, K = int(sys.argv[1]), int(sys.argv[2])
    cases = [c for c in sorted(meta) if c not in SEALED][:N]
    for sc in ('indep', 'team_bias', 'annot_bias'):
        # pass 1: reads and the wave-level habit estimates
        def reads_of(c, cs):  # deterministic per case and scenario, so pass 2 regenerates the same reads
            rng = np.random.default_rng(11 + int(c[1:])); crng = {'u': rng.uniform(0.6, 1.05), 'm': rng.normal(0, 2)}
            rs = []
            for i in range(K + 2):
                sh, rt = draw(sc, crng, rng, 'X' if i % 2 == 0 else 'Y'); rs.append(cs.read(rng, sh, rt))
            return rs
        offs, truncs = [], []
        for c in cases:
            cs = Case(c); rs = reads_of(c, cs)
            for r in rs[:2]:  # the wave sees each case's two real reads
                a = RD.carina_offset(r, cs.T, cs.m, cs.sp)
                if not a.review: offs.append(a.offset_mm)
                t = RD.truncation_radius(r, cs.m, cs.sp)
                if t is not None: truncs.append(t)
            del cs, rs
        sh_hat = float(np.median(offs)) if offs else 0.0
        rt_hat = float(np.median(truncs)) if truncs else 0.0
        # pass 2: score
        for c in cases:
            if os.path.exists(f'{OUT7}/{sc}_{c}.json'): continue
            cs = Case(c); rs = reads_of(c, cs)
            A, B = rs[0], rs[1]
            refs = {'T': Ref(cs.T), 'A': Ref(A), 'B': Ref(B)}
            P = {'proxy': cs.T, 'calibrated': calibrated(cs, sh_hat, rt_hat), 'read_mode': mode(np.stack(rs[2:]))}
            r = {'case': c, 'scenario': sc, 'sh_hat': sh_hat, 'rt_hat': rt_hat,
                 'inter_read': (tf1(refs['A'], pred_info(B, cs.sp, cs.roots)) + tf1(refs['B'], pred_info(A, cs.sp, cs.roots))) / 2}
            for k, p in P.items():
                pi = pred_info(p, cs.sp, cs.roots)
                r[f'{k}_vs_T'] = tf1(refs['T'], pi); r[f'{k}_vs_reads'] = (tf1(refs['A'], pi) + tf1(refs['B'], pi)) / 2
            json.dump(r, open(f'{OUT7}/{sc}_{c}.json', 'w'))
            print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
