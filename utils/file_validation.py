"""
Utilidades para validación segura de archivos subidos
"""
import logging
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_file_upload(file):
    """
    Valida un archivo subido de manera segura
    
    Args:
        file: Archivo subido (werkzeug.FileStorage)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file or not file.filename:
        return False, 'No se proporcionó ningún archivo'
    
    # Validar tamaño del archivo
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return False, f'El archivo excede el tamaño máximo de {MAX_FILE_SIZE // (1024*1024)}MB'
    
    # Validar extensión
    filename = secure_filename(file.filename)
    if not filename:
        return False, 'Nombre de archivo inválido'
    
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'Extensión no permitida. Extensiones permitidas: {", ".join(ALLOWED_EXTENSIONS)}'
    
    # Validar tipo MIME real usando Pillow
    try:
        file.seek(0)
        img = Image.open(file)
        # Formato real según el contenido (no la extensión); imghdr ya no existe en Python 3.13+
        format_detected = (img.format or '').lower()

        # Verificar que el archivo es realmente una imagen
        img.verify()
        file.seek(0)
        
        if format_detected not in ['jpeg', 'png', 'webp']:
            return False, 'Formato de imagen no válido'
            
    except Exception:
        # Pillow describe el fallo con detalles internos (objetos, rutas): no se muestran al usuario
        logger.warning('Imagen subida rechazada por Pillow', exc_info=True)
        return False, 'Archivo de imagen inválido'
    
    return True, None


def generate_unique_filename(original_filename):
    """
    Genera un nombre de archivo único usando UUID
    
    Args:
        original_filename: Nombre original del archivo
    
    Returns:
        str: Nombre de archivo único con extensión original
    """
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    unique_name = str(uuid.uuid4())
    return f"{unique_name}.{ext}" if ext else unique_name


def validate_image_url(url):
    """
    Valida una URL de imagen de manera básica
    
    Args:
        url: URL de imagen
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not url or not url.strip():
        return True, None  # URL vacía es válida (opcional)
    
    url = url.strip()
    
    # Validar que sea HTTP/HTTPS
    if not url.startswith(('http://', 'https://')):
        return False, 'La URL debe comenzar con http:// o https://'
    
    # Validar extensión en URL
    ext = url.rsplit('.', 1)[1].lower() if '.' in url else ''
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False, f'Extensión no permitida en URL. Extensiones permitidas: {", ".join(ALLOWED_EXTENSIONS)}'
    
    return True, None
