"""
Formularios de validación usando Flask-WTF
Centraliza todas las validaciones de entrada de datos
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, IntegerField, FloatField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, Optional
import re


class RegistrationForm(FlaskForm):
    """Formulario de registro de usuarios"""
    username = StringField('Nombre de usuario', validators=[
        DataRequired(message='El nombre de usuario es requerido'),
        Length(min=4, max=20, message='El nombre de usuario debe tener entre 4 y 20 caracteres')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='El email es requerido'),
        Email(message='Email inválido')
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message='La contraseña es requerida'),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres')
    ])
    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(message='Debes confirmar la contraseña'),
        EqualTo('password', message='Las contraseñas no coinciden')
    ])

    def validate_password(self, field):
        """Validar complejidad de contraseña"""
        password = field.data
        if not re.search(r'[A-Z]', password):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', password):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', password):
            raise ValueError('La contraseña debe contener al menos un número')


class LoginForm(FlaskForm):
    """Formulario de login"""
    username = StringField('Nombre de usuario', validators=[
        DataRequired(message='El nombre de usuario es requerido')
    ])
    password = PasswordField('Contraseña', validators=[
        DataRequired(message='La contraseña es requerida')
    ])


class ProfileEditForm(FlaskForm):
    """Formulario para editar perfil"""
    email = StringField('Email', validators=[
        DataRequired(message='El email es requerido'),
        Email(message='Email inválido')
    ])
    current_password = PasswordField('Contraseña actual', validators=[
        Optional()
    ])
    new_password = PasswordField('Nueva contraseña', validators=[
        Optional()
    ])
    confirm_new_password = PasswordField('Confirmar nueva contraseña', validators=[
        Optional(),
        EqualTo('new_password', message='Las contraseñas nuevas no coinciden')
    ])


class PasswordResetRequestForm(FlaskForm):
    """Formulario para solicitar recuperación de contraseña"""
    email = StringField('Email', validators=[
        DataRequired(message='El email es requerido'),
        Email(message='Email inválido')
    ])


class PasswordResetForm(FlaskForm):
    """Formulario para restablecer contraseña"""
    password = PasswordField('Nueva contraseña', validators=[
        DataRequired(message='La contraseña es requerida'),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres')
    ])
    confirm_password = PasswordField('Confirmar contraseña', validators=[
        DataRequired(message='Debes confirmar la contraseña'),
        EqualTo('password', message='Las contraseñas no coinciden')
    ])

    def validate_password(self, field):
        """Validar complejidad de contraseña"""
        password = field.data
        if not re.search(r'[A-Z]', password):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', password):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'\d', password):
            raise ValueError('La contraseña debe contener al menos un número')


class GameForm(FlaskForm):
    """Formulario para crear/editar juegos"""
    nombre = StringField('Nombre', validators=[
        DataRequired(message='El nombre es requerido'),
        Length(max=200, message='El nombre no puede exceder 200 caracteres')
    ])
    descripcion = TextAreaField('Descripción', validators=[
        DataRequired(message='La descripción es requerida')
    ])
    precio = FloatField('Precio', validators=[
        DataRequired(message='El precio es requerido'),
        NumberRange(min=0, message='El precio debe ser positivo')
    ])
    genero = SelectField('Género', validators=[
        DataRequired(message='El género es requerido')
    ], choices=[
        ('Acción', 'Acción'),
        ('Aventura', 'Aventura'),
        ('RPG', 'RPG'),
        ('Estrategia', 'Estrategia'),
        ('Deportes', 'Deportes'),
        ('Simulación', 'Simulación'),
        ('Terror', 'Terror'),
        ('Carreras', 'Carreras'),
        ('Puzzle', 'Puzzle'),
        ('Otro', 'Otro')
    ])
    desarrollador = StringField('Desarrollador', validators=[
        DataRequired(message='El desarrollador es requerido'),
        Length(max=100, message='El desarrollador no puede exceder 100 caracteres')
    ])
    fecha_lanzamiento = DateField('Fecha de lanzamiento', validators=[
        DataRequired(message='La fecha de lanzamiento es requerida')
    ])
    requisitos_minimos = TextAreaField('Requisitos mínimos', validators=[
        DataRequired(message='Los requisitos mínimos son requeridos')
    ])
    requisitos_recomendados = TextAreaField('Requisitos recomendados', validators=[
        DataRequired(message='Los requisitos recomendados son requeridos')
    ])
    stock = IntegerField('Stock', validators=[
        DataRequired(message='El stock es requerido'),
        NumberRange(min=0, message='El stock debe ser positivo')
    ])
    imagen_url = StringField('URL de imagen', validators=[
        Optional()
    ])


class HardwareForm(FlaskForm):
    """Formulario para crear/editar hardware"""
    tipo = SelectField('Tipo', validators=[
        DataRequired(message='El tipo es requerido')
    ], choices=[
        ('CPU', 'CPU'),
        ('GPU', 'GPU'),
        ('RAM', 'RAM'),
        ('Motherboard', 'Motherboard'),
        ('Almacenamiento', 'Almacenamiento'),
        ('Fuente de poder', 'Fuente de poder'),
        ('Refrigeración', 'Refrigeración'),
        ('Gabinete', 'Gabinete'),
        ('Otro', 'Otro')
    ])
    marca = StringField('Marca', validators=[
        DataRequired(message='La marca es requerida'),
        Length(max=100, message='La marca no puede exceder 100 caracteres')
    ])
    modelo = StringField('Modelo', validators=[
        DataRequired(message='El modelo es requerido'),
        Length(max=200, message='El modelo no puede exceder 200 caracteres')
    ])
    precio = FloatField('Precio', validators=[
        DataRequired(message='El precio es requerido'),
        NumberRange(min=0, message='El precio debe ser positivo')
    ])
    descripcion = TextAreaField('Descripción', validators=[
        Optional()
    ])
    especificaciones = TextAreaField('Especificaciones', validators=[
        DataRequired(message='Las especificaciones son requeridas')
    ])
    stock = IntegerField('Stock', validators=[
        DataRequired(message='El stock es requerido'),
        NumberRange(min=0, message='El stock debe ser positivo')
    ])
    imagen_url = StringField('URL de imagen', validators=[
        Optional()
    ])
