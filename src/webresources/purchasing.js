// Purchasing commands (classic ribbon buttons on the purchase request, RFQ, purchase order, goods receipt and supplier
// invoice forms; enable rules on the status show each button only where it applies).
// Web resource op365_/scripts/purchasing.js; every handler receives the form (PrimaryControl).
var OP365 = OP365 || {};
(function () {
    "use strict";

    // English text -> [German, French, Italian]
    var TEXT = {
        "Working...": ["Wird ausgeführt...", "Traitement en cours...", "Elaborazione..."],
        "Submit": ["Einreichen", "Soumettre", "Invia"],
        "Submitting...": ["Wird gesendet...", "Soumission...", "Invio in corso..."],
        "Purchase request submitted for approval.": ["Bestellanforderung zur Genehmigung gesendet.", "Demande d'achat soumise pour approbation.", "Richiesta di acquisto inviata in approvazione."],
        "Approve": ["Genehmigen", "Approuver", "Approva"],
        "Approve this purchase request?": ["Diese Bestellanforderung genehmigen?", "Approuver cette demande d'achat ?", "Approvare questa richiesta di acquisto?"],
        "Approving...": ["Wird genehmigt...", "Approbation...", "Approvazione in corso..."],
        "Reject Purchase Request": ["Bestellanforderung ablehnen", "Rejeter la demande d'achat", "Rifiuta richiesta di acquisto"],
        "Cancel Request": ["Anforderung stornieren", "Annuler la demande", "Annulla richiesta"],
        "Cancel this purchase request?": ["Diese Bestellanforderung stornieren?", "Annuler cette demande d'achat ?", "Annullare questa richiesta di acquisto?"],
        "Cancelling...": ["Wird storniert...", "Annulation...", "Annullamento in corso..."],
        "Create RFQ": ["Angebotsanfrage erstellen", "Créer une demande de prix", "Crea RdO"],
        "Create a request for quotation for the preferred supplier and the item suppliers? You can add more suppliers before sending it.": ["Eine Angebotsanfrage für den bevorzugten Lieferanten und die Artikellieferanten erstellen? Vor dem Senden können Sie weitere Lieferanten hinzufügen.", "Créer une demande de prix pour le fournisseur préféré et les fournisseurs des articles ? Vous pourrez ajouter d'autres fournisseurs avant l'envoi.", "Creare una richiesta di offerta per il fornitore preferito e i fornitori degli articoli? Potrai aggiungere altri fornitori prima dell'invio."],
        "Creating the request for quotation...": ["Angebotsanfrage wird erstellt...", "Création de la demande de prix...", "Creazione della richiesta di offerta..."],
        "Create Order": ["Bestellung erstellen", "Créer la commande", "Crea ordine"],
        "Create a draft purchase order to the preferred supplier with these lines?": ["Einen Bestellentwurf mit diesen Positionen an den bevorzugten Lieferanten erstellen?", "Créer une commande d'achat brouillon pour le fournisseur préféré avec ces lignes ?", "Creare una bozza di ordine di acquisto al fornitore preferito con queste righe?"],
        "Creating the purchase order...": ["Bestellung wird erstellt...", "Création de la commande d'achat...", "Creazione dell'ordine di acquisto..."],
        "Send": ["Senden", "Envoyer", "Invia"],
        "Send the request for quotation to the invited suppliers?": ["Die Angebotsanfrage an die eingeladenen Lieferanten senden?", "Envoyer la demande de prix aux fournisseurs invités ?", "Inviare la richiesta di offerta ai fornitori invitati?"],
        "Sending...": ["Wird gesendet...", "Envoi...", "Invio in corso..."],
        "Request for quotation sent.": ["Angebotsanfrage gesendet.", "Demande de prix envoyée.", "Richiesta di offerta inviata."],
        "Cancel RFQ": ["Angebotsanfrage stornieren", "Annuler la demande de prix", "Annulla RdO"],
        "Cancel this request for quotation?": ["Diese Angebotsanfrage stornieren?", "Annuler cette demande de prix ?", "Annullare questa richiesta di offerta?"],
        "Send to Supplier": ["An Lieferanten senden", "Envoyer au fournisseur", "Invia al fornitore"],
        "Mark the order as sent to the supplier? Its lines can no longer change.": ["Die Bestellung als an den Lieferanten gesendet markieren? Ihre Positionen können dann nicht mehr geändert werden.", "Marquer la commande comme envoyée au fournisseur ? Ses lignes ne pourront plus être modifiées.", "Segnare l'ordine come inviato al fornitore? Le sue righe non potranno più essere modificate."],
        "Confirm": ["Bestätigen", "Confirmer", "Conferma"],
        "Record the supplier confirmation?": ["Die Bestätigung des Lieferanten erfassen?", "Enregistrer la confirmation du fournisseur ?", "Registrare la conferma del fornitore?"],
        "Confirming...": ["Wird bestätigt...", "Confirmation...", "Conferma in corso..."],
        "Back to Draft": ["Zurück zu Entwurf", "Repasser en brouillon", "Riporta in bozza"],
        "Move the order back to Draft to change it?": ["Die Bestellung zur Bearbeitung zurück in den Entwurf setzen?", "Repasser la commande en brouillon pour la modifier ?", "Riportare l'ordine in bozza per modificarlo?"],
        "Updating...": ["Wird aktualisiert...", "Mise à jour...", "Aggiornamento in corso..."],
        "Cancel Order": ["Bestellung stornieren", "Annuler la commande", "Annulla ordine"],
        "Cancel this purchase order?": ["Diese Bestellung stornieren?", "Annuler cette commande d'achat ?", "Annullare questo ordine di acquisto?"],
        "Register Receipt": ["Eingang erfassen", "Enregistrer la réception", "Registra ricevimento"],
        "Cancel Receipt": ["Eingang stornieren", "Annuler la réception", "Annulla ricevimento"],
        "Delete this receipt and its material usage, and restore the quantities to receive?": ["Diesen Wareneingang und seinen Materialverbrauch löschen und die zu empfangenden Mengen wiederherstellen?", "Supprimer cette réception et sa consommation de matériel, et rétablir les quantités à recevoir ?", "Eliminare questo ricevimento e il relativo consumo di materiale, ripristinando le quantità da ricevere?"],
        "Cancelling the receipt...": ["Wareneingang wird storniert...", "Annulation de la réception...", "Annullamento del ricevimento..."],
        "Approve this supplier invoice?": ["Diese Lieferantenrechnung genehmigen?", "Approuver cette facture fournisseur ?", "Approvare questa fattura fornitore?"],
        "Reject Supplier Invoice": ["Lieferantenrechnung ablehnen", "Rejeter la facture fournisseur", "Rifiuta fattura fornitore"]
    };
    function t(text) {
        var col = { 1031: 0, 1036: 1, 1040: 2 }[Xrm.Utility.getGlobalContext().userSettings.languageId];
        return col === undefined || !TEXT[text] ? text : TEXT[text][col];
    }

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
            Xrm.Utility.showProgressIndicator(options.progress || t("Working..."));
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
            return run(form, { action: "op365_SubmitPurchaseRequest", title: t("Submit"), progress: t("Submitting..."), done: t("Purchase request submitted for approval.") });
        },
        approveRequest: function (form) {
            return run(form, { action: "op365_DecidePurchaseRequest", body: { Approve: true }, title: t("Approve"), confirm: t("Approve this purchase request?"), progress: t("Approving...") });
        },
        rejectRequest: function (form) { return reject(form, "op365_DecidePurchaseRequest", t("Reject Purchase Request")); },
        cancelRequest: function (form) {
            return run(form, { action: "op365_CancelPurchaseRequest", title: t("Cancel Request"), confirm: t("Cancel this purchase request?"), progress: t("Cancelling...") });
        },
        createRfq: function (form) {
            return run(form, {
                action: "op365_CreateRfq", title: t("Create RFQ"), confirm: t("Create a request for quotation for the preferred supplier and the item suppliers? You can add more suppliers before sending it."),
                progress: t("Creating the request for quotation..."), open: { table: "op365_rfq", field: "RfqId" }
            });
        },
        createOrder: function (form) {
            return run(form, {
                action: "op365_CreatePurchaseOrder", title: t("Create Order"), confirm: t("Create a draft purchase order to the preferred supplier with these lines?"),
                progress: t("Creating the purchase order..."), open: { table: "op365_purchaseorder", field: "PurchaseOrderId" }
            });
        },

        // ----- RFQ
        sendRfq: function (form) {
            return run(form, { action: "op365_SendRfq", title: t("Send"), confirm: t("Send the request for quotation to the invited suppliers?"), progress: t("Sending..."), done: t("Request for quotation sent.") });
        },
        cancelRfq: function (form) {
            return run(form, { action: "op365_CancelRfq", title: t("Cancel RFQ"), confirm: t("Cancel this request for quotation?"), progress: t("Cancelling...") });
        },

        // ----- purchase order
        sendOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Sent" }, title: t("Send to Supplier"), confirm: t("Mark the order as sent to the supplier? Its lines can no longer change."), progress: t("Sending...") });
        },
        confirmOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Confirmed" }, title: t("Confirm"), confirm: t("Record the supplier confirmation?"), progress: t("Confirming...") });
        },
        reopenOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Draft" }, title: t("Back to Draft"), confirm: t("Move the order back to Draft to change it?"), progress: t("Updating...") });
        },
        cancelOrder: function (form) {
            return run(form, { action: "op365_SetPurchaseOrderStatus", body: { Status: "Cancelled" }, title: t("Cancel Order"), confirm: t("Cancel this purchase order?"), progress: t("Cancelling...") });
        },
        registerReceipt: function (form) {
            var open = function () {
                return Xrm.Navigation.navigateTo(
                    { pageType: "webresource", webresourceName: "op365_/pages/receipt.html", data: "id=" + idOf(form) },
                    { target: 2, position: 1, width: { value: 720, unit: "px" }, height: { value: 560, unit: "px" }, title: t("Register Receipt") }
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
            return Xrm.Navigation.openConfirmDialog({ title: t("Cancel Receipt"), text: t("Delete this receipt and its material usage, and restore the quantities to receive?"), confirmButtonLabel: t("Cancel Receipt") })
                .then(function (r) {
                    if (!r.confirmed) { return; }
                    Xrm.Utility.showProgressIndicator(t("Cancelling the receipt..."));
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
            return run(form, { action: "op365_DecideSupplierInvoice", body: { Approve: true }, title: t("Approve"), confirm: t("Approve this supplier invoice?"), progress: t("Approving...") });
        },
        rejectInvoice: function (form) { return reject(form, "op365_DecideSupplierInvoice", t("Reject Supplier Invoice")); }
    };
})();
