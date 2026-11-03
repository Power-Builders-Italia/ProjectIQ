import os, re, requests
def env_url(value):
    # pac accepts the environment URL without scheme or with spaces; the token scope needs https://<host>
    value=value.strip().rstrip('/')
    return value if value.lower().startswith('https://') else 'https://'+value.split('://')[-1]
ENV=env_url(os.environ['PAC_ENVIRONMENT_URL'])
def tenant():
    # the environment names its own tenant in the 401 challenge; PAC_TENANT_ID is only the fallback
    try:
        h=requests.get(ENV+'/api/data/v9.2/',headers={'Authorization':'Bearer'},timeout=30).headers.get('WWW-Authenticate','')
        m=re.search(r'login\.microsoftonline\.com/([0-9a-fA-F-]{36})/',h)
        if m: return m.group(1)
    except requests.RequestException: pass
    return os.environ['PAC_TENANT_ID'].strip()
def token():
    r=requests.post(f"https://login.microsoftonline.com/{tenant()}/oauth2/v2.0/token",data={
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
