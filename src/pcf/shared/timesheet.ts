// Weekly timesheet: entries of one week arranged as project / WBS node rows by weekday.

export const STATUS = { draft: 1, submitted: 365000000, approved: 365000001, rejected: 365000002 } as const;

export interface TimeEntry {
    id: string;
    projectId: string;
    projectName: string;
    nodeId?: string;
    nodeName?: string;
    day: number;
    hours: number;
    status: number;
}

export interface Cell {
    hours: number;
    /** Entries of the cell; a cell can be edited only when it holds at most one entry. */
    entries: TimeEntry[];
}

export interface TimesheetRow {
    key: string;
    projectId: string;
    projectName: string;
    nodeId?: string;
    nodeName?: string;
    cells: Cell[];
    total: number;
}

export interface Timesheet {
    rows: TimesheetRow[];
    dayTotals: number[];
    total: number;
}

/** Monday of the week of a day number (day 0 = Thursday 1970-01-01). */
export function weekStart(day: number): number {
    return day - (((day + 3) % 7) + 7) % 7;
}

export const rowKey = (projectId: string, nodeId?: string): string => `${projectId}|${nodeId ?? ""}`;

export const isEditable = (status: number): boolean => status === STATUS.draft || status === STATUS.rejected;

export function cellEditable(cell: Cell): boolean {
    return cell.entries.length <= 1 && cell.entries.every(e => isEditable(e.status));
}

/** Builds the grid of the week starting on `monday`; `extra` adds empty rows (lines the user added). */
export function buildTimesheet(entries: TimeEntry[], monday: number,
    extra: Omit<TimesheetRow, "cells" | "total" | "key">[] = []): Timesheet {
    const rows = new Map<string, TimesheetRow>();
    const add = (r: Omit<TimesheetRow, "cells" | "total" | "key">): TimesheetRow => {
        const key = rowKey(r.projectId, r.nodeId);
        let row = rows.get(key);
        if (!row) {
            row = { ...r, key, cells: Array.from({ length: 7 }, () => ({ hours: 0, entries: [] })), total: 0 };
            rows.set(key, row);
        }
        return row;
    };
    entries.filter(e => e.day >= monday && e.day < monday + 7).forEach(e => {
        const cell = add(e).cells[e.day - monday];
        cell.entries.push(e);
        cell.hours += e.hours;
    });
    extra.forEach(add);
    const list = [...rows.values()].sort((a, b) =>
        a.projectName.localeCompare(b.projectName) || (a.nodeName ?? "").localeCompare(b.nodeName ?? ""));
    const dayTotals = Array<number>(7).fill(0);
    list.forEach(r => {
        r.total = r.cells.reduce((s, c) => s + c.hours, 0);
        r.cells.forEach((c, i) => { dayTotals[i] += c.hours; });
    });
    return { rows: list, dayTotals, total: dayTotals.reduce((s, h) => s + h, 0) };
}

export type Change =
    | { kind: "create"; projectId: string; nodeId?: string; dayIndex: number; hours: number }
    | { kind: "update"; id: string; hours: number }
    | { kind: "delete"; id: string }
    | { kind: "none" };

/** What saving `hours` in a cell means for its (single) entry. */
export function cellChange(row: TimesheetRow, dayIndex: number, hours: number): Change {
    const entry = row.cells[dayIndex].entries[0];
    if (!entry) return hours > 0 ? { kind: "create", projectId: row.projectId, nodeId: row.nodeId, dayIndex, hours } : { kind: "none" };
    if (hours <= 0) return { kind: "delete", id: entry.id };
    return hours === entry.hours ? { kind: "none" } : { kind: "update", id: entry.id, hours };
}

/** Entries of the week that can be submitted (draft or rejected). */
export function submittable(sheet: Timesheet): string[] {
    return sheet.rows.flatMap(r => r.cells.flatMap(c => c.entries.filter(e => isEditable(e.status)).map(e => e.id)));
}

/** Parses a typed number of hours: comma or dot decimals, 0-24, quarter hours; undefined when invalid. */
export function parseHours(text: string): number | undefined {
    const t = text.trim().replace(",", ".");
    if (t === "") return 0;
    const n = Number(t);
    if (!isFinite(n) || n < 0 || n > 24) return undefined;
    return Math.round(n * 4) / 4;
}
