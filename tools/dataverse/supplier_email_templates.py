"""Default e-mail templates for the messages to suppliers (Account type, one per message and language).

The op365_SupplierEmailTemplates environment variable maps each message and supplier Language to a template title; its
default value names the templates created here. Templates are environment data, not solution components: run this
script once in every environment (PAC_* variables), then adapt the text in Settings > Templates > Email Templates.
An existing template with the same title is left as it is. Placeholders {Document}, {DocumentType}, {Number},
{IssueDate} and {ExpiryDate} (documents), {Contact}, {Email}, {Link} and {ExpiryDate} (portal invitation) are filled
by the plugin; the supplier name comes from the Account.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from dv import S, API

LANGUAGES = {'English': 1033, 'Italian': 1040, 'German': 1031, 'French': 1036}

TEXTS = {
    'DocumentExpiring': {
        'English': ('ProjectIQ - Document expiring', 'Document expiring: {Document}',
                    'your document {Document} ({DocumentType} {Number}) expires on {ExpiryDate}. '
                    'Please upload the renewed document in the Documents page of the supplier portal.'),
        'Italian': ('ProjectIQ - Documento in scadenza', 'Documento in scadenza: {Document}',
                    'il vostro documento {Document} ({DocumentType} {Number}) scade il {ExpiryDate}. '
                    'Vi chiediamo di caricare il documento rinnovato nella pagina Documents del portale fornitori.'),
        'German': ('ProjectIQ - Dokument läuft bald ab', 'Dokument läuft bald ab: {Document}',
                   'Ihr Dokument {Document} ({DocumentType} {Number}) läuft am {ExpiryDate} ab. '
                   'Bitte laden Sie das erneuerte Dokument auf der Seite Documents des Lieferantenportals hoch.'),
        'French': ('ProjectIQ - Document bientôt expiré', 'Document bientôt expiré : {Document}',
                   'votre document {Document} ({DocumentType} {Number}) expire le {ExpiryDate}. '
                   'Merci de téléverser le document renouvelé dans la page Documents du portail fournisseurs.'),
    },
    'DocumentExpired': {
        'English': ('ProjectIQ - Document expired', 'Document expired: {Document}',
                    'your document {Document} ({DocumentType} {Number}) expired on {ExpiryDate}. '
                    'Please upload the renewed document in the Documents page of the supplier portal.'),
        'Italian': ('ProjectIQ - Documento scaduto', 'Documento scaduto: {Document}',
                    'il vostro documento {Document} ({DocumentType} {Number}) è scaduto il {ExpiryDate}. '
                    'Vi chiediamo di caricare il documento rinnovato nella pagina Documents del portale fornitori.'),
        'German': ('ProjectIQ - Dokument abgelaufen', 'Dokument abgelaufen: {Document}',
                   'Ihr Dokument {Document} ({DocumentType} {Number}) ist am {ExpiryDate} abgelaufen. '
                   'Bitte laden Sie das erneuerte Dokument auf der Seite Documents des Lieferantenportals hoch.'),
        'French': ('ProjectIQ - Document expiré', 'Document expiré : {Document}',
                   'votre document {Document} ({DocumentType} {Number}) a expiré le {ExpiryDate}. '
                   'Merci de téléverser le document renouvelé dans la page Documents du portail fournisseurs.'),
    },
    'PortalInvitation': {
        'English': ('ProjectIQ - Portal invitation', 'Invitation to the supplier portal',
                    '{Contact}, you are invited to the supplier portal, where you can see the documents, requests for quotation '
                    'and purchase orders of your company. Create your account with the e-mail {Email} from this link by '
                    '{ExpiryDate} (it can be used once): <a href="{Link}">{Link}</a>'),
        'Italian': ('ProjectIQ - Invito al portale', 'Invito al portale fornitori',
                    '{Contact}, sei invitato al portale fornitori, dove puoi vedere i documenti, le richieste di offerta e gli '
                    'ordini di acquisto della tua azienda. Crea il tuo account con l\'e-mail {Email} da questo link entro il '
                    '{ExpiryDate} (utilizzabile una volta): <a href="{Link}">{Link}</a>'),
        'German': ('ProjectIQ - Portaleinladung', 'Einladung zum Lieferantenportal',
                   '{Contact}, Sie sind zum Lieferantenportal eingeladen, wo Sie die Dokumente, Angebotsanfragen und '
                   'Bestellungen Ihres Unternehmens sehen. Legen Sie Ihr Konto mit der E-Mail {Email} über diesen Link bis zum '
                   '{ExpiryDate} an (einmal verwendbar): <a href="{Link}">{Link}</a>'),
        'French': ('ProjectIQ - Invitation au portail', 'Invitation au portail fournisseurs',
                   '{Contact}, vous êtes invité(e) au portail fournisseurs, où vous voyez les documents, les appels d\'offres '
                   'et les bons de commande de votre entreprise. Créez votre compte avec l\'e-mail {Email} depuis ce lien avant le '
                   '{ExpiryDate} (utilisable une fois) : <a href="{Link}">{Link}</a>'),
    },
}


def xsl(parts):
    """Template XSL: literal text in CDATA, ('field', name) for an Account column."""
    out = ''.join(f'<![CDATA[{p}]]>' if isinstance(p, str) else f'<xsl:value-of select="account/{p[1]}" />' for p in parts)
    return ('<?xml version="1.0" ?><xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">'
            f'<xsl:output method="text" indent="no"/><xsl:template match="/data">{out}</xsl:template></xsl:stylesheet>')


def default_mapping():
    """Default value of op365_SupplierEmailTemplates: the titles created here."""
    return {message: dict({lang: t[0] for lang, t in texts.items()}, default='English') for message, texts in TEXTS.items()}


if __name__ == '__main__':
    headers = {'MSCRM.SolutionUniqueName': None}  # environment data: keep templates out of the solution
    for message, texts in TEXTS.items():
        for lang, (title, subject, body) in texts.items():
            q = title.replace("'", "''")
            if S.get(API + f"templates?$select=templateid&$filter=title eq '{q}' and templatetypecode eq 'account'").json()['value']:
                print('skip', title); continue
            r = S.post(API + 'templates', headers=headers, json={
                'title': title, 'templatetypecode': 'account', 'ispersonal': False, 'languagecode': LANGUAGES[lang],
                'description': f'ProjectIQ message {message} to suppliers ({lang}); see op365_SupplierEmailTemplates',
                'subject': xsl([subject]),
                'body': xsl(['<p>', ('field', 'name'), ',</p><p>', body, '</p>'])})
            if r.status_code >= 300:
                sys.exit(f'{title}: {r.status_code} {r.text[:300]}')
            print('ok  ', title)
    print(json.dumps(default_mapping(), ensure_ascii=False))
