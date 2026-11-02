"""
Fechas: la base guarda UTC y se muestran en hora de Bogotá (hallazgo 31, visto en la prueba e2e del 1 de noviembre).

Antes: `Invoice.fecha_emision` y `fecha_cancelacion` se guardaban con `datetime.now()` (hora local del servidor) mientras todas las
demás columnas usaban UTC, así que una misma factura mostraba "Fecha Emisión" 16:22 y "Fecha Validación DIAN" 21:22; y las
plantillas mostraban la hora UTC sin convertir (una orden hecha a las 20:15 en Bogotá decía "02/11/2026 01:15").
Ahora hay una sola convención: se guarda UTC (`ahora_utc`) y se convierte a América/Bogotá (UTC-5, sin horario de verano) al mostrar,
con el filtro `fecha_local` de las plantillas y `formatear_local` en el código (PDF y correos).

Momento de referencia de las pruebas: 2026-11-02 01:15:22 UTC == 2026-11-01 20:15:22 en Bogotá (el día cambia).
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from reportlab import rl_config

from app import app
from extensions import db
from models.database_models import Invoice, Order, OrderItem, User
from tests.test_invoice import crear_orden, datos_factura_validos, login
from utils.fechas import ahora_utc, formatear_local

RAIZ = Path(__file__).resolve().parent.parent
UTC = datetime(2026, 11, 2, 1, 15, 22)
LOCAL = '01/11/2026 20:15'
EN_UTC = '02/11/2026 01:15'


# ----------------------------------------------------------------------------- el convertidor
def test_utc_se_muestra_en_hora_de_bogota():
    assert formatear_local(UTC) == LOCAL
    assert formatear_local(UTC, '%d/%m/%Y %H:%M:%S') == '01/11/2026 20:15:22'


def test_al_convertir_la_fecha_puede_cambiar_de_dia():
    assert formatear_local(datetime(2026, 11, 2, 3, 0), '%d/%m/%Y') == '01/11/2026'
    assert formatear_local(datetime(2026, 11, 2, 5, 0), '%d/%m/%Y %H:%M') == '02/11/2026 00:00'
    assert formatear_local(datetime(2026, 11, 2, 4, 59), '%d/%m/%Y') == '01/11/2026'


def test_acepta_un_datetime_con_zona_utc():
    assert formatear_local(UTC.replace(tzinfo=timezone.utc)) == LOCAL


def test_un_valor_vacio_no_rompe_la_pagina():
    assert formatear_local(None) == ''


def test_colombia_no_cambia_de_hora_en_verano():
    assert formatear_local(datetime(2026, 1, 15, 12, 0), '%H:%M') == '07:00'
    assert formatear_local(datetime(2026, 7, 15, 12, 0), '%H:%M') == '07:00'


def test_ahora_utc_sigue_siendo_utc_sin_zona():
    ahora = ahora_utc()
    assert ahora.tzinfo is None
    assert abs(ahora - datetime.now(timezone.utc).replace(tzinfo=None)) < timedelta(seconds=2)


def test_el_filtro_esta_registrado_en_las_plantillas():
    assert app.jinja_env.filters['fecha_local'] is formatear_local


# ------------------------------------------------------------------------- reglas estáticas
def test_las_plantillas_no_formatean_fechas_sin_convertir():
    """Solo la fecha de lanzamiento (una fecha de calendario, sin hora) puede usar strftime directo."""
    quienes = []
    for p in (RAIZ / 'templates').rglob('*.html'):
        for n, linea in enumerate(p.read_text(encoding='utf-8').split('\n'), 1):
            if '.strftime(' in linea and 'fecha_lanzamiento' not in linea:
                quienes.append(f'{p.relative_to(RAIZ).as_posix()}:{n}')
    assert not quienes, quienes


def test_el_codigo_no_usa_la_hora_local_del_servidor():
    quienes = []
    for carpeta in ('controllers', 'models', 'utils'):
        for p in (RAIZ / carpeta).rglob('*.py'):
            for n, linea in enumerate(p.read_text(encoding='utf-8').split('\n'), 1):
                if re.search(r'datetime\.now\(\s*\)', linea):
                    quienes.append(f'{p.relative_to(RAIZ).as_posix()}:{n}')
    assert not quienes, quienes


# --------------------------------------------------------------------------------- pantallas
@pytest.fixture
def orden(test_user):
    test_user.created_at = datetime(2026, 11, 2, 3, 0)
    order = crear_orden(test_user)
    order.created_at = UTC
    db.session.commit()
    return order


def _admin():
    admin = User(username='admintest', email='admintest@example.com', is_admin=True, email_verified=True)
    admin.set_password('Test1234')
    admin.created_at = datetime(2026, 11, 2, 3, 0)
    db.session.add(admin)
    db.session.commit()
    return admin


def _ver(client, ruta, usuario='testuser'):
    login(client, usuario)
    return client.get(ruta).get_data(as_text=True)


@pytest.mark.parametrize('ruta', ['/orden/{id}', '/mis-ordenes', '/factura/solicitar/{id}'])
def test_las_pantallas_del_cliente_muestran_la_hora_de_bogota(client, test_user, orden, ruta):
    html = _ver(client, ruta.format(id=orden.id))
    assert LOCAL in html and EN_UTC not in html


def test_el_perfil_muestra_las_fechas_en_hora_de_bogota(client, test_user, orden):
    html = _ver(client, '/perfil')
    assert '01/11/2026' in html and '02/11/2026' not in html


@pytest.mark.parametrize('ruta', ['/admin/ordenes', '/admin/orden/{id}'])
def test_el_panel_de_administracion_muestra_la_hora_de_bogota(client, test_user, orden, ruta):
    _admin()
    html = _ver(client, ruta.format(id=orden.id), 'admintest')
    assert LOCAL in html and EN_UTC not in html


@pytest.mark.parametrize('ruta', ['/admin', '/admin/usuarios'])
def test_el_panel_muestra_las_altas_de_usuarios_y_ordenes_con_la_fecha_local(client, test_user, orden, ruta):
    _admin()
    html = _ver(client, ruta, 'admintest')
    assert '01/11/2026' in html and '02/11/2026' not in html


def _factura(order, user):
    invoice = Invoice(uuid='11111111-1111-1111-1111-111111111111', folio=f'FE-{order.id:06d}', user_id=user.id, order_id=order.id,
                      nit_receptor='900123456', razon_social_receptor='Cliente de Prueba', email_receptor=user.email,
                      subtotal=50.41, iva=9.58, total=59.99, cufe='c' * 40, fecha_emision=UTC, fecha_validacion_dian=UTC)
    db.session.add(invoice)
    db.session.commit()
    return invoice


def test_una_factura_muestra_emision_y_validacion_a_la_misma_hora(client, test_user, orden):
    invoice = _factura(orden, test_user)
    html = _ver(client, f'/factura/{invoice.id}')
    assert html.count('01/11/2026 20:15:22') == 2 and '02/11/2026 01:15' not in html


def test_la_lista_de_facturas_muestra_la_fecha_local(client, test_user, orden):
    _factura(orden, test_user)
    html = _ver(client, '/mis-facturas')
    assert '01/11/2026' in html and '02/11/2026' not in html


# -------------------------------------------------------------- lo que se guarda: siempre UTC
@pytest.fixture
def sin_correo(monkeypatch):
    monkeypatch.setattr('controllers.invoice.enviar_factura_por_email', lambda *a, **k: True)


def test_la_factura_guarda_la_emision_en_utc(client, test_user, sin_correo, monkeypatch):
    login(client)
    order = crear_orden(test_user)
    monkeypatch.setattr('controllers.invoice.ahora_utc', lambda: UTC)

    client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos())

    assert Invoice.query.filter_by(order_id=order.id).one().fecha_emision == UTC


def test_emision_y_validacion_de_una_factura_nueva_son_del_mismo_momento(client, test_user, sin_correo):
    login(client)
    order = crear_orden(test_user)
    client.post(f'/factura/solicitar/{order.id}', data=datos_factura_validos())
    invoice = Invoice.query.filter_by(order_id=order.id).one()
    assert abs(invoice.fecha_emision - invoice.fecha_validacion_dian) < timedelta(seconds=5)


def test_la_cancelacion_se_guarda_en_utc(client, test_user, orden, monkeypatch):
    invoice = _factura(orden, test_user)
    _admin()
    login(client, 'admintest')
    monkeypatch.setattr('controllers.invoice.ahora_utc', lambda: UTC)

    client.post(f'/factura/cancelar/{invoice.id}')

    assert db.session.get(Invoice, invoice.id).fecha_cancelacion == UTC


def test_el_token_de_verificacion_vence_a_las_24_horas_en_utc(monkeypatch):
    from utils.email_service import get_token_expiry
    monkeypatch.setattr('utils.email_service.ahora_utc', lambda: UTC)
    assert get_token_expiry() == UTC + timedelta(hours=24)


# ---------------------------------------------------------------- PDF y correo de la factura
def test_el_pdf_de_la_factura_lleva_la_hora_de_bogota(client, test_user, orden, tmp_path, monkeypatch):
    from utils.invoice_generator_colombia import InvoiceGeneratorColombia
    invoice = _factura(orden, test_user)
    monkeypatch.setattr(rl_config, 'pageCompression', 0)            # PDF sin comprimir para poder leer su texto
    destino = tmp_path / 'factura.pdf'

    InvoiceGeneratorColombia.generate_pdf(invoice, orden, str(destino))

    contenido = destino.read_bytes()
    assert LOCAL.encode() in contenido and EN_UTC.encode() not in contenido


def test_el_correo_de_la_factura_lleva_la_hora_de_bogota(test_user, orden, tmp_path, monkeypatch):
    from utils.email_sender import enviar_factura_por_email
    invoice = _factura(orden, test_user)
    pdf = tmp_path / 'f.pdf'
    pdf.write_bytes(b'%PDF-1.4')
    enviados = []
    monkeypatch.setattr('utils.email_sender.mail.send', lambda msg: enviados.append(msg))

    enviar_factura_por_email(invoice, test_user, str(pdf))

    assert len(enviados) == 1 and LOCAL in enviados[0].html and EN_UTC not in enviados[0].html


@pytest.mark.parametrize('funcion', ['send_order_pending_email', 'send_order_confirmation_email', 'send_order_rejected_email'])
def test_los_correos_de_la_orden_llevan_la_hora_de_bogota(test_user, orden, monkeypatch, funcion):
    """Se ejecutan las funciones reales de envío y se captura el mensaje que saldría por SMTP."""
    import utils.email_service as servicio
    enviados = []
    monkeypatch.setattr(servicio.mail, 'send', lambda msg: enviados.append(msg))

    with app.test_request_context():
        assert getattr(servicio, funcion)(test_user.email, test_user.username, orden) is True

    assert len(enviados) == 1 and LOCAL in enviados[0].html and EN_UTC not in enviados[0].html
