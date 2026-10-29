import { attentionItems } from './myWork';
import { approvalQueue } from './approvals';
import { STATUS } from '../projectiq/timesheet';
import { projectHealth, PROJECT_STATUS, type ProjectFigures } from './portfolio';

describe('attentionItems', () => {
  it('ranks high severity first and points each item to its view', () => {
    const p: ProjectFigures = { id: 'p', code: 'PRJ-1', name: 'X', status: PROJECT_STATUS.inProgress, contract: 100, budget: 100,
      actual: 150, committed: 0, progress: 50, actualHours: 0 };
    const items = attentionItems({
      today: 18, monday: 18, weeklyHours: 40,
      entries: [
        { id: 'a', projectId: 'p', projectName: 'X', day: 12, hours: 8, status: STATUS.draft },
        { id: 'b', projectId: 'p', projectName: 'X', day: 13, hours: 8, status: STATUS.rejected },
      ],
      approvals: approvalQueue([{ id: 't', resourceId: 'r', resourceName: 'R', projectId: 'p', projectName: 'X', day: 12, hours: 4, submittedOn: 17 }], 18),
      myProjects: [{ ...p, health: projectHealth(p, 18) }],
    });
    expect(items.map(i => i.kind)).toEqual(['rejectedHours', 'hoursToSubmit', 'projectOffTrack', 'timeToApprove', 'missingHours']);
    expect(items.find(i => i.kind === 'missingHours')?.detail).toBe('24');
    expect(items.find(i => i.kind === 'projectOffTrack')?.intent).toBe('GetProjectHealth');
  });

  it('is empty when everything is in order', () => {
    expect(attentionItems({ today: 18, monday: 18, weeklyHours: 0, entries: [], approvals: [], myProjects: [] })).toEqual([]);
  });
});
