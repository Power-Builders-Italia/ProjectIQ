import { costSummary } from "./cost";
import { buildTree, WbsItem } from "./wbs";

const item = (id: string, parentId: string | undefined, budgetTotal: number, budgetHours = 0): WbsItem => ({
    id, parentId, code: id, name: "N" + id, progress: 0, budgetHours, budgetLabour: 0, budgetMaterials: 0, budgetOther: 0, budgetTotal,
});

test("branches roll up budget and actuals; EAC from progress", () => {
    const roots = buildTree([item("1", undefined, 0), item("1.1", "1", 600, 10), item("1.2", "1", 400, 5), item("2", undefined, 1000)]);
    const actuals = new Map([["1.1", { actualCost: 500, actualHours: 8 }], ["1.2", { actualCost: 100, actualHours: 2 }],
        ["2", { actualCost: 1200, actualHours: 0 }]]);
    const s = costSummary(roots, actuals, { contract: 3000, labour: 1000, materials: 800, progressPct: 60, unassignedCost: 0 });
    expect(s.lines.map(l => [l.code, l.budget, l.actual, l.budgetHours, l.actualHours])).toEqual([["1", 1000, 600, 15, 10], ["2", 1000, 1200, 0, 0]]);
    expect(s.lines[1].variance).toBe(200);
    expect(s.lines[0].spent).toBeCloseTo(0.6);
    expect(s.actual).toBe(1800);
    expect(s.eac).toBe(3000);
    expect(s.margin).toBe(0);
});

test("unassigned actuals get their own line; no progress -> EAC = max(budget, actual)", () => {
    const s = costSummary(buildTree([item("1", undefined, 500)]), new Map(), { contract: 0, labour: 0, materials: 0, progressPct: 0,
        unassignedCost: 700, unassignedHours: 3 });
    expect(s.lines).toHaveLength(2);
    expect(s.lines[1]).toMatchObject({ id: "", actual: 700, actualHours: 3 });
    expect(s.eac).toBe(700);
});
