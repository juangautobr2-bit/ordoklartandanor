import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v31 - Limpia y completa
DB_PATH = '/tmp/ordoklar_v31.db'

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

# --- API PERSONAL (CRUD COMPLETO) ---
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

# --- API PUESTOS (CRUD COMPLETO) ---
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

# --- INTERFAZ COMPLETA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | TANDANOR - WATCHMAN</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        /* CABECERA SOLICITADA */
        .header-main { text-align: center; padding: 40px 20px; border-bottom: 3px solid var(--gold); background: #0a0a0a; }
        .brand-logo { font-size: 38px; font-weight: 900; letter-spacing: 12px; margin: 0; }
        .brand-logo span { color: var(--gold); }
        .brand-company { font-size: 22px; font-weight: 700; letter-spacing: 6px; margin: 10px 0 5px 0; text-transform: uppercase; }
        .brand-sub { font-size: 16px; font-weight: 300; letter-spacing: 4px; color: var(--gold); text-transform: uppercase; }

        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 11px; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); background: #111; }

        .content { padding: 25px; max-width: 1600px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* FORMULARIOS */
        .form-box { background: var(--card); padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 12px; flex-wrap: wrap; border: 1px solid var(--border); align-items: center; }
        .form-box input { background: #000; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 4px; width: 180px; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: 900; cursor: pointer; border-radius: 4px; text-transform: uppercase; }

        /* TABLAS */
        .table-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; min-width: 1200px; }
        th, td { border: 1px solid #222; padding: 10px; text-align: center; font-size: 12px; }
        th { background: #111; color: var(--gold); }
        .name-col { text-align: left; color: var(--gold); font-weight: bold; position: sticky; left: 0; background: #111; z-index: 10; border-right: 3px solid var(--gold); }
        
        /* FILAS DE TOTALES */
        .row-total { background: #111; font-weight: 900; }
        .row-total td { color: var(--gold); border-top: 2px solid var(--gold); }

        /* ESTADOS */
        .cell-12 { background: #1B5E20 !important; }
        .cell-F { background: #333 !important; }
        .cell-ART { background: #B71C1C !important; }
        .cell-VAC { background: #0D47A1 !important; }
        select { background: transparent; color: white; border: none; font-weight: bold; width: 100%; text-align-last: center; cursor: pointer; }

        .btn-edit { background: #1976D2; color: white; border: none; padding: 5px 10px; cursor: pointer; margin-right: 5px; border-radius: 3px; }
        .btn-del { background: #D32F2F; color: white; border: none; padding: 5px 10px; cursor: pointer; border-radius: 3px; }

        @media print {
            .no-print { display: none !important; }
            body { background: white; color: black; }
            .header-main { background: white; border-bottom: 4px solid black; }
            .brand-logo, .brand-company, .brand-sub { color: black !important; }
            table { color: black !important; border: 1px solid #000; }
            th, td { border: 1px solid #000 !important; }
        }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 class="brand-logo">ORDO <span>KLAR</span></h1>
        <div class="brand-company">TANDANOR</div>
        <div class="brand-sub">WATCHMAN</div>
    </header>

    <nav class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Guardias / Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <button class="btn-gold no-print" style="margin-bottom:20px; background:#2E7D32; color:white;" onclick="exportPDF()">📄 EXPORTAR PDF (A3)</button>
            <div class="no-print" style="float:right; display:flex; gap:10px;">
                <select id="sel-mes" onchange="render()" style="background:#111; color:white; padding:10px; border:1px solid #333;"></select>
                <select id="sel-anio" onchange="render()" style="background:#111; color:white; padding:10px; border:1px solid #333;"></select>
            </div>
            <div class="table-wrap">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <input type="text" id="pue-nom" placeholder="Nombre del Puesto">
                <input type="text" id="pue-hor" placeholder="Horario">
                <input type="number" id="pue-can" placeholder="Cantidad Personal">
                <button class="btn-gold" onclick="savePuesto()">GUARDAR PUESTO</button>
            </div>
            <table>
                <thead><tr><th>PUESTO</th><th>HORARIO</th><th>CANTIDAD</th><th class="no-print">ACCIONES</th></tr></thead>
                <tbody id="b-pue"></tbody>
            </table>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()">GUARDAR PERSONAL</button>
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

            const m = document.getElementById('sel-mes').value;
            const a = document.getElementById('sel-anio').value;
            const dias = new Date(a, m, 0).getDate();

            let hsDia = new Array(dias).fill(0);
            let perDia = new Array(dias).fill(0);

            // Planilla
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th>TOTAL</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                let totalHs = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { totalHs += 12; hsDia[i-1] += 12; perDia[i-1] += 1; }
                    r += `<td class="cell-${st}">
                        <select class="no-print" onchange="updNov(${p.id},'${f}',this.value)">
                            <option value="12" ${st=='12'?'selected':''}>12</option>
                            <option value="F" ${st=='F'?'selected':''}>F</option>
                            <option value="ART" ${st=='ART'?'selected':''}>ART</option>
                            <option value="VAC" ${st=='VAC'?'selected':''}>VAC</option>
                        </select>
                        <span class="no-web" style="display:none">${st}</span>
                    </td>`;
                }
                return `<tr>${r}<td>${totalHs}</td></tr>`;
            }).join('');

            // Totales Planilla
            let fHs = `<tr class="row-total"><td class="name-col">CANT HS DIA</td>`;
            hsDia.forEach(v => fHs += `<td>${v}</td>`);
            fHs += `<td>-</td></tr>`;
            let fPe = `<tr class="row-total"><td class="name-col">CANT PERSONAL DIA</td>`;
            perDia.forEach(v => fPe += `<td>${v}</td>`);
            fPe += `<td>-</td></tr>`;
            document.getElementById('f-pla').innerHTML = fHs + fPe;

            // Listas Puestos y Personal
            document.getElementById('b-pue').innerHTML = pue.map(x => `<tr><td>${x.nombre}</td><td>${x.horario}</td><td>${x.cantidad}</td><td class="no-print"><button class="btn-edit" onclick="editPuesto(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})">EDITAR</button><button class="btn-del" onclick="delPuesto(${x.id})">ELIMINAR</button></td></tr>`).join('');
            document.getElementById('b-per').innerHTML = per.map(x => `<tr><td>${x.legajo}</td><td class="name-col">${x.apellido.toUpperCase()}, ${x.nombre}</td><td class="no-print"><button class="btn-edit" onclick="editPer(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')">EDITAR</button><button class="btn-del" onclick="delPer(${x.id})">ELIMINAR</button></td></tr>`).join('');
        }

        // Acciones CRUD
        async function savePersonal() {
            const d = { id: document.getElementById('per-id').value, legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            resetForms(); render();
        }
        function editPer(id, l, a, n) { document.getElementById('per-id').value=id; document.getElementById('per-leg').value=l; document.getElementById('per-ape').value=a; document.getElementById('per-nom').value=n; }
        async function delPer(id) { if(confirm('¿Borrar?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

        async function savePuesto() {
            const d = { id: document.getElementById('pue-id').value, nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            resetForms(); render();
        }
        function editPuesto(id, n, h, c) { document.getElementById('pue-id').value=id; document.getElementById('pue-nom').value=n; document.getElementById('pue-hor').value=h; document.getElementById('pue-can').value=c; }
        async function delPuesto(id) { if(confirm('¿Borrar?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }
        function resetForms() { document.querySelectorAll('input').forEach(i => i.value = ''); }

        function exportPDF() {
            const opt = { margin: 5, filename: 'Planilla.pdf', html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.body).save();
        }

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
