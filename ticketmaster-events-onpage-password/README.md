# 공연·콘서트 검색 대시보드 — On-Page Password

This Streamlit app searches live events via **Ticketmaster Discovery API**.
It asks for the **password on the main page** (not sidebar).

## Password behavior
- If `APP_PASSWORD` exists in secrets/env, the entered password **must match**.
- If not set, any non-empty password will unlock (dev convenience).

## Secrets (optional but recommended)
`.streamlit/secrets.toml`:
```toml
APP_PASSWORD = "your_password"
TICKETMASTER_KEY = "your_tm_api_key"
```

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```