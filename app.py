import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Base de Datos
DB_PATH = os.path.abspath("ordoklar_v54_master.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, tipo TEXT, fecha TEXT)')
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

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['dotacion']))
        conn.commit()
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
    conn.close()
    return jsonify(res)

# --- UI MAESTRA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v54</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); background: #0a0a0a; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #777; padding: 15px; cursor: pointer; font-weight: bold; }
        nav button.active { color: var(--gold); border-bottom: 2px solid var(--gold); }

        .container { padding: 20px; max-width: 1600px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        
        /* ESTILO PUESTOS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-radius: 5px; border-top: 3px solid var(--gold); }
        .slot { background: #111; padding: 8px; margin-top: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
        .slot select { background: #000; color: #fff; border: 1px solid #444; font-size: 11px; width: 70%; }
        .slot-fixed { font-weight: bold; color: #fff; display: none; }
        
        /* ESTADOS DE CONFIRMACIÓN */
        .is-confirmed { border-top-color: #1b4332; background: #020804; }
        .is-confirmed select, .is-confirmed .btn-confirm { display: none; }
        .is-confirmed .slot-fixed { display: block; }
        .btn-confirm { width: 100%; margin-top: 10px; background: #1b4332; color: #fff; border: none; padding: 6px; cursor: pointer; font-size: 11px; }

        /* TABLAS */
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th { color: var(--gold); text-align: left; border-bottom: 1px solid var(--gold); padding: 10px; }
        td { padding: 10px; border-bottom: 1px solid #222; }

        /* IMPRESION */
        #area-nomina-print { background: white; color: black; padding: 40px; display: none; }
        #area-nomina-print table { border: 1px solid #000; }
        #area-nomina-print th { color: black; border-bottom: 2px solid black; }
        #area-nomina-print td { border-bottom: 1px solid #ccc; }

        @media print { .no-print { display: none !important; } }
    </style>
</head>
<body>

    <div class="header"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>

    <nav>
        <button id="n-pue" class="active" onclick="tab('pue')">GESTIÓN DE PUESTOS</button>
        <button id="n-per" onclick="tab('per')">PERSONAL</button>
        <button id="n-inf" onclick="tab('inf')">INFORMES</button>
    </nav>

    <div class="container">
        
        <!-- SECCION PUESTOS -->
        <div id="s-pue" class="section active-section">
            <div class="box no-print">
                <div style="display:flex; gap:10px; flex-wrap:wrap">
                    <input type="text" id="p-nom" placeholder="Nombre del Puesto">
                    <input type="text" id="p-hor" placeholder="Horario (06-18)">
                    <input type="number" id="p-dot" placeholder="Dotación">
                    <button class="btn" onclick="addPuesto()">Crear Puesto</button>
                    <button class="btn" style="background:#fff" onclick="printPuestos()">🖨️ Imprimir Todo</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- SECCION PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <div style="display:flex; gap:10px">
                    <input type="text" id="per-l" placeholder="Legajo">
                    <input type="text" id="per-a" placeholder="Apellido">
                    <input type="text" id="per-n" placeholder="Nombre">
                    <button class="btn" onclick="addPersonal()">Cargar</button>
                </div>
            </div>
            <div class="box">
                <table id="tbl-per">
                    <thead><tr><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acciones</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- SECCION INFORMES -->
        <div id="s-inf" class="section">
            <div class="box" style="text-align:center">
                <h2>CENTRO DE INFORMES</h2>
                <button class="btn" onclick="printNomina()">GENERAR NÓMINA DE PERSONAL (TABLA)</button>
            </div>
        </div>

        <!-- AREA OCULTA PARA GENERAR PDF NOMINA -->
        <div id="area-nomina-print">
            <h1 id="tit-nomina" style="text-align:center; text-transform: uppercase;"></h1>
            <table style="width:100%; margin-top:30px">
                <thead>
                    <tr><th>NOMBRE</th><th>APELLIDO</th><th>LEGAJO</th></tr>
                </thead>
                <tbody id="body-nomina"></tbody>
            </table>
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
            const [per, pue] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);

            // Render Puestos
            const opts = `<option value="">-- Seleccionar --</option>` + per.map(p => `<option>${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let s = "";
                for(let i=1; i<=x.dotacion; i++) s += `<div class="slot"><select>${opts}</select><span class="slot-fixed"></span></div>`;
                return `
                <div class="card-pue" id="pue-${x.id}">
                    <h3 style="margin:0; color:var(--gold)">${x.nombre}</h3>
                    <small>${x.horario}</small>
                    ${s}
                    <button class="btn-confirm no-print" onclick="confirmarPuesto(${x.id})">CONFIRMAR PUESTO</button>
                    <button class="btn no-print" style="display:none; width:100%; margin-top:5px; font-size:10px" id="edit-${x.id}" onclick="editarPuesto(${x.id})">MODIFICAR</button>
                </div>`;
            }).join('');

            // Render Personal
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido}</td><td>${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="color:red; background:none; border:none; cursor:pointer">Eliminar</button></td></tr>
            `).join('');
        }

        function confirmarPuesto(id) {
            const card = document.getElementById(`pue-${id}`);
            card.querySelectorAll('.slot').forEach(slot => {
                const sel = slot.querySelector('select');
                const txt = slot.querySelector('.slot-fixed');
                if(sel.value) {
                    txt.innerText = sel.value;
                    card.classList.add('is-confirmed');
                    document.getElementById(`edit-${id}`).style.display = "block";
                }
            });
        }

        function editarPuesto(id) {
            const card = document.getElementById(`pue-${id}`);
            card.classList.remove('is-confirmed');
            document.getElementById(`edit-${id}`).style.display = "none";
        }

        async function printNomina() {
            const per = await fetch('/api/personal').then(r => r.json());
            const hoy = new Date().toLocaleDateString('es-AR');
            document.getElementById('tit-nomina').innerText = `NOMINA DE PERSONAL A LA FECHA ${hoy}`;
            document.getElementById('body-nomina').innerHTML = per.map(p => `
                <tr><td>${p.nombre}</td><td>${p.apellido}</td><td>${p.legajo}</td></tr>
            `).join('');

            const area = document.getElementById('area-nomina-print');
            area.style.display = 'block';
            html2pdf().from(area).set({
                margin: 10,
                filename: `Nomina_${hoy}.pdf`,
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            }).save().then(() => area.style.display = 'none');
        }

        function printPuestos() {
            window.print();
        }

        async function addPuesto() {
            const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function addPersonal() {
            const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function delPer(id) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }

        window.onload = render;
    </script>
</body>
</html>
