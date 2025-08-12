# intern.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, make_response
from models import db, User
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Float, Date, Time, Boolean, ForeignKey, Text
import json
from datetime import datetime as dt
from datetime import date
import os
import uuid
from werkzeug.utils import secure_filename

# --- LIBRERÍAS PARA EXPORTACIÓN ---
import io
from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.cell import MergedCell

intern_bp = Blueprint('intern', __name__, template_folder='templates', static_folder='static')

# --- MODELOS (sin cambios) ---
class Intern(db.Model):
    __tablename__ = 'intern'
    id = Column(Integer, primary_key=True)
    flyer = Column(String(200), nullable=True)
    nombre_viaje = Column(String(150), nullable=False)
    precio_paquete = Column(Float, default=0.0)
    capacidad = Column(Integer, default=0)
    tipo_moneda = Column(String(20))
    tipo_cambio = Column(Float, default=1.0)
    pais = Column(String(50))
    user_id = Column(Integer, ForeignKey('user.id'))
    prealertas = relationship('PreAlerta', backref='intern', cascade="all, delete-orphan")
    lugares = relationship('LugarVisitar', backref='intern', cascade="all, delete-orphan")
    transportes = relationship('Transporte', backref='intern', cascade="all, delete-orphan")
    guias = relationship('Guia', backref='intern', cascade="all, delete-orphan")
    estadias = relationship('Estadia', backref='intern', cascade="all, delete-orphan")
    aerolineas = relationship('Aerolinea', backref='intern', cascade="all, delete-orphan")

class PreAlerta(db.Model):
    __tablename__ = 'pre_alerta'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    banco = Column(String(100))
    telefono_entidad = Column(String(20))
    fecha_prealerta = Column(Date)
    asesor = Column(String(100))
    hora_prealerta = Column(Time)
    numero_prealerta = Column(String(50))
    fecha_desde = Column(Date)
    fecha_hasta = Column(Date)

class LugarVisitar(db.Model):
    __tablename__ = 'lugar_visitar'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    tipo_lugar = Column(String(50))
    nombre_sitio = Column(String(150))
    precio_entrada = Column(Float, default=0.0)
    fecha_reserva = Column(Date)
    guia_local = Column(Boolean, default=False)
    nombre_guia = Column(String(100))
    telefono_lugar = Column(String(20))
    telefono_contacto = Column(String(20))
    whatsapp_contacto = Column(String(20))
    email = Column(String(120))
    enlaces = Column(Text)
    nota = Column(Text)

class Transporte(db.Model):
    __tablename__ = 'transporte'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    tipo_transporte = Column(String(50))
    nombre_transporte = Column(String(150))
    conductor = Column(String(100))
    precio = Column(Float, default=0.0)
    fecha_contratacion = Column(Date)
    telefono_lugar = Column(String(20))
    telefono_contacto = Column(String(20))
    whatsapp_contacto = Column(String(20))
    email = Column(String(120))
    enlaces = Column(Text)
    nota = Column(Text)

class Guia(db.Model):
    __tablename__ = 'guia'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    nombre = Column(String(100))
    telefono = Column(String(20))
    operador = Column(String(100))
    email = Column(String(120))
    whatsapp = Column(String(20))
    precio_guia_pp = Column(Float, default=0.0)
    cpl = Column(String(10))
    fecha_disponible = Column(Date)
    reserva = Column(String(50))
    precio_acarreo = Column(Float, default=0.0)
    enlaces = Column(Text)
    nota = Column(Text)
    fecha_reserva = Column(Date)

class Estadia(db.Model):
    __tablename__ = 'estadia'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    nombre = Column(String(150))
    contacto = Column(String(100))
    telefono = Column(String(20))
    whatsapp = Column(String(20))
    email = Column(String(120))
    precio_pp = Column(Float, default=0.0)
    cpl = Column(Boolean, default=False)
    fecha_disponible = Column(Date)
    alimentacion_incluida = Column(Boolean, default=False)
    cantidad_noches = Column(Integer, default=1)
    enlaces = Column(Text)
    nota = Column(Text)
    fecha_entrada = Column(Date)
    fecha_salida = Column(Date)

class Aerolinea(db.Model):
    __tablename__ = 'aerolinea'
    id = Column(Integer, primary_key=True)
    intern_id = Column(Integer, ForeignKey('intern.id'), nullable=False)
    tipo_transporte = Column(String(50))
    nombre_aerolinea = Column(String(100))
    telefono_aerolinea = Column(String(20))
    email = Column(String(120))
    whatsapp = Column(String(20))
    telefono_prealertar_fecha = Column(Date)
    enlace_prealertar = Column(Text)
    numero_vuelo = Column(String(50))
    horario_salida = Column(Time)
    horario_llegada = Column(Time)
    nombre_aeropuerto = Column(String(150))
    telefono_aeropuerto = Column(String(20))
    precio_asientos = Column(Float, default=0.0)
    precio_maletas_documentado = Column(Float, default=0.0)
    equipaje_mano = Column(Float, default=0.0)
    precio_estandar = Column(Float, default=0.0)
    precio_mas_equipo = Column(Float, default=0.0)
    precio_salida_rapida = Column(Float, default=0.0)
    precio_premium = Column(Float, default=0.0)
    precio_vip = Column(Float, default=0.0)
    precio_basic = Column(Float, default=0.0)
    precio_classic = Column(Float, default=0.0)
    precio_flexible = Column(Float, default=0.0)
    precio_impuestos = Column(Float, default=0.0)
    otros_costos = Column(Text)
    fecha_compra = Column(Date)

# --- FUNCIONES AUXILIARES (sin cambios) ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def save_flyer(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
        upload_folder = current_app.config.get('INTERN_FLYER_UPLOAD_FOLDER', os.path.join(current_app.static_folder, 'uploads', 'intern_flyers'))
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return os.path.join('uploads', 'intern_flyers', unique_filename).replace('\\', '/')
    return None

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def to_date(date_string):
    if not date_string: return None
    try:
        return dt.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        return None

def to_time(time_string):
    if not time_string: return None
    try:
        return dt.strptime(time_string, '%H:%M').time()
    except ValueError:
        return None

# --- RUTAS PRINCIPALES (sin cambios) ---
@intern_bp.route('/')
def index():
    viajes = Intern.query.order_by(Intern.id.desc()).all()
    return render_template('ver_intern.html', viajes=viajes)

@intern_bp.route('/crear', methods=['GET', 'POST'])
def crear_intern():
    if request.method == 'POST':
        try:
            flyer_path = None
            if 'flyer_file' in request.files:
                flyer_file = request.files['flyer_file']
                if flyer_file.filename != '':
                    flyer_path = save_flyer(flyer_file)

            nuevo_viaje = Intern(
                nombre_viaje=request.form.get('nombre_viaje'),
                flyer=flyer_path,
                precio_paquete=safe_float(request.form.get('precio_paquete')),
                capacidad=safe_int(request.form.get('capacidad')),
                tipo_moneda=request.form.get('tipo_moneda'),
                tipo_cambio=safe_float(request.form.get('tipo_cambio'), 1),
                pais=request.form.get('pais'),
            )
            db.session.add(nuevo_viaje)
            db.session.flush()

            # --- GUARDAR PRE-ALERTAS ---
            bancos = request.form.getlist('prealerta_banco[]')
            telefonos_entidad = request.form.getlist('prealerta_telefono[]')
            for i in range(len(bancos)):
                if bancos[i]:
                    prealerta = PreAlerta(
                        intern_id=nuevo_viaje.id,
                        banco=bancos[i],
                        telefono_entidad=telefonos_entidad[i]
                    )
                    db.session.add(prealerta)

            # --- GUARDAR LUGARES A VISITAR ---
            nombres_sitio = request.form.getlist('lugar_nombre[]')
            tipos_lugar = request.form.getlist('lugar_tipo[]')
            precios_entrada = request.form.getlist('lugar_precio[]')
            for i in range(len(nombres_sitio)):
                if nombres_sitio[i]:
                    lugar = LugarVisitar(
                        intern_id=nuevo_viaje.id,
                        tipo_lugar=tipos_lugar[i],
                        nombre_sitio=nombres_sitio[i],
                        precio_entrada=safe_float(precios_entrada[i])
                    )
                    db.session.add(lugar)
            
            # --- GUARDAR TRANSPORTES ---
            nombres_transporte = request.form.getlist('transporte_nombre[]')
            tipos_transporte = request.form.getlist('transporte_tipo[]')
            precios_transporte = request.form.getlist('transporte_precio[]')
            for i in range(len(nombres_transporte)):
                if nombres_transporte[i]:
                    transporte = Transporte(
                        intern_id=nuevo_viaje.id,
                        tipo_transporte=tipos_transporte[i],
                        nombre_transporte=nombres_transporte[i],
                        precio=safe_float(precios_transporte[i])
                    )
                    db.session.add(transporte)

            # --- GUARDAR GUÍAS ---
            nombres_guia = request.form.getlist('guia_nombre[]')
            operadores_guia = request.form.getlist('guia_operador[]')
            precios_guia_pp = request.form.getlist('guia_precio_pp[]')
            precios_acarreo = request.form.getlist('guia_acarreo[]')
            for i in range(len(nombres_guia)):
                if nombres_guia[i]:
                    guia = Guia(
                        intern_id=nuevo_viaje.id,
                        nombre=nombres_guia[i],
                        operador=operadores_guia[i],
                        precio_guia_pp=safe_float(precios_guia_pp[i]),
                        precio_acarreo=safe_float(precios_acarreo[i])
                    )
                    db.session.add(guia)

            # --- GUARDAR ESTADÍAS ---
            nombres_estadia = request.form.getlist('estadia_nombre[]')
            precios_pp_estadia = request.form.getlist('estadia_precio_pp[]')
            noches_estadia = request.form.getlist('estadia_noches[]')
            for i in range(len(nombres_estadia)):
                if nombres_estadia[i]:
                    estadia = Estadia(
                        intern_id=nuevo_viaje.id,
                        nombre=nombres_estadia[i],
                        precio_pp=safe_float(precios_pp_estadia[i]),
                        cantidad_noches=safe_int(noches_estadia[i], 1)
                    )
                    db.session.add(estadia)

            # --- GUARDAR AEROLÍNEAS ---
            tipos_transporte_aerolinea = request.form.getlist('aerolinea_tipo_transporte[]')
            nombres_aerolinea = request.form.getlist('aerolinea_nombre[]')
            precios_asientos = request.form.getlist('aerolinea_precio_asientos[]')
            precios_maletas = request.form.getlist('aerolinea_precio_maletas[]')
            equipajes_mano = request.form.getlist('aerolinea_equipaje_mano[]')
            precios_impuestos = request.form.getlist('aerolinea_impuestos[]')
            for i in range(len(nombres_aerolinea)):
                if nombres_aerolinea[i]:
                    aerolinea = Aerolinea(
                        intern_id=nuevo_viaje.id,
                        tipo_transporte=tipos_transporte_aerolinea[i],
                        nombre_aerolinea=nombres_aerolinea[i],
                        precio_asientos=safe_float(precios_asientos[i]),
                        precio_maletas_documentado=safe_float(precios_maletas[i]),
                        equipaje_mano=safe_float(equipajes_mano[i]),
                        precio_impuestos=safe_float(precios_impuestos[i])
                    )
                    db.session.add(aerolinea)

            db.session.commit()
            flash('Plan de viaje creado exitosamente.', 'success')
            return redirect(url_for('intern.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el viaje: {str(e)}', 'danger')
            current_app.logger.error(f"Error en crear_intern: {e}")
    
    paises = ["Panamá", "Nicaragua", "Honduras", "El Salvador", "Guatemala", "México", "Perú", "España"]
    bancos = ["Banco de Costa Rica (BCR)", "Banco Nacional de Costa Rica (BNCR)", "Banco Popular", "Mucap", "Mutual", "BAC Credomatic", "Banco Cathay", "Banco BCT", "Banco CMB", "Banco Davivienda", "Banco General", "Banco Improsa", "Banco Lafise", "Banco Promérica", "Prival Bank", "Scotiabank", "Coopealianza", "Coopeande", "CoopeAnde No. 1", "CoopeAnde No. 2", "CoopeAnde No. 3", "CoopeAnde No. 4", "CoopeAnde No. 5", "CoopeAnde No. 6", "CoopeAnde No. 7", "CoopeAnde No. 8", "CoopeAnde No. 9", "CoopeAnde No. 10", "CoopeAnde No. 11", "CoopeCaja", "Caja de ANDE", "COOPENAE", "COOPEUCHA", "COOPESANRAMON", "COOPESERVIDORES", "COOPEUNA", "CREDECOOP"]
    aerolineas_opciones = sorted(["Avianca", "American Airlines", "Copa", "Volaris", "Jetblue", "Sansa", "Spirit", "United", "Wingo", "KLM", "Iberia", "Lufthansa", "Latam Airlines", "IberoJet", "Delta", "AirFrance", "Alaska", "AeroMéxico", "Arajet", "Air Canadá", "Airtransat", "Green Airways", "Southwest", "Edelweiss", "Frontier", "GOL"])
    
    return render_template('crear_intern.html', 
                           paises=paises, 
                           bancos=bancos, 
                           aerolineas_opciones=aerolineas_opciones)

def update_dynamic_items(model_class, existing_items, submitted_data):
    """
    Función genérica para actualizar, crear y eliminar elementos dinámicos.
    :param model_class: La clase del modelo (ej. LugarVisitar).
    :param existing_items: Lista de objetos existentes en la BD para el viaje.
    :param submitted_data: Lista de diccionarios con los datos enviados desde el form.
    """
    existing_ids = {str(item.id) for item in existing_items}
    submitted_ids = {data['id'] for data in submitted_data if data.get('id')}
    
    # Eliminar
    ids_to_delete = existing_ids - submitted_ids
    if ids_to_delete:
        model_class.query.filter(model_class.id.in_(ids_to_delete)).delete(synchronize_session=False)

    # Actualizar o Crear
    for data in submitted_data:
        item_id = data.get('id')
        if item_id and item_id in existing_ids: # Actualizar
            item = next((item for item in existing_items if str(item.id) == item_id), None)
            if item:
                for key, value in data.items():
                    if key != 'id':
                        setattr(item, key, value)
        else: # Crear
            data.pop('id', None) # Eliminar el id vacío si existe
            new_item = model_class(**data)
            db.session.add(new_item)

@intern_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_intern(id):
    viaje = Intern.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # 1. Actualizar datos principales del viaje
            viaje.nombre_viaje = request.form.get('nombre_viaje')
            viaje.precio_paquete=safe_float(request.form.get('precio_paquete', 0))
            viaje.capacidad=safe_int(request.form.get('capacidad', 0))
            viaje.tipo_moneda=request.form.get('tipo_moneda')
            viaje.tipo_cambio=safe_float(request.form.get('tipo_cambio', 1))
            viaje.pais=request.form.get('pais')

            if 'flyer_file' in request.files:
                flyer_file = request.files['flyer_file']
                if flyer_file.filename != '':
                    if viaje.flyer:
                        old_flyer_path = os.path.join(current_app.static_folder, viaje.flyer)
                        if os.path.exists(old_flyer_path):
                            os.remove(old_flyer_path)
                    viaje.flyer = save_flyer(flyer_file)

            # 2. Procesar Pre-Alertas
            prealerta_data = []
            prealerta_ids = request.form.getlist('prealerta_id[]')
            bancos = request.form.getlist('prealerta_banco[]')
            telefonos = request.form.getlist('prealerta_telefono[]')
            for i in range(len(bancos)):
                if bancos[i]:
                    prealerta_data.append({
                        'id': prealerta_ids[i], 'intern_id': viaje.id,
                        'banco': bancos[i], 'telefono_entidad': telefonos[i]
                    })
            update_dynamic_items(PreAlerta, viaje.prealertas, prealerta_data)

            # 3. Procesar Lugares a Visitar
            lugar_data = []
            lugar_ids = request.form.getlist('lugar_id[]')
            nombres_sitio = request.form.getlist('lugar_nombre[]')
            tipos_lugar = request.form.getlist('lugar_tipo[]')
            precios_entrada = request.form.getlist('lugar_precio[]')
            for i in range(len(nombres_sitio)):
                if nombres_sitio[i]:
                    lugar_data.append({
                        'id': lugar_ids[i], 'intern_id': viaje.id,
                        'nombre_sitio': nombres_sitio[i], 'tipo_lugar': tipos_lugar[i],
                        'precio_entrada': safe_float(precios_entrada[i])
                    })
            update_dynamic_items(LugarVisitar, viaje.lugares, lugar_data)

            # 4. Procesar Transportes
            transporte_data = []
            transporte_ids = request.form.getlist('transporte_id[]')
            nombres_transporte = request.form.getlist('transporte_nombre[]')
            tipos_transporte = request.form.getlist('transporte_tipo[]')
            precios_transporte = request.form.getlist('transporte_precio[]')
            for i in range(len(nombres_transporte)):
                if nombres_transporte[i]:
                    transporte_data.append({
                        'id': transporte_ids[i], 'intern_id': viaje.id,
                        'nombre_transporte': nombres_transporte[i], 'tipo_transporte': tipos_transporte[i],
                        'precio': safe_float(precios_transporte[i])
                    })
            update_dynamic_items(Transporte, viaje.transportes, transporte_data)
            
            # 5. Procesar Guías
            guia_data = []
            guia_ids = request.form.getlist('guia_id[]')
            nombres_guia = request.form.getlist('guia_nombre[]')
            operadores_guia = request.form.getlist('guia_operador[]')
            precios_guia_pp = request.form.getlist('guia_precio_pp[]')
            precios_acarreo = request.form.getlist('guia_acarreo[]')
            for i in range(len(nombres_guia)):
                if nombres_guia[i]:
                    guia_data.append({
                        'id': guia_ids[i], 'intern_id': viaje.id,
                        'nombre': nombres_guia[i], 'operador': operadores_guia[i],
                        'precio_guia_pp': safe_float(precios_guia_pp[i]),
                        'precio_acarreo': safe_float(precios_acarreo[i])
                    })
            update_dynamic_items(Guia, viaje.guias, guia_data)

            # 6. Procesar Estadías
            estadia_data = []
            estadia_ids = request.form.getlist('estadia_id[]')
            nombres_estadia = request.form.getlist('estadia_nombre[]')
            precios_pp_estadia = request.form.getlist('estadia_precio_pp[]')
            noches_estadia = request.form.getlist('estadia_noches[]')
            for i in range(len(nombres_estadia)):
                if nombres_estadia[i]:
                    estadia_data.append({
                        'id': estadia_ids[i], 'intern_id': viaje.id,
                        'nombre': nombres_estadia[i],
                        'precio_pp': safe_float(precios_pp_estadia[i]),
                        'cantidad_noches': safe_int(noches_estadia[i], 1)
                    })
            update_dynamic_items(Estadia, viaje.estadias, estadia_data)

            # 7. Procesar Aerolíneas
            aerolinea_data = []
            aerolinea_ids = request.form.getlist('aerolinea_id[]')
            tipos_transporte_aerolinea = request.form.getlist('aerolinea_tipo_transporte[]')
            nombres_aerolinea = request.form.getlist('aerolinea_nombre[]')
            precios_asientos = request.form.getlist('aerolinea_precio_asientos[]')
            precios_maletas = request.form.getlist('aerolinea_precio_maletas[]')
            equipajes_mano = request.form.getlist('aerolinea_equipaje_mano[]')
            precios_impuestos = request.form.getlist('aerolinea_impuestos[]')
            for i in range(len(nombres_aerolinea)):
                if nombres_aerolinea[i]:
                    aerolinea_data.append({
                        'id': aerolinea_ids[i], 'intern_id': viaje.id,
                        'tipo_transporte': tipos_transporte_aerolinea[i],
                        'nombre_aerolinea': nombres_aerolinea[i],
                        'precio_asientos': safe_float(precios_asientos[i]),
                        'precio_maletas_documentado': safe_float(precios_maletas[i]),
                        'equipaje_mano': safe_float(equipajes_mano[i]),
                        'precio_impuestos': safe_float(precios_impuestos[i])
                    })
            update_dynamic_items(Aerolinea, viaje.aerolineas, aerolinea_data)

            db.session.commit()
            flash('Plan de viaje actualizado correctamente.', 'success')
            return redirect(url_for('intern.detalle_intern', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al editar el viaje: {str(e)}', 'danger')
            current_app.logger.error(f"Error en editar_intern: {e}")

    paises = ["Panamá", "Nicaragua", "Honduras", "El Salvador", "Guatemala", "México", "Perú", "España"]
    bancos = ["Banco de Costa Rica (BCR)", "Banco Nacional de Costa Rica (BNCR)", "Banco Popular", "Mucap", "Mutual", "BAC Credomatic", "Banco Cathay", "Banco BCT", "Banco CMB", "Banco Davivienda", "Banco General", "Banco Improsa", "Banco Lafise", "Banco Promérica", "Prival Bank", "Scotiabank", "Coopealianza", "Coopeande", "CoopeAnde No. 1", "CoopeAnde No. 2", "CoopeAnde No. 3", "CoopeAnde No. 4", "CoopeAnde No. 5", "CoopeAnde No. 6", "CoopeAnde No. 7", "CoopeAnde No. 8", "CoopeAnde No. 9", "CoopeAnde No. 10", "CoopeAnde No. 11", "CoopeCaja", "Caja de ANDE", "COOPENAE", "COOPEUCHA", "COOPESANRAMON", "COOPESERVIDORES", "COOPEUNA", "CREDECOOP"]
    aerolineas_opciones = sorted(["Avianca", "American Airlines", "Copa", "Volaris", "Jetblue", "Sansa", "Spirit", "United", "Wingo", "KLM", "Iberia", "Lufthansa", "Latam Airlines", "IberoJet", "Delta", "AirFrance", "Alaska", "AeroMéxico", "Arajet", "Air Canadá", "Airtransat", "Green Airways", "Southwest", "Edelweiss", "Frontier", "GOL"])

    return render_template('editar_intern.html', 
                           viaje=viaje,
                           paises=paises,
                           bancos=bancos,
                           aerolineas_opciones=aerolineas_opciones)

@intern_bp.route('/ver/<int:id>')
def detalle_intern(id):
    viaje = Intern.query.get_or_404(id)
    total_atracciones = sum(lugar.precio_entrada for lugar in viaje.lugares if lugar.precio_entrada)
    total_transporte = sum(transporte.precio for transporte in viaje.transportes if transporte.precio)
    total_guias_pp = sum((guia.precio_guia_pp or 0) + (guia.precio_acarreo or 0) for guia in viaje.guias)
    total_estadia_pp = sum((estadia.precio_pp or 0) * (estadia.cantidad_noches or 1) for estadia in viaje.estadias)
    
    total_aerolinea_pp = 0
    for aero in viaje.aerolineas:
        total_aerolinea_pp += (aero.precio_asientos or 0) + (aero.precio_maletas_documentado or 0) + (aero.equipaje_mano or 0) + (aero.precio_impuestos or 0)
    
    total_individual_crc = (viaje.precio_paquete or 0) + total_atracciones + total_transporte + total_guias_pp + total_estadia_pp + total_aerolinea_pp
    total_individual_usd = total_individual_crc / viaje.tipo_cambio if viaje.tipo_cambio and viaje.tipo_cambio > 0 else 0

    return render_template('detalle_intern.html', 
                           viaje=viaje,
                           total_atracciones=total_atracciones,
                           total_transporte=total_transporte,
                           total_guias_pp=total_guias_pp,
                           total_estadia_pp=total_estadia_pp,
                           total_aerolinea_pp=total_aerolinea_pp,
                           total_individual_crc=total_individual_crc,
                           total_individual_usd=total_individual_usd)

@intern_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_intern(id):
    viaje = Intern.query.get_or_404(id)
    try:
        if viaje.flyer:
            flyer_path = os.path.join(current_app.static_folder, viaje.flyer)
            if os.path.exists(flyer_path):
                os.remove(flyer_path)
        
        db.session.delete(viaje)
        db.session.commit()
        flash('El plan de viaje ha sido eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el viaje: {str(e)}', 'danger')
    return redirect(url_for('intern.index'))

# --- RUTAS DE EXPORTACIÓN (IMPLEMENTADAS COMPLETAMENTE) ---

def get_trip_data(id):
    """Función auxiliar para obtener todos los datos de un viaje y sus totales."""
    viaje = Intern.query.get_or_404(id)
    
    # Calcular totales
    total_atracciones = sum(l.precio_entrada for l in viaje.lugares if l.precio_entrada)
    total_transporte = sum(t.precio for t in viaje.transportes if t.precio)
    total_guias_pp = sum((g.precio_guia_pp or 0) + (g.precio_acarreo or 0) for g in viaje.guias)
    total_estadia_pp = sum((e.precio_pp or 0) * (e.cantidad_noches or 1) for e in viaje.estadias)
    total_aerolinea_pp = sum((a.precio_asientos or 0) + (a.precio_maletas_documentado or 0) + (a.equipaje_mano or 0) + (a.precio_impuestos or 0) for a in viaje.aerolineas)
    
    total_individual_crc = (viaje.precio_paquete or 0) + total_atracciones + total_transporte + total_guias_pp + total_estadia_pp + total_aerolinea_pp
    total_individual_usd = total_individual_crc / viaje.tipo_cambio if viaje.tipo_cambio and viaje.tipo_cambio > 0 else 0
    
    totals = {
        "atracciones": total_atracciones,
        "transporte": total_transporte,
        "guias": total_guias_pp,
        "estadia": total_estadia_pp,
        "aerolinea": total_aerolinea_pp,
        "total_crc": total_individual_crc,
        "total_usd": total_individual_usd
    }
    
    return viaje, totals

def write_section_txt(title, items, formatter):
    """Genera una sección para el archivo de texto."""
    content = ""
    if items:
        content += f"{title.upper()}\n"
        content += "-"*len(title) + "\n"
        for i, item in enumerate(items, 1):
            content += f"  {i}. {formatter(item)}\n"
        content += "\n"
    return content

@intern_bp.route('/exportar/txt/<int:id>')
def exportar_txt(id):
    viaje, totals = get_trip_data(id)
    
    content = f"PLAN DE VIAJE: {viaje.nombre_viaje}\n"
    content += "="*40 + "\n\n"
    content += f"DESTINO\n"
    content += f"País: {viaje.pais}\n"
    content += f"Precio Paquete: {viaje.precio_paquete or 0:.2f} {viaje.tipo_moneda}\n"
    content += f"Capacidad: {viaje.capacidad} personas\n\n"

    content += write_section_txt("Pre-Alertas", viaje.prealertas, 
        lambda p: f"Banco: {p.banco}, Tel: {p.telefono_entidad or 'N/A'}")
    content += write_section_txt("Lugares a Visitar", viaje.lugares, 
        lambda l: f"{l.nombre_sitio} ({l.tipo_lugar}): {l.precio_entrada or 0:.2f} CRC")
    content += write_section_txt("Transportes", viaje.transportes, 
        lambda t: f"{t.nombre_transporte} ({t.tipo_transporte}): {t.precio or 0:.2f} CRC")
    content += write_section_txt("Guías", viaje.guias, 
        lambda g: f"{g.nombre} (Operador: {g.operador or 'N/A'}): {((g.precio_guia_pp or 0) + (g.precio_acarreo or 0)):.2f} CRC")
    content += write_section_txt("Estadías", viaje.estadias, 
        lambda e: f"{e.nombre} ({e.cantidad_noches} noches): {(e.precio_pp or 0) * (e.cantidad_noches or 1):.2f} CRC")
    content += write_section_txt("Aerolíneas", viaje.aerolineas, 
        lambda a: f"{a.nombre_aerolinea}: {((a.precio_asientos or 0) + (a.precio_maletas_documentado or 0) + (a.equipaje_mano or 0) + (a.precio_impuestos or 0)):.2f} CRC")

    content += "="*40 + "\n"
    content += "TOTALES GENERALES\n"
    content += "="*40 + "\n"
    content += f"Total Individual (CRC): {totals['total_crc']:.2f}\n"
    content += f"Total Individual (USD): {totals['total_usd']:.2f}\n"

    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename=viaje_{viaje.id}_{viaje.nombre_viaje}.txt"
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response

class PDF(FPDF):
    def __init__(self, trip_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trip_name = trip_name

    def header(self):
        self.set_font('Arial', 'B', 15)
        # Usar 'latin-1' para codificar, manejando errores
        trip_name_encoded = self.trip_name.encode('latin-1', 'replace').decode('latin-1')
        self.cell(0, 10, f'Plan de Viaje: {trip_name_encoded}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title.upper(), 0, 1, 'L')
        self.ln(2)
    
    def chapter_body(self, content):
        self.set_font('Arial', '', 11)
        # Usar 'latin-1' para codificar, manejando errores
        content_encoded = content.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 8, content_encoded)
        self.ln()

@intern_bp.route('/exportar/pdf/<int:id>')
def exportar_pdf(id):
    viaje, totals = get_trip_data(id)
    
    pdf = PDF(viaje.nombre_viaje)
    pdf.add_page()
    
    pdf.chapter_title('DESTINO')
    pdf.chapter_body(
        f"País: {viaje.pais}\n"
        f"Precio Paquete: {viaje.precio_paquete or 0:.2f} {viaje.tipo_moneda}\n"
        f"Capacidad: {viaje.capacidad} personas"
    )

    if viaje.prealertas:
        pdf.chapter_title('PRE-ALERTAS')
        body = ""
        for p in viaje.prealertas:
            body += f"- Banco: {p.banco}, Tel: {p.telefono_entidad or 'N/A'}\n"
        pdf.chapter_body(body)

    if viaje.lugares:
        pdf.chapter_title('LUGARES A VISITAR')
        body = ""
        for lugar in viaje.lugares:
            body += f"- {lugar.nombre_sitio} ({lugar.tipo_lugar}): {lugar.precio_entrada or 0:.2f} CRC\n"
        pdf.chapter_body(body)

    if viaje.transportes:
        pdf.chapter_title('TRANSPORTES')
        body = ""
        for t in viaje.transportes:
            body += f"- {t.nombre_transporte} ({t.tipo_transporte}): {t.precio or 0:.2f} CRC\n"
        pdf.chapter_body(body)

    if viaje.guias:
        pdf.chapter_title('GUÍAS')
        body = ""
        for g in viaje.guias:
            costo_guia = (g.precio_guia_pp or 0) + (g.precio_acarreo or 0)
            body += f"- {g.nombre} (Operador: {g.operador or 'N/A'}): {costo_guia:.2f} CRC\n"
        pdf.chapter_body(body)

    if viaje.estadias:
        pdf.chapter_title('ESTADÍAS')
        body = ""
        for e in viaje.estadias:
            costo_estadia = (e.precio_pp or 0) * (e.cantidad_noches or 1)
            body += f"- {e.nombre} ({e.cantidad_noches} noches): {costo_estadia:.2f} CRC\n"
        pdf.chapter_body(body)

    if viaje.aerolineas:
        pdf.chapter_title('AEROLÍNEAS')
        body = ""
        for a in viaje.aerolineas:
            costo_aerolinea = (a.precio_asientos or 0) + (a.precio_maletas_documentado or 0) + (a.equipaje_mano or 0) + (a.precio_impuestos or 0)
            body += f"- {a.nombre_aerolinea}: {costo_aerolinea:.2f} CRC\n"
        pdf.chapter_body(body)
    
    pdf.chapter_title('TOTALES GENERALES')
    pdf.chapter_body(
        f"Total Individual (CRC): {totals['total_crc']:.2f}\n"
        f"Total Individual (USD): {totals['total_usd']:.2f}"
    )

    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=viaje_{viaje.id}_{viaje.nombre_viaje}.pdf'
    return response

@intern_bp.route('/exportar/jpg/<int:id>')
def exportar_jpg(id):
    flash('La exportación a JPG genera una imagen de resumen con los datos principales.', 'info')
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        flash('La librería Pillow es necesaria para exportar a JPG. Instálala con "pip install Pillow".', 'danger')
        return redirect(url_for('intern.detalle_intern', id=id))

    viaje, totals = get_trip_data(id)
    
    # 1. Build Content Lines
    lines = []
    
    def add_section_lines(title, items, formatter):
        if items:
            lines.append((title.upper(), 'bold'))
            lines.extend([(f"  - {formatter(item)}", 'normal') for item in items])
            lines.append(("", 'spacer')) # Spacer

    lines.append((f"PLAN DE VIAJE: {viaje.nombre_viaje}", 'title'))
    lines.append((f"País: {viaje.pais}", 'normal'))
    lines.append(("", 'spacer'))

    add_section_lines("Pre-Alertas", viaje.prealertas, lambda p: f"Banco: {p.banco}")
    add_section_lines("Atracciones", viaje.lugares, lambda l: f"{l.nombre_sitio}: {l.precio_entrada or 0:.2f} CRC")
    add_section_lines("Transportes", viaje.transportes, lambda t: f"{t.nombre_transporte}: {t.precio or 0:.2f} CRC")
    add_section_lines("Guías", viaje.guias, lambda g: f"{g.nombre}: {((g.precio_guia_pp or 0) + (g.precio_acarreo or 0)):.2f} CRC")
    add_section_lines("Estadías", viaje.estadias, lambda e: f"{e.nombre} ({e.cantidad_noches} noches): {(e.precio_pp or 0) * (e.cantidad_noches or 1):.2f} CRC")
    add_section_lines("Aerolíneas", viaje.aerolineas, lambda a: f"{a.nombre_aerolinea}: {((a.precio_asientos or 0) + (a.precio_maletas_documentado or 0) + (a.equipaje_mano or 0) + (a.precio_impuestos or 0)):.2f} CRC")

    lines.append(("TOTALES GENERALES", 'bold'))
    lines.append((f"  Total (CRC): {totals['total_crc']:.2f}", 'normal'))
    lines.append((f"  Total (USD): {totals['total_usd']:.2f}", 'normal'))

    # 2. Setup Fonts and Image Dimensions
    try:
        font_title = ImageFont.truetype("arial.ttf", 32)
        font_bold = ImageFont.truetype("arialbd.ttf", 22)
        font_normal = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font_title = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_normal = ImageFont.load_default()

    margin = 40
    line_spacing = 10
    image_width = 800
    current_height = margin

    # Dummy draw to calculate height
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    for text, style in lines:
        font = font_normal
        if style == 'title': font = font_title
        if style == 'bold': font = font_bold
        
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        current_height += (bbox[3] - bbox[1]) + line_spacing

    image_height = current_height + margin

    # 3. Create Image and Draw Text
    img = Image.new('RGB', (image_width, image_height), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    y_text = margin
    for text, style in lines:
        font = font_normal
        fill_color = (50, 50, 50) # Dark Gray
        if style == 'title':
            font = font_title
            fill_color = (0, 0, 0) # Black
        elif style == 'bold':
            font = font_bold
            fill_color = (0, 0, 0) # Black
        
        d.text((margin, y_text), text, font=font, fill=fill_color)
        bbox = d.textbbox((0, 0), text, font=font)
        y_text += (bbox[3] - bbox[1]) + line_spacing

    # 4. Save and Return
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=90)
    img_io.seek(0)
    
    response = make_response(img_io.getvalue())
    response.headers['Content-Type'] = 'image/jpeg'
    response.headers['Content-Disposition'] = f'attachment; filename=viaje_{viaje.id}_{viaje.nombre_viaje}.jpg'
    return response

@intern_bp.route('/exportar/excel/<int:id>')
def exportar_excel(id):
    viaje, totals = get_trip_data(id)
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen del Viaje"

    # Estilos
    bold_font = Font(bold=True, size=14)
    header_font = Font(bold=True)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    def set_header(cell, text):
        ws[cell] = text
        ws[cell].font = header_font

    # Título
    ws['A1'] = f"Plan de Viaje: {viaje.nombre_viaje}"
    ws.merge_cells('A1:E1')
    ws['A1'].font = bold_font
    
    current_row = 3
    
    # Función para añadir secciones
    def add_section(title, headers, items, item_formatter):
        nonlocal current_row
        if not items: return
        
        ws[f'A{current_row}'] = title.upper()
        ws[f'A{current_row}'].font = bold_font
        current_row += 1
        
        for i, header in enumerate(headers):
            col = chr(65 + i) # A, B, C...
            set_header(f'{col}{current_row}', header)
        
        current_row += 1
        
        for item in items:
            row_data = item_formatter(item)
            for i, data in enumerate(row_data):
                col = chr(65 + i)
                ws[f'{col}{current_row}'] = data
            current_row += 1
        current_row += 1 # Espacio entre secciones

    # Añadir todas las secciones
    add_section("Pre-Alertas", ["Banco", "Teléfono"], viaje.prealertas,
        lambda p: [p.banco, p.telefono_entidad or "N/A"])
    add_section("Lugares a Visitar", ["Sitio", "Tipo", "Precio (CRC)"], viaje.lugares,
        lambda l: [l.nombre_sitio, l.tipo_lugar, l.precio_entrada or 0])
    add_section("Transportes", ["Nombre", "Tipo", "Precio (CRC)"], viaje.transportes,
        lambda t: [t.nombre_transporte, t.tipo_transporte, t.precio or 0])
    add_section("Guías", ["Nombre", "Operador", "Costo PP (CRC)"], viaje.guias,
        lambda g: [g.nombre, g.operador, (g.precio_guia_pp or 0) + (g.precio_acarreo or 0)])
    add_section("Estadías", ["Lugar", "Noches", "Costo Total PP (CRC)"], viaje.estadias,
        lambda e: [e.nombre, e.cantidad_noches, (e.precio_pp or 0) * (e.cantidad_noches or 1)])
    add_section("Aerolíneas", ["Aerolínea", "Costo Total PP (CRC)"], viaje.aerolineas,
        lambda a: [a.nombre_aerolinea, (a.precio_asientos or 0) + (a.precio_maletas_documentado or 0) + (a.equipaje_mano or 0) + (a.precio_impuestos or 0)])

    # Totales
    ws[f'A{current_row}'] = "TOTALES"
    ws[f'A{current_row}'].font = bold_font
    current_row += 1
    ws[f'A{current_row}'] = "Total Individual (CRC)"
    ws[f'B{current_row}'] = totals['total_crc']
    ws[f'B{current_row}'].number_format = '#,##0.00'
    current_row += 1
    ws[f'A{current_row}'] = "Total Individual (USD)"
    ws[f'B{current_row}'] = totals['total_usd']
    ws[f'B{current_row}'].number_format = '#,##0.00'

    # Ajustar ancho de columnas (CORREGIDO)
    dims = {}
    for row in ws.rows:
        for cell in row:
            if cell.value and not isinstance(cell, MergedCell):
                dims[cell.column_letter] = max((dims.get(cell.column_letter, 0), len(str(cell.value))))
    for col, max_len in dims.items():
        ws.column_dimensions[col].width = max_len + 2


    excel_io = io.BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)

    response = make_response(excel_io.getvalue())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = f'attachment; filename=viaje_{viaje.id}_{viaje.nombre_viaje}.xlsx'
    return response
