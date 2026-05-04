import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# v39 - Forzamos una ruta que persista en entornos de contenedor
# Si el entorno permite persistencia, este archivo no debería borrarse.
DB_PATH = os.path.abspath("ordoklar_v39_final.db")

def get_db_connection():
    """Establece conexión con persistencia reforzada."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    # PRAGMA asegura que la base de datos escriba al disco inmediatamente
    conn.execute("PRAGMA synchronous = EXTRA")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa tablas solo si no existen."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT NOT NULL, 
        apellido TEXT NOT NULL, 
        legajo TEXT UNIQUE NOT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT NOT NULL, 
        horario TEXT, 
        cantidad INTEGER DEFAULT 1)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        personal_id INTEGER NOT NULL, 
        fecha TEXT NOT NULL, 
        estado TEXT NOT NULL, 
        UNIQUE(personal_id, fecha))''')
    conn.commit()
    conn.close()
    print(f"Base de datos verificada en: {DB_PATH}")

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- APIs CON MANEJO DE ERRORES Y COMMIT FORZADO ---
@app.route('/api/personal', methods=['GET', 'POST', 'DELETE'])
def handle_personal():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM personal WHERE id=?", (request.args.get('id'),))
            conn.commit()
        
        res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/puestos', methods=['GET', 'POST', 'DELETE'])
def handle_puestos():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO puestos (nombre, horario, cantidad) VALUES (?, ?, ?)", 
                         (d['nombre'], d['horario'], d['cantidad']))
            conn.commit()
        elif request.method == 'DELETE':
            conn.execute("DELETE FROM puestos WHERE id=?", (request.args.get('id'),))
            conn.commit()
            
        res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            d = request.json
            conn.execute("INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado", 
                         (d['p_id'], d['fecha'], d['estado']))
            conn.commit()
        res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
        return jsonify(res)
    finally:
        conn.close()

# --- INTERFAZ v39 (Fuentes Grandes y Selectores de Personal) ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel Técnico v39</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root { --gold: #D4AF37; --bg: #000; --card: #151515; --border: #333; }
        body { background: var(--bg); color: #FFF; font-family: 'Segoe UI', sans-serif; margin: 0; font-size: 18px; }
        
        .header-main { text-align: center; padding: 40px; border-bottom: 3px solid var(--gold); background: #050505; }
        .nav { display: flex; justify-content: center; background: var(--card); position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border); }
        .nav button { background: none; border: none; color: #aaa; padding: 25px 40px; cursor: pointer; font-weight: bold; font-size: 18px; text-transform: uppercase; transition: 0.3s; }
        .nav button.active { color: var(--gold); border-bottom: 4px solid var(--gold); background: #222; }

        .content { padding: 30px; max-width: 1600px; margin: auto; }
        .section { display: none; }
        .active-section { display: block; }

        /* Inputs y Botones Premium */
        .form-box { background: var(--card); padding: 35px; border-radius: 15px; margin-bottom: 30px; border: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 20px; align-items: center; }
        input, select { background: #000; border: 2px solid var(--border); color: #fff; padding: 18px; border-radius: 10px; font-size: 20px; flex: 1; min-width: 250px; }
        input:focus { border-color: var(--gold); outline: none; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 20px 40px; font-weight: 900; border-radius: 10px; cursor: pointer; font-size: 18px; text-transform: uppercase; }

        /* Planilla Mensual Optimizada */
        .table-wrap { overflow-x: auto; background: #000; border: 1px solid var(--border); border-radius: 12px; }
        table { width: 100%; border-collapse: collapse; font-size: 16px; }
        th, td { border: 1px solid #333; padding: 12px 8px; text-align: center; }
        
        .name-col { text-align: left; padding-left: 20px; font-weight: bold; color: var(--gold); width: 300px; position: sticky; left: 0; background: #0a0a0a; z-index: 10; font-size: 18px; border-right: 3px solid var(--gold); }
        .total-col { background: #1a1a1a; font-weight: 900; color: var(--gold); width: 100px; font-size: 20px; }
        
        .th-date { height: 110px; background: #080808; }
        .date-label { transform: rotate(-90deg); display: block; width: 40px; margin: 0 auto; font-weight: bold; font-size: 16px; }

        /* Estados con Colores Vivos */
        .cell-12 { background: #2E7D32 !important; color: #fff; font-weight: bold; cursor: pointer; }
        .cell-F { background: #222 !important; color: #555; cursor: pointer; }
        .cell-ART { background: #C62828 !important; color: #fff; cursor: pointer; }
        .cell-VAC { background: #1565C0 !important; color: #fff; cursor: pointer; }

        /* Grid de Puestos */
        .puestos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 25px; }
        .puesto-box { background: var(--card); border: 1px solid var(--border); border-radius: 20px; padding: 25px; border-left: 8px solid var(--gold); }
        .puesto-box h3 { font-size: 24px; margin: 0 0 10px 0; color: var(--gold); }
        .puesto-box select { width: 100%; margin-top: 15px; font-size: 16px; padding: 12px; border-color: #444; }
    </style>
</head>
<body>

    <header class="header-main">
        <h1 style="letter-spacing: 10px; margin:0; font-size: 40px;">ORDO <span style="color:var(--gold)">KLAR</span></h1>
        <p style="color:#888; font-size:14px; margin-top:10px; letter-spacing: 2px;">SISTEMA PROFESIONAL DE ASISTENCIA Y DOTACIÓN</p>
    </header>

    <nav class="nav">
        <button id="n-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="n-pue" onclick="tab('pue')">Dotación de Puestos</button>
        <button id="n-per" onclick="tab('per')">Gestión de Personal</button>
    </nav>

    <div class="content">
        <!-- SECCIÓN PLANILLA -->
        <div id="s-pla" class="section active-section">
            <div class="form-box">
                <select id="sel-mes" onchange="render()"></select>
                <select id="sel-anio" onchange="render()"></select>
                <button class="btn-gold" onclick="genPDF('render-planilla', 'Planilla_Mensual', 'a3', 'landscape')">Exportar PDF A3</button>
            </div>
            <div class="table-wrap" id="render-planilla">
                <table>
                    <thead id="h-pla"></thead>
                    <tbody id="b-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- SECCIÓN PUESTOS -->
        <div id="s-pue" class="section">
            <div class="form-box">
                <input type="text" id="pue-nom" placeholder="Nombre del Objetivo">
                <input type="text" id="pue-hor" placeholder="Horario (ej: 06:00 a 18:00)">
                <input type="number" id="pue-can" placeholder="Agentes Necesarios">
                <button class="btn-gold" onclick="savePuesto()">Crear Objetivo</button>
            </div>
            <div class="puestos-grid" id="grid-puestos"></div>
        </div>

        <!-- SECCIÓN PERSONAL -->
        <div id="s-per" class="section">
            <div class="form-box">
                <input type="text" id="per-leg" placeholder="Legajo">
                <input type="text" id="per-ape" placeholder="Apellido">
                <input type="text" id="per-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="savePersonal()">Registrar</button>
            </div>
            <div class="table-wrap">
                <table style="font-size: 18px;">
                    <thead><tr><th style="padding:20px">Legajo</th><th>Agente</th><th>Gestión</th></tr></thead>
                    <tbody id="b-per"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const estados = ["F", "12", "ART", "VAC"];
        let personalGlobal = [];

        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active-section'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('s-'+t).classList.add('active-section');
            document.getElementById('n-'+t).classList.add('active');
            render();
        }

        async function render() {
            try {
                const [per, nov, pue] = await Promise.all([
                    fetch('/api/personal').then(r => r.json()),
                    fetch('/api/novedades').then(r => r.json()),
                    fetch('/api/puestos').then(r => r.json())
                ]);
                personalGlobal = per;

                const m = document.getElementById('sel-mes').value;
                const a = document.getElementById('sel-anio').value;
                const diasMes = new Date(a, m, 0).getDate();

                // 1. Render Planilla
                let h = `<tr><th class="name-col">AGENTES (ORDEN ALF.)</th>`;
                for(let i=1; i<=diasMes; i++) h += `<th class="th-date"><span class="date-label">Día ${i}</span></th>`;
                h += `<th class="total-col">TOTAL HS</th></tr>`;
                document.getElementById('h-pla').innerHTML = h;

                document.getElementById('b-pla').innerHTML = per.map(p => {
                    let acumuladoHs = 0;
                    let celdas = `<td class="name-col">${p.apellido.toUpperCase()}, ${p.nombre}</td>`;
                    for(let i=1; i<=diasMes; i++) {
                        const fechaIdx = `${a}-${String(m).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
                        const registro = nov.find(x => x.personal_id == p.id && x.fecha == fechaIdx);
                        const st = registro ? registro.estado : 'F';
                        if(st === '12') acumuladoHs += 12;
                        celdas += `<td class="cell-${st}" onclick="cycleEstado(this, ${p.id}, '${fechaIdx}')">${st}</td>`;
                    }
                    celdas += `<td class="total-col">${acumuladoHs}</td>`;
                    return `<tr>${celdas}</tr>`;
                }).join('');

                // 2. Render Personal
                document.getElementById('b-per').innerHTML = per.map(p => `
                    <tr><td style="font-weight:bold">${p.legajo}</td><td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button onclick="delPer(${p.id})" style="background:#441111; color:red; border:1px solid red; padding:10px; cursor:pointer; border-radius:5px">Eliminar</button></td></tr>
                `).join('');

                // 3. Render Puestos (con Selectores de Personal)
                document.getElementById('grid-puestos').innerHTML = pue.map(x => {
                    let selects = '';
                    for(let j=0; j<x.cantidad; j++) {
                        selects += `
                        <select>
                            <option>-- Asignar Agente --</option>
                            ${per.map(ag => `<option>${ag.apellido}, ${ag.nombre} (${ag.legajo})</option>`).join('')}
                        </select>`;
                    }
                    return `
                    <div class="puesto-box">
                        <h3>${x.nombre}</h3>
                        <p style="color:#aaa; margin:0">Horario: ${x.horario}</p>
                        <p style="color:var(--gold); font-weight:bold">Dotación Requerida: ${x.cantidad}</p>
                        <div style="margin-top:15px">${selects}</div>
                        <button onclick="delPue(${x.id})" style="margin-top:20px; background:none; border:1px solid #555; color:#888; cursor:pointer; font-size:12px; padding:5px">Eliminar Objetivo</button>
                    </div>`;
                }).join('');

            } catch (err) { console.error("Error en render:", err); }
        }

        async function cycleEstado(td, pid, fecha) {
            let actual = td.innerText;
            let proximo = estados[(estados.indexOf(actual) + 1) % estados.length];
            await fetch('/api/novedades', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({p_id: pid, fecha: fecha, estado: proximo})
            });
            render();
        }

        async function savePersonal() {
            const d = { 
                legajo: document.getElementById('per-leg').value, 
                apellido: document.getElementById('per-ape').value, 
                nombre: document.getElementById('per-nom').value 
            };
            if(!d.legajo || !d.apellido) return alert("Faltan datos");
            await fetch('/api/personal', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            document.getElementById('per-leg').value=''; document.getElementById('per-ape').value=''; document.getElementById('per-nom').value='';
            render();
        }

        async function delPer(id) { if(confirm('¿Eliminar Agente de forma permanente?')) { await fetch(`/api/personal?id=${id}`, {method:'DELETE'}); render(); } }

        async function savePuesto() {
            const d = { 
                nombre: document.getElementById('pue-nom').value, 
                horario: document.getElementById('pue-hor').value, 
                cantidad: document.getElementById('pue-can').value 
            };
            await fetch('/api/puestos', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(d)});
            render();
        }

        async function delPue(id) { if(confirm('¿Eliminar Objetivo?')) { await fetch(`/api/puestos?id=${id}`, {method:'DELETE'}); render(); } }

        function genPDF(id, name, format, orient) {
            const el = document.getElementById(id);
            const opt = { margin: 10, filename: `${name}.pdf`, html2canvas: { scale: 2 }, jsPDF: { unit: 'mm', format: format, orientation: orient } };
            html2pdf().set(opt).from(el).save();
        }

        window.onload = () => {
            const m = document.getElementById('sel-mes'); const a = document.getElementById('sel-anio'); const now = new Date();
            const mesesStr = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
            mesesStr.forEach((n, i) => m.innerHTML += `<option value="${i+1}" ${i==now.getMonth()?'selected':''}>${n}</option>`);
            for(let i=2025; i<=2026; i++) a.innerHTML += `<option value="${i}" ${i==now.getFullYear()?'selected':''}>${i}</option>`;
            render();
        };
    </script>
</body>
</html>
'''
