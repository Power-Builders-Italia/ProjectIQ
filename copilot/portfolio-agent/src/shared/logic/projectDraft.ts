// New project from a document: Copilot reads the document the user attached and passes what it found (project data
// and WBS); the card shows it as an editable draft, asks for what is missing and creates the project, in status
// Offer, only after the user confirms. Pure rules, tested without Dataverse or SharePoint.

export interface WbsDraftLine {
  key: string;
  /** Outline code: 1, 1.2, 1.2.3. The parent is the code without its last part. */
  code: string;
  name: string;
  budgetHours: string;
  startDate: string;
  endDate: string;
}

/** Customer created with the project, when it is not yet an account in ProjectIQ. */
export interface NewCustomer {
  name: string;
  vatNumber: string;
}

export interface ProjectDraft {
  name: string;
  customerId?: string;
  /** Set when the user creates a new customer instead of choosing an account; customerId is then ignored. */
  newCustomer?: NewCustomer;
  managerId?: string;
  /** yyyy-mm-dd, empty when unknown. */
  startDate: string;
  endDate: string;
  /** As typed by the user; parsed on save. */
  contractValue: string;
  description: string;
  lines: WbsDraftLine[];
}

/** What Copilot extracted from the document (tool properties). */
export interface ExtractedWbs {
  code?: string;
  name?: string;
  budgetHours?: number;
  startDate?: string;
  endDate?: string;
}

export interface ExtractedProject {
  name?: string;
  startDate?: string;
  endDate?: string;
  contractValue?: number;
  description?: string;
  wbs?: ExtractedWbs[];
}

export type DraftIssueCode =
  | 'noName' | 'noCustomer' | 'noCustomerName' | 'customerExists' | 'noManager' | 'noStart' | 'noEnd' | 'endBeforeStart' | 'badValue'
  | 'noNodeName' | 'badCode' | 'duplicateCode' | 'noParent' | 'badHours' | 'badNodeDates' | 'nodeOutsideProject'
  | 'noWbs' | 'noFile';

export interface DraftIssue {
  code: DraftIssueCode;
  severity: 'error' | 'warning';
  /** WBS line the issue is about. */
  key?: string;
}

export interface PlannedNode {
  code: string;
  name: string;
  /** Code of the parent node, empty for a top-level phase. */
  parentCode: string;
  sortOrder: number;
  budgetHours?: number;
  startDate?: string;
  endDate?: string;
}

export interface ProjectPlan {
  name: string;
  /** Empty when newCustomer is set: the account is created first. */
  customerId: string;
  newCustomer?: { name: string; vatNumber?: string };
  managerId: string;
  startDate: string;
  endDate: string;
  contractValue?: number;
  description?: string;
  /** Parents before children, siblings in outline order. */
  nodes: PlannedNode[];
}

const CODE = /^\d+(\.\d+)*$/;

/** yyyy-mm-dd from an ISO date or a day-first date (31/12/2026, 31.12.2026); empty when not a date. */
export function normaliseDate(value: string | undefined): string {
  const v = (value || '').trim();
  const iso = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(v);
  const dayFirst = /^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$/.exec(v);
  const parts = iso ? [iso[1], iso[2], iso[3]] : dayFirst ? [dayFirst[3], dayFirst[2], dayFirst[1]] : undefined;
  if (!parts) return '';
  const [y, mo, d] = parts.map(Number);
  const date = new Date(Date.UTC(y, mo - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== mo - 1 || date.getUTCDate() !== d) return '';
  return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

/** Outline code without blanks and trailing dot ("1.2." -> "1.2"). */
export const normaliseCode = (value: string | undefined): string => (value || '').replace(/\s+/g, '').replace(/\.+$/, '');

export const parentCode = (code: string): string => (code.indexOf('.') >= 0 ? code.substring(0, code.lastIndexOf('.')) : '');

/** Number typed in any of the four cultures (1.234,5 or 1,234.5 or 1234.5); undefined when empty, NaN when not a number. */
export function parseAmount(text: string | undefined): number | undefined {
  let v = (text || '').replace(/[\s '€$£]/g, '');
  if (!v) return undefined;
  const comma = v.lastIndexOf(','), dot = v.lastIndexOf('.');
  if (comma > dot) v = v.replace(/\./g, '').replace(',', '.');
  else v = v.replace(/,/g, '');
  return /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : NaN;
}

const compareCodes = (a: string, b: string): number => {
  const x = a.split('.').map(Number), y = b.split('.').map(Number);
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    if (x[i] === undefined) return -1;
    if (y[i] === undefined) return 1;
    if (x[i] !== y[i]) return x[i] - y[i];
  }
  return 0;
};

/** Best match of a name in the document among the choices: exact, then the only one containing it (or contained). */
export function matchByName<T extends { name: string }>(choices: T[], text: string | undefined): T | undefined {
  const q = (text || '').trim().toLowerCase();
  if (!q) return undefined;
  const exact = choices.filter(c => c.name.toLowerCase() === q);
  if (exact.length === 1) return exact[0];
  const near = choices.filter(c => { const n = c.name.toLowerCase(); return n.indexOf(q) >= 0 || q.indexOf(n) >= 0; });
  return near.length === 1 ? near[0] : undefined;
}

/** WBS lines of the draft; lines without a valid code get the next top-level number. */
export function draftLines(wbs: ExtractedWbs[] | undefined, newKey: () => string): WbsDraftLine[] {
  const lines = (wbs || []).filter(w => (w.name || '').trim() || (w.code || '').trim()).map(w => ({
    key: newKey(),
    code: normaliseCode(w.code),
    name: (w.name || '').trim(),
    budgetHours: typeof w.budgetHours === 'number' && w.budgetHours >= 0 ? String(w.budgetHours) : '',
    startDate: normaliseDate(w.startDate),
    endDate: normaliseDate(w.endDate),
  }));
  let next = lines.reduce((max, l) => (CODE.test(l.code) ? Math.max(max, Number(l.code.split('.')[0])) : max), 0);
  return lines.map(l => (CODE.test(l.code) ? l : { ...l, code: String(++next) }));
}

export function draftFrom(p: ExtractedProject, newKey: () => string): ProjectDraft {
  return {
    name: (p.name || '').trim(),
    startDate: normaliseDate(p.startDate),
    endDate: normaliseDate(p.endDate),
    contractValue: typeof p.contractValue === 'number' && p.contractValue >= 0 ? String(p.contractValue) : '',
    description: (p.description || '').trim(),
    lines: draftLines(p.wbs, newKey),
  };
}

/** Errors block the creation; warnings are shown in the review. customers: existing names, to warn about a duplicate. */
export function validateDraft(d: ProjectDraft, hasFile: boolean, customers: { name: string }[] = []): DraftIssue[] {
  const issues: DraftIssue[] = [];
  const error = (code: DraftIssueCode, key?: string): void => { issues.push({ code, severity: 'error', key }); };
  const warning = (code: DraftIssueCode, key?: string): void => { issues.push({ code, severity: 'warning', key }); };
  if (!d.name.trim()) error('noName');
  if (d.newCustomer) {
    const n = d.newCustomer.name.trim().toLowerCase();
    if (!n) error('noCustomerName');
    else if (customers.some(c => c.name.trim().toLowerCase() === n)) warning('customerExists');
  } else if (!d.customerId) error('noCustomer');
  if (!d.managerId) error('noManager');
  if (!d.startDate) error('noStart');
  if (!d.endDate) error('noEnd');
  if (d.startDate && d.endDate && d.endDate < d.startDate) error('endBeforeStart');
  const value = parseAmount(d.contractValue);
  if (value !== undefined && (isNaN(value) || value < 0)) error('badValue');
  const codes = d.lines.map(l => l.code);
  for (const l of d.lines) {
    if (!l.name.trim()) error('noNodeName', l.key);
    if (!CODE.test(l.code)) error('badCode', l.key);
    else if (codes.filter(c => c === l.code).length > 1) error('duplicateCode', l.key);
    else if (parentCode(l.code) && codes.indexOf(parentCode(l.code)) < 0) error('noParent', l.key);
    const h = parseAmount(l.budgetHours);
    if (h !== undefined && (isNaN(h) || h < 0)) error('badHours', l.key);
    if (l.startDate && l.endDate && l.endDate < l.startDate) error('badNodeDates', l.key);
    else if ((l.startDate && d.startDate && l.startDate < d.startDate) || (l.endDate && d.endDate && l.endDate > d.endDate)) warning('nodeOutsideProject', l.key);
  }
  if (!d.lines.length) warning('noWbs');
  if (!hasFile) warning('noFile');
  return issues;
}

export const canCreate = (issues: DraftIssue[]): boolean => !issues.some(i => i.severity === 'error');

/** What will be written: the project and its WBS nodes, parents first. Call only when canCreate. */
export function planProject(d: ProjectDraft): ProjectPlan {
  const value = parseAmount(d.contractValue);
  const nodes = [...d.lines].sort((a, b) => compareCodes(a.code, b.code)).map(l => {
    const h = parseAmount(l.budgetHours);
    return {
      code: l.code,
      name: l.name.trim(),
      parentCode: parentCode(l.code),
      sortOrder: Number(l.code.split('.').pop()),
      budgetHours: h === undefined || isNaN(h) ? undefined : h,
      startDate: l.startDate || undefined,
      endDate: l.endDate || undefined,
    };
  });
  return {
    name: d.name.trim(),
    customerId: d.newCustomer ? '' : d.customerId || '',
    newCustomer: d.newCustomer ? { name: d.newCustomer.name.trim(), vatNumber: d.newCustomer.vatNumber.trim() || undefined } : undefined,
    managerId: d.managerId || '',
    startDate: d.startDate,
    endDate: d.endDate,
    contractValue: value === undefined || isNaN(value) ? undefined : value,
    description: d.description.trim() || undefined,
    nodes,
  };
}

/**
 * Name of the SharePoint folder of a project, as Dataverse names it when Documents is opened: the project name
 * without the characters SharePoint refuses, an underscore and the id in capitals without hyphens.
 */
export function projectFolderName(projectName: string, projectId: string): string {
  const id = projectId.replace(/[{}-]/g, '').toUpperCase();
  const name = projectName.replace(/[~"#%&*:<>?/\\{|}]/g, '').replace(/\s+/g, ' ').trim().replace(/^\.+|\.+$/g, '').substring(0, 80).trim();
  return name ? `${name}_${id}` : id;
}

/** File name SharePoint accepts: forbidden characters become a hyphen. */
export const safeFileName = (name: string): string => name.replace(/[~"#%&*:<>?/\\{|}]/g, '-').replace(/^\.+/, '').trim() || 'document';
