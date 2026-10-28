using System.ComponentModel.Composition;
using Microsoft.Xrm.Tooling.PackageDeployment.CrmPackageExtentionBase;

namespace ProjectIQ.Package
{
    /// <summary>
    /// Package Deployer extension of ProjectIQ: names the package; the import itself is driven by PkgAssets/ImportConfig.xml.
    /// </summary>
    [Export(typeof(IImportExtensions))]
    public class PackageImportExtension : ImportExtension
    {
        public override string GetImportPackageDataFolderName => "PkgAssets";

        public override string GetNameOfImport(bool plural) => "ProjectIQ";

        public override string GetLongNameOfImport => "ProjectIQ - project and job management";

        public override string GetImportPackageDescriptionText =>
            "ProjectIQ: projects, WBS and Gantt, timesheets, materials, purchasing and the supplier portal on Microsoft Dataverse.";

        public override void InitializeCustomExtension()
        {
        }

        public override bool BeforeImportStage() => true;

        public override bool AfterPrimaryImport() => true;
    }
}
