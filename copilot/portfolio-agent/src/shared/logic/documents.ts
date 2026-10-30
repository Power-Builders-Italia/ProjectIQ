// Documents of a project in SharePoint: the folders Dataverse created for the record (document locations) and their
// content, read with the user's own SharePoint permissions.

export interface DocumentItem {
  name: string;
  /** Link that opens the file (Office files in the browser) or the folder in SharePoint. */
  url: string;
  folder: boolean;
  /** Last change, as a day number. */
  modified?: number;
  modifiedBy?: string;
  /** Bytes (files) or number of items (folders). */
  size: number;
}

export interface DocumentFolder {
  /** Document location name in Dataverse, for example "Documents on ProjectIQ Documents 1". */
  name: string;
  url: string;
  /** False when the folder is registered in Dataverse but not created in SharePoint yet. */
  exists: boolean;
  items: DocumentItem[];
}

export interface DocumentSummary {
  files: number;
  folders: number;
  lastModified?: number;
  lastModifiedBy?: string;
  /** Subfolders first, then files from the most recent change. */
  items: DocumentItem[];
}

const OFFICE = /\.(docx?|xlsx?|pptx?|docm|xlsm|pptm)$/i;

/** Absolute link of a file or folder from its server-relative URL; Office files open in the browser. */
export function documentUrl(webUrl: string, serverRelativeUrl: string, folder = false): string {
  const origin = /^https:\/\/[^/]+/i.exec(webUrl)?.[0] || '';
  const path = serverRelativeUrl.split('/').map(encodeURIComponent).join('/');
  return origin + path + (!folder && OFFICE.test(serverRelativeUrl) ? '?web=1' : '');
}

/** Server-relative path of an absolute SharePoint URL (decoded), for GetFolderByServerRelativePath. */
export function serverRelativePath(absoluteUrl: string): string {
  const path = absoluteUrl.replace(/^https:\/\/[^/]+/i, '').replace(/\/+$/, '');
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}

/** Joins the site URL and the relative URLs of the library and the record folder. */
export function joinUrl(base: string, ...parts: string[]): string {
  return [base.replace(/\/+$/, ''), ...parts.map(p => p.replace(/^\/+|\/+$/g, '')).filter(Boolean)].join('/');
}

export function documentSummary(folders: DocumentFolder[]): DocumentSummary {
  const items = folders.flatMap(f => f.items);
  const files = items.filter(i => !i.folder);
  const latest = files.reduce<DocumentItem | undefined>((best, i) => (i.modified !== undefined && (best?.modified === undefined || i.modified > best.modified) ? i : best), undefined);
  const sorted = [...items].sort((a, b) => (a.folder === b.folder
    ? (b.modified ?? -1) - (a.modified ?? -1) || a.name.localeCompare(b.name)
    : a.folder ? -1 : 1));
  return {
    files: files.length,
    folders: items.length - files.length,
    lastModified: latest?.modified,
    lastModifiedBy: latest?.modifiedBy,
    items: sorted,
  };
}

/** File size in the user's culture (B, KB, MB, GB). */
export function fileSize(bytes: number, locale?: string): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: unit ? 1 : 0 }).format(value) + ' ' + units[unit];
}
