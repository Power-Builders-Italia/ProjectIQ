import { DataverseClient, type HttpSend } from './DataverseClient';
import { NoDocumentLibraryError, ProjectIQService } from './ProjectIQService';
import { SharePointClient } from './SharePointClient';

function fake(routes: Record<string, unknown>): { send: HttpSend; posts: { url: string; body?: string }[] } {
  const posts: { url: string; body?: string }[] = [];
  const send: HttpSend = async (method, url, _h, body) => {
    if (method === 'POST') posts.push({ url, body: typeof body === 'string' ? body : undefined });
    const key = Object.keys(routes).find(k => url.indexOf(k) >= 0);
    const value = key ? routes[key] : { value: [] };
    return { ok: true, status: 200, statusText: 'OK', text: async () => JSON.stringify(value) };
  };
  return { send, posts };
}

const ENV = 'https://org.crm4.dynamics.com';

describe('ProjectIQService', () => {
  it('finds the user and their resource', async () => {
    const { send } = fake({ WhoAmI: { UserId: '{AAA}' }, op365_resources: { value: [{ op365_resourceid: 'r1', op365_name: 'Mario Rossi', op365_weeklyhours: 36 }] } });
    expect(await new ProjectIQService(new DataverseClient(ENV, send)).me()).toEqual({ userId: 'aaa', resourceId: 'r1', resourceName: 'Mario Rossi', weeklyHours: 36 });
  });

  it('keeps only the hours of the projects the user manages', async () => {
    const { send } = fake({
      WhoAmI: { UserId: 'u1' },
      'op365_timeentries': { value: [
        { op365_timeentryid: 't1', _op365_projectid_value: 'p1', op365_entrydate: '1970-01-05', op365_hours: 8 },
        { op365_timeentryid: 't2', _op365_projectid_value: 'p2', op365_entrydate: '1970-01-05', op365_hours: 8 },
      ] },
      'op365_projects?$select=op365_projectid&': { value: [{ op365_projectid: 'p1' }] },
    });
    const pending = await new ProjectIQService(new DataverseClient(ENV, send)).pendingTime();
    expect(pending.map(p => p.id)).toEqual(['t1']);
    expect(pending[0].day).toBe(4);
  });

  it('creates a draft entry and submits through the Custom API', async () => {
    const { send, posts } = fake({ 'op365_timeentries?$select': { op365_timeentryid: 'new1' }, op365_SubmitTimeEntries: { Count: 2 } });
    const service = new ProjectIQService(new DataverseClient(ENV, send));
    expect(await service.createEntry('{P1}', 'n1', 4, 7.5)).toBe('new1');
    expect(await service.submitEntries(['new1', 'old'])).toBe(2);
    expect(JSON.parse(posts[0].body!)).toEqual({
      'op365_ProjectId@odata.bind': '/op365_projects(p1)', op365_entrydate: '1970-01-05', op365_hours: 7.5, 'op365_WbsNodeId@odata.bind': '/op365_wbsnodes(n1)',
    });
    expect(posts[1].url).toBe(`${ENV}/api/data/v9.2/op365_SubmitTimeEntries`);
  });

  it('sends the rejection note to op365_DecideTimeEntries', async () => {
    const { send, posts } = fake({ op365_DecideTimeEntries: { Count: 1 } });
    await new ProjectIQService(new DataverseClient(ENV, send)).decideEntries(['t1'], false, 'Wrong task');
    expect(JSON.parse(posts[0].body!)).toEqual({ TimeEntryIds: ['t1'], Approve: false, Note: 'Wrong task' });
  });

  it('lists the SharePoint folder of a project from its document location', async () => {
    const { send } = fake({ sharepointdocumentlocations: { value: [{
      name: 'Documents on ProjectIQ 1', relativeurl: 'PRJ-000123_ABC',
      parentsiteorlocation_sharepointdocumentlocation: {
        relativeurl: 'op365_project', parentsiteorlocation_sharepointsite: { absoluteurl: 'https://contoso.sharepoint.com/sites/ProjectIQ' },
      },
    }] } });
    const urls: string[] = [];
    const sp = new SharePointClient(async (_m, url) => {
      urls.push(url);
      return { ok: true, status: 200, statusText: 'OK', text: async () => JSON.stringify({
        Files: [{ Name: 'Contratto.docx', ServerRelativeUrl: '/sites/ProjectIQ/op365_project/PRJ-000123_ABC/Contratto.docx', Length: '2048',
          TimeLastModified: '1970-01-05T10:00:00Z', ModifiedBy: { Title: 'Anna Bianchi' } }],
        Folders: [{ Name: 'Forms', ServerRelativeUrl: '/x/Forms', ItemCount: 0 }],
      }) };
    });
    const folders = await new ProjectIQService(new DataverseClient(ENV, send), sp).documents('{P1}');
    expect(urls[0]).toBe("https://contoso.sharepoint.com/sites/ProjectIQ/_api/web/GetFolderByServerRelativePath(decodedurl=@p)"
      + "?@p='%2Fsites%2FProjectIQ%2Fop365_project%2FPRJ-000123_ABC'&$expand=Files/ModifiedBy,Folders&$select=Files/Name,Files/ServerRelativeUrl,"
      + 'Files/Length,Files/TimeLastModified,Files/ModifiedBy/Title,Folders/Name,Folders/ServerRelativeUrl,Folders/TimeLastModified,Folders/ItemCount');
    expect(folders).toEqual([{
      name: 'Documents on ProjectIQ 1', url: 'https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-000123_ABC', exists: true,
      items: [{ name: 'Contratto.docx', url: 'https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-000123_ABC/Contratto.docx?web=1',
        folder: false, modified: 4, modifiedBy: 'Anna Bianchi', size: 2048 }],
    }]);
  });

  it('reports a folder not created in SharePoint yet', async () => {
    const { send } = fake({ sharepointdocumentlocations: { value: [{ name: 'D', relativeurl: 'f', absoluteurl: 'https://contoso.sharepoint.com/teams/pm/lib/f/' }] } });
    const webs: string[] = [];
    const sp = new SharePointClient(async (_m, url) => {
      webs.push(url.split('/_api/')[0]);
      return { ok: false, status: 404, statusText: 'Not Found', text: async () => '' };
    });
    const folders = await new ProjectIQService(new DataverseClient(ENV, send), sp).documents('p1');
    expect(webs).toEqual(['https://contoso.sharepoint.com/teams/pm']);
    expect(folders).toEqual([{ name: 'D', url: 'https://contoso.sharepoint.com/teams/pm/lib/f', exists: false, items: [] }]);
  });

  it('creates a draft project in status Offer and its WBS nodes under their parents', async () => {
    const { send, posts } = fake({
      'op365_projects?$select': { op365_projectid: 'p9' }, 'op365_projects(p9)': { op365_code: 'PRJ-000124' }, 'op365_wbsnodes?$select': { op365_wbsnodeid: 'n2' },
    });
    const service = new ProjectIQService(new DataverseClient(ENV, send));
    const created = await service.createProject({
      name: 'Warehouse', customerId: '{A1}', managerId: 'u1', startDate: '2026-11-02', endDate: '2027-03-31', contractValue: 1000, nodes: [],
    });
    expect(created).toEqual({ id: 'p9', code: 'PRJ-000124' });
    expect(JSON.parse(posts[0].body!)).toEqual({
      op365_name: 'Warehouse', statuscode: 365000000, 'op365_CustomerId@odata.bind': '/accounts(a1)',
      'op365_ProjectManagerId@odata.bind': '/systemusers(u1)', op365_startdate: '2026-11-02', op365_enddate: '2027-03-31', op365_contractvalue: 1000,
    });
    expect(await service.createNode('p9', { code: '1.2', name: 'Survey', parentCode: '1', sortOrder: 2, budgetHours: 16 }, 'n1')).toBe('n2');
    expect(JSON.parse(posts[1].body!)).toEqual({
      op365_name: 'Survey', op365_code: '1.2', op365_sortorder: 2, 'op365_ProjectId@odata.bind': '/op365_projects(p9)',
      'op365_ParentId@odata.bind': '/op365_wbsnodes(n1)', op365_budgethours: 16,
    });
  });

  it('creates the customer of a new project as an account marked as customer', async () => {
    const { send, posts } = fake({ 'accounts?$select': { accountid: 'a7' } });
    const service = new ProjectIQService(new DataverseClient(ENV, send));
    expect(await service.createCustomer({ name: 'Northwind', vatNumber: 'IT01234567890' })).toBe('a7');
    expect(await service.createCustomer({ name: 'Contoso' })).toBe('a7');
    expect(posts.map(p => JSON.parse(p.body!))).toEqual([
      { name: 'Northwind', op365_iscustomer: true, op365_customertype: 365000001, op365_vatnumber: 'IT01234567890' },
      { name: 'Contoso', op365_iscustomer: true, op365_customertype: 365000001 },
    ]);
  });

  it('creates the project folder in the op365_project library, registers it and uploads the document', async () => {
    const { send, posts } = fake({
      '_regardingobjectid_value eq null': { value: [{
        sharepointdocumentlocationid: 'lib1', relativeurl: 'op365_project',
        parentsiteorlocation_sharepointsite: { absoluteurl: 'https://contoso.sharepoint.com/sites/ProjectIQ', isdefault: true },
      }] },
      'sharepointdocumentlocations?$select=sharepointdocumentlocationid': { sharepointdocumentlocationid: 'loc1' },
    });
    const calls: { url: string; body?: string | Blob }[] = [];
    const sp = new SharePointClient(async (_m, url, _h, body) => {
      calls.push({ url, body });
      const json = url.indexOf('/Files/') >= 0 ? { ServerRelativeUrl: '/sites/ProjectIQ/op365_project/Warehouse_0A1B/Offer.pdf' } : {};
      return { ok: true, status: 200, statusText: 'OK', text: async () => JSON.stringify(json) };
    });
    const file = new Blob(['%PDF']);
    const saved = await new ProjectIQService(new DataverseClient(ENV, send), sp).saveProjectDocument('0a1b', 'Warehouse', 'Offer.pdf', file);
    expect(calls[0].url).toBe("https://contoso.sharepoint.com/sites/ProjectIQ/_api/web/folders/AddUsingPath(decodedurl=@p)?@p='%2Fsites%2FProjectIQ%2Fop365_project%2FWarehouse_0A1B'");
    expect(JSON.parse(posts[0].body!)).toEqual({
      name: 'Documents on Warehouse', relativeurl: 'Warehouse_0A1B',
      'parentsiteorlocation_sharepointdocumentlocation@odata.bind': '/sharepointdocumentlocations(lib1)',
      'regardingobjectid_op365_project@odata.bind': '/op365_projects(0a1b)',
    });
    expect(calls[1].url).toContain("/Files/AddUsingPath(decodedurl=@f,overwrite=true)?@p='%2Fsites%2FProjectIQ%2Fop365_project%2FWarehouse_0A1B'&@f='Offer.pdf'");
    expect(calls[1].body).toBe(file);
    expect(saved).toEqual({
      fileUrl: 'https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/Warehouse_0A1B/Offer.pdf',
      folderUrl: 'https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/Warehouse_0A1B',
    });
  });

  it('reports when document management has no project library', async () => {
    const { send } = fake({});
    const sp = new SharePointClient(async () => ({ ok: true, status: 200, statusText: 'OK', text: async () => '{}' }));
    await expect(new ProjectIQService(new DataverseClient(ENV, send), sp).saveProjectDocument('p1', 'X', 'a.pdf', new Blob(['x'])))
      .rejects.toBeInstanceOf(NoDocumentLibraryError);
  });
});
