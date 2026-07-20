import csv
import io
from flask import render_template, request, redirect, url_for, Response, session
from datetime import date, timedelta
from database import db, Transaksi
from auth import login_required
from sqlalchemy import func


# ── Helper format tanggal Bahasa Indonesia ────────────────────────────────────

_HARI  = {'Monday':'Senin','Tuesday':'Selasa','Wednesday':'Rabu',
           'Thursday':'Kamis','Friday':'Jumat','Saturday':'Sabtu','Sunday':'Minggu'}
_BULAN = {'January':'Januari','February':'Februari','March':'Maret',
           'April':'April','May':'Mei','June':'Juni','July':'Juli',
           'August':'Agustus','September':'September','October':'Oktober',
           'November':'November','December':'Desember'}

def _fmt_tanggal(d: date) -> str:
    return f"{_HARI[d.strftime('%A')]}, {d.strftime('%d')} {_BULAN[d.strftime('%B')]} {d.strftime('%Y')}"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard():
    today = date.today()
    user_id = session.get('user_id')

    # Statistik hari ini
    today_rows = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).filter(Transaksi.tanggal == today, Transaksi.user_id == user_id).group_by(Transaksi.tipe).all()
    total_masuk_hari  = next((r.total for r in today_rows if r.tipe == 'Masuk'),  0) or 0
    total_keluar_hari = next((r.total for r in today_rows if r.tipe == 'Keluar'), 0) or 0
    saldo_hari        = total_masuk_hari - total_keluar_hari

    # Data 7 hari untuk bar chart
    labels, bar_masuk, bar_keluar = [], [], []
    for i in range(6, -1, -1):
        d    = today - timedelta(days=i)
        rows = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).filter(Transaksi.tanggal == d, Transaksi.user_id == user_id).group_by(Transaksi.tipe).all()
        labels.append(d.strftime('%d %b'))
        bar_masuk.append(next((r.total for r in rows if r.tipe == 'Masuk'),  0) or 0)
        bar_keluar.append(next((r.total for r in rows if r.tipe == 'Keluar'), 0) or 0)

    # 10 transaksi terbaru
    riwayat = Transaksi.query.filter_by(user_id=user_id).order_by(Transaksi.tanggal.desc(), Transaksi.id.desc()).limit(10).all()

    # Total keseluruhan
    totals = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).filter(Transaksi.user_id == user_id).group_by(Transaksi.tipe).all()
    total_all_masuk  = next((r.total for r in totals if r.tipe == 'Masuk'),  0) or 0
    total_all_keluar = next((r.total for r in totals if r.tipe == 'Keluar'), 0) or 0
    saldo_total      = total_all_masuk - total_all_keluar

    return render_template('dashboard.html',
        today             = _fmt_tanggal(today),
        total_masuk_hari  = total_masuk_hari,
        total_keluar_hari = total_keluar_hari,
        saldo_hari        = saldo_hari,
        chart_labels      = labels,
        bar_masuk         = bar_masuk,
        bar_keluar        = bar_keluar,
        riwayat           = riwayat,
        saldo_total       = saldo_total,
        total_all_masuk   = total_all_masuk,
        total_all_keluar  = total_all_keluar,
    )


# ── Form Input Transaksi ──────────────────────────────────────────────────────

@login_required
def input_transaksi():
    pesan = None
    if request.method == 'POST':
        tgl_str     = request.form.get('tanggal', '')
        tipe        = request.form.get('tipe', '')
        kategori    = request.form.get('kategori', '')
        nama        = request.form.get('nama_barang', '').strip()
        nominal_str = request.form.get('nominal', '0').replace('.', '').replace(',', '')
        try:
            tgl     = date.fromisoformat(tgl_str)
            nominal = int(nominal_str)
            if not nama or nominal <= 0:
                raise ValueError
            
            if tipe == 'Masuk' and kategori != 'Harian Penjualan':
                raise ValueError
            elif tipe == 'Keluar' and kategori not in ['Harian', 'Stok Bahan', 'Operasional']:
                raise ValueError
                
            new_tx = Transaksi(
                tanggal=tgl, 
                tipe=tipe, 
                kategori=kategori, 
                nama_barang=nama, 
                nominal=nominal,
                user_id=session.get('user_id')
            )
            db.session.add(new_tx)
            db.session.commit()
            pesan = {'status': 'success', 'text': f'Transaksi "{nama}" berhasil disimpan!'}
        except Exception:
            pesan = {'status': 'error', 'text': 'Data tidak valid. Periksa kembali semua isian Anda.'}

    return render_template('input.html', today=date.today().isoformat(), pesan=pesan)


# ── Hapus Transaksi ───────────────────────────────────────────────────────────

@login_required
def hapus_transaksi(id):
    user_id = session.get('user_id')
    tx = Transaksi.query.filter_by(id=id, user_id=user_id).first()
    if tx:
        db.session.delete(tx)
        db.session.commit()
    return redirect(url_for('dashboard'))


# ── Cetak Laporan ─────────────────────────────────────────────────────────────

@login_required
def cetak_laporan():
    return render_template('cetak_laporan.html', today=date.today().isoformat())


# ── Ekspor Transaksi ke CSV ───────────────────────────────────────────────────

@login_required
def export_csv():
    try:
        today = date.today()
        user_id = session.get('user_id')
        range_val = request.args.get('range')
        start_date = None
        
        def get_past_month_date(date_obj, months_back):
            m = date_obj.month - months_back
            y = date_obj.year
            while m <= 0:
                m += 12
                y -= 1
            return date(y, m, 1)

        periode_str = "Semua Waktu"
        months_list = []
        if range_val == '1':
            start_date = get_past_month_date(today, 0)
            months_list = [start_date]
        elif range_val == '2':
            start_date = get_past_month_date(today, 1)
            months_list = [start_date, get_past_month_date(today, 0)]
        elif range_val == '3':
            start_date = get_past_month_date(today, 2)
            months_list = [start_date, get_past_month_date(today, 1), get_past_month_date(today, 0)]
            
        if months_list:
            parts = []
            for i, m in enumerate(months_list):
                name = _BULAN[m.strftime('%B')]
                if i == len(months_list) - 1 or m.year != months_list[i+1].year:
                    parts.append(f"{name} {m.year}")
                else:
                    parts.append(name)
            periode_str = "Bulan: " + " - ".join(parts)
            
        base_query = Transaksi.query.filter_by(user_id=user_id)
        
        if start_date:
            rows = base_query.filter(Transaksi.tanggal >= start_date).order_by(Transaksi.tanggal.asc(), Transaksi.id.asc()).all()
        else:
            rows = base_query.order_by(Transaksi.tanggal.asc(), Transaksi.id.asc()).all()
            
        saldo_awal = 0
        if start_date:
            past_rows = base_query.filter(Transaksi.tanggal < start_date).all()
            for r in past_rows:
                if r.tipe == 'Masuk':
                    saldo_awal += r.nominal
                else:
                    saldo_awal -= r.nominal
                    
        total_penjualan = sum(r.nominal for r in rows if r.tipe == 'Masuk')
        total_penarikan = sum(r.nominal for r in rows if r.tipe == 'Keluar')
        saldo_akhir = saldo_awal + total_penjualan - total_penarikan

        def format_rp(val):
            if val < 0:
                return f"Rp.-{abs(val):,}".replace(',', '.')
            return f"Rp.{val:,}".replace(',', '.')

        # Generate CSV in memory (delimiter ';' lebih bersahabat dengan Excel Indonesia)
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Header Rekening Koran
        writer.writerow(['Rekening Koran Toko - WARTEG PLAMBOYAN'])
        writer.writerow([periode_str])
        writer.writerow([])
        writer.writerow(['Rangkuman'])
        writer.writerow(['Total Transaksi :', f"{len(rows)} Transaksi"])
        writer.writerow(['Total Pendapatan :', format_rp(total_penjualan)])
        writer.writerow(['Total Pengeluaran :', format_rp(total_penarikan)])
        writer.writerow([])
        
        # Kolom Data
        writer.writerow(['Tanggal', 'Tipe Transaksi', 'kategori', 'keterangan', 'nominal'])
        
        for row in rows:
            tgl_str = row.tanggal.strftime('%d/%m/%Y')
            writer.writerow([
                tgl_str, 
                row.tipe, 
                row.kategori, 
                row.nama_barang, 
                format_rp(row.nominal)
            ])
            
        # Supaya tidak ada masalah encoding saat dibuka di Excel, tambahkan BOM
        csv_data = "\ufeff" + output.getvalue()
        
        # Buat nama file dinamis berdasarkan rentang waktu
        if range_val in ['1', '2', '3']:
            safe_filename = periode_str.replace("Bulan: ", "").replace(" - ", "_").replace(" ", "_")
        else:
            safe_filename = "Semua_Waktu"
            
        return Response(
            csv_data,
            mimetype="text/csv; charset=utf-8-sig",
            headers={"Content-disposition": f"attachment; filename=Rekening_Koran_{safe_filename}.csv"}
        )
    except Exception as e:
        return f"Gagal mengekspor data: {e}", 500
