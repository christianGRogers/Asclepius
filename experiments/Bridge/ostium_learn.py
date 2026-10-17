"""Learned ostium picker: logistic regression on endpoint features (label from ImageCAS-X ostium), 5-fold CV by case.
Reports top-1 ostium accuracy (chosen endpoint within 5 mm of the ImageCAS-X ostium) vs the hand rules,
and the accuracy as a function of the number of training cases (label efficiency).
usage: ostium_learn.py EV.jsonl [CTEV.jsonl]"""
import sys, json, numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
F = ['r6', 'r3', 'rmax6', 'h', 'sl', 'beyond', 'dR', 'r6_rk', 'r3_rk', 'h_rk', 'dR_rk']
rows = [json.loads(l) for l in open(sys.argv[1])]
extra = sys.argv[2:] and {json.loads(l)['case']: json.loads(l) for l in open(sys.argv[2])}
if extra:
    F = F + ['bright']
cases = []
for r in rows:
    ef = r.get('ef')
    if not ef or 'd_true' not in ef[0]:
        continue
    if extra:
        if r['case'] not in extra:
            continue
        b = {f['e']: f.get('bright', 0) for f in extra[r['case']]['ef']}
        for f in ef:
            f['bright'] = b.get(f['e'], 0)
    ef = [f for f in ef if not f['edge']]
    if min(f['d_true'] for f in ef) > 5:
        continue  # ostium not representable by any endpoint
    X = np.array([[f[k] for k in F] for f in ef]); y = np.array([f['d_true'] < 5 for f in ef])
    cases.append((r['case'], X, y, ef))
print('cases', len(cases), 'features', F)
rng = np.random.RandomState(0); idx = rng.permutation(len(cases)); folds = np.array_split(idx, 5)


def fit(tr):
    X = np.concatenate([cases[i][1] for i in tr]); y = np.concatenate([cases[i][2] for i in tr])
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight='balanced', max_iter=2000)).fit(X, y)


def acc(model, te):
    return np.mean([cases[i][2][np.argmax(model.decision_function(cases[i][1]))] for i in te])


cv = []
for k in range(5):
    te = folds[k]; tr = np.concatenate([folds[j] for j in range(5) if j != k])
    cv.append(acc(fit(tr), te) * len(te))
print('learned ostium top-1 (5-fold CV): %.3f' % (sum(cv) / len(cases)))
for name, fn in [('terminal radius+h', lambda f: f['r3'] + 0.5 * f['h']), ('r6', lambda f: f['r6']),
                 ('combo', lambda f: f['r6'] + 0.5 * f['h'] - 0.02 * f['dR'])] + ([('CT bright', lambda f: f['bright'])] if extra else []):
    print('rule %-18s top-1: %.3f' % (name, np.mean([c[2][np.argmax([fn(f) for f in c[3]])] for c in cases])))
# label efficiency: train on N cases, test on a fixed third
te = idx[:len(cases) // 3]; pool = idx[len(cases) // 3:]
for N in (5, 10, 20, 40, 80, 160, 320):
    if N > len(pool):
        break
    a = [acc(fit(np.random.RandomState(s).choice(pool, N, replace=False)), te) for s in range(5)]
    print('N=%3d train cases -> top-1 %.3f +- %.3f (test n=%d)' % (N, np.mean(a), np.std(a), len(te)))
m = fit(idx)
import os
if os.environ.get('SAVE_W'):
    json.dump(dict(F=F, mean=m[0].mean_.tolist(), scale=m[0].scale_.tolist(), coef=m[-1].coef_[0].tolist(),
                   trained_on=[cases[i][0] for i in idx]), open(os.environ['SAVE_W'], 'w'))
print('coefficients:', dict(zip(F, np.round(m[-1].coef_[0], 2))))
