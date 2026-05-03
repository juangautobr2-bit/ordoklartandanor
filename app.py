from flask import Flask, render_template_string, request, jsonify
import sqlite3
import os

app = Flask(__name__)
DB_PATH = 'ordoklar.db'

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
    # Tabla de Puestos (Estructura)
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        cantidad INTEGER
    )''')
    # Tabla de Novedades (Planilla Mensual)
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
            conn.execute("INSERT INTO personal (nombre, apellido, legajo, estado_p) VALUES (?, ?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo'], d['estado_p']))
            conn.commit()
        except: return jsonify({"error": "Legajo duplicado"}), 400
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
    conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                    ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                 (d['p_id'], d['fecha'], d['estado']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# --- RUTA PRINCIPAL (FRONTEND) ---

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- FRONTEND UI (HTML/CSS/JS) ---

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
        
        body { background: var(--black); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; line-height: 1.6; }
        
        /* HEADER & NAV */
        .header { background: #000; border-bottom: 1px solid var(--gold); padding: 15px; text-align: center; }
        .logo { letter-spacing: 5px; font-weight: 200; font-size: 22px; margin: 0; }
        .logo span { color: var(--gold); font-weight: 800; }

        .nav { background: var(--dark-gray); display: flex; justify-content: center; border-bottom: 1px solid #222; position: sticky; top: 0; z-index: 1000; }
        .nav-btn { background: none; border: none; color: var(--text-dim); padding: 15px 25px; cursor: pointer; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; transition: 0.3s; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }

        .container { padding: 20px; max-width: 1800px; margin: 0 auto; }
        .section { display: none; animation: fadeIn 0.4s ease; }
        .section.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

        /* COMPONENTES */
        .card { background: var(--dark-gray); border-radius: 12px; border: 1px solid #222; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .leyenda-bar { display: flex; gap: 15px; margin-bottom: 15px; background: var(--dark-gray); padding: 12px; border-radius: 8px; border: 1px solid #222; flex-wrap: wrap; }
        .leyenda-item { display: flex; align-items: center; gap: 8px; font-size: 10px; font-weight: bold; }
        .box-ref { width: 12px; height: 12px; border-radius: 2px; }

        /* TABLA PLANILLA */
        .tabla-scroll { overflow-x: auto; background: var(--dark-gray); border-radius: 12px; border: 1px solid #222; }
        .t-planilla { table-layout: fixed; border-collapse: collapse; width: 100%; }
        .t-planilla th, .t-planilla td { border: 1px solid #222; text-align: center; }

        .dia-nombre { height: 180px; vertical-align: top; padding-top: 10px; font-size: 10px; font-weight: 800; color: #666; background: #080808; line-height: 1.2; }
        .dia-numero { background: #111; color: var(--gold); font-size: 12px; height: 30px; font-weight: bold; }
        .col-personal { width: 180px; text-align: left; padding-left: 12px !important; font-size: 11px; font-weight: bold; background: #0a0a0a !important; color: var(--gold); }
        .col-legajo { width: 60px; background: #0a0a0a !important; border-right: 2px solid var(--gold) !important; font-weight: 900; font-size: 11px; }
        
        .sel-planilla { width: 100%; height: 32px; border: none; background: transparent; color: white; text-align-last: center; font-weight: 800; cursor: pointer; font-size: 10px; }

        /* ESTADOS COLORES */
        .cell-12 { background-color: var(--color-12) !important; }
        .cell-F { background-color: var(--color-F) !important; color: #000 !important; }
        .cell-VAC { background-color: var(--color-VAC) !important; }
        .cell-ART { background-color: var(--color-ART) !important; }
        .cell-FE { background-color: var(--color-FE) !important; }

        /* FORMULARIOS */
        input, select { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 6px; outline: none; }
        input:focus { border-color: var(--gold); }
        .btn { border-radius: 6px; padding: 10px 20px; cursor: pointer; font-weight: 700; font-size: 11px; text-transform: uppercase; border: none; transition: 0.3s; }
        .btn-gold { background: var(--gold); color: #000; }
        .btn-outline { background: transparent; border: 1px solid #444; color: var(--text-dim); }
        .btn-outline:hover { border-color: var(--gold); color: var(--gold); }

        /* SWITCH */
        .switch { position: relative; display: inline-block; width: 40px; height: 20px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #333; transition: .4s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: var(--gold); }
        input:checked + .slider:before { transform: translateX(20px); }

        @media print {
            .nav, .header, .btn, .card:has(details), .nav-btn { display: none !important; }
            body { background: #fff; color: #000; }
            .container { max-width: 100%; padding: 0; }
            .card { border: 1px solid #000 !important; background: #fff !important; color: #000 !important; box-shadow: none !important; page-break-inside: avoid; }
            .card b { color: #000 !important; }
            select { appearance: none; border: none !important; color: #000 !important; }
            .section { display: block !important; }
        }
    </style>
</head>
<body>

<div class="header">
    <h1 class="logo">ORDO <span>KLAR</span></h1>
</div>

<div class="nav">
    <button class="nav-btn active" onclick="showTab('planilla')">Planilla Mensual</button>
    <button class="nav-btn" onclick="showTab('personal')">Gestión de Personal</button>
    <button class="nav-btn" onclick="showTab('puestos')">La Diaria / Puestos</button>
</div>

<div class="container">
    
    <!-- SECCION PLANILLA -->
    <div id="planilla" class="section active">
        <div class="leyenda-bar">
            <div class="leyenda-item"><div class="box-ref" style="background:var(--color-12)"></div> 12: TRABAJA</div>
            <div class="leyenda-item"><div class="box-ref" style="background:var(--color-F)"></div> F: FRANCO</div>
            <div class="leyenda-item"><div class="box-ref" style="background:var(--color-VAC)"></div> V: VACACIONES</div>
            <div class="leyenda-item"><div class="box-ref" style="background:var(--color-ART)"></div> A: ART</div>
            <div class="leyenda-item"><div class="box-ref" style="background:var(--color-FE)"></div> FE: FRANCO ESCUCHA</div>
        </div>
        <div class="tabla-scroll">
            <table class="t-planilla">
                <thead id="h-mensual"></thead>
                <tbody id="b-mensual"></tbody>
            </table>
        </div>
    </div>

    <!-- SECCION PERSONAL -->
    <div id="personal" class="section">
        <div class="card">
            <h3 style="color:var(--gold); font-size:12px; text-transform:uppercase; margin-bottom:15px;">Nuevo Registro de Personal</h3>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:15px; align-items:end;">
                <div><label style="font-size:10px; color:var(--text-dim)">LEGAJO</label><br><input type="text" id="p_legajo" style="width:100%"></div>
                <div><label style="font-size:10px; color:var(--text-dim)">APELLIDO</label><br><input type="text" id="p_apellido" style="width:100%"></div>
                <div><label style="font-size:10px; color:var(--text-dim)">NOMBRES</label><br><input type="text" id="p_nombre" style="width:100%"></div>
                <button class="btn btn-gold" id="btn_save_p" onclick="savePersonal()">+ Confirmar</button>
            </div>
        </div>
        <table style="width:100%; border-collapse: separate; border-spacing: 0 8px;">
            <tbody id="lista-personal"></tbody>
        </table>
    </div>

    <!-- SECCION PUESTOS / DIARIA -->
    <div id="puestos" class="section">
        <div class="card" style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h3 style="color:var(--gold); font-size:14px; margin:0;">INFORME DIARIO DE SERVICIO</h3>
                <input type="date" id="fecha_diaria" onchange="renderPuestos()" style="margin-top:10px; border:1px solid var(--gold); padding:5px 15px;">
            </div>
            <button class="btn btn-outline" onclick="window.print()" style="border-color:var(--success); color:var(--success)">⎙ Imprimir La Diaria</button>
        </div>

        <div class="card" style="border-style: dashed; background: transparent;">
            <details>
                <summary style="cursor:pointer; color:var(--gold); font-size:11px;">+ CONFIGURAR NUEVO OBJETIVO / PUESTO</summary>
                <div style="display:flex; gap:10px; margin-top:15px;">
                    <input type="text" id="pst_nombre" placeholder="Nombre Puesto" style="flex:2">
                    <input type="number" id="pst_cant" placeholder="Plazas" style="flex:0.5">
                    <button class="btn btn-gold" onclick="savePuesto()">Crear</button>
                </div>
            </details>
        </div>

        <div id="grid-puestos" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap:20px;"></div>
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

    // PLANILLA
    function renderPlanilla() {
        const hoy = new Date(), mes = hoy.getMonth(), anio = hoy.getFullYear();
        const totalDias = new Date(anio, mes + 1, 0).getDate();
        const diasNombres = ["DOMINGO", "LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO"];

        let h1 = `<tr><th class="col-personal" rowspan="3">PERSONAL</th><th class="col-legajo" rowspan="3">LEGAJO</th>`;
        for(let s=1; s<=4; s++) h1 += `<th colspan="${s<4?7:totalDias-21}" style="background:#000; color:var(--gold); font-size:9px;">SEMANA ${s}</th>`;
        h1 += `<th rowspan="3" style="width:50px; background:#000; font-size:10px;">HS</th></tr><tr>`;

        let h2 = "", h3 = "<tr>";
        for(let i=1; i<=totalDias; i++) {
            const f = new Date(anio, mes, i);
            h2 += `<th class="dia-nombre">${diasNombres[f.getDay()].split('').join('<br>')}</th>`;
            h3 += `<th class="dia-numero">${i}</th>`;
        }
        document.getElementById('h-mensual').innerHTML = h1 + h2 + "</tr>" + h3 + "</tr>";

        document.getElementById('b-mensual').innerHTML = personal.filter(p => p.estado_p === 'ACTIVO').map(p => {
            let hs = 0, celdas = "";
            for(let i=1; i<=totalDias; i++) {
                const f_str = `${anio}-${String(mes+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const n = novedades.find(x => x.personal_id == p.id && x.fecha == f_str);
                const e = n ? n.estado : 'F';
                if(e === '12') hs += 12;
                celdas += `<td class="cell-${e}"><select class="sel-planilla" onchange="updateNov(${p.id},'${f_str}',this.value)">
                    <option value="12" ${e=='12'?'selected':''}>12</option>
                    <option value="F" ${e=='F'?'selected':''}>F</option>
                    <option value="VAC" ${e=='VAC'?'selected':''}>V</option>
                    <option value="ART" ${e=='ART'?'selected':''}>A</option>
                    <option value="FE" ${e=='FE'?'selected':''}>FE</option>
                </select></td>`;
            }
            return `<tr><td class="col-personal">${p.apellido.toUpperCase()} ${p.nombre[0]}.</td><td class="col-legajo">${p.legajo}</td>${celdas}<td style="background:#000; font-weight:bold; color:var(--gold)">${hs}</td></tr>`;
        }).join('');
    }

    async function updateNov(p_id, fecha, estado) {
        await fetch('/api/actualizar_novedad', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado}) });
        loadData();
    }

    // PERSONAL
    async function savePersonal() {
        const d = { legajo: document.getElementById('p_legajo').value, apellido: document.getElementById('p_apellido').value, nombre: document.getElementById('p_nombre').value, estado_p: 'ACTIVO' };
        await fetch(editId ? `/api/personal/${editId}` : '/api/personal', { method: editId?'PUT':'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d) });
        editId = null; document.getElementById('btn_save_p').innerText = '+ Confirmar';
        document.querySelectorAll('#personal input').forEach(i => i.value = '');
        loadData();
    }

    function renderPersonal() {
        document.getElementById('lista-personal').innerHTML = personal.map(p => `
            <tr style="background:var(--light-gray);">
                <td style="color:var(--gold); font-weight:800; padding:15px; width:80px; border-radius:8px 0 0 8px;">${p.legajo}</td>
                <td style="font-weight:bold;">${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td style="text-align:center">
                    <label class="switch"><input type="checkbox" ${p.estado_p === 'ACTIVO' ? 'checked' : ''} onchange="toggleStatus(${p.id}, '${p.estado_p}')"><span class="slider"></span></label>
                </td>
                <td style="text-align:right; padding-right:15px; border-radius:0 8px 8px 0;">
                    <button class="btn btn-outline" onclick='editP(${JSON.stringify(p)})'>EDITAR</button>
                    <button class="btn btn-outline" style="border-color:var(--danger); color:var(--danger); margin-left:5px;" onclick="deletePersonal(${p.id})">X</button>
                </td>
            </tr>
        `).join('');
    }

    async function toggleStatus(id, current) {
        const p = personal.find(x => x.id === id);
        await fetch(`/api/personal/${id}`, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({...p, estado_p: current==='ACTIVO'?'PASIVO':'ACTIVO'}) });
        loadData();
    }

    async function deletePersonal(id) { if(confirm("¿Eliminar registro?")) { await fetch(`/api/personal/${id}`, {method:'DELETE'}); loadData(); } }
    function editP(p) { editId = p.id; document.getElementById('p_legajo').value = p.legajo; document.getElementById('p_apellido').value = p.apellido; document.getElementById('p_nombre').value = p.nombre; document.getElementById('btn_save_p').innerText = 'Actualizar'; }

    // PUESTOS
    async function savePuesto() {
        const d = { nombre: document.getElementById('pst_nombre').value, cantidad: document.getElementById('pst_cant').value };
        await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d) });
        loadData();
    }

    function renderPuestos() {
        const grid = document.getElementById('grid-puestos');
        grid.innerHTML = puestos.map(pst => {
            let selects = "";
            for(let i=0; i<pst.cantidad; i++) {
                selects += `<select style="width:100%; margin-bottom:8px; font-size:11px;">
                    <option value="">-- SELECCIONAR PERSONAL --</option>
                    ${personal.filter(p => p.estado_p==='ACTIVO').map(p => `<option>${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('')}
                </select>`;
            }
            return `<div class="card" style="border-top: 3px solid var(--gold);">
                <div style="display:flex; justify-content:space-between; margin-bottom:15px;">
                    <b style="color:var(--gold); font-size:12px;">${pst.nombre.toUpperCase()}</b>
                    <button onclick="deletePuesto(${pst.id})" style="background:none; border:none; color:var(--danger); cursor:pointer;">✕</button>
                </div>
                ${selects}
                <textarea placeholder="Novedades del puesto..." style="width:100%; background:transparent; border:none; border-top:1px solid #222; padding-top:10px; color:#666; font-size:10px; font-family:inherit; resize:none;"></textarea>
            </div>`;
        }).join('');
    }

    async function deletePuesto(id) { if(confirm("¿Eliminar puesto?")) { await fetch(`/api/puestos/${id}`, {method:'DELETE'}); loadData(); } }

    window.onload = () => {
        document.getElementById('fecha_diaria').value = new Date().toISOString().split('T')[0];
        loadData();
    };
</script>
</body>
</html>
'''

if __name__ == '__main__':
    # Render asigna un puerto automáticamente en la variable PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)