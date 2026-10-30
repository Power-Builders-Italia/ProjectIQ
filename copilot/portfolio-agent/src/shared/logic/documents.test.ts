import { documentSummary, documentUrl, fileSize, joinUrl, serverRelativePath } from './documents';

describe('project documents', () => {
  const web = 'https://contoso.sharepoint.com/sites/ProjectIQ';

  it('builds links from server-relative URLs and opens Office files in the browser', () => {
    expect(documentUrl(web, '/sites/ProjectIQ/op365_project/PRJ-1_ABC/Offerta cliente.docx'))
      .toBe('https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-1_ABC/Offerta%20cliente.docx?web=1');
    expect(documentUrl(web, '/sites/ProjectIQ/op365_project/PRJ-1_ABC/Pianta.pdf'))
      .toBe('https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-1_ABC/Pianta.pdf');
    expect(documentUrl(web, '/sites/ProjectIQ/op365_project/PRJ-1_ABC/Contratti.docx', true))
      .toBe('https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-1_ABC/Contratti.docx');
  });

  it('joins the site, library and folder and reads the server-relative path back', () => {
    const url = joinUrl(web + '/', '/op365_project/', 'PRJ-1 Sede_ABC');
    expect(url).toBe('https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-1 Sede_ABC');
    expect(serverRelativePath(url)).toBe('/sites/ProjectIQ/op365_project/PRJ-1 Sede_ABC');
    expect(serverRelativePath('https://contoso.sharepoint.com/sites/ProjectIQ/op365_project/PRJ-1%20Sede/')).toBe('/sites/ProjectIQ/op365_project/PRJ-1 Sede');
  });

  it('counts files and folders, finds the last change and lists folders first', () => {
    const s = documentSummary([
      { name: 'A', url: 'a', exists: true, items: [
        { name: 'old.pdf', url: '1', folder: false, modified: 100, modifiedBy: 'Anna', size: 10 },
        { name: 'Contracts', url: '2', folder: true, modified: 300, size: 2 },
        { name: 'new.docx', url: '3', folder: false, modified: 200, modifiedBy: 'Marco', size: 20 },
      ] },
      { name: 'B', url: 'b', exists: false, items: [] },
    ]);
    expect(s.files).toBe(2);
    expect(s.folders).toBe(1);
    expect(s.lastModified).toBe(200);
    expect(s.lastModifiedBy).toBe('Marco');
    expect(s.items.map(i => i.name)).toEqual(['Contracts', 'new.docx', 'old.pdf']);
  });

  it('formats file sizes', () => {
    expect(fileSize(512, 'en')).toBe('512 B');
    expect(fileSize(1536, 'en')).toBe('1.5 KB');
    expect(fileSize(5 * 1024 * 1024, 'en')).toBe('5 MB');
  });
});
