import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos en /tmp para Render
DB_PATH = '/tmp/ordoklar_final_v6.db'

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

# --- APIs PERSONAL (CON EDITAR) ---
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

@app.route('/api/puestos/<int:id>', methods=['DELETE', 'PUT'])
def edit_del_puesto(id):
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM puestos WHERE id = ?", (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE puestos SET nombre = ?, cantidad = ? WHERE id = ?", (d['nombre'], d['cantidad'], id))
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

# --- INTERFAZ ---
HTML_UI = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; }
        body { background: var(--bg); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; overflow-x: hidden; }
        .nav { background: var(--card); display: flex; justify-content: center; border-bottom: 1px solid var(--gold); }
        .nav button { background: none; border: none; color: #777; padding: 15px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 10px; }
        .nav button.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 10px; width: 100vw; box-sizing: border-box; }
        .section { display: none; }
        .active { display: block; }
        .card { background: var(--card); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        
        /* Planilla Compacta */
        table { width: 100%; border-collapse: collapse; font-size: 9px; table-layout: fixed; }
        th, td { border: 1px solid #222; text-align: center; height: 30px; overflow: hidden; }
        th { background: #111; color: var(--gold); }
        .col-fixed { text-align: left; color: var(--gold); width: 80px; font-weight: bold; padding-left: 3px; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .col-hs { background: #1a1a1a; color: var(--gold); font-weight: bold; width: 30px; border-left: 1px solid var(--gold); font-size: 10px; }
        
        select { background: transparent; color: #fff; border: none; font-weight: bold; cursor: pointer; width: 100%; height: 100%; font-size: 9px; outline: none; appearance: none; text-align-last: center; }
        .st-12 { background: #1b5e20 !important; } 
        .st-F { background: #333 !important; }    
        .st-VAC { background: #01579b !important; } 
        .st-ART { background: #b71c1c !important; } 

        .btn-action { background: none; border: 1px solid #444; color: #fff; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 9px; }
        .btn-edit { border-color: var(--gold); color: var(--gold); }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 5px; margin: 2px; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <div style="text-align:center; padding:10px; font-size:18px; letter-spacing:5px; border-bottom:1px solid #222;">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="btn-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="btn-per" onclick="tab('per')">Personal</button>
        <button id="btn-pue" onclick="tab('pue')">Puestos</button>
    </div>

    <div class="container">
        <div id="sec-pla" class="section active">
            <table><thead id="h-pla"></thead><tbody id="b-pla"></tbody></table>
        </div>

        <div id="sec-per" class="section">
            <div class="card">
                <input type="text" id="p_leg" placeholder="Legajo">
                <input type="text" id="p_ape" placeholder="Apellido">
                <input type="text" id="p_nom" placeholder="Nombre">
                <button onclick="addPer()" style="background:var(--gold); border:none; padding:8px; font-weight:bold; cursor:pointer;">AÑADIR</button>
            </div>
            <table style="table-layout: auto; font-size: 12px;">
                <thead><tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acciones</th></tr></thead>
                <tbody id="l-per"></tbody>
            </table>
        </div>

        <div id="sec-pue" class="section">
            <div class="card">
                <input type="text" id="t_nom" placeholder="Puesto">
                <input type="number" id="t_can" placeholder="Plazas">
                <button onclick="addPue()" style="background:var(--gold); border:none; padding:8px; font-weight:bold; cursor:pointer;">CREAR</button>
            </div>
            <div id="grid-pue" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap:10px;"></div>
        </div>
    </div>

    <script>
        function tab(t) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('sec-'+t).classList.add('active');
            document.getElementById('btn-'+t).classList.add('active');
        }

        async function refresh() {
            const [p, n, t] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);

            // Personal con BOTÓN EDITAR
            document.getElementById('l-per').innerHTML = p.map(x => `<tr>
                <td>${x.legajo}</td><td>${x.apellido.toUpperCase()}, ${x.nombre}</td>
                <td>
                    <button onclick="editPer(${x.id}, '${x.nombre}', '${x.apellido}', '${x.legajo}')" class="btn-action btn-edit">EDITAR</button>
                    <button onclick="delP(${x.id})" class="btn-action">X</button>
                </td></tr>`).join('');

            // Planilla SIN Scroll y con HS
            const now = new Date();
            const dias = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
            let th = '<tr><th class="col-fixed">Personal</th>';
            for(let i=1; i<=dias; i++) th += `<th>${i}</th>`;
            th += '<th class="col-hs">HS</th></tr>';
            document.getElementById('h-pla').innerHTML = th;

            document.getElementById('b-pla').innerHTML = p.map(per => {
                let row = `<td class="col-fixed">${per.apellido.toUpperCase()}</td>`;
                let totalHs = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const nov = n.find(x => x.personal_id == per.id && x.fecha == f);
                    const est = nov ? nov.estado : 'F';
                    if(est === '12') totalHs += 12;
                    row += `<td class="st-${est}"><select onchange="updNov(${per.id},'${f}',this.value)">
                        <option value="12" ${est=='12'?'selected':''}>12</option>
                        <option value="F" ${est=='F'?'selected':''}>F</option>
                        <option value="VAC" ${est=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${est=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                row += `<td class="col-hs">${totalHs}</td>`;
                return `<tr>${row}</tr>`;
            }).join('');

            document.getElementById('grid-pue').innerHTML = t.map(pst => {
                let s = "";
                for(let i=0; i<pst.cantidad; i++) s += `<select style="width:100%; background:#000; color:#ccc; border:1px solid #222; margin-bottom:2px; font-size:9px;"><option>VACANTE</option>${p.map(pe => `<option>${pe.apellido}</option>`).join('')}</select>`;
                return `<div class="card"><div style="display:flex; justify-content:space-between; font-size:10px; color:var(--gold); font-weight:bold; margin-bottom:5px;"><span>${pst.nombre.toUpperCase()}</span><button onclick="delPue(${pst.id})" style="background:none; border:none; color:red; cursor:pointer;">X</button></div>${s}</div>`;
            }).join('');
        }

        async function editPer(id, nom, ape, leg) {
            const nApe = prompt("Apellido:", ape);
            const nNom = prompt("Nombre:", nom);
            const nLeg = prompt("Legajo:", leg);
            if(nApe && nNom) {
                await fetch('/api/personal/'+id, { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({nombre: nNom, apellido: nApe, legajo: nLeg}) });
                refresh();
            }
        }

        async function delPue(id) { await fetch('/api/puestos/'+id, { method: 'DELETE' }); refresh(); }
        async function addPer() { await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({legajo:document.getElementById('p_leg').value, apellido:document.getElementById('p_ape').value, nombre:document.getElementById('p_nom').value})}); refresh(); }
        async function addPue() { await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({nombre:document.getElementById('t_nom').value, cantidad:document.getElementById('t_can').value})}); refresh(); }
        async function updNov(p_id, fecha, estado) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado})}); refresh(); }
        async function delP(id) { if(confirm("¿Eliminar?")) { await fetch('/api/personal/'+id, {method:'DELETE'}); refresh(); } }

        window.onload = refresh;
    </script>
</body>
</html>
