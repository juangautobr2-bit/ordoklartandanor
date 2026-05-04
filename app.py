import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v33
DB_PATH = '/tmp/ordoklar_v33.db'

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

# --- INTERFAZ COMPLETA v33 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Panel Técnico v33</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; --input-bg: #0a0a0a; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; padding-bottom: 50px; }
        
        .header-main { text-align: center; padding: 40px 20px; border-bottom: 3px solid var(--gold); background: #0a0a0a; }
        .brand-logo { font-size: 38px; font-weight: 900; letter-spacing: 12px; margin: 0; }
        .brand-logo span { color: var(--gold); }
        .brand-company { font-size: 22px; font-weight: 700; letter-spacing: 6px; margin: 10px 0; text-transform: uppercase; }

        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 18px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 12px; transition: 0.3s; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); background: #111; }

        .content { padding: 30px; max-width: 1400px; margin: auto; }
        .section { display: none; animation: fadeIn 0.4s ease; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .active-section { display: block; }

        /* INPUTS GRANDES */
        .form-box { background: var(--card); padding: 30px; border-radius: 12px; margin-bottom: 30px; border: 1px solid var(--border); display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; align-items: end; }
        input, select { background: var(--input-bg); border: 1px solid var(--border); color: #fff; padding: 15px; border-radius: 8px; font-size: 16px; width: 100%; box-sizing: border-box; }
        input:focus { border-color: var(--gold); outline: none; }
        label { display: block; margin-bottom: 8px; color: var(--gold); font-size: 12px; font-weight: bold; text-transform: uppercase; }

        /* PUESTOS COMO BOXES */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }
        .puesto-card { background: var(--card); border: 2px solid var(--border); border-radius: 15px; padding: 25px; position: relative; transition: 0.3s; }
        .puesto-card:hover { border-color: var(--gold); transform: translateY(-5px); }
        .puesto-card h3 { color: var(--gold); margin: 0 0 10px 0; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .puesto-meta { font-size: 14px; color: #888; margin-bottom: 15px; }
        .puesto-asignacion { margin-top: 15px; }
        .puesto-asignacion select { margin-bottom: 8px; font-size: 13px; padding: 8px; }
        .puesto-actions { display: flex; gap: 10px; margin-top: 20px; }

        /* TABLA PLANILLA */
        .table-wrap { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; background: #000; }
        th, td { border: 1px solid #222; padding: 12px; text-align: center; font-size: 13px; }
        th { background: #111; color: var(--gold); }
        .name-col { text-align: left; color: var(--gold); font-weight: bold; position: sticky; left: 0; background: #111; z-index: 10; border-right: 3px solid var(--gold); }

        /* BOTONES */
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 15px 25px; font-weight: 900; cursor: pointer; border-radius: 8px; text-transform: uppercase; transition: 0.3s; }
        .btn-gold:hover { background: #fff; box-shadow: 0 0 15px rgba(212,175,55,0.4); }
        .btn-red { background: #C62828; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }
        .btn-blue { background: #1976D2; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; }

        /* INFORMES */
        .info-panel { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .info-card { background: var(--card); border: 1px solid var(--border); padding: 30px; border-radius: 12px; text-align: center; }

        /* ESTADOS PLANILLA */
        .cell-12 { background: #1B5E20 !important; }
        .cell-F { background: #333 !important; }
        .cell-ART { background: #B71C1C !important; }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 class="brand-logo">ORDO <span>KLAR</span></h1>
        <div class="brand-company">TANDANOR - WATCHMAN</div>
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
            <div class="form-box no-print">
                <div>
                    <label>Mes de Gestión</label>
                    <select id="sel-mes" onchange="render()"></select>
                </div>
                <div>
                    <label>Año</label>
                    <select id="sel-anio" onchange="render()"></select>
                </div>
                <div style="grid-column: span 2; text-align: right; color: var(--gold); font-weight: bold;">
                    CONTROL DE ASISTENCIA MENSUAL
                </div>
            </div>
            <div class="table-wrap">
                <table id="pdf-planilla">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS (CARDS CON ASIGNACIÓN) -->
        <div id="s-pue" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <div><label>Nombre del Puesto</label><input type="text" id="pue-nom" placeholder="Ej: Portería Norte"></div>
                <div><label>Horario</label><input type="text" id="pue-hor" placeholder="06:00 a 18:00"></div>
                <div><label>Dotación Req.</label><input type="number" id="pue-can" value="1"></div>
                <button class="btn-gold" onclick="savePuesto()">GUARDAR PUESTO</button>
            </div>
            <div class="puestos-grid" id="grid-puestos">
                <!-- Se carga dinámicamente -->
            </div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <div><label>N° Legajo</label><input type="text" id="per-leg" placeholder="Legajo"></div>
                <div><label>Apellido</label><input type="text" id="per-ape" placeholder="Apellido"></div>
                <div><label>Nombre</label><input type="text" id="per-nom" placeholder="Nombre"></div>
                <button class="btn-gold" onclick="savePersonal()">REGISTRAR AGENTE</button>
            </div>
            <div class="table-wrap">
                <table id="pdf-personal">
                    <thead><tr><th>LEGAJO</th><th style="text-align:left">APELLIDO Y NOMBRE</th><th>ACCIONES</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="info-panel">
                <div class="info-card">
                    <h3>PLANILLA GENERAL</h3>
                    <button class="btn-gold" onclick="genPDF('planilla')">DESCARGAR PDF A3</button>
                </div>
                <div class="info-card">
                    <h3>NÓMINA PERSONAL</h3>
                    <button class="btn-gold" onclick="genPDF('personal')">DESCARGAR PDF A4</button>
                </div>
                <div class="info-card">
                    <h3>ESTADO DE PUESTOS</h3>
                    <button class="btn-gold" onclick="genPDF('grid-puestos')">DESCARGAR REPORTE</button>
                </div>
            </div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <h2 style="color:var(--gold)">HISTORIAL DE GENERACIÓN</h2>
            <div id="file-list" style="background:var(--card); border-radius:12px; padding:20px;">
                <p style="color:#666">No hay archivos en la sesión actual.</p>
            </div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
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

            // RENDER PLANILLA
            let h = `<tr><th class="name-col">PERSONAL / DÍAS</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th>HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                let sum = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = n ? n.estado : 'F';
                    if(st == '12') sum += 12;
                    r += `<td class="cell-${st}"><select class="no-print" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="ART" ${st=='ART'?'selected':''}>ART</option>
                    </select></td>`;
                }
                return `<tr>${r}<td style="font-weight:900; background:#111">${sum}</td></tr>`;
            }).join('');

            // RENDER PUESTOS (BOXES)
            const optPer = per.map(x => `<option value="${x.id}">${x.apellido}, ${x.nombre}</option>`).join('');
            document.getElementById('grid-puestos').innerHTML = pue.map(x => {
                let selects = '';
                for(let i=0; i<x.cantidad; i++) {
                    selects += `<select><option>Asignar Personal...</option>${optPer}</select>`;
                }
                return `
                <div class="puesto-card">
                    <h3>${x.nombre}</h3>
                    <div class="puesto-meta">
                        <b>HORARIO:</b> ${x.horario} <br>
                        <b>DOTACIÓN:</b> ${x.cantidad} Agentes
                    </div>
                    <div class="puesto-asignacion">
                        <label>ASIGNACIÓN DIARIA</label>
                        ${selects}
                    </div>
                    <div class="puesto-actions no-print">
                        <button class="btn-blue" onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})">EDITAR</button>
                        <button class="btn-red" onclick="delPue(${x.id})">BORRAR</button>
                    </div>
                </div>`;
            }).join('');

            // RENDER TABLA PERSONAL
            document.getElementById('b-per').innerHTML = per.map(x => `
                <tr>
                    <td>${x.legajo}</td>
                    <td style="text-align:left">${x.apellido.toUpperCase()}, ${x.nombre}</td>
                    <td>
                        <button class="btn-blue" onclick="editPer(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')">EDITAR</button>
                        <button class="btn-red" onclick="delPer(${x.id})">BORRAR</button>
                    </td>
                </tr>
            `).join('');
        }

        // --- ACCIONES PDF ---
        function genPDF(id) {
            const el = document.getElementById(id === 'planilla' ? 'pdf-planilla' : (id === 'personal' ? 'pdf-personal' : 'grid-puestos'));
            const name = `OrdoKlar_${id}_${Date.now()}.pdf`;
            const opt = { 
                margin: 5, filename: name, 
                html2canvas: { scale: 2, useCORS: true }, 
                jsPDF: { unit: 'mm', format: id==='planilla'?'a3':'a4', orientation: id==='planilla'?'landscape':'portrait' } 
            };
            html2pdf().set(opt).from(el).save();
            logs.push({name, fecha: new Date().toLocaleString()});
            updateLogs();
        }

        function updateLogs() {
            document.getElementById('file-list').innerHTML = logs.map(l => `
                <div style="padding:10px; border-bottom:1px solid #333; display:flex; justify-content:space-between">
                    <span>📄 ${l.name}</span> <span style="color:#888">${l.fecha}</span>
                </div>
            `).reverse().join('');
        }

        // --- CRUD LOGIC ---
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
        async function delPer(id) { if(confirm('¿Eliminar Agente?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

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
        async function delPue(id) { if(confirm('¿Eliminar Puesto?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }
        function reset() { document.querySelectorAll('input').forEach(i => i.value = ''); document.getElementById('pue-can').value = 1; }

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
