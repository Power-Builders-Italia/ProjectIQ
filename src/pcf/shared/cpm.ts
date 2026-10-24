// Critical path method on the WBS leaves (finish-to-start links with lag).
// Durations come from the planned dates; a task never starts before its planned start.

export interface CpmTask {
    id: string;
    start: number; // day number, inclusive
    end: number;   // day number, inclusive
}

export interface CpmLink {
    predecessorId: string;
    successorId: string;
    lagDays?: number;
}

export interface CpmResult {
    /** Earliest start / finish (inclusive) after the dependencies are applied. */
    earlyStart: Map<string, number>;
    earlyFinish: Map<string, number>;
    /** Total float in days. */
    float: Map<string, number>;
    critical: Set<string>;
    /** Tasks left out because they sit on a dependency loop. */
    cyclic: Set<string>;
}

export function criticalPath(tasks: CpmTask[], links: CpmLink[]): CpmResult {
    const byId = new Map(tasks.map(t => [t.id, t]));
    const valid = links.filter(l => byId.has(l.predecessorId) && byId.has(l.successorId) && l.predecessorId !== l.successorId);
    const succ = new Map<string, CpmLink[]>(), pred = new Map<string, CpmLink[]>();
    tasks.forEach(t => { succ.set(t.id, []); pred.set(t.id, []); });
    valid.forEach(l => { succ.get(l.predecessorId)!.push(l); pred.get(l.successorId)!.push(l); });

    // Kahn topological order; whatever remains is on a loop
    const indeg = new Map(tasks.map(t => [t.id, pred.get(t.id)!.length]));
    const queue = tasks.filter(t => indeg.get(t.id) === 0).map(t => t.id);
    const order: string[] = [];
    while (queue.length) {
        const id = queue.shift()!;
        order.push(id);
        succ.get(id)!.forEach(l => {
            const d = indeg.get(l.successorId)! - 1;
            indeg.set(l.successorId, d);
            if (d === 0) queue.push(l.successorId);
        });
    }
    const inOrder = new Set(order);
    const cyclic = new Set(tasks.filter(t => !inOrder.has(t.id)).map(t => t.id));

    const duration = (id: string): number => byId.get(id)!.end - byId.get(id)!.start + 1;
    const es = new Map<string, number>(), ef = new Map<string, number>();
    order.forEach(id => {
        let start = byId.get(id)!.start;
        pred.get(id)!.forEach(l => {
            if (ef.has(l.predecessorId)) start = Math.max(start, ef.get(l.predecessorId)! + 1 + (l.lagDays ?? 0));
        });
        es.set(id, start);
        ef.set(id, start + duration(id) - 1);
    });

    const projectEnd = order.length ? Math.max(...order.map(id => ef.get(id)!)) : 0;
    const lf = new Map<string, number>();
    [...order].reverse().forEach(id => {
        let finish = projectEnd;
        succ.get(id)!.forEach(l => {
            if (lf.has(l.successorId)) {
                const ls = lf.get(l.successorId)! - duration(l.successorId) + 1;
                finish = Math.min(finish, ls - 1 - (l.lagDays ?? 0));
            }
        });
        lf.set(id, finish);
    });

    const float = new Map<string, number>();
    const critical = new Set<string>();
    order.forEach(id => {
        const f = lf.get(id)! - ef.get(id)!;
        float.set(id, f);
        if (f <= 0) critical.add(id);
    });
    return { earlyStart: es, earlyFinish: ef, float, critical, cyclic };
}
