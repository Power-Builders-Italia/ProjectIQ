using OpenProject365.Plugins;
using Xunit;

public class TextTests
{
    [Fact]
    public void Translate_FixedMessage()
    {
        Assert.Equal("La commessa è chiusa.", Text.Translate("The project is closed.", Text.Column(1040)));
        Assert.Equal("Das Projekt ist abgeschlossen.", Text.Translate("The project is closed.", Text.Column(1031)));
    }

    [Fact] public void ManagerOrBuyerMessage_IsTranslated() =>
        Assert.Equal("Solo un capo commessa della commessa o un buyer può creare una richiesta di offerta.",
            Text.Translate("Only a manager of the project or a buyer can create a request for quotation.", Text.Column(1040)));

    [Fact] public void ProposalMessages_AreTranslated() =>
        Assert.NotEqual("This proposal has already been decided.", Text.Translate("This proposal has already been decided.", Text.Column(1040)));

    [Fact]
    public void SourcingAgentMessages_AreTranslated()
    {
        Assert.Equal("L'utente che ha deciso non è un utente ProjectIQ.", Text.Translate("The user who decided is not a ProjectIQ user.", Text.Column(1040)));
        Assert.Equal("Neuer Agentenvorschlag", Text.Translate("New agent proposal", Text.Column(1031)));
        Assert.Equal("L'agente di approvvigionamento è disattivato.", Text.Translate("The sourcing agent is switched off.", Text.Column(1040)));
    }

    [Fact]
    public void Translate_PlaceholderValuesAreTranslatedToo()
    {
        Assert.Equal("Seul un chef de projet du projet ou un acheteur peut créer une commande d'achat.",
            Text.Translate("Only a manager of the project or a buyer can create a purchase order.", Text.Column(1036)));
        Assert.Equal("Steel beam: nur noch 2,5 zu empfangen.",
            Text.Translate("Steel beam: only 2,5 still to receive.", Text.Column(1031)));
    }

    [Fact]
    public void Translate_SpecificTemplateWinsOverGeneric()
    {
        Assert.Equal("Solo un capo commessa della commessa può decidere questa richiesta di acquisto.",
            Text.Translate("Only a manager of the project can decide this purchase request.", Text.Column(1040)));
        Assert.Equal("PR-1 Steel è stata rifiutata. Nota: too expensive",
            Text.Translate("PR-1 Steel was rejected. Note: too expensive", Text.Column(1040)));
    }

    [Fact]
    public void Translate_KeepsEnglishAndUnknownMessages()
    {
        Assert.Equal("The project is closed.", Text.Translate("The project is closed.", Text.Column(1033)));
        Assert.Equal("The project is closed.", Text.Translate("The project is closed.", Text.Column(1034)));
        Assert.Equal("Something else.", Text.Translate("Something else.", Text.Column(1040)));
    }
}
