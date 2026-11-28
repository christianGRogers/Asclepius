"""Janus 1-F round 4 (Atlas): j1f2_freeze.py's refusals on whole exports (no pool data: stand-in masks only).
1. a read dir named as a sealed pool volume -> exit 3, and no file of the export is opened;
2. its __r2 replica alone -> exit 3;
3. a manifest written with --acceptance-scoring -> exit 3;
4. a --four-class export -> exit 3;
5. --no-guard on a non-stand-in name -> exit 3;
6. the annotator benchmark -> exit 3.
Usage: python test_refusals.py <standin_export_dir> <scratch_dir>"""
import builtins, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import j1f2_freeze as F  # noqa: E402

src, tmp = sys.argv[1], sys.argv[2]
one = sorted(n for n in os.listdir(src) if os.path.isdir(os.path.join(src, n)) and '__r' not in n[10:])[-1]
seal = F.pool_seal.load_pool_seal(os.path.join(F._ROOT, F.pool_seal.SEAL_RELPATH))
sealed = sorted(seal.volumes)[0]


def make(name, dirs, manifest=None):
    d = os.path.join(tmp, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for new in dirs:
        shutil.copytree(os.path.join(src, one), os.path.join(d, new))
    if manifest is not None:
        json.dump(manifest, open(os.path.join(d, 'manifest.json'), 'w'))
    return d


def rc(d, *extra):
    p = subprocess.run([sys.executable, os.path.join(HERE, 'j1f2_freeze.py'), d, d + '_out', '--np', '1', *extra],
                       capture_output=True, text=True)
    return p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:160]


# 1, with an open() spy in-process: nothing under the export may be opened before the refusal
d1 = make('sealed', [one, sealed])
opened = []
real_open = builtins.open
def spy(path, *a, **k):  # noqa: E302
    if str(path).startswith(d1 + '/'):
        opened.append(str(path))
    return real_open(path, *a, **k)
builtins.open = spy
try:
    F.run(d1, d1 + '_out', nproc=1)
    code = 0
except SystemExit as e:
    code = e.code
finally:
    builtins.open = real_open
cases = [('sealed volume beside a stand-in', code, f'opened {len(opened)} file(s) of the export')]
cases.append(('sealed replica __r2',) + rc(make('sealed_r2', [one, sealed + '__r2'])))
cases.append(('acceptance-mode manifest',) + rc(make('accept', [one], {'source': {'pool_seal': {'mode': 'acceptance'}}})))
cases.append(('four-class export',) + rc(make('four', [one], {'source': {'classes': 'four'}})))
cases.append(('--no-guard on a pool name',) + rc(make('noguard', ['VMR-Coronary__0001']), '--no-guard'))
cases.append(('annotator benchmark',) + rc(make('bench', [one, 'annotator_benchmark_0001'])))
ok = True
for name, c, msg in cases:
    good = c == 3 and (name != 'sealed volume beside a stand-in' or msg.startswith('opened 0'))
    ok &= good
    print('PASS' if good else 'FAIL', name, 'exit', c, '|', msg)
print('ALL PASS' if ok else 'SOME FAILED')
sys.exit(0 if ok else 1)
