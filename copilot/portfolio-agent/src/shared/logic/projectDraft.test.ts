import {
  canCreate, draftFrom, matchByName, normaliseDate, parseAmount, planProject, projectFolderName, safeFileName, validateDraft, type ProjectDraft,
} from './projectDraft';

let seq = 0;
const key = (): string => `k${++seq}`;

const complete = (patch: Partial<ProjectDraft> = {}): ProjectDraft => ({
  name: 'Warehouse Milan', customerId: 'a1', managerId: 'u1', startDate: '2026-11-02', endDate: '2027-03-31',
  contractValue: '120.000,50', description: '', lines: [], ...patch,
});

describe('projectDraft', () => {
  it('reads ISO and day-first dates and rejects impossible ones', () => {
    expect(normaliseDate('2026-11-02T00:00:00Z')).toBe('2026-11-02');
    expect(normaliseDate('2/11/2026')).toBe('2026-11-02');
    expect(normaliseDate('31.12.2026')).toBe('2026-12-31');
    expect(normaliseDate('31/02/2026')).toBe('');
    expect(normaliseDate('next month')).toBe('');
  });

  it('parses amounts typed in any culture', () => {
    expect(parseAmount('120.000,50')).toBe(120000.5);
    expect(parseAmount('120,000.50')).toBe(120000.5);
    expect(parseAmount('€ 1 500')).toBe(1500);
    expect(parseAmount('')).toBeUndefined();
    expect(parseAmount('abc')).toBeNaN();
  });

  it('matches the customer or manager named in the document', () => {
    const choices = [{ id: '1', name: 'Contoso Ltd' }, { id: '2', name: 'Contoso Italia' }, { id: '3', name: 'Fabrikam' }];
    expect(matchByName(choices, 'fabrikam')?.id).toBe('3');
    expect(matchByName(choices, 'Contoso Italia S.r.l.')?.id).toBe('2');
    expect(matchByName(choices, 'Contoso')).toBeUndefined();
    expect(matchByName(choices, '')).toBeUndefined();
  });

  it('builds the draft and numbers WBS lines without a code', () => {
    const d = draftFrom({ name: ' Warehouse ', contractValue: 1000, wbs: [{ code: '1', name: 'Design' }, { code: '1.1.', name: 'Survey' }, { name: 'Build' }, { name: '' }] }, key);
    expect(d.name).toBe('Warehouse');
    expect(d.contractValue).toBe('1000');
    expect(d.lines.map(l => l.code)).toEqual(['1', '1.1', '2']);
  });

  it('asks for the missing project data', () => {
    const issues = validateDraft(complete({ name: '', customerId: undefined, managerId: undefined, startDate: '', endDate: '' }), true);
    expect(issues.map(i => i.code)).toEqual(['noName', 'noCustomer', 'noManager', 'noStart', 'noEnd', 'noWbs']);
    expect(canCreate(issues)).toBe(false);
  });

  it('creates a new customer with the project', () => {
    const customers = [{ name: 'Fabrikam' }];
    const named = (name: string): ProjectDraft => complete({ customerId: undefined, newCustomer: { name, vatNumber: ' IT01234567890 ' } });
    expect(validateDraft(named(' '), true, customers).map(i => i.code)).toEqual(['noCustomerName', 'noWbs']);
    const dup = validateDraft(named('fabrikam'), true, customers);
    expect(dup.map(i => `${i.severity}:${i.code}`)).toEqual(['warning:customerExists', 'warning:noWbs']);
    expect(canCreate(dup)).toBe(true);
    const plan = planProject({ ...named(' Northwind '), customerId: 'a1' });
    expect(plan.customerId).toBe('');
    expect(plan.newCustomer).toEqual({ name: 'Northwind', vatNumber: 'IT01234567890' });
    expect(planProject(complete()).newCustomer).toBeUndefined();
  });

  it('checks the outline of the WBS', () => {
    const lines = [
      { key: 'a', code: '1', name: 'Design', budgetHours: '', startDate: '', endDate: '' },
      { key: 'b', code: '2.1', name: 'Orphan', budgetHours: '', startDate: '', endDate: '' },
      { key: 'c', code: '1', name: 'Again', budgetHours: 'x', startDate: '', endDate: '' },
      { key: 'd', code: '3', name: 'Late', budgetHours: '', startDate: '2027-03-01', endDate: '2027-05-01' },
    ];
    const issues = validateDraft(complete({ lines }), false);
    expect(issues.map(i => `${i.key || ''}:${i.code}`)).toEqual(['a:duplicateCode', 'b:noParent', 'c:duplicateCode', 'c:badHours', 'd:nodeOutsideProject', ':noFile']);
  });

  it('plans parents before children in outline order', () => {
    const lines = [
      { key: 'a', code: '2', name: 'Build', budgetHours: '', startDate: '', endDate: '' },
      { key: 'b', code: '1.10', name: 'Permits', budgetHours: '8', startDate: '', endDate: '' },
      { key: 'c', code: '1', name: 'Design', budgetHours: '', startDate: '', endDate: '' },
      { key: 'd', code: '1.2', name: 'Survey', budgetHours: '16,5', startDate: '2026-11-02', endDate: '' },
    ];
    const draft = complete({ lines });
    expect(canCreate(validateDraft(draft, true))).toBe(true);
    const plan = planProject(draft);
    expect(plan.contractValue).toBe(120000.5);
    expect(plan.description).toBeUndefined();
    expect(plan.nodes.map(n => `${n.code}<${n.parentCode}#${n.sortOrder}`)).toEqual(['1<#1', '1.2<1#2', '1.10<1#10', '2<#2']);
    expect(plan.nodes[1]).toMatchObject({ budgetHours: 16.5, startDate: '2026-11-02', endDate: undefined });
  });

  it('names the SharePoint folder as Dataverse does', () => {
    expect(projectFolderName('Warehouse: Milan / Phase 1', '{0a1b2c3d-1111-2222-3333-444455556666}'))
      .toBe('Warehouse Milan Phase 1_0A1B2C3D111122223333444455556666');
    expect(safeFileName('Offer #12: final?.pdf')).toBe('Offer -12- final-.pdf');
  });
});
