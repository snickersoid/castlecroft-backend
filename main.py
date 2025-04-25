from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from datetime import datetime

# Инициализация SQLite-базы
conn = sqlite3.connect("referrals.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    wallet_address TEXT UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    referrer_address TEXT,
    created_at TEXT
)
""")
conn.commit()

app = FastAPI()

class RegisterPayload(BaseModel):
    address: str
    username: str | None = None
    first_name: str
    last_name: str | None = None
    referrer: str | None = None

@app.post("/register")
def register(user: RegisterPayload):
    """
    Регистрирует пользователя в базе.
    Если уже есть запись с таким address, то INSERT IGNORE пропустит её.
    """
    try:
        now = datetime.utcnow().isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO users "
            "(wallet_address, username, first_name, last_name, referrer_address, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user.address, user.username, user.first_name, user.last_name, user.referrer, now)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}

@app.get("/referrals/{address}")
def get_referrals(address: str):
    """
    Возвращает JSON вида:
      {
        "count": <общее количество приглашённых>,
        "recent": [
          {"display": "<имя или username>", "when": "<ISO-timestamp>"},
          ...
        ]
      }
    """
    # Считаем общее число приглашённых
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_address = ?", (address,))
    count = cursor.fetchone()[0]

    # Берём последние 10 приглашённых
    cursor.execute("""
      SELECT username, first_name, last_name, created_at
      FROM users
      WHERE referrer_address = ?
      ORDER BY created_at DESC
      LIMIT 10
    """, (address,))
    rows = cursor.fetchall()

    # Формируем список с display-именем
    data = []
    for username, first_name, last_name, created_at in rows:
        display = username if username else f"{first_name} {last_name or ''}".strip()
        data.append({"display": display, "when": created_at})

    return {"count": count, "recent": data}
