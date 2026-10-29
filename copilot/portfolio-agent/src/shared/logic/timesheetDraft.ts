// Draft of hours to log from Copilot: prompt values prefill editable lines, nothing is saved until the user confirms.
import { isEditable, parseHours, type TimeEntry } from '../projectiq/timesheet';
import { toDay } from '../projectiq/dates';

export interface DraftLine {
  key: string;
  projectId?: string;
  nodeId?: string;
  day: number;
  /** Text typed by the user, parsed with the same rule as the Weekly Timesheet (0-24, quarter hours). */
  hours: string;
  notes?: string;
}

export interface DraftIssue {
  key?: string;
  /** Message id, see the strings of the Submit Timesheet view. */
  code: 'noResource' | 'noProject' | 'badHours' | 'zeroHours' | 'dayOver24' | 'dayOver10' | 'nothingToDo';
  day?: number;
  severity: 'error' | 'warning';
}

/** Day number of a date written by Copilot or the user: yyyy-mm-dd, "today" or "yesterday". */
export function resolveDay(text: string | undefined, today: number): number | undefined {
  const t = (text || '').trim().toLowerCase();
  if (!t) return undefined;
  if (t === 'today' || t === 'oggi') return today;
  if (t === 'yesterday' || t === 'ieri') return today - 1;
  return /^\d{4}-\d{2}-\d{2}/.test(t) ? toDay(t.substring(0, 10)) : undefined;
}

export interface SubmissionPlan {
  creates: { projectId: string; nodeId?: string; day: number; hours: number; notes?: string }[];
  /** Existing draft or rejected entries submitted together with the new ones. */
  existingToSubmit: string[];
  hoursByDay: Map<number, number>;
  issues: DraftIssue[];
}

/**
 * Checks the draft against the entries already recorded in the period: every line needs a project and valid hours,
 * a day cannot exceed 24 hours (same limit as the Hours column) and more than 10 hours is flagged, as in the approval skill.
 */
export function planSubmission(lines: DraftLine[], existing: TimeEntry[], hasResource: boolean, submitExisting: boolean): SubmissionPlan {
  const issues: DraftIssue[] = [];
  if (!hasResource) issues.push({ code: 'noResource', severity: 'error' });
  const creates: SubmissionPlan['creates'] = [];
  lines.forEach(l => {
    const hours = parseHours(l.hours);
    if (!l.projectId) issues.push({ key: l.key, code: 'noProject', severity: 'error' });
    if (hours === undefined) issues.push({ key: l.key, code: 'badHours', severity: 'error' });
    else if (hours === 0) issues.push({ key: l.key, code: 'zeroHours', severity: 'error' });
    if (l.projectId && hours) creates.push({ projectId: l.projectId, nodeId: l.nodeId, day: l.day, hours, notes: l.notes || undefined });
  });
  const hoursByDay = new Map<number, number>();
  existing.forEach(e => hoursByDay.set(e.day, (hoursByDay.get(e.day) ?? 0) + e.hours));
  creates.forEach(c => hoursByDay.set(c.day, (hoursByDay.get(c.day) ?? 0) + c.hours));
  hoursByDay.forEach((h, d) => {
    if (h > 24) issues.push({ code: 'dayOver24', day: d, severity: 'error' });
    else if (h > 10) issues.push({ code: 'dayOver10', day: d, severity: 'warning' });
  });
  const existingToSubmit = submitExisting ? existing.filter(e => isEditable(e.status)).map(e => e.id) : [];
  if (!creates.length && !existingToSubmit.length && !issues.some(i => i.severity === 'error')) {
    issues.push({ code: 'nothingToDo', severity: 'error' });
  }
  return { creates, existingToSubmit, hoursByDay, issues };
}

export const canConfirm = (plan: SubmissionPlan): boolean => !plan.issues.some(i => i.severity === 'error');
