import { documentState, supplierCompliance } from './suppliers';

describe('supplier compliance', () => {
  it('classifies documents by expiry date', () => {
    const d = { id: 'd', supplierId: 's', description: 'DURC', type: 'DURC' };
    expect(documentState({ ...d, expiry: 99 }, 100)).toBe('expired');
    expect(documentState({ ...d, expiry: 100 }, 100)).toBe('expiring');
    expect(documentState({ ...d, expiry: 130 }, 100)).toBe('expiring');
    expect(documentState({ ...d, expiry: 131 }, 100)).toBe('valid');
    expect(documentState(d, 100)).toBe('noExpiry');
  });

  it('blocks orders to blocked suppliers or with expired documents and sorts by severity', () => {
    const list = supplierCompliance([
      { id: 'a', name: 'Alfa', blocked: false, expired: 0, expiring: 1, openOrders: 0 },
      { id: 'b', name: 'Beta', blocked: true, expired: 0, expiring: 0, openOrders: 2 },
      { id: 'c', name: 'Gamma', blocked: false, expired: 1, expiring: 0, openOrders: 1 },
    ], [
      { id: '1', supplierId: 'a', description: 'Insurance', type: 'Insurance', expiry: 110 },
      { id: '2', supplierId: 'c', description: 'DURC', type: 'DURC', expiry: 90 },
    ], 100);
    expect(list.map(c => [c.supplier.id, c.state, c.canOrder])).toEqual([
      ['b', 'blocked', false], ['c', 'expired', false], ['a', 'expiring', true],
    ]);
    expect(list[1].documents[0].daysLeft).toBe(-10);
  });
});
