"""The hashes of record for J1F-A and the refusals on any mismatch (F-A27, F-A28, F-A29, F-A36).

`collect` and `check` pin four files (F-A36):
  scorer   trillium/janus1f/lib/j1f_scorer.py   5221032f...2e5b  (F-A28; byte copy of experiments/Atlas/j1f_r3)
  gates    configs/janus1/j1f_gates.json        198b3b15...1406  (F-A27; byte copy of experiments/Judge/j1f_r3)
  labels   src/segqueue14/labels.py             5f69b5be...0a4b  (F-A17)
  tf1      src/segtrain/tf1.py                  24441cf8...5254  (A1c)
and, for `prep`, Step T's plans and fingerprint (#302) and the D45 split (#306).
"""
import hashlib
import json
import os

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # trillium/janus1f/lib
ROOT = os.path.abspath(os.path.join(LIB, '..', '..', '..'))                # the repository

SCORER = os.path.join(LIB, 'j1f_scorer.py')
GATES = os.path.join(ROOT, 'configs', 'janus1', 'j1f_gates.json')
LABELS = os.path.join(ROOT, 'src', 'segqueue14', 'labels.py')
TF1 = os.path.join(ROOT, 'src', 'segtrain', 'tf1.py')
PARENTS = os.path.join(ROOT, 'configs', 'janus1', 'j1f_parents.json')
SPLIT = os.path.join(ROOT, 'configs', 'janus1', 'split-2026-11.json')
SEALED = os.path.join(ROOT, 'trillium', 'icx4', 'sealed_test.json')

SCORER_SHA256 = '5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b'
GATES_SHA256 = '198b3b158098d846358971ad8a85f22eda7f9a76c00f0e1ee798e15171191406'
LABELS_SHA256 = '5f69b5bef59ad1346c5877a43c65daf7bdf1329b0ca7e427b6addd55d0000a4b'
TF1_SHA256 = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
SPLIT_SHA256 = '19b832fee023986e1dc64b724fbf218fce71942b7f3908f5ae110388ca1b4dd3'      # #306 §1
TRAIN620_SHA256 = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'   # F0-r2 line 1
LOCKED100_SHA256 = 'bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895'  # F0-r2 line 2
FITCHECK20_SHA256 = '3f3b696c231d71bcc99763f83983fb824c2e74bdd597a37e09220188191f1330'  # F-A5, Delta v3 §4.1
CONVERTER_LINE = {'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}  # F0-r2 line 3
PLANS_SHA256 = 'b7178bbc6d86e658e449b72cef7621f06de222c107083a2622792d346bd93cc2'       # Step T
FINGERPRINT_SHA256 = 'e41c772faf5e58a31d44cfc948031354dde6d0070a900a1ebfdb14691f937e05'  # Step T

# The four pins `collect` checks (F-A36), in the order `check` prints them.
FOUR = (('scorer', SCORER, SCORER_SHA256, 'J1F_SCORER_SHA256'),
        ('gates', GATES, GATES_SHA256, 'J1F_GATES_SHA256'),
        ('labels.py', LABELS, LABELS_SHA256, None),
        ('tf1.py', TF1, TF1_SHA256, None))


class PinError(RuntimeError):
    """A pinned file differs from its hash of record; the launcher refuses."""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ids_sha256(ids):
    """The split pins' form: sha256 of the sorted ids joined by newlines (F0-r2)."""
    return hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()


def check_four(files=None, env=None):
    """Return the printed lines for the four pins; raise PinError on any mismatch.

    `files` overrides the paths (tests); `env` (default os.environ) may carry J1F_SCORER_SHA256 / J1F_GATES_SHA256,
    the values the lead exported from #303. When set, they must equal the hashes of record as well."""
    env = os.environ if env is None else env
    lines, bad = [], []
    for name, path, want, var in FOUR:
        path = (files or {}).get(name, path)
        try:
            got = sha256_file(path)
        except OSError as e:
            got = f'unreadable ({e.__class__.__name__})'
        ok = got == want
        exported = env.get(var) if var else None
        if exported is not None and exported != want:
            ok = False
            bad.append(f'{name}: ${var}={exported} is not the hash of record {want}')
        if got != want:
            bad.append(f'{name}: {path} has sha256 {got}, not {want}')
        lines.append(f'pin {name:9s} {got} {"OK" if ok else "MISMATCH"}')
    if bad:
        raise PinError('refusing: ' + '; '.join(bad))
    return lines


def check_file(path, want, what):
    got = sha256_file(path)
    if got != want:
        raise PinError(f'refusing: {what} {path} has sha256 {got}, not {want}')
    return got


def load_json(path):
    with open(path) as f:
        return json.load(f)
