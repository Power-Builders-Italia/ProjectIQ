// Supplier compliance: expired and expiring documents (DURC, certifications, insurance...), blocked suppliers.

export const EXPIRING_DAYS = 30;

export interface SupplierInfo {
  id: string;
  name: string;
  blocked: boolean;
  /** Counters refreshed every day by the supplier documents flow. */
  expired: number;
  expiring: number;
  openOrders: number;
}

export interface SupplierDocument {
  id: string;
  supplierId: string;
  description: string;
  type: string;
  number?: string;
  expiry?: number;
}

export type DocumentState = 'expired' | 'expiring' | 'valid' | 'noExpiry';

export function documentState(d: SupplierDocument, today: number): DocumentState {
  if (d.expiry === undefined) return 'noExpiry';
  if (d.expiry < today) return 'expired';
  return d.expiry <= today + EXPIRING_DAYS ? 'expiring' : 'valid';
}

export interface SupplierCompliance {
  supplier: SupplierInfo;
  documents: (SupplierDocument & { state: DocumentState; daysLeft?: number })[];
  /** Same rule as the skill: active and without expired documents. */
  canOrder: boolean;
  state: 'blocked' | 'expired' | 'expiring' | 'ok';
}

const ORDER: Record<SupplierCompliance['state'], number> = { blocked: 0, expired: 1, expiring: 2, ok: 3 };

export function supplierCompliance(suppliers: SupplierInfo[], documents: SupplierDocument[], today: number): SupplierCompliance[] {
  return suppliers.map(supplier => {
    const docs = documents.filter(d => d.supplierId === supplier.id).map(d => ({
      ...d, state: documentState(d, today), daysLeft: d.expiry === undefined ? undefined : d.expiry - today,
    })).sort((a, b) => (a.expiry ?? Infinity) - (b.expiry ?? Infinity));
    const expired = docs.some(d => d.state === 'expired');
    const expiring = docs.some(d => d.state === 'expiring');
    const state = supplier.blocked ? 'blocked' : expired ? 'expired' : expiring ? 'expiring' : 'ok';
    return { supplier, documents: docs, canOrder: !supplier.blocked && !expired, state } as SupplierCompliance;
  }).sort((a, b) => ORDER[a.state] - ORDER[b.state] || a.supplier.name.localeCompare(b.supplier.name));
}
