import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v23
DB_PATH = '/tmp/ordoklar_v23.db'

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

# --- APIs Mantenidas ---
@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        if 'id' in d and d['id']:
            conn.execute("UPDATE puestos SET nombre=?, horario=?, cantidad=? WHERE id=?", (d['nombre'], d['horario'], d['cantidad'], d['id']))
        else:
            conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['cantidad']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos/<int:id>', methods=['DELETE'])
def delete_puesto(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM puestos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
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

# --- INTERFAZ v23 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión Profesional</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        /* HEADER WEB */
        .header-web { text-align: center; padding: 20px; font-size: 26px; font-weight: 900; letter-spacing: 8px; border-bottom: 2px solid var(--gold); }
        
        /* REPORTE OFICIAL (PDF/PRINT) */
        .report-header { display: none; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 3px solid #000; margin-bottom: 20px; color: #000; background: #fff; }
        .report-header img { height: 80px; width: auto; object-fit: contain; }
        .report-title { text-align: center; flex: 1; }
        .report-title h1 { margin: 0; font-size: 22px; text-transform: uppercase; }

        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
        
        .content { padding: 20px; }
        .section { display: none; }
        .active { display: block; }

        .actions-bar { display: flex; gap: 15px; margin-bottom: 20px; padding: 15px; background: #111; border-radius: 8px; justify-content: center; border: 1px solid #222; }
        .btn-action { padding: 12px 18px; border-radius: 6px; font-weight: 900; cursor: pointer; border: none; text-transform: uppercase; font-size: 11px; display: flex; align-items: center; gap: 8px; }
        .btn-pdf { background: #2E7D32; color: white; }
        .btn-gold { background: var(--gold); color: black; }

        .form-box { background: var(--card); padding: 20px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 20px; }
        .form-box input { background: #000; color: #fff; border: 1px solid #444; padding: 10px; border-radius: 5px; margin: 5px; }

        .table-wrap { overflow-x: auto; border-radius: 12px; border: 2px solid var(--border); background: #000; }
        table { border-collapse: collapse; min-width: 1200px; width: 100%; }
        th, td { border: 1px solid #222; text-align: center; padding: 8px; font-size: 13px; }
        .name-col { width: 220px; text-align: left !important; color: var(--gold); font-weight: 800; position: sticky; left: 0; background: #111; z-index: 20; border-right: 3px solid var(--gold) !important; }
        .row-total { background: #111; font-weight: bold; color: var(--gold); }

        .card-puesto { background: #151515; border-left: 5px solid var(--gold); padding: 15px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .list-item { background: #111; padding: 12px; border-bottom: 1px solid #222; display: flex; gap: 40px; }

        @media print {
            .no-print, .nav, .header-web, .form-box { display: none !important; }
            body { background: #FFF; color: #000; }
            .report-header { display: flex !important; }
            .section { display: block !important; }
            table { color: #000 !important; border: 1px solid #000 !important; width: 100% !important; }
            th, td { border: 1px solid #000 !important; color: #000 !important; }
            .name-col { background: #eee !important; color: #000 !important; }
            .row-total { background: #eee !important; color: #000 !important; }
        }
    </style>
</head>
<body>

    <div class="header-web">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Guardias</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <!-- ENCABEZADO OFICIAL PDF -->
    <div id="report-header-ui" class="report-header">
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/TANDANOR.PNG" alt="Tandanor">
        <div class="report-title">
            <h1 id="rt-titulo">INFORME DE SERVICIO</h1>
            <p id="rt-subtitulo">SUBTÍTULO</p>
        </div>
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/WATCHMAN.SVG" alt="Watchman">
    </div>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active">
            <div class="actions-bar no-print">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
                <button class="btn-action btn-pdf" onclick="pdfPlanilla()">📄 INFORME MENSUAL (PDF)</button>
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
            <div class="actions-bar no-print">
                <button class="btn-action btn-pdf" onclick="pdfPuestos()">📄 DESCARGAR PDF GUARDIAS</button>
            </div>
            <div class="form-box no-print">
                <input type="hidden" id="p-id">
                <input type="text" id="p-nom" placeholder="Nombre Puesto">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-can" placeholder="Dotación">
                <button class="btn-action btn-gold" onclick="savePuesto()">GUARDAR</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="actions-bar no-print">
                <button class="btn-action btn-pdf" onclick="pdfPersonal()">📄 DESCARGAR PDF PERSONAL</button>
            </div>
            <div class="form-box no-print">
                <input type="text" id="i-leg" placeholder="Legajo">
                <input type="text" id="i-ape" placeholder="Apellido">
                <input type="text" id="i-nom" placeholder="Nombre">
                <button class="btn-action btn-gold" onclick="addPersonal()">REGISTRAR</button>
            </div>
            <div id="l-per" style="background: white; color: black; border-radius: 8px;"></div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const diasSemana = ["DOM","LUN","MAR","MIE","JUE","VIE","SAB"];

        function fillSelectors() {
            const m = document.getElementById('sel-mes');
            const a = document.getElementById('sel-anio');
            const now = new Date();
            meses.forEach((name, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${name}</option>`);
            for(let i=2024; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
        }

        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active');
            document.getElementById('n-'+t).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);
            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const cantDias = new Date(anio, mes, 0).getDate();

            // Render Cabecera Planilla
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=cantDias; i++) h += `<th>${i}</th>`;
            h += '<th>TOT</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            // Render Cuerpo y Totales
            let colHs = new Array(cantDias).fill(0);
            let colPer = new Array(cantDias).fill(0);

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                let hsFila = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { 
                        hsFila += 12; 
                        colHs[i-1] += 12; 
                        colPer[i-1] += 1; 
                    }
                    r += `<td><select class="no-print" onchange="updNov(${p.id},'${f}',this.value)" style="background:transparent; color:white; border:none;">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                    </select><span class="only-print" style="display:none">${st}</span></td>`;
                }
                return `<tr>${r}<td>${hsFila}</td></tr>`;
            }).join('');

            // Pie de tabla: Totales
            let f1 = `<tr class="row-total"><td class="name-col">CANT HS POR DIA</td>`;
            colHs.forEach(v => f1 += `<td>${v}</td>`);
            f1 += `<td>-</td></tr>`;

            let f2 = `<tr class="row-total"><td class="name-col">CANT DE PERSONAL</td>`;
            colPer.forEach(v => f2 += `<td>${v}</td>`);
            f2 += `<td>-</td></tr>`;

            document.getElementById('f-pla').innerHTML = f1 + f2;

            // Render Puestos y Personal List
            document.getElementById('g-pue').innerHTML = pue.map(p => `
                <div class="card-puesto">
                    <div><b>${p.nombre.toUpperCase()}</b><br><small>${p.horario} | Dotación: ${p.cantidad}</small></div>
                    <div class="no-print"><button onclick='editPuesto(${JSON.stringify(p)})'>EDITAR</button></div>
                </div>`).join('');

            document.getElementById('l-per').innerHTML = per.map(p => `
                <div class="list-item"><span><b>${p.legajo}</b></span> <span>${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</span></div>
            `).join('');
        }

        // --- FUNCIONES PDF (v23 ACTUALIZADAS) ---
        function genericPDF(titulo, subtitulo, filename, orientation='portrait') {
            document.getElementById('rt-titulo').innerText = titulo;
            document.getElementById('rt-subtitulo').innerText = subtitulo;
            document.getElementById('report-header-ui').style.display = 'flex';
            
            const element = document.body;
            const opt = {
                margin: 5,
                filename: filename,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2 },
                jsPDF: { unit: 'mm', format: orientation == 'landscape' ? 'a3' : 'a4', orientation: orientation }
            };

            html2pdf().set(opt).from(element).save().then(() => {
                document.getElementById('report-header-ui').style.display = 'none';
            });
        }

        function pdfPlanilla() {
            const m = meses[document.getElementById('sel-mes').value - 1];
            const a = document.getElementById('sel-anio').value;
            genericPDF("PLANILLA MENSUAL DE NOVEDADES", `${m.toUpperCase()} ${a}`, `Planilla_${m}.pdf`, 'landscape');
        }

        function pdfPuestos() {
            const n = new Date();
            genericPDF("ESTADO DE GUARDIAS / PUESTOS", `${n.toLocaleDateString()}`, "Reporte_Guardias.pdf");
        }

        function pdfPersonal() {
            genericPDF("PLANILLA DE PERSONAL REGISTRADO", "NOMINA GENERAL", "Nomina_Personal.pdf");
        }

        // --- CRUD LOGIC ---
        async function savePuesto() {
            const d = { id:document.getElementById('p-id').value, nombre:document.getElementById('p-nom').value, horario:document.getElementById('p-hor').value, cantidad:document.getElementById('p-can').value };
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function addPersonal() {
            const d = {nombre:document.getElementById('i-nom').value, apellido:document.getElementById('i-ape').value, legajo:document.getElementById('i-leg').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
