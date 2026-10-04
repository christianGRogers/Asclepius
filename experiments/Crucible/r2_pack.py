# Pack r2data labels into one uint8 per voxel to fit the 4 GB scratch budget:
# bits 0-3 = ICX 14-class, bits 4-6 = thick4 (Girder proxy), bit 7 = ramus/Other voxel assigned to LCx (else LAD).
# thin4 = TERR[icx14] with ramus/Other -> 3 if bit7 else 2. Keeps 10 of the ICX-test cases (sorted) as the test set.
import os, json, numpy as np
D = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible/r2data'
meta = json.load(open(D + '/meta.json'))
tests = sorted(c for c, v in meta.items() if v['test'])
drop = tests[10:]
for c in list(meta):
    if c in drop:
        for k in ('ct', 'icx14', 'thin4', 'thick4', 'lab'):
            if os.path.exists(f'{D}/{c}_{k}.npy'): os.remove(f'{D}/{c}_{k}.npy')
        del meta[c]; continue
    if os.path.exists(f'{D}/{c}_lab.npy'): continue
    L = np.load(f'{D}/{c}_icx14.npy'); t4 = np.load(f'{D}/{c}_thin4.npy'); k4 = np.load(f'{D}/{c}_thick4.npy')
    amb3 = ((L == 8) | (L == 14)) & (t4 == 3)
    np.save(f'{D}/{c}_lab.npy', (L | (k4 << 4) | (amb3.astype(np.uint8) << 7)).astype(np.uint8))
    for k in ('icx14', 'thin4', 'thick4'): os.remove(f'{D}/{c}_{k}.npy')
json.dump(meta, open(D + '/meta.json', 'w'))
print(len(meta), sum(v['test'] for v in meta.values()), 'dropped', drop)
