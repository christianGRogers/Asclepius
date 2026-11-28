"""Decode F, T and G (F-A19, F-A31), the chunked decode-and-delete, and `collect`'s marker check.

Channels: 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB.

  F   territory = argmax of the summed probabilities over F's groups; class = argmax inside it.
  G   three uint8 maps, at every voxel: the argmax within {LAD, D1, D2, D3}, within {LCx, OM1, OM2, Ramus, PDA, PLB},
      within {RCA, PDA, PLB}.
  T   G selected by Janus 0's territory; T's four classes ARE Janus 0's map (asserted bit-equal).
  T_L G selected by Janus 1-L's shipped map, under the same assertion.

Per case `decode` writes <case>_F, _T, _G2, _G3, _G4 (.nii.gz, through nnU-Net's own writer, so the grid and header
are nnU-Net's export's, which is Janus 0's), deletes the case's npz, pkl and nnU-Net's own argmax export, and writes
`<case>.j1f_decoded` with every map's sha256. `collect` reads only maps whose marker matches.

  python -m janus1f.decode --run a1 --chunk 0 --probs <nnU-Net out dir> --janus0 <pred_fir> --out <maps dir> \
      --plans <plans.json>
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np

from .parents import F_GROUPS

# T's name sets inside Janus 0's territories (F-A19): the LCx territory admits PDA and PLB
T_SETS = {2: (2, 5, 6, 7), 3: (3, 8, 9, 10, 11, 12), 4: (4, 11, 12)}
# Round 2's LCx set without PDA/PLB: F-A19's broken fixture (cannot name a left PDA)
OLD_T_SETS = {2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}
MAPS = ('F', 'T', 'G2', 'G3', 'G4')
MARKER = '.j1f_decoded'
# what nnU-Net 2.8.1 writes into a predict output folder besides the cases; decode removes these too
NNUNET_SIDECARS = ('dataset.json', 'plans.json', 'predict_from_raw_data_args.json')


class DecodeError(RuntimeError):
    pass


def territory(prob):
    return np.argmax(np.stack([prob[list(g)].sum(0) for g in F_GROUPS.values()]), 0).astype(np.uint8)


def within_group(prob, sets=None):
    """G: {2: uint8, 3: uint8, 4: uint8}, the argmax channel inside each name set, at every voxel."""
    sets = T_SETS if sets is None else sets
    out = {}
    for t, chans in sets.items():
        chans = np.asarray(chans)
        out[t] = chans[np.argmax(prob[chans], 0)].astype(np.uint8)
    return out


def decode_in_territory(terr4, g):
    terr4 = np.asarray(terr4)
    out = np.zeros(terr4.shape, np.uint8)
    out[terr4 == 1] = 1
    for t in (2, 3, 4):
        m = terr4 == t
        out[m] = g[t][m]
    return out


def collapse_by_group(lab13, groups=None):
    """13-class map -> its territory under F's groups (not SegQueue's contact collapse: that is the scorer's)."""
    lab13 = np.asarray(lab13)
    out = np.zeros(lab13.shape, np.uint8)
    for t, g in (groups or F_GROUPS).items():
        out[np.isin(lab13, g)] = t
    return out


def decode_f(prob):
    """F: the hierarchical decode. Its territory map is `territory(prob)` (F-A4)."""
    return decode_in_territory(territory(prob), within_group(prob, {k: v for k, v in F_GROUPS.items() if k >= 2}))


def decode_t(four, g):
    """T (or T_L): G selected by a four-class map. Returns the 13-class map; asserts its four classes are `four`."""
    four = np.asarray(four)
    if four.dtype.kind not in 'iu' or four.min() < 0 or four.max() > 4:
        raise DecodeError('the four-class map must hold 0..4')
    t13 = decode_in_territory(four, g)
    back = np.where(t13 == 1, 1, 0).astype(np.uint8)
    for t in (2, 3, 4):
        back[(four == t) & np.isin(t13, T_SETS[t])] = t
    if not np.array_equal(back, four.astype(np.uint8)):
        raise DecodeError('T must keep the four-class map territory for territory (F-A19, F-A31)')
    return t13


def check_t(t13, four, g):
    """collect: T rebuilt from G and the four-class map must equal the stored T byte for byte."""
    if not np.array_equal(decode_t(four, g), np.asarray(t13)):
        raise DecodeError('T is not G selected by the four-class map')
    return True


def sha_array(a):
    a = np.ascontiguousarray(np.asarray(a, np.uint8))
    return hashlib.sha256(a.tobytes() + repr(a.shape).encode()).hexdigest()


# ---------------------------------------------------------------------------- the chunk loop
class NnunetIO:
    """nnU-Net's own reader/writer from the plans (SimpleITKIO for icx4), so maps share the export's grid."""

    def __init__(self, plans_json):
        from nnunetv2.utilities.plans_handling.plans_handler import PlansManager
        with open(plans_json) as f:
            rw = PlansManager(json.load(f)).image_reader_writer_class   # a class (2.8.1 property)
        self.rw = rw() if isinstance(rw, type) else rw

    def read_seg(self, path):
        seg, props = self.rw.read_seg(path)
        return np.asarray(seg)[0], props

    def write_seg(self, arr, path, props):
        self.rw.write_seg(np.asarray(arr, np.uint8), path, props)

    @staticmethod
    def load_case(npz, pkl):
        import pickle
        prob = np.load(npz)['probabilities'].astype(np.float32)
        with open(pkl, 'rb') as f:
            props = pickle.load(f)
        return prob, props


def decode_case(case, prob, props, janus0_four, out_dir, io):
    """Write F, T, G2-G4 for one case and its marker. Returns the marker dict."""
    if prob.shape[0] != 13:
        raise DecodeError(f'{case}: {prob.shape[0]} channels, not 13')
    if tuple(janus0_four.shape) != tuple(prob.shape[1:]):
        raise DecodeError(f'{case}: Janus 0 map {janus0_four.shape} is not on the npz grid {prob.shape[1:]}')
    g = within_group(prob)
    maps = {'F': decode_f(prob), 'T': decode_t(janus0_four, g), 'G2': g[2], 'G3': g[3], 'G4': g[4]}
    marker = {'case': case, 'maps': {}}
    for k, a in maps.items():
        p = os.path.join(out_dir, f'{case}_{k}.nii.gz')
        io.write_seg(a, p + '.part.nii.gz', props)
        os.replace(p + '.part.nii.gz', p)
        marker['maps'][k] = {'file_sha256': _sha_file(p), 'array_sha256': sha_array(a)}
    with open(os.path.join(out_dir, case + MARKER), 'w') as f:
        json.dump(marker, f, indent=1)
    return marker


def decode_chunk(probs_dir, out_dir, janus0_dir, io, cases=None):
    """Decode every case nnU-Net wrote into `probs_dir`, then delete its npz, pkl and argmax export (and nnU-Net's
    three sidecar files). Refuses if anything else is left (chunk hygiene). Returns the decoded case ids."""
    os.makedirs(out_dir, exist_ok=True)
    found = sorted(f[:-4] for f in os.listdir(probs_dir) if f.endswith('.npz'))
    if cases is not None and sorted(cases) != found:
        raise DecodeError(f'chunk holds {found[:3]}..., expected {sorted(cases)[:3]}...')
    for c in found:
        j0p = os.path.join(janus0_dir, c + '.nii.gz')
        if not os.path.exists(j0p):
            raise DecodeError(f'{c}: no Janus 0 baseline prediction {j0p}; refusing (never re-predicted)')
        prob, props = io.load_case(os.path.join(probs_dir, c + '.npz'), os.path.join(probs_dir, c + '.pkl'))
        j0, _ = io.read_seg(j0p)
        decode_case(c, prob, props, np.asarray(j0).astype(np.uint8), out_dir, io)
        del prob
        for ext in ('.npz', '.pkl', '.nii.gz'):
            p = os.path.join(probs_dir, c + ext)
            if os.path.exists(p):
                os.remove(p)
    for s in NNUNET_SIDECARS:
        p = os.path.join(probs_dir, s)
        if os.path.exists(p):
            os.remove(p)
    left = os.listdir(probs_dir)
    if left:
        raise DecodeError(f'chunk hygiene: {len(left)} file(s) left in {probs_dir}: {sorted(left)[:5]}')
    return found


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def collect_inputs(maps_dir, cases):
    """Refuse any case without its marker, or whose map files do not match the marker. Returns {case: {map: path}}."""
    out = {}
    for c in cases:
        m = os.path.join(maps_dir, c + MARKER)
        if not os.path.exists(m):
            raise DecodeError(f'{c}: no decode marker in {maps_dir}; collect reads only decode output')
        with open(m) as f:
            mk = json.load(f)
        paths = {}
        for k in MAPS:
            p = os.path.join(maps_dir, f'{c}_{k}.nii.gz')
            if k not in mk.get('maps', {}) or not os.path.exists(p) or _sha_file(p) != mk['maps'][k]['file_sha256']:
                raise DecodeError(f'{c}: map {k} is missing or does not match its decode marker')
            paths[k] = p
        out[c] = paths
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m janus1f.decode')
    ap.add_argument('--run', required=True, choices=('a1', 'a2'))
    ap.add_argument('--chunk', required=True, type=int)
    ap.add_argument('--probs', required=True)
    ap.add_argument('--janus0', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--plans', required=True)
    ap.add_argument('--cases', help='JSON list of the chunk ids (the chunk plan); refuses on a difference')
    a = ap.parse_args(argv)
    cases = json.load(open(a.cases)) if a.cases else None
    done = decode_chunk(a.probs, a.out, a.janus0, NnunetIO(a.plans), cases)
    print(f'[janus1f] decode {a.run} chunk {a.chunk}: {len(done)} cases -> F, T, G2-G4 + marker; '
          'npz, pkl and argmax export deleted')
    return 0


if __name__ == '__main__':
    sys.exit(main())
