from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime, date, time
import json
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Date, Time, Index, UniqueConstraint
from sqlalchemy.orm import relationship

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()

# --- TABELAS DE ASSOCIAÇÃO ---
note_viewers = db.Table('note_viewers',
    db.Column('note_id', db.Integer, db.ForeignKey('note.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

caminata_participantes = db.Table('caminata_participantes',
    db.Column('caminata_id', db.Integer, db.ForeignKey('caminata.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

playlist_songs = db.Table('playlist_songs',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlist.id'), primary_key=True),
    db.Column('song_id', db.Integer, db.ForeignKey('song.id'), primary_key=True)
)

# --- MODELOS DE APLICAÇÃO ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=True) 
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    avatar_url = db.Column(db.String(200), nullable=True, default='uploads/avatars/default.png')
    segundo_apellido = db.Column(db.String(100), nullable=True)
    telefono_emergencia = db.Column(db.String(20), nullable=True)
    nombre_emergencia = db.Column(db.String(100), nullable=True)
    empresa = db.Column(db.String(100), nullable=True)
    cedula = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    actividad = db.Column(db.String(100), nullable=True)
    capacidad = db.Column(db.String(50), nullable=True)
    participacion = db.Column(db.String(100), nullable=True)
    fecha_cumpleanos = db.Column(db.Date, nullable=True)
    tipo_sangre = db.Column(db.String(5), nullable=True)
    poliza = db.Column(db.String(100), nullable=True)
    aseguradora = db.Column(db.String(100), nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    enfermedades_cronicas = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(50), nullable=False, default='Usuario Regular')
    last_login_at = db.Column(db.DateTime, nullable=True)
    oauth_logins = db.relationship('OAuthSignIn', backref='user', lazy=True, cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('email', name='uq_user_email'),
    )

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f'<User {self.username}>'

class OAuthSignIn(db.Model):
    __tablename__ = 'oauth_signin'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_signin_provider_user_id'),
    )

    def __repr__(self):
        return f'<OAuthSignIn {self.provider} para {self.user.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_proyecto = db.Column(db.String(255), nullable=False)
    imagen_proyecto_url = db.Column(db.String(255), nullable=True)
    propuesta_por = db.Column(db.String(100), nullable=True)
    nombre_invitado_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    nombre_invitado = db.relationship('User', foreign_keys=[nombre_invitado_id])
    provincia = db.Column(db.String(50), nullable=True)
    fecha_actividad_propuesta = db.Column(db.Date, nullable=True)
    dificultad = db.Column(db.String(50), nullable=True)
    transporte_terrestre = db.Column(db.String(50), nullable=True)
    transporte_acuatico = db.Column(db.String(2), nullable=True)
    transporte_aereo = db.Column(db.String(2), nullable=True)
    precio_entrada_aplica = db.Column(db.String(2), nullable=True)
    nombre_lugar = db.Column(db.String(255), nullable=True)
    contacto_lugar = db.Column(db.String(255), nullable=True)
    telefono_lugar = db.Column(db.String(20), nullable=True)
    tipo_terreno = db.Column(db.String(50), nullable=True)
    mas_tipo_terreno = db.Column(db.Text, nullable=True)
    presupuesto_total = db.Column(db.Float, nullable=True)
    costo_entrada = db.Column(db.Float, nullable=True)
    costo_guia = db.Column(db.Float, nullable=True)
    costo_transporte = db.Column(db.Float, nullable=True)
    nombres_acompanantes = db.Column(db.Text, nullable=True)
    recomendaciones = db.Column(db.Text, nullable=True)
    notas_adicionales = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_ultima_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    def __repr__(self):
        return f"Project('{self.nombre_proyecto}', '{self.propuesta_por}', '{self.fecha_actividad_propuesta}')"

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    background_color = db.Column(db.String(20), default='#FFFFFF', nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    creator = db.relationship('User', backref=db.backref('created_notes', lazy=True, cascade="all, delete-orphan"), foreign_keys=[creator_id])
    authorized_viewers = db.relationship(
        'User', secondary=note_viewers, lazy='subquery',
        backref=db.backref('viewable_notes', lazy=True)
    )

    def __repr__(self):
        return f"Note('{self.title}', Creator ID: {self.creator_id}, Public: {self.is_public}, Color: {self.background_color}')"

class Caminata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    finalizada = db.Column(db.Boolean, nullable=False, server_default='0')
    imagen_caminata_url = db.Column(db.String(255), nullable=True)
    actividad = db.Column(db.String(100), nullable=False)
    etapa = db.Column(db.String(255), nullable=True)
    nombre = db.Column(db.String(255), nullable=False)
    moneda = db.Column(db.String(10), nullable=False, server_default='CRC', default='CRC')
    precio = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    hora_salida = db.Column(db.Time, nullable=True)
    hora_regreso = db.Column(db.Time, nullable=True)
    costo_b = db.Column(db.Float, nullable=True)
    costo_c = db.Column(db.Float, nullable=True)
    costo_extranjeros = db.Column(db.Float, nullable=True)
    lugar_salida = db.Column(db.String(255), nullable=True)
    dificultad = db.Column(db.String(50), nullable=True)
    distancia = db.Column(db.Float, nullable=True)
    capacidad_minima = db.Column(db.String(50), nullable=True)
    capacidad_maxima = db.Column(db.String(50), nullable=True)
    nombre_guia = db.Column(db.String(255), nullable=True)
    se_requiere = db.Column(db.String(100), nullable=True)
    provincia = db.Column(db.String(50), nullable=True)
    tipo_terreno = db.Column(db.Text, nullable=True)
    otras_senas_terreno = db.Column(db.Text, nullable=True)
    tipo_transporte = db.Column(db.Text, nullable=True)
    incluye = db.Column(db.Text, nullable=True)
    cuenta_con = db.Column(db.Text, nullable=True)
    tipo_clima = db.Column(db.String(100), nullable=True)
    altura_maxima = db.Column(db.Float, nullable=True)
    altura_minima = db.Column(db.Float, nullable=True)
    desnivel = db.Column(db.Float, nullable=True)
    desnivel_positivo = db.Column(db.Float, nullable=True)
    desnivel_negativo = db.Column(db.Float, nullable=True)
    altura_positiva = db.Column(db.Float, nullable=True)
    altura_negativa = db.Column(db.Float, nullable=True)
    otros_datos = db.Column(db.Text, nullable=True)
    duracion_horas = db.Column(db.Float, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    participantes = db.relationship(
        'User', secondary=caminata_participantes, lazy='subquery',
        backref=db.backref('caminatas_participa', lazy=True)
    )
    abonos = db.relationship('AbonoCaminata', backref='caminata', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"Caminata('{self.nombre}', '{self.fecha}', '{self.actividad}')"

    __table_args__ = (
        db.Index('idx_caminata_fecha_desc', fecha.desc()),
        db.Index('idx_caminata_actividad', actividad),
    )

class AbonoCaminata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caminata_id = db.Column(db.Integer, db.ForeignKey('caminata.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='abonos_realizados')
    opcion = db.Column(db.String(50), nullable=False)
    cantidad_acompanantes = db.Column(db.Integer, default=0, nullable=False)
    nombres_acompanantes = db.Column(db.Text, nullable=True)
    monto_abono_crc = db.Column(db.Float, default=0)
    monto_abono_usd = db.Column(db.Float, default=0)
    tipo_cambio_bcr = db.Column(db.Float, nullable=True)
    fecha_abono = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    periodo_cancela = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"AbonoCaminata(Caminata: {self.caminata_id}, User: {self.user_id}, CRC: {self.monto_abono_crc}, USD: {self.monto_abono_usd})"

class Pagos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    nombre_caminata = db.Column(db.String(255), nullable=False)
    flyer_imagen_url = db.Column(db.String(255), nullable=True)
    precio_paquete = db.Column(db.Float, default=0)
    capacidad = db.Column(db.Integer, default=0)
    tipo_cambio = db.Column(db.Float, default=0)
    precio_buseta = db.Column(db.Float, default=0)
    cantidad_busetas = db.Column(db.Integer, default=0)
    precio_acuatico = db.Column(db.Float, default=0)
    cantidad_acuatico = db.Column(db.Integer, default=0)
    precio_aereo = db.Column(db.Float, default=0)
    cantidad_aereo = db.Column(db.Integer, default=0)
    precio_otros_transporte = db.Column(db.Float, default=0)
    cantidad_otros_transporte = db.Column(db.Integer, default=0)
    descripcion_otros_transporte = db.Column(db.String(255), nullable=True)
    precio_guias = db.Column(db.Float, default=0)
    precio_guia_por_persona = db.Column(db.Float, default=0)
    cantidad_guias = db.Column(db.Integer, default=0)
    precio_estadia = db.Column(db.Float, default=0)
    cantidad_dias_estadia = db.Column(db.Integer, default=1)
    precio_impuestos = db.Column(db.Float, default=0)
    precio_banos = db.Column(db.Float, default=0)
    precio_servicios_sanitarios = db.Column(db.Float, default=0)
    precio_desayuno = db.Column(db.Float, default=0)
    cantidad_dias_desayuno = db.Column(db.Integer, default=1)
    precio_merienda = db.Column(db.Float, default=0)
    cantidad_dias_merienda = db.Column(db.Integer, default=1)
    precio_almuerzo = db.Column(db.Float, default=0)
    cantidad_dias_almuerzo = db.Column(db.Integer, default=1)
    precio_acarreo = db.Column(db.Float, default=0)
    precio_cafe = db.Column(db.Float, default=0)
    cantidad_dias_cafe = db.Column(db.Integer, default=1)
    precio_cena = db.Column(db.Float, default=0)
    cantidad_dias_cena = db.Column(db.Integer, default=1)
    precio_entrada = db.Column(db.Float, default=0)
    precio_reconocimiento = db.Column(db.Float, default=0)
    precio_permisos = db.Column(db.Float, default=0)
    precio_pasaporte = db.Column(db.Float, default=0)
    precio_otros1_personales = db.Column(db.Float, default=0)
    descripcion_otros1_personales = db.Column(db.String(255), nullable=True)
    precio_otros2_personales = db.Column(db.Float, default=0)
    descripcion_otros2_personales = db.Column(db.String(255), nullable=True)
    precio_otros3_personales = db.Column(db.Float, default=0)
    descripcion_otros3_personales = db.Column(db.String(255), nullable=True)
    precio_otros4_personales = db.Column(db.Float, default=0)
    descripcion_otros4_personales = db.Column(db.String(255), nullable=True)
    total_general_transporte = db.Column(db.Float, default=0)
    total_individual_transporte = db.Column(db.Float, default=0)
    total_general_guias = db.Column(db.Float, default=0)
    total_individual_guias = db.Column(db.Float, default=0)
    total_individual_personales = db.Column(db.Float, default=0)
    total_general_total = db.Column(db.Float, default=0)
    total_individual_total = db.Column(db.Float, default=0)
    ganancia_pp = db.Column(db.Float, default=0)
    ganancia_gral = db.Column(db.Float, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    def __repr__(self):
        return f'<Pagos {self.nombre_caminata}>'

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flyer_imagen_url = db.Column(db.String(255), nullable=True)
    nombre_actividad = db.Column(db.String(255), nullable=False)
    fecha_actividad = db.Column(db.Date, nullable=False)
    hora_actividad = db.Column(db.Time, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    nombre_etiqueta = db.Column(db.String(50), nullable=False)
    es_todo_el_dia = db.Column(db.Boolean, default=False, nullable=False)
    correos_notificacion = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref='created_calendar_events', foreign_keys=[creator_id])

    def __repr__(self):
        return f"CalendarEvent('{self.nombre_actividad}', '{self.fecha_actividad}', '{self.hora_actividad}')"

class Instruction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caminata_id = db.Column(db.Integer, db.ForeignKey('caminata.id'), nullable=False)
    caminata = db.relationship('Caminata', backref='instrucciones')
    dificultad = db.Column(db.String(50), nullable=True)
    distancia = db.Column(db.Float, nullable=True)
    capacidad = db.Column(db.String(20), nullable=True)
    lugar_salida = db.Column(db.String(255), nullable=True)
    fecha_salida = db.Column(db.Date, nullable=True)
    hora_salida = db.Column(db.Time, nullable=True)
    recogemos_en = db.Column(db.Text, nullable=True)
    hidratacion = db.Column(db.String(20), nullable=True)
    litros_hidratacion = db.Column(db.String(20), nullable=True)
    tennis_ligera = db.Column(db.String(20), nullable=True)
    tennis_runner = db.Column(db.String(20), nullable=True)
    tennis_hiking_baja = db.Column(db.String(20), nullable=True)
    zapato_cana_media = db.Column(db.String(20), nullable=True)
    zapato_cana_alta = db.Column(db.String(20), nullable=True)
    bastones = db.Column(db.String(20), nullable=True)
    foco_headlamp = db.Column(db.String(20), nullable=True)
    snacks = db.Column(db.String(20), nullable=True)
    repelente = db.Column(db.String(20), nullable=True)
    poncho = db.Column(db.String(20), nullable=True)
    guantes = db.Column(db.String(20), nullable=True)
    bloqueador = db.Column(db.String(20), nullable=True)
    ropa_cambio = db.Column(db.String(20), nullable=True)
    otras_recomendaciones = db.Column(db.Text, nullable=True)
    normas_generales = db.Column(db.Text, nullable=True)
    otras_indicaciones_generales = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    def __repr__(self):
        return f"Instruction(Caminata_ID: {self.caminata_id}, Fecha Caminata: {self.fecha_caminata})"

class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=True)
    album = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), unique=True, nullable=False)
    cover_image_path = db.Column(db.String(500), nullable=True)
    playlists = db.relationship('Playlist', secondary=playlist_songs, backref='songs')

    def __repr__(self):
        return f'<Song {self.title} by {self.artist}>'

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    
    def __repr__(self):
        return f'<Playlist {self.name}>'

class Itinerario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    caminata_id = db.Column(db.Integer, db.ForeignKey('caminata.id'), nullable=False)
    caminata = db.relationship('Caminata', backref='itinerarios')
    lugar_salida = db.Column(db.String(255), nullable=True)
    hora_salida = db.Column(db.Time, nullable=True)
    puntos_recogida = db.Column(db.Text, nullable=True)
    contenido_itinerario = db.Column(db.Text, nullable=True)
    pasaremos_a_comer = db.Column(db.String(20), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_modificacion = db.Column(db.DateTime, onupdate=datetime.utcnow, nullable=True)

    def __repr__(self):
        return f"Itinerario(Caminata: {self.caminata.nombre}, Fecha: {self.caminata.fecha})"

class AboutUs(db.Model):
    __tablename__ = 'about_us'
    id = db.Column(db.Integer, primary_key=True)
    logo_filename = db.Column(db.String(255), nullable=False)
    logo_info = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    detail = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AboutUs {self.title}>"

class Ruta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(255), nullable=False)
    provincia = db.Column(db.String(50), nullable=False) 
    detalle = db.Column(db.Text, nullable=True)
    enlace_video = db.Column(db.String(500), nullable=True)
    fecha = db.Column(db.Date, nullable=True)
    precio = db.Column(db.Float, nullable=True)
    gpx_file_url = db.Column(db.String(255), nullable=True)
    kml_file_url = db.Column(db.String(255), nullable=True)
    kmz_file_url = db.Column(db.String(255), nullable=True)
    dificultad = db.Column(db.String(50), nullable=False, default='Básico')

    def __repr__(self):
        return f"Ruta(Nombre: {self.nombre}, Categoría: {self.provincia}, Fecha: {self.fecha}, Precio: {self.precio})"

class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), nullable=True) 
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh_key = db.Column(db.String(255), nullable=False)
    auth_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<PushSubscription {self.endpoint}>"

    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh_key,
                "auth": self.auth_key
            }
        }

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    unique_filename = db.Column(db.String(255), unique=True, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader = db.relationship('User', backref='uploaded_files')
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<File {self.original_filename} ({self.file_type})>"

class SiteStats(db.Model):
    __tablename__ = 'site_stats'
    id = db.Column(db.Integer, primary_key=True)
    visits = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SiteStats (ID: {self.id}, Visits: {self.visits})>"

class Poliza(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coordinador_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coordinador = db.relationship('User', foreign_keys=[coordinador_id])
    aseguradora_nombre = db.Column(db.String(150), nullable=True)
    asesor_nombre = db.Column(db.String(150), nullable=True)
    aseguradora_telefono = db.Column(db.String(20), nullable=True)
    aseguradora_email = db.Column(db.String(120), nullable=True)
    asesor_telefono = db.Column(db.String(20), nullable=True)
    asegurado_registrado_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    asegurado_registrado = db.relationship('User', foreign_keys=[asegurado_registrado_id], backref='polizas_asegurado')
    asegurado_nombre_manual = db.Column(db.String(150), nullable=True)
    asegurado_primer_apellido = db.Column(db.String(100), nullable=True)
    asegurado_segundo_apellido = db.Column(db.String(100), nullable=True)
    asegurado_telefono = db.Column(db.String(20), nullable=True)
    asegurado_email = db.Column(db.String(120), nullable=True)
    genero = db.Column(db.String(50), nullable=True)
    costo_tramite = db.Column(db.Float, default=1000.0, nullable=True)
    otros_detalles = db.Column(db.Text, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.now, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    precio_poliza = db.Column(db.Float, nullable=True)
    monto_cancelacion = db.Column(db.Float, nullable=True)
    banco = db.Column(db.String(100), nullable=True)
    cuenta_deposito = db.Column(db.String(100), nullable=True)
    sinpe_deposito = db.Column(db.String(20), nullable=True)
    beneficiarios = db.relationship('Beneficiario', backref='poliza', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        asegurado = self.asegurado_registrado.nombre if self.asegurado_registrado else self.asegurado_nombre_manual
        return f'<Poliza {self.id} para {asegurado}>'

class Beneficiario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    poliza_id = db.Column(db.Integer, db.ForeignKey('poliza.id', ondelete='CASCADE'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=True)
    segundo_apellido = db.Column(db.String(100), nullable=True)
    cedula = db.Column(db.String(20), nullable=True)
    parentesco = db.Column(db.String(50), nullable=True)
    porcentaje = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Beneficiario {self.nombre} para Póliza {self.poliza_id}>'
        


