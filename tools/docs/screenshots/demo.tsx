// Renders the ProjectIQ PCF controls (src/pcf) with demo data for the website screenshots (docs/assets/screenshots).
// The context is a stub: strings come from the 1033 resx files, the Web API answers with the demo rows below.
// Names come from the test dataset (tools/dataverse/seed_test.py); "today" is fixed by page.html. Run screenshots.py.
import * as React from "react";
import * as ReactDOM from "react-dom";
import STRINGS from "./build/strings.json";
import { GanttChartApp } from "PCF/GanttChart/GanttChartApp";
import { WbsTreeGridApp } from "PCF/WbsTreeGrid/WbsTreeGridApp";
import { WeeklyTimesheetApp } from "PCF/WeeklyTimesheet/WeeklyTimesheetApp";
import { TimeApprovalApp } from "PCF/TimeApproval/TimeApprovalApp";
import { ResourceLoadApp } from "PCF/ResourceLoad/ResourceLoadApp";
import { CostSummaryApp } from "PCF/CostSummary/CostSummaryApp";
import { QuoteComparisonApp } from "PCF/QuoteComparison/QuoteComparisonApp";

type Row = Record<string, unknown>;
const PRJ = "11111111-0000-0000-0000-000000000124";
const RFQ = "22222222-0000-0000-0000-000000000042";
const ME = "33333333-0000-0000-0000-000000000001";

const n = (id: string, parent: string | null, code: string, name: string, s: string | null, e: string | null, prog: number,
    h: number, lab: number, mat: number, act: number, acth: number, sort: number): Row => ({
    op365_wbsnodeid: id, _op365_parentid_value: parent, op365_code: code, op365_name: name, op365_startdate: s, op365_enddate: e,
    op365_progresspct: prog, op365_budgethours: h, op365_budgetlabour: lab, op365_budgetmaterials: mat, op365_budgetother: 0,
    op365_budgettotal: lab + mat, op365_sortorder: sort, op365_actualcost: act, op365_actualhours: acth,
});
const NODES: Row[] = [
    n("n1", null, "1", "Design and grid application", "2026-09-14", "2026-10-09", 100, 200, 9000, 0, 8900, 196, 1),
    n("n2", null, "2", "Installation", null, null, 0, 0, 0, 0, 0, 0, 2),
    n("n21", "n2", "2.1", "Mounting structures", "2026-10-12", "2026-11-13", 85, 420, 13400, 38000, 48600, 380, 1),
    n("n22", "n2", "2.2", "PV modules", "2026-11-02", "2026-12-11", 30, 380, 12200, 150000, 37480, 120, 2),
    n("n23", "n2", "2.3", "Inverters and DC/AC wiring", "2026-12-07", "2027-01-08", 0, 300, 9600, 58000, 0, 0, 3),
    n("n3", null, "3", "Grid connection and commissioning", "2027-01-11", "2027-01-29", 0, 120, 4300, 7500, 0, 0, 3),
];
const LINKS: Row[] = [["n1", "n21"], ["n21", "n22"], ["n22", "n23"], ["n23", "n3"]]
    .map(([p, s]) => ({ _op365_predecessorid_value: p, _op365_successorid_value: s, op365_lagdays: 0 }));
const BASE: Row[] = [
    ["n1", "2026-09-14", "2026-10-02"], ["n21", "2026-10-05", "2026-11-06"], ["n22", "2026-10-26", "2026-12-04"],
    ["n23", "2026-11-30", "2027-01-08"], ["n3", "2027-01-11", "2027-01-29"],
].map(([id, s, e]) => ({ _op365_wbsnodeid_value: id, op365_startdate: s, op365_enddate: e }));

const PROJECTS: [string, string, string][] = [
    [PRJ, "PRJ-000124", "Rooftop solar plant 450 kWp"],
    ["p2", "PRJ-000123", "Head office refurbishment - Riverside Tower"],
    ["p3", "PRJ-000125", "Main switchboard upgrade - Plant 2"],
    ["p4", "PRJ-000129", "LED retrofit - three warehouses"],
];
const proj = (id: string): Row => { const p = PROJECTS.find(x => x[0] === id)!; return { op365_code: p[1], op365_name: p[2], statecode: 0 }; };

const te = (id: string, res: string, resName: string, pid: string, node: [string, string, string] | null, day: string, hours: number, status: number, notes?: string): Row => ({
    op365_timeentryid: id, op365_entrydate: day, op365_hours: hours, statuscode: status, op365_notes: notes,
    _op365_projectid_value: pid, _op365_wbsnodeid_value: node?.[0], _op365_resourceid_value: res,
    op365_ProjectId: proj(pid), op365_WbsNodeId: node ? { op365_code: node[1], op365_name: node[2] } : null, op365_ResourceId: { op365_name: resName },
});
const N21: [string, string, string] = ["n21", "2.1", "Mounting structures"];
const N22: [string, string, string] = ["n22", "2.2", "PV modules"];
const SW: [string, string, string] = ["s3", "3", "Sub-distribution and wiring"];
const LED: [string, string, string] = ["l2", "2", "Fixture replacement"];
const MYWEEK: Row[] = [
    ...["2026-11-02", "2026-11-03", "2026-11-04"].map((d, i) => te(`w1${i}`, "r-me", "James Walker", PRJ, N22, d, 6, 1)),
    ...["2026-11-02", "2026-11-03", "2026-11-04"].map((d, i) => te(`w2${i}`, "r-me", "James Walker", "p3", SW, d, 2, 1)),
    te("w30", "r-me", "James Walker", "p4", LED, "2026-11-05", 8, 1),
    te("w31", "r-me", "James Walker", PRJ, N21, "2026-11-06", 4, 1),
];
const PENDING: Row[] = [
    te("a1", "r2", "Sophie Turner", PRJ, N22, "2026-10-26", 8, 365000000),
    te("a2", "r2", "Sophie Turner", PRJ, N22, "2026-10-27", 8, 365000000),
    te("a3", "r2", "Sophie Turner", PRJ, N21, "2026-10-28", 6, 365000000, "Rail alignment on the north roof"),
    te("a4", "r3", "Daniel Hughes", PRJ, N21, "2026-10-27", 8, 365000000),
    te("a5", "r3", "Daniel Hughes", PRJ, N21, "2026-10-28", 7.5, 365000000),
    te("a6", "r4", "Thomas Reed", PRJ, N21, "2026-10-29", 8, 365000000),
    te("a7", "r5", "Grace Mitchell", "p3", ["s1", "1", "Survey and design"], "2026-10-29", 4, 365000000, "As-built drawings"),
];

const RESOURCES: [string, string, number][] = [
    ["r1", "Oliver Bennett", 40], ["r-me", "James Walker", 40], ["r2", "Sophie Turner", 40], ["r3", "Daniel Hughes", 40],
    ["r4", "Thomas Reed", 40], ["r5", "Grace Mitchell", 40], ["r6", "Isla Ward", 32], ["r7", "Amelia Foster", 24],
];
const alloc = (res: string, h: number, s: string, e: string, pid: string): Row => ({
    _op365_resourceid_value: res, op365_hours: h,
    op365_WbsNodeId: { op365_startdate: s, op365_enddate: e, statecode: 0, op365_ProjectId: proj(pid) },
});
const ALLOC: Row[] = [
    alloc("r1", 220, "2026-11-02", "2026-12-24", "p2"), alloc("r1", 90, "2026-11-02", "2026-11-27", PRJ),
    alloc("r-me", 180, "2026-11-02", "2026-12-11", PRJ), alloc("r-me", 60, "2026-11-02", "2026-11-20", "p3"),
    alloc("r2", 180, "2026-11-02", "2026-12-11", PRJ), alloc("r2", 70, "2026-11-30", "2026-12-24", "p4"),
    alloc("r3", 200, "2026-11-02", "2026-11-27", PRJ), alloc("r3", 40, "2026-11-16", "2026-11-27", "p3"),
    alloc("r4", 160, "2026-11-02", "2026-12-04", "p2"),
    alloc("r5", 60, "2026-11-02", "2026-11-13", "p3"), alloc("r5", 80, "2026-11-16", "2026-12-18", PRJ),
    alloc("r6", 120, "2026-11-09", "2026-12-18", "p4"),
    alloc("r7", 40, "2026-12-07", "2026-12-24", PRJ),
];
const ABS: Row[] = [{ _op365_resourceid_value: "r4", op365_fromdate: "2026-11-23", op365_todate: "2026-11-27" },
    { _op365_resourceid_value: null, op365_fromdate: "2026-12-24", op365_todate: "2026-12-24" }];

const RFQ_LINES: Row[] = [
    ["l1", "PV module 450 Wp monocrystalline", 1000, "pcs", 1], ["l2", "Aluminium mounting rail 4.2 m", 640, "pcs", 2],
    ["l3", "String inverter 100 kW", 4, "pcs", 3], ["l4", "Solar cable 6 mm2", 2400, "m", 4],
].map(([id, name, q, u, s]) => ({ op365_purchaserequestlineid: id, op365_name: name, op365_quantity: q, op365_uom: u, op365_sortorder: s }));
const INV: Row[] = [
    ["i1", "Helios Energy Supplies", 365000001, 21], ["i2", "SunPeak Solar Distribution", 365000001, 14],
    ["i3", "Volt Electrical Wholesale", 365000001, 10], ["i4", "Sparkline Cables Ltd", 365000002, undefined],
].map(([id, name, st, dd]) => ({ op365_rfqinvitationid: id, op365_name: name, statuscode: st, op365_deliverydays: dd }));
const PRICES: Record<string, number[]> = { i1: [118, 31.5, 6950, 1.32], i2: [112.4, 33.9, 7120, 1.29], i3: [121.0, 29.8, 6880, 1.18] };
const QUOTES: Row[] = Object.entries(PRICES).flatMap(([inv, ps]) => ps.map((p, i) => ({
    _op365_invitationid_value: inv, _op365_requestlineid_value: `l${i + 1}`, op365_price: p, "cur.currencysymbol": "€",
})));

const page = (entities: Row[]) => Promise.resolve({ entities, nextLink: "" });
const webAPI = {
    retrieveMultipleRecords(table: string, query: string) {
        const q = decodeURIComponent(query);
        switch (table) {
            case "op365_wbsnode": return page(NODES);
            case "op365_wbsdependency": return page(LINKS);
            case "op365_baseline": return page([{ op365_baselineid: "b1", op365_name: "Contract baseline", op365_isreference: true }]);
            case "op365_baselinenode": return page(BASE);
            case "op365_resource":
                if (q.includes("_op365_userid_value")) return page([{ op365_resourceid: "r-me", op365_name: "James Walker", op365_weeklyhours: 40 }]);
                return page(RESOURCES.map(([id, name, h]) => ({ op365_resourceid: id, op365_name: name, op365_weeklyhours: h, op365_workingdays: "" })));
            case "op365_project": return page(PROJECTS.map(([id, code, name]) => ({ op365_projectid: id, op365_code: code, op365_name: name })));
            case "op365_timeentry":
                if (q.includes("aggregate")) return page([{ total: 30980 }]);
                return page(q.includes("statuscode eq 365000000") ? PENDING : MYWEEK);
            case "op365_materialusage": return page([{ total: 64000 }]);
            case "op365_wbsallocation": return page(ALLOC);
            case "op365_absence": return page(ABS);
            case "op365_purchaserequestline": return page(RFQ_LINES);
            case "op365_rfqinvitation": return page(INV);
            case "op365_rfqquote": return page(QUOTES);
        }
        return page([]);
    },
    retrieveRecord(table: string) {
        if (table === "op365_rfq") return Promise.resolve({ statuscode: 365000000, _op365_purchaserequestid_value: "pr1" });
        return Promise.resolve({
            op365_name: "Rooftop solar plant 450 kWp", op365_contractvalue: 380000, op365_progresspct: 34,
            op365_actualcost: 94980, op365_actualhours: 696, transactioncurrencyid: { currencysymbol: "€" },
        });
    },
    createRecord: () => Promise.resolve({}), updateRecord: () => Promise.resolve({}), deleteRecord: () => Promise.resolve({}),
};

const fmt = (v: number, d = 2) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
function ctx(control: keyof typeof STRINGS, entityId: string | undefined, width: number): unknown {
    const strings = STRINGS[control] as Record<string, string>;
    return {
        resources: { getString: (k: string) => strings[k] ?? k },
        webAPI,
        mode: { contextInfo: { entityId }, allocatedWidth: width, allocatedHeight: -1, isControlDisabled: false, trackContainerResize: () => undefined },
        userSettings: { userId: ME, languageId: 1033 },
        formatting: {
            formatCurrency: (v: number, _p?: number, sym?: string) => `${sym ?? "€"}${fmt(v)}`,
            formatDecimal: (v: number, p = 2) => fmt(v, p),
            formatDateShort: (d: Date) => d.toLocaleDateString("en-GB", { timeZone: "UTC" }),
        },
        navigation: { openForm: () => Promise.resolve() },
        parameters: { nodes: { refresh: () => undefined }, entries: { refresh: () => undefined }, resources: { refresh: () => undefined }, value: { raw: null } },
        updatedProperties: [],
    };
}

const which = new URLSearchParams(location.search).get("c");
const W = 1180;
function app(name: string | null): React.ReactElement {
    // only the known control names are rendered (?c= comes from the page URL)
    switch (name) {
        case "wbs": return <WbsTreeGridApp context={ctx("WbsTreeGrid", PRJ, W) as never} refreshKey={0} />;
        case "timesheet": return <WeeklyTimesheetApp context={ctx("WeeklyTimesheet", undefined, W) as never} refreshKey={0} />;
        case "approval": return <TimeApprovalApp context={ctx("TimeApproval", undefined, W) as never} refreshKey={0} />;
        case "load": return <ResourceLoadApp context={ctx("ResourceLoad", undefined, W) as never} refreshKey={0} />;
        case "cost": return <CostSummaryApp context={ctx("CostSummary", PRJ, W) as never} refreshKey={0} />;
        case "quotes": return <QuoteComparisonApp context={ctx("QuoteComparison", RFQ, W) as never} refreshKey={0} />;
        default: return <GanttChartApp context={ctx("GanttChart", PRJ, W) as never} refreshKey={0} />;
    }
}
ReactDOM.render(app(which), document.getElementById("root"));
