"""Offline static checks for the synthetic Phase 2 OpenFilm project."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import wave

ROOT = Path(__file__).resolve().parent

class FilmParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.viewport = None
        self.text = []

    def handle_data(self, data):
        self.text.append(data)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'meta' and attrs.get('name') == 'viewport':
            self.viewport = attrs.get('content')
        if tag in ('iframe', 'audio'):
            self.items.append((tag, attrs))

film = FilmParser()
film.feed((ROOT / 'film.html').read_text(encoding='utf-8'))
assert film.viewport == 'width=1080, height=1920'
shots = [a for tag, a in film.items if tag == 'iframe']
audio = [a for tag, a in film.items if tag == 'audio']
assert len(shots) == 3 and [a.get('at') for a in shots] == ['0', '4', '8']
assert all(a.get('src', '').endswith('#t=0,4') for a in shots)
assert len(audio) == 1 and audio[0].get('src', '').endswith('#t=0,12')
for item in shots + audio:
    url = urlsplit(item['src'])
    assert not url.scheme and not url.netloc
    path = (ROOT / url.path).resolve()
    assert path.is_relative_to(ROOT) and path.is_file(), item['src']
titles = ['我不会编程', '但是我开始用 AI 做 APP', '这是我的第一个作品']
for item, title in zip(shots, titles):
    page = (ROOT / urlsplit(item['src']).path).read_text(encoding='utf-8')
    page_html = FilmParser()
    page_html.feed(page)
    assert ''.join(title.split()) in ''.join(''.join(page_html.text).split())
    assert 'window.film' in page and 'duration' in page and 'frame' in page
with wave.open(str(ROOT / urlsplit(audio[0]['src']).path), 'rb') as sound:
    assert sound.getframerate() == 48000
    assert sound.getnframes() / sound.getframerate() == 12
print('PASS: static timeline, local references, titles and 12-second WAV')
print('NOT_RUN: browser rendering, Studio editing and video export')
