// SharePoint REST access with the identity of the signed-in user (SPHttpClient): the agent lists only the files
// the user can open in SharePoint, and creates folders and uploads files only where the user can write.
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
    const json = await this._request('GET', url, undefined, true);
    if (!json) return undefined;
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

  /** Creates a folder from its absolute URL (its parent must exist); nothing changes when it already exists. */
  public async ensureFolder(webUrl: string, folderUrl: string): Promise<void> {
    const path = serverRelativePath(folderUrl).replace(/'/g, "''");
    await this._request('POST', `${webUrl.replace(/\/+$/, '')}/_api/web/folders/AddUsingPath(decodedurl=@p)?@p='${encodeURIComponent(path)}'`);
  }

  /** Uploads a file into a folder (replacing a file with the same name) and returns the link that opens it. */
  public async upload(webUrl: string, folderUrl: string, fileName: string, content: Blob): Promise<string> {
    const folder = serverRelativePath(folderUrl).replace(/'/g, "''");
    const name = fileName.replace(/'/g, "''");
    const url = `${webUrl.replace(/\/+$/, '')}/_api/web/GetFolderByServerRelativePath(decodedurl=@p)/Files/AddUsingPath(decodedurl=@f,overwrite=true)`
      + `?@p='${encodeURIComponent(folder)}'&@f='${encodeURIComponent(name)}'`;
    const json = await this._request('POST', url, content);
    return documentUrl(webUrl, str(json?.ServerRelativeUrl) || `${serverRelativePath(folderUrl)}/${fileName}`);
  }

  /** JSON of the response; undefined on 404 when `allowMissing`, SharePointError otherwise. */
  private async _request(method: 'GET' | 'POST', url: string, body?: Blob, allowMissing = false): Promise<Row | undefined> {
    const headers: Record<string, string> = { Accept: 'application/json;odata=nometadata' };
    if (method === 'POST' && !body) headers['Content-Type'] = 'application/json;odata=nometadata';
    const response = await this._send(method, url, headers, body);
    const text = await response.text();
    if (allowMissing && response.status === 404) return undefined;
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
    return json;
  }
}
