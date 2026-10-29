import { DataverseClient, DataverseError, formatted, type HttpSend, type IHttpResult } from './DataverseClient';

const reply = (status: number, body: unknown): IHttpResult => ({
  ok: status < 400, status, statusText: status < 400 ? 'OK' : 'Error', text: async () => JSON.stringify(body),
});

describe('DataverseClient', () => {
  it('follows nextLink and asks for formatted values', async () => {
    const calls: { url: string; headers: Record<string, string> }[] = [];
    const send: HttpSend = async (_m, url, headers) => {
      calls.push({ url, headers });
      return url.indexOf('page2') >= 0 ? reply(200, { value: [{ id: 2 }] }) : reply(200, { value: [{ id: 1 }], '@odata.nextLink': 'https://org.crm4.dynamics.com/api/data/v9.2/x?page2' });
    };
    const rows = await new DataverseClient('https://org.crm4.dynamics.com/', send).all('op365_projects', '$select=op365_name');
    expect(rows).toEqual([{ id: 1 }, { id: 2 }]);
    expect(calls[0].url).toBe('https://org.crm4.dynamics.com/api/data/v9.2/op365_projects?$select=op365_name');
    expect(calls[0].headers.Prefer).toContain('OData.Community.Display.V1.FormattedValue');
  });

  it('raises the Dataverse error message', async () => {
    const send: HttpSend = async () => reply(400, { error: { message: 'Only draft or rejected time entries can be submitted.' } });
    await expect(new DataverseClient('https://org.crm4.dynamics.com', send).action('op365_SubmitTimeEntries', { TimeEntryIds: ['x'] }))
      .rejects.toEqual(new DataverseError('Only draft or rejected time entries can be submitted.', 400));
  });

  it('reads formatted values', () => {
    expect(formatted({ '_x_value@OData.Community.Display.V1.FormattedValue': 'Rossi' }, '_x_value')).toBe('Rossi');
  });
});
