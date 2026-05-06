import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v61_final_key'

# Ruta absoluta para persistencia real
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ordoklar_v61_FINAL.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
        conn.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, dotacion INTEGER)')
        conn.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
        conn.execute('CREATE TABLE IF NOT EXISTS archivos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, fecha TEXT)')
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

# --- API CORREGIDA ---

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            try:
                d = request.json
                # Forzamos integridad de datos
                nombre = str(d.get('nombre', '')).strip()
                horario = str(d.get('horario', '')).strip()
                dotacion = int(d.get('dotacion', 1))
                
                if nombre:
                    conn.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (?, ?, ?)", 
                                 (nombre, horario, dotacion))
                    conn.commit()
                    return jsonify({"status": "success"}), 201
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
            conn.commit()
            
        res = [dict(row) for row in conn.execute("SELECT * FROM puestos").fetchall()]
    return jsonify(res)

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
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    return jsonify(res)

@app.route('/api/archivos', methods=['GET', 'POST', 'DELETE'])
def handle_archivos():
    with get_db_connection() as conn:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO archivos (nombre, fecha) VALUES (?, ?)", (d['nombre'], d['fecha']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM archivos WHERE id=?", (request.args.get('id'),))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM archivos ORDER BY id DESC").fetchall()]
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
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v61</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); }
    nav { display: flex; justify-content: center; background: #0a0a0a; }
    nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; }
    .section { display: none; }
    .active-section { display: block; }
    .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 10px 18px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    input, select { background: #000; color: #fff; border: 1px solid #444; padding: 8px; margin-right: 5px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { border: 1px solid #333; padding: 8px; text-align: center; }
    .st-12 { background: #1b4332; } .st-F { background: #ff8c00; color:#000; } .st-ART { background: #6a0dad; } .st-VAC { background: #0000ff; } .st-FE { background: #ff0000; }
    .grid-pue { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
    .card-pue { background: #050505; border: 1px solid var(--border); padding: 15px; border-top: 4px solid var(--gold); }
    .slot { margin-top: 8px; display: flex; justify-content: space-between; }
    .slot-fixed { display: none; font-weight: bold; color: var(--gold); }
    .global-fixed .slot select { display: none; }
    .global-fixed .slot-fixed { display: block; }
    @media print { .no-print { display: none !important; } body { background: white; color: black; } table { color: black; border: 1px solid black; } }
</style>
</head><body>
    <div class="header no-print"><h1>ORDO <span style="color:var(--gold)">KLAR</span></h1></div>
    <nav class="no-print">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>
    <div class="container">
        <div id="s-pla" class="section active-section">
            <div class="box no-print">
                <select id="m-sel" onchange="render()"></select><select id="a-sel" onchange="render()"></select>
                <button class="btn" onclick="window.print()">🖨️ Imprimir Planilla</button>
            </div>
            <div style="overflow-x:auto"><table><thead id="h-pla"></thead><tbody id="b-pla"></tbody><tfoot id="f-pla"></tfoot></table></div>
        </div>
        <div id="s-pue" class="section">
            <div class="box no-print">
                <input type="text" id="p-nom" placeholder="Nombre Objetivo">
                <input type="text" id="p-hor" placeholder="Horario (ej 12x36)">
                <input type="number" id="p-dot" placeholder="Cant. Agentes" value="1">
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
        <div id="s-arc" class="section"><div class="box"><h3>HISTORIAL</h3><div id="historial-list"></div></div></div>
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
        const [per, pue, nov, arc] = await Promise.all([
            fetch('/api/personal').then(r=>r.json()), fetch('/api/puestos').then(r=>r.json()),
            fetch('/api/novedades').then(r=>r.json()), fetch('/api/archivos').then(r=>r.json())
        ]);
        const m = parseInt(document.getElementById('m-sel').value);
        const a = parseInt(document.getElementById('a-sel').value);
        const dias = new Date(a, m, 0).getDate();
        
        let h = `<tr><th>PERSONAL</th>`;
        for(let i=1;i<=dias;i++) h += `<th>${i}</th>`;
        h += `<th>HS</th></tr>`;
        document.getElementById('h-pla').innerHTML = h;

        let b = "";
        per.forEach(p=>{
            let hs = 0; let r = `<td style="text-align:left; color:var(--gold)">${p.apellido}, ${p.nombre}</td>`;
            for(let i=1;i<=dias;i++){
                const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                const n = nov.find(x=>x.personal_id==p.id && x.fecha==f) || {estado:'F'};
                if(n.estado=='12') hs += 12;
                r += `<td class="st-${n.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${n.estado}</td>`;
            }
            b += `<tr>${r}<td>${hs}</td></tr>`;
        });
        document.getElementById('b-pla').innerHTML = b;

        const opts = `<option value="">-- Seleccionar --</option>` + per.map(p=>`<option>${p.apellido} ${p.nombre}</option>`).join('');
        document.getElementById('grid-pue').innerHTML = pue.map(x=>{
            let s = ""; for(let i=0;i<x.dotacion;i++) s += `<div class="slot"><select>${opts}</select><span class="slot-fixed"></span></div>`;
            return `<div class="card-pue"><h3>${x.nombre}</h3><p>${x.horario}</p>${s}<br><button onclick="delPue(${x.id})" style="color:red;background:none;border:none;cursor:pointer">Eliminar</button></div>`;
        }).join('');
    }
    async function addPuesto(){
        const d = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value };
        await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
        document.getElementById('p-nom').value = ""; render();
    }
    async function addPersonal(){
        const d = { legajo: document.getElementById('per-l').value, apellido: document.getElementById('per-a').value, nombre: document.getElementById('per-n').value };
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
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
                const v = s.querySelector('select').value;
                s.querySelector('.slot-fixed').innerText = v || "---";
            });
        } else g.classList.remove('global-fixed');
    }
    async function delPue(id){ await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); }
    
    window.onload = () => {
        const ms = document.getElementById('m-sel'); const as = document.getElementById('a-sel');
        meses.forEach((n,i)=>ms.innerHTML+=`<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
        for(let i=2025;i<=2027;i++) as.innerHTML+=`<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
        render();
    };
</script>
</body></html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)
