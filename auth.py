from functools import wraps
from flask import session, redirect, url_for, flash, request, render_template
from database import User, verify_password


# ── Decorator proteksi rute ───────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


# ── Halaman Login ─────────────────────────────────────────────────────────────

def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '')

        user = User.query.filter_by(username=username).first()

        if user and verify_password(password, user.password):
            session.clear()
            session['user_id']  = user.id
            session['username'] = user.username
            safe_next = (next_url
                         if next_url and next_url.startswith('/')
                         else url_for('dashboard'))
            return redirect(safe_next)
        else:
            error = 'Username atau password salah.'

    return render_template('login.html',
                           error=error,
                           next=request.args.get('next', ''))


# ── Halaman Logout ────────────────────────────────────────────────────────────

def logout():
    session.clear()
    return redirect(url_for('login'))
