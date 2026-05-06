import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Persistencia Total en Ruta Absoluta
DB_PATH = os.path.abspath("ordoklar_v45_master.db")

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

# --- APIs ---
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

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR v45 | Gestión de Puestos</title>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; }
        
        .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); }
        nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #666; padding: 15px 20px; cursor: pointer; font-weight: bold; font-size: 13px; text-transform: uppercase; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 15px; box-sizing: border-box; }
        .section { display: none; }
        .active-section { display: block; }

        .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 15px; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 10px; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; flex: 1; }
        .btn { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; }
        
        /* Puestos Visuals */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 15px; }
        .card-pue { background: #080808; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 6px; }
        .card-pue h3 { margin: 0; color: var(--gold); text-transform: uppercase; font-size: 18px; }
        .card-pue p { color: #888; font-size: 13px; margin: 5px 0 15px 0; }
        
        .assign-slot { background: #151515; padding: 8px; margin-bottom: 5px; border-radius: 4px; display: flex; align-items: center; gap: 10px; }
        .assign-slot span { font-size: 11px; color: var(--gold); font-weight: bold; width: 60px; }

        .btn-edit { background: #333; color: white; border: none; padding: 6px; cursor: pointer; font-size: 11px; margin-right: 5px; border-radius: 3px; }
        .btn-del { background: #5a1818; color: white; border: none; padding: 6px; cursor: pointer; font-size: 11px; border-radius: 3px; }

        /* Planilla Compacta */
        .table-wrap { width: 100%; border: 1px solid var(--border); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 10px; }
        th, td { border: 1px solid #222; text-align: center; padding: 5px 0; }
        .col-name { text-align: left; width: 150px; padding-left: 8px; color: var(--gold); font-weight: bold; }
        .st-12 { background: #1b4332; } .st-F { color: #444; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 3px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#555; font-size:10px; margin:0;">SISTEMA DE GESTIÓN TÉCNICA v45</p>
    </div>

    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>

    <div class="container">
        
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box flex-row">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
            </div>
            <div class="table-wrap">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- PUESTOS (EDICIÓN Y ASIGNACIÓN) -->
        <div id="s-pue" class="section">
            <div class="box">
                <h4 id="form-title" style="margin-top:0; color:var(--gold)">NUEVO OBJETIVO / PUESTO</h4>
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <input type="text" id="p-nom" placeholder="Nombre del Puesto">
                    <input type="text" id="p-hor" placeholder="Horario (Ej: 07:00 a 19:00)">
                    <input type="number" id="p-dot" placeholder="Cant. Personal Requerido">
                    <button class="btn" id="p-btn" onclick="savePuesto()">Guardar Puesto</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box flex-row">
                <input type="text" id="per-l" placeholder="Legajo">
                <input type="text" id="per-a" placeholder="Apellido">
                <input type="text" id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">Alta Agente</button>
            </div>
            <div class="table-wrap">
                <table>
                    <thead><tr><th class="col-name">Legajo</th><th>Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
        let globalPersonal = [];

        function tab(t) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
            document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
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
            
            globalPersonal = per;
            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();

            // Render Planilla
            let h = `<tr><th class="col-name">PERSONAL</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `</tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = "";
            per.forEach(p => {
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre[0]}.</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    r += `<td class="st-${d.estado}" onclick="cycle(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;

            // Render Puestos Cards
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let slots = "";
                for(let i=1; i<=x.dotacion; i++){
                    slots += `
                    <div class="assign-slot">
                        <span>PUESTO ${i}</span>
                        <select>
                            <option>-- Asignar Agente --</option>
                            ${per.map(p => `<option>${p.apellido}, ${p.nombre}</option>`).join('')}
                        </select>
                    </div>`;
                }
                return `
                <div class="card-pue">
                    <div style="float:right">
                        <button class="btn-edit" onclick="editPue(${x.id}, '${x.nombre}', '${x.horario}', ${x.dotacion})">EDITAR</button>
                        <button class="btn-del" onclick="delPue(${x.id})">X</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <p>${x.horario} | Dotación: ${x.dotacion}</p>
                    <div class="slots-container">${slots}</div>
                </div>`;
            }).join('');

            // Listado Personal
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td>
                <td><button class="btn-del" onclick="delPer(${p.id})">BORRAR</button></td></tr>
            `).join('');
        }

        async function savePuesto() {
            const id = document.getElementById('p-id').value;
            const data = {
                nombre: document.getElementById('p-nom').value,
                horario: document.getElementById('p-hor').value,
                dotacion: document.getElementById('p-dot').value
            };

            if(id) {
                data.id = id;
                await fetch('/api/puestos', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
            } else {
                await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
            }
            
            resetForm();
            render();
        }

        function editPue(id, nom, hor, dot) {
            document.getElementById('p-id').value = id;
            document.getElementById('p-nom').value = nom;
            document.getElementById('p-hor').value = hor;
            document.getElementById('p-dot').value = dot;
            document.getElementById('form-title').innerText = "EDITAR PUESTO: " + nom;
            document.getElementById('p-btn').innerText = "Actualizar Puesto";
        }

        function resetForm() {
            document.getElementById('p-id').value = "";
            document.getElementById('p-nom').value = "";
            document.getElementById('p-hor').value = "";
            document.getElementById('p-dot').value = "";
            document.getElementById('form-title').innerText = "NUEVO OBJETIVO / PUESTO";
            document.getElementById('p-btn').innerText = "Guardar Puesto";
        }

        async function cycle(td, pid, fecha) {
            const sts = ["F", "12", "ART", "VAC"];
            let n = sts[(sts.indexOf(td.innerText) + 1) % sts.length];
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:fecha, estado:n})});
            render();
        }

        async function delPue(id) { if(confirm("¿Eliminar puesto?")) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }
        async function addPersonal() {
            const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }
        async function delPer(id) { if(confirm("¿Borrar agente?")) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

        window.onload = () => {
            const m = document.getElementById('m-sel'); const a = document.getElementById('a-sel');
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
