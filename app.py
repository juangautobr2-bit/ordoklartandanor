import os
import sqlite3
import logging
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v74_stable_engine'

# Configuración de rutas y base de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v74_fixed.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS asignaciones (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, PRIMARY KEY(puesto_id, slot_index))')
        conn.commit()

init_db()

# --- RUTAS ---
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
        elif request.method == 'DELETE':
            pid = request.args.get('id')
            conn.execute("DELETE FROM puestos WHERE id=?", (pid,))
            conn.execute("DELETE FROM asignaciones WHERE puesto_id=?", (pid,))
        conn.commit()
        
        puestos = []
        rows = conn.execute("SELECT * FROM puestos").fetchall()
        for r in rows:
            p = dict(r)
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
            puestos.append(p)
    return jsonify(puestos)

@app.route('/api/asignar_batch', methods=['POST'])
def asignar_batch():
    d = request.json # {puesto_id: X, asignaciones: [{slot: 0, per_id: Y}, ...]}
    with get_db_connection() as conn:
        for a in d['asignaciones']:
            conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)",
                         (d['puesto_id'], a['slot'], a['per_id']))
        conn.commit()
    return jsonify({"status":"ok"})

# --- INTERFAZ ---
HTML_LOGIN = '''
<!DOCTYPE html><html><head><title>Acceso</title><style>
body{background:#000;color:#D4AF37;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;}
.box{border:1px solid #D4AF37;padding:30px;border-radius:10px;text-align:center;width:300px;}
input{display:block;width:100%;margin:10px 0;padding:12px;background:#111;color:#fff;border:1px solid #333;box-sizing:border-box;}
button{width:100%;padding:12px;background:#D4AF37;font-weight:bold;cursor:pointer;border:none;}
</style></head><body><div class="box"><h2>ORDO KLAR</h2><form method="POST"><input name="username" placeholder="Usuario"><input type="password" name="password" placeholder="Contraseña"><button>ENTRAR</button></form></div></body></html>
'''

HTML_UI = '''
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v74</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #121212; --border: #333; }
    body { background: var(--bg); color: #eee; font-family: 'Segoe UI', sans-serif; margin: 0; padding-bottom: 50px; }
    nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 2px solid var(--gold); position: sticky; top: 0; z-index: 1000; }
    nav button { background: none; border: none; color: #777; padding: 20px; cursor: pointer; font-weight: bold; font-size: 14px; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; max-width: 1100px; margin: auto; }
    .section { display: none; } .active-section { display: block; }
    .box { background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 25px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
    .card { background: #080808; border: 1px solid var(--border); border-top: 5px solid var(--gold); padding: 15px; border-radius: 6px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .btn { background: var(--gold); color: #000; border: none; padding: 12px; font-weight: bold; cursor: pointer; border-radius: 4px; transition: 0.3s; }
    .btn:hover { opacity: 0.8; }
    .btn-confirm { background: #1b4332; color: #fff; width: 100%; margin: 10px 0; border: 1px solid #2d6a4f; }
    input, select { background: #000; color: #fff; border: 1px solid #444; padding: 12px; margin: 8px 0; width: 100%; box-sizing: border-box; border-radius: 4px; }
    .slot { background: #1a1a1a; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid var(--gold); }
    .slot select { margin: 0; padding: 5px; font-size: 13px; border: none; }
    .actions { display: flex; gap: 10px; margin-top: 15px; border-top: 1px solid #222; padding-top: 10px; }
    .btn-edit { background: #333; color: #fff; flex: 1; }
    .btn-del { background: #4a0000; color: #fff; flex: 1; }
    @media print { nav, .box, .actions, .btn-confirm { display: none !important; } .section { display: block !important; } .card { border: 1px solid #000; page-break-inside: avoid; margin-bottom: 20px; } }
</style>
</head><body>
    <nav>
        <button onclick="tab('pue')" id="n-pue" class="active">GUARDIAS-PUESTOS</button>
        <button onclick="tab('per')" id="n-per">PERSONAL</button>
        <button onclick="window.print()" style="color:white">🖨️ IMPRIMIR</button>
    </nav>

    <div class="container">
        <!-- SECCION PUESTOS -->
        <div id="s-pue" class="section active-section">
            <div class="box">
                <h3 style="margin-top:0; color:var(--gold)">Configurar Nueva Guardia</h3>
                <input type="hidden" id="p-id">
                <div style="display:flex; gap:10px">
                    <input id="p-nom" placeholder="Nombre del Puesto / Objetivo">
                    <input id="p-hor" placeholder="Horario (ej: 07 a 19)">
                    <input id="p-dot" type="number" placeholder="Cant. Personal" style="width:150px">
                </div>
                <button class="btn" style="width:100%" onclick="savePuesto()" id="btn-main">CREAR PUESTO</button>
            </div>
            <div id="grid-pue" class="grid"></div>
        </div>

        <!-- SECCION PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <h3 style="margin-top:0; color:var(--gold)">Alta de Agente</h3>
                <div style="display:flex; gap:10px">
                    <input id="per-l" placeholder="Legajo">
                    <input id="per-a" placeholder="Apellido">
                    <input id="per-n" placeholder="Nombre">
                </div>
                <button class="btn" style="width:100%" onclick="savePer()">REGISTRAR EN BASE</button>
            </div>
            <div class="box">
                <table style="width:100%; border-collapse: collapse;">
                    <thead style="text-align:left; color:var(--gold)">
                        <tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acción</th></tr>
                    </thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>
    </div>

<script>
    let cachePer = [];

    async function tab(t){
        document.querySelectorAll('.section').forEach(s=>s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
        document.getElementById('s-'+t).classList.add('active-section');
        document.getElementById('n-'+t).classList.add('active');
        render();
    }

    async function render(){
        try {
            const [rPer, rPue] = await Promise.all([fetch('/api/personal'), fetch('/api/puestos')]);
            cachePer = await rPer.json();
            const puestos = await rPue.json();

            // Render Personal
            document.getElementById('list-per').innerHTML = cachePer.map(p=>`
                <tr style="border-bottom: 1px solid #222;">
                    <td style="padding:10px">${p.legajo}</td>
                    <td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button onclick="delPer(${p.id})" style="color:#ff4444; background:none; border:none; cursor:pointer">Eliminar</button></td>
                </tr>`).join('');

            // Render Puestos
            document.getElementById('grid-pue').innerHTML = puestos.map(p=>{
                let slotsHtml = "";
                for(let i=0; i<p.dotacion; i++){
                    let opts = `<option value="">-- Seleccionar Agente --</option>`;
                    cachePer.forEach(per => {
                        const sel = p.asignados[i] == per.id ? 'selected' : '';
                        opts += `<option value="${per.id}" ${sel}>${per.apellido.toUpperCase()}, ${per.nombre}</option>`;
                    });
                    slotsHtml += `<div class="slot"><label><small>Posición ${i+1}</small></label><select id="sel-${p.id}-${i}">${opts}</select></div>`;
                }
                return `
                <div class="card">
                    <h3 style="margin:0; color:var(--gold)">${p.nombre}</h3>
                    <p style="margin:5px 0"><b>Reloj:</b> ${p.horario}</p>
                    <div id="slots-${p.id}">${slotsHtml}</div>
                    <button class="btn btn-confirm" onclick="confirmBatch(${p.id}, ${p.dotacion})">CONFIRMAR GUARDIA</button>
                    <div class="actions">
                        <button class="btn btn-edit" onclick="editMode(${p.id}, '${p.nombre}', '${p.horario}', ${p.dotacion})">EDITAR</button>
                        <button class="btn btn-del" onclick="delPue(${p.id})">BORRAR</button>
                    </div>
                </div>`;
            }).join('');
        } catch(e) { console.error("Render Error:", e); }
    }

    async function savePuesto(){
        const d = {
            id: document.getElementById('p-id').value || null,
            nombre: document.getElementById('p-nom').value,
            horario: document.getElementById('p-hor').value,
            dotacion: document.getElementById('p-dot').value
        };
        if(!d.nombre || !d.dotacion) return alert("Nombre y Dotación son obligatorios");
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        clearForm();
        render();
    }

    async function confirmBatch(pId, dot){
        const asigs = [];
        for(let i=0; i<dot; i++){
            const val = document.getElementById(`sel-${pId}-${i}`).value;
            asigs.push({slot: i, per_id: val ? parseInt(val) : null});
        }
        await fetch('/api/asignar_batch', {
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body:JSON.stringify({puesto_id: pId, asignaciones: asigs})
        });
        alert("¡Guardia actualizada con éxito!");
        render();
    }

    function editMode(id, nom, hor, dot){
        document.getElementById('p-id').value = id;
        document.getElementById('p-nom').value = nom;
        document.getElementById('p-hor').value = hor;
        document.getElementById('p-dot').value = dot;
        document.getElementById('btn-main').innerText = "GUARDAR CAMBIOS";
        window.scrollTo(0,0);
    }

    function clearForm(){
        document.getElementById('p-id').value = "";
        document.getElementById('p-nom').value = "";
        document.getElementById('p-hor').value = "";
        document.getElementById('p-dot').value = "";
        document.getElementById('btn-main').innerText = "CREAR PUESTO";
    }

    async function savePer(){
        const d = {legajo:document.getElementById('per-l').value, apellido:document.getElementById('per-a').value, nombre:document.getElementById('per-n').value};
        if(!d.legajo || !d.apellido) return alert("Faltan datos del agente");
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('per-l').value=""; document.getElementById('per-a').value=""; document.getElementById('per-n').value="";
        render();
    }

    async function delPer(id){ if(confirm('¿Dar de baja agente?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
    async function delPue(id){ if(confirm('¿Eliminar este puesto de guardia?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

    window.onload = render;
</script>
</body></html>
