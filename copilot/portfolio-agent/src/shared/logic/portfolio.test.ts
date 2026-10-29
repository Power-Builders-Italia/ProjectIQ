import { matchProjects, portfolioSummary, projectHealth, PROJECT_STATUS, type ProjectFigures } from './portfolio';

const base: ProjectFigures = {
  id: 'p1', code: 'PRJ-000001', name: 'School roof', status: PROJECT_STATUS.inProgress, start: 100, end: 199,
  contract: 120000, budget: 100000, actual: 40000, committed: 10000, progress: 50, actualHours: 300,
};

describe('projectHealth', () => {
  it('is on track when spending, margin and schedule are in line', () => {
    const h = projectHealth(base, 150);
    expect(h.level).toBe('onTrack');
    expect(h.reasons).toEqual([]);
    expect(h.budgetUsed).toBeCloseTo(0.5);
    expect(h.remaining).toBe(50000);
    expect(h.eac).toBe(80000);
    expect(h.margin).toBe(40000);
  });

  it('is off track when actual + committed exceed the budget', () => {
    const h = projectHealth({ ...base, actual: 95000, committed: 10000, progress: 95 }, 150);
    expect(h.level).toBe('offTrack');
    expect(h.reasons).toContain('overBudget');
  });

  it('flags a nearly used budget and an estimate at completion above budget as risks', () => {
    const h = projectHealth({ ...base, actual: 80000, committed: 12000, progress: 60 }, 160);
    expect(h.reasons).toEqual(expect.arrayContaining(['budgetNearlyUsed']));
    expect(h.level).toBe('offTrack'); // EAC 133k > contract 120k
    expect(h.reasons).toContain('negativeMargin');
  });

  it('is off track after the end date when not complete, at risk when behind elapsed time', () => {
    expect(projectHealth(base, 250).reasons).toContain('pastEndDate');
    const behind = projectHealth({ ...base, actual: 20000, progress: 30 }, 180);
    expect(behind.reasons).toContain('behindSchedule');
    expect(behind.level).toBe('atRisk');
  });

  it('does not track offers and closed projects', () => {
    expect(projectHealth({ ...base, status: PROJECT_STATUS.offer }, 150).level).toBe('notTracked');
    expect(projectHealth({ ...base, status: PROJECT_STATUS.closed }, 150).level).toBe('notTracked');
  });

  it('uses max(budget, actual) as estimate without progress, like the Cost Summary', () => {
    expect(projectHealth({ ...base, progress: 0 }, 101).eac).toBe(100000);
  });
});

describe('portfolioSummary', () => {
  it('sorts worst first and totals only tracked projects', () => {
    const s = portfolioSummary([
      base,
      { ...base, id: 'p2', code: 'PRJ-000002', actual: 120000 },
      { ...base, id: 'p3', code: 'PRJ-000003', status: PROJECT_STATUS.offer, budget: 999999 },
    ], 150);
    expect(s.rows.map(r => r.id)).toEqual(['p2', 'p1', 'p3']);
    expect(s.counts).toEqual({ offTrack: 1, atRisk: 0, onTrack: 1, notTracked: 1 });
    expect(s.budget).toBe(200000);
  });
});

describe('matchProjects', () => {
  const list = [base, { ...base, id: 'p2', code: 'PRJ-000012', name: 'School gym' }];
  it('prefers exact code or name', () => {
    expect(matchProjects(list, 'prj-000001').map(p => p.id)).toEqual(['p1']);
  });
  it('falls back to partial matches', () => {
    expect(matchProjects(list, 'school').length).toBe(2);
    expect(matchProjects(list, '')).toEqual([]);
  });
});
