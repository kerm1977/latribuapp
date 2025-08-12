# intern.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, User # Suponiendo que tienes un modelo User
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Float, Date, Time, Boolean, ForeignKey, Text
import json
from datetime import date

# Blueprint para la sección internacional
intern_bp = Blueprint('intern', __name__, template_folder='templates', static_folder='static')

# --- MODELOS DE BASE DE DATOS ---
# Estos modelos representan la estructura de datos para cada viaje internacional.

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

    # Relaciones con otras tablas
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
    otros_costos = Column(Text) # JSON para otros costos
    fecha_compra = Column(Date)

# --- RUTAS ---

@intern_bp.route('/')
def index():
    """Muestra todos los viajes internacionales."""
    viajes = Intern.query.order_by(Intern.id.desc()).all()
    return render_template('ver_intern.html', viajes=viajes)

@intern_bp.route('/crear', methods=['GET', 'POST'])
def crear_intern():
    """Crea un nuevo plan de viaje internacional."""
    if request.method == 'POST':
        # Lógica para procesar el formulario y guardar en la BD
        try:
            # --- Sección Principal ---
            nuevo_viaje = Intern(
                flyer=request.form.get('flyer'),
                nombre_viaje=request.form.get('nombre_viaje'),
                precio_paquete=float(request.form.get('precio_paquete', 0)),
                capacidad=int(request.form.get('capacidad', 0)),
                tipo_moneda=request.form.get('tipo_moneda'),
                tipo_cambio=float(request.form.get('tipo_cambio', 1)),
                pais=request.form.get('pais'),
                # user_id=session.get('user_id') # Asumiendo que usas sesiones
            )
            db.session.add(nuevo_viaje)
            db.session.flush() # Para obtener el ID del nuevo viaje antes del commit

            # --- Procesar secciones dinámicas ---
            # (Prealertas, Lugares, Transportes, etc.)
            # La lógica detallada para procesar cada sección iría aquí,
            # extrayendo los datos de los campos generados dinámicamente.
            # Ejemplo para lugares a visitar:
            nombres_sitio = request.form.getlist('nombre_sitio[]')
            for i in range(len(nombres_sitio)):
                lugar = LugarVisitar(
                    intern_id=nuevo_viaje.id,
                    nombre_sitio=nombres_sitio[i],
                    # ... otros campos del lugar
                )
                db.session.add(lugar)

            db.session.commit()
            flash('Plan de viaje creado exitosamente.', 'success')
            return redirect(url_for('intern.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el viaje: {str(e)}', 'danger')

    # Listas para los selects del formulario
    paises = ["Panamá", "Nicaragua", "Honduras", "El Salvador", "Guatemala", "México", "Perú", "España"]
    bancos = ["Banco de Costa Rica (BCR)", "Banco Nacional de Costa Rica (BNCR)", "Banco Popular", "Mucap", "Mutual", "BAC Credomatic", "Banco Cathay", "Banco BCT", "Banco CMB", "Banco Davivienda", "Banco General", "Banco Improsa", "Banco Lafise", "Banco Promérica", "Prival Bank", "Scotiabank", "Coopealianza", "Coopeande", "CoopeAnde No. 1", "CoopeAnde No. 2", "CoopeAnde No. 3", "CoopeAnde No. 4", "CoopeAnde No. 5", "CoopeAnde No. 6", "CoopeAnde No. 7", "CoopeAnde No. 8", "CoopeAnde No. 9", "CoopeAnde No. 10", "CoopeAnde No. 11", "CoopeCaja", "Caja de ANDE", "COOPENAE", "COOPEUCHA", "COOPESANRAMON", "COOPESERVIDORES", "COOPEUNA", "CREDECOOP"]
    aerolineas_opciones = sorted(["Avianca", "American Airlines", "Copa", "Volaris", "Jetblue", "Sansa", "Spirit", "United", "Wingo", "KLM", "Iberia", "Lufthansa", "Latam Airlines", "IberoJet", "Delta", "AirFrance", "Alaska", "AeroMéxico", "Arajet", "Air Canadá", "Airtransat", "Green Airways", "Southwest", "Edelweiss", "Frontier", "GOL"])
    
    return render_template('crear_intern.html', 
                           paises=paises, 
                           bancos=bancos, 
                           aerolineas_opciones=aerolineas_opciones)

@intern_bp.route('/ver/<int:id>')
def detalle_intern(id):
    """Muestra el detalle completo de un viaje."""
    viaje = Intern.query.get_or_404(id)
    
    # Lógica de cálculo de totales
    total_atracciones = sum(lugar.precio_entrada for lugar in viaje.lugares if lugar.precio_entrada)
    total_transporte = sum(transporte.precio for transporte in viaje.transportes if transporte.precio)
    total_guias_pp = sum((guia.precio_guia_pp or 0) + (guia.precio_acarreo or 0) for guia in viaje.guias)
    total_estadia_pp = sum((estadia.precio_pp or 0) * (estadia.cantidad_noches or 1) for estadia in viaje.estadias)
    
    total_aerolinea_pp = 0
    for aero in viaje.aerolineas:
        total_aerolinea_pp += (aero.precio_asientos or 0) + (aero.precio_maletas_documentado or 0) # ... y así con todos los precios
        if aero.otros_costos:
            try:
                otros = json.loads(aero.otros_costos)
                for item in otros:
                    total_aerolinea_pp += (float(item.get('costo', 0)) or 0) * (int(item.get('cantidad', 1)) or 1)
            except (json.JSONDecodeError, TypeError):
                pass # Ignorar si el JSON es inválido
    
    # Cálculos finales
    total_individual_crc = (viaje.precio_paquete or 0) + total_atracciones + total_transporte + total_guias_pp + total_estadia_pp + total_aerolinea_pp
    total_individual_usd = total_individual_crc / viaje.tipo_cambio if viaje.tipo_cambio else 0

    return render_template('detalle_intern.html', 
                           viaje=viaje,
                           total_atracciones=total_atracciones,
                           total_transporte=total_transporte,
                           total_guias_pp=total_guias_pp,
                           total_estadia_pp=total_estadia_pp,
                           total_aerolinea_pp=total_aerolinea_pp,
                           total_individual_crc=total_individual_crc,
                           total_individual_usd=total_individual_usd)

@intern_bp.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_intern(id):
    """Edita un plan de viaje existente."""
    viaje = Intern.query.get_or_404(id)
    if request.method == 'POST':
        # Lógica para actualizar el viaje en la BD
        try:
            # Actualizar campos principales
            viaje.flyer = request.form.get('flyer')
            viaje.nombre_viaje = request.form.get('nombre_viaje')
            # ... y así con todos los demás campos
            
            # Lógica para actualizar, añadir o eliminar items de las secciones dinámicas
            # (Esta parte es compleja y requiere manejar IDs para saber qué actualizar y qué borrar)

            db.session.commit()
            flash('Plan de viaje actualizado correctamente.', 'success')
            return redirect(url_for('intern.detalle_intern', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al editar el viaje: {str(e)}', 'danger')

    paises = ["Panamá", "Nicaragua", "Honduras", "El Salvador", "Guatemala", "México", "Perú", "España"]
    bancos = ["Banco de Costa Rica (BCR)", "Banco Nacional de Costa Rica (BNCR)", "Banco Popular", "etc..."]
    aerolineas_opciones = sorted(["Avianca", "American Airlines", "Copa", "etc..."])

    return render_template('editar_intern.html', 
                           viaje=viaje,
                           paises=paises,
                           bancos=bancos,
                           aerolineas_opciones=aerolineas_opciones)

@intern_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_intern(id):
    """Elimina un plan de viaje."""
    viaje = Intern.query.get_or_404(id)
    try:
        db.session.delete(viaje)
        db.session.commit()
        flash('El plan de viaje ha sido eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el viaje: {str(e)}', 'danger')
    return redirect(url_for('intern.index'))

# --- RUTAS PARA EXPORTACIÓN ---
# Aquí irían las funciones para exportar a PDF, TXT, JPG, EXCEL.
# Estas requerirían librerías adicionales como FPDF, openpyxl, etc.

@intern_bp.route('/exportar/pdf/<int:id>')
def exportar_pdf(id):
    # Lógica para generar PDF
    flash('Funcionalidad de exportar a PDF no implementada.', 'info')
    return redirect(url_for('intern.detalle_intern', id=id))

@intern_bp.route('/exportar/txt/<int:id>')
def exportar_txt(id):
    # Lógica para generar TXT con UTF-8
    flash('Funcionalidad de exportar a TXT no implementada.', 'info')
    return redirect(url_for('intern.detalle_intern', id=id))