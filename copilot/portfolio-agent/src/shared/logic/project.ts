// Project detail: top-level WBS phases with their flags, baseline slippage and timeline rows with the critical path.
import { buildTree, leaves, type WbsItem, type WbsNode } from '../projectiq/wbs';
import { criticalPath, type CpmLink } from '../projectiq/cpm';
import type { NodeActuals } from '../projectiq/cost';

export interface PhaseRow {
  node: WbsNode;
  actualCost: number;
  actualHours: number;
  /** Actual hours above budget hours. */
  hoursOverrun: boolean;
  /** End date passed and not complete. */
  late: boolean;
  /** Days between the current end and the reference baseline end (positive = later). */
  slipDays?: number;
  /** Budget minus baseline budget. */
  budgetDelta?: number;
}

export interface BaselineNode { start?: number; end?: number; budget: number; }

function sumActuals(n: WbsNode, actuals: Map<string, NodeActuals>): NodeActuals {
  const own = actuals.get(n.id) ?? { actualCost: 0, actualHours: 0 };
  return n.children.reduce((acc, c) => {
    const a = sumActuals(c, actuals);
    return { actualCost: acc.actualCost + a.actualCost, actualHours: acc.actualHours + a.actualHours };
  }, { ...own });
}

/** Baseline values of a branch: the node's own saved row, else the sum / span of its descendants'. */
function baselineOf(n: WbsNode, baseline: Map<string, BaselineNode>): BaselineNode | undefined {
  const own = baseline.get(n.id);
  const kids = n.children.map(c => baselineOf(c, baseline)).filter((b): b is BaselineNode => !!b);
  if (!own && !kids.length) return undefined;
  const ends = [own?.end, ...kids.map(k => k.end)].filter((d): d is number => d !== undefined);
  const starts = [own?.start, ...kids.map(k => k.start)].filter((d): d is number => d !== undefined);
  return {
    start: starts.length ? Math.min(...starts) : undefined,
    end: ends.length ? Math.max(...ends) : undefined,
    budget: (own?.budget ?? 0) + kids.reduce((s, k) => s + k.budget, 0),
  };
}

export function projectPhases(items: WbsItem[], actuals: Map<string, NodeActuals>, today: number,
  baseline?: Map<string, BaselineNode>): PhaseRow[] {
  return buildTree(items).map(node => {
    const a = sumActuals(node, actuals);
    const b = baseline ? baselineOf(node, baseline) : undefined;
    return {
      node,
      actualCost: a.actualCost,
      actualHours: a.actualHours,
      hoursOverrun: node.totalHours > 0 && a.actualHours > node.totalHours,
      late: node.rollEnd !== undefined && node.rollEnd < today && node.rollProgress < 100,
      slipDays: b?.end !== undefined && node.rollEnd !== undefined ? node.rollEnd - b.end : undefined,
      budgetDelta: b ? node.totalBudget - b.budget : undefined,
    };
  });
}

export interface TimelineRow {
  node: WbsNode;
  start?: number;
  end?: number;
  baselineStart?: number;
  baselineEnd?: number;
  critical: boolean;
  /** Earliest finish after the dependencies, when later than the planned end. */
  pushedEnd?: number;
  late: boolean;
}

/**
 * Rows of the timeline down to `depth` levels (0 = phases only). The critical path is computed on the leaves with
 * their dependencies, as in the Gantt Chart control; a summary row is critical when one of its leaves is.
 */
export function timelineRows(items: WbsItem[], links: CpmLink[], today: number, depth: number,
  baseline?: Map<string, BaselineNode>): { rows: TimelineRow[]; start?: number; end?: number } {
  const roots = buildTree(items);
  const allLeaves = roots.flatMap(leaves).filter(l => l.start !== undefined && l.end !== undefined);
  const cpm = criticalPath(allLeaves.map(l => ({ id: l.id, start: l.start as number, end: l.end as number })), links);
  const rows: TimelineRow[] = [];
  const walk = (n: WbsNode): void => {
    const ls = leaves(n);
    const pushed = ls.map(l => cpm.earlyFinish.get(l.id)).filter((d): d is number => d !== undefined);
    const pushedEnd = pushed.length ? Math.max(...pushed) : undefined;
    const b = baseline ? baselineOf(n, baseline) : undefined;
    rows.push({
      node: n,
      start: n.rollStart,
      end: n.rollEnd,
      baselineStart: b?.start,
      baselineEnd: b?.end,
      critical: ls.some(l => cpm.critical.has(l.id)),
      pushedEnd: pushedEnd !== undefined && n.rollEnd !== undefined && pushedEnd > n.rollEnd ? pushedEnd : undefined,
      late: n.rollEnd !== undefined && n.rollEnd < today && n.rollProgress < 100,
    });
    if (n.level < depth) n.children.forEach(walk);
  };
  roots.forEach(walk);
  const starts = rows.map(r => Math.min(r.start ?? Infinity, r.baselineStart ?? Infinity)).filter(isFinite);
  const ends = rows.map(r => Math.max(r.end ?? -Infinity, r.baselineEnd ?? -Infinity, r.pushedEnd ?? -Infinity)).filter(isFinite);
  return { rows, start: starts.length ? Math.min(...starts) : undefined, end: ends.length ? Math.max(...ends) : undefined };
}
