import { canConfirm, planSubmission, resolveDay } from './timesheetDraft';
import { STATUS, type TimeEntry } from '../projectiq/timesheet';

const entry = (id: string, day: number, hours: number, status: number): TimeEntry =>
  ({ id, projectId: 'p', projectName: 'P', day, hours, status });

describe('resolveDay', () => {
  it('understands ISO dates, today and yesterday', () => {
    expect(resolveDay('1970-01-11', 500)).toBe(10);
    expect(resolveDay('today', 500)).toBe(500);
    expect(resolveDay('Ieri', 500)).toBe(499);
    expect(resolveDay('next monday', 500)).toBeUndefined();
    expect(resolveDay(undefined, 500)).toBeUndefined();
  });
});

describe('planSubmission', () => {
  it('creates the new lines and submits the draft and rejected entries of the week', () => {
    const plan = planSubmission([{ key: 'a', projectId: 'p', day: 10, hours: '7,5' }],
      [entry('e1', 9, 8, STATUS.draft), entry('e2', 8, 8, STATUS.approved), entry('e3', 7, 4, STATUS.rejected)], true, true);
    expect(plan.creates).toEqual([{ projectId: 'p', nodeId: undefined, day: 10, hours: 7.5, notes: undefined }]);
    expect(plan.existingToSubmit).toEqual(['e1', 'e3']);
    expect(canConfirm(plan)).toBe(true);
  });

  it('requires a project, valid hours and a linked resource', () => {
    const plan = planSubmission([{ key: 'a', day: 10, hours: '25' }, { key: 'b', projectId: 'p', day: 10, hours: '0' }], [], false, false);
    expect(plan.issues.map(i => i.code).sort()).toEqual(['badHours', 'noProject', 'noResource', 'zeroHours']);
    expect(canConfirm(plan)).toBe(false);
  });

  it('warns over 10 hours a day and blocks over 24', () => {
    const warn = planSubmission([{ key: 'a', projectId: 'p', day: 10, hours: '4' }], [entry('e1', 10, 8, STATUS.submitted)], true, true);
    expect(warn.issues).toEqual([{ code: 'dayOver10', day: 10, severity: 'warning' }]);
    expect(canConfirm(warn)).toBe(true);
    const block = planSubmission([{ key: 'a', projectId: 'p', day: 10, hours: '20' }], [entry('e1', 10, 8, STATUS.approved)], true, true);
    expect(canConfirm(block)).toBe(false);
  });

  it('has nothing to do without lines or entries to submit', () => {
    expect(planSubmission([], [entry('e2', 8, 8, STATUS.approved)], true, true).issues.map(i => i.code)).toEqual(['nothingToDo']);
  });
});
