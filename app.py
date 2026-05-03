import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v17
DB_PATH = '/tmp/ordoklar_v17.db'

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

# --- APIs (Mantenidas) ---
@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
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

# --- INTERFAZ CON FUNCIONES DE REPORTE ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión & Reportes</title>
    <!-- Librería para PDF -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; --cyan: #00FBFF; }
        
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        /* Estilos de Impresión */
        @media print {
            .nav, .header, .btn-gold, .form-box, .no-print { display: none !important; }
            body { background: #FFF; color: #000; }
            .card { border: 1px solid #000 !important; color: #000 !important; page-break-inside: avoid; }
            .name-col { background: #EEE !important; color: #000 !important; border-right: 1px solid #000 !important; }
            table { font-size: 10px !important; color: #000; }
            th { background: #DDD !important; color: #000 !important; }
        }

        .header { text-align: center; padding: 20px; font-size: 26px; font-weight: 900; letter-spacing: 8px; border-bottom: 2px solid var(--gold); }
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
        
        .content { padding: 20px; }
        .section { display: none; }
        .active { display: block; }

        /* Botonera de Acciones */
        .actions-bar { display: flex; gap: 10px; margin-bottom: 20px; justify-content: center; }
        .btn-report { background: #2E7D32; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; }
        .btn-print { background: #1565C0; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; }

        /* TABLA */
        .table-wrap { overflow-x: auto; border-radius: 12px; background: #0a0a0a; border: 1px solid var(--border); }
        table { border-collapse: collapse; min-width: 1300px; width: 100%; }
        th, td { border: 1px solid #222; text-align: center; font-size: 15px; }
        th { background: #111; color: var(--gold); padding: 10px; }
        
        .day-name { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 12px; font-weight: 800; margin-bottom: 5px; display: inline-block; }
        .name-col { width: 180px; text-align: left !important; padding-left: 15px; color: var(--gold); font-weight: 800; height: 50px; position: sticky; left: 0; background: #111; z-index: 20; border-right: 3px solid var(--gold) !important; }
        
        .total-hs { background: #000; color: var(--gold); font-weight: 900; height: 55px; }
        .total-per { background: #000; color: var(--cyan); font-weight: 900; height: 55px; }

        select.cell-sel { background: transparent; color: #FFF; border: none; width: 100%; height: 50px; text-align-last: center; font-weight: 900; font-size: 15px; appearance: none; }
        .st-12 { background: #1B5E20 !important; } .st-F { background: #424242 !important; } .st-VAC { background: #0D47A1 !important; } .st-ART { background: #B71C1C !important; }

        .card { background: var(--card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; margin-bottom: 15px; border-left: 5px solid var(--gold); }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="content">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active">
            <div class="actions-bar no-print">
                <select id="sel-mes" onchange="render()" style="padding:10px; background:#111; color:white; border:1px solid var(--gold); border-radius:5px;"></select>
                <select id="sel-anio" onchange="render()" style="padding:10px; background:#111; color:white; border:1px solid var(--gold); border-radius:5px;"></select>
                <button class="btn-report" onclick="exportarPDF()">📄 GENERAR INFORME PDF</button>
            </div>
            <div class="table-wrap" id="reporte-pdf">
                <div class="only-print" style="display:none; color:black; text-align:center; padding:20px;">
                    <h2>INFORME MENSUAL DE NOVEDADES - ORDO KLAR</h2>
                </div>
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
                <button class="btn-print" onclick="window.print()">🖨️ IMPRIMIR PUESTOS</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="card no-print">
                <h3>Nuevo Operativo</h3>
                <input type="text" id="i-leg" placeholder="Legajo" style="padding:10px; margin:5px">
                <input type="text" id="i-ape" placeholder="Apellido" style="padding:10px; margin:5px">
                <input type="text" id="i-nom" placeholder="Nombre" style="padding:10px; margin:5px">
                <button class="btn-report" onclick="addPersonal()">REGISTRAR</button>
            </div>
            <div id="l-per"></div>
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
            
            // Header
            let h = `<tr><th class="name-col">OPERATIVO</th>`;
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-name">${dNom}</span><br>${i}</th>`;
            }
            h += '<th>TOT</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colTotHs = new Array(cantDias).fill(0);
            let colTotPer = new Array(cantDias).fill(0);

            // Cuerpo
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { rowHs += 12; colTotHs[i-1] += 12; colTotPer[i-1] += 1; }
                    r += `<td class="st-${st}"><select class="cell-sel" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${st=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${r}<td style="background:#1a1a1a; font-weight:bold; color:var(--gold)">${rowHs}</td></tr>`;
            }).join('');

            // Footer
            let fHs = `<tr class="total-hs"><td class="name-col">TOTAL HORAS</td>`;
            colTotHs.forEach(t => fHs += `<td>${t}</td>`);
            fHs += `<td>${colTotHs.reduce((a,b)=>a+b, 0)}</td></tr>`;

            let fPer = `<tr class="total-per"><td class="name-col">CANT. PERSONAL</td>`;
            colTotPer.forEach(t => fPer += `<td>${t}</td>`);
            fPer += `<td>-</td></tr>`;
            document.getElementById('f-pla').innerHTML = fHs + fPer;

            // Render Puestos
            document.getElementById('g-pue').innerHTML = pue.map(p => `
                <div class="card">
                    <h2 style="margin:0; color:var(--gold)">${p.nombre.toUpperCase()}</h2>
                    <p><b>Horario:</b> ${p.horario} | <b>Dotación Requerida:</b> ${p.cantidad} personas</p>
                </div>
            `).join('');
        }

        function exportarPDF() {
            const element = document.getElementById('reporte-pdf');
            const mesNombre = meses[document.getElementById('sel-mes').value - 1];
            const opt = {
                margin: [10, 10],
                filename: `Planilla_${mesNombre}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } // A3 horizontal para que entre la planilla
            };
            html2pdf().set(opt).from(element).save();
        }

        async function updNov(pid, f, e) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})});
            render();
        }

        async function addPersonal() {
            const d = {nombre:document.getElementById('i-nom').value, apellido:document.getElementById('i-ape').value, legajo:document.getElementById('i-leg').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
