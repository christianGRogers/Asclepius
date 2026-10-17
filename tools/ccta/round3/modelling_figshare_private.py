"""Round 3 (agent Modelling): render a figshare private-link page (/s/<key>) past the AWS WAF JS challenge with
headless Chromium and save the HTML (file ids in /ndownloader/files/<id>). Needs: python -m venv v; v/bin/pip install
playwright; v/bin/playwright install chromium-headless-shell; the proxy CA in ~/.pki/nssdb (certutil -A -t C,,).
Usage: v/bin/python modelling_figshare_private.py https://figshare.com/s/<key> out.html"""
import sys, json, re, os
from playwright.sync_api import sync_playwright
url=sys.argv[1]; out=sys.argv[2]
px=os.environ.get('HTTPS_PROXY')
with sync_playwright() as p:
    b=p.chromium.launch(proxy={'server':px} if px else None)
    ctx=b.new_context(ignore_https_errors=False)
    pg=ctx.new_page()
    pg.goto(url, wait_until='networkidle', timeout=90000)
    pg.wait_for_timeout(5000)
    open(out,'w').write(pg.content())
    json.dump(ctx.cookies(), open(out+'.cookies.json','w'))
    print(pg.title())
    b.close()
