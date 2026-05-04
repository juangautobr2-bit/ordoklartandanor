import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v32
DB_PATH = '/tmp/ordoklar_v32.db'

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
        conn.execute("UPDATE puestos SET nombre=?, apellido=?, legajo=? WHERE id=?", (d['nombre'], d['horario'], d['cantidad'], d['id']))
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
    <title>ORDO KLAR | Gestión Técnica</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
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

        /* PANEL INFORMES */
        .info-panel { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .info-card { background: var(--card); border: 1px solid var(--border); padding: 25px; border-radius: 8px; text-align: center; transition: 0.3s; }
        .info-card:hover { border-color: var(--gold); }
        .info-card h3 { color: var(--gold); margin-bottom: 15px; letter-spacing: 2px; }
        
        /* ARCHIVOS */
        .file-list { background: #0a0a0a; border: 1px solid #222; border-radius: 8px; padding: 20px; }
        .file-item { display: flex; justify-content: space-between; padding: 12px; border-bottom: 1px solid #222; align-items: center; }
        .file-item:last-child { border: none; }

        /* TABLAS Y FORMULARIOS */
        .table-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid var(--border); margin-top: 15px; }
        table { width: 100%; border-collapse: collapse; background: #000; }
        th, td { border: 1px solid #222; padding: 12px; text-align: center; font-size: 12px; }
        th { background: #111; color: var(--gold); text-transform: uppercase; }
        .name-col { text-align: left; color: var(--gold); font-weight: bold; position: sticky; left: 0; background: #111; z-index: 10; border-right: 3px solid var(--gold); }

        .form-box { background: var(--card); padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; border: 1px solid var(--border); }
        .form-box input { background: #000; border: 1px solid var(--border); color: #fff; padding: 10px; border-radius: 4px; }
        
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 12px 20px; font-weight: 900; cursor: pointer; border-radius: 4px; text-transform: uppercase; width: 100%; }
        .btn-gold:hover { background: #fff; }

        /* ESTADOS */
        .cell-12 { background: #1B5E20 !important; }
        .cell-F { background: #333 !important; }
        .cell-ART { background: #B71C1C !important; }
        select { background: transparent; color: white; border: none; text-align-last: center; width: 100%; cursor: pointer; }

        @media print {
            .no-print { display: none !important; }
            body { background: white; color: black; }
            .header-main { border-bottom: 4px solid black; }
            table { color: black !important; border: 1px solid #000; }
            th, td { border: 1px solid #000 !important; color: black !important; }
            .name-col { background: white !important; }
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
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>

    <div class="content">
        <!-- SECCIÓN PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="no-print" style="display:flex; justify-content: flex-end; gap: 10px; margin-bottom: 15px;">
                <select id="sel-mes" onchange="render()" style="background:#111; color:white; padding:10px; border:1px solid #333;"></select>
                <select id="sel-anio" onchange="render()" style="background:#111; color:white; padding:10px; border:1px solid #333;"></select>
            </div>
            <div class="table-wrap">
                <table id="pdf-planilla">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- SECCIÓN INFORMES -->
        <div id="s-inf" class="section">
            <h2 style="color:var(--gold); text-align:center; letter-spacing:4px;">INFORMES</h2>
            <div class="info-panel">
                <div class="info-card">
                    <h3>PLANILLA MENSUAL</h3>
                    <p>Reporte de servicios, horas totales y personal por día.</p>
                    <button class="btn-gold" onclick="exportar('planilla')">GENERAR PDF (A3)</button>
                </div>
                <div class="info-card">
                    <h3>NÓMINA PERSONAL</h3>
                    <p>Listado completo de agentes activos y sus legajos.</p>
                    <button class="btn-gold" onclick="exportar('personal')">GENERAR PDF (A4)</button>
                </div>
                <div class="info-card">
                    <h3>ESTRUCTURA GUARDIAS</h3>
                    <p>Detalle de puestos, horarios y dotación requerida.</p>
                    <button class="btn-gold" onclick="exportar('puestos')">GENERAR PDF (A4)</button>
                </div>
            </div>
        </div>

        <!-- SECCIÓN ARCHIVOS -->
        <div id="s-arc" class="section">
            <h2 style="color:var(--gold); letter-spacing:4px;">ARCHIVOS GENERADOS</h2>
            <div class="file-list" id="file-history">
                <p style="text-align:center; color:#555;">No hay registros de descargas en esta sesión.</p>
            </div>
        </div>

        <!-- SECCIÓN PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="pue-id">
                <input type="text" id="pue-nom" placeholder="Puesto">
                <input type="text" id="pue-hor" placeholder="Horario">
                <input type="number" id="pue-can" placeholder="Cantidad">
                <button class="btn-gold" onclick="savePuesto()" style="width:auto">GUARDAR</button>
            </div>
            <div class="table-wrap">
                <table id="pdf-puestos">
                    <thead><tr><th>PUESTO</th><th>HORARIO</th><th>CANTIDAD</th><th class="no-print">ACCIONES</th></tr></thead>
                    <tbody id="b-pue"></tbody>
                </table>
            </div>
        </div>

        <!-- SECCIÓN PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box no-print">
                <input type="hidden" id="per-id">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()" style="width:auto">GUARDAR</button>
            </div>
            <div class="table-wrap">
                <table id="pdf-personal">
                    <thead><tr><th>LEGAJO</th><th>APELLIDO Y NOMBRE</th><th class="no-print">ACCIONES</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        let archivosRecientes = [];

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

            // Header Tabla
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th>TOTAL</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            // Body Tabla
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                let sum = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = n ? n.estado : 'F';
                    if(st == '12') { sum += 12; hsDia[i-1] += 12; perDia[i-1] += 1; }
                    r += `<td class="cell-${st}"><select class="no-print" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="ART" ${st=='ART'?'selected':''}>ART</option>
                    </select><span style="display:none" class="no-web">${st}</span></td>`;
                }
                return `<tr>${r}<td><b>${sum}</b></td></tr>`;
            }).join('');

            // Totales
            let f1 = `<tr style="background:#111; color:var(--gold); font-weight:bold;"><td class="name-col">CANT HS DIA</td>`;
            hsDia.forEach(v => f1 += `<td>${v}</td>`);
            f1 += `<td>-</td></tr>`;
            let f2 = `<tr style="background:#111; color:var(--gold); font-weight:bold;"><td class="name-col">PERSONAL DIA</td>`;
            perDia.forEach(v => f2 += `<td>${v}</td>`);
            f2 += `<td>-</td></tr>`;
            document.getElementById('f-pla').innerHTML = f1 + f2;

            // Listados CRUD
            document.getElementById('b-pue').innerHTML = pue.map(x => `<tr><td>${x.nombre}</td><td>${x.horario}</td><td>${x.cantidad}</td><td class="no-print"><button onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.cantidad})" style="background:#1976D2; color:white; border:none; padding:5px; cursor:pointer;">EDITAR</button></td></tr>`).join('');
            document.getElementById('b-per').innerHTML = per.map(x => `<tr><td>${x.legajo}</td><td class="name-col">${x.apellido.toUpperCase()}, ${x.nombre}</td><td class="no-print"><button onclick="editPer(${x.id},'${x.legajo}','${x.apellido}','${x.nombre}')" style="background:#1976D2; color:white; border:none; padding:5px; cursor:pointer;">EDITAR</button></td></tr>`).join('');
        }

        // --- SISTEMA DE INFORMES Y ARCHIVOS ---
        function exportar(tipo) {
            let el, nom, fmt, ori;
            const t = new Date().toLocaleString();

            if(tipo === 'planilla') {
                el = document.getElementById('pdf-planilla');
                nom = `OrdoKlar_Planilla_${meses[document.getElementById('sel-mes').value-1]}.pdf`;
                fmt = 'a3'; ori = 'landscape';
            } else if(tipo === 'personal') {
                el = document.getElementById('pdf-personal');
                nom = `OrdoKlar_Nomina_Personal.pdf`;
                fmt = 'a4'; ori = 'portrait';
            } else {
                el = document.getElementById('pdf-puestos');
                nom = `OrdoKlar_Estructura_Puestos.pdf`;
                fmt = 'a4'; ori = 'portrait';
            }

            const opt = { margin: 10, filename: nom, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: fmt, orientation: ori } };
            html2pdf().set(opt).from(el).save();
            
            archivosRecientes.push({ nombre: nom, fecha: t });
            actualizarHistorial();
        }

        function actualizarHistorial() {
            const h = document.getElementById('file-history');
            h.innerHTML = archivosRecientes.map(f => `
                <div class="file-item">
                    <span>📄 <b>${f.nombre}</b></span>
                    <span style="color:#888;">${f.fecha}</span>
                    <span style="color:var(--gold); font-size:10px;">GENERADO ✅</span>
                </div>
            `).reverse().join('');
        }

        // Acciones Auxiliares
        async function savePersonal() {
            const d = { id: document.getElementById('per-id').value, legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value };
            await fetch('/api/personal', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPer(id, l, a, n) { document.getElementById('per-id').value=id; document.getElementById('per-leg').value=l; document.getElementById('per-ape').value=a; document.getElementById('per-nom').value=n; }

        async function savePuesto() {
            const d = { id: document.getElementById('pue-id').value, nombre: document.getElementById('pue-nom').value, horario: document.getElementById('pue-hor').value, cantidad: document.getElementById('pue-can').value };
            await fetch('/api/puestos', { method: d.id ? 'PUT' : 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            reset(); render();
        }
        function editPue(id, n, h, c) { document.getElementById('pue-id').value=id; document.getElementById('pue-nom').value=n; document.getElementById('pue-hor').value=h; document.getElementById('pue-can').value=c; }

        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }
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
