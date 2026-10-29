import { projectPhases, timelineRows } from './project';
import type { WbsItem } from '../projectiq/wbs';

const item = (id: string, parentId: string | undefined, code: string, start: number, end: number, budget: number, hours: number, progress: number): WbsItem =>
  ({ id, parentId, code, name: code, start, end, progress, budgetHours: hours, budgetLabour: budget, budgetMaterials: 0, budgetOther: 0, budgetTotal: budget });

const items = [
  item('1', undefined, '1', 0, 0, 0, 0, 0),
  item('1.1', '1', '1.1', 10, 19, 1000, 10, 100),
  item('1.2', '1', '1.2', 20, 29, 1000, 10, 20),
  item('2', undefined, '2', 30, 39, 500, 5, 0),
];

describe('projectPhases', () => {
  it('rolls up actuals and flags overruns, late phases and baseline slippage', () => {
    const actuals = new Map([['1.1', { actualCost: 900, actualHours: 12 }], ['1.2', { actualCost: 300, actualHours: 3 }]]);
    const baseline = new Map([['1.1', { start: 10, end: 19, budget: 1000 }], ['1.2', { start: 20, end: 25, budget: 800 }]]);
    const phases = projectPhases(items, actuals, 35, baseline);
    expect(phases.map(p => p.node.id)).toEqual(['1', '2']);
    expect(phases[0]).toMatchObject({ actualCost: 1200, actualHours: 15, hoursOverrun: false, late: true, slipDays: 4, budgetDelta: 200 });
    expect(phases[1].slipDays).toBeUndefined();
  });
});

describe('timelineRows', () => {
  it('marks the critical path and the bars pushed by dependencies', () => {
    const t = timelineRows(items, [{ predecessorId: '1.2', successorId: '2', lagDays: 5 }], 15, 1);
    expect(t.rows.map(r => r.node.id)).toEqual(['1', '1.1', '1.2', '2']);
    const two = t.rows.find(r => r.node.id === '2')!;
    expect(two.critical).toBe(true);
    expect(two.pushedEnd).toBe(44);
    expect(t.start).toBe(0);
    expect(t.end).toBe(44);
  });
});
