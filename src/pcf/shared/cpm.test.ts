import { criticalPath } from "./cpm";
import { isoDay, toDay } from "./dates";

describe("cpm", () => {
    it("finds the longest chain and the float of the others", () => {
        // A(1-5) -> B(6-10) -> D(11-12); A -> C(6-7) -> D
        const r = criticalPath(
            [{ id: "A", start: 1, end: 5 }, { id: "B", start: 6, end: 10 }, { id: "C", start: 6, end: 7 }, { id: "D", start: 11, end: 12 }],
            [{ predecessorId: "A", successorId: "B" }, { predecessorId: "A", successorId: "C" },
             { predecessorId: "B", successorId: "D" }, { predecessorId: "C", successorId: "D" }]);
        expect([...r.critical].sort()).toEqual(["A", "B", "D"]);
        expect(r.float.get("C")).toBe(3);
    });

    it("pushes successors after late predecessors, with lag", () => {
        const r = criticalPath([{ id: "A", start: 1, end: 10 }, { id: "B", start: 5, end: 6 }],
            [{ predecessorId: "A", successorId: "B", lagDays: 2 }]);
        expect(r.earlyStart.get("B")).toBe(13);
        expect(r.earlyFinish.get("B")).toBe(14);
        expect([...r.critical].sort()).toEqual(["A", "B"]);
    });

    it("leaves out loops and unknown tasks", () => {
        const r = criticalPath([{ id: "A", start: 1, end: 2 }, { id: "B", start: 1, end: 2 }, { id: "C", start: 1, end: 9 }],
            [{ predecessorId: "A", successorId: "B" }, { predecessorId: "B", successorId: "A" }, { predecessorId: "X", successorId: "C" }]);
        expect([...r.cyclic].sort()).toEqual(["A", "B"]);
        expect([...r.critical]).toEqual(["C"]);
    });
});

describe("dates", () => {
    it("round-trips date-only values", () => {
        const d = toDay("2026-10-24")!;
        expect(isoDay(d)).toBe("2026-10-24");
        expect(toDay("2026-10-24T00:00:00Z")).toBe(d);
        expect(toDay("")).toBeUndefined();
        expect(toDay(null)).toBeUndefined();
    });
});
