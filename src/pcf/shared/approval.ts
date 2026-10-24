// Time approval: submitted entries grouped by resource and week.
import { weekStart } from "./timesheet";

export interface PendingEntry {
    id: string;
    resourceId: string;
    resourceName: string;
    projectName: string;
    nodeName?: string;
    day: number;
    hours: number;
    notes?: string;
}

export interface ApprovalGroup {
    key: string;
    resourceId: string;
    resourceName: string;
    weekStart: number;
    hours: number;
    /** Hours by project name. */
    projects: { name: string; hours: number }[];
    entries: PendingEntry[];
}

export function groupForApproval(entries: PendingEntry[]): ApprovalGroup[] {
    const groups = new Map<string, ApprovalGroup>();
    entries.forEach(e => {
        const week = weekStart(e.day);
        const key = `${e.resourceId}|${week}`;
        let g = groups.get(key);
        if (!g) {
            g = { key, resourceId: e.resourceId, resourceName: e.resourceName, weekStart: week, hours: 0, projects: [], entries: [] };
            groups.set(key, g);
        }
        g.entries.push(e);
        g.hours += e.hours;
        const p = g.projects.find(x => x.name === e.projectName);
        if (p) p.hours += e.hours; else g.projects.push({ name: e.projectName, hours: e.hours });
    });
    const list = [...groups.values()];
    list.forEach(g => {
        g.entries.sort((a, b) => a.day - b.day || a.projectName.localeCompare(b.projectName));
        g.projects.sort((a, b) => b.hours - a.hours);
    });
    return list.sort((a, b) => a.weekStart - b.weekStart || a.resourceName.localeCompare(b.resourceName));
}

/** Ids of the entries of the selected groups and of the individually selected entries, without duplicates. */
export function selectedIds(groups: ApprovalGroup[], groupKeys: Set<string>, entryIds: Set<string>): string[] {
    const ids = new Set<string>();
    groups.forEach(g => g.entries.forEach(e => { if (groupKeys.has(g.key) || entryIds.has(e.id)) ids.add(e.id); }));
    return [...ids];
}
