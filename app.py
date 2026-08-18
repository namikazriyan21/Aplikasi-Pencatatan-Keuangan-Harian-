import secrets
import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()
from database import db, seed_data
from auth import login, logout
from routes import dashboard, input_transaksi, hapus_transaksi, export_csv, cetak_laporan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))

db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/warung_db')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Pastikan tabel dan data awal dibuat saat aplikasi dijalankan oleh Gunicorn
with app.app_context():
    try:
        db.create_all()
        seed_data()
    except Exception as e:
        print(f"Warning: Database initialization error: {e}")

# ── Daftarkan semua route ─────────────────────────────────────────────────────
app.add_url_rule('/login',          'login',           login,           methods=['GET','POST'])
app.add_url_rule('/logout',         'logout',          logout,          methods=['POST'])
app.add_url_rule('/',               'dashboard',       dashboard)
app.add_url_rule('/input',          'input_transaksi', input_transaksi, methods=['GET','POST'])
app.add_url_rule('/hapus/<int:id>', 'hapus_transaksi', hapus_transaksi, methods=['POST'])
app.add_url_rule('/export-csv',     'export_csv',      export_csv)
app.add_url_rule('/cetak_laporan',  'cetak_laporan',   cetak_laporan)

# ── Jalankan aplikasi (Hanya untuk lokal) ─────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
