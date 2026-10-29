// "What needs my attention": one ranked list built from the other views, each item pointing to the view that handles it.
import type { PortfolioRow } from './portfolio';
import type { PurchasingStatus } from './purchasing';
import type { FlaggedGroup } from './approvals';
import { isEditable, type TimeEntry } from '../projectiq/timesheet';
import { level, type ResourceLoadRow } from '../projectiq/load';

export type IntentKey =
  | 'GetMyWorkSummary' | 'GetPortfolioHealth' | 'GetProjectHealth' | 'GetProjectBudget' | 'GetProjectTimeline'
  | 'GetResourceLoad' | 'GetPurchasingStatus' | 'GetSupplierCompliance' | 'ReviewTimeApprovals' | 'SubmitTimesheet'
  | 'ExploreAgentCapabilities';

export interface AttentionItem {
  kind: 'timeToApprove' | 'requestsToApprove' | 'hoursToSubmit' | 'rejectedHours' | 'missingHours' | 'projectOffTrack'
    | 'projectAtRisk' | 'lateOrders' | 'invoicesToReview' | 'overloaded';
  severity: 'high' | 'medium' | 'low';
  count: number;
  /** Extra value for the message: hours, project code, week. */
  detail?: string;
  /** Follow-up view and the prompt that opens it. */
  intent: IntentKey;
  projectId?: string;
}

export interface MyWorkInput {
  today: number;
  /** Monday of the current week. */
  monday: number;
  weeklyHours: number;
  /** User's entries of last week and this week. */
  entries: TimeEntry[];
  approvals: FlaggedGroup[];
  purchasing?: PurchasingStatus;
  /** Projects managed by the user, with their health. */
  myProjects: PortfolioRow[];
  /** The user's load for the next weeks. */
  load?: ResourceLoadRow;
}

const RANK = { high: 0, medium: 1, low: 2 };

export function attentionItems(input: MyWorkInput): AttentionItem[] {
  const items: AttentionItem[] = [];
  const approvalHours = input.approvals.reduce((s, g) => s + g.hours, 0);
  if (input.approvals.length) {
    items.push({ kind: 'timeToApprove', severity: input.approvals.some(g => g.flags.stale) ? 'high' : 'medium',
      count: input.approvals.reduce((s, g) => s + g.entries.length, 0), detail: String(approvalHours), intent: 'ReviewTimeApprovals' });
  }
  if (input.purchasing?.toApprove.length) {
    items.push({ kind: 'requestsToApprove', severity: 'high', count: input.purchasing.toApprove.length, intent: 'GetPurchasingStatus' });
  }
  const rejected = input.entries.filter(e => e.status === 365000002);
  if (rejected.length) items.push({ kind: 'rejectedHours', severity: 'high', count: rejected.length, intent: 'SubmitTimesheet' });
  const drafts = input.entries.filter(e => isEditable(e.status) && e.status !== 365000002);
  if (drafts.length) {
    items.push({ kind: 'hoursToSubmit', severity: drafts.some(e => e.day < input.monday) ? 'high' : 'low', count: drafts.length,
      detail: String(drafts.reduce((s, e) => s + e.hours, 0)), intent: 'SubmitTimesheet' });
  }
  const lastWeek = input.entries.filter(e => e.day >= input.monday - 7 && e.day < input.monday).reduce((s, e) => s + e.hours, 0);
  if (input.weeklyHours > 0 && lastWeek < input.weeklyHours) {
    items.push({ kind: 'missingHours', severity: lastWeek === 0 ? 'high' : 'medium', count: 1,
      detail: String(Math.round((input.weeklyHours - lastWeek) * 100) / 100), intent: 'SubmitTimesheet' });
  }
  input.myProjects.filter(p => p.health.level === 'offTrack' || p.health.level === 'atRisk').forEach(p => {
    items.push({ kind: p.health.level === 'offTrack' ? 'projectOffTrack' : 'projectAtRisk',
      severity: p.health.level === 'offTrack' ? 'high' : 'medium', count: 1, detail: p.code || p.name, intent: 'GetProjectHealth', projectId: p.id });
  });
  if (input.purchasing?.lateOrders.length) {
    items.push({ kind: 'lateOrders', severity: 'medium', count: input.purchasing.lateOrders.length, intent: 'GetPurchasingStatus' });
  }
  if (input.purchasing?.invoicesToReview.length) {
    items.push({ kind: 'invoicesToReview', severity: 'low', count: input.purchasing.invoicesToReview.length, intent: 'GetPurchasingStatus' });
  }
  const over = input.load?.weeks.filter(w => level(w) === 'over').length ?? 0;
  if (over) items.push({ kind: 'overloaded', severity: 'medium', count: over, intent: 'GetResourceLoad' });
  return items.sort((a, b) => RANK[a.severity] - RANK[b.severity]);
}
