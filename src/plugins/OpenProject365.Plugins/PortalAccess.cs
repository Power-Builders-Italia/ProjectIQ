using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Supplier portal access: the "Supplier" web role of the Power Pages site follows the contact's Company Name, and
    /// contacts are invited from the app with a Power Pages invitation.
    /// </summary>
    internal static class PortalAccess
    {
        public const string RoleName = "Supplier";
        private const int WebRoleComponent = 11;           // powerpagecomponenttype of a web role
        private const string ContactRoles = "powerpagecomponent_mspp_webrole_contact";
        private const string InvitationRoles = "adx_invitation_mspp_webrole_powerpagecomponent";
        private const int SingleInvitation = 756150000;
        public const int InvitationDays = 30;

        /// <summary>The "Supplier" web role (id and site), or null when no supplier portal is installed.</summary>
        public static Entity SupplierRole(IOrganizationService system)
        {
            var query = new QueryExpression("powerpagecomponent") { ColumnSet = new ColumnSet("powerpagesiteid"), TopCount = 1 };
            query.Criteria.AddCondition("powerpagecomponenttype", ConditionOperator.Equal, WebRoleComponent);
            query.Criteria.AddCondition("name", ConditionOperator.Equal, RoleName);
            query.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            return system.RetrieveMultiple(query).Entities.FirstOrDefault();
        }

        /// <summary>True when the reference is an account flagged as supplier.</summary>
        public static bool IsSupplier(IOrganizationService system, EntityReference company)
        {
            if (company == null || company.LogicalName != "account") return false;
            var account = system.Retrieve("account", company.Id, new ColumnSet("op365_issupplier"));
            return account.GetAttributeValue<bool>("op365_issupplier");
        }

        public static bool HasRole(IOrganizationService system, Guid contactId, Guid roleId)
        {
            var query = new QueryExpression(ContactRoles) { ColumnSet = new ColumnSet(false), TopCount = 1 };
            query.Criteria.AddCondition("contactid", ConditionOperator.Equal, contactId);
            query.Criteria.AddCondition("powerpagecomponentid", ConditionOperator.Equal, roleId);
            return system.RetrieveMultiple(query).Entities.Count > 0;
        }

        public static void SetRole(IOrganizationService system, Guid contactId, Guid roleId, bool grant)
        {
            if (HasRole(system, contactId, roleId) == grant) return;
            var related = new EntityReferenceCollection { new EntityReference("powerpagecomponent", roleId) };
            var relationship = new Relationship(ContactRoles);
            if (grant) system.Associate("contact", contactId, relationship, related);
            else system.Disassociate("contact", contactId, relationship, related);
        }

        /// <summary>Single-use invitation of the contact, assigning the Supplier role and the supplier on redemption.</summary>
        public static Guid CreateInvitation(IOrganizationService system, Entity contact, Entity role, DateTime now)
        {
            var invitation = new Entity("adx_invitation")
            {
                ["adx_name"] = $"Supplier portal: {contact.GetAttributeValue<string>("fullname")}",
                ["adx_type"] = new OptionSetValue(SingleInvitation),
                ["adx_invitecontact"] = contact.ToEntityReference(),
                ["adx_assigntoaccount"] = contact.GetAttributeValue<EntityReference>("parentcustomerid"),
                ["adx_maximumredemptions"] = 1,
                ["adx_expirydate"] = now.AddDays(InvitationDays),
                ["mspp_websiteid"] = new EntityReference("powerpagesite", role.GetAttributeValue<EntityReference>("powerpagesiteid").Id),
            };
            var id = system.Create(invitation);
            system.Associate("adx_invitation", id, new Relationship(InvitationRoles),
                new EntityReferenceCollection { new EntityReference("powerpagecomponent", role.Id) });
            return id;
        }

        /// <summary>Registration link of the invitation on the portal site (its primary domain), or null.</summary>
        public static string InvitationLink(IOrganizationService system, Guid invitationId, Entity role)
        {
            var code = system.Retrieve("adx_invitation", invitationId, new ColumnSet("adx_invitationcode"))
                .GetAttributeValue<string>("adx_invitationcode");
            var site = system.Retrieve("powerpagesite", role.GetAttributeValue<EntityReference>("powerpagesiteid").Id,
                new ColumnSet("primarydomainname")).GetAttributeValue<string>("primarydomainname");
            if (string.IsNullOrWhiteSpace(code) || string.IsNullOrWhiteSpace(site)) return null;
            return $"https://{site}/register/?returnurl=%2f&invitation={Uri.EscapeDataString(code)}";
        }
    }

    /// <summary>
    /// Contact Create/Update of Company Name (post): a contact of a supplier account gets the Supplier web role of the
    /// supplier portal, and loses it when the Company Name stops being a supplier. A supplier who registered by
    /// themselves can work on the portal as soon as the buyer links the contact to its supplier.
    /// </summary>
    public class SupplierContactRole : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Message == "Update" && !context.Changed("parentcustomerid")) return;
            var system = context.SystemService;
            var role = PortalAccess.SupplierRole(system);
            if (role == null) return;
            var supplier = PortalAccess.IsSupplier(system, context.Get<EntityReference>("parentcustomerid"));
            if (context.Message == "Create" && !supplier) return;
            PortalAccess.SetRole(system, context.PrimaryId, role.Id, supplier);
        }
    }

    /// <summary>
    /// Custom API op365_InviteToPortal (bound to contact). Output InvitationId. Creates a single-use Power Pages invitation
    /// (30 days) that gives the Supplier web role and the contact's supplier when it is redeemed, then e-mails the registration
    /// link to the contact with the PortalInvitation template of op365_SupplierEmailTemplates (supplier's language).
    /// The contact needs an e-mail and a supplier as Company Name; nothing is kept when the e-mail cannot be sent.
    /// </summary>
    public class InviteToPortal : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            var system = context.SystemService;
            var contact = context.Service.Retrieve("contact", context.TargetReference.Id,
                new ColumnSet("fullname", "emailaddress1", "parentcustomerid"));
            if (string.IsNullOrWhiteSpace(contact.GetAttributeValue<string>("emailaddress1")))
                SupplierDocuments.Fail("Add the e-mail address of the contact before inviting it to the supplier portal.");
            if (!PortalAccess.IsSupplier(system, contact.GetAttributeValue<EntityReference>("parentcustomerid")))
                SupplierDocuments.Fail("Set a supplier as Company Name of the contact before inviting it to the supplier portal.");
            var role = PortalAccess.SupplierRole(system);
            if (role == null) SupplierDocuments.Fail("The supplier portal is not installed in this environment.");
            var supplier = contact.GetAttributeValue<EntityReference>("parentcustomerid");
            var expiry = DateTime.UtcNow.AddDays(PortalAccess.InvitationDays);
            var id = PortalAccess.CreateInvitation(system, contact, role, DateTime.UtcNow);
            var link = PortalAccess.InvitationLink(system, id, role);
            var tokens = new Dictionary<string, string>
            {
                ["{Contact}"] = contact.GetAttributeValue<string>("fullname") ?? "",
                ["{Email}"] = contact.GetAttributeValue<string>("emailaddress1"),
                ["{Link}"] = link ?? "",
                ["{ExpiryDate}"] = expiry.ToString("dd/MM/yyyy"),
            };
            // A failure rolls back the invitation: the buyer can fix the e-mail settings and invite again.
            if (link == null || !new SupplierMailer(context).Send("PortalInvitation", supplier.Id, new EntityReference("adx_invitation", id), tokens, contact.ToEntityReference()))
                SupplierDocuments.Fail("The invitation e-mail could not be sent: check the environment variables op365_SupplierEmailSender and op365_SupplierEmailTemplates (PortalInvitation).");
            PortalAccess.SetRole(system, contact.Id, role.Id, true);
            context.Execution.OutputParameters["InvitationId"] = id;
        }
    }
}
