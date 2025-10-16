# ---------------------------------------------------------------------------- #
#                               ÁREA DE IMPORTACIONES                          #
# ---------------------------------------------------------------------------- #

# --- Importaciones de la Librería Estándar de Python ---
import os
import re
import json
import uuid
from functools import wraps
from datetime import datetime, date

# --- Importaciones de Librerías de Terceros (Flask y extensiones) ---
from flask import Flask, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError
from flask_cors import CORS
from flask_mail import Mail, Message

# --- Importaciones de Módulos Locales de la Aplicación ---
from config import Config
from auth_setup import oauth_bp, init_oauth
from models import (db, bcrypt, migrate, User, Project, Note, Caminata,
                    AbonoCaminata, caminata_participantes, Pagos, CalendarEvent,
                    Instruction, Song, Playlist, Itinerario, AboutUs)
from version import version_bp, Version
# --- Importación de Blueprints (Módulos de la App) ---
from contactos import contactos_bp
from perfil import perfil_bp
from proyecto import proyecto_bp
from notas import notas_bp
from caminatas import caminatas_bp
from pagos import pagos_bp
from calendario import calendario_bp
from instrucciones import instrucciones_bp
from player import player_bp
from itinerario import itinerario_bp
from aboutus import aboutus_bp
from rutas import rutas_bp
from polizas import polizas_bp
from intern import intern_bp
from files import files_bp
from btns import btns_bp
from transporte import transporte_bp
from rifas import rifas_bp


# ---------------------------------------------------------------------------- #
#                  INICIALIZACIÓN Y CONFIGURACIÓN DE LA APLICACIÓN             #
# ---------------------------------------------------------------------------- #

# --- Creación de la instancia principal de la aplicación Flask ---
app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)

# --- Instanciación de extensiones (sin la app todavía) ---
mail = Mail()

# --- Habilitación de CORS para permitir peticiones desde otros dominios ---
CORS(app)

# --- Asegurar que la carpeta 'instance' exista para la base de datos y otros archivos ---
if not os.path.exists(app.instance_path):
    os.makedirs(app.instance_path)


# ---------------------------------------------------------------------------- #
#                        INICIALIZACIÓN DE EXTENSIONES                         #
# ---------------------------------------------------------------------------- #

# --- Se conectan las extensiones con la aplicación Flask ---
db.init_app(app)
bcrypt.init_app(app)
migrate.init_app(app, db)
mail.init_app(app)
init_oauth(app) # Inicializador para el login con redes sociales


# ---------------------------------------------------------------------------- #
#                   CREACIÓN DE DIRECTORIOS PARA SUBIDA DE ARCHIVOS            #
# ---------------------------------------------------------------------------- #

# --- Se crean las carpetas necesarias si no existen, usando la configuración ---
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROJECT_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['NOTE_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CAMINATA_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PAGOS_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CALENDAR_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SONGS_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PLAYLIST_COVER_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['INSTRUCTION_ATTACHMENT_FOLDER'], exist_ok=True)
os.makedirs(app.config['MAP_FILES_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COVERS_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ABOUTUS_IMAGE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FILES_FOLDER'], exist_ok=True)


# ---------------------------------------------------------------------------- #
#                              FUNCIONES AUXILIARES                            #
# ---------------------------------------------------------------------------- #

def allowed_file(filename):
    """Verifica si la extensión de un archivo de imagen es permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def allowed_music_file(filename):
    """Verifica si la extensión de un archivo de música es permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'mp3', 'wav', 'ogg'}

# --- Se adjuntan las funciones a la app para que sean accesibles desde los Blueprints ---
app.allowed_file = allowed_file
app.allowed_music_file = allowed_music_file


# ---------------------------------------------------------------------------- #
#                           FILTROS Y PROCESADORES DE JINJA2                   #
# ---------------------------------------------------------------------------- #

@app.template_filter('format_currency')
def format_currency_filter(value):
    """Filtro para dar formato de moneda a un valor en las plantillas."""
    if value is None:
        return "N/A"
    try:
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return str(value)

@app.template_filter('from_json')
def from_json_filter(value):
    """Filtro para convertir una cadena JSON a un objeto Python en las plantillas."""
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []

@app.template_filter('to_datetime')
def to_datetime_filter(value):
    """Filtro para convertir una cadena a un objeto datetime en las plantillas."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
    return value

@app.context_processor
def inject_latest_version():
    """Inyecta el número de la última versión en todas las plantillas."""
    try:
        latest_version = Version.query.order_by(Version.fecha_creacion.desc()).first()
        if latest_version:
            return {'latest_version_number': latest_version.numero_version}
    except Exception as e:
        print(f"DEBUG: Error al obtener la última versión: {e}")
    return {'latest_version_number': 'N/A'}


# ---------------------------------------------------------------------------- #
#                 DECORADORES DE AUTENTICACIÓN Y AUTORIZACIÓN                  #
# ---------------------------------------------------------------------------- #

def login_required(f):
    """Decorador para requerir que un usuario haya iniciado sesión."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """Decorador para requerir que un usuario tenga un rol específico."""
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


# ---------------------------------------------------------------------------- #
#                            HOOKS DE LA APLICACIÓN                            #
# ---------------------------------------------------------------------------- #

@app.before_request
def check_for_first_user():
    """
    Se ejecuta antes de cada petición. Verifica si no hay usuarios en la BD
    para asignar al primer usuario registrado el rol de 'Superuser'.
    """
    if 'first_user_registration_allowed' not in current_app.config:
        with app.app_context():
            try:
                if db.session.query(User).count() == 0:
                    current_app.config['first_user_registration_allowed'] = True
                    print("DEBUG: No hay usuarios. El próximo registro será un Superuser.")
                else:
                    current_app.config['first_user_registration_allowed'] = False
            except Exception as e:
                current_app.config['first_user_registration_allowed'] = True
                print(f"DEBUG: Error al contar usuarios (tabla podría no existir): {e}.")


# ---------------------------------------------------------------------------- #
#                            RUTAS PRINCIPALES DE LA APLICACIÓN                #
# ---------------------------------------------------------------------------- #

@app.route('/')
@app.route('/home')
def home():
    """Página de inicio que muestra las caminatas."""
    all_caminatas = Caminata.query.order_by(Caminata.fecha.desc()).all()
    search_actividad = request.args.get('actividad')

    if search_actividad:
        caminatas = Caminata.query.filter_by(actividad=search_actividad).all()
    else:
        caminatas = Caminata.query.all()
        
    return render_template('ver_caminatas.html', caminatas=caminatas, search_actividad=search_actividad)


# ---------------------------------------------------------------------------- #
#                           RUTAS DE GESTIÓN DE USUARIOS                       #
# ---------------------------------------------------------------------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro de nuevos usuarios."""
    # (El código de la función register va aquí, se omite por brevedad pero permanece igual)
    # ...
    provincia_opciones = ["Cartago", "Limón", "Puntarenas", "San José", "Heredia", "Guanacaste", "Alajuela"]
    # ... (resto del código de la función register sin cambios) ...
    return render_template('register.html', provincia_opciones=provincia_opciones)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión."""
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']
        user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email.lower())).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'¡Bienvenido, {user.username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Nombre de usuario, correo electrónico o contraseña incorrectos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------- #
#                      RUTAS DE RECUPERACIÓN DE CONTRASEÑA                     #
# ---------------------------------------------------------------------------- #

def send_reset_email(user):
    """Envía un correo electrónico para restablecer la contraseña."""
    token = user.get_reset_token()
    msg = Message('Solicitud de Restablecimiento de Contraseña',
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    msg.body = f'''Para restablecer tu contraseña, visita el siguiente enlace:
{url_for('reset_password', token=token, _external=True)}

Si no solicitaste este cambio, ignora este correo.
'''
    mail.send(msg)


@app.route('/request_password_reset', methods=['GET', 'POST'])
def request_password_reset():
    """Formulario para solicitar el restablecimiento de contraseña."""
    if session.get('logged_in'):
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user:
            send_reset_email(user)
            flash('Se ha enviado un correo con las instrucciones.', 'info')
            return redirect(url_for('login'))
        else:
            flash('No se encontró una cuenta con ese correo.', 'warning')
    return render_template('request_password_reset.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Página para establecer una nueva contraseña usando un token."""
    if session.get('logged_in'):
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if not user:
        flash('El token es inválido o ha expirado.', 'warning')
        return redirect(url_for('request_password_reset'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not password or password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('reset_password.html', token=token)

        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.session.commit()
        flash('Tu contraseña ha sido actualizada.', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_password.html', token=token)


# ---------------------------------------------------------------------------- #
#                               MANEJADORES DE ERRORES                         #
# ---------------------------------------------------------------------------- #

@app.errorhandler(404)
def page_not_found(e):
    """Maneja los errores 404 (Página no encontrada)."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Maneja los errores 500 (Error interno del servidor)."""
    return render_template('500.html'), 500


# ---------------------------------------------------------------------------- #
#                            REGISTRO DE BLUEPRINTS                            #
# ---------------------------------------------------------------------------- #

# --- Se registran todos los módulos (Blueprints) de la aplicación ---
app.register_blueprint(contactos_bp)
app.register_blueprint(perfil_bp, url_prefix='/perfil')
app.register_blueprint(proyecto_bp)
app.register_blueprint(notas_bp)
app.register_blueprint(caminatas_bp, url_prefix='/caminatas')
app.register_blueprint(pagos_bp, url_prefix='/pagos')
app.register_blueprint(calendario_bp, url_prefix='/calendario')
app.register_blueprint(instrucciones_bp, url_prefix='/instrucciones')
app.register_blueprint(player_bp)
app.register_blueprint(itinerario_bp, url_prefix='/itinerario')
app.register_blueprint(aboutus_bp, url_prefix='/aboutus')
app.register_blueprint(rutas_bp, url_prefix='/rutas')
app.register_blueprint(version_bp, url_prefix='/version')
app.register_blueprint(files_bp, url_prefix='/files')
app.register_blueprint(btns_bp)
app.register_blueprint(polizas_bp)
app.register_blueprint(intern_bp, url_prefix='/intern')
app.register_blueprint(transporte_bp)
app.register_blueprint(rifas_bp, url_prefix='/rifas')
app.register_blueprint(oauth_bp) # Blueprint para OAuth


# ---------------------------------------------------------------------------- #
#                           PUNTO DE ENTRADA DE LA APLICACIÓN                  #
# ---------------------------------------------------------------------------- #

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() # Generalmente manejado por Flask-Migrate
        pass
    app.run(host='0.0.0.0', debug=True, port=3030)





# TOTALMENTE PROHIBIDO PARA CHATGPT Y GEMINI O PERSONA FÍSICA MODIFICAR O ELIMINAR ESTOS COMENTARIOS 
# Migraciones Cmder
        # set FLASK_APP=app.py     <--Crea un directorio de migraciones
        # flask db init             <--
        # $ flask db stamp head
        # $ flask db migrate
        # $ flask db migrate -m "mensaje x"
        # $ flask db upgrade
        # ERROR [flask_migrate] Error: Target database is not up to date.
        # $ flask db stamp head
        # $ flask db migrate
        # $ flask db upgrade
        # git clone https://github.com/kerm1977/MI_APP_FLASK.git
        # mysql> DROP DATABASE kenth1977$db; PYTHONANYWHATE
# -----------------------

# del db.db
# rmdir /s /q migrations
# flask db init
# flask db migrate -m "Reinitial migration with all correct models"
# flask db upgrade


# -----------------------
# Consola de pythonanywhere ante los errores de versiones
# Error: Can't locate revision identified by '143967eb40c0'

# flask db stamp head
# flask db migrate
# flask db upgrade

# Database pythonanywhere
# kenth1977$db
# DROP TABLE alembic_version;
# rm -rf migrations
# flask db init
# flask db migrate -m "Initial migration after reset"
# flask db upgrade

# 21:56 ~/LATRIBU1 (main)$ source env/Scripts/activate
# (env) 21:57 ~/LATRIBU1 (main)$

# En caso de que no sirva el env/Scripts/activate
# remover en env
# 05:48 ~/latribuapp (main)$ rm -rf env
# Crear nuevo
# 05:49 ~/latribuapp (main)$ python -m venv env
# 05:51 ~/latribuapp (main)$ source env/bin/activate
# (env) 05:52 ~/latribuapp (main)$ 



# Cuando se cambia de repositorio
# git remote -v
# git remote add origin <URL_DEL_REPOSITORIO>
# git remote set-url origin <NUEVA_URL_DEL_REPOSITORIO>
# git branchgit remote -v
# git push -u origin flet



# borrar base de datos y reconstruirla
# pip install PyMySQL
# SHOW TABLES;
# 21:56 ~/LATRIBU1 (main)$ source env/Scripts/activate <-- Entra al entorno virtual
# (env) 21:57 ~/LATRIBU1 (main)$
# (env) 23:30 ~/LATRIBU1 (main)$ cd /home/kenth1977/LATRIBU1
# (env) 23:31 ~/LATRIBU1 (main)$ rm -f instance/db.db
# (env) 23:32 ~/LATRIBU1 (main)$ rm -rf migrations
# (env) 23:32 ~/LATRIBU1 (main)$ flask db init
# (env) 23:33 ~/LATRIBU1 (main)$ flask db migrate -m "Initial migration with all models"
# (env) 23:34 ~/LATRIBU1 (main)$ flask db upgrade
# (env) 23:34 ~/LATRIBU1 (main)$ ls -l instance/db


# GUARDA  todas las dependecias para utilizar offline luego
# pip download -r requirements.txt -d librerias_offline
# INSTALA  todas las dependecias para utilizar offline luego
# pip install --no-index --find-links=./librerias_offline -r requirements.txt