from flask import Flask, render_template, request, redirect, url_for, flash , session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from models import *
from functools import wraps
from datetime import timedelta
import base64 #====> para convertir pdf datos en base64
import os


app = Flask(__name__)
app.secret_key = '123'

# Configurar para que la cookie expire al cerrar el navegador
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=45)# Deshabilitar cookies persistentes
# app.config['SESSION_TYPE'] = 'filesystem'  # Almacenar sesiones en archivos temporales

#cerrar sesion
@app.route('/logout')
def logout():
    # Limpiar toda la información de la sesión
    session.clear()

    # Mostrar mensaje y redirigir al login
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('login'))

# roles 


def requiere_rol(*roles_permitidos):
    """
    Decorador para restringir el acceso a usuarios con roles específicos.
    :param roles_permitidos: Lista de roles permitidos para acceder a la ruta.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'rol' not in session or session['rol'] not in roles_permitidos:
                flash('No tienes permiso para acceder a esta página.', 'error')
                return redirect(url_for('login'))  # Redirige a login si no tiene el rol adecuado
            return f(*args, **kwargs)
        return decorated_function
    return decorator




def verificar_usuario_existe(username):
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuario WHERE username = ?', (username,))
    usuario = cursor.fetchone()
    conn.close()
    return usuario  # Devuelve el usuario si existe, de lo contrario None
# crear usuario

@app.route('/crear_usuario', methods=['GET', 'POST'])
@requiere_rol('Administrador')
def crear_usuario():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rol = request.form['rol']

        # Verificar si el usuario ya existe
        if verificar_usuario_existe(username):
            flash('El usuario ya existe. Elija otro nombre de usuario.', 'error')
            return redirect(url_for('crear_usuario'))

        password_hash = generate_password_hash(password)

        # Si no existe, insertar el nuevo usuario
        conn = sqlite3.connect('taller.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usuario (username, password, rol)
            VALUES (?, ?, ?)
        ''', (username, password_hash, rol))
        conn.commit()
        conn.close()

        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('vista_gestion'))

    return render_template('crear_usuario.html')



# login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        usuario = autenticar_usuario(username, password)

        if usuario:
            session['idUsuario'] = usuario['idUsuario']
            session['username'] = usuario['username']
            session['rol'] = usuario['rol']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('clientes'))  # Cambia según tu página principal
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')

def autenticar_usuario(username, password):
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuario WHERE username = ?', (username,))
    usuario = cursor.fetchone()
    conn.close()

    if usuario and check_password_hash(usuario['password'], password):
        return usuario
    return None


@app.route('/eliminar_cliente/<int:idUsuario>', methods=['POST'])
@requiere_rol('Administrador')
def eliminar_cliente(idUsuario):
    # Verificar si el rut es válido
    if not idUsuario:
        return render_template('error.html', message="No se proporcionó un RUT válido.")

    # Conectar a la base de datos
    conn = sqlite3.connect('taller.db')
    cursor = conn.cursor()

    try:
        # Sentencia SQL para eliminar el cliente por RUT
        sql = '''
        DELETE FROM usuario WHERE idUsuario = ?
        '''
        cursor.execute(sql, (idUsuario,))
        conn.commit()
        
        return redirect(url_for('vista_gestion'))

    except sqlite3.Error as e:
        conn.rollback()
        return render_template('error.html', message=f'Error al eliminar el cliente: {e}')
    finally:
        conn.close()




@app.route('/gestion')
@requiere_rol('Administrador')
def vista_gestion():
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(' SELECT idUsuario, username, rol FROM usuario')
    usuarios = cursor.fetchall()
    conn.close()
    
    return render_template('gestion_usuarios.html', usuarios = usuarios)



@app.route('/')
def mainmenu():
    return redirect(url_for('login'))






@app.route('/ingreso')
@requiere_rol('lector','editor','Administrador')
def dashboardingreso():
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row  # Esto permite acceder a los resultados como un diccionario
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * 
        FROM cliente 
        JOIN maquina ON cliente.rut = maquina.rut 
        WHERE maquina.estado_equipo = 'ENTREGADO'
    ''')
    clientes_maquinas = cursor.fetchall()
    conn.close()
    return render_template('ingreso.html', clientes_maquinas=clientes_maquinas)


@app.route('/dashboard')
@requiere_rol('lector','editor','Administrador')
def dashboard():
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM cliente 
        JOIN maquina ON cliente.rut = maquina.rut 
        WHERE maquina.estado_equipo = 'EN TALLER'
    ''')
    clientes_maquinas = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', clientes_maquinas=clientes_maquinas)

@app.route('/clientes')
@requiere_rol('lector','editor','Administrador')
def clientes():
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cliente')
    clientes = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/<rut>')
@requiere_rol('lector','editor','Administrador')
def cliente(rut):
    try:
        conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cliente WHERE rut = ?', (rut,))
        cliente = cursor.fetchone()

        if cliente is None:
            return f"No se encontró el cliente con RUT {rut}", 404  # Si no se encuentra el cliente

        cursor.execute('SELECT * FROM maquina WHERE rut = ?', (rut,))
        maquinas = cursor.fetchall()
        conn.close()

        return render_template('cliente.html', cliente=cliente, maquinas=maquinas)

    except sqlite3.Error as e:
        return f"Error en la base de datos: {e}", 500


@app.route('/maquina/<numeroSerie>')
@requiere_rol('lector','editor','Administrador')
def maquina(numeroSerie):
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM maquina WHERE numeroSerie = ?', (numeroSerie,))
    maquina = cursor.fetchone()
    cursor.execute('SELECT * FROM Informe WHERE numeroSerie = ?', (maquina['numeroSerie'],))
    informes = cursor.fetchall()
    conn.close()
    return render_template('maquina.html', maquina=maquina, informes=informes)

@app.route('/informe/<int:idInforme>')
@requiere_rol('lector','editor','Administrador')
def informe(idInforme):
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Informe WHERE idInforme = ?', (idInforme,))
    informe = cursor.fetchone()
    conn.close()
    return render_template('informe.html', informe=informe)

@app.route('/nuevo_cliente', methods=['POST'])
@requiere_rol('editor', 'Administrador')
def nuevo_cliente():
    if request.method == 'POST':
        # Obtener los datos enviados como JSON
        data = request.get_json()

        rut = data.get('rut')
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        empresa = data.get('empresa')
        correo = data.get('correo')
        telefono = data.get('telefono')

        # Verificar que los campos obligatorios estén completos
        if not rut or not nombre or not apellido:
            return jsonify({"success": False, "error": "Por favor complete todos los campos obligatorios."})

        # Verificar si el cliente ya existe
        existing_client = verificacion_rut(rut)
        if existing_client:
            return jsonify({"success": False, "error": f'El cliente con el RUT {rut} ya existe.'})

        # Conectar a la base de datos
        conn = sqlite3.connect('taller.db')
        cursor = conn.cursor()

        # Sentencia SQL para insertar el cliente
        sql = '''
        INSERT INTO cliente (rut, nombre, apellido, empresa, correo, telefono)
        VALUES (?, ?, ?, ?, ?, ?)
        '''

        try:
            cursor.execute(sql, (rut, nombre, apellido, empresa, correo, telefono))
            conn.commit()
            return jsonify({"success": True, "message": "Cliente agregado exitosamente!"})
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"success": False, "error": f'Error al agregar el cliente: {e}'})
        finally:
            conn.close()

    return render_template('clientes.html')  # Si no es una solicitud POST, renderizar el formulario

 # Si es GET, muestra el formulario



# Función de búsqueda modificada para ser reutilizada
def verificacion_rut(rut):
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Consulta SQL para buscar un cliente por RUT
    consulta = '''
    SELECT cliente.rut, cliente.nombre, cliente.apellido, cliente.correo, cliente.telefono
    FROM cliente
    WHERE cliente.rut LIKE ?
    LIMIT 1
    '''

    # Ejecutar la consulta SQL
    cursor.execute(consulta, (f'%{rut}%',))
    resultado = cursor.fetchone()  # Obtener un solo resultado

    conn.close()
    return resultado  # Retorna el resultado si existe un cliente con el RUT, de lo contrario None

# @app.route('/nuevo_cliente', methods=('GET', 'POST'))
# def nuevo_cliente():
#     if request.method == 'POST':
#         rut = request.form['rut']
#         nombre = request.form['nombre']
#         apellido = request.form['apellido']
#         empresa = request.form['empresa']
#         correo = request.form['correo']
#         telefono = request.form['telefono']
#         if rut and nombre and apellido:
#             conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
#             conn.row_factory = sqlite3.Row 
#             cursor = conn.cursor()
#             cursor.execute('''
#                 INSERT INTO cliente (rut,nombre, apellido, empresa, correo, telefono) 
#                 VALUES (?, ?, ?, ?, ?)
#             ''', (rut, nombre, apellido, empresa, correo, telefono))
#             conn.commit()
#             conn.close()
#             flash('Cliente añadido correctamente')
#             return redirect(url_for('clientes'))
#         else:
#             flash('!!! Ingrese todos los campos !!!')
#     return render_template('nuevo_cliente.html')

@app.route('/nueva_maquina/<rut>', methods=('GET', 'POST'))
@requiere_rol('editor','Administrador')
def nueva_maquina(rut):
    if request.method == 'POST':
        tipo_equipo = request.form['tipo_equipo']
        estado_equipo = request.form['estado_equipo']
        info = request.form['info']
        marca = request.form['marca']
        modelo = request.form['modelo']
        numeroSerie = request.form['numeroSerie']
        
        if tipo_equipo and estado_equipo and marca and modelo and numeroSerie:
            # Verificar si el número de serie ya existe
            if verificacion_serie(numeroSerie):
                flash('El número de serie ya está registrado en el sistema.', 'error')
            else:
                # Insertar la nueva máquina
                conn = sqlite3.connect('taller.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO maquina (tipo_equipo, estado_equipo, info, marca, modelo, numeroSerie, rut) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (tipo_equipo, estado_equipo, info, marca, modelo, numeroSerie, rut))
                conn.commit()
                conn.close()
                flash('Máquina registrada con éxito.', 'success')
                return redirect(url_for('cliente', rut=rut))
        else:
            flash('Por favor, complete todos los campos.', 'error')

    return render_template('nueva_maquina.html', rut=rut)


# Función de verificación del número de serie (sin cambios)
def verificacion_serie(numeroSerie):
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Consulta SQL para verificar si existe la máquina con el número de serie dado
    consulta = '''
    SELECT numeroSerie, tipo_equipo, estado_equipo, marca, modelo
    FROM maquina
    WHERE numeroSerie = ?
    LIMIT 1
    '''

    # Ejecutar la consulta SQL
    cursor.execute(consulta, (numeroSerie,))
    resultado = cursor.fetchone()  # Obtener un solo resultado

    conn.close()
    return resultado  # Retorna el resultado si existe, de lo contrario None









@app.route('/nuevo_informe/<numeroSerie>', methods=('GET', 'POST'))
@requiere_rol('editor','Administrador')
def nuevo_informe(numeroSerie):
    if request.method == 'POST':
        fecha_entrada = request.form['fecha_entrada']
        fecha_salida = request.form['fecha_salida']
        contador = request.form['contador']
        observacion = request.form['observacion']
        problema_detectado = request.form['problema_detectado']
        diagnostico_tecnico = request.form['diagnostico_tecnico']
        estado_reparacion = request.form['estado_reparacion']
        
        # Verificar si se subió un archivo
        if 'archivo' not in request.files:
            return "No se ha subido ningún archivo", 400

        archivo = request.files['archivo']

        # Verificar si el archivo tiene un nombre
        if archivo.filename == '':
            return "No se seleccionó ningún archivo", 400

        # Validar que el archivo sea un PDF
        if not archivo.filename.endswith('.pdf'):
            return "El archivo no es un PDF", 400
        
        archivo_binario = archivo.read()
        reporte_fisico = base64.b64encode(archivo_binario).decode('utf-8')
        
        # Aquí podrías almacenar el archivo Base64 en la base de datos
        # Por ejemplo, guardar los datos en la base de datos MySQL o SQLite

        # Devuelve la cadena Base64 como respuesta (puedes usarla según lo necesites)
        # return jsonify({
        #     'mensaje': 'Informe guardado exitosamente',
        #     'archivo_base64': archivo_base64
        # })
        
        if fecha_entrada and fecha_salida and contador and problema_detectado and diagnostico_tecnico and estado_reparacion:
            conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
        
        # Obtener el numeroSerie de la maquina usando numeroSerie
            cursor.execute('SELECT numeroSerie FROM maquina WHERE numeroSerie = ?', (numeroSerie,))
            maquina = cursor.fetchone()
            if maquina is None:
            # Manejar el caso donde numeroSerie no existe
                flash('Error: Máquina no encontrada')
            numeroSerie = maquina[0]
        
        # Insertar el nuevo informe
            cursor.execute('''
                INSERT INTO Informe (fecha_entrada, fecha_salida, contador, observacion, problema_detectado, diagnostico_tecnico, estado_reparacion, numeroSerie, reporte_fisico) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fecha_entrada, fecha_salida, contador, observacion,  problema_detectado, diagnostico_tecnico, estado_reparacion, numeroSerie, reporte_fisico))
        
            conn.commit()
            conn.close()
        
            return redirect(url_for('maquina', numeroSerie=numeroSerie))
        else:
            flash('!!! Rellene todos los campos !!!')

    
    return render_template('nuevo_informe.html', numeroSerie=numeroSerie)


@app.route('/buscar', methods=['POST'])
@requiere_rol('lector','editor','Administrador')
def search():
    conn = sqlite3.connect('taller.db')  # Asegúrate de usar el nombre correcto de tu archivo SQLite
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Consulta SQL para buscar por número de serie
    consulta = '''
    SELECT maquina.*, cliente.nombre, cliente.apellido, cliente.correo, cliente.telefono
    FROM maquina 
    JOIN cliente ON maquina.rut = cliente.rut 
    WHERE maquina.numeroSerie = ?
    '''

    numero = request.form['numero']  # Obtener el número de serie desde el formulario
    cursor.execute(consulta, (numero,))
    resultado = cursor.fetchone()  # Solo obtenemos un resultado ya que estamos buscando por un número único
    conn.close()

    if not resultado:
        flash('No se encontró ninguna máquina con ese número de serie.')
        return redirect(url_for('clientes'))  # O redirigir a la página que desees

    return render_template('buscar.html', consulta=resultado)  # Pasamos el resultado a la plantilla


@app.route('/buscar2', methods=['POST'])
@requiere_rol('lector','editor','Administrador')
def search2():
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Obtener el valor del formulario (RUT)
    data = request.get_json()  # Cambiado para manejar datos JSON
    rut = data.get('rut')
    #manejo error 
    if not rut:
        return jsonify({'error': 'RUT no proporcionado'}), 400

    # Consulta SQL para buscar un cliente por RUT
    consulta = '''
    SELECT cliente.rut, cliente.nombre, cliente.apellido, cliente.correo, cliente.telefono
    FROM cliente
    WHERE cliente.rut LIKE ?
    LIMIT 1
    '''

    # Ejecutar la consulta SQL
    cursor.execute(consulta, (f'%{rut}%',))
    resultado = cursor.fetchone()  # Obtener un solo resultado

    conn.close()

    # Procesar el resultado y devolverlo como JSON
    if resultado:
        cliente = {
            'rut': resultado['rut'],
            'nombre': resultado['nombre'],
            'apellido': resultado['apellido'],
            'correo': resultado['correo'],
            'telefono': resultado['telefono']
        }
        return jsonify({'existe': True, 'cliente': cliente})
    else:
        print('no hay')
        return jsonify({'existe': False})  # Cliente no encontrado
       
       

@app.route('/descargar_pdf/<int:idInforme>', methods=['GET'])
def descargar_pdf(idInforme):
    
    # Ruta para guardar archivos generados temporalmente
    TEMP_FOLDER = "archivos_temp"
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    # Recuperar el contenido Base64 desde la base de datos
    conn = sqlite3.connect('taller.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT reporte_fisico FROM informe WHERE idInforme = ?", (idInforme,))
    archivo = cursor.fetchone()
    conn.close()
    
    if not archivo:
        return jsonify({"error": "Archivo no encontrado"}), 404
    
    base64_content = archivo['reporte_fisico']
    
    try:
        # Decodificar el Base64 a binario
        pdf_content = base64.b64decode(base64_content)
        
        # Guardar temporalmente el archivo PDF
        pdf_path = os.path.join(TEMP_FOLDER)
        with open(pdf_path, "wb") as pdf_file:
            pdf_file.write(pdf_content)
        
        # Enviar el archivo como descarga
        return send_file(pdf_path, as_attachment=True)
    
    except Exception as e:
        return jsonify({"error": f"Error al procesar el archivo: {e}"}), 500







if __name__ == '__main__':
    app.run(debug=True , host='0.0.0.0')
