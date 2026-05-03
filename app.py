import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v24
DB_PATH = '/tmp/ordoklar_v24.db'

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

# --- APIs (Mantienen funcionalidad) ---
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

# --- INTERFAZ v24 ---
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
        
        .header-web { text-align: center; padding: 20px; font-size: 26px; font-weight: 900; letter-spacing: 8px; border-bottom: 2px solid var(--gold); }
        
        /* ESTILOS DE REPORTE (PDF) */
        .report-header { display: none; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 4px solid #000; margin-bottom: 20px; color: #000; background: #fff; }
        .report-header img { height: 80px; width: auto; object-fit: contain; }
        .report-title { text-align: center; flex: 1; }
        .report-title h1 { margin: 0; font-size: 24px; text-transform: uppercase; font-weight: 900; }
        
        /* NAVEGACIÓN */
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 13px; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
        
        .content { padding: 20px; }
        .section { display: none; }
        .active-section { display: block; }

        .actions-bar { display: flex; gap: 15px; margin-bottom: 20px; padding: 15px; background: #111; border-radius: 8px; justify-content: center; border: 1px solid #222; }
        .btn-action { padding: 12px 18px; border-radius: 6px; font-weight: 900; cursor: pointer; border: none; text-transform: uppercase; font-size: 11px; display: flex; align-items: center; gap: 8px; }
        .btn-pdf { background: #2E7D32; color: white; }
        .btn-gold { background: var(--gold); color: black; }

        /* TABLA PLANILLA */
        .table-wrap { overflow-x: auto; border-radius: 12px; border: 2px solid var(--border); background: #000; }
        table { border-collapse: collapse; min-width: 1300px; width: 100%; }
        th, td { border: 1px solid #222; text-align: center; padding: 5px; font-size: 12px; }
        .name-col { width: 220px; text-align: left !important; color: var(--gold); font-weight: 800; position: sticky; left: 0; background: #111; z-index: 20; border-right: 3px solid var(--gold) !important; padding-left: 10px; }
        .row-total { background: #111; font-weight: bold; color: var(--gold); }

        /* COLORES DE ESTADOS */
        .cell-12 { background-color: #1B5E20 !important; color: white; } /* Verde Fuerte */
        .cell-F  { background-color: #424242 !important; color: white; } /* Gris */
        .cell-ART { background-color: #B71C1C !important; color: white; } /* Rojo */
        .cell-FE { background-color: #E65100 !important; color: white; } /* Naranja */
        .cell-VAC { background-color: #0D47A1 !important; color: white; } /* Azul */

        select.nov-select { background: transparent; color: white; border: none; width: 100%; height: 30px; cursor: pointer; text-align-last: center; font-weight: bold; }
        
        .card-puesto { background: #151515; border-left: 5px solid var(--gold); padding: 15px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .list-item { background: #111; padding: 12px; border-bottom: 1px solid #222; display: flex; gap: 40px; font-size: 16px; }

        @media print {
            .no-print, .nav, .header-web { display: none !important; }
            body { background: #FFF; color: #000; }
            .report-header { display: flex !important; }
            .section { display: block !important; }
            table { color: #000 !important; border: 1px solid #000 !important; min-width: 100% !important; }
            th, td { border: 1px solid #000 !important; }
            .name-col { background: #eee !important; color: #000 !important; }
            select { display: none; }
            .print-val { display: block !important; font-weight: bold; color: #000 !important; }
        }
    </style>
</head>
<body>

    <div class="header-web">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Guardias / Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <!-- CABECERA DE REPORTE PARA PDF -->
    <div id="report-header-ui" class="report-header">
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/TANDANOR.PNG" alt="Logo Tandanor">
        <div class="report-title">
            <h1 id="rt-titulo">INFORME DE SERVICIO</h1>
            <p id="rt-subtitulo">SUBTÍTULO DINÁMICO</p>
        </div>
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/WATCHMAN.SVG" alt="Logo Watchman">
    </div>

    <div class="content">
        <!-- SECCION PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="actions-bar no-print">
                <select id="sel-mes" onchange="render()" style="background:#000; color:var(--gold); padding:8px; border:1px solid var(--gold);"></select>
                <select id="sel-anio" onchange="render()" style="background:#000; color:var(--gold); padding:8px; border:1px solid var(--gold);"></select>
                <button class="btn-action btn-pdf" onclick="pdfPlanilla()">📄 EXPORTAR PLANILLA MENSUAL</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- SECCION PUESTOS -->
        <div id="s-pue" class="section">
            <div class="actions-bar no-print">
                <button class="btn-action btn-pdf" onclick="pdfPuestos()">📄 EXPORTAR GUARDIAS PDF</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <!-- SECCION PERSONAL -->
        <div id="s-per" class="section">
            <div class="actions-bar no-print">
                <button class="btn-action btn-pdf" onclick="pdfPersonal()">📄 EXPORTAR PERSONAL PDF</button>
            </div>
            <div id="l-per" style="background: white; color: black; border-radius: 8px; overflow: hidden;"></div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const diasSemana = ["DOM","LUN","MAR","MIE","JUE","VIE","SAB"];

        function getStatusClass(st) {
            if(st == '12') return 'cell-12';
            if(st == 'F') return 'cell-F';
            if(st == 'ART') return 'cell-ART';
            if(st == 'FE') return 'cell-FE';
            if(st == 'VAC') return 'cell-VAC';
            return '';
        }

        function fillSelectors() {
            const m = document.getElementById('sel-mes');
            const a = document.getElementById('sel-anio');
            const now = new Date();
            meses.forEach((name, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${name}</option>`);
            for(let i=2024; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
        }

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
            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const cantDias = new Date(anio, mes, 0).getDate();

            // Cabecera Planilla
            let h = `<tr><th class="name-col">PERSONAL</th>`;
            for(let i=1; i<=cantDias; i++) h += `<th>${i}</th>`;
            h += '<th>TOTAL</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colHs = new Array(cantDias).fill(0);
            let colPer = new Array(cantDias).fill(0);

            // Cuerpo Planilla
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                let hsFila = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { hsFila += 12; colHs[i-1] += 12; colPer[i-1] += 1; }
                    
                    r += `<td class="${getStatusClass(st)}">
                        <select class="nov-select no-print" onchange="updNov(${p.id},'${f}',this.value)">
                            <option value="12" ${st=='12'?'selected':''}>12</option>
                            <option value="F" ${st=='F'?'selected':''}>F</option>
                            <option value="ART" ${st=='ART'?'selected':''}>ART</option>
                            <option value="FE" ${st=='FE'?'selected':''}>FE</option>
                            <option value="VAC" ${st=='VAC'?'selected':''}>VAC</option>
                        </select>
                        <span class="print-val" style="display:none">${st}</span>
                    </td>`;
                }
                return `<tr>${r}<td><b>${hsFila}</b></td></tr>`;
            }).join('');

            // Totales Inferiores
            let f1 = `<tr class="row-total"><td class="name-col">CANT HS POR DIA</td>`;
            colHs.forEach(v => f1 += `<td>${v}</td>`);
            f1 += `<td>-</td></tr>`;

            let f2 = `<tr class="row-total"><td class="name-col">CANT DE PERSONAL</td>`;
            colPer.forEach(v => f2 += `<td>${v}</td>`);
            f2 += `<td>-</td></tr>`;
            document.getElementById('f-pla').innerHTML = f1 + f2;

            // Puestos
            document.getElementById('g-pue').innerHTML = pue.map(p => `
                <div class="card-puesto">
                    <div><b>${p.nombre.toUpperCase()}</b><br><small>HORARIO: ${p.horario} | DOTACIÓN: ${p.cantidad}</small></div>
                </div>`).join('');

            // Personal
            document.getElementById('l-per').innerHTML = per.map(p => `
                <div class="list-item"><span><b>${p.legajo}</b></span> <span>${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</span></div>
            `).join('');
        }

        // --- FUNCIONES DE PDF ---
        function generatePDF(titulo, subtitulo, filename, orientation) {
            document.getElementById('rt-titulo').innerText = titulo;
            document.getElementById('rt-subtitulo').innerText = subtitulo;
            document.getElementById('report-header-ui').style.display = 'flex';
            
            const element = document.body;
            const opt = {
                margin: 5,
                filename: filename,
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm', format: orientation == 'landscape' ? 'a3' : 'a4', orientation: orientation }
            };

            html2pdf().set(opt).from(element).save().then(() => {
                document.getElementById('report-header-ui').style.display = 'none';
            });
        }

        function pdfPlanilla() {
            const m = meses[document.getElementById('sel-mes').value - 1];
            const a = document.getElementById('sel-anio').value;
            generatePDF("PLANILLA MENSUAL DE NOVEDADES", `${m.toUpperCase()} ${a}`, `Planilla_${m}.pdf`, 'landscape');
        }

        function pdfPuestos() {
            generatePDF("REPORTE DE GUARDIAS Y PUESTOS", new Date().toLocaleDateString(), "Guardias.pdf", 'portrait');
        }

        function pdfPersonal() {
            generatePDF("NOMINA GENERAL DE PERSONAL", "ORDO KLAR", "Nomina_Personal.pdf", 'portrait');
        }

        async function updNov(pid, f, e) { await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})}); render(); }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
