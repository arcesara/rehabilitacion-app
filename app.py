# ============================================================
# REHABILITACIÓN — Servidor web
# Flask + SocketIO + SQLite
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'rehab-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///rehabilitacion.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ─── MODELOS ────────────────────────────────────────────────

class Usuario(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    sesiones      = db.relationship('Sesion', backref='usuario', lazy=True)
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Sesion(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    usuario_id  = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    fecha       = db.Column(db.DateTime, default=datetime.utcnow)
    duracion_s  = db.Column(db.Float, default=0)
    reps_total  = db.Column(db.Integer, default=0)
    hr_medio    = db.Column(db.Float, default=0)
    datos_json  = db.Column(db.Text, default='{}')

    def get_datos(self):
        return json.loads(self.datos_json)

# ─── RUTAS AUTENTICACIÓN ────────────────────────────────────

@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        usuario  = Usuario.query.filter_by(email=email).first()
        if usuario and usuario.check_password(password):
            session['usuario_id'] = usuario.id
            session['nombre']     = usuario.nombre
            return redirect(url_for('dashboard'))
        error = 'Email o contraseña incorrectos'
    return render_template('login.html', error=error)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    error = None
    if request.method == 'POST':
        nombre   = request.form.get('nombre')
        email    = request.form.get('email')
        password = request.form.get('password')
        if Usuario.query.filter_by(email=email).first():
            error = 'Ya existe una cuenta con ese email'
        else:
            usuario = Usuario(nombre=nombre, email=email)
            usuario.set_password(password)
            db.session.add(usuario)
            db.session.commit()
            session['usuario_id'] = usuario.id
            session['nombre']     = usuario.nombre
            return redirect(url_for('dashboard'))
    return render_template('registro.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── RUTAS PRINCIPALES ──────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    ultima  = Sesion.query.filter_by(usuario_id=usuario.id).order_by(Sesion.fecha.desc()).first()
    return render_template('dashboard.html', usuario=usuario, ultima_sesion=ultima)

@app.route('/ejercicio')
def ejercicio():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('ejercicio.html', nombre=session['nombre'])

@app.route('/historial')
def historial():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    sesiones = Sesion.query.filter_by(usuario_id=session['usuario_id'])\
                           .order_by(Sesion.fecha.desc()).all()
    return render_template('historial.html', sesiones=sesiones)

@app.route('/sesion/<int:sesion_id>')
def detalle_sesion(sesion_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    s = Sesion.query.get_or_404(sesion_id)
    if s.usuario_id != session['usuario_id']:
        return redirect(url_for('historial'))
    return render_template('detalle_sesion.html', sesion=s)

# ─── API PARA RASPBERRY PI ──────────────────────────────────

@app.route('/api/datos', methods=['POST'])
def recibir_datos():
    """La RPi manda datos en tiempo real aquí."""
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Sin datos'}), 400
    # Reenviar a todos los clientes web conectados por WebSocket
    socketio.emit('datos_sensores', datos)
    return jsonify({'ok': True})

@app.route('/api/sesion', methods=['POST'])
def guardar_sesion():
    """La RPi manda el resumen completo al terminar la sesión."""
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Sin datos'}), 400

    usuario_id = datos.get('usuario_id')
    if not usuario_id:
        return jsonify({'error': 'Sin usuario_id'}), 400

    muestras = datos.get('muestras', [])
    reps     = datos.get('repeticiones', [])

    # Calcular métricas
    hr_values = [m.get('heartrate', 0) for m in muestras if m.get('heartrate', 0) > 0]
    hr_medio  = round(sum(hr_values) / len(hr_values), 1) if hr_values else 0
    duracion  = (muestras[-1]['ts'] - muestras[0]['ts']) if len(muestras) > 1 else 0

    nueva = Sesion(
        usuario_id = usuario_id,
        duracion_s = round(duracion, 1),
        reps_total = len(reps),
        hr_medio   = hr_medio,
        datos_json = json.dumps(datos),
    )
    db.session.add(nueva)
    db.session.commit()

    socketio.emit('sesion_completada', {
        'sesion_id': nueva.id,
        'reps':      len(reps),
        'hr_medio':  hr_medio,
        'duracion':  round(duracion, 1),
    })

    return jsonify({'ok': True, 'sesion_id': nueva.id})

# ─── WEBSOCKET EVENTOS ──────────────────────────────────────

@socketio.on('connect')
def on_connect():
    print(f'[WS] Cliente conectado')

@socketio.on('disconnect')
def on_disconnect():
    print(f'[WS] Cliente desconectado')

# ─── ARRANQUE ───────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
