import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v75_modular'

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ordoklar_v75.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS asignaciones (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, PRIMARY KEY(puesto_id, slot_index))')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        conn.commit()

init_db()

# --- RUTAS DE NAVEGACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('u') == "admin" and request.form.get('p') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('index.html')

# --- API ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def api_personal():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
        conn.commit()
        return jsonify([dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()])

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def api_puestos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            if d.get('id'):
                conn.execute("UPDATE puestos SET nombre=?, horario=?, dotacion=? WHERE id=?", (d['nombre'], d['horario'], int(d['dotacion']), d['id']))
            else:
                conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", (d['nombre'], d['horario'], int(d['dotacion'])))
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
        conn.commit()
        
        puestos = []
        for r in conn.execute("SELECT * FROM puestos").fetchall():
            p = dict(r)
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
            puestos.append(p)
        return jsonify(puestos)

@app.route('/api/asignar_batch', methods=['POST'])
def asignar_batch():
    d = request.json
    with get_db_connection() as conn:
        for a in d['asignaciones']:
            conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)", (d['puesto_id'], a['slot'], a['per_id']))
        conn.commit()
    return jsonify({"status":"ok"})

if __name__ == '__main__':
    app.run(debug=True)
