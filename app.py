import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Usamos una ruta que Render garantiza como escribible
DB_PATH = '/tmp/ordoklar.db'

def get_db_connection():
    """Conexión con creación automática de tablas para evitar el error 'no such table'."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # --- AUTO-FIX: Verificamos y creamos las tablas en cada conexión ---
    cursor = conn.cursor()
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
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_UI)

# --- API ---

@app.route('/api/personal', methods=['GET', 'POST'])
def handle_personal():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            d = request.json
            if not d.get('apellido'):
                return jsonify({"error": "El apellido es obligatorio"}), 400
            
            cursor.execute(
                "INSERT INTO personal (nombre, apellido, legajo) VALUES (?, ?, ?)",
                (d.get('nombre', ''), d.get('apellido', ''), d.get('legajo', ''))
            )
            conn.commit()
            conn.close()
            return jsonify({"status": "success"}), 201

        # GET
        cursor.execute("SELECT * FROM personal ORDER BY apellido ASC")
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/personal/<int:id>', methods=['DELETE'])
def delete_personal(id):
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM personal WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- INTERFAZ PREMIUM ---
HTML_UI = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ORDO KLAR | Panel</title>
    <style>
        :root { --gold: #C5A059; --black: #050505; --gray: #121212; }
        body { background: var(--black); color: #fff; font-family: 'Segoe UI', sans-serif; margin: 0; padding: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .card { background: var(--gray); padding: 30px; border-radius: 15px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { color: var(--gold); letter-spacing: 4px; text-align: center; text-transform: uppercase; margin-bottom: 30px; }
        input { background: #000; border: 1px solid #444; color: #fff; padding: 12px; margin-bottom: 15px; width: 100%; border-radius: 8px; box-sizing: border-box; }
        input:focus { border-color: var(--gold); outline: none; }
        button { background: var(--gold); color: #000; border: none; padding: 15px; width: 100%; font-weight: bold; cursor: pointer; border-radius: 8px; text-transform: uppercase; transition: 0.3s; }
        button:hover { background: #e0b86d; transform: translateY(-2px); }
        table { width: 100%; border-collapse: collapse; margin-top: 30px; }
        th { text-align: left; color: var(--gold); border-bottom: 1px solid #333; padding: 10px; font-size: 12px; }
        td { padding: 12px; border-bottom: 1px solid #222; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>ORDO <span style="color:#fff">KLAR</span></h2>
        
        <div class="card">
            <input type="text" id="legajo" placeholder="N° de Legajo">
            <input type="text" id="apellido" placeholder="Apellido">
            <input type="text" id="nombre" placeholder="Nombre">
            <button onclick="guardar()">Registrar Personal</button>
        </div>

        <div id="lista-container">
            <table>
                <thead><tr><th>Legajo</th><th>Nombre Completo</th><th></th></tr></thead>
                <tbody id="tabla-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        async function cargar() {
            const r = await fetch('/api/personal');
            const data = await r.json();
            const body = document.getElementById('tabla-body');
            body.innerHTML = data.map(p => `
                <tr>
                    <td>${p.legajo}</td>
                    <td style="font-weight:bold;">${p.apellido.toUpperCase()}, ${p.nombre}</td>
                    <td style="text-align:right;"><button onclick="eliminar(${p.id})" style="background:none; color:#ff4444; width:auto; padding:0; border:none; font-size:18px;">&times;</button></td>
                </tr>
            `).join('');
        }

        async function guardar() {
            const btn = event.target;
            btn.disabled = true;
            btn.innerText = "Guardando...";

            const datos = {
                legajo: document.getElementById('legajo').value,
                apellido: document.getElementById('apellido').value,
                nombre: document.getElementById('nombre').value
            };

            try {
                const r = await fetch('/api/personal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(datos)
                });
                
                if(r.ok) {
                    document.querySelectorAll('input').forEach(i => i.value = '');
                    await cargar();
                } else {
                    const res = await r.json();
                    alert("Error: " + res.error);
                }
            } catch (e) {
                alert("Error de conexión");
            } finally {
                btn.disabled = false;
                btn.innerText = "Registrar Personal";
            }
        }

        async function eliminar(id) {
            if(confirm("¿Eliminar registro?")) {
                await fetch('/api/personal/' + id, { method: 'DELETE' });
                cargar();
            }
        }

        window.onload = cargar;
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # No llamamos a init_db aquí, se llama automáticamente al conectar
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
