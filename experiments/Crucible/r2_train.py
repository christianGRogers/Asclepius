# Round 2 paired CPU experiment: identical tiny 3D U-Nets trained on three label targets, same cases/seed/schedule.
#   arm thin4  : ICX lumen, 4-class territory           (Crucible option A, direct 4-class)
#   arm thin14 : ICX lumen, ICX 14 classes, read out 4  (Crucible v1's 14-class head)
#   arm thick4 : Girder mask named by nearest ICX class (Atlas's proxy / option B)
# Usage: python r2_train.py ARM ITERS [SEED]
# Writes test-set 4-class predictions + foreground probability to work/Crucible/r2pred/<ARM>/.
import os, sys, json, time, numpy as np, torch, torch.nn as nn, torch.nn.functional as F
from scipy import ndimage as ndi
torch.set_num_threads(int(os.environ.get('TORCH_THREADS', '1')))
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
D = SCR + '/work/Crucible/r2data'
ARM, ITERS = sys.argv[1], int(sys.argv[2]); SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 0
OUT = SCR + f'/work/Crucible/r2pred/{ARM}_s{SEED}'; os.makedirs(OUT, exist_ok=True)
TGT = {'thin4': 'thin4', 'thin14': 'icx14', 'thick4': 'thick4'}[ARM]
NC = 15 if ARM == 'thin14' else 5
TERR = np.zeros(15, np.uint8); TERR[[1]] = 1; TERR[[2, 4, 5]] = 2; TERR[[3, 6, 7, 12, 13]] = 3; TERR[[9, 10, 11]] = 4
PATCH = (80, 80, 56)
TILE = (160, 160, 112)  # inference tile (fully convolutional), step 3/4
meta = json.load(open(D + '/meta.json'))
train = sorted(c for c, v in meta.items() if not v['test']); test = sorted(c for c, v in meta.items() if v['test'])
rng = np.random.default_rng(SEED); torch.manual_seed(SEED)


def norm(ct): return ((np.clip(ct.astype(np.float32), -300, 1300) - 100.0) / 400.0)




def decode(lab):  # see r2_pack.py
    L = lab & 15
    if TGT == 'icx14': return L
    if TGT == 'thick4': return (lab >> 4) & 7
    t = TERR[L]; amb = (L == 8) | (L == 14)
    return np.where(amb, np.where(lab >> 7, 3, 2), t).astype(np.uint8)


data = {c: (np.load(f'{D}/{c}_ct.npy', mmap_mode='r'), np.load(f'{D}/{c}_lab.npy', mmap_mode='r')) for c in train}
fg = {c: np.argwhere(decode(np.asarray(data[c][1])) > 0) for c in train}


def sample():
    c = train[rng.integers(len(train))]; ct, lab = data[c]; sh = np.array(ct.shape); p = np.array(PATCH)
    if rng.random() < 0.67:
        ctr = fg[c][rng.integers(len(fg[c]))] + rng.integers(-p // 4, p // 4 + 1)
    else:
        ctr = rng.integers(0, sh)
    lo = np.clip(ctr - p // 2, 0, np.maximum(sh - p, 0))
    sl = tuple(slice(a, a + b) for a, b in zip(lo, p))
    x = norm(np.asarray(ct[sl])); y = decode(np.asarray(lab[sl])).astype(np.int64)
    pad = [(0, b - a) for a, b in zip(x.shape, p)]
    x = np.pad(x, pad, constant_values=-1.0); y = np.pad(y, pad)
    x = x * rng.uniform(0.9, 1.1) + rng.uniform(-0.1, 0.1)  # mild intensity aug; no mirroring/rotation
    return x, y


def block(i, o): return nn.Sequential(nn.Conv3d(i, o, 3, padding=1), nn.InstanceNorm3d(o, affine=True), nn.LeakyReLU(0.01),
                                      nn.Conv3d(o, o, 3, padding=1), nn.InstanceNorm3d(o, affine=True), nn.LeakyReLU(0.01))


class UNet(nn.Module):
    def __init__(s, nc, ch=(8, 16, 32, 64)):
        super().__init__()
        s.enc = nn.ModuleList([block(1, ch[0])] + [block(ch[i], ch[i + 1]) for i in range(len(ch) - 1)])
        s.up = nn.ModuleList([nn.ConvTranspose3d(ch[i + 1], ch[i], 2, 2) for i in range(len(ch) - 1)])
        s.dec = nn.ModuleList([block(2 * ch[i], ch[i]) for i in range(len(ch) - 1)])
        s.head = nn.Conv3d(ch[0], nc, 1)

    def forward(s, x):
        sk = []
        for i, e in enumerate(s.enc):
            x = e(x if i == 0 else F.max_pool3d(x, 2)); sk.append(x)
        for i in reversed(range(len(s.up))):
            x = s.dec[i](torch.cat([s.up[i](x), sk[i]], 1))
        return s.head(x)


def loss_fn(logit, y):
    ce = F.cross_entropy(logit, y)
    p = logit.softmax(1); oh = F.one_hot(y, NC).permute(0, 4, 1, 2, 3).float()
    inter = (p * oh).sum((0, 2, 3, 4)); den = p.sum((0, 2, 3, 4)) + oh.sum((0, 2, 3, 4))
    present = oh.sum((0, 2, 3, 4))[1:] > 0
    dice = (2 * inter[1:] + 1e-5) / (den[1:] + 1e-5)
    return ce + (1 - dice[present].mean() if present.any() else 0.0)


net = UNet(NC); opt = torch.optim.Adam(net.parameters(), 1e-3, weight_decay=1e-5)
log = open(OUT + '/train.log', 'a'); t0 = time.time(); start = 0
CK = OUT + '/ckpt.pt'
if os.path.exists(CK):  # resume (container restarts)
    ck = torch.load(CK); net.load_state_dict(ck['net']); opt.load_state_dict(ck['opt']); start = ck['it']
    rng = np.random.default_rng(SEED + start); print('resumed', start, file=log, flush=True)
if os.path.exists(OUT + '/net.pt'):  # training already finished: inference only
    net.load_state_dict(torch.load(OUT + '/net.pt')); start = ITERS
for it in range(start, ITERS):
    if it % 100 == 0 and it > start:
        torch.save({'net': net.state_dict(), 'opt': opt.state_dict(), 'it': it}, CK)
    for g in opt.param_groups: g['lr'] = 1e-3 * (1 - it / ITERS) ** 0.9
    b = [sample() for _ in range(2)]
    x = torch.from_numpy(np.stack([a for a, _ in b])[:, None]); y = torch.from_numpy(np.stack([c for _, c in b]))
    l = loss_fn(net(x), y); opt.zero_grad(); l.backward(); opt.step()
    if it % 100 == 0 or it == 20: print(it, round(float(l.detach()), 4), round(time.time() - t0), 's', file=log, flush=True)
if not os.path.exists(OUT + '/net.pt'): torch.save(net.state_dict(), OUT + '/net.pt')

# sliding-window inference on the test crops (160x160x112 tiles, step 3/4 tile, uniform averaging)
net.eval()
with torch.no_grad():
    for c in test:
        if os.path.exists(f'{OUT}/{c}_pred4.npy'): continue
        ct = norm(np.load(f'{D}/{c}_ct.npy')); sh = np.array(ct.shape); p = np.array(TILE)
        acc = np.zeros((NC,) + ct.shape, np.float32); cnt = np.zeros(ct.shape, np.float32)
        starts = [sorted(set(list(range(0, max(s - q, 0) + 1, 3 * q // 4)) + [max(s - q, 0)])) for s, q in zip(sh, p)]
        for a in starts[0]:
            for bb in starts[1]:
                for cc in starts[2]:
                    sl = (slice(a, a + p[0]), slice(bb, bb + p[1]), slice(cc, cc + p[2]))
                    x = ct[sl]; pad = [(0, q - s) for s, q in zip(x.shape, p)]
                    xp = np.pad(x, pad, constant_values=-1.0)
                    pr = net(torch.from_numpy(xp[None, None]))[0].softmax(0).numpy()
                    pr = pr[:, :x.shape[0], :x.shape[1], :x.shape[2]]
                    acc[(slice(None),) + sl] += pr; cnt[sl] += 1
        prob = acc / cnt; am = prob.argmax(0).astype(np.uint8)
        if NC == 15:
            p4 = TERR[am]; amb = (am == 8) | (am == 14)
            if amb.any():
                _, ind = ndi.distance_transform_edt(~np.isin(p4, (2, 3)), return_indices=True); p4[amb] = p4[tuple(ind)][amb]
        else:
            p4 = am
        np.save(f'{OUT}/{c}_pred4.npy', p4.astype(np.uint8)); np.save(f'{OUT}/{c}_fg.npy', (1 - prob[0]).astype(np.float16))
        print('pred', c, round(time.time() - t0), 's', file=log, flush=True)
print('done', round(time.time() - t0), file=log, flush=True)
