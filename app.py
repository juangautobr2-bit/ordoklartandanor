import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v21
DB_PATH = '/tmp/ordoklar_v21.db'

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

# --- APIs PUESTOS ---
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

# --- APIs PERSONAL Y NOVEDADES ---
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

# --- INTERFAZ ÚNICA ORDO KLAR ---
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
        
        /* HEADER PRINCIPAL WEB */
        .header-web { text-align: center; padding: 20px; font-size: 26px; font-weight: 900; letter-spacing: 8px; border-bottom: 2px solid var(--gold); }
        
        /* ENCABEZADO DE REPORTE (PARA IMPRESIÓN) */
        .report-header { display: none; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 3px solid #000; margin-bottom: 30px; color: #000; }
        .report-header img { height: 70px; width: auto; object-fit: contain; }
        .report-title { text-align: center; flex-grow: 1; }
        .report-title h1 { margin: 0; font-size: 26px; text-transform: uppercase; font-weight: 900; }
        .report-title p { margin: 5px 0 0 0; font-weight: bold; font-size: 18px; }

        /* NAVEGACIÓN */
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #AAA; padding: 15px 25px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 13px; }
        .nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); background: #111; }
        
        .content { padding: 20px; }
        .section { display: none; }
        .active { display: block; }

        /* ACCIONES */
        .actions-bar { display: flex; gap: 15px; margin-bottom: 20px; padding: 15px; background: #111; border-radius: 8px; justify-content: center; border: 1px solid #222; }
        .btn-action { padding: 12px 20px; border-radius: 6px; font-weight: 900; cursor: pointer; border: none; text-transform: uppercase; font-size: 12px; display: flex; align-items: center; gap: 8px; }
        .btn-pdf { background: #2E7D32; color: white; }
        .btn-print { background: #1565C0; color: white; }
        .btn-gold { background: var(--gold); color: black; }

        /* FORMULARIOS */
        .form-box { background: var(--card); padding: 20px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 20px; }
        .form-box input { background: #000; color: #fff; border: 1px solid #444; padding: 12px; border-radius: 5px; margin: 5px; outline: none; }
        .form-box input:focus { border-color: var(--gold); }

        /* TABLA PLANILLA */
        .table-wrap { overflow-x: auto; border-radius: 12px; border: 2px solid var(--border); background: #000; }
        table { border-collapse: collapse; min-width: 1300px; width: 100%; }
        th, td { border: 1px solid #222; text-align: center; font-size: 15px; }
        th { background: #111; color: var(--gold); padding: 10px; }
        .name-col { width: 180px; text-align: left !important; padding-left: 10px; color: var(--gold); font-weight: 800; position: sticky; left: 0; background: #111; z-index: 20; border-right: 3px solid var(--gold) !important; }
        .day-name { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 12px; padding: 5px 0; }

        /* CARDS */
        .card-puesto { background: #151515; border-left: 6px solid var(--gold); padding: 20px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #222; }
        .puesto-info h2 { margin: 0; color: var(--gold); letter-spacing: 1px; }
        .puesto-info p { margin: 5px 0 0 0; color: #ccc; }

        .item-personal { background: #111; padding: 15px; border-bottom: 1px solid #222; display: flex; gap: 20px; font-size: 16px; }

        /* MODO IMPRESIÓN */
        @media print {
            .no-print, .nav, .header-web, .form-box { display: none !important; }
            body { background: #FFF; color: #000; }
            .report-header { display: flex !important; }
            .section { display: block !important; }
            .card-puesto { border: 1px solid #000 !important; color: #000 !important; border-left: 10px solid #000 !important; }
            .puesto-info h2, .puesto-info p { color: #000 !important; }
            table { color: #000 !important; border: 1px solid #000 !important; font-size: 10px !important; }
            .name-col { background: #EEE !important; color: #000 !important; }
            .item-personal { color: #000; border-bottom: 1px solid #000; background: #FFF; }
        }
    </style>
</head>
<body>

    <!-- VISIBLE EN WEB -->
    <div class="header-web">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Guardias / Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <!-- ENCABEZADO DE REPORTE (SOLO IMPRESIÓN/PDF) -->
    <div id="report-header-ui" class="report-header">
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/TANDANOR.PNG" alt="Tandanor">
        <div class="report-title">
            <h1 id="rt-titulo">TÍTULO DEL REPORTE</h1>
            <p id="rt-subtitulo">SUBTÍTULO DINÁMICO</p>
        </div>
        <img src="https://raw.githubusercontent.com/juangautobr2-bit/ordoklartandanor/main/WATCHMAN.SVG" alt="Watchman">
    </div>

    <div class="content">
        <!-- SECCIÓN PLANILLA -->
        <div id="s-pla" class="section active">
            <div class="actions-bar no-print">
                <select id="sel-mes" onchange="render()" style="padding:10px; background:#000; color:var(--gold); border:1px solid var(--gold);"></select>
                <select id="sel-anio" onchange="render()" style="padding:10px; background:#000; color:var(--gold); border:1px solid var(--gold);"></select>
                <button class="btn-action btn-pdf" onclick="exportarPDF()">📄 GENERAR INFORME MENSUAL (PDF)</button>
            </div>
            <div class="table-wrap" id="render-planilla">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- SECCIÓN PUESTOS -->
        <div id="s-pue" class="section">
            <div class="actions-bar no-print">
                <button class="btn-action btn-print" onclick="imprimirPuestos()">🖨️ IMPRIMIR ESTADO DE GUARDIAS</button>
            </div>
            <div class="form-box no-print">
                <h3 style="color:var(--gold); margin-top:0;">Configuración de Puesto / Objetivo</h3>
                <input type="hidden" id="p-id">
                <input type="text" id="p-nom" placeholder="Nombre del Puesto" style="width:250px">
                <input type="text" id="p-hor" placeholder="Horario Operativo" style="width:200px">
                <input type="number" id="p-can" placeholder="Dotación" style="width:80px">
                <button class="btn-action btn-gold" onclick="savePuesto()">GUARDAR PUESTO</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <!-- SECCIÓN PERSONAL -->
        <div id="s-per" class="section">
            <div class="actions-bar no-print">
                <button class="btn-action btn-print" onclick="imprimirPersonal()">🖨️ IMPRIMIR PLANILLA DE PERSONAL</button>
            </div>
            <div class="form-box no-print">
                <h3 style="color:var(--gold); margin-top:0;">Alta de Personal</h3>
                <input type="text" id="i-leg" placeholder="N° Legajo">
                <input type="text" id="i-ape" placeholder="Apellido">
                <input type="text" id="i-nom" placeholder="Nombre">
                <button class="btn-action btn-gold" onclick="addPersonal()">REGISTRAR OPERATIVO</button>
            </div>
            <div id="l-per" style="background: white; color: black; border-radius: 8px; overflow: hidden;"></div>
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

            // Render Planilla Mensual
            let h = `<tr><th class="name-col">OPERATIVO</th>`;
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-name">${dNom}</span><br>${i}</th>`;
            }
            h += '<th>TOT</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') rowHs += 12;
                    r += `<td style="background:${st=='12'?'#1B5E20':st=='F'?'#444':st=='VAC'?'#0D47A1':'#B71C1C'}">
                        <select class="no-print" style="background:transparent; color:white; border:none; width:100%; cursor:pointer;" onchange="updNov(${p.id},'${f}',this.value)">
                            <option value="12" ${st=='12'?'selected':''}>12</option>
                            <option value="F" ${st=='F'?'selected':''}>F</option>
                            <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                            <option value="ART" ${st=='ART'?'selected':''}>A</option>
                        </select>
                        <span class="only-print" style="display:none; font-weight:bold;">${st=='12'?'12':st[0]}</span>
                    </td>`;
                }
                return `<tr>${r}<td style="font-weight:900; color:var(--gold)">${rowHs}</td></tr>`;
            }).join('');

            // Render Puestos
            document.getElementById('g-pue').innerHTML = pue.map(p => `
                <div class="card-puesto">
                    <div class="puesto-info">
                        <h2>${p.nombre.toUpperCase()}</h2>
                        <p><b>HORARIO:</b> ${p.horario} | <b>CANTIDAD:</b> ${p.cantidad}</p>
                    </div>
                    <div class="no-print">
                        <button class="btn-action" style="background:#444; color:white" onclick='editPuesto(${JSON.stringify(p)})'>EDITAR</button>
                        <button class="btn-action" style="background:#B71C1C; color:white" onclick="deletePuesto(${p.id})">BORRAR</button>
                    </div>
                </div>
            `).join('');

            // Render Personal
            document.getElementById('l-per').innerHTML = per.map(p => `
                <div class="item-personal">
                    <span style="width:80px"><b>${p.legajo}</b></span>
                    <span>${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</span>
                </div>
            `).join('');
        }

        // --- FUNCIONES DE REPORTES ---
        function imprimirPersonal() {
            document.getElementById('rt-titulo').innerText = "PLANILLA DE PERSONAL";
            document.getElementById('rt-subtitulo').innerText = "LISTADO ACTUALIZADO DE OPERATIVOS";
            window.print();
        }

        function imprimirPuestos() {
            const n = new Date();
            document.getElementById('rt-titulo').innerText = "ESTADO DE GUARDIAS";
            document.getElementById('rt-subtitulo').innerText = `${n.getDate()} ${meses[n.getMonth()].toUpperCase()} ${n.getFullYear()}`;
            window.print();
        }

        function exportarPDF() {
            const m = meses[document.getElementById('sel-mes').value - 1];
            const a = document.getElementById('sel-anio').value;
            document.getElementById('rt-titulo').innerText = "PLANILLA MENSUAL DE NOVEDADES";
            document.getElementById('rt-subtitulo').innerText = `${m.toUpperCase()} ${a}`;
            
            const element = document.body; 
            const opt = {
                margin: 5,
                filename: `OrdoKlar_Planilla_${m}_${a}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2 },
                jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' }
            };
            
            document.getElementById('report-header-ui').style.display = 'flex';
            html2pdf().set(opt).from(element).save().then(() => {
                document.getElementById('report-header-ui').style.display = 'none';
            });
        }

        // --- CRUD LOGIC ---
        async function savePuesto() {
            const d = { id:document.getElementById('p-id').value, nombre:document.getElementById('p-nom').value, horario:document.getElementById('p-hor').value, cantidad:document.getElementById('p-can').value };
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            document.getElementById('p-id').value=""; document.getElementById('p-nom').value=""; document.getElementById('p-hor').value="";
            render();
        }
        async function deletePuesto(id) { if(confirm("¿Eliminar?")) await fetch(`/api/puestos/${id}`, {method:'DELETE'}); render(); }
        function editPuesto(p) { document.getElementById('p-id').value=p.id; document.getElementById('p-nom').value=p.nombre; document.getElementById('p-hor').value=p.horario; document.getElementById('p-can').value=p.cantidad; }
        
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
