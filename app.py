import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v69_final'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v69.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        conn.execute('''CREATE TABLE IF NOT EXISTS asignaciones 
                        (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, 
                        PRIMARY KEY(puesto_id, slot_index))''')
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

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(HTML_UI)

# --- API ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    if not session.get('logged_in'): return jsonify([]), 401
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
    if not session.get('logged_in'): return jsonify([]), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
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

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_nov():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT DO UPDATE SET estado=excluded.estado", (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    return jsonify(res)

# --- TEMPLATES ---
HTML_LOGIN = '''
<!DOCTYPE html><html><head><title>Login</title><style>
body{background:#000;color:#D4AF37;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;}
.box{border:1px solid #D4AF37;padding:30px;border-radius:10px;text-align:center;}
input{display:block;width:100%;margin:10px 0;padding:10px;background:#111;color:#fff;border:1px solid #333;}
button{width:100%;padding:10px;background:#D4AF37;font-weight:bold;cursor:pointer;}
</style></head><body><div class="box"><h2>ORDO KLAR</h2><form method="POST"><input name="username" placeholder="Admin"><input type="password" name="password" placeholder="Pass"><button>ENTRAR</button></form></div></body></html>
'''

HTML_UI = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ORDO KLAR v69</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; }
    body { background: var(--bg); color: #eee; font-family: 'Segoe UI', sans-serif; margin: 0; }
    .header { text-align: center; padding: 10px; border-bottom: 2px solid var(--gold); }
    nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); }
    nav button { background: none; border: none; color: #777; padding: 15px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; }
    .section { display: none; }
    .active-section { display: block; }
    .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 10px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    input, select { background: #000; color: #fff; border: 1px solid #444; padding: 8px; margin: 5px; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border: 1px solid #333; padding: 8px; text-align: center; }
    th { color: var(--gold); }
    .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
    .card-pue { background: #0a0a0a; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 5px; }
    .slot { margin-top: 8px; padding: 5px; background: #111; border-radius: 4px; }
    .st-12 { background: #1b4332; } .st-F { background: #444; }
</style>
</head><body>
    <div class="header"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>
    <nav>
        <button onclick="tab('pla')" id="n-pla" class="active">Planilla Mensual</button>
        <button onclick="tab('pue')" id="n-pue">Puestos / Objetivos</button>
        <button onclick="tab('per')" id="n-per">Gestión Personal</button>
    </nav>
    <div class="container">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box">
                <label>Periodo:</label>
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="window.print()">Imprimir Informe</button>
            </div>
            <div style="overflow-x:auto"><table><thead id="h-pla"></thead><tbody id="b-pla"></tbody></table></div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="box">
                <h3>Nuevo Objetivo</h3>
                <input id="p-nom" placeholder="Nombre Objetivo">
                <input id="p-hor" placeholder="Horario (ej: 08-20)">
                <input id="p-dot" type="number" value="1" style="width:60px">
                <button class="btn" onclick="addPuesto()">+ Crear Caja</button>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <h3>Registrar Personal</h3>
                <input id="per-l" placeholder="Legajo">
                <input id="per-a" placeholder="Apellido">
                <input id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">GUARDAR</button>
            </div>
            <div class="box">
                <table>
                    <thead><tr><th>Legajo</th><th>Apellido y Nombre</th><th>Acción</th></tr></thead>
                    <tbody id="list-per"></tbody>
                </table>
            </div>
        </div>
    </div>

<script>
    const meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
    let currentTab = 'pla';

    function tab(t){
        currentTab = t;
        document.querySelectorAll('.section').forEach(s=>s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
        document.getElementById('s-'+t).classList.add('active-section');
        document.getElementById('n-'+t).classList.add('active');
        render();
    }

    async function render(){
        const per = await fetch('/api/personal').then(r=>r.json());
        const pue = await fetch('/api/puestos').then(r=>r.json());
        const nov = await fetch('/api/novedades').then(r=>r.json());

        // Render Personal Table
        const lp = document.getElementById('list-per');
        if(lp) lp.innerHTML = per.map(p=>`<tr><td>${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td><td><button onclick="delPer(${p.id})" style="color:red;background:none;border:none;cursor:pointer">X</button></td></tr>`).join('');

        if(currentTab === 'pla'){
            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();
            
            let h = `<tr><th>AGENTE</th>`;
            for(let i=1;i<=dias;i++) h += `<th>${i}</th>`;
            h += `<th>TOT</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;

            document.getElementById('b-pla').innerHTML = per.map(p=>{
                let hs = 0;
                let row = `<tr><td style="text-align:left;color:var(--gold)">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1;i<=dias;i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x=>x.personal_id==p.id && x.fecha==f) || {estado:'F'};
                    if(n.estado=='12') hs += 12;
                    row += `<td class="st-${n.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${n.estado}</td>`;
                }
                return row + `<td style="font-weight:bold">${hs}</td></tr>`;
            }).join('');
        }

        if(currentTab === 'pue'){
            document.getElementById('grid-pue').innerHTML = pue.map(p=>{
                let selects = "";
                for(let i=0; i<p.dotacion; i++){
                    let opt = `<option value="">-- Seleccionar --</option>`;
                    per.forEach(pers => {
                        const sel = (p.asignados[i] == pers.id) ? 'selected' : '';
                        opt += `<option value="${pers.id}" ${sel}>${pers.apellido.toUpperCase()}</option>`;
                    });
                    selects += `<div class="slot"><select onchange="saveAsig(${p.id}, ${i}, this.value)">${opt}</select></div>`;
                }
                return `<div class="card-pue"><h3>${p.nombre}</h3><p>${p.horario} hs</p>${selects}<br><button class="btn" style="background:#444;width:100%" onclick="delPue(${p.id})">Borrar</button></div>`;
            }).join('');
        }
    }

    async function addPersonal(){
        const d = {legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value};
        if(!d.legajo || !d.apellido) return alert("Faltan datos");
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('per-l').value=""; document.getElementById('per-a').value=""; document.getElementById('per-n').value="";
        render();
    }

    async function addPuesto(){
        const d = {nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value};
        if(!d.nombre) return;
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('p-nom').value=""; render();
    }

    async function saveAsig(p_id, s_idx, per_id){
        await fetch('/api/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({puesto_id:p_id, slot_index:s_idx, personal_id:per_id})});
    }

    async function cycleSt(td, pid, f){
        const sts = ["F","12","ART","VAC","FE"];
        let nxt = sts[(sts.indexOf(td.innerText)+1)%sts.length];
        await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:nxt})});
        render();
    }

    async function delPer(id){ if(confirm('¿Baja?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
    async function delPue(id){ if(confirm('¿Borrar?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

    window.onload = () => {
        const ms = document.getElementById('m-sel'); const as = document.getElementById('a-sel');
        meses.forEach((m,i)=>ms.innerHTML+=`<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${m}</option>`);
        for(let i=2025;i<=2027;i++) as.innerHTML+=`<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
        render();
    };
</script>
</body></html>
