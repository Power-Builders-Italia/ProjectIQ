// Catalog of the agent's Copilot Components: one tool per component, grouped as in the capability explorer.
// Titles, summaries and prompts are translated in i18n (intents.<key>).
import type { IntentKey } from './logic/myWork';
import { strings } from './i18n';

export type { IntentKey };

export type IntentCategory = 'myWork' | 'project' | 'portfolio' | 'purchasing' | 'approvals' | 'help';
export type IntentOperation = 'information' | 'review' | 'submit';

export interface IntentDefinition {
  key: IntentKey;
  category: IntentCategory;
  operation: IntentOperation;
  /** ProjectIQ tables read; written only by review and submit views. */
  reads: string[];
}

export const INTENTS: IntentDefinition[] = [
  { key: 'GetMyWorkSummary', category: 'myWork', operation: 'information', reads: ['Time Entry', 'Project', 'Purchase Request', 'WBS Allocation'] },
  { key: 'SubmitTimesheet', category: 'myWork', operation: 'submit', reads: ['Time Entry', 'Project', 'WBS Node'] },
  { key: 'GetProjectHealth', category: 'project', operation: 'information', reads: ['Project', 'WBS Node', 'Baseline', 'Purchase Request', 'Purchase Order'] },
  { key: 'GetProjectBudget', category: 'project', operation: 'information', reads: ['Project', 'WBS Node'] },
  { key: 'GetProjectTimeline', category: 'project', operation: 'information', reads: ['WBS Node', 'WBS Dependency', 'Baseline'] },
  { key: 'GetPortfolioHealth', category: 'portfolio', operation: 'information', reads: ['Project'] },
  { key: 'GetResourceLoad', category: 'portfolio', operation: 'information', reads: ['Resource', 'WBS Allocation', 'Absence'] },
  { key: 'GetPurchasingStatus', category: 'purchasing', operation: 'information', reads: ['Purchase Request', 'RFQ', 'Purchase Order', 'Supplier Invoice'] },
  { key: 'GetSupplierCompliance', category: 'purchasing', operation: 'information', reads: ['Account', 'Supplier Document', 'Purchase Order'] },
  { key: 'ReviewTimeApprovals', category: 'approvals', operation: 'review', reads: ['Time Entry', 'Project Member'] },
  { key: 'ExploreAgentCapabilities', category: 'help', operation: 'information', reads: [] },
];

export const CATEGORIES: IntentCategory[] = ['myWork', 'project', 'portfolio', 'purchasing', 'approvals', 'help'];

/** Prompt that opens a view, in the user's language, for follow-up buttons ({project} is replaced by the project code). */
export function promptFor(key: IntentKey, project?: string): string {
  return strings().intents[key].prompt.replace('{project}', project || '');
}
