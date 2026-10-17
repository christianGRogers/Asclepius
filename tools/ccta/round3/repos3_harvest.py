"""Repos3 (round 3): harvest search hits from Zenodo, Figshare, Dryad and DataCite (Mendeley/figshare+/
institutional figshare prefixes) for many cardiac-CT query variants, with full pagination. Writes JSONL of
unique records to <out>/<repo>.jsonl (id, title, desc, license, access, files, creators, related ids)."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error

OUT = sys.argv[1]
WHICH = sys.argv[2].split(',') if len(sys.argv) > 2 else ['zenodo', 'figshare', 'dryad', 'datacite']
UA = {'User-Agent': 'curl/8.5.0', 'Accept': 'application/json'}

TERMS = [
 'coronary CT angiography', 'CCTA', 'coronary computed tomography', 'cardiac CT', 'cardiac computed tomography',
 'coronary CTA', 'cardiac CTA', 'heart CT', 'CT angiography heart', 'CTCA', 'coronary artery CT',
 'TAVI CT', 'TAVR CT', 'transcatheter aortic valve CT', 'aortic root CT', 'aortic valve CT', 'aortic annulus CT',
 'left atrial appendage CT', 'LAAO CT', 'left atrial appendage occlusion', 'PFO', 'patent foramen ovale CT',
 'atrial fibrillation ablation CT', 'pulmonary vein CT', 'left atrium CT', 'catheter ablation CT',
 'PCI coronary CT', 'CABG CT', 'coronary bypass graft CT', 'FFR-CT', 'FFRCT', 'CT-FFR', 'fractional flow reserve CT',
 'coronary CFD', 'computational fluid dynamics coronary', 'patient-specific coronary', 'coronary hemodynamics',
 '4D CT heart', '4D flow CT', 'dynamic CT heart', 'cine CT', 'myocardial perfusion CT', 'CT perfusion myocardium',
 '3D printing heart', '3D printed heart CT', 'surgical planning heart CT', 'congenital heart disease CT',
 'coronary plaque CT', 'coronary stenosis CT', 'coronary calcium contrast', 'epicardial fat CT', 'pericardial fat',
 'whole heart segmentation CT', 'heart segmentation CT', 'cardiac segmentation CT', 'coronary segmentation',
 'coronary centerline', 'coronary artery segmentation', 'left ventricle CT', 'myocardium CT', 'mitral valve CT',
 'tricuspid CT', 'cardiac chambers CT', 'aortic stenosis CT', 'bicuspid aortic valve', 'hypertrophic cardiomyopathy CT',
 'coronary anomaly', 'anomalous coronary', 'coronary aneurysm', 'Kawasaki CT', 'myocardial bridge', 'coronary fistula',
 'dual-source CT heart', 'photon-counting CT heart', 'photon counting coronary', 'spectral CT cardiac',
 'dual energy cardiac CT', 'SOMATOM Force cardiac', 'Revolution CT cardiac', 'Aquilion ONE heart', 'iCT 256',
 'ECG-gated CT', 'ECG gated', 'retrospective gating CT', 'prospective gating coronary',
 'cardiac DICOM', 'coronary DICOM', 'heart DICOM', 'cardiac NIfTI', 'heart nrrd', 'cardiac CT nii',
 'coronary artery disease imaging', 'CAD CT dataset', 'chest pain CT', 'cardiac imaging dataset',
 'cardiovascular CT', 'Tomografía coronaria', 'angiotomografía coronaria', 'Herz-CT', 'scanner cardiaque',
 'coroscanner', 'cardiac CT radiomics', 'pericoronary adipose', 'fat attenuation index', 'aortic dissection heart CT',
 'ventricular tachycardia CT', 'cardiac radioablation', 'STAR radioablation', 'cardiac resynchronization CT',
 'left ventricular thrombus CT', 'cardiac tumor CT', 'cardiac mass CT', 'pulmonary artery CTA heart',
 'cardiac digital twin', 'heart digital twin CT', 'cardiac mesh CT', 'biventricular model CT', 'four-chamber heart model',
 'statistical shape model heart', 'aortic valve calcification', 'valve calcium CT', 'coronary lumen', 'vessel wall CT',
 'stent CT coronary', 'in-stent', 'coronary artery bypass', 'deep learning coronary CT', 'cardiac CT deep learning',
 'CT angiography dataset', 'CTA dataset', 'contrast-enhanced CT heart', 'contrast enhanced cardiac',
]

def get(url, data=None, tries=6):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=dict(UA, **({'Content-Type': 'application/json'} if data else {})))
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(10 * (a + 1)); continue
            if e.code in (400, 422):
                return None
            raise
        except Exception:
            time.sleep(5 * (a + 1))
    return None

def save(repo, recs, seen):
    with open(os.path.join(OUT, repo + '.jsonl'), 'a') as f:
        for r in recs:
            if r['id'] not in seen:
                seen.add(r['id']); f.write(json.dumps(r) + '\n')

def load_seen(repo):
    p = os.path.join(OUT, repo + '.jsonl'); s = set()
    if os.path.exists(p):
        for l in open(p):
            s.add(json.loads(l)['id'])
    return s

def zenodo():
    seen = load_seen('zenodo'); done = os.path.join(OUT, 'zenodo2.done'); dq = set(open(done).read().split('\n')) if os.path.exists(done) else set()
    for t in TERMS:
        for mode in ('title', 'all'):
            key = mode + ':' + t
            if key in dq: continue
            q = ('title:(' + ' AND '.join(t.split()) + ')' if mode == 'title' else f'"{t}"')
            for page in range(1, 401):
                d = get('https://zenodo.org/api/records?' + urllib.parse.urlencode({'q': q, 'size': 25, 'page': page}))
                time.sleep(0.7)
                if not d or not d.get('hits', {}).get('hits'): break
                recs = []
                for h in d['hits']['hits']:
                    m = h['metadata']
                    recs.append({'id': str(h['id']), 'title': m.get('title'), 'desc': (m.get('description') or '')[:3000],
                                 'license': (m.get('license') or {}).get('id'), 'access': m.get('access_right'),
                                 'files': [(f.get('key'), f.get('size')) for f in h.get('files', [])][:200],
                                 'creators': [c.get('name') for c in m.get('creators', [])][:10],
                                 'communities': [c.get('id') for c in m.get('communities', [])],
                                 'related': [r.get('identifier') for r in m.get('related_identifiers', [])][:50],
                                 'keywords': m.get('keywords'), 'rtype': (m.get('resource_type') or {}).get('type'), 'q': key, 'date': m.get('publication_date')})
                save('zenodo', recs, seen)
                if page * 25 >= min(d['hits']['total'], 10000): break
            open(done, 'a').write(key + '\n'); print('zenodo', key, len(seen), flush=True)

def figshare():
    seen = load_seen('figshare'); done = os.path.join(OUT, 'figshare.done'); dq = set(open(done).read().split('\n')) if os.path.exists(done) else set()
    for t in TERMS:
        if t in dq: continue
        for page in range(1, 11):
            d = get('https://api.figshare.com/v2/articles/search', json.dumps({'search_for': t, 'page_size': 1000, 'page': page}).encode())
            time.sleep(1)
            if not d: break
            save('figshare', [{'id': str(a['id']), 'title': a.get('title'), 'url': a.get('url_public_html'), 'doi': a.get('doi'),
                               'date': a.get('published_date'), 'type': a.get('defined_type_name'), 'q': t} for a in d], seen)
            if len(d) < 1000: break
        open(done, 'a').write(t + '\n'); print('figshare', t, len(seen), flush=True)

def dryad():
    seen = load_seen('dryad'); done = os.path.join(OUT, 'dryad.done'); dq = set(open(done).read().split('\n')) if os.path.exists(done) else set()
    for t in TERMS:
        if t in dq: continue
        for page in range(1, 30):
            d = get('https://datadryad.org/api/v2/search?' + urllib.parse.urlencode({'q': t, 'per_page': 100, 'page': page}))
            time.sleep(1)
            if not d: break
            ds = d.get('_embedded', {}).get('stash:datasets', [])
            save('dryad', [{'id': x.get('identifier'), 'title': x.get('title'), 'desc': (x.get('abstract') or '')[:2000],
                            'license': x.get('license'), 'size': x.get('storageSize'), 'q': t} for x in ds], seen)
            if len(ds) < 100: break
        open(done, 'a').write(t + '\n'); print('dryad', t, len(seen), flush=True)

def datacite():
    seen = load_seen('datacite'); done = os.path.join(OUT, 'datacite.done'); dq = set(open(done).read().split('\n')) if os.path.exists(done) else set()
    for pref in ('10.17632', '10.25452', '10.6084', '10.5061', '10.5281'):
        for t in TERMS:
            key = pref + ':' + t
            if key in dq: continue
            url = 'https://api.datacite.org/dois?' + urllib.parse.urlencode({'query': f'"{t}"', 'prefix': pref, 'page[size]': 1000,
                     'resource-type-id': 'dataset', 'page[cursor]': 1, 'fields[dois]': 'titles,descriptions,rightsList,url,publisher,creators,relatedIdentifiers,sizes,formats,publicationYear'})
            n = 0
            while url and n < 20:
                d = get(url); n += 1; time.sleep(0.5)
                if not d: break
                recs = []
                for x in d.get('data', []):
                    a = x['attributes']
                    recs.append({'id': x['id'], 'title': (a.get('titles') or [{}])[0].get('title'),
                                 'desc': ' '.join(dd.get('description') or '' for dd in (a.get('descriptions') or []))[:3000],
                                 'license': [r.get('rightsIdentifier') or r.get('rights') for r in a.get('rightsList') or []],
                                 'url': a.get('url'), 'publisher': a.get('publisher'),
                                 'creators': [c.get('name') for c in a.get('creators') or []][:10],
                                 'related': [(r.get('relationType'), r.get('relatedIdentifier')) for r in a.get('relatedIdentifiers') or []][:50],
                                 'sizes': a.get('sizes'), 'year': a.get('publicationYear'), 'q': key})
                save('datacite', recs, seen)
                url = (d.get('links') or {}).get('next')
            open(done, 'a').write(key + '\n'); print('datacite', key, len(seen), flush=True)

def mendeley():
    import re, html as H
    seen = load_seen('mendeley'); done = os.path.join(OUT, 'mendeley.done'); dq = set(open(done).read().split('\n')) if os.path.exists(done) else set()
    for t in TERMS:
        if t in dq: continue
        for page in range(1, 16):
            url = 'https://data.mendeley.com/research-data/?' + urllib.parse.urlencode({'query': t, 'page': page})
            s = None
            for a in range(5):
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
                        s = r.read().decode('utf8', 'replace'); break
                except Exception:
                    time.sleep(10 * (a + 1))
            time.sleep(1)
            if not s: break
            items = re.findall(r'<li class="datasearch-item">(.*?)</li>', s, re.S)
            recs = []
            for it in items:
                m = re.search(r'href="([^"]+)">(.*?)</a>', it, re.S)
                src = re.search(r'class="source">(.*?)</span>', it, re.S)
                de = re.search(r'class="description">(.*?)</div>', it, re.S)
                if m:
                    recs.append({'id': m.group(1), 'title': H.unescape(re.sub('<[^>]+>', '', m.group(2))),
                                 'source': src and H.unescape(src.group(1)), 'desc': de and H.unescape(re.sub('<[^>]+>', '', de.group(1)))[:1500], 'q': t})
            save('mendeley', recs, seen)
            if len(items) < 10: break
        open(done, 'a').write(t + '\n'); print('mendeley', t, len(seen), flush=True)

for w in WHICH:
    globals()[w]()
