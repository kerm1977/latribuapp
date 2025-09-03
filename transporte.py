from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
)
from models import db, User  # Asegúrate de que User y otros modelos necesarios se importen desde tu archivo models.py
from sqlalchemy import desc, or_
from datetime import datetime
from functools import wraps

# Define el Blueprint para esta sección
transporte_bp = Blueprint('transporte', __name__, template_folder='templates')

# --- Decoradores de Autenticación y Roles ---
# (Puedes moverlos a un archivo utils.py si los usas en más sitios)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    if not isinstance(roles, list):
        roles = [roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Debes iniciar sesión para ver esta página.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('No tienes permiso para acceder a esta funcionalidad.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# --- Modelos de Base de Datos ---

class EtiquetaViaje(db.Model):
    """Modelo para las etiquetas o categorías personalizadas de los viajes."""
    __tablename__ = 'etiqueta_viaje'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<EtiquetaViaje {self.nombre}>'

class Viaje(db.Model):
    """Modelo principal para almacenar la información de cada caminata o viaje."""
    __tablename__ = 'viaje'
    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(150), nullable=False)
    nombre_lugar = db.Column(db.String(200))
    provincia = db.Column(db.String(50))
    fecha_requerida = db.Column(db.Boolean, default=False)
    fecha_hora = db.Column(db.DateTime, nullable=True)
    nota = db.Column(db.Text, nullable=True)
    recoger_en = db.Column(db.Text, nullable=True)
    nombre_entrega = db.Column(db.String(200), nullable=True)
    punto_entrega = db.Column(db.String(200), nullable=True)
    url_mapa_entrega = db.Column(db.String(500), nullable=True)
    nombre_destino = db.Column(db.String(200), nullable=True)
    punto_destino = db.Column(db.String(200), nullable=True)
    url_mapa_destino = db.Column(db.String(500), nullable=True)
    precio = db.Column(db.Integer, nullable=True, default=0)
    # Relación con usuario (opcional, si quieres saber quién creó el viaje)
    # user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # creador = db.relationship('User', backref=db.backref('viajes_creados', lazy=True))

    def __repr__(self):
        return f'<Viaje {self.id}: {self.categoria}>'


# --- Rutas ---

@transporte_bp.route('/viajes/crear', methods=['GET', 'POST'])
#@login_required # Descomenta si necesitas que el usuario esté logueado
def crear_viaje():
    """
    Gestiona la creación y edición de un viaje.
    Si se pasa un 'id' en la URL, carga los datos para editar.
    Si no, muestra un formulario vacío para crear uno nuevo.
    """
    viaje_a_editar = None
    viaje_id = request.args.get('id', None, type=int)
    if viaje_id:
        viaje_a_editar = Viaje.query.get_or_404(viaje_id)

    if request.method == 'POST':
        # --- Recoger datos del formulario ---
        categoria = request.form.get('categoria')
        nombre_lugar = request.form.get('nombre_lugar')
        provincia = request.form.get('provincia')
        fecha_requerida = request.form.get('fecha_radio') == 'Si'
        nota = request.form.get('nota')
        recoger_en = request.form.get('recoger_en')
        nombre_entrega = request.form.get('nombre_entrega')
        punto_entrega = request.form.get('punto_entrega')
        url_mapa_entrega = request.form.get('url_mapa_entrega')
        nombre_destino = request.form.get('nombre_destino')
        punto_destino = request.form.get('punto_destino')
        url_mapa_destino = request.form.get('url_mapa_destino')
        
        fecha_hora_combinada = None
        if fecha_requerida:
            fecha_str = request.form.get('fecha')
            hora_str = request.form.get('hora')
            if fecha_str and hora_str:
                try:
                    fecha_hora_combinada = datetime.strptime(f"{fecha_str} {hora_str}", '%Y-%m-%d %H:%M')
                except ValueError:
                    flash('El formato de fecha u hora es incorrecto.', 'danger')
                    # Recargar datos para no perderlos
                    etiquetas_personalizadas = EtiquetaViaje.query.order_by(EtiquetaViaje.nombre).all()
                    return render_template('crear_viaje.html', viaje=request.form, etiquetas=etiquetas_personalizadas)

        # --- Lógica para Crear o Actualizar ---
        if viaje_a_editar: # Actualizar
            viaje_a_editar.categoria = categoria
            viaje_a_editar.nombre_lugar = nombre_lugar
            viaje_a_editar.provincia = provincia
            viaje_a_editar.fecha_requerida = fecha_requerida
            viaje_a_editar.fecha_hora = fecha_hora_combinada
            viaje_a_editar.nota = nota
            viaje_a_editar.recoger_en = recoger_en
            viaje_a_editar.nombre_entrega = nombre_entrega
            viaje_a_editar.punto_entrega = punto_entrega
            viaje_a_editar.url_mapa_entrega = url_mapa_entrega
            viaje_a_editar.nombre_destino = nombre_destino
            viaje_a_editar.punto_destino = punto_destino
            viaje_a_editar.url_mapa_destino = url_mapa_destino
            flash(f'¡Viaje "{categoria}" actualizado correctamente!', 'success')
        else: # Crear nuevo
            nuevo_viaje = Viaje(
                categoria=categoria,
                nombre_lugar=nombre_lugar,
                provincia=provincia,
                fecha_requerida=fecha_requerida,
                fecha_hora=fecha_hora_combinada,
                nota=nota,
                recoger_en=recoger_en,
                nombre_entrega=nombre_entrega,
                punto_entrega=punto_entrega,
                url_mapa_entrega=url_mapa_entrega,
                nombre_destino=nombre_destino,
                punto_destino=punto_destino,
                url_mapa_destino=url_mapa_destino
            )
            db.session.add(nuevo_viaje)
            flash(f'¡Viaje "{categoria}" creado exitosamente!', 'success')
        
        db.session.commit()
        return redirect(url_for('transporte.ver_viaje'))

    etiquetas_personalizadas = EtiquetaViaje.query.order_by(EtiquetaViaje.nombre).all()
    return render_template('crear_viaje.html', viaje=viaje_a_editar, etiquetas=etiquetas_personalizadas)

@transporte_bp.route('/viajes/ver')
#@login_required
def ver_viaje():
    """Muestra una lista de todos los viajes creados."""
    viajes = Viaje.query.order_by(desc(Viaje.id)).all()
    etiquetas_personalizadas = EtiquetaViaje.query.order_by(EtiquetaViaje.nombre).all()
    return render_template('ver_viaje.html', viajes=viajes, etiquetas=etiquetas_personalizadas)
    
@transporte_bp.route('/viajes/detalle/<int:id>')
#@login_required
def detalle_viaje(id):
    """Muestra la información completa de un viaje específico."""
    viaje = Viaje.query.get_or_404(id)
    return render_template('detalle_viaje.html', viaje=viaje)

@transporte_bp.route('/viajes/borrar', methods=['POST'])
@login_required
@role_required('Superuser')
def borrar_viaje():
    """
    Ruta para procesar la eliminación de un viaje.
    Se activa desde el modal de confirmación. SOLO PARA SUPERUSUARIOS.
    """
    try:
        viaje_id = request.form.get('viaje_id')
        viaje = Viaje.query.get(viaje_id)
        if viaje:
            db.session.delete(viaje)
            db.session.commit()
            flash(f'El viaje "{viaje.categoria}" ha sido eliminado.', 'success')
        else:
            flash('El viaje no fue encontrado.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocurrió un error al eliminar el viaje: {str(e)}', 'danger')
    return redirect(url_for('transporte.ver_viaje'))

# --- Rutas para API/AJAX (Funcionalidades adicionales) ---

@transporte_bp.route('/viajes/api/agregar-etiqueta', methods=['POST'])
#@login_required
def agregar_etiqueta():
    """API para agregar una nueva etiqueta personalizada desde el formulario."""
    nombre_etiqueta = request.json.get('etiqueta_nombre')
    if not nombre_etiqueta:
        return jsonify({'success': False, 'message': 'El nombre de la etiqueta no puede estar vacío.'}), 400

    if EtiquetaViaje.query.filter_by(nombre=nombre_etiqueta).first():
        return jsonify({'success': False, 'message': 'Esta etiqueta ya existe.'}), 409

    nueva_etiqueta = EtiquetaViaje(nombre=nombre_etiqueta)
    db.session.add(nueva_etiqueta)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Etiqueta agregada.',
        'etiqueta': {
            'id': nueva_etiqueta.id,
            'nombre': nueva_etiqueta.nombre
        }
    })

@transporte_bp.route('/viajes/api/eliminar-etiqueta', methods=['POST'])
#@login_required
def eliminar_etiqueta():
    """
    API para eliminar una etiqueta.
    Si la etiqueta está en uso, devuelve una advertencia con la lista de viajes.
    Si se recibe el parámetro 'force=true', la elimina y actualiza los viajes.
    """
    data = request.get_json()
    nombre_etiqueta = data.get('etiqueta_nombre')
    force_delete = data.get('force', False)

    if not nombre_etiqueta:
        return jsonify({'success': False, 'message': 'El nombre de la etiqueta no puede estar vacío.'}), 400

    etiqueta = EtiquetaViaje.query.filter_by(nombre=nombre_etiqueta).first()
    if not etiqueta:
        return jsonify({'success': False, 'message': 'La etiqueta no fue encontrada.'}), 404
    
    # Verificar si la etiqueta está en uso
    viajes_asociados = Viaje.query.filter_by(categoria=nombre_etiqueta).all()
    
    if viajes_asociados and not force_delete:
        # Crear una lista de los viajes que usan la etiqueta
        viajes_conflictivos = [{'id': v.id, 'categoria': v.categoria} for v in viajes_asociados]
        return jsonify({
            'success': False, 
            'in_use': True,
            'message': f'La etiqueta "{nombre_etiqueta}" está siendo usada por {len(viajes_asociados)} viaje(s).',
            'viajes': viajes_conflictivos # Enviar la lista al frontend
        }), 409

    try:
        # Si se fuerza el borrado, actualizar los viajes asociados
        if viajes_asociados and force_delete:
            for viaje in viajes_asociados:
                viaje.categoria = "Sin Categoría"
        
        db.session.delete(etiqueta)
        db.session.commit()
        
        message = 'Etiqueta eliminada correctamente.'
        if force_delete and viajes_asociados:
            message = f'Etiqueta eliminada y {len(viajes_asociados)} viaje(s) actualizado(s) a "Sin Categoría".'
            
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ocurrió un error: {str(e)}'}), 500


@transporte_bp.route('/viajes/api/get-viaje-data/<int:viaje_id>')
#@login_required
def get_viaje_data(viaje_id):
    """API para obtener los datos de un viaje y mostrarlos en ver_viaje.html."""
    viaje = Viaje.query.get(viaje_id)
    if not viaje:
        return jsonify({'error': 'Viaje no encontrado'}), 404
        
    # Formatear la fecha para el input
    fecha_formato = viaje.fecha_hora.strftime('%Y-%m-%d') if viaje.fecha_hora else ''
    hora_formato = viaje.fecha_hora.strftime('%H:%M') if viaje.fecha_hora else ''

    return jsonify({
        'id': viaje.id,
        'categoria': viaje.categoria,
        'nombre_lugar': viaje.nombre_lugar,
        'provincia': viaje.provincia,
        'fecha_requerida': viaje.fecha_requerida,
        'fecha': fecha_formato,
        'hora': hora_formato,
        'nota': viaje.nota,
        'recoger_en': viaje.recoger_en,
        'nombre_entrega': viaje.nombre_entrega,
        'punto_entrega': viaje.punto_entrega,
        'url_mapa_entrega': viaje.url_mapa_entrega,
        'nombre_destino': viaje.nombre_destino,
        'punto_destino': viaje.punto_destino,
        'url_mapa_destino': viaje.url_mapa_destino,
        'precio': viaje.precio if viaje.precio is not None else 0
    })

@transporte_bp.route('/viajes/api/guardar-precio', methods=['POST'])
#@login_required
def guardar_precio():
    """API para guardar el precio desde ver_viaje.html."""
    data = request.get_json()
    viaje_id = data.get('id')
    precio = data.get('precio')

    if viaje_id is None or precio is None:
        return jsonify({'success': False, 'message': 'Faltan datos.'}), 400
        
    try:
        precio_int = int(precio)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'El precio debe ser un número entero.'}), 400

    viaje = Viaje.query.get(viaje_id)
    if not viaje:
        return jsonify({'success': False, 'message': 'Viaje no encontrado.'}), 404

    viaje.precio = precio_int
    db.session.commit()

    return jsonify({'success': True, 'message': 'Precio guardado correctamente.'})


# --- Rutas para Exportación ---
# La exportación de imagen (JPG) se gestiona en el lado del cliente (detalle_viaje.html) con JavaScript.
# Dejamos esta ruta preparada para una futura implementación de exportación a PDF en el servidor.
@transporte_bp.route('/viajes/exportar/<int:id>/pdf')
#@login_required
def exportar_viaje_pdf(id):
    """
    Gestiona la exportación de un viaje a formato PDF.
    Actualmente es un marcador de posición.
    """
    viaje = Viaje.query.get_or_404(id)
    
    # Simulación de la lógica de exportación a PDF
    flash('La funcionalidad para exportar a PDF aún no está implementada.', 'info')
    
    # Aquí iría la lógica para generar el archivo PDF con una librería como WeasyPrint o FPDF
    
    return redirect(url_for('transporte.detalle_viaje', id=id))

