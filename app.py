import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Configuración de base de datos en /tmp para Render
DB_PATH = '/tmp/ordoklar_full.db'

def get_db_connection():
    """Conecta y asegura que todas las tablas existan siempre."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Creación de tablas (si no existen)
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        legajo TEXT,
        estado_p TEXT DEFAULT 'ACTIVO'
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cantidad INTEGER
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id INTEGER,
        fecha TEXT,
        estado TEXT,
        UNIQUE(personal_id, fecha)
    )''')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API PERSONAL ---
@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                     (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

# --- API PUESTOS ---
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
def delete_puesto(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM puestos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

# --- API NOVEDADES ---
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

# --- INTERFAZ ÚNICA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión Integral</title>
    <style>
        :root { 
            --gold: #C5A059; --black: #050505; --gray: #121212; 
            --c-12: #1b5e20; --c-F: #dae343; --c-VAC: #01579b; --c-ART: #ef6c00;
        }
        body { background: var(--black); color: #E0E0E0; font-family: 'Segoe UI', sans-serif; margin: 0; }
        .header { background: #000; border-bottom: 1px solid var(--gold); padding: 15px; text-align: center; letter-spacing: 4px; }
        .nav { display: flex; justify-content: center; background: var(--gray); border-bottom: 1px solid #333; }
        .nav-btn { background: none; border: none; color: #888; padding: 15px 25px; cursor: pointer; text-transform: uppercase; font-size: 11px; font-weight: bold; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 20px; max-width: 1400px; margin: 0 auto; }
        .section { display: none; }
        .active { display: block; }
        .card { background: var(--gray); padding: 20px; border-radius: 10px; border: 1px solid #222; margin-bottom: 20px; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 5px; margin: 5px; }
        button.primary { background: var(--gold); color: #000; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
        th, td { border: 1px solid #333; padding: 8px; text-align: center; }
        .col-fix { text-align: left; color: var(--gold); font-weight: bold; min-width: 150px; }
        select { background: transparent; color: #fff; border: none; font-weight: bold; cursor: pointer; width: 100%; text-align-last: center; }
        .cell-12 { background: var(--c-12); } .cell-F { background: var(--c-F); color: #000; }
        .cell-VAC { background: var(--c-VAC); } .cell-ART { background: var(--c-ART); }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    <div class="nav">
        <button class="nav-btn active" onclick="tab('sec-planilla')">Planilla Mensual</button>
        <button class="nav-btn" onclick="tab('sec-personal')">Personal</button>
        <button class="nav-btn" onclick="tab('sec-puestos')">Puestos</button>
    </div>

    <div class="container">
        <!-- PLANILLA -->
        <div id="sec-planilla" class="section active">
            <div style="overflow-x:auto;">
                <table><thead id="h-plan"></thead><tbody id="b-plan"></tbody></table>
            </div>
        </div>

        <!-- PERSONAL -->
        <div id="sec-personal" class="section">
            <div class="card">
                <input type="text" id="p_legajo" placeholder="Legajo">
                <input type="text" id="p_ape" placeholder="Apellido">
                <input type="text" id="p_nom" placeholder="Nombre">
                <button class="primary" onclick="addPersonal()">AGREGAR</button>
            </div>
            <table>
                <thead><tr><th>Legajo</th><th>Nombre</th><th>Acción</th></tr></thead>
                <tbody id="lista-p"></tbody>
            </table>
        </div>

        <!-- PUESTOS -->
        <div id="sec-puestos" class="section">
            <div class="card">
                <input type="text" id="pst_nom" placeholder="Nombre Puesto">
                <input type="number" id="pst_cant" placeholder="Cantidad de Plazas">
                <button class="primary" onclick="addPuesto()">CREAR PUESTO</button>
            </div>
            <div id="grid-pst" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:20px;"></div>
        </div>
    </div>

    <script>
        let dataP = [], dataN = [], dataT = [];

        async function load() {
            dataP = await fetch('/api/personal').then(r => r.json());
            dataN = await fetch('/api/novedades').then(r => r.json());
            dataT = await fetch('/api/puestos').then(r => r.json());
            render();
        }

        function tab(id) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }

        function render() {
            // Render Personal
            document.getElementById('lista-p').innerHTML = dataP.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td>
                <td><button onclick="delP(${p.id})">Eliminar</button></td></tr>`).join('');

            // Render Planilla
            const dMes = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
            let h = '<tr><th class="col-fix">Personal</th>';
            for(let i=1; i<=dMes; i++) h += `<th>${i}</th>`;
            document.getElementById('h-plan').innerHTML = h + '</tr>';
            
            document.getElementById('b-plan').innerHTML = dataP.map(p => {
                let row = `<td class="col-fix">${p.apellido.toUpperCase()}</td>`;
                for(let i=1; i<=dMes; i++){
                    const f = `${new Date().getFullYear()}-${String(new Date().getMonth()+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = dataN.find(x => x.personal_id == p.id && x.fecha == f);
                    const e = n ? n.estado : 'F';
                    row += `<td class="cell-${e}"><select onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${e=='12'?'selected':''}>12</option>
                        <option value="F" ${e=='F'?'selected':''}>F</option>
                        <option value="VAC" ${e=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${e=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${row}</tr>`;
            }).join('');

            // Render Puestos
            document.getElementById('grid-pst').innerHTML = dataT.map(t => {
                let sels = "";
                for(let i=0; i<t.cantidad; i++) sels += `<select style="margin-top:5px; background:#000; color:#fff; border:1px solid #444; padding:5px; width:100%;"><option>-- VACANTE --</option>${dataP.map(p => `<option>${p.apellido}</option>`).join('')}</select>`;
                return `<div class="card"><b>${t.nombre.toUpperCase()}</b><br>${sels}<br><button onclick="delT(${t.id})" style="margin-top:10px; background:none; color:red; border:none; cursor:pointer;">Eliminar Puesto</button></div>`;
            }).join('');
        }

        async function addPersonal() {
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({legajo:document.getElementById('p_legajo').value, apellido:document.getElementById('p_ape').value, nombre:document.getElementById('p_nom').value})});
            load();
        }

        async function updNov(p_id, fecha, estado) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado})});
            load();
        }

        async function addPuesto() {
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({nombre:document.getElementById('pst_nom').value, cantidad:document.getElementById('pst_cant').value})});
            load();
        }

        async function delP(id) { await fetch('/api/personal/'+id, {method:'DELETE'}); load(); }
        async function delT(id) { await fetch('/api/puestos/'+id, {method:'DELETE'}); load(); }

        window.onload = load;
    </script>
</body>
</html>
