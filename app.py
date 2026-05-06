import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de Datos - Persistencia garantizada
DB_PATH = os.path.abspath("ordoklar_v50_master.db")

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

# --- API CONTROLADORES ---

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

@app.route('/api/archivos', methods=['GET', 'POST', 'DELETE'])
def handle_archivos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO historial_archivos (nombre, tipo, fecha) VALUES (?, ?, ?)", (d['nombre'], d['tipo'], d['fecha']))
        conn.commit()
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM historial_archivos WHERE id=?", (request.args.get('id'),))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM historial_archivos ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(res)

# --- INTERFAZ DE USUARIO (HTML/CSS/JS) ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v50 | Sistema de Gestión</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); background: linear-gradient(to bottom, #111, #000); }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); sticky; top: 0; z-index: 100; }
        nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 12px; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 150px; }
        label { font-size: 11px; color: var(--gold); font-weight: bold; text-transform: uppercase; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; outline: none; }
        input:focus { border-color: var(--gold); }

        .btn { background: var(--gold); color: #000; border: none; padding: 12px 24px; font-weight: bold; cursor: pointer; border-radius: 4px; transition: 0.3s; }
        .btn:hover { background: #fff; }
        .btn-del { background: #5a1818; color: #fff; border: none; padding: 8px 15px; cursor: pointer; border-radius: 4px; }

        /* PLANILLA TABLA */
        .table-wrap { width: 100%; overflow-x: auto; border: 1px solid var(--border); background: #000; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; }
        th, td { border: 1px solid #222; text-align: center; padding: 6px 3px; }
        th { background: #111; color: var(--gold); }
        .col-name { text-align: left; width: 180px; padding-left: 10px; font-weight: bold; color: var(--gold); }
        .col-total { width: 45px; background: #151515; font-weight: bold; color: var(--gold); border-left: 2px solid var(--gold); }
        .row-total { background: #080808; color: var(--gold); font-weight: bold; }

        /* Estados Novedades */
        .st-12 { background: #1b4332; color: #fff; } 
        .st-ART { background: #5a1818; color: #fff; } 
        .st-VAC { background: #004e89; color: #fff; } 
        .st-F { color: #555; }

        /* PUESTOS CARDS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
        .card-pue { background: #0a0a0a; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 8px; position: relative; }
        .card-pue h3 { margin: 0; color: var(--gold); }
        .slot { background: #151515; padding: 6px; margin-top: 5px; border-radius: 4px; display: flex; justify-content: space-between; font-size: 11px; }

        /* ARCHIVOS */
        .arc-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; border-bottom: 1px solid #222; }
        .arc-item:hover { background: #0d0d0d; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 5px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#555; font-size:10px; margin-top:5px; text-transform: uppercase;">Módulo de Gestión de Seguridad e Higiene</p>
    </div>

    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Gestión Puestos</button>
        <button id="n-per" onclick="tab('per')">Nómina Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box flex-row">
                <div class="form-group"><label>Seleccionar Mes</label><select id="m-sel" onchange="render()"></select></div>
                <div class="form-group"><label>Seleccionar Año</label><select id="a-sel" onchange="render()"></select></div>
            </div>
            <div class="table-wrap" id="area-planilla">
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
                <h3 id="pue-form-title" style="margin-top:0; color:var(--gold)">Configurar Nuevo Objetivo</h3>
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <div class="form-group"><label>Nombre del Puesto</label><input type="text" id="p-nom"></div>
                    <div class="form-group"><label>Rango Horario</label><input type="text" id="p-hor"></div>
                    <div class="form-group"><label>Dotación Requerida</label><input type="number" id="p-dot"></div>
                    <button class="btn" onclick="savePuesto()">Guardar Cambios</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box flex-row">
                <div class="form-group"><label>Legajo</label><input type="text" id="per-l"></div>
                <div class="form-group"><label>Apellido</label><input type="text" id="per-a"></div>
                <div class="form-group"><label>Nombre</label><input type="text" id="per-n"></div>
                <button class="btn" onclick="addPersonal()">Alta de Agente</button>
            </div>
            <div class="box" id="area-nomina">
                <table style="width:100%">
                    <thead><tr><th class="col-name">Legajo</th><th>Apellido y Nombre</th><th>Gestión</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="box" style="text-align:center">
                <h2 style="color:var(--gold)">Centro de Impresión y Reportes</h2>
                <p style="color:#888">Seleccione el documento que desea exportar a formato PDF:</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 30px;">
                    <div class="box" style="background:#080808">
                        <h4>PLANILLA DE NOVEDADES</h4>
                        <button class="btn" onclick="genPDF('area-planilla', 'Planilla_Mensual')">Exportar Planilla</button>
                    </div>
                    <div class="box" style="background:#080808">
                        <h4>ESTRUCTURA DE OBJETIVOS</h4>
                        <button class="btn" onclick="genPDF('grid-pue', 'Estructura_Puestos')">Exportar Puestos</button>
                    </div>
                    <div class="box" style="background:#080808">
                        <h4>NÓMINA GENERAL</h4>
                        <button class="btn" onclick="genPDF('area-nomina', 'Nomina_Personal')">Exportar Nómina</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div class="box">
                <h3 style="color:var(--gold)">Historial de Documentos Generados</h3>
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

            // 1. Lógica de Planilla
            let h = `<tr><th class="col-name">LISTADO AGENTES</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th class="col-total">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = ""; let sumHs = new Array(dias).fill(0); let sumPr = new Array(dias).fill(0);
            per.forEach(p => {
                let rowHs = 0;
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
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
            let f = `<tr class="row-total"><td class="col-name">TOTAL HORAS</td>${sumHs.map(v=>`<td>${v}</td>`).join('')}<td class="col-total">-</td></tr>`;
            f += `<tr class="row-total"><td class="col-name">PERS. PRESENTE</td>${sumPr.map(v=>`<td>${v}</td>`).join('')}<td class="col-total">-</td></tr>`;
            document.getElementById('f-pla').innerHTML = f;

            // 2. Lógica de Puestos
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let s = ""; for(let i=1; i<=x.dotacion; i++) s+=`<div class="slot"><span>Posición ${i}</span><span style="color:#444">Sin Asignar</span></div>`;
                return `<div class="card-pue">
                    <div style="position:absolute; top:10px; right:10px;">
                        <button onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.dotacion})" style="background:none; border:1px solid var(--gold); color:var(--gold); cursor:pointer; font-size:10px; margin-right:5px">E</button>
                        <button onclick="delPue(${x.id})" style="background:none; border:1px solid #5a1818; color:#f55; cursor:pointer; font-size:10px">X</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <p style="font-size:12px; color:#666">${x.horario} | Dotación: ${x.dotacion}</p>${s}</div>`;
            }).join('');

            // 3. Nómina y Archivos
            document.getElementById('list-per').innerHTML = per.map(p => `<tr><td class="col-name">${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td><td><button class="btn-del" onclick="delPer(${p.id})">BAJA</button></td></tr>`).join('');
            document.getElementById('list-arc').innerHTML = arc.map(x => `
                <div class="arc-item">
                    <span>📄 ${x.nombre}</span>
                    <span style="color:#555; font-size:12px">${x.fecha}</span>
                    <button class="btn-del" onclick="delArc(${x.id})">ELIMINAR</button>
                </div>`).join('');
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let n = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:n})});
            render();
        }

        async function genPDF(divId, label) {
            const name = `${label}_${new Date().getTime()}.pdf`;
            const opt = { margin: 10, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById(divId)).save().then(async () => {
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: name, tipo: 'PDF', fecha: new Date().toLocaleString()})});
                render();
            });
        }

        async function savePuesto() {
            const id = document.getElementById('p-id').value;
            const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            if(id) { d.id = id; await fetch('/api/puestos', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); }
            else { await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); }
            document.getElementById('p-id').value=""; render();
        }

        function editPue(id, n, h, d) { document.getElementById('p-id').value=id; document.getElementById('p-nom').value=n; document.getElementById('p-hor').value=h; document.getElementById('p-dot').value=d; }
        async function delPue(id) { if(confirm("¿Eliminar puesto?")) await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }
        async function delPer(id) { if(confirm("¿Dar de baja al agente?")) await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delArc(id) { if(confirm("¿Borrar registro de archivo?")) await fetch(`/api/archivos?id=${id}`, {method:'DELETE'}); render(); }
        
        async function addPersonal() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); render();
        }

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
