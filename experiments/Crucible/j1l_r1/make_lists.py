"""Crucible, Janus 1-L Round 1: the case lists Job 0 and the gate use (ids only; no image or label is opened).

locked100 = Janus 0's val 80 (ImageCAS-X filelist/val.txt, id n -> case c{n-1:04d}) + the 20 of open-36 with the
smallest sha256('asclepius-janus1-locked100:' + id) (D45). tuning60 = the 44 dev cases + the other 16 of open-36:
D45 sends them to training, and Janus 0 never trained on them. train620 = ImageCAS-X train 560 + tuning60.
Usage: python3 make_lists.py <ImageCAS-X filelist dir> > lists.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from locked100_power import locked, REPO  # noqa: E402

fl = sys.argv[1]
ids = lambda n: sorted('c%04d' % (int(x) - 1) for x in open(os.path.join(fl, n + '.txt')).read().split())
S = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
L = locked()
val80, train560, dev44 = ids('val'), ids('train'), sorted(S['excluded_dev_cases_in_test'])
locked100 = sorted(val80 + L['locked20'])
tuning60 = sorted(dev44 + L['train16'])
train620 = sorted(train560 + tuning60)
assert len(val80) == 80 and len(train560) == 560 and len(dev44) == 44
assert len(locked100) == 100 and len(tuning60) == 60 and len(train620) == 620
assert not set(locked100) & set(train620) and not (set(locked100) | set(train620)) & sealed
print(json.dumps(dict(rule='D45; ids as in vault/Plans/Sealed test.md and ImageCAS-X filelist',
                      locked100=locked100, locked20_of_open36=L['locked20'], tuning60=tuning60,
                      train620=train620, job0=sorted(locked100 + tuning60)), indent=1))
