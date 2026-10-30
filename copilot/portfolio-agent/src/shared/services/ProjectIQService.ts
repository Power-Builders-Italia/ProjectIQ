// Queries of the agent on the ProjectIQ tables. Read with the user's own permissions; the only writes are the
// time entries of the user and the two time Custom APIs, always after an explicit confirmation in the UI.
import { isoDay, toDay } from '../projectiq/dates';
import type { WbsItem } from '../projectiq/wbs';
import type { CpmLink } from '../projectiq/cpm';
import type { NodeActuals } from '../projectiq/cost';
import type { LoadAbsence, LoadAllocation, LoadResource } from '../projectiq/load';
import type { PendingEntry } from '../projectiq/approval';
import type { TimeEntry } from '../projectiq/timesheet';
import { DataverseClient, formatted, num, Row, str } from './DataverseClient';
import type { ProjectFigures } from '../logic/portfolio';
import type { PurchasingData } from '../logic/purchasing';
import type { SupplierDocument, SupplierInfo } from '../logic/suppliers';
import { joinUrl, type DocumentFolder } from '../logic/documents';
import type { SharePointClient } from './SharePointClient';

const bare = (id: string): string => id.replace(/[{}]/g, '').toLowerCase();
const label = (r: Row | undefined, ...cols: string[]): string => (r ? cols.map(c => str(r[c])).filter(Boolean).join(' ') : '');
const day = (v: unknown): number | undefined => toDay(str(v) || undefined);
/** OData string literal. */
const lit = (s: string): string => `'${s.replace(/'/g, "''")}'`;

export interface Me {
  userId: string;
  resourceId?: string;
  resourceName?: string;
  weeklyHours: number;
}

export interface ProjectDetail {
  project: ProjectFigures;
  currencySymbol?: string;
  nodes: WbsItem[];
  links: CpmLink[];
  actuals: Map<string, NodeActuals>;
  /** Reference baseline: name and saved dates/budget by WBS node id. */
  baseline?: { name: string; nodes: Map<string, { start?: number; end?: number; budget: number }> };
  openRequests: number;
  openOrders: number;
}

export interface Choice { id: string; name: string; }

const PROJECT_SELECT = 'op365_projectid,op365_code,op365_name,_op365_customerid_value,_op365_projectmanagerid_value,statuscode,'
  + 'op365_startdate,op365_enddate,op365_contractvalue,op365_budgettotal,op365_actualcost,op365_committedcost,op365_progresspct,'
  + 'op365_actualhours,_transactioncurrencyid_value';

function toProject(r: Row): ProjectFigures {
  return {
    id: str(r.op365_projectid),
    code: str(r.op365_code),
    name: str(r.op365_name),
    customer: formatted(r, '_op365_customerid_value') || undefined,
    manager: formatted(r, '_op365_projectmanagerid_value') || undefined,
    managerId: str(r._op365_projectmanagerid_value) || undefined,
    status: num(r.statuscode),
    start: day(r.op365_startdate),
    end: day(r.op365_enddate),
    contract: num(r.op365_contractvalue),
    budget: num(r.op365_budgettotal),
    actual: num(r.op365_actualcost),
    committed: num(r.op365_committedcost),
    progress: num(r.op365_progresspct),
    actualHours: num(r.op365_actualhours),
  };
}

const ENTRY_SELECT = '$select=op365_timeentryid,op365_entrydate,op365_hours,statuscode,op365_notes,op365_submittedon,'
  + '_op365_projectid_value,_op365_wbsnodeid_value,_op365_resourceid_value';

export class ProjectIQService {
  private _me?: Promise<Me>;

  public constructor(private readonly _dv: DataverseClient, private readonly _sp?: SharePointClient) {}

  public get environmentUrl(): string {
    return this._dv.environmentUrl;
  }

  /** Dataverse user of the signed-in person and their resource (WhoAmI, then Resource by User). */
  public me(): Promise<Me> {
    if (!this._me) {
      this._me = (async () => {
        const who = await this._dv.get('WhoAmI');
        const userId = bare(str(who.UserId));
        const rows = await this._dv.all('op365_resources',
          `$select=op365_resourceid,op365_name,op365_weeklyhours&$filter=_op365_userid_value eq ${userId} and statecode eq 0&$top=1`);
        const r = rows[0];
        return {
          userId,
          resourceId: r ? str(r.op365_resourceid) : undefined,
          resourceName: r ? str(r.op365_name) : undefined,
          weeklyHours: r ? num(r.op365_weeklyhours) || 40 : 40,
        };
      })();
      this._me.catch(() => { this._me = undefined; });
    }
    return this._me;
  }

  /** Projects visible to the user; closed projects only when asked. */
  public async projects(includeClosed = false): Promise<{ projects: ProjectFigures[]; currencySymbol?: string }> {
    const rows = await this._dv.all('op365_projects', `$select=${PROJECT_SELECT}`
      + `&$expand=transactioncurrencyid($select=currencysymbol)`
      + (includeClosed ? '' : '&$filter=statecode eq 0') + '&$orderby=op365_code');
    const currency = rows.map(r => (r.transactioncurrencyid as Row | null)?.currencysymbol).find(Boolean);
    return { projects: rows.map(toProject), currencySymbol: str(currency) || undefined };
  }

  /** Ids of the projects the user manages (project manager, or member with role Manager). */
  public async managedProjectIds(): Promise<Set<string>> {
    const me = await this.me();
    const [pm, members] = await Promise.all([
      this._dv.all('op365_projects', `$select=op365_projectid&$filter=_op365_projectmanagerid_value eq ${me.userId}`),
      this._dv.all('op365_projectmembers',
        `$select=_op365_projectid_value&$filter=_op365_userid_value eq ${me.userId} and op365_projectrole eq 365000000 and statecode eq 0`),
    ]);
    return new Set([...pm.map(r => str(r.op365_projectid)), ...members.map(r => str(r._op365_projectid_value))]);
  }

  public async projectDetail(projectId: string): Promise<ProjectDetail> {
    const id = bare(projectId);
    const [p, nodes, links, baselines, requests, orders] = await Promise.all([
      this._dv.get(`op365_projects(${id})?$select=${PROJECT_SELECT}&$expand=transactioncurrencyid($select=currencysymbol)`),
      this._dv.all('op365_wbsnodes', '$select=op365_wbsnodeid,_op365_parentid_value,op365_code,op365_name,op365_startdate,op365_enddate,'
        + 'op365_progresspct,op365_budgethours,op365_budgetlabour,op365_budgetmaterials,op365_budgetother,op365_budgettotal,op365_sortorder,'
        + `op365_actualcost,op365_actualhours&$filter=_op365_projectid_value eq ${id} and statecode eq 0`),
      this._dv.all('op365_wbsdependencies',
        `$select=_op365_predecessorid_value,_op365_successorid_value,op365_lagdays&$filter=_op365_projectid_value eq ${id} and statecode eq 0`),
      this._dv.all('op365_baselines',
        `$select=op365_baselineid,op365_name&$filter=_op365_projectid_value eq ${id} and statecode eq 0 and op365_isreference eq true&$top=1`),
      this._dv.all('op365_purchaserequests', `$select=op365_purchaserequestid&$filter=_op365_projectid_value eq ${id} and statuscode eq 365000000`),
      this._dv.all('op365_purchaseorders',
        `$select=op365_purchaseorderid&$filter=_op365_projectid_value eq ${id} and (statuscode eq 365000000 or statuscode eq 365000001)`),
    ]);
    let baseline: ProjectDetail['baseline'];
    if (baselines[0]) {
      const saved = await this._dv.all('op365_baselinenodes', '$select=_op365_wbsnodeid_value,op365_startdate,op365_enddate,op365_budgettotal'
        + `&$filter=_op365_baselineid_value eq ${str(baselines[0].op365_baselineid)}`);
      baseline = {
        name: str(baselines[0].op365_name),
        nodes: new Map(saved.filter(r => r._op365_wbsnodeid_value).map(r => [str(r._op365_wbsnodeid_value), {
          start: day(r.op365_startdate), end: day(r.op365_enddate), budget: num(r.op365_budgettotal),
        }])),
      };
    }
    return {
      project: toProject(p),
      currencySymbol: str((p.transactioncurrencyid as Row | null)?.currencysymbol) || undefined,
      nodes: nodes.map(r => ({
        id: str(r.op365_wbsnodeid),
        parentId: str(r._op365_parentid_value) || undefined,
        code: str(r.op365_code),
        name: str(r.op365_name),
        start: day(r.op365_startdate),
        end: day(r.op365_enddate),
        progress: num(r.op365_progresspct),
        budgetHours: num(r.op365_budgethours),
        budgetLabour: num(r.op365_budgetlabour),
        budgetMaterials: num(r.op365_budgetmaterials),
        budgetOther: num(r.op365_budgetother),
        budgetTotal: num(r.op365_budgettotal),
        sortOrder: typeof r.op365_sortorder === 'number' ? r.op365_sortorder : undefined,
      })),
      links: links.map(r => ({
        predecessorId: str(r._op365_predecessorid_value), successorId: str(r._op365_successorid_value), lagDays: num(r.op365_lagdays),
      })),
      actuals: new Map(nodes.map(r => [str(r.op365_wbsnodeid), { actualCost: num(r.op365_actualcost), actualHours: num(r.op365_actualhours) }])),
      baseline,
      openRequests: requests.length,
      openOrders: orders.length,
    };
  }

  /** Labour (approved hours) and materials cost of a project, summed like the Cost Summary control. */
  public async labourAndMaterials(projectId: string): Promise<{ labour: number; materials: number }> {
    const id = bare(projectId);
    const sum = async (entitySet: string, table: string, column: string, extra = ''): Promise<number> => {
      const xml = `<fetch aggregate="true"><entity name="${table}"><attribute name="${column}" alias="total" aggregate="sum" />`
        + `<filter><condition attribute="op365_projectid" operator="eq" value="${id}" />`
        + `<condition attribute="statecode" operator="eq" value="0" />${extra}</filter></entity></fetch>`;
      const rows = await this._dv.all(entitySet, 'fetchXml=' + encodeURIComponent(xml));
      return num(rows[0]?.total);
    };
    const [labour, materials] = await Promise.all([
      sum('op365_timeentries', 'op365_timeentry', 'op365_cost', '<condition attribute="statuscode" operator="eq" value="365000001" />'),
      sum('op365_materialusages', 'op365_materialusage', 'op365_totalcost'),
    ]);
    return { labour, materials };
  }

  /** Same data as the Resource Load control: active resources, allocations of active nodes, absences in the range. */
  public async loadData(first: number, last: number): Promise<{ resources: LoadResource[]; allocations: LoadAllocation[]; absences: LoadAbsence[] }> {
    const [res, alloc, abs] = await Promise.all([
      this._dv.all('op365_resources', '$select=op365_resourceid,op365_name,op365_weeklyhours,op365_workingdays&$filter=statecode eq 0&$orderby=op365_name'),
      this._dv.all('op365_wbsallocations', '$select=_op365_resourceid_value,op365_hours&$filter=statecode eq 0'
        + '&$expand=op365_WbsNodeId($select=op365_startdate,op365_enddate,statecode;$expand=op365_ProjectId($select=op365_code,op365_name,statecode))'),
      this._dv.all('op365_absences', '$select=_op365_resourceid_value,op365_fromdate,op365_todate,op365_hours'
        + `&$filter=statecode eq 0 and op365_todate ge ${isoDay(first)} and op365_fromdate le ${isoDay(last)}`),
    ]);
    return {
      resources: res.map(r => ({
        id: str(r.op365_resourceid), name: str(r.op365_name), weeklyHours: num(r.op365_weeklyhours),
        workingDays: str(r.op365_workingdays) ? str(r.op365_workingdays).split(',').map(Number) : [],
      })),
      allocations: alloc.filter(a => {
        const node = a.op365_WbsNodeId as Row | undefined;
        const project = node?.op365_ProjectId as Row | undefined;
        return node && node.statecode === 0 && (!project || project.statecode === 0);
      }).map(a => {
        const node = a.op365_WbsNodeId as Row;
        return {
          resourceId: str(a._op365_resourceid_value), hours: num(a.op365_hours),
          start: day(node.op365_startdate), end: day(node.op365_enddate),
          projectName: label(node.op365_ProjectId as Row, 'op365_code', 'op365_name'),
        };
      }),
      absences: abs.map(a => ({
        resourceId: str(a._op365_resourceid_value) || undefined,
        from: day(a.op365_fromdate)!, to: day(a.op365_todate)!,
        hours: typeof a.op365_hours === 'number' ? a.op365_hours : undefined,
      })),
    };
  }

  /** Submitted time entries of the projects the user manages (all of them when `all`). */
  public async pendingTime(all = false): Promise<(PendingEntry & { projectId: string; submittedOn?: number })[]> {
    const [rows, managed] = await Promise.all([
      this._dv.all('op365_timeentries', `${ENTRY_SELECT}&$filter=statuscode eq 365000000 and statecode eq 0&$orderby=op365_entrydate`),
      all ? Promise.resolve(undefined) : this.managedProjectIds(),
    ]);
    return rows.filter(r => !managed || managed.has(str(r._op365_projectid_value))).map(r => ({
      id: str(r.op365_timeentryid),
      projectId: str(r._op365_projectid_value),
      resourceId: str(r._op365_resourceid_value),
      resourceName: formatted(r, '_op365_resourceid_value'),
      projectName: formatted(r, '_op365_projectid_value'),
      nodeName: formatted(r, '_op365_wbsnodeid_value') || undefined,
      day: day(r.op365_entrydate)!,
      hours: num(r.op365_hours),
      notes: str(r.op365_notes) || undefined,
      submittedOn: day(r.op365_submittedon),
    }));
  }

  /** Time entries of the user's resource between two days. */
  public async myEntries(first: number, last: number): Promise<TimeEntry[]> {
    const me = await this.me();
    if (!me.resourceId) return [];
    const rows = await this._dv.all('op365_timeentries', `${ENTRY_SELECT}&$filter=_op365_resourceid_value eq ${me.resourceId}`
      + ` and op365_entrydate ge ${isoDay(first)} and op365_entrydate le ${isoDay(last)} and statecode eq 0`);
    return rows.map(r => ({
      id: str(r.op365_timeentryid),
      projectId: str(r._op365_projectid_value),
      projectName: formatted(r, '_op365_projectid_value'),
      nodeId: str(r._op365_wbsnodeid_value) || undefined,
      nodeName: formatted(r, '_op365_wbsnodeid_value') || undefined,
      day: day(r.op365_entrydate)!,
      hours: num(r.op365_hours),
      status: num(r.statuscode),
    }));
  }

  /** In Progress projects (time is entered only on them). */
  public async openProjects(): Promise<Choice[]> {
    const rows = await this._dv.all('op365_projects', '$select=op365_projectid,op365_code,op365_name&$filter=statuscode eq 1&$orderby=op365_code');
    return rows.map(r => ({ id: str(r.op365_projectid), name: label(r, 'op365_code', 'op365_name') }));
  }

  public async projectNodes(projectId: string): Promise<Choice[]> {
    const rows = await this._dv.all('op365_wbsnodes',
      `$select=op365_wbsnodeid,op365_code,op365_name&$filter=_op365_projectid_value eq ${bare(projectId)} and statecode eq 0&$orderby=op365_code`);
    return rows.map(r => ({ id: str(r.op365_wbsnodeid), name: label(r, 'op365_code', 'op365_name') }));
  }

  /** Creates a draft time entry of the user (the plugin sets resource, name and cost). */
  public async createEntry(projectId: string, nodeId: string | undefined, entryDay: number, hours: number, notes?: string): Promise<string> {
    const body: Record<string, unknown> = {
      'op365_ProjectId@odata.bind': `/op365_projects(${bare(projectId)})`, op365_entrydate: isoDay(entryDay), op365_hours: hours,
    };
    if (nodeId) body['op365_WbsNodeId@odata.bind'] = `/op365_wbsnodes(${bare(nodeId)})`;
    if (notes) body.op365_notes = notes;
    return this._dv.create('op365_timeentries', body, 'op365_timeentryid');
  }

  /** Custom API op365_SubmitTimeEntries: draft or rejected entries of the user become Submitted (Approved when approval is off). */
  public async submitEntries(ids: string[]): Promise<number> {
    const r = await this._dv.action('op365_SubmitTimeEntries', { TimeEntryIds: ids });
    return typeof r.Count === 'number' ? r.Count : ids.length;
  }

  /** Custom API op365_DecideTimeEntries: approve, or reject with a note (project managers and administrators). */
  public async decideEntries(ids: string[], approve: boolean, note?: string): Promise<number> {
    const r = await this._dv.action('op365_DecideTimeEntries', approve
      ? { TimeEntryIds: ids, Approve: true }
      : { TimeEntryIds: ids, Approve: false, Note: note });
    return typeof r.Count === 'number' ? r.Count : ids.length;
  }

  public async purchasing(projectId?: string): Promise<PurchasingData> {
    const me = await this.me();
    const scope = projectId ? ` and _op365_projectid_value eq ${bare(projectId)}` : '';
    const [requests, rfqs, orders, invoices] = await Promise.all([
      this._dv.all('op365_purchaserequests', '$select=op365_purchaserequestid,op365_number,op365_title,statuscode,op365_estimatedamount,'
        + 'op365_neededby,op365_overbudget,op365_abovethreshold,op365_submittedon,_op365_projectid_value,_op365_currentapproverid_value'
        + `&$filter=(statuscode eq 1 or statuscode eq 365000000 or statuscode eq 365000001 or statuscode eq 365000002)${scope}`),
      this._dv.all('op365_rfqs', '$select=op365_rfqid,op365_number,statuscode,op365_deadline,op365_responsecount,_op365_projectid_value'
        + `&$filter=(statuscode eq 1 or statuscode eq 365000000)${scope}`),
      this._dv.all('op365_purchaseorders', '$select=op365_purchaseorderid,op365_number,statuscode,op365_expecteddelivery,op365_totalamount,'
        + 'op365_receivedamount,_op365_supplierid_value,_op365_projectid_value'
        + `&$filter=(statuscode eq 1 or statuscode eq 365000000 or statuscode eq 365000001)${scope}`),
      this._dv.all('op365_supplierinvoices', '$select=op365_supplierinvoiceid,op365_number,op365_invoicenumber,op365_invoicedate,'
        + `op365_totalamount,_op365_supplierid_value,_op365_projectid_value,_op365_purchaseorderid_value&$filter=statuscode eq 1${scope}`),
    ]);
    return {
      me: me.userId,
      requests: requests.map(r => ({
        id: str(r.op365_purchaserequestid), number: str(r.op365_number), title: str(r.op365_title), status: num(r.statuscode),
        amount: num(r.op365_estimatedamount), neededBy: day(r.op365_neededby), overBudget: r.op365_overbudget === true,
        aboveThreshold: r.op365_abovethreshold === true, submittedOn: day(r.op365_submittedon),
        project: formatted(r, '_op365_projectid_value'), approverId: str(r._op365_currentapproverid_value) || undefined,
      })),
      rfqs: rfqs.map(r => ({
        id: str(r.op365_rfqid), number: str(r.op365_number), status: num(r.statuscode), deadline: day(r.op365_deadline),
        responses: num(r.op365_responsecount), project: formatted(r, '_op365_projectid_value'),
      })),
      orders: orders.map(r => ({
        id: str(r.op365_purchaseorderid), number: str(r.op365_number), status: num(r.statuscode), expected: day(r.op365_expecteddelivery),
        total: num(r.op365_totalamount), received: num(r.op365_receivedamount), supplier: formatted(r, '_op365_supplierid_value'),
        project: formatted(r, '_op365_projectid_value'),
      })),
      invoices: invoices.map(r => ({
        id: str(r.op365_supplierinvoiceid), number: str(r.op365_number), invoiceNumber: str(r.op365_invoicenumber),
        date: day(r.op365_invoicedate), total: num(r.op365_totalamount), supplier: formatted(r, '_op365_supplierid_value'),
        project: formatted(r, '_op365_projectid_value') || undefined, order: formatted(r, '_op365_purchaseorderid_value') || undefined,
      })),
    };
  }

  /** Suppliers and their documents expiring by `until` (or a named supplier with all its documents). */
  public async suppliers(until: number, supplierName?: string): Promise<{ suppliers: SupplierInfo[]; documents: SupplierDocument[] }> {
    const filter = supplierName
      ? `op365_issupplier eq true and contains(name,${lit(supplierName)})`
      : 'op365_issupplier eq true and (op365_expireddocs gt 0 or op365_expiringdocs gt 0 or op365_supplierstatus eq 365000001)';
    const accounts = await this._dv.all('accounts',
      `$select=accountid,name,op365_supplierstatus,op365_expireddocs,op365_expiringdocs&$filter=${filter} and statecode eq 0&$orderby=name`);
    if (!accounts.length) return { suppliers: [], documents: [] };
    const ids = accounts.slice(0, 100).map(a => `_op365_supplierid_value eq ${str(a.accountid)}`).join(' or ');
    const docs = await this._dv.all('op365_supplierdocuments', '$select=op365_supplierdocumentid,op365_description,op365_documenttype,op365_number,'
      + `op365_expirydate,_op365_supplierid_value&$filter=statecode eq 0 and (${ids})`
      + (supplierName ? '' : ` and op365_expirydate le ${isoDay(until)}`) + '&$orderby=op365_expirydate');
    const orders = await this._dv.all('op365_purchaseorders',
      `$select=_op365_supplierid_value&$filter=(statuscode eq 1 or statuscode eq 365000000 or statuscode eq 365000001) and (${ids})`);
    return {
      suppliers: accounts.map(a => ({
        id: str(a.accountid), name: str(a.name), blocked: num(a.op365_supplierstatus) === 365000001,
        expired: num(a.op365_expireddocs), expiring: num(a.op365_expiringdocs),
        openOrders: orders.filter(o => str(o._op365_supplierid_value) === str(a.accountid)).length,
      })),
      documents: docs.map(d => ({
        id: str(d.op365_supplierdocumentid), supplierId: str(d._op365_supplierid_value), description: str(d.op365_description),
        type: formatted(d, 'op365_documenttype'), number: str(d.op365_number) || undefined, expiry: day(d.op365_expirydate),
      })),
    };
  }

  /**
   * SharePoint folders of a record (Documents in the ProjectIQ app) and their content. Dataverse keeps one document
   * location per folder: record folder -> library (relative URLs) -> SharePoint site (absolute URL).
   */
  public async documents(recordId: string): Promise<DocumentFolder[]> {
    const rows = await this._dv.all('sharepointdocumentlocations', '$select=name,relativeurl,absoluteurl'
      + '&$expand=parentsiteorlocation_sharepointdocumentlocation($select=relativeurl;$expand=parentsiteorlocation_sharepointsite($select=absoluteurl)),'
      + 'parentsiteorlocation_sharepointsite($select=absoluteurl)'
      + `&$filter=_regardingobjectid_value eq ${bare(recordId)} and statecode eq 0&$orderby=createdon`);
    const folders: { name: string; url: string; web: string }[] = [];
    for (const r of rows) {
      const library = r.parentsiteorlocation_sharepointdocumentlocation as Row | null | undefined;
      const librarySite = str((library?.parentsiteorlocation_sharepointsite as Row | null | undefined)?.absoluteurl);
      const site = str((r.parentsiteorlocation_sharepointsite as Row | null | undefined)?.absoluteurl);
      const absolute = str(r.absoluteurl);
      if (absolute) {
        // Absolute location: the web is the site collection in the URL (/sites/x or /teams/x), else the root site.
        const web = /^https:\/\/[^/]+(\/(sites|teams)\/[^/]+)?/i.exec(absolute)?.[0] || absolute;
        folders.push({ name: str(r.name), url: absolute.replace(/\/+$/, ''), web });
      } else if (library && librarySite) {
        folders.push({ name: str(r.name), url: joinUrl(librarySite, str(library.relativeurl), str(r.relativeurl)), web: librarySite });
      } else if (site) {
        folders.push({ name: str(r.name), url: joinUrl(site, str(r.relativeurl)), web: site });
      }
    }
    const sp = this._sp;
    return Promise.all(folders.map(async f => {
      const items = sp ? await sp.folder(f.web, f.url) : [];
      return { name: f.name, url: f.url, exists: items !== undefined, items: items || [] };
    }));
  }
}
