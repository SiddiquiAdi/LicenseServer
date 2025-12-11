from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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
        filename = f"{invoice_data['invoice_number']}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
        )
        story = []

        header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=12
        )

        story.append(Paragraph(invoice_data['company']['name'], header_style))
        story.append(Paragraph(
            f"{invoice_data['company']['address']}<br/>"
            f"Email: {invoice_data['company']['email']} | "
            f"Phone: {invoice_data['company']['phone']}<br/>"
            f"GST: {invoice_data['company']['gst']}",
            ParagraphStyle(
                'CompanyInfo',
                parent=self.styles['Normal'],
                alignment=TA_CENTER,
                fontSize=9
            )
        ))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph(
            'TAX INVOICE',
            ParagraphStyle('Title2', parent=self.styles['Heading2'], alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 0.2 * inch))

        invoice_info_data = [
            ['Invoice Number:', invoice_data['invoice_number'],
             'Invoice Date:', invoice_data['invoice_date'].strftime('%d-%b-%Y')],
            ['Due Date:', invoice_data.get('due_date', invoice_data['invoice_date']).strftime('%d-%b-%Y'),
             'Payment Method:', invoice_data.get('payment_method', '-')]
        ]
        invoice_info_table = Table(invoice_info_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 2 * inch])
        invoice_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (2, 0), (2, -1), colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 0.3 * inch))

        client_rows = [
            ['BILL TO:'],
            [invoice_data['client']['name']],
        ]
        if invoice_data['client'].get('contact'):
            client_rows.append([invoice_data['client']['contact']])
        client_rows.append([invoice_data['client']['address'] or '-'])
        if invoice_data['client'].get('email'):
            client_rows.append([f"Email: {invoice_data['client']['email']}"])
        if invoice_data['client'].get('phone'):
            client_rows.append([f"Phone: {invoice_data['client']['phone']}"])
        if invoice_data['client'].get('gst'):
            client_rows.append([f"GST: {invoice_data['client']['gst']}"])

        client_table = Table(client_rows, colWidths=[6.5 * inch])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 10),
            ('FONTSIZE', (0, 1), (0, -1), 9),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.grey),
            ('BOTTOMPADDING', (0, 0), (0, 0), 6),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 0.3 * inch))

        items_data = [['#', 'Description', 'Qty', 'Rate', 'Amount']]
        for idx, item in enumerate(invoice_data['items'], 1):
            items_data.append([
                str(idx),
                item['description'],
                str(item['quantity']),
                f"₹{item['rate']:,.2f}",
                f"₹{item['amount']:,.2f}",
            ])
        items_table = Table(items_data, colWidths=[0.5 * inch, 3.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3 * inch))

        totals_data = [
            ['Subtotal:', f"₹{invoice_data['subtotal']:,.2f}"],
            [f"GST ({invoice_data['tax_rate']}%):", f"₹{invoice_data['tax_amount']:,.2f}"],
        ]
        if invoice_data.get('discount', 0) > 0:
            totals_data.append(['Discount:', f"- ₹{invoice_data['discount']:,.2f}"])
        totals_data.append(['Total Amount:', f"₹{invoice_data['total']:,.2f}"])

        totals_table = Table(totals_data, colWidths=[5 * inch, 1.5 * inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1a237e')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1a237e')),
        ]))
        story.append(totals_table)
        story.append(Spacer(1, 0.4 * inch))

        if invoice_data.get('notes'):
            story.append(Paragraph('<b>Notes:</b>', self.styles['Normal']))
            story.append(Paragraph(invoice_data['notes'], self.styles['Normal']))
            story.append(Spacer(1, 0.2 * inch))

        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        )
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph('This is a computer-generated invoice. No signature required.', footer_style))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}",
            footer_style
        ))

        doc.build(story)
        return filepath
