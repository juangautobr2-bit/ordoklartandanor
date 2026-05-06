import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de Datos - Persistencia Ordo Klar
DB_PATH = os.path.abspath("ordoklar_v53_master.db")

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

# --- INTERFAZ MAESTRA ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v53 | Sistema de Puestos y Guardia</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', Arial, sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); background: #0a0a0a; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; text-transform: uppercase; font-size: 11px; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; max-width: 1500px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 15px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 120px; }
        label { font-size: 10px; color: var(--gold); font-weight: bold; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 8px; border-radius: 4px; }

        .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; font-size: 12px; }
        .btn-confirm { background: #1b4332; color: #fff; padding: 5px 10px; margin-top: 10px; width: 100%; border: none; cursor: pointer; border-radius: 4px; font-size: 11px; }
        .btn-red { background: #5a1818; color: #fff; border: none; padding: 5px 10px; cursor: pointer; border-radius: 3px; }

        /* GRID PUESTOS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; width: 100%; }
        .card-pue { background: #0a0a0a; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 8px; break-inside: avoid; }
        .card-pue h3 { margin: 0 0 5px 0; color: var(--gold); font-size: 15px; text-transform: uppercase; }
        
        .slot { background: #151515; padding: 6px 10px; margin-top: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        .slot select { width: 65%; font-size: 11px; }
        .slot-val { color: #fff; font-weight: bold; display: none; font-size: 12px; }

        /* REPORTE */
        #area-puestos-reporte { padding: 30px; background: #000; min-height: 100%; }
        .report-header { text-align: center; border-bottom: 2px solid var(--gold); margin-bottom: 25px; padding-bottom: 15px; display: none; }

        /* ESTADO CONFIRMADO EN UI */
        .is-confirmed .pue-sel, .is-confirmed .btn-confirm { display: none; }
        .is-confirmed .slot-val { display: block; }
        .is-confirmed { border-top-color: #1b4332; background: #050505; }
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
        
        <!-- SECCION PUESTOS -->
        <div id="s-pue" class="section active-section">
            <div class="box">
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <div class="form-group"><label>Objetivo / Puesto</label><input type="text" id="p-nom" placeholder="Ej: Portería"></div>
                    <div class="form-group"><label>Horario</label><input type="text" id="p-hor" placeholder="06:00 a 18:00"></div>
                    <div class="form-group"><label>Dotación</label><input type="number" id="p-dot" placeholder="Cant."></div>
                    <button class="btn" onclick="savePuesto()">Guardar Configuración</button>
                </div>
            </div>

            <div class="box" style="border: 1px solid var(--gold);">
                <label style="color:var(--gold)">Configuración para Impresión:</label>
                <div class="flex-row" style="margin-top:10px">
                    <div class="form-group"><label>Día</label><select id="rpt-dia"></select></div>
                    <div class="form-group"><label>Mes</label><select id="rpt-mes"></select></div>
                    <div class="form-group"><label>Año</label><select id="rpt-anio"></select></div>
                    <button class="btn" style="background:#fff" onclick="genPuePDF()">🖨️ Imprimir Hoja Completa</button>
                </div>
            </div>

            <div id="area-puestos-reporte">
                <div id="head-puestos" class="report-header">
                    <h1 id="dynamic-title" style="margin:0; color:var(--gold)"></h1>
                    <p style="color:#666; font-size:12px; margin-top:5px">SISTEMA ORDO KLAR - CONTROL DE GUARDIA</p>
                </div>
                <div id="grid-pue" class="grid-pue"></div>
            </div>
        </div>

        <!-- OTRAS SECCIONES (Simplificadas para esta versión) -->
        <div id="s-pla" class="section">
            <div class="box"><h3>Módulo de Planilla</h3><p>Use la sección de informes para exportar novedades mensuales.</p></div>
        </div>

        <div id="s-per" class="section">
            <div class="box flex-row">
                <div class="form-group"><label>Legajo</label><input type="text" id="per-l"></div>
                <div class="form-group"><label>Apellido</label><input type="text" id="per-a"></div>
                <div class="form-group"><label>Nombre</label><input type="text" id="per-n"></div>
                <button class="btn" onclick="addPersonal()">Cargar Agente</button>
            </div>
            <div class="box">
                <table style="width:100%; text-align:left; border-collapse: collapse;">
                    <thead><tr style="color:var(--gold)"><th>Legajo</th><th>Nombre Completo</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <div id="s-inf" class="section">
            <div class="box" style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                <div class="box" style="text-align:center"><h4>Reporte de Guardias</h4><button class="btn" onclick="tab('pue')">Ir a Puestos</button></div>
                <div class="box" style="text-align:center"><h4>Nómina Personal</h4><button class="btn" onclick="tab('per')">Ver Nómina</button></div>
            </div>
        </div>

        <div id="s-arc" class="section">
            <div class="box"><div id="list-arc"></div></div>
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
            const [per, pue, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/archivos').then(r => r.json())
            ]);

            // Render Puestos
            const perOpts = `<option value="">-- Seleccionar --</option>` + per.map(p => `<option value="${p.id}">${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let slots = "";
                for(let i=1; i<=x.dotacion; i++) {
                    slots += `<div class="slot">
                        <span style="font-size:9px; color:var(--gold)">POS ${i}</span>
                        <select class="pue-sel">${perOpts}</select>
                        <span class="slot-val">-- VACANTE --</span>
                    </div>`;
                }
                return `
                <div class="card-pue" id="card-${x.id}">
                    <div style="float:right" class="no-print">
                        <button onclick="editPue(${x.id},'${x.nombre}','${x.horario}',${x.dotacion})" style="background:none; color:var(--gold); border:none; cursor:pointer; font-size:14px">✎</button>
                        <button onclick="delPue(${x.id})" style="background:none; color:red; border:none; cursor:pointer; font-size:14px; margin-left:10px">✖</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <p style="font-size:11px; color:#777; margin: 5px 0 10px 0;">${x.horario} | DOT: ${x.dotacion}</p>
                    ${slots}
                    <button class="btn-confirm no-print" onclick="confirmCard(${x.id})">CONFIRMAR ASIGNACIÓN</button>
                    <button class="btn no-print" style="display:none; margin-top:10px; width:100%; font-size:10px" id="reedit-${x.id}" onclick="unconfirmCard(${x.id})">RE-EDITAR</button>
                </div>`;
            }).join('');

            // Render Personal
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr style="border-bottom: 1px solid #222">
                    <td style="padding:10px">${p.legajo}</td>
                    <td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button class="btn-red" onclick="delPer(${p.id})">BAJA</button></td>
                </tr>`).join('');

            // Render Archivos
            document.getElementById('list-arc').innerHTML = arc.map(x => `
                <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333">
                    <span>📄 ${x.nombre}</span><button class="btn-red" onclick="delArc(${x.id})">X</button>
                </div>`).join('');
        }

        // --- LÓGICA DE CONFIRMACIÓN ---
        function confirmCard(id) {
            const card = document.getElementById(`card-${id}`);
            card.querySelectorAll('.slot').forEach(slot => {
                const sel = slot.querySelector('select');
                const val = slot.querySelector('.slot-val');
                if(sel.value !== "") {
                    val.innerText = sel.options[sel.selectedIndex].text;
                }
            });
            card.classList.add('is-confirmed');
            document.getElementById(`reedit-${id}`).style.display = "block";
        }

        function unconfirmCard(id) {
            const card = document.getElementById(`card-${id}`);
            card.classList.remove('is-confirmed');
            document.getElementById(`reedit-${id}`).style.display = "none";
        }

        // --- IMPRESIÓN ---
        async function genPuePDF() {
            const d = document.getElementById('rpt-dia').value;
            const m = mesesNombres[document.getElementById('rpt-mes').value - 1];
            const a = document.getElementById('rpt-anio').value;
            const title = `GUARDIAS ${d} DEL ${m} DEL AÑO ${a}`;
            
            document.getElementById('dynamic-title').innerText = title;
            document.getElementById('head-puestos').style.display = "block";
            
            // Ocultar botones de sistema
            document.querySelectorAll('.no-print').forEach(el => el.style.display = 'none');
            
            const opt = { 
                margin: 5, 
                filename: `Guardias_${d}_${m}.pdf`, 
                html2canvas: { scale: 2, backgroundColor: '#000' }, 
                jsPDF: { unit: 'mm', format: 'a3', orientation: 'landscape' } 
            };

            html2pdf().set(opt).from(document.getElementById('area-puestos-reporte')).save().then(async () => {
                document.getElementById('head-puestos').style.display = "none";
                document.querySelectorAll('.no-print').forEach(el => el.style.display = 'block');
                await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: title, tipo: 'PDF', fecha: new Date().toLocaleString()})});
                render();
            });
        }

        // --- CRUD SOPORTE ---
        async function savePuesto() {
            const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function addPersonal() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function delPue(id) { if(confirm("¿Eliminar?")) await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }
        async function delPer(id) { if(confirm("¿Baja?")) await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delArc(id) { await fetch(`/api/archivos?id=${id}`, {method:'DELETE'}); render(); }

        window.onload = () => {
            const rD = document.getElementById('rpt-dia'); const rM = document.getElementById('rpt-mes'); const rA = document.getElementById('rpt-anio');
            mesesNombres.forEach((n, i) => rM.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) rA.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            for(let i=1; i<=31; i++) rD.innerHTML += `<option value="${i}" ${i==new Date().getDate()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
