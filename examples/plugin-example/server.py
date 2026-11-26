"""Минимальный плагин Cinema — пример для разработчиков (протокол: docs/PLUGINS.md).

Запуск:  python server.py [порт]      (по умолчанию 48100)
Подключение в Cinema:  «Настройки → Плагины» → http://127.0.0.1:48100 → «Найти» → «Подключить».

Отдаёт открытый тестовый фильм Big Buck Bunny (HLS, разные качества) для любого запроса и
субтитры, которые сервер отдаёт только с правильным Referer, — так видно, что Cinema
подставляет заголовки, которые попросил плагин. Только стандартная библиотека Python.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 48100
BASE = f'http://127.0.0.1:{PORT}'
REFERER = 'https://plugin-example.local/'

MANIFEST = {
    'protocol': 1,
    'id': 'org.example.cinema-plugin',
    'name': 'Пример плагина',
    'version': '1.0.0',
    'author': 'Cinema',
    'description': 'Открытый тестовый фильм Big Buck Bunny — проверка протокола плагинов.',
    'capabilities': ['streams'],
}

SUBS = 'WEBVTT\n\n00:00:01.000 --> 00:00:06.000\nСубтитры пришли с правильным Referer.\n'


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write('[plugin] ' + fmt % args + '\n')

    def send_json(self, code, body):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return json.loads(self.rfile.read(n) or b'{}')

    def do_GET(self):
        if self.path == '/cinema/manifest':
            return self.send_json(200, MANIFEST)
        if self.path == '/media/subs.vtt':
            if self.headers.get('Referer') != REFERER:
                return self.send_json(403, {'error': 'нужен Referer'})
            data = SUBS.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/vtt; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        return self.send_json(404, {'error': 'нет такого адреса'})

    def do_POST(self):
        q = self.body()
        if self.path == '/cinema/streams/search':
            serial = bool(q.get('serial'))
            result = {
                'id': 'bbb',
                'title': f"{q.get('title') or 'Фильм'} — Big Buck Bunny (пример)",
                'quality': '1080p',
                'voices': [{'id': 'orig', 'name': 'Оригинал'}, {'id': 'demo', 'name': 'Пример озвучки'}],
                'seasons': [{'season': 1, 'episodes': [{'episode': 1, 'title': 'Первая'}, {'episode': 2, 'title': 'Вторая'}]}] if serial else [],
            }
            return self.send_json(200, {'results': [result]})
        if self.path == '/cinema/streams/resolve':
            if q.get('id') != 'bbb':
                return self.send_json(404, {'error': 'нет такого результата'})
            hls = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'
            return self.send_json(200, {
                'url': hls,
                'hls': True,
                'qualities': [{'label': 'Авто', 'url': hls}],
                'subtitles': [{'label': 'Русские', 'lang': 'ru', 'url': '/media/subs.vtt'}],
                'headers': {'Referer': REFERER, 'User-Agent': 'CinemaPluginExample/1.0'},
            })
        return self.send_json(404, {'error': 'нет такого адреса'})


if __name__ == '__main__':
    print(f'Плагин-пример: {BASE}  (Ctrl+C — выход)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
