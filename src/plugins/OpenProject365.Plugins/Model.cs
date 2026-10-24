namespace OpenProject365.Plugins
{
    /// <summary>Logical names used by the plugins.</summary>
    internal static class Model
    {
        public const string Project = "op365_project";
        public const string ProjectMember = "op365_projectmember";
        public const string WbsNode = "op365_wbsnode";
        public const string WbsDependency = "op365_wbsdependency";
        public const string Baseline = "op365_baseline";
        public const string BaselineNode = "op365_baselinenode";
        public const string Resource = "op365_resource";
        public const string ResourceCost = "op365_resourcecost";
        public const string TimeEntry = "op365_timeentry";
        public const string MaterialUsage = "op365_materialusage";
        public const string Settings = "op365_settings";
        public const string Item = "op365_item";
        public const string PurchaseRequest = "op365_purchaserequest";
        public const string PurchaseRequestLine = "op365_purchaserequestline";
        public const string Rfq = "op365_rfq";
        public const string RfqInvitation = "op365_rfqinvitation";
        public const string RfqQuote = "op365_rfqquote";
        public const string PurchaseOrder = "op365_purchaseorder";
        public const string PurchaseOrderLine = "op365_purchaseorderline";
        public const string GoodsReceipt = "op365_goodsreceipt";
        public const string GoodsReceiptLine = "op365_goodsreceiptline";
        public const string SupplierInvoice = "op365_supplierinvoice";
        public const string SupplierInvoiceLine = "op365_supplierinvoiceline";

        public const string ProjectId = "op365_projectid";
        public const string CustomerId = "op365_customerid";
        public const string ProjectManagerId = "op365_projectmanagerid";
        public const string ContractValue = "op365_contractvalue";
        public const string BudgetTotal = "op365_budgettotal";
        public const string BudgetHours = "op365_budgethours";
        public const string ProgressPct = "op365_progresspct";
        public const string UserId = "op365_userid";
        public const string ProjectRole = "op365_projectrole";
        public const string ParentId = "op365_parentid";
        public const string WbsNodeId = "op365_wbsnodeid";
        public const string ResourceId = "op365_resourceid";
        public const string ActualCost = "op365_actualcost";
        public const string ActualHours = "op365_actualhours";
        public const string CommittedCost = "op365_committedcost";
        public const string ItemId = "op365_itemid";
        public const string SupplierId = "op365_supplierid";
        public const string PurchaseRequestId = "op365_purchaserequestid";
        public const string PurchaseOrderId = "op365_purchaseorderid";
        public const string RfqId = "op365_rfqid";
        public const string InvitationId = "op365_invitationid";
        public const string RequestLineId = "op365_requestlineid";
        public const string OrderLineId = "op365_orderlineid";
        public const string GoodsReceiptId = "op365_goodsreceiptid";
        public const string SupplierInvoiceId = "op365_supplierinvoiceid";

        public const int RoleManager = 365000000;
        public const int RoleContributor = 365000001;
        public const int RoleReader = 365000002;

        // project status reasons
        public const int ProjectInProgress = 1;

        // time entry status reasons
        public const int TimeDraft = 1;
        public const int TimeSubmitted = 365000000;
        public const int TimeApproved = 365000001;
        public const int TimeRejected = 365000002;

        // purchase request status reasons and approval levels
        public const int PrDraft = 1;
        public const int PrSubmitted = 365000000;
        public const int PrApproved = 365000001;
        public const int PrRejected = 365000002;
        public const int PrCancelled = 365000003;
        public const int PrOrdered = 365000004;
        public const int LevelManager = 365000000;
        public const int LevelAdministrator = 365000001;

        // RFQ and invitation status reasons
        public const int RfqDraft = 1;
        public const int RfqSent = 365000000;
        public const int RfqAwarded = 365000001;
        public const int RfqCancelled = 365000002;
        public const int InvitationToInvite = 1;
        public const int InvitationInvited = 365000000;
        public const int InvitationResponded = 365000001;
        public const int InvitationDeclined = 365000002;

        // purchase order status reasons
        public const int PoDraft = 1;
        public const int PoSent = 365000000;
        public const int PoConfirmed = 365000001;
        public const int PoReceived = 365000002;
        public const int PoCancelled = 365000003;

        // supplier invoice status reasons
        public const int InvoiceToReview = 1;
        public const int InvoiceApproved = 365000000;
        public const int InvoiceRejected = 365000001;
    }
}
