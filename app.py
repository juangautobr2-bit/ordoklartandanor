import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos unificada v42 - Almacenamiento persistente rígido
DB_PATH = os.path.abspath("ordoklar_v42_master.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("PRAGMA synchronous = EXTRA")  # Fuerza la escritura física en disco inmediata
    conn.execute("PRAGMA journal_mode = WAL")    # Previene la corrupción y bloqueos de lectura/escritura
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Estructuras de tablas robustas con persistencia temporal
    c.execute('''CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT, 
        apellido TEXT, 
        legajo TEXT UNIQUE)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT, 
        horario TEXT, 
        cantidad INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        personal_id INTEGER, 
        fecha TEXT, 
        estado TEXT, 
        UNIQUE(personal_id, fecha))''')
    
    # Nueva tabla para que el historial de informes permanezca en el tiempo
    c.execute('''CREATE TABLE IF NOT EXISTS informes_archivos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre_archivo TEXT, 
        tipo TEXT, 
        fecha_generado TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- ENDPOINTS API CON CONTROL DE TRANSACCIONES ---

@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['cantidad']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

@app.route('/api/informes', methods=['GET', 'POST'])
def handle_informes():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO informes_archivos (nombre_archivo, tipo, fecha_generado) VALUES (?, ?, ?)", (d['nombre'], d['tipo'], d['fecha']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM informes_archivos ORDER BY id DESC").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

# --- INTERFAZ DE USUARIO v42 ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR v42 | Control de Infraestructura y Personal</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #121212; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 25px; border-bottom: 2px solid var(--gold); background: #050505; }
        nav { display: flex; justify-content: center; background: #111; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 1000; }
        nav button { background: none; border: none; color: #888; padding: 20px 30px; cursor: pointer; font-weight: bold; font-size: 16px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); background: #1a1a1a; }

        .container { padding: 20px; max-width: 100%; margin: auto; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        /* Contenedores de Formulario e Inputs Grandes */
        .box { background: var(--card); padding: 25px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 20px; }
        .flex-form { display: flex; flex-wrap: wrap; gap: 15px; }
        input, select { background: #000; border: 1px solid var(--border); color: #fff; padding: 15px; border-radius: 8px; font-size: 18px; flex: 1; min-width: 200px; }
        input:focus, select:focus { border-color: var(--gold); outline: none; }
        .btn { background: var(--gold); color: #000; border: none; padding: 15px 30px; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; text-transform: uppercase; transition: 0.2s; }
        .btn:hover { background: #fff; }

        /* AJUSTE CRÍTICO: Planilla Mensual Fluida sin Desplazamiento Horizontal */
        .table-container { width: 100%; overflow: hidden; background: #000; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        
        th, td { border: 1px solid #222; padding: 6px 2px; text-align: center; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        
        /* Reparto de Anchos fijos en porcentaje para obligar a entrar en pantalla */
        .name-col { text-align: left; width: 15%; padding-left: 10px; color: var(--gold); font-weight: bold; font-size: 13px; background: #080808; }
        .day-col { width: calc(81% / 31); font-weight: bold; }
        .total-hs-col { width: 4%; background: #1a1a1a; color: var(--gold); font-weight: bold; font-size: 13px; }
        
        .total-row { background: #0d0d0d; font-weight: bold; color: var(--gold); }
        .total-row td { font-size: 12px; padding: 8px 2px; }

        /* Celdas de Estados Operativos */
        .st-12 { background: #1b4332 !important; color: #fff; font-weight: bold; cursor: pointer; }
        .st-F { color: #444; background: #111 !important; cursor: pointer; }
        .st-ART { background: #5a1818 !important; color: #fff; font-weight: bold; cursor: pointer; }
        .st-VAC { background: #03045e !important; color: #fff; font-weight: bold; cursor: pointer; }

        /* Lista de Archivos */
        .file-item { display: flex; justify-content: space-between; padding: 15px 20px; border-bottom: 1px solid #222; background: #080808; margin-top: 8px; border-radius: 6px; border-left: 3px solid var(--gold); }
        
        /* Grids de Puestos */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 6px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#666; font-size: 13px; margin:5px 0 0 0; letter-spacing: 1px;">SISTEMA DE ASIGNACIÓN TÉCNICA E INFORMES METRÓPOLIS | v42</p>
    </div>

    <nav>
        <button id="btn-pla" class="active" onclick="show('pla')">Planilla Mensual</button>
        <button id="btn-pue" onclick="show('pue')">Objetivos / Puestos</button>
        <button id="btn-per" onclick="show('per')">Personal</button>
        <button id="btn-inf" onclick="show('inf')">Informes</button>
        <button id="btn-arc" onclick="show('arc')">Archivos Guardados</button>
    </nav>

    <div class="container">
        
        <div id="sec-pla" class="section active-section">
            <div class="box flex-form">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
            </div>
            <div class="table-container" id="area-planilla">
                <table>
                    <thead id="h-table"></thead>
                    <tbody id="b-table"></tbody>
                    <tfoot id="f-table"></tfoot>
                </table>
            </div>
        </div>

        <div id="sec-pue" class="section">
            <div class="box flex-form">
                <input type="text" id="pue-n" placeholder="Nombre del Puesto">
                <input type="text" id="pue-h" placeholder="Horario de Guardia">
                <input type="number" id="pue-c" placeholder="Cantidad Operarios">
                <button class="btn" onclick="addPue()">Crear Objetivo</button>
            </div>
            <div id="pue-list" class="puestos-grid"></div>
        </div>

        <div id="sec-per" class="section">
            <div class="box flex-form">
                <input type="text" id="per-l" placeholder="Legajo Único">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPer()">Inscribir Agente</button>
            </div>
            <div class="table-container">
                <table style="table-layout: auto;">
                    <thead><tr><th style="padding:15px;">Legajo</th><th>Apellido y Nombre</th><th>Gestión Técnica</th></tr></thead>
                    <tbody id="per-list"></tbody>
                </table>
            </div>
        </div>

        <div id="sec-inf" class="section">
            <div class="box" style="text-align:center; padding: 40px;">
                <h2 style="color:var(--gold); margin-bottom: 10px;">MÓDULO EXPORTADOR DE DOCUMENTOS</h2>
                <p style="color:#aaa; margin-bottom: 30px;">Generación de archivos PDF listos para archivo físico o auditoría.</p>
                <div style="display:flex; flex-wrap: wrap; justify-content:center; gap:25px;">
                    <button class="btn" onclick="generatePDFReport('planilla')">GENERAR PLANILLA MENSUAL</button>
                    <button class="btn" onclick="generatePDFReport('nomina')">GENERAR NÓMINA DE AGENTES</button>
                    <button class="btn" onclick="generatePDFReport('puestos')">GENERAR RELEVAMIENTO DE PUESTOS</button>
                </div>
            </div>
            <div id="pdf-nomina" style="display:none; color:#000; background:#fff; padding:20px;"></div>
            <div id="pdf-puestos" style="display:none; color:#000; background:#fff; padding:20px;"></div>
        </div>

        <div id="sec-arc" class="section">
            <div class="box">
                <h2 style="color:var(--gold); margin-bottom: 5px;">HISTÓRICO REAL DE EXPORTACIONES</h2>
                <p style="color:#555; font-size:14px; margin:0 0 20px 0;">Estos registros quedan salvados permanentemente en la base de datos interna.</p>
                <div id="file-log"></div>
            </div>
        </div>

    </div>

    <script>
        function show(s) {
            document.querySelectorAll('.section').forEach(e => e.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(e => e.classList.remove('active'));
            document.getElementById('sec-'+s).classList.add('active-section');
            document.getElementById('btn-'+s).classList.add('active');
            render();
        }

        async function render() {
            const [per, nov, pue, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/informes').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // 1. Cabecera con Clases de Ancho Controlado
            let h = `<tr><th class="name-col">AGENTES</th>`;
            for(let i=1; i<=dias; i++) h += `<th class="day-col">${i}</th>`;
            // Completar celdas invisibles si el mes tiene menos de 31 días para no alterar el ancho de la grilla
            for(let i=dias+1; i<=31; i++) h += `<th class="day-col" style="color:#222">-</th>`;
            h += `<th class="total-hs-col">TOTAL</th></tr>`;
            document.getElementById('h-table').innerHTML = h;

            // 2. Render de Filas y Sumatorias
            let b = "";
            let sumHs = new Array(31).fill(0);
            let sumPer = new Array(31).fill(0);

            per.forEach(p => {
                let rowHs = 0;
                let row = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                
                for(let i=1; i<=31; i++) {
                    if(i <= dias) {
                        const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                        const n = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado: 'F'};
                        if(n.estado == '12') { rowHs += 12; sumHs[i-1] += 12; sumPer[i-1]++; }
                        row += `<td class="st-${n.estado} day-col" onclick="cycle(this, ${p.id}, '${f}')">${n.estado}</td>`;
                    } else {
                        row += `<td class="day-col" style="background:#050505;"></td>`;
                    }
                }
                row += `<td class="total-hs-col">${rowHs}</td>`;
                b += `<tr>${row}</tr>`;
            });
            document.getElementById('b-table').innerHTML = b;

            // 3. Footer con Totales de Horas y de Personal Cargado por Día
            let f1 = `<tr class="total-row"><td class="name-col">HS DE SERVICIO</td>`;
            let f2 = `<tr class="total-row"><td class="name-col">PERS. PRESENTE</td>`;
            for(let i=0; i<31; i++) {
                f1 += `<td class="day-col">${sumHs[i]}</td>`;
                f2 += `<td class="day-col">${sumPer[i]}</td>`;
            }
            document.getElementById('f-table').innerHTML = f1 + "<td class="total-hs-col">-</td></tr>" + f2 + "<td class="total-hs-col">-</td></tr>";

            // 4. Personal
            document.getElementById('per-list').innerHTML = per.map(p => `
                <tr><td style="font-weight:bold; padding:12px;">${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="background:none; border:1px solid #ff4444; color:#ff4444; padding:5px 10px; border-radius:4px; cursor:pointer">Eliminar</button></td></tr>
            `).join('');

            // 5. Puestos con Selectores
            document.getElementById('pue-list').innerHTML = pue.map(x => {
                let selectors = "";
                for(let k=0; k<x.cantidad; k++) {
                    selectors += `<select style="width:100%; font-size:14px; margin-top:5px; padding:8px;"><option>-- Asignar Operario --</option>${per.map(p=>`<option>${p.apellido}, ${p.nombre}</option>`).join('')}</select>`;
                }
                return `
                <div class="box" style="border-left:5px solid var(--gold); margin-bottom:0;">
                    <h3 style="margin:0 0 5px 0; color:var(--gold);">${x.nombre}</h3>
                    <p style="color:#888; font-size:14px; margin:0 0 10px 0;">${x.horario} | Requerido: ${x.cantidad} agentes</p>
                    ${selectors}
                    <button onclick="delPue(${x.id})" style="font-size:12px; margin-top:15px; background:none; border:1px solid #444; color:#777; cursor:pointer; padding:4px 8px;">Remover Objetivo</button>
                </div>`;
            }).join('');

            // 6. Historial de Informes Persistente de la Base de Datos
            const divArc = document.getElementById('file-log');
            if(arc.length === 0) {
                divArc.innerHTML = `<p style="color:#444">No existen registros de informes emitidos.</p>`;
            } else {
                divArc.innerHTML = arc.map(f => `
                    <div class="file-item">
                        <span><strong>📄 ${f.nombre_archivo}</strong> <small style="color:#666; margin-left:15px;">(${f.tipo})</small></span>
                        <span style="color:var(--gold); font-size:15px;">${f.fecha_generado}</span>
                    </div>
                `).join('');
            }
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let next = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({p_id: pid, fecha: fecha, estado: next})});
            render();
        }

        async function addPer() {
            const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
            if(!d.legajo || !d.apellido) return alert("Faltan campos mandatorios");
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            document.getElementById('per-l').value = ""; document.getElementById('per-a').value = ""; document.getElementById('per-n').value = "";
            render();
        }

        async function addPue() {
            const d = { nombre: document.getElementById('pue-n').value, horario: document.getElementById('pue-h').value, cantidad: document.getElementById('pue-c').value };
            if(!d.nombre || !d.cantidad) return alert("Indicar nombre y dotación");
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            document.getElementById('pue-n').value = ""; document.getElementById('pue-h').value = ""; document.getElementById('pue-c').value = "";
            render();
        }

        async function delPer(id) { if(confirm('¿Desea dar de baja al agente?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
        async function delPue(id) { if(confirm('¿Eliminar objetivo del cuadrante?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        function generatePDFReport(type) {
            const now = new Date();
            const ts = now.toLocaleString('es-AR');
            let sourceId = "";
            let filename = "";
            let reportType = "";

            if(type === 'planilla') {
                sourceId = 'area-planilla';
                filename = `PLANILLA_MENSUAL_${now.getTime()}.pdf`;
                reportType = "Cuadrante de Asistencia Mensual";
            } else if(type === 'nomina') {
                const data = document.querySelector("#sec-per table").outerHTML;
                const wrapper = document.getElementById('pdf-nomina');
                wrapper.innerHTML = `<h2 style="font-family:sans-serif; border-bottom:2px solid #000; padding-bottom:5px;">ORDO KLAR - NÓMINA DE PERSONAL REGISTRADO</h2><p style="font-size:12px; color:#555;">Fecha de extracción: ${ts}</p>` + data;
                sourceId = 'pdf-nomina';
                filename = `NOMINA_AGENTES_${now.getTime()}.pdf`;
                reportType = "Nómina de Personal Activo";
            } else if(type === 'puestos') {
                const data = document.getElementById('pue-list').innerHTML;
                const wrapper = document.getElementById('pdf-puestos');
                wrapper.innerHTML = `<h2 style="font-family:sans-serif; border-bottom:2px solid #000; padding-bottom:5px;">ORDO KLAR - RELEVAMIENTO DE OBJETIVOS OPERATIVOS</h2><p style="font-size:12px; color:#555;">Fecha de extracción: ${ts}</p><div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:20px;">` + data + `</div>`;
                sourceId = 'pdf-puestos';
                filename = `ESTADO_OBJETIVOS_${now.getTime()}.pdf`;
                reportType = "Relevamiento de Puestos";
            }

            const opt = { margin: 12, filename: filename, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } };
            
            html2pdf().set(opt).from(document.getElementById(sourceId)).save().then(async () => {
                // Guardar la traza del reporte directamente en la base de datos para que persista
                await fetch('/api/informes', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ nombre: filename, tipo: reportType, fecha: ts })
                });
                render();
            });
        }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel'); const now = new Date();
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
