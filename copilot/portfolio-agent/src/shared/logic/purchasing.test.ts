import { PO_STATUS, PR_STATUS, purchasingStatus, RFQ_STATUS, type PurchasingData } from './purchasing';

const data: PurchasingData = {
  me: 'u1',
  requests: [
    { id: 'r1', number: 'PR-00001', title: 'Scaffolding', status: PR_STATUS.submitted, amount: 5000, overBudget: false, aboveThreshold: false, project: 'A', approverId: 'u1', neededBy: 20 },
    { id: 'r2', number: 'PR-00002', title: 'Cement', status: PR_STATUS.submitted, amount: 900, overBudget: true, aboveThreshold: false, project: 'A', approverId: 'u2' },
    { id: 'r3', number: 'PR-00003', title: 'Paint', status: PR_STATUS.approved, amount: 300, overBudget: false, aboveThreshold: false, project: 'B' },
  ],
  rfqs: [
    { id: 'q1', number: 'RFQ-00001', status: RFQ_STATUS.sent, deadline: 5, responses: 2, project: 'A' },
    { id: 'q2', number: 'RFQ-00002', status: RFQ_STATUS.sent, deadline: 50, responses: 0, project: 'A' },
  ],
  orders: [
    { id: 'o1', number: 'PO-00001', status: PO_STATUS.sent, expected: 7, total: 1000, received: 200, supplier: 'Rossi', project: 'A' },
    { id: 'o2', number: 'PO-00002', status: PO_STATUS.confirmed, expected: 30, total: 500, received: 0, supplier: 'Bianchi', project: 'B' },
    { id: 'o3', number: 'PO-00003', status: PO_STATUS.draft, total: 400, received: 0, supplier: 'Verdi', project: 'B' },
  ],
  invoices: [{ id: 'i1', number: 'INV-00001', invoiceNumber: '12/A', date: 9, total: 1220, supplier: 'Rossi' }],
};

describe('purchasingStatus', () => {
  const s = purchasingStatus(data, 10);
  it('separates requests waiting for the user from the others', () => {
    expect(s.toApprove.map(r => r.id)).toEqual(['r1']);
    expect(s.submitted.map(r => r.id)).toEqual(['r2']);
    expect(s.toOrder.map(r => r.id)).toEqual(['r3']);
  });
  it('finds RFQs past deadline and late orders', () => {
    expect(s.rfqsToClose.map(r => r.id)).toEqual(['q1']);
    expect(s.lateOrders.map(o => [o.id, o.daysLate])).toEqual([['o1', 3]]);
    expect(s.openOrders.map(o => o.id)).toEqual(['o2']);
  });
  it('computes committed cost on sent and confirmed orders only', () => {
    expect(s.committed).toBe(800 + 500);
  });
});
