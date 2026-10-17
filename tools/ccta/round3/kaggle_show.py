"""Show licence/description and folder summary for Kaggle refs."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kaggle_common as kc
for r in sys.argv[1:]:
    d = kc.view(r)
    print('==', r, '|', d.get('licenseName'), '|', d.get('title'), '|', d.get('subtitle'))
    print('  desc:', (d.get('description') or '').replace('\n', ' ')[:700])
    f = kc.files_retry(r)
    print('  files', len(f), round(sum(f.values()) / 1e9, 2), 'GB;', collections.Counter('/'.join(k.split('/')[:-1]) for k in f).most_common(6))
    for k, v in list(f.items())[:5]:
        print('   ', k, v)
