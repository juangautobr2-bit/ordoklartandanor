import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# PERSISTENCIA TOTAL: Ruta absoluta para asegurar que el archivo no se mueva
DB_PATH = os.path.abspath("ordoklar_v43_final.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA journal_mode = WAL") # Permite lectura y escritura simultánea
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    # Tabla Puestos
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)')
    # Tabla Novedades (Planilla Mensual) - PERSISTENTE
    c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    # Tabla Historial de Informes
    c.execute('CREATE TABLE IF NOT EXISTS historial_informes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_archivo TEXT, fecha_gen TEXT)')
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

@app.route('/api/historial', methods=['GET', 'POST'])
def handle_historial():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO historial_informes (nombre_archivo, fecha_gen) VALUES (?, ?)", (d['nombre'], d['fecha']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM historial_informes ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(res)

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v43 | Master Plan</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; overflow-x: hidden; }
        
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); background: #050505; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #666; padding: 15px 20px; cursor: pointer; font-weight: bold; font-size: 13px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 15px; width: 100vw; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        /* DISEÑO DE TABLA SIN SCROLL (FIT TO WIDTH) */
        .table-wrapper { width: 100%; background: #000; border: 1px solid var(--border); border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }
        th, td { border: 1px solid #222; text-align: center; padding: 4px 1px; overflow: hidden; text-overflow: ellipsis; }
        
        .col-name { text-align: left; width: 140px; padding-left: 5px; color: var(--gold); font-weight: bold; font-size: 11px; white-space: nowrap; }
        .col-day { width: auto; }
        .col-total { width: 35px; background: #151515; font-weight: bold; color: var(--gold); }

        /* Estilos de Celda */
        .st-12 { background: #1b4332 !important; color: white; cursor: pointer; font-weight: bold; }
        .st-F { color: #444; cursor: pointer; }
        .st-ART { background: #5a1818 !important; color: white; cursor: pointer; }
        .st-VAC { background: #03045e !important; color: white; cursor: pointer; }

        /* Footer Totales */
        .row-total { background: #0a0a0a; color: var(--gold); font-weight: bold; }

        /* UI Elements */
        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 15px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; font-size: 14px; flex: 1; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 3px; font-size: 24px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#444; font-size: 10px; margin:0; font-weight: bold;">INFRASTRUCTURE MANAGEMENT SYSTEM | v43</p>
    </div>

    <nav>
        <button id="nav-pla" class="active" onclick="openTab('pla')">Planilla</button>
        <button id="nav-pue" onclick="openTab('pue')">Puestos</button>
        <button id="nav-per" onclick="openTab('per')">Personal</button>
        <button id="nav-inf" onclick="openTab('inf')">Informes</button>
        <button id="nav-arc" onclick="openTab('arc')">Archivos</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA MENSUAL COMPACTA -->
        <div id="sec-pla" class="section active-section">
            <div class="box flex-row">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
            </div>
            <div class="table-wrapper" id="capture-area">
                <table>
                    <thead id="head-pla"></thead>
                    <tbody id="body-pla"></tbody>
                    <tfoot id="foot-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="sec-inf" class="section">
            <div class="box" style="text-align:center">
                <h2 style="color:var(--gold)">CENTRO DE EXPORTACIÓN</h2>
                <div class="flex-row" style="justify-content:center; margin-top:20px;">
                    <button class="btn" onclick="exportPDF('planilla')">GENERAR PLANILLA A3</button>
                    <button class="btn" onclick="exportPDF('nomina')">DESCARGAR NÓMINA</button>
                </div>
            </div>
        </div>

        <!-- ARCHIVOS PERSISTENTES -->
        <div id="sec-arc" class="section">
            <div class="box">
                <h2 style="color:var(--gold)">HISTORIAL DE ARCHIVOS EN BASE DE DATOS</h2>
                <div id="historial-list" style="font-size: 13px;"></div>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="sec-pue" class="section">
            <div class="box flex-row">
                <input type="text" id="p-nom" placeholder="Objetivo/Puesto">
                <input type="text" id="p-hor" placeholder="Horario">
                <button class="btn" onclick="savePue()">Añadir Puesto</button>
            </div>
            <div id="lista-puestos" class="flex-row"></div>
        </div>

        <!-- PERSONAL -->
        <div id="sec-per" class="section">
            <div class="box flex-row">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn" onclick="savePer()">Dar de Alta</button>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead><tr><th class="col-name">Legajo</th><th>Agente</th><th>Acción</th></tr></thead>
                    <tbody id="lista-personal"></tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
        function openTab(t) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
            document.getElementById('sec-'+t).classList.add('active-section');
            document.getElementById('nav-'+t).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue, hist] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/historial').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('sel-mes').value);
            const a = parseInt(document.getElementById('sel-anio').value);
            const diasMes = new Date(a, m, 0).getDate();

            // Render Cabecera
            let h = `<tr><th class="col-name">AGENTES</th>`;
            for(let i=1; i<=diasMes; i++) h += `<th class="col-day">${i}</th>`;
            h += `<th class="col-total">HS</th></tr>`;
            document.getElementById('head-pla').innerHTML = h;

            // Render Cuerpo y Cálculos
            let b = "";
            let tHs = new Array(diasMes).fill(0);
            let tPr = new Array(diasMes).fill(0);

            per.forEach(p => {
                let rowHs = 0;
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre[0]}.</td>`;
                for(let i=1; i<=diasMes; i++){
                    const fecha = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == fecha) || {estado:'F'};
                    if(d.estado == '12') { rowHs += 12; tHs[i-1]+=12; tPr[i-1]++; }
                    r += `<td class="st-${d.estado}" onclick="changeSt(this, ${p.id}, '${fecha}')">${d.estado}</td>`;
                }
                r += `<td class="col-total">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('body-pla').innerHTML = b;

            // Render Totales
            let f1 = `<tr class="row-total"><td class="col-name">TOTAL HORAS</td>`;
            let f2 = `<tr class="row-total"><td class="col-name">PERS. PRESENTE</td>`;
            tHs.forEach(v => f1 += `<td>${v}</td>`);
            tPr.forEach(v => f2 += `<td>${v}</td>`);
            document.getElementById('foot-pla').innerHTML = f1 + "<td>-</td></tr>" + f2 + "<td>-</td></tr>";

            // Otras Listas
            document.getElementById('lista-personal').innerHTML = per.map(p => `<tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td><td><button onclick="delPer(${p.id})">ELIMINAR</button></td></tr>`).join('');
            document.getElementById('lista-puestos').innerHTML = pue.map(x => `<div class="box" style="border-top: 3px solid var(--gold); min-width:150px;"><strong>${x.nombre}</strong><br><small>${x.horario}</small></div>`).join('');
            document.getElementById('historial-list').innerHTML = hist.map(h => `<div style="padding:8px; border-bottom:1px solid #222;">💾 ${h.nombre_archivo} <span style="float:right; color:#555;">${h.fecha_gen}</span></div>`).join('');
        }

        async function changeSt(td, pid, fecha) {
            const cycle = ["F", "12", "ART", "VAC"];
            let next = cycle[(cycle.indexOf(td.innerText) + 1) % cycle.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:next})});
            render();
        }

        async function savePer() {
            const d = {legajo: document.getElementById('per-leg').value, apellido: document.getElementById('per-ape').value, nombre: document.getElementById('per-nom').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function savePue() {
            const d = {nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, cantidad: 0};
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function exportPDF(type) {
            const name = `Reporte_${type}_${Date.now()}.pdf`;
            const opt = { margin: 5, filename: name, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            
            html2pdf().set(opt).from(document.getElementById('capture-area')).save().then(async () => {
                await fetch('/api/historial', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: name, fecha: new Date().toLocaleString()})});
                render();
            });
        }

        window.onload = () => {
            const mSel = document.getElementById('sel-mes'); const aSel = document.getElementById('sel-anio');
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => mSel.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2027; i++) aSel.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
