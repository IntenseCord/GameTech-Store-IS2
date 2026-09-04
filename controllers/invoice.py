"""
Controlador de facturas electrónicas colombianas
Maneja la solicitud, generación y envío de facturas por correo
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models.database_models import Invoice, Order, User
from utils.invoice_generator_colombia import InvoiceGeneratorColombia as InvoiceGenerator
from utils.email_sender import enviar_factura_por_email
from utils.error_handling import log_db_error
import os
from datetime import datetime

CART_ORDENES = 'cart.mis_ordenes'
VER_FACTURA = 'invoice.ver_factura'
SOLICITAR_FACTURA = 'invoice/solicitar_factura.html'

invoice_bp = Blueprint('invoice', __name__)

@invoice_bp.route('/factura/solicitar/<int:order_id>', methods=['GET', 'POST'])
@login_required
def solicitar_factura(order_id):
    """Solicitar factura para una orden"""
    order = Order.query.get_or_404(order_id)

    if not _orden_pertenece_usuario(order):
        return _orden_sin_permiso()

    invoice_existente = Invoice.query.filter_by(order_id=order.id).first()
    if invoice_existente:
        return _orden_facturada(invoice_existente)

    if request.method == 'POST':
        datos = _datos_formulario_factura(request)
        error = _validar_datos_factura(datos)
        if error:
            flash(error, "danger")
            return render_template(SOLICITAR_FACTURA, order=order, user=current_user)

        try:
            if datos['guardar_datos']:
                _guardar_datos_usuario(datos)

            invoice = _crear_objeto_factura(order, datos)
            db.session.add(invoice)
            pdf_path = _generar_pdf_factura(invoice, order)
            invoice.pdf_path = pdf_path

            db.session.commit()

            # La factura ya quedó guardada en este punto: un fallo al enviar el
            # correo no debe hacer creer al usuario que la generación falló.
            if not enviar_factura_por_email(invoice, current_user, pdf_path):
                current_app.logger.warning(f'No se pudo enviar la factura {invoice.folio} por correo')

            flash(f'¡Factura generada exitosamente! Folio: {invoice.folio}', 'success')
            return redirect(url_for(CART_ORDENES))
        except (SQLAlchemyError, OSError) as e:
            # SQLAlchemyError: fallo de BD al guardar la factura. OSError: fallo al escribir el PDF a disco.
            log_db_error('solicitar_factura', e)
            _traceback_log()
            flash(f'Error al generar la factura: {str(e)}', 'danger')
            return render_template(SOLICITAR_FACTURA, order=order, user=current_user)

    # GET - Mostrar formulario
    return render_template(SOLICITAR_FACTURA, order=order, user=current_user)


def _orden_pertenece_usuario(order):
    return order.user_id == current_user.id

def _orden_sin_permiso():
    flash('No tienes permiso para facturar esta orden', 'danger')
    return redirect(url_for(CART_ORDENES))

def _orden_facturada(invoice_existente):
    flash('Esta orden ya tiene una factura generada', 'info')
    return redirect(url_for(VER_FACTURA, invoice_id=invoice_existente.id))

def _datos_formulario_factura(request):
    return {
        'nit': request.form.get('nit', '').strip(),
        'tipo_documento': request.form.get('tipo_documento', '31'),
        'razon_social': request.form.get('razon_social', '').strip(),
        'direccion_fiscal': request.form.get('direccion_fiscal', '').strip(),
        'ciudad': request.form.get('ciudad', '').strip(),
        'departamento': request.form.get('departamento', '').strip(),
        'codigo_postal': request.form.get('codigo_postal', '').strip(),
        'telefono': request.form.get('telefono', '').strip(),
        'forma_pago': request.form.get('forma_pago', 'Tarjeta de Crédito'),
        'guardar_datos': bool(request.form.get('guardar_datos')),
    }

def _validar_datos_factura(datos):
    if not datos['nit'] or not datos['razon_social']:
        return 'NIT/CC y Razón Social son obligatorios'
    if len(datos['nit']) < 6 or len(datos['nit']) > 20:
        return 'NIT/CC inválido. Debe tener entre 6 y 20 caracteres'
    return None

def _guardar_datos_usuario(datos):
    current_user.rfc = datos['nit']
    current_user.razon_social = datos['razon_social']
    current_user.direccion_fiscal = datos['direccion_fiscal']
    current_user.codigo_postal = datos['codigo_postal']
    db.session.commit()
    current_app.logger.info('Datos fiscales guardados en usuario')

def _crear_objeto_factura(order, datos):
    import uuid as uuid_lib
    invoice_uuid = str(uuid_lib.uuid4())
    # order.total es Decimal (columna NUMERIC); convertir a float antes de
    # operar con 1.19, ya que Python no permite Decimal / float directamente.
    total = float(order.total)
    subtotal = total / 1.19
    return Invoice(
        uuid=invoice_uuid,
        order_id=order.id,
        user_id=current_user.id,
        folio=f'FE-{order.id:06d}',
        fecha_emision=datetime.now(),
        nit_receptor=datos['nit'] or '000000000',
        tipo_documento_receptor=datos['tipo_documento'] or '31',
        razon_social_receptor=datos['razon_social'] or 'Cliente General',
        direccion_fiscal=datos['direccion_fiscal'] or 'N/A',
        ciudad=datos['ciudad'] or 'Bogotá',
        departamento=datos['departamento'] or 'Bogotá D.C.',
        codigo_postal=datos['codigo_postal'] or '110111',
        telefono=datos['telefono'] or '0000000000',
        email_receptor=current_user.email or 'cliente@example.com',
        nit_emisor='900123456-7',
        razon_social_emisor='GameTech Store SAS',
        regimen_emisor='Responsable de IVA',
        subtotal=subtotal,
        iva=total - subtotal,
        total=total,
        forma_pago=datos['forma_pago'] or 'Tarjeta de Crédito',
        metodo_pago='Contado',
        status='active',
        cufe=invoice_uuid,
    )

def _generar_pdf_factura(invoice, order):
    temp_id = f"{order.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pdf_filename = f'factura_{invoice.folio}_{temp_id}.pdf'
    pdf_dir = os.path.join('static', 'invoices', 'pdf')
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, pdf_filename)
    full_pdf_path = os.path.join(os.getcwd(), pdf_path)
    InvoiceGenerator.generate_pdf(invoice, order, full_pdf_path)
    current_app.logger.info(f'PDF generado exitosamente: {pdf_path}')
    return pdf_path

def _traceback_log():
    import traceback
    current_app.logger.error(traceback.format_exc())

@invoice_bp.route('/factura/<int:invoice_id>')
@login_required
def ver_factura(invoice_id):
    """Ver detalles de una factura"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verificar que la factura pertenece al usuario
    if invoice.user_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para ver esta factura', 'danger')
        return redirect(url_for(CART_ORDENES))
    
    return render_template('invoice/ver_factura.html', invoice=invoice)

@invoice_bp.route('/factura/descargar/<int:invoice_id>')
@login_required
def descargar_factura(invoice_id):
    """Descargar PDF de factura"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Verificar permisos
    if invoice.user_id != current_user.id and not current_user.is_admin:
        flash('No tienes permiso para descargar esta factura', 'danger')
        return redirect(url_for(CART_ORDENES))
    
    # Verificar que existe el PDF
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        flash('El PDF de la factura no está disponible', 'danger')
        return redirect(url_for(VER_FACTURA, invoice_id=invoice_id))
    
    return send_file(
        invoice.pdf_path,
        as_attachment=True,
        download_name=f'Factura_{invoice.folio}.pdf',
        mimetype='application/pdf'
    )

@invoice_bp.route('/mis-facturas')
@login_required
def mis_facturas():
    """Ver todas las facturas del usuario"""
    invoices = Invoice.query.filter_by(user_id=current_user.id).order_by(Invoice.created_at.desc()).all()
    return render_template('invoice/mis_facturas.html', invoices=invoices)

@invoice_bp.route('/factura/cancelar/<int:invoice_id>', methods=['POST'])
@login_required
def cancelar_factura(invoice_id):
    """Cancelar una factura (solo admin)"""
    if not current_user.is_admin:
        return jsonify({'error': 'No autorizado'}), 403
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
    if invoice.status == 'cancelled':
        return jsonify({'error': 'La factura ya está cancelada'}), 400
    
    invoice.status = 'cancelled'
    invoice.fecha_cancelacion = datetime.now()
    db.session.commit()
    
    flash('Factura cancelada exitosamente', 'success')
    return redirect(url_for(VER_FACTURA, invoice_id=invoice_id))