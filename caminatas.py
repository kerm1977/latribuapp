from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_file
from functools import wraps
from datetime import datetime, date, time # Importar time para manejar horas
import os
import json
# from werkzeug.utils import secure_filename # COMENTADO: Ya no usaremos secure_filename directamente
from sqlalchemy import desc, func
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io # Importar io para manejar datos en memoria
from bs4 import BeautifulSoup # Importar BeautifulSoup para eliminar etiquetas HTML
import pytz # Importar pytz para manejo de zonas horarias
import locale # NUEVO: Importar módulo locale
from flask_wtf.csrf import generate_csrf # Añade esta línea
from sqlalchemy.exc import IntegrityError # NUEVO: Importar IntegrityError para manejar errores de integridad
import re # NUEVO: Importar re para expresiones regulares
from btns import load_button_config

# Intenta configurar el locale para español.
# La cadena exacta puede variar según el sistema operativo (Linux, Windows, macOS).
# Se prueban varias opciones comunes para asegurar que el nombre del mes se muestre en español.
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8') # Para sistemas Unix/Linux
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES') # Otra opción para Unix/Linux
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'Spanish_Spain.1252') # Para Windows
        except locale.Error:
            print("Advertencia: No se pudo configurar el locale a español. Las fechas podrían no mostrarse correctamente.")


# Importa db, User, Caminata, AbonoCaminata, caminata_participantes, Itinerario Y AHORA Instruction desde models.py
# Es CRUCIAL que db y los modelos se importen desde models.py
from models import db, User, Caminata, AbonoCaminata, caminata_participantes, Itinerario, Instruction # <--- MODIFICADO: Añade Instruction aquí

caminatas_bp = Blueprint('caminatas', __name__)

# Definir la zona horaria de Costa Rica
COSTA_RICA_TZ = pytz.timezone('America/Costa_Rica')
UTC_TZ = pytz.utc


# --- Decoradores ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """
    Decorador para restringir el acceso a rutas basadas en roles.
    """
    if not isinstance(roles, list):
        roles = [roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session['logged_in']:
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                return redirect(url_for('login'))
            
            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        if 'role' not in session or session['role'] != 'Superuser': # Asume que 'Superuser' es el rol de administrador
            flash('Acceso denegado: Se requiere rol de administrador.', 'danger')
            return redirect(url_for('home')) # Redirige a una página de inicio o de acceso denegado
        return f(*args, **kwargs)
    return decorated_function

# --- Funciones Auxiliares para Nombres de Archivo ---
def is_valid_filename(filename):
    """
    Valida si el nombre del archivo contiene caracteres especiales no permitidos.
    Caracteres no permitidos: #<>!$%&/=?¡'"¿°|
    """
    invalid_chars_pattern = r'[#<>!$%&/=?¡\'"¿°|]'
    if re.search(invalid_chars_pattern, filename):
        return False
    return True

def generate_unique_filename(original_filename, upload_folder):
    """
    Genera un nombre de archivo único, manteniendo el nombre original si es posible,
    o añadiendo un número consecutivo si ya existe.
    """
    filename_base, extension = os.path.splitext(original_filename)
    counter = 1
    unique_filename = original_filename
    while os.path.exists(os.path.join(upload_folder, unique_filename)):
        unique_filename = f"{filename_base}_{counter}{extension}"
        counter += 1
    return unique_filename

# --- Rutas de Caminatas ---

@caminatas_bp.route('/ver_caminatas')
def ver_caminatas():
    all_caminatas = Caminata.query.order_by(Caminata.fecha.desc()).all()
    search_actividad = request.args.get('actividad')

    if search_actividad:
        caminatas = Caminata.query.filter_by(actividad=search_actividad).all()
    else:
        caminatas = Caminata.query.all()

    return render_template(
        'ver_caminatas.html', 
        caminatas=caminatas, 
        search_actividad=search_actividad
    )
  
# Ruta para crear una nueva caminata
@caminatas_bp.route('/crear_caminata', methods=['GET', 'POST'])
@login_required
def crear_caminata():
    if request.method == 'POST':
        nombre = request.form['nombre']
        actividad = request.form['actividad']
        etapa = request.form.get('etapa') 
        
        # --- INICIO DE LA MODIFICACIÓN ---
        moneda = request.form.get('moneda', 'CRC') # Obtener la moneda del formulario
        # --- FIN DE LA MODIFICACIÓN ---

        # --- Manejo de campos numéricos y de fecha con validación ---
        try:
            precio = float(request.form['precio']) if request.form['precio'] else 0.0 # Manejo de cadena vacía
        except ValueError:
            flash('El precio debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        fecha_str = request.form['fecha']
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido. Utilice AAAA-MM-DD.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        try:
            distancia = float(request.form['distancia']) if request.form.get('distancia') else None
        except ValueError:
            flash('La distancia debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        try:
            altura_maxima = float(request.form['altura_maxima']) if request.form.get('altura_maxima') else None
        except ValueError:
            flash('La altura máxima debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        try:
            altura_minima = float(request.form['altura_minima']) if request.form.get('altura_minima') else None
        except ValueError:
            flash('La altura mínima debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        try:
            altura_positiva = float(request.form['altura_positiva']) if request.form.get('altura_positiva') else None
        except ValueError:
            flash('La altura positiva debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))

        try:
            altura_negativa = float(request.form['altura_negativa']) if request.form.get('altura_negativa') else None
        except ValueError:
            flash('La altura negativa debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.crear_caminata'))
        # --- Fin Manejo de campos numéricos y de fecha con validación ---

        # NUEVO: Manejo de campos de hora y duración
        hora_salida_str = request.form.get('hora_salida')
        hora_salida = None
        if hora_salida_str:
            try:
                hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()
            except ValueError:
                flash('Formato de Hora de Salida inválido. Utilice HH:MM.', 'danger')
                return redirect(url_for('caminatas.crear_caminata'))

        hora_regreso_str = request.form.get('hora_regreso')
        hora_regreso = None
        if hora_regreso_str:
            try:
                hora_regreso = datetime.strptime(hora_regreso_str, '%H:%M').time()
            except ValueError:
                flash('Formato de Hora de Regreso inválido. Utilice HH:MM.', 'danger')
                return redirect(url_for('caminatas.crear_caminata'))

        duracion_horas = None
        duracion_horas_str = request.form.get('duracion_horas')
        if duracion_horas_str:
            try:
                duracion_horas = float(duracion_horas_str)
            except ValueError:
                flash('La Duración (horas) debe ser un número válido.', 'danger')
                return redirect(url_for('caminatas.crear_caminata'))
        # FIN NUEVO

        dificultad = request.form.get('dificultad')
        capacidad_minima = request.form['capacidad_minima'] if request.form.get('capacidad_minima') else None
        capacidad_maxima = request.form['capacidad_maxima'] if request.form.get('capacidad_maxima') else None
        otros_datos_ckeditor = request.form.get('otros_datos_ckeditor')

        lugar_salida = request.form.get('lugar_salida')
        provincia = request.form.get('provincia')
        tipo_terreno = request.form.getlist('tipo_terreno') 
        tipo_transporte = request.form.getlist('tipo_transporte') 
        incluye = request.form.getlist('incluye') 
        tipo_clima = request.form.get('tipo_clima')


        imagen_caminata_url = None
        if 'imagen_caminata' in request.files:
            file = request.files['imagen_caminata']
            if file.filename != '':
                # NUEVO: Validar caracteres en el nombre del archivo original
                if not is_valid_filename(file.filename):
                    flash('El nombre del archivo contiene caracteres especiales no permitidos (#, <, >, !, $, %, &, /, =, ?, ¡, \', ", ¿, °, |). Por favor, renombra el archivo.', 'danger')
                    return redirect(url_for('caminatas.crear_caminata'))

                # MODIFICADO: Usar generate_unique_filename para manejar nombres originales y duplicados
                filename = generate_unique_filename(file.filename, current_app.config['CAMINATA_IMAGE_UPLOAD_FOLDER'])
                upload_folder = current_app.config['CAMINATA_IMAGE_UPLOAD_FOLDER'] # Usar la ruta de config
                os.makedirs(upload_folder, exist_ok=True) 
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                imagen_caminata_url = os.path.join('uploads', 'caminatas', filename).replace("\\", "/")

        nueva_caminata = Caminata(
            nombre=nombre,
            actividad=actividad,
            etapa=etapa, 
            moneda=moneda, # Añadir moneda al crear el objeto
            precio=precio,
            fecha=fecha,
            dificultad=dificultad,
            distancia=distancia,
            capacidad_minima=capacidad_minima,
            capacidad_maxima=capacidad_maxima,
            altura_maxima=altura_maxima,
            altura_minima=altura_minima,
            altura_positiva=altura_positiva,
            altura_negativa=altura_negativa,
            otros_datos=otros_datos_ckeditor,
            imagen_caminata_url=imagen_caminata_url,
            lugar_salida=lugar_salida,
            provincia=provincia,
            tipo_terreno=json.dumps(tipo_terreno), 
            tipo_transporte=json.dumps(tipo_transporte), 
            incluye=json.dumps(incluye), 
            tipo_clima=tipo_clima,
            # NUEVO: Asignar valores de hora y duración
            hora_salida=hora_salida,
            hora_regreso=hora_regreso,
            duracion_horas=duracion_horas
            # FIN NUEVO
        )
        db.session.add(nueva_caminata)
        db.session.commit()
        flash('Caminata creada exitosamente!', 'success')
        return redirect(url_for('caminatas.ver_caminatas'))
    
    actividad_opciones = [
        "El Camino de Costa Rica",
        "Parque Nacional",
        "Paseo",
        "Iniciante",
        "Básico",
        "Intermedio",
        "Dificil",
        "Avanzado",
        "Técnico"
    ]
    etapa_opciones = [
        "Etapa 1a - Parismina a Laguna Perlas 5.13k",
        "Etapa 1b - Muelle Goshen a Cimarrones 24.02k",
        "Etapa 2 - Cimarrones a Brisas 15.09k",
        "Etapa 3 - Brisas de Pacuarito a Tsiobata 15.05k",
        "Etapa 4 - Tsiobata a Tres Equis 6.85k",
        "Etapa 5 - Tres Equis a Pacayitas 13.30k",
        "Etapa 6 - Pacayitas a La Suiza 12.58k",
        "Etapa 7 - La Suiza a Humo de Pejibaye",
        "Etapa 8 - Humo de Pejibaye a Tapanti 16.58k",
        "Etapa 9 - Tapanti a Navarro del Muneco 24.40k",
        "Etapa 10 - Navarro del Muneco a Palo Verde",
        "Etapa 11 - Palo Verde a Cerro Alto 8.90k",
        "Etapa 12 - Cerro Alto a San Pablo de Leon Cortes 18.28k",
        "Etapa 13 - San Pablo de Leon Cortes a Napoles 16.41k",
        "Etapa 14 - Napoles a Naranjillo 13.35k",
        "Etapa 15 - Naranjillo a Esquipulas 12.01k",
        "Etapa 16 - Esquipulas a Quepos 22.72k",
        "--------------",
        "Etapas 1a & 1b / 29.32k",
        "Etapas 3 & 4 / 21.09k",
        "Etapas 14 & 15 / 25.36k"
    ]
    lugar_salida_opciones = [
        "Parque De Tres Ríos - Escuela",
        "Parque De Tres Ríos - Cruz Roja",
        "Parque De Tres Ríos - Letras",
        "Plaza de San Diego",
        "Iglesia San Diego"
    ]
    dificultad_opciones = [
        "Iniciante",
        "Básico",
        "Intermedio",
        "Avanzado",
        "Técnico"
    ]
    provincia_opciones = [
        "Cartago",
        "Alajuela",
        "Heredia",
        "San José",
        "Puntarenas",
        "Guanacaste",
        "Limón"
    ]
    tipo_terreno_opciones = [
        "Asfalto llano",
        "Asfalto Pendiente Básico",
        "Asfalto Pendiente Medio",
        "Asfalto Pendiente Difícil",
        "Lastre Pendiente Básico",
        "Lastre Pendiente Medio",
        "Lastre Pendiente Difícil",
        "Sendero Pendiente Básico",
        "Sendero Pendiente Medio",
        "Sendero Pendiente Difícil",
        "Montaña Pendiente Básico",
        "Montaña Pendiente Medio",
        "Montaña Pendiente Difícil",
        "Montaña Técnica",
        "Otros(Otras Señas de Terreno)"
    ]
    tipo_transporte_opciones = [
        "Moto",
        "Bus Público",
        "Buseta",
        "Automobil",
        "Lancha",
        "Ferry",
        "Avion"
    ]
    incluye_opciones = [
        "Transporte",
        "Transporte y Entrada",
        "Transporte y Guía",
        "Transporte y Alimentación",
        "Transporte, Entrada y Guía",
        "Transporte, Entrada y Alimentación",
        "Transporte, y Alimentación",
        "Transporte, Guía y Alimentación",
        "Todo menos Alimentación"
    ]
    tipo_clima_opciones = [
        "Clima Tropical Húmedo",
        "Clima Tropical Seco",
        "Clima Tropical Muy Húmedo",
        "Clima de Montaña"
    ]

    return render_template('crear_caminatas.html', 
                           actividad_opciones=actividad_opciones,
                           etapa_opciones=etapa_opciones, 
                           lugar_salida_opciones=lugar_salida_opciones,
                           dificultad_opciones=dificultad_opciones,
                           provincia_opciones=provincia_opciones,
                           tipo_terreno_opciones=tipo_terreno_opciones,
                           tipo_transporte_opciones=tipo_transporte_opciones,
                           incluye_opciones=incluye_opciones,
                           tipo_clima_opciones=tipo_clima_opciones
                           )

# Ruta para ver el detalle de una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>')
# @login_required # Comentado para permitir ver detalles sin login, puedes descomentar si lo necesitas
def detalle_caminata(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    usuarios_registrados = User.query.all()

    # Preparar los datos de acompañantes y estado de abono para cada participante
    participantes_con_info = []

    for participant in caminata.participantes:
        ultimo_abono = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).order_by(desc(AbonoCaminata.fecha_abono)).first()

        estado_abono = ultimo_abono.opcion if ultimo_abono else None

        companion_names_for_participant = set()
        abonos_del_participante = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).all()
        for abono in abonos_del_participante:
            if abono.nombres_acompanantes:
                try:
                    names_list = json.loads(abono.nombres_acompanantes)
                    for name in names_list:
                        if name.strip():
                            companion_names_for_participant.add(name.strip())
                except json.JSONDecodeError:
                    print(f"Advertencia: No se pudo decodificar JSON para nombres_acompanantes: {abono.nombres_acompanantes}")
                    pass

        participantes_con_info.append({
            'id': participant.id,
            'nombre': participant.nombre,
            'primer_apellido': participant.primer_apellido,
            'username': participant.username,
            'email': participant.email,
            'telefono': participant.telefono,
            'estado_abono': estado_abono,
            'acompanantes': list(companion_names_for_participant)
        })

    return render_template(
        'detalle_caminatas.html',
        caminata=caminata,
        usuarios_registrados=usuarios_registrados,
        participantes_con_info=participantes_con_info,
        csrf_token=generate_csrf() # Añade esta línea
    )


# Ruta para editar una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_caminata(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)

    if request.method == 'POST':
        caminata.nombre = request.form['nombre']
        caminata.actividad = request.form['actividad']
        caminata.etapa = request.form.get('etapa') 
        
        # --- INICIO DE LA MODIFICACIÓN ---
        caminata.moneda = request.form.get('moneda', 'CRC') # Actualizar la moneda
        # --- FIN DE LA MODIFICACIÓN ---

        # --- Manejo de campos numéricos y de fecha con validación en edición ---
        try:
            caminata.precio = float(request.form['precio']) if request.form['precio'] else 0.0
        except ValueError:
            flash('El precio debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        fecha_str = request.form['fecha']
        try:
            caminata.fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido. Utilice AAAA-MM-DD.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        try:
            distancia = float(request.form['distancia']) if request.form.get('distancia') else None
        except ValueError:
            flash('La distancia debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        try:
            altura_maxima = float(request.form['altura_maxima']) if request.form.get('altura_maxima') else None
        except ValueError:
            flash('La altura máxima debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        try:
            altura_minima = float(request.form['altura_minima']) if request.form.get('altura_minima') else None
        except ValueError:
            flash('La altura mínima debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        try:
            caminata.altura_positiva = float(request.form['altura_positiva']) if request.form.get('altura_positiva') else None
        except ValueError:
            flash('La altura positiva debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

        try:
            caminata.altura_negativa = float(request.form['altura_negativa']) if request.form.get('altura_negativa') else None
        except ValueError:
            flash('La altura negativa debe ser un número válido.', 'danger')
            return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))
        # --- Fin Manejo de campos numéricos y de fecha con validación en edición ---

        # NUEVO: Manejo de campos de hora y duración para edición
        hora_salida_str = request.form.get('hora_salida')
        if hora_salida_str:
            try:
                caminata.hora_salida = datetime.strptime(hora_salida_str, '%H:%M').time()
            except ValueError:
                flash('Formato de Hora de Salida inválido. Utilice HH:MM.', 'danger')
                return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))
        else:
            caminata.hora_salida = None # Si el campo está vacío, establecer a None

        hora_regreso_str = request.form.get('hora_regreso')
        if hora_regreso_str:
            try:
                caminata.hora_regreso = datetime.strptime(hora_regreso_str, '%H:%M').time()
            except ValueError:
                flash('Formato de Hora de Regreso inválido. Utilice HH:MM.', 'danger')
                return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))
        else:
            caminata.hora_regreso = None # Si el campo está vacío, establecer a None

        duracion_horas_str = request.form.get('duracion_horas')
        if duracion_horas_str:
            try:
                caminata.duracion_horas = float(duracion_horas_str)
            except ValueError:
                flash('La Duración (horas) debe ser un número válido.', 'danger')
                return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))
        else:
            caminata.duracion_horas = None # Si el campo está vacío, establecer a None
        # FIN NUEVO

        caminata.otros_datos = request.form.get('otros_datos_ckeditor')

        lugar_salida = request.form.get('lugar_salida')
        provincia = request.form.get('provincia')
        caminata.tipo_terreno = json.dumps(request.form.getlist('tipo_terreno')) 
        caminata.tipo_transporte = json.dumps(request.form.getlist('tipo_transporte')) 
        caminata.incluye = json.dumps(request.form.getlist('incluye')) 
        caminata.tipo_clima = request.form.get('tipo_clima')


        # Manejo de la imagen
        if 'imagen_caminata' in request.files:
            file = request.files['imagen_caminata']
            if file.filename != '':
                # NUEVO: Validar caracteres en el nombre del archivo original
                if not is_valid_filename(file.filename):
                    flash('El nombre del archivo contiene caracteres especiales no permitidos (#, <, >, !, $, %, &, /, =, ?, ¡, \', ", ¿, °, |). Por favor, renombra el archivo.', 'danger')
                    return redirect(url_for('caminatas.editar_caminata', caminata_id=caminata.id))

                # Eliminar la imagen antigua si existe
                if caminata.imagen_caminata_url:
                    old_image_path = os.path.join(current_app.root_path, 'static', caminata.imagen_caminata_url)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                # MODIFICADO: Usar generate_unique_filename para manejar nombres originales y duplicados
                filename = generate_unique_filename(file.filename, current_app.config['CAMINATA_IMAGE_UPLOAD_FOLDER'])
                upload_folder = current_app.config['CAMINATA_IMAGE_UPLOAD_FOLDER'] # Usar la ruta de config
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                caminata.imagen_caminata_url = os.path.join('uploads', 'caminatas', filename).replace("\\", "/")
        else:
            # Si no se sube nueva imagen, mantener la existente o establecer a None si se borró
            # Asegúrate de que el campo 'current_imagen_caminata_url' se envíe desde el formulario HTML
            # si deseas mantener la imagen existente.
            if request.form.get('current_imagen_caminata_url') == '': 
                caminata.imagen_caminata_url = None

        db.session.commit()
        flash('Caminata actualizada exitosamente!', 'success')
        return redirect(url_for('caminatas.detalle_caminata', caminata_id=caminata.id))
    
    actividad_opciones = [
        "El Camino de Costa Rica",
        "Parque Nacional",
        "Paseo",
        "Iniciante",
        "Básico",
        "Intermedio",
        "Avanzado",
        "Técnico"
    ]
    etapa_opciones = [
        "Etapa 1a - Parismina a Laguna Perlas 5.13k",
        "Etapa 1b - Muelle Goshen a Cimarrones 24.02k",
        "Etapa 2 - Cimarrones a Brisas 15.09k",
        "Etapa 3 - Brisas de Pacuarito a Tsiobata 15.05k",
        "Etapa 4 - Tsiobata a Tres Equis 6.85k",
        "Etapa 5 - Tres Equis a Pacayitas 13.30k",
        "Etapa 6 - Pacayitas a La Suiza 12.58k",
        "Etapa 7 - La Suiza a Humo de Pejibaye",
        "Etapa 8 - Humo de Pejibaye a Tapanti 16.58k",
        "Etapa 9 - Tapanti a Navarro del Muneco 24.40k",
        "Etapa 10 - Navarro del Muneco a Palo Verde",
        "Etapa 11 - Palo Verde a Cerro Alto 8.90k",
        "Etapa 12 - Cerro Alto a San Pablo de Leon Cortes 18.28k",
        "Etapa 13 - San Pablo de Leon Cortes a Napoles 16.41k",
        "Etapa 14 - Napoles a Naranjillo 13.35k",
        "Etapa 15 - Naranjillo a Esquipulas 12.01k",
        "Etapa 16 - Esquipulas a Quepos 22.72k",
        "--------------",
        "Etapas 1a & 1b / 29.32k",
        "Etapas 3 & 4 / 21.09k",
        "Etapas 14 & 15 / 25.36k"
    ]
    lugar_salida_opciones = [
        "Parque De Tres Ríos - Escuela",
        "Parque De Tres Ríos - Cruz Roja",
        "Parque De Tres Ríos - Letras",
        "Plaza de San Diego",
        "Iglesia San Diego"
    ]
    dificultad_opciones = [
        "Iniciante",
        "Básico",
        "Intermedio",
        "Avanzado",
        "Técnico"
    ]
    provincia_opciones = [
        "Cartago",
        "Alajuela",
        "Heredia",
        "San José",
        "Puntarenas",
        "Guanacaste",
        "Limón"
    ]
    tipo_terreno_opciones = [
        "Asfalto llano",
        "Asfalto Pendiente Básico",
        "Asfalto Pendiente Medio",
        "Asfalto Pendiente Difícil",
        "Lastre Pendiente Básico",
        "Lastre Pendiente Medio",
        "Lastre Pendiente Difícil",
        "Sendero Pendiente Básico",
        "Sendero Pendiente Medio",
        "Sendero Pendiente Difícil",
        "Montaña Pendiente Básico",
        "Montaña Pendiente Medio",
        "Montaña Pendiente Difícil",
        "Montaña Técnica",
        "Otros(Otras Señas de Terreno)"
    ]
    tipo_transporte_opciones = [
        "Moto",
        "Bus Público",
        "Buseta",
        "Automobil",
        "Lancha",
        "Ferry",
        "Avion"
    ]
    incluye_opciones = [
        "Transporte",
        "Transporte y Entrada",
        "Transporte y Guía",
        "Transporte y Alimentación",
        "Transporte, Entrada y Guía",
        "Transporte, Entrada y Alimentación",
        "Transporte, y Alimentación",
        "Transporte, Guía y Alimentación",
        "Todo menos Alimentación"
    ]
    tipo_clima_opciones = [
        "Clima Tropical Húmedo",
        "Clima Tropical Seco",
        "Clima Tropical Muy Húmedo",
        "Clima de Montaña"
    ]

    return render_template('editar_caminatas.html', 
                           caminata=caminata,
                           actividad_opciones=actividad_opciones,
                           etapa_opciones=etapa_opciones, 
                           lugar_salida_opciones=lugar_salida_opciones,
                           dificultad_opciones=dificultad_opciones,
                           provincia_opciones=provincia_opciones,
                           tipo_terreno_opciones=tipo_terreno_opciones,
                           tipo_transporte_opciones=tipo_transporte_opciones,
                           incluye_opciones=incluye_opciones,
                           tipo_clima_opciones=tipo_clima_opciones
                           )

# Ruta para eliminar una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>/eliminar', methods=['POST'])
@login_required
@admin_required # Solo administradores pueden eliminar caminatas
def eliminar_caminata(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    try:
        # Paso 1: Eliminar todas las instrucciones asociadas a esta caminata.
        # Esto es crucial porque 'instruction.caminata_id' es NOT NULL.
        # Usa .delete(synchronize_session=False) para evitar problemas si el objeto 'caminata'
        # ya ha cargado las relaciones de 'instructions' en la sesión.
        Instruction.query.filter_by(caminata_id=caminata.id).delete(synchronize_session=False) # <--- AÑADIR/MODIFICAR ESTA LÍNEA
        
        # Paso 2: Eliminar todos los itinerarios asociados a esta caminata
        # Esto es crucial porque itinerario.caminata_id es NOT NULL
        Itinerario.query.filter_by(caminata_id=caminata.id).delete(synchronize_session=False)
        
        # Paso 3: Eliminar abonos asociados primero para evitar errores de restricción de clave externa
        # MODIFICADO: Eliminar abonos para la caminata sin filtrar por un participante específico
        AbonoCaminata.query.filter_by(caminata_id=caminata.id).delete(synchronize_session=False)
        
        # Paso 4: Eliminar las asociaciones en la tabla intermedia caminata_participantes
        # Esto se hace vaciando la lista de participantes de la caminata
        # Nota: Si usas cascade="all, delete-orphan" en la relación en models.py,
        # esta línea podría no ser estrictamente necesaria para la eliminación,
        # pero es una forma explícita de desvincular.
        caminata.participantes = [] 

        # Paso 5: Eliminar la caminata
        db.session.delete(caminata)
        db.session.commit()
        flash('Caminata y sus datos asociados (instrucciones, itinerarios, abonos, participantes) eliminados exitosamente.', 'success') # <--- MENSAJE MODIFICADO
    except IntegrityError as e:
        db.session.rollback()
        # Este error es menos probable ahora, pero se mantiene por si hay otras restricciones
        flash(f'Error de integridad al eliminar la caminata: No se pudieron eliminar registros asociados. Detalles: {e}', 'danger')
        current_app.logger.error(f"IntegrityError al eliminar caminata {caminata_id}: {e}")
    except Exception as e:
        db.session.rollback()
        flash(f'Error inesperado al eliminar la caminata: {str(e)}', 'danger')
        current_app.logger.error(f"Error general al eliminar caminata {caminata_id}: {e}")
    return redirect(url_for('caminatas.ver_caminatas'))

# Ruta para añadir/quitar participantes de una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>/participantes', methods=['POST'])
@login_required
def gestionar_participantes(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)

    if 'add_participant' in request.form:
        user_id = request.form['user_id']
        participante = User.query.get_or_404(user_id)
        if participante not in caminata.participantes:
            caminata.participantes.append(participante)
            db.session.commit()
            flash(f'{participante.nombre} {participante.primer_apellido} ha sido añadido como participante.', 'success')
        else:
            flash(f'{participante.nombre} {participante.primer_apellido} ya es participante de esta caminata.', 'info')
    
    elif 'remove_participant' in request.form:
        user_id = request.form['user_id']
        participante = User.query.get_or_404(user_id)
        if participante in caminata.participantes:
            caminata.participantes.remove(participante)
            # También eliminar todos los abonos de este participante para esta caminata
            AbonoCaminata.query.filter_by(caminata_id=caminata.id, user_id=participante.id).delete()
            db.session.commit()
            flash(f'{participante.nombre} {participante.primer_apellido} ha sido eliminado de los participantes y todos sus abonos para esta caminata han sido borrados.', 'success')
        else:
            flash(f'{participante.nombre} {participante.primer_apellido} no es participante de esta caminata.', 'info')
            
    return redirect(url_for('caminatas.detalle_caminata', caminata_id=caminata.id))


# --- INICIO DE LA MODIFICACIÓN: RUTA DE ABONOS ---
@caminatas_bp.route('/caminatas/<int:caminata_id>/abono/<int:user_id>', methods=['GET', 'POST'])
@login_required
def abono_caminata(caminata_id, user_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    participante = User.query.get_or_404(user_id)
    
    abonos = AbonoCaminata.query.filter_by(caminata_id=caminata.id, user_id=participante.id).order_by(desc(AbonoCaminata.fecha_abono)).all()
    
    # Convertir las fechas de los abonos a la zona horaria de Costa Rica para mostrar
    for abono in abonos:
        if abono.fecha_abono.tzinfo is None:
            abono.fecha_abono = UTC_TZ.localize(abono.fecha_abono)
        abono.fecha_abono = abono.fecha_abono.astimezone(COSTA_RICA_TZ)

    # --- Cálculos de totales para doble moneda ---
    total_abonado_crc = sum(abono.monto_abono_crc for abono in abonos if abono.monto_abono_crc)
    total_abonado_usd = sum(abono.monto_abono_usd for abono in abonos if abono.monto_abono_usd)
    
    ultima_cantidad_acompanantes = abonos[0].cantidad_acompanantes if abonos else 0
    total_personas = 1 + ultima_cantidad_acompanantes
    total_a_pagar_crc = (caminata.precio or 0) * total_personas
    
    total_abonado_consolidado_crc = total_abonado_crc
    for abono in abonos:
        if abono.monto_abono_usd and abono.tipo_cambio_bcr:
            total_abonado_consolidado_crc += abono.monto_abono_usd * abono.tipo_cambio_bcr

    monto_restante_crc = total_a_pagar_crc - total_abonado_consolidado_crc
    
    ultimo_tipo_cambio = next((abono.tipo_cambio_bcr for abono in reversed(abonos) if abono.tipo_cambio_bcr), None)
    monto_restante_usd = (monto_restante_crc / ultimo_tipo_cambio) if ultimo_tipo_cambio else 0

    if request.method == 'POST':
        if 'add_abono' in request.form:
            try:
                opcion = request.form.get('opcion') 
                cantidad_acompanantes = int(request.form.get('cantidad_acompanantes', 0))
                
                monto_abono_crc_str = request.form.get('monto_abono_crc')
                monto_abono_usd_str = request.form.get('monto_abono_usd')
                tipo_cambio_bcr_str = request.form.get('tipo_cambio_bcr')

                monto_abono_crc = float(monto_abono_crc_str) if monto_abono_crc_str else 0.0
                monto_abono_usd = float(monto_abono_usd_str) if monto_abono_usd_str else 0.0
                tipo_cambio_bcr = float(tipo_cambio_bcr_str) if tipo_cambio_bcr_str else None

                nombres_acompanantes_raw = request.form.get('nombres_acompanantes_raw', '')
                nombres_acompanantes_list = [name.strip() for name in nombres_acompanantes_raw.split(',') if name.strip()]
                nombres_acompanantes_json = json.dumps(nombres_acompanantes_list, ensure_ascii=False)

                if not opcion:
                    flash('Por favor, selecciona una opción (Abono, Reserva, Cancelación).', 'danger')
                    return redirect(url_for('caminatas.abono_caminata', caminata_id=caminata.id, user_id=participante.id))

                nuevo_abono = AbonoCaminata(
                    caminata_id=caminata.id,
                    user_id=participante.id,
                    opcion=opcion, 
                    cantidad_acompanantes=cantidad_acompanantes,
                    monto_abono_crc=monto_abono_crc,
                    monto_abono_usd=monto_abono_usd,
                    tipo_cambio_bcr=tipo_cambio_bcr,
                    fecha_abono=datetime.utcnow(),
                    nombres_acompanantes=nombres_acompanantes_json
                )
                db.session.add(nuevo_abono)
                db.session.commit()
                flash('Abono registrado exitosamente.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error al registrar el abono: {e}', 'danger')
                current_app.logger.error(f"Error en abono_caminata (POST): {e}")

            return redirect(url_for('caminatas.abono_caminata', caminata_id=caminata.id, user_id=participante.id))
        
        elif 'delete_abono' in request.form:
            abono_id = request.form.get('abono_id')
            if abono_id:
                abono_to_delete = AbonoCaminata.query.get(abono_id)
                if abono_to_delete and abono_to_delete.caminata_id == caminata.id and abono_to_delete.user_id == participante.id:
                    db.session.delete(abono_to_delete)
                    db.session.commit()
                    flash('Abono eliminado exitosamente.', 'success')
                else:
                    flash('Error: Abono no encontrado o no corresponde a este participante/caminata.', 'danger')
            else:
                flash('Error: No se especificó el abono a eliminar.', 'danger')
            return redirect(url_for('caminatas.abono_caminata', caminata_id=caminata.id, user_id=participante.id))

    return render_template(
        'abono_caminatas.html', 
        caminata=caminata, 
        participante=participante, 
        abonos=abonos, 
        total_abonado_crc=total_abonado_crc,
        total_abonado_usd=total_abonado_usd,
        monto_restante_crc=monto_restante_crc,
        monto_restante_usd=monto_restante_usd
    )
# --- FIN DE LA MODIFICACIÓN ---


# --- INICIO NUEVA SECCIÓN: LÓGICA DE EXPORTACIÓN DE FACTURAS ---

def _get_invoice_data_as_text(caminata, participante, abonos):
    """
    Genera una cadena de texto con los detalles de la factura,
    replicando la lógica de la plantilla y omitiendo valores vacíos.
    """
    lines = []

    def should_display(value):
        """Función auxiliar para determinar si un valor debe mostrarse."""
        if value is None:
            return False
        if isinstance(value, str) and (value.strip() == '' or value.strip().upper() == 'N/A'):
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        return True

    # --- Cálculos de la factura (replicando la lógica de la plantilla) ---
    price = float(caminata.precio or 0)
    paid_crc_from_db = sum(a.monto_abono_crc for a in abonos if a.monto_abono_crc)
    paid_usd_from_db = sum(a.monto_abono_usd for a in abonos if a.monto_abono_usd)
    exchange_rate = 0
    if abonos and abonos[0].tipo_cambio_bcr:
        exchange_rate = float(abonos[0].tipo_cambio_bcr)

    price_in_crc = 0
    remaining_usd = 0
    if caminata.moneda == 'USD':
        if exchange_rate > 0:
            price_in_crc = price * exchange_rate
        remaining_usd = price - paid_usd_from_db
    else: # Moneda es CRC
        price_in_crc = price
        remaining_usd = 0 - paid_usd_from_db

    total_paid_in_crc = paid_crc_from_db
    if exchange_rate > 0:
         total_paid_in_crc += (paid_usd_from_db * exchange_rate)

    remaining_crc = price_in_crc - total_paid_in_crc

    is_cancelled = False
    if caminata.moneda == 'USD':
        if price_in_crc > 0 and total_paid_in_crc >= price_in_crc:
            is_cancelled = True
        elif paid_usd_from_db >= price:
            is_cancelled = True
    else: # Moneda es CRC
        if total_paid_in_crc >= price:
            is_cancelled = True
    
    # --- Construcción del texto de la factura ---
    lines.append("FACTURA DE CAMINATA")
    lines.append("="*30)
    
    # Datos de la Caminata
    if should_display(caminata.nombre): lines.append(f"Caminata: {caminata.nombre}")
    if caminata.fecha: lines.append(f"Fecha: {caminata.fecha.strftime('%d-%m-%Y')}")
    if should_display(caminata.actividad): lines.append(f"Actividad: {caminata.actividad}")
    if should_display(caminata.dificultad): lines.append(f"Dificultad: {caminata.dificultad}")
    if should_display(caminata.distancia): lines.append(f"Distancia: {caminata.distancia} km")
    lines.append("")

    # Datos del Participante
    lines.append(f"Participante: {participante.nombre} {participante.primer_apellido}")
    lines.append("")
    lines.append("--- Resumen Financiero ---")
    
    # Resumen Financiero
    if should_display(price): lines.append(f"Precio por Persona: {'$' if caminata.moneda == 'USD' else '¢'}{price:,.0f}")
    if should_display(total_paid_in_crc): lines.append(f"Total Abonado CRC: ¢{total_paid_in_crc:,.0f}")
    if should_display(paid_usd_from_db): lines.append(f"Total Abonado USD: ${paid_usd_from_db:,.0f}")

    if is_cancelled:
        lines.append("Monto Restante: CANCELADO")
    else:
        if should_display(remaining_crc): lines.append(f"Monto Restante CRC: ¢{remaining_crc:,.0f}")
        if should_display(remaining_usd): lines.append(f"Monto Restante USD: ${remaining_usd:,.0f}")
    
    lines.append("")
    lines.append("--- Historial de Abonos ---")

    if abonos:
        total_historial_crc = 0
        for abono in abonos:
            # Convertir fecha a zona horaria de Costa Rica
            fecha_abono_cr = abono.fecha_abono
            if fecha_abono_cr.tzinfo is None:
                fecha_abono_cr = UTC_TZ.localize(fecha_abono_cr)
            fecha_abono_cr = fecha_abono_cr.astimezone(COSTA_RICA_TZ)

            lines.append(f"Fecha: {fecha_abono_cr.strftime('%d/%m/%Y %H:%M')}")
            
            crc_val = float(abono.monto_abono_crc or 0)
            usd_val = float(abono.monto_abono_usd or 0)
            tc_val = float(abono.tipo_cambio_bcr or 0)
            display_crc = crc_val + (usd_val * tc_val)
            total_historial_crc += display_crc

            if should_display(abono.opcion): lines.append(f"  Opción: {abono.opcion}")
            if should_display(abono.cantidad_acompanantes): lines.append(f"  Acompañantes: {abono.cantidad_acompanantes}")
            
            if abono.nombres_acompanantes:
                nombres_acom = json.loads(abono.nombres_acompanantes)
                if nombres_acom:
                    lines.append(f"  Detalles: {', '.join(nombres_acom)}")
            
            lines.append(f"  Monto Abonado CRC (calculado): ¢{display_crc:,.0f}")
            if should_display(usd_val): lines.append(f"  Monto Abonado USD (original): ${usd_val:,.0f}")
            if should_display(tc_val): lines.append(f"  T.C. usado: {tc_val}")
            lines.append("-" * 20)

        lines.append("")
        lines.append("--- Totales del Historial ---")
        lines.append(f"Total Historial CRC (calculado): ¢{total_historial_crc:,.0f}")
        lines.append(f"Total Historial USD (original): ${paid_usd_from_db:,.0f}")
    else:
        lines.append("No hay abonos registrados.")

    return "\n".join(lines)


@caminatas_bp.route('/caminatas/<int:caminata_id>/abono/<int:user_id>/export_pdf')
@login_required
def exportar_abono_pdf(caminata_id, user_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    participante = User.query.get_or_404(user_id)
    abonos = AbonoCaminata.query.filter_by(caminata_id=caminata.id, user_id=participante.id).order_by(AbonoCaminata.fecha_abono.asc()).all()

    invoice_text = _get_invoice_data_as_text(caminata, participante, abonos)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    # Usar multi_cell para manejar saltos de línea y texto largo
    pdf.multi_cell(0, 5, invoice_text.encode('latin-1', 'replace').decode('latin-1'))

    pdf_output = pdf.output(dest='S').encode('latin-1')
    response = current_app.make_response(pdf_output)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=factura_{caminata.nombre}_{participante.username}.pdf'
    return response

@caminatas_bp.route('/caminatas/<int:caminata_id>/abono/<int:user_id>/export_jpg')
@login_required
def exportar_abono_jpg(caminata_id, user_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    participante = User.query.get_or_404(user_id)
    abonos = AbonoCaminata.query.filter_by(caminata_id=caminata.id, user_id=participante.id).order_by(AbonoCaminata.fecha_abono.asc()).all()

    invoice_text = _get_invoice_data_as_text(caminata, participante, abonos)
    
    font_size = 20
    font_path = os.path.join(current_app.root_path, 'static', 'fonts', 'arial.ttf')
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()

    # Calcular dimensiones de la imagen
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    lines = invoice_text.split('\n')
    max_line_width = 0
    total_text_height = 0
    
    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1] + 5 # Espacio entre líneas
        max_line_width = max(max_line_width, line_width)
        total_text_height += line_height

    padding = 40
    img_width = int(max_line_width + (2 * padding))
    img_height = int(total_text_height + (2 * padding))
    
    img = Image.new('RGB', (img_width, img_height), color='white')
    d = ImageDraw.Draw(img)

    # Dibujar el texto
    y_offset = padding
    for line in lines:
        d.text((padding, y_offset), line, fill=(0, 0, 0), font=font)
        bbox = d.textbbox((0,0), line, font=font)
        line_height_actual = bbox[3] - bbox[1] + 5
        y_offset += line_height_actual

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    return send_file(img_byte_arr, mimetype='image/jpeg', as_attachment=True, download_name=f'factura_{caminata.nombre}_{participante.username}.jpg')


@caminatas_bp.route('/caminatas/<int:caminata_id>/abono/<int:user_id>/export_txt')
@login_required
def exportar_abono_txt(caminata_id, user_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    participante = User.query.get_or_404(user_id)
    abonos = AbonoCaminata.query.filter_by(caminata_id=caminata.id, user_id=participante.id).order_by(AbonoCaminata.fecha_abono.asc()).all()

    invoice_text = _get_invoice_data_as_text(caminata, participante, abonos)
    
    response = current_app.make_response(invoice_text)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=factura_{caminata.nombre}_{participante.username}.txt'
    return response

# --- FIN NUEVA SECCIÓN ---


# --- RUTAS DE EXPORTACIÓN DE DETALLE DE CAMINATA ---

# Helper para formatear los detalles de la caminata en texto plano
def _get_caminata_details_as_text(caminata, participantes_con_info=None):
    """Genera una cadena de texto con los detalles de la caminata para exportación.
    Incluye información de participantes, sus acompañantes y su estado de abono,
    filtrando los valores 'N/A' y '0'.
    """
    if participantes_con_info is None:
        participantes_con_info = []

    details = []
    
    # --- INICIO DE LA MODIFICACIÓN ---
    currency_symbol = '¢' if caminata.moneda == 'CRC' else '$'
    currency_code = 'CRC' if caminata.moneda == 'CRC' else 'USD'
    # --- FIN DE LA MODIFICACIÓN ---

    def should_exclude(value):
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return True
        if isinstance(value, (int, float)) and value == 0:
            return True
        return False

    if caminata.nombre and not should_exclude(caminata.nombre):
        details.append(f"Detalle de la Caminata: {caminata.nombre}")
        details.append(f"----------------------------------------")

    if caminata.actividad and not should_exclude(caminata.actividad):
        details.append(f"Actividad: {caminata.actividad}")
    if caminata.etapa and not should_exclude(caminata.etapa):
        details.append(f"Etapa: {caminata.etapa}")
    if caminata.precio is not None and not should_exclude(caminata.precio):
        # --- INICIO DE LA MODIFICACIÓN ---
        details.append(f"Precio: {currency_symbol}{caminata.precio:,.0f} {currency_code}")
        # --- FIN DE LA MODIFICACIÓN ---
    if caminata.fecha:
        details.append(f"Fecha: {caminata.fecha.strftime('%d de %B de %Y')}")
    if caminata.hora_salida and not should_exclude(caminata.hora_salida):
        details.append(f"Hora de Salida: {caminata.hora_salida.strftime('%H:%M')}")
    if caminata.hora_regreso and not should_exclude(caminata.hora_regreso):
        details.append(f"Hora de Regreso: {caminata.hora_regreso.strftime('%H:%M')}")
    if caminata.duracion_horas is not None and not should_exclude(caminata.duracion_horas):
        details.append(f"Duración (horas): {caminata.duracion_horas}")
    if caminata.lugar_salida and not should_exclude(caminata.lugar_salida):
        details.append(f"Lugar de Salida: {caminata.lugar_salida}")
    if caminata.dificultad and not should_exclude(caminata.dificultad):
        details.append(f"Dificultad: {caminata.dificultad}")
    if caminata.distancia is not None and not should_exclude(caminata.distancia):
        details.append(f"Distancia: {caminata.distancia} km")
    if caminata.capacidad_minima is not None and not should_exclude(caminata.capacidad_minima):
        details.append(f"Capacidad Mínima: {caminata.capacidad_minima}")
    if caminata.capacidad_maxima is not None and not should_exclude(caminata.capacidad_maxima):
        details.append(f"Capacidad Máxima: {caminata.capacidad_maxima}")
    if caminata.nombre_guia and not should_exclude(caminata.nombre_guia):
        details.append(f"Nombre del Guía: {caminata.nombre_guia}")
    if caminata.se_requiere and not should_exclude(caminata.se_requiere):
        details.append(f"Se Requiere: {caminata.se_requiere}")
    if caminata.provincia and not should_exclude(caminata.provincia):
        details.append(f"Provincia: {caminata.provincia}")
    if caminata.tipo_terreno:
        terreno_list = json.loads(caminata.tipo_terreno)
        if terreno_list and not should_exclude(terreno_list):
            details.append(f"Tipo de Terreno: {', '.join(terreno_list)}")
    if caminata.otras_senas_terreno and not should_exclude(caminata.otras_senas_terreno):
        details.append(f"Otras Señas del Terreno: {caminata.otras_senas_terreno}")
    if caminata.tipo_transporte:
        transporte_list = json.loads(caminata.tipo_transporte)
        if transporte_list and not should_exclude(transporte_list):
            details.append(f"Tipo de Transporte: {', '.join(transporte_list)}")
    if caminata.incluye:
        incluye_list = json.loads(caminata.incluye)
        if incluye_list and not should_exclude(incluye_list):
            details.append(f"Incluye: {', '.join(incluye_list)}")
    if caminata.cuenta_con:
        cuenta_con_list = json.loads(caminata.cuenta_con)
        if cuenta_con_list and not should_exclude(cuenta_con_list):
            details.append(f"Cuenta con: {', '.join(cuenta_con_list)}")
    if caminata.tipo_clima and not should_exclude(caminata.tipo_clima):
        details.append(f"Tipo de Clima: {caminata.tipo_clima}")
    if caminata.altura_maxima is not None and not should_exclude(caminata.altura_maxima):
        details.append(f"Altura Máxima: {caminata.altura_maxima} m")
    if caminata.altura_minima is not None and not should_exclude(caminata.altura_minima):
        details.append(f"Altura Mínima: {caminata.altura_minima} m")
    if caminata.altura_positiva is not None and not should_exclude(caminata.altura_positiva):
        details.append(f"Altura Positiva: {caminata.altura_positiva} m")
    if caminata.altura_negativa is not None and not should_exclude(caminata.altura_negativa):
        details.append(f"Altura Negativa: {caminata.altura_negativa} m")
    if caminata.otros_datos and not should_exclude(caminata.otros_datos):
        clean_otros_datos = BeautifulSoup(caminata.otros_datos, "html.parser").get_text()
        if clean_otros_datos.strip(): 
            details.append(f"\nOtros Datos:\n{clean_otros_datos.strip()}")

    details.append("\n--- Participantes de la Caminata ---")
    if participantes_con_info: 
        participant_counter = 1
        for participant_info in participantes_con_info:
            status_text = ""
            if participant_info.get('estado_abono'):
                if participant_info['estado_abono'] == 'Reserva':
                    status_text = " (Estado: RESERVADO)"
                elif participant_info['estado_abono'] == 'Abono':
                    status_text = " (Estado: ABONO)"
                elif participant_info['estado_abono'] == 'Cancelación':
                    status_text = " (Estado: CANCELADO)"
            
            if (participant_info['nombre'] and not should_exclude(participant_info['nombre'])) and \
               (participant_info['primer_apellido'] and not should_exclude(participant_info['primer_apellido'])) and \
               (participant_info['username'] and not should_exclude(participant_info['username'])):
                details.append(f"  {participant_counter}. {participant_info['nombre']} {participant_info['primer_apellido']} ({participant_info['username']}){status_text}")
                
                if participant_info.get('email') and not should_exclude(participant_info['email']):
                    details.append(f"    Email: {participant_info['email']}")
                if participant_info.get('telefono') and not should_exclude(participant_info['telefono']):
                    details.append(f"    Teléfono: {participant_info['telefono']}")
                
                if participant_info.get('acompanantes'):
                    filtered_companions = [c for c in participant_info['acompanantes'] if c and not should_exclude(c)]
                    if filtered_companions:
                        companion_sub_counter = 1
                        details.append(f"    Acompañante(s) registrado(s) por {participant_info['nombre']}:")
                        for companion_name in filtered_companions:
                            details.append(f"      {companion_sub_counter}. {companion_name}")
                            companion_sub_counter += 1
                participant_counter += 1
    else:
        details.append("No hay participantes registrados para esta caminata aún.")

    return "\n".join(details)


@caminatas_bp.route('/caminatas/exportar/pdf/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_caminata_pdf(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    
    participantes_con_info = []
    for participant in caminata.participantes:
        ultimo_abono = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).order_by(desc(AbonoCaminata.fecha_abono)).first()
        estado_abono = ultimo_abono.opcion if ultimo_abono else None 

        companion_names_for_participant = set()
        abonos_del_participante = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).all()
        for abono in abonos_del_participante:
            if abono.nombres_acompanantes:
                try: 
                    names_list = json.loads(abono.nombres_acompanantes)
                    for name in names_list:
                        if name.strip():
                            companion_names_for_participant.add(name.strip())
                except json.JSONDecodeError:
                    print(f"Advertencia: No se pudo decodificar JSON para nombres_acompanantes en exportación PDF: {abono.nombres_acompanantes}")
                    pass 
        
        participantes_con_info.append({
            'id': participant.id,
            'nombre': participant.nombre,
            'primer_apellido': participant.primer_apellido,
            'username': participant.username,
            'email': participant.email,
            'telefono': participant.telefono,
            'estado_abono': estado_abono,
            'acompanantes': list(companion_names_for_participant)
        })

    caminata_text = _get_caminata_details_as_text(caminata, participantes_con_info) 

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, "Detalles de la Caminata", 0, 1, 'C')
    pdf.ln(10) 

    
    for line in caminata_text.split('\n'):
        if len(line) > 70: 
            pdf.set_font("Arial", size=9)
        elif line.strip().startswith(tuple(str(i) + '.' for i in range(1, 10))):
            pdf.set_font("Arial", 'B', 10) 
        elif line.startswith('    Email:') or line.startswith('    Teléfono:'):
            pdf.set_font("Arial", '', 9)
        elif line.startswith('    Acompañante(s)'):
            pdf.set_font("Arial", 'I', 9)
        elif line.strip().startswith(tuple('      ' + str(i) + '.' for i in range(1, 100))):
            pdf.set_font("Arial", '', 9)
        else:
            pdf.set_font("Arial", size=10)

        pdf.multi_cell(0, 7, line.encode('latin-1', 'replace').decode('latin-1'))
    
    response = current_app.response_class(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename=f'caminata_{caminata.nombre}.pdf')
    return response


@caminatas_bp.route('/caminatas/exportar/txt/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_caminata_txt(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    
    participantes_con_info = []
    for participant in caminata.participantes:
        ultimo_abono = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).order_by(desc(AbonoCaminata.fecha_abono)).first()
        estado_abono = ultimo_abono.opcion if ultimo_abono else None 

        companion_names_for_participant = set()
        abonos_del_participante = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).all()
        for abono in abonos_del_participante:
            if abono.nombres_acompanantes:
                try: 
                    names_list = json.loads(abono.nombres_acompanantes)
                    for name in names_list:
                        if name.strip():
                            companion_names_for_participant.add(name.strip())
                except json.JSONDecodeError:
                    print(f"Advertencia: No se pudo decodificar JSON para nombres_acompanantes en exportación TXT: {abono.nombres_acompanantes}")
                    pass 
        
        participantes_con_info.append({
            'id': participant.id,
            'nombre': participant.nombre,
            'primer_apellido': participant.primer_apellido,
            'username': participant.username,
            'email': participant.email,
            'telefono': participant.telefono,
            'estado_abono': estado_abono,
            'acompanantes': list(companion_names_for_participant)
        })

    caminata_text = _get_caminata_details_as_text(caminata, participantes_con_info) 

    buffer = io.BytesIO()
    buffer.write(caminata_text.encode('utf-8'))
    buffer.seek(0)

    response = current_app.response_class(buffer.getvalue(), mimetype='text/plain')
    response.headers.set('Content-Disposition', 'attachment', filename=f'caminata_{caminata.nombre}.txt')
    return response

@caminatas_bp.route('/caminatas/exportar/jpg/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_caminata_jpg(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    
    participantes_con_info = []
    for participant in caminata.participantes:
        ultimo_abono = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).order_by(desc(AbonoCaminata.fecha_abono)).first()
        estado_abono = ultimo_abono.opcion if ultimo_abono else None 

        companion_names_for_participant = set()
        abonos_del_participante = AbonoCaminata.query.filter_by(
            caminata_id=caminata.id,
            user_id=participant.id
        ).all()
        for abono in abonos_del_participante:
            if abono.nombres_acompanantes:
                try: 
                    names_list = json.loads(abono.nombres_acompanantes)
                    for name in names_list:
                        if name.strip():
                            companion_names_for_participant.add(name.strip())
                except json.JSONDecodeError:
                    print(f"Advertencia: No se pudo decodificar JSON para nombres_acompanantes en exportación JPG: {abono.nombres_acompanantes}")
                    pass 
        
        participantes_con_info.append({
            'id': participant.id,
            'nombre': participant.nombre,
            'primer_apellido': participant.primer_apellido,
            'username': participant.username,
            'email': participant.email,
            'telefono': participant.telefono,
            'estado_abono': estado_abono,
            'acompanantes': list(companion_names_for_participant)
        })

    caminata_text = _get_caminata_details_as_text(caminata, participantes_con_info) 

    temp_img = Image.new('RGB', (1, 1))
    d_temp = ImageDraw.Draw(temp_img)

    font_path = os.path.join(current_app.root_path, 'static', 'fonts', 'arial.ttf')
    try:
        font = ImageFont.truetype(font_path, 18)
        font_small = ImageFont.truetype(font_path, 14) 
        font_bold = ImageFont.truetype(os.path.join(current_app.root_path, 'static', 'fonts', 'arialbd.ttf'), 18)
        font_italic = ImageFont.truetype(os.path.join(current_app.root_path, 'static', 'fonts', 'ariali.ttf'), 14)
    except IOError:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_italic = ImageFont.load_default()
        print(f"ADVERTENCIA: No se encontró la fuente en {font_path}. Usando la fuente por defecto.")

    lines = caminata_text.split('\n')
    
    total_text_height = 0
    max_line_width = 0
    for line in lines:
        current_font = font
        if line.startswith("--- Participantes de la Caminata ---"):
            current_font = font_bold
        elif line.strip().startswith(tuple(str(i) + '.' for i in range(1, 100))): 
            current_font = font_bold
        elif line.startswith("    Email:") or line.startswith("    Teléfono:"):
            current_font = font_small
        elif line.startswith("    Acompañante(s)"):
            current_font = font_italic
        elif line.strip().startswith(tuple('      ' + str(i) + '.' for i in range(1, 100))):
            current_font = font_small

        bbox = d_temp.textbbox((0,0), line, font=current_font)
        line_height = bbox[3] - bbox[1] + 5
        line_width = bbox[2] - bbox[0]
        
        total_text_height += line_height
        if line_width > max_line_width:
            max_line_width = line_width
    
    padding = 30
    img_width = int(max_line_width + (2 * padding))
    img_height = int(total_text_height + (2 * padding))
    
    img = Image.new('RGB', (img_width, img_height), color='white')
    d = ImageDraw.Draw(img)

    y_offset = padding
    for line in lines:
        current_font = font
        if line.startswith("--- Participantes de la Caminata ---"):
            current_font = font_bold
        elif line.strip().startswith(tuple(str(i) + '.' for i in range(1, 100))):
            current_font = font_bold
        elif line.startswith("    Email:") or line.startswith("    Teléfono:"):
            current_font = font_small
        elif line.startswith("    Acompañante(s)"):
            current_font = font_italic
        elif line.strip().startswith(tuple('      ' + str(i) + '.' for i in range(1, 100))):
            current_font = font_small

        d.text((padding, y_offset), line, fill=(0, 0, 0), font=current_font) 
        bbox = d.textbbox((0,0), line, font=current_font)
        line_height_actual = bbox[3] - bbox[1] + 5
        y_offset += line_height_actual

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)

    response = current_app.response_class(buffer.getvalue(), mimetype='image/jpeg')
    response.headers.set('Content-Disposition', 'attachment', filename=f'caminata_{caminata.nombre}.jpg')
    return response

# NUEVA RUTA PARA CAMBIAR EL ESTADO DE LA CAMINATA
@caminatas_bp.route('/caminata/toggle_finalizada/<int:caminata_id>', methods=['POST'])
@role_required(['Superuser'])
def toggle_finalizada(caminata_id):
    """
    Cambia el estado de 'finalizada' de una caminata.
    """
    caminata = Caminata.query.get_or_404(caminata_id)
    caminata.finalizada = not caminata.finalizada
    try:
        db.session.commit()
        estado = "finalizada" if caminata.finalizada else "reactivada"
        flash(f'La caminata "{caminata.nombre}" ha sido marcada como {estado}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar el estado de la caminata: {e}', 'danger')
    
    return redirect(url_for('caminatas.detalle_caminata', caminata_id=caminata.id))

# --- INICIO DEL CÓDIGO RESTAURADO ---

# Ruta para gestionar el itinerario de una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>/itinerario', methods=['GET', 'POST'])
@login_required
def itinerario_caminata(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    if request.method == 'POST':
        # Detectar si se está agregando o eliminando
        if 'add_itinerario' in request.form:
            hora_inicio_str = request.form.get('hora_inicio')
            hora_fin_str = request.form.get('hora_fin')
            actividad = request.form.get('actividad_itinerario') # Cambiado para evitar conflicto
            detalles = request.form.get('detalles')

            # Validación de campos
            if not hora_inicio_str or not actividad:
                flash('La hora de inicio y la actividad son obligatorias.', 'danger')
                return redirect(url_for('caminatas.itinerario_caminata', caminata_id=caminata.id))

            # Conversión de hora
            try:
                hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
                hora_fin = datetime.strptime(hora_fin_str, '%H:%M').time() if hora_fin_str else None
            except ValueError:
                flash('Formato de hora inválido. Use HH:MM.', 'danger')
                return redirect(url_for('caminatas.itinerario_caminata', caminata_id=caminata.id))

            nuevo_item = Itinerario(
                caminata_id=caminata.id,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                actividad=actividad,
                detalles=detalles
            )
            db.session.add(nuevo_item)
            db.session.commit()
            flash('Ítem de itinerario agregado exitosamente.', 'success')

        elif 'delete_itinerario' in request.form:
            itinerario_id = request.form.get('itinerario_id')
            item_a_eliminar = Itinerario.query.get(itinerario_id)
            if item_a_eliminar and item_a_eliminar.caminata_id == caminata.id:
                db.session.delete(item_a_eliminar)
                db.session.commit()
                flash('Ítem de itinerario eliminado.', 'success')
            else:
                flash('Error al eliminar el ítem del itinerario.', 'danger')

        return redirect(url_for('caminatas.itinerario_caminata', caminata_id=caminata.id))

    itinerarios = Itinerario.query.filter_by(caminata_id=caminata.id).order_by(Itinerario.hora_inicio).all()
    return render_template('itinerario_caminata.html', caminata=caminata, itinerarios=itinerarios)

# Ruta para gestionar las instrucciones de una caminata
@caminatas_bp.route('/caminata/<int:caminata_id>/instrucciones', methods=['GET', 'POST'])
@login_required
def instrucciones_caminata(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    if request.method == 'POST':
        if 'add_instruction' in request.form:
            instruccion_texto = request.form.get('instruccion_texto')
            if instruccion_texto:
                nueva_instruccion = Instruction(caminata_id=caminata.id, texto=instruccion_texto)
                db.session.add(nueva_instruccion)
                db.session.commit()
                flash('Instrucción agregada exitosamente.', 'success')
            else:
                flash('El texto de la instrucción no puede estar vacío.', 'danger')
        
        elif 'delete_instruction' in request.form:
            instruccion_id = request.form.get('instruccion_id')
            instruccion_a_eliminar = Instruction.query.get(instruccion_id)
            if instruccion_a_eliminar and instruccion_a_eliminar.caminata_id == caminata.id:
                db.session.delete(instruccion_a_eliminar)
                db.session.commit()
                flash('Instrucción eliminada.', 'success')
            else:
                flash('Error al eliminar la instrucción.', 'danger')
        
        return redirect(url_for('caminatas.instrucciones_caminata', caminata_id=caminata.id))

    instrucciones = Instruction.query.filter_by(caminata_id=caminata.id).all()
    return render_template('instrucciones_caminata.html', caminata=caminata, instrucciones=instrucciones)

# --- Rutas de Exportación para Instrucciones ---
@caminatas_bp.route('/caminatas/exportar_instrucciones/pdf/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_instrucciones_pdf(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    instrucciones = Instruction.query.filter_by(caminata_id=caminata.id).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f'Instrucciones para: {caminata.nombre}', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for i, instruccion in enumerate(instrucciones, 1):
        pdf.multi_cell(0, 10, f'{i}. {instruccion.texto}'.encode('latin-1', 'replace').decode('latin-1'))
    
    response = current_app.response_class(pdf.output(dest='S').encode('latin1'), mimetype='application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename=f'instrucciones_{caminata.nombre}.pdf')
    return response

@caminatas_bp.route('/caminatas/exportar_instrucciones/jpg/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_instrucciones_jpg(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    instrucciones = Instruction.query.filter_by(caminata_id=caminata.id).all()

    text = f"Instrucciones para: {caminata.nombre}\n\n" + "\n".join([f"{i}. {inst.texto}" for i, inst in enumerate(instrucciones, 1)])
    
    font_path = os.path.join(current_app.root_path, 'static', 'fonts', 'arial.ttf')
    try:
        font_title = ImageFont.truetype(font_path.replace('.ttf', 'bd.ttf'), 24)
        font_body = ImageFont.truetype(font_path, 18)
    except IOError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    dummy_img = Image.new('RGB', (1, 1))
    d_temp = ImageDraw.Draw(dummy_img)
    
    lines = text.split('\n')
    max_width = 0
    total_height = 0
    for i, line in enumerate(lines):
        font = font_title if i == 0 else font_body
        bbox = d_temp.textbbox((0,0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1] + 5
        if width > max_width:
            max_width = width
        total_height += height

    padding = 20
    img_width = max_width + 2 * padding
    img_height = total_height + 2 * padding
    
    img = Image.new('RGB', (img_width, img_height), color='white')
    d = ImageDraw.Draw(img)

    y_offset = padding
    for i, line in enumerate(lines):
        font = font_title if i == 0 else font_body
        d.text((padding, y_offset), line, fill=(0, 0, 0), font=font)
        bbox = d.textbbox((0,0), line, font=font)
        y_offset += (bbox[3] - bbox[1] + 5)

    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)

    response = current_app.response_class(buffer.getvalue(), mimetype='image/jpeg')
    response.headers.set('Content-Disposition', 'attachment', filename=f'instrucciones_{caminata.nombre}.jpg')
    return response

@caminatas_bp.route('/caminatas/exportar_instrucciones/txt/<int:caminata_id>', methods=['GET'])
@login_required
def exportar_instrucciones_txt(caminata_id):
    caminata = Caminata.query.get_or_404(caminata_id)
    instrucciones = Instruction.query.filter_by(caminata_id=caminata.id).all()

    text = f"Instrucciones para: {caminata.nombre}\n\n" + "\n".join([f"{i}. {inst.texto}" for i, inst in enumerate(instrucciones, 1)])
    
    buffer = io.BytesIO()
    buffer.write(text.encode('utf-8'))
    buffer.seek(0)

    response = current_app.response_class(buffer.getvalue(), mimetype='text/plain')
    response.headers.set('Content-Disposition', 'attachment', filename=f'instrucciones_{caminata.nombre}.txt')
    return response

# --- Rutas para Botones Dinámicos ---

@caminatas_bp.route('/load_buttons')
@login_required
def load_buttons():
    buttons = load_button_config()
    return render_template('load_buttons.html', buttons=buttons)

@caminatas_bp.route('/procesar_botones', methods=['GET', 'POST'])
@login_required
def procesar_botones():
    if request.method == 'POST':
        return procesar_botones_post()
    return procesar_botones_get()

def procesar_botones_post():
    buttons = load_button_config()
    selected_buttons = request.form.getlist('botones')
    
    # Almacenar los botones seleccionados en la sesión
    session['selected_buttons'] = selected_buttons
    
    # Renderizar la plantilla que muestra los formularios
    return render_template('procesar_botones.html', buttons=buttons, selected_buttons=selected_buttons)

def procesar_botones_get():
    # Si se accede por GET, simplemente mostrar la página de selección
    buttons = load_button_config()
    return render_template('load_buttons.html', buttons=buttons)

# --- FIN DEL CÓDIGO RESTAURADO ---
