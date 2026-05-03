import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# --- CONFIGURACIÓN DE BASE DE DATOS ---
if os.name == 'nt': 
    DB_PATH = os.path.join(os.getcwd(), 'ordoklar.db')
else: 
    DB_PATH = '/tmp/ordoklar.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabla de Personal
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        legajo TEXT UNIQUE,
        estado_p TEXT DEFAULT 'ACTIVO'
    )''')
    # Tabla de Puestos
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cantidad INTEGER
    )''')
    # Tabla de Novedades
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER,
        fecha TEXT,
        estado TEXT,
        UNIQUE(personal_id, fecha)
    )''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- RUTAS API ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        try:
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo']))
            conn.commit()
        except: return jsonify({"error": "Error de duplicado"}), 400
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, cantidad) VALUES (?, ?)", (d['nombre'], d['cantidad']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos/<int:id>', methods=['DELETE'])
def delete_puesto(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM puestos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                        ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                     (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- INTERFAZ UNIFICADA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión de Personal</title>
    <style>
        :root { 
            --gold: #C5A059; --black: #050505; --dark-gray: #121212; --text: #E0E0E0; 
            --color-12: #1b5e20; --color-F: #dae343; --color-VAC: #01579b; --color-ART: #ef6c00;
        }
        body { background: var(--black); color: var(--text); font-family: sans-serif; margin: 0; }
        .header { background: #000; border-bottom: 1px solid var(--gold); padding: 20px; text-align: center; }
        .logo { letter-spacing: 5px; font-size: 24px; text-transform: uppercase; }
        .logo span { color: var(--gold); font-weight: 800; }
        .nav { background: var(--dark-gray); display: flex; justify-content: center; border-bottom: 1px solid #222; }
        .nav-btn { background: none; border: none; color: #888; padding: 15px 25px; cursor: pointer; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 20px; max-width: 1400px; margin: 0 auto; }
        .section { display: none; }
        .section.active { display: block; }
        .card { background: var(--dark-gray); border-radius: 8px; border: 1px solid #222; padding: 20px; margin-bottom: 20px; }
        
        /* Planilla Styles */
        .tabla-scroll { overflow-x: auto; background: var(--dark-gray); border-radius: 8px; border: 1px solid #222; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { border: 1px solid #222; padding: 8px; text-align: center; }
        .col-nombre { text-align: left; width: 200px; color: var(--gold); font-weight: bold; background: #000; }
        select { background: transparent; color: #fff; border: none; cursor: pointer; font-weight: bold; width: 100%; }
        .cell-12 { background-color: var(--color-12); }
        .cell-F { background-color: var(--color-F); color: #000; }
        .cell-VAC { background-color: var(--color-VAC); }
        .cell-ART { background-color: var(--color-ART); }

        /* Inputs & Buttons */
        input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 4px; margin: 5px; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; border-radius: 4px; }
    </style>
</head>
<body>
<div class="header"><div class="logo">ORDO <span>KLAR</span></div></div>
<div class="nav">
    <button class="nav-btn active" onclick="showTab('planilla')">Planilla Mensual</button>
    <button class="nav-btn" onclick="showTab('personal')">Personal</button>
    <button class="nav-btn" onclick="showTab('puestos')">Puestos / Diaria</button>
</div>

<div class="container">
    <!-- SECCIÓN PLANILLA -->
    <div id="planilla" class="section active">
        <div class="tabla-scroll">
            <table><thead id="h-mensual"></thead><tbody id="b-mensual"></tbody></table>
        </div>
    </div>

    <!-- SECCIÓN PERSONAL -->
    <div id="personal" class="section">
        <div class="card">
            <h3>Nuevo Personal</h3>
            <input type="text" id="p_legajo" placeholder="Legajo">
            <input type="text" id="p_apellido" placeholder="Apellido">
            <input type="text" id="p_nombre" placeholder="Nombre">
            <button class="btn" onclick="addPersonal()">Agregar</button>
        </div>
        <div class="tabla-scroll">
            <table id="t-personal"></table>
        </div>
    </div>

    <!-- SECCIÓN PUESTOS -->
    <div id="puestos" class="section">
        <div class="card">
            <h3>Configuración de Puestos</h3>
            <input type="text" id="pst_nombre" placeholder="Nombre del Puesto">
            <input type="number" id="pst_cant" placeholder="Plazas">
            <button class="btn" onclick="addPuesto()">Crear Puesto</button>
        </div>
        <div id="grid-puestos" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:20px;"></div>
    </div>
</div>

<script>
    let personal = [], novedades = [], puestos = [];

    async function fetchData() {
        personal = await fetch('/api/personal').then(r => r.json());
        novedades = await fetch('/api/novedades').then(r => r.json());
        puestos = await fetch('/api/puestos').then(r => r.json());
        renderAll();
    }

    function showTab(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        event.target.classList.add('active');
    }

    function renderAll() {
        renderPlanilla();
        renderPersonal();
        renderPuestos();
    }

    function renderPlanilla() {
        const hoy = new Date(), mes = hoy.getMonth(), anio = hoy.getFullYear();
        const totalDias = new Date(anio, mes + 1, 0).getDate();
        let h = '<tr><th class="col-nombre">Personal</th>';
        for(let i=1; i<=totalDias; i++) h += `<th>${i}</th>`;
        document.getElementById('h-mensual').innerHTML = h + '</tr>';

        document.getElementById('b-mensual').innerHTML = personal.map(p => {
            let td = `<td class="col-nombre">${p.apellido}</td>`;
            for(let i=1; i<=totalDias; i++){
                const fecha = `${anio}-${String(mes+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const nov = novedades.find(n => n.personal_id == p.id && n.fecha == fecha);
                const estado = nov ? nov.estado : 'F';
                td += `<td class="cell-${estado}">
                    <select onchange="updateNov(${p.id}, '${fecha}', this.value)">
                        <option value="12" ${estado=='12'?'selected':''}>12</option>
                        <option value="F" ${estado=='F'?'selected':''}>F</option>
                        <option value="VAC" ${estado=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${estado=='ART'?'selected':''}>A</option>
                    </select></td>`;
            }
            return `<tr>${td}</tr>`;
        }).join('');
    }

    async function updateNov(p_id, fecha, estado) {
        await fetch('/api/novedades', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({p_id, fecha, estado})
        });
        fetchData();
    }

    function renderPersonal() {
        document.getElementById('t-personal').innerHTML = personal.map(p => 
            `<tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td><td><button onclick="delP(${p.id})">Eliminar</button></td></tr>`
        ).join('');
    }

    async function addPersonal() {
        const d = { legajo: document.getElementById('p_legajo').value, apellido: document.getElementById('p_apellido').value, nombre: document.getElementById('p_nombre').value };
        await fetch('/api/personal', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(d)});
        fetchData();
    }

    async function delP(id) { await fetch(`/api/personal/${id}`, {method:'DELETE'}); fetchData(); }

    function renderPuestos() {
        document.getElementById('grid-puestos').innerHTML = puestos.map(pst => {
            let selects = "";
            for(let i=0; i<pst.cantidad; i++) {
                selects += `<select style="background:#000; border:1px solid #333; margin-top:5px;"><option>-- Asignar --</option>${personal.map(p => `<option>${p.apellido}</option>`).join('')}</select>`;
            }
            return `<div class="card"><div style="display:flex; justify-content:space-between"><b>${pst.nombre}</b><button onclick="delPst(${pst.id})">✕</button></div>${selects}</div>`;
        }).join('');
    }

    async function addPuesto() {
        const d = { nombre: document.getElementById('pst_nombre').value, cantidad: document.getElementById('pst_cant').value };
        await fetch('/api/puestos', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(d)});
        fetchData();
    }

    async function delPst(id) { await fetch(`/api/puestos/${id}`, {method:'DELETE'}); fetchData(); }

    window.onload = fetchData;
</script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
