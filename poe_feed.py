#!/usr/bin/env python3
"""Generador RSS del Periódico Oficial de Chihuahua a partir del índice público.
Solo publica ediciones de hoy/ayer (fecha impresa), sin alterar la fuente oficial.
No usa OCR, PDF ni servicios de pago. Python 3.11+.
"""
from __future__ import annotations
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, date, time, timedelta
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

TZ = ZoneInfo('America/Chihuahua')
ROOT = 'https://chihuahua.gob.mx'
INDEX = ROOT + '/periodicooficial/buscador'
MONTHS = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
          'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,
          'noviembre':11,'diciembre':12}
# Disposiciones importantes para administración pública, fiscalización y finanzas.
TERMS = ('participacion','aportacion','deuda','financ','presupuest','ingreso',
         'egreso','hacienda','fiscal','tribut','recaud','impuesto','cuenta publica',
         'contabilidad gubernamental','auditor','fideicomis','obra publica',
         'fondos federales','transferencia','disciplina financiera',
         'subsidio','gasto publico','ley de coordinacion','reglamento',
         'lineamiento','convenio','desarrollo municipal','administracion publica',
         'programa municipal','remuneracion','arancel','tarifa',
         'economia','municipios','municipal','secretaria de hacienda',
         'congreso del estado','decreto')


def normal(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold())
                   if not unicodedata.combining(c))


def issue_date(text: str) -> date | None:
    x = normal(text)
    m = re.search(r'\b(\d{1,2})\s+de\s+([a-z]+)\s+(?:de|del)\s+(\d{4})\b', x)
    if not m or m.group(2) not in MONTHS:
        return None
    try:
        return date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
    except ValueError:
        return None


def relevant(title: str) -> bool:
    x = normal(title)
    # Excluye solo anexos claramente ajenos si no incluyen un tema relevante.
    return any(term in x for term in TERMS)


def official_url(href: str, base: str = INDEX) -> str | None:
    if not href or href.strip().startswith(('javascript:', 'data:')):
        return None
    u = urljoin(base,href)
    p = urlparse(u)
    if p.scheme != 'https' or p.hostname not in ('chihuahua.gob.mx','www.chihuahua.gob.mx'):
        return None
    return u


def parse_index(html: str, today: date) -> list[dict]:
    soup = BeautifulSoup(html,'html.parser')
    entries: list[dict] = []
    target = {today, today-timedelta(days=1)}
    table = soup.find('table')
    if table is None:
        raise ValueError('No se encontró tabla HTML en el catálogo del POE; revisar estructura del sitio.')
    nrows = 0
    valid_dates = 0
    for tr in table.find_all('tr'):
        cells = tr.find_all('td',recursive=False)
        if len(cells)<5:
            continue
        nrows += 1
        # Página oficial: Año | Núm. | Periódico (con fecha) | Mes | Archivo | Anexos.
        link_detail = cells[2].find('a',href=True)
        fecha = issue_date(cells[2].get_text(' ',strip=True))
        if fecha is not None:
            valid_dates += 1
        if fecha not in target:
            continue
        issue_no = cells[1].get_text(' ',strip=True)
        detail_url = official_url(link_detail.get('href','')) if link_detail else INDEX
        pdf_anchor = cells[4].find('a',href=True)
        pdf_url = official_url(pdf_anchor['href']) if pdf_anchor else None
        # El ejemplar completo se muestra como enlace general, no como resumen del PDF.
        if pdf_url:
            entries.append({'title':f'Periódico Oficial de Chihuahua | Ejemplar {issue_no} | {fecha.strftime("%d/%m/%Y")}',
                            'url':pdf_url,'date':fecha,'kind':'Ejemplar oficial', 'number':issue_no})
        for cell in cells[5:]:
            for a in cell.find_all('a',href=True):
                title = a.get_text(' ',strip=True)
                href = official_url(a.get('href',''))
                if title and href and relevant(title):
                    entries.append({'title':title,'url':href,'date':fecha,'kind':'Anexo relevante',
                                    'number':issue_no,'detail':detail_url})
    if nrows==0 or valid_dates==0:
        raise ValueError('El catálogo no presentó filas o fechas reconocibles; evita crear un RSS vacío silenciosamente.')
    # Elimina duplicados por URL (sin duplicación entre páginas de índice).
    out, seen = [], set()
    for e in entries:
        k=e['url'].split('#',1)[0]
        if k not in seen:
            seen.add(k);out.append(e)
    out.sort(key=lambda x:(x['date'],x['kind']=='Anexo relevante',x['title']),reverse=True)
    return out


def fetch_index(session: requests.Session, page: int) -> str:
    r=session.get(INDEX,params={'page':page},timeout=25,headers={'User-Agent':'Monitor-POE-Chihuahua/8.0 (lectura publicaciones oficiales; 1 vez por hora)'})
    r.raise_for_status()
    if len(r.content)>5_000_000:
        raise ValueError('La página del POE superó el límite de lectura.')
    return r.text


def rss_xml(items: list[dict], now: datetime) -> bytes:
    rss=ET.Element('rss',{'version':'2.0'})
    channel=ET.SubElement(rss,'channel')
    for tag,txt in [('title','Periódico Oficial Chihuahua - ejemplares y anexos relevantes'),
                    ('link',INDEX),('description','Detección directa en el índice del POE; únicamente hoy y ayer, hora Chihuahua.'),
                    ('language','es-MX'),('lastBuildDate',format_datetime(now))]:
        ET.SubElement(channel,tag).text=txt
    for e in items:
        el=ET.SubElement(channel,'item')
        pub_dt=datetime.combine(e['date'],time(0,5),tzinfo=TZ)
        for tag,txt in [('title',e['title']),('link',e['url']),('guid',e['url']),
                        ('pubDate',format_datetime(pub_dt)),('category',e['kind']),
                        ('description',f"Publicación oficial de Chihuahua, número {e['number']}, fecha {e['date'].strftime('%d/%m/%Y')}. {e['kind']}. Documento original.")]:
            if tag=='guid': ET.SubElement(el,tag,{'isPermaLink':'true'}).text=txt
            else: ET.SubElement(el,tag).text=txt
    ET.indent(rss,space='  ')
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True)


def main() -> int:
    now=datetime.now(TZ)
    # Para pruebas: V8_FECHA_PRUEBA=2026-10-15, sin alterar las fuentes.
    today=date.fromisoformat(os.environ['V8_FECHA_PRUEBA']) if 'V8_FECHA_PRUEBA' in os.environ else now.date()
    combined=[]
    with requests.Session() as session:
        for page in (0,1):
            html=fetch_index(session,page)
            combined += parse_index(html,today)
    combined=list({x['url']:x for x in combined}.values())
    combined.sort(key=lambda x:(x['date'],x['kind']),reverse=True)
    out=Path('public');out.mkdir(exist_ok=True,parents=True)
    rss=rss_xml(combined,now)
    ET.fromstring(rss)  # valida RSS antes de publicarlo
    (out/'feed.xml').write_bytes(rss)
    status={'fecha_generacion':now.isoformat(),'fecha_hoy':today.isoformat(),
            'fecha_ayer':(today-timedelta(days=1)).isoformat(),
            'elementos':len(combined),'fuente':INDEX,
            'titulos':[{'fecha':e['date'].isoformat(),'titulo':e['title'],'url':e['url']} for e in combined]}
    (out/'estado.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'RSS generado: {len(combined)} publicaciones de {today} y {today-timedelta(days=1)}')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print(f'ERROR: no se publicó un RSS nuevo: {exc}',file=sys.stderr)
        sys.exit(1)
