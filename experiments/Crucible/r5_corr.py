# Round 4: do the two-read fusion conclusions survive CORRELATED annotator errors and boundary jitter?
# Same machinery as r4_fusion.py (mode of each scheme's target over many simulated reads = what a converged model
# learns), with the read generator of trillium/crucible/lib/sim.py (ramus -> LCx, every tree rooted), now with
# scenario-specific error structure:
#   indep        : carina s ~ N(0,2) mm, truncation r_t ~ U(0.6,1.05) mm, independent per read (round-3 model)
#   corr_trunc   : r_t = 0.8 * u_case + 0.2 * u_read  (both readers stop at the same thin/stenotic point)
#   corr_carina  : s = m_case + N(0, 0.7), m_case ~ N(0, 2)  (a case-level carina ambiguity both readers share)
#   annot_bias   : two annotators with opposite habits; X: s ~ N(+1.5,1), r_t ~ U(0.8,1.1); Y: s ~ N(-1.5,1),
#                  r_t ~ U(0.55,0.8). Read A is X, read B is Y; extra reads alternate X, Y
#   team_bias    : the whole team shares one habit: s ~ N(+1.5,1), r_t ~ U(0.8,1.1) for every read
#   jitter       : indep + brush jitter: ~30 % of surface voxels removed in smooth random patches
# Slip rates (ramus 0.3, D1/OM1 0.15) as before in every scenario.
# Predictors (modes): single/both, agree (disagree -> ignore), union (extent OR, name conflict -> ignore),
#   a11 (judge's hybrid: each read a sample, name conflict inside shared vessel -> ignore, extent kept).
# Scored by tF1 @1.5 mm against the truth T and against the two reads (A10: mean of tF1 vs each read), plus
# inter-read tF1 (B vs A).   Usage: python r5_corr.py SCENARIO[,SCENARIO...] NCASES K
import sys, os, json, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
sys.path.insert(0, '/home/user/Asclepius/trillium/crucible/lib')
import sim  # noqa: E402
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
D = SCR + '/work/Crucible/r2data'; OUT = SCR + '/work/Crucible/' + ('r5corr_fill' if os.environ.get('FILL') == '1' else 'r5corr_hier' if os.environ.get('HIER') == '1' else 'r5corr'); os.makedirs(OUT, exist_ok=True)
S26 = np.ones((3, 3, 3)); IGN = sim.IGNORE
meta = json.load(open(D + '/meta.json'))


class Case:
    def __init__(s, c):
        lab = np.load(f'{D}/{c}_lab.npy'); s.sp = np.array(meta[c]['spacing'])
        m = ((lab >> 4) & 7) > 0; L14 = (lab & 15).astype(np.uint8)
        u = np.argwhere(m); lo = np.maximum(u.min(0) - 3, 0); hi = u.max(0) + 4
        sl = tuple(slice(a, b) for a, b in zip(lo, hi)); m = m[sl]; L14 = L14[sl]
        s.T, s.near14 = sim.truth(m, L14); s.m = s.T > 0
        s.rl = sim.local_radius(s.m, s.sp); s.roots = sim.ostia(s.T, s.sp)
        s.d_lm = ndi.distance_transform_edt(s.T != 1, sampling=s.sp)
        s.d_23 = ndi.distance_transform_edt(~np.isin(s.T, (2, 3)), sampling=s.sp)
        _, s.ind23 = ndi.distance_transform_edt(~np.isin(s.T, (2, 3)), return_indices=True)
        surf = s.m & ~ndi.binary_erosion(s.m, S26); s.surf = surf

    def read(s, rng, sh, rt, jitter=False):
        R = s.T.copy()
        if sh > 0: R[np.isin(R, (2, 3)) & (s.d_lm <= sh)] = 1
        elif sh < 0:
            sel = (R == 1) & (s.d_23 <= -sh)
            R[sel] = s.T[tuple(s.ind23)][sel]
        if rng.random() < sim.PARAMS['P_RAMUS']: R[(s.near14 == 8) & s.m & (R == 3)] = 2
        if rng.random() < sim.PARAMS['P_SIDE']:
            k = rng.choice([4, 6]); sel = (s.near14 == k) & s.m & np.isin(R, (2, 3)); R[sel] = 5 - R[sel]
        lab, _ = ndi.label(s.m & (s.rl >= rt), S26)
        rc = {lab[tuple(r)] for r in s.roots if lab[tuple(r)] > 0}
        R[~np.isin(lab, list(rc))] = 0
        if jitter:
            f = ndi.gaussian_filter(rng.standard_normal(R.shape).astype(np.float32), 3)
            R[s.surf & (f > np.percentile(f[s.surf], 70))] = 0
        return R


def draw(sc, case_rng, rng, who):
    u = rng.uniform
    if sc in ('indep', 'jitter'): return rng.normal(0, 2), u(0.6, 1.05)
    if sc == 'corr_trunc': return rng.normal(0, 2), 0.8 * case_rng['u'] + 0.2 * u(0.6, 1.05)
    if sc == 'corr_carina': return case_rng['m'] + rng.normal(0, 0.7), u(0.6, 1.05)
    if sc == 'annot_bias':
        return (rng.normal(1.5, 1), u(0.8, 1.1)) if who == 'X' else (rng.normal(-1.5, 1), u(0.55, 0.8))
    if sc == 'team_bias': return rng.normal(1.5, 1), u(0.8, 1.1)
    raise ValueError(sc)


FILL = os.environ.get('FILL') == '1'


def mode(stack):
    cnt = np.stack([(stack == k).sum(0) for k in range(5)]); tot = cnt.sum(0)
    m = cnt.argmax(0).astype(np.uint8)
    if FILL and (tot == 0).any():
        # voxels ignored in EVERY sample: a network extrapolates from supervised neighbours rather than predicting
        # background, so give them the label of the nearest supervised voxel (FILL=1; default = background, worst case)
        _, ind = ndi.distance_transform_edt(tot == 0, return_indices=True); m = m[tuple(ind)]
    else:
        m[tot == 0] = 0
    return m


def hmode(stack):
    # hierarchical read-out: vessel if vessel votes > background votes, then the plurality class among vessel votes
    # (what argmax over [P(bg), sum P(classes)] then argmax over classes would give)
    cnt = np.stack([(stack == k).sum(0) for k in range(5)])
    ves = cnt[1:].sum(0) > cnt[0]
    m = (cnt[1:].argmax(0) + 1).astype(np.uint8); m[~ves] = 0; return m


class Ref:
    def __init__(s, lab):
        s.lab = lab; sk = skeletonize(lab > 0); s.pts = np.argwhere(sk); s.cls = lab[tuple(s.pts.T)]


def pred_info(p, sp, roots, tol=1.5):
    pm = p > 0
    comp, _ = ndi.label(ndi.distance_transform_edt(~pm, sampling=sp) <= tol / 2, S26)
    rc = set(); r = np.ceil(1.5 / sp).astype(int)
    for rt in roots:
        sl = tuple(slice(max(a - b, 0), a + b + 1) for a, b in zip(rt, r))
        g = np.stack(np.meshgrid(*[np.arange(x.start, min(x.stop, n)) for x, n in zip(sl, p.shape)], indexing='ij'), -1)
        d = np.sqrt((((g - rt) * sp) ** 2).sum(-1)); sub = comp[sl][: d.shape[0], : d.shape[1], : d.shape[2]]
        rc |= set(np.unique(sub[(d <= 1.5) & (sub > 0)]).tolist())
    pp = np.argwhere(skeletonize(pm)) if pm.any() else np.zeros((0, 3), int)
    return dict(p=p, comp=comp, rc=rc, pp=pp, ppl=p[tuple(pp.T)])


def tf1(ref, pi):
    pl = pi['p'][tuple(ref.pts.T)]; rooted = np.isin(pi['comp'][tuple(ref.pts.T)], list(pi['rc']))
    ppr = ref.lab[tuple(pi['pp'].T)]; out = []
    for c in (1, 2, 3, 4):
        g = ref.cls == c
        if not g.any(): continue
        rec = ((pl == c) & rooted & g).sum() / g.sum()
        pc = pi['ppl'] == c; prec = (ppr[pc] == c).mean() if pc.any() else 0.0
        out.append(2 * rec * prec / (rec + prec) if rec + prec else 0.0)
    return float(np.mean(out))


if __name__ == '__main__':
    scs, N, K = sys.argv[1].split(','), int(sys.argv[2]), int(sys.argv[3])
    cases = sorted(meta)[:N]
    for c in cases:
        cs = None
        for sc in scs:
            fn = f'{OUT}/{sc}_{c}.json'
            if os.path.exists(fn): continue
            cs = cs or Case(c)
            rng = np.random.default_rng(7 + int(c[1:])); crng = {'u': rng.uniform(0.6, 1.05), 'm': rng.normal(0, 2)}
            reads = []
            for i in range(K + 2):
                who = 'X' if i % 2 == 0 else 'Y'
                sh, rt = draw(sc, crng, rng, who)
                reads.append(cs.read(rng, sh, rt, jitter=(sc == 'jitter')))
            A, B = reads[0], reads[1]; ex = reads[2:]; pairs = [(ex[i], ex[i + 1]) for i in range(0, K - 1, 2)]
            a11 = [x for a, b in pairs for x in sim.fuse(a, b, 'a11')]
            P = {'single_or_both': mode(np.stack(ex)),
                 'agree': mode(np.stack([sim.fuse(a, b, 'agree') for a, b in pairs])),
                 'union': mode(np.stack([sim.fuse(a, b, 'union') for a, b in pairs])),
                 'a11': mode(np.stack(a11)), 'truth': cs.T}
            if os.environ.get('HIER') == '1':
                P['both_hier'] = hmode(np.stack(ex)); P['a11_hier'] = hmode(np.stack(a11))
            refs = {'T': Ref(cs.T), 'A': Ref(A), 'B': Ref(B)}
            r = {'case': c, 'scenario': sc, 'inter_read': tf1(refs['A'], pred_info(B, cs.sp, cs.roots))}
            for k, p in P.items():
                pi = pred_info(p, cs.sp, cs.roots)
                r[f'{k}_vs_T'] = tf1(refs['T'], pi); r[f'{k}_vs_reads'] = (tf1(refs['A'], pi) + tf1(refs['B'], pi)) / 2
                r[f'{k}_fg'] = float((p > 0).sum() / cs.m.sum())
            json.dump(r, open(fn, 'w')); print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
