// SharePoint REST access with the identity of the signed-in user (SPHttpClient): the agent lists only the files
// the user can open in SharePoint.
import { toDay } from '../projectiq/dates';
import { documentUrl, serverRelativePath, type DocumentItem } from '../logic/documents';
import { num, str, type HttpSend, type Row } from './DataverseClient';

export class SharePointError extends Error {
  public constructor(message: string, public readonly status: number) {
    super(message);
  }
}

const SELECT = 'Files/Name,Files/ServerRelativeUrl,Files/Length,Files/TimeLastModified,Files/ModifiedBy/Title,'
  + 'Folders/Name,Folders/ServerRelativeUrl,Folders/TimeLastModified,Folders/ItemCount';

export class SharePointClient {
  public constructor(private readonly _send: HttpSend) {}

  /** Files and subfolders of a folder; undefined when the folder does not exist (yet). */
  public async folder(webUrl: string, folderUrl: string): Promise<DocumentItem[] | undefined> {
    const path = serverRelativePath(folderUrl).replace(/'/g, "''");
    const url = `${webUrl.replace(/\/+$/, '')}/_api/web/GetFolderByServerRelativePath(decodedurl=@p)`
      + `?@p='${encodeURIComponent(path)}'&$expand=Files/ModifiedBy,Folders&$select=${SELECT}`;
    const response = await this._send('GET', url, { Accept: 'application/json;odata=nometadata' });
    const text = await response.text();
    if (response.status === 404) return undefined;
    let json: Row = {};
    try {
      json = text ? JSON.parse(text) as Row : {};
    } catch {
      json = {};
    }
    if (!response.ok) {
      const error = json['odata.error'] as { message?: { value?: string } } | undefined;
      throw new SharePointError(error?.message?.value || response.statusText || `HTTP ${response.status}`, response.status);
    }
    const files = ((json.Files as Row[]) || []).map(f => ({
      name: str(f.Name),
      url: documentUrl(webUrl, str(f.ServerRelativeUrl)),
      folder: false,
      modified: toDay(str(f.TimeLastModified) || undefined),
      modifiedBy: str((f.ModifiedBy as Row | undefined)?.Title) || undefined,
      size: Number(f.Length) || 0,
    }));
    const folders = ((json.Folders as Row[]) || []).filter(f => str(f.Name) !== 'Forms').map(f => ({
      name: str(f.Name),
      url: documentUrl(webUrl, str(f.ServerRelativeUrl), true),
      folder: true,
      modified: toDay(str(f.TimeLastModified) || undefined),
      size: num(f.ItemCount),
    }));
    return [...folders, ...files];
  }
}
