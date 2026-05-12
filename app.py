# ============================================================
# REHABILITACIÓN — Servidor web (versión con ejercicios y niveles)
# Flask + SocketIO + SQLi<te
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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# ─── DEFINICIÓN DE EJERCICIOS Y NIVELES ─────────────────────

EJERCICIOS = {
    "sentadillas": {
        "nombre": "Sentadillas",
        "descripcion": "Flexión de rodillas manteniendo el peso distribuido en ambos pies.",
        "icono": "S"
    },
    "equilibrio_monopodal": {
        "nombre": "Equilibrio monopodal",
        "descripcion": "Mantenerse en equilibrio sobre un solo pie alternando entre ambos.",
        "icono": "E"
    },
    "saltos": {
        "nombre": "Saltos en el sitio",
        "descripcion": "Saltos suaves en el sitio aterrizando con ambos pies a la vez.",
        "icono": "SJ"
    },
    "transferencia_peso": {
        "nombre": "Transferencia de peso",
        "descripcion": "Desplazar el peso del pie izquierdo al derecho y viceversa de forma controlada.",
        "icono": "TP"
    },
    "puntillas": {
        "nombre": "Puntillas",
        "descripcion": "Elevación de talones apoyándose en la punta de los pies y volviendo.",
        "icono": "P"
    },
    "marcha_estatica": {
        "nombre": "Marcha estática",
        "descripcion": "Levantar los pies alternos simulando marcha sin desplazarse.",
        "icono": "ME"
    },
}

NIVELES = {
    1: {"reps": 5,  "intervalo_ms": 8000},
    2: {"reps": 8,  "intervalo_ms": 7000},
    3: {"reps": 10, "intervalo_ms": 6000},
    4: {"reps": 12, "intervalo_ms": 5000},
    5: {"reps": 15, "intervalo_ms": 4000},
}

# ─── MODELOS ────────────────────────────────────────────────

class Usuario(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nombre        = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    sesiones      = db.relationship('Sesion', backref='usuario', lazy=True)
    progreso      = db.relationship('Progreso', backref='usuario', lazy=True)
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_progreso(self, ejercicio_id):
        """Devuelve el nivel actual del usuario en un ejercicio."""
        p = Progreso.query.filter_by(usuario_id=self.id, ejercicio_id=ejercicio_id).first()
        return p.nivel_actual if p else 1

    def get_siguiente_ejercicio(self):
        """Devuelve el ejercicio y nivel recomendado para continuar."""
        for ej_id in EJERCICIOS:
            nivel = self.get_progreso(ej_id)
            if nivel <= 5:
                return ej_id, nivel
        return list(EJERCICIOS.keys())[0], 1

class UsuarioActivo(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Progreso(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ejercicio_id = db.Column(db.String(50), nullable=False)
    nivel_actual = db.Column(db.Integer, default=1)
    completado   = db.Column(db.Boolean, default=False)

class Sesion(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    usuario_id   = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    ejercicio_id = db.Column(db.String(50), default="sentadillas")
    nivel        = db.Column(db.Integer, default=1)
    fecha        = db.Column(db.DateTime, default=datetime.utcnow)
    duracion_s   = db.Column(db.Float, default=0)
    reps_total   = db.Column(db.Integer, default=0)
    hr_medio     = db.Column(db.Float, default=0)
    completada   = db.Column(db.Boolean, default=True)
    datos_json   = db.Column(db.Text, default='{}')

    def get_datos(self):
        return json.loads(self.datos_json)

    def nombre_ejercicio(self):
        return EJERCICIOS.get(self.ejercicio_id, {}).get('nombre', self.ejercicio_id)

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
            # Guardar usuario activo en BD para que la RPi lo pueda consultar
            activo = UsuarioActivo.query.first()
            if not activo:
                activo = UsuarioActivo(usuario_id=usuario.id)
                db.session.add(activo)
            else:
                activo.usuario_id = usuario.id
                activo.updated_at = datetime.utcnow()
            db.session.commit()
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
    if usuario is None:
        session.clear()
        return redirect(url_for('login'))

    ultima = Sesion.query.filter_by(usuario_id=usuario.id)\
                         .order_by(Sesion.fecha.desc()).first()

    # Ejercicio y nivel recomendado para continuar
    ej_id, nivel = usuario.get_siguiente_ejercicio()
    ejercicio_actual = EJERCICIOS.get(ej_id, {})
    nivel_config = NIVELES.get(nivel, NIVELES[1])

    return render_template('dashboard.html',
        usuario=usuario,
        ultima_sesion=ultima,
        ejercicio_actual=ejercicio_actual,
        ejercicio_actual_id=ej_id,
        nivel_actual=nivel,
        nivel_config=nivel_config,
        ejercicios=EJERCICIOS,
    )

@app.route('/ejercicios')
def lista_ejercicios():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario is None:
        session.clear()
        return redirect(url_for('login'))

    # Construir lista con progreso de cada ejercicio
    lista = []
    for ej_id, ej_info in EJERCICIOS.items():
        nivel = usuario.get_progreso(ej_id)
        lista.append({
            "id": ej_id,
            "nombre": ej_info["nombre"],
            "descripcion": ej_info["descripcion"],
            "icono": ej_info["icono"],
            "nivel_actual": nivel,
            "completado": nivel > 5,
        })

    return render_template('ejercicios.html', ejercicios=lista, usuario=usuario)

@app.route('/ejercicio/<ejercicio_id>/<int:nivel>')
def ejercicio(ejercicio_id, nivel):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if ejercicio_id not in EJERCICIOS or nivel not in NIVELES:
        return redirect(url_for('lista_ejercicios'))

    ej_info     = EJERCICIOS[ejercicio_id]
    nivel_config = NIVELES[nivel]

    return render_template('ejercicio.html',
        nombre=session['nombre'],
        ejercicio_id=ejercicio_id,
        ejercicio_nombre=ej_info['nombre'],
        ejercicio_desc=ej_info['descripcion'],
        nivel=nivel,
        reps=nivel_config['reps'],
        intervalo_ms=nivel_config['intervalo_ms'],
    )

@app.route('/historial')
def historial():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    if usuario is None:
        session.clear()
        return redirect(url_for('login'))
    sesiones = Sesion.query.filter_by(usuario_id=session['usuario_id'])\
                           .order_by(Sesion.fecha.desc()).all()
    return render_template('historial.html', sesiones=sesiones, ejercicios=EJERCICIOS)

@app.route('/sesion/<int:sesion_id>')
def detalle_sesion(sesion_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    s = Sesion.query.get_or_404(sesion_id)
    if s.usuario_id != session['usuario_id']:
        return redirect(url_for('historial'))
    return render_template('detalle_sesion.html', sesion=s, ejercicios=EJERCICIOS)

# ─── API PARA RASPBERRY PI ──────────────────────────────────

@app.route('/api/datos', methods=['POST'])
def recibir_datos():
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Sin datos'}), 400
    socketio.emit('datos_sensores', datos)
    return jsonify({'ok': True})

@app.route('/api/usuario_activo', methods=['GET'])
def usuario_activo():
    """Devuelve el ID del último usuario que hizo login."""
    activo = UsuarioActivo.query.first()
    if activo and activo.usuario_id:
        usuario = Usuario.query.get(activo.usuario_id)
        if usuario:
            return jsonify({'usuario_id': activo.usuario_id, 'nombre': usuario.nombre})
    return jsonify({'usuario_id': None}), 200
    
@app.route('/api/sesion', methods=['POST'])
def guardar_sesion():
    datos = request.get_json()
    if not datos:
        return jsonify({'error': 'Sin datos'}), 400

    usuario_id   = datos.get('usuario_id')
    ejercicio_id = datos.get('ejercicio_id', 'sentadillas')
    nivel        = datos.get('nivel', 1)

    if not usuario_id:
        return jsonify({'error': 'Sin usuario_id'}), 400

    muestras = datos.get('muestras', [])
    reps     = datos.get('repeticiones', [])

    hr_values = [m.get('heartrate', 0) for m in muestras if m.get('heartrate', 0) > 0]
    hr_medio  = round(sum(hr_values) / len(hr_values), 1) if hr_values else 0
    duracion  = (muestras[-1]['ts'] - muestras[0]['ts']) if len(muestras) > 1 else 0
    completada = len(reps) >= NIVELES.get(nivel, {}).get('reps', 0)

    nueva = Sesion(
        usuario_id   = usuario_id,
        ejercicio_id = ejercicio_id,
        nivel        = nivel,
        duracion_s   = round(duracion, 1),
        reps_total   = len(reps),
        hr_medio     = hr_medio,
        completada   = completada,
        datos_json   = json.dumps(datos),
    )
    db.session.add(nueva)

    # Actualizar progreso si la sesión fue completada
    if completada:
        progreso = Progreso.query.filter_by(
            usuario_id=usuario_id, ejercicio_id=ejercicio_id).first()
        if not progreso:
            progreso = Progreso(usuario_id=usuario_id, ejercicio_id=ejercicio_id, nivel_actual=1)
            db.session.add(progreso)
        if progreso.nivel_actual == nivel and nivel < 5:
            progreso.nivel_actual = nivel + 1
        elif nivel >= 5:
            progreso.completado = True

    db.session.commit()

    siguiente_nivel = min(nivel + 1, 5) if completada else nivel

    socketio.emit('sesion_completada', {
        'sesion_id':      nueva.id,
        'reps':           len(reps),
        'hr_medio':       hr_medio,
        'duracion':       round(duracion, 1),
        'completada':     completada,
        'nivel_actual':   nivel,
        'siguiente_nivel': siguiente_nivel,
        'ejercicio_id':   ejercicio_id,
        'ejercicio_nombre': EJERCICIOS.get(ejercicio_id, {}).get('nombre', ''),
    })

    return jsonify({'ok': True, 'sesion_id': nueva.id})

# ─── WEBSOCKET ──────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    print('[WS] Cliente conectado')

@socketio.on('disconnect')
def on_disconnect():
    print('[WS] Cliente desconectado')

# ─── ARRANQUE ───────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
