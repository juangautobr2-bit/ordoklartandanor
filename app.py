import os
import sqlite3
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# CAMBIO CRÍTICO: Movemos la DB a la carpeta temporal del sistema
# Esto evita el error 500 por falta de permisos de escritura
DB_PATH = '/tmp/ordoklar.db' 

def init_db():
    """Inicializa la base de datos en la ruta temporal."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS personal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            apellido TEXT,
            legajo TEXT UNIQUE,
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
        print(f"Base de datos creada exitosamente en {DB_PATH}")
    except Exception as e:
        print(f"ERROR CRÍTICO AL INICIALIZAR DB: {e}")

# ... (El resto de tus rutas de API se mantienen igual)
