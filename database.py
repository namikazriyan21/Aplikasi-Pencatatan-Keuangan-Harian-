from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta, timezone
import hashlib
import secrets
import os

db = SQLAlchemy()

WIB = timezone(timedelta(hours=7))

def get_today() -> date:
    return datetime.now(WIB).date()

# ── Password (PBKDF2-SHA256, 260k iterasi) ────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260_000)
    return f"{salt}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split('$', 1)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(WIB))

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tanggal = db.Column(db.Date, nullable=False)
    tipe = db.Column(db.String(50), nullable=False)
    kategori = db.Column(db.String(100), nullable=False)
    nama_barang = db.Column(db.String(255), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ── Data awal ─────────────────────────────────────────────────────────────────

def seed_data():
    if not User.query.first():
        admin = User(username='admin', password=hash_password('admin123'))
        db.session.add(admin)
        db.session.commit()
