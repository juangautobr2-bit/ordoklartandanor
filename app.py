import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# CONFIGURACIÓN DE BASE DE DATOS
# Usamos /tmp/ para asegurar permisos de escritura en el servidor de Render
DB_PATH = '/tmp/ordoklar.db'

def init_db():
    """Crea las tablas necesarias si no existen."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Tabla de Personal
        cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellido TEXT,
            legajo TEXT UNIQUE,
            estado_p TEXT DEFAULT 'ACTIVO'
        )''')
        # Tabla de Puestos
        cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER
        )''')
        # Tabla de Novedades
        cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personal_id INTEGER,
            fecha TEXT,
            estado TEXT,
            UNIQUE(personal_id, fecha)
        )''')
        conn.commit()
        conn.close()
        print(f"Base de datos inicializada en {DB_PATH}")
    except Exception as e:
        print(f"Error al inicializar DB: {e}")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- RUTAS DE LA API ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        try:
            conn.execute("INSERT INTO personal (nombre, apellido, legajo, estado_p) VALUES (?, ?, ?, ?)", 
                         (d['nombre'], d['apellido'], d['legajo'], d['estado_p']))
            conn.commit()
        except sqlite3.IntegrityError:
            return jsonify({"error": "Legajo duplicado"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    res = [dict(row) for row in conn.execute("SELECT * FROM personal ORDER BY apellido ASC").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE', 'PUT'])
def handle_personal_individual(id):
    conn = get_db_connection()
    if request.method == 'DELETE':
        conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    elif request.method == 'PUT':
        d = request.json
        conn.execute("UPDATE personal SET nombre=?, apellido=?, legajo=?, estado_p=? WHERE id=?", 
                     (d['nombre'], d['apellido'], d['legajo'], d['estado_p'], id))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/actualizar_novedad', methods=['POST'])
def update_nov():
    conn = get_db_connection()
    d = request.json
    try:
        conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                        ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                     (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "success"})

@app.route('/api/novedades')
def get_novedades():
    conn = get_db_connection()
    res = [dict(row) for row in conn.execute("SELECT * FROM novedades").fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/puestos', methods=['GET', 'POST'])
def handle_puestos():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute("INSERT INTO puestos (nombre, cantidad) VALUES (?, ?)", (d['nombre'], d['cantidad']))
        conn.commit()
    res = [dict(row) for row in conn.execute("SELECT * FROM puestos ORDER BY nombre ASC").fetchall()]
    conn.close()
    return jsonify(res)

# --- RUTA PRINCIPAL ---

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- INTERFAZ DE USUARIO (HTML/CSS/JS) ---

HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORDO KLAR | Gestión</title>
    <style>
        :root { 
            --gold: #C5A059; --black: #050505; --dark-gray: #121212; 
            --text: #E0E0E0; --danger: #CF6679;
            --c12: #1b5e20; --cF: #dae343; --cVAC: #01579b;
        }
        body { background: var(--black); color: var(--text); font-family: sans-serif; margin: 0; }
        .header { border-bottom: 1px solid var(--gold); padding: 20px; text-align: center; }
        .logo { letter-spacing: 5px; color: var(--text); }
        .logo span { color: var(--gold); }
        
        .nav { display: flex; justify-content: center; background: var(--dark-gray); }
        .nav-btn { background: none; border: none; color: #888; padding: 15px; cursor: pointer; text-transform: uppercase; font-size: 12px; }
        .nav-btn.active { color: var(--gold); border-bottom: 2px solid var(--gold); }

        .container { padding: 20px; max-width: 1200px; margin: auto; }
        .section { display: none; }
        .section.active { display: block; }

        .card { background: var(--dark-gray); padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #222; }
        input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; margin: 5px; border-radius: 4px; }
        .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-gold { background: var(--gold); color: #000; }

        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #222; padding: 10px; text-align: center; }
        .col-nombre { text-align: left; color: var(--gold); }
        
        .cell-12 { background: var(--c12); }
        .cell-F { background: var(--cF); color: #000; }
        .cell-VAC { background: var(--cVAC); }
        
        select { background: transparent; color: #fff; border: none; font-weight: bold; width: 100%; cursor: pointer; }
    </style>
</head>
<body>

<div class="header">
    <h1 class="logo">ORDO <span>KLAR</span></h1>
</div>

<div class="nav">
    <button class="nav-btn active" onclick="showTab('planilla')">Planilla</button>
    <button class="nav-btn" onclick="showTab('personal')">Personal</button>
</div>

<div class="container">
    <div id="planilla" class="section active">
        <div style="overflow-x: auto;">
            <table>
                <thead id="h-mensual"></thead>
                <tbody id="b-mensual"></tbody>
            </table>
        </div>
    </div>

    <div id="personal" class="section">
        <div class="card">
            <h3>NUEVO PERSONAL</h3>
            <input type="text" id="p_legajo" placeholder="Legajo">
            <input type="text" id="p_apellido" placeholder="Apellido">
            <input type="text" id="p_nombre" placeholder="Nombre">
            <button class="btn btn-gold" onclick="savePersonal()">GUARDAR</button>
        </div>
        <table id="lista-personal"></table>
    </div>
</div>

<script>
    let personal = [], novedades = [];

    async function loadData() {
        try {
            const resP = await fetch('/api/personal');
            const resN = await fetch('/api/novedades');
            personal = await resP.json();
            novedades = await resN.json();
            renderPersonal();
            renderPlanilla();
        } catch (e) { console.error("Error cargando datos:", e); }
    }

    function showTab(id) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        event.currentTarget.classList.add('active');
    }

    async function savePersonal() {
        const d = { 
            legajo: document.getElementById('p_legajo').value, 
            apellido: document.getElementById('p_apellido').value, 
            nombre: document.getElementById('p_nombre').value,
            estado_p: 'ACTIVO' 
        };
        const res = await fetch('/api/personal', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(d)
        });
        if(res.ok) {
            document.querySelectorAll('input').forEach(i => i.value = '');
            loadData();
        } else { alert("Error al guardar. ¿Legajo duplicado?"); }
    }

    function renderPersonal() {
        document.getElementById('lista-personal').innerHTML = personal.map(p => `
            <tr>
                <td>${p.legajo}</td>
                <td class="col-nombre">${p.apellido.toUpperCase()}, ${p.nombre}</td>
                <td><button onclick="deleteP(${p.id})">BORRAR</button></td>
            </tr>
        `).join('');
    }

    function renderPlanilla() {
        const totalDias = 31; // Simplificado para prueba
        let h = '<tr><th>PERSONAL</th>';
        for(let i=1; i<=totalDias; i++) h += `<th>${i}</th>`;
        document.getElementById('h-mensual').innerHTML = h + '</tr>';

        document.getElementById('b-mensual').innerHTML = personal.map(p => {
            let celdas = "";
            for(let i=1; i<=totalDias; i++) {
                const fecha = `2026-05-${String(i).padStart(2,'0')}`;
                const n = novedades.find(x => x.personal_id == p.id && x.fecha == fecha);
                const e = n ? n.estado : 'F';
                celdas += `<td class="cell-${e}">
                    <select onchange="updateNov(${p.id}, '${fecha}', this.value)">
                        <option value="12" ${e=='12'?'selected':''}>12</option>
                        <option value="F" ${e=='F'?'selected':''}>F</option>
                        <option value="VAC" ${e=='VAC'?'selected':''}>V</option>
                    </select>
                </td>`;
            }
            return `<tr><td class="col-nombre">${p.apellido}</td>${celdas}</tr>`;
        }).join('');
    }

    async function updateNov(p_id, fecha, estado) {
        await fetch('/api/actualizar_novedad', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({p_id, fecha, estado})
        });
        loadData();
    }

    async function deleteP(id) {
        if(confirm("¿Eliminar?")) {
            await fetch(`/api/personal/${id}`, {method: 'DELETE'});
            loadData();
        }
    }

    window.onload = loadData;
</script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
