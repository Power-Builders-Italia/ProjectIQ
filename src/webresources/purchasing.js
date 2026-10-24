// Purchasing commands (classic ribbon buttons on the purchase request, RFQ, purchase order, goods receipt and supplier
// invoice forms; enable rules on the status show each button only where it applies).
// Web resource op365_/scripts/purchasing.js; every handler receives the form (PrimaryControl).
var OP365 = OP365 || {};
(function () {
    "use strict";

    var SETS = {
        op365_purchaserequest: "op365_purchaserequests", op365_rfq: "op365_rfqs", op365_purchaseorder: "op365_purchaseorders",
        op365_goodsreceipt: "op365_goodsreceipts", op365_supplierinvoice: "op365_supplierinvoices"
    };

    function idOf(form) { return form.data.entity.getId().replace(/[{}]/g, ""); }
    function tableOf(form) { return form.data.entity.getEntityName(); }

    // Bound Custom API through the Web API; resolves with the response body.
    function call(form, action, body) {
        var url = Xrm.Utility.getGlobalContext().getClientUrl() + "/api/data/v9.2/" + SETS[tableOf(form)] + "(" + idOf(form) + ")/Microsoft.Dynamics.CRM." + action;
        return fetch(url, {
            method: "POST", credentials: "same-origin", body: JSON.stringify(body || {}),
            headers: { "Content-Type": "application/json; charset=utf-8", Accept: "application/json", "OData-Version": "4.0", "OData-MaxVersion": "4.0" }
        }).then(function (response) {
            return response.text().then(function (text) {
                var json = text ? JSON.parse(text) : {};
                if (!response.ok) { throw new Error(json.error && json.error.message || response.statusText); }
                return json;
            });
        });
    }

    function refresh(form) {
        return form.data.refresh(false).then(function () { form.ui.refreshRibbon(); });
    }

    // Saves pending changes, asks for confirmation, runs the action, refreshes the form (or opens the created record).
    function run(form, options) {
        var go = function () {
            Xrm.Utility.showProgressIndicator(options.progress || "Working...");
            return call(form, options.action, options.body).then(function (result) {
                Xrm.Utility.closeProgressIndicator();
                if (options.open && result[options.open.field]) {
                    return Xrm.Navigation.openForm({ entityName: options.open.table, entityId: result[options.open.field] });
                }
                if (options.done) { form.ui.setFormNotification(options.done, "INFO", "op365_purchasing"); }
                return refresh(form);
            }, function (error) {
                Xrm.Utility.closeProgressIndicator();
                Xrm.Navigation.openErrorDialog({ message: error.message });
            });
        };
        var start = form.data.entity.getIsDirty() ? form.data.save() : Promise.resolve();
        return start.then(function () {
            if (!options.confirm) { return go(); }
            return Xrm.Navigation.openConfirmDialog({ title: options.title, text: options.confirm, confirmButtonLabel: options.title })
                .then(function (r) { if (r.confirmed) { return go(); } });
        });
    }

    // Note dialog (web resource page) that runs a decide action with Approve = false.
    function reject(form, action, title) {
        var data = "action=" + encodeURIComponent(action) + "&set=" + SETS[tableOf(form)] + "&id=" + idOf(form) + "&title=" + encodeURIComponent(title);
        return Xrm.Navigation.navigateTo(
            { pageType: "webresource", webresourceName: "op365_/pages/decision.html", data: data },
            { target: 2, position: 1, width: { value: 480, unit: "px" }, height: { value: 320, unit: "px" }, title: title }
        ).then(function () { return refresh(form); });
    }

    OP365.Purchasing = {
        // ----- purchase request
        submitRequest: function (form) {
            return run(form, { action: "op365_SubmitPurchaseRequest", title: "Submit", progress: "Submitting...", done: "Purchase request submitted for approval." });
        },
        approveRequest: function (form) {
            return run(form, { action: "op365_DecidePurchaseRequest", body: { Approve: true }, title: "Approve", confirm: "Approve this purchase request?", progress: "Approving..." });
        },
        rejectRequest: function (form) { return reject(form, "op365_DecidePurchaseRequest", "Reject Purchase Request"); },
        cancelRequest: function (form) {
            return run(form, { action: "op365_CancelPurchaseRequest", title: "Cancel Request", confirm: "Cancel this purchase request?", progress: "Cancelling..." });
        },
        createRfq: function (form) {
            return run(form, {
                action: "op365_CreateRfq", title: "Create RFQ", confirm: "Create a request for quotation for the preferred supplier and the item suppliers? You can add more suppliers before sending it.",
                progress: "Creating the request for quotation...", open: { table: "op365_rfq", field: "RfqId" }
            });
        },
        createOrder: function (form) {
            return run(form, {
                action: "op365_CreatePurchaseOrder", title: "Create Order", confirm: "Create a draft purchase order to the preferred supplier with these lines?",
                progress: "Creating the purchase order...", open: { table: "op365_purchaseorder", field: "PurchaseOrderId" }
            });
        },

        // ----- RFQ
        sendRfq: function (form) {
            return run(form, { action: "op365_SendRfq", title: "Send", confirm: "Send the request for quotation to the invited suppliers?", progress: "Sending...", done: "Request for quotation sent." });
        },
        cancelRfq: function (form) {
            return run(form, { action: "op365_CancelRfq", title: "Cancel RFQ", confirm: "Cancel this request for quotation?", progress: "Cancelling..." });
        },

        // ----- purchase order
        sendOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Sent" }, title: "Send to Supplier", confirm: "Mark the order as sent to the supplier? Its lines can no longer change.", progress: "Sending..." });
        },
        confirmOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Confirmed" }, title: "Confirm", confirm: "Record the supplier confirmation?", progress: "Confirming..." });
        },
        reopenOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Draft" }, title: "Back to Draft", confirm: "Move the order back to Draft to change it?", progress: "Updating..." });
        },
        cancelOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Cancelled" }, title: "Cancel Order", confirm: "Cancel this purchase order?", progress: "Cancelling..." });
        },
        registerReceipt: function (form) {
            var open = function () {
                return Xrm.Navigation.navigateTo(
                    { pageType: "webresource", webresourceName: "op365_/pages/receipt.html", data: "id=" + idOf(form) },
                    { target: 2, position: 1, width: { value: 720, unit: "px" }, height: { value: 560, unit: "px" }, title: "Register Receipt" }
                ).then(function () {
                    ["Receipts", "Lines"].forEach(function (name) { var c = form.getControl(name); if (c) { c.refresh(); } });
                    return refresh(form);
                });
            };
            return form.data.entity.getIsDirty() ? form.data.save().then(open) : open();
        },

        // ----- goods receipt
        cancelReceipt: function (form) {
            var order = form.getAttribute("op365_purchaseorderid").getValue();
            return Xrm.Navigation.openConfirmDialog({ title: "Cancel Receipt", text: "Delete this receipt and its material usage, and restore the quantities to receive?", confirmButtonLabel: "Cancel Receipt" })
                .then(function (r) {
                    if (!r.confirmed) { return; }
                    Xrm.Utility.showProgressIndicator("Cancelling the receipt...");
                    return call(form, "op365_CancelGoodsReceipt").then(function () {
                        Xrm.Utility.closeProgressIndicator();
                        if (order && order.length) { return Xrm.Navigation.openForm({ entityName: "op365_purchaseorder", entityId: order[0].id }); }
                        return Xrm.Navigation.navigateTo({ pageType: "entitylist", entityName: "op365_goodsreceipt" });
                    }, function (error) {
                        Xrm.Utility.closeProgressIndicator();
                        Xrm.Navigation.openErrorDialog({ message: error.message });
                    });
                });
        },

        // ----- supplier invoice
        approveInvoice: function (form) {
            return run(form, { action: "op365_DecideSupplierInvoice", body: { Approve: true }, title: "Approve", confirm: "Approve this supplier invoice?", progress: "Approving..." });
        },
        rejectInvoice: function (form) { return reject(form, "op365_DecideSupplierInvoice", "Reject Supplier Invoice"); }
    };
})();
