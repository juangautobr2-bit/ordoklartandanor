import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de Datos con Ruta Absoluta para persistencia total
DB_PATH = os.path.abspath("ordoklar_v47_master.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    c.execute('CREATE TABLE IF NOT EXISTS historial_archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT, fecha TEXT)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API ENDPOINTS ---

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

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE', 'PUT'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['dotacion']))
        conn.commit()
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE puestos SET nombre=?, horario=?, dotacion=? WHERE id=?", (d['nombre'], d['horario'], d['dotacion'], d['id']))
        conn.commit()
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
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
        conn.execute("INSERT INTO historial_archivos (nombre, tipo, fecha) VALUES (?, ?, ?)", (d['nombre'], d['tipo'], d['fecha']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM historial_archivos ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(res)

# --- INTERFAZ HTML ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v47 | Master System</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #666; padding: 12px 20px; cursor: pointer; font-weight: bold; font-size: 12px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 15px; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 15px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; flex: 1; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }

        /* PLANILLA RESPONSIVA */
        .table-wrap { width: 100%; overflow: hidden; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }
        th, td { border: 1px solid #222; text-align: center; padding: 4px 0; overflow: hidden; }
        .col-name { text-align: left; width: 140px; padding-left: 5px; color: var(--gold); font-weight: bold; font-size: 11px; }
        .col-total { width: 35px; background: #151515; font-weight: bold; color: var(--gold); }
        .row-total { background: #080808; color: var(--gold); font-weight: bold; }

        /* Estados */
        .st-12 { background: #1b4332; } .st-ART { background: #5a1818; } .st-VAC { background: #004e89; } .st-F { color: #444; }

        /* Puestos */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .card-pue { background: #080808; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 6px; position: relative; }
        .btn-sm { padding: 4px 8px; font-size: 10px; cursor: pointer; border-radius: 3px; border: none; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 3px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
    </div>

    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box flex-row">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
            </div>
            <div class="table-wrap" id="area-impresion">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="box">
                <h3 id="pue-titulo" style="margin-top:0; color:var(--gold)">Configurar Puesto</h3>
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <input type="text" id="p-nom" placeholder="Objetivo">
                    <input type="text" id="p-hor" placeholder="Horario">
                    <input type="number" id="p-dot" placeholder="Dotación">
                    <button class="btn" onclick="savePuesto()">Guardar</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box flex-row">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">Alta</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th class="col-name">Legajo</th><th>Agente</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="box" style="text-align:center">
                <h2 style="color:var(--gold)">Generación de Documentos PDF</h2>
                <button class="btn" onclick="genPDF('Planilla_Mensual')">Exportar Planilla Actual</button>
            </div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div class="box">
                <h3 style="color:var(--gold)">Historial de Archivos Generados</h3>
                <div id="list-arc"></div>
            </div>
        </div>

    </div>

    <script>
        function tab(t) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active-section');
            document.getElementById('n-'+t).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/archivos').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // 1. Render Planilla
            let h = `<tr><th class="col-name">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th class="col-total">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = "";
            let sumHs = new Array(dias).fill(0);
            let sumPr = new Array(dias).fill(0);

            per.forEach(p => {
                let rowHs = 0;
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre[0]}.</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    if(d.estado == '12') { rowHs += 12; sumHs[i-1]+=12; sumPr[i-1]++; }
                    r += `<td class="st-${d.estado}" onclick="cycle(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                r += `<td class="col-total">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;

            let f1 = `<tr class="row-total"><td class="col-name">HORAS TOTALES</td>`;
            let f2 = `<tr class="row-total"><td class="col-name">PRESENTE</td>`;
            sumHs.forEach(v => f1 += `<td>${v}</td>`);
            sumPr.forEach(v => f2 += `<td>${v}</td>`);
            document.getElementById('f-pla').innerHTML = f1 + "<td>-</td></tr>" + f2 + "<td>-</td></tr>";

            // 2. Render Puestos
            document.getElementById('grid-pue').innerHTML = pue.map(x => `
                <div class="card-pue">
                    <div style="float:right">
                        <button class="btn-sm" style="background:#333; color:#fff" onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.dotacion})">EDIT</button>
                        <button class="btn-sm" style="background:#5a1818; color:#fff" onclick="delPue(${x.id})">DEL</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <p style="font-size:12px; color:#777">H: ${x.horario} | Requerido: ${x.dotacion}</p>
                </div>`).join('');

            // 3. Render Otros
            document.getElementById('list-per').innerHTML = per.map(p => `<tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td><td><button onclick="delPer(${p.id})">X</button></td></tr>`).join('');
            document.getElementById('list-arc').innerHTML = arc.map(x => `<div style="padding:10px; border-bottom:1px solid #222">📄 ${x.nombre} <span style="float:right; color:#444">${x.fecha}</span></div>`).join('');
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let n = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:n})});
            render();
        }

        async function savePuesto() {
            const id = document.getElementById('p-id').value;
            const data = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            if(id) { data.id = id; await fetch('/api/puestos', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
            else { await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)}); }
            document.getElementById('p-id').value = ""; render();
        }

        function editPue(id, n, h, d) {
            document.getElementById('p-id').value = id; document.getElementById('p-nom').value = n;
            document.getElementById('p-hor').value = h; document.getElementById('p-dot').value = d;
        }

        async function genPDF(tipo) {
            const name = `${tipo}_${Date.now()}.pdf`;
            const opt = { margin: 5, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById('area-impresion')).save().then(async () => {
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: name, tipo: tipo, fecha: new Date().toLocaleString()})});
                render();
            });
        }

        async function addPersonal() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); render();
        }

        async function delPer(id) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delPue(id) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
