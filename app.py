import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v63_persistent_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v63_FINAL.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        # Nueva tabla para que las asignaciones no se borren
        conn.execute('''CREATE TABLE IF NOT EXISTS asignaciones 
                        (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, 
                        PRIMARY KEY(puesto_id, slot_index))''')
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
@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", 
                         (d.get('nombre'), d.get('horario'), int(d.get('dotacion', 1))))
            conn.commit()
        elif request.method == 'DELETE':
            pid = request.args.get('id')
            conn.execute("DELETE FROM puestos WHERE id=?", (pid,))
            conn.execute("DELETE FROM asignaciones WHERE puesto_id=?", (pid,))
            conn.commit()
        
        puestos = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
        # Adjuntamos las asignaciones actuales a cada puesto
        for p in puestos:
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {a['slot_index']: a['personal_id'] for a in asig}
            
    return jsonify(puestos)

@app.route('/api/asignar', methods=['POST'])
def asignar_personal():
    d = request.json
    with get_db_connection() as conn:
        if d['personal_id'] == "":
            conn.execute("DELETE FROM asignaciones WHERE puesto_id=? AND slot_index=?", (d['puesto_id'], d['slot_index']))
        else:
            conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)",
                         (d['puesto_id'], d['slot_index'], d['personal_id']))
        conn.commit()
    return jsonify({"status": "ok"})

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

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", 
                         (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    return jsonify(res)

# --- UI HTML ---
HTML_LOGIN = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Login</title><style>
body{background:#000;color:#D4AF37;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;}
.box{border:1px solid #D4AF37;padding:30px;border-radius:10px;text-align:center;}
input{display:block;width:100%;margin:10px 0;padding:10px;background:#111;color:#fff;border:1px solid #333;}
button{width:100%;padding:10px;background:#D4AF37;color:#000;font-weight:bold;border:none;cursor:pointer;}
</style></head><body><div class="box"><h1>ORDO KLAR</h1><form method="POST"><input name="username" placeholder="Usuario"><input type="password" name="password" placeholder="Clave"><button>ENTRAR</button></form></div></body></html>
'''

HTML_UI = '''
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v63</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); }
    nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
    nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; }
    .section { display: none; }
    .active-section { display: block; }
    .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    input, select { background: #000; color: #fff; border: 1px solid #444; padding: 8px; margin-right: 5px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; margin-top: 10px; }
    th, td { border: 1px solid #333; padding: 6px; text-align: center; }
    .st-12 { background: #1b4332; } .st-F { background: #444; color:#fff; } .st-ART { background: #6a0dad; } .st-VAC { background: #0000ff; } .st-FE { background: #ff0000; }
    .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
    .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-top: 4px solid var(--gold); }
    .slot { margin-top: 8px; display: flex; justify-content: space-between; align-items: center; }
    .slot-fixed { display: none; font-weight: bold; color: var(--gold); }
    .global-fixed .slot select { display: none; }
    .global-fixed .slot-fixed { display: block; }
    tfoot td { background: #111; color: var(--gold); font-weight: bold; }
</style>
</head><body>
    <div class="header no-print"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>
    <nav class="no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>
    <div class="container">
        <div id="s-pla" class="section active-section">
            <div class="box no-print">
                <select id="m-sel" onchange="render()"></select><select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="window.print()">🖨️ Imprimir</button>
            </div>
            <div style="overflow-x:auto"><table><thead id="h-pla"></thead><tbody id="b-pla"></tbody><tfoot id="f-pla"></tfoot></table></div>
        </div>
        <div id="s-pue" class="section">
            <div class="box no-print">
                <input type="text" id="p-nom" placeholder="Objetivo">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-dot" placeholder="Cant." value="1">
                <button class="btn" onclick="addPuesto()">+ Crear Puesto</button>
                <button class="btn" style="background:#1b4332;color:#fff;margin-left:20px" onclick="toggleGlobalFix(true)">🔒 FIJAR</button>
                <button class="btn" style="background:#444;color:#fff" onclick="toggleGlobalFix(false)">🔓 EDITAR</button>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>
        <div id="s-per" class="section">
            <div class="box"><input id="per-l" placeholder="Legajo"><input id="per-a" placeholder="Apellido"><input id="per-n" placeholder="Nombre"><button class="btn" onclick="addPersonal()">Cargar</button></div>
            <div class="box"><table><thead><tr><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acción</th></tr></thead><tbody id="list-per"></tbody></table></div>
        </div>
    </div>
<script>
    const meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
    function tab(t){ 
        document.querySelectorAll('.section').forEach(s=>s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
        document.getElementById('s-'+t).classList.add('active-section');
        document.getElementById('n-'+t).classList.add('active');
        render();
    }

    async function render(){
        const [per, pue, nov] = await Promise.all([
            fetch('/api/personal').then(r=>r.json()), 
            fetch('/api/puestos').then(r=>r.json()),
            fetch('/api/novedades').then(r=>r.json())
        ]);

        const m = parseInt(document.getElementById('m-sel').value);
        const a = parseInt(document.getElementById('a-sel').value);
        const dias = new Date(a, m, 0).getDate();
        
        // Planilla
        let h = `<tr><th>PERSONAL</th>`;
        for(let i=1;i<=dias;i++) h += `<th>${i}</th>`;
        h += `<th>HS</th></tr>`;
        document.getElementById('h-pla').innerHTML = h;

        let b = ""; let totalesDia = new Array(dias).fill(0);
        per.forEach(p=>{
            let hs = 0; let r = `<td style="text-align:left; color:var(--gold)">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
            for(let i=1;i<=dias;i++){
                const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const n = nov.find(x=>x.personal_id==p.id && x.fecha==f) || {estado:'F'};
                if(n.estado=='12') { hs += 12; totalesDia[i-1]++; }
                r += `<td class="st-${n.estado}" style="cursor:pointer" onclick="cycleSt(this, ${p.id}, '${f}')">${n.estado}</td>`;
            }
            b += `<tr>${r}<td>${hs}</td></tr>`;
        });
        document.getElementById('b-pla').innerHTML = b;
        document.getElementById('f-pla').innerHTML = `<tr><td>CANT. PERSONAL</td>${totalesDia.map(v=>`<td>${v}</td>`).join('')}<td>-</td></tr>`;

        // Puestos con PERSISTENCIA
        const grid = document.getElementById('grid-pue');
        grid.innerHTML = pue.map(pue_data=>{
            let slots_html = "";
            for(let i=0; i<pue_data.dotacion; i++){
                const asig_id = pue_data.asignados[i] || "";
                let options = `<option value="">-- Vacante --</option>`;
                per.forEach(p => {
                    const sel = (p.id == asig_id) ? "selected" : "";
                    options += `<option value="${p.id}" ${sel}>${p.apellido.toUpperCase()} ${p.nombre}</option>`;
                });
                slots_html += `<div class="slot">
                    <select onchange="saveAsig(${pue_data.id}, ${i}, this.value)">${options}</select>
                    <span class="slot-fixed"></span>
                </div>`;
            }
            return `<div class="card-pue"><h3>${pue_data.nombre}</h3><p><small>${pue_data.horario}</small></p>${slots_html}
            <br><button onclick="delPue(${pue_data.id})" style="color:red;background:none;border:none;cursor:pointer;font-size:10px">ELIMINAR</button></div>`;
        }).join('');

        document.getElementById('list-per').innerHTML = per.map(p=>`<tr><td>${p.legajo}</td><td>${p.apellido}</td><td>${p.nombre}</td><td><button onclick="delPer(${p.id})" style="color:red;background:none;border:none;cursor:pointer">Baja</button></td></tr>`).join('');
    }

    async function saveAsig(pue_id, slot_idx, per_id){
        await fetch('/api/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({puesto_id:pue_id, slot_index:slot_idx, personal_id:per_id})});
    }

    async function addPuesto(){
        const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
        if(!d.nombre) return;
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('p-nom').value = ""; render();
    }

    async function addPersonal(){
        const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('per-l').value=""; document.getElementById('per-a').value=""; document.getElementById('per-n').value="";
        render();
    }

    async function cycleSt(td, pid, f){
        const sts = ["F","12","ART","VAC","FE"];
        let nxt = sts[(sts.indexOf(td.innerText)+1)%sts.length];
        await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:nxt})});
        render();
    }

    function toggleGlobalFix(fix){
        const g = document.getElementById('grid-pue');
        if(fix){
            g.classList.add('global-fixed');
            document.querySelectorAll('.slot').forEach(s=>{
                const sel = s.querySelector('select');
                s.querySelector('.slot-fixed').innerText = sel.options[sel.selectedIndex].text;
            });
        } else g.classList.remove('global-fixed');
    }

    async function delPue(id){ if(confirm('¿Borrar puesto?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }
    async function delPer(id){ if(confirm('¿Dar de baja?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
    
    window.onload = () => {
        const ms = document.getElementById('m-sel'); const as = document.getElementById('a-sel');
        meses.forEach((n,i)=>ms.innerHTML+=`<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
        for(let i=2025;i<=2027;i++) as.innerHTML+=`<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
        render();
    };
</script>
</body></html>
