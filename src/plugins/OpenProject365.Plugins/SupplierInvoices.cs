using System;
using System.Collections.Generic;
using System.Linq;
using Microsoft.Xrm.Sdk;
using Microsoft.Xrm.Sdk.Query;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Supplier invoices sent from the supplier portal: the file (FatturaPA XML, signed or not, or a PDF/image read by
    /// AI Builder) fills the invoice and its lines, then the checks against the orders of the supplier set the extraction
    /// status (Ready, To Check, Blocked). See docs/en/purchasing.md#reading-the-file.
    /// </summary>
    public static class SupplierInvoices
    {
        public const string File = "op365_xmlfile";
        public const string ExtractRequested = "op365_extractrequested";
        public const string ExtractionStatus = "op365_extractionstatus";
        public const string AiVariable = "op365_InvoiceAiExtraction";
        public static readonly string[] PaymentColumns = { "op365_paymentstatus", "op365_paidamount", "op365_paidon", "op365_paymentreference", "op365_duedate" };

        /// <summary>Invoice AI Extraction environment variable; on when not set.</summary>
        public static bool AiEnabled(IOrganizationService system) => EnvironmentValue.Bool(Settings.Value(system, AiVariable), true);

        /// <summary>Content and name of a file column, null when empty.</summary>
        public static Tuple<byte[], string> Download(IOrganizationService system, EntityReference record, string column)
        {
            OrganizationResponse init;
            try
            {
                init = system.Execute(new OrganizationRequest("InitializeFileBlocksDownload")
                {
                    ["Target"] = record,
                    ["FileAttributeName"] = column,
                });
            }
            catch (System.ServiceModel.FaultException<OrganizationServiceFault>) { return null; }
            var token = (string)init["FileContinuationToken"];
            var size = Convert.ToInt64(init["FileSizeInBytes"]);
            var name = (string)init["FileName"];
            var data = new List<byte>();
            const long block = 4 * 1024 * 1024;
            for (long offset = 0; offset < size; offset += block)
            {
                var r = system.Execute(new OrganizationRequest("DownloadBlock")
                {
                    ["FileContinuationToken"] = token,
                    ["Offset"] = offset,
                    ["BlockLength"] = Math.Min(block, size - offset),
                });
                data.AddRange((byte[])r["Data"]);
            }
            return Tuple.Create(data.ToArray(), name);
        }

        /// <summary>The prebuilt Invoice processing model of AI Builder, null when the environment has none.</summary>
        public static Guid? InvoiceModel(IOrganizationService system)
        {
            var query = new QueryExpression("msdyn_aimodel") { ColumnSet = new ColumnSet(false), TopCount = 1 };
            var template = query.AddLink("msdyn_aitemplate", "msdyn_templateid", "msdyn_aitemplateid");
            template.LinkCriteria.AddCondition("msdyn_uniquename", ConditionOperator.Equal, "InvoiceProcessing");
            return system.RetrieveMultiple(query).Entities.FirstOrDefault()?.Id;
        }

        public static string Mime(string fileName)
        {
            var ext = (System.IO.Path.GetExtension(fileName ?? "") ?? "").ToLowerInvariant();
            switch (ext)
            {
                case ".pdf": return "application/pdf";
                case ".jpg": case ".jpeg": return "image/jpeg";
                case ".png": return "image/png";
                case ".tif": case ".tiff": return "image/tiff";
                case ".bmp": return "image/bmp";
                default: return null;
            }
        }

        /// <summary>Reads an invoice with AI Builder; the confidence of each value is kept for the checks.</summary>
        public static InvoiceData Predict(IOrganizationService system, Guid model, byte[] content, string mime)
        {
            var response = system.Execute(new OrganizationRequest("Predict")
            {
                ["Target"] = new EntityReference("msdyn_aimodel", model),
                ["version"] = "2.0",
                ["requestv2"] = new Entity { ["mimeType"] = mime, ["base64Encoded"] = Convert.ToBase64String(content) },
            });
            var output = Child(Child(response.Results.Contains("responsev2") ? response["responsev2"] as Entity : null, "predictionOutput"), "result");
            if (output == null) return null;
            var fields = Child(output, "fields");
            var data = new InvoiceData();
            data.Number = TextOf(fields, "invoiceId", data, "op365_invoicenumber");
            data.Date = DateOf(fields, "invoiceDate", data, "op365_invoicedate");
            data.DueDate = DateOf(fields, "dueDate", data, "op365_duedate");
            data.SellerName = TextOf(fields, "vendorName", data, null);
            data.SellerVat = TextOf(fields, "vendorTaxId", data, null);
            data.Taxable = NumberOf(fields, "subTotal", data, "op365_taxableamount");
            data.Vat = NumberOf(fields, "totalTax", data, "op365_vatamount");
            data.Total = NumberOf(fields, "invoiceTotal", data, "op365_totalamount");
            data.OrderRefs = TextOf(fields, "purchaseOrder", data, null);
            var rate = data.Taxable > 0 && data.Vat.HasValue ? Math.Round(data.Vat.Value / data.Taxable.Value * 100m, 0) : (decimal?)null;
            if (output.Contains("items") && output["items"] is EntityCollection items)
            {
                foreach (var row in items.Entities)
                {
                    var f = Child(row, "fields");
                    var line = new InvoiceLineData
                    {
                        Name = TextOf(f, "description", null, null),
                        Code = TextOf(f, "productCode", null, null),
                        Quantity = NumberOf(f, "quantity", null, null),
                        Uom = TextOf(f, "unit", null, null),
                        UnitPrice = NumberOf(f, "unitPrice", null, null),
                        Total = NumberOf(f, "amount", null, null),
                        VatRate = NumberOf(f, "taxRate", null, null) ?? rate,
                    };
                    if (line.Name != null || line.Total.HasValue) data.Lines.Add(line);
                }
            }
            return data;
        }

        private static Entity Child(Entity e, string name) => e != null && e.Contains(name) ? e[name] as Entity : null;

        private static Entity Field(Entity fields, string name, InvoiceData data, string column)
        {
            var f = Child(fields, name);
            if (f != null && data != null && column != null && f.Contains("confidence"))
                data.Confidence[column] = Convert.ToDouble(f["confidence"]);
            return f;
        }

        private static string TextOf(Entity fields, string name, InvoiceData data, string column)
        {
            var f = Field(fields, name, data, column);
            var v = f != null && f.Contains("valueText") ? (f["valueText"] as string)?.Trim() : null;
            return string.IsNullOrEmpty(v) ? null : v;
        }

        private static decimal? NumberOf(Entity fields, string name, InvoiceData data, string column)
        {
            var f = Field(fields, name, data, column);
            return f != null && f.Contains("valueNumber") && f["valueNumber"] != null ? Convert.ToDecimal(f["valueNumber"]) : (decimal?)null;
        }

        private static DateTime? DateOf(Entity fields, string name, InvoiceData data, string column)
        {
            var f = Field(fields, name, data, column);
            if (f == null || !f.Contains("valueDate") || f["valueDate"] == null) return null;
            var v = f["valueDate"];
            if (v is DateTime d) return d.Date;
            return DateTime.TryParse(v.ToString(), System.Globalization.CultureInfo.InvariantCulture,
                                     System.Globalization.DateTimeStyles.AdjustToUniversal, out var p) ? p.Date : (DateTime?)null;
        }

        /// <summary>Sent, confirmed and received orders of the supplier with their lines.</summary>
        public static List<OrderInfo> Orders(IOrganizationService system, Guid supplier)
        {
            var query = new QueryExpression(Model.PurchaseOrder) { ColumnSet = new ColumnSet("op365_number", "op365_totalamount") };
            query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.Equal, supplier);
            query.Criteria.AddCondition("statuscode", ConditionOperator.In, Model.PoSent, Model.PoConfirmed, Model.PoReceived);
            var orders = system.RetrieveMultiple(query).Entities.Select(o => new OrderInfo
            {
                Id = o.Id,
                Number = o.GetAttributeValue<string>("op365_number"),
                Taxable = o.GetAttributeValue<Money>("op365_totalamount")?.Value ?? 0m,
            }).ToList();
            if (orders.Count == 0) return orders;
            var lines = new QueryExpression(Model.PurchaseOrderLine) { ColumnSet = new ColumnSet(Model.PurchaseOrderId, "op365_name", "op365_amount") };
            lines.Criteria.AddCondition(Model.PurchaseOrderId, ConditionOperator.In, orders.Select(o => (object)o.Id).ToArray());
            lines.Criteria.AddCondition("statecode", ConditionOperator.Equal, 0);
            foreach (var l in system.RetrieveMultiple(lines).Entities)
                orders.First(o => o.Id == l.GetAttributeValue<EntityReference>(Model.PurchaseOrderId).Id).Lines.Add(new OrderLineInfo
                {
                    Id = l.Id,
                    Name = l.GetAttributeValue<string>("op365_name"),
                    Amount = l.GetAttributeValue<Money>("op365_amount")?.Value ?? 0m,
                });
            return orders;
        }

        /// <summary>Number (INV-#####) of another invoice of the supplier with the same invoice number in the same year, not rejected.</summary>
        public static string DuplicateOf(IOrganizationService system, Guid id, Guid supplier, string number, DateTime? date)
        {
            var key = InvoiceCheck.Key(number);
            if (key.Length == 0) return null;
            var query = new QueryExpression(Model.SupplierInvoice) { ColumnSet = new ColumnSet("op365_number", "op365_invoicenumber", "op365_invoicedate") };
            query.Criteria.AddCondition(Model.SupplierId, ConditionOperator.Equal, supplier);
            query.Criteria.AddCondition(Model.SupplierInvoiceId, ConditionOperator.NotEqual, id);
            query.Criteria.AddCondition("statuscode", ConditionOperator.NotEqual, Model.InvoiceRejected);
            var twin = system.RetrieveMultiple(query).Entities.FirstOrDefault(i =>
                InvoiceCheck.Key(i.GetAttributeValue<string>("op365_invoicenumber")) == key
                && (!date.HasValue || !i.Contains("op365_invoicedate") || i.GetAttributeValue<DateTime>("op365_invoicedate").Year == date.Value.Year));
            return twin == null ? null : twin.GetAttributeValue<string>("op365_number") ?? twin.GetAttributeValue<string>("op365_invoicenumber");
        }
    }

    /// <summary>
    /// op365_supplierinvoice Update, PostOperation, asynchronous: a new file (or Extract Requested) reads the invoice from
    /// the file and replaces its lines; a new number, date or order only runs the checks again. Draft and To Review
    /// invoices only. Updates written by this plugin (depth above 1) do not start it again.
    /// </summary>
    public class SupplierInvoiceExtract : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Execution.Depth > 1) return;
            try { Extract(context); }
            catch (Exception e)
            {
                // never leave the invoice Pending: the supplier fills in the data
                context.Trace(e.ToString());
                context.SystemService.Update(new Entity(Model.SupplierInvoice, context.PrimaryId)
                {
                    [SupplierInvoices.ExtractionStatus] = new OptionSetValue(Model.ExtractionToCheck),
                    ["op365_extractionnotes"] = "The file could not be read automatically: fill in the data by hand.",
                    [SupplierInvoices.ExtractRequested] = false,
                });
            }
        }

        private static void Extract(LocalContext context)
        {
            var system = context.SystemService;
            var id = context.PrimaryId;
            var invoice = system.Retrieve(Model.SupplierInvoice, id, new ColumnSet("statuscode", Model.SupplierId, Model.PurchaseOrderId,
                "op365_invoicenumber", "op365_invoicedate", "op365_taxableamount", "op365_extractionsource"));
            var status = invoice.GetAttributeValue<OptionSetValue>("statuscode")?.Value;
            if (status != Model.InvoiceDraft && status != Model.InvoiceToReview) return;
            var supplier = invoice.GetAttributeValue<EntityReference>(Model.SupplierId);
            if (supplier == null) return;
            var extract = context.Changed(SupplierInvoices.File) || context.Get<bool?>(SupplierInvoices.ExtractRequested) == true;
            var update = new Entity(Model.SupplierInvoice, id);
            InvoiceData data = null;
            Guid? orderId = invoice.GetAttributeValue<EntityReference>(Model.PurchaseOrderId)?.Id;
            var notes = new List<string>();
            if (extract)
            {
                update[SupplierInvoices.ExtractRequested] = false;
                var file = SupplierInvoices.Download(system, invoice.ToEntityReference(), SupplierInvoices.File);
                if (file != null)
                {
                    data = FatturaPa.Parse(FatturaPa.Xml(file.Item1));
                    if (data != null) update["op365_extractionsource"] = new OptionSetValue(Model.SourceXml);
                    else
                    {
                        var mime = SupplierInvoices.Mime(file.Item2);
                        var model = mime != null && SupplierInvoices.AiEnabled(system) ? SupplierInvoices.InvoiceModel(system) : null;
                        if (model.HasValue)
                        {
                            try { data = SupplierInvoices.Predict(system, model.Value, file.Item1, mime); }
                            catch (Exception e) { context.Trace("Predict failed: " + e.Message); }
                        }
                        if (data != null) update["op365_extractionsource"] = new OptionSetValue(Model.SourceAi);
                        else
                        {
                            update["op365_extractionsource"] = new OptionSetValue(Model.SourceManual);
                            notes.Add(mime == null ? "The file is neither a FatturaPA XML nor a PDF or image: fill in the data by hand."
                                                   : "The file could not be read automatically: fill in the data by hand.");
                        }
                    }
                }
                if (data != null)
                {
                    if (data.Number != null) update["op365_invoicenumber"] = data.Number.Length > 50 ? data.Number.Substring(0, 50) : data.Number;
                    if (data.Date.HasValue) update["op365_invoicedate"] = data.Date.Value;
                    if (data.DueDate.HasValue) update["op365_duedate"] = data.DueDate.Value;
                    if (data.DocumentType.HasValue) update["op365_documenttype"] = new OptionSetValue(data.DocumentType.Value);
                    if (data.OrderRefs != null) update["op365_orderrefs"] = Cut(data.OrderRefs, 400);
                    if (data.DeliveryNoteRefs != null) update["op365_deliverynoterefs"] = Cut(data.DeliveryNoteRefs, 400);
                    if (data.SellerName != null) update["op365_sellername"] = Cut(data.SellerName, 200);
                    if (data.SellerVat != null) update["op365_sellervatnumber"] = Cut(data.SellerVat, 30);
                    // seller check: the VAT number on the file must be the supplier's
                    var vat = system.Retrieve("account", supplier.Id, new ColumnSet("op365_vatnumber")).GetAttributeValue<string>("op365_vatnumber");
                    if (data.SellerVat != null && !string.IsNullOrEmpty(vat) && InvoiceCheck.Key(vat).TrimStart('I', 'T') != InvoiceCheck.Key(data.SellerVat).TrimStart('I', 'T'))
                        notes.Add($"The VAT number on the invoice ({data.SellerVat}) is not your company's.");
                }
                else
                {
                    data = Current(invoice);
                    data.Number = null;   // the placeholder number of the upload
                    data.Date = null;
                }
            }
            else data = Current(invoice);

            // the checks, on the values just read or on the current values and lines
            if (!extract) data.Lines = Lines(system, id);
            var orders = SupplierInvoices.Orders(system, supplier.Id);
            var duplicate = SupplierInvoices.DuplicateOf(system, id, supplier.Id, data.Number, data.Date);
            if (extract && data.Lines.Count > 0 && !data.Taxable.HasValue) data.Taxable = data.Lines.Sum(l => l.Total ?? 0m);
            var result = InvoiceCheck.Run(data, orderId, orders, duplicate);
            if (data.Number == null) result.CheckFields.Add("op365_invoicenumber");
            if (data.Date == null) result.CheckFields.Add("op365_invoicedate");
            if (notes.Count > 0 && result.Status == Model.ExtractionReady) result.Status = Model.ExtractionToCheck;
            result.Notes.InsertRange(0, notes);
            if (extract && data.Lines.Count > 0 && data.Taxable.HasValue && Math.Abs(data.Lines.Sum(l => l.Total ?? 0m) - data.Taxable.Value) >= 0.01m)
            {
                result.Notes.Add("The lines do not add up to the taxable amount on the invoice.");
                if (result.Status == Model.ExtractionReady) result.Status = Model.ExtractionToCheck;
            }

            update[SupplierInvoices.ExtractionStatus] = new OptionSetValue(result.Status);
            update["op365_extractionnotes"] = result.Notes.Count == 0 ? null : string.Join("\n", result.Notes);
            update["op365_checkfields"] = result.CheckFields.Count == 0 ? null : string.Join(",", result.CheckFields);
            if (result.OrderId.HasValue && result.OrderId != orderId)
            {
                update[Model.PurchaseOrderId] = new EntityReference(Model.PurchaseOrder, result.OrderId.Value);
                update[Model.ProjectId] = system.Retrieve(Model.PurchaseOrder, result.OrderId.Value, new ColumnSet(Model.ProjectId)).GetAttributeValue<EntityReference>(Model.ProjectId);
            }
            system.Update(update);

            if (extract && data.Lines.Count > 0)
            {
                foreach (var old in Purchasing.Children(system, Model.SupplierInvoiceLine, Model.SupplierInvoiceId, id))
                    system.Delete(Model.SupplierInvoiceLine, old.Id);
                for (var i = 0; i < data.Lines.Count; i++)
                {
                    var l = data.Lines[i];
                    var line = new Entity(Model.SupplierInvoiceLine)
                    {
                        [Model.SupplierInvoiceId] = new EntityReference(Model.SupplierInvoice, id),
                        ["op365_name"] = Cut(l.Name ?? $"Line {i + 1}", 200),
                        ["op365_linenumber"] = i + 1,
                    };
                    if (l.Code != null) line["op365_code"] = Cut(l.Code, 50);
                    if (l.Quantity.HasValue) line["op365_quantity"] = l.Quantity.Value;
                    if (l.Uom != null) line["op365_uom"] = Cut(l.Uom, 20);
                    if (l.UnitPrice.HasValue) line["op365_unitprice"] = new Money(l.UnitPrice.Value);
                    if (l.Total.HasValue) line["op365_totalprice"] = new Money(l.Total.Value);
                    if (l.VatRate.HasValue) line["op365_vatrate"] = l.VatRate.Value;
                    if (result.LineMatches.TryGetValue(i, out var orderLine)) line["op365_orderlineid"] = new EntityReference(Model.PurchaseOrderLine, orderLine);
                    system.Create(line);
                }
            }
            else if (!extract)
            {
                // order lines of the current lines, after a change of the order
                var lines = Purchasing.Children(system, Model.SupplierInvoiceLine, Model.SupplierInvoiceId, id, "op365_linenumber", "op365_orderlineid")
                    .OrderBy(l => l.GetAttributeValue<int?>("op365_linenumber") ?? int.MaxValue).ToList();
                for (var i = 0; i < lines.Count; i++)
                {
                    var want = result.LineMatches.TryGetValue(i, out var ol) ? ol : (Guid?)null;
                    if (lines[i].GetAttributeValue<EntityReference>("op365_orderlineid")?.Id != want)
                        system.Update(new Entity(Model.SupplierInvoiceLine, lines[i].Id) { ["op365_orderlineid"] = want.HasValue ? new EntityReference(Model.PurchaseOrderLine, want.Value) : null });
                }
            }
        }

        private static string Cut(string s, int max) => s.Length > max ? s.Substring(0, max) : s;

        private static InvoiceData Current(Entity invoice) => new InvoiceData
        {
            Number = invoice.GetAttributeValue<string>("op365_invoicenumber"),
            Date = invoice.GetAttributeValue<DateTime?>("op365_invoicedate"),
            Taxable = invoice.GetAttributeValue<Money>("op365_taxableamount")?.Value,
        };

        private static List<InvoiceLineData> Lines(IOrganizationService system, Guid id) =>
            Purchasing.Children(system, Model.SupplierInvoiceLine, Model.SupplierInvoiceId, id, "op365_name", "op365_totalprice", "op365_linenumber")
                .OrderBy(l => l.GetAttributeValue<int?>("op365_linenumber") ?? int.MaxValue)
                .Select(l => new InvoiceLineData { Name = l.GetAttributeValue<string>("op365_name"), Total = l.GetAttributeValue<Money>("op365_totalprice")?.Value })
                .ToList();
    }

    /// <summary>op365_supplierinvoice Delete, PreOperation (PreImage): the supplier portal deletes only draft invoices.</summary>
    public class SupplierInvoiceDelete : PluginBase
    {
        protected override void Run(LocalContext context)
        {
            if (context.Execution.Depth > 1) return;
            if (Purchasing.Status(context.Pre) != Model.InvoiceDraft && SupplierDocuments.IsPortal(context.SystemService, context.Execution.InitiatingUserId))
                Purchasing.Fail("Only draft invoices can be deleted.");
        }
    }
}
