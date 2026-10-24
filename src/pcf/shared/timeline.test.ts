import { bands, range } from "./timeline";
import { isoDay, toDay } from "./dates";

describe("timeline", () => {
    it("starts week view on a Monday", () => {
        const r = range(toDay("2026-10-24")!, toDay("2026-11-10")!, "week");
        expect(new Date(isoDay(r.start)).getUTCDay()).toBe(1);
        expect(r.start).toBeLessThanOrEqual(toDay("2026-10-17")!);
    });

    it("covers whole quarters", () => {
        const r = range(toDay("2026-05-10")!, toDay("2026-08-01")!, "quarter");
        expect(isoDay(r.start)).toBe("2026-04-01");
        expect(isoDay(r.end)).toBe("2026-09-30");
        const b = bands(r.start, r.end, "quarter");
        expect(b.lower.map(x => x.label)).toEqual(["Q2", "Q3"]);
        expect(b.upper.map(x => x.label)).toEqual(["2026"]);
    });

    it("labels months", () => {
        const r = range(toDay("2026-11-15")!, toDay("2027-01-20")!, "month");
        const b = bands(r.start, r.end, "month");
        expect(b.lower.map(x => x.label)).toEqual(["Nov", "Dec", "Jan"]);
        expect(b.upper.map(x => x.label)).toEqual(["2026", "2027"]);
    });
});
