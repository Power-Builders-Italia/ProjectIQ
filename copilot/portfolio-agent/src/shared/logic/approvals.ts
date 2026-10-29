// Hours to approve: the Time Approval grouping (resource and week) with the flags of the approval skill.
import { groupForApproval, type ApprovalGroup, type PendingEntry } from '../projectiq/approval';

export interface PendingTime extends PendingEntry {
  projectId: string;
  submittedOn?: number;
}

export interface ApprovalFlags {
  /** Submitted more than 7 days ago. */
  stale: boolean;
  /** Days of the group where the resource has more than 10 hours. */
  longDays: number[];
}

export interface FlaggedGroup extends ApprovalGroup {
  flags: ApprovalFlags;
  oldestSubmission?: number;
}

export function approvalQueue(entries: PendingTime[], today: number): FlaggedGroup[] {
  return groupForApproval(entries).map(g => {
    const subs = (g.entries as PendingTime[]).map(e => e.submittedOn).filter((d): d is number => d !== undefined);
    const oldest = subs.length ? Math.min(...subs) : undefined;
    const byDay = new Map<number, number>();
    g.entries.forEach(e => byDay.set(e.day, (byDay.get(e.day) ?? 0) + e.hours));
    const longDays = [...byDay.entries()].filter(([, h]) => h > 10).map(([d]) => d).sort((a, b) => a - b);
    return { ...g, oldestSubmission: oldest, flags: { stale: oldest !== undefined && today - oldest > 7, longDays } };
  });
}

/** Ids to decide: the selected groups, or every entry when nothing is selected. */
export function idsToDecide(groups: FlaggedGroup[], selected: Set<string>): string[] {
  const chosen = selected.size ? groups.filter(g => selected.has(g.key)) : groups;
  return chosen.flatMap(g => g.entries.map(e => e.id));
}
