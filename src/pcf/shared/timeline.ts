// Time scale of the Gantt: pixels per day and header bands for each zoom level.
import { fromDay, toDay } from "./dates";

export type Zoom = "week" | "month" | "quarter";

export const PX_PER_DAY: Record<Zoom, number> = { week: 18, month: 5, quarter: 1.8 };

export interface Band { start: number; end: number; label: string; }

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthStart(day: number): number {
    const d = fromDay(day);
    return toDay(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)))!;
}

function addMonths(day: number, n: number): number {
    const d = fromDay(day);
    return toDay(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + n, 1)))!;
}

/** Visible range: whole periods around [start, end] with a small margin. */
export function range(start: number, end: number, zoom: Zoom): { start: number; end: number } {
    if (zoom === "week") {
        const s = start - 7, e = end + 7;
        const monday = s - ((fromDay(s).getUTCDay() + 6) % 7);
        return { start: monday, end: e };
    }
    let s = monthStart(start - 1);
    let e = addMonths(monthStart(end), 1);
    if (zoom === "quarter") {
        s = addMonths(s, -(fromDay(s).getUTCMonth() % 3));
        e = addMonths(e, (3 - (fromDay(e).getUTCMonth() % 3)) % 3);
    }
    return { start: s, end: e - 1 };
}

/** Upper band (months or years) and lower band (weeks, months or quarters). */
export function bands(start: number, end: number, zoom: Zoom): { upper: Band[]; lower: Band[] } {
    const upper: Band[] = [], lower: Band[] = [];
    if (zoom === "week") {
        for (let m = monthStart(start); m <= end; m = addMonths(m, 1)) {
            const d = fromDay(m);
            upper.push({ start: Math.max(m, start), end: Math.min(addMonths(m, 1) - 1, end), label: `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}` });
        }
        for (let w = start; w <= end; w += 7) {
            lower.push({ start: w, end: Math.min(w + 6, end), label: String(fromDay(w).getUTCDate()) });
        }
    } else {
        for (let m = monthStart(start); m <= end; m = addMonths(m, 1)) {
            const d = fromDay(m);
            if (d.getUTCMonth() === 0 || m === monthStart(start)) {
                const yearEnd = toDay(new Date(Date.UTC(d.getUTCFullYear() + 1, 0, 1)))! - 1;
                upper.push({ start: Math.max(m, start), end: Math.min(yearEnd, end), label: String(d.getUTCFullYear()) });
            }
            if (zoom === "month") {
                lower.push({ start: m, end: Math.min(addMonths(m, 1) - 1, end), label: MONTHS[d.getUTCMonth()] });
            } else if (d.getUTCMonth() % 3 === 0) {
                lower.push({ start: m, end: Math.min(addMonths(m, 3) - 1, end), label: `Q${d.getUTCMonth() / 3 + 1}` });
            }
        }
    }
    return { upper, lower };
}
