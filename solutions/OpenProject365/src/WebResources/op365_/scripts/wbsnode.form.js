// WBS Node form: the Parent Node lookup only offers nodes of the same project.
// Web resource op365_/scripts/wbsnode.form.js, onload handler OP365.WbsNode.onLoad.
var OP365 = OP365 || {};
(function () {
    "use strict";

    function projectFilter(form) {
        var project = form.getAttribute("op365_projectid").getValue();
        if (!project || !project.length) { return null; }
        var id = project[0].id.replace(/[{}]/g, "");
        var self = form.data.entity.getId().replace(/[{}]/g, "");
        return "<filter type='and'><condition attribute='op365_projectid' operator='eq' value='" + id + "' />" +
            (self ? "<condition attribute='op365_wbsnodeid' operator='ne' value='" + self + "' />" : "") + "</filter>";
    }

    OP365.WbsNode = {
        onLoad: function (executionContext) {
            var form = executionContext.getFormContext();
            var parent = form.getControl("op365_parentid");
            if (!parent) { return; }
            parent.addPreSearch(function () {
                var filter = projectFilter(form);
                if (filter) { parent.addCustomFilter(filter, "op365_wbsnode"); }
            });
        }
    };
})();
