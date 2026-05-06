import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v60_ultra_key'

# --- CONFIGURACIÓN DE PERSISTENCIA ÓPTIMA ---
# Buscamos la ruta del script para guardar la DB en el mismo lugar siempre
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v60_FINAL.db")

USER_ADMIN = "admin"
PASS_ADMIN = "admin123"

def get_db_connection():
    # Establecemos una conexión con mayor tiempo de espera para evitar bloqueos
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        c.execute('CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT)')
        conn.commit()

init_db()

# --- AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == USER_ADMIN and request.form.get('password') == PASS_ADMIN:
            session['logged_in'] = True
            session.permanent = True # Mantiene la sesión activa
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

# --- API CON PERSISTENCIA GARANTIZADA ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    if not session.get('logged_in'): return jsonify({"error": "No auth"}), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo']))
            conn.commit() # ESCRITURA FÍSICA EN DISCO
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    if not session.get('logged_in'): return jsonify({"error": "No auth"}), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", 
                         (d['nombre'], d['horario'], d['dotacion']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
    return jsonify(res)

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    if not session.get('logged_in'): return jsonify({"error": "No auth"}), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", 
                         (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    return jsonify(res)

@app.route('/api/archivos', methods=['GET', 'POST', 'DELETE'])
def handle_archivos():
    if not session.get('logged_in'): return jsonify({"error": "No auth"}), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO archivos (nombre, fecha) VALUES (?, ?)", (d['nombre'], d['fecha']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM archivos WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM archivos ORDER BY id DESC").fetchall()]
    return jsonify(res)

# --- INTERFAZ HTML (v60) ---
HTML_LOGIN = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>Login | ORDO KLAR</title>
    <style>
        body { background: #000; color: #eee; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #111; padding: 40px; border-radius: 10px; border: 1px solid #D4AF37; width: 300px; text-align: center; }
        h1 { color: #D4AF37; letter-spacing: 5px; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #000; border: 1px solid #333; color: #fff; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #D4AF37; border: none; font-weight: bold; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>ORDO KLAR</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Usuario" required autofocus>
            <input type="password" name="password" placeholder="Contraseña" required>
            <button type="submit">INGRESAR</button>
        </form>
        {% if error %}<p style="color:red; font-size:12px">{{ error }}</p>{% endif %}
    </div>
</body>
</html>
'''

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>ORDO KLAR v60</title>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); position: relative; }
        .logout { position: absolute; right: 20px; top: 20px; color: #777; text-decoration: none; font-size: 11px; border: 1px solid #333; padding: 5px; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; font-size: 11px; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
        .container { padding: 20px; }
        .section { display: none; }
        .active-section { display: block; }
        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; font-size: 10px; background: #000; }
        th, td { border: 1px solid #333; text-align: center; padding: 6px 2px; }
        .col-name { text-align: left; min-width: 180px; padding-left: 10px; color: var(--gold); }
        .st-12 { background: #1b4332 !important; }
        .st-F { background: #ff8c00 !important; color: #000; }
        .st-ART { background: #6a0dad !important; }
        .st-VAC { background: #0000ff !important; }
        .st-FE { background: #ff0000 !important; }
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-radius: 5px; border-top: 4px solid var(--gold); }
        .slot { background: #111; padding: 5px; margin-top: 5px; display: flex; justify-content: space-between; align-items: center; }
        .slot select { background: #000; color: #fff; border: 1px solid #444; width: 75%; }
        .slot-fixed { display: none; font-weight: bold; }
        .global-fixed .slot select { display: none; }
        .global-fixed .slot-fixed { display: block; }
        #print-header { display: none; text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); }
        @media print { .no-print { display: none !important; } #print-header { display: block !important; } body { background: white; color: black; } table { color: black; border: 1px solid black; } th, td { border: 1px solid black; } }
    </style>
</head>
<body>
    <div id="print-header"><h1 id="print-title">ORDO KLAR</h1></div>
    <div class="header no-print">
        <h1>ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <a href="/logout" class="logout">CERRAR SESIÓN</a>
    </div>
    <nav class="no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>
    <div class="container">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box no-print" style="display:flex; gap:15px">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="printPlanilla()">🖨️ Imprimir Planilla</button>
            </div>
            <div style="overflow-x: auto;">
                <table id="full-planilla"><thead id="h-pla"></thead><tbody id="b-pla"></tbody><tfoot id="f-pla"></tfoot></table>
            </div>
        </div>
        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="box no-print" style="display:flex; flex-wrap:wrap; gap:10px; align-items:center">
                <input type="text" id="p-nom" placeholder="Objetivo">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-dot" placeholder="Cant.">
                <button class="btn" onclick="addPuesto()">+ Crear Puesto</button>
                <div style="border-left:1px solid #333; padding-left:15px; margin-left:15px; display:flex; gap:10px">
                    <button class="btn" style="background:#1b4332; color:white" onclick="toggleGlobalFix(true)">🔒 FIJAR GUARDIAS</button>
                    <button class="btn" style="background:#444; color:white" onclick="toggleGlobalFix(false)">🔓 EDITAR</button>
                    <button class="btn" style="background:#fff" onclick="printPue()">🖨️ Imprimir</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>
        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">Cargar Agente</button>
            </div>
            <div class="box">
                <table style="width:100%; text-align:left"><thead style="color:var(--gold)"><tr><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acción</th></tr></thead><tbody id="list-per"></tbody></table>
            </div>
        </div>
        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div class="box"><h3>HISTORIAL</h3><div id="historial-list"></div></div>
        </div>
    </div>
    <script>
        const mesesNombres = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
        function tab(t) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active-section');
            document.getElementById('n-'+t).classList.add('active');
            render();
        }
        async function render() {
            const [per, pue, nov, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()), fetch('/api/puestos').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()), fetch('/api/archivos').then(r => r.json())
            ]);
            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();
            let h = `<tr><th class="col-name">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th style="background:var(--gold); color:black">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;
            let b = ""; let sumHs = new Array(dias).fill(0); let cntPer = new Array(dias).fill(0);
            per.forEach(p => {
                let rowHs = 0; let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    if(d.estado == '12') { rowHs += 12; sumHs[i-1] += 12; cntPer[i-1]++; }
                    r += `<td class="st-${d.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                r += `<td style="font-weight:bold; color:var(--gold)">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;
            document.getElementById('f-pla').innerHTML = `<tr><td class="col-name">PERSONAL ACTIVO</td>${cntPer.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>`;
            const opts = `<option value="">-- Seleccionar --</option>` + per.map(p => `<option>${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let s = ""; for(let i=1; i<=x.dotacion; i++) s += `<div class="slot"><select>${opts}</select><span class="slot-fixed"></span></div>`;
                return `<div class="card-pue" id="pue-${x.id}"><div style="float:right" class="no-print"><button onclick="delPue(${x.id})" style="background:none; border:none; color:red; cursor:pointer">✖</button></div><h3>${x.nombre}</h3><small>${x.horario}</small>${s}</div>`;
            }).join('');
            document.getElementById('historial-list').innerHTML = arc.map(x => `<div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333"><span>📄 ${x.nombre} <small>(${x.fecha})</small></span><button class="btn" style="background:red; color:white; padding:5px" onclick="delArc(${x.id})">X</button></div>`).join('');
            document.getElementById('list-per').innerHTML = per.map(p => `<tr><td>${p.legajo}</td><td>${p.apellido}</td><td>${p.nombre}</td><td><button onclick="delPer(${p.id})" style="color:red; background:none; border:none; cursor:pointer">Baja</button></td></tr>`).join('');
        }
        function toggleGlobalFix(fix) {
            const grid = document.getElementById('grid-pue');
            if(fix) {
                grid.classList.add('global-fixed');
                document.querySelectorAll('.slot').forEach(slot => {
                    const sel = slot.querySelector('select');
                    slot.querySelector('.slot-fixed').innerText = sel.value || "---";
                });
            } else grid.classList.remove('global-fixed');
        }
        async function cycleSt(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC", "FE"];
            let nxt = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:nxt})});
            render();
        }
        async function printPlanilla() {
            const tit = `PLANILLA ${mesesNombres[document.getElementById('m-sel').value - 1]} ${document.getElementById('a-sel').value}`;
            document.getElementById('print-title').innerText = tit;
            await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: tit, fecha: new Date().toLocaleString()})});
            window.print();
        }
        async function printPue() {
            const tit = `GUARDIAS - ${new Date().toLocaleDateString()}`;
            document.getElementById('print-title').innerText = tit;
            await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: tit, fecha: new Date().toLocaleString()})});
            window.print();
        }
        async function addPuesto() {
            const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function addPersonal() {
            const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function delArc(id) { await fetch(`/api/archivos?id=${id}`, {method:'DELETE'}); render(); }
        async function delPer(id) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delPue(id) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }
        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            mesesNombres.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2027; i++) a.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # El servidor corre en el puerto 5000 por defecto
    app.run(debug=True, port=5000)
