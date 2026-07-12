from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import hashlib
import secrets
import os

db = SQLAlchemy()

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tanggal = db.Column(db.Date, nullable=False)
    tipe = db.Column(db.String(50), nullable=False)
    kategori = db.Column(db.String(100), nullable=False)
    nama_barang = db.Column(db.String(255), nullable=False)
    nominal = db.Column(db.Integer, nullable=False)

# ── Data awal ─────────────────────────────────────────────────────────────────

def seed_data():
    if not User.query.first():
        admin = User(username='admin', password=hash_password('admin123'))
        db.session.add(admin)
        db.session.commit()

    if not Transaksi.query.first():
        today = date.today()
        samples = [
            Transaksi(tanggal=today - timedelta(days=6), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Nasi Goreng', nominal=350000),
            Transaksi(tanggal=today - timedelta(days=6), tipe='Keluar', kategori='Stok Bahan',       nama_barang='Beli Beras 10kg',       nominal=130000),
            Transaksi(tanggal=today - timedelta(days=5), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Mie Ayam',    nominal=420000),
            Transaksi(tanggal=today - timedelta(days=5), tipe='Keluar', kategori='Operasional',      nama_barang='Bayar Listrik',         nominal=80000),
            Transaksi(tanggal=today - timedelta(days=4), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Soto Ayam',   nominal=310000),
            Transaksi(tanggal=today - timedelta(days=4), tipe='Keluar', kategori='Stok Bahan',       nama_barang='Beli Ayam 5kg',         nominal=165000),
            Transaksi(tanggal=today - timedelta(days=3), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Bakso',       nominal=480000),
            Transaksi(tanggal=today - timedelta(days=3), tipe='Keluar', kategori='Stok Bahan',       nama_barang='Beli Sayuran Segar',    nominal=55000),
            Transaksi(tanggal=today - timedelta(days=2), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Nasi Gudeg',  nominal=390000),
            Transaksi(tanggal=today - timedelta(days=2), tipe='Keluar', kategori='Operasional',      nama_barang='Beli Gas LPG 3 Tabung', nominal=75000),
            Transaksi(tanggal=today - timedelta(days=1), tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Rawon',       nominal=445000),
            Transaksi(tanggal=today - timedelta(days=1), tipe='Keluar', kategori='Stok Bahan',       nama_barang='Beli Bumbu Dapur',      nominal=95000),
            Transaksi(tanggal=today,                     tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Pagi',        nominal=275000),
            Transaksi(tanggal=today,                     tipe='Masuk',  kategori='Harian Penjualan', nama_barang='Penjualan Siang',       nominal=310000),
            Transaksi(tanggal=today,                     tipe='Keluar', kategori='Stok Bahan',       nama_barang='Beli Tahu & Tempe',     nominal=45000),
            Transaksi(tanggal=today,                     tipe='Keluar', kategori='Operasional',      nama_barang='Bayar Air PDAM',        nominal=35000),
        ]
        db.session.bulk_save_objects(samples)
        db.session.commit()
