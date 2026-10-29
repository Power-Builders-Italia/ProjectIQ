// Portfolio and project health: the same figures as the Project form (budget, actual, committed, progress)
// turned into a traffic light with the reasons behind it.

/** Project status reasons (statuscode). */
export const PROJECT_STATUS = { inProgress: 1, closed: 2, offer: 365000000, suspended: 365000001 } as const;

export interface ProjectFigures {
  id: string;
  code: string;
  name: string;
  customer?: string;
  manager?: string;
  managerId?: string;
  status: number;
  start?: number; // day number, see projectiq/dates.ts
  end?: number;
  contract: number;
  budget: number;
  actual: number;
  committed: number;
  /** 0-100, rolled up from the WBS by the WbsNodeRollup plugin. */
  progress: number;
  actualHours: number;
}

export type HealthLevel = 'onTrack' | 'atRisk' | 'offTrack' | 'notTracked';

export type HealthReason =
  | 'overBudget'        // actual + committed above budget
  | 'budgetNearlyUsed'  // actual + committed at 90% of budget or more
  | 'eacOverBudget'     // estimate at completion above budget
  | 'negativeMargin'    // estimate at completion above contract value
  | 'pastEndDate'       // end date past, progress below 100%
  | 'behindSchedule'    // progress more than 20 points behind elapsed time
  | 'suspended'
  | 'noBudget';

export interface ProjectHealth {
  level: HealthLevel;
  reasons: HealthReason[];
  /** (actual + committed) / budget; 0 without budget. */
  budgetUsed: number;
  remaining: number;
  /** Estimate at completion: actual / progress when progress > 0, else max(budget, actual) (same rule as the Cost Summary). */
  eac: number;
  /** contract - eac. */
  margin: number;
  /** Share of the planned duration already elapsed, 0-1; undefined without dates. */
  elapsed?: number;
}

const OFF: HealthReason[] = ['overBudget', 'negativeMargin', 'pastEndDate'];
const RISK: HealthReason[] = ['budgetNearlyUsed', 'eacOverBudget', 'behindSchedule', 'suspended', 'noBudget'];

export function estimateAtCompletion(p: Pick<ProjectFigures, 'actual' | 'budget' | 'progress'>): number {
  return p.progress > 0 ? p.actual / (p.progress / 100) : Math.max(p.budget, p.actual);
}

export function projectHealth(p: ProjectFigures, today: number): ProjectHealth {
  const spent = p.actual + p.committed;
  const budgetUsed = p.budget > 0 ? spent / p.budget : 0;
  const eac = estimateAtCompletion(p);
  const margin = p.contract - eac;
  const elapsed = p.start !== undefined && p.end !== undefined && p.end >= p.start
    ? Math.min(1, Math.max(0, (today - p.start + 1) / (p.end - p.start + 1)))
    : undefined;
  const base = { budgetUsed, remaining: p.budget - spent, eac, margin, elapsed };
  if (p.status === PROJECT_STATUS.offer || p.status === PROJECT_STATUS.closed) {
    return { level: 'notTracked', reasons: [], ...base };
  }
  const reasons: HealthReason[] = [];
  if (p.status === PROJECT_STATUS.suspended) reasons.push('suspended');
  if (p.budget <= 0) reasons.push('noBudget');
  else if (spent > p.budget) reasons.push('overBudget');
  else if (budgetUsed >= 0.9) reasons.push('budgetNearlyUsed');
  if (p.budget > 0 && p.progress > 0 && eac > p.budget && spent <= p.budget) reasons.push('eacOverBudget');
  if (p.contract > 0 && p.progress > 0 && eac > p.contract) reasons.push('negativeMargin');
  if (p.end !== undefined && p.end < today && p.progress < 100) reasons.push('pastEndDate');
  else if (elapsed !== undefined && elapsed * 100 - p.progress > 20) reasons.push('behindSchedule');
  const level: HealthLevel = reasons.some(r => OFF.indexOf(r) >= 0) ? 'offTrack'
    : reasons.some(r => RISK.indexOf(r) >= 0) ? 'atRisk' : 'onTrack';
  return { level, reasons, ...base };
}

export interface PortfolioRow extends ProjectFigures {
  health: ProjectHealth;
}

export interface PortfolioSummary {
  rows: PortfolioRow[];
  contract: number;
  budget: number;
  actual: number;
  committed: number;
  eac: number;
  margin: number;
  counts: Record<HealthLevel, number>;
}

const LEVEL_ORDER: Record<HealthLevel, number> = { offTrack: 0, atRisk: 1, onTrack: 2, notTracked: 3 };

/** Health of every project, worst first; totals cover the tracked (In Progress and Suspended) projects only. */
export function portfolioSummary(projects: ProjectFigures[], today: number): PortfolioSummary {
  const rows = projects.map(p => ({ ...p, health: projectHealth(p, today) }))
    .sort((a, b) => LEVEL_ORDER[a.health.level] - LEVEL_ORDER[b.health.level]
      || a.health.margin - b.health.margin || a.code.localeCompare(b.code));
  const tracked = rows.filter(r => r.health.level !== 'notTracked');
  const sum = (f: (r: PortfolioRow) => number): number => tracked.reduce((s, r) => s + f(r), 0);
  const counts: Record<HealthLevel, number> = { onTrack: 0, atRisk: 0, offTrack: 0, notTracked: 0 };
  rows.forEach(r => { counts[r.health.level]++; });
  return {
    rows,
    contract: sum(r => r.contract),
    budget: sum(r => r.budget),
    actual: sum(r => r.actual),
    committed: sum(r => r.committed),
    eac: sum(r => r.health.eac),
    margin: sum(r => r.health.margin),
    counts,
  };
}

/** Projects whose code or name matches the text (code first, exact before partial). */
export function matchProjects<T extends Pick<ProjectFigures, 'code' | 'name'>>(projects: T[], text: string | undefined): T[] {
  const q = (text || '').trim().toLowerCase();
  if (!q) return [];
  const exact = projects.filter(p => p.code.toLowerCase() === q || p.name.toLowerCase() === q);
  if (exact.length) return exact;
  return projects.filter(p => p.code.toLowerCase().indexOf(q) >= 0 || p.name.toLowerCase().indexOf(q) >= 0);
}
