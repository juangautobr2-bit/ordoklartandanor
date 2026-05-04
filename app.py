import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v36
DB_PATH = '/tmp/ordoklar_v36.db'

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

# --- APIs (Se mantienen consistentes para integridad de datos) ---
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

# --- INTERFAZ COMPLETA v36 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión Técnica v36</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #222; }
        body { background: var(--bg); color: #E0E0E0; font-family: 'Condensed', 'Arial Narrow', sans-serif; margin: 0; overflow-x: hidden; }
        
        .header-main { text-align: center; padding: 25px; border-bottom: 2px solid var(--gold); background: #050505; }
        .brand-logo { font-size: 30px; font-weight: 900; letter-spacing: 8px; margin: 0; }
        .brand-logo span { color: var(--gold); }
        
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        .nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: 700; text-transform: uppercase; font-size: 12px; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); background: #181818; }

        .content { padding: 15px; width: 100vw; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        /* PLANILLA COMPACTA SIN SCROLL */
        .table-wrap { width: 100%; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
        th, td { border: 1px solid #222; text-align: center; padding: 4px 1px; overflow: hidden; }
        
        .name-col { text-align: left; width: 150px; padding-left: 8px; font-weight: bold; color: var(--gold); background: #080808; border-right: 2px solid var(--gold); }
        
        .th-date { height: 90px; vertical-align: bottom; width: auto; }
        .date-label { transform: rotate(-90deg); display: block; white-space: nowrap; font-weight: bold; margin-bottom: 10px; }
        .date-label b { color: var(--gold); font-size: 13px; }

        /* ESTADOS COLORES */
        .cell-12 { background: #1B5E20 !important; color: #fff; cursor: pointer; font-weight: bold; }
        .cell-F { background: #222 !important; color: #555; cursor: pointer; }
        .cell-ART { background: #B71C1C !important; color: #fff; cursor: pointer; }
        .cell-VAC { background: #0D47A1 !important; color: #fff; cursor: pointer; }

        /* TOTALES AL FINAL */
        .row-total { background: #0a0a0a; color: var(--gold); font-weight: 900; border-top: 2px solid var(--gold); }
        .row-total td { padding: 8px 0; font-size: 12px; }

        /* PUESTOS EN BOXES */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .puesto-box { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 15px; border-left: 4px solid var(--gold); }
        .puesto-box h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--gold); }

        /* INFORMES */
        .report-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .report-card { background: var(--card); padding: 30px; border-radius: 15px; text-align: center; border: 1px solid var(--border); }

        /* FORMULARIOS */
        .form-box { background: var(--card); padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid var(--border); display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; }
        input { background: #000; border: 1px solid var(--border); color: #fff; padding: 12px; border-radius: 6px; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 12px; font-weight: bold; border-radius: 6px; cursor: pointer; text-transform: uppercase; }

        @media print { .no-print { display: none !important; } }
    </style>
</head>
<body>

    <header class="header-main no-print">
        <h1 class="brand-logo">ORDO <span>KLAR</span></h1>
    </header>

    <nav class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
    </nav>

    <div class="content">
        <!-- PLANILLA MENSUAL -->
        <div id="s-pla" class="section active-section">
            <div class="form-box no-print">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
                <div style="color:var(--gold); font-size:12px; align-self:center">CLIC EN CELDA PARA CAMBIAR ESTADO</div>
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
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <input type="text" id="pue-nom" placeholder="Objetivo">
                <input type="text" id="pue-hor" placeholder="Horario">
                <input type="number" id="pue-can" placeholder="Dotación">
                <button class="btn-gold" onclick="savePuesto()">GUARDAR</button>
            </div>
            <div class="puestos-grid" id="grid-puestos"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()">REGISTRAR</button>
            </div>
            <div class="table-wrap" id="render-personal">
                <table style="font-size: 14px;">
                    <thead><tr><th style="width:100px">LEGAJO</th><th style="text-align:left">NOMBRE Y APELLIDO</th><th>ACCIONES</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="report-grid">
                <div class="report-card">
                    <h3>PLANILLA MENSUAL</h3>
                    <p>Exportación técnica en formato A3 Paisaje.</p>
                    <button class="btn-gold" onclick="genPDF('render-planilla', 'Planilla_Mensual', 'a3', 'landscape')">DESCARGAR PDF</button>
                </div>
                <div class="report-card">
                    <h3>NÓMINA DE PERSONAL</h3>
                    <p>Listado completo de agentes activos.</p>
                    <button class="btn-gold" onclick="genPDF('render-personal', 'Nomina_Personal', 'a4', 'portrait')">DESCARGAR PDF</button>
                </div>
                <div class="report-card">
                    <h3>ESTADO DE PUESTOS</h3>
                    <p>Relevamiento de objetivos y dotaciones.</p>
                    <button class="btn-gold" onclick="genPDF('grid-puestos', 'Estado_Puestos', 'a4', 'portrait')">DESCARGAR PDF</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const diasSem = ["DOM","LUN","MAR","MIE","JUE","VIE","SAB"];
        const estados = ["F", "12", "ART", "VAC"];

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

            // HEADER
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) {
                const fObj = new Date(a, m-1, i);
                h += `<th class="th-date"><span class="date-label">${diasSem[fObj.getDay()]} <b>${i}</b></span></th>`;
            }
            h += `</tr>`;
            document.getElementById('h-pla').innerHTML = h;

            // CUERPO Y TOTALES
            let hsT = new Array(dias).fill(0);
            let prT = new Array(dias).fill(0);

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = n ? n.estado : 'F';
                    if(st == '12') { hsT[i-1] += 12; prT[i-1] += 1; }
                    r += `<td class="cell-${st}" onclick="cycleEstado(this, ${p.id}, '${f}')">${st}</td>`;
                }
                return `<tr>${r}</tr>`;
            }).join('');

            // FOOTER CON TOTALES
            let fRows = `<tr class="row-total"><td class="name-col">CANT HS</td>`;
            hsT.forEach(v => fRows += `<td>${v}</td>`);
            fRows += `</tr><tr class="row-total"><td class="name-col">CANT PERSONAL</td>`;
            prT.forEach(v => fRows += `<td>${v}</td>`);
            fRows += `</tr>`;
            document.getElementById('f-pla').innerHTML = fRows;

            // PUESTOS
            document.getElementById('grid-puestos').innerHTML = pue.map(x => `
                <div class="puesto-box">
                    <h3>${x.nombre}</h3>
                    <div style="font-size:13px; color:#888">
                        Horario: ${x.horario} <br> Dotación: ${x.cantidad}
                    </div>
                    <div class="no-print" style="margin-top:10px">
                        <button onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})" style="background:#1976D2; border:none; color:#fff; padding:5px 10px; border-radius:4px; cursor:pointer">EDITAR</button>
                        <button onclick="delPue(${x.id})" style="background:#D32F2F; border:none; color:#fff; padding:5px 10px; border-radius:4px; cursor:pointer">ELIMINAR</button>
                    </div>
                </div>
            `).join('');

            // PERSONAL TABLA
            document.getElementById('b-per').innerHTML = per.map(x => `
                <tr><td>${x.legajo}</td><td style="text-align:left">${x.apellido.toUpperCase()}, ${x.nombre}</td><td class="no-print">
                    <button onclick="editPer(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')">EDITAR</button>
                </td></tr>
            `).join('');
        }

        async function cycleEstado(td, pid, fecha) {
            let next = estados[(estados.indexOf(td.innerText) + 1) % estados.length];
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})});
            render();
        }

        // CRUD
        async function savePersonal() {
            const d = { id: document.getElementById('per-id').value, legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPer(id, l, a, n) { document.getElementById('per-id').value=id; document.getElementById('per-leg').value=l; document.getElementById('per-ape').value=a; document.getElementById('per-nom').value=n; window.scrollTo(0,0); }

        async function savePuesto() {
            const d = { id: document.getElementById('pue-id').value, nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPue(id, n, h, c) { document.getElementById('pue-id').value=id; document.getElementById('pue-nom').value=n; document.getElementById('pue-hor').value=h; document.getElementById('pue-can').value=c; window.scrollTo(0,0); }
        async function delPue(id) { if(confirm('¿Eliminar objetivo?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        function genPDF(id, name, format, orient) {
            const el = document.getElementById(id);
            const opt = { margin: 10, filename: `${name}.pdf`, image: { type: 'jpeg', quality: 0.98 }, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: format, orientation: orient } };
            html2pdf().set(opt).from(el).save();
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
