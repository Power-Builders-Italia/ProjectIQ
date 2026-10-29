import { approvalQueue, idsToDecide, type PendingTime } from './approvals';

const e = (id: string, resourceId: string, day: number, hours: number, submittedOn?: number): PendingTime =>
  ({ id, resourceId, resourceName: resourceId.toUpperCase(), projectId: 'p', projectName: 'P', day, hours, submittedOn });

describe('approvalQueue', () => {
  // day 4 = Monday 1970-01-05
  const groups = approvalQueue([e('1', 'a', 4, 6, 10), e('2', 'a', 4, 5, 12), e('3', 'a', 5, 8, 12), e('4', 'b', 11, 8, 19)], 20);
  it('groups by resource and week and flags stale submissions and long days', () => {
    expect(groups.map(g => [g.resourceId, g.weekStart, g.hours])).toEqual([['a', 4, 19], ['b', 11, 8]]);
    expect(groups[0].flags).toEqual({ stale: true, longDays: [4] });
    expect(groups[1].flags).toEqual({ stale: false, longDays: [] });
  });
  it('decides the selected groups, or all of them', () => {
    expect(idsToDecide(groups, new Set([groups[1].key]))).toEqual(['4']);
    expect(idsToDecide(groups, new Set()).sort()).toEqual(['1', '2', '3', '4']);
  });
});
