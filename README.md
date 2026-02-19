# TG Auth

```bash
make develop

cp .env.dev .env
# setup APP_BOT_TOKEN and APP_SECRET_KEY
source .venv/bin/activate

uvicorn tg_auth.__main__:app --port 8080 --log-level debug

# in other terminal
ngrok http 8080
```
