from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlsplit
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import re

PAGES = ['index.html','faq.html','what-we-do.html','who-we-are.html']
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.images=[]; self.styles=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag=='img' and 'src' in a: self.images.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet': self.styles.append(a['href'])

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

server=ThreadingHTTPServer(('127.0.0.1',0),Quiet)
Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
try:
    for page in PAGES:
        path=Path(page); assert path.is_file(),f'Missing {page}'
        with urlopen(f'{origin}/{page}',timeout=10) as r:
            assert r.status==200,(page,r.status)
            document=r.read().decode('utf-8')
        parser=Links(); parser.feed(document)
        assert parser.links,f'No navigation on {page}'
        assert parser.images,f'No image on {page}'
        assert parser.styles,f'No stylesheet on {page}'
        for target in parser.links+parser.images+parser.styles:
            parsed=urlsplit(target)
            if parsed.scheme in ('http','https') or target.startswith(('mailto:','tel:','#')): continue
            local=parsed.path.lstrip('/') or 'index.html'
            if local.endswith('/'): local+='index.html'
            assert Path(local).is_file(),f'Broken reference in {page}: {target}'
            with urlopen(f'{origin}/{local}',timeout=10) as r:
                assert r.status==200,(page,target,r.status)
                body=r.read()
                if target in parser.images:
                    assert len(body)>1000,f'Empty image: {target}'
                    if local.endswith('.png'): assert body.startswith(bytes.fromhex('89504e470d0a1a0a'))
                    if local.endswith(('.jpg','.jpeg')): assert body.startswith(bytes.fromhex('ffd8ff'))
                    if local.endswith('.svg'): assert b'<svg' in body
        assert any('heyday-build-logo.svg' in src for src in parser.images),f'Header logo missing in {page}'
        print(f'PASS {page}: HTTP 200, {len(parser.links)} navigation links, {len(parser.images)} images, stylesheets and assets')
    print('All static deployment smoke tests passed')
finally:
    server.shutdown()
