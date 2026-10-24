// Time Entry and Material Usage forms: the WBS Node lookup only offers nodes of the selected project,
// and changing the project clears a node of another project.
// Web resource op365_/scripts/execution.form.js, onload handler OP365.Execution.onLoad.
var OP365 = OP365 || {};
(function () {
    "use strict";

    function projectId(form) {
        var project = form.getAttribute("op365_projectid").getValue();
        return project && project.length ? project[0].id.replace(/[{}]/g, "").toLowerCase() : null;
    }

    OP365.Execution = {
        onLoad: function (executionContext) {
            var form = executionContext.getFormContext();
            var node = form.getControl("op365_wbsnodeid");
            if (!node) { return; }
            node.addPreSearch(function () {
                var id = projectId(form);
                if (id) {
                    node.addCustomFilter("<filter type='and'><condition attribute='op365_projectid' operator='eq' value='" + id + "' /></filter>", "op365_wbsnode");
                }
            });
            form.getAttribute("op365_projectid").addOnChange(function () {
                var value = form.getAttribute("op365_wbsnodeid").getValue();
                if (!value || !value.length) { return; }
                var id = projectId(form);
                if (!id) { form.getAttribute("op365_wbsnodeid").setValue(null); return; }
                Xrm.WebApi.retrieveRecord("op365_wbsnode", value[0].id.replace(/[{}]/g, ""), "?$select=_op365_projectid_value").then(function (n) {
                    if ((n._op365_projectid_value || "").toLowerCase() !== id) { form.getAttribute("op365_wbsnodeid").setValue(null); }
                }, function () { form.getAttribute("op365_wbsnodeid").setValue(null); });
            });
        }
    };
})();
