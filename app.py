import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de Datos
DB_PATH = os.path.abspath("ordoklar_v51_master.db")

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

# --- API ---

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

# --- INTERFAZ ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v51 | Sistema de Gestión</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); background: #111; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 11px; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 120px; }
        label { font-size: 10px; color: var(--gold); font-weight: bold; text-transform: uppercase; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 8px; border-radius: 4px; font-size: 13px; }

        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        .btn-red { background: #5a1818; color: #fff; border: none; padding: 5px 10px; cursor: pointer; border-radius: 3px; }

        /* PLANILLA */
        .table-wrap { width: 100%; border: 1px solid var(--border); background: #000; }
        table { width: 100%; border-collapse: collapse; font-size: 11px; }
        th, td { border: 1px solid #222; text-align: center; padding: 6px 3px; }
        .col-name { text-align: left; width: 180px; padding-left: 10px; color: var(--gold); font-weight: bold; }
        .st-12 { background: #1b4332; color: #fff; } 
        .st-ART { background: #5a1818; color: #fff; } 
        .st-VAC { background: #004e89; color: #fff; } 

        /* PUESTOS CARDS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }
        .card-pue { background: #0a0a0a; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 8px; position: relative; }
        .card-pue h3 { margin: 0 0 10px 0; color: var(--gold); font-size: 16px; border-bottom: 1px solid #222; padding-bottom: 5px;}
        .slot { background: #151515; padding: 5px 10px; margin-top: 5px; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; }
        .slot select { width: 70%; font-size: 11px; padding: 3px; }

        /* REPORTE PUESTOS */
        #area-puestos-reporte { padding: 20px; background: #000; }
        .report-header { text-align: center; border-bottom: 2px solid var(--gold); margin-bottom: 20px; padding-bottom: 10px; display: none; }

        /* ARCHIVOS */
        .arc-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #222; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 5px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
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
                <div class="form-group"><label>Mes</label><select id="m-sel" onchange="render()"></select></div>
                <div class="form-group"><label>Año</label><select id="a-sel" onchange="render()"></select></div>
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
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <div class="form-group"><label>Puesto</label><input type="text" id="p-nom"></div>
                    <div class="form-group"><label>Horario</label><input type="text" id="p-hor"></div>
                    <div class="form-group"><label>Dotación</label><input type="number" id="p-dot"></div>
                    <button class="btn" onclick="savePuesto()">Guardar Puesto</button>
                </div>
            </div>

            <!-- SELECTORES DE FECHA PARA EL INFORME -->
            <div class="box" style="background:#080808; border-color: var(--gold);">
                <label style="display:block; margin-bottom:10px;">Fecha del Informe de Guardias:</label>
                <div class="flex-row">
                    <div class="form-group"><label>Día</label><select id="rpt-dia"></select></div>
                    <div class="form-group"><label>Mes</label><select id="rpt-mes"></select></div>
                    <div class="form-group"><label>Año</label><select id="rpt-anio"></select></div>
                    <button class="btn" onclick="genPuePDF()">Imprimir Reporte Guardias</button>
                </div>
            </div>

            <!-- AREA DE IMPRESION DINAMICA -->
            <div id="area-puestos-reporte">
                <div id="report-title-head" class="report-header">
                    <h2 id="dynamic-title" style="color:var(--gold); margin:0;"></h2>
                </div>
                <div id="grid-pue" class="grid-pue"></div>
            </div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box flex-row">
                <div class="form-group"><label>Legajo</label><input type="text" id="per-l"></div>
                <div class="form-group"><label>Apellido</label><input type="text" id="per-a"></div>
                <div class="form-group"><label>Nombre</label><input type="text" id="per-n"></div>
                <button class="btn" onclick="addPersonal()">Alta</button>
            </div>
            <div class="box" id="area-nomina">
                <table style="width:100%">
                    <thead><tr><th class="col-name">Legajo</th><th>Agente</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="box" style="text-align:center; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px;">
                <div class="box"><h4>Planilla Mensual</h4><button class="btn" onclick="genPDF('area-planilla', 'Planilla')">PDF</button></div>
                <div class="box"><h4>Estructura Puestos</h4><button class="btn" onclick="genPuePDF()">PDF</button></div>
                <div class="box"><h4>Nómina Personal</h4><button class="btn" onclick="genPDF('area-nomina', 'Nomina')">PDF</button></div>
            </div>
        </div>

        <!-- ARCHIVOS -->
        <div id="s-arc" class="section">
            <div class="box">
                <h3 style="color:var(--gold)">Historial de Archivos</h3>
                <div id="list-arc"></div>
            </div>
        </div>

    </div>

    <script>
        const mesesNombres = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];

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

            // 1. Planilla
            let h = `<tr><th class="col-name">PERSONAL</th>`;
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
                r += `<td style="border-left:2px solid var(--gold); font-weight:bold; color:var(--gold)">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;
            document.getElementById('f-pla').innerHTML = `
                <tr style="background:#080808; color:var(--gold); font-weight:bold"><td class="col-name">TOTAL HORAS</td>${sumHs.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>
                <tr style="background:#080808; color:var(--gold); font-weight:bold"><td class="col-name">PRESENTES</td>${sumPr.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>`;

            // 2. Puestos con Asignación de Personal
            const perOptions = `<option value="">-- Sin Asignar --</option>` + per.map(p => `<option value="${p.id}">${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let slots = "";
                for(let i=1; i<=x.dotacion; i++) {
                    slots += `<div class="slot"><span>Posición ${i}</span><select>${perOptions}</select></div>`;
                }
                return `<div class="card-pue">
                    <div style="float:right">
                        <button onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.dotacion})" style="background:none; border:1px solid var(--gold); color:var(--gold); cursor:pointer; font-size:9px">EDIT</button>
                        <button onclick="delPue(${x.id})" style="background:none; border:1px solid #5a1818; color:red; cursor:pointer; font-size:9px; margin-left:5px">X</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <p style="font-size:11px; color:#555; margin-bottom:10px">${x.horario} | Requerido: ${x.dotacion}</p>
                    ${slots}
                </div>`;
            }).join('');

            // 3. Nómina y Archivos
            document.getElementById('list-per').innerHTML = per.map(p => `<tr><td class="col-name">${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td><td><button class="btn-red" onclick="delPer(${p.id})">X</button></td></tr>`).join('');
            document.getElementById('list-arc').innerHTML = arc.map(x => `
                <div class="arc-item">
                    <span>📄 ${x.nombre}</span><span style="color:#444">${x.fecha}</span>
                    <button class="btn-red" onclick="delArc(${x.id})">ELIMINAR</button>
                </div>`).join('');
        }

        async function genPuePDF() {
            const d = document.getElementById('rpt-dia').value;
            const m = mesesNombres[document.getElementById('rpt-mes').value - 1];
            const a = document.getElementById('rpt-anio').value;
            
            const title = `GUARDIAS ${d} DEL ${m} DEL AÑO ${a}`;
            document.getElementById('dynamic-title').innerText = title;
            document.getElementById('report-title-head').style.display = "block";

            const opt = { margin: 10, filename: `Guardias_${d}_${m}.pdf`, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            
            html2pdf().set(opt).from(document.getElementById('area-puestos-reporte')).save().then(async () => {
                document.getElementById('report-title-head').style.display = "none";
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: `Reporte_${title}`, tipo: 'PDF', fecha: new Date().toLocaleString()})});
                render();
            });
        }

        async function genPDF(divId, label) {
            const name = `${label}_${Date.now()}.pdf`;
            const opt = { margin: 10, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            html2pdf().set(opt).from(document.getElementById(divId)).save().then(async () => {
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: name, tipo: 'PDF', fecha: new Date().toLocaleString()})});
                render();
            });
        }

        // --- Funciones de Soporte ---
        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let n = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:n})});
            render();
        }

        async function savePuesto() {
            const id = document.getElementById('p-id').value;
            const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            if(id) { d.id = id; await fetch('/api/puestos', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); }
            else { await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); }
            document.getElementById('p-id').value=""; render();
        }

        function editPue(id, n, h, d) { document.getElementById('p-id').value=id; document.getElementById('p-nom').value=n; document.getElementById('p-hor').value=h; document.getElementById('p-dot').value=d; }
        async function delPue(id) { if(confirm("¿Eliminar?")) await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }
        async function delPer(id) { if(confirm("¿Baja?")) await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delArc(id) { await fetch(`/api/archivos?id=${id}`, {method:'DELETE'}); render(); }
        async function addPersonal() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); render();
        }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            const rD = document.getElementById('rpt-dia'); const rM = document.getElementById('rpt-mes'); const rA = document.getElementById('rpt-anio');
            
            mesesNombres.forEach((n, i) => {
                m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`;
                rM.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`;
            });

            for(let i=2025; i<=2026; i++) {
                const opt = `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
                a.innerHTML += opt; rA.innerHTML += opt;
            }

            for(let i=1; i<=31; i++) {
                rD.innerHTML += `<option value="${i}" ${i==new Date().getDate()?'selected':''}>${i}</option>`;
            }

            render();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
