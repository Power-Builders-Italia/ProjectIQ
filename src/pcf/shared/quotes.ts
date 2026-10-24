// Quote comparison of a request for quotation: request lines x invited suppliers, best price per line and best total.

export interface QuoteLine { id: string; name: string; quantity: number; uom: string; sortOrder: number }
export interface QuoteInvitation { id: string; name: string; status: number; deliveryDays?: number }
export interface Quote { invitationId: string; lineId: string; price: number }

export const INVITATION_RESPONDED = 365000001;

export interface QuoteCell { price: number; amount: number; best: boolean }
export interface QuoteRow { line: QuoteLine; cells: Map<string, QuoteCell>; bestPrice?: number; bestInvitationId?: string }
export interface SupplierTotal { invitation: QuoteInvitation; total: number; quoted: number; complete: boolean; best: boolean }
export interface Comparison { rows: QuoteRow[]; totals: SupplierTotal[] }

const round2 = (v: number): number => Math.round(v * 100) / 100;

/** Lowest unit price per line (ties: first invitation in order); best total among suppliers who quoted every line. */
export function compareQuotes(lines: QuoteLine[], invitations: QuoteInvitation[], quotes: Quote[]): Comparison {
    const byKey = new Map<string, number>();
    for (const q of quotes) byKey.set(`${q.invitationId}|${q.lineId}`, q.price);
    const sorted = [...lines].sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name));

    const rows: QuoteRow[] = sorted.map(line => {
        const cells = new Map<string, QuoteCell>();
        let bestPrice: number | undefined;
        let bestInvitationId: string | undefined;
        for (const inv of invitations) {
            const price = byKey.get(`${inv.id}|${line.id}`);
            if (price === undefined) continue;
            cells.set(inv.id, { price, amount: round2(price * line.quantity), best: false });
            if (bestPrice === undefined || price < bestPrice) { bestPrice = price; bestInvitationId = inv.id; }
        }
        if (bestPrice !== undefined) for (const c of cells.values()) c.best = c.price === bestPrice;
        return { line, cells, bestPrice, bestInvitationId };
    });

    const totals: SupplierTotal[] = invitations.map(inv => {
        const quoted = rows.filter(r => r.cells.has(inv.id));
        return {
            invitation: inv,
            total: round2(quoted.reduce((t, r) => t + r.cells.get(inv.id)!.amount, 0)),
            quoted: quoted.length,
            complete: rows.length > 0 && quoted.length === rows.length,
            best: false,
        };
    });
    const complete = totals.filter(t => t.complete);
    if (complete.length) {
        const min = Math.min(...complete.map(t => t.total));
        for (const t of complete) t.best = t.total === min;
    }
    return { rows, totals };
}
