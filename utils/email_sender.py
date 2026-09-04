"""
Utilidad para enviar correos electrónicos
"""
from flask_mail import Message
from flask import current_app
from extensions import mail
import os

def enviar_factura_por_email(invoice, user, pdf_path):
    """
    Enviar factura electrónica por correo
    
    Args:
        invoice: Objeto Invoice
        user: Objeto User
        pdf_path: Ruta al archivo PDF de la factura
    """
    try:
        # Crear mensaje
        msg = Message(
            subject=f'Factura Electrónica #{invoice.folio} - GameTech Store',
            recipients=[user.email],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Cuerpo del email en HTML
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f8f9fa;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .invoice-details {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .detail-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 10px 0;
                    border-bottom: 1px solid #e0e0e0;
                }}
                .detail-label {{
                    font-weight: bold;
                    color: #667eea;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 GameTech Store</h1>
                    <h2>Factura Electrónica</h2>
                </div>
                
                <div class="content">
                    <p>Hola <strong>{user.username}</strong>,</p>
                    
                    <p>Tu factura electrónica ha sido generada exitosamente.</p>
                    
                    <div class="invoice-details">
                        <h3 style="color: #667eea; margin-top: 0;">Detalles de la Factura</h3>
                        
                        <div class="detail-row">
                            <span class="detail-label">Número de Factura:</span>
                            <span>#{invoice.folio}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="detail-label">CUFE:</span>
                            <span style="font-size: 11px;">{invoice.uuid}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="detail-label">Fecha de Emisión:</span>
                            <span>{invoice.fecha_emision.strftime('%d/%m/%Y %H:%M')}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="detail-label">NIT/CC:</span>
                            <span>{invoice.nit_receptor}</span>
                        </div>
                        
                        <div class="detail-row">
                            <span class="detail-label">Razón Social:</span>
                            <span>{invoice.razon_social_receptor}</span>
                        </div>
                        
                        <div class="detail-row" style="border-bottom: none;">
                            <span class="detail-label">Total:</span>
                            <span style="font-size: 20px; color: #28a745; font-weight: bold;">
                                ${invoice.total:,.2f} COP
                            </span>
                        </div>
                    </div>
                    
                    <p style="margin-top: 20px;">
                        <strong>📎 Adjunto:</strong> Encontrarás tu factura en formato PDF adjunta a este correo.
                    </p>
                    
                    <p style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                        <strong>⚠️ Importante:</strong> Esta factura es válida ante la DIAN. 
                        Guárdala para tus registros contables.
                    </p>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <p>¿Tienes alguna pregunta?</p>
                        <p>Contáctanos en: <strong>soporte@gametechstore.com</strong></p>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>GameTech Store SAS</strong></p>
                    <p>NIT: 900123456-7</p>
                    <p>Responsable de IVA - Régimen Común</p>
                    <p style="margin-top: 10px;">
                        Este es un correo automático, por favor no responder.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.html = html_body
        
        # Adjuntar PDF
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                msg.attach(
                    filename=f'Factura_{invoice.folio}.pdf',
                    content_type='application/pdf',
                    data=pdf_file.read()
                )
        
        # Enviar email
        mail.send(msg)
        current_app.logger.info(f'Factura {invoice.folio} enviada por email a {user.email}')
        return True
        
    except Exception as e:
        current_app.logger.error(f'Error enviando factura por email: {str(e)}')
        return False
