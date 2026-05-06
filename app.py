import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# RUTA ABSOLUTA PARA PERSISTENCIA TOTAL
DB_PATH = os.path.abspath("ordoklar_v42_master.db")

def get_db_connection():
    """Conexión robusta con bloqueo de seguridad y escritura inmediata."""
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA synchronous = EXTRA")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicialización de todas las tablas para que existan en el tiempo."""
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla de Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    # Tabla de Puestos
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)')
    # Tabla de Planilla Mensual (Novedades)
    c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    # Tabla de Historial de Informes (Persistencia de archivos generados)
    c.execute('CREATE TABLE IF NOT EXISTS historial_archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_archivo TEXT, tipo TEXT, fecha_creacion TEXT)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs CON PERSISTENCIA ---
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

@app.route('/api/archivos', methods=['GET', 'POST'])
def handle_archivos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO historial_archivos (nombre_archivo, tipo, fecha_creacion) VALUES (?, ?, ?)", (d['nombre'], d['tipo'], d['fecha']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM historial_archivos ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(res)

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v42 | Máxima Visibilidad</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; overflow-x: hidden; }
        
        .header { text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #777; padding: 15px 25px; cursor: pointer; font-weight: bold; font-size: 14px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; width: 100vw; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        /* PLANILLA RESPONSIVA AL ANCHO (SIN SCROLL) */
        .table-responsive { width: 100%; overflow: hidden; background: #000; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 11px; }
        th, td { border: 1px solid #222; text-align: center; padding: 6px 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        
        .name-col { text-align: left; width: 180px; padding-left: 10px; color: var(--gold); font-weight: bold; font-size: 12px; }
        .day-col { width: auto; } /* Se ajusta al resto del espacio */
        .total-col { width: 45px; background: #111; font-weight: bold; color: var(--gold); }

        /* Inputs de Diseño Premium */
        .box { background: var(--card); padding: 20px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 20px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 12px; border-radius: 5px; font-size: 14px; flex: 1; }
        .btn { background: var(--gold); color: #000; border: none; padding: 12px 25px; font-weight: bold; border-radius: 5px; cursor: pointer; }

        /* Estados */
        .st-12 { background: #1b4332 !important; color: white; cursor: pointer; font-weight: bold; }
        .st-F { color: #444; cursor: pointer; }
        .st-ART { background: #5a1818 !important; color: white; cursor: pointer; }
        .st-VAC { background: #03045e !important; color: white; cursor: pointer; }

        /* Footer de Totales */
        .f-total { background: #080808; color: var(--gold); font-weight: bold; font-size: 10px; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 4px; font-size: 28px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#555; font-size: 11px; margin:0;">SISTEMA TÉCNICO DE GESTIÓN v42</p>
    </div>

    <nav>
        <button id="b-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="b-pue" onclick="tab('pue')">Puestos</button>
        <button id="b-per" onclick="tab('per')">Personal</button>
        <button id="b-inf" onclick="tab('inf')">Informes</button>
        <button id="b-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="container">
        
        <div id="s-pla" class="section active-section">
            <div class="box flex-row">
                <select id="sel-m" onchange="render()"></select>
                <select id="sel-a" onchange="render()"></select>
            </div>
            <div class="table-responsive" id="area-planilla">
                <table>
                    <thead id="h-table"></thead>
                    <tbody id="b-table"></tbody>
                    <tfoot id="f-table"></tfoot>
                </table>
            </div>
        </div>

        <div id="s-inf" class="section">
            <div class="box" style="text-align:center">
                <h2 style="color:var(--gold)">GENERADOR DE REPORTES</h2>
                <div style="display:flex; justify-content:center; gap:15px; margin-top:20px;">
                    <button class="btn" onclick="genPDF('planilla')">PLANILLA PDF</button>
                    <button class="btn" onclick="genPDF('nomina')">NÓMINA PDF</button>
                    <button class="btn" onclick="genPDF('puestos')">PUESTOS PDF</button>
                </div>
            </div>
            <div id="pdf-tmp" style="display:none; background:white; color:black; padding:20px;"></div>
        </div>

        <div id="s-arc" class="section">
            <div class="box">
                <h2 style="color:var(--gold)">HISTORIAL PERMANENTE</h2>
                <div id="arc-list"></div>
            </div>
        </div>

        <div id="s-pue" class="section">
            <div class="box flex-row">
                <input type="text" id="pue-n" placeholder="Nombre Puesto">
                <input type="text" id="pue-h" placeholder="Horario">
                <input type="number" id="pue-c" placeholder="Dotación">
                <button class="btn" onclick="addPue()">Guardar</button>
            </div>
            <div id="pue-list" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap:15px;"></div>
        </div>

        <div id="s-per" class="section">
            <div class="box flex-row">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPer()">Registrar</button>
            </div>
            <div class="table-responsive">
                <table id="tbl-per-master">
                    <thead><tr><th class="name-col">Legajo</th><th>Agente</th><th>Acción</th></tr></thead>
                    <tbody id="per-list"></tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
        function tab(t) {
            document.querySelectorAll('.section').forEach(e => e.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(e => e.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active-section');
            document.getElementById('b-'+t).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/archivos').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('sel-m').value);
            const a = parseInt(document.getElementById('sel-a').value);
            const dias = new Date(a, m, 0).getDate();

            // Render Planilla (Ajuste de ancho automático)
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th class="day-col">${i}</th>`;
            h += `<th class="total-col">HS</th></tr>`;
            document.getElementById('h-table').innerHTML = h;

            let b = "";
            let sHs = new Array(dias).fill(0);
            let sPr = new Array(dias).fill(0);

            per.forEach(p => {
                let pHs = 0;
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    if(n.estado == '12'){ pHs += 12; sHs[i-1] += 12; sPr[i-1]++; }
                    r += `<td class="st-${n.estado}" onclick="cycle(this, ${p.id}, '${f}')">${n.estado}</td>`;
                }
                r += `<td class="total-col">${pHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-table').innerHTML = b;

            let f1 = `<tr class="f-total"><td class="name-col">HORAS TOTALES</td>`;
            let f2 = `<tr class="f-total"><td class="name-col">PERSONAL ACTIVO</td>`;
            sHs.forEach(v => f1 += `<td>${v}</td>`);
            sPr.forEach(v => f2 += `<td>${v}</td>`);
            document.getElementById('f-table').innerHTML = f1 + "<td>-</td></tr>" + f2 + "<td>-</td></tr>";

            // Listas
            document.getElementById('per-list').innerHTML = per.map(p => `<tr><td class="name-col">${p.legajo}</td><td>${p.apellido} ${p.nombre}</td><td><button onclick="delPer(${p.id})">X</button></td></tr>`).join('');
            document.getElementById('pue-list').innerHTML = pue.map(x => `<div class="box" style="border-left:4px solid var(--gold)"><strong>${x.nombre}</strong><br><small>${x.horario}</small></div>`).join('');
            
            // Archivos Persistentes
            document.getElementById('arc-list').innerHTML = arc.map(x => `<div style="padding:10px; border-bottom:1px solid #222">📄 ${x.nombre_archivo} <span style="color:#555">(${x.fecha_creacion})</span></div>`).join('');
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let n = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:n})});
            render();
        }

        async function addPer() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function addPue() {
            const d = {nombre: document.getElementById('pue-n').value, horario: document.getElementById('pue-h').value, cantidad: document.getElementById('pue-c').value};
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function genPDF(type) {
            const now = new Date();
            const ts = now.toLocaleString();
            let elId = "area-planilla";
            let name = `Reporte_${type}_${now.getTime()}.pdf`;

            if(type !== 'planilla'){
                const el = document.getElementById(type === 'nomina' ? 'tbl-per-master' : 'pue-list');
                document.getElementById('pdf-tmp').innerHTML = `<h1>REPORTE ${type.toUpperCase()}</h1>` + el.outerHTML;
                elId = 'pdf-tmp';
            }

            const opt = { margin: 5, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById(elId)).save().then(async () => {
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: name, tipo: type, fecha: ts})});
                render();
            });
        }

        window.onload = () => {
            const m = document.getElementById('sel-m'); const a = document.getElementById('sel-a'); const now = new Date();
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
