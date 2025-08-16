from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, Response
from models import db
from datetime import datetime, time
import json
from fpdf import FPDF
import io

# Helper para convertir string a objeto time, manejando strings vacíos
def to_time(time_str):
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, '%H:%M').time()
    except (ValueError, TypeError):
        return None

# Helper para convertir string a objeto date, manejando strings vacíos
def to_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

intern_bp = Blueprint('intern', __name__, template_folder='templates', url_prefix='/intern')

# Filtro Jinja personalizado para convertir una cadena JSON en un objeto Python
@intern_bp.app_template_filter('fromjson')
def from_json_filter(json_string):
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return []

# --- MODELOS DE BASE DE DATOS ---

class InternationalTravel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo_destino = db.Column(db.String(200), nullable=False)
    flyer_url = db.Column(db.String(500))
    nombre_viaje = db.Column(db.String(200), nullable=False)
    precio_paquete = db.Column(db.Float, default=0.0)
    capacidad = db.Column(db.Integer, default=0)
    tipo_moneda = db.Column(db.String(10), default='CRC')
    tipo_cambio = db.Column(db.Float, default=1.0)
    pais = db.Column(db.String(100))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    prealertas = db.relationship('PreAlerta', backref='travel', lazy=True, cascade="all, delete-orphan")
    lugares = db.relationship('LugarVisitar', backref='travel', lazy=True, cascade="all, delete-orphan")
    transportes = db.relationship('Transporte', backref='travel', lazy=True, cascade="all, delete-orphan")
    guias = db.relationship('Guia', backref='travel', lazy=True, cascade="all, delete-orphan")
    estadias = db.relationship('Estadia', backref='travel', lazy=True, cascade="all, delete-orphan")
    aerolineas = db.relationship('Aerolinea', backref='travel', lazy=True, cascade="all, delete-orphan")

class PreAlerta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    banco = db.Column(db.String(150))
    telefono_entidad = db.Column(db.String(50))
    fecha_prealerta = db.Column(db.Date)
    nombre_asesor = db.Column(db.String(150))
    hora_prealerta = db.Column(db.Time)
    numero_prealerta = db.Column(db.String(100))
    fecha_desde = db.Column(db.Date)
    fecha_hasta = db.Column(db.Date)

class LugarVisitar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    tipo_lugar = db.Column(db.String(100))
    nombre_sitio = db.Column(db.String(200))
    precio_entrada = db.Column(db.Float, default=0.0)
    fecha_reserva = db.Column(db.Date)
    guia_local = db.Column(db.String(5)) # Si/No
    nombre_guia = db.Column(db.String(150))
    telefono_lugar = db.Column(db.String(50))
    telefono_contacto = db.Column(db.String(50))
    whatsapp_contacto = db.Column(db.String(50))
    enlaces = db.Column(db.Text)
    nota = db.Column(db.Text)
    email = db.Column(db.String(120))

class Transporte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    tipo_transporte = db.Column(db.String(100))
    nombre_transporte = db.Column(db.String(200))
    conductor = db.Column(db.String(150))
    precio = db.Column(db.Float, default=0.0)
    fecha_contratacion = db.Column(db.Date)
    telefono_lugar = db.Column(db.String(50))
    telefono_contacto = db.Column(db.String(50))
    whatsapp_contacto = db.Column(db.String(50))
    email = db.Column(db.String(120))
    enlaces = db.Column(db.Text)
    nota = db.Column(db.Text)

class Guia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    nombre = db.Column(db.String(150))
    telefono = db.Column(db.String(50))
    operador = db.Column(db.String(150))
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(50))
    precio_guia_pp = db.Column(db.Float, default=0.0)
    cpl = db.Column(db.String(5)) # Si/No
    fecha_disponible = db.Column(db.Date)
    reserva = db.Column(db.String(100))
    precio_acarreo = db.Column(db.Float, default=0.0)
    enlaces = db.Column(db.Text)
    nota = db.Column(db.Text)
    fecha_reserva = db.Column(db.Date)

class Estadia(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    nombre = db.Column(db.String(200))
    contacto = db.Column(db.String(150))
    telefono = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    email = db.Column(db.String(120))
    precio_pp = db.Column(db.Float, default=0.0)
    cpl = db.Column(db.String(5)) # Si/No
    fecha_disponible_reserva = db.Column(db.Date)
    alimentacion_incluida = db.Column(db.String(5)) # Si/No
    cantidad_noches = db.Column(db.Integer, default=1)
    enlaces = db.Column(db.Text)
    nota = db.Column(db.Text)
    fecha_entrada = db.Column(db.Date)
    fecha_salida = db.Column(db.Date)

class Aerolinea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    travel_id = db.Column(db.Integer, db.ForeignKey('international_travel.id'), nullable=False)
    tipo_transporte = db.Column(db.String(100))
    nombre_aerolinea = db.Column(db.String(150))
    telefono_aerolinea = db.Column(db.String(50))
    email = db.Column(db.String(120))
    whatsapp = db.Column(db.String(50))
    fecha_prealertar = db.Column(db.Date)
    enlace_prealertar = db.Column(db.String(500))
    numero_vuelo = db.Column(db.String(50))
    horario_salida = db.Column(db.Time)
    horario_llegada = db.Column(db.Time)
    nombre_aeropuerto = db.Column(db.String(200))
    telefono_aeropuerto = db.Column(db.String(50))
    precio_asientos = db.Column(db.Float, default=0.0)
    precio_maletas_doc = db.Column(db.Float, default=0.0)
    equipaje_mano = db.Column(db.Float, default=0.0)
    precio_estandar = db.Column(db.Float, default=0.0)
    precio_mas_equipo = db.Column(db.Float, default=0.0)
    precio_salida_rapida = db.Column(db.Float, default=0.0)
    precio_premium = db.Column(db.Float, default=0.0)
    precio_vip = db.Column(db.Float, default=0.0)
    precio_basic = db.Column(db.Float, default=0.0)
    precio_classic = db.Column(db.Float, default=0.0)
    precio_flexible = db.Column(db.Float, default=0.0)
    precio_impuestos = db.Column(db.Float, default=0.0)
    otros_costos_json = db.Column(db.Text, default='[]')
    fecha_compra = db.Column(db.Date)


# --- RUTAS DEL BLUEPRINT ---

@intern_bp.route('/')
def ver_intern():
    viajes = InternationalTravel.query.order_by(InternationalTravel.fecha_creacion.desc()).all()
    return render_template('ver_intern.html', viajes=viajes)

@intern_bp.route('/crear', methods=['GET', 'POST'])
def crear_intern():
    if request.method == 'POST':
        nuevo_viaje = InternationalTravel(
            titulo_destino=request.form.get('titulo_destino'),
            nombre_viaje=request.form.get('nombre_viaje'),
            precio_paquete=float(request.form.get('precio_paquete') or 0.0),
            capacidad=int(request.form.get('capacidad') or 0),
            tipo_moneda=request.form.get('tipo_moneda'),
            tipo_cambio=float(request.form.get('tipo_cambio') or 1.0),
            pais=request.form.get('pais')
        )
        db.session.add(nuevo_viaje)
        db.session.flush()

        for i in range(len(request.form.getlist('prealerta_banco[]'))):
            if request.form.getlist('prealerta_banco[]')[i]:
                db.session.add(PreAlerta(travel_id=nuevo_viaje.id, banco=request.form.getlist('prealerta_banco[]')[i], telefono_entidad=request.form.getlist('prealerta_telefono[]')[i], fecha_prealerta=to_date(request.form.getlist('prealerta_fecha[]')[i]), nombre_asesor=request.form.getlist('prealerta_asesor[]')[i], hora_prealerta=to_time(request.form.getlist('prealerta_hora[]')[i]), numero_prealerta=request.form.getlist('prealerta_numero[]')[i], fecha_desde=to_date(request.form.getlist('prealerta_desde[]')[i]), fecha_hasta=to_date(request.form.getlist('prealerta_hasta[]')[i])))
        
        for i in range(len(request.form.getlist('lugar_nombre[]'))):
            if request.form.getlist('lugar_nombre[]')[i]:
                db.session.add(LugarVisitar(travel_id=nuevo_viaje.id, tipo_lugar=request.form.getlist('lugar_tipo[]')[i], nombre_sitio=request.form.getlist('lugar_nombre[]')[i], precio_entrada=float(request.form.getlist('lugar_precio[]')[i] or 0.0), fecha_reserva=to_date(request.form.getlist('lugar_fecha_reserva[]')[i]), guia_local=request.form.getlist('lugar_guia_local[]')[i], nombre_guia=request.form.getlist('lugar_nombre_guia[]')[i], telefono_lugar=request.form.getlist('lugar_telefono_lugar[]')[i], telefono_contacto=request.form.getlist('lugar_telefono_contacto[]')[i], whatsapp_contacto=request.form.getlist('lugar_whatsapp_contacto[]')[i], email=request.form.getlist('lugar_email[]')[i], enlaces=request.form.getlist('lugar_enlaces[]')[i], nota=request.form.getlist('lugar_nota[]')[i]))

        for i in range(len(request.form.getlist('transporte_nombre[]'))):
            if request.form.getlist('transporte_nombre[]')[i]:
                db.session.add(Transporte(travel_id=nuevo_viaje.id, tipo_transporte=request.form.getlist('transporte_tipo[]')[i], nombre_transporte=request.form.getlist('transporte_nombre[]')[i], precio=float(request.form.getlist('transporte_precio[]')[i] or 0.0), conductor=request.form.getlist('transporte_conductor[]')[i], fecha_contratacion=to_date(request.form.getlist('transporte_fecha_contratacion[]')[i]), telefono_lugar=request.form.getlist('transporte_telefono_lugar[]')[i], telefono_contacto=request.form.getlist('transporte_telefono_contacto[]')[i], whatsapp_contacto=request.form.getlist('transporte_whatsapp_contacto[]')[i], email=request.form.getlist('transporte_email[]')[i], enlaces=request.form.getlist('transporte_enlaces[]')[i], nota=request.form.getlist('transporte_nota[]')[i]))

        for i in range(len(request.form.getlist('guia_nombre[]'))):
            if request.form.getlist('guia_nombre[]')[i]:
                db.session.add(Guia(travel_id=nuevo_viaje.id, nombre=request.form.getlist('guia_nombre[]')[i], telefono=request.form.getlist('guia_telefono[]')[i], operador=request.form.getlist('guia_operador[]')[i], email=request.form.getlist('guia_email[]')[i], whatsapp=request.form.getlist('guia_whatsapp[]')[i], precio_guia_pp=float(request.form.getlist('guia_precio_pp[]')[i] or 0.0), cpl=request.form.getlist('guia_cpl[]')[i], fecha_disponible=to_date(request.form.getlist('guia_fecha_disponible[]')[i]), reserva=request.form.getlist('guia_reserva[]')[i], precio_acarreo=float(request.form.getlist('guia_precio_acarreo[]')[i] or 0.0), enlaces=request.form.getlist('guia_enlaces[]')[i], nota=request.form.getlist('guia_nota[]')[i], fecha_reserva=to_date(request.form.getlist('guia_fecha_reserva[]')[i])))

        for i in range(len(request.form.getlist('estadia_nombre[]'))):
            if request.form.getlist('estadia_nombre[]')[i]:
                db.session.add(Estadia(travel_id=nuevo_viaje.id, nombre=request.form.getlist('estadia_nombre[]')[i], contacto=request.form.getlist('estadia_contacto[]')[i], telefono=request.form.getlist('estadia_telefono[]')[i], whatsapp=request.form.getlist('estadia_whatsapp[]')[i], email=request.form.getlist('estadia_email[]')[i], precio_pp=float(request.form.getlist('estadia_precio_pp[]')[i] or 0.0), cpl=request.form.getlist('estadia_cpl[]')[i], fecha_disponible_reserva=to_date(request.form.getlist('estadia_fecha_disponible[]')[i]), alimentacion_incluida=request.form.getlist('estadia_alimentacion[]')[i], cantidad_noches=int(request.form.getlist('estadia_noches[]')[i] or 1), enlaces=request.form.getlist('estadia_enlaces[]')[i], nota=request.form.getlist('estadia_nota[]')[i], fecha_entrada=to_date(request.form.getlist('estadia_fecha_entrada[]')[i]), fecha_salida=to_date(request.form.getlist('estadia_fecha_salida[]')[i])))
        
        tipos_transporte = request.form.getlist('aerolinea_tipo_transporte[]')
        for i in range(len(tipos_transporte)):
            if tipos_transporte[i]:
                otros_costos_list = []
                for j in range(1, 5):
                    desc = request.form.getlist(f'aerolinea_desc_{j}[]')[i]
                    costo = request.form.getlist(f'aerolinea_costo_{j}[]')[i]
                    cant = request.form.getlist(f'aerolinea_cant_{j}[]')[i]
                    if desc and (costo or cant):
                        otros_costos_list.append({'descripcion': desc, 'costo': float(costo or 0.0), 'cantidad': int(cant or 1)})
                
                db.session.add(Aerolinea(travel_id=nuevo_viaje.id, tipo_transporte=tipos_transporte[i], nombre_aerolinea=request.form.getlist('aerolinea_nombre[]')[i], telefono_aerolinea=request.form.getlist('aerolinea_telefono[]')[i], email=request.form.getlist('aerolinea_email[]')[i], whatsapp=request.form.getlist('aerolinea_whatsapp[]')[i], fecha_prealertar=to_date(request.form.getlist('aerolinea_fecha_prealerta[]')[i]), enlace_prealertar=request.form.getlist('aerolinea_enlace_prealerta[]')[i], numero_vuelo=request.form.getlist('aerolinea_num_vuelo[]')[i], horario_salida=to_time(request.form.getlist('aerolinea_hora_salida[]')[i]), horario_llegada=to_time(request.form.getlist('aerolinea_hora_llegada[]')[i]), nombre_aeropuerto=request.form.getlist('aerolinea_aeropuerto[]')[i], telefono_aeropuerto=request.form.getlist('aerolinea_tel_aeropuerto[]')[i], precio_asientos=float(request.form.getlist('aerolinea_p_asientos[]')[i] or 0.0), precio_maletas_doc=float(request.form.getlist('aerolinea_p_maletas[]')[i] or 0.0), equipaje_mano=float(request.form.getlist('aerolinea_p_equipaje_mano[]')[i] or 0.0), precio_estandar=float(request.form.getlist('aerolinea_p_estandar[]')[i] or 0.0), precio_mas_equipo=float(request.form.getlist('aerolinea_p_mas_equipo[]')[i] or 0.0), precio_salida_rapida=float(request.form.getlist('aerolinea_p_salida_rapida[]')[i] or 0.0), precio_premium=float(request.form.getlist('aerolinea_p_premium[]')[i] or 0.0), precio_vip=float(request.form.getlist('aerolinea_p_vip[]')[i] or 0.0), precio_basic=float(request.form.getlist('aerolinea_p_basic[]')[i] or 0.0), precio_classic=float(request.form.getlist('aerolinea_p_classic[]')[i] or 0.0), precio_flexible=float(request.form.getlist('aerolinea_p_flexible[]')[i] or 0.0), precio_impuestos=float(request.form.getlist('aerolinea_p_impuestos[]')[i] or 0.0), otros_costos_json=json.dumps(otros_costos_list), fecha_compra=to_date(request.form.getlist('aerolinea_fecha_compra[]')[i])))

        try:
            db.session.commit()
            flash('Viaje internacional creado con éxito.', 'success')
            return redirect(url_for('intern.ver_intern'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el viaje: {str(e)}', 'danger')

    return render_template('crear_intern.html')

@intern_bp.route('/detalle/<int:id>')
def detalle_intern(id):
    viaje = InternationalTravel.query.get_or_404(id)
    return render_template('detalle_intern.html', viaje=viaje)

@intern_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_intern(id):
    viaje = InternationalTravel.query.get_or_404(id)
    if request.method == 'POST':
        viaje.titulo_destino = request.form.get('titulo_destino')
        viaje.nombre_viaje = request.form.get('nombre_viaje')
        viaje.precio_paquete = float(request.form.get('precio_paquete') or 0.0)
        viaje.capacidad = int(request.form.get('capacidad') or 0)
        viaje.tipo_moneda = request.form.get('tipo_moneda')
        viaje.tipo_cambio = float(request.form.get('tipo_cambio') or 1.0)
        viaje.pais = request.form.get('pais')

        for item in viaje.prealertas: db.session.delete(item)
        for i in range(len(request.form.getlist('prealerta_banco[]'))):
            if request.form.getlist('prealerta_banco[]')[i]:
                db.session.add(PreAlerta(travel_id=viaje.id, banco=request.form.getlist('prealerta_banco[]')[i], telefono_entidad=request.form.getlist('prealerta_telefono[]')[i], fecha_prealerta=to_date(request.form.getlist('prealerta_fecha[]')[i]), nombre_asesor=request.form.getlist('prealerta_asesor[]')[i], hora_prealerta=to_time(request.form.getlist('prealerta_hora[]')[i]), numero_prealerta=request.form.getlist('prealerta_numero[]')[i], fecha_desde=to_date(request.form.getlist('prealerta_desde[]')[i]), fecha_hasta=to_date(request.form.getlist('prealerta_hasta[]')[i])))

        for item in viaje.lugares: db.session.delete(item)
        for i in range(len(request.form.getlist('lugar_nombre[]'))):
            if request.form.getlist('lugar_nombre[]')[i]:
                db.session.add(LugarVisitar(travel_id=viaje.id, tipo_lugar=request.form.getlist('lugar_tipo[]')[i], nombre_sitio=request.form.getlist('lugar_nombre[]')[i], precio_entrada=float(request.form.getlist('lugar_precio[]')[i] or 0.0), fecha_reserva=to_date(request.form.getlist('lugar_fecha_reserva[]')[i]), guia_local=request.form.getlist('lugar_guia_local[]')[i], nombre_guia=request.form.getlist('lugar_nombre_guia[]')[i], telefono_lugar=request.form.getlist('lugar_telefono_lugar[]')[i], telefono_contacto=request.form.getlist('lugar_telefono_contacto[]')[i], whatsapp_contacto=request.form.getlist('lugar_whatsapp_contacto[]')[i], email=request.form.getlist('lugar_email[]')[i], enlaces=request.form.getlist('lugar_enlaces[]')[i], nota=request.form.getlist('lugar_nota[]')[i]))

        for item in viaje.transportes: db.session.delete(item)
        for i in range(len(request.form.getlist('transporte_nombre[]'))):
            if request.form.getlist('transporte_nombre[]')[i]:
                db.session.add(Transporte(travel_id=viaje.id, tipo_transporte=request.form.getlist('transporte_tipo[]')[i], nombre_transporte=request.form.getlist('transporte_nombre[]')[i], precio=float(request.form.getlist('transporte_precio[]')[i] or 0.0), conductor=request.form.getlist('transporte_conductor[]')[i], fecha_contratacion=to_date(request.form.getlist('transporte_fecha_contratacion[]')[i]), telefono_lugar=request.form.getlist('transporte_telefono_lugar[]')[i], telefono_contacto=request.form.getlist('transporte_telefono_contacto[]')[i], whatsapp_contacto=request.form.getlist('transporte_whatsapp_contacto[]')[i], email=request.form.getlist('transporte_email[]')[i], enlaces=request.form.getlist('transporte_enlaces[]')[i], nota=request.form.getlist('transporte_nota[]')[i]))

        for item in viaje.guias: db.session.delete(item)
        for i in range(len(request.form.getlist('guia_nombre[]'))):
            if request.form.getlist('guia_nombre[]')[i]:
                db.session.add(Guia(travel_id=viaje.id, nombre=request.form.getlist('guia_nombre[]')[i], telefono=request.form.getlist('guia_telefono[]')[i], operador=request.form.getlist('guia_operador[]')[i], email=request.form.getlist('guia_email[]')[i], whatsapp=request.form.getlist('guia_whatsapp[]')[i], precio_guia_pp=float(request.form.getlist('guia_precio_pp[]')[i] or 0.0), cpl=request.form.getlist('guia_cpl[]')[i], fecha_disponible=to_date(request.form.getlist('guia_fecha_disponible[]')[i]), reserva=request.form.getlist('guia_reserva[]')[i], precio_acarreo=float(request.form.getlist('guia_precio_acarreo[]')[i] or 0.0), enlaces=request.form.getlist('guia_enlaces[]')[i], nota=request.form.getlist('guia_nota[]')[i], fecha_reserva=to_date(request.form.getlist('guia_fecha_reserva[]')[i])))

        for item in viaje.estadias: db.session.delete(item)
        for i in range(len(request.form.getlist('estadia_nombre[]'))):
            if request.form.getlist('estadia_nombre[]')[i]:
                db.session.add(Estadia(travel_id=viaje.id, nombre=request.form.getlist('estadia_nombre[]')[i], contacto=request.form.getlist('estadia_contacto[]')[i], telefono=request.form.getlist('estadia_telefono[]')[i], whatsapp=request.form.getlist('estadia_whatsapp[]')[i], email=request.form.getlist('estadia_email[]')[i], precio_pp=float(request.form.getlist('estadia_precio_pp[]')[i] or 0.0), cpl=request.form.getlist('estadia_cpl[]')[i], fecha_disponible_reserva=to_date(request.form.getlist('estadia_fecha_disponible[]')[i]), alimentacion_incluida=request.form.getlist('estadia_alimentacion[]')[i], cantidad_noches=int(request.form.getlist('estadia_noches[]')[i] or 1), enlaces=request.form.getlist('estadia_enlaces[]')[i], nota=request.form.getlist('estadia_nota[]')[i], fecha_entrada=to_date(request.form.getlist('estadia_fecha_entrada[]')[i]), fecha_salida=to_date(request.form.getlist('estadia_fecha_salida[]')[i])))

        for item in viaje.aerolineas: db.session.delete(item)
        tipos_transporte = request.form.getlist('aerolinea_tipo_transporte[]')
        for i in range(len(tipos_transporte)):
            if tipos_transporte[i]:
                otros_costos_list = []
                for j in range(1, 5):
                    desc = request.form.getlist(f'aerolinea_desc_{j}[]')[i]
                    costo = request.form.getlist(f'aerolinea_costo_{j}[]')[i]
                    cant = request.form.getlist(f'aerolinea_cant_{j}[]')[i]
                    if desc and (costo or cant):
                        otros_costos_list.append({'descripcion': desc, 'costo': float(costo or 0.0), 'cantidad': int(cant or 1)})

                db.session.add(Aerolinea(travel_id=viaje.id, tipo_transporte=tipos_transporte[i], nombre_aerolinea=request.form.getlist('aerolinea_nombre[]')[i], telefono_aerolinea=request.form.getlist('aerolinea_telefono[]')[i], email=request.form.getlist('aerolinea_email[]')[i], whatsapp=request.form.getlist('aerolinea_whatsapp[]')[i], fecha_prealertar=to_date(request.form.getlist('aerolinea_fecha_prealerta[]')[i]), enlace_prealertar=request.form.getlist('aerolinea_enlace_prealerta[]')[i], numero_vuelo=request.form.getlist('aerolinea_num_vuelo[]')[i], horario_salida=to_time(request.form.getlist('aerolinea_hora_salida[]')[i]), horario_llegada=to_time(request.form.getlist('aerolinea_hora_llegada[]')[i]), nombre_aeropuerto=request.form.getlist('aerolinea_aeropuerto[]')[i], telefono_aeropuerto=request.form.getlist('aerolinea_tel_aeropuerto[]')[i], precio_asientos=float(request.form.getlist('aerolinea_p_asientos[]')[i] or 0.0), precio_maletas_doc=float(request.form.getlist('aerolinea_p_maletas[]')[i] or 0.0), equipaje_mano=float(request.form.getlist('aerolinea_p_equipaje_mano[]')[i] or 0.0), precio_estandar=float(request.form.getlist('aerolinea_p_estandar[]')[i] or 0.0), precio_mas_equipo=float(request.form.getlist('aerolinea_p_mas_equipo[]')[i] or 0.0), precio_salida_rapida=float(request.form.getlist('aerolinea_p_salida_rapida[]')[i] or 0.0), precio_premium=float(request.form.getlist('aerolinea_p_premium[]')[i] or 0.0), precio_vip=float(request.form.getlist('aerolinea_p_vip[]')[i] or 0.0), precio_basic=float(request.form.getlist('aerolinea_p_basic[]')[i] or 0.0), precio_classic=float(request.form.getlist('aerolinea_p_classic[]')[i] or 0.0), precio_flexible=float(request.form.getlist('aerolinea_p_flexible[]')[i] or 0.0), precio_impuestos=float(request.form.getlist('aerolinea_p_impuestos[]')[i] or 0.0), otros_costos_json=json.dumps(otros_costos_list), fecha_compra=to_date(request.form.getlist('aerolinea_fecha_compra[]')[i])))

        try:
            db.session.commit()
            flash('Viaje actualizado correctamente.', 'success')
            return redirect(url_for('intern.detalle_intern', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el viaje: {str(e)}', 'danger')
            
    return render_template('editar_intern.html', viaje=viaje)

@intern_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_intern(id):
    viaje = InternationalTravel.query.get_or_404(id)
    try:
        db.session.delete(viaje)
        db.session.commit()
        flash('El viaje ha sido eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el viaje: {str(e)}', 'danger')
    return redirect(url_for('intern.ver_intern'))

# --- INICIO: RUTAS DE EXPORTACIÓN COMPLETAS ---

def _get_export_context(id):
    """Función auxiliar para obtener todos los datos y cálculos para las exportaciones."""
    viaje = InternationalTravel.query.get_or_404(id)
    
    total_cost = 0
    # Calcular el costo total de todas las secciones
    for item in viaje.lugares: total_cost += item.precio_entrada or 0
    for item in viaje.transportes: total_cost += item.precio or 0
    for item in viaje.guias:
        total_cost += item.precio_guia_pp or 0
        total_cost += item.precio_acarreo or 0
    for item in viaje.estadias:
        total_cost += (item.precio_pp or 0) * (item.cantidad_noches or 1)
    for item in viaje.aerolineas:
        total_cost += item.precio_asientos or 0
        total_cost += item.precio_maletas_doc or 0
        total_cost += item.equipaje_mano or 0
        total_cost += item.precio_estandar or 0
        total_cost += item.precio_mas_equipo or 0
        total_cost += item.precio_salida_rapida or 0
        total_cost += item.precio_premium or 0
        total_cost += item.precio_vip or 0
        total_cost += item.precio_basic or 0
        total_cost += item.precio_classic or 0
        total_cost += item.precio_flexible or 0
        total_cost += item.precio_impuestos or 0
        otros_costos = json.loads(item.otros_costos_json or '[]')
        for costo_item in otros_costos:
            total_cost += (costo_item.get('costo', 0) or 0) * (costo_item.get('cantidad', 1) or 1)

    # Realizar cálculos de moneda
    total_individual_crc = 0
    total_individual_usd = 0
    if viaje.tipo_moneda == 'CRC':
        total_individual_crc = total_cost
        if viaje.tipo_cambio and viaje.tipo_cambio > 0:
            total_individual_usd = total_cost / viaje.tipo_cambio
    else: # USD
        total_individual_usd = total_cost
        total_individual_crc = total_cost * viaje.tipo_cambio

    precio_paquete_en_usd = 0
    if viaje.tipo_moneda == 'CRC':
        if viaje.tipo_cambio and viaje.tipo_cambio > 0:
            precio_paquete_en_usd = (viaje.precio_paquete or 0) / viaje.tipo_cambio
    else: # USD
        precio_paquete_en_usd = viaje.precio_paquete or 0
    
    diferencia_usd = precio_paquete_en_usd - total_individual_usd
    diferencia_crc = diferencia_usd * (viaje.tipo_cambio or 1)
    
    ganancia_total_usd = diferencia_usd * (viaje.capacidad or 0)
    ganancia_total_crc = diferencia_crc * (viaje.capacidad or 0)

    return {
        "viaje": viaje,
        "total_individual_crc": total_individual_crc,
        "total_individual_usd": total_individual_usd,
        "diferencia_usd": diferencia_usd,
        "diferencia_crc": diferencia_crc,
        "ganancia_total_usd": ganancia_total_usd,
        "ganancia_total_crc": ganancia_total_crc
    }

@intern_bp.route('/exportar/pdf/<int:id>')
def exportar_pdf(id):
    context = _get_export_context(id)
    viaje = context['viaje']

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 14)
            self.cell(0, 10, f"Resumen del Viaje: {viaje.nombre_viaje}", 0, 1, 'C')
            self.set_font('Arial', '', 10)
            self.cell(0, 7, f"Destino: {viaje.titulo_destino}, {viaje.pais}", 0, 1, 'C')
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

        def section_title(self, title):
            self.set_font('Arial', 'B', 12)
            self.set_fill_color(220, 220, 220)
            self.cell(0, 8, title, 0, 1, 'L', 1)
            self.ln(4)

        def item_entry(self, label, value, indent=False):
            if value:
                self.set_font('Arial', 'B' if ':' not in label else '', 9)
                if indent: self.cell(5)
                self.cell(60, 5, label)
                self.set_font('Arial', '', 9)
                self.multi_cell(0, 5, str(value), 0, 'L')
                self.ln(1)
        
        def sub_section_title(self, title):
            self.set_font('Arial', 'B', 10)
            self.cell(0, 8, title, 0, 1, 'L')
            self.ln(2)

    def format_currency(value, currency):
        symbol = "CRC " if currency == 'CRC' else "USD "
        return f"{symbol}{value:,.2f}"

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.section_title("Información General")
    pdf.item_entry("Precio del Paquete:", format_currency(viaje.precio_paquete, viaje.tipo_moneda))
    pdf.item_entry("Capacidad:", f"{viaje.capacidad} personas")
    pdf.item_entry("Moneda Base:", viaje.tipo_moneda)
    pdf.item_entry("Tipo de Cambio:", f"{viaje.tipo_cambio:,.2f} (CRC por USD)")
    pdf.ln(5)

    if viaje.prealertas:
        pdf.section_title("Pre-Alertas Bancarias")
        for i, item in enumerate(viaje.prealertas, 1):
            pdf.sub_section_title(f"Pre-Alerta #{i}")
            pdf.item_entry("Entidad:", item.banco, indent=True)
            pdf.item_entry("Teléfono:", item.telefono_entidad, indent=True)
            pdf.item_entry("Fecha Alerta:", item.fecha_prealerta.strftime('%d/%m/%Y') if item.fecha_prealerta else '', indent=True)
            pdf.item_entry("Asesor:", item.nombre_asesor, indent=True)
            pdf.item_entry("Hora:", item.hora_prealerta.strftime('%I:%M %p') if item.hora_prealerta else '', indent=True)
            pdf.item_entry("No. Alerta:", item.numero_prealerta, indent=True)
            pdf.item_entry("Válido Desde:", item.fecha_desde.strftime('%d/%m/%Y') if item.fecha_desde else '', indent=True)
            pdf.item_entry("Válido Hasta:", item.fecha_hasta.strftime('%d/%m/%Y') if item.fecha_hasta else '', indent=True)
            pdf.ln(3)

    if viaje.lugares:
        pdf.section_title("Lugares a Visitar")
        for item in viaje.lugares:
            pdf.sub_section_title(f"{item.nombre_sitio} ({item.tipo_lugar})")
            pdf.item_entry("Precio Entrada:", format_currency(item.precio_entrada, viaje.tipo_moneda), indent=True)
            pdf.item_entry("Fecha Reserva:", item.fecha_reserva.strftime('%d/%m/%Y') if item.fecha_reserva else '', indent=True)
            pdf.item_entry("Contacto:", f"{item.telefono_contacto} / {item.whatsapp_contacto}", indent=True)
            pdf.item_entry("Email:", item.email, indent=True)
            pdf.ln(3)

    if viaje.transportes:
        pdf.section_title("Transportes")
        for item in viaje.transportes:
            pdf.sub_section_title(f"{item.nombre_transporte} ({item.tipo_transporte})")
            pdf.item_entry("Precio:", format_currency(item.precio, viaje.tipo_moneda), indent=True)
            pdf.item_entry("Conductor:", item.conductor, indent=True)
            pdf.item_entry("Contacto:", f"{item.telefono_contacto} / {item.whatsapp_contacto}", indent=True)
            pdf.item_entry("Email:", item.email, indent=True)
            pdf.ln(3)
            
    if viaje.guias:
        pdf.section_title("Guías")
        for item in viaje.guias:
            pdf.sub_section_title(item.nombre)
            pdf.item_entry("Precio Guía (p.p.):", format_currency(item.precio_guia_pp, viaje.tipo_moneda), indent=True)
            pdf.item_entry("Precio Acarreo:", format_currency(item.precio_acarreo, viaje.tipo_moneda), indent=True)
            pdf.item_entry("Contacto:", f"{item.telefono} / {item.whatsapp}", indent=True)
            pdf.item_entry("Email:", item.email, indent=True)
            pdf.ln(3)
            
    if viaje.estadias:
        pdf.section_title("Estadías")
        for item in viaje.estadias:
            total_estadia = (item.precio_pp or 0) * (item.cantidad_noches or 1)
            pdf.sub_section_title(item.nombre)
            pdf.item_entry("Precio Total:", f"{format_currency(total_estadia, viaje.tipo_moneda)} ({item.cantidad_noches} noches)", indent=True)
            pdf.item_entry("Fechas:", f"{item.fecha_entrada.strftime('%d/%m/%Y') if item.fecha_entrada else ''} - {item.fecha_salida.strftime('%d/%m/%Y') if item.fecha_salida else ''}", indent=True)
            pdf.item_entry("Contacto:", f"{item.telefono} / {item.whatsapp}", indent=True)
            pdf.item_entry("Email:", item.email, indent=True)
            pdf.ln(3)

    if viaje.aerolineas:
        pdf.section_title("Aerolínea / Transporte Principal")
        for item in viaje.aerolineas:
            pdf.sub_section_title(f"{item.nombre_aerolinea or 'N/A'} ({item.tipo_transporte})")
            pdf.item_entry("Vuelo No.:", item.numero_vuelo, indent=True)
            pdf.item_entry("Horario:", f"Salida: {item.horario_salida.strftime('%I:%M %p') if item.horario_salida else ''} - Llegada: {item.horario_llegada.strftime('%I:%M %p') if item.horario_llegada else ''}", indent=True)
            pdf.item_entry("Aeropuerto:", item.nombre_aeropuerto, indent=True)
            pdf.item_entry("Contacto:", f"{item.telefono_aerolinea} / {item.whatsapp}", indent=True)
            pdf.item_entry("Email:", item.email, indent=True)
            
            # Precios
            prices = {
                "Asientos": item.precio_asientos, "Maletas Doc.": item.precio_maletas_doc, "Equipaje Mano": item.equipaje_mano,
                "Estándar": item.precio_estandar, "Más Equipo": item.precio_mas_equipo, "Salida Rápida": item.precio_salida_rapida,
                "Premium": item.precio_premium, "VIP": item.precio_vip, "Basic": item.precio_basic, "Classic": item.precio_classic,
                "Flexible": item.precio_flexible, "Impuestos": item.precio_impuestos
            }
            for name, price in prices.items():
                if price and price > 0:
                    pdf.item_entry(f"  {name}:", format_currency(price, viaje.tipo_moneda), indent=True)
            
            otros_costos = json.loads(item.otros_costos_json or '[]')
            if otros_costos:
                pdf.item_entry("  Otros Costos:", "", indent=True)
                for costo_item in otros_costos:
                    if costo_item.get('costo', 0) > 0:
                        total_linea = costo_item['costo'] * costo_item.get('cantidad', 1)
                        pdf.item_entry(f"    - {costo_item['descripcion']} (x{costo_item['cantidad']}):", format_currency(total_linea, viaje.tipo_moneda), indent=True)
            pdf.ln(3)

    pdf.section_title("Resumen Financiero")
    pdf.item_entry("Costo Total Individual (CRC):", f"CRC {context['total_individual_crc']:,.2f}")
    pdf.item_entry("Costo Total Individual (USD):", f"$ {context['total_individual_usd']:,.2f}")
    pdf.ln(2)
    pdf.item_entry("Diferencia por Persona (CRC):", f"CRC {context['diferencia_crc']:,.2f}")
    pdf.item_entry("Diferencia por Persona (USD):", f"$ {context['diferencia_usd']:,.2f}")
    pdf.ln(2)
    pdf.item_entry("GANANCIA TOTAL (CRC):", f"CRC {context['ganancia_total_crc']:,.2f}")
    pdf.item_entry("GANANCIA TOTAL (USD):", f"$ {context['ganancia_total_usd']:,.2f}")

    pdf_output = pdf.output(dest='S').encode('latin1')
    
    return Response(pdf_output, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment;filename=resumen_{viaje.nombre_viaje.replace(" ", "_")}.pdf'})


@intern_bp.route('/exportar/txt/<int:id>')
def exportar_txt(id):
    context = _get_export_context(id)
    viaje = context['viaje']
    content = []

    def format_currency(value, currency):
        symbol = "CRC " if currency == 'CRC' else "USD "
        return f"{symbol}{value or 0:,.2f}"

    def add_line(label, value, indent=0):
        if value:
            content.append(f"{'  ' * indent}- {label}: {value}")

    content.append("="*60)
    content.append(f"RESUMEN DE VIAJE: {viaje.nombre_viaje.upper()}")
    content.append(f"DESTINO: {viaje.titulo_destino}, {viaje.pais}")
    content.append(f"FECHA DE EMISIÓN: {datetime.now().strftime('%d/%m/%Y')}")
    content.append("="*60)

    content.append("\n[ INFORMACIÓN GENERAL ]")
    add_line("Precio Paquete", format_currency(viaje.precio_paquete, viaje.tipo_moneda), 1)
    add_line("Capacidad", f"{viaje.capacidad} personas", 1)
    add_line("Moneda Base", viaje.tipo_moneda, 1)
    add_line("Tipo de Cambio", f"{viaje.tipo_cambio:,.2f}", 1)

    if viaje.prealertas:
        content.append("\n[ PRE-ALERTAS BANCARIAS ]")
        for i, item in enumerate(viaje.prealertas, 1):
            content.append(f"\n  Pre-Alerta #{i}:")
            add_line("Entidad", item.banco, 2)
            add_line("Contacto", f"{item.telefono_entidad} (Asesor: {item.nombre_asesor or 'N/A'})", 2)
            add_line("Fecha y Hora", f"{item.fecha_prealerta.strftime('%d/%m/%Y') if item.fecha_prealerta else ''} {item.hora_prealerta.strftime('%I:%M %p') if item.hora_prealerta else ''}", 2)
            add_line("No. Alerta", item.numero_prealerta, 2)
            add_line("Vigencia", f"Del {item.fecha_desde.strftime('%d/%m/%Y') if item.fecha_desde else ''} al {item.fecha_hasta.strftime('%d/%m/%Y') if item.fecha_hasta else ''}", 2)

    if viaje.lugares:
        content.append("\n[ LUGARES A VISITAR ]")
        for item in viaje.lugares:
            content.append(f"\n  Lugar: {item.nombre_sitio} ({item.tipo_lugar})")
            add_line("Precio Entrada", format_currency(item.precio_entrada, viaje.tipo_moneda), 2)
            add_line("Fecha Reserva", item.fecha_reserva.strftime('%d/%m/%Y') if item.fecha_reserva else '', 2)
            add_line("Contacto", f"Tel: {item.telefono_contacto or 'N/A'} / WA: {item.whatsapp_contacto or 'N/A'}", 2)
            add_line("Email", item.email, 2)

    if viaje.transportes:
        content.append("\n[ TRANSPORTES ]")
        for item in viaje.transportes:
            content.append(f"\n  Transporte: {item.nombre_transporte} ({item.tipo_transporte})")
            add_line("Precio", format_currency(item.precio, viaje.tipo_moneda), 2)
            add_line("Conductor", item.conductor, 2)
            add_line("Contacto", f"Tel: {item.telefono_contacto or 'N/A'} / WA: {item.whatsapp_contacto or 'N/A'}", 2)
            add_line("Email", item.email, 2)

    if viaje.guias:
        content.append("\n[ GUÍAS ]")
        for item in viaje.guias:
            content.append(f"\n  Guía: {item.nombre}")
            add_line("Precio p.p.", format_currency(item.precio_guia_pp, viaje.tipo_moneda), 2)
            add_line("Precio Acarreo", format_currency(item.precio_acarreo, viaje.tipo_moneda), 2)
            add_line("Contacto", f"Tel: {item.telefono or 'N/A'} / WA: {item.whatsapp or 'N/A'}", 2)
            add_line("Email", item.email, 2)

    if viaje.estadias:
        content.append("\n[ ESTADÍAS ]")
        for item in viaje.estadias:
            total_estadia = (item.precio_pp or 0) * (item.cantidad_noches or 1)
            content.append(f"\n  Estadía: {item.nombre}")
            add_line("Precio Total", f"{format_currency(total_estadia, viaje.tipo_moneda)} ({item.cantidad_noches} noches)", 2)
            add_line("Fechas", f"Entrada: {item.fecha_entrada.strftime('%d/%m/%Y') if item.fecha_entrada else ''} - Salida: {item.fecha_salida.strftime('%d/%m/%Y') if item.fecha_salida else ''}", 2)
            add_line("Contacto", f"Tel: {item.telefono or 'N/A'} / WA: {item.whatsapp or 'N/A'}", 2)
            add_line("Email", item.email, 2)

    if viaje.aerolineas:
        content.append("\n[ AEROLÍNEA / TRANSPORTE PRINCIPAL ]")
        for item in viaje.aerolineas:
            content.append(f"\n  Compañía: {item.nombre_aerolinea or 'N/A'} ({item.tipo_transporte})")
            add_line("Vuelo No.", item.numero_vuelo, 2)
            add_line("Horario", f"Salida: {item.horario_salida.strftime('%I:%M %p') if item.horario_salida else ''} - Llegada: {item.horario_llegada.strftime('%I:%M %p') if item.horario_llegada else ''}", 2)
            add_line("Aeropuerto", item.nombre_aeropuerto, 2)
            add_line("Contacto", f"Tel: {item.telefono_aerolinea or 'N/A'} / WA: {item.whatsapp or 'N/A'}", 2)
            add_line("Email", item.email, 2)
            content.append("    Desglose de Precios:")
            prices = {"Asientos": item.precio_asientos, "Maletas Doc.": item.precio_maletas_doc, "Equipaje Mano": item.equipaje_mano, "Estándar": item.precio_estandar, "Más Equipo": item.precio_mas_equipo, "Salida Rápida": item.precio_salida_rapida, "Premium": item.precio_premium, "VIP": item.precio_vip, "Basic": item.precio_basic, "Classic": item.precio_classic, "Flexible": item.precio_flexible, "Impuestos": item.precio_impuestos}
            for name, price in prices.items():
                if price and price > 0: add_line(name, format_currency(price, viaje.tipo_moneda), 3)
            otros_costos = json.loads(item.otros_costos_json or '[]')
            if otros_costos:
                add_line("Otros Costos", "", 3)
                for costo_item in otros_costos:
                    if costo_item.get('costo', 0) > 0:
                        total_linea = costo_item['costo'] * costo_item.get('cantidad', 1)
                        add_line(f"{costo_item['descripcion']} (x{costo_item['cantidad']})", format_currency(total_linea, viaje.tipo_moneda), 4)

    content.append("\n" + "="*60)
    content.append("[ RESUMEN FINANCIERO ]")
    content.append("="*60)
    add_line("Costo Total Individual (CRC)", f"CRC {context['total_individual_crc']:,.2f}", 1)
    add_line("Costo Total Individual (USD)", f"$ {context['total_individual_usd']:,.2f}", 1)
    content.append("  --------------------------------------------------")
    add_line("Diferencia por Persona (CRC)", f"CRC {context['diferencia_crc']:,.2f}", 1)
    add_line("Diferencia por Persona (USD)", f"$ {context['diferencia_usd']:,.2f}", 1)
    content.append("  --------------------------------------------------")
    add_line("GANANCIA TOTAL (CRC)", f"CRC {context['ganancia_total_crc']:,.2f}", 1)
    add_line("GANANCIA TOTAL (USD)", f"$ {context['ganancia_total_usd']:,.2f}", 1)
    content.append("="*60)

    final_content = "\n".join(content)
    response = make_response(final_content)
    response.headers["Content-Disposition"] = f"attachment; filename=resumen_{viaje.nombre_viaje.replace(' ', '_')}.txt"
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@intern_bp.route('/exportar/jpg/<int:id>')
def exportar_jpg(id):
    viaje = InternationalTravel.query.get_or_404(id)
    flash(f'La funcionalidad para exportar {viaje.nombre_viaje} a JPG aún no está implementada.', 'info')
    return redirect(url_for('intern.detalle_intern', id=id))

@intern_bp.route('/exportar/excel/<int:id>')
def exportar_excel(id):
    viaje = InternationalTravel.query.get_or_404(id)
    flash(f'La funcionalidad para exportar {viaje.nombre_viaje} a Excel aún no está implementada.', 'info')
    return redirect(url_for('intern.detalle_intern', id=id))

# --- FIN: RUTAS DE EXPORTACIÓN COMPLETAS ---
