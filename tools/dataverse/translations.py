"""Translations IT/FR/DE: exports the solution translation file, fills the missing labels
from translations.json (English text -> [de, fr, it]) and imports it back.
Usage: python tools/dataverse/translations.py [export-only]
ExportTranslation/ImportTranslation are not on the Web API, so they go through the SOAP endpoint."""
import base64, io, json, os, re, sys, uuid, zipfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, ENV

SOLUTION = 'OpenProject365'
SS = '{urn:schemas-microsoft-com:office:spreadsheet}'
NS = {'ss': SS[1:-1]}
LANGS = {'1031': 0, '1036': 1, '1040': 2}   # columns in translations.json: de, fr, it
for p, u in [('', SS[1:-1]), ('o', 'urn:schemas-microsoft-com:office:office'), ('x', 'urn:schemas-microsoft-com:office:excel'),
             ('ss', SS[1:-1]), ('html', 'http://www.w3.org/TR/REC-html40')]:
    ET.register_namespace(p, u)


XSD = {'guid': 'http://schemas.microsoft.com/2003/10/Serialization/', '*': 'http://www.w3.org/2001/XMLSchema'}


def soap(name, params):
    """Execute an SDK message; params = [(key, xsd type, value)]."""
    kv = ''.join(f'<a:KeyValuePairOfstringanyType><b:key>{k}</b:key><b:value i:type="c:{t}" '
                 f'xmlns:c="{XSD.get(t, XSD["*"])}">{v}</b:value></a:KeyValuePairOfstringanyType>'
                 for k, t, v in params)
    body = ('<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>'
            '<Execute xmlns="http://schemas.microsoft.com/xrm/2011/Contracts/Services"><request '
            'xmlns:a="http://schemas.microsoft.com/xrm/2011/Contracts" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">'
            f'<a:Parameters xmlns:b="http://schemas.datacontract.org/2004/07/System.Collections.Generic">{kv}</a:Parameters>'
            f'<a:RequestId i:nil="true"/><a:RequestName>{name}</a:RequestName></request></Execute></s:Body></s:Envelope>')
    r = S.post(ENV + '/XRMServices/2011/Organization.svc/web', data=body.encode('utf-8'), timeout=900, headers={
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': 'http://schemas.microsoft.com/xrm/2011/Contracts/Services/IOrganizationService/Execute'})
    if r.status_code >= 300:
        raise SystemExit(f'{name}: {r.status_code} {r.text[:600]}')
    return r.text


def rows(ws):
    for r in ws.findall('.//ss:Row', NS):
        cells, vals = r.findall('ss:Cell', NS), []
        for c in cells:
            if c.get(SS + 'Index'):
                vals += [None] * (int(c.get(SS + 'Index')) - 1 - len(vals))
            d = c.find('ss:Data', NS)
            vals.append(d.text if d is not None else None)
        yield r, cells, vals


def fill(xml, table):
    root = ET.fromstring(xml)
    ws = [w for w in root.findall('ss:Worksheet', NS) if w.get(SS + 'Name') == 'Localized Labels'][0]
    it = rows(ws)
    header = next(it)[2]
    cols = {i: LANGS[h] for i, h in enumerate(header) if h in LANGS}
    base = header.index('1033')
    filled, missing = 0, set()
    for r, cells, vals in it:
        vals += [None] * (len(header) - len(vals))
        en = vals[base]
        if not en or all(vals[i] for i in cols):
            continue
        if en not in table:
            missing.add(en)
            continue
        for i, k in cols.items():
            if not vals[i]:
                vals[i] = table[en][k]
                filled += 1
        style = cells[0].get(SS + 'StyleID')
        for c in cells:
            r.remove(c)
        for v in vals:
            c = ET.SubElement(r, SS + 'Cell')
            if style:
                c.set(SS + 'StyleID', style)
            if v is not None:
                d = ET.SubElement(c, SS + 'Data')
                d.set(SS + 'Type', 'String')
                d.text = v
    return ET.tostring(root, encoding='utf-8', xml_declaration=True), filled, missing


exported = soap('ExportTranslation', [('SolutionName', 'string', SOLUTION)])
src = zipfile.ZipFile(io.BytesIO(base64.b64decode(re.search(r'ExportTranslationFile</b:key><b:value[^>]*>([^<]+)', exported).group(1))))
table = json.load(open(os.path.join(os.path.dirname(__file__), 'translations.json'), encoding='utf-8'))
xml, filled, missing = fill(src.read('CrmTranslations.xml'), table)
print(f'filled {filled} labels; {len(missing)} English labels without translation')
for m in sorted(missing):
    print('  missing:', m)
if 'export-only' in sys.argv or not filled:
    sys.exit(0)
out = io.BytesIO()
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('CrmTranslations.xml', xml)
    z.writestr('[Content_Types].xml', src.read('[Content_Types].xml'))
soap('ImportTranslation', [('TranslationFile', 'base64Binary', base64.b64encode(out.getvalue()).decode()),
                           ('ImportJobId', 'guid', str(uuid.uuid4()))])
soap('PublishAllXml', [])
print('imported and published')
