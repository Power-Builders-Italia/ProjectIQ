// Web API access shared by the Phase 3 controls (timesheet, approval, resource load, cost summary).
import { isoDay, toDay } from "./dates";
import { TimeEntry } from "./timesheet";
import { PendingEntry } from "./approval";
import { LoadAbsence, LoadAllocation, LoadResource } from "./load";
import { NodeActuals } from "./cost";

type WebApi = ComponentFramework.WebApi;
type Row = ComponentFramework.WebApi.Entity;

const num = (v: unknown): number => (typeof v === "number" ? v : 0);
const bare = (id: string): string => id.replace(/[{}]/g, "").toLowerCase();
const label = (r: Row | undefined, ...cols: string[]): string =>
    r ? cols.map(c => r[c] as string).filter(Boolean).join(" ") : "";

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

/** Calls an unbound Custom API (Web API action) of the current environment. */
export async function callAction(name: string, body: Record<string, unknown>): Promise<Record<string, unknown>> {
    const response = await fetch(`/api/data/v9.2/${name}`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8", Accept: "application/json", "OData-Version": "4.0", "OData-MaxVersion": "4.0" },
        body: JSON.stringify(body),
        credentials: "same-origin",
    });
    const text = await response.text();
    const json = text ? JSON.parse(text) as Record<string, unknown> : {};
    if (!response.ok) {
        const error = json.error as { message?: string } | undefined;
        throw new Error(error?.message ?? response.statusText);
    }
    return json;
}

export interface Me { userId: string; resourceId?: string; resourceName?: string; weeklyHours: number; }

export async function loadMe(api: WebApi, userId: string): Promise<Me> {
    const id = bare(userId);
    const rows = await api.retrieveMultipleRecords("op365_resource",
        `?$select=op365_resourceid,op365_name,op365_weeklyhours&$filter=_op365_userid_value eq ${id} and statecode eq 0&$top=1`);
    const r = rows.entities[0];
    return { userId: id, resourceId: r?.op365_resourceid as string | undefined, resourceName: r?.op365_name as string | undefined,
        weeklyHours: r ? num(r.op365_weeklyhours) || 40 : 40 };
}

const ENTRY_SELECT = "$select=op365_timeentryid,op365_entrydate,op365_hours,statuscode,op365_notes,_op365_projectid_value,_op365_wbsnodeid_value,_op365_resourceid_value"
    + "&$expand=op365_ProjectId($select=op365_code,op365_name),op365_WbsNodeId($select=op365_code,op365_name),op365_ResourceId($select=op365_name)";

export async function loadWeek(api: WebApi, resourceId: string, monday: number): Promise<TimeEntry[]> {
    const rows = await all(api, "op365_timeentry", `?${ENTRY_SELECT}&$filter=_op365_resourceid_value eq ${resourceId}`
        + ` and op365_entrydate ge ${isoDay(monday)} and op365_entrydate le ${isoDay(monday + 6)} and statecode eq 0`);
    return rows.map(r => ({
        id: r.op365_timeentryid as string,
        projectId: r._op365_projectid_value as string,
        projectName: label(r.op365_ProjectId as Row, "op365_code", "op365_name"),
        nodeId: (r._op365_wbsnodeid_value as string) || undefined,
        nodeName: r._op365_wbsnodeid_value ? label(r.op365_WbsNodeId as Row, "op365_code", "op365_name") : undefined,
        day: toDay(r.op365_entrydate as string)!,
        hours: num(r.op365_hours),
        status: num(r.statuscode),
    }));
}

export interface Choice { id: string; name: string; }

/** In Progress projects visible to the user. */
export async function loadOpenProjects(api: WebApi): Promise<Choice[]> {
    const rows = await all(api, "op365_project", "?$select=op365_projectid,op365_code,op365_name&$filter=statuscode eq 1&$orderby=op365_code");
    return rows.map(r => ({ id: r.op365_projectid as string, name: label(r, "op365_code", "op365_name") }));
}

export async function loadProjectNodes(api: WebApi, projectId: string): Promise<Choice[]> {
    const rows = await all(api, "op365_wbsnode",
        `?$select=op365_wbsnodeid,op365_code,op365_name&$filter=_op365_projectid_value eq ${projectId} and statecode eq 0&$orderby=op365_code`);
    return rows.map(r => ({ id: r.op365_wbsnodeid as string, name: label(r, "op365_code", "op365_name") }));
}

export async function createEntry(api: WebApi, projectId: string, nodeId: string | undefined, day: number, hours: number): Promise<void> {
    const body: Record<string, unknown> = {
        "op365_ProjectId@odata.bind": `/op365_projects(${projectId})`, op365_entrydate: isoDay(day), op365_hours: hours,
    };
    if (nodeId) body["op365_WbsNodeId@odata.bind"] = `/op365_wbsnodes(${nodeId})`;
    await api.createRecord("op365_timeentry", body);
}

export async function updateEntry(api: WebApi, id: string, hours: number): Promise<void> {
    await api.updateRecord("op365_timeentry", id, { op365_hours: hours });
}

export async function deleteEntry(api: WebApi, id: string): Promise<void> {
    await api.deleteRecord("op365_timeentry", id);
}

export async function loadPending(api: WebApi): Promise<PendingEntry[]> {
    const rows = await all(api, "op365_timeentry", `?${ENTRY_SELECT}&$filter=statuscode eq 365000000&$orderby=op365_entrydate`);
    return rows.map(r => ({
        id: r.op365_timeentryid as string,
        resourceId: r._op365_resourceid_value as string,
        resourceName: label(r.op365_ResourceId as Row, "op365_name"),
        projectName: label(r.op365_ProjectId as Row, "op365_code", "op365_name"),
        nodeName: r._op365_wbsnodeid_value ? label(r.op365_WbsNodeId as Row, "op365_code", "op365_name") : undefined,
        day: toDay(r.op365_entrydate as string)!,
        hours: num(r.op365_hours),
        notes: (r.op365_notes as string) || undefined,
    }));
}

export async function loadLoadData(api: WebApi, first: number, last: number):
    Promise<{ resources: LoadResource[]; allocations: LoadAllocation[]; absences: LoadAbsence[] }> {
    const [res, alloc, abs] = await Promise.all([
        all(api, "op365_resource", "?$select=op365_resourceid,op365_name,op365_weeklyhours,op365_workingdays&$filter=statecode eq 0&$orderby=op365_name"),
        all(api, "op365_wbsallocation", "?$select=_op365_resourceid_value,op365_hours&$filter=statecode eq 0"
            + "&$expand=op365_WbsNodeId($select=op365_startdate,op365_enddate,statecode;$expand=op365_ProjectId($select=op365_code,op365_name,statecode))"),
        all(api, "op365_absence", `?$select=_op365_resourceid_value,op365_fromdate,op365_todate,op365_hours`
            + `&$filter=statecode eq 0 and op365_todate ge ${isoDay(first)} and op365_fromdate le ${isoDay(last)}`),
    ]);
    return {
        resources: res.map(r => ({
            id: r.op365_resourceid as string, name: r.op365_name as string, weeklyHours: num(r.op365_weeklyhours),
            workingDays: typeof r.op365_workingdays === "string" && r.op365_workingdays
                ? (r.op365_workingdays as string).split(",").map(Number) : [],
        })),
        allocations: alloc.filter(a => {
            const node = a.op365_WbsNodeId as Row | undefined;
            const project = node?.op365_ProjectId as Row | undefined;
            return node && node.statecode === 0 && (!project || project.statecode === 0);
        }).map(a => {
            const node = a.op365_WbsNodeId as Row;
            return {
                resourceId: a._op365_resourceid_value as string, hours: num(a.op365_hours),
                start: toDay(node.op365_startdate as string), end: toDay(node.op365_enddate as string),
                projectName: label(node.op365_ProjectId as Row, "op365_code", "op365_name"),
            };
        }),
        absences: abs.map(a => ({
            resourceId: (a._op365_resourceid_value as string) || undefined,
            from: toDay(a.op365_fromdate as string)!, to: toDay(a.op365_todate as string)!,
            hours: typeof a.op365_hours === "number" ? a.op365_hours : undefined,
        })),
    };
}

export interface ProjectCosts {
    contract: number;
    progressPct: number;
    actualCost: number;
    actualHours: number;
    labour: number;
    materials: number;
    nodeActuals: Map<string, NodeActuals>;
}

async function aggregate(api: WebApi, table: string, column: string, projectId: string, extra = ""): Promise<number> {
    const xml = `<fetch aggregate="true"><entity name="${table}"><attribute name="${column}" alias="total" aggregate="sum" />`
        + `<filter><condition attribute="op365_projectid" operator="eq" value="${projectId}" />`
        + `<condition attribute="statecode" operator="eq" value="0" />${extra}</filter></entity></fetch>`;
    const result = await api.retrieveMultipleRecords(table, "?fetchXml=" + encodeURIComponent(xml));
    const v = result.entities[0]?.total as unknown;
    return typeof v === "number" ? v : typeof v === "object" && v !== null ? num((v as { Value?: number }).Value) : 0;
}

export async function loadProjectCosts(api: WebApi, projectId: string): Promise<ProjectCosts> {
    const [p, nodes, labour, materials] = await Promise.all([
        api.retrieveRecord("op365_project", projectId, "?$select=op365_contractvalue,op365_progresspct,op365_actualcost,op365_actualhours"),
        all(api, "op365_wbsnode", `?$select=op365_wbsnodeid,op365_actualcost,op365_actualhours&$filter=_op365_projectid_value eq ${projectId} and statecode eq 0`),
        aggregate(api, "op365_timeentry", "op365_cost", projectId, '<condition attribute="statuscode" operator="eq" value="365000001" />'),
        aggregate(api, "op365_materialusage", "op365_totalcost", projectId),
    ]);
    return {
        contract: num(p.op365_contractvalue), progressPct: num(p.op365_progresspct), actualCost: num(p.op365_actualcost),
        actualHours: num(p.op365_actualhours), labour, materials,
        nodeActuals: new Map(nodes.map(n => [n.op365_wbsnodeid as string, { actualCost: num(n.op365_actualcost), actualHours: num(n.op365_actualhours) }])),
    };
}
