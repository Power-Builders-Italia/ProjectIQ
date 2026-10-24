// Web API access shared by the WBS Tree Grid and the Gantt Chart.
import { toDay } from "./dates";
import { WbsItem } from "./wbs";
import { CpmLink } from "./cpm";

type WebApi = ComponentFramework.WebApi;
type Row = ComponentFramework.WebApi.Entity;

const num = (v: unknown): number => (typeof v === "number" ? v : 0);

const NODE_COLUMNS = [
    "op365_wbsnodeid", "_op365_parentid_value", "op365_code", "op365_name", "op365_startdate", "op365_enddate",
    "op365_progresspct", "op365_budgethours", "op365_budgetlabour", "op365_budgetmaterials", "op365_budgetother",
    "op365_budgettotal", "op365_sortorder",
];

/** Reads every page of a query. */
async function all(api: WebApi, table: string, query: string): Promise<Row[]> {
    const out: Row[] = [];
    let result = await api.retrieveMultipleRecords(table, query, 5000);
    out.push(...result.entities);
    while (result.nextLink) {
        result = await api.retrieveMultipleRecords(table, "?" + result.nextLink.split("?")[1], 5000);
        out.push(...result.entities);
    }
    return out;
}

export async function loadNodes(api: WebApi, projectId: string): Promise<WbsItem[]> {
    const rows = await all(api, "op365_wbsnode",
        `?$select=${NODE_COLUMNS.join(",")}&$filter=_op365_projectid_value eq ${projectId} and statecode eq 0`);
    return rows.map(r => ({
        id: r.op365_wbsnodeid as string,
        parentId: (r._op365_parentid_value as string) || undefined,
        code: (r.op365_code as string) || "",
        name: (r.op365_name as string) || "",
        start: toDay(r.op365_startdate as string),
        end: toDay(r.op365_enddate as string),
        progress: num(r.op365_progresspct),
        budgetHours: num(r.op365_budgethours),
        budgetLabour: num(r.op365_budgetlabour),
        budgetMaterials: num(r.op365_budgetmaterials),
        budgetOther: num(r.op365_budgetother),
        budgetTotal: num(r.op365_budgettotal),
        sortOrder: typeof r.op365_sortorder === "number" ? r.op365_sortorder : undefined,
    }));
}

export async function loadLinks(api: WebApi, projectId: string): Promise<CpmLink[]> {
    const rows = await all(api, "op365_wbsdependency",
        `?$select=_op365_predecessorid_value,_op365_successorid_value,op365_lagdays&$filter=_op365_projectid_value eq ${projectId} and statecode eq 0`);
    return rows.map(r => ({
        predecessorId: r._op365_predecessorid_value as string,
        successorId: r._op365_successorid_value as string,
        lagDays: num(r.op365_lagdays),
    }));
}

export interface BaselineInfo { id: string; name: string; isReference: boolean; }

export async function loadBaselines(api: WebApi, projectId: string): Promise<BaselineInfo[]> {
    const rows = await all(api, "op365_baseline",
        `?$select=op365_baselineid,op365_name,op365_isreference&$filter=_op365_projectid_value eq ${projectId} and statecode eq 0&$orderby=createdon desc`);
    return rows.map(r => ({ id: r.op365_baselineid as string, name: r.op365_name as string, isReference: r.op365_isreference === true }));
}

export interface BaselineBar { start?: number; end?: number; }

/** Saved dates of a baseline, by WBS node id. */
export async function loadBaselineBars(api: WebApi, baselineId: string): Promise<Map<string, BaselineBar>> {
    const rows = await all(api, "op365_baselinenode",
        `?$select=_op365_wbsnodeid_value,op365_startdate,op365_enddate&$filter=_op365_baselineid_value eq ${baselineId}`);
    return new Map(rows.filter(r => r._op365_wbsnodeid_value).map(r => [r._op365_wbsnodeid_value as string, {
        start: toDay(r.op365_startdate as string), end: toDay(r.op365_enddate as string),
    }]));
}

export async function updateNode(api: WebApi, id: string, values: Record<string, unknown>): Promise<void> {
    await api.updateRecord("op365_wbsnode", id, values);
}

/** Id of the record that hosts the control (the project on the Project form), without braces. */
export function hostRecordId(context: ComponentFramework.Context<unknown>): string | undefined {
    const info = (context.mode as unknown as { contextInfo?: { entityId?: string } }).contextInfo;
    const id = info?.entityId;
    return id ? id.replace(/[{}]/g, "").toLowerCase() : undefined;
}
