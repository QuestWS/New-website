"""HTML -> markdown-ish text snapshot (refactored from the original extractor).

Output is byte-identical to the original script for the same HTML input.
"""
import re
from bs4 import BeautifulSoup, NavigableString

BLOCK = {'h1','h2','h3','h4','h5','p','li','div','section','td','tr','br','ul','ol','table','article','blockquote','form'}


def walk(el, out):
    for c in el.children:
        if isinstance(c, NavigableString):
            t = re.sub(r'\s+', ' ', str(c))
            if t.strip():
                out.append(t)
            continue
        n = c.name
        if n == 'img':
            s = c.get('data-src') or c.get('src') or ''
            if s and not s.startswith('data:') and 'mygarage' not in s and 'spin.gif' not in s:
                out.append(f"\n![{c.get('alt','')}]({s})\n")
            continue
        if n == 'iframe':
            out.append(f"\n[IFRAME]({c.get('src') or c.get('data-src')})\n")
            continue
        if n == 'a':
            inner = []
            walk(c, inner)
            txt = ''.join(inner).strip()
            h = c.get('href', '')
            out.append(f"[{txt}]({h})" if txt and h and not h.startswith('#') else txt)
            continue
        if n in ('input', 'select', 'textarea', 'button', 'label') and n != 'label':
            nm = c.get('name') or c.get('placeholder') or ''
            if n == 'select':
                out.append(f"\n[SELECT {nm}: " + ' | '.join(o.get_text(strip=True) for o in c.find_all('option')) + "]\n")
            elif c.get('type') not in ('hidden',):
                out.append(f" [FIELD {n} {c.get('type','')} {nm}] ")
            continue
        pre = {'h1': '\n# ', 'h2': '\n## ', 'h3': '\n### ', 'h4': '\n#### ', 'h5': '\n##### ', 'li': '\n- '}.get(n, '\n' if n in BLOCK else '')
        if n in ('strong', 'b'):
            out.append('**')
        out.append(pre)
        walk(c, out)
        if n in ('strong', 'b'):
            out.append('**')
        if n in BLOCK:
            out.append('\n')


def html_to_md(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(strip=True) if soup.title else ''
    md = soup.find('meta', attrs={'name': 'description'})
    mdc = md.get('content', '') if md else ''
    for t in soup(['script', 'style', 'noscript', 'svg', 'header', 'footer', 'nav', 'link', 'meta']):
        t.decompose()
    for t in soup.select('[class*=mygarage],[id*=mygarage],.modal'):
        t.decompose()
    out = []
    walk(soup.body, out)
    txt = ''.join(out)
    txt = re.sub(r'[ \t]+', ' ', txt)
    txt = re.sub(r'\n\s*\n+', '\n\n', txt)
    txt = txt.split('© 20')[0]
    return f"# TITLE: {title}\nMETA: {mdc}\n\n{txt.strip()}\n"
