import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Base de datos v16
DB_PATH = '/tmp/ordoklar_v16.db'

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

# --- APIs Mantenidas para Estabilidad ---
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

# --- INTERFAZ DE ALTA LEGIBILIDAD ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión de Personal</title>
    <style>
        :root { 
            --gold: #D4AF37; 
            --bg: #000000; 
            --card: #151515; 
            --border: #333; 
            --text-main: #FFFFFF;
            --cyan: #00FBFF;
        }
        
        body { 
            background: var(--bg); 
            color: var(--text-main); 
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            margin: 0; 
            -webkit-font-smoothing: antialiased;
        }
        
        .header { 
            text-align: center; 
            padding: 25px; 
            font-size: 28px; 
            font-weight: 900; 
            letter-spacing: 10px; 
            border-bottom: 2px solid var(--gold);
            background: #000;
        }
        
        .nav { 
            display: flex; 
            justify-content: center; 
            background: var(--card); 
            position: sticky; 
            top: 0; 
            z-index: 1000; 
            border-bottom: 1px solid var(--border);
        }
        
        .nav button { 
            background: none; 
            border: none; 
            color: #AAA; 
            padding: 18px 30px; 
            cursor: pointer; 
            font-weight: bold; 
            font-size: 14px; 
            text-transform: uppercase;
            transition: 0.2s;
        }
        
        .nav button.active { 
            color: var(--gold); 
            background: #222;
            border-bottom: 3px solid var(--gold);
        }
        
        .content { padding: 20px; }
        .section { display: none; }
        .active { display: block; }

        /* TABLA PLANILLA - MAX LEGIBILIDAD */
        .table-wrap { 
            overflow-x: auto; 
            border: 2px solid var(--border); 
            border-radius: 12px; 
            background: #0a0a0a;
        }
        
        table { border-collapse: collapse; min-width: 1300px; width: 100%; }
        
        th, td { 
            border: 1px solid #222; 
            text-align: center; 
            font-size: 16px; /* Aumento de tamaño general */
        }
        
        /* Cabecera con Días Verticales */
        th { background: #111; color: var(--gold); padding: 12px 6px; }
        
        .day-name { 
            writing-mode: vertical-rl; 
            text-orientation: mixed;
            transform: rotate(180deg);
            font-size: 13px; 
            text-transform: uppercase;
            color: #FFF;
            font-weight: 800;
            margin-bottom: 8px;
            display: inline-block;
        }
        
        .day-num { font-size: 18px; font-weight: 900; color: var(--gold); }

        /* Columna de Personal Fija */
        .name-col { 
            width: 180px; 
            text-align: left !important; 
            padding-left: 15px; 
            color: var(--gold); 
            font-weight: 800; 
            height: 55px; 
            position: sticky; 
            left: 0; 
            background: #111; 
            z-index: 20;
            border-right: 3px solid var(--gold) !important;
            font-size: 15px;
        }

        .hs-col { 
            width: 60px; 
            background: #1a1a1a; 
            color: var(--gold); 
            font-weight: 900; 
            font-size: 18px; 
            border-left: 3px solid var(--gold) !important; 
        }

        /* Filas de Totales */
        .total-hs { background: #000; color: var(--gold); font-weight: 900; }
        .total-per { background: #000; color: var(--cyan); font-weight: 900; border-top: 2px solid #333; }
        .total-hs td, .total-per td { height: 60px; font-size: 18px; }

        /* Selectores */
        select.cell-sel { 
            background: transparent; 
            color: #FFF; 
            border: none; 
            width: 100%; 
            height: 55px; 
            cursor: pointer; 
            text-align-last: center; 
            font-weight: 900; 
            font-size: 16px;
            appearance: none;
            outline: none;
        }

        /* Estados con Colores Vivos */
        .st-12 { background: #1B5E20 !important; } 
        .st-F { background: #424242 !important; }  
        .st-VAC { background: #0D47A1 !important; } 
        .st-ART { background: #B71C1C !important; } 

        /* Otros elementos */
        .card { background: var(--card); border: 1px solid var(--border); padding: 25px; border-radius: 10px; margin-bottom: 20px; }
        input, select.form-control { background: #000; border: 2px solid #444; color: #fff; padding: 15px; border-radius: 6px; font-size: 16px; margin: 5px 0; }
        .btn-gold { background: var(--gold); border: none; padding: 15px 30px; font-weight: 900; cursor: pointer; border-radius: 6px; font-size: 14px; color: #000; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="header">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Config. Puestos</button>
        <button id="n-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="content">
        <div id="s-pla" class="section active">
            <div style="display:flex; gap:20px; margin-bottom:25px; justify-content:center;">
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
            <div class="card">
                <h2>Añadir Puesto</h2>
                <input type="text" id="p-nom" placeholder="Nombre (Ej: Portería)" style="width: 100%">
                <input type="text" id="p-hor" placeholder="Horario (Ej: 07:00 a 19:00)" style="width: 100%">
                <input type="number" id="p-can" placeholder="Cantidad de Personal" style="width: 100%">
                <button class="btn-gold" style="width:100%; margin-top:10px" onclick="addPuesto()">Guardar Puesto</button>
            </div>
            <div id="g-pue"></div>
        </div>

        <div id="s-per" class="section">
            <div class="card">
                <h2>Alta de Personal</h2>
                <input type="text" id="i-leg" placeholder="Número de Legajo" style="width: 100%">
                <input type="text" id="i-ape" placeholder="Apellido" style="width: 100%">
                <input type="text" id="i-nom" placeholder="Nombre" style="width: 100%">
                <button class="btn-gold" style="width:100%; margin-top:10px" onclick="addPersonal()">Registrar Operativo</button>
            </div>
            <div id="l-per"></div>
        </div>
    </div>

    <script>
        const meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
        const diasSemana = ["DOMINGO","LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"];

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
            const [per, nov] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json())
            ]);

            const mes = document.getElementById('sel-mes').value;
            const anio = document.getElementById('sel-anio').value;
            const cantDias = new Date(anio, mes, 0).getDate();
            
            // Header con Días Verticales
            let h = `<tr><th class="name-col" style="text-align:center !important">OPERATIVOS</th>`;
            for(let i=1; i<=cantDias; i++) {
                const dNom = diasSemana[new Date(anio, mes-1, i).getDay()];
                h += `<th><span class="day-name">${dNom}</span><br><span class="day-num">${i}</span></th>`;
            }
            h += '<th class="hs-col">TOTAL</th></tr>';
            document.getElementById('h-pla').innerHTML = h;

            let colTotHs = new Array(cantDias).fill(0);
            let colTotPer = new Array(cantDias).fill(0);

            // Cuerpo
            document.getElementById('b-pla').innerHTML = per.map(p => {
                let r = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre.toUpperCase()}</td>`;
                let rowHs = 0;
                for(let i=1; i<=cantDias; i++) {
                    const f = `${anio}-${String(mes).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                    const d = nov.find(x => x.personal_id == p.id && x.fecha == f);
                    const st = d ? d.estado : 'F';
                    
                    if(st == '12') { rowHs += 12; colTotHs[i-1] += 12; colTotPer[i-1] += 1; }

                    r += `<td class="st-${st}"><select class="cell-sel" onchange="updNov(${p.id},'${f}',this.value)">
                        <option value="12" ${st=='12'?'selected':''}>12</option>
                        <option value="F" ${st=='F'?'selected':''}>F</option>
                        <option value="VAC" ${st=='VAC'?'selected':''}>V</option>
                        <option value="ART" ${st=='ART'?'selected':''}>A</option>
                    </select></td>`;
                }
                return `<tr>${r}<td class="hs-col">${rowHs}</td></tr>`;
            }).join('');

            // Footer con Totales Resaltados
            let fHs = `<tr class="total-hs"><td class="name-col">TOTAL HORAS</td>`;
            colTotHs.forEach(t => fHs += `<td>${t}</td>`);
            fHs += `<td class="hs-col">${colTotHs.reduce((a,b)=>a+b, 0)}</td></tr>`;

            let fPer = `<tr class="total-per"><td class="name-col">CANT. PERSONAL</td>`;
            colTotPer.forEach(t => fPer += `<td>${t}</td>`);
            fPer += `<td class="hs-col">---</td></tr>`;

            document.getElementById('f-pla').innerHTML = fHs + fPer;
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
