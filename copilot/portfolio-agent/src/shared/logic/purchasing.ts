// Purchasing status: what is waiting for the user, what is late, what is still open.

export const PR_STATUS = { draft: 1, submitted: 365000000, approved: 365000001, rejected: 365000002, cancelled: 365000003, ordered: 365000004 } as const;
export const RFQ_STATUS = { draft: 1, sent: 365000000, awarded: 365000001, cancelled: 365000002 } as const;
export const PO_STATUS = { draft: 1, sent: 365000000, confirmed: 365000001, received: 365000002, cancelled: 365000003 } as const;

export interface PurchaseRequestRow {
  id: string;
  number: string;
  title: string;
  status: number;
  amount: number;
  neededBy?: number;
  overBudget: boolean;
  aboveThreshold: boolean;
  submittedOn?: number;
  project: string;
  approverId?: string;
}

export interface RfqRow { id: string; number: string; status: number; deadline?: number; responses: number; project: string; }

export interface PurchaseOrderRow {
  id: string;
  number: string;
  status: number;
  expected?: number;
  total: number;
  received: number;
  supplier: string;
  project: string;
}

export interface SupplierInvoiceRow {
  id: string;
  number: string;
  invoiceNumber: string;
  date?: number;
  total: number;
  supplier: string;
  project?: string;
  order?: string;
}

export interface PurchasingData {
  /** Dataverse user id of the signed-in user. */
  me: string;
  requests: PurchaseRequestRow[];
  rfqs: RfqRow[];
  orders: PurchaseOrderRow[];
  invoices: SupplierInvoiceRow[];
}

export interface PurchasingStatus {
  /** Submitted requests whose current approver is the user. */
  toApprove: PurchaseRequestRow[];
  /** Submitted requests waiting for someone else. */
  submitted: PurchaseRequestRow[];
  /** Approved requests not yet ordered. */
  toOrder: PurchaseRequestRow[];
  /** Sent RFQs whose deadline is past. */
  rfqsToClose: RfqRow[];
  /** Sent or confirmed orders whose expected delivery is past. */
  lateOrders: (PurchaseOrderRow & { daysLate: number })[];
  /** Sent or confirmed orders on time. */
  openOrders: PurchaseOrderRow[];
  invoicesToReview: SupplierInvoiceRow[];
  /** Amount still to receive on open orders (committed cost). */
  committed: number;
}

const isOpenOrder = (o: PurchaseOrderRow): boolean => o.status === PO_STATUS.sent || o.status === PO_STATUS.confirmed;

export function purchasingStatus(data: PurchasingData, today: number): PurchasingStatus {
  const submitted = data.requests.filter(r => r.status === PR_STATUS.submitted);
  const open = data.orders.filter(isOpenOrder);
  const late = open.filter(o => o.expected !== undefined && o.expected < today)
    .map(o => ({ ...o, daysLate: today - (o.expected as number) }))
    .sort((a, b) => b.daysLate - a.daysLate);
  return {
    toApprove: submitted.filter(r => r.approverId === data.me).sort((a, b) => (a.neededBy ?? Infinity) - (b.neededBy ?? Infinity)),
    submitted: submitted.filter(r => r.approverId !== data.me),
    toOrder: data.requests.filter(r => r.status === PR_STATUS.approved),
    rfqsToClose: data.rfqs.filter(r => r.status === RFQ_STATUS.sent && r.deadline !== undefined && r.deadline < today)
      .sort((a, b) => (a.deadline as number) - (b.deadline as number)),
    lateOrders: late,
    openOrders: open.filter(o => late.every(l => l.id !== o.id)),
    invoicesToReview: [...data.invoices].sort((a, b) => (a.date ?? 0) - (b.date ?? 0)),
    committed: open.reduce((s, o) => s + Math.max(0, o.total - o.received), 0),
  };
}
