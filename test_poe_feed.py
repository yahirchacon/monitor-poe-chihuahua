import sys
from pathlib import Path
from datetime import date,datetime
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET
import poe_feed

HTML='''<!doctype html><html><body>
<table><thead><tr><th>Año</th><th>Núm.</th><th>Periódico</th><th>Mes</th><th>Archivo</th><th>Anexos</th></tr></thead>
<tbody>
<tr><td>2026</td><td>82</td><td><a href="/periodicooficial/miercoles-14-de-octubre-de-2026">Miércoles 14 de octubre de 2026</a></td><td>Octubre</td><td><a href="/pdfs/PO82-2026.pdf">PO82-2026</a></td><td><a href="/pdfs/IEE82.pdf">ANEXO 82-2026 IEE ACUERDO 99</a> <a href="/pdfs/Ojinaga82.pdf">ANEXO 82-2026 MUNICIPIO OJINAGA CÓDIGO DE ÉTICA</a> <a href="/pdfs/Contabilidad82.pdf">ANEXO 82-2026 PJE OAJ MANUAL DE CONTABILIDAD GUBERNAMENTAL</a></td></tr>
<tr><td>2026</td><td>81</td><td><a href="/periodicooficial/sabado-10-de-octubre-de-2026">Sábado 10 de octubre de 2026</a></td><td>Octubre</td><td><a href="/pdfs/PO81-2026.pdf">PO81-2026</a></td><td><a href="/sites/default/atach2/periodico-oficial/anexos/2026-10/ANEXO%2081-2026%20SH%20ACUERDO%20PARTICIPACIONES%20Y%20APORTACIONES%20A%20MPIO%20EGRESO%20TERCER%20TRIMESTRE%20Y%20ACUMULADO%202026.pdf">ANEXO 81-2026 SH ACUERDO PARTICIPACIONES Y APORTACIONES A MUNICIPIOS REGISTRADAS EN EL EGRESO TERCER TRIMESTRE Y ACUMULADO 2026</a></td></tr>
</tbody></table></body></html>'''

def test_filtra_fechas_y_temas():
    items=poe_feed.parse_index(HTML,date(2026,10,15))
    assert len(items)==2, [(i['title'],i['date']) for i in items]
    assert all(i['date']==date(2026,10,14) for i in items)
    assert all('81-2026' not in i['title'] for i in items)
    assert not any('IEE' in i['title'] or 'ÉTICA' in i['title'] for i in items)

def test_documento_ejemplo_fecha_real():
    items=poe_feed.parse_index(HTML,date(2026,10,11))
    assert any('PARTICIPACIONES Y APORTACIONES' in i['title'] for i in items)
    assert all(i['date']==date(2026,10,10) for i in items)

def test_rss_fecha_y_xml():
    items=poe_feed.parse_index(HTML,date(2026,10,15))
    rss=poe_feed.rss_xml(items,datetime(2026,10,15,10,0,tzinfo=ZoneInfo('America/Chihuahua')))
    root=ET.fromstring(rss)
    assert root.tag=='rss'
    assert len(root.findall('.//item'))==2
    assert '2026' in root.find('.//item/pubDate').text
    assert root.find('.//item/guid').text.startswith('https://chihuahua.gob.mx/')

def test_html_invalido_falla():
    try:poe_feed.parse_index('<html>estructura cambiada</html>',date(2026,10,15))
    except ValueError:pass
    else:raise AssertionError('Un cambio de sitio debe reportar error; no enviar RSS vacío')

def test_external_link_bloqueado():
    assert poe_feed.official_url('https://evil.example/x') is None
    assert poe_feed.official_url('/a.pdf') == 'https://chihuahua.gob.mx/a.pdf'
