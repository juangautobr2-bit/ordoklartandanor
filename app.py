import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Cambiamos el nombre de la DB para asegurar que no haya conflictos de tablas viejas
DB_PATH = '/tmp/ordoklar_v9.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, apellido TEXT, legajo TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS puestos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, cantidad INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS novedades (id INTEGER PRIMARY KEY AUTOINCREMENT, personal_id INTEGER, fecha TEXT, estado TEXT, UNIQUE(personal_id, fecha))')
    conn.commit()
    return conn

@app.route('/')
def index():
    # El parámetro v=9 fuerza al navegador a refrescar el diseño
    return render_template_string(HTML_UI)

# --- APIs PERSONAL ---
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

# --- API NOVEDADES ---
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

# --- INTERFAZ REDISEÑADA ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel Profesional</title>
    <style>
        :root { --gold: #C5A059; --bg: #050505; --card: #121212; --border: #222; }
        body { background: var(--bg); color: #fff; font-family: 'Inter', sans-serif; margin: 0; }
        
        .top-bar { text-align: center; padding: 20px; font-size: 22px; letter-spacing: 8px; border-bottom: 1px solid var(--border); }
        
        .nav { display: flex; justify-content: center; background: var(--card); border-bottom: 2px solid var(--gold); }
        .nav button { background: none; border: none; color: #666; padding: 15px 30px; cursor: pointer; font-weight: bold; font-size: 11px; text-transform: uppercase; }
        .nav button.active { color: var(--gold); }

        .content { padding: 15px; }
        .section { display: none; }
        .active { display: block; }

        /* PLANILLA MENSUAL COMPACTA CON COLUMNA HS */
        .scroll-container { width: 100%; overflow: hidden; border: 1px solid var(--border); }
        table.main-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 9px; }
        .main-table th, .main-table td { border: 1px solid #1a1a1a; text-align: center; height: 35px; }
        .main-table th { background: #111; color: var(--gold); font-weight: normal; }
        
        .name-cell { width: 100px; text-align: left !important; padding-left: 8px; color: var(--gold); font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .hs-cell { width: 40px; background: #1a1a1a; color: var(--gold); font-weight: bold; border-left: 2px solid var(--gold) !important; font-size: 11px; }

        /* COLORES ASISTENCIA */
        select { background: transparent; color: #fff; border: none; width: 100%; height: 100%; cursor: pointer; text-align-last: center; font-weight: bold; outline: none; appearance: none; }
        .st-12 { background: #1b5e20 !important; }
        .st-F { background: #333 !important; }
        .st-VAC { background: #01579b !important; }
        .st-ART { background: #b71c1c !important; }

        /* SECCION PERSONAL */
        .card { background: var(--card); border: 1px solid var(--border); padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .btn-gold { background: var(--gold); color: #000; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; }
        .btn-edit { color: var(--gold); border: 1px solid var(--gold); background: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; margin-right: 10px; }
        
        input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 4px; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="top-bar">ORDO <span style="color:var(--gold)">KLAR</span></div>
    
    <div class="nav">
        <button id="nav-pla" class="active" onclick="tab('pla')">Planilla Mensual</button>
        <button id="nav-per" onclick="tab('per')">Personal</button>
    </div>

    <div class="content">
        <!-- PLANILLA -->
        <div id="sec-pla" class="section active">
            <div class="scroll-container">
                <table class="main-table">
                    <thead id="head-pla"></thead>
                    <tbody id="body-pla"></tbody>
                </table>
            </div>
        </div>

        <!-- PERSONAL -->
        <div id="sec-per" class="section">
            <div class="card">
                <input type="text" id="in-leg" placeholder="Legajo">
                <input type="text" id="in-ape" placeholder="Apellido">
                <input type="text" id="in-nom" placeholder="Nombre">
                <button class="btn-gold" onclick="addPersonal()">REGISTRAR</button>
            </div>
            <div id="list-per"></div>
        </div>
    </div>

    <script>
        function tab(t) {
            document.querySelectorAll('.section').forEach(x => x.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active'));
            document.getElementById('sec-'+t).classList.add('active');
            document.getElementById('nav-'+t).classList.add('active');
        }

        async function init() {
            const [p, n] = await Promise.all([
                fetch('/api/personal').then(r => r.json()),
                fetch('/api/novedades').then(r => r.json())
            ]);

            // 1. GESTION PERSONAL (CON EDITAR)
            document.getElementById('list-per').innerHTML = p.map(x => `
                <div class="card" style="display:flex; justify-content:space-between; align-items:center; padding:10px 20px;">
                    <span><b>${x.legajo}</b> - ${x.apellido.toUpperCase()}, ${x.nombre}</span>
                    <div>
                        <button class="btn-edit" onclick="editPersonal(${x.id},'${x.nombre}','${x.apellido}','${x.legajo}')">EDITAR</button>
                        <button style="color:red; background:none; border:none; cursor:pointer;" onclick="delPersonal(${x.id})">ELIMINAR</button>
                    </div>
                </div>`).join('');

            // 2. PLANILLA (HS Y AUTO-AJUSTE)
            const dias = new Date(2026, 5, 0).getDate(); // Mayo 2026
            let h = '<tr><th class="name-cell">Personal</th>';
            for(let i=1; i<=dias; i++) h += `<th>${i}</th>`;
            h += '<th class="hs-cell">HS</th></tr>';
            document.getElementById('head-pla').innerHTML = h;

            document.getElementById('body-pla').innerHTML = p.map(per => {
                let r = `<td class="name-cell">${per.apellido.toUpperCase()}</td>`;
                let totalHs = 0;
                for(let i=1; i<=dias; i++) {
                    const fecha = `2026-05-${String(i).padStart(2,'0')}`;
                    const data = n.find(x => x.personal_id == per.id && x.fecha == fecha);
                    const est = data ? data.estado : 'F';
                    if(est == '12') totalHs += 12;
                    r += `<td class="st-${est}">
                        <select onchange="updateNov(${per.id},'${fecha}',this.value)">
                            <option value="12" ${est=='12'?'selected':''}>12</option>
                            <option value="F" ${est=='F'?'selected':''}>F</option>
                            <option value="VAC" ${est=='VAC'?'selected':''}>V</option>
                            <option value="ART" ${est=='ART'?'selected':''}>A</option>
                        </select>
                    </td>`;
                }
                return `<tr>${r}<td class="hs-cell">${totalHs}</td></tr>`;
            }).join('');
        }

        async function editPersonal(id, n, a, l) {
            const na = prompt("Apellido:", a);
            const nn = prompt("Nombre:", n);
            const nl = prompt("Legajo:", l);
            if(na && nn) {
                await fetch('/api/personal/'+id, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nombre:nn, apellido:na, legajo:nl}) });
                init();
            }
        }

        async function updateNov(pid, f, e) {
            await fetch('/api/novedades', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({p_id:pid, fecha:f, estado:e}) });
            init();
        }

        async function addPersonal() {
            const d = {nombre:document.getElementById('in-nom').value, apellido:document.getElementById('in-ape').value, legajo:document.getElementById('in-leg').value};
            await fetch('/api/personal', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(d) });
            init();
        }

        async function delPersonal(id) { if(confirm("¿Eliminar?")) { await fetch('/api/personal/'+id, {method:'DELETE'}); init(); } }

        window.onload = init;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
