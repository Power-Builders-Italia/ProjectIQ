// Project form: Save Baseline command (modern command bar, Main form of op365_project).
// Web resource op365_/scripts/project.form.js, command handler OP365.Project.saveBaseline(PrimaryControl).
var OP365 = OP365 || {};
(function () {
    "use strict";

    OP365.Project = {
        saveBaseline: function (form) {
            var id = form.data.entity.getId().replace(/[{}]/g, "");
            if (!id) {
                Xrm.Navigation.openAlertDialog({ text: "Save the project before saving a baseline." });
                return;
            }
            var confirm = {
                title: "Save Baseline",
                text: "Save the current WBS budget and dates as a new reference baseline?",
                confirmButtonLabel: "Save Baseline"
            };
            Xrm.Navigation.openConfirmDialog(confirm).then(function (result) {
                if (!result.confirmed) { return; }
                Xrm.Utility.showProgressIndicator("Saving baseline...");
                var request = {
                    entity: { entityType: "op365_project", id: id },
                    getMetadata: function () {
                        return {
                            boundParameter: "entity",
                            parameterTypes: { entity: { typeName: "mscrm.op365_project", structuralProperty: 5 } },
                            operationType: 0,
                            operationName: "op365_SaveBaseline"
                        };
                    }
                };
                return Xrm.WebApi.online.execute(request).then(function () {
                    Xrm.Utility.closeProgressIndicator();
                    ["Gantt", "Baselines"].forEach(function (name) {
                        var grid = form.getControl(name);
                        if (grid) { grid.refresh(); }
                    });
                    form.ui.setFormNotification("Baseline saved.", "INFO", "op365_baseline");
                }, function (error) {
                    Xrm.Utility.closeProgressIndicator();
                    Xrm.Navigation.openErrorDialog({ message: error.message });
                });
            });
        }
    };
})();
