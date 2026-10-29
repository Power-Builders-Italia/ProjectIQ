import type { HealthReason } from '../logic/portfolio';

export const REASON_LABELS: Record<HealthReason, string> = {
  overBudget: 'Actual + committed above budget',
  budgetNearlyUsed: '90% of the budget used',
  eacOverBudget: 'Estimate at completion above budget',
  negativeMargin: 'Estimate at completion above contract value',
  pastEndDate: 'End date passed, not complete',
  behindSchedule: 'Progress behind elapsed time',
  suspended: 'Project suspended',
  noBudget: 'No budget on the WBS',
};

export const PROJECT_STATUS_LABELS: Record<number, string> = {
  1: 'In Progress', 2: 'Closed', 365000000: 'Offer', 365000001: 'Suspended',
};
