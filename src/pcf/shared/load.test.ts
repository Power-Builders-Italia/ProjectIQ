import { level, MONDAY, resourceLoad, weekday } from "./load";
import { toDay } from "./dates";

const monday = toDay("2026-03-02")!;
const amy = { id: "amy", name: "Amy", weeklyHours: 40, workingDays: [] };
const part = { id: "pat", name: "Pat", weeklyHours: 24, workingDays: [MONDAY, MONDAY + 2, MONDAY + 4] };

test("weekday", () => {
    expect(weekday(monday)).toBe(0);
    expect(weekday(monday + 6)).toBe(6);
});

test("capacity minus absences and company closures", () => {
    const rows = resourceLoad([amy, part], [], [
        { resourceId: "amy", from: monday, to: monday + 1 },          // 2 days off
        { resourceId: "amy", from: monday + 2, to: monday + 2, hours: 4 },
        { from: monday + 7, to: monday + 7 },                          // closure, both
    ], monday, 2);
    expect(rows[0].weeks.map(w => w.capacity)).toEqual([20, 32]);
    expect(rows[1].weeks.map(w => w.capacity)).toEqual([24, 16]);
});

test("allocations spread over working days, unscheduled kept apart", () => {
    const rows = resourceLoad([amy], [
        { resourceId: "amy", hours: 60, start: monday, end: monday + 13, projectName: "Alpha" }, // 10 working days
        { resourceId: "amy", hours: 8, projectName: "Beta" },
    ], [], monday, 2);
    expect(rows[0].weeks.map(w => w.load)).toEqual([30, 30]);
    expect(rows[0].weeks[0].projects.get("Alpha")).toBe(30);
    expect(rows[0].unscheduled).toBe(8);
});

test("levels", () => {
    expect(level({ capacity: 40, load: 10, projects: new Map() })).toBe("free");
    expect(level({ capacity: 40, load: 30, projects: new Map() })).toBe("ok");
    expect(level({ capacity: 40, load: 40, projects: new Map() })).toBe("full");
    expect(level({ capacity: 40, load: 41, projects: new Map() })).toBe("over");
    expect(level({ capacity: 0, load: 1, projects: new Map() })).toBe("over");
});
