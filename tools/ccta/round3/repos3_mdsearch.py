"""Repos3: Mendeley Data search pages for one query (all pages up to N) -> lines id|source|title."""
import re, sys, time, urllib.parse, urllib.request, html as H
q = sys.argv[1]; maxp = int(sys.argv[2]) if len(sys.argv) > 2 else 30
for page in range(1, maxp + 1):
    url = 'https://data.mendeley.com/research-data/?' + urllib.parse.urlencode({'query': q, 'page': page})
    s = None
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120) as r:
                s = r.read().decode('utf8', 'replace'); break
        except Exception:
            time.sleep(8 * (a + 1))
    if not s: break
    items = re.findall(r'<li class="datasearch-item">(.*?)</li>', s, re.S)
    if page == 1:
        print('#', re.findall(r'([0-9,]+) results', s)[:1])
    for it in items:
        m = re.search(r'href="([^"]+)">(.*?)</a>', it, re.S); src = re.search(r'class="source">(.*?)</span>', it, re.S)
        c = re.search(r'class="metadata contributors">(.*?)</div>', it, re.S)
        if m: print(m.group(1).replace('https://data.mendeley.com/datasets/', 'md:'), '|', src and src.group(1), '|', H.unescape(re.sub('<[^>]+>', '', m.group(2)))[:110], '|', c and H.unescape(re.sub('<[^>]+>', '', c.group(1)))[:60])
    if len(items) < 10: break
    time.sleep(1)
