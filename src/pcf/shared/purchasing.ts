// Web API access of the Phase 4 controls (quote comparison).
import { Quote, QuoteInvitation, QuoteLine } from "./quotes";

type WebApi = ComponentFramework.WebApi;

const num = (v: unknown): number => (typeof v === "number" ? v : 0);

export const RFQ_SENT = 365000000;

export interface RfqData { status: number; lines: QuoteLine[]; invitations: QuoteInvitation[]; quotes: Quote[] }

export async function loadRfq(api: WebApi, rfqId: string): Promise<RfqData> {
    const rfq = await api.retrieveRecord("op365_rfq", rfqId, "?$select=statuscode,_op365_purchaserequestid_value");
    const requestId = rfq._op365_purchaserequestid_value as string | undefined;
    const [lines, invitations, quotes] = await Promise.all([
        requestId
            ? api.retrieveMultipleRecords("op365_purchaserequestline",
                `?$select=op365_purchaserequestlineid,op365_name,op365_quantity,op365_uom,op365_sortorder&$filter=_op365_purchaserequestid_value eq ${requestId} and statecode eq 0`)
            : Promise.resolve({ entities: [] as ComponentFramework.WebApi.Entity[], nextLink: "" }),
        api.retrieveMultipleRecords("op365_rfqinvitation",
            `?$select=op365_rfqinvitationid,op365_name,statuscode,op365_deliverydays&$filter=_op365_rfqid_value eq ${rfqId} and statecode eq 0&$orderby=op365_name`),
        api.retrieveMultipleRecords("op365_rfqquote", "?fetchXml=" + encodeURIComponent(
            "<fetch><entity name='op365_rfqquote'><attribute name='op365_price' /><attribute name='op365_invitationid' />" +
            "<attribute name='op365_requestlineid' /><filter><condition attribute='statecode' operator='eq' value='0' /></filter>" +
            "<link-entity name='op365_rfqinvitation' from='op365_rfqinvitationid' to='op365_invitationid'>" +
            `<filter><condition attribute='op365_rfqid' operator='eq' value='${rfqId}' /></filter></link-entity></entity></fetch>`)),
    ]);
    return {
        status: num(rfq.statuscode),
        lines: lines.entities.map(r => ({
            id: r.op365_purchaserequestlineid as string, name: (r.op365_name as string) || "", quantity: num(r.op365_quantity),
            uom: (r.op365_uom as string) || "", sortOrder: num(r.op365_sortorder),
        })),
        invitations: invitations.entities.map(r => ({
            id: r.op365_rfqinvitationid as string, name: (r.op365_name as string) || "", status: num(r.statuscode),
            deliveryDays: typeof r.op365_deliverydays === "number" ? r.op365_deliverydays : undefined,
        })),
        quotes: quotes.entities.filter(r => r._op365_requestlineid_value).map(r => ({
            invitationId: r._op365_invitationid_value as string, lineId: r._op365_requestlineid_value as string, price: num(r.op365_price),
        })),
    };
}
