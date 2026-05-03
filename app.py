import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import calendar

app = Flask(__name__)

# Base de datos persistente en el entorno temporal de Render
DB_PATH = '/tmp/ordoklar_v3.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Aseguramos que todas las tablas existan en cada conexión
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, apellido TEXT, legajo TEXT, estado_p TEXT DEFAULT 'ACTIVO')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, cantidad INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER, fecha TEXT, estado TEXT,
        UNIQUE(personal_id, fecha))''')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API DE GESTIÓN ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                     (d.get('nombre'), d.get('apellido'), d.get('legajo')))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

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

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                        ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                     (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# --- INTERFAZ PREMIUM ORDO KLAR ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Sistema de Gestión</title>
    <style>
        :root { --gold: #C5A059; --black: #050505; --dark: #121212; --gray: #222; }
        body { background: var(--black); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; }
        .header { text-align: center; padding: 20px; border-bottom: 1px solid var(--gold); letter-spacing: 5px; background: #000; }
        .nav { display: flex; justify-content: center; background: var(--dark); border-bottom: 1px solid #333; }
        .nav-btn { background: none; border: none; color: #777; padding: 15px 30px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 12px; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 30px; max-width: 1500px; margin: 0 auto; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .card { background: var(--dark); border: 1px solid #333; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; margin-right: 10px; }
        button.btn-gold { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; background: var(--dark); }
        th, td { border: 1px solid #333; padding: 10px; text-align: center; font-size: 13px; }
        th { color: var(--gold); background: #000; }
        .col-nombre { text-align: left; min-width: 200px; font-weight: bold; color: var(--gold); }
        select { background: transparent; color: #fff; border: none; cursor: pointer; font-weight: bold; width: 100%; text-align-last: center; }
        /* Estados */
        .st-12 { background: #1b5e20 !important; } .st-F { background: #b71c1c !important; }
        .st-VAC { background: #01579b !important; } .st-ART { background: #e65100 !important; }
        .grid-puestos { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    <div class="nav">
        <button class="nav-btn active" onclick="openTab(event, 'tab-planilla')">Planilla Mensual</button>
        <button class="nav-btn" onclick="openTab(event, 'tab-personal')">Personal</button>
        <button class="nav-btn" onclick="openTab(event, 'tab-puestos')">Puestos</button>
    </div>

    <div class="container">
        <!-- PLANILLA MENSUAL -->
        <div id="tab-planilla" class="tab-content active">
            <h3 class="gold">CONTROL DE ASISTENCIA - MES ACTUAL</h3>
            <div style="overflow-x: auto;">
                <table id="table-planilla">
                    <thead id="head-planilla"></thead>
                    <tbody id="body-planilla"></tbody>
                </table>
            </div>
        </div>

        <!-- GESTIÓN DE PERSONAL -->
        <div id="tab-personal" class="tab-content">
            <div class="card">
                <h3>Nuevo Integrante</h3>
                <input type="text" id="p-legajo" placeholder="Legajo">
                <input type="text" id="p-apellido" placeholder="Apellido">
                <input type="text" id="p-nombre" placeholder="Nombre">
                <button class="btn-gold" onclick="addPersonal()">REGISTRAR</button>
            </div>
            <table>
                <thead><tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acciones</th></tr></thead>
                <tbody id="lista-personal"></tbody>
            </table>
        </div>

        <!-- GESTIÓN DE PUESTOS -->
        <div id="tab-puestos" class="tab-content">
            <div class="card">
                <h3>Crear Nuevo Puesto</h3>
                <input type="text" id="pst-nombre" placeholder="Nombre del Puesto (ej. Acceso 1)">
                <input type="number" id="pst-cant" placeholder="Cantidad de Plazas">
                <button class="btn-gold" onclick="addPuesto()">CREAR PUESTO</button>
            </div>
            <div id="grid-puestos" class="grid-puestos"></div>
        </div>
    </div>

    <script>
        let personal = [], novedades = [], puestos = [];

        async function refreshData() {
            personal = await fetch('/api/personal').then(r => r.json());
            novedades = await fetch('/api/novedades').then(r => r.json());
            puestos = await fetch('/api/puestos').then(r => r.json());
            renderAll();
        }

        function openTab(evt, tabId) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            evt.currentTarget.classList.add('active');
        }

        function renderAll() {
            // Render Personal
            document.getElementById('lista-personal').innerHTML = personal.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPersonal(${p.id})" style="background:red; color:white; border:none; padding:5px; border-radius:3px; cursor:pointer;">Eliminar</button></td></tr>
            `).join('');

            // Render Planilla
            const now = new Date();
            const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
            
            let h = '<tr><th class="col-nombre">Apellido y Nombre</th>';
            for(let i=1; i<=daysInMonth; i++) h += `<th>${i}</th>`;
            document.getElementById('head-planilla').innerHTML = h + '</tr>';

            document.getElementById('body-planilla').innerHTML = personal.map(p => {
                let r = `<tr><td class="col-nombre">${p.apellido.toUpperCase()}</td>`;
                for(let i=1; i<=daysInMonth; i++){
                    const fecha = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const nov = novedades.find(n => n.personal_id == p.id && n.fecha == fecha);
                    const val = nov ? nov.estado : 'F';
                    r += `<td class="st-${val}"><select onchange="updateNov(${p.id}, '${fecha}', this.value)">
                        <option value="12" ${val=='12'?'selected':''}>12</option>
                        <option value="F" ${val=='F'?'selected':''}>F</option>
                        <option value="VAC" ${val=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${val=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return r + '</tr>';
            }).join('');

            // Render Puestos
            document.getElementById('grid-puestos').innerHTML = puestos.map(pst => {
                let lines = "";
                for(let i=0; i<pst.cantidad; i++) {
                    lines += `<select style="width:100%; margin-bottom:5px; background:#000; color:#fff; border:1px solid #444; padding:5px;">
                        <option>-- VACANTE --</option>
                        ${personal.map(p => `<option>${p.apellido}</option>`).join('')}
                    </select>`;
                }
                return `<div class="card"><h4 style="color:var(--gold); margin-top:0;">${pst.nombre.toUpperCase()}</h4>${lines}</div>`;
            }).join('');
        }

        async function addPersonal() {
            const data = { legajo: document.getElementById('p-legajo').value, apellido: document.getElementById('p-apellido').value, nombre: document.getElementById('p-nombre').value };
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)});
            refreshData();
        }

        async function updateNov(p_id, fecha, estado) {
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado})});
            refreshData();
        }

        async function addPuesto() {
            const data = { nombre: document.getElementById('pst-nombre').value, cantidad: document.getElementById('pst-cant').value };
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)});
            refreshData();
        }

        async function delPersonal(id) {
            if(confirm("¿Eliminar?")) { await fetch('/api/personal/'+id, {method:'DELETE'}); refreshData(); }
        }

        window.onload = refreshData;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
