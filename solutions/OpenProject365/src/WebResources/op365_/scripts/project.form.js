// Project form: Save Baseline command (modern command bar, Main form of op365_project).
// Web resource op365_/scripts/project.form.js, command handler OP365.Project.saveBaseline(PrimaryControl).
var OP365 = OP365 || {};
(function () {
    "use strict";

    // English text -> [German, French, Italian]
    var TEXT = {
        "Save the project before saving a baseline.": ["Speichern Sie das Projekt, bevor Sie einen Basisplan speichern.", "Enregistrez le projet avant d'enregistrer un planning de référence.", "Salva la commessa prima di salvare una baseline."],
        "Save Baseline": ["Basisplan speichern", "Enregistrer le planning de référence", "Salva baseline"],
        "Save the current WBS budget and dates as a new reference baseline?": ["Aktuelles PSP-Budget und Termine als neuen Basisplan speichern?", "Enregistrer le budget et les dates actuels du WBS comme nouveau planning de référence ?", "Salvare budget e date attuali della WBS come nuova baseline di riferimento?"],
        "Saving baseline...": ["Basisplan wird gespeichert...", "Enregistrement du planning de référence...", "Salvataggio baseline..."],
        "Baseline saved.": ["Basisplan gespeichert.", "Planning de référence enregistré.", "Baseline salvata."]
    };
    function t(text) {
        var col = { 1031: 0, 1036: 1, 1040: 2 }[Xrm.Utility.getGlobalContext().userSettings.languageId];
        return col === undefined || !TEXT[text] ? text : TEXT[text][col];
    }

    OP365.Project = {
        saveBaseline: function (form) {
            var id = form.data.entity.getId().replace(/[{}]/g, "");
            if (!id) {
                Xrm.Navigation.openAlertDialog({ text: t("Save the project before saving a baseline.") });
                return;
            }
            var confirm = {
                title: t("Save Baseline"),
                text: t("Save the current WBS budget and dates as a new reference baseline?"),
                confirmButtonLabel: t("Save Baseline")
            };
            Xrm.Navigation.openConfirmDialog(confirm).then(function (result) {
                if (!result.confirmed) { return; }
                Xrm.Utility.showProgressIndicator(t("Saving baseline..."));
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
                    form.ui.setFormNotification(t("Baseline saved."), "INFO", "op365_baseline");
                }, function (error) {
                    Xrm.Utility.closeProgressIndicator();
                    Xrm.Navigation.openErrorDialog({ message: error.message });
                });
            });
        }
    };
})();
