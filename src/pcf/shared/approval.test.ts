import { groupForApproval, PendingEntry, selectedIds } from "./approval";
import { toDay } from "./dates";

const monday = toDay("2026-03-02")!;
const e = (id: string, resource: string, day: number, hours: number, project = "Alpha"): PendingEntry =>
    ({ id, resourceId: resource, resourceName: resource.toUpperCase(), projectName: project, day, hours });

test("groups by resource and week, sorted by week then name", () => {
    const groups = groupForApproval([e("1", "bob", monday + 1, 8), e("2", "amy", monday, 4), e("3", "bob", monday, 2, "Beta"),
        e("4", "bob", monday + 7, 1)]);
    expect(groups.map(g => g.key)).toEqual([`amy|${monday}`, `bob|${monday}`, `bob|${monday + 7}`]);
    expect(groups[1].hours).toBe(10);
    expect(groups[1].projects).toEqual([{ name: "Alpha", hours: 8 }, { name: "Beta", hours: 2 }]);
    expect(groups[1].entries.map(x => x.id)).toEqual(["3", "1"]);
});

test("selection merges groups and single entries", () => {
    const groups = groupForApproval([e("1", "bob", monday, 8), e("2", "bob", monday + 1, 4), e("3", "amy", monday, 4)]);
    expect(selectedIds(groups, new Set([`bob|${monday}`]), new Set(["1", "3"])).sort()).toEqual(["1", "2", "3"]);
});
