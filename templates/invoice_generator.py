"""
Invoice PDF Generator using ReportLab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
import os

class InvoiceGenerator:
    def __init__(self, output_dir='invoices'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()
        
    def generate_invoice(self, invoice_data):
        """
        Generate PDF invoice
        
        invoice_data = {
            'invoice_number': 'INV-2024-001',
            'invoice_date': datetime.now(),
            'due_date': datetime.now(),
            'company': {
                'name': 'Your Company Name',
                'address': 'Address Line 1\nCity, State - PIN',
                'email': 'info@company.com',
                'phone': '+91-9876543210',
                'gst': '22AAAAA0000A1Z5'
            },
            'client': {
                'name': 'ABC Transport Ltd',
                'contact': 'John Doe',
                'address': 'Client Address',
                'email': 'client@email.com',
                'phone': '+91-1234567890',
                'gst': '27BBBBB1111B1Z5'
            },
            'items': [
                {'description': 'GTMS License - Professional Plan', 'quantity': 1, 'rate': 10000, 'amount': 10000}
            ],
            'subtotal': 10000,
            'tax_rate': 18,
            'tax_amount': 1800,
            'discount': 0,
            'total': 11800,
            'payment_method': 'UPI',
            'transaction_id': 'TXN123456',
            'notes': 'Thank you for your business!'
        }
        """
        
        filename = f"{invoice_data['invoice_number']}.pdf"
        filepath = os.path.join(self.output_dir, filename)
        
        doc = SimpleDocTemplate(filepath, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        story = []
        
        # Header Style
        header_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        # Company Header
        story.append(Paragraph(invoice_data['company']['name'], header_style))
        story.append(Paragraph(
            f"{invoice_data['company']['address']}<br/>"
            f"Email: {invoice_data['company']['email']} | Phone: {invoice_data['company']['phone']}<br/>"
            f"GST: {invoice_data['company']['gst']}",
            ParagraphStyle('center_small', parent=self.styles['Normal'], alignment=TA_CENTER, fontSize=9)
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice Title
        story.append(Paragraph('TAX INVOICE', ParagraphStyle('invoice_title', parent=self.styles['Heading2'], alignment=TA_CENTER)))
        story.append(Spacer(1, 0.2*inch))
        
        # Invoice Details Table
        invoice_info_data = [
            ['Invoice Number:', invoice_data['invoice_number'], 'Invoice Date:', invoice_data['invoice_date'].strftime('%d-%b-%Y')],
            ['Due Date:', invoice_data['due_date'].strftime('%d-%b-%Y') if invoice_data.get('due_date') else '-', 'Payment Method:', invoice_data.get('payment_method', '-')]
        ]
        
        invoice_info_table = Table(invoice_info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
        invoice_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Client Details
        client_data = [
            ['BILL TO:'],
            [invoice_data['client']['name']],
            [invoice_data['client']['contact']] if invoice_data['client'].get('contact') else [],
            [invoice_data['client']['address']],
            [f"Email: {invoice_data['client']['email']}"] if invoice_data['client'].get('email') else [],
            [f"Phone: {invoice_data['client']['phone']}"] if invoice_data['client'].get('phone') else [],
            [f"GST: {invoice_data['client']['gst']}"] if invoice_data['client'].get('gst') else []
        ]
        
        client_table = Table([row for row in client_data if row], colWidths=[6.5*inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('FONTSIZE', (0, 1), (0, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.grey),
            ('BOTTOMPADDING', (0, 0), (0, 0), 6),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Items Table
        items_data = [['#', 'Description', 'Qty', 'Rate', 'Amount']]
        for idx, item in enumerate(invoice_data['items'], 1):
            items_data.append([
                str(idx),
                item['description'],
                str(item['quantity']),
                f"₹{item['rate']:,.2f}",
                f"₹{item['amount']:,.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Totals Table
        totals_data = [
            ['Subtotal:', f"₹{invoice_data['subtotal']:,.2f}"],
            [f"GST ({invoice_data['tax_rate']}%):", f"₹{invoice_data['tax_amount']:,.2f}"]
        ]
        
        if invoice_data.get('discount', 0) > 0:
            totals_data.append(['Discount:', f"- ₹{invoice_data['discount']:,.2f}"])
        
        totals_data.append(['Total Amount:', f"₹{invoice_data['total']:,.2f}"])
        
        totals_table = Table(totals_data, colWidths=[5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1a237e')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1a237e')),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 0.4*inch))
        
        # Notes
        if invoice_data.get('notes'):
            story.append(Paragraph('<b>Notes:</b>', self.styles['Normal']))
            story.append(Paragraph(invoice_data['notes'], self.styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.3*inch))
        footer_style = ParagraphStyle('footer', parent=self.styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)
        story.append(Paragraph('This is a computer-generated invoice. No signature required.', footer_style))
        story.append(Paragraph(f'Generated on {datetime.now().strftime("%d-%b-%Y %I:%M %p")}', footer_style))
        
        # Build PDF
        doc.build(story)
        
        return filepath
