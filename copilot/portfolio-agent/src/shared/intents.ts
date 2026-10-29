// Catalog of the agent's Copilot Components: one tool per component, grouped as in the capability explorer.
import type { IntentKey } from './logic/myWork';

export type { IntentKey };

export type IntentCategory = 'myWork' | 'project' | 'portfolio' | 'purchasing' | 'approvals' | 'help';
export type IntentOperation = 'information' | 'review' | 'submit';

export interface IntentDefinition {
  key: IntentKey;
  title: string;
  category: IntentCategory;
  operation: IntentOperation;
  /** What the view shows, for the capability explorer. */
  summary: string;
  /** Prompt sent when the user opens the view from another one ({project} is replaced by the project code). */
  prompt: string;
  /** ProjectIQ tables read; written only by review and submit views. */
  reads: string[];
}

export const INTENTS: IntentDefinition[] = [
  { key: 'GetMyWorkSummary', title: 'My work', category: 'myWork', operation: 'information',
    summary: 'What needs your attention: hours to approve or submit, missing hours, projects at risk, purchases waiting for you, overload.',
    prompt: 'What needs my attention across my projects this week?', reads: ['Time Entry', 'Project', 'Purchase Request', 'WBS Allocation'] },
  { key: 'SubmitTimesheet', title: 'Log and submit hours', category: 'myWork', operation: 'submit',
    summary: 'Prepares your hours as an editable draft, then saves and submits them for approval after you confirm.',
    prompt: 'Submit my timesheet for this week', reads: ['Time Entry', 'Project', 'WBS Node'] },
  { key: 'GetProjectHealth', title: 'Project health', category: 'project', operation: 'information',
    summary: 'Status, budget vs actual vs committed, estimate at completion, margin, schedule, flagged WBS phases and open purchases.',
    prompt: 'How is project {project} going?', reads: ['Project', 'WBS Node', 'Baseline', 'Purchase Request', 'Purchase Order'] },
  { key: 'GetProjectBudget', title: 'Project budget', category: 'project', operation: 'information',
    summary: 'Budget against actual cost by WBS branch, labour and materials, variance and estimate at completion.',
    prompt: 'Show the budget of project {project}', reads: ['Project', 'WBS Node'] },
  { key: 'GetProjectTimeline', title: 'Project timeline', category: 'project', operation: 'information',
    summary: 'WBS phases on a timeline with progress, critical path and slippage against the reference baseline.',
    prompt: 'Show the timeline of project {project}', reads: ['WBS Node', 'WBS Dependency', 'Baseline'] },
  { key: 'GetPortfolioHealth', title: 'Portfolio health', category: 'portfolio', operation: 'information',
    summary: 'All your projects with a traffic light, contract, budget, actual, committed, estimate at completion and margin.',
    prompt: 'Show the health of the project portfolio', reads: ['Project'] },
  { key: 'GetResourceLoad', title: 'Resource load', category: 'portfolio', operation: 'information',
    summary: 'Allocated hours against capacity (weekly hours minus absences) by week, for one person or the whole team.',
    prompt: 'Who is overloaded in the next weeks?', reads: ['Resource', 'WBS Allocation', 'Absence'] },
  { key: 'GetPurchasingStatus', title: 'Purchasing status', category: 'purchasing', operation: 'information',
    summary: 'Requests waiting for your approval, requests to order, RFQs to close, late orders and invoices to review.',
    prompt: 'What is the purchasing status?', reads: ['Purchase Request', 'RFQ', 'Purchase Order', 'Supplier Invoice'] },
  { key: 'GetSupplierCompliance', title: 'Supplier compliance', category: 'purchasing', operation: 'information',
    summary: 'Suppliers with expired or expiring documents (DURC, certifications, insurance) and blocked suppliers.',
    prompt: 'Which suppliers have expired or expiring documents?', reads: ['Account', 'Supplier Document', 'Purchase Order'] },
  { key: 'ReviewTimeApprovals', title: 'Approve hours', category: 'approvals', operation: 'review',
    summary: 'Submitted hours of your projects by person and week, with flags; approve or reject (with a note) after confirming.',
    prompt: 'Which hours do I have to approve?', reads: ['Time Entry', 'Project Member'] },
  { key: 'ExploreAgentCapabilities', title: 'What I can do', category: 'help', operation: 'information',
    summary: 'The scenarios of the ProjectIQ agent, with an example question for each.',
    prompt: 'Show me what you can help with', reads: [] },
];

export function getIntent(key: IntentKey): IntentDefinition {
  const found = INTENTS.filter(i => i.key === key)[0];
  if (!found) throw new Error(`Unknown intent ${key}`);
  return found;
}

export const CATEGORY_TITLES: Record<IntentCategory, string> = {
  myWork: 'My work', project: 'Project', portfolio: 'Portfolio', purchasing: 'Purchasing', approvals: 'Approvals', help: 'Help',
};

/** Prompt that opens a view, for follow-up buttons. */
export function promptFor(key: IntentKey, project?: string): string {
  return getIntent(key).prompt.replace('{project}', project || '');
}
