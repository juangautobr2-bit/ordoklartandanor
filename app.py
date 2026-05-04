import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v34
DB_PATH = '/tmp/ordoklar_v34.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs CRUD ---
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
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE puestos SET nombre=?, horario=?, cantidad=? WHERE id=?", (d['nombre'], d['horario'], d['cantidad'], d['id']))
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

# --- INTERFAZ COMPLETA v34 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Panel de Gestión v34</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #121212; --border: #2A2A2A; --text: #E0E0E0; }
        body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; margin: 0; }
        
        /* Header & Nav */
        .header-main { text-align: center; padding: 40px 20px; border-bottom: 3px solid var(--gold); background: #080808; }
        .brand-logo { font-size: 35px; font-weight: 900; letter-spacing: 10px; margin: 0; color: #FFF; }
        .brand-logo span { color: var(--gold); }
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        .nav button { background: none; border: none; color: #888; padding: 20px 30px; cursor: pointer; font-weight: 700; text-transform: uppercase; font-size: 13px; }
        .nav button.active { color: var(--gold); border-bottom: 4px solid var(--gold); background: #181818; }

        .content { padding: 30px; max-width: 1500px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* Form Estilo Grande */
        .form-box { background: var(--card); padding: 30px; border-radius: 15px; margin-bottom: 30px; border: 1px solid var(--border); display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 18px; border-radius: 10px; font-size: 16px; width: 100%; box-sizing: border-box; }
        input:focus { border-color: var(--gold); outline: none; }
        label { display: block; margin-bottom: 10px; color: var(--gold); font-weight: bold; font-size: 13px; }

        /* Planilla Interactiva */
        .table-wrap { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; user-select: none; }
        th, td { border: 1px solid #222; padding: 15px 10px; text-align: center; min-width: 45px; cursor: pointer; }
        th { background: #111; color: var(--gold); font-size: 12px; }
        .name-col { text-align: left; min-width: 250px; background: #0a0a0a; font-weight: 800; color: var(--gold); position: sticky; left: 0; z-index: 5; border-right: 2px solid var(--gold); }

        /* Colores de Estados */
        .cell-12 { background: #1B5E20 !important; color: white; font-weight: 900; } /* Verde */
        .cell-F { background: #333333 !important; color: #888; } /* Gris */
        .cell-ART { background: #B71C1C !important; color: white; font-weight: 900; } /* Rojo */
        .cell-VAC { background: #0D47A1 !important; color: white; font-weight: 900; } /* Azul */

        /* Puestos como Boxes */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px; }
        .puesto-box { background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 25px; transition: 0.3s; border-left: 5px solid var(--gold); }
        .puesto-box:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }
        .puesto-box h3 { margin: 0 0 15px 0; color: var(--gold); text-transform: uppercase; letter-spacing: 1px; }
        .puesto-info { font-size: 14px; line-height: 1.6; color: #aaa; margin-bottom: 20px; }
        .puesto-actions { display: flex; gap: 10px; }

        /* Botones */
        .btn-main { background: var(--gold); color: #000; border: none; padding: 18px 30px; font-weight: 900; cursor: pointer; border-radius: 12px; text-transform: uppercase; font-size: 14px; }
        .btn-edit { background: #1976D2; color: white; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; }
        .btn-del { background: #D32F2F; color: white; border: none; padding: 10px 15px; border-radius: 8px; cursor: pointer; }

        @media print { .no-print { display: none !important; } .name-col { border-right: 2px solid black; } }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 class="brand-logo">ORDO <span>KLAR</span></h1>
        <div style="letter-spacing: 5px; font-weight: 300; font-size: 14px; margin-top: 5px;">TANDANOR - WATCHMAN</div>
    </header>

    <nav class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="content">
        <!-- PLANILLA MENSUAL -->
        <div id="s-pla" class="section active-section">
            <div class="form-box no-print" style="grid-template-columns: 1fr 1fr auto;">
                <div><label>Mes</label><select id="sel-mes" onchange="render()"></select></div>
                <div><label>Año</label><select id="sel-anio" onchange="render()"></select></div>
                <div style="align-self: end; color: var(--gold); padding: 18px;">MODO EDICIÓN RÁPIDA (CLIC EN CELDA)</div>
            </div>
            <div class="table-wrap">
                <table id="pdf-planilla">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- PUESTOS (BOXES) -->
        <div id="s-pue" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <div><label>Nombre del Objetivo</label><input type="text" id="pue-nom" placeholder="Ej: Acceso Principal"></div>
                <div><label>Horario de Guardia</label><input type="text" id="pue-hor" placeholder="06 a 18 hs"></div>
                <div><label>Dotación</label><input type="number" id="pue-can" value="1"></div>
                <button class="btn-main" onclick="savePuesto()">GUARDAR PUESTO</button>
            </div>
            <div class="puestos-grid" id="grid-puestos"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <div><label>N° de Legajo</label><input type="text" id="per-leg" placeholder="Ej: 4500"></div>
                <div><label>Apellido</label><input type="text" id="per-ape" placeholder="Apellido"></div>
                <div><label>Nombre</label><input type="text" id="per-nom" placeholder="Nombre"></div>
                <button class="btn-main" onclick="savePersonal()">REGISTRAR AGENTE</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th>LEGAJO</th><th style="text-align:left">NOMBRE Y APELLIDO</th><th>ACCIONES</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="form-box" style="text-align:center; display:block">
                <h2 style="color:var(--gold)">GENERAR REPORTES OFICIALES</h2>
                <div style="display:flex; gap:20px; justify-content: center; margin-top:30px;">
                    <button class="btn-main" onclick="genPDF('pdf-planilla', 'Planilla_Mensual', 'a3', 'landscape')">PDF PLANILLA (A3)</button>
                    <button class="btn-main" onclick="genPDF('grid-puestos', 'Reporte_Puestos', 'a4', 'portrait')">PDF PUESTOS (A4)</button>
                </div>
            </div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div id="file-log" class="form-box" style="display:block">
                <p style="color:#666">No se han generado archivos en esta sesión.</p>
            </div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const estados = ["F", "12", "ART", "VAC"];
        let logs = [];

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

            const m = document.getElementById('sel-mes').value;
            const a = document.getElementById('sel-anio').value;
            const dias = new Date(a, m, 0).getDate();

            // Render Planilla
            let h = `<tr><th class="name-col">AGENTE / DÍAS DEL MES</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `</tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = n ? n.estado : 'F';
                    r += `<td class="cell-${st}" onclick="cycleEstado(this, ${p.id}, '${f}')">${st}</td>`;
                }
                return `<tr>${r}</tr>`;
            }).join('');

            // Render Puestos en BOXES
            document.getElementById('grid-puestos').innerHTML = pue.map(x => `
                <div class="puesto-box">
                    <h3>${x.nombre}</h3>
                    <div class="puesto-info">
                        <b>HORARIO:</b> ${x.horario}<br>
                        <b>PERSONAL REQUERIDO:</b> ${x.cantidad}
                    </div>
                    <div class="puesto-actions">
                        <button class="btn-edit" onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})">EDITAR</button>
                        <button class="btn-del" onclick="delPue(${x.id})">ELIMINAR</button>
                    </div>
                </div>
            `).join('');

            // Render Personal
            document.getElementById('b-per').innerHTML = per.map(x => `
                <tr>
                    <td>${x.legajo}</td>
                    <td style="text-align:left"><b>${x.apellido.toUpperCase()}</b>, ${x.nombre}</td>
                    <td>
                        <button class="btn-edit" onclick="editPer(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')">EDITAR</button>
                        <button class="btn-del" onclick="delPer(${x.id})">ELIMINAR</button>
                    </td>
                </tr>
            `).join('');
        }

        // Lógica de Ciclo de Estados
        async function cycleEstado(td, pid, fecha) {
            let current = td.innerText;
            let nextIndex = (estados.indexOf(current) + 1) % estados.length;
            let next = estados[nextIndex];
            
            td.className = `cell-${next}`;
            td.innerText = next;

            await fetch('/api/novedades', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})
            });
        }

        // CRUD Puestos
        async function savePuesto() {
            const d = { id: document.getElementById('pue-id').value, nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPue(id, n, h, c) { 
            document.getElementById('pue-id').value=id; document.getElementById('pue-nom').value=n; 
            document.getElementById('pue-hor').value=h; document.getElementById('pue-can').value=c; 
            window.scrollTo(0,0);
        }
        async function delPue(id) { if(confirm('¿Eliminar objetivo?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        // CRUD Personal
        async function savePersonal() {
            const d = { id: document.getElementById('per-id').value, legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPer(id, l, a, n) { 
            document.getElementById('per-id').value=id; document.getElementById('per-leg').value=l; 
            document.getElementById('per-ape').value=a; document.getElementById('per-nom').value=n; 
            window.scrollTo(0,0);
        }
        async function delPer(id) { if(confirm('¿Eliminar agente?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

        function genPDF(id, name, format, orient) {
            const el = document.getElementById(id);
            const opt = { margin: 10, filename: `${name}.pdf`, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: format, orientation: orient } };
            html2pdf().set(opt).from(el).save();
            logs.push(`${name}.pdf - ${new Date().toLocaleTimeString()}`);
            updateLogs();
        }

        function updateLogs() {
            document.getElementById('file-log').innerHTML = logs.map(l => `<div style="padding:10px; border-bottom:1px solid #333">📄 ${l}</div>`).reverse().join('');
        }

        function reset() { document.querySelectorAll('input').forEach(i => i.value = ''); }

        window.onload = () => {
            const m = document.getElementById('sel-mes'); const a = document.getElementById('sel-anio'); const now = new Date();
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
