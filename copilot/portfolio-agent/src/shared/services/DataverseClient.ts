// Dataverse Web API access with the identity of the signed-in user (delegated user_impersonation token):
// the agent sees exactly the rows and columns the user sees in the ProjectIQ app.

export interface IHttpResult {
  ok: boolean;
  status: number;
  statusText: string;
  text(): Promise<string>;
}

/** Sends one request; the SPFx implementation wraps AadHttpClient, the tests use a fake. */
export type HttpSend = (method: 'GET' | 'POST', url: string, headers: Record<string, string>, body?: string) => Promise<IHttpResult>;

export type Row = Record<string, unknown>;

const FORMATTED = '@OData.Community.Display.V1.FormattedValue';

export const num = (v: unknown): number => (typeof v === 'number' ? v : 0);
export const str = (v: unknown): string => (typeof v === 'string' ? v : '');
/** Display text of a lookup or choice column (needs the formatted-value annotation, always requested). */
export const formatted = (r: Row, column: string): string => str(r[column + FORMATTED]);

export class DataverseError extends Error {
  public constructor(message: string, public readonly status: number) {
    super(message);
  }
}

export class DataverseClient {
  private readonly _base: string;

  public constructor(environmentUrl: string, private readonly _send: HttpSend) {
    this._base = environmentUrl.replace(/\/+$/, '') + '/api/data/v9.2/';
  }

  public get environmentUrl(): string {
    return this._base.substring(0, this._base.length - '/api/data/v9.2/'.length);
  }

  /** Reads every page of a query on an entity set (for example `op365_projects`). */
  public async all(entitySet: string, query: string): Promise<Row[]> {
    const out: Row[] = [];
    let url: string | undefined = this._base + entitySet + (query ? '?' + query : '');
    while (url) {
      const page: Row = await this._request('GET', url);
      out.push(...((page.value as Row[]) || []));
      url = page['@odata.nextLink'] as string | undefined;
    }
    return out;
  }

  public async get(path: string): Promise<Row> {
    return this._request('GET', this._base + path);
  }

  /** Calls an unbound Custom API (Web API action), for example op365_SubmitTimeEntries. */
  public async action(name: string, body: Record<string, unknown>): Promise<Row> {
    return this._request('POST', this._base + name, body);
  }

  /** Creates a row and returns its id; the row is returned in the body because the OData-EntityId header is not exposed cross-origin. */
  public async create(entitySet: string, body: Record<string, unknown>, idColumn: string): Promise<string> {
    const row = await this._request('POST', this._base + entitySet + '?$select=' + idColumn, body, true);
    return str(row[idColumn]);
  }

  private async _request(method: 'GET' | 'POST', url: string, body?: Record<string, unknown>, returnRow = false): Promise<Row> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'OData-MaxVersion': '4.0',
      'OData-Version': '4.0',
      Prefer: 'odata.include-annotations="OData.Community.Display.V1.FormattedValue",odata.maxpagesize=5000'
        + (returnRow ? ',return=representation' : ''),
    };
    if (body) headers['Content-Type'] = 'application/json; charset=utf-8';
    const response = await this._send(method, url, headers, body ? JSON.stringify(body) : undefined);
    const text = await response.text();
    let json: Row = {};
    try {
      json = text ? JSON.parse(text) as Row : {};
    } catch {
      json = {};
    }
    if (!response.ok) {
      const error = json.error as { message?: string } | undefined;
      throw new DataverseError(error?.message || response.statusText || `HTTP ${response.status}`, response.status);
    }
    return json;
  }
}
