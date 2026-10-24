// Account forms: open suppliers on the Supplier form and customers on the Customer form.
// Web resource op365_/scripts/account.form.js, onload handler OP365.Account.onLoad on both forms.
var OP365 = OP365 || {};
OP365.Account = {
    onLoad: function (executionContext) {
        var form = executionContext.getFormContext();
        var current = form.ui.formSelector.getCurrentItem();
        if (!current) {
            return;
        }
        var label = current.getLabel();
        var isCustomer = form.getAttribute("op365_iscustomer");
        var isSupplier = form.getAttribute("op365_issupplier");

        if (form.ui.getFormType() === 1) {
            // new record: flag it according to the form the user chose
            if (label === "Supplier" && isSupplier) { isSupplier.setValue(true); }
            if (label === "Customer" && isCustomer) { isCustomer.setValue(true); }
            return;
        }

        var supplierOnly = isSupplier && isSupplier.getValue() && !(isCustomer && isCustomer.getValue());
        var target = supplierOnly ? "Supplier" : "Customer";
        if (label === target) {
            return;
        }
        form.ui.formSelector.items.forEach(function (item) {
            if (item.getLabel() === target) {
                item.navigate();
            }
        });
    }
};
