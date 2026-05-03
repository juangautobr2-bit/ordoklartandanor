import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v15
DB_PATH = '/tmp/ordoklar_v15.db'

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

# --- APIs ---
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

# --- INTERFAZ DE ALTA VISIBILIDAD ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Panel Operativo</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --border: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Inter', sans-serif; margin: 0; padding: 0; }
        
        .header { text-align: center; padding: 20px; font-size: 24px; letter-spacing: 8px; border-bottom: 1px solid var(--border); background: #000; }
        
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 2px solid var(--gold); position: sticky; top: 0; z-index: 1000; }
        .nav button { background: none; border: none; color: #888; padding: 15px 25px; cursor: pointer; font-weight: bold; font-size: 13px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); background: #1a1a1a; }
        
        .content { padding: 15px; }
        .section { display: none; }
        .active { display: block; }

        /* TABLA PLANILLA OPTIMIZADA */
        .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: #000; }
        table { border-collapse: collapse; min-width: 1200px; }
        
        th, td { border: 1px solid #1a1a1a; text-align: center; font-size: 13px; }
        
        /* Cabecera */
        th { background: #111; color: var(--gold); padding: 10px 5px; font-weight: 800; }
        .day-label { writing-mode: vertical-rl; transform: rotate(180deg); font-size: 11px; color: #aaa; margin-bottom: 5px; display: inline-block; font-weight: 400; }
        
        /* Columna Fija de Nombres */
        .name-col { 
            width: 160px; 
            text-align: left !important; 
            padding-left: 12px; 
            color: var(--gold); 
            font-weight: bold; 
            height: 45px; 
            position: sticky; 
            left: 0; 
            background: #0a0a0a; 
            z-index: 10;
            border-right: 2px solid var(--gold) !important;
            font-size: 13px;
        }

        .hs-col { width: 50px; background: #1a1a1a; color: var(--gold); font-weight: 900; font-size: 15px; border-left: 2px solid var(--gold) !important; }

        /* Filas de Totales */
        .total-hs { background: #0a0a0a; color: var(--gold); font-weight: bold; }
        .total-per { background: #000; color: #00e5ff; font-weight: bold; }
        .total-hs td, .total-per td { height: 50px; font-size: 15px; }

        /* Selectores de celda */
        select.cell-sel { 
            background: transparent; 
            color: #fff; 
            border: none; 
            width: 100%; 
            height: 45px; 
            cursor: pointer; 
            text-align-last: center; 
            font-weight: bold; 
            font-size: 14px;
            appearance: none; 
            outline: none;
        }

        /* Estados con colores fuertes */
        .st-12 { background: #2e7d32 !important; } /* Verde bosque */
        .st-F { background: #424242 !important; }  /* Gris oscuro */
        .st-VAC { background: #1565c0 !important; } /* Azul */
        .st-ART { background: #c62828 !important; } /* Rojo */

        /* Formularios */
        .card { background: var(--card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; margin-bottom: 15px; }
        input, select.form-control { background: #000; border: 1px solid #444; color: #fff; padding: 12px; border-radius: 4px; font-size: 15px; }
        .btn-gold { background: var(--gold); border: none; padding: 12px 25px; font-weight: bold; cursor: pointer; border-radius: 4px; font-size: 13px; color: #000; }
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
        <!-- PLANILLA -->
        <div id="s-pla" class="section active">
            <div style="display:flex; gap:15px; margin-bottom:20px; justify-content:center;">
                <select id="sel-mes" class="form-control" onchange="render()"></select>
                <select id="sel-anio" class="form-control" onchange="render()"></select>
            </div>
            <div class="table-wrap">
                <table id="main-table">
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                    <tfoot id="f-pla"></tfoot>
                </table>
            </div>
        </div>

        <!-- PUESTOS -->
        <div id="s-pue" class="section">
            <div class="card">
                <h3>Nuevo Puesto</h3>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <input type="text" id="p-nom" placeholder="Nombre Puesto" style="flex:2">
                    <input type="text" id="p-hor" placeholder="Horario" style="flex:1">
                    <input type="number" id="p-can" placeholder="Cant." style="width:80px">
                    <button class="btn-gold" onclick="addPuesto()">GUARDAR</button>
                </div>
            </div>
            <div id="g-pue"></div>
        </div>

        <!-- PERSONAL -->
        <div id="s-per" class="section">
            <div class="card">
                <h3>Registrar Operativo</h3>
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <input type="text" id="i-leg" placeholder="Legajo">
                    <input type="text" id="i-ape" placeholder="Apellido">
                    <input type="text" id="i-nom" placeholder="Nombre">
                    <button class="btn-gold" onclick="addPersonal()">REGISTRAR</button>
                </div>
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
            let h = `<tr><th class="name-col" style="text-align:center !important">OPERATIVO</th>`;
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-label">${dNom}</span><br>${i}</th>`;
            }
            h += '<th class="hs-col">TOTAL</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colTotHs = new Array(cantDias).fill(0);
            let colTotPer = new Array(cantDias).fill(0);

            // CUERPO
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre[0]}.</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    
                    if(st == '12') { 
                        rowHs += 12; colTotHs[i-1] += 12; colTotPer[i-1] += 1; 
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

            // FOOTER CON LAS DOS FILAS SOLICITADAS
            let fHs = `<tr class="total-hs"><td class="name-col">TOTAL HORAS</td>`;
            colTotHs.forEach(t => fHs += `<td>${t}</td>`);
            fHs += `<td class="hs-col">${colTotHs.reduce((a,b)=>a+b, 0)}</td></tr>`;

            let fPer = `<tr class="total-per"><td class="name-col">CANT. PERSONAL</td>`;
            colTotPer.forEach(t => fPer += `<td>${t}</td>`);
            fPer += `<td class="hs-col">-</td></tr>`;

            document.getElementById('f-pla').innerHTML = fHs + fPer;

            // Listados secundarios
            document.getElementById('g-pue').innerHTML = pue.map(p => `<div class="card"><b>${p.nombre}</b> | ${p.horario} | Dotación: ${p.cantidad}</div>`).join('');
            document.getElementById('l-per').innerHTML = per.map(x => `<div class="card" style="padding:10px">${x.legajo} - ${x.apellido}, ${x.nombre}</div>`).join('');
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
