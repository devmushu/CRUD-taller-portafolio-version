import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('test.db')  # Cambia el nombre si necesitas otro archivo
cursor = conn.cursor()