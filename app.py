import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v27
DB_PATH = '/tmp/ordoklar_v27.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Tablas
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API PERSONAL ---
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
        conn.execute("DELETE FROM novedades WHERE personal_id=?", (request.args.get('id'),))
    conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

# --- API PUESTOS ---
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

# --- INTERFAZ v27 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel de Gestión</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        /* HEADER WEB */
        .header-web { text-align: center; padding: 20px; font-size: 26px; font-weight: 900; letter-spacing: 8px; border-bottom: 2px solid var(--gold); }
        
        /* HEADER PDF */
        .report-header { display: none; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 5px solid #000; background: #fff; color: #000; }
        .logo-box { width: 120px; text-align: center; font-size: 10px; font-weight: bold; }
        .logo-box img { height: 70px; display: block; margin: 0 auto; }

        /* NAV */
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .content { padding: 20px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* FORMULARIOS */
        .form-box { background: var(--card); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid var(--border); display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .form-box input { background: #000; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 4px; }
        .btn-add { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }

        /* TABLAS */
        table { width: 100%; border-collapse: collapse; background: #000; }
        th, td { border: 1px solid #222; padding: 10px; text-align: center; }
        th { background: #111; color: var(--gold); font-size: 12px; }
        .name-col { text-align: left; color: var(--gold); font-weight: bold; }

        /* BOTONES ACCION */
        .btn-edit { background: #1976D2; color: white; border: none; padding: 5px 10px; cursor: pointer; margin-right: 5px; }
        .btn-del { background: #D32F2F; color: white; border: none; padding: 5px 10px; cursor: pointer; }
        .btn-pdf { background: #2E7D32; color: white; border: none; padding: 12px 20px; cursor: pointer; font-weight: bold; margin-bottom: 10px; border-radius: 4px; }

        /* COLORES NOVEDADES */
        .cell-12 { background: #1B5E20 !important; }
        .cell-F { background: #424242 !important; }
        .cell-ART { background: #B71C1C !important; }
        .cell-FE { background: #E65100 !important; }
        .cell-VAC { background: #0D47A1 !important; }
        
        select { background: transparent; color: white; border: none; font-weight: bold; width: 100%; cursor: pointer; }

        @media print {
            .no-print { display: none !important; }
            .report-header { display: flex !important; }
            body { background: white; color: black; }
            table { color: black !important; border: 1px solid #000; }
            th, td { border: 1px solid #000; }
            .section { display: block !important; }
        }
    </style>
</head>
<body>

    <div class="header-web no-print">ORDO <span style="color:var(--gold)">KLAR</span></div>

    <div class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Guardias / Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <!-- HEADER PDF -->
    <div id="report-header-ui" class="report-header">
        <div class="logo-box">
            <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/TANDANOR.PNG" crossorigin="anonymous">
            TANDANOR
        </div>
        <div style="text-align:center; flex:1">
            <h1 id="rt-titulo">INFORME DE SERVICIO</h1>
            <p id="rt-subtitulo">SISTEMA ORDO KLAR</p>
        </div>
        <div class="logo-box">
            <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/WATCHMAN.SVG" crossorigin="anonymous">
            WATCHMAN
        </div>
    </div>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="actions-bar no-print">
                <button class="btn-pdf" onclick="exportPDF('PLANILLA MENSUAL', '', 'Planilla.pdf', 'landscape')">📄 EXPORTAR PLANILLA</button>
                <select id="sel-mes" onchange="render()" style="width:auto; background:#111; padding:10px;"></select>
                <select id="sel-anio" onchange="render()" style="width:auto; background:#111; padding:10px;"></select>
            </div>
            <div style="overflow-x:auto">
                <table id="table-pla">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <button class="btn-pdf no-print" onclick="exportPDF('REPORTE DE PUESTOS', '', 'Puestos.pdf', 'portrait')">📄 EXPORTAR PUESTOS</button>
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <input type="text" id="pue-nom" placeholder="Nombre del Puesto">
                <input type="text" id="pue-hor" placeholder="Horario (Ej: 07 a 19)">
                <input type="number" id="pue-can" placeholder="Dotación">
                <button class="btn-add" onclick="savePuesto()">GUARDAR PUESTO</button>
            </div>
            <table>
                <thead><tr><th>PUESTO</th><th>HORARIO</th><th>DOTACIÓN</th><th class="no-print">ACCIONES</th></tr></thead>
                <tbody id="b-pue"></tbody>
            </table>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <button class="btn-pdf no-print" onclick="exportPDF('NÓMINA DE PERSONAL', '', 'Personal.pdf', 'portrait')">📄 EXPORTAR PERSONAL</button>
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-add" onclick="savePersonal()">GUARDAR AGENTE</button>
            </div>
            <table>
                <thead><tr><th>LEGAJO</th><th>APELLIDO Y NOMBRE</th><th class="no-print">ACCIONES</th></tr></thead>
                <tbody id="b-per"></tbody>
            </table>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];

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

            // Render Planilla
            const m = document.getElementById('sel-mes').value || new Date().getMonth()+1;
            const a = document.getElementById('sel-anio').value || new Date().getFullYear();
            const dias = new Date(a, m, 0).getDate();
            
            let h = `<tr><th style="min-width:200px">AGENTE</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th>TOTAL</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido}, ${p.nombre}</td>`;
                let total = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') total += 12;
                    r += `<td class="cell-${st}">
                        <select class="no-print" onchange="updNov(${p.id},'${f}',this.value)">
                            <option value="12" ${st=='12'?'selected':''}>12</option>
                            <option value="F" ${st=='F'?'selected':''}>F</option>
                            <option value="ART" ${st=='ART'?'selected':''}>ART</option>
                            <option value="FE" ${st=='FE'?'selected':''}>FE</option>
                            <option value="VAC" ${st=='VAC'?'selected':''}>VAC</option>
                        </select>
                        <span class="no-web" style="display:none">${st}</span>
                    </td>`;
                }
                return `<tr>${r}<td>${total}</td></tr>`;
            }).join('');

            // Render Puestos
            document.getElementById('b-pue').innerHTML = pue.map(x => `
                <tr>
                    <td>${x.nombre}</td><td>${x.horario}</td><td>${x.cantidad}</td>
                    <td class="no-print">
                        <button class="btn-edit" onclick="editPuesto(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})">EDITAR</button>
                        <button class="btn-del" onclick="delPuesto(${x.id})">BORRAR</button>
                    </td>
                </tr>`).join('');

            // Render Personal
            document.getElementById('b-per').innerHTML = per.map(x => `
                <tr>
                    <td>${x.legajo}</td><td class="name-col">${x.apellido}, ${x.nombre}</td>
                    <td class="no-print">
                        <button class="btn-edit" onclick="editPersonal(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')">EDITAR</button>
                        <button class="btn-del" onclick="delPersonal(${x.id})">BORRAR</button>
                    </td>
                </tr>`).join('');
        }

        // --- ACCIONES PERSONAL ---
        async function savePersonal() {
            const data = { id: document.getElementById('per-id').value, legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            const method = data.id ? 'PUT' : 'POST';
            await fetch('/api/personal', { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)});
            resetPer(); render();
        }
        function editPersonal(id, leg, ape, nom) {
            document.getElementById('per-id').value = id;
            document.getElementById('per-leg').value = leg;
            document.getElementById('per-ape').value = ape;
            document.getElementById('per-nom').value = nom;
        }
        async function delPersonal(id) { if(confirm('¿Borrar agente y sus novedades?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
        function resetPer() { document.getElementById('per-id').value = ''; document.getElementById('per-leg').value = ''; document.getElementById('per-ape').value = ''; document.getElementById('per-nom').value = ''; }

        // --- ACCIONES PUESTOS ---
        async function savePuesto() {
            const data = { id: document.getElementById('pue-id').value, nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            const method = data.id ? 'PUT' : 'POST';
            await fetch('/api/puestos', { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)});
            resetPue(); render();
        }
        function editPuesto(id, nom, hor, can) {
            document.getElementById('pue-id').value = id;
            document.getElementById('pue-nom').value = nom;
            document.getElementById('pue-hor').value = hor;
            document.getElementById('pue-can').value = can;
        }
        async function delPuesto(id) { if(confirm('¿Borrar puesto?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }
        function resetPue() { document.getElementById('pue-id').value = ''; document.getElementById('pue-nom').value = ''; document.getElementById('pue-hor').value = ''; document.getElementById('pue-can').value = ''; }

        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }

        function exportPDF(tit, sub, file, ori) {
            document.getElementById('rt-titulo').innerText = tit;
            const header = document.getElementById('report-header-ui');
            header.style.display = 'flex';
            const opt = { margin: 5, filename: file, html2canvas: { scale: 2, useCORS: true }, jsPDF: { unit: 'mm', format: ori=='landscape'?'a3':'a4', orientation: ori } };
            html2pdf().set(opt).from(document.body).save().then(() => header.style.display = 'none');
        }

        window.onload = () => {
            const m = document.getElementById('sel-mes');
            const a = document.getElementById('sel-anio');
            const now = new Date();
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
