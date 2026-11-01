"""Definitions of the cloud flows of the solution, shared by flows.py (creates them in an environment) and the solution
source in solutions/OpenProject365/src/Workflows (same clientdata).

Document metadata flows (docs/en/documents.md): one per document library. A file created in the folder of a record
(<name>_<record id without hyphens>, the Dataverse and Portfolio Agent convention) gets the ProjectIQ columns of that
record; files outside a record folder, or in the folder of a deleted record, are left as they are.
"""
import json

DATAVERSE = '/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps'
SHAREPOINT = '/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
CONNECTORS = {'shared_commondataserviceforapps': ('op365_dataverse', DATAVERSE),
              'shared_sharepointonline': ('op365_sharepoint', SHAREPOINT)}
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# environment variables: (schema name, display name, description); values are set per environment, never in the repository
SITE = ('op365_SharePointSiteUrl', 'SharePoint Site URL',
        'URL of the SharePoint site of the ProjectIQ document libraries (the default site of Document Management).')
LIBRARIES = {
    'op365_project': ('op365_ProjectLibraryId', 'Project Library Id', 'Id of the op365_project document library.'),
    'op365_purchaseorder': ('op365_PurchaseOrderLibraryId', 'Purchase Order Library Id',
                            'Id of the op365_purchaseorder document library.'),
    'op365_supplierdocument': ('op365_SupplierDocumentLibraryId', 'Supplier Document Library Id',
                               'Id of the op365_supplierdocument document library.'),
}


def parameter(variable):
    """Name of the flow parameter bound to an environment variable."""
    return f'{variable[1]} ({variable[0]})'


def unbound_action(action, parameters=None):
    params = {'actionName': action}
    params.update({f'item/{k}': v for k, v in (parameters or {}).items()})
    return {'runAfter': {}, 'type': 'OpenApiConnection', 'inputs': {
        'host': {'connectionName': 'shared_commondataserviceforapps', 'operationId': 'PerformUnboundAction',
                 'apiId': DATAVERSE},
        'parameters': params, 'authentication': "@parameters('$authentication')"}}


def clientdata(trigger, actions, connectors=('shared_commondataserviceforapps',), variables=()):
    parameters = {'$connections': {'defaultValue': {}, 'type': 'Object'},
                  '$authentication': {'defaultValue': {}, 'type': 'SecureObject'}}
    for v in variables:
        parameters[parameter(v)] = {'defaultValue': '', 'type': 'String',
                                    'metadata': {'schemaName': v[0], 'description': v[2]}}
    return {'properties': {
        'connectionReferences': {c: {
            'runtimeSource': 'embedded', 'connection': {'connectionReferenceLogicalName': CONNECTORS[c][0]},
            'api': {'name': c}} for c in connectors},
        'definition': {
            '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
            'contentVersion': '1.0.0.0',
            'parameters': parameters,
            'triggers': trigger, 'actions': actions},
        'templateName': None},
        'schemaVersion': '1.0.0.0'}


def _op(connector, operation, parameters, run_after=None):
    return {'runAfter': run_after or {}, 'type': 'OpenApiConnection', 'inputs': {
        'host': {'connectionName': connector, 'operationId': operation, 'apiId': CONNECTORS[connector][1]},
        'parameters': parameters, 'authentication': "@parameters('$authentication')"}}


def _site():
    return f"@parameters('{parameter(SITE)}')"


# ProjectIQ columns of the document libraries: internal name -> (display name, SharePoint field type, field id)
COLUMNS = {
    'ProjectIQRecordType': ('ProjectIQ Record Type', 'Choice', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b001'),
    'ProjectIQRecordId': ('ProjectIQ Record Id', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b002'),
    'ProjectIQProjectCode': ('Project Code', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b003'),
    'ProjectIQProjectName': ('Project Name', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b004'),
    'ProjectIQCustomer': ('Customer', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b005'),
    'ProjectIQProjectManager': ('Project Manager', 'User', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b006'),
    'ProjectIQPONumber': ('PO Number', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b007'),
    'ProjectIQSupplier': ('Supplier', 'Text', '5b0e3f6c-2d4a-4c1e-9f61-7a3e10c2b008'),
}
MANAGER = 'ProjectIQProjectManager'

# record of each library: Web API entity set, record type (choice value), $select, $expand and, for each column, the
# path of its value in the record (the project manager column takes the e-mail of the user)
RECORDS = {
    'op365_project': ('op365_projects', 'Project', 'op365_code,op365_name',
                      'op365_CustomerId($select=name),op365_ProjectManagerId($select=internalemailaddress)', {
                          'ProjectIQProjectCode': ('op365_code',),
                          'ProjectIQProjectName': ('op365_name',),
                          'ProjectIQCustomer': ('op365_CustomerId', 'name'),
                          MANAGER: ('op365_ProjectManagerId', 'internalemailaddress'),
                      }),
    'op365_purchaseorder': ('op365_purchaseorders', 'Purchase Order', 'op365_number',
                            'op365_SupplierId($select=name),op365_ProjectId($select=op365_code,op365_name;'
                            '$expand=op365_CustomerId($select=name),op365_ProjectManagerId($select=internalemailaddress))', {
                                'ProjectIQPONumber': ('op365_number',),
                                'ProjectIQSupplier': ('op365_SupplierId', 'name'),
                                'ProjectIQProjectCode': ('op365_ProjectId', 'op365_code'),
                                'ProjectIQProjectName': ('op365_ProjectId', 'op365_name'),
                                'ProjectIQCustomer': ('op365_ProjectId', 'op365_CustomerId', 'name'),
                                MANAGER: ('op365_ProjectId', 'op365_ProjectManagerId', 'internalemailaddress'),
                            }),
    'op365_supplierdocument': ('op365_supplierdocuments', 'Supplier Document', 'op365_description',
                               'op365_SupplierId($select=name)', {
                                   'ProjectIQSupplier': ('op365_SupplierId', 'name'),
                               }),
}


def library_columns(library):
    """Columns of a library: record type and id, then the ones filled from the record."""
    return ['ProjectIQRecordType', 'ProjectIQRecordId', *RECORDS[library][4]]


def record_values(library, record):
    """Column values of a record read with the $select/$expand of RECORDS (Python twin of the flow expressions)."""
    values = {}
    for column, path in RECORDS[library][4].items():
        value = record
        for key in path:
            value = (value or {}).get(key)
        values[column] = value
    return values


def _value(path):
    return "body('Get_record')" + ''.join(f"?['{key}']" for key in path)


# record folder (second segment of the file path) -> last 32 characters -> record id
FOLDER = "last(take(split(triggerOutputs()?['body/{Path}'], '/'), 2))"
HEX = f"if(greaterOrEquals(length({FOLDER}), 32), toLower(substring({FOLDER}, sub(length({FOLDER}), 32), 32)), '')"


def metadata_flow(library):
    entity_set, record_type, select, expand, paths = RECORDS[library]
    manager = _value(paths[MANAGER]) if MANAGER in paths else None
    variable = LIBRARIES[library]
    table = f"@parameters('{parameter(variable)}')"
    poll = _op('shared_sharepointonline', 'GetOnNewFileItems', {'dataset': _site(), 'table': table})
    del poll['runAfter']
    trigger = {'When_a_file_is_created_(properties_only)': {
        'recurrence': {'interval': 3, 'frequency': 'Minute'}, 'splitOn': "@triggerOutputs()?['body/value']", **poll}}
    hex_id = "outputs('Record_folder_id')"
    record_id = (f"concat(substring({hex_id}, 0, 8), '-', substring({hex_id}, 8, 4), '-', substring({hex_id}, 12, 4), '-', "
                 f"substring({hex_id}, 16, 4), '-', substring({hex_id}, 20, 12))")
    item = {'dataset': _site(), 'table': table, 'id': "@triggerOutputs()?['body/ID']",
            'item/ProjectIQRecordType/Value': record_type, 'item/ProjectIQRecordId': f'@{record_id}'}
    item.update({f'item/{column}': '@' + _value(path) for column, path in paths.items() if column != MANAGER})
    tag = {'Get_record': _op('shared_commondataserviceforapps', 'GetItem', {
        'entityName': entity_set, 'recordId': f'@{record_id}', '$select': select, '$expand': expand}),
        'Set_ProjectIQ_columns': _op('shared_sharepointonline', 'PatchFileItem', item, {'Get_record': ['Succeeded']}),
        'Record_not_found': {'runAfter': {'Get_record': ['Failed']}, 'type': 'Terminate',
                             'inputs': {'runStatus': 'Succeeded'}}}
    if manager:
        tag['Has_project_manager'] = {
            'runAfter': {'Set_ProjectIQ_columns': ['Succeeded']}, 'type': 'If',
            'expression': {'not': {'equals': [f'@coalesce({manager}, \'\')', '']}},
            'actions': {'Set_project_manager': _op('shared_sharepointonline', 'PatchFileItem', {
                'dataset': _site(), 'table': table, 'id': "@triggerOutputs()?['body/ID']",
                'item/ProjectIQProjectManager/Claims': f"@concat('i:0#.f|membership|', {manager})"})},
            'else': {'actions': {}}}
    actions = {
        'Record_folder_id': {'runAfter': {}, 'type': 'Compose', 'inputs': f'@{HEX}'},
        'In_a_record_folder': {'runAfter': {'Record_folder_id': ['Succeeded']}, 'type': 'If',
                               'expression': {'equals': [f'@length({hex_id})', 32]},
                               'actions': tag, 'else': {'actions': {}}},
    }
    return clientdata(trigger, actions, ('shared_commondataserviceforapps', 'shared_sharepointonline'),
                      (SITE, variable))


# (id, name, description, clientdata, state code, localized names {lcid: (name, description)})
FLOWS = [
    ('a58865cd-fbcf-f111-a05b-000d3ad895be', 'Daily time reminder',
     'Working days at 17:30 (Europe/Rome): reminds the users who recorded fewer hours than expected today',
     clientdata({'Recurrence': {'type': 'Recurrence', 'recurrence': {
         'frequency': 'Week', 'interval': 1, 'timeZone': 'W. Europe Standard Time',
         'schedule': {'weekDays': WEEKDAYS, 'hours': ['17'], 'minutes': [30]}}}},
         {'Send_time_reminders': unbound_action('op365_SendTimeReminders')}), 1, None),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a04', 'Daily document expiry',
     'Every day at 06:00 (Europe/Rome): expiry status of the supplier documents, supplier alert counters and expiry e-mails',
     clientdata({'Recurrence': {'type': 'Recurrence', 'recurrence': {
         'frequency': 'Day', 'interval': 1, 'timeZone': 'W. Europe Standard Time',
         'schedule': {'hours': ['6'], 'minutes': [0]}}}},
         {'Update_document_expiry': unbound_action('op365_UpdateDocumentExpiry')}), 0, {
         1031: ('Tägliche Dokumentenfälligkeit', 'Täglich um 06:00: Ablaufstatus der Lieferantendokumente, Zähler und Ablauf-E-Mails'),
         1033: ('Daily document expiry', 'Every day at 06:00 (Europe/Rome): expiry status of the supplier documents, supplier alert counters and expiry e-mails'),
         1036: ('Échéance quotidienne des documents', 'Chaque jour à 06:00 : statut d\'expiration des documents fournisseur, compteurs et e-mails d\'expiration'),
         1040: ('Scadenza giornaliera documenti', 'Ogni giorno alle 06:00: stato di scadenza dei documenti fornitore, contatori ed e-mail di scadenza')}),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a01', 'Tag project documents',
     'Fills the ProjectIQ columns of the files added to the folder of a project',
     metadata_flow('op365_project'), 0, {
         1031: ('Projektdokumente kennzeichnen', 'Füllt die ProjectIQ-Spalten der Dateien im Ordner eines Projekts'),
         1033: ('Tag project documents', 'Fills the ProjectIQ columns of the files added to the folder of a project'),
         1036: ('Étiqueter les documents de projet', 'Renseigne les colonnes ProjectIQ des fichiers ajoutés au dossier d\'un projet'),
         1040: ('Classifica documenti commessa', 'Compila le colonne ProjectIQ dei file aggiunti alla cartella di una commessa')}),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a02', 'Tag purchase order documents',
     'Fills the ProjectIQ columns of the files added to the folder of a purchase order',
     metadata_flow('op365_purchaseorder'), 0, {
         1031: ('Bestelldokumente kennzeichnen', 'Füllt die ProjectIQ-Spalten der Dateien im Ordner einer Bestellung'),
         1033: ('Tag purchase order documents', 'Fills the ProjectIQ columns of the files added to the folder of a purchase order'),
         1036: ('Étiqueter les documents de commande', 'Renseigne les colonnes ProjectIQ des fichiers ajoutés au dossier d\'une commande'),
         1040: ('Classifica documenti ordine', 'Compila le colonne ProjectIQ dei file aggiunti alla cartella di un ordine di acquisto')}),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a03', 'Tag supplier documents',
     'Fills the ProjectIQ columns of the files added to the folder of a supplier document',
     metadata_flow('op365_supplierdocument'), 0, {
         1031: ('Lieferantendokumente kennzeichnen', 'Füllt die ProjectIQ-Spalten der Dateien im Ordner eines Lieferantendokuments'),
         1033: ('Tag supplier documents', 'Fills the ProjectIQ columns of the files added to the folder of a supplier document'),
         1036: ('Étiqueter les documents fournisseur', 'Renseigne les colonnes ProjectIQ des fichiers ajoutés au dossier d\'un document fournisseur'),
         1040: ('Classifica documenti fornitore', 'Compila le colonne ProjectIQ dei file aggiunti alla cartella di un documento fornitore')}),
]


if __name__ == '__main__':
    print(json.dumps([f[1] for f in FLOWS]))
