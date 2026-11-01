"""
e2e de las recomendaciones: el recorrido completo de un cliente con la aplicación real (rutas, motor, base y carrito).

Un cliente con Ryzen 5 5600 + GTX 1650 analiza su equipo, recibe la mejora con mejor relación precio/rendimiento, abre su ficha,
comprueba que con ella el cuello de botella desaparece, y la agrega al carrito.
"""
import pytest

from database import agregar_juegos_faltantes, sincronizar_hardware
from models.database_models import CartItem, Hardware
from scripts.populate_game_requirements import populate_game_requirements


@pytest.fixture
def tienda(client, test_user):
    sincronizar_hardware()
    agregar_juegos_faltantes()
    populate_game_requirements()
    return {h.modelo: h.id for h in Hardware.query.all()}


def test_el_cliente_analiza_compra_la_mejora_y_el_cuello_de_botella_desaparece(client, test_user, tienda):
    cpu, gpu, ram = tienda['Ryzen 5 5600'], tienda['GTX 1650'], tienda['Vengeance LPX 16GB DDR4']

    # 1. analiza su equipo y recibe recomendaciones con piezas concretas
    antes = client.post('/api/analizar-hardware', json={'cpu_id': cpu, 'gpu_id': gpu, 'ram_id': ram}).get_json()
    assert antes['bottlenecks']['has_bottleneck'] and antes['bottlenecks']['type'] == 'gpu'
    mejora = next(u for u in antes['upgrades'] if u['tipo'] == 'GPU')['opciones'][0]
    assert mejora['modelo'] == 'RX 7600' and mejora['mejor_relacion'] is True

    # 2. abre la ficha de la pieza recomendada
    ficha = client.get(f"/hardware/{mejora['id']}")
    assert ficha.status_code == 200 and 'RX 7600' in ficha.get_data(as_text=True)

    # 3. con esa pieza, el verificador confirma compatibilidad y el cuello de botella ya no existe
    despues = client.post('/api/verificar-configuracion', json={'cpu_id': cpu, 'gpu_id': mejora['id'], 'ram_id': ram}).get_json()
    assert despues['estado'] == 'ok' and despues['cuello']['has_bottleneck'] is False
    assert despues['rendimiento']['total'] > antes['system_score']['total']

    # 4. la compra: inicia sesión y agrega la pieza al carrito
    assert client.post('/login', data={'username': 'testuser', 'password': 'Test1234'}).status_code in (200, 302)
    r = client.post('/carrito/agregar', json={'product_type': 'hardware', 'product_id': mejora['id'], 'quantity': 1})
    assert r.status_code == 200 and r.get_json()['success'] is True
    assert CartItem.query.filter_by(user_id=test_user.id, product_id=mejora['id']).count() == 1
    assert client.get('/carrito').status_code == 200


def test_el_cliente_con_poca_vram_compra_la_gpu_que_pide_el_juego(client, test_user, tienda):
    cpu, gpu, ram = tienda['Core i5-12400F'], tienda['RTX 4060'], tienda['Vengeance LPX 16GB DDR4']
    d = client.post('/api/analizar-hardware', json={'cpu_id': cpu, 'gpu_id': gpu, 'ram_id': ram}).get_json()
    limitados = [j['nombre'] for j in d['games']['can_run_high'] if j['bottleneck'] == 'vram']
    assert set(limitados) == {'Red Dead Redemption 2', "Baldur's Gate 3"}

    opcion = next(u for u in d['upgrades'] if u['tipo'] == 'GPU')['opciones'][0]
    assert opcion['modelo'] == 'RTX 4070'
    # con la GPU recomendada, esos juegos suben a Ultra
    nuevo = client.post('/api/analizar-hardware', json={'cpu_id': cpu, 'gpu_id': opcion['id'], 'ram_id': ram}).get_json()
    ultra = {j['nombre'] for j in nuevo['games']['can_run_ultra']}
    assert {'Red Dead Redemption 2', "Baldur's Gate 3"} <= ultra


def test_una_recomendacion_con_otro_socket_no_pasa_inadvertida_en_el_verificador(client, tienda):
    """La CPU recomendada requiere cambiar la placa: el verificador lo confirma con la placa actual."""
    cpu, gpu, ram = tienda['Ryzen 5 5600'], tienda['RTX 4070'], tienda['Vengeance LPX 16GB DDR4']
    d = client.post('/api/analizar-hardware', json={'cpu_id': cpu, 'gpu_id': gpu, 'ram_id': ram}).get_json()
    recomendada = next(u for u in d['upgrades'] if u['tipo'] == 'CPU')['opciones'][0]
    assert any('placa base' in a for a in recomendada['avisos'])
    v = client.post('/api/verificar-configuracion', json={'cpu_id': recomendada['id'], 'placa_id': tienda['ROG Strix B450-F Gaming']}).get_json()
    assert v['estado'] == 'incompatible'                             # LGA1700 en una placa AM4
