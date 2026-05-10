# TG Auth

Минимальный пример авторизации через Telegram **OpenID Connect** (новый
`telegram-login.js` от `oauth.telegram.org`) на `Litestar`.

Проект показывает полный цикл:
- клиент рендерит OIDC-кнопку из `https://oauth.telegram.org/js/telegram-login.js`;
- виджет открывает попап Telegram, пользователь подтверждает вход;
- виджет возвращает на фронт `id_token` (подписанный JWT);
- фронт шлёт `{id_token}` на `POST /api/v1/auth/telegram`;
- backend валидирует подпись JWT по JWKS Telegram (`iss`, `aud`, `exp`, `iat`);
- при успехе сохраняет пользователя в in-memory хранилище и пишет `session` cookie;
- клиент переходит на `/app`, где читаются данные из сессии.

> Это **OIDC-вариант** через JS-библиотеку Telegram. Server-side flow
> (`/auth` → `code` → `/token`) тут не реализован — токен-обмен происходит
> внутри попапа Telegram, нам отдают уже готовый `id_token`.

## Стек

- Python `>=3.13`
- Litestar
- PyJWT (с `cryptography` для RS256/ES256)
- Jinja2
- Uvicorn

## Структура

- `tg_auth/__main__.py`:
  основной backend, роуты, валидация Telegram `id_token` (JWT) по JWKS,
  cookie session.
- `index.html`:
  Telegram OIDC widget (`telegram-login.js`) + JS callback `onTelegramAuth`.

## Эндпоинты

- `GET /`
  - если в сессии есть `user`, делает redirect на `/app`;
  - иначе отдает `index.html`.
- `POST /api/v1/auth/telegram`
  - принимает `{id_token}` от виджета;
  - валидирует JWT по JWKS Telegram (`https://oauth.telegram.org/.well-known/jwks.json`);
  - проверяет `iss == https://oauth.telegram.org`, `aud == APP_TG_CLIENT_ID`, `exp`;
  - создает внутреннего пользователя и сохраняет его в `telegram_users`;
  - пишет `request.session["user"]`.
- `GET /app`
  - достает `user` из сессии;
  - возвращает профиль из `telegram_users`.

## Переменные окружения

Нужны две обязательные переменные:

- `APP_TG_CLIENT_ID`:
  Client ID, выданный BotFather (см. ниже). У текущего бота это `8506301481`.
  В JWT он лежит как claim `aud`.
- `APP_SECRET_KEY`:
  секрет для подписи cookie-сессии Litestar.

Пример:

```bash
export APP_TG_CLIENT_ID="8506301481"
export APP_SECRET_KEY="change-me-to-a-long-random-string"
```

> `Client Secret` от BotFather в этом flow **не нужен** — он используется
> только при server-side обмене `code` → `id_token` на `/token`. JS-виджет
> делает этот обмен сам.

## Локальный запуск

```bash
make develop

cp .env.dev .env
# заполнить APP_TG_CLIENT_ID и APP_SECRET_KEY

source .venv/bin/activate
uvicorn tg_auth.__main__:app --port 8080 --log-level debug
```

В отдельном терминале:

```bash
ngrok http 8080
```

Используй HTTPS URL от `ngrok`, например
`https://<your-subdomain>.ngrok-free.app`. Telegram требует именно HTTPS-origin
для OIDC-виджета.

## Настройка Telegram (обязательно)

1. Открой mini-app [@BotFather](https://t.me/botfather?startapp) →
   `Bot Settings` → `Web Login`.
2. Добавь **Allowed URLs**: origin страницы, например
   `https://<your-subdomain>.ngrok-free.app`. Этого достаточно для
   JS-виджета — redirect внутри попапа держит сам Telegram. (Если позже
   добавишь server-side flow — туда же надо добавить точный callback URL.)
3. BotFather покажет `Client ID` и `Client Secret`. Сохрани `Client ID` —
   именно его прокидываем в `APP_TG_CLIENT_ID` и в `data-client-id` виджета
   (в `index.html` он уже подставлен — `8506301481`).

> Старая команда `/setdomain` относится к легаси-виджету и здесь не
> используется.

## Как выглядит успешный flow

1. Пользователь открывает `GET /`.
2. Виджет `telegram-login.js` рендерит кнопку.
3. По клику открывается попап Telegram, пользователь подтверждает вход.
4. Попап вызывает `onTelegramAuth({id_token, user, error})` через
   `postMessage`.
5. Фронт делает `POST /api/v1/auth/telegram` с `id_token`.
6. Backend валидирует JWT (подпись + claims), пишет cookie `session`,
   отвечает `200`.
7. Фронт делает `window.location.href = "/app"`.
8. `GET /app` возвращает объект пользователя.

## Частые проблемы

- Попап Telegram открылся, но `onTelegramAuth` не вызван:
  origin не зарегистрирован в `BotFather → Web Login`, либо на сервере стоит
  заголовок `Cross-Origin-Opener-Policy: same-origin`. Уберите его или
  смягчите до `same-origin-allow-popups`.

- `401 Invalid id_token: Audience doesn't match`:
  `APP_TG_CLIENT_ID` не совпадает с `data-client-id` в `index.html`.

- `401 Invalid id_token: Signature verification failed`:
  кэш JWKS устарел или ключ ротировался — рестарт процесса либо подождать
  до следующего `lifespan` (10 минут).

- `GET /app` иногда `null`:
  `telegram_users` хранится в памяти процесса. После рестарта запись
  пропадает, но cookie в браузере остается.

## Ограничения текущего примера

- Нет постоянного хранилища пользователей (БД/Redis).
- Нет logout/очистки сессии.
- Нет server-side OIDC flow (`/auth` → `code` → `/token`) — только
  клиентский через JS-виджет.

Для production рекомендуется:
- вынести пользователей в БД и матчить по `sub`/`id` из claims;
- добавить отдельный endpoint logout;
- рассмотреть server-side flow с PKCE, если нужен полноценный backend-only
  обмен без зависимости от JS-попапа.
