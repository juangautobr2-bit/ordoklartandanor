import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v73_final_check'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v73.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        conn.execute('CREATE TABLE IF NOT EXISTS asignaciones (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, PRIMARY KEY(puesto_id, slot_index))')
        conn.commit()

init_db()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template_string(HTML_LOGIN)

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(HTML_UI)

# --- API ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            if d.get('id'):
                conn.execute("UPDATE puestos SET nombre=?, horario=?, dotacion=? WHERE id=?", (d['nombre'], d['horario'], int(d['dotacion']), d['id']))
            else:
                conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", (d['nombre'], d['horario'], int(d['dotacion'])))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
            conn.commit()
        
        rows = conn.execute("SELECT * FROM puestos").fetchall()
        puestos = []
        for r in rows:
            p = dict(r)
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
            puestos.append(p)
    return jsonify(puestos)

@app.route('/api/asignar', methods=['POST'])
def asignar():
    d = request.json
    with get_db_connection() as conn:
        conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)",
                     (d['puesto_id'], d['slot_index'], d['personal_id'] if d['personal_id'] else None))
        conn.commit()
    return jsonify({"status":"ok"})

# --- TEMPLATES ---
HTML_LOGIN = '''
<!DOCTYPE html><html><head><title>Login</title><style>
body{background:#000;color:#D4AF37;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;}
.box{border:1px solid #D4AF37;padding:30px;border-radius:10px;text-align:center;}
input{display:block;width:100%;margin:10px 0;padding:10px;background:#111;color:#fff;border:1px solid #333;}
button{width:100%;padding:10px;background:#D4AF37;font-weight:bold;cursor:pointer;border:none;}
</style></head><body><div class="box"><h2>ORDO KLAR</h2><form method="POST"><input name="username" placeholder="Admin"><input type="password" name="password" placeholder="Pass"><button>ENTRAR</button></form></div></body></html>
'''

HTML_UI = '''
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v73</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
    body { background: var(--bg); color: #eee; font-family: sans-serif; margin: 0; }
    nav { display: flex; justify-content: center; background: #111; border-bottom: 1px solid var(--gold); padding: 10px; }
    nav button { background: none; border: none; color: #777; padding: 10px 20px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 2px solid var(--gold); }
    .container { padding: 20px; max-width: 1200px; margin: auto; }
    .section { display: none; } .active-section { display: block; }
    .box { background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
    .card { background: #1a1a1a; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 5px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 10px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    .btn-save { background: #28a745; color: #fff; width: 100%; margin-top: 10px; }
    input, select { background: #000; color: #fff; border: 1px solid #444; padding: 10px; margin: 5px 0; width: 100%; box-sizing: border-box; }
    .slot { background: #222; padding: 5px; margin: 5px 0; border-radius: 4px; }
    .actions { display: flex; gap: 5px; margin-top: 10px; }
    .btn-edit { background: #555; color: #fff; flex: 1; }
    .btn-del { background: #700; color: #fff; flex: 1; }
    @media print { nav, .box, .actions, .btn-save { display: none !important; } .section { display: block !important; } }
</style>
</head><body>
    <nav>
        <button onclick="tab('pue')" id="n-pue" class="active">GUARDIAS-PUESTOS</button>
        <button onclick="tab('per')" id="n-per">PERSONAL</button>
        <button onclick="window.print()" class="btn" style="margin-left: 20px;">IMPRIMIR INFORME</button>
    </nav>

    <div class="container">
        <!-- SECCION GUARDIAS-PUESTOS -->
        <div id="s-pue" class="section active-section">
            <div class="box">
                <h3>Nueva Guardia / Puesto</h3>
                <input type="hidden" id="p-id">
                <input id="p-nom" placeholder="Nombre (ej: Objetivo Lomas)">
                <input id="p-hor" placeholder="Horario (ej: 08:00 a 20:00)">
                <input id="p-dot" type="number" placeholder="Cantidad Personal Asignado">
                <button class="btn" onclick="crearPuesto()" id="btn-main">CREAR GUARDIA</button>
            </div>
            <div id="grid-pue" class="grid"></div>
        </div>

        <!-- SECCION PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <h3>Alta de Personal</h3>
                <input id="per-l" placeholder="Legajo">
                <input id="per-a" placeholder="Apellido">
                <input id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPer()">GUARDAR PERSONAL</button>
            </div>
            <div class="box">
                <table style="width:100%; border-collapse: collapse;">
                    <thead><tr style="color:var(--gold)"><th>Legajo</th><th>Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>
    </div>

<script>
    let personalCache = [];

    async function tab(t){
        document.querySelectorAll('.section').forEach(s=>s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
        document.getElementById('s-'+t).classList.add('active-section');
        document.getElementById('n-'+t).classList.add('active');
        render();
    }

    async function render(){
        const resPer = await fetch('/api/personal');
        personalCache = await resPer.json();
        const resPue = await fetch('/api/puestos');
        const puestos = await resPue.json();

        // Lista Personal
        document.getElementById('list-per').innerHTML = personalCache.map(p=>`
            <tr style="border-bottom: 1px solid #222;">
                <td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="delPer(${p.id})" style="color:red;background:none;border:none;cursor:pointer">Eliminar</button></td>
            </tr>`).join('');

        // Grid de Puestos
        document.getElementById('grid-pue').innerHTML = puestos.map(p=>{
            let selects = "";
            for(let i=0; i<p.dotacion; i++){
                let options = `<option value="">-- Seleccionar --</option>`;
                personalCache.forEach(pers => {
                    const selected = p.asignados[i] == pers.id ? 'selected' : '';
                    options += `<option value="${pers.id}" ${selected}>${pers.apellido.toUpperCase()}, ${pers.nombre}</option>`;
                });
                selects += `<div class="slot"><select id="sel-${p.id}-${i}">${options}</select></div>`;
            }
            return `
            <div class="card">
                <h2 style="color:var(--gold);margin:0">${p.nombre}</h2>
                <p><b>Horario:</b> ${p.horario}</p>
                <p><small>Dotación: ${p.dotacion} personas</small></p>
                ${selects}
                <button class="btn btn-save" onclick="confirmarGuardia(${p.id}, ${p.dotacion})">CONFIRMAR GUARDIA</button>
                <div class="actions">
                    <button class="btn btn-edit" onclick="cargarEdicion(${p.id}, '${p.nombre}', '${p.horario}', ${p.dotacion})">EDITAR</button>
                    <button class="btn btn-del" onclick="delPue(${p.id})">ELIMINAR</button>
                </div>
            </div>`;
        }).join('');
    }

    async function crearPuesto(){
        const id = document.getElementById('p-id').value;
        const d = {
            id: id ? id : null,
            nombre: document.getElementById('p-nom').value,
            horario: document.getElementById('p-hor').value,
            dotacion: document.getElementById('p-dot').value
        };
        if(!d.nombre || !d.dotacion) return alert("Faltan datos");
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        resetForm();
        render();
    }

    function cargarEdicion(id, nom, hor, dot){
        document.getElementById('p-id').value = id;
        document.getElementById('p-nom').value = nom;
        document.getElementById('p-hor').value = hor;
        document.getElementById('p-dot').value = dot;
        document.getElementById('btn-main').innerText = "ACTUALIZAR GUARDIA";
        window.scrollTo(0,0);
    }

    function resetForm(){
        document.getElementById('p-id').value = "";
        document.getElementById('p-nom').value = "";
        document.getElementById('p-hor').value = "";
        document.getElementById('p-dot').value = "";
        document.getElementById('btn-main').innerText = "CREAR GUARDIA";
    }

    async function confirmarGuardia(pId, dot){
        for(let i=0; i<dot; i++){
            const perId = document.getElementById(`sel-${pId}-${i}`).value;
            await fetch('/api/asignar', {
                method:'POST', 
                headers:{'Content-Type':'application/json'}, 
                body:JSON.stringify({puesto_id:pId, slot_index:i, personal_id:perId})
            });
        }
        alert("Guardia Guardada con Éxito");
        render();
    }

    async function addPer(){
        const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        render();
    }

    async function delPer(id){ if(confirm('¿Eliminar?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
    async function delPue(id){ if(confirm('¿Eliminar Puesto?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

    window.onload = render;
</script>
</body></html>
