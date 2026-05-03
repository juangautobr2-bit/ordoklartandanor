import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Cambiamos el nombre de la DB para forzar una estructura limpia
DB_PATH = '/tmp/ordoklar_v8.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs PERSONAL ---
@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE', 'PUT'])
def edit_del_personal(id):
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE personal SET nombre=?, apellido=?, legajo=? WHERE id=?", (d['nombre'], d['apellido'], d['legajo'], id))
    conn.commit()
    conn.close()
    return jsonify({"s": "ok"})

# --- APIs PUESTOS ---
@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, cantidad) VALUES (?, ?)", (d['nombre'], d['cantidad']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos/<int:id>', methods=['DELETE'])
def del_puesto(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM puestos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"s": "ok"})

# --- API NOVEDADES ---
@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

# --- INTERFAZ PROFESIONAL ---
HTML_UI = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel v8</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --gray: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; }
        
        .header { text-align: center; padding: 15px; font-size: 22px; letter-spacing: 8px; border-bottom: 1px solid var(--gray); background: #000; }
        
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--gold); margin-bottom: 10px; }
        .nav button { background: none; border: none; color: #777; padding: 15px 25px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 2px solid var(--gold); }

        .container { padding: 10px; }
        .section { display: none; }
        .active { display: block; }

        /* PLANILLA COMPACTA */
        .wrapper { width: 100%; overflow: hidden; }
        table.pla { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 9px; background: #000; }
        .pla th, .pla td { border: 1px solid #222; text-align: center; height: 32px; padding: 0; }
        .pla th { color: var(--gold); font-weight: normal; background: #111; }
        .col-nombre { width: 100px; text-align: left !important; padding-left: 5px !important; color: var(--gold); font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .col-hs { width: 35px; background: #1a1a1a; color: var(--gold); font-weight: bold; border-left: 1px solid var(--gold) !important; font-size: 11px; }

        /* SELECTORES Y COLORES */
        select { background: transparent; color: #fff; border: none; width: 100%; height: 100%; cursor: pointer; font-weight: bold; text-align-last: center; outline: none; appearance: none; }
        .st-12 { background: #1b5e20 !important; } /* Verde */
        .st-F { background: #333 !important; }    /* Gris */
        .st-VAC { background: #01579b !important; } /* Azul */
        .st-ART { background: #b71c1c !important; } /* Rojo */

        /* PERSONAL */
        .card { background: var(--card); border: 1px solid var(--gray); padding: 15px; border-radius: 6px; margin-bottom: 15px; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 8px; border-radius: 4px; margin-right: 5px; font-size: 12px; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 8px 15px; font-weight: bold; border-radius: 4px; cursor: pointer; }
        .btn-edit { color: var(--gold); border: 1px solid var(--gold); background: none; padding: 4px 8px; cursor: pointer; border-radius: 4px; font-size: 10px; margin-right: 5px; }
        .btn-del { color: #ff4444; border: 1px solid #ff4444; background: none; padding: 4px 8px; cursor: pointer; border-radius: 4px; font-size: 10px; }
        
        .list-table { width: 100%; border-collapse: collapse; }
        .list-table td { padding: 12px; border-bottom: 1px solid var(--gray); font-size: 13px; }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="b1" class="active" onclick="show('pla')">Planilla Mensual</button>
        <button id="b2" onclick="show('
