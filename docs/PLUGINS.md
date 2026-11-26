# Плагины Cinema — протокол для разработчиков

Плагин — это **отдельная программа со своим HTTP-сервером**, которую пользователь ставит сам:
программа на ПК, контейнер на NAS, сервис в интернете или **отдельный APK на Android TV**.
Cinema подключается к серверу по адресу и показывает то, что он отдаёт.

Cinema **не скачивает и не запускает код плагина**. Что плагин показывает и откуда берёт —
ответственность его автора и того, кто его поставил.

- Протокол: **версия 1**, обмен JSON в UTF-8.
- Подключение: «Настройки → Плагины» → адрес сервера (`http://127.0.0.1:48100`,
  `http://192.168.0.20:48100`, `https://plugins.example.org/films`) **или** прямая ссылка
  на `manifest.json` (например, raw-файл на GitHub) → «Найти» → «Подключить».
  Разрешены любые адреса `http://` и `https://`.
- Пример плагина на Python (только стандартная библиотека): [`examples/plugin-example/server.py`](../examples/plugin-example/server.py).

## Возможности

| `capabilities` | Что даёт | Статус |
|---|---|---|
| `streams` | Источники видео: поиск по фильму/серии и поток для плеера Cinema | ✅ поддерживается |
| `catalogs`, `subtitles`, `meta`, `theme` | Подборки, субтитры, описания, тема | зарезервировано, в следующих версиях протокола |

Cinema показывает список возможностей при подключении. Неизвестные значения игнорируются.

## Манифест

`GET {server}/cinema/manifest` — или файл по прямой ссылке (тогда поле `server` обязательно).

```json
{
  "protocol": 1,
  "id": "org.example.films",
  "name": "Мой плагин",
  "version": "1.2.0",
  "author": "Иван Петров",
  "description": "Что умеет плагин — коротко.",
  "server": "http://127.0.0.1:48100",
  "capabilities": ["streams"]
}
```

| Поле | | |
|---|---|---|
| `protocol` | обязательно | Версия протокола. Больше, чем понимает Cinema, — подключение откажется с просьбой обновить Cinema. |
| `id` | обязательно | Постоянный уникальный идентификатор (обратный домен). По нему Cinema узнаёт плагин при обновлении. |
| `name` | обязательно | Название для пользователя. |
| `version`, `author`, `description` | по желанию | Показываются в настройках. |
| `server` | если манифест по прямой ссылке | Адрес сервера плагина, `http(s)://…` без `/` в конце. Если манифест отдаёт сам сервер — можно не указывать. |
| `capabilities` | обязательно | См. таблицу выше. |

«Обновить» в настройках заново читает манифест по той же ссылке.

## Источники видео (`streams`)

### Поиск

`POST {server}/cinema/streams/search`

Cinema спрашивает все включённые плагины одновременно, на каждый — до 35 секунд.

```json
{
  "tmdb_id": 603,
  "imdb_id": "tt0133093",
  "kinopoisk_id": 301,
  "title": "Матрица",
  "original_title": "The Matrix",
  "year": 1999,
  "serial": false,
  "season": null,
  "episode": null
}
```

Любое поле кроме `title` и `serial` может быть `null`. Для сериала `serial: true`; `season`/`episode` —
серия, которую зритель собирается смотреть (если известна).

Ответ:

```json
{
  "results": [
    {
      "id": "matrix-1999",
      "title": "Матрица (1999)",
      "quality": "1080p",
      "voices": [
        { "id": "dub", "name": "Дубляж" },
        { "id": "orig", "name": "Оригинал" }
      ],
      "seasons": []
    }
  ]
}
```

Для сериала — сезоны и серии:

```json
{
  "results": [
    {
      "id": "show-42",
      "title": "Сериал (2011)",
      "quality": "1080p",
      "voices": [{ "id": "1", "name": "Озвучка студии" }],
      "seasons": [
        { "season": 1, "episodes": [ { "episode": 1, "title": "Пилот" }, { "episode": 2, "title": "" } ] },
        { "season": 2, "episodes": [ { "episode": 1, "title": "" } ] }
      ]
    }
  ]
}
```

| Поле результата | | |
|---|---|---|
| `id` | обязательно | Строка или число — Cinema вернёт его в `resolve`. |
| `title` | по желанию | Название в списке (иначе — название фильма). |
| `quality` | по желанию | Метка в списке, например `1080p`, `4K`. |
| `voices[]` | по желанию | Озвучки `{id, name}`. Если их несколько — зритель выберет. |
| `seasons[]` | для сериалов | `{season, episodes: [{episode, title}]}`. Пусто — это фильм. |

Ничего не нашли — `{"results": []}`.

### Поток

`POST {server}/cinema/streams/resolve`

```json
{ "plugin": "org.example.films", "id": "show-42", "voice": "1", "season": 1, "episode": 2 }
```

`voice`, `season`, `episode` — `null`, если не выбирались (фильм, одна озвучка). Для следующей
серии плеер Cinema сам вызовет `resolve` со следующим `episode`.

Ответ:

```json
{
  "url": "https://cdn.example.org/show/1x02/master.m3u8",
  "hls": true,
  "qualities": [
    { "label": "1080p", "url": "https://cdn.example.org/show/1x02/1080.m3u8" },
    { "label": "720p",  "url": "https://cdn.example.org/show/1x02/720.m3u8" }
  ],
  "subtitles": [
    { "label": "Русские", "lang": "ru", "url": "https://cdn.example.org/show/1x02/ru.vtt" }
  ],
  "headers": {
    "Referer": "https://player.example.org/",
    "Origin": "https://player.example.org",
    "User-Agent": "Mozilla/5.0 …"
  }
}
```

| Поле | | |
|---|---|---|
| `url` | обязательно | Поток: HLS (`.m3u8`) или файл (MP4, MKV…). Может быть относительным — от адреса сервера плагина. |
| `hls` | по желанию | `true` для HLS. Если не указано — по расширению `.m3u8`. |
| `qualities[]` | по желанию | Разрешения `{label, url}`. Если их больше одного — зритель выберет; без них плеер возьмёт качества из master-плейлиста HLS. |
| `subtitles[]` | по желанию | `{label, lang, url}` — WebVTT (`.vtt`) или SRT (`.srt`). |
| `headers` | по желанию | Заголовки для **всех** запросов потока, качеств, субтитров, сегментов и ключей HLS. Разрешены: `Referer`, `Origin`, `User-Agent`, `Cookie`, `Authorization`, `Accept-Language` — остальные отбрасываются. |

Как играется: Cinema не отдаёт ссылки плагина плееру напрямую. Все `url` (поток, качества,
субтитры) превращаются в адреса собственного прокси ядра (`/api/online/stream/…`), который
подставляет `headers` и переписывает HLS-плейлисты — каждый сегмент и ключ тоже идёт через
него с теми же заголовками. Поэтому поток играет любой плеер Cinema: mpv на ПК, ExoPlayer на
Android TV, браузер. Прокси открывает только ссылки, подписанные текущим запуском ядра.

### Ошибки

Любой ответ не `2xx` — ошибка. Текст для пользователя — в поле `error`:

```json
{ "error": "Фильм не найден" }
```

Cinema покажет его как «Название плагина: текст».

## Плагин на Android TV (отдельный APK)

Cinema сама находит плагины-APK на устройстве («Настройки → Плагины → Найдены на этом
устройстве») и **будит их сервис**, когда нужен поиск, — открывать второе приложение руками не нужно.

В `AndroidManifest.xml` плагина:

```xml
<uses-permission android:name="android.permission.INTERNET" />

<application android:usesCleartextTraffic="true" …>
    <service
        android:name=".CinemaPluginService"
        android:exported="true">
        <intent-filter>
            <action android:name="app.cinema.PLUGIN" />
        </intent-filter>
        <!-- Адрес, на котором сервис поднимает свой HTTP-сервер. -->
        <meta-data
            android:name="app.cinema.plugin.url"
            android:value="http://127.0.0.1:48100" />
    </service>
</application>
```

- Cinema подключается к сервису через `bindService(…, BIND_AUTO_CREATE)` и держит связь, пока
  работает, — система не выгружает сервер плагина. В `onBind` верните любой `IBinder`
  (достаточно `Binder()`), а HTTP-сервер запускайте в `onCreate` и останавливайте в `onDestroy`.
- Слушайте `127.0.0.1` — тогда сервер виден только приложениям на этом устройстве.
- Сервер должен начать отвечать в течение ~3 секунд после `onCreate`: первые запросы к
  `127.0.0.1` Cinema повторяет, пока сервис просыпается.
- `usesCleartextTraffic="true"` нужен, если сам плагин ходит в сеть по `http://`. Cinema к
  локальным адресам по `http://` подключается всегда (запросы идут из её ядра).

Минимальный сервис на Kotlin:

```kotlin
class CinemaPluginService : Service() {
    private var server: MyHttpServer? = null          // любой встраиваемый сервер: NanoHTTPD, Ktor…

    override fun onCreate() {
        super.onCreate()
        server = MyHttpServer("127.0.0.1", 48100).also { it.start() }
    }

    override fun onBind(intent: Intent): IBinder = Binder()

    override fun onDestroy() {
        server?.stop()
        super.onDestroy()
    }
}
```

## Проверка своего плагина

1. Запустите пример: `python examples/plugin-example/server.py` (или свой сервер).
2. Проверьте манифест: `curl http://127.0.0.1:48100/cinema/manifest`.
3. В Cinema: «Настройки → Плагины» → `http://127.0.0.1:48100` → «Найти» → «Подключить».
4. Откройте любой фильм → кнопка «Плагины» → результат → озвучка → (серия) → качество.

Можно и без интерфейса — через API ядра Cinema (`http://127.0.0.1:47800`):

```bash
curl -X POST http://127.0.0.1:47800/api/plugins/inspect -H "content-type: application/json" -d "{\"url\":\"http://127.0.0.1:48100\"}"
```
