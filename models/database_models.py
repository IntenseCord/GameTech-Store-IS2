"""
Modelos de base de datos usando SQLAlchemy
"""
from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, and_
import json

CASCADE = 'all, delete-orphan'
USERS_ID = 'users.id'

class User(db.Model):
    """Modelo de usuario"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Verificación de email
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(255), unique=True, nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    # Reverificación de login (IP nueva o sesión inactiva por mucho tiempo)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    login_verification_token = db.Column(db.String(255), unique=True, nullable=True)
    login_verification_expiry = db.Column(db.DateTime, nullable=True)
    
    # Datos fiscales
    rfc = db.Column(db.String(13), nullable=True)
    razon_social = db.Column(db.String(200), nullable=True)
    direccion_fiscal = db.Column(db.String(300), nullable=True)
    codigo_postal = db.Column(db.String(10), nullable=True)
    regimen_fiscal = db.Column(db.String(100), nullable=True)
    
    # Relaciones
    cart_items = db.relationship('CartItem', backref='user', lazy='dynamic', cascade=CASCADE)
    orders = db.relationship('Order', backref='user', lazy='dynamic', cascade=CASCADE)
    invoices = db.relationship('Invoice', backref='user', lazy='dynamic', cascade=CASCADE)
    
    def set_password(self, password):
        """Establecer contraseña hasheada"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Game(db.Model):
    """Modelo de juego con base de datos"""
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False, index=True)
    descripcion = db.Column(db.Text, nullable=False)
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    imagen = db.Column(db.String(5000))  # Aumentado de 300 a 1000 para soportar URLs largas/base64
    genero = db.Column(db.String(50), index=True)
    desarrollador = db.Column(db.String(100))
    fecha_lanzamiento = db.Column(db.DateTime)
    requisitos_minimos = db.Column(db.Text)  # JSON string
    requisitos_recomendados = db.Column(db.Text)  # JSON string
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_requisitos_minimos(self):
        """Obtener requisitos mínimos como dict"""
        if not self.requisitos_minimos or not self.requisitos_minimos.strip():
            return {}
        try:
            return json.loads(self.requisitos_minimos)
        except (json.JSONDecodeError, ValueError):
            return {'Requisitos': self.requisitos_minimos}

    def get_requisitos_recomendados(self):
        """Obtener requisitos recomendados como dict"""
        if not self.requisitos_recomendados or not self.requisitos_recomendados.strip():
            return {}
        try:
            return json.loads(self.requisitos_recomendados)
        except (json.JSONDecodeError, ValueError):
            return {'Requisitos': self.requisitos_recomendados}
    
    @classmethod
    def get_all_games(cls):
        """Obtener todos los juegos"""
        return cls.query.filter_by().all()
    
    @classmethod
    def get_game_by_id(cls, game_id):
        """Obtener un juego por id"""
        return cls.query.get(game_id)
    
    @classmethod
    def get_games_by_hardware(cls, hardware_specs):
        """Obtener juegos compatibles con el hardware especificado usando el sistema de compatibilidad"""
        from models.compatibility import Compatibility

        juegos = cls.get_all_games()
        juegos_compatibles = []

        for juego in juegos:
            # Convertir hardware_specs a objetos Hardware para compatibilidad
            componentes = []
            for tipo, specs in hardware_specs.items():
                # Crear un objeto Hardware temporal para la comparación
                componente = Hardware(
                    tipo=tipo.upper(),
                    marca=specs.get('marca', ''),
                    modelo=specs.get('modelo', ''),
                    especificaciones=json.dumps(specs)
                )
                componentes.append(componente)

            # Verificar compatibilidad usando el sistema existente
            resultado = Compatibility.verificar_compatibility_completa([juego], componentes)
            if resultado['compatible']:
                juegos_compatibles.append(juego)

        return juegos_compatibles
    
    @classmethod
    def search_games(cls, query):
        """Buscar juegos por nombre, descripción o desarrollador"""
        if not query:
            return []
        
        query_lower = query.lower()
        return cls.query.filter(
            or_(
                cls.nombre.ilike(f'%{query}%'),
                cls.descripcion.ilike(f'%{query}%'),
                cls.desarrollador.ilike(f'%{query}%')
            )
        ).all()
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': self.precio,
            'imagen': self.imagen,
            'genero': self.genero,
            'desarrollador': self.desarrollador,
            'fecha_lanzamiento': self.fecha_lanzamiento.isoformat() if self.fecha_lanzamiento else None,
            'requisitos_minimos': self.get_requisitos_minimos(),
            'requisitos_recomendados': self.get_requisitos_recomendados(),
            'stock': self.stock
        }
    
    def __repr__(self):
        return f'<Game {self.nombre}>'


class Hardware(db.Model):
    """Modelo de hardware con base de datos"""
    __tablename__ = 'hardware'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)
    marca = db.Column(db.String(100), nullable=False, index=True)
    modelo = db.Column(db.String(200), nullable=False)
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    descripcion = db.Column(db.Text)
    imagen = db.Column(db.String(10000)) 
    especificaciones = db.Column(db.Text)  
    stock = db.Column(db.Integer, default=0)
    
    # Campos para análisis de rendimiento
    benchmark_score = db.Column(db.Integer, default=0)
    vram_gb = db.Column(db.Integer, default=0)
    cores = db.Column(db.Integer, default=0)
    threads = db.Column(db.Integer, default=0)
    frequency_ghz = db.Column(db.Float, default=0.0)
    tdp_watts = db.Column(db.Integer, default=0)
    socket = db.Column(db.String(50))
    generation = db.Column(db.String(50))
    architecture = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_especificaciones(self):
        """Obtener especificaciones como dict"""
        if not self.especificaciones:
            return {}
        try:
            return json.loads(self.especificaciones)
        except (TypeError, ValueError) as e:
            print(f"Error parsing especificaciones for {self.id}: {e}")
            return {}
    
    def get_ram_capacity_gb(self):
        """Extraer capacidad de RAM en GB"""
        if self.tipo != 'RAM':
            return 0
        
        specs = self.get_especificaciones()
        capacity_str = specs.get('capacidad', '8 GB')
        
        # Extraer número: "16 GB" -> 16
        import re
        match = re.search(r'(\d+)\s*GB', capacity_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 8  # Default
    
    def get_vram_gb(self):
        """Obtener VRAM de GPU"""
        if self.tipo != 'GPU':
            return 0
        return self.vram_gb or 0
    
    @classmethod
    def get_all_hardware(cls):
        """Obtener todo el hardware"""
        return cls.query.all()
    
    @classmethod
    def get_hardware_by_tipo(cls, tipo):
        """Obtener hardware por tipo"""
        return cls.query.filter_by(tipo=tipo).all()
    
    @classmethod
    def get_hardware_by_id(cls, hardware_id):
        """Obtener hardware por ID"""
        return cls.query.get(hardware_id)
    
    @classmethod
    def buscar_hardware(cls, query):
        """Buscar hardware"""
        search = f"%{query}%"
        return cls.query.filter(
            or_(
                cls.marca.ilike(search),
                cls.modelo.ilike(search),
                cls.descripcion.ilike(search),
                cls.tipo.ilike(search)
            )
        ).all()
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'tipo': self.tipo,
            'marca': self.marca,
            'modelo': self.modelo,
            'precio': self.precio,
            'descripcion': self.descripcion,
            'imagen': self.imagen,
            'especificaciones': self.get_especificaciones(),
            'stock': self.stock
        }
    
    def __repr__(self):
        return f'<Hardware {self.marca} {self.modelo}>'


class CartItem(db.Model):
    """Modelo de item en el carrito"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)  # 'game' o 'hardware'
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_product(self):
        """Obtener el producto asociado"""
        if self.product_type == 'game':
            return Game.query.get(self.product_id)
        elif self.product_type == 'hardware':
            return Hardware.query.get(self.product_id)
        return None
    
    def get_subtotal(self):
        """Calcular subtotal"""
        product = self.get_product()
        if product:
            return product.precio * self.quantity
        return 0.0
    
    def __repr__(self):
        return f'<CartItem {self.product_type}:{self.product_id}>'


class Order(db.Model):
    """Modelo de orden de compra"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    items = db.relationship('OrderItem', backref='order', lazy='dynamic', cascade=CASCADE)
    
    def __repr__(self):
        return f'<Order {self.id} - ${self.total}>'


class OrderItem(db.Model):
    """Modelo de item en una orden"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    
    def get_subtotal(self):
        """Calcular subtotal"""
        return self.price * self.quantity
    
    def __repr__(self):
        return f'<OrderItem {self.product_name}>'


class GameRequirements(db.Model):
    """Modelo de requisitos de sistema para juegos"""
    __tablename__ = 'game_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    
    # Requisitos Mínimos (1080p Low, 30 FPS)
    min_cpu_score = db.Column(db.Integer, default=0)
    min_gpu_score = db.Column(db.Integer, default=0)
    min_ram_gb = db.Column(db.Integer, default=8)
    min_vram_gb = db.Column(db.Integer, default=2)
    
    # Requisitos Recomendados (1080p High, 60 FPS)
    rec_cpu_score = db.Column(db.Integer, default=0)
    rec_gpu_score = db.Column(db.Integer, default=0)
    rec_ram_gb = db.Column(db.Integer, default=16)
    rec_vram_gb = db.Column(db.Integer, default=4)
    
    # Requisitos Ultra (1440p/4K Ultra, 60+ FPS)
    ultra_cpu_score = db.Column(db.Integer, default=0)
    ultra_gpu_score = db.Column(db.Integer, default=0)
    ultra_ram_gb = db.Column(db.Integer, default=32)
    ultra_vram_gb = db.Column(db.Integer, default=8)
    
    # Otros requisitos
    storage_gb = db.Column(db.Integer, default=50)
    directx_version = db.Column(db.String(10), default='DX12')
    requires_ssd = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con Game
    game = db.relationship('Game', backref=db.backref('requirements', uselist=False))
    
    @classmethod
    def get_by_game_id(cls, game_id):
        """Obtener requisitos por ID de juego"""
        return cls.query.filter_by(game_id=game_id).first()
    
    @classmethod
    def create_requirements(cls, game_id, **kwargs):
        """Crear nuevos requisitos"""
        requirements = cls(game_id=game_id, **kwargs)
        db.session.add(requirements)
        db.session.commit()
        return requirements
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'game_id': self.game_id,
            'minimum': {
                'cpu_score': self.min_cpu_score,
                'gpu_score': self.min_gpu_score,
                'ram_gb': self.min_ram_gb,
                'vram_gb': self.min_vram_gb
            },
            'recommended': {
                'cpu_score': self.rec_cpu_score,
                'gpu_score': self.rec_gpu_score,
                'ram_gb': self.rec_ram_gb,
                'vram_gb': self.rec_vram_gb
            },
            'ultra': {
                'cpu_score': self.ultra_cpu_score,
                'gpu_score': self.ultra_gpu_score,
                'ram_gb': self.ultra_ram_gb,
                'vram_gb': self.ultra_vram_gb
            },
            'storage_gb': self.storage_gb,
            'directx_version': self.directx_version,
            'requires_ssd': self.requires_ssd
        }
    
    def __repr__(self):
        return f'<GameRequirements for Game {self.game_id}>'


class Invoice(db.Model):
    """Modelo de factura electrónica colombiana"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)  # CUFE
    folio = db.Column(db.String(50), nullable=False)  # Número de factura
    
    # Relaciones
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    
    # Datos fiscales del cliente (Colombia)
    nit_receptor = db.Column(db.String(20), nullable=False)  # NIT o CC
    tipo_documento_receptor = db.Column(db.String(10), default='31')  
    razon_social_receptor = db.Column(db.String(200), nullable=False)
    direccion_fiscal = db.Column(db.String(300))
    ciudad = db.Column(db.String(100))
    departamento = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(10))
    telefono = db.Column(db.String(20))
    email_receptor = db.Column(db.String(200))
    
    # Datos fiscales del emisor (GameTech Store Colombia)
    nit_emisor = db.Column(db.String(20), default='900123456-7')
    razon_social_emisor = db.Column(db.String(200), default='GameTech Store SAS')
    regimen_emisor = db.Column(db.String(50), default='Responsable de IVA')
    
    # Montos (Colombia - IVA 19%)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    iva = db.Column(db.Numeric(12, 2), nullable=False)  # 19% en Colombia
    total = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Método y forma de pago
    metodo_pago = db.Column(db.String(50), default='Contado')  # Contado, Crédito
    forma_pago = db.Column(db.String(50), default='Tarjeta de Crédito')
    
    # Estado y fechas
    status = db.Column(db.String(20), default='active')  # active, cancelled
    fecha_emision = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_validacion_dian = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)
    
    # Archivos
    pdf_path = db.Column(db.String(300))
    xml_path = db.Column(db.String(300))
    
    # CUFE y firma digital (Colombia)
    cufe = db.Column(db.Text)  # Código Único de Factura Electrónica
    qr_code = db.Column(db.Text)  # Código QR para validación DIAN
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con Order
    order = db.relationship('Order', backref=db.backref('invoice', uselist=False))
    
    @classmethod
    def generate_uuid(cls):
        """Generar UUID único para la factura"""
        import uuid
        return str(uuid.uuid4())
    
    @classmethod
    def generate_folio(cls):
        """Generar folio consecutivo"""
        last_invoice = cls.query.order_by(cls.id.desc()).first()
        if last_invoice and last_invoice.folio:
            try:
                last_number = int(last_invoice.folio.split('-')[1])
                return f'FAC-{last_number + 1:06d}'
            except (IndexError, ValueError):
                pass
        return 'FAC-000001'
    
    @classmethod
    def create_from_order(cls, order, user_fiscal_data):
        """Crear factura desde una orden (Colombia - DIAN)"""
        # Calcular montos (IVA 19% en Colombia). order.total es Decimal
        # (columna NUMERIC); convertir a float antes de dividir entre 1.19.
        total = float(order.total)
        subtotal = total / 1.19
        iva = total - subtotal
        
        invoice = cls(
            uuid=cls.generate_uuid(),
            folio=cls.generate_folio(),
            user_id=order.user_id,
            order_id=order.id,
            nit_receptor=user_fiscal_data.get('nit'),
            tipo_documento_receptor=user_fiscal_data.get('tipo_documento', '31'),
            razon_social_receptor=user_fiscal_data.get('razon_social'),
            direccion_fiscal=user_fiscal_data.get('direccion_fiscal'),
            ciudad=user_fiscal_data.get('ciudad'),
            departamento=user_fiscal_data.get('departamento'),
            codigo_postal=user_fiscal_data.get('codigo_postal'),
            telefono=user_fiscal_data.get('telefono'),
            email_receptor=user_fiscal_data.get('email'),
            subtotal=round(subtotal, 2),
            iva=round(iva, 2),
            total=round(order.total, 2),
            metodo_pago=user_fiscal_data.get('metodo_pago', 'Contado'),
            forma_pago=user_fiscal_data.get('forma_pago', 'Tarjeta de Crédito')
        )
        
        return invoice
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'folio': self.folio,
            'nit_receptor': self.nit_receptor,
            'tipo_documento_receptor': self.tipo_documento_receptor,
            'razon_social_receptor': self.razon_social_receptor,
            'direccion_fiscal': self.direccion_fiscal,
            'ciudad': self.ciudad,
            'departamento': self.departamento,
            'codigo_postal': self.codigo_postal,
            'telefono': self.telefono,
            'email_receptor': self.email_receptor,
            'nit_emisor': self.nit_emisor,
            'razon_social_emisor': self.razon_social_emisor,
            'regimen_emisor': self.regimen_emisor,
            'subtotal': self.subtotal,
            'iva': self.iva,
            'total': self.total,
            'metodo_pago': self.metodo_pago,
            'forma_pago': self.forma_pago,
            'status': self.status,
            'fecha_emision': self.fecha_emision.strftime('%Y-%m-%d %H:%M:%S'),
            'fecha_validacion_dian': self.fecha_validacion_dian.strftime('%Y-%m-%d %H:%M:%S'),
            'pdf_path': self.pdf_path,
            'xml_path': self.xml_path,
            'cufe': self.cufe,
            'qr_code': self.qr_code
        }
    
    def __repr__(self):
        return f'<Invoice {self.folio} - {self.uuid}>'


class Wishlist(db.Model):
    """Modelo de lista de deseos"""
    __tablename__ = 'wishlist'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(USERS_ID), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_type = db.Column(db.String(20), nullable=False)  # 'game' or 'hardware'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'product_type': self.product_type,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    @staticmethod
    def add_to_wishlist(user_id, product_id, product_type):
        """Agregar producto a wishlist"""
        # Verificar si ya existe
        existing = Wishlist.query.filter_by(
            user_id=user_id,
            product_id=product_id,
            product_type=product_type
        ).first()
        
        if existing:
            return False, "El producto ya está en tu lista de deseos"
        
        wishlist_item = Wishlist(
            user_id=user_id,
            product_id=product_id,
            product_type=product_type
        )
        db.session.add(wishlist_item)
        db.session.commit()
        return True, "Producto agregado a tu lista de deseos"
    
    @staticmethod
    def remove_from_wishlist(user_id, product_id, product_type):
        """Remover producto de wishlist"""
        item = Wishlist.query.filter_by(
            user_id=user_id,
            product_id=product_id,
            product_type=product_type
        ).first()
        
        if item:
            db.session.delete(item)
            db.session.commit()
            return True, "Producto removido de tu lista de deseos"
        return False, "Producto no encontrado en tu lista de deseos"
    
    @staticmethod
    def get_user_wishlist(user_id):
        """Obtener wishlist de un usuario"""
        return Wishlist.query.filter_by(user_id=user_id).all()
    
    def __repr__(self):
        return f'<Wishlist User:{self.user_id} Product:{self.product_id} Type:{self.product_type}>'
