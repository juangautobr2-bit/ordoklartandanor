import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Persistencia Reforzada v40
DB_PATH = os.path.abspath("ordoklar_v40_data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA synchronous = EXTRA")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['cantidad']))
        conn.commit()
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
    <title>ORDO KLAR | Gestión Integral v40</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; font-size: 18px; }
        
        .header-main { text-align: center; padding: 30px; border-bottom: 2px solid var(--gold); }
        .nav { display: flex; flex-wrap: wrap; justify-content: center; background: var(--card); position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border); }
        .nav button { background: none; border: none; color: #888; padding: 20px 25px; cursor: pointer; font-weight: bold; font-size: 16px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .content { padding: 30px; }
        .section { display: none; }
        .active-section { display: block; }

        /* Form boxes y inputs grandes */
        .form-box { background: var(--card); padding: 30px; border-radius: 15px; margin-bottom: 30px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 15px; }
        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 18px; border-radius: 8px; font-size: 18px; flex: 1; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 18px 30px; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; }

        /* Planilla Mensual con Totales */
        .table-wrap { overflow-x: auto; background: #000; border: 1px solid var(--border); border-radius: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #222; padding: 12px 5px; text-align: center; }
        .name-col { text-align: left; padding-left: 15px; font-weight: bold; color: var(--gold); width: 280px; position: sticky; left: 0; background: #0a0a0a; z-index: 5; }
        .total-col { background: #1a1a1a; font-weight: 900; color: var(--gold); }
        .foot-row { background: #111; font-weight: bold; color: var(--gold); }

        /* Estados */
        .cell-12 { background: #1b4332 !important; color: #fff; cursor: pointer; }
        .cell-F { background: #222 !important; color: #444; cursor: pointer; }
        .cell-ART { background: #5a1818 !important; color: #fff; cursor: pointer; }
        .cell-VAC { background: #03045e !important; color: #fff; cursor: pointer; }

        /* Informes y Archivos */
        .report-card { background: var(--card); border: 1px solid var(--border); padding: 40px; border-radius: 20px; text-align: center; margin-bottom: 20px; }
        .file-list { list-style: none; padding: 0; }
        .file-item { background: #111; padding: 15px; border-bottom: 1px solid #222; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 style="letter-spacing: 8px; margin:0;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#666; font-size:14px;">MAESTRO MAYOR DE OBRAS - GESTIÓN TÉCNICA</p>
    </header>

    <nav class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="form-box">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
            </div>
            <div class="table-wrap" id="print-area-planilla">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="report-card">
                <h2 style="color:var(--gold)">GENERACIÓN DE REPORTES OFICIALES</h2>
                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:20px; margin-top:30px;">
                    <button class="btn-gold" onclick="exportReport('planilla')">DESCARGAR PLANILLA MENSUAL</button>
                    <button class="btn-gold" onclick="exportReport('nomina')">DESCARGAR NÓMINA PERSONAL</button>
                    <button class="btn-gold" onclick="exportReport('puestos')">DESCARGAR LISTADO PUESTOS</button>
                </div>
            </div>
            <!-- Áreas ocultas para renderizar y exportar -->
            <div id="print-nomina" style="display:none; color:black; background:white; padding:40px;"></div>
            <div id="print-puestos" style="display:none; color:black; background:white; padding:40px;"></div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div class="form-box">
                <h2 style="color:var(--gold); width:100%">HISTORIAL DE EXPORTACIONES (Sesión)</h2>
                <div id="lista-archivos" style="width:100%" class="file-list">
                    <p style="color:#666">No hay archivos generados recientemente.</p>
                </div>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box">
                <input type="text" id="pue-nom" placeholder="Nombre Objetivo">
                <input type="text" id="pue-hor" placeholder="Horario">
                <input type="number" id="pue-can" placeholder="Dotación">
                <button class="btn-gold" onclick="savePuesto()">Crear</button>
            </div>
            <div id="grid-puestos" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:20px;"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()">Cargar</button>
            </div>
            <div class="table-wrap">
                <table id="tbl-per-main">
                    <thead><tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        let historyFiles = [];

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

            // 1. Cabecera Planilla
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th class="total-col">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            // 2. Cuerpo Planilla
            let b = "";
            let dailySumHs = new Array(dias).fill(0);
            let dailySumPer = new Array(dias).fill(0);

            per.forEach(p => {
                let pTotalHs = 0;
                let row = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const st = (nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'}).estado;
                    if(st == '12') { pTotalHs += 12; dailySumHs[i-1] += 12; dailySumPer[i-1]++; }
                    row += `<td class="cell-${st}" onclick="cycleEstado(this, ${p.id}, '${f}')">${st}</td>`;
                }
                row += `<td class="total-col">${pTotalHs}</td>`;
                b += `<tr>${row}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;

            // 3. Totales al final (NUEVO)
            let fHs = `<tr class="foot-row"><td class="name-col">TOTAL HORAS DÍA</td>`;
            let fPer = `<tr class="foot-row"><td class="name-col">CANT. PERSONAL</td>`;
            dailySumHs.forEach(v => fHs += `<td>${v}</td>`);
            dailySumPer.forEach(v => fPer += `<td>${v}</td>`);
            document.getElementById('f-pla').innerHTML = fHs + "<td>-</td></tr>" + fPer + "<td>-</td></tr>";

            // 4. Personal
            document.getElementById('b-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="color:red; background:none; border:none; cursor:pointer">X</button></td></tr>`).join('');

            // 5. Puestos
            document.getElementById('grid-puestos').innerHTML = pue.map(x => `
                <div class="report-card" style="padding:20px; text-align:left; border-left: 5px solid var(--gold)">
                    <h3 style="margin:0">${x.nombre}</h3>
                    <p>${x.horario} | Dotación: ${x.cantidad}</p>
                    <select>${per.map(p => `<option>${p.apellido}, ${p.nombre}</option>`).join('')}</select>
                </div>`).join('');
        }

        async function cycleEstado(td, pid, fecha) {
            const estados = ["F", "12", "ART", "VAC"];
            let next = estados[(estados.indexOf(td.innerText) + 1) % estados.length];
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})});
            render();
        }

        async function savePersonal() {
            const d = { legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function savePuesto() {
            const d = { nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        function exportReport(type) {
            const now = new Date();
            const timestamp = now.toLocaleString();
            let elementId = "";
            let fileName = "";

            if(type === 'planilla') {
                elementId = 'print-area-planilla';
                fileName = `Planilla_Mensual_${now.getTime()}.pdf`;
            } else if(type === 'nomina') {
                const content = document.getElementById('tbl-per-main').innerHTML;
                document.getElementById('print-nomina').innerHTML = "<h1>NÓMINA DE PERSONAL</h1><table border='1' style='width:100%'>" + content + "</table>";
                elementId = 'print-nomina';
                fileName = `Nomina_Personal_${now.getTime()}.pdf`;
            } else if(type === 'puestos') {
                const content = document.getElementById('grid-puestos').innerHTML;
                document.getElementById('print-puestos').innerHTML = "<h1>LISTADO DE PUESTOS</h1>" + content;
                elementId = 'print-puestos';
                fileName = `Listado_Puestos_${now.getTime()}.pdf`;
            }

            const opt = { margin: 10, filename: fileName, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById(elementId)).save().then(() => {
                historyFiles.push({ name: fileName, time: timestamp });
                updateFileHistory();
            });
        }

        function updateFileHistory() {
            const container = document.getElementById('lista-archivos');
            if(historyFiles.length === 0) return;
            container.innerHTML = historyFiles.map(f => `
                <div class="file-item">
                    <span><strong>📄 ${f.name}</strong></span>
                    <span style="color:#666">${f.time}</span>
                </div>
            `).reverse().join('');
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
