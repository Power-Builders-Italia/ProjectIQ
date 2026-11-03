"""Definitions of the cloud flows of the solution, shared by flows.py (creates them in an environment) and the solution
source in solutions/OpenProject365/src/Workflows (same clientdata).

Document metadata flows (docs/en/documents.md): one per document library. A file created in the folder of a record
(<name>_<record id without hyphens>, the Dataverse and Portfolio Agent convention) gets the ProjectIQ columns of that
record; files outside a record folder, or in the folder of a deleted record, are left as they are.
"""
import json

DATAVERSE = '/providers/Microsoft.PowerApps/apis/shared_commondataserviceforapps'
SHAREPOINT = '/providers/Microsoft.PowerApps/apis/shared_sharepointonline'
TEAMS = '/providers/Microsoft.PowerApps/apis/shared_teams'
CONNECTORS = {'shared_commondataserviceforapps': ('op365_dataverse', DATAVERSE),
              'shared_sharepointonline': ('op365_sharepoint', SHAREPOINT),
              'shared_teams': ('op365_teams', TEAMS)}
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# environment variables: (schema name, display name, description); values are set per environment, never in the repository
SITE = ('op365_SharePointSiteUrl', 'SharePoint Site URL',
        'URL of the SharePoint site of the ProjectIQ document libraries (the default site of Document Management).')
# Teams team id and channel id (separated by |) of the agent proposal approval card; same definition as settings_env.py
APPROVAL_TEAM = ('op365_SourcingApprovalTeam', 'Sourcing Approval Team', 'Teams team id and channel id separated by |')
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


def bound_action(action, entity_set, record_id, parameters=None, run_after=None):
    """Dataverse action bound to a row (PerformBoundAction), e.g. op365_DecideAgentProposal on an op365_agentproposal."""
    params = {'entityName': entity_set, 'recordId': record_id, 'actionName': action}
    params.update({f'item/{k}': v for k, v in (parameters or {}).items()})
    return {'runAfter': run_after or {}, 'type': 'OpenApiConnection', 'inputs': {
        'host': {'connectionName': 'shared_commondataserviceforapps', 'operationId': 'PerformBoundAction',
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


def file_approved_flow():
    """Approved supplier document: its op365_file goes to the SharePoint folder of the record, then leaves Dataverse."""
    library = 'op365_supplierdocument'
    doc = "triggerOutputs()?['body/op365_supplierdocumentid']"
    trigger = {'When_a_supplier_document_is_approved': {
        'type': 'OpenApiConnectionWebhook', 'inputs': {
            'host': {'connectionName': 'shared_commondataserviceforapps', 'operationId': 'SubscribeWebhookTrigger',
                     'apiId': DATAVERSE},
            'parameters': {'subscriptionRequest/message': 3, 'subscriptionRequest/entityname': library,
                           'subscriptionRequest/scope': 4, 'subscriptionRequest/filteringattributes': 'statuscode',
                           'subscriptionRequest/filterexpression': 'statuscode eq 1'},
            'authentication': "@parameters('$authentication')"}}}
    name = "coalesce(body('Get_document')?['op365_description'], 'Document')"
    for ch in '~"#%&*:<>?/\\{|}':
        name = f"replace({name}, '{ch}', '')"
    new_folder = f"concat(trim(substring({name}, 0, min(length({name}), 80))), '_', toUpper(replace({doc}, '-', '')))"
    found = "body('Find_record_folder')?['value']"
    path = "body('Create_SharePoint_file')?['Path']"
    enc = f"replace(replace(replace({path}, '%', '%25'), ' ', '%20'), '#', '%23')"
    has_file = {
        'Download_file': _op('shared_commondataserviceforapps', 'GetEntityFileImageFieldContent', {
            'entityName': 'op365_supplierdocuments', 'recordId': f'@{doc}', 'fileImageFieldName': 'op365_file'}),
        'Find_record_folder': _op('shared_commondataserviceforapps', 'ListRecords', {
            'entityName': 'sharepointdocumentlocations', '$select': 'relativeurl',
            '$filter': f"@concat('_regardingobjectid_value eq ', {doc})", '$top': 1}, {'Download_file': ['Succeeded']}),
        'Record_folder': {'runAfter': {'Find_record_folder': ['Succeeded']}, 'type': 'Compose',
                          'inputs': f"@if(empty({found}), {new_folder}, first({found})?['relativeurl'])"},
        'Folder_registered': {
            'runAfter': {'Record_folder': ['Succeeded']}, 'type': 'If',
            'expression': {'equals': [f'@empty({found})', False]},
            'actions': {}, 'else': {'actions': {
                'Find_library': _op('shared_commondataserviceforapps', 'ListRecords', {
                    'entityName': 'sharepointdocumentlocations', '$select': 'sharepointdocumentlocationid',
                    '$filter': f"relativeurl eq '{library}' and _regardingobjectid_value eq null", '$top': 1}),
                # The library location exists once Document Management is on for the table; otherwise it is created
                # under the default SharePoint site.
                'Library_registered': {
                    'runAfter': {'Find_library': ['Succeeded']}, 'type': 'If',
                    'expression': {'equals': [f"@empty(body('Find_library')?['value'])", False]},
                    'actions': {'Use_library': {'runAfter': {}, 'type': 'SetVariable', 'inputs': {
                        'name': 'LibraryLocation', 'value': f"@{{first(body('Find_library')?['value'])?['sharepointdocumentlocationid']}}"}}},
                    'else': {'actions': {
                        'Find_default_site': _op('shared_commondataserviceforapps', 'ListRecords', {
                            'entityName': 'sharepointsites', '$select': 'sharepointsiteid',
                            '$filter': 'isdefault eq true and statecode eq 0', '$top': 1}),
                        'Register_library': _op('shared_commondataserviceforapps', 'CreateRecord', {
                            'entityName': 'sharepointdocumentlocations',
                            'item/name': 'Supplier Documents', 'item/relativeurl': library,
                            'item/parentsiteorlocation_sharepointsite@odata.bind':
                                "@concat('sharepointsites(', first(body('Find_default_site')?['value'])?['sharepointsiteid'], ')')"},
                            {'Find_default_site': ['Succeeded']}),
                        'Use_new_library': {'runAfter': {'Register_library': ['Succeeded']}, 'type': 'SetVariable',
                                            'inputs': {'name': 'LibraryLocation',
                                                       'value': "@{body('Register_library')?['sharepointdocumentlocationid']}"}}}}},
                'Register_record_folder': _op('shared_commondataserviceforapps', 'CreateRecord', {
                    'entityName': 'sharepointdocumentlocations',
                    'item/name': "@concat('Documents on ', outputs('Record_folder'))",
                    'item/relativeurl': "@outputs('Record_folder')",
                    'item/parentsiteorlocation_sharepointdocumentlocation@odata.bind':
                        "@concat('sharepointdocumentlocations(', variables('LibraryLocation'), ')')",
                    'item/regardingobjectid_op365_supplierdocument@odata.bind': f"@concat('op365_supplierdocuments(', {doc}, ')')"},
                    {'Library_registered': ['Succeeded']})}}},
        'Create_SharePoint_file': _op('shared_sharepointonline', 'CreateFile', {
            'dataset': _site(), 'folderPath': f"@concat('/{library}/', outputs('Record_folder'))",
            'name': "@body('Get_document')?['op365_file_name']", 'body': "@body('Download_file')"},
            {'Folder_registered': ['Succeeded']}),
        # link to the file (Path is relative to the site), shown on the form once the file left Dataverse
        'Set_SharePoint_URL': _op('shared_commondataserviceforapps', 'UpdateRecord', {
            'entityName': 'op365_supplierdocuments', 'recordId': f'@{doc}',
            'item/op365_sharepointurl': f"@replace(replace(concat({_site()[1:]}, '|', {enc}), '/|', ''), '|', '')"},
            {'Create_SharePoint_file': ['Succeeded']}),
        'Remove_Dataverse_file': dict(unbound_action('DeleteFile', {'FileId': "@body('Get_document')?['op365_file']"}),
                                      runAfter={'Set_SharePoint_URL': ['Succeeded']}),
    }
    actions = {
        'Library_location': {'runAfter': {}, 'type': 'InitializeVariable',
                             'inputs': {'variables': [{'name': 'LibraryLocation', 'type': 'string', 'value': ''}]}},
        'Get_document': _op('shared_commondataserviceforapps', 'GetItem', {
            'entityName': 'op365_supplierdocuments', 'recordId': f'@{doc}',
            '$select': 'op365_description,op365_file,op365_file_name'}, {'Library_location': ['Succeeded']}),
        'Has_file': {'runAfter': {'Get_document': ['Succeeded']}, 'type': 'If',
                     'expression': {'not': {'equals': ["@coalesce(body('Get_document')?['op365_file_name'], '')", '']}},
                     'actions': has_file, 'else': {'actions': {}}},
    }
    return clientdata(trigger, actions, ('shared_commondataserviceforapps', 'shared_sharepointonline'), (SITE,))


def proposal_approval_flow():
    """Agent proposal added: adaptive card to the approval channel, wait for the answer, decide the proposal.

    The card is posted whether or not the sourcing agent is enabled (open proposals stay decidable). The in-app
    notification to the project managers is not here: the AgentProposalNotify plugin sends it. A Reject without a note
    reaches op365_DecideAgentProposal on purpose: the API answers "Add a note to reject the proposal." and the flow shows
    it in the channel; only a failed Approve is written on the proposal (op365_RecordProposalError).
    """
    pid = "triggerOutputs()?['body/op365_agentproposalid']"
    team = f"outputs('Team_and_channel')"
    answer = "body('Post_approval_card')"
    fact = lambda title, value: {'title': title, 'value': value}
    card = {
        '$schema': 'http://adaptivecards.io/schemas/adaptive-card.json', 'type': 'AdaptiveCard', 'version': '1.4',
        'body': [
            {'type': 'TextBlock', 'text': 'Agent proposal', 'weight': 'Bolder', 'size': 'Medium'},
            {'type': 'TextBlock', 'text': "@{outputs('Get_proposal')?['body/op365_name']}", 'wrap': True, 'weight': 'Bolder'},
            {'type': 'FactSet', 'facts': [
                fact('Action type', "@{coalesce(outputs('Get_proposal')?['body/op365_actiontype@OData.Community.Display.V1.FormattedValue'], '')}"),
                fact('Project', "@{coalesce(outputs('Get_proposal')?['body/op365_ProjectId/op365_name'], '')}"),
                fact('Supplier', "@{coalesce(outputs('Get_proposal')?['body/op365_SupplierId/name'], '')}"),
                fact('Amount', "@{coalesce(outputs('Get_proposal')?['body/op365_amount'], '')}")]},
            {'type': 'TextBlock', 'text': "@{coalesce(outputs('Get_proposal')?['body/op365_rationale'], '')}", 'wrap': True},
            {'type': 'TextBlock', 'text': "[Open the proposal in ProjectIQ](@{outputs('Record_link')})", 'wrap': True},
            {'type': 'Input.Text', 'id': 'Note', 'isMultiline': True,
             'label': 'Note (required to reject)', 'placeholder': 'Reason for the decision'}],
        'actions': [{'type': 'Action.Submit', 'title': 'Approve', 'style': 'positive', 'data': {'Decision': 'Approve'}},
                    {'type': 'Action.Submit', 'title': 'Reject', 'style': 'destructive', 'data': {'Decision': 'Reject'}}]}
    trigger = {'When_an_agent_proposal_is_added': {
        'type': 'OpenApiConnectionWebhook', 'inputs': {
            'host': {'connectionName': 'shared_commondataserviceforapps', 'operationId': 'SubscribeWebhookTrigger',
                     'apiId': DATAVERSE},
            'parameters': {'subscriptionRequest/message': 1, 'subscriptionRequest/entityname': 'op365_agentproposal',
                           'subscriptionRequest/scope': 4, 'subscriptionRequest/filterexpression': 'op365_kind eq 365000000'},
            'authentication': "@parameters('$authentication')"}}}
    channel = {'poster': 'Flow bot', 'location': 'Channel', 'body/recipient/groupId': f'@first({team})',
               'body/recipient/channelId': f'@last({team})'}
    decide_error = "coalesce(body('Decide_proposal')?['error']?['message'], 'The decision could not be recorded.')"
    actions = {
        'Team_and_channel': {'runAfter': {}, 'type': 'Compose',
                             'inputs': f"@split(parameters('{parameter(APPROVAL_TEAM)}'), '|')"},
        'Get_proposal': _op('shared_commondataserviceforapps', 'GetItem', {
            'entityName': 'op365_agentproposals', 'recordId': f'@{pid}',
            '$select': 'op365_name,op365_actiontype,op365_amount,op365_rationale',
            '$expand': 'op365_ProjectId($select=op365_name),op365_SupplierId($select=name)'},
            {'Team_and_channel': ['Succeeded']}),
        # organisation URL = the part of the row URL before /api/data
        'Record_link': {'runAfter': {'Get_proposal': ['Succeeded']}, 'type': 'Compose', 'inputs': (
            f"@concat(first(split(triggerOutputs()?['body/@odata.id'], '/api/data')), "
            f"'/main.aspx?pagetype=entityrecord&etn=op365_agentproposal&id=', {pid})")},
        'Card': {'runAfter': {'Record_link': ['Succeeded']}, 'type': 'Compose', 'inputs': card},
        'Post_approval_card': _op('shared_teams', 'PostCardAndWaitForResponse', {
            **channel, 'body/messageBody': "@string(outputs('Card'))", 'body/shouldUpdateCard': True,
            'body/updateMessage': 'Response received: the decision is being recorded.'}, {'Card': ['Succeeded']}),
        'Decide_proposal': bound_action('op365_DecideAgentProposal', 'op365_agentproposals', f'@{pid}', {
            'Approve': f"@equals({answer}?['data']?['Decision'], 'Approve')",
            'Note': f"@coalesce({answer}?['data']?['Note'], '')",
            'DecidedBy': f"@{answer}?['responder']?['email']"}, {'Post_approval_card': ['Succeeded']}),
        'Failed_approval': {
            'runAfter': {'Decide_proposal': ['Failed']}, 'type': 'If',
            'expression': {'equals': [f"@{answer}?['data']?['Decision']", 'Approve']},
            'actions': {'Record_error': _op('shared_commondataserviceforapps', 'PerformUnboundAction', {
                'actionName': 'op365_RecordProposalError', 'item/ProposalId': f'@{pid}',
                'item/Error': f'@{decide_error}'})},
            'else': {'actions': {}}},
        'Post_decision_failed': _op('shared_teams', 'PostMessageToConversation', {
            **channel, 'body/messageBody': (
                f"@concat('Proposal \"', outputs('Get_proposal')?['body/op365_name'], '\" not decided: ', {decide_error})")},
            {'Failed_approval': ['Succeeded', 'Skipped', 'Failed']}),
        'Post_decision_recorded': _op('shared_teams', 'PostMessageToConversation', {
            **channel, 'body/messageBody': (
                f"@concat('Proposal \"', outputs('Get_proposal')?['body/op365_name'], '\" ', "
                f"if(equals({answer}?['data']?['Decision'], 'Approve'), 'approved', 'rejected'), ' by ', "
                f"{answer}?['responder']?['email'], '.')")}, {'Decide_proposal': ['Succeeded']}),
    }
    return clientdata(trigger, actions, ('shared_commondataserviceforapps', 'shared_teams'), (APPROVAL_TEAM,))


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
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a05', 'File approved supplier documents',
     'When a supplier document is approved, moves its file to the SharePoint folder of the document',
     file_approved_flow(), 0, {
         1031: ('Genehmigte Lieferantendokumente ablegen', 'Verschiebt bei der Genehmigung eines Lieferantendokuments die Datei in seinen SharePoint-Ordner'),
         1033: ('File approved supplier documents', 'When a supplier document is approved, moves its file to the SharePoint folder of the document'),
         1036: ('Classer les documents fournisseur approuvés', 'À l\'approbation d\'un document fournisseur, déplace son fichier dans son dossier SharePoint'),
         1040: ('Archivia documenti fornitore approvati', 'All\'approvazione di un documento fornitore sposta il file nella sua cartella SharePoint')}),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a06', 'Agent proposal approval',
     'When the sourcing agent adds a proposal, posts an approval card (Approve / Reject with a note) in the Teams channel of Sourcing Approval Team and records the decision',
     proposal_approval_flow(), 0, {
         1031: ('Genehmigung von Agentenvorschlägen', 'Postet bei einem neuen Vorschlag des Beschaffungsagenten eine Genehmigungskarte im Teams-Kanal und erfasst die Entscheidung'),
         1033: ('Agent proposal approval', 'When the sourcing agent adds a proposal, posts an approval card (Approve / Reject with a note) in the Teams channel of Sourcing Approval Team and records the decision'),
         1036: ('Approbation des propositions de l\'agent', 'À chaque proposition de l\'agent achats, publie une carte d\'approbation dans le canal Teams et enregistre la décision'),
         1040: ('Approvazione proposte agente', 'Quando l\'agente acquisti aggiunge una proposta, pubblica una scheda di approvazione nel canale Teams e registra la decisione')}),
    ('3c6f1d2a-8b1e-4f57-9a43-5d2b7e0c1a07', 'Daily agent proposal expiry',
     'Every day at 06:30 (Europe/Rome): expires the pending agent proposals past their Expires On date',
     clientdata({'Recurrence': {'type': 'Recurrence', 'recurrence': {
         'frequency': 'Day', 'interval': 1, 'timeZone': 'W. Europe Standard Time',
         'schedule': {'hours': ['6'], 'minutes': [30]}}}},
         {'Expire_agent_proposals': unbound_action('op365_ExpireAgentProposals')}), 0, {
         1031: ('Tägliches Ablaufen von Agentenvorschlägen', 'Täglich um 06:30: lässt offene Agentenvorschläge nach ihrem Ablaufdatum verfallen'),
         1033: ('Daily agent proposal expiry', 'Every day at 06:30 (Europe/Rome): expires the pending agent proposals past their Expires On date'),
         1036: ('Expiration quotidienne des propositions de l\'agent', 'Chaque jour à 06:30 : fait expirer les propositions de l\'agent en attente après leur date d\'expiration'),
         1040: ('Scadenza giornaliera proposte agente', 'Ogni giorno alle 06:30: fa scadere le proposte dell\'agente in sospeso oltre la data di scadenza')}),
]


if __name__ == '__main__':
    print(json.dumps([f[1] for f in FLOWS]))
