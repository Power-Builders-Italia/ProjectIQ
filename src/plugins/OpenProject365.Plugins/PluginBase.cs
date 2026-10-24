using System;
using System.Linq;
using Microsoft.Xrm.Sdk;

namespace OpenProject365.Plugins
{
    /// <summary>Common plumbing: services, images and the cascade check shared by all plugins.</summary>
    public abstract class PluginBase : IPlugin
    {
        public const string PreImage = "PreImage";

        public void Execute(IServiceProvider serviceProvider)
        {
            var context = new LocalContext(serviceProvider);
            try
            {
                Run(context);
            }
            catch (InvalidPluginExecutionException)
            {
                throw;
            }
            catch (Exception ex)
            {
                context.Trace(ex.ToString());
                throw new InvalidPluginExecutionException(GetType().Name + ": " + ex.Message, ex);
            }
        }

        protected abstract void Run(LocalContext context);
    }

    public sealed class LocalContext
    {
        private readonly ITracingService tracing;

        public LocalContext(IServiceProvider serviceProvider)
        {
            Execution = (IPluginExecutionContext)serviceProvider.GetService(typeof(IPluginExecutionContext));
            tracing = (ITracingService)serviceProvider.GetService(typeof(ITracingService));
            var factory = (IOrganizationServiceFactory)serviceProvider.GetService(typeof(IOrganizationServiceFactory));
            Service = factory.CreateOrganizationService(Execution.UserId);
            // null user = SYSTEM: used for totals and access teams, which users cannot write themselves
            SystemService = factory.CreateOrganizationService(null);
        }

        public IPluginExecutionContext Execution { get; }
        public IOrganizationService Service { get; }
        public IOrganizationService SystemService { get; }

        public string Message => Execution.MessageName;

        public Entity Target =>
            Execution.InputParameters.Contains("Target") ? Execution.InputParameters["Target"] as Entity : null;

        public EntityReference TargetReference =>
            Execution.InputParameters.Contains("Target") ? Execution.InputParameters["Target"] as EntityReference : null;

        public Entity Pre =>
            Execution.PreEntityImages.Contains(PluginBase.PreImage) ? Execution.PreEntityImages[PluginBase.PreImage] : null;

        public Guid PrimaryId => Execution.PrimaryEntityId;

        /// <summary>Value from the target, falling back to the pre-image (current value after the operation).</summary>
        public T Get<T>(string attribute)
        {
            var target = Target;
            if (target != null && target.Contains(attribute))
                return target.GetAttributeValue<T>(attribute);
            var pre = Pre;
            return pre != null ? pre.GetAttributeValue<T>(attribute) : default(T);
        }

        public bool Changed(string attribute) => Target != null && Target.Contains(attribute);

        /// <summary>True when the update touches only the given columns (the primary key and modifiedon don't count).</summary>
        public bool ChangesOnly(params string[] attributes) =>
            Target != null && Target.Attributes.Keys.All(k => k == Execution.PrimaryEntityName + "id" || k == "modifiedon" || attributes.Contains(k));

        /// <summary>True when this operation runs because a parent record of the given table is being deleted.</summary>
        public bool IsCascadeDeleteOf(string table)
        {
            for (var c = Execution.ParentContext; c != null; c = c.ParentContext)
                if (c.MessageName == "Delete" && c.PrimaryEntityName == table)
                    return true;
            return false;
        }

        /// <summary>True when this operation runs inside one of the given messages (e.g. a Custom API).</summary>
        public bool IsInside(params string[] messages)
        {
            for (var c = Execution.ParentContext; c != null; c = c.ParentContext)
                if (Array.IndexOf(messages, c.MessageName) >= 0)
                    return true;
            return false;
        }

        public void Trace(string format, params object[] args) => tracing?.Trace(format, args);
    }
}
