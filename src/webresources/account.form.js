// Account forms: open suppliers on the Supplier form and customers on the Customer form.
// Web resource op365_/scripts/account.form.js, onload handler OP365.Account.onLoad on both forms.
var OP365 = OP365 || {};
(function () {
    "use strict";

    // form ids are fixed by the solution; labels change with the user's language
    var CUSTOMER = "f83260a8-d6cf-f111-a05b-7ced8d2d53e4";
    var SUPPLIER = "2c3360a8-d6cf-f111-a05b-7ced8d2d53e4";

    function idOf(item) { return item.getId().replace(/[{}]/g, "").toLowerCase(); }

    OP365.Account = {
        onLoad: function (executionContext) {
            var form = executionContext.getFormContext();
            var current = form.ui.formSelector.getCurrentItem();
            if (!current) {
                return;
            }
            var currentId = idOf(current);
            var isCustomer = form.getAttribute("op365_iscustomer");
            var isSupplier = form.getAttribute("op365_issupplier");

            if (form.ui.getFormType() === 1) {
                // new record: flag it according to the form the user chose
                if (currentId === SUPPLIER && isSupplier) { isSupplier.setValue(true); }
                if (currentId === CUSTOMER && isCustomer) { isCustomer.setValue(true); }
                return;
            }

            var supplierOnly = isSupplier && isSupplier.getValue() && !(isCustomer && isCustomer.getValue());
            var target = supplierOnly ? SUPPLIER : CUSTOMER;
            if (currentId === target) {
                return;
            }
            form.ui.formSelector.items.forEach(function (item) {
                if (idOf(item) === target) {
                    item.navigate();
                }
            });
        }
    };
})();
