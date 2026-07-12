import csv
import io
from flask import render_template, request, redirect, url_for, Response
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

    # Statistik hari ini
    today_rows = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).filter(Transaksi.tanggal == today).group_by(Transaksi.tipe).all()
    total_masuk_hari  = next((r.total for r in today_rows if r.tipe == 'Masuk'),  0) or 0
    total_keluar_hari = next((r.total for r in today_rows if r.tipe == 'Keluar'), 0) or 0
    saldo_hari        = total_masuk_hari - total_keluar_hari

    # Data 7 hari untuk bar chart
    labels, bar_masuk, bar_keluar = [], [], []
    for i in range(6, -1, -1):
        d    = today - timedelta(days=i)
        rows = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).filter(Transaksi.tanggal == d).group_by(Transaksi.tipe).all()
        labels.append(d.strftime('%d %b'))
        bar_masuk.append(next((r.total for r in rows if r.tipe == 'Masuk'),  0) or 0)
        bar_keluar.append(next((r.total for r in rows if r.tipe == 'Keluar'), 0) or 0)

    # 10 transaksi terbaru
    riwayat = Transaksi.query.order_by(Transaksi.tanggal.desc(), Transaksi.id.desc()).limit(10).all()

    # Total keseluruhan
    totals = db.session.query(Transaksi.tipe, func.sum(Transaksi.nominal).label('total')).group_by(Transaksi.tipe).all()
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
                
            new_tx = Transaksi(tanggal=tgl, tipe=tipe, kategori=kategori, nama_barang=nama, nominal=nominal)
            db.session.add(new_tx)
            db.session.commit()
            pesan = {'status': 'success', 'text': f'Transaksi "{nama}" berhasil disimpan!'}
        except Exception:
            pesan = {'status': 'error', 'text': 'Data tidak valid. Periksa kembali semua isian Anda.'}

    return render_template('input.html', today=date.today().isoformat(), pesan=pesan)


# ── Hapus Transaksi ───────────────────────────────────────────────────────────

@login_required
def hapus_transaksi(id):
    tx = Transaksi.query.get(id)
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
        start_date = None
        
        range_val = request.args.get('range')
        if range_val == '1':
            start_date = today.replace(day=1)
        elif range_val == '2':
            start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif range_val == '3':
            prev = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            start_date = (prev - timedelta(days=1)).replace(day=1)
            
        if start_date:
            rows = Transaksi.query.filter(Transaksi.tanggal >= start_date).order_by(Transaksi.tanggal.desc(), Transaksi.id.desc()).all()
        else:
            rows = Transaksi.query.order_by(Transaksi.tanggal.desc(), Transaksi.id.desc()).all()
        
        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['ID', 'Tanggal', 'Tipe', 'Kategori', 'Nama Barang', 'Nominal'])
        
        # Data
        for row in rows:
            writer.writerow([
                row.id, 
                row.tanggal, 
                row.tipe, 
                row.kategori, 
                row.nama_barang, 
                row.nominal
            ])
            
        csv_data = output.getvalue()
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=laporan_transaksi.csv"}
        )
    except Exception as e:
        return f"Gagal mengekspor data: {e}", 500
