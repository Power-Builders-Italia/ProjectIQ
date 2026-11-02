using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

namespace OpenProject365.Plugins
{
    // Supplier invoice extraction and checks without SDK types, covered by OpenProject365.Plugins.Tests
    // (docs/en/purchasing.md#reading-the-file, docs/en/supplier-portal.md#invoices).

    public class InvoiceLineData
    {
        public string Name;
        public string Code;
        public decimal? Quantity;
        public string Uom;
        public decimal? UnitPrice;
        public decimal? Total;
        public decimal? VatRate;
    }

    /// <summary>Invoice data read from a FatturaPA XML or by AI Builder; Confidence holds the AI score per column (0..1).</summary>
    public class InvoiceData
    {
        public string Number;
        public DateTime? Date;
        public DateTime? DueDate;
        public int? DocumentType;
        public string SellerName;
        public string SellerVat;
        public decimal? Taxable;
        public decimal? Vat;
        public decimal? Total;
        public string OrderRefs;
        public string DeliveryNoteRefs;
        public List<InvoiceLineData> Lines = new List<InvoiceLineData>();
        public Dictionary<string, double> Confidence = new Dictionary<string, double>();
    }

    public static class FatturaPa
    {
        /// <summary>FatturaPA document types in the order of the Document Type choice (365000000 = TD01).</summary>
        public static readonly string[] DocumentTypes = { "TD01", "TD02", "TD04", "TD05", "TD06", "TD24", "TD25" };

        /// <summary>
        /// The XML of a FatturaPA file, also when it is signed (.xml.p7m: the XML sits inside the CAdES envelope);
        /// null when the bytes hold no FatturaElettronica document.
        /// </summary>
        public static string Xml(byte[] bytes)
        {
            if (bytes == null || bytes.Length == 0) return null;
            var text = Encoding.UTF8.GetString(bytes);
            var start = text.IndexOf("<?xml", StringComparison.Ordinal);
            var root = Regex.Match(text, @"<([A-Za-z0-9_]+:)?FatturaElettronica[\s>]");
            if (!root.Success) return null;
            if (start < 0 || start > root.Index) start = root.Index;
            var close = Regex.Matches(text, @"</([A-Za-z0-9_]+:)?FatturaElettronica>").Cast<Match>().LastOrDefault();
            if (close == null) return null;
            var xml = text.Substring(start, close.Index + close.Length - start);
            // a signed file with the content split in DER chunks keeps chunk headers inside the text: drop control bytes
            return Regex.Replace(xml, @"[\x00-\x08\x0B\x0C\x0E-\x1F]", "");
        }

        /// <summary>Reads the first invoice body of a FatturaPA document; null when the XML is not a FatturaPA.</summary>
        public static InvoiceData Parse(string xml)
        {
            if (xml == null) return null;
            var doc = new XmlDocument { XmlResolver = null };
            try { doc.LoadXml(xml); } catch (XmlException) { return null; }
            var header = First(doc.DocumentElement, "FatturaElettronicaHeader");
            var body = First(doc.DocumentElement, "FatturaElettronicaBody");
            if (body == null) return null;
            var data = new InvoiceData();
            var seller = First(header, "CedentePrestatore");
            var anagrafica = First(First(seller, "DatiAnagrafici"), "Anagrafica");
            data.SellerName = Text(anagrafica, "Denominazione")
                              ?? string.Join(" ", new[] { Text(anagrafica, "Nome"), Text(anagrafica, "Cognome") }.Where(s => s != null));
            if (data.SellerName == "") data.SellerName = null;
            var vat = First(First(seller, "DatiAnagrafici"), "IdFiscaleIVA");
            data.SellerVat = Text(vat, "IdCodice");

            var general = First(First(body, "DatiGenerali"), "DatiGeneraliDocumento");
            data.Number = Text(general, "Numero");
            data.Date = Date(Text(general, "Data"));
            var type = Array.IndexOf(DocumentTypes, Text(general, "TipoDocumento"));
            data.DocumentType = type >= 0 ? 365000000 + type : (int?)null;
            data.Total = Number(Text(general, "ImportoTotaleDocumento"));
            data.OrderRefs = Join(All(First(body, "DatiGenerali"), "DatiOrdineAcquisto").Select(o => Text(o, "IdDocumento")));
            data.DeliveryNoteRefs = Join(All(First(body, "DatiGenerali"), "DatiDDT").Select(o => Text(o, "NumeroDDT")));

            var goods = First(body, "DatiBeniServizi");
            foreach (var line in All(goods, "DettaglioLinee"))
            {
                var code = All(line, "CodiceArticolo").Select(c => Text(c, "CodiceValore")).FirstOrDefault(c => c != null);
                data.Lines.Add(new InvoiceLineData
                {
                    Name = Text(line, "Descrizione"),
                    Code = code,
                    Quantity = Number(Text(line, "Quantita")),
                    Uom = Text(line, "UnitaMisura"),
                    UnitPrice = Number(Text(line, "PrezzoUnitario")),
                    Total = Number(Text(line, "PrezzoTotale")),
                    VatRate = Number(Text(line, "AliquotaIVA")),
                });
            }
            var summary = All(goods, "DatiRiepilogo").ToList();
            if (summary.Count > 0)
            {
                data.Taxable = summary.Sum(s => Number(Text(s, "ImponibileImporto")) ?? 0m);
                data.Vat = summary.Sum(s => Number(Text(s, "Imposta")) ?? 0m);
                if (!data.Total.HasValue) data.Total = data.Taxable + data.Vat;
            }
            data.DueDate = All(First(body, "DatiPagamento"), "DettaglioPagamento")
                .Select(p => Date(Text(p, "DataScadenzaPagamento"))).Where(d => d.HasValue).OrderBy(d => d).FirstOrDefault();
            return data;
        }

        private static IEnumerable<XmlElement> All(XmlNode parent, string name) =>
            parent == null ? Enumerable.Empty<XmlElement>() : parent.ChildNodes.OfType<XmlElement>().Where(e => e.LocalName == name);

        private static XmlElement First(XmlNode parent, string name) => All(parent, name).FirstOrDefault();

        private static string Text(XmlNode parent, string name)
        {
            var value = First(parent, name)?.InnerText?.Trim();
            return string.IsNullOrEmpty(value) ? null : value;
        }

        private static string Join(IEnumerable<string> values)
        {
            var list = values.Where(v => v != null).Distinct().ToList();
            return list.Count == 0 ? null : string.Join(", ", list);
        }

        public static decimal? Number(string text) =>
            decimal.TryParse(text, NumberStyles.Number, CultureInfo.InvariantCulture, out var n) ? n : (decimal?)null;

        public static DateTime? Date(string text) =>
            DateTime.TryParseExact(text, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var d) ? d : (DateTime?)null;
    }

    public class OrderLineInfo
    {
        public Guid Id;
        public string Name;
        public decimal Amount;
    }

    public class OrderInfo
    {
        public Guid Id;
        public string Number;
        public decimal Taxable;
        public List<OrderLineInfo> Lines = new List<OrderLineInfo>();
    }

    public class InvoiceCheckResult
    {
        public int Status;
        public Guid? OrderId;
        public List<string> Notes = new List<string>();
        public SortedSet<string> CheckFields = new SortedSet<string>();
        /// <summary>Order line of each invoice line (index in InvoiceData.Lines).</summary>
        public Dictionary<int, Guid> LineMatches = new Dictionary<int, Guid>();
    }

    /// <summary>Checks of a supplier invoice before the supplier sends it: duplicates, low AI confidence, order and lines.</summary>
    public static class InvoiceCheck
    {
        /// <summary>AI Builder scores below this need a check by the supplier.</summary>
        public const double MinConfidence = 0.8;

        /// <param name="data">Current values of the invoice (and of its lines).</param>
        /// <param name="orderId">Order already chosen on the invoice, if any.</param>
        /// <param name="orders">Sent, confirmed and received orders of the supplier.</param>
        /// <param name="duplicateOf">Number (INV-#####) of another invoice of the supplier with the same invoice number and year, not rejected.</param>
        public static InvoiceCheckResult Run(InvoiceData data, Guid? orderId, IList<OrderInfo> orders, string duplicateOf)
        {
            var r = new InvoiceCheckResult { Status = Model.ExtractionReady };
            if (duplicateOf != null)
            {
                r.Status = Model.ExtractionBlocked;
                r.Notes.Add($"Already sent as {duplicateOf}.");
                r.CheckFields.Add("op365_invoicenumber");
                r.OrderId = orderId;
                return r;
            }
            if (string.IsNullOrWhiteSpace(data.Number)) Check(r, "op365_invoicenumber", "Invoice number not found.");
            if (!data.Date.HasValue) Check(r, "op365_invoicedate", "Invoice date not found.");
            foreach (var c in data.Confidence.Where(c => c.Value < MinConfidence).OrderBy(c => c.Key))
                Check(r, c.Key, null);
            if (r.CheckFields.Count > 0 && r.Notes.Count == 0) r.Notes.Add("Some values were read with low confidence: check the highlighted fields.");

            var order = orderId.HasValue ? orders.FirstOrDefault(o => o.Id == orderId.Value) : null;
            if (order == null && !orderId.HasValue)
            {
                var candidates = orders.Where(o => Refers(data.OrderRefs, o.Number)).ToList();
                if (candidates.Count == 1) order = candidates[0];
                else if (candidates.Count > 1) Check(r, "op365_purchaseorderid", $"{candidates.Count} purchase orders match: choose one.");
                else Check(r, "op365_purchaseorderid", "Choose the purchase order.");
            }
            r.OrderId = order?.Id ?? orderId;
            if (order == null) return r;

            if (data.Taxable.HasValue && Math.Abs(data.Taxable.Value - order.Taxable) >= 0.01m)
            {
                var diff = data.Taxable.Value - order.Taxable;
                Check(r, null, $"The taxable amount differs from order {order.Number} by {(diff > 0 ? "+" : "")}{diff.ToString("N2", CultureInfo.InvariantCulture)}.");
            }
            var free = order.Lines.ToList();
            for (var i = 0; i < data.Lines.Count; i++)
            {
                var line = data.Lines[i];
                var match = free.FirstOrDefault(o => Same(o.Name, line.Name))
                            ?? free.FirstOrDefault(o => Close(o.Name, line.Name))
                            ?? free.FirstOrDefault(o => line.Total.HasValue && o.Amount == line.Total.Value);
                if (match == null)
                {
                    Check(r, null, $"Line {i + 1} ({line.Name}) is not on the order.");
                    continue;
                }
                free.Remove(match);
                r.LineMatches[i] = match.Id;
                if (line.Total.HasValue && Math.Abs(line.Total.Value - match.Amount) >= 0.01m)
                    Check(r, null, $"Line {i + 1} ({line.Name}): {line.Total.Value.ToString("N2", CultureInfo.InvariantCulture)} on the invoice, "
                                   + $"{match.Amount.ToString("N2", CultureInfo.InvariantCulture)} on the order.");
            }
            return r;
        }

        private static void Check(InvoiceCheckResult r, string field, string note)
        {
            r.Status = Model.ExtractionToCheck;
            if (field != null) r.CheckFields.Add(field);
            if (note != null) r.Notes.Add(note);
        }

        /// <summary>Whether the order references written on the invoice name the order (PO-00031, PO00031 or 31).</summary>
        public static bool Refers(string refs, string orderNumber)
        {
            if (string.IsNullOrWhiteSpace(refs) || string.IsNullOrWhiteSpace(orderNumber)) return false;
            var number = Key(orderNumber);
            var digits = Regex.Replace(orderNumber, @"\D", "").TrimStart('0');
            foreach (var token in Regex.Split(refs, @"[,;\s]+").Where(t => t.Length > 0))
            {
                if (Key(token) == number) return true;
                var d = Regex.Replace(token, @"\D", "").TrimStart('0');
                if (digits.Length > 0 && d == digits && Regex.IsMatch(token, @"^\W*(PO|ODA|ORD|N)?\W*\d+\W*$", RegexOptions.IgnoreCase)) return true;
            }
            return false;
        }

        /// <summary>Invoice number as compared for duplicates: letters and digits only, upper case.</summary>
        public static string Key(string text) => Regex.Replace(text ?? "", @"[^A-Za-z0-9]", "").ToUpperInvariant();

        private static bool Same(string a, string b) => Key(a).Length > 0 && Key(a) == Key(b);

        private static bool Close(string a, string b)
        {
            var x = Key(a); var y = Key(b);
            return x.Length >= 4 && y.Length >= 4 && (x.Contains(y) || y.Contains(x));
        }
    }
}
