# polizas.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify, send_file
from models import db, User, Poliza, Beneficiario
from functools import wraps
from datetime import datetime
import pytz # Para manejar zonas horarias
import io

# --- LIBRERÍAS PARA EXPORTACIÓN ---
# (Asegúrate de instalarlas: pip install reportlab openpyxl)
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- DECORADOR DE ROLES (para mantener el archivo autocontenido) ---
def role_required(roles):
    if not isinstance(roles, list):
        roles = [roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- BLUEPRINT DE PÓLIZAS ---
polizas_bp = Blueprint('polizas', __name__, url_prefix='/polizas')

# --- RUTAS ---

@polizas_bp.route('/ver')
@role_required(['Superuser', 'Usuario Regular'])
def ver_polizas():
    user_id = session.get('user_id')
    user_role = session.get('role')
    
    if user_role == 'Superuser':
        polizas = Poliza.query.order_by(Poliza.fecha_registro.desc()).all()
    else:
        polizas = Poliza.query.filter_by(asegurado_registrado_id=user_id).order_by(Poliza.fecha_registro.desc()).all()
        
    return render_template('ver_polizas.html', polizas=polizas)


@polizas_bp.route('/crear', methods=['GET', 'POST'])
@role_required(['Superuser'])
def crear_poliza():
    if request.method == 'POST':
        try:
            # --- Recopilar datos del formulario ---
            coordinador_id = request.form.get('coordinador_id')
            aseguradora_nombre = request.form.get('aseguradora_nombre')
            asesor_nombre = request.form.get('asesor_nombre')
            aseguradora_telefono = request.form.get('aseguradora_telefono')
            asesor_telefono = request.form.get('asesor_telefono')
            aseguradora_email = request.form.get('aseguradora_email')
            
            tipo_asegurado = request.form.get('tipo_asegurado')
            asegurado_registrado_id = request.form.get('asegurado_registrado_id')
            asegurado_nombre_manual = request.form.get('asegurado_nombre_manual')
            
            asegurado_primer_apellido = request.form.get('asegurado_primer_apellido')
            asegurado_segundo_apellido = request.form.get('asegurado_segundo_apellido')
            asegurado_telefono = request.form.get('asegurado_telefono')
            asegurado_email = request.form.get('asegurado_email')
            genero = request.form.get('genero')
            
            costo_tramite = request.form.get('costo_tramite', 1000.0, type=float)
            otros_detalles = request.form.get('otros_detalles')

            # --- Crear la nueva póliza ---
            nueva_poliza = Poliza(
                coordinador_id=coordinador_id,
                aseguradora_nombre=aseguradora_nombre,
                asesor_nombre=asesor_nombre,
                aseguradora_telefono=aseguradora_telefono,
                asesor_telefono=asesor_telefono,
                aseguradora_email=aseguradora_email,
                asegurado_primer_apellido=asegurado_primer_apellido,
                asegurado_segundo_apellido=asegurado_segundo_apellido,
                asegurado_telefono=asegurado_telefono,
                asegurado_email=asegurado_email,
                genero=genero,
                costo_tramite=costo_tramite,
                otros_detalles=otros_detalles,
                fecha_registro=datetime.now(pytz.timezone('America/Costa_Rica'))
            )

            if tipo_asegurado == 'registrado':
                nueva_poliza.asegurado_registrado_id = asegurado_registrado_id if asegurado_registrado_id else None
            else:
                nueva_poliza.asegurado_nombre_manual = asegurado_nombre_manual

            db.session.add(nueva_poliza)
            
            # --- Recopilar y agregar beneficiarios ---
            nombres = request.form.getlist('beneficiario_nombre[]')
            primeros_apellidos = request.form.getlist('beneficiario_primer_apellido[]')
            segundos_apellidos = request.form.getlist('beneficiario_segundo_apellido[]')
            cedulas = request.form.getlist('beneficiario_cedula[]')
            parentescos = request.form.getlist('beneficiario_parentesco[]')
            porcentajes = request.form.getlist('beneficiario_porcentaje[]')

            for i in range(len(nombres)):
                if nombres[i]: # Solo agregar si el nombre no está vacío
                    nuevo_beneficiario = Beneficiario(
                        poliza=nueva_poliza,
                        nombre=nombres[i],
                        primer_apellido=primeros_apellidos[i],
                        segundo_apellido=segundos_apellidos[i],
                        cedula=cedulas[i],
                        parentesco=parentescos[i],
                        porcentaje=float(porcentajes[i]) if porcentajes[i] else None
                    )
                    db.session.add(nuevo_beneficiario)
            
            db.session.commit()
            flash('Póliza creada exitosamente.', 'success')
            return redirect(url_for('polizas.ver_polizas'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear la póliza: {str(e)}', 'danger')
            current_app.logger.error(f"Error en crear_poliza: {e}")

    # --- Lógica para el método GET ---
    superusers = User.query.filter_by(role='Superuser').all()
    all_users = User.query.order_by(User.nombre).all()
    return render_template('crear_polizas.html', superusers=superusers, all_users=all_users)


@polizas_bp.route('/detalle/<int:poliza_id>')
@role_required(['Superuser', 'Usuario Regular'])
def detalle_poliza(poliza_id):
    poliza = Poliza.query.get_or_404(poliza_id)
    user_id = session.get('user_id')
    user_role = session.get('role')

    # Verificación de permisos
    if user_role == 'Usuario Regular' and poliza.asegurado_registrado_id != user_id:
        flash('No tienes permiso para ver esta póliza.', 'danger')
        return redirect(url_for('polizas.ver_polizas'))

    return render_template('detalle_polizas.html', poliza=poliza)

@polizas_bp.route('/editar/<int:poliza_id>', methods=['GET', 'POST'])
@role_required(['Superuser']) 
def editar_poliza(poliza_id):
    poliza = Poliza.query.get_or_404(poliza_id)

    if request.method == 'POST':
        try:
            # Actualizar datos de la póliza
            poliza.coordinador_id = request.form.get('coordinador_id')
            poliza.aseguradora_nombre = request.form.get('aseguradora_nombre')
            poliza.asesor_nombre = request.form.get('asesor_nombre')
            poliza.aseguradora_telefono = request.form.get('aseguradora_telefono')
            poliza.asesor_telefono = request.form.get('asesor_telefono')
            poliza.aseguradora_email = request.form.get('aseguradora_email')
            
            tipo_asegurado = request.form.get('tipo_asegurado')
            if tipo_asegurado == 'registrado':
                poliza.asegurado_registrado_id = request.form.get('asegurado_registrado_id')
                poliza.asegurado_nombre_manual = None
            else:
                poliza.asegurado_registrado_id = None
                poliza.asegurado_nombre_manual = request.form.get('asegurado_nombre_manual')

            poliza.asegurado_primer_apellido = request.form.get('asegurado_primer_apellido')
            poliza.asegurado_segundo_apellido = request.form.get('asegurado_segundo_apellido')
            poliza.asegurado_telefono = request.form.get('asegurado_telefono')
            poliza.asegurado_email = request.form.get('asegurado_email')
            poliza.genero = request.form.get('genero')
            poliza.costo_tramite = request.form.get('costo_tramite', type=float)
            poliza.otros_detalles = request.form.get('otros_detalles')

            # Manejar beneficiarios
            ids = request.form.getlist('beneficiario_id[]')
            nombres = request.form.getlist('beneficiario_nombre[]')
            primeros_apellidos = request.form.getlist('beneficiario_primer_apellido[]')
            segundos_apellidos = request.form.getlist('beneficiario_segundo_apellido[]')
            cedulas = request.form.getlist('beneficiario_cedula[]')
            parentescos = request.form.getlist('beneficiario_parentesco[]')
            porcentajes = request.form.getlist('beneficiario_porcentaje[]')

            ids_en_formulario = {int(id) for id in ids if id != 'new'}
            ids_en_db = {b.id for b in poliza.beneficiarios}

            for id_a_eliminar in ids_en_db - ids_en_formulario:
                beneficiario = Beneficiario.query.get(id_a_eliminar)
                db.session.delete(beneficiario)

            for i in range(len(ids)):
                if not nombres[i]: continue
                
                beneficiario_id = ids[i]
                data = {
                    'nombre': nombres[i],
                    'primer_apellido': primeros_apellidos[i],
                    'segundo_apellido': segundos_apellidos[i],
                    'cedula': cedulas[i],
                    'parentesco': parentescos[i],
                    'porcentaje': float(porcentajes[i]) if porcentajes[i] else None
                }

                if beneficiario_id == 'new':
                    nuevo_beneficiario = Beneficiario(poliza_id=poliza.id, **data)
                    db.session.add(nuevo_beneficiario)
                else:
                    beneficiario = Beneficiario.query.get(int(beneficiario_id))
                    if beneficiario:
                        for key, value in data.items():
                            setattr(beneficiario, key, value)
            
            db.session.commit()
            flash('Póliza actualizada exitosamente.', 'success')
            return redirect(url_for('polizas.detalle_poliza', poliza_id=poliza.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la póliza: {str(e)}', 'danger')
            current_app.logger.error(f"Error en editar_poliza: {e}")

    superusers = User.query.filter_by(role='Superuser').all()
    all_users = User.query.order_by(User.nombre).all()
    return render_template('editar_polizas.html', poliza=poliza, superusers=superusers, all_users=all_users)


@polizas_bp.route('/eliminar/<int:poliza_id>', methods=['POST'])
@role_required(['Superuser'])
def eliminar_poliza(poliza_id):
    poliza_a_eliminar = Poliza.query.get_or_404(poliza_id)
    try:
        db.session.delete(poliza_a_eliminar)
        db.session.commit()
        flash('La póliza ha sido eliminada exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la póliza: {str(e)}', 'danger')
        current_app.logger.error(f"Error en eliminar_poliza: {e}")
    
    return redirect(url_for('polizas.ver_polizas'))

# --- LÓGICA DE EXPORTACIÓN ---

def _generar_contenido_texto(poliza):
    """Función auxiliar para generar el contenido de texto para TXT y PDF."""
    contenido = []
    asegurado_nombre = ""
    if poliza.asegurado_registrado:
        asegurado_nombre = f"{poliza.asegurado_registrado.nombre} {poliza.asegurado_registrado.primer_apellido}"
    else:
        asegurado_nombre = f"{poliza.asegurado_nombre_manual} {poliza.asegurado_primer_apellido}"

    contenido.append(f"Detalle de Póliza para: {asegurado_nombre}\n")
    contenido.append("="*40 + "\n")

    if session.get('role') == 'Superuser':
        contenido.append("DATOS DE LA ASEGURADORA\n")
        contenido.append(f"  Coordinador: {poliza.coordinador.nombre} {poliza.coordinador.primer_apellido}\n")
        contenido.append(f"  Aseguradora: {poliza.aseguradora_nombre or 'N/A'}\n")
        contenido.append(f"  Asesor: {poliza.asesor_nombre or 'N/A'}\n")
        contenido.append(f"  Teléfono Aseguradora: {poliza.aseguradora_telefono or 'N/A'}\n")
        contenido.append(f"  Email Aseguradora: {poliza.aseguradora_email or 'N/A'}\n")
        contenido.append(f"  Teléfono Asesor: {poliza.asesor_telefono or 'N/A'}\n\n")

    contenido.append("DATOS DEL ASEGURADO\n")
    contenido.append(f"  Nombre Completo: {asegurado_nombre} {poliza.asegurado_segundo_apellido or ''}\n")
    contenido.append(f"  Teléfono: {poliza.asegurado_telefono or 'N/A'}\n")
    contenido.append(f"  Email: {poliza.asegurado_email or 'N/A'}\n")
    contenido.append(f"  Género: {poliza.genero or 'N/A'}\n\n")

    contenido.append("BENEFICIARIOS\n")
    if poliza.beneficiarios:
        for b in poliza.beneficiarios:
            contenido.append(f"  - {b.nombre} {b.primer_apellido} {b.segundo_apellido or ''}\n")
            contenido.append(f"    Cédula: {b.cedula or 'N/A'}, Parentesco: {b.parentesco or 'N/A'}, Porcentaje: {b.porcentaje or 'N/A'}%\n")
    else:
        contenido.append("  No hay beneficiarios registrados.\n")
    
    contenido.append("\nDETALLES ADICIONALES\n")
    if session.get('role') == 'Superuser':
        contenido.append(f"  Costo del Trámite: ₡{poliza.costo_tramite:,.2f}\n")
    contenido.append(f"  Fecha de Registro: {poliza.fecha_registro.strftime('%d/%m/%Y %I:%M %p')}\n")
    if poliza.otros_detalles:
        contenido.append(f"\nNotas:\n{poliza.otros_detalles}\n")

    return "".join(contenido)

@polizas_bp.route('/exportar/<int:poliza_id>/<string:format>')
@role_required(['Superuser', 'Usuario Regular'])
def exportar_poliza(poliza_id, format):
    poliza = Poliza.query.get_or_404(poliza_id)
    user_id = session.get('user_id')
    user_role = session.get('role')

    if user_role == 'Usuario Regular' and poliza.asegurado_registrado_id != user_id:
        flash('No tienes permiso para exportar esta póliza.', 'danger')
        return redirect(url_for('polizas.ver_polizas'))

    filename = f"poliza_{poliza.id}.{format}"
    
    if format == 'txt':
        contenido = _generar_contenido_texto(poliza)
        buffer = io.BytesIO(contenido.encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/plain; charset=utf-8')

    elif format == 'xls':
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Detalle de Póliza"
        
        # Escribir datos
        sheet.append(["Campo", "Valor"])
        sheet.append(["Asegurado", f"{poliza.asegurado_registrado.nombre if poliza.asegurado_registrado else poliza.asegurado_nombre_manual}"])
        # ... agregar todas las demás filas ...
        sheet.append([])
        sheet.append(["Beneficiarios"])
        sheet.append(["Nombre", "Cédula", "Parentesco", "Porcentaje"])
        for b in poliza.beneficiarios:
            sheet.append([f"{b.nombre} {b.primer_apellido}", b.cedula, b.parentesco, b.porcentaje])

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.ms-excel')

    elif format == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        texto_contenido = _generar_contenido_texto(poliza)
        for line in texto_contenido.split('\n'):
            story.append(Paragraph(line.replace(' ', '&nbsp;'), styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    elif format == 'jpg':
        flash('La exportación a JPG se realiza directamente desde el navegador. Usa el botón correspondiente en la página de detalles.', 'info')
        return redirect(url_for('polizas.detalle_poliza', poliza_id=poliza_id))

    return "Formato no válido", 400


# --- RUTA AUXILIAR PARA AUTOCOMPLETAR DATOS DE USUARIO ---
@polizas_bp.route('/get_user_data/<int:user_id>')
@role_required(['Superuser'])
def get_user_data(user_id):
    user = User.query.get(user_id)
    if user:
        user_data = {
            'primer_apellido': user.primer_apellido or '',
            'segundo_apellido': user.segundo_apellido or '',
            'telefono': user.telefono or '',
            'email': user.email or ''
        }
        return jsonify(user_data)
    return jsonify({'error': 'Usuario no encontrado'}), 404
