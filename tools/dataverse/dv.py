import os, requests
def env_url(value):
    # pac accepts the environment URL without scheme or with spaces; the token scope needs https://<host>
    value=value.strip().rstrip('/')
    return value if value.lower().startswith('https://') else 'https://'+value.split('://')[-1]
ENV=env_url(os.environ['PAC_ENVIRONMENT_URL'])
def token():
    r=requests.post(f"https://login.microsoftonline.com/{os.environ['PAC_TENANT_ID'].strip()}/oauth2/v2.0/token",data={
        'grant_type':'client_credentials','client_id':os.environ['PAC_CLIENT_ID'].strip(),
        'client_secret':os.environ['PAC_CLIENT_SECRET'].strip(),'scope':ENV+'/.default'})
    if not r.ok:
        # the Entra error (AADSTS code and description) names the cause; it holds no secret
        try: e=r.json(); detail=f"{e.get('error')}: {(e.get('error_description') or '').split(chr(10))[0]}"
        except ValueError: detail=r.text[:300]
        raise SystemExit(f"Token request failed ({r.status_code}): {detail}")
    return r.json()['access_token']
S=requests.Session()
S.headers.update({'Authorization':'Bearer '+token(),'OData-MaxVersion':'4.0','OData-Version':'4.0',
  'Accept':'application/json','Content-Type':'application/json; charset=utf-8',
  'MSCRM.SolutionUniqueName':'OpenProject365'})
API=ENV+'/api/data/v9.2/'
