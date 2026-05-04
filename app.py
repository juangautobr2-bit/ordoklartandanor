import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Persistencia en el directorio actual para evitar borrados
DB_PATH = os.path.join(os.getcwd(), 'ordoklar_v38_data.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))''')
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs ---
@app.route('/api/personal', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE personal SET nombre=?, apellido=?, legajo=? WHERE id=?", (d['nombre'], d['apellido'], d['legajo'], d['id']))
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
    conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['cantidad']))
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
    conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
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

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión Técnica v38</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; font-size: 16px; }
        
        .header-main { text-align: center; padding: 30px; border-bottom: 2px solid var(--gold); }
        .nav { display: flex; justify-content: center; background: var(--card); position: sticky; top: 0; z-index: 100; }
        .nav button { background: none; border: none; color: #999; padding: 20px 30px; cursor: pointer; font-weight: bold; font-size: 16px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .content { padding: 20px; }
        .section { display: none; }
        .active-section { display: block; }

        /* Inputs Grandes */
        .form-box { background: var(--card); padding: 25px; border-radius: 12px; margin-bottom: 25px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 15px; }
        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 15px; border-radius: 8px; font-size: 18px; flex: 1; min-width: 200px; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 15px 30px; font-weight: 900; border-radius: 8px; cursor: pointer; font-size: 16px; }

        /* Planilla Mensual */
        .table-wrap { overflow-x: auto; background: #000; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { border: 1px solid #333; padding: 10px 5px; text-align: center; }
        .name-col { text-align: left; padding-left: 15px; font-weight: bold; color: var(--gold); width: 250px; position: sticky; left: 0; background: #050505; z-index: 10; font-size: 15px; }
        .total-col { background: #1a1a1a; font-weight: 900; color: var(--gold); width: 80px; font-size: 16px; }
        
        .th-date { height: 100px; }
        .date-label { transform: rotate(-90deg); display: block; width: 30px; margin: 0 auto; font-weight: bold; }

        /* Estados */
        .cell-12 { background: #1B5E20 !important; color: #fff; font-weight: bold; cursor: pointer; }
        .cell-F { background: #222 !important; color: #666; cursor: pointer; }
        .cell-ART { background: #B71C1C !important; color: #fff; cursor: pointer; }
        .cell-VAC { background: #0D47A1 !important; color: #fff; cursor: pointer; }

        /* Puestos */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .puesto-box { background: var(--card); border: 1px solid var(--border); border-radius: 15px; padding: 20px; border-left: 5px solid var(--gold); }
        .puesto-box select { width: 100%; margin-top: 10px; font-size: 14px; padding: 10px; }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 style="letter-spacing: 8px; margin:0;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#666; font-size:12px; margin:5px 0 0 0">GESTIÓN TÉCNICA DE PERSONAL v38</p>
    </header>

    <nav class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Asignación Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="form-box">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
                <button class="btn-gold" onclick="genPDF('render-planilla', 'Planilla', 'a3', 'landscape')">Descargar A3</button>
            </div>
            <div class="table-wrap" id="render-planilla">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box">
                <input type="text" id="pue-nom" placeholder="Nombre del Puesto (ej: Guardia Sur)">
                <input type="text" id="pue-hor" placeholder="Horario (ej: 08-20hs)">
                <input type="number" id="pue-can" placeholder="Dotación Requerida">
                <button class="btn-gold" onclick="savePuesto()">Crear Puesto</button>
            </div>
            <div class="puestos-grid" id="grid-puestos"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()">Guardar Agente</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>Legajo</th><th>Nombre Completo</th><th>Acción</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const estados = ["F", "12", "ART", "VAC"];
        let personalCache = [];

        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active-section'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active-section');
            document.getElementById('n-'+t).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);
            personalCache = per;

            const m = document.getElementById('sel-mes').value;
            const a = document.getElementById('sel-anio').value;
            const dias = new Date(a, m, 0).getDate();

            // Render Planilla
            let h = `<tr><th class="name-col">APELLIDO Y NOMBRE</th>`;
            for(let i=1; i<=dias; i++) h += `<th class="th-date"><span class="date-label">${i}</span></th>`;
            h += `<th class="total-col">TOTAL HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let rowHs = 0;
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const st = (nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'}).estado;
                    if(st == '12') rowHs += 12;
                    r += `<td class="cell-${st}" onclick="cycleEstado(this, ${p.id}, '${f}')">${st}</td>`;
                }
                r += `<td class="total-col">${rowHs}</td>`;
                return `<tr>${r}</tr>`;
            }).join('');

            // Render Personal
            document.getElementById('b-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="background:red; color:white; border:none; padding:5px; border-radius:4px; cursor:pointer">Eliminar</button></td></tr>
            `).join('');

            // Render Puestos con Selectores de Personal
            document.getElementById('grid-puestos').innerHTML = pue.map(x => {
                let selectores = '';
                for(let i=0; i<x.cantidad; i++) {
                    selectores += `
                        <select>
                            <option>-- Seleccionar Agente --</option>
                            ${per.map(p => `<option>${p.apellido}, ${p.nombre}</option>`).join('')}
                        </select>`;
                }
                return `
                <div class="puesto-box">
                    <h3 style="color:var(--gold); margin:0">${x.nombre}</h3>
                    <p style="font-size:13px; color:#aaa">${x.horario} | Dotación: ${x.cantidad}</p>
                    <div style="margin-top:10px">${selectores}</div>
                    <button onclick="delPue(${x.id})" style="margin-top:10px; background:none; border:1px solid #444; color:#666; cursor:pointer">Eliminar Puesto</button>
                </div>`;
            }).join('');
        }

        async function cycleEstado(td, pid, fecha) {
            let next = estados[(estados.indexOf(td.innerText) + 1) % estados.length];
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})});
            render();
        }

        async function savePersonal() {
            const d = { legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function delPer(id) { if(confirm('¿Eliminar?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

        async function savePuesto() {
            const d = { nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function delPue(id) { if(confirm('¿Eliminar?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        function genPDF(id, name, format, orient) {
            const el = document.getElementById(id);
            const opt = { margin: 10, filename: `${name}.pdf`, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: format, orientation: orient } };
            html2pdf().set(opt).from(el).save();
        }

        window.onload = () => {
            const m = document.getElementById('sel-mes'); const a = document.getElementById('sel-anio'); const now = new Date();
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
