import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v12 para incluir horarios en puestos
DB_PATH = '/tmp/ordoklar_v12.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, horario TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs PUESTOS ---
@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", 
                     (d['nombre'], d['horario'], d['cantidad']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos/<int:id>', methods=['DELETE'])
def del_puesto(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM puestos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"s": "ok"})

# --- APIs PERSONAL Y NOVEDADES (Se mantienen igual para estabilidad) ---
@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", (d['nombre'], d['apellido'], d['legajo']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE', 'PUT'])
def edit_del_personal(id):
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE personal SET nombre=?, apellido=?, legajo=? WHERE id=?", (d['nombre'], d['apellido'], d['legajo'], id))
    conn.commit()
    conn.close()
    return jsonify({"s": "ok"})

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

# --- INTERFAZ PREMIUM ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión de Operaciones</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --border: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Inter', sans-serif; margin: 0; padding-bottom: 50px; }
        .header { text-align: center; padding: 15px; font-size: 22px; letter-spacing: 8px; border-bottom: 1px solid var(--border); background: #000; }
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 2px solid var(--gold); sticky; top: 0; z-index: 100; }
        .nav button { background: none; border: none; color: #666; padding: 15px 25px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; transition: 0.3s; }
        .nav button.active { color: var(--gold); background: #1a1a1a; }

        .content { padding: 20px; max-width: 1400px; margin: auto; }
        .section { display: none; }
        .active { display: block; }

        /* TABLA PLANILLA */
        .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 10px; }
        th, td { border: 1px solid #1a1a1a; text-align: center; }
        th { background: #111; color: var(--gold); padding: 10px 2px; }
        .day-label { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 9px; color: #888; margin-bottom: 4px; display: inline-block; }
        .name-col { width: 130px; text-align: left !important; padding-left: 10px; color: var(--gold); font-weight: bold; height: 38px; }
        .hs-col { width: 45px; background: #1a1a1a; color: var(--gold); font-weight: bold; border-left: 2px solid var(--gold) !important; font-size: 12px; }
        .total-row { background: #0a0a0a; color: var(--gold); font-weight: bold; border-top: 2px solid var(--gold); font-size: 12px; }

        /* ESTILOS PUESTOS */
        .puestos-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
        .puesto-card { background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--gold); padding: 15px; border-radius: 4px; position: relative; }
        .puesto-header { display: flex; justify-content: space-between; border-bottom: 1px solid #222; margin-bottom: 10px; padding-bottom: 5px; }
        .puesto-horario { font-size: 11px; color: #aaa; margin-bottom: 10px; }

        /* FORMULARIOS */
        .form-box { background: var(--card); padding: 20px; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 25px; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        input, select.form-control { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 4px; font-size: 13px; }
        .btn-gold { background: var(--gold); border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; border-radius: 4px; color: #000; text-transform: uppercase; font-size: 11px; }

        select.cell-sel { background: transparent; color: #fff; border: none; width: 100%; height: 100%; cursor: pointer; text-align-last: center; font-weight: bold; outline: none; appearance: none; }
        .st-12 { background: #1b5e20 !important; }
        .st-F { background: #333 !important; }
        .st-VAC { background: #01579b !important; }
        .st-ART { background: #b71c1c !important; }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Configurar Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="content">
        <!-- SECCION PLANILLA -->
        <div id="s-pla" class="section active">
            <div style="display:flex; gap:10px; margin-bottom:15px; justify-content:center;">
                <select id="sel-mes" class="form-control" onchange="render()"></select>
                <select id="sel-anio" class="form-control" onchange="render()"></select>
            </div>
            <div class="table-wrap">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- SECCION PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box">
                <input type="text" id="p-nom" placeholder="Ej: Garita Principal" style="flex:2">
                <input type="text" id="p-hor" placeholder="Horario (07 a 19)" style="flex:1">
                <input type="number" id="p-can" placeholder="Cant. Personal" style="width:120px">
                <button class="btn-gold" onclick="addPuesto()">+ AGREGAR PUESTO</button>
            </div>
            <div id="g-pue" class="puestos-container"></div>
        </div>

        <!-- SECCION PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box">
                <input type="text" id="i-leg" placeholder="Legajo">
                <input type="text" id="i-ape" placeholder="Apellido">
                <input type="text" id="i-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="addPersonal()">REGISTRAR OPERATIVO</button>
            </div>
            <div id="l-per"></div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const diasSemana = ["Dom","Lun","Mar","Mie","Jue","Vie","Sab"];

        function fillSelectors() {
            const m = document.getElementById('sel-mes');
            const a = document.getElementById('sel-anio');
            const now = new Date();
            meses.forEach((name, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${name}</option>`);
            for(let i=2024; i<=2027; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
        }

        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active');
            document.getElementById('n-'+t).classList.add('active');
        }

        async function render() {
            const [per, nov, pue] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json()),
                fetch('/api/puestos').then(r => r.json())
            ]);

            // Render Puestos
            document.getElementById('g-pue').innerHTML = pue.map(p => `
                <div class="puesto-card">
                    <div class="puesto-header">
                        <b style="color:var(--gold)">${p.nombre.toUpperCase()}</b>
                        <button onclick="delPuesto(${p.id})" style="color:red; background:none; border:none; cursor:pointer; font-weight:bold;">X</button>
                    </div>
                    <div class="puesto-horario">🕒 Horario: ${p.horario}</div>
                    <div style="font-size:10px; color:#666; margin-bottom:5px;">ASIGNACIONES REQUERIDAS: ${p.cantidad}</div>
                    ${Array.from({length: p.cantidad}).map(() => `
                        <select class="form-control" style="width:100%; margin-bottom:5px; font-size:11px; padding:5px;">
                            <option>-- Vacante --</option>
                            ${per.map(e => `<option>${e.apellido}, ${e.nombre}</option>`).join('')}
                        </select>
                    `).join('')}
                </div>
            `).join('');

            // Render Personal
            document.getElementById('l-per').innerHTML = per.map(x => `
                <div class="form-box" style="margin-bottom:10px; padding:10px; justify-content:space-between">
                    <span><b>${x.legajo}</b> | ${x.apellido.toUpperCase()}, ${x.nombre}</span>
                    <button style="color:red; background:none; border:none; cursor:pointer;" onclick="delPersonal(${x.id})">ELIMINAR</button>
                </div>
            `).join('');

            // Render Planilla
            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const cantDias = new Date(anio, mes, 0).getDate();
            
            let h = '<tr><th class="name-col">Personal</th>';
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-label">${dNom}</span><br>${i}</th>`;
            }
            h += '<th class="hs-col">HS</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colTot = new Array(cantDias).fill(0);
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { rowHs += 12; colTot[i-1] += 12; }
                    r += `<td class="st-${st}"><select class="cell-sel" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${st=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${r}<td class="hs-col">${rowHs}</td></tr>`;
            }).join('');

            let f = `<tr class="total-row"><td class="name-col">TOTAL HS DÍA</td>`;
            colTot.forEach(t => f += `<td>${t}</td>`);
            f += `<td class="hs-col">${colTot.reduce((a,b)=>a+b, 0)}</td></tr>`;
            document.getElementById('f-pla').innerHTML = f;
        }

        async function addPuesto() {
            const d = {nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, cantidad: document.getElementById('p-can').value};
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function delPuesto(id) { if(confirm("¿Eliminar puesto?")) { await fetch('/api/puestos/'+id, {method:'DELETE'}); render(); } }

        async function addPersonal() {
            const d = {nombre:document.getElementById('i-nom').value, apellido:document.getElementById('i-ape').value, legajo:document.getElementById('i-leg').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function delPersonal(id) { if(confirm("¿Eliminar operativo?")) { await fetch('/api/personal/'+id, {method:'DELETE'}); render(); } }

        async function updNov(pid, f, e) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})});
            render();
        }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
