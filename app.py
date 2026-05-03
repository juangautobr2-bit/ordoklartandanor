import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# CONFIGURACIÓN PARA RENDER: Usamos la carpeta /tmp para tener permisos de escritura
DB_PATH = '/tmp/ordoklar.db'

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    try:
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
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"Error inicializando DB: {e}")

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
            conn.execute("INSERT INTO personal (nombre, apellido, legajo, estado_p) VALUES (?, ?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo'], d['estado_p']))
            conn.commit()
        except: 
            return jsonify({"error": "Legajo duplicado"}), 400
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE', 'PUT'])
def handle_personal_individual(id):
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE personal SET nombre=?, apellido=?, legajo=?, estado_p=? WHERE id=?", 
                     (d['nombre'], d['apellido'], d['legajo'], d['estado_p'], id))
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

@app.route('/api/novedades')
def get_novedades():
    conn = get_db_connection()
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/actualizar_novedad', methods=['POST'])
def update_nov():
    conn = get_db_connection()
    d = request.json
    try:
        conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                        ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                     (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    return jsonify({"status": "success"})

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- FRONTEND UI (EL HTML QUE YA TENÍAS) ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión de Personal</title>
    <style>
        :root { 
            --gold: #C5A059; --black: #050505; --dark-gray: #121212; --light-gray: #1E1E1E;
            --text-main: #E0E0E0; --text-dim: #888; --danger: #CF6679; --success: #03DAC6;
            --color-12: #1b5e20; --color-F: #dae343; --color-VAC: #01579b; --color-ART: #ef6c00; --color-FE: #6a1b9a;
        }
        body { background: var(--black); color: var(--text-main); font-family: sans-serif; margin: 0; }
        .header { background: #000; border-bottom: 1px solid var(--gold); padding: 15px; text-align: center; }
        .logo { letter-spacing: 5px; font-size: 22px; }
        .logo span { color: var(--gold); font-weight: 800; }
        .nav { background: var(--dark-gray); display: flex; justify-content: center; position: sticky; top: 0; z-index: 1000; }
        .nav-btn { background: none; border: none; color: var(--text-dim); padding: 15px 25px; cursor: pointer; font-size: 11px; text-transform: uppercase; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 20px; max-width: 1800px; margin: 0 auto; }
        .section { display: none; }
        .section.active { display: block; }
        .card { background: var(--dark-gray); border-radius: 12px; border: 1px solid #222; padding: 20px; margin-bottom: 20px; }
        .tabla-scroll { overflow-x: auto; background: var(--dark-gray); border-radius: 12px; border: 1px solid #222; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #222; text-align: center; padding: 8px; }
        .col-personal { width: 180px; text-align: left; color: var(--gold); font-weight: bold; }
        .dia-numero { background: #111; color: var(--gold); }
        .sel-planilla { width: 100%; border: none; background: transparent; color: white; cursor: pointer; font-weight: bold; }
        .cell-12 { background-color: var(--color-12); }
        .cell-F { background-color: var(--color-F); color: #000; }
        .cell-VAC { background-color: var(--color-VAC); }
        .cell-ART { background-color: var(--color-ART); }
        .cell-FE { background-color: var(--color-FE); }
        input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 6px; }
        .btn { border-radius: 6px; padding: 10px 20px; cursor: pointer; font-weight: 700; border: none; text-transform: uppercase; }
        .btn-gold { background: var(--gold); color: #000; }
    </style>
</head>
<body>
<div class="header"><h1 class="logo">ORDO <span>KLAR</span></h1></div>
<div class="nav">
    <button class="nav-btn active" onclick="showTab('planilla')">Planilla Mensual</button>
    <button class="nav-btn" onclick="showTab('personal')">Gestión de Personal</button>
    <button class="nav-btn" onclick="showTab('puestos')">La Diaria / Puestos</button>
</div>
<div class="container">
    <div id="planilla" class="section active">
        <div class="tabla-scroll">
            <table><thead id="h-mensual"></thead><tbody id="b-mensual"></tbody></table>
        </div>
    </div>
    <div id="personal" class="section">
        <div class="card">
            <h3>Nuevo Registro</h3>
            <input type="text" id="p_legajo" placeholder="Legajo">
            <input type="text" id="p_apellido" placeholder="Apellido">
            <input type="text" id="p_nombre" placeholder="Nombre">
            <button class="btn btn-gold" id="btn_save_p" onclick="savePersonal()">+ Confirmar</button>
        </div>
        <table id="lista-personal"></table>
    </div>
    <div id="puestos" class="section">
        <div class="card">
            <input type="date" id="fecha_diaria" onchange="renderPuestos()">
            <button class="btn btn-gold" onclick="window.print()">Imprimir Diaria</button>
        </div>
        <div id="grid-puestos" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:20px;"></div>
    </div>
</div>
<script>
    let personal = [], novedades = [], puestos = [];
    let editId = null;

    async function loadData() {
        const [resP, resN, resT] = await Promise.all([
            fetch('/api/personal').then(r => r.json()),
            fetch('/api/novedades').then(r => r.json()),
            fetch('/api/puestos').then(r => r.json())
        ]);
        personal = resP; novedades = resN; puestos = resT;
        renderPersonal(); renderPlanilla(); renderPuestos();
    }

    function showTab(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        event.currentTarget.classList.add('active');
    }

    function renderPlanilla() {
        const hoy = new Date(), mes = hoy.getMonth(), anio = hoy.getFullYear();
        const totalDias = new Date(anio, mes + 1, 0).getDate();
        let h = '<tr><th>PERSONAL</th>';
        for(let i=1; i<=totalDias; i++) h += `<th class="dia-numero">${i}</th>`;
        document.getElementById('h-mensual').innerHTML = h + '</tr>';
        document.getElementById('b-mensual').innerHTML = personal.filter(p => p.estado_p === 'ACTIVO').map(p => {
            let celdas = "";
            for(let i=1; i<=totalDias; i++) {
                const f_str = `${anio}-${String(mes+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const n = novedades.find(x => x.personal_id == p.id && x.fecha == f_str);
                const e = n ? n.estado : 'F';
                celdas += `<td class="cell-${e}"><select class="sel-planilla" onchange="updateNov(${p.id},'${f_str}',this.value)">
                    <option value="12" ${e=='12'?'selected':''}>12</option>
                    <option value="F" ${e=='F'?'selected':''}>F</option>
                    <option value="VAC" ${e=='VAC'?'selected':''}>V</option>
                    <option value="ART" ${e=='ART'?'selected':''}>A</option>
                </select></td>`;
            }
            return `<tr><td class="col-personal">${p.apellido}</td>${celdas}</tr>`;
        }).join('');
    }

    async function updateNov(p_id, fecha, estado) {
        await fetch('/api/actualizar_novedad', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado}) });
        loadData();
    }

    async function savePersonal() {
        const d = { legajo: document.getElementById('p_legajo').value, apellido: document.getElementById('p_apellido').value, nombre: document.getElementById('p_nombre').value, estado_p: 'ACTIVO' };
        await fetch(editId ? `/api/personal/${editId}` : '/api/personal', { method: editId?'PUT':'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d) });
        editId = null; loadData();
    }

    function renderPersonal() {
        document.getElementById('lista-personal').innerHTML = personal.map(p => `<tr><td>${p.legajo}</td><td>${p.apellido}</td><td><button onclick="deleteP(${p.id})">X</button></td></tr>`).join('');
    }

    function renderPuestos() {
        document.getElementById('grid-puestos').innerHTML = puestos.map(pst => `<div class="card"><b>${pst.nombre}</b><br>Plazas: ${pst.cantidad}</div>`).join('');
    }

    window.onload = loadData;
</script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
