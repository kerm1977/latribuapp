from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from models import db
from datetime import datetime, time
import json

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
        # --- 1. Crear Viaje Principal ---
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

        # --- 2. Procesar Secciones Dinámicas ---
        # Pre-alertas
        for i in range(len(request.form.getlist('prealerta_banco[]'))):
            if request.form.getlist('prealerta_banco[]')[i]:
                db.session.add(PreAlerta(
                    travel_id=nuevo_viaje.id,
                    banco=request.form.getlist('prealerta_banco[]')[i],
                    telefono_entidad=request.form.getlist('prealerta_telefono[]')[i],
                    fecha_prealerta=to_date(request.form.getlist('prealerta_fecha[]')[i]),
                    nombre_asesor=request.form.getlist('prealerta_asesor[]')[i],
                    hora_prealerta=to_time(request.form.getlist('prealerta_hora[]')[i]),
                    numero_prealerta=request.form.getlist('prealerta_numero[]')[i],
                    fecha_desde=to_date(request.form.getlist('prealerta_desde[]')[i]),
                    fecha_hasta=to_date(request.form.getlist('prealerta_hasta[]')[i])
                ))
        
        # Lugares a Visitar
        for i in range(len(request.form.getlist('lugar_nombre[]'))):
             if request.form.getlist('lugar_nombre[]')[i]:
                db.session.add(LugarVisitar(
                    travel_id=nuevo_viaje.id,
                    tipo_lugar=request.form.getlist('lugar_tipo[]')[i],
                    nombre_sitio=request.form.getlist('lugar_nombre[]')[i],
                    precio_entrada=float(request.form.getlist('lugar_precio[]')[i] or 0.0)
                ))

        # Transportes
        for i in range(len(request.form.getlist('transporte_nombre[]'))):
            if request.form.getlist('transporte_nombre[]')[i]:
                db.session.add(Transporte(
                    travel_id=nuevo_viaje.id,
                    tipo_transporte=request.form.getlist('transporte_tipo[]')[i],
                    nombre_transporte=request.form.getlist('transporte_nombre[]')[i],
                    precio=float(request.form.getlist('transporte_precio[]')[i] or 0.0)
                ))

        # Guías
        for i in range(len(request.form.getlist('guia_nombre[]'))):
            if request.form.getlist('guia_nombre[]')[i]:
                db.session.add(Guia(
                    travel_id=nuevo_viaje.id,
                    nombre=request.form.getlist('guia_nombre[]')[i],
                    precio_guia_pp=float(request.form.getlist('guia_precio_pp[]')[i] or 0.0),
                    precio_acarreo=float(request.form.getlist('guia_precio_acarreo[]')[i] or 0.0)
                ))

        # Estadías
        for i in range(len(request.form.getlist('estadia_nombre[]'))):
            if request.form.getlist('estadia_nombre[]')[i]:
                db.session.add(Estadia(
                    travel_id=nuevo_viaje.id,
                    nombre=request.form.getlist('estadia_nombre[]')[i],
                    precio_pp=float(request.form.getlist('estadia_precio_pp[]')[i] or 0.0),
                    cantidad_noches=int(request.form.getlist('estadia_noches[]')[i] or 1)
                ))
        
        # Aerolíneas
        tipos_transporte = request.form.getlist('aerolinea_tipo_transporte[]')
        for i in range(len(tipos_transporte)):
            if tipos_transporte[i]:
                otros_costos_list = []
                for j in range(1, 5):
                    desc = request.form.getlist(f'aerolinea_desc_{j}[]')[i]
                    costo = request.form.getlist(f'aerolinea_costo_{j}[]')[i]
                    cant = request.form.getlist(f'aerolinea_cant_{j}[]')[i]
                    if desc and (costo or cant):
                        otros_costos_list.append({
                            'descripcion': desc,
                            'costo': float(costo or 0.0),
                            'cantidad': int(cant or 1)
                        })
                
                db.session.add(Aerolinea(
                    travel_id=nuevo_viaje.id,
                    tipo_transporte=tipos_transporte[i],
                    nombre_aerolinea=request.form.getlist('aerolinea_nombre[]')[i],
                    telefono_aerolinea=request.form.getlist('aerolinea_telefono[]')[i],
                    email=request.form.getlist('aerolinea_email[]')[i],
                    whatsapp=request.form.getlist('aerolinea_whatsapp[]')[i],
                    fecha_prealertar=to_date(request.form.getlist('aerolinea_fecha_prealerta[]')[i]),
                    enlace_prealertar=request.form.getlist('aerolinea_enlace_prealerta[]')[i],
                    numero_vuelo=request.form.getlist('aerolinea_num_vuelo[]')[i],
                    horario_salida=to_time(request.form.getlist('aerolinea_hora_salida[]')[i]),
                    horario_llegada=to_time(request.form.getlist('aerolinea_hora_llegada[]')[i]),
                    nombre_aeropuerto=request.form.getlist('aerolinea_aeropuerto[]')[i],
                    telefono_aeropuerto=request.form.getlist('aerolinea_tel_aeropuerto[]')[i],
                    precio_asientos=float(request.form.getlist('aerolinea_p_asientos[]')[i] or 0.0),
                    precio_maletas_doc=float(request.form.getlist('aerolinea_p_maletas[]')[i] or 0.0),
                    equipaje_mano=float(request.form.getlist('aerolinea_p_equipaje_mano[]')[i] or 0.0),
                    precio_estandar=float(request.form.getlist('aerolinea_p_estandar[]')[i] or 0.0),
                    precio_mas_equipo=float(request.form.getlist('aerolinea_p_mas_equipo[]')[i] or 0.0),
                    precio_salida_rapida=float(request.form.getlist('aerolinea_p_salida_rapida[]')[i] or 0.0),
                    precio_premium=float(request.form.getlist('aerolinea_p_premium[]')[i] or 0.0),
                    precio_vip=float(request.form.getlist('aerolinea_p_vip[]')[i] or 0.0),
                    precio_basic=float(request.form.getlist('aerolinea_p_basic[]')[i] or 0.0),
                    precio_classic=float(request.form.getlist('aerolinea_p_classic[]')[i] or 0.0),
                    precio_flexible=float(request.form.getlist('aerolinea_p_flexible[]')[i] or 0.0),
                    precio_impuestos=float(request.form.getlist('aerolinea_p_impuestos[]')[i] or 0.0),
                    otros_costos_json=json.dumps(otros_costos_list),
                    fecha_compra=to_date(request.form.getlist('aerolinea_fecha_compra[]')[i])
                ))

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
        # --- 1. Actualizar Viaje Principal ---
        viaje.titulo_destino = request.form.get('titulo_destino')
        viaje.nombre_viaje = request.form.get('nombre_viaje')
        viaje.precio_paquete = float(request.form.get('precio_paquete') or 0.0)
        viaje.capacidad = int(request.form.get('capacidad') or 0)
        viaje.tipo_moneda = request.form.get('tipo_moneda')
        viaje.tipo_cambio = float(request.form.get('tipo_cambio') or 1.0)
        viaje.pais = request.form.get('pais')

        # --- 2. Borrar y Recrear Secciones Dinámicas ---
        # Pre-alertas
        for item in viaje.prealertas: db.session.delete(item)
        for i in range(len(request.form.getlist('prealerta_banco[]'))):
            if request.form.getlist('prealerta_banco[]')[i]:
                db.session.add(PreAlerta(travel_id=viaje.id, banco=request.form.getlist('prealerta_banco[]')[i], telefono_entidad=request.form.getlist('prealerta_telefono[]')[i], fecha_prealerta=to_date(request.form.getlist('prealerta_fecha[]')[i]), nombre_asesor=request.form.getlist('prealerta_asesor[]')[i], hora_prealerta=to_time(request.form.getlist('prealerta_hora[]')[i]), numero_prealerta=request.form.getlist('prealerta_numero[]')[i], fecha_desde=to_date(request.form.getlist('prealerta_desde[]')[i]), fecha_hasta=to_date(request.form.getlist('prealerta_hasta[]')[i])))

        # Lugares a Visitar
        for item in viaje.lugares: db.session.delete(item)
        for i in range(len(request.form.getlist('lugar_nombre[]'))):
            if request.form.getlist('lugar_nombre[]')[i]:
                db.session.add(LugarVisitar(travel_id=viaje.id, tipo_lugar=request.form.getlist('lugar_tipo[]')[i], nombre_sitio=request.form.getlist('lugar_nombre[]')[i], precio_entrada=float(request.form.getlist('lugar_precio[]')[i] or 0.0)))

        # Transportes
        for item in viaje.transportes: db.session.delete(item)
        for i in range(len(request.form.getlist('transporte_nombre[]'))):
            if request.form.getlist('transporte_nombre[]')[i]:
                db.session.add(Transporte(travel_id=viaje.id, tipo_transporte=request.form.getlist('transporte_tipo[]')[i], nombre_transporte=request.form.getlist('transporte_nombre[]')[i], precio=float(request.form.getlist('transporte_precio[]')[i] or 0.0)))

        # Guías
        for item in viaje.guias: db.session.delete(item)
        for i in range(len(request.form.getlist('guia_nombre[]'))):
            if request.form.getlist('guia_nombre[]')[i]:
                db.session.add(Guia(travel_id=viaje.id, nombre=request.form.getlist('guia_nombre[]')[i], precio_guia_pp=float(request.form.getlist('guia_precio_pp[]')[i] or 0.0), precio_acarreo=float(request.form.getlist('guia_precio_acarreo[]')[i] or 0.0)))

        # Estadías
        for item in viaje.estadias: db.session.delete(item)
        for i in range(len(request.form.getlist('estadia_nombre[]'))):
            if request.form.getlist('estadia_nombre[]')[i]:
                db.session.add(Estadia(travel_id=viaje.id, nombre=request.form.getlist('estadia_nombre[]')[i], precio_pp=float(request.form.getlist('estadia_precio_pp[]')[i] or 0.0), cantidad_noches=int(request.form.getlist('estadia_noches[]')[i] or 1)))

        # Aerolíneas
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
                        otros_costos_list.append({
                            'descripcion': desc,
                            'costo': float(costo or 0.0),
                            'cantidad': int(cant or 1)
                        })

                db.session.add(Aerolinea(
                    travel_id=viaje.id,
                    tipo_transporte=tipos_transporte[i],
                    nombre_aerolinea=request.form.getlist('aerolinea_nombre[]')[i],
                    telefono_aerolinea=request.form.getlist('aerolinea_telefono[]')[i],
                    email=request.form.getlist('aerolinea_email[]')[i],
                    whatsapp=request.form.getlist('aerolinea_whatsapp[]')[i],
                    fecha_prealertar=to_date(request.form.getlist('aerolinea_fecha_prealerta[]')[i]),
                    enlace_prealertar=request.form.getlist('aerolinea_enlace_prealerta[]')[i],
                    numero_vuelo=request.form.getlist('aerolinea_num_vuelo[]')[i],
                    horario_salida=to_time(request.form.getlist('aerolinea_hora_salida[]')[i]),
                    horario_llegada=to_time(request.form.getlist('aerolinea_hora_llegada[]')[i]),
                    nombre_aeropuerto=request.form.getlist('aerolinea_aeropuerto[]')[i],
                    telefono_aeropuerto=request.form.getlist('aerolinea_tel_aeropuerto[]')[i],
                    precio_asientos=float(request.form.getlist('aerolinea_p_asientos[]')[i] or 0.0),
                    precio_maletas_doc=float(request.form.getlist('aerolinea_p_maletas[]')[i] or 0.0),
                    equipaje_mano=float(request.form.getlist('aerolinea_p_equipaje_mano[]')[i] or 0.0),
                    precio_estandar=float(request.form.getlist('aerolinea_p_estandar[]')[i] or 0.0),
                    precio_mas_equipo=float(request.form.getlist('aerolinea_p_mas_equipo[]')[i] or 0.0),
                    precio_salida_rapida=float(request.form.getlist('aerolinea_p_salida_rapida[]')[i] or 0.0),
                    precio_premium=float(request.form.getlist('aerolinea_p_premium[]')[i] or 0.0),
                    precio_vip=float(request.form.getlist('aerolinea_p_vip[]')[i] or 0.0),
                    precio_basic=float(request.form.getlist('aerolinea_p_basic[]')[i] or 0.0),
                    precio_classic=float(request.form.getlist('aerolinea_p_classic[]')[i] or 0.0),
                    precio_flexible=float(request.form.getlist('aerolinea_p_flexible[]')[i] or 0.0),
                    precio_impuestos=float(request.form.getlist('aerolinea_p_impuestos[]')[i] or 0.0),
                    otros_costos_json=json.dumps(otros_costos_list),
                    fecha_compra=to_date(request.form.getlist('aerolinea_fecha_compra[]')[i])
                ))

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

@intern_bp.route('/exportar/pdf/<int:id>')
def exportar_pdf(id):
    viaje = InternationalTravel.query.get_or_404(id)
    flash(f'La funcionalidad para exportar {viaje.nombre_viaje} a PDF aún no está implementada.', 'info')
    return redirect(url_for('intern.detalle_intern', id=id))

@intern_bp.route('/exportar/txt/<int:id>')
def exportar_txt(id):
    viaje = InternationalTravel.query.get_or_404(id)
    content = f"Detalles del Viaje: {viaje.nombre_viaje}\n"
    content += "=" * 30 + "\n\n"
    content += f"Destino: {viaje.titulo_destino}\n"
    content += f"País: {viaje.pais}\n"
    if viaje.lugares:
        content += "\n--- Lugares a Visitar ---\n"
        for lugar in viaje.lugares:
            content += f"- {lugar.nombre_sitio} (Entrada: {lugar.precio_entrada} CRC)\n"
    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename=viaje_{viaje.id}.txt"
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

# --- FIN: RUTAS DE EXPORTACIÓN COMPLETAS 