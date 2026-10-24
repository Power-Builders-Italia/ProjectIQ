// Resource load: allocated WBS hours against capacity (weekly hours minus absences), by week.

/** Working Days choice values, Monday (365000000) to Sunday (365000006). */
export const MONDAY = 365000000;

export interface LoadResource {
    id: string;
    name: string;
    weeklyHours: number;
    /** Working Days choice values; empty = Monday to Friday. */
    workingDays: number[];
}

export interface LoadAllocation {
    resourceId: string;
    hours: number;
    start?: number;
    end?: number;
    projectName: string;
}

export interface LoadAbsence {
    /** Empty = company closure. */
    resourceId?: string;
    from: number;
    to: number;
    /** Hours of a single-day absence; empty = whole days. */
    hours?: number;
}

export interface WeekLoad {
    capacity: number;
    load: number;
    /** Allocated hours by project name. */
    projects: Map<string, number>;
}

export interface ResourceLoadRow {
    resource: LoadResource;
    weeks: WeekLoad[];
    /** Allocations without dates, not placed on the calendar. */
    unscheduled: number;
}

/** Weekday index of a day number, 0 = Monday. */
export const weekday = (day: number): number => (((day + 3) % 7) + 7) % 7;

function workdays(r: LoadResource): Set<number> {
    const days = r.workingDays.length ? r.workingDays.map(v => v - MONDAY) : [0, 1, 2, 3, 4];
    return new Set(days);
}

/** Capacity and allocated hours of each resource for `weeks` weeks from the Monday `first`. */
export function resourceLoad(resources: LoadResource[], allocations: LoadAllocation[], absences: LoadAbsence[],
    first: number, weeks: number): ResourceLoadRow[] {
    const last = first + weeks * 7 - 1;
    return resources.map(resource => {
        const days = workdays(resource);
        const daily = days.size ? resource.weeklyHours / days.size : 0;
        const rows: WeekLoad[] = Array.from({ length: weeks }, () => ({ capacity: 0, load: 0, projects: new Map() }));
        const off = new Map<number, number>(); // day -> hours off
        absences.filter(a => !a.resourceId || a.resourceId === resource.id).forEach(a => {
            for (let d = Math.max(a.from, first); d <= Math.min(a.to, last); d++) {
                if (!days.has(weekday(d))) continue;
                const hours = a.hours !== undefined && a.from === a.to ? Math.min(a.hours, daily) : daily;
                off.set(d, Math.min(daily, (off.get(d) ?? 0) + hours));
            }
        });
        for (let d = first; d <= last; d++) {
            if (days.has(weekday(d))) rows[Math.floor((d - first) / 7)].capacity += daily - (off.get(d) ?? 0);
        }
        let unscheduled = 0;
        allocations.filter(a => a.resourceId === resource.id).forEach(a => {
            if (a.start === undefined || a.end === undefined || a.end < a.start) { unscheduled += a.hours; return; }
            const span: number[] = [];
            for (let d = a.start; d <= a.end; d++) if (days.has(weekday(d))) span.push(d);
            if (!span.length) span.push(a.start);
            const perDay = a.hours / span.length;
            span.filter(d => d >= first && d <= last).forEach(d => {
                const w = rows[Math.floor((d - first) / 7)];
                w.load += perDay;
                w.projects.set(a.projectName, (w.projects.get(a.projectName) ?? 0) + perDay);
            });
        });
        return { resource, weeks: rows, unscheduled };
    });
}

export type LoadLevel = "free" | "ok" | "full" | "over";

/** Utilisation band: under 50%, up to 90%, up to 100%, over 100%. */
export function level(w: WeekLoad): LoadLevel {
    if (w.capacity <= 0) return w.load > 0 ? "over" : "free";
    const pct = w.load / w.capacity;
    return pct > 1.0001 ? "over" : pct >= 0.9 ? "full" : pct >= 0.5 ? "ok" : "free";
}
