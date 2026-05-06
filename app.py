import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Base de Datos - Ordo Klar v57 Final
DB_PATH = os.path.abspath("ordoklar_v57_final.db")

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
    c.execute('CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT)')
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

@app.route('/api/archivos', methods=['GET', 'POST', 'DELETE'])
def handle_archivos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO archivos (nombre, fecha) VALUES (?, ?)", (d['nombre'], d['fecha']))
        conn.commit()
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM archivos WHERE id=?", (request.args.get('id'),))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM archivos ORDER BY id DESC").fetchall()]
    conn.close()
    return jsonify(res)

# --- INTERFAZ ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v57 | PREMIUM</title>
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
        
        /* PLANILLA COLORES */
        .table-wrap { overflow-x: auto; border: 1px solid #333; }
        table { width: 100%; border-collapse: collapse; font-size: 10px; color: #fff; background: #000; }
        th, td { border: 1px solid #333; text-align: center; padding: 6px 2px; min-width: 30px; }
        .col-name { text-align: left; min-width: 200px; padding-left: 10px; color: var(--gold); font-weight: bold; }
        
        .st-12 { background: #1b4332 !important; } /* Verde */
        .st-F { background: #ff8c00 !important; color: #000; font-weight: bold; } /* Naranja */
        .st-ART { background: #6a0dad !important; } /* Violeta */
        .st-VAC { background: #0000ff !important; } /* Azul */
        .st-FE { background: #ff0000 !important; } /* Rojo */

        /* PUESTOS */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }
        .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-radius: 5px; border-top: 4px solid var(--gold); }
        .slot { background: #111; padding: 6px; margin-top: 5px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #222; }
        .slot select { background: #000; color: #fff; border: 1px solid #444; font-size: 11px; width: 70%; }
        .slot-fixed { font-weight: bold; color: #fff; display: none; font-size: 12px; }
        
        .is-confirmed { border-top-color: #1b4332; background: #020804; }
        .is-confirmed select, .is-confirmed .btn-confirm { display: none; }
        .is-confirmed .slot-fixed { display: block; }
        .btn-confirm { width: 100%; margin-top: 10px; background: #1b4332; color: #fff; border: none; padding: 8px; cursor: pointer; font-weight: bold; }

        #print-header { display: none; text-align: center; color: white; background: black; padding: 20px; border-bottom: 2px solid var(--gold); }

        @media print { 
            .no-print { display: none !important; } 
            #print-header { display: block !important; }
            body { background: white; }
            .container { padding: 0; }
            table { color: black; border: 1px solid black; }
            th, td { border: 1px solid black; }
            .st-12 { color: white; -webkit-print-color-adjust: exact; }
        }
    </style>
</head>
<body>

    <div id="print-header">
        <h1 id="print-title">ORDO KLAR - INFORME</h1>
    </div>

    <div class="header no-print"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>

    <nav class="no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-inf" onclick="tab('inf')">Informes</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box no-print" style="display:flex; gap:15px">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="printPlanilla()">🖨️ Imprimir Planilla</button>
            </div>
            <div class="table-wrap">
                <table id="full-planilla">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="box no-print" style="display:flex; gap:10px">
                <input type="text" id="p-nom" placeholder="Objetivo">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-dot" placeholder="Dotación">
                <button class="btn" onclick="addPuesto()">Crear Puesto</button>
                <button class="btn" style="background:#fff" onclick="printPue()">🖨️ Imprimir Guardias</button>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">Cargar Agente</button>
            </div>
            <div class="box">
                <table style="width:100%; text-align:left">
                    <thead><tr style="color:var(--gold)"><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

        <!-- ARCHIVOS (HISTORIAL) -->
        <div id="s-arc" class="section">
            <div class="box">
                <h3>HISTORIAL DE INFORMES ELABORADOS</h3>
                <div id="historial-list"></div>
            </div>
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
            const [per, pue, nov, arc] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/archivos').then(r => r.json())
            ]);

            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // RENDER PLANILLA
            let h = `<tr><th class="col-name">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `<th style="background:var(--gold); color:black">HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = ""; let sumHs = new Array(dias).fill(0); let cntPer = new Array(dias).fill(0);
            per.forEach(p => {
                let rowHs = 0;
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    if(d.estado == '12') { rowHs += 12; sumHs[i-1] += 12; cntPer[i-1]++; }
                    r += `<td class="st-${d.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                r += `<td style="font-weight:bold; color:var(--gold)">${rowHs}</td>`;
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;
            document.getElementById('f-pla').innerHTML = `
                <tr><td class="col-name">CANT. PERSONAL ACTIVO</td>${cntPer.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>
                <tr style="background:#111"><td class="col-name">TOTAL HORAS DÍA</td>${sumHs.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>`;

            // RENDER PUESTOS
            const opts = `<option value="">-- Seleccionar --</option>` + per.map(p => `<option>${p.apellido.toUpperCase()}, ${p.nombre}</option>`).join('');
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let s = "";
                for(let i=1; i<=x.dotacion; i++) s += `<div class="slot"><select>${opts}</select><span class="slot-fixed"></span></div>`;
                return `
                <div class="card-pue" id="pue-${x.id}">
                    <div style="float:right" class="no-print"><button onclick="delPue(${x.id})" style="background:none; border:none; color:red; cursor:pointer">✖</button></div>
                    <h3 style="margin:0">${x.nombre}</h3><small>${x.horario}</small>
                    ${s}
                    <button class="btn-confirm no-print" onclick="fixPue(${x.id})">CONFIRMAR PUESTO</button>
                    <button class="btn no-print" style="display:none; width:100%; margin-top:5px; font-size:10px" id="ed-${x.id}" onclick="unfixPue(${x.id})">RE-EDITAR</button>
                </div>`;
            }).join('');

            // RENDER ARCHIVOS
            document.getElementById('historial-list').innerHTML = arc.map(x => `
                <div style="display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #333">
                    <span>📄 ${x.nombre} <small style="color:#777">(${x.fecha})</small></span>
                    <button class="btn" style="background:red; color:white; padding:5px" onclick="delArc(${x.id})">ELIMINAR</button>
                </div>`).join('');

            // RENDER LISTA PERSONAL
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido}</td><td>${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="color:red; background:none; border:none; cursor:pointer">Baja</button></td></tr>`).join('');
        }

        async function cycleSt(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC", "FE"];
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

        async function printPlanilla() {
            const m = mesesNombres[document.getElementById('m-sel').value - 1];
            const a = document.getElementById('a-sel').value;
            const tit = `PLANILLA MENSUAL ${m} ${a}`;
            document.getElementById('print-title').innerText = tit;
            await logArch(tit);
            window.print();
        }

        async function printPue() {
            const hoy = new Date().toLocaleDateString();
            const tit = `GUARDIAS - FECHA: ${hoy}`;
            document.getElementById('print-title').innerText = tit;
            await logArch(tit);
            window.print();
        }

        async function logArch(nom) {
            await fetch('/api/archivos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: nom, fecha: new Date().toLocaleString()})});
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

        async function delArc(id) { if(confirm("¿Eliminar del historial?")) await fetch(`/api/archivos?id=${id}`, {method:'DELETE'}); render(); }
        async function delPer(id) { if(confirm("¿Baja de personal?")) await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); }
        async function delPue(id) { if(confirm("¿Eliminar puesto?")) await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            mesesNombres.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2027; i++) a.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
