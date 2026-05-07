import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v68_neon_verified'

# --- CONEXIÓN A NEON.TECH ---
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    # En Neon/Postgres usamos psycopg2
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Tablas con sintaxis PostgreSQL
            cur.execute('CREATE TABLE IF NOT EXISTS personal (id SERIAL PRIMARY KEY, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
            cur.execute('CREATE TABLE IF NOT EXISTS puestos (id SERIAL PRIMARY KEY, nombre TEXT, horario TEXT, dotacion INTEGER)')
            cur.execute('CREATE TABLE IF NOT EXISTS novedades (id SERIAL PRIMARY KEY, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
            cur.execute('CREATE TABLE IF NOT EXISTS informes (id SERIAL PRIMARY KEY, nombre TEXT, fecha_generado TEXT)')
            cur.execute('''CREATE TABLE IF NOT EXISTS asignaciones 
                            (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, 
                            PRIMARY KEY(puesto_id, slot_index))''')
            conn.commit()

init_db()

# --- SEGURIDAD ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Mantengo tus credenciales de admin
        if request.form.get('username') == "admin" and request.form.get('password') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = "Credenciales incorrectas"
    return render_template_string(HTML_LOGIN, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(HTML_UI)

# --- API ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    if not session.get('logged_in'): return jsonify([]), 401
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (%s, %s, %s)", (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM personal WHERE id=%s", (request.args.get('id'),))
        conn.commit()
    cur.execute("SELECT * FROM personal ORDER BY apellido ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

@app.route('/api/informes', methods=['GET', 'POST', 'DELETE'])
def handle_informes():
    if not session.get('logged_in'): return jsonify([]), 401
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO informes (nombre, fecha_generado) VALUES (%s, %s)", (d['nombre'], datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM informes WHERE id=%s", (request.args.get('id'),))
        conn.commit()
    cur.execute("SELECT * FROM informes ORDER BY id DESC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    if not session.get('logged_in'): return jsonify([]), 401
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        # Sintaxis UPSERT para PostgreSQL
        cur.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (%s, %s, %s)
                       ON CONFLICT (personal_id, fecha) DO UPDATE SET estado = EXCLUDED.estado''', 
                    (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    cur.execute("SELECT * FROM novedades")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

# (El resto de las rutas api/puestos y api/asignar siguen la misma lógica de cerrar cursor/conexión)
