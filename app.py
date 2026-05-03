import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Intentamos usar /tmp que es el estándar de Linux para archivos temporales
DB_PATH = '/tmp/ordoklar.db'

def get_db_connection():
    """Establece conexión con reintentos y configuración de permisos."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea las tablas forzando la creación del archivo."""
    try:
        # Si el archivo existe pero da problemas, podrías descomentar la siguiente línea para resetearlo:
        # if os.path.exists(DB_PATH): os.remove(DB_PATH)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        # Usamos una estructura simple sin restricciones UNIQUE para testeo total
        cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellido TEXT,
            legajo TEXT,
            estado_p TEXT DEFAULT 'ACTIVO'
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS novedades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personal_id INTEGER,
            fecha TEXT,
            estado TEXT
        )''')
        conn.commit()
        conn.close()
        print("SISTEMA DE BASE DE DATOS INICIADO")
    except Exception as e:
        print(f"ERROR CRÍTICO DB: {e}")

# --- RUTAS API ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            d = request.json
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)",
                (d.get('nombre'), d.get('apellido'), d.get('legajo'))
            )
            conn.commit()
            return jsonify({"status": "success"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    
    # GET
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM personal ORDER BY apellido ASC")
    res = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(res)

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM personal WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- INTERFAZ COMPLETA (HTML/JS) ---
HTML_UI = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Gestión</title>
    <style>
        body { background: #050505; color: #fff; font-family: sans-serif; padding: 20px; }
        .gold { color: #C5A059; }
        .card { background: #121212; padding: 20px; border-radius: 10px; border: 1px solid #C5A059; margin-bottom: 20px; }
        input { background: #000; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 5px; margin-bottom: 10px; width: 100%; box-sizing: border-box; }
        button { background: #C5A059; color: #000; border: none; padding: 10px; width: 100%; font-weight: bold; cursor: pointer; border-radius: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #222; padding: 12px; text-align: left; }
        th { color: #C5A059; text-transform: uppercase; font-size: 12px; }
    </style>
</head>
<body>
    <h1 style="text-align:center; letter-spacing:5px;">ORDO <span class="gold">KLAR</span></h1>
    
    <div class="card">
        <h3 class="gold">ALTA DE PERSONAL</h3>
        <input type="text" id="legajo" placeholder="Número de Legajo / DNI">
        <input type="text" id="apellido" placeholder="Apellido">
        <input type="text" id="nombre" placeholder="Nombre">
        <button onclick="enviar()">REGISTRAR EN BASE DE DATOS</button>
    </div>

    <div class="card">
        <h3 class="gold">LISTADO ACTUAL</h3>
        <table>
            <thead><tr><th>Legajo</th><th>Personal</th><th>Acción</th></tr></thead>
            <tbody id="lista"></tbody>
        </table>
    </div>

    <script>
        async function listar() {
            const r = await fetch('/api/personal');
            const data = await r.json();
            const tabla = document.getElementById('lista');
            tabla.innerHTML = data.map(p => `
                <tr>
                    <td>${p.legajo}</td>
                    <td>${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td><button onclick="eliminar(${p.id})" style="background:red; color:white; width:auto; padding:5px 10px;">X</button></td>
                </tr>
            `).join('');
        }

        async function enviar() {
            const payload = {
                legajo: document.getElementById('legajo').value,
                apellido: document.getElementById('apellido').value,
                nombre: document.getElementById('nombre').value
            };
            
            if(!payload.legajo || !payload.apellido) return alert("Legajo y Apellido son obligatorios");

            const r = await fetch('/api/personal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            if(r.ok) {
                document.querySelectorAll('input').forEach(i => i.value = '');
                listar();
            } else {
                alert("Error al guardar en el servidor");
            }
        }

        async function eliminar(id) {
            await fetch('/api/personal/' + id, { method: 'DELETE' });
            listar();
        }

        window.onload = listar;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
