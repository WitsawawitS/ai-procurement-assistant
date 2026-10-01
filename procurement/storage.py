"""Explicitly saved, local SQLite snapshots. Parameterized queries only."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL, sha256 TEXT NOT NULL, payload TEXT NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save(self, title, payload):
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        with self.connect() as db:
            cur = db.execute('INSERT INTO analyses(title,created_at,sha256,payload) VALUES (?,?,?,?)',
                (title, datetime.now(timezone.utc).isoformat(), digest, encoded))
            return {'id': cur.lastrowid, 'sha256': digest}

    def list(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute('SELECT id,title,created_at,sha256 FROM analyses ORDER BY id DESC LIMIT 100')]

    def get(self, ident):
        with self.connect() as db:
            row = db.execute('SELECT payload,sha256 FROM analyses WHERE id=?',(ident,)).fetchone()
        if not row:
            return None
        if hashlib.sha256(row[0].encode()).hexdigest() != row[1]:
            raise ValueError('Snapshot integrity check failed.')
        return json.loads(row[0])
