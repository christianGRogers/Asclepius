#!/usr/bin/env python3
"""Job M0, step 1 (Fir login node): the fetch list for trillium/totalseg/lib/fetch.py.

Reads ../allowed_volumes.json (Kilo's Janus-M allowed list: no sealed, reserve or D35-draw patient),
re-checks every name against the project's seal guard, and adds each item's byte size from Girder
(read-only GET item/<id>). Writes OUT (a list of {name, item_id, size}).

    python3 m0_inputs.py OUT.json
Standard library only. Authenticates like fetch.py (GIRDER_TOKEN, or GIRDER_USER/GIRDER_PASSWORD, or prompts).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src')); sys.path.insert(0, os.path.join(REPO, 'trillium', 'totalseg', 'lib'))
from segtrain.pool_seal import load_pool_seal  # noqa: E402
import fetch  # noqa: E402


def main(out):
    allowed = json.load(open(os.path.join(HERE, '..', 'allowed_volumes.json')))
    guard = load_pool_seal()
    vols = allowed['volumes']
    bad = [v['name'] for v in vols if guard.is_sealed(v['name'])]
    if bad:
        sys.exit(f'refusing: {len(bad)} sealed names in the allowed list, e.g. {bad[:3]}')
    known = {i['name']: i['size'] for i in json.load(open(os.path.join(REPO, 'trillium', 'totalseg', 'inputs.json')))}
    token = None
    items = []
    for v in vols:
        size = known.get(v['name'])
        if size is None:
            token = token or fetch.login()
            size = fetch.call(f"item/{v['item_id']}", token=token)['size']
        items.append({'name': v['name'], 'item_id': v['item_id'], 'size': size})
    json.dump(items, open(out, 'w'), indent=1)
    print(f'[m0] {len(items)} volumes, {sum(i["size"] for i in items) / 1e9:.1f} GB, sealed 0 -> {out}')


if __name__ == '__main__':
    main(sys.argv[1])
