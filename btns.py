# btns.py
import json
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

# Crea un Blueprint para organizar las rutas relacionadas con los botones.
btns_bp = Blueprint('btns', __name__)

# Define el nombre del archivo donde se guardará la configuración de los botones.
CONFIG_FILE = 'buttons_config.json'

def load_button_config():
    """
    Carga la configuración de ambos botones desde el archivo JSON.
    Si el archivo no existe o está corrupto, devuelve una configuración por defecto.
    """
    default_config = {
        "button_one": {"link": "#", "visibility_state": "all", "is_visible": True, "icon": "fa-link"},
        "button_two": {"link": "#", "visibility_state": "disabled", "is_visible": False, "icon": "fa-file-pdf"}
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            try:
                config = json.load(f)
                # Asegurarse de que la configuración por defecto se aplique si faltan claves
                for btn_key in ['button_one', 'button_two']:
                    if btn_key not in config:
                        config[btn_key] = default_config[btn_key]
                    else:
                        # Asegurar que las claves de visibilidad existan
                        if 'visibility_state' not in config[btn_key]:
                            config[btn_key]['visibility_state'] = default_config[btn_key]['visibility_state']
                        config[btn_key]['is_visible'] = (config[btn_key]['visibility_state'] != 'disabled')
                        if 'icon' not in config[btn_key]:
                             config[btn_key]['icon'] = default_config[btn_key]['icon']

                return config
            except json.JSONDecodeError:
                print(f"Advertencia: El archivo {CONFIG_FILE} está corrupto. Usando configuración por defecto.")
                return default_config
    return default_config

def save_button_config(config):
    """
    Guarda la configuración de los botones en el archivo JSON.
    """
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4) # indent=4 para una mejor legibilidad del JSON

@btns_bp.route('/crear_btns', methods=['GET', 'POST'])
def crear_btns():
    """
    Maneja la lógica para el formulario de configuración de los botones.
    """
    if request.method == 'POST':
        # Recoger datos para el botón 1
        link1 = request.form.get('enlace_1', '#')
        visibility_state1 = request.form.get('visibilidad_1', 'all')
        icon1 = request.form.get('icon_1', 'fa-link')
        is_visible1 = (visibility_state1 != 'disabled')

        # Recoger datos para el botón 2
        link2 = request.form.get('enlace_2', '#')
        visibility_state2 = request.form.get('visibilidad_2', 'all')
        icon2 = request.form.get('icon_2', 'fa-file-pdf')
        is_visible2 = (visibility_state2 != 'disabled')

        # Crear el nuevo diccionario de configuración
        new_config = {
            "button_one": {"link": link1, "visibility_state": visibility_state1, "is_visible": is_visible1, "icon": icon1},
            "button_two": {"link": link2, "visibility_state": visibility_state2, "is_visible": is_visible2, "icon": icon2}
        }
        save_button_config(new_config)

        flash('Configuración de los botones guardada con éxito!', 'success')
        return redirect(url_for('btns.crear_btns'))
    
    # Para GET, cargar la configuración y mostrar el formulario
    config = load_button_config()
    return render_template('crear_btns.html', config=config)

@btns_bp.route('/get_btn_config')
def get_btn_config():
    """
    Endpoint API para que el frontend obtenga la configuración actual de los botones.
    """
    return jsonify(load_button_config())

@btns_bp.route('/get_session_status')
def get_session_status():
    """
    Endpoint API para que el frontend obtenga el estado actual de la sesión del usuario.
    """
    return jsonify({
        "logged_in": session.get('logged_in', False),
        "is_superuser": session.get('role') == 'Superuser' # Comprobación más precisa del rol
    })

# --- Simulación de Autenticación/Roles de Usuario ---
# Estas rutas son para demostración y simulan el inicio y cierre de sesión.
@btns_bp.route('/login/<role>')
def login(role):
    """
    Simula el inicio de sesión de un usuario con un rol específico.
    """
    session.clear() # Limpia la sesión anterior

    if role == 'regular':
        session['logged_in'] = True
        session['role'] = 'Regular'
        flash('Has iniciado sesión como Usuario Regular.', 'info')
    elif role == 'superuser':
        session['logged_in'] = True
        session['role'] = 'Superuser'
        flash('Has iniciado sesión como Superusuario.', 'info')
    else: # Cualquier otro valor o 'logout'
        session['logged_in'] = False
        session.pop('role', None)
        flash('Has cerrado sesión.', 'info')
    # Redirige a una página principal para ver el efecto
    return redirect(url_for('home')) 

@btns_bp.route('/index_test') # Ruta de prueba
def index():
    """
    Ruta para una página de prueba que renderiza base.html.
    """
    return render_template('base.html')
