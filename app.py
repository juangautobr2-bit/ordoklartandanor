import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ordo_klar_v75_key')

# --- VÍNCULO A NEON ---
def get_db_connection():
    # Usamos la variable de entorno de Render
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Mantenemos tus tablas exactamente como las definimos al principio
    cur.execute('''CREATE TABLE IF NOT EXISTS personal (
        id SERIAL PRIMARY KEY, 
        nombre TEXT, 
        apellido TEXT, 
        legajo TEXT UNIQUE)''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id SERIAL PRIMARY KEY, 
        nombre TEXT, 
        horario TEXT, 
        dotacion INTEGER)''')
    
    # Aquí está la Clave Compuesta para que no fallen las asignaciones
    cur.execute('''CREATE TABLE IF NOT EXISTS asignaciones (
        puesto_id INTEGER, 
        slot_index INTEGER, 
        personal_id INTEGER, 
        PRIMARY KEY(puesto_id, slot_index))''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS novedades (
        personal_id INTEGER, 
        fecha TEXT, 
        estado TEXT, 
        UNIQUE(personal_id, fecha))''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

# --- RUTAS DE NAVEGACIÓN (TUS RUTAS ORIGINALES) ---

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('u') == "admin" and request.form.get('p') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/templates/<path:path>')
def send_template(path):
    return render_template(path)

# --- API: PERSONAL (CON %s PARA NEON) ---

@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def api_personal():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (%s, %s, %s)", 
                    (d['nombre'], d['apellido'], d['legajo']))
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM personal WHERE id=%s", (request.args.get('id'),))
    conn.commit()
    cur.execute("SELECT * FROM personal ORDER BY apellido ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

# --- API: PUESTOS Y ASIGNACIONES (TU LÓGICA BASE) ---

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def api_puestos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        if d.get('id'):
            cur.execute("UPDATE puestos SET nombre=%s, horario=%s, dotacion=%s WHERE id=%s", 
                        (d['nombre'], d['horario'], int(d['dotacion']), d['id']))
        else:
            cur.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (%s, %s, %s)", 
                        (d['nombre'], d['horario'], int(d['dotacion'])))
    elif request.method == 'DELETE':
        pid = request.args.get('id')
        cur.execute("DELETE FROM puestos WHERE id=%s", (pid,))
        cur.execute("DELETE FROM asignaciones WHERE puesto_id=%s", (pid,))
    conn.commit()
    
    cur.execute("SELECT * FROM puestos ORDER BY id DESC")
    rows = cur.fetchall()
    puestos = []
    for r in rows:
        p = dict(r)
        cur.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=%s", (p['id'],))
        asig = cur.fetchall()
        p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
        puestos.append(p)
    cur.close()
    conn.close()
    return jsonify(puestos)

@app.route('/api/asignar_batch', methods=['POST'])
def asignar_batch():
    d = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    for a in d['asignaciones']:
        if a['per_id']:
            # ON CONFLICT hace que funcione el "Insert or Replace" en Neon
            cur.execute("""
                INSERT INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (%s, %s, %s)
                ON CONFLICT (puesto_id, slot_index) DO UPDATE SET personal_id = EXCLUDED.personal_id
            """, (d['puesto_id'], a['slot'], a['per_id']))
        else:
            cur.execute("DELETE FROM asignaciones WHERE puesto_id=%s AND slot_index=%s", 
                        (d['puesto_id'], a['slot']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})

# --- API: NOVEDADES (TU PLANILLA) ---

@app.route('/api/novedades', methods=['GET', 'POST'])
def api_novedades():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("""
            INSERT INTO novedades (personal_id, fecha, estado) VALUES (%s, %s, %s)
            ON CONFLICT (personal_id, fecha) DO UPDATE SET estado = EXCLUDED.estado
        """, (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
        return jsonify({"status": "ok"})
    
    cur.execute("SELECT * FROM novedades")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
