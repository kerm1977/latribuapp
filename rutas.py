# rutas.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, make_response, send_from_directory
from models import db, Ruta # Importa db y el nuevo modelo Ruta
from functools import wraps # Importar wraps para el decorador role_required
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas # Renombrado para evitar conflicto con Flask canvas
from datetime import datetime, date # Importar datetime y date para manejar fechas
import re # NUEVO: Importar re para expresiones regulares
import os # Importar os para manejo de rutas de archivo
from werkzeug.utils import secure_filename # Para nombres de archivo seguros
from collections import defaultdict # Importar defaultdict para agrupar rutas

# Crea un Blueprint para el módulo de rutas
rutas_bp = Blueprint('rutas', __name__, template_folder='templates')

# Configuración para subida de archivos de mapa
MAP_FILES_UPLOAD_FOLDER = os.path.join(rutas_bp.root_path, 'static', 'uploads', 'map_files')
ALLOWED_MAP_EXTENSIONS = {'gpx', 'kml', 'kmz'}

# Asegúrate de que la carpeta de subidas de mapas exista
os.makedirs(MAP_FILES_UPLOAD_FOLDER, exist_ok=True)

def allowed_map_file(filename):
    """
    Verifica si la extensión del archivo de mapa está permitida.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_MAP_EXTENSIONS

# Lista de provincias de Costa Rica
PROVINCIAS = ["Alajuela", "Cartago", "Heredia", "Puntarenas", "Limón", "Guanacaste", "San José"]

# ***** MODIFICADO: Lista de dificultades con "Desconocida" *****
DIFICULTADES = ["Básico", "Intermedio", "Difícil", "Avanzado", "Técnico", "Desconocida"]


# NUEVA: Lista de categorías de búsqueda, con las provincias primero, luego el separador y las nuevas opciones
CATEGORIAS_BUSQUEDA = [
    "Todas las Categorías", # Opción por defecto para mostrar todo
] + sorted(PROVINCIAS) + [ # Añade las provincias ordenadas alfabéticamente
    "Otros", # Nueva etiqueta de grupo
    "Internacional", # Nueva categoría: Internacional
    "Caminatas Programadas", # Nueva categoría 1
    "Caminatas por Reconocer" # Nueva categoría 2
]

# Define la categoría permitida para la exportación masiva
ALLOWED_EXPORT_CATEGORY = "Caminatas Programadas"

# Define las categorías que están explícitamente prohibidas para la exportación masiva
FORBIDDEN_MASS_EXPORT_CATEGORIES = PROVINCIAS + ["Internacional", "Caminatas por Reconocer", "Otros"]


# DECORADOR PARA ROLES (MOVIDO AQUÍ DESDE app.py)
def role_required(roles):
    """
    Decorador para restringir el acceso a rutas basadas en roles.
    `roles` puede ser una cadena (un solo rol) o una lista de cadenas (múltiples roles).
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
                # Mensaje específico para el acceso a detalle_ruta
                if f.__name__ == 'detalle_ruta':
                    flash('SOLO ADMINISTRADORES PUEDEN VER EL CONTENIDO.', 'danger') # Mensaje más claro
                else:
                    flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_embed_url(video_url):
    """
    Función para obtener la URL de incrustación de videos de YouTube o Facebook.
    Esto permite que los videos se muestren correctamente en la vista de detalle.
    """
    if not video_url:
        return None

    # Expresiones regulares más robustas para YouTube
    youtube_patterns = [
        re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=|embed\/|)([a-zA-Z0-9_-]{11})(?:\S+)?'),
        re.compile(r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})(?:\S+)?')
    ]

    for pattern in youtube_patterns:
        youtube_match = pattern.search(video_url)
        if youtube_match:
            video_id = youtube_match.group(1)
            return f"https://www.youtube.com/embed/{video_id}"

    # Expresiones regulares para Facebook
    facebook_patterns = [
        re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:facebook\.com)\/watch\/\?v=(\d+)'),
        re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:facebook\.com)\/([a-zA-Z0-9\.]+)\/videos\/(?:vb\.\d+\/)?(\d+)(?:\S+)?')
    ]

    for pattern in facebook_patterns:
        facebook_match = pattern.search(video_url)
        if facebook_match:
            # Para Facebook, el plugin de video usa la URL original como el parámetro 'href'
            # y requiere el width para que se muestre correctamente en el iframe.
            return f"https://www.facebook.com/plugins/video.php?href={video_url}&show_text=0&width=1280"
    
    # Si no se reconoce ninguna plataforma de video conocida, devuelve None
    return None

# Helper function to return an empty PDF or TXT document
def _return_empty_pdf_or_txt(is_pdf=True):
    """
    Función de ayuda para devolver un documento PDF o TXT vacío
    con un mensaje indicando que la categoría no es exportable.
    """
    if is_pdf:
        buffer = BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=letter)
        c.setFont('Helvetica', 12)
        c.drawString(100, 750, "No hay rutas disponibles para exportar en la categoría seleccionada.")
        c.save()
        pdf_data = buffer.getvalue()
        buffer.close()
        response = make_response(pdf_data)
        response.headers["Content-Disposition"] = f"attachment; filename=rutas_no_exportables.pdf"
        response.headers["Content-type"] = "application/pdf"
        return response
    else:
        content = "No hay rutas disponibles para exportar en la categoría seleccionada."
        response = make_response(content)
        response.headers["Content-Disposition"] = f"attachment; filename=rutas_no_exportables.txt"
        response.headers["Content-type"] = "text/plain; charset=utf-8"
        return response


@rutas_bp.route('/rutas')
def ver_rutas():
    # --- INICIO: LÓGICA DE VISIBILIDAD DE DIFICULTAD ---
    # Obtener el parámetro para alternar la visibilidad
    toggle_difficulty = request.args.get('toggle_difficulty')
    categoria_seleccionada = request.args.get('categoria', 'Todas las Categorías')
    dificultad_seleccionada = request.args.get('dificultad', 'Todas')

    # Si se recibe el parámetro, se alterna el estado en la sesión
    if toggle_difficulty:
        # Alterna el valor booleano. Si no existe, lo establece en False (oculto).
        session['difficulty_visible'] = not session.get('difficulty_visible', True)
        # Redirige para eliminar el parámetro de la URL y evitar que se alterne de nuevo al recargar
        return redirect(url_for('rutas.ver_rutas', categoria=categoria_seleccionada, dificultad=dificultad_seleccionada))
    
    # Obtiene el estado actual de la sesión, por defecto 'True' (visible)
    difficulty_visible = session.get('difficulty_visible', True)
    # --- FIN: LÓGICA DE VISIBILIDAD DE DIFICULTAD ---

    user_logged_in = session.get('logged_in', False)

    # --- INICIO: LÓGICA PARA GRÁFICO CIRCULAR GENERAL ---
    todas_las_rutas_para_grafico = Ruta.query.all()
    categorias_grafico = PROVINCIAS + ["Caminatas Programadas", "Caminatas por Reconocer"]
    conteo_categorias = defaultdict(int)
    for ruta in todas_las_rutas_para_grafico:
        if ruta.provincia in categorias_grafico:
            conteo_categorias[ruta.provincia] += 1
    chart_data_dict = {k: v for k, v in conteo_categorias.items() if v > 0}
    chart_labels = list(chart_data_dict.keys())
    chart_values = list(chart_data_dict.values())
    datos_grafico_general = {
        "labels": chart_labels,
        "data": chart_values
    }
    # --- FIN: LÓGICA GRÁFICO CIRCULAR ---

    # --- INICIO: LÓGICA PARA GRÁFICO DE BARRAS DE 'CAMINATAS POR RECONOCER' ---
    rutas_reconocer = Ruta.query.filter_by(provincia='Caminatas por Reconocer').all()
    conteo_dificultad_reconocer = defaultdict(int)
    for ruta in rutas_reconocer:
        if ruta.dificultad: # ***** MODIFICADO: Incluir "Desconocida" *****
             conteo_dificultad_reconocer[ruta.dificultad] += 1
    
    reconocer_chart_labels = sorted(conteo_dificultad_reconocer.keys(), key=lambda d: DIFICULTADES.index(d) if d in DIFICULTADES else -1)
    reconocer_chart_values = [conteo_dificultad_reconocer[label] for label in reconocer_chart_labels]
    datos_grafico_reconocer = {
        "labels": reconocer_chart_labels,
        "data": reconocer_chart_values
    }
    # --- FIN: LÓGICA GRÁFICO DE BARRAS ---

    # --- INICIO: LÓGICA PARA LA LISTA DE RUTAS (CON FILTROS DE VISIBILIDAD) ---
    query = Ruta.query

    if not user_logged_in:
        query = query.filter(Ruta.provincia != 'Caminatas por Reconocer')

    if categoria_seleccionada and categoria_seleccionada not in ['Todas las Categorías', 'Otros']:
        query = query.filter_by(provincia=categoria_seleccionada)
    
    if dificultad_seleccionada and dificultad_seleccionada != 'Todas':
        query = query.filter_by(dificultad=dificultad_seleccionada)

    rutas_para_vista = query.order_by(Ruta.fecha.asc(), Ruta.nombre.asc()).all()
    
    rutas_por_categoria = defaultdict(lambda: defaultdict(list))
    meses_espanol = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    for ruta in rutas_para_vista:
        if ruta.provincia == 'Caminatas Programadas' and ruta.fecha:
            nombre_mes = meses_espanol[ruta.fecha.month]
            rutas_por_categoria[ruta.provincia][f"{nombre_mes} {ruta.fecha.year}"].append(ruta)
        else:
            if 'rutas_sin_fecha' not in rutas_por_categoria[ruta.provincia]:
                rutas_por_categoria[ruta.provincia]['rutas_sin_fecha'] = []
            rutas_por_categoria[ruta.provincia]['rutas_sin_fecha'].append(ruta)
    # --- FIN: LÓGICA PARA LA LISTA DE RUTAS ---

    return render_template('ver_rutas.html', 
                           rutas_por_categoria=rutas_por_categoria,
                           categorias_busqueda=CATEGORIAS_BUSQUEDA,
                           provincia_seleccionada=categoria_seleccionada,
                           dificultades=DIFICULTADES,
                           dificultad_seleccionada=dificultad_seleccionada,
                           chart_data=json.dumps(datos_grafico_general),
                           reconocer_chart_data=json.dumps(datos_grafico_reconocer),
                           difficulty_visible=difficulty_visible) # Pasa la variable de visibilidad a la plantilla

@rutas_bp.route('/rutas/crear', methods=['GET', 'POST'])
@role_required('Superuser')
def crear_ruta():
    if request.method == 'POST':
        nombre = request.form['nombre']
        categoria = request.form['provincia'] 
        dificultad = request.form['dificultad']
        detalle = request.form['detalle']
        enlace_video = request.form.get('enlace_video')
        
        fecha_str = request.form.get('fecha')
        fecha = None
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha inválido. Por favor, usa YYYY-MM-DD.', 'danger')
                return redirect(url_for('rutas.crear_ruta'))

        precio_str = request.form.get('precio')
        precio = None
        if precio_str:
            try:
                precio = float(precio_str)
            except ValueError:
                flash('Formato de precio inválido. Por favor, ingresa un número válido.', 'danger')
                return redirect(url_for('rutas.crear_ruta'))

        gpx_file_url = None
        kml_file_url = None
        kmz_file_url = None

        if 'gpx_file' in request.files:
            gpx_file = request.files['gpx_file']
            if gpx_file and allowed_map_file(gpx_file.filename):
                filename = secure_filename(gpx_file.filename)
                gpx_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                gpx_file.save(gpx_path)
                gpx_file_url = 'uploads/map_files/' + filename
            elif gpx_file.filename != '':
                flash('Tipo de archivo GPX no permitido.', 'warning')

        if 'kml_file' in request.files:
            kml_file = request.files['kml_file']
            if kml_file and allowed_map_file(kml_file.filename):
                filename = secure_filename(kml_file.filename)
                kml_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                kml_file.save(kml_path)
                kml_file_url = 'uploads/map_files/' + filename
            elif kml_file.filename != '':
                flash('Tipo de archivo KML no permitido.', 'warning')

        if 'kmz_file' in request.files:
            kmz_file = request.files['kmz_file']
            if kmz_file and allowed_map_file(kmz_file.filename):
                filename = secure_filename(kmz_file.filename)
                kmz_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                kmz_file.save(kmz_path)
                kmz_file_url = 'uploads/map_files/' + filename
            elif kmz_file.filename != '':
                flash('Tipo de archivo KMZ no permitido.', 'warning')

        if not nombre or not categoria or not dificultad:
            flash('El nombre, la categoría y la dificultad son campos obligatorios.', 'danger')
            return render_template('crear_rutas.html', categorias_busqueda=CATEGORIAS_BUSQUEDA, dificultades=DIFICULTADES)

        nueva_ruta = Ruta(
            nombre=nombre,
            provincia=categoria,
            dificultad=dificultad,
            detalle=detalle,
            enlace_video=enlace_video,
            fecha=fecha,
            precio=precio,
            gpx_file_url=gpx_file_url,
            kml_file_url=kml_file_url,
            kmz_file_url=kmz_file_url
        )
        try:
            db.session.add(nueva_ruta)
            db.session.commit()
            flash('Ruta creada exitosamente.', 'success')
            return redirect(url_for('rutas.ver_rutas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la ruta: {e}', 'danger')
            current_app.logger.error(f"Error al crear ruta: {e}")
    
    categorias_para_formulario = [cat for cat in CATEGORIAS_BUSQUEDA if cat != 'Todas las Categorías' and cat != 'Otros']
    return render_template('crear_rutas.html', categorias_busqueda=categorias_para_formulario, dificultades=DIFICULTADES)

@rutas_bp.route('/rutas/editar/<int:ruta_id>', methods=['GET', 'POST'])
@role_required('Superuser')
def editar_ruta(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta:
        flash('Ruta no encontrada.', 'danger')
        return redirect(url_for('rutas.ver_rutas'))

    if request.method == 'POST':
        ruta.nombre = request.form['nombre']
        ruta.provincia = request.form['provincia']
        ruta.dificultad = request.form['dificultad']
        ruta.detalle = request.form['detalle']
        ruta.enlace_video = request.form.get('enlace_video')

        fecha_str = request.form.get('fecha')
        ruta.fecha = None
        if fecha_str:
            try:
                ruta.fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato de fecha inválido. Por favor, usa YYYY-MM-DD.', 'danger')
                return redirect(url_for('rutas.editar_ruta', ruta_id=ruta.id))

        precio_str = request.form.get('precio')
        ruta.precio = None
        if precio_str:
            try:
                ruta.precio = float(precio_str)
            except ValueError:
                flash('Formato de precio inválido. Por favor, ingresa un número válido.', 'danger')
                return redirect(url_for('rutas.editar_ruta', ruta_id=ruta.id))
        
        if 'gpx_file' in request.files:
            gpx_file = request.files['gpx_file']
            if gpx_file and allowed_map_file(gpx_file.filename):
                filename = secure_filename(gpx_file.filename)
                gpx_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                gpx_file.save(gpx_path)
                ruta.gpx_file_url = 'uploads/map_files/' + filename
            elif gpx_file.filename == '' and 'clear_gpx' in request.form:
                ruta.gpx_file_url = None
            elif gpx_file.filename != '':
                flash('Tipo de archivo GPX no permitido.', 'warning')

        if 'kml_file' in request.files:
            kml_file = request.files['kml_file']
            if kml_file and allowed_map_file(kml_file.filename):
                filename = secure_filename(kml_file.filename)
                kml_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                kml_file.save(kml_path)
                ruta.kml_file_url = 'uploads/map_files/' + filename
            elif kml_file.filename == '' and 'clear_kml' in request.form:
                ruta.kml_file_url = None
            elif kml_file.filename != '':
                flash('Tipo de archivo KML no permitido.', 'warning')

        if 'kmz_file' in request.files:
            kmz_file = request.files['kmz_file']
            if kmz_file and allowed_map_file(kmz_file.filename):
                filename = secure_filename(kmz_file.filename)
                kmz_path = os.path.join(MAP_FILES_UPLOAD_FOLDER, filename)
                kmz_file.save(kmz_path)
                ruta.kmz_file_url = 'uploads/map_files/' + filename
            elif kmz_file.filename == '' and 'clear_kmz' in request.form:
                ruta.kmz_file_url = None
            elif kmz_file.filename != '':
                flash('Tipo de archivo KMZ no permitido.', 'warning')
        
        try:
            db.session.commit()
            flash('Ruta actualizada exitosamente.', 'success')
            return redirect(url_for('rutas.ver_rutas'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la ruta: {e}', 'danger')
            current_app.logger.error(f"Error al actualizar ruta {ruta_id}: {e}")
    
    categorias_para_formulario = [cat for cat in CATEGORIAS_BUSQUEDA if cat != 'Todas las Categorías' and cat != 'Otros']
    return render_template('editar_rutas.html', ruta=ruta, categorias_busqueda=categorias_para_formulario, dificultades=DIFICULTADES)

@rutas_bp.route('/rutas/<int:ruta_id>')
@role_required(['Superuser', 'Usuario Regular'])
def detalle_ruta(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta:
        flash('Ruta no encontrada.', 'danger')
        return redirect(url_for('rutas.ver_rutas'))
        
    embed_url = get_embed_url(ruta.enlace_video) if ruta.enlace_video else None
    return render_template('detalle_rutas.html', ruta=ruta, embed_url=embed_url)

@rutas_bp.route('/rutas/eliminar/<int:ruta_id>', methods=['POST'])
@role_required('Superuser')
def eliminar_ruta(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta:
        flash('Ruta no encontrada.', 'danger')
        return redirect(url_for('rutas.ver_rutas'))

    try:
        if ruta.gpx_file_url:
            file_path = os.path.join(rutas_bp.root_path, 'static', ruta.gpx_file_url)
            if os.path.exists(file_path):
                os.remove(file_path)
        if ruta.kml_file_url:
            file_path = os.path.join(rutas_bp.root_path, 'static', ruta.kml_file_url)
            if os.path.exists(file_path):
                os.remove(file_path)
        if ruta.kmz_file_url:
            file_path = os.path.join(rutas_bp.root_path, 'static', ruta.kmz_file_url)
            if os.path.exists(file_path):
                os.remove(file_path)

        db.session.delete(ruta)
        db.session.commit()
        flash('Ruta eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la ruta: {e}', 'danger')
        current_app.logger.error(f"Error al eliminar ruta {ruta_id}: {e}")
    
    return redirect(url_for('rutas.ver_rutas'))

# Rutas para descargar archivos de mapa
@rutas_bp.route('/rutas/download/gpx/<int:ruta_id>')
@role_required(['Superuser', 'Usuario Regular'])
def download_gpx(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta or not ruta.gpx_file_url:
        flash('Archivo GPX no encontrado.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))
    
    directory = os.path.join(rutas_bp.root_path, 'static', 'uploads', 'map_files')
    filename = os.path.basename(ruta.gpx_file_url)
    
    if not os.path.exists(os.path.join(directory, filename)):
        flash('El archivo GPX no se encuentra en el servidor.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))

    return send_from_directory(directory, filename, as_attachment=True)

@rutas_bp.route('/rutas/download/kml/<int:ruta_id>')
@role_required(['Superuser', 'Usuario Regular'])
def download_kml(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta or not ruta.kml_file_url:
        flash('Archivo KML no encontrado.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))
    
    directory = os.path.join(rutas_bp.root_path, 'static', 'uploads', 'map_files')
    filename = os.path.basename(ruta.kml_file_url)

    if not os.path.exists(os.path.join(directory, filename)):
        flash('El archivo KML no se encuentra en el servidor.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))

    return send_from_directory(directory, filename, as_attachment=True)

@rutas_bp.route('/rutas/download/kmz/<int:ruta_id>')
@role_required(['Superuser', 'Usuario Regular'])
def download_kmz(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta or not ruta.kmz_file_url:
        flash('Archivo KMZ no encontrado.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))
    
    directory = os.path.join(rutas_bp.root_path, 'static', 'uploads', 'map_files')
    filename = os.path.basename(ruta.kmz_file_url)

    if not os.path.exists(os.path.join(directory, filename)):
        flash('El archivo KMZ no se encuentra en el servidor.', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))

    return send_from_directory(directory, filename, as_attachment=True)


@rutas_bp.route('/rutas/exportar/txt/<int:ruta_id>')
def exportar_ruta_txt(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta:
        flash('Ruta no encontrada para exportar.', 'danger')
        return redirect(url_for('rutas.ver_rutas'))

    user_role = session.get('role')
    if user_role == 'Usuario Regular' and ruta.provincia != ALLOWED_EXPORT_CATEGORY:
        flash(f'Como Usuario Regular, solo puedes exportar rutas de "{ALLOWED_EXPORT_CATEGORY}".', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta.id))

    content = f"Nombre de la Ruta: {ruta.nombre}\n" \
              f"Dificultad: {ruta.dificultad}\n" \
              f"Detalle: {ruta.detalle}\n" \
              f"Enlace de Video: {ruta.enlace_video if ruta.enlace_video else 'N/A'}\n" \
              f"Fecha: {ruta.fecha.strftime('%d/%m/%Y') if ruta.fecha else 'N/A'}\n" \
              f"Precio: ¢{int(ruta.precio) if ruta.precio is not None else 'N/A'}\n"

    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename=ruta_{ruta.nombre.replace(' ', '_').lower()}.txt"
    response.headers["Content-type"] = "text/plain; charset=utf-8"
    return response

@rutas_bp.route('/rutas/exportar/pdf/<int:ruta_id>')
def exportar_ruta_pdf(ruta_id):
    ruta = db.session.get(Ruta, ruta_id)
    if not ruta:
        flash('Ruta no encontrada para exportar.', 'danger')
        return redirect(url_for('rutas.ver_rutas'))

    user_role = session.get('role')
    if user_role == 'Usuario Regular' and ruta.provincia != ALLOWED_EXPORT_CATEGORY:
        flash(f'Como Usuario Regular, solo puedes exportar rutas de "{ALLOWED_EXPORT_CATEGORY}".', 'danger')
        return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta.id))

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    
    y_position = 750
    line_height = 15

    c.setFont('Helvetica-Bold', 14)
    c.drawString(100, y_position, f"Detalles de la Ruta: {ruta.nombre}")
    y_position -= (line_height * 2)

    c.setFont('Helvetica', 10)
    
    c.drawString(100, y_position, f"Dificultad: {ruta.dificultad}")
    y_position -= line_height
    c.drawString(100, y_position, f"Fecha: {ruta.fecha.strftime('%d/%m/%Y') if ruta.fecha else 'N/A'}")
    y_position -= line_height
    c.drawString(100, y_position, f"Precio: ¢{int(ruta.precio) if ruta.precio is not None else 'N/A'}\n")
    y_position -= line_height
    c.drawString(100, y_position, f"Enlace de Video: {ruta.enlace_video if ruta.enlace_video else 'N/A'}")
    y_position -= (line_height * 2)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(100, y_position, "Detalle de la Ruta:")
    y_position -= line_height
    c.setFont('Helvetica', 10)
    
    clean_detail = re.sub('<[^<]+?>', '', ruta.detalle)
    lines = clean_detail.split('\n')
    for line in lines:
        words = line.split(' ')
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if c.stringWidth(test_line, 'Helvetica', 10) < 400:
                current_line.append(word)
            else:
                if y_position < 50:
                    c.showPage()
                    c.setFont('Helvetica', 10)
                    y_position = 750
                c.drawString(100, y_position, ' '.join(current_line))
                y_position -= line_height
                current_line = [word]
        if current_line:
            if y_position < 50:
                c.showPage()
                c.setFont('Helvetica', 10)
                y_position = 750
            c.drawString(100, y_position, ' '.join(current_line))
            y_position -= line_height

    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_data)
    filename = f"ruta_{ruta.nombre.replace(' ', '_').lower()}.pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response

@rutas_bp.route('/rutas/exportar/jpg/<int:ruta_id>')
@role_required(['Superuser', 'Usuario Regular'])
def exportar_ruta_jpg(ruta_id):
    flash('La exportación a JPG desde el servidor no está implementada directamente. Considere usar una solución de captura de pantalla en el cliente (navegador) o un servicio externo si es indispensable.', 'info')
    return redirect(url_for('rutas.detalle_ruta', ruta_id=ruta_id))


# NUEVAS RUTAS PARA EXPORTAR TODAS LAS RUTAS (o las filtradas por la categoría seleccionada)
@rutas_bp.route('/rutas/exportar/todas/pdf')
def exportar_todas_rutas_pdf():
    categoria_seleccionada = request.args.get('categoria')
    
    if categoria_seleccionada in FORBIDDEN_MASS_EXPORT_CATEGORIES:
        flash(f'La categoría "{categoria_seleccionada}" no puede ser exportada en este formato masivo.', 'danger')
        return _return_empty_pdf_or_txt(is_pdf=True)

    query = Ruta.query

    if categoria_seleccionada == ALLOWED_EXPORT_CATEGORY:
        query = query.filter_by(provincia=ALLOWED_EXPORT_CATEGORY)
    elif categoria_seleccionada == 'Todas las Categorías' or not categoria_seleccionada:
        query = query.filter(Ruta.provincia.notin_(FORBIDDEN_MASS_EXPORT_CATEGORIES))
    else:
        flash(f'Categoría de exportación no válida: "{categoria_seleccionada}".', 'danger')
        return _return_empty_pdf_or_txt(is_pdf=True)

    rutas = query.order_by(Ruta.provincia, Ruta.fecha.asc(), Ruta.nombre.asc()).all()

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=letter)
    
    y_position = 750
    line_height = 15
    page_number = 1

    def add_page_header(canvas_obj, y_pos, current_page_num):
        canvas_obj.setFont('Helvetica-Bold', 10)
        canvas_obj.drawString(500, 770, f"Página {current_page_num}")
        canvas_obj.setFont('Helvetica-Bold', 14)
        canvas_obj.drawString(100, y_pos, "Listado de Rutas Disponibles")
        canvas_obj.setFont('Helvetica', 10)
        return y_pos - (line_height * 2)

    y_position = add_page_header(c, y_position, page_number)

    if not rutas:
        c.drawString(100, y_position, "No hay rutas disponibles para exportar.")
    else:
        current_category = None
        current_month_year = None
        meses_espanol_pdf = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        for ruta in rutas:
            if y_position < 70:
                c.showPage()
                page_number += 1
                y_position = 750
                y_position = add_page_header(c, y_position, page_number)
                current_category = None
                current_month_year = None

            if ruta.provincia != current_category:
                if current_category is not None:
                    y_position -= line_height
                c.setFont('Helvetica-Bold', 12)
                c.drawString(100, y_position, f"Categoría: {ruta.provincia}")
                y_position -= line_height
                c.setFont('Helvetica', 10)
                current_category = ruta.provincia
                current_month_year = None

            if ruta.provincia == 'Caminatas Programadas' and ruta.fecha:
                month_year_str = f"{meses_espanol_pdf[ruta.fecha.month]} {ruta.fecha.year}"
                if month_year_str != current_month_year:
                    if current_month_year is not None:
                        y_position -= line_height
                    c.setFont('Helvetica-Bold', 11)
                    c.drawString(120, y_position, f"--- {month_year_str} ---")
                    y_position -= line_height
                    c.setFont('Helvetica', 10)
                    current_month_year = month_year_str
            else:
                current_month_year = None
            
            c.drawString(110, y_position, f"  - Nombre: {ruta.nombre}")
            y_position -= line_height
            c.drawString(110, y_position, f"    Dificultad: {ruta.dificultad}")
            y_position -= line_height
            c.drawString(110, y_position, f"    Fecha: {ruta.fecha.strftime('%d/%m/%Y') if ruta.fecha else 'N/A'}")
            y_position -= line_height
            c.drawString(110, y_position, f"    Precio: ¢{int(ruta.precio) if ruta.precio is not None else 'N/A'}")
            y_position -= line_height
            c.drawString(110, y_position, f"    Detalle: {re.sub('<[^<]+?>', '', ruta.detalle)[:100]}...")
            y_position -= line_height
            c.drawString(110, y_position, f"    Video: {ruta.enlace_video if ruta.enlace_video else 'N/A'}")
            y_position -= (line_height * 1.5)

    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()

    response = make_response(pdf_data)
    filename = f"todas_las_rutas_{categoria_seleccionada.replace(' ', '_').lower()}.pdf" if categoria_seleccionada and categoria_seleccionada != 'Todas las Categorías' else "todas_las_rutas.pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response


@rutas_bp.route('/rutas/exportar/todas/txt')
def exportar_todas_rutas_txt():
    categoria_seleccionada = request.args.get('categoria')

    if categoria_seleccionada in FORBIDDEN_MASS_EXPORT_CATEGORIES:
        flash(f'La categoría "{categoria_seleccionada}" no puede ser exportada en este formato masivo.', 'danger')
        return _return_empty_pdf_or_txt(is_pdf=False)

    query = Ruta.query
    if categoria_seleccionada == ALLOWED_EXPORT_CATEGORY:
        query = query.filter_by(provincia=ALLOWED_EXPORT_CATEGORY)
    elif categoria_seleccionada == 'Todas las Categorías' or not categoria_seleccionada:
        query = query.filter(Ruta.provincia.notin_(FORBIDDEN_MASS_EXPORT_CATEGORIES))
    else:
        flash(f'Categoría de exportación no válida: "{categoria_seleccionada}".', 'danger')
        return _return_empty_pdf_or_txt(is_pdf=False)

    rutas = query.order_by(Ruta.provincia, Ruta.fecha.asc(), Ruta.nombre.asc()).all()

    content = "Listado de Rutas Disponibles\n\n"
    if not rutas:
        content += "No hay rutas disponibles para exportar."
    else:
        current_category = None
        current_month_year = None
        meses_espanol_txt = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        for ruta in rutas:
            if ruta.provincia != current_category:
                content += f"\n--- Categoría: {ruta.provincia} ---\n"
                current_category = ruta.provincia
                current_month_year = None

            if ruta.provincia == 'Caminatas Programadas' and ruta.fecha:
                month_year_str = f"{meses_espanol_txt[ruta.fecha.month]} {ruta.fecha.year}"
                if month_year_str != current_month_year:
                    content += f"\n--- Mes: {month_year_str} ---\n"
                    current_month_year = month_year_str
            else:
                current_month_year = None

            content += f"Nombre: {ruta.nombre}\n"
            content += f"Dificultad: {ruta.dificultad}\n"
            content += f"Fecha: {ruta.fecha.strftime('%d/%m/%Y') if ruta.fecha else 'N/A'}\n"
            content += f"Precio: ¢{int(ruta.precio) if ruta.precio is not None else 'N/A'}\n"
            content += f"Detalle: {re.sub('<[^<]+?>', '', ruta.detalle)}\n"
            content += f"Enlace de Video: {ruta.enlace_video if ruta.enlace_video else 'N/A'}\n\n"

    response = make_response(content)
    filename = f"todas_las_rutas_{categoria_seleccionada.replace(' ', '_').lower()}.txt" if categoria_seleccionada and categoria_seleccionada != 'Todas las Categorías' else "todas_las_rutas.txt"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "text/plain; charset=utf-8"
    return response

@rutas_bp.route('/rutas/exportar/todas/jpg')
@role_required(['Superuser', 'Usuario Regular'])
def exportar_todas_rutas_jpg():
    flash('La exportación de todas las rutas a JPG desde el servidor no está implementada directamente. Considere usar una solución de captura de pantalla en el cliente (navegador) o un servicio externo si es indispensable.', 'info')
    return redirect(url_for('rutas.ver_rutas', categoria=request.args.get('categoria')))
