import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v75_modular_key'

# Configuración de la base de datos
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ordoklar_v75.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa las tablas necesarias si no existen."""
    with get_db_connection() as conn:
        # Tabla de Personal
        conn.execute('''CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT, 
            apellido TEXT, 
            legajo TEXT UNIQUE)''')
        
        # Tabla de Puestos/Guardias
        conn.execute('''CREATE TABLE IF NOT EXISTS puestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT, 
            horario TEXT, 
            dotacion INTEGER)''')
        
        # Tabla de Asignaciones (quién está en qué puesto)
        conn.execute('''CREATE TABLE IF NOT EXISTS asignaciones (
            puesto_id INTEGER, 
            slot_index INTEGER, 
            personal_id INTEGER, 
            PRIMARY KEY(puesto_id, slot_index))''')
        
        # Tabla de Novedades (asistencia mensual)
        conn.execute('''CREATE TABLE IF NOT EXISTS novedades (
            personal_id INTEGER, 
            fecha TEXT, 
            estado TEXT, 
            UNIQUE(personal_id, fecha))''')
        conn.commit()

# Ejecutar la creación de tablas al iniciar
init_db()

# --- RUTAS DE NAVEGACIÓN Y PLANTILLAS ---

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Credenciales básicas (puedes cambiarlas aquí)
        if request.form.get('u') == "admin" and request.form.get('p') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/templates/<path:path>')
def send_template(path):
    """Permite al index cargar dinámicamente los fragmentos HTML."""
    return render_template(path)

# --- API: PERSONAL ---

@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def api_personal():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo']))
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
        
        conn.commit()
        rows = conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()
        return jsonify([dict(row) for row in rows])

# --- API: PUESTOS Y ASIGNACIONES ---

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def api_puestos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            if d.get('id'):
                conn.execute("UPDATE puestos SET nombre=?, horario=?, dotacion=? WHERE id=?", 
                             (d['nombre'], d['horario'], int(d['dotacion']), d['id']))
            else:
                conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", 
                             (d['nombre'], d['horario'], int(d['dotacion'])))
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
        
        conn.commit()
        
        # Obtenemos puestos y sus asignados actuales
        puestos = []
        for r in conn.execute("SELECT * FROM puestos").fetchall():
            p = dict(r)
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
            puestos.append(p)
        return jsonify(puestos)

@app.route('/api/asignar_batch', methods=['POST'])
def asignar_batch():
    """Guarda quién fue asignado a cada puesto en la solapa de Guardias."""
    d = request.json
    with get_db_connection() as conn:
        for a in d['asignaciones']:
            if a['per_id']: # Solo guarda si hay un ID de persona
                conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)", 
                             (d['puesto_id'], a['slot'], a['per_id']))
            else:
                conn.execute("DELETE FROM asignaciones WHERE puesto_id=? AND slot_index=?", 
                             (d['puesto_id'], a['slot']))
        conn.commit()
    return jsonify({"status":"ok"})

# --- API: NOVEDADES (PLANILLA MENSUAL) ---

@app.route('/api/novedades', methods=['GET', 'POST'])
def api_novedades():
    """Gestiona los estados (12, F, ART, etc.) de cada agente por día."""
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("""
                INSERT OR REPLACE INTO novedades (personal_id, fecha, estado) 
                VALUES (?, ?, ?)
            """, (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
            return jsonify({"status": "ok"})
        
        # Devolver todas las novedades para renderizar la planilla
        rows = conn.execute("SELECT * FROM novedades").fetchall()
        return jsonify([dict(row) for row in rows])

if __name__ == '__main__':
    # Ejecuta el servidor en modo desarrollo
    app.run(host='0.0.0.0', port=5000, debug=True)
