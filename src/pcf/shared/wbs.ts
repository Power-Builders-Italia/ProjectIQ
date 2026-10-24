// WBS tree: builds the hierarchy from flat rows, rolls up totals and dates, flattens it for display.

export interface WbsItem {
    id: string;
    parentId?: string;
    code: string;
    name: string;
    start?: number; // day number, see dates.ts
    end?: number;
    progress: number;
    budgetHours: number;
    budgetLabour: number;
    budgetMaterials: number;
    budgetOther: number;
    budgetTotal: number;
    sortOrder?: number;
}

export interface WbsNode extends WbsItem {
    level: number;
    children: WbsNode[];
    /** Own values plus all descendants. */
    totalHours: number;
    totalBudget: number;
    /** Earliest start / latest end of the node and its descendants. */
    rollStart?: number;
    rollEnd?: number;
    /** Budget-weighted progress of the leaves below (own progress for a leaf). */
    rollProgress: number;
}

/** Natural order of outline codes: 1.2 < 1.10. */
export function compareCodes(a: string, b: string): number {
    const pa = a.split(/[.\-/ ]/), pb = b.split(/[.\-/ ]/);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
        if (pa[i] === undefined) return -1;
        if (pb[i] === undefined) return 1;
        const na = Number(pa[i]), nb = Number(pb[i]);
        const c = !isNaN(na) && !isNaN(nb) ? na - nb : pa[i].localeCompare(pb[i]);
        if (c !== 0) return c;
    }
    return 0;
}

function compareItems(a: WbsItem, b: WbsItem): number {
    const sa = a.sortOrder ?? Number.MAX_SAFE_INTEGER, sb = b.sortOrder ?? Number.MAX_SAFE_INTEGER;
    if (sa !== sb) return sa - sb;
    return compareCodes(a.code || "", b.code || "") || a.name.localeCompare(b.name);
}

/** Builds the tree. Rows whose parent is missing (or that would form a loop) become roots. */
export function buildTree(items: WbsItem[]): WbsNode[] {
    const nodes = new Map<string, WbsNode>();
    items.forEach(i => nodes.set(i.id, {
        ...i, level: 0, children: [], totalHours: 0, totalBudget: 0, rollProgress: 0,
    }));
    const roots: WbsNode[] = [];
    nodes.forEach(n => {
        let parent = n.parentId ? nodes.get(n.parentId) : undefined;
        // walk up to detect loops
        for (let p = parent, guard = 0; p && guard <= nodes.size; p = p.parentId ? nodes.get(p.parentId) : undefined, guard++) {
            if (p.id === n.id || guard === nodes.size) { parent = undefined; break; }
        }
        if (parent) parent.children.push(n); else roots.push(n);
    });
    const visit = (n: WbsNode, level: number): void => {
        n.level = level;
        n.children.sort(compareItems);
        n.children.forEach(c => visit(c, level + 1));
        n.totalHours = n.budgetHours + n.children.reduce((s, c) => s + c.totalHours, 0);
        n.totalBudget = n.budgetTotal + n.children.reduce((s, c) => s + c.totalBudget, 0);
        const starts = [n.start, ...n.children.map(c => c.rollStart)].filter((d): d is number => d !== undefined);
        const ends = [n.end, ...n.children.map(c => c.rollEnd)].filter((d): d is number => d !== undefined);
        n.rollStart = starts.length ? Math.min(...starts) : undefined;
        n.rollEnd = ends.length ? Math.max(...ends) : undefined;
        n.rollProgress = n.children.length ? progressOf(leaves(n)) : n.progress;
    };
    roots.sort(compareItems);
    roots.forEach(r => visit(r, 0));
    return roots;
}

export function leaves(n: WbsNode): WbsNode[] {
    return n.children.length ? n.children.flatMap(leaves) : [n];
}

/** Same rule as the WbsNodeRollup plugin: weight by budget, then hours, else plain average. */
export function progressOf(items: WbsItem[]): number {
    if (!items.length) return 0;
    let weight: (i: WbsItem) => number = () => 1;
    if (items.some(i => i.budgetTotal > 0)) weight = i => i.budgetTotal;
    else if (items.some(i => i.budgetHours > 0)) weight = i => i.budgetHours;
    const total = items.reduce((s, i) => s + weight(i), 0);
    return Math.round(items.reduce((s, i) => s + weight(i) * i.progress, 0) / total * 100) / 100;
}

/** Visible rows in display order; children of collapsed nodes are skipped. */
export function flatten(roots: WbsNode[], collapsed: Set<string>): WbsNode[] {
    const out: WbsNode[] = [];
    const walk = (n: WbsNode): void => {
        out.push(n);
        if (!collapsed.has(n.id)) n.children.forEach(walk);
    };
    roots.forEach(walk);
    return out;
}

/** Ids of the nodes that have children, to collapse everything at once. */
export function parentIds(roots: WbsNode[]): string[] {
    const out: string[] = [];
    const walk = (n: WbsNode): void => {
        if (n.children.length) out.push(n.id);
        n.children.forEach(walk);
    };
    roots.forEach(walk);
    return out;
}
