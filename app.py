import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos persistente
DB_PATH = '/tmp/ordoklar_v10.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

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

# --- INTERFAZ DINÁMICA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión Dinámica</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --border: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Inter', sans-serif; margin: 0; }
        .top-bar { text-align: center; padding: 15px; font-size: 20px; letter-spacing: 6px; border-bottom: 1px solid var(--border); }
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 2px solid var(--gold); }
        .nav button { background: none; border: none; color: #666; padding: 12px 25px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); }
        
        .controls { padding: 15px; display: flex; gap: 10px; align-items: center; justify-content: center; background: #0a0a0a; }
        select.date-sel { background: #111; color: var(--gold); border: 1px solid var(--gold); padding: 5px; border-radius: 4px; font-weight: bold; }

        .content { padding: 10px; }
        .section { display: none; }
        .active { display: block; }

        table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 9px; }
        th, td { border: 1px solid #1a1a1a; text-align: center; height: 32px; }
        th { background: #111; color: var(--gold); font-weight: normal; }
        
        .name-col { width: 110px; text-align: left !important; padding-left: 5px; color: var(--gold); font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .hs-col { width: 35px; background: #1a1a1a; color: var(--gold); font-weight: bold; border-left: 2px solid var(--gold) !important; }
        .total-row { background: #111; color: var(--gold); font-weight: bold; }

        select.cell-sel { background: transparent; color: #fff; border: none; width: 100%; height: 100%; cursor: pointer; text-align-last: center; font-weight: bold; outline: none; appearance: none; }
        .st-12 { background: #1b5e20 !important; }
        .st-F { background: #333 !important; }
        .st-VAC { background: #01579b !important; }
        .st-ART { background: #b71c1c !important; }

        .card { background: var(--card); border: 1px solid var(--border); padding: 15px; border-radius: 6px; margin-bottom: 10px; }
        input { background: #000; border: 1px solid #333; color: #fff; padding: 8px; border-radius: 4px; margin-right: 5px; }
        .btn-gold { background: var(--gold); border: none; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="top-bar">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="controls" id="pla-controls">
        <label style="font-size: 11px; color: #888;">PERÍODO:</label>
        <select id="sel-mes" class="date-sel" onchange="render()"></select>
        <select id="sel-anio" class="date-sel" onchange="render()"></select>
    </div>

    <div class="content">
        <div id="s-pla" class="section active">
            <table>
                <thead id="h-pla"></thead>
                <tbody id="b-pla"></tbody>
                <tfoot id="f-pla"></tfoot>
            </table>
        </div>

        <div id="s-per" class="section">
            <div class="card">
                <input type="text" id="i-leg" placeholder="Legajo">
                <input type="text" id="i-ape" placeholder="Apellido">
                <input type="text" id="i-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="addP()">+ REGISTRAR</button>
            </div>
            <div id="l-per"></div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        
        function fillSelectors() {
            const m = document.getElementById('sel-mes');
            const a = document.getElementById('sel-anio');
            const now = new Date();
            meses.forEach((name, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${name}</option>`);
            for(let i=2024; i<=2028; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
        }

        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active');
            document.getElementById('n-'+t).classList.add('active');
            document.getElementById('pla-controls').style.display = (t == 'pla') ? 'flex' : 'none';
        }

        async function render() {
            const [p, n] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json())
            ]);

            // Personal
            document.getElementById('l-per').innerHTML = p.map(x => `
                <div class="card" style="display:flex; justify-content:space-between; align-items:center;">
                    <span><b>${x.legajo}</b> - ${x.apellido.toUpperCase()}, ${x.nombre}</span>
                    <div>
                        <button class="btn-gold" style="padding:4px 8px; font-size:10px; margin-right:5px;" onclick="editP(${x.id},'${x.nombre}','${x.apellido}','${x.legajo}')">EDITAR</button>
                        <button style="color:red; background:none; border:none; cursor:pointer; font-size:10px;" onclick="delP(${x.id})">ELIMINAR</button>
                    </div>
                </div>`).join('');

            // Planilla Dinámica
            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const dias = new Date(anio, mes, 0).getDate();
            
            let h = '<tr><th class="name-col">Personal</th>';
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += '<th class="hs-col">HS</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colTotals = new Array(dias).fill(0);
            
            document.getElementById('b-pla').innerHTML = p.map(per => {
                let r = `<td class="name-col">${per.apellido.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=dias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = n.find(x => x.personal_id == per.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { rowHs += 12; colTotals[i-1] += 12; }
                    r += `<td class="st-${st}"><select class="cell-sel" onchange="upd(${per.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${st=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${r}<td class="hs-col">${rowHs}</td></tr>`;
            }).join('');

            // Fila de Totales
            let ft = `<tr class="total-row"><td class="name-col">TOTAL HS DÍA</td>`;
            colTotals.forEach(t => ft += `<td>${t}</td>`);
            ft += `<td class="hs-col">${colTotals.reduce((a,b)=>a+b, 0)}</td></tr>`;
            document.getElementById('f-pla').innerHTML = ft;
        }

        async function upd(pid, f, e) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})});
            render();
        }

        async function editP(id, n, a, l) {
            const na = prompt("Apellido:", a); const nn = prompt("Nombre:", n); const nl = prompt("Legajo:", l);
            if(na && nn) { await fetch('/api/personal/'+id, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre:nn, apellido:na, legajo:nl})}); render(); }
        }

        async function addP() {
            const d = {nombre:document.getElementById('i-nom').value, apellido:document.getElementById('i-ape').value, legajo:document.getElementById('i-leg').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)}); render();
        }

        async function delP(id) { if(confirm("¿Eliminar?")) { await fetch('/api/personal/'+id, {method:'DELETE'}); render(); } }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
