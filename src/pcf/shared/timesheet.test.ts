import { buildTimesheet, cellChange, cellEditable, parseHours, STATUS, submittable, TimeEntry, weekStart } from "./timesheet";
import { toDay } from "./dates";

const monday = toDay("2026-03-02")!;
const e = (id: string, day: number, hours: number, status: number = STATUS.draft, nodeId?: string): TimeEntry =>
    ({ id, projectId: "p1", projectName: "Alpha", nodeId, nodeName: nodeId ? "Task " + nodeId : undefined, day, hours, status });

test("week starts on Monday", () => {
    expect(weekStart(monday)).toBe(monday);
    expect(weekStart(monday + 6)).toBe(monday);
    expect(weekStart(monday + 7)).toBe(monday + 7);
    expect(weekStart(toDay("1970-01-01")!)).toBe(toDay("1969-12-29"));
});

test("grid groups by project and node, totals by day", () => {
    const sheet = buildTimesheet([e("a", monday, 4), e("b", monday, 2), e("c", monday + 1, 8, STATUS.draft, "n1"), e("x", monday + 7, 5)], monday);
    expect(sheet.rows.map(r => r.key)).toEqual(["p1|", "p1|n1"]);
    expect(sheet.rows[0].cells[0].hours).toBe(6);
    expect(sheet.dayTotals.slice(0, 2)).toEqual([6, 8]);
    expect(sheet.total).toBe(14);
    expect(cellEditable(sheet.rows[0].cells[0])).toBe(false); // two entries
    expect(cellEditable(sheet.rows[1].cells[1])).toBe(true);
});

test("extra rows are kept empty", () => {
    const sheet = buildTimesheet([], monday, [{ projectId: "p2", projectName: "Beta" }]);
    expect(sheet.rows).toHaveLength(1);
    expect(sheet.rows[0].total).toBe(0);
});

test("cell changes", () => {
    const sheet = buildTimesheet([e("a", monday, 4)], monday, [{ projectId: "p2", projectName: "Beta" }]);
    const [alpha, beta] = sheet.rows;
    expect(cellChange(alpha, 0, 6)).toEqual({ kind: "update", id: "a", hours: 6 });
    expect(cellChange(alpha, 0, 0)).toEqual({ kind: "delete", id: "a" });
    expect(cellChange(alpha, 0, 4)).toEqual({ kind: "none" });
    expect(cellChange(beta, 2, 3)).toEqual({ kind: "create", projectId: "p2", nodeId: undefined, dayIndex: 2, hours: 3 });
    expect(cellChange(beta, 2, 0)).toEqual({ kind: "none" });
});

test("only draft and rejected entries are submitted or edited", () => {
    const sheet = buildTimesheet([e("a", monday, 4), e("b", monday + 1, 4, STATUS.submitted), e("c", monday + 2, 4, STATUS.rejected),
        e("d", monday + 3, 4, STATUS.approved)], monday);
    expect(submittable(sheet).sort()).toEqual(["a", "c"]);
    expect(cellEditable(sheet.rows[0].cells[1])).toBe(false);
});

test("hours parsing", () => {
    expect(parseHours("7,5")).toBe(7.5);
    expect(parseHours("")).toBe(0);
    expect(parseHours("8.1")).toBe(8);
    expect(parseHours("25")).toBeUndefined();
    expect(parseHours("abc")).toBeUndefined();
});
