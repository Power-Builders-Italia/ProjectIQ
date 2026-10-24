import os, requests
ENV=os.environ['PAC_ENVIRONMENT_URL'].rstrip('/')
def token():
    r=requests.post(f"https://login.microsoftonline.com/{os.environ['PAC_TENANT_ID']}/oauth2/v2.0/token",data={
        'grant_type':'client_credentials','client_id':os.environ['PAC_CLIENT_ID'],
        'client_secret':os.environ['PAC_CLIENT_SECRET'],'scope':ENV+'/.default'})
    r.raise_for_status(); return r.json()['access_token']
S=requests.Session()
S.headers.update({'Authorization':'Bearer '+token(),'OData-MaxVersion':'4.0','OData-Version':'4.0',
  'Accept':'application/json','Content-Type':'application/json; charset=utf-8',
  'MSCRM.SolutionUniqueName':'OpenProject365'})
API=ENV+'/api/data/v9.2/'
