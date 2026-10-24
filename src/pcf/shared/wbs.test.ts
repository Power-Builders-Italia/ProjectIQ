import { buildTree, compareCodes, flatten, parentIds, progressOf, WbsItem } from "./wbs";

const item = (id: string, code: string, extra: Partial<WbsItem> = {}): WbsItem => ({
    id, code, name: code, progress: 0, budgetHours: 0, budgetLabour: 0, budgetMaterials: 0, budgetOther: 0,
    budgetTotal: 0, ...extra,
});

describe("wbs", () => {
    it("orders codes naturally", () => {
        expect(["1.10", "1.2", "2", "1"].sort(compareCodes)).toEqual(["1", "1.2", "1.10", "2"]);
    });

    it("builds the tree with totals, dates and progress", () => {
        const roots = buildTree([
            item("b", "1.2", { parentId: "a", budgetTotal: 100, budgetHours: 10, progress: 0, start: 20, end: 30 }),
            item("a", "1", { budgetTotal: 50 }),
            item("c", "1.1", { parentId: "a", budgetTotal: 300, budgetHours: 5, progress: 100, start: 10, end: 15 }),
            item("d", "2"),
        ]);
        expect(roots.map(r => r.id)).toEqual(["a", "d"]);
        const a = roots[0];
        expect(a.children.map(c => c.id)).toEqual(["c", "b"]);
        expect(a.totalBudget).toBe(450);
        expect(a.totalHours).toBe(15);
        expect([a.rollStart, a.rollEnd]).toEqual([10, 30]);
        expect(a.rollProgress).toBe(75);
        expect(a.children[0].level).toBe(1);
    });

    it("turns orphans and loops into roots", () => {
        const roots = buildTree([item("x", "1", { parentId: "y" }), item("y", "2", { parentId: "x" }), item("z", "3", { parentId: "gone" })]);
        expect(roots.map(r => r.id).sort()).toEqual(["x", "y", "z"]);
    });

    it("hides children of collapsed nodes", () => {
        const roots = buildTree([item("a", "1"), item("b", "1.1", { parentId: "a" }), item("c", "1.1.1", { parentId: "b" })]);
        expect(flatten(roots, new Set()).map(n => n.id)).toEqual(["a", "b", "c"]);
        expect(flatten(roots, new Set(["b"])).map(n => n.id)).toEqual(["a", "b"]);
        expect(parentIds(roots)).toEqual(["a", "b"]);
    });

    it("falls back to hours and plain average for progress", () => {
        expect(progressOf([item("a", "1", { budgetHours: 30 }), item("b", "2", { budgetHours: 10, progress: 100 })])).toBe(25);
        expect(progressOf([item("a", "1"), item("b", "2", { progress: 100 })])).toBe(50);
        expect(progressOf([])).toBe(0);
    });
});
