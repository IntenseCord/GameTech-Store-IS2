"""
Hallazgo 30: en /tienda un clic en "Agregar" creaba dos filas iguales en el carrito.

Causa 1 (navegador): initializeShoppingCart() se llamaba desde initializeCommonFeatures() y otra vez desde
initializeStorePage(), y cada llamada registraba su propio manejador de clic en `document`: un clic mandaba
dos peticiones a /carrito/agregar.
Causa 2 (servidor): dos peticiones simultáneas pasan la comprobación "¿ya existe la fila?" antes de que
exista, y `cart_items` no tenía restricción única por usuario y producto, así que se insertaban dos filas.
"""
import importlib.util
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.database_models import CartItem

RAIZ = Path(__file__).resolve().parent.parent
MAIN_JS = RAIZ / 'static' / 'js' / 'main.js'
MIGRACION = next((RAIZ / 'migrations' / 'versions').glob('*cart_items_unico*.py'), None)

necesita_node = pytest.mark.skipif(shutil.which('node') is None, reason='Node.js no está instalado')

GUION_NODE = textwrap.dedent(r"""
    const fs = require('fs');
    const vm = require('vm');
    const [rutaJs, rutasJson] = process.argv.slice(1);
    const rutas = JSON.parse(rutasJson);

    const salida = rutas.map((ruta) => {
      const escuchas = {};
      let peticiones = 0;
      const elemento = () => ({ style: {}, classList: { add() {}, remove() {} }, appendChild() {}, remove() {},
                                addEventListener() {}, setAttribute() {}, set innerHTML(v) {}, set textContent(v) {} });
      const documento = {
        addEventListener: (tipo, f) => { (escuchas[tipo] = escuchas[tipo] || []).push(f); },
        querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
        createElement: elemento, body: { appendChild() {}, contains: () => false },
      };
      const contexto = vm.createContext({
        document: documento, console: { log() {}, error() {} }, location: { pathname: ruta, href: '' },
        localStorage: { getItem: () => null, setItem() {} },
        bootstrap: { Tooltip: function () {}, Toast: function () { this.show = () => {}; } },
        IntersectionObserver: function () { this.observe = () => {}; },
        setTimeout: () => 0, setInterval: () => 0,
        fetch: (url) => { if (String(url).includes('/carrito/agregar')) peticiones++;
          return Promise.resolve({ redirected: false, json: () => Promise.resolve({ success: true, message: 'ok', cart_count: 1 }) }); },
      });
      vm.runInContext(fs.readFileSync(rutaJs, 'utf8'), contexto);
      (escuchas['DOMContentLoaded'] || []).forEach((f) => { try { f(); } catch (e) {} });
      const boton = { dataset: { juegoId: '1' } };
      const evento = { target: { closest: () => boton } };
      (escuchas['click'] || []).forEach((f) => { try { f(evento); } catch (e) {} });
      return { ruta, peticiones };
    });
    process.stdout.write(JSON.stringify(salida));
""")


@necesita_node
@pytest.mark.parametrize('ruta', ['/', '/tienda', '/tienda?pagina=2', '/hardware', '/juego/1', '/carrito'])
def test_un_clic_en_agregar_manda_una_sola_peticion(ruta):
    resultado = subprocess.run(
        ['node', '-e', GUION_NODE, str(MAIN_JS), json.dumps([ruta])],
        capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert resultado.returncode == 0, resultado.stderr
    [r] = json.loads(resultado.stdout)
    assert r['peticiones'] == 1, f'{ruta}: un clic mandó {r["peticiones"]} peticiones a /carrito/agregar'


def _login(client):
    return client.post('/login', data={'username': 'testuser', 'password': 'Test1234'})


def test_cart_items_no_admite_dos_filas_del_mismo_producto_para_el_mismo_usuario(app_context, test_user, test_hardware):
    db.session.add(CartItem(user_id=test_user.id, product_type='hardware', product_id=test_hardware.id, quantity=1))
    db.session.commit()

    db.session.add(CartItem(user_id=test_user.id, product_type='hardware', product_id=test_hardware.id, quantity=1))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_el_mismo_producto_puede_estar_en_el_carrito_de_dos_usuarios_y_con_otro_tipo(app_context, test_user, test_hardware, test_game):
    from models.database_models import User
    otro = User(username='otro', email='otro@example.com')
    otro.set_password('Test1234')
    db.session.add(otro)
    db.session.commit()
    db.session.add_all([
        CartItem(user_id=test_user.id, product_type='hardware', product_id=test_hardware.id, quantity=1),
        CartItem(user_id=otro.id, product_type='hardware', product_id=test_hardware.id, quantity=1),
        CartItem(user_id=test_user.id, product_type='game', product_id=test_hardware.id, quantity=1),
    ])
    db.session.commit()

    assert CartItem.query.count() == 3


def test_dos_peticiones_seguidas_suman_la_cantidad_en_una_sola_fila(client, test_user, test_hardware):
    _login(client)
    for _ in range(2):
        r = client.post('/carrito/agregar', json={'product_type': 'hardware', 'product_id': test_hardware.id, 'quantity': 1})
        assert r.status_code == 200

    filas = CartItem.query.filter_by(user_id=test_user.id).all()
    assert len(filas) == 1 and filas[0].quantity == 2


def test_si_otra_peticion_inserto_la_fila_primero_se_suma_la_cantidad_en_vez_de_fallar(client, test_user, test_hardware, monkeypatch):
    """Carrera: las dos peticiones no ven la fila al comprobar; la otra la inserta antes que esta. La
    restricción única hace fallar el INSERT y el endpoint debe reintentar sumando, no devolver un 500."""
    import controllers.cart as cart
    _login(client)
    real = cart.actualizar_carrito
    llamadas = []

    def con_carrera(product_type, product_id, quantity):
        llamadas.append(1)
        if len(llamadas) == 1:
            # la otra petición confirma su fila justo antes de que esta inserte la suya
            db.session.add(CartItem(user_id=test_user.id, product_type=product_type, product_id=product_id, quantity=1))
            db.session.commit()
            raise IntegrityError('INSERT cart_items', {}, Exception('UNIQUE constraint failed'))
        return real(product_type, product_id, quantity)

    monkeypatch.setattr(cart, 'actualizar_carrito', con_carrera)

    r = client.post('/carrito/agregar', json={'product_type': 'hardware', 'product_id': test_hardware.id, 'quantity': 1})

    assert r.status_code == 200, r.get_json()
    filas = CartItem.query.filter_by(user_id=test_user.id).all()
    assert len(filas) == 1 and filas[0].quantity == 2


# ------------------------------------------------------------------ migración
def _cargar_migracion():
    assert MIGRACION is not None, 'falta la migración de la restricción única de cart_items'
    spec = importlib.util.spec_from_file_location('migracion_cart_items', MIGRACION)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_migracion_fusiona_las_filas_duplicadas_sumando_cantidades():
    modulo = _cargar_migracion()
    motor = create_engine('sqlite://')
    with motor.begin() as con:
        con.execute(text('CREATE TABLE cart_items (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, '
                         'product_type VARCHAR(20) NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER)'))
        con.execute(text("INSERT INTO cart_items (id, user_id, product_type, product_id, quantity) VALUES "
                         "(1, 7, 'game', 1, 1), (2, 7, 'game', 1, 1), (3, 7, 'game', 1, 3), "   # triplicado
                         "(4, 7, 'hardware', 1, 2), "                                            # mismo id, otro tipo
                         "(5, 8, 'game', 1, 1), (6, 8, 'game', 1, 1), "                          # otro usuario
                         "(7, 9, 'game', 2, 4)"))                                                 # sin duplicar
        modulo.fusionar_duplicados(con)
        filas = con.execute(text('SELECT id, user_id, product_type, product_id, quantity FROM cart_items ORDER BY id')).all()

    assert [tuple(f) for f in filas] == [
        (1, 7, 'game', 1, 5),
        (4, 7, 'hardware', 1, 2),
        (5, 8, 'game', 1, 2),
        (7, 9, 'game', 2, 4),
    ]


def test_la_migracion_encadena_con_la_anterior_y_define_el_mismo_nombre_que_el_modelo():
    modulo = _cargar_migracion()
    assert modulo.down_revision == 'e4496e5d856a'
    nombres = {c.name for c in CartItem.__table__.constraints if c.name}
    assert modulo.NOMBRE_RESTRICCION in nombres


def test_upgrade_y_downgrade_de_la_migracion_crean_y_quitan_la_restriccion():
    """Ejecuta upgrade()/downgrade() reales de Alembic (no solo la función auxiliar) sobre una tabla
    con duplicados."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    modulo = _cargar_migracion()
    motor = create_engine('sqlite://')
    with motor.begin() as con:
        con.execute(text('CREATE TABLE cart_items (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, '
                         'product_type VARCHAR(20) NOT NULL, product_id INTEGER NOT NULL, quantity INTEGER)'))
        con.execute(text("INSERT INTO cart_items (id, user_id, product_type, product_id, quantity) VALUES "
                         "(1, 7, 'game', 1, 1), (2, 7, 'game', 1, 1)"))
        with Operations.context(MigrationContext.configure(con)):
            modulo.upgrade()
        assert con.execute(text('SELECT COUNT(*), SUM(quantity) FROM cart_items')).one() == (1, 2)
        with pytest.raises(IntegrityError):
            with con.begin_nested():
                con.execute(text("INSERT INTO cart_items (user_id, product_type, product_id, quantity) VALUES (7, 'game', 1, 1)"))
        with Operations.context(MigrationContext.configure(con)):
            modulo.downgrade()
        con.execute(text("INSERT INTO cart_items (user_id, product_type, product_id, quantity) VALUES (7, 'game', 1, 1)"))
        assert con.execute(text('SELECT COUNT(*) FROM cart_items')).scalar() == 2
