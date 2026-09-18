"""
Generador de facturas electrónicas colombianas en PDF
Compatible con normativa DIAN
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import os
import qrcode
from io import BytesIO

class InvoiceGeneratorColombia:
    """Generador de facturas electrónicas colombianas"""
    
    @staticmethod
    def generate_qr_code(cufe):
        """Generar código QR con el CUFE"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(cufe)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a BytesIO
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def generate_pdf(invoice, order, output_path):
        """
        Generar PDF de factura electrónica colombiana
        
        Args:
            invoice: Objeto Invoice con datos colombianos
            order: Objeto Order
            output_path: Ruta donde guardar el PDF
        """
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Crear documento
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=6
        )
        
        # Encabezado
        elements.append(Paragraph("🎮 GAMETECH STORE SAS", title_style))
        elements.append(Paragraph("FACTURA ELECTRÓNICA DE VENTA", heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Información del emisor
        emisor_data = [
            ['DATOS DEL EMISOR', ''],
            ['Razón Social:', 'GameTech Store SAS'],
            ['NIT:', invoice.nit_emisor or '900123456-7'],
            ['Régimen:', invoice.regimen_emisor or 'Responsable de IVA'],
            ['Dirección:', 'Calle 123 #45-67, Bogotá D.C.'],
            ['Teléfono:', '+57 (1) 234-5678'],
            ['Email:', 'facturacion@gametechstore.com']
        ]
        
        emisor_table = Table(emisor_data, colWidths=[2*inch, 4*inch])
        emisor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(emisor_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Información de la factura y receptor
        info_data = [
            ['INFORMACIÓN DE LA FACTURA', 'DATOS DEL RECEPTOR'],
            [f'Folio: {invoice.folio}', f'NIT/CC: {invoice.nit_receptor}'],
            [f'Fecha: {invoice.fecha_emision.strftime("%d/%m/%Y %H:%M")}', f'Razón Social: {invoice.razon_social_receptor}'],
            [f'CUFE: {invoice.cufe[:20]}...', f'Dirección: {invoice.direccion_fiscal or "N/A"}'],
            ['Moneda: COP', f'Ciudad: {invoice.ciudad or "N/A"}'],
            [f'Forma de Pago: {invoice.forma_pago}', f'Departamento: {invoice.departamento or "N/A"}'],
            ['', f'Email: {invoice.email_receptor}']
        ]
        
        info_table = Table(info_data, colWidths=[3*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Detalle de productos
        products_data = [['#', 'Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
        
        for idx, item in enumerate(order.items, 1):
            products_data.append([
                str(idx),
                item.product_name[:40],
                str(item.quantity),
                f'${item.price:,.2f}',
                f'${item.get_subtotal():,.2f}'
            ])
        
        products_table = Table(products_data, colWidths=[0.5*inch, 3*inch, 1*inch, 1.25*inch, 1.25*inch])
        products_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(products_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Totales
        totales_data = [
            ['Subtotal:', f'${invoice.subtotal:,.2f} COP'],
            ['IVA (19%):', f'${invoice.iva:,.2f} COP'],
            ['TOTAL:', f'${invoice.total:,.2f} COP']
        ]
        
        totales_table = Table(totales_data, colWidths=[4.5*inch, 1.5*inch])
        totales_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
        ]))
        elements.append(totales_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Información DIAN
        dian_text = f"""
        <para align=center>
        <b>FACTURA ELECTRÓNICA VÁLIDA ANTE LA DIAN</b><br/>
        CUFE: {invoice.cufe}<br/>
        Esta factura electrónica ha sido generada conforme a la normativa colombiana.<br/>
        Resolución DIAN No. 123456789 del 01/01/2024<br/>
        Rango autorizado: FE-000001 hasta FE-999999<br/>
        Vigencia: 01/01/2024 hasta 31/12/2024
        </para>
        """
        elements.append(Paragraph(dian_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Pie de página
        footer_text = """
        <para align=center fontSize=8>
        GameTech Store SAS - NIT 900123456-7<br/>
        www.gametechstore.com | soporte@gametechstore.com<br/>
        ¡Gracias por tu compra!
        </para>
        """
        elements.append(Paragraph(footer_text, styles['Normal']))
        
        # Construir PDF
        doc.build(elements)
        
        return output_path
