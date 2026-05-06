import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Base de Datos - Ordo Klar v56
DB_PATH = os.path.abspath("ordoklar_v56_master.db")

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

# --- INTERFAZ ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v56</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); background: #0a0a0a; }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
        nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; max-width: 100%; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        
        /* TABLA PLANILLA */
        .table-wrap { overflow-x: auto; border: 1px solid #333; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; font-size: 10px; }
        th, td { border: 1px solid #222; text-align: center; padding: 6px 3px; min-width: 28px; }
        .col-name { text-align: left; min-width: 200px; padding-left: 10px; color: var(--gold); font-weight: bold; }
        
        /* ESTADOS */
        .st-12 { background: #1b4332; color: #fff; } .st-ART { background: #5a1818; } .st-VAC { background: #004e89; } 

        /* PUESTOS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }
        .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-radius: 5px; border-top: 4px solid var(--gold); }
        .slot { background: #111; padding: 6px; margin-top: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        .slot select { background: #000; color: #fff; border: 1px solid #444; font-size: 11px; width: 70%; }
        .slot-fixed { font-weight: bold; color: #fff; display: none; }
        
        .is-confirmed { border-top-color: #1b4332; }
        .is-confirmed select, .is-confirmed .btn-confirm { display: none; }
        .is-confirmed .slot-fixed { display: block; }
        .btn-confirm { width: 100%; margin-top: 10px; background: #1b4332; color: #fff; border: none; padding: 8px; cursor: pointer; font-weight: bold; }

        @media print { .no-print { display: none !important; } table { font-size: 9px; } }
    </style>
</head>
<body>

    <div class="header"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>

    <nav class="no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA MENSUAL -->
        <div id="s-pla" class="section active-section">
            <div class="box no-print" style="display:flex; gap:15px">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="window.print()">🖨️ Imprimir Planilla</button>
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
            <div class="box no-print">
                <div style="display:flex; gap:10px; flex-wrap:wrap">
                    <input type="text" id="p-nom" placeholder="Objetivo">
                    <input type="text" id="p-hor" placeholder="Horario">
                    <input type="number" id="p-dot" placeholder="Dotación">
                    <button class="btn" onclick="addPuesto()">+ Crear Puesto</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
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
                <table style="width:100%; text-align:left">
                    <thead><tr style="color:var(--gold)"><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- INFORMES -->
        <div id="s-inf" class="section">
            <div class="box" style="text-align:center">
                <h2>CENTRO DE INFORMES</h2>
                <button class="btn" onclick="printNomina()">DESCARGAR NÓMINA PERSONAL (PDF)</button>
            </div>
        </div>

    </div>

    <!-- AREA NOMINA OCULTA -->
    <div id="area-nomina-print" style="display:none; background:white; color:black; padding:40px">
        <h1 id="tit-nomina" style="text-align:center"></h1>
        <table style="width:100%; border:1px solid #000; margin-top:20px">
            <thead><tr style="background:#ddd"><th>NOMBRE</th><th>APELLIDO</th><th>LEGAJO</th></tr></thead>
            <tbody id="body-nomina"></tbody>
        </table>
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
            const [per, pue, nov] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // 1. PLANILLA
            let h = `<tr><th class="col-name">AGENTE</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th style="background:var(--gold); color:black">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = ""; let sumHs = new Array(dias).fill(0);
            per.forEach(p => {
                let rowHs = 0;
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    if(d.estado == '12') { rowHs += 12; sumHs[i-1] += 12; }
                    r += `<td class="st-${d.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                r += `<td style="font-weight:bold; color:var(--gold)">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;
            document.getElementById('f-pla').innerHTML = `<tr><td class="col-name">TOTAL HORAS</td>${sumHs.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>`;

            // 2. PUESTOS
            const opts = `<option value="">-- Asignar --</option>` + per.map(p => `<option>${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let s = "";
                for(let i=1; i<=x.dotacion; i++) s += `<div class="slot"><select>${opts}</select><span class="slot-fixed"></span></div>`;
                return `
                <div class="card-pue" id="pue-${x.id}">
                    <div style="float:right" class="no-print"><button onclick="delPue(${x.id})" style="background:none; border:none; color:red; cursor:pointer">✖</button></div>
                    <h3>${x.nombre}</h3><small>${x.horario}</small>
                    ${s}
                    <button class="btn-confirm no-print" onclick="fixPue(${x.id})">CONFIRMAR PUESTO</button>
                    <button class="btn no-print" style="display:none; width:100%; margin-top:5px; font-size:10px" id="ed-${x.id}" onclick="unfixPue(${x.id})">MODIFICAR</button>
                </div>`;
            }).join('');

            // 3. PERSONAL
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido}</td><td>${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="color:red; background:none; border:none; cursor:pointer">Eliminar</button></td></tr>
            `).join('');
        }

        async function cycleSt(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let nxt = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:nxt})});
            render();
        }

        function fixPue(id) {
            const card = document.getElementById(`pue-${id}`);
            card.querySelectorAll('.slot').forEach(slot => {
                const sel = slot.querySelector('select');
                const fixed = slot.querySelector('.slot-fixed');
                if(sel.value) fixed.innerText = sel.value;
            });
            card.classList.add('is-confirmed');
            document.getElementById(`ed-${id}`).style.display = "block";
        }

        function unfixPue(id) {
            const card = document.getElementById(`pue-${id}`);
            card.classList.remove('is-confirmed');
            document.getElementById(`ed-${id}`).style.display = "none";
        }

        async function printNomina() {
            const per = await fetch('/api/personal').then(r => r.json());
            const hoy = new Date().toLocaleDateString('es-AR');
            document.getElementById('tit-nomina').innerText = `NOMINA DE PERSONAL A LA FECHA ${hoy}`;
            document.getElementById('body-nomina').innerHTML = per.map(p => `<tr><td>${p.nombre}</td><td>${p.apellido}</td><td>${p.legajo}</td></tr>`).join('');
            const area = document.getElementById('area-nomina-print');
            area.style.display = 'block';
            html2pdf().from(area).set({ margin: 10, filename: `Nomina_${hoy}.pdf` }).save().then(() => area.style.display='none');
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

        async function delPer(id) { if(confirm("¿Eliminar?")) await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delPue(id) { if(confirm("¿Eliminar?")) await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            mesesNombres.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
