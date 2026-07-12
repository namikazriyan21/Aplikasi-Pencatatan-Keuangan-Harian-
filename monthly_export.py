import os
import csv
import calendar
import argparse
import threading
import time
from datetime import date, timedelta
from database import db, Transaksi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

def export_monthly_report(year: int, month: int):
    """Exports transactions for the specified year and month to a CSV file."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Calculate start and end dates for the given month
    num_days = calendar.monthrange(year, month)[1]
    start_date = f"{year:04d}-{month:02d}-01"
    end_date = f"{year:04d}-{month:02d}-{num_days:02d}"
    
    csv_filename = f"laporan_bulanan_{year:04d}_{month:02d}.csv"
    csv_path = os.path.join(REPORTS_DIR, csv_filename)
    
    try:
        rows = Transaksi.query.filter(
            Transaksi.tanggal >= start_date,
            Transaksi.tanggal <= end_date
        ).order_by(Transaksi.tanggal.asc(), Transaksi.id.asc()).all()
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write Header
            writer.writerow(['ID', 'Tanggal', 'Tipe', 'Kategori', 'Nama Barang', 'Nominal'])
            # Write Data
            for row in rows:
                writer.writerow([
                    row.id, 
                    row.tanggal, 
                    row.tipe, 
                    row.kategori, 
                    row.nama_barang, 
                    row.nominal
                ])
        print(f"[Exporter] Report generated: {csv_path} ({len(rows)} transactions)")
        return csv_path, len(rows)
    except Exception as e:
        print(f"[Exporter] Error generating report for {year}-{month:02d}: {e}")
        raise e

def check_and_generate_previous_month():
    """Checks if report for previous month exists, if not generates it."""
    today = date.today()
    # First day of this month minus 1 day is last day of previous month
    first_of_this_month = today.replace(day=1)
    last_day_of_prev_month = first_of_this_month - timedelta(days=1)
    
    prev_month = last_day_of_prev_month.month
    prev_year = last_day_of_prev_month.year
    
    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_filename = f"laporan_bulanan_{prev_year:04d}_{prev_month:02d}.csv"
    csv_path = os.path.join(REPORTS_DIR, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"[Scheduler] Laporan bulanan {prev_year:04d}_{prev_month:02d}.csv tidak ditemukan. Membuat laporan otomatis...")
        export_monthly_report(prev_year, prev_month)
    else:
        print(f"[Scheduler] Laporan bulanan untuk {prev_year:04d}_{prev_month:02d} sudah tersedia.")

def run_scheduler_loop(app):
    """Background task loop that checks monthly reports."""
    # Wait a few seconds to let Flask main threads start up properly
    time.sleep(5)
    while True:
        try:
            with app.app_context():
                check_and_generate_previous_month()
        except Exception as e:
            print(f"[Scheduler] Error in scheduler loop: {e}")
        # Sleep for 12 hours (43200 seconds) before checking again
        time.sleep(12 * 3600)

def start_scheduler(app):
    """Starts the background scheduler thread."""
    # Prevent duplicate thread launch in Flask debug reloader
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        t = threading.Thread(target=run_scheduler_loop, args=(app,), daemon=True)
        t.start()
        print("[Scheduler] Monthly report scheduler thread started.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ekspor Laporan Transaksi Bulanan Kasir Warung ke CSV")
    parser.add_argument('--year', type=int, help="Tahun laporan (contoh: 2026)")
    parser.add_argument('--month', type=int, help="Bulan laporan (contoh: 7)")
    args = parser.parse_args()
    
    # To run standalone, we need an app context
    from app import app as flask_app
    
    with flask_app.app_context():
        if args.year is not None and args.month is not None:
            if not (1 <= args.month <= 12):
                print("Error: Bulan harus bernilai antara 1 sampai 12.")
                exit(1)
            print(f"Menjalankan ekspor data untuk bulan {args.year}-{args.month:02d}...")
            export_monthly_report(args.year, args.month)
        else:
            # Default to previous month
            today = date.today()
            first_of_this_month = today.replace(day=1)
            last_day_of_prev_month = first_of_this_month - timedelta(days=1)
            prev_month = last_day_of_prev_month.month
            prev_year = last_day_of_prev_month.year
            print(f"Menjalankan ekspor data bulan lalu ({prev_year}-{prev_month:02d}) secara default...")
            export_monthly_report(prev_year, prev_month)
