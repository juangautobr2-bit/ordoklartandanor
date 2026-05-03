import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos en /tmp para Render
DB_PATH = '/tmp/ordoklar_final.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # CREACIÓN FORZADA DE TODAS LAS TABLAS
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs ---
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
        conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def del_p(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"s": "ok"})

# --- INTERFAZ COMPLETA ---
HTML_UI = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; }
        body { background: var(--bg); color: #fff; font-family: sans-serif; margin: 0; padding: 0; }
        .nav { background: var(--card); display: flex; justify-content: center; border-bottom: 1px solid var(--gold); }
        .nav button { background: none; border: none; color: #777; padding: 20px; cursor: pointer; font-weight: bold; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
        .container { padding: 20px; }
        .section { display: none; }
        .active { display: block; }
        .card { background: var(--card); border: 1px solid #333; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 8px; margin: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }
        th, td { border: 1px solid #333; padding: 5px; text-align: center; }
        .col-fixed { text-align: left; color: var(--gold); min-width: 120px; font-weight: bold; }
        select { background: transparent; color: #fff; border: none; font-weight: bold; cursor: pointer; }
        .st-12 { background: #1b5e20; } .st-F { background: #444; } .st-VAC { background: #01579b; } .st-ART { background: #ef6c00; }
    </style>
</head>
<body>
    <div style="text-align:center; padding:15px; font-size:24px; letter-spacing:8px; border-bottom:1px solid #222;">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="btn-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="btn-per" onclick="tab('per')">Personal</button>
        <button id="btn-pue" onclick="tab('pue')">Puestos</button>
    </div>

    <div class="container">
        <!-- PLANILLA -->
        <div id="sec-pla" class="section active">
            <h3 style="color:var(--gold)">ASISTENCIA MENSUAL</h3>
            <div style="overflow-x:auto;">
                <table><thead id="h-pla"></thead><tbody id="b-pla"></tbody></table>
            </div>
        </div>

        <!-- PERSONAL -->
        <div id="sec-per" class="section">
            <div class="card">
                <input type="text" id="p_leg" placeholder="Legajo">
                <input type="text" id="p_ape" placeholder="Apellido">
                <input type="text" id="p_nom" placeholder="Nombre">
                <button onclick="addPer()" style="background:var(--gold); border:none; padding:8px 15px; cursor:pointer;">AÑADIR</button>
            </div>
            <table><thead><tr><th>Legajo</th><th>Nombre</th><th></th></tr></thead><tbody id="l-per"></tbody></table>
        </div>

        <!-- PUESTOS -->
        <div id="sec-pue" class="section">
            <div class="card">
                <input type="text" id="t_nom" placeholder="Nombre Puesto">
                <input type="number" id="t_can" placeholder="Cantidad Plazas">
                <button onclick="addPue()" style="background:var(--gold); border:none; padding:8px 15px; cursor:pointer;">CREAR</button>
            </div>
            <div id="grid-pue" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap:15px;"></div>
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

            // Render Personal
            document.getElementById('l-per').innerHTML = p.map(x => `<tr><td>${x.legajo}</td><td>${x.apellido}, ${x.nombre}</td><td><button onclick="delP(${x.id})">X</button></td></tr>`).join('');

            // Render Planilla
            const dias = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate();
            let th = '<tr><th class="col-fixed">Personal</th>';
            for(let i=1; i<=dias; i++) th += `<th>${i}</th>`;
            document.getElementById('h-pla').innerHTML = th + '</tr>';

            document.getElementById('b-pla').innerHTML = p.map(per => {
                let row = `<td class="col-fixed">${per.apellido.toUpperCase()}</td>`;
                for(let i=1; i<=dias; i++) {
                    const f = `2026-05-${String(i).padStart(2,'0')}`; // Forzado a Mayo por el ejemplo
                    const nov = n.find(x => x.personal_id == per.id && x.fecha == f);
                    const est = nov ? nov.estado : 'F';
                    row += `<td class="st-${est}"><select onchange="updNov(${per.id},'${f}',this.value)">
                        <option value="12" ${est=='12'?'selected':''}>12</option>
                        <option value="F" ${est=='F'?'selected':''}>F</option>
                        <option value="VAC" ${est=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${est=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${row}</tr>`;
            }).join('');

            // Render Puestos
            document.getElementById('grid-pue').innerHTML = t.map(pst => {
                let selects = "";
                for(let i=0; i<pst.cantidad; i++) selects += `<select style="width:100%; background:#000; color:#fff; margin-bottom:5px; border:1px solid #333; padding:5px;"><option>-- VACANTE --</option>${p.map(pe => `<option>${pe.apellido}</option>`).join('')}</select>`;
                return `<div class="card"><b style="color:var(--gold)">${pst.nombre.toUpperCase()}</b><br><br>${selects}</div>`;
            }).join('');
        }

        async function addPer() {
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({legajo:document.getElementById('p_leg').value, apellido:document.getElementById('p_ape').value, nombre:document.getElementById('p_nom').value})});
            refresh();
        }

        async function addPue() {
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({nombre:document.getElementById('t_nom').value, cantidad:document.getElementById('t_can').value})});
            refresh();
        }

        async function updNov(p_id, fecha, estado) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({p_id, fecha, estado})});
            refresh();
        }

        async function delP(id) { await fetch('/api/personal/'+id, {method:'DELETE'}); refresh(); }

        window.onload = refresh;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
