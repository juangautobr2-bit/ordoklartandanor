import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Configuración de Base de Datos con Ruta Absoluta
DB_PATH = os.path.abspath("ordoklar_v41_final.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA synchronous = EXTRA")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY, nombre TEXT, horario TEXT, cantidad INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- ENDPOINTS API ---
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR v41 | Gestión Profesional</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #121212; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 25px; border-bottom: 2px solid var(--gold); background: #050505; }
        nav { display: flex; justify-content: center; background: #111; border-bottom: 1px solid var(--border); sticky: top; z-index: 1000; }
        nav button { background: none; border: none; color: #888; padding: 20px 30px; cursor: pointer; font-weight: bold; font-size: 15px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 30px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* Forms e Inputs */
        .box { background: var(--card); padding: 25px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 20px; }
        .flex-form { display: flex; flex-wrap: wrap; gap: 15px; }
        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 15px; border-radius: 8px; font-size: 16px; flex: 1; min-width: 200px; }
        .btn { background: var(--gold); color: #000; border: none; padding: 15px 30px; font-weight: bold; border-radius: 8px; cursor: pointer; }

        /* Planilla Mensual */
        .table-container { overflow-x: auto; background: #000; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { border: 1px solid #222; padding: 10px; text-align: center; min-width: 40px; }
        .name-col { text-align: left; min-width: 250px; position: sticky; left: 0; background: #0a0a0a; color: var(--gold); font-weight: bold; z-index: 10; border-right: 2px solid var(--gold); }
        
        .total-row { background: #111; font-weight: bold; color: var(--gold); }
        .total-hs { background: #1a1a1a; color: var(--gold); font-weight: bold; }

        /* Estados Colores */
        .st-12 { background: #1b4332 !important; cursor: pointer; }
        .st-F { color: #444; cursor: pointer; }
        .st-ART { background: #5a1818 !important; cursor: pointer; }
        .st-VAC { background: #03045e !important; cursor: pointer; }

        /* Archivos */
        .file-item { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #222; background: #080808; margin-top: 5px; border-radius: 5px; }
        
        /* Estilos Impresión */
        #print-area-nomina, #print-area-puestos { color: black !important; background: white !important; }
        #print-area-nomina table, #print-area-puestos table { border: 1px solid black; width: 100%; border-collapse: collapse; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 5px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
         <h1 style="margin:0; letter-spacing: 5px;">TANDANOR <span style="color:var(--gold)">WATCHMAN</span></h1>
        <p style="color:#666; font-size: 12px; margin:5px 0 0 0;">TANDANOR / WATCHMAN | v41</p>
    </div>

    <nav>
        <button id="btn-pla" class="active" onclick="show('pla')">Planilla Mensual</button>
        <button id="btn-pue" onclick="show('pue')">Puestos Guardias Diaria</button>
        <button id="btn-per" onclick="show('per')">Personal</button>
        <button id="btn-inf" onclick="show('inf')">Informes</button>
        <button id="btn-arc" onclick="show('arc')">Archivos Historial</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA -->
        <div id="sec-pla" class="section active-section">
            <div class="box flex-form">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
            </div>
            <div class="table-container" id="area-planilla">
                <table>
                    <thead id="h-table"></thead>
                    <tbody id="b-table"></tbody>
                    <tfoot id="f-table"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="sec-pue" class="section">
            <div class="box flex-form">
                <input type="text" id="pue-n" placeholder="Nombre Puesto/Objetivo">
                <input type="text" id="pue-h" placeholder="Horario">
                <input type="number" id="pue-c" placeholder="Dotación">
                <button class="btn" onclick="addPue()">Agregar</button>
            </div>
            <div id="pue-list" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:20px;"></div>
        </div>

        <!-- PERSONAL -->
        <div id="sec-per" class="section">
            <div class="box flex-form">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPer()">Cargar Agente</button>
            </div>
            <div class="table-container">
                <table id="tbl-per-data">
                    <thead><tr><th>Legajo</th><th>Agente</th><th>Acción</th></tr></thead>
                    <tbody id="per-list"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="sec-inf" class="section">
            <div class="box" style="text-align:center">
                <h2 style="color:var(--gold)">CENTRO DE REPORTES</h2>
                <p>Genera documentos oficiales en formato PDF A3.</p>
                <div style="display:flex; justify-content:center; gap:20px; margin-top:30px;">
                    <button class="btn" onclick="pdf('planilla')">PLANILLA MENSUAL</button>
                    <button class="btn" onclick="pdf('nomina')">NÓMINA DE PERSONAL</button>
                    <button class="btn" onclick="pdf('puestos')">ESTADO DE PUESTOS</button>
                </div>
            </div>
            <!-- Áreas técnicas para PDF -->
            <div id="pdf-nomina" style="display:none"></div>
            <div id="pdf-puestos" style="display:none"></div>
        </div>

        <!-- ARCHIVOS -->
        <div id="sec-arc" class="section">
            <div class="box">
                <h2 style="color:var(--gold)">REGISTRO DE ARCHIVOS GENERADOS</h2>
                <div id="file-log">
                    <p style="color:#444">No se han generado archivos en esta sesión.</p>
                </div>
            </div>
        </div>

    </div>

    <script>
        let fileHistory = [];

        function show(s) {
            document.querySelectorAll('.section').forEach(e => e.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(e => e.classList.remove('active'));
            document.getElementById('sec-'+s).classList.add('active-section');
            document.getElementById('btn-'+s).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // 1. Header Planilla
            let h = `<tr><th class="name-col">AGENTES</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th class="total-hs">HS</th></tr>`;
            document.getElementById('h-table').innerHTML = h;

            // 2. Body Planilla & Calculos
            let b = "";
            let sumHs = new Array(dias).fill(0);
            let sumPer = new Array(dias).fill(0);

            per.forEach(p => {
                let rowHs = 0;
                let row = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado: 'F'};
                    if(n.estado == '12') { rowHs += 12; sumHs[i-1] += 12; sumPer[i-1]++; }
                    row += `<td class="st-${n.estado}" onclick="cycle(this, ${p.id}, '${f}')">${n.estado}</td>`;
                }
                row += `<td class="total-hs">${rowHs}</td>`;
                b += `<tr>${row}</tr>`;
            });
            document.getElementById('b-table').innerHTML = b;

            // 3. Footer Totales (LO QUE PEDISTE)
            let f1 = `<tr class="total-row"><td class="name-col">TOTAL HORAS SERVICIO</td>`;
            let f2 = `<tr class="total-row"><td class="name-col">PERSONAL PRESENTE</td>`;
            sumHs.forEach(v => f1 += `<td>${v}</td>`);
            sumPer.forEach(v => f2 += `<td>${v}</td>`);
            document.getElementById('f-table').innerHTML = f1 + "<td>-</td></tr>" + f2 + "<td>-</td></tr>";

            // 4. Listas Secundarias
            document.getElementById('per-list').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="background:none; border:none; color:red; cursor:pointer">Eliminar</button></td></tr>
            `).join('');

            document.getElementById('pue-list').innerHTML = pue.map(x => `
                <div class="box" style="border-left:4px solid var(--gold)">
                    <h3 style="margin:0">${x.nombre}</h3>
                    <p style="color:#888; font-size:14px">${x.horario} | Dotación: ${x.cantidad}</p>
                    <button onclick="delPue(${x.id})" style="font-size:11px; background:none; border:1px solid #333; color:#666; cursor:pointer">Quitar</button>
                </div>
            `).join('');
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let next = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})});
            render();
        }

        async function addPer() {
            const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function addPue() {
            const d = { nombre: document.getElementById('pue-n').value, horario: document.getElementById('pue-h').value, cantidad: document.getElementById('pue-c').value };
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function delPer(id) { if(confirm('¿Borrar?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
        async function delPue(id) { if(confirm('¿Borrar?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        function pdf(type) {
            const now = new Date();
            const ts = now.toLocaleString();
            let elId = "";
            let name = "";

            if(type === 'planilla') { elId = 'area-planilla'; name = `Planilla_${now.getTime()}.pdf`; }
            if(type === 'nomina') { 
                document.getElementById('pdf-nomina').innerHTML = "<h2>NOMINA DE PERSONAL</h2>" + document.getElementById('tbl-per-data').outerHTML;
                elId = 'pdf-nomina'; name = `Nomina_${now.getTime()}.pdf`;
            }
            if(type === 'puestos') {
                document.getElementById('pdf-puestos').innerHTML = "<h2>ESTADO DE PUESTOS</h2>" + document.getElementById('pue-list').innerHTML;
                elId = 'pdf-puestos'; name = `Puestos_${now.getTime()}.pdf`;
            }

            const opt = { margin: 10, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById(elId)).save().then(() => {
                fileHistory.push({ name: name, time: ts });
                updateArchive();
            });
        }

        function updateArchive() {
            const div = document.getElementById('file-log');
            div.innerHTML = fileHistory.map(f => `
                <div class="file-item">
                    <span><strong>📄 ${f.name}</strong></span>
                    <span style="color:var(--gold)">${f.time}</span>
                </div>
            `).reverse().join('');
        }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel'); const now = new Date();
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
