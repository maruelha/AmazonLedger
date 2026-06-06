"""
Convert HTML clipboard content to the markdown-link text the parser expects.
Each <a href="URL">TEXT</a> becomes [TEXT](URL); block-level elements produce
newlines so the line structure the parser relies on is preserved.
"""
from html.parser import HTMLParser
import re

_BLOCK_TAGS = frozenset([
    'div', 'p', 'br', 'hr', 'tr', 'li', 'ul', 'ol',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'section', 'article', 'header', 'footer', 'main',
    'table', 'tbody', 'thead', 'tfoot',
])


class _Converter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._out = []
        self._cur_href = None
        self._cur_atext = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == 'a':
            self._cur_href = dict(attrs).get('href', '')
            self._cur_atext = []
        elif t in _BLOCK_TAGS:
            self._out.append('\n')

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == 'a' and self._cur_href is not None:
            text = ''.join(self._cur_atext).strip()
            if text and self._cur_href:
                self._out.append(f'[{text}]({self._cur_href})')
            elif text:
                self._out.append(text)
            self._cur_href = None
            self._cur_atext = []
        elif t in _BLOCK_TAGS:
            self._out.append('\n')

    def handle_data(self, data):
        if self._cur_href is not None:
            self._cur_atext.append(data)
        else:
            self._out.append(data)

    def result(self):
        raw = ''.join(self._out)
        lines = [l.rstrip() for l in raw.split('\n')]
        out = []
        prev_blank = False
        for l in lines:
            if not l:
                if not prev_blank:
                    out.append('')
                prev_blank = True
            else:
                out.append(l)
                prev_blank = False
        return '\n'.join(out).strip()


def html_to_markdown(html: str) -> str:
    """
    Convert HTML clipboard content to markdown-link format for the parser.
    Each <a href="URL">TEXT</a> → [TEXT](URL).  URLs are preserved verbatim,
    including query strings (shipmentId=…, /dp/ASIN, etc.).
    """
    c = _Converter()
    c.feed(html)
    return c.result()
