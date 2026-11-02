using System;
using System.Collections.Generic;
using System.Text;
using OpenProject365.Plugins;
using Xunit;

public class InvoiceTests
{
    private const string Sample = @"<?xml version=""1.0"" encoding=""UTF-8""?>
<p:FatturaElettronica versione=""FPR12"" xmlns:p=""http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"">
  <FatturaElettronicaHeader>
    <CedentePrestatore><DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>01234567890</IdCodice></IdFiscaleIVA>
      <Anagrafica><Denominazione>Elettroforniture Nord S.r.l.</Denominazione></Anagrafica></DatiAnagrafici></CedentePrestatore>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento><TipoDocumento>TD01</TipoDocumento><Divisa>EUR</Divisa><Data>2026-10-28</Data><Numero>FT-2026/0412</Numero>
        <ImportoTotaleDocumento>6710.00</ImportoTotaleDocumento></DatiGeneraliDocumento>
      <DatiOrdineAcquisto><IdDocumento>PO-00031</IdDocumento></DatiOrdineAcquisto>
      <DatiDDT><NumeroDDT>118</NumeroDDT><DataDDT>2026-10-20</DataDDT></DatiDDT>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee><NumeroLinea>1</NumeroLinea><CodiceArticolo><CodiceTipo>INT</CodiceTipo><CodiceValore>QE2</CodiceValore></CodiceArticolo>
        <Descrizione>Quadro elettrico QE-2</Descrizione><Quantita>2.00</Quantita><UnitaMisura>PZ</UnitaMisura><PrezzoUnitario>1850.00</PrezzoUnitario><PrezzoTotale>3700.00</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee>
      <DettaglioLinee><NumeroLinea>2</NumeroLinea><Descrizione>Posa e cablaggio</Descrizione><Quantita>16</Quantita><PrezzoUnitario>42</PrezzoUnitario><PrezzoTotale>672.00</PrezzoTotale><AliquotaIVA>22.00</AliquotaIVA></DettaglioLinee>
      <DatiRiepilogo><AliquotaIVA>22.00</AliquotaIVA><ImponibileImporto>4372.00</ImponibileImporto><Imposta>961.84</Imposta></DatiRiepilogo>
    </DatiBeniServizi>
    <DatiPagamento><CondizioniPagamento>TP02</CondizioniPagamento><DettaglioPagamento><ModalitaPagamento>MP05</ModalitaPagamento><DataScadenzaPagamento>2026-11-30</DataScadenzaPagamento><ImportoPagamento>6710.00</ImportoPagamento></DettaglioPagamento></DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>";

    [Fact]
    public void Parse_ReadsHeaderLinesAndPayment()
    {
        var d = FatturaPa.Parse(FatturaPa.Xml(Encoding.UTF8.GetBytes(Sample)));
        Assert.Equal("FT-2026/0412", d.Number);
        Assert.Equal(new DateTime(2026, 10, 28), d.Date);
        Assert.Equal(new DateTime(2026, 11, 30), d.DueDate);
        Assert.Equal(365000000, d.DocumentType);
        Assert.Equal("Elettroforniture Nord S.r.l.", d.SellerName);
        Assert.Equal("01234567890", d.SellerVat);
        Assert.Equal(4372m, d.Taxable);
        Assert.Equal(961.84m, d.Vat);
        Assert.Equal(6710m, d.Total);
        Assert.Equal("PO-00031", d.OrderRefs);
        Assert.Equal("118", d.DeliveryNoteRefs);
        Assert.Equal(2, d.Lines.Count);
        Assert.Equal("QE2", d.Lines[0].Code);
        Assert.Equal(1850m, d.Lines[0].UnitPrice);
        Assert.Equal(22m, d.Lines[1].VatRate);
    }

    [Fact]
    public void Xml_FindsTheDocumentInsideASignedFile()
    {
        var bytes = new List<byte> { 0x30, 0x80, 0x06, 0x09 };
        bytes.AddRange(Encoding.UTF8.GetBytes(Sample));
        bytes.AddRange(new byte[] { 0x00, 0x00, 0xA0, 0x82 });
        Assert.Equal("FT-2026/0412", FatturaPa.Parse(FatturaPa.Xml(bytes.ToArray())).Number);
        Assert.Null(FatturaPa.Xml(Encoding.UTF8.GetBytes("%PDF-1.4 not an invoice")));
    }

    private static OrderInfo Order(string number, decimal taxable, params (string name, decimal amount)[] lines)
    {
        var o = new OrderInfo { Id = Guid.NewGuid(), Number = number, Taxable = taxable };
        foreach (var l in lines) o.Lines.Add(new OrderLineInfo { Id = Guid.NewGuid(), Name = l.name, Amount = l.amount });
        return o;
    }

    [Fact]
    public void Check_ReadyWhenOrderAndLinesMatch()
    {
        var d = FatturaPa.Parse(FatturaPa.Xml(Encoding.UTF8.GetBytes(Sample)));
        var po = Order("PO-00031", 4372m, ("Quadro elettrico QE-2", 3700m), ("Posa e cablaggio", 672m));
        var r = InvoiceCheck.Run(d, null, new List<OrderInfo> { Order("PO-00030", 100m), po }, null);
        Assert.Equal(Model.ExtractionReady, r.Status);
        Assert.Equal(po.Id, r.OrderId);
        Assert.Equal(po.Lines[1].Id, r.LineMatches[1]);
        Assert.Empty(r.Notes);
    }

    [Fact]
    public void Check_FlagsDifferencesLowConfidenceAndMissingOrder()
    {
        var d = FatturaPa.Parse(FatturaPa.Xml(Encoding.UTF8.GetBytes(Sample)));
        var po = Order("PO-00031", 4288m, ("Quadro elettrico QE-2", 3700m), ("Posa", 588m));
        var r = InvoiceCheck.Run(d, null, new List<OrderInfo> { po }, null);
        Assert.Equal(Model.ExtractionToCheck, r.Status);
        Assert.Contains("The taxable amount differs from order PO-00031 by +84.00.", r.Notes);
        Assert.Contains("Line 2 (Posa e cablaggio): 672.00 on the invoice, 588.00 on the order.", r.Notes);

        d.OrderRefs = null; d.Confidence["op365_totalamount"] = 0.6;
        r = InvoiceCheck.Run(d, null, new List<OrderInfo> { po }, null);
        Assert.Contains("op365_purchaseorderid", r.CheckFields);
        Assert.Contains("op365_totalamount", r.CheckFields);
        Assert.Null(r.OrderId);
    }

    [Fact]
    public void Check_BlocksDuplicates()
    {
        var r = InvoiceCheck.Run(new InvoiceData { Number = "412" }, null, new List<OrderInfo>(), "INV-00007");
        Assert.Equal(Model.ExtractionBlocked, r.Status);
        Assert.Equal("Already sent as INV-00007.", r.Notes[0]);
    }

    [Theory]
    [InlineData("PO-00031", true)]
    [InlineData("po 00031", true)]
    [InlineData("Ordine n. 31", true)]
    [InlineData("31", true)]
    [InlineData("PO-00310", false)]
    [InlineData("DDT 31/2026", false)]
    public void Refers_MatchesOrderNumbers(string refs, bool expected) =>
        Assert.Equal(expected, InvoiceCheck.Refers(refs, "PO-00031"));
}
