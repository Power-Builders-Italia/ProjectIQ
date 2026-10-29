import { listUrl, normaliseEnvironmentUrl, recordUrl } from './settings';

describe('settings', () => {
  it('accepts only Dataverse environment URLs', () => {
    expect(normaliseEnvironmentUrl(' https://Contoso.crm4.dynamics.com/main.aspx ')).toBe('https://contoso.crm4.dynamics.com');
    expect(normaliseEnvironmentUrl('https://evil.example.com')).toBeUndefined();
    expect(normaliseEnvironmentUrl('http://contoso.crm.dynamics.com')).toBeUndefined();
  });
  it('builds app links with or without app id', () => {
    expect(recordUrl({ environmentUrl: 'https://o.crm.dynamics.com', appId: 'a1' }, 'op365_project', 'p1'))
      .toBe('https://o.crm.dynamics.com/main.aspx?appid=a1&pagetype=entityrecord&etn=op365_project&id=p1');
    expect(listUrl({ environmentUrl: 'https://o.crm.dynamics.com' }, 'op365_timeentry'))
      .toBe('https://o.crm.dynamics.com/main.aspx?pagetype=entitylist&etn=op365_timeentry');
  });
});
