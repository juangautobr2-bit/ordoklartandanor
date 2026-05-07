import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ordo_klar_v69_neon'

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS personal (id SERIAL PRIMARY KEY, nombre TEXT, apellido TEXT, legajo TEXT UNIQUE)')
            cur.execute('CREATE TABLE IF NOT EXISTS puestos (id SERIAL PRIMARY KEY, nombre TEXT, horario TEXT, dotacion INTEGER)')
            cur.execute('CREATE TABLE IF NOT EXISTS novedades (id SERIAL PRIMARY KEY, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
            cur.execute('CREATE TABLE IF NOT EXISTS informes (id SERIAL PRIMARY KEY, nombre TEXT, fecha_generado TEXT)')
            cur.execute('CREATE TABLE IF NOT EXISTS asignaciones (puesto_id INTEGER, slot_index INTEGER, personal_id INTEGER, PRIMARY KEY(puesto_id, slot_index))')
            conn.commit()

init_db()

# --- SEGURIDAD ---
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

# --- API PUESTOS (NUEVAS FUNCIONES) ---
@app.route('/api/puestos', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO puestos (nombre, horario, dotacion) VALUES (%s, %s, %s)", (d['nombre'], d['horario'], int(d['dotacion'])))
    elif request.method == 'PUT':
        d = request.json
        cur.execute("UPDATE puestos SET nombre=%s, horario=%s, dotacion=%s WHERE id=%s", (d['nombre'], d['horario'], int(d['dotacion']), d['id']))
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM puestos WHERE id=%s", (request.args.get('id'),))
    
    conn.commit()
    cur.execute("SELECT * FROM puestos ORDER BY id ASC")
    puestos = cur.fetchall()
    for p in puestos:
        cur.execute("SELECT slot_index, personal_id FROM asignaciones WHERE puesto_id=%s", (p['id'],))
        p['asignados'] = {str(a['slot_index']): a['personal_id'] for a in cur.fetchall()}
    
    cur.close()
    conn.close()
    return jsonify(puestos)

# --- API PERSONAL ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (%s, %s, %s)", (d['nombre'], d['apellido'], d['legajo']))
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM personal WHERE id=%s", (request.args.get('id'),))
    conn.commit()
    cur.execute("SELECT * FROM personal ORDER BY apellido ASC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

# --- API NOVEDADES ---
@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        d = request.json
        cur.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (%s, %s, %s) ON CONFLICT (personal_id, fecha) DO UPDATE SET estado = EXCLUDED.estado", (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    cur.execute("SELECT * FROM novedades")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

@app.route('/api/asignar', methods=['POST'])
def asignar():
    d = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    if not d.get('personal_id'):
        cur.execute("DELETE FROM asignaciones WHERE puesto_id=%s AND slot_index=%s", (d['puesto_id'], d['slot_index']))
    else:
        cur.execute("INSERT INTO asignaciones (puesto_id, slot_index, personal_id) VALUES (%s, %s, %s) ON CONFLICT (puesto_id, slot_index) DO UPDATE SET personal_id = EXCLUDED.personal_id", (d['puesto_id'], d['slot_index'], d['personal_id']))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status":"ok"})

@app.route('/api/informes', methods=['GET', 'POST', 'DELETE'])
def handle_informes():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        cur.execute("INSERT INTO informes (nombre, fecha_generado) VALUES (%s, %s)", (request.json['nombre'], datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
    elif request.method == 'DELETE':
        cur.execute("DELETE FROM informes WHERE id=%s", (request.args.get('id'),))
        conn.commit()
    cur.execute("SELECT * FROM informes ORDER BY id DESC")
    res = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(res)

HTML_LOGIN = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Login</title><style>body{background:#000;color:#D4AF37;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0;}.box{background:#111;border:1px solid #D4AF37;padding:40px;border-radius:10px;text-align:center;width:300px;}input{display:block;width:100%;margin:15px 0;padding:10px;background:#000;color:#fff;border:1px solid #333;box-sizing:border-box;}button{width:100%;padding:10px;background:#D4AF37;color:#000;font-weight:bold;border:none;cursor:pointer;}</style></head><body><div class="box"><h2>ORDO KLAR</h2><form method="POST"><input name="username" placeholder="Usuario"><input type="password" name="password" placeholder="Clave"><button type="submit">ENTRAR</button></form></div></body></html>'''

HTML_UI = '''
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>ORDO KLAR v69</title>
<style>
    :root { --gold: #D4AF37; --bg: #000; --card: #111; --border: #333; --text: #eee; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; margin: 0; }
    .header { text-align: center; padding: 15px; border-bottom: 2px solid var(--gold); }
    nav { display: flex; justify-content: center; background: #0a0a0a; border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 100; }
    nav button { background: none; border: none; color: #777; padding: 15px 20px; cursor: pointer; font-weight: bold; }
    nav button.active { color: var(--gold); border-bottom: 3px solid var(--gold); }
    .container { padding: 20px; }
    .section { display: none; } .active-section { display: block; }
    .box { background: var(--card); padding: 15px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 20px; }
    .btn { background: var(--gold); color: #000; border: none; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; margin: 2px; }
    .btn-red { background: #800; color: white; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { border: 1px solid #333; padding: 6px; text-align: center; }
    th { color: var(--gold); background: #1a1a1a; }
    .st-12 { background: #1b4332; cursor: pointer; } .st-F { background: #222; cursor: pointer; }
    .st-ART, .st-VAC, .st-FE { background: #432; cursor: pointer; }
    .total-row { background: #1a1a1a; font-weight: bold; color: var(--gold); }
    
    /* Grid de Puestos */
    .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
    .puesto-card { background: var(--card); border: 1px solid var(--gold); padding: 15px; border-radius: 8px; position: relative; }
    .puesto-card h3 { margin-top: 0; color: var(--gold); border-bottom: 1px solid #333; padding-bottom: 5px; }
    .puesto-card select { width: 100%; padding: 8px; margin: 5px 0; background: #000; color: #fff; border: 1px solid #444; }
    .card-actions { margin-top: 15px; display: flex; justify-content: flex-end; }
    
    @media print { nav, .header, .box, .btn, .card-actions, .btn-del { display: none !important; } .container { padding: 0; } body { background: #fff; color: #000; } }
</style>
</head><body>
    <div class="header">
        <h1>ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <div id="print-title" style="display:none; font-size: 24px; margin-bottom: 10px;"></div>
    </div>
    <nav>
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
        <button id="n-arc" onclick="tab('arc')">Archivos</button>
    </nav>
    <div class="container">
        <div id="s-pla" class="section active-section">
            <div class="box">
                <label>Mes/Año:</label>
                <select id="m-sel" onchange="render()"></select>
                <select id="a-sel" onchange="render()"></select>
                <label style="margin-left:20px">Fecha Informe:</label>
                <input type="date" id="report-date" value="${new Date().toISOString().split('T')[0]}">
                <button class="btn" onclick="generarInforme()">Imprimir Informe</button>
            </div>
            <div style="overflow-x:auto"><table><thead id="h-pla"></thead><tbody id="b-pla"></tbody><tfoot id="f-pla"></tfoot></table></div>
        </div>

        <div id="s-pue" class="section">
            <div class="box">
                <input type="hidden" id="p-id">
                <input type="text" id="p-nom" placeholder="Nombre Puesto">
                <input type="text" id="p-hor" placeholder="Horario (ej: 07 a 19)">
                <input type="number" id="p-dot" placeholder="Dotación" value="1" style="width:60px">
                <button class="btn" id="btn-pue-save" onclick="savePuesto()">+ Crear Puesto</button>
            </div>
            <div id="puestos-container" class="puestos-grid"></div>
        </div>

        <div id="s-per" class="section">
            <div class="box">
                <input id="per-l" placeholder="Legajo"> <input id="per-a" placeholder="Apellido"> <input id="per-n" placeholder="Nombre">
                <button class="btn" onclick="addPersonal()">GUARDAR</button>
            </div>
            <div class="box"><table><thead><tr><th>Legajo</th><th>Personal</th><th>Acción</th></tr></thead><tbody id="list-per"></tbody></table></div>
        </div>

        <div id="s-arc" class="section">
            <div class="box">
                <h3>Informes Históricos</h3>
                <table><thead><tr><th>Nombre</th><th>Fecha Generado</th><th>Acción</th></tr></thead><tbody id="list-arc"></tbody></table>
            </div>
        </div>
    </div>

<script>
    const meses = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"];
    let currentTab = 'pla';
    let globalPersonal = [];

    function tab(t){ 
        currentTab = t;
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active-section'));
        document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
        document.getElementById('s-' + t).classList.add('active-section');
        document.getElementById('n-' + t).classList.add('active');
        render();
    }

    async function render(){
        const [per, pue, nov, arc] = await Promise.all([
            fetch('/api/personal').then(r=>r.json()), fetch('/api/puestos').then(r=>r.json()),
            fetch('/api/novedades').then(r=>r.json()), fetch('/api/informes').then(r=>r.json())
        ]);
        globalPersonal = per;

        if(currentTab === 'pla'){
            const m = parseInt(document.getElementById('m-sel').value), a = parseInt(document.getElementById('a-sel').value);
            const dias = new Date(a, m, 0).getDate();
            let h = `<tr><th>PERSONAL</th>`, b = "";
            let daySumsHs = new Array(dias).fill(0), daySumsPer = new Array(dias).fill(0);

            for(let i=1;i<=dias;i++) h += `<th>${i}</th>`;
            h += `<th>TOTAL HS</th></tr>`;
            
            per.forEach(p => {
                let p_hs = 0, r = `<td style="text-align:left">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                for(let i=1;i<=dias;i++){
                    const f = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const n = nov.find(x=>x.personal_id==p.id && x.fecha==f) || {estado:'F'};
                    if(n.estado=='12') { 
                        p_hs += 12; 
                        daySumsHs[i-1] += 12;
                        daySumsPer[i-1] += 1;
                    }
                    r += `<td class="st-${n.estado}" onclick="cycleSt(this, ${p.id}, '${f}')">${n.estado}</td>`;
                }
                b += `<tr>${r}<td style="font-weight:bold">${p_hs}</td></tr>`;
            });

            let fHs = `<tr class="total-row"><td>CANT DE HS</td>`, fPer = `<tr class="total-row"><td>CANT DE PERSONAL</td>`;
            let totalMonthHs = 0, totalMonthPer = 0;
            for(let i=0; i<dias; i++){
                fHs += `<td>${daySumsHs[i]}</td>`;
                fPer += `<td>${daySumsPer[i]}</td>`;
                totalMonthHs += daySumsHs[i];
                totalMonthPer += daySumsPer[i];
            }
            fHs += `<td>${totalMonthHs}</td></tr>`;
            fPer += `<td>${totalMonthPer}</td></tr>`;

            document.getElementById('h-pla').innerHTML = h;
            document.getElementById('b-pla').innerHTML = b;
            document.getElementById('f-pla').innerHTML = fPer + fHs;
        }

        if(currentTab === 'pue'){
            const cont = document.getElementById('puestos-container');
            cont.innerHTML = pue.map(p => {
                let selects = "";
                for(let i=0; i<p.dotacion; i++){
                    const selectedId = p.asignados[i] || "";
                    selects += `<select onchange="asignarPue(${p.id}, ${i}, this.value)">
                        <option value="">-- Seleccionar Personal --</option>
                        ${per.map(pers => `<option value="${pers.id}" ${pers.id == selectedId ? 'selected' : ''}>${pers.apellido} ${pers.nombre}</option>`).join('')}
                    </select>`;
                }
                return `<div class="puesto-card">
                    <h3>${p.nombre}</h3>
                    <p><b>Horario:</b> ${p.horario}</p>
                    ${selects}
                    <div class="card-actions">
                        <button class="btn" onclick="editPue(${p.id}, '${p.nombre}', '${p.horario}', ${p.dotacion})">Editar</button>
                        <button class="btn btn-red" onclick="delPue(${p.id})">Eliminar</button>
                    </div>
                </div>`;
            }).join('');
        }

        if(currentTab === 'per') {
            document.getElementById('list-per').innerHTML = per.map(p => `<tr><td>${p.legajo}</td><td>${p.apellido}, ${p.nombre}</td><td><button class="btn btn-red" onclick="delPer(${p.id})">BORRAR</button></td></tr>`).join('');
        }

        if(currentTab === 'arc') {
            document.getElementById('list-arc').innerHTML = arc.map(i => `<tr><td>${i.nombre}</td><td>${i.fecha_generado}</td><td><button class="btn btn-red" onclick="delInf(${i.id})">ELIMINAR</button></td></tr>`).join('');
        }
    }

    async function asignarPue(pueId, slot, perId){
        await fetch('/api/asignar', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({puesto_id:pueId, slot_index:slot, personal_id:perId})});
    }

    async function savePuesto(){
        const id = document.getElementById('p-id').value;
        const data = { nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, dotacion: document.getElementById('p-dot').value, id: id };
        const method = id ? 'PUT' : 'POST';
        await fetch('/api/puestos', {method: method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
        clearPue(); render();
    }

    function editPue(id, nom, hor, dot){
        document.getElementById('p-id').value = id;
        document.getElementById('p-nom').value = nom;
        document.getElementById('p-hor').value = hor;
        document.getElementById('p-dot').value = dot;
        document.getElementById('btn-pue-save').innerText = "Actualizar Puesto";
    }

    function clearPue(){
        document.getElementById('p-id').value = "";
        document.getElementById('p-nom').value = "";
        document.getElementById('p-hor').value = "";
        document.getElementById('p-dot').value = 1;
        document.getElementById('btn-pue-save').innerText = "+ Crear Puesto";
    }

    async function delPue(id){ if(confirm('¿Eliminar puesto?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

    async function generarInforme(){
        const dateInput = document.getElementById('report-date').value;
        const parts = dateInput.split('-');
        const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
        const title = `PLANILLA DE CONTROL - FECHA: ${formattedDate}`;
        
        document.getElementById('print-title').innerText = title;
        document.getElementById('print-title').style.display = 'block';

        await fetch('/api/informes', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre: title})});
        window.print();
        document.getElementById('print-title').style.display = 'none';
        render();
    }

    async function cycleSt(td, pid, f){
        const sts = ["F","12","ART","VAC","FE"];
        let nxt = sts[(sts.indexOf(td.innerText)+1)%sts.length];
        await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:nxt})});
        render();
    }

    async function addPersonal(){
        await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({legajo:document.getElementById('per-l').value, apellido:document.getElementById('per-a').value, nombre:document.getElementById('per-n').value})});
        render();
    }

    async function delPer(id){ if(confirm('¿Baja?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }
    async function delInf(id){ if(confirm('¿Borrar registro?')) { await fetch(`/api/informes?id=${id}`, {method:'DELETE'}); render(); } }

    window.onload = () => {
        const ms = document.getElementById('m-sel'), as = document.getElementById('a-sel');
        meses.forEach((n,i)=>ms.innerHTML+=`<option value="${i+1}" ${i==new Date().getMonth()?'selected':''}>${n}</option>`);
        for(let i=2025;i<=2027;i++) as.innerHTML+=`<option value="${i}" ${i==new Date().getFullYear()?'selected':''}>${i}</option>`;
        render();
    };
</script>
</body></html>
