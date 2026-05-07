import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v68_verified_fix'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v68.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        conn.execute('''CREATE TABLE IF NOT EXISTS asignaciones 
                        (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, 
                        PRIMARY KEY(puesto_id, slot_index))''')
        conn.commit()

init_db()

# --- RUTAS DE ACCESO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "admin123":
            session['logged_in'] = True
            return redirect(url_for('index'))
        error = "Credenciales incorrectas"
    return render_template_string(HTML_LOGIN, error=error)

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
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
            conn.execute("DELETE FROM asignaciones WHERE personal_id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    if not session.get('logged_in'): return jsonify([]), 401
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
        
        rows = conn.execute("SELECT * FROM puestos").fetchall()
        puestos = []
        for r in rows:
            p = dict(r)
            asig = conn.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=?", (p['id'],)).fetchall()
            p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in asig}
            puestos.append(p)
    return jsonify(puestos)

@app.route('/api/asignar', methods=['POST'])
def asignar_personal():
    if not session.get('logged_in'): return jsonify({"status": "error"}), 401
    d = request.json
    with get_db_connection() as conn:
        if not d.get('personal_id'):
            conn.execute("DELETE FROM asignaciones WHERE puesto_id=? AND slot_index=?", (d['puesto_id'], d['slot_index']))
        else:
            conn.execute("INSERT OR REPLACE INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (?, ?, ?)",
                         (int(d['puesto_id']), int(d['slot_index']), int(d['personal_id'])))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    if not session.get('logged_in'): return jsonify([]), 401
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", 
                         (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    return jsonify(res)

# --- UI TEMPLATES ---

HTML_LOGIN = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Login</title>
<style>
    body { background: #000; color: #D4AF37; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; margin: 0; }
    .box { background: #111; border: 1px solid #D4AF37; padding: 40px; border-radius: 10px; text-align: center; width: 300px; }
    input { display: block; width: 100%; margin: 15px 0; padding: 10px; background: #000; color: #fff; border: 1px solid #333; box-sizing: border-box; }
    button { width: 100%; padding: 10px; background: #D4AF37; color: #000; font-weight: bold; border: none; cursor: pointer; }
    .err { color: red; font-size: 12px; }
</style></head><body><div class="box"><h2>ORDO KLAR</h2>{% if error %}<p class="err">{{error}}</p>{% endif %}<form method="POST"><input name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Clave" required><button type="submit">ENTRAR</button></form></div></body></html>
'''

HTML_UI = '''
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v68</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); position: relative; }
    .logout { position: absolute; right: 20px; top: 25px; color: #777; text-decoration: none; font-size: 12px; }
    nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
    nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; }
    .section { display: none; }
    .active-section { display: block; }
    .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    input { background: #000; color: #fff; border: 1px solid #444; padding: 8px; border-radius: 4px; margin-bottom: 5px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { border: 1px solid #333; padding: 10px; text-align: left; }
    th { color: var(--gold); background: #1a1a1a; }
    .st-12 { background: #1b4332; text-align:center; } .st-F { background: #444; text-align:center; }
    .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
    .card-pue { background: #080808; border: 1px solid var(--border); border-top: 4px solid var(--gold); padding: 15px; border-radius: 5px; }
    .slot { margin-top: 5px; background: #111; padding: 5px; border-radius: 4px; border: 1px solid #222; }
    .slot select { width: 100%; background: none; color: #fff; border: none; font-size: 12px; }
    .btn-del { color: #ff4444; background: none; border: none; cursor: pointer; font-size: 11px; }
    .total-row { background: #1a1a1a; font-weight: bold; color: var(--gold); }
</style>
</head><body>
    <div class="header">
        <h1>ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <a href="/logout" class="logout">SALIR</a>
    </div>
    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </nav>
    <div class="container">
        <!-- PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="box">
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="window.print()">Imprimir</button>
            </div>
            <div style="overflow-x:auto"><table><thead id="h-pla"></thead><tbody id="b-pla"></tbody><tfoot id="f-pla"></tfoot></table></div>
        </div>
        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="box">
                <input type="text" id="p-nom" placeholder="Objetivo">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-dot" value="1" style="width:60px">
                <button class="btn" onclick="addPuesto()">+ Crear</button>
            </div>
            <div id="grid-pue" class="grid-pue"></div>
        </div>
        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="box">
                <h3>Cargar Nuevo Agente</h3>
                <input id="per-l" placeholder="Legajo">
                <input id="per-a" placeholder="Apellido">
                <input id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">GUARDAR PERSONAL</button>
            </div>
            <div class="box">
                <table id="table-per-list">
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
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
        document.getElementById('s-' + t).classList.add('active-section');
        document.getElementById('n-' + t).classList.add('active');
        render();
    }

    async function render(){
        const [per, pue, nov] = await Promise.all([
            fetch('/api/personal').then(r=>r.json()), 
            fetch('/api/puestos').then(r=>r.json()),
            fetch('/api/novedades').then(r=>r.json())
        ]);

        const listPer = document.getElementById('list-per');
        if(listPer) {
            listPer.innerHTML = per.map(p => `
                <tr>
                    <td style="color:var(--gold)">${p.legajo}</td>
                    <td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button class="btn-del" onclick="delPer(${p.id})">ELIMINAR</button></td>
                </tr>`).join('');
        }

        if(currentTab === 'pla'){
            const m = parseInt(document.getElementById('m-sel').value);
            const a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();
            
            if(per.length === 0){
                document.getElementById('h-pla').innerHTML = "<tr><th>Cargue personal en la pestaña correspondiente</th></tr>";
                document.getElementById('b-pla').innerHTML = "";
                document.getElementById('f-pla').innerHTML = "";
                return;
            }

            let h = `<tr><th>PERSONAL</th>`;
            for(let i=1;i<=dias;i++) h += `<th style="text-align:center">${i}</th>`;
            h += `<th>HS</th></tr>`;
            document.getElementById('h-pla').innerHTML = h;
            
            let b = "";
            let sumaHorasGeneral = 0;

            per.forEach(p=>{
                let hs = 0; 
                let r = `<td style="color:var(--gold)">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1;i<=dias;i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x=>x.personal_id==p.id && x.fecha==f) || {estado:'F'};
                    if(n.estado=='12') hs += 12;
                    r += `<td class="st-${n.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${n.estado}</td>`;
                }
                sumaHorasGeneral += hs;
                b += `<tr>${r}<td style="font-weight:bold">${hs}</td></tr>`;
            });
            document.getElementById('b-pla').innerHTML = b;

            // FILAS DE TOTALES (SOLICITADAS)
            let f = `
                <tr class="total-row">
                    <td colspan="${dias + 1}">CANT. DE HS TOTALES:</td>
                    <td>${sumaHorasGeneral}</td>
                </tr>
                <tr class="total-row">
                    <td colspan="${dias + 1}">CANT. DE PERSONAL:</td>
                    <td>${per.length}</td>
                </tr>
            `;
            document.getElementById('f-pla').innerHTML = f;
        }

        if(currentTab === 'pue'){
            document.getElementById('grid-pue').innerHTML = pue.map(p => {
                let slots = "";
                for(let i=0; i<p.dotacion; i++){
                    const savedId = p.asignados[i] || "";
                    let opts = `<option value="">-- Vacante --</option>`;
                    per.forEach(pers => {
                        opts += `<option value="${pers.id}" ${pers.id == savedId ? 'selected':''}>${pers.apellido.toUpperCase()} ${pers.nombre}</option>`;
                    });
                    slots += `<div class="slot"><select onchange="saveAsig(${p.id}, ${i}, this.value)">${opts}</select></div>`;
                }
                return `<div class="card-pue"><h3>${p.nombre}</h3><p><small>${p.horario}</small></p>${slots}<br><button onclick="delPue(${p.id})" class="btn-del">BORRAR OBJETIVO</button></div>`;
            }).join('');
        }
    }

    async function addPersonal(){
        const l = document.getElementById('per-l').value;
        const a = document.getElementById('per-a').value;
        const n = document.getElementById('per-n').value;
        if(!l || !a) return alert("Complete los datos");
        
        await fetch('/api/personal', {
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body:JSON.stringify({ legajo: l, apellido: a, nombre: n })
        });
        
        document.getElementById('per-l').value=""; 
        document.getElementById('per-a').value=""; 
        document.getElementById('per-n').value="";
        render();
    }

    async function addPuesto(){
        const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
        if(!d.nombre) return;
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('p-nom').value = ""; render();
    }

    async function saveAsig(pue_id, slot_idx, per_id){
        await fetch('/api/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({puesto_id:pue_id, slot_index:slot_idx, personal_id:per_id})});
    }

    async function cycleSt(td, pid, f){
        const sts = ["F","12","ART","VAC","FE"];
        let nxt = sts[(sts.indexOf(td.innerText)+1)%sts.length];
        await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:nxt})});
        render();
    }

    async function delPue(id){ if(confirm('¿Borrar objetivo?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }
    async function delPer(id){ if(confirm('¿Dar de baja?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

    window.onload = () => {
        const ms = document.getElementById('m-sel'); const as = document.getElementById('a-sel');
        if(ms && as){
            meses.forEach((n,i)=>ms.innerHTML+=`<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025;i<=2027;i++) as.innerHTML+=`<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
            render();
        }
    };
</script>
</body></html>'''
