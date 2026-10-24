// Cost summary of a project: budget against actual cost by top-level WBS branch, labour and materials split.
import { WbsNode } from "./wbs";

export interface CostLine {
    id: string;
    code: string;
    name: string;
    budget: number;
    actual: number;
    budgetHours: number;
    actualHours: number;
    /** actual - budget; positive = over budget. */
    variance: number;
    /** Share of budget spent (0 when no budget). */
    spent: number;
}

export interface CostSummary {
    lines: CostLine[];
    budget: number;
    actual: number;
    labour: number;
    materials: number;
    contract: number;
    /** Estimate at completion: actual / progress when progress > 0, else max(budget, actual). */
    eac: number;
    /** contract - eac. */
    margin: number;
}

export interface NodeActuals { actualCost: number; actualHours: number; }

function sumActuals(n: WbsNode, actuals: Map<string, NodeActuals>): NodeActuals {
    const own = actuals.get(n.id) ?? { actualCost: 0, actualHours: 0 };
    return n.children.reduce((acc, c) => {
        const a = sumActuals(c, actuals);
        return { actualCost: acc.actualCost + a.actualCost, actualHours: acc.actualHours + a.actualHours };
    }, { ...own });
}

export function costSummary(roots: WbsNode[], actuals: Map<string, NodeActuals>, totals: {
    contract: number; labour: number; materials: number; progressPct: number; unassignedCost?: number; unassignedHours?: number;
}): CostSummary {
    const lines: CostLine[] = roots.map(n => {
        const a = sumActuals(n, actuals);
        const budget = n.totalBudget;
        return {
            id: n.id, code: n.code, name: n.name, budget, actual: a.actualCost, budgetHours: n.totalHours,
            actualHours: a.actualHours, variance: a.actualCost - budget, spent: budget > 0 ? a.actualCost / budget : 0,
        };
    });
    if ((totals.unassignedCost ?? 0) > 0 || (totals.unassignedHours ?? 0) > 0) {
        const actual = totals.unassignedCost ?? 0;
        lines.push({ id: "", code: "", name: "", budget: 0, actual, budgetHours: 0, actualHours: totals.unassignedHours ?? 0,
            variance: actual, spent: 0 });
    }
    const budget = lines.reduce((s, l) => s + l.budget, 0);
    const actual = lines.reduce((s, l) => s + l.actual, 0);
    const eac = totals.progressPct > 0 ? actual / (totals.progressPct / 100) : Math.max(budget, actual);
    return { lines, budget, actual, labour: totals.labour, materials: totals.materials, contract: totals.contract, eac,
        margin: totals.contract - eac };
}
