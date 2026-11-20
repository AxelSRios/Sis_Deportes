"""Exportadores de reportes del sistema A.F.O. · Oruro.

Genera documentos listos para archivo o impresión:

- PDF con ReportLab: encabezado institucional, tabla paginada con cabecera
  repetida, filas alternas y numeración de páginas.
- Excel con openpyxl: hoja con título, filtros activables, encabezados fijos
  y formato de impresión horizontal.

Ambos exportadores reciben el diccionario que devuelven las funciones de
``core.views_admin`` (titulo, encabezados, filas, nota, desde, hasta) y no
consultan la base de datos por su cuenta.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Paleta institucional (coincide con static/js/tailwind-config.js).
AZUL = colors.HexColor('#002b6d')
AZUL_CLARO = colors.HexColor('#eff4ff')
TEAL = colors.HexColor('#00677f')
GRIS = colors.HexColor('#434651')
GRIS_LINEA = colors.HexColor('#c9d3e0')
GRIS_FILA = colors.HexColor('#f4f7fc')

LOGO = Path(settings.BASE_DIR) / 'static' / 'img' / 'afo-crest.png'

MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
    'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


def _texto(valor) -> str:
    """Convierte cualquier celda a texto imprimible."""
    if valor is None:
        return '—'
    if isinstance(valor, Decimal):
        return f'{valor:.2f}'
    if isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y %H:%M')
    texto = str(valor)
    return texto if texto.strip() else '—'


def _fecha_larga(momento: datetime | None) -> str:
    momento = momento or datetime.now()
    return (
        f'{momento.day} de {MESES[momento.month - 1]} de {momento.year}, '
        f'{momento.strftime("%H:%M")}'
    )


def _anchos_columnas(encabezados, filas, disponible: float) -> list[float]:
    """Reparte el ancho disponible según el contenido esperado."""
    pesos = []
    for indice, encabezado in enumerate(encabezados):
        largo = len(str(encabezado))
        for fila in filas[:80]:
            if indice < len(fila):
                largo = max(largo, len(_texto(fila[indice])))
        pesos.append(min(max(largo, 5), 46))

    total = sum(pesos) or 1
    anchos = [disponible * peso / total for peso in pesos]

    minimo = 13 * mm
    deficit = sum(minimo - ancho for ancho in anchos if ancho < minimo)
    if deficit:
        sobrante = sum(ancho - minimo for ancho in anchos if ancho > minimo)
        factor = max(0.0, (sobrante - deficit) / sobrante) if sobrante else 1.0
        anchos = [
            max(minimo, ancho - (ancho - minimo) * (1 - factor))
            if ancho > minimo else minimo
            for ancho in anchos
        ]

    escala = disponible / sum(anchos)
    return [ancho * escala for ancho in anchos]


def _encabezado_pdf(datos, generado: datetime, disponible: float):
    """Bloque superior con escudo, título y metadatos del reporte."""
    titulo = Paragraph(
        escape(str(datos.get('titulo') or 'Reporte institucional')),
        ParagraphStyle(
            'TituloReporte', fontName='Helvetica-Bold', fontSize=15,
            leading=18, textColor=AZUL, alignment=TA_LEFT,
        ),
    )
    detalles = (
        f'Generado el {_fecha_larga(generado)} · '
        f'{len(datos.get("filas") or [])} registro(s)'
    )
    nota = datos.get('nota') or ''
    subtitulo = Paragraph(
        escape(detalles) + (f'<br/><i>{escape(str(nota))}</i>' if nota else ''),
        ParagraphStyle(
            'DetalleReporte', fontName='Helvetica', fontSize=8,
            leading=11, textColor=GRIS,
        ),
    )

    if LOGO.exists():
        escudo = Image(
            str(LOGO), width=16 * mm, height=8.9 * mm, kind='proportional',
        )
        cabecera = Table(
            [[escudo, [titulo, Spacer(1, 1.5 * mm), subtitulo]]],
            colWidths=[20 * mm, disponible - 20 * mm],
        )
        cabecera.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
    else:
        cabecera = Table([[titulo], [subtitulo]], colWidths=[disponible])

    marca = Paragraph(
        'ASOCIACIÓN DE FÚTBOL ORURO',
        ParagraphStyle(
            'MarcaReporte', fontName='Helvetica-Bold', fontSize=8,
            leading=10, textColor=TEAL,
        ),
    )
    return [marca, Spacer(1, 1.5 * mm), cabecera, Spacer(1, 4 * mm)]


def _pie_pdf(canvas, documento):
    canvas.saveState()
    ancho, _ = landscape(A4)
    canvas.setStrokeColor(GRIS_LINEA)
    canvas.setLineWidth(0.4)
    canvas.line(10 * mm, 10 * mm, ancho - 10 * mm, 10 * mm)
    canvas.setFillColor(GRIS)
    canvas.setFont('Helvetica', 7)
    canvas.drawString(
        10 * mm, 6 * mm,
        'Asociación de Fútbol Oruro · Sistema de Gestión Deportiva',
    )
    canvas.drawRightString(
        ancho - 10 * mm, 6 * mm, f'Página {canvas.getPageNumber()}',
    )
    canvas.restoreState()


def generar_pdf(datos, generado: datetime | None = None) -> bytes:
    """Devuelve el reporte en PDF (bytes) listo para descargar o imprimir."""
    generado = generado or datetime.now()
    buffer = BytesIO()
    ancho, alto = landscape(A4)
    margen = 10 * mm
    disponible = ancho - 2 * margen

    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=margen,
        rightMargin=margen,
        topMargin=10 * mm,
        bottomMargin=13 * mm,
        title=str(datos.get('titulo') or 'Reporte A.F.O. Oruro'),
        author='Asociación de Fútbol Oruro',
        subject='Reporte institucional',
    )

    historia = _encabezado_pdf(datos, generado, disponible)
    encabezados = list(datos.get('encabezados') or [])
    filas = list(datos.get('filas') or [])

    estilo_celda = ParagraphStyle(
        'CeldaReporte', fontName='Helvetica', fontSize=7.2,
        leading=8.8, textColor=colors.HexColor('#0b1c30'),
    )
    estilo_numero = ParagraphStyle(
        'CeldaNumero', parent=estilo_celda, alignment=TA_RIGHT,
    )
    estilo_cabecera = ParagraphStyle(
        'CabeceraReporte', fontName='Helvetica-Bold', fontSize=7.4,
        leading=9, textColor=colors.white, alignment=TA_LEFT,
    )

    tabla_datos = [[
        Paragraph(escape(str(encabezado)), estilo_cabecera)
        for encabezado in encabezados
    ]]
    for fila in filas:
        celdas = []
        for indice in range(len(encabezados)):
            valor = fila[indice] if indice < len(fila) else ''
            estilo = (
                estilo_numero
                if isinstance(valor, (int, float, Decimal))
                else estilo_celda
            )
            celdas.append(Paragraph(escape(_texto(valor)), estilo))
        tabla_datos.append(celdas)

    if not filas:
        tabla_datos.append([
            Paragraph(
                'Sin datos para el reporte con los filtros aplicados.',
                estilo_celda,
            )
        ] + [''] * (len(encabezados) - 1))

    anchos = _anchos_columnas(encabezados, filas, disponible)
    tabla = Table(tabla_datos, colWidths=anchos, repeatRows=1)
    estilos = [
        ('BACKGROUND', (0, 0), (-1, 0), AZUL),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.35, GRIS_LINEA),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2.6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS_FILA]),
    ]
    if not filas:
        estilos.append(('SPAN', (0, 1), (-1, 1)))
        estilos.append(('ALIGN', (0, 1), (-1, 1), 'CENTER'))
    tabla.setStyle(TableStyle(estilos))
    historia.append(tabla)

    documento.build(historia, onFirstPage=_pie_pdf, onLaterPages=_pie_pdf)
    return buffer.getvalue()


def _titulo_hoja(titulo: str) -> str:
    limpio = ''.join(
        caracter for caracter in str(titulo)[:31]
        if caracter not in '[]:*?/\\'
    ).strip()
    return limpio or 'Reporte'


def generar_xlsx(datos, generado: datetime | None = None) -> bytes:
    """Devuelve el reporte en Excel (.xlsx) con formato institucional."""
    generado = generado or datetime.now()
    encabezados = list(datos.get('encabezados') or [])
    filas = list(datos.get('filas') or [])
    columnas = max(len(encabezados), 1)
    ultima = get_column_letter(columnas)

    libro = Workbook()
    hoja = libro.active
    hoja.title = _titulo_hoja(datos.get('titulo') or 'Reporte')
    hoja.sheet_view.showGridLines = False

    borde = Border(
        left=Side(style='thin', color='C9D3E0'),
        right=Side(style='thin', color='C9D3E0'),
        top=Side(style='thin', color='C9D3E0'),
        bottom=Side(style='thin', color='C9D3E0'),
    )

    hoja.merge_cells(f'A1:{ultima}1')
    marca = hoja['A1']
    marca.value = 'ASOCIACIÓN DE FÚTBOL ORURO'
    marca.font = Font(name='Calibri', size=9, bold=True, color='00677F')
    marca.alignment = Alignment(horizontal='left', vertical='center')

    hoja.merge_cells(f'A2:{ultima}2')
    titulo = hoja['A2']
    titulo.value = datos.get('titulo') or 'Reporte institucional'
    titulo.font = Font(name='Calibri', size=15, bold=True, color='002B6D')
    titulo.alignment = Alignment(horizontal='left', vertical='center')
    hoja.row_dimensions[2].height = 22

    detalle = (
        f'Generado el {_fecha_larga(generado)} · '
        f'{len(filas)} registro(s)'
    )
    if datos.get('nota'):
        detalle += f' · {datos["nota"]}'
    hoja.merge_cells(f'A3:{ultima}3')
    subtitulo = hoja['A3']
    subtitulo.value = detalle
    subtitulo.font = Font(name='Calibri', size=9, color='434651')
    subtitulo.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    hoja.row_dimensions[3].height = 26

    fila_cabecera = 5
    for indice, encabezado in enumerate(encabezados, start=1):
        celda = hoja.cell(row=fila_cabecera, column=indice, value=str(encabezado))
        celda.font = Font(name='Calibri', size=9, bold=True, color='FFFFFF')
        celda.fill = PatternFill('solid', fgColor='002B6D')
        celda.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        celda.border = borde

    for numero_fila, fila in enumerate(filas, start=fila_cabecera + 1):
        for indice in range(columnas):
            valor = fila[indice] if indice < len(fila) else None
            celda = hoja.cell(row=numero_fila, column=indice + 1, value=valor)
            celda.font = Font(name='Calibri', size=9, color='0B1C30')
            celda.alignment = Alignment(
                horizontal='right' if isinstance(valor, (int, float, Decimal)) else 'left',
                vertical='top',
                wrap_text=True,
            )
            celda.border = borde
            if numero_fila % 2 == 0:
                celda.fill = PatternFill('solid', fgColor='F4F7FC')
            if isinstance(valor, (int, float, Decimal)):
                celda.number_format = '#,##0.00' if isinstance(valor, Decimal) else '#,##0'

    if not filas:
        hoja.merge_cells(
            start_row=fila_cabecera + 1, start_column=1,
            end_row=fila_cabecera + 1, end_column=columnas,
        )
        vacio = hoja.cell(row=fila_cabecera + 1, column=1)
        vacio.value = 'Sin datos para el reporte con los filtros aplicados.'
        vacio.font = Font(name='Calibri', size=9, italic=True, color='434651')
        vacio.alignment = Alignment(horizontal='center', vertical='center')

    ultima_fila = max(fila_cabecera + 1, fila_cabecera + len(filas))
    hoja.auto_filter.ref = f'A{fila_cabecera}:{ultima}{ultima_fila}'
    hoja.freeze_panes = f'A{fila_cabecera + 1}'

    for indice, encabezado in enumerate(encabezados, start=1):
        largo = len(str(encabezado))
        for fila in filas[:200]:
            if indice - 1 < len(fila):
                largo = max(largo, len(_texto(fila[indice - 1])))
        hoja.column_dimensions[get_column_letter(indice)].width = min(
            max(largo + 2, 10), 42
        )
    hoja.row_dimensions[fila_cabecera].height = 24

    hoja.page_setup.orientation = 'landscape'
    hoja.page_setup.paperSize = hoja.PAPERSIZE_A4
    hoja.page_setup.fitToWidth = 1
    hoja.page_setup.fitToHeight = 0
    hoja.sheet_properties.pageSetUpPr.fitToPage = True
    hoja.print_title_rows = f'1:{fila_cabecera}'
    hoja.print_options.horizontalCentered = True

    buffer = BytesIO()
    libro.save(buffer)
    return buffer.getvalue()
