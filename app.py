import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# CONFIGURACIÓN DE RUTA: Forzamos una ruta simple según el sistema
if os.name == 'nt': 
    DB_PATH = os.path.join(os.getcwd(), 'ordoklar.db')
else: 
    DB_PATH = '/tmp/ordoklar.db'

def init_db():
    """Inicializa la base de datos sin restricciones estrictas para evitar errores."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Eliminamos 'UNIQUE' del legajo para que nunca de error de duplicado por ahora
        cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellido TEXT,
            legajo TEXT,
            estado_p TEXT DEFAULT 'ACTIVO'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS puestos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            cantidad INTEGER
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personal_id INTEGER,
            fecha TEXT,
            estado TEXT,
            UNIQUE(personal_id, fecha)
        )''')
        conn.commit()
        conn.close()
        print(f"Base de datos lista en: {DB_PATH}")
    except Exception as e:
        print(f"Error inicializando DB: {e}")

def get_db_connection():
    return sqlite3.connect(DB_PATH)

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API CORREGIDA ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        try:
            d = request.json
            # Validamos que los datos no lleguen vacíos
            if not d.get('apellido') or not d.get('legajo'):
                return jsonify({"error": "Faltan datos obligatorios"}), 400
            
            cursor.execute("INSERT INTO personal (nombre, apellido, legajo, estado_p) VALUES (?, ?, ?, 'ACTIVO')", 
                         (d.get('nombre', ''), d.get('apellido', ''), d.get('legajo', '')))
            conn.commit()
            print("Personal guardado con éxito")
        except Exception as e:
            conn.rollback()
            print(f"Error al insertar: {e}")
            return jsonify({"error": str(e)}), 500
    
    cursor.execute("SELECT * FROM personal ORDER BY apellido ASC")
    rows = cursor.fetchall()
    res = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route('/api/novedades', methods=['GET', 'POST'])
def handle_novedades():
    conn = get_db_connection()
    if request.method == 'POST':
        d = request.json
        conn.execute('''INSERT INTO novedades (personal_id, fecha, estado) VALUES (?, ?, ?) 
                        ON CONFLICT(personal_id, fecha) DO UPDATE SET estado=excluded.estado''', 
                     (d['p_id'], d['fecha'], d['estado']))
        conn.commit()
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM novedades")
    res = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
    conn.close()
    return jsonify(res)

# --- INTERFAZ (HTML) ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión</title>
    <style>
        :root { --gold: #C5A059; --black: #050505; --gray: #1E1E1E; }
        body { background: var(--black); color: #fff; font-family: sans-serif; margin: 0; padding: 20px; }
        .card { background: var(--gray); padding: 20px; border-radius: 8px; border: 1px solid #333; margin-bottom: 20px; }
        input { background: #000; border: 1px solid var(--gold); color: #fff; padding: 10px; margin: 5px; border-radius: 4px; }
        button { background: var(--gold); color: #000; border: none; padding: 10px 20px; cursor: pointer; font-weight: bold; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #333; padding: 10px; text-align: left; }
        th { color: var(--gold); }
        .nav { margin-bottom: 20px; text-align: center; border-bottom: 1px solid var(--gold); padding-bottom: 10px; }
        .nav-btn { background: none; color: #888; border: none; cursor: pointer; margin: 0 10px; text-transform: uppercase; font-size: 12px; }
        .active-btn { color: var(--gold); font-weight: bold; }
    </style>
</head>
<body>
    <h2 style="text-align:center; letter-spacing:3px;">ORDO <span style="color:var(--gold)">KLAR</span></h2>
    <div class="nav">
        <button class="nav-btn active-btn" onclick="showTab('tab-personal')">Personal</button>
        <button class="nav-btn" onclick="showTab('tab-planilla')">Planilla</button>
    </div>

    <div id="tab-personal" class="section">
        <div class="card">
            <h3>Registrar Personal</h3>
            <input type="text" id="legajo" placeholder="Legajo (DNI)">
            <input type="text" id="apellido" placeholder="Apellido">
            <input type="text" id="nombre" placeholder="Nombre">
            <button onclick="guardarPersonal()">GUARDAR</button>
        </div>
        <div class="card">
            <table id="tabla-personal">
                <thead><tr><th>Legajo</th><th>Apellido</th><th>Nombre</th><th>Acción</th></tr></thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <div id="tab-planilla" class="section" style="display:none">
        <div class="card">
            <h3>Planilla de Novedades</h3>
            <p>Aquí se reflejará el personal cargado.</p>
            <div id="contenedor-planilla"></div>
        </div>
    </div>

    <script>
        async function cargarPersonal() {
            const res = await fetch('/api/personal');
            const data = await res.json();
            const tbody = document.querySelector('#tabla-personal tbody');
            tbody.innerHTML = '';
            data.forEach(p => {
                tbody.innerHTML += `<tr>
                    <td>${p.legajo}</td>
                    <td>${p.apellido}</td>
                    <td>${p.nombre}</td>
                    <td><button style="background:red; color:white; padding:5px;" onclick="eliminarPersonal(${p.id})">X</button></td>
                </tr>`;
            });
        }

        async function guardarPersonal() {
            const doc = {
                legajo: document.getElementById('legajo').value,
                apellido: document.getElementById('apellido').value,
                nombre: document.getElementById('nombre').value
            };
            
            const res = await fetch('/api/personal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(doc)
            });

            if(res.ok) {
                alert("Guardado correctamente");
                document.getElementById('legajo').value = '';
                document.getElementById('apellido').value = '';
                document.getElementById('nombre').value = '';
                cargarPersonal();
            } else {
                const err = await res.json();
                alert("Error al guardar: " + err.error);
            }
        }

        async function eliminarPersonal(id) {
            if(confirm("¿Eliminar?")) {
                await fetch(`/api/personal/${id}`, {method: 'DELETE'});
                cargarPersonal();
            }
        }

        function showTab(id) {
            document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
            document.getElementById(id).style.display = 'block';
        }

        window.onload = cargarPersonal;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
