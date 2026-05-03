import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v13
DB_PATH = '/tmp/ordoklar_v13.db'

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

# --- APIs (Puestos, Personal, Novedades) ---
@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", (d['nombre'], d['horario'], d['cantidad']))
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

# --- INTERFAZ ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión Operativa</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --border: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Inter', sans-serif; margin: 0; }
        .header { text-align: center; padding: 15px; font-size: 22px; letter-spacing: 8px; border-bottom: 1px solid var(--border); background: #000; }
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 2px solid var(--gold); }
        .nav button { background: none; border: none; color: #666; padding: 15px 25px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); background: #1a1a1a; }
        .content { padding: 20px; }
        .section { display: none; }
        .active { display: block; }

        /* TABLA */
        .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; font-size: 10px; }
        th, td { border: 1px solid #1a1a1a; text-align: center; }
        th { background: #111; color: var(--gold); padding: 8px 2px; }
        .day-label { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 8px; color: #888; }
        .name-col { width: 130px; text-align: left !important; padding-left: 8px; color: var(--gold); font-weight: bold; height: 35px; }
        .hs-col { width: 40px; background: #1a1a1a; color: var(--gold); font-weight: bold; border-left: 2px solid var(--gold) !important; }
        
        .total-row-hs { background: #0a0a0a; color: var(--gold); font-weight: bold; border-top: 2px solid var(--gold); }
        .total-row-per { background: #000; color: #fff; font-weight: bold; border-top: 1px solid #333; }

        /* ESTADOS */
        select.cell-sel { background: transparent; color: #fff; border: none; width: 100%; height: 100%; cursor: pointer; text-align-last: center; font-weight: bold; appearance: none; }
        .st-12 { background: #1b5e20 !important; }
        .st-F { background: #333 !important; }
        .st-VAC { background: #01579b !important; }
        .st-ART { background: #b71c1c !important; }

        /* FORMS */
        .form-box { background: var(--card); padding: 15px; border-radius: 6px; border: 1px solid var(--border); margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        input, select.form-control { background: #000; border: 1px solid #333; color: #fff; padding: 8px; border-radius: 4px; }
        .btn-gold { background: var(--gold); border: none; padding: 8px 15px; font-weight: bold; cursor: pointer; border-radius: 4px; color: #000; font-size: 10px; }
        .puesto-card { background: var(--card); border: 1px solid var(--border); border-left: 4px solid var(--gold); padding: 15px; border-radius: 4px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    <div class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla</button>
        <button id="n-pue" onclick="tab('pue')">Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="content">
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

        <div id="s-pue" class="section">
            <div class="form-box">
                <input type="text" id="p-nom" placeholder="Puesto">
                <input type="text" id="p-hor" placeholder="Horario">
                <input type="number" id="p-can" placeholder="Cant. Personas">
                <button class="btn-gold" onclick="addPuesto()">+ AGREGAR</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <div id="s-per" class="section">
            <div class="form-box">
                <input type="text" id="i-leg" placeholder="Legajo">
                <input type="text" id="i-ape" placeholder="Apellido">
                <input type="text" id="i-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="addPersonal()">REGISTRAR</button>
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
            for(let i=2024; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
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

            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const cantDias = new Date(anio, mes, 0).getDate();
            
            // HEADER
            let h = '<tr><th class="name-col">Personal</th>';
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-label">${dNom}</span><br>${i}</th>`;
            }
            h += '<th class="hs-col">HS</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            // CUERPO Y CÁLCULOS
            let colTotHs = new Array(cantDias).fill(0);
            let colTotPer = new Array(cantDias).fill(0);

            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    if(st == '12') { 
                        rowHs += 12; 
                        colTotHs[i-1] += 12; 
                        colTotPer[i-1] += 1; 
                    }
                    r += `<td class="st-${st}"><select class="cell-sel" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${st=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${r}<td class="hs-col">${rowHs}</td></tr>`;
            }).join('');

            // FOOTER CON DOS FILAS
            let fHs = `<tr class="total-row-hs"><td class="name-col">TOTAL HS</td>`;
            colTotHs.forEach(t => fHs += `<td>${t}</td>`);
            fHs += `<td class="hs-col">${colTotHs.reduce((a,b)=>a+b, 0)}</td></tr>`;

            let fPer = `<tr class="total-row-per"><td class="name-col">CANT. PERSONAL</td>`;
            colTotPer.forEach(t => fPer += `<td>${t}</td>`);
            fPer += `<td class="hs-col">-</td></tr>`;

            document.getElementById('f-pla').innerHTML = fHs + fPer;

            // Render Puestos y Personal (simplificado)
            document.getElementById('g-pue').innerHTML = pue.map(p => `<div class="puesto-card"><b>${p.nombre}</b> | ${p.horario} | Requisito: ${p.cantidad} pers.</div>`).join('');
            document.getElementById('l-per').innerHTML = per.map(x => `<div style="padding:5px; border-bottom:1px solid #222">${x.apellido}, ${x.nombre}</div>`).join('');
        }

        async function updNov(pid, f, e) {
            await fetch('/api/novedades', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e})});
            render();
        }

        async function addPuesto() {
            const d = {nombre: document.getElementById('p-nom').value, horario: document.getElementById('p-hor').value, cantidad: document.getElementById('p-can').value};
            await fetch('/api/puestos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        async function addPersonal() {
            const d = {nombre:document.getElementById('i-nom').value, apellido:document.getElementById('i-ape').value, legajo:document.getElementById('i-leg').value};
            await fetch('/api/personal', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d)});
            render();
        }

        window.onload = () => { fillSelectors(); render(); };
    </script>
</body>
</html>
'''
