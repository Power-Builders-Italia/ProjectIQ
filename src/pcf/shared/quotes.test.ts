import { compareQuotes, QuoteInvitation, QuoteLine } from "./quotes";

const lines: QuoteLine[] = [
    { id: "l2", name: "Inverter", quantity: 1, uom: "pcs", sortOrder: 2 },
    { id: "l1", name: "Panel", quantity: 10, uom: "pcs", sortOrder: 1 },
];
const invs: QuoteInvitation[] = [
    { id: "a", name: "Alpha", status: 365000001 },
    { id: "b", name: "Beta", status: 365000001 },
    { id: "c", name: "Gamma", status: 365000000 },
];

describe("compareQuotes", () => {
    it("marks the best unit price per line and orders lines", () => {
        const c = compareQuotes(lines, invs, [
            { invitationId: "a", lineId: "l1", price: 40 }, { invitationId: "b", lineId: "l1", price: 38 },
            { invitationId: "a", lineId: "l2", price: 900 }, { invitationId: "b", lineId: "l2", price: 1000 },
        ]);
        expect(c.rows.map(r => r.line.id)).toEqual(["l1", "l2"]);
        expect(c.rows[0].bestInvitationId).toBe("b");
        expect(c.rows[0].cells.get("b")).toEqual({ price: 38, amount: 380, best: true });
        expect(c.rows[0].cells.get("a")!.best).toBe(false);
        expect(c.rows[1].bestPrice).toBe(900);
    });

    it("picks the best total only among complete quotes", () => {
        const c = compareQuotes(lines, invs, [
            { invitationId: "a", lineId: "l1", price: 40 }, { invitationId: "a", lineId: "l2", price: 900 },  // 1300
            { invitationId: "b", lineId: "l1", price: 38 }, { invitationId: "b", lineId: "l2", price: 1000 }, // 1380
            { invitationId: "c", lineId: "l1", price: 1 },                                                    // incomplete
        ]);
        const t = new Map(c.totals.map(x => [x.invitation.id, x]));
        expect(t.get("a")).toMatchObject({ total: 1300, quoted: 2, complete: true, best: true });
        expect(t.get("b")).toMatchObject({ total: 1380, best: false });
        expect(t.get("c")).toMatchObject({ total: 10, complete: false, best: false });
    });

    it("handles no quotes", () => {
        const c = compareQuotes(lines, invs, []);
        expect(c.rows.every(r => r.bestPrice === undefined)).toBe(true);
        expect(c.totals.every(t => !t.best && t.total === 0)).toBe(true);
    });
});
