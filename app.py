import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Configuración de Base de Datos
DB_PATH = os.path.abspath("ordoklar_v46_master.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla de Personal
    c.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
    # Tabla de Puestos (Objetivos)
    c.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
    # Tabla de Novedades (Planilla)
    c.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- ENDPOINTS API ---

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

# --- INTERFAZ DE USUARIO ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR v46</title>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #EEE; }
        body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; }
        
        /* Header & Nav */
        .header { text-align: center; padding: 20px; border-bottom: 2px solid var(--gold); background: linear-gradient(to bottom, #111, #000); }
        nav { display: flex; justify-content: center; background: #0a0a0a; sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border); }
        nav button { background: none; border: none; color: #777; padding: 15px 25px; cursor: pointer; font-weight: bold; transition: 0.3s; text-transform: uppercase; letter-spacing: 1px; }
        nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }

        .container { padding: 20px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* Componentes Comunes */
        .box { background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .flex-row { display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; }
        .form-group { display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 200px; }
        label { font-size: 12px; color: var(--gold); text-transform: uppercase; font-weight: bold; }
        input, select { background: #000; border: 1px solid #444; color: #fff; padding: 10px; border-radius: 4px; outline: none; }
        input:focus { border-color: var(--gold); }
        .btn { background: var(--gold); color: #000; border: none; padding: 12px 24px; font-weight: bold; cursor: pointer; border-radius: 4px; transition: 0.2s; }
        .btn:hover { background: #fff; }

        /* Estilos de Puestos */
        .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card-pue { background: #0a0a0a; border: 1px solid var(--border); border-top: 5px solid var(--gold); padding: 20px; border-radius: 8px; position: relative; }
        .card-pue h3 { margin: 0; color: var(--gold); font-size: 20px; }
        .card-pue .info { color: #888; font-size: 14px; margin: 10px 0; border-bottom: 1px solid #222; padding-bottom: 10px; }
        
        .puesto-asignacion { margin-top: 15px; }
        .slot { background: #151515; padding: 10px; margin-bottom: 8px; border-radius: 5px; display: flex; align-items: center; justify-content: space-between; }
        .slot span { font-size: 11px; font-weight: bold; color: #666; }
        .slot select { width: 70%; font-size: 12px; padding: 5px; }

        .actions { position: absolute; top: 15px; right: 15px; display: flex; gap: 8px; }
        .btn-sm-edit { background: #222; color: #D4AF37; border: 1px solid #D4AF37; padding: 5px 10px; font-size: 10px; cursor: pointer; border-radius: 3px; }
        .btn-sm-del { background: #400; color: #fff; border: none; padding: 5px 10px; font-size: 10px; cursor: pointer; border-radius: 3px; }

        /* Tabla Planilla */
        .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; min-width: 1000px; }
        th, td { border: 1px solid #222; text-align: center; padding: 8px; font-size: 12px; }
        th { background: #111; color: var(--gold); }
        .col-name { text-align: left; width: 200px; position: sticky; left: 0; background: #0a0a0a; z-index: 10; font-weight: bold; }
        
        /* Estados */
        .st-12 { background: #1b4332; color: #fff; }
        .st-ART { background: #5a1818; color: #fff; }
        .st-VAC { background: #004e89; color: #fff; }
        .st-F { color: #555; }
    </style>
</head>
<body>

    <div class="header">
        <h1 style="margin:0; letter-spacing: 5px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#555; font-size:12px; margin:5px 0 0 0;">PLATAFORMA INTEGRAL DE GESTIÓN OPERATIVA</p>
    </div>

    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Gestión de Puestos</button>
        <button id="n-per" onclick="tab('per')">Base Personal</button>
    </nav>

    <div class="container">
        
        <!-- SECCIÓN: PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box flex-row">
                <div class="form-group">
                    <label>Mes</label>
                    <select id="m-sel" onchange="render()"></select>
                </div>
                <div class="form-group">
                    <label>Año</label>
                    <select id="a-sel" onchange="render()"></select>
                </div>
            </div>
            <div class="table-wrap">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- SECCIÓN: PUESTOS (MEJORADA) -->
        <div id="s-pue" class="section">
            <div class="box">
                <h3 id="pue-form-title" style="margin-top:0; color:var(--gold)">Configurar Nuevo Puesto</h3>
                <div class="flex-row">
                    <input type="hidden" id="p-id">
                    <div class="form-group">
                        <label>Nombre del Objetivo / Puesto</label>
                        <input type="text" id="p-nom" placeholder="Ej: Portería Central">
                    </div>
                    <div class="form-group">
                        <label>Rango Horario</label>
                        <input type="text" id="p-hor" placeholder="Ej: 06:00 a 18:00">
                    </div>
                    <div class="form-group">
                        <label>Dotación (Cant. Personal)</label>
                        <input type="number" id="p-dot" placeholder="Ej: 2">
                    </div>
                    <button class="btn" id="p-btn-main" onclick="savePuesto()">Guardar Cambios</button>
                    <button class="btn" style="background:#333; color:white" onclick="clearPuestoForm()">Cancelar</button>
                </div>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- SECCIÓN: PERSONAL -->
        <div id="s-per" class="section">
            <div class="box flex-row">
                <div class="form-group"><label>Legajo</label><input type="text" id="per-l"></div>
                <div class="form-group"><label>Apellido</label><input type="text" id="per-a"></div>
                <div class="form-group"><label>Nombre</label><input type="text" id="per-n"></div>
                <button class="btn" onclick="addPersonal()">Dar de Alta</button>
            </div>
            <div class="box">
                <table style="min-width: 100%;">
                    <thead><tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acciones</th></tr></thead>
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
            let h = `<tr><th class="col-name">LISTADO DE AGENTES</th>`;
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += `</tr>`;
            document.getElementById('h-pla').innerHTML = h;

            let b = "";
            per.forEach(p => {
                let r = `<td class="col-name">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1; i<=dias; i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f) || {estado:'F'};
                    r += `<td class="st-${d.estado}" style="cursor:pointer" onclick="cycle(this, ${p.id}, '${f}')">${d.estado}</td>`;
                }
                b += `<tr>${r}</tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;

            // Render Puestos (Tarjetas con personal asignado)
            document.getElementById('grid-pue').innerHTML = pue.map(x => {
                let slots = "";
                for(let i=1; i<=x.dotacion; i++){
                    slots += `
                    <div class="slot">
                        <span>POSICIÓN ${i}</span>
                        <select>
                            <option value="">-- Sin Asignar --</option>
                            ${per.map(p => `<option value="${p.id}">${p.apellido}, ${p.nombre}</option>`).join('')}
                        </select>
                    </div>`;
                }
                return `
                <div class="card-pue">
                    <div class="actions">
                        <button class="btn-sm-edit" onclick="editPuesto(${x.id}, '${x.nombre}', '${x.horario}', ${x.dotacion})">EDITAR</button>
                        <button class="btn-sm-del" onclick="delPuesto(${x.id})">ELIMINAR</button>
                    </div>
                    <h3>${x.nombre}</h3>
                    <div class="info">H: ${x.horario} | Personal: ${x.dotacion}</div>
                    <div class="puesto-asignacion">${slots}</div>
                </div>`;
            }).join('');

            // Render Lista Personal en pestaña Personal
            document.getElementById('list-per').innerHTML = per.map(p => `
                <tr>
                    <td>${p.legajo}</td>
                    <td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button class="btn-sm-del" onclick="delPersonal(${p.id})">BAJA</button></td>
                </tr>
            `).join('');
        }

        // --- FUNCIONES DE PUESTOS ---

        async function savePuesto() {
            const id = document.getElementById('p-id').value;
            const payload = {
                nombre: document.getElementById('p-nom').value,
                horario: document.getElementById('p-hor').value,
                dotacion: parseInt(document.getElementById('p-dot').value)
            };

            if(!payload.nombre || !payload.dotacion) return alert("Complete nombre y dotación");

            const method = id ? 'PUT' : 'POST';
            if(id) payload.id = id;

            await fetch('/api/puestos', {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            clearPuestoForm();
            render();
        }

        function editPuesto(id, nom, hor, dot) {
            document.getElementById('p-id').value = id;
            document.getElementById('p-nom').value = nom;
            document.getElementById('p-hor').value = hor;
            document.getElementById('p-dot').value = dot;
            document.getElementById('pue-form-title').innerText = "Editando: " + nom;
            document.getElementById('p-btn-main').innerText = "Actualizar Puesto";
            window.scrollTo({top: 0, behavior: 'smooth'});
        }

        async function delPuesto(id) {
            if(confirm("¿Seguro que desea eliminar este puesto?")) {
                await fetch(`/api/puestos?id=${id}`, { method: 'DELETE' });
                render();
            }
        }

        function clearPuestoForm() {
            document.getElementById('p-id').value = "";
            document.getElementById('p-nom').value = "";
            document.getElementById('p-hor').value = "";
            document.getElementById('p-dot').value = "";
            document.getElementById('pue-form-title').innerText = "Configurar Nuevo Puesto";
            document.getElementById('p-btn-main').innerText = "Guardar Cambios";
        }

        // --- FUNCIONES DE PLANILLA Y PERSONAL ---

        async function cycle(td, pid, fecha) {
            const estados = ["F", "12", "ART", "VAC"];
            let actual = td.innerText;
            let prox = estados[(estados.indexOf(actual) + 1) % estados.length];
            await fetch('/api/novedades', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({p_id: pid, fecha: fecha, estado: prox})
            });
            render();
        }

        async function addPersonal() {
            const data = {
                legajo: document.getElementById('per-l').value,
                apellido: document.getElementById('per-a').value,
                nombre: document.getElementById('per-n').value
            };
            await fetch('/api/personal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            render();
        }

        async function delPersonal(id) {
            if(confirm("¿Eliminar agente?")) {
                await fetch(`/api/personal?id=${id}`, { method: 'DELETE' });
                render();
            }
        }

        // --- INICIO ---
        window.onload = () => {
            const mSel = document.getElementById('m-sel');
            const aSel = document.getElementById('a-sel');
            const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            meses.forEach((m, i) => mSel.innerHTML += `<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${m}</option>`);
            for(let i=2025; i<=2027; i++) aSel.innerHTML += `<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
