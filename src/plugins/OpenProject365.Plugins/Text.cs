using System;
using System.Linq;
using System.Text.RegularExpressions;

namespace OpenProject365.Plugins
{
    /// <summary>
    /// Translates the English messages of the plugins (errors and in-app notifications) into the user's language.
    /// Messages stay English in the code; a message matches a template here, {n} placeholders included, and the
    /// placeholder values are translated in turn (e.g. the action of "Only a manager of the project can {0}.").
    /// </summary>
    public static class Text
    {
        // English, German, French, Italian. Specific templates before the generic ones that could also match.
        private static readonly string[][] Templates =
        {
            // ----- errors
            new[] { "A WBS node cannot depend on itself.", "Ein PSP-Element kann nicht von sich selbst abhängen.", "Un nœud WBS ne peut pas dépendre de lui-même.", "Un nodo WBS non può dipendere da se stesso." },
            new[] { "Predecessor and successor must belong to the same project.", "Vorgänger und Nachfolger müssen zum selben Projekt gehören.", "Le prédécesseur et le successeur doivent appartenir au même projet.", "Predecessore e successore devono appartenere alla stessa commessa." },
            new[] { "This dependency would create a cycle in the plan.", "Diese Abhängigkeit würde einen Zyklus im Plan erzeugen.", "Cette dépendance créerait un cycle dans le planning.", "Questa dipendenza creerebbe un ciclo nel piano." },
            new[] { "Hours and materials can be recorded only on projects In Progress.", "Stunden und Material können nur auf Projekten im Status In Bearbeitung erfasst werden.", "Les heures et le matériel ne peuvent être saisis que sur des projets En cours.", "Ore e materiali si possono registrare solo su commesse In corso." },
            new[] { "The WBS node belongs to another project.", "Das PSP-Element gehört zu einem anderen Projekt.", "Le nœud WBS appartient à un autre projet.", "Il nodo WBS appartiene a un'altra commessa." },
            new[] { "Select at least one time entry.", "Wählen Sie mindestens einen Zeiteintrag aus.", "Sélectionnez au moins une saisie de temps.", "Seleziona almeno una registrazione ore." },
            new[] { "Use Submit, Approve or Reject to change the status of time entries.", "Verwenden Sie Einreichen, Genehmigen oder Ablehnen, um den Status von Zeiteinträgen zu ändern.", "Utilisez Soumettre, Approuver ou Rejeter pour changer le statut des saisies de temps.", "Usa Invia, Approva o Rifiuta per cambiare lo stato delle registrazioni ore." },
            new[] { "Submitted or approved time entries cannot be changed.", "Eingereichte oder genehmigte Zeiteinträge können nicht geändert werden.", "Les saisies de temps soumises ou approuvées ne peuvent pas être modifiées.", "Le registrazioni ore inviate o approvate non si possono modificare." },
            new[] { "Submitted or approved time entries cannot be deleted.", "Eingereichte oder genehmigte Zeiteinträge können nicht gelöscht werden.", "Les saisies de temps soumises ou approuvées ne peuvent pas être supprimées.", "Le registrazioni ore inviate o approvate non si possono eliminare." },
            new[] { "Your user is not linked to a resource. Ask an administrator to set User on your Resource.", "Ihr Benutzer ist keiner Ressource zugeordnet. Bitten Sie einen Administrator, Benutzer in Ihrer Ressource festzulegen.", "Votre utilisateur n'est lié à aucune ressource. Demandez à un administrateur de renseigner Utilisateur sur votre ressource.", "Il tuo utente non è collegato a una risorsa. Chiedi a un amministratore di impostare Utente sulla tua risorsa." },
            new[] { "Only draft or rejected time entries can be submitted.", "Nur Zeiteinträge im Entwurf oder abgelehnte Zeiteinträge können eingereicht werden.", "Seules les saisies de temps en brouillon ou rejetées peuvent être soumises.", "Si possono inviare solo registrazioni ore in bozza o rifiutate." },
            new[] { "You can submit only your own time entries.", "Sie können nur Ihre eigenen Zeiteinträge einreichen.", "Vous ne pouvez soumettre que vos propres saisies de temps.", "Puoi inviare solo le tue registrazioni ore." },
            new[] { "Add a note to reject time entries.", "Fügen Sie eine Notiz hinzu, um Zeiteinträge abzulehnen.", "Ajoutez une note pour rejeter des saisies de temps.", "Aggiungi una nota per rifiutare le registrazioni ore." },
            new[] { "Only submitted time entries can be approved or rejected.", "Nur eingereichte Zeiteinträge können genehmigt oder abgelehnt werden.", "Seules les saisies de temps soumises peuvent être approuvées ou rejetées.", "Si possono approvare o rifiutare solo registrazioni ore inviate." },
            new[] { "Only a manager of the project can approve or reject its time entries.", "Nur ein Projektleiter des Projekts kann dessen Zeiteinträge genehmigen oder ablehnen.", "Seul un chef de projet du projet peut approuver ou rejeter ses saisies de temps.", "Solo un capo commessa della commessa può approvarne o rifiutarne le registrazioni ore." },
            new[] { "Only a manager of the project can decide this purchase request.", "Nur ein Projektleiter des Projekts kann über diese Bestellanforderung entscheiden.", "Seul un chef de projet du projet peut statuer sur cette demande d'achat.", "Solo un capo commessa della commessa può decidere questa richiesta di acquisto." },
            new[] { "Only a manager of the project can {0}.", "Nur ein Projektleiter des Projekts kann {0}.", "Seul un chef de projet du projet peut {0}.", "Solo un capo commessa della commessa può {0}." },
            new[] { "Only a manager or contributor of the project can {0}.", "Nur ein Projektleiter oder Mitwirkender des Projekts kann {0}.", "Seul un chef de projet ou un contributeur du projet peut {0}.", "Solo un capo commessa o un collaboratore della commessa può {0}." },
            new[] { "The project is closed.", "Das Projekt ist abgeschlossen.", "Le projet est clôturé.", "La commessa è chiusa." },
            new[] { "{0} is not an active supplier.", "{0} ist kein aktiver Lieferant.", "{0} n'est pas un fournisseur actif.", "{0} non è un fornitore attivo." },
            new[] { "{0} is blocked.", "{0} ist gesperrt.", "{0} est bloqué.", "{0} è bloccato." },
            new[] { "Use Submit to send a purchase request for approval.", "Verwenden Sie Einreichen, um eine Bestellanforderung zur Genehmigung zu senden.", "Utilisez Soumettre pour envoyer une demande d'achat en approbation.", "Usa Invia per mandare in approvazione una richiesta di acquisto." },
            new[] { "Use Submit, Approve, Reject or Cancel to change the status of a purchase request.", "Verwenden Sie Einreichen, Genehmigen, Ablehnen oder Stornieren, um den Status einer Bestellanforderung zu ändern.", "Utilisez Soumettre, Approuver, Rejeter ou Annuler pour changer le statut d'une demande d'achat.", "Usa Invia, Approva, Rifiuta o Annulla per cambiare lo stato di una richiesta di acquisto." },
            new[] { "A purchase request can be changed only while it is Draft or Rejected.", "Eine Bestellanforderung kann nur im Status Entwurf oder Abgelehnt geändert werden.", "Une demande d'achat ne peut être modifiée que lorsqu'elle est Brouillon ou Rejetée.", "Una richiesta di acquisto si può modificare solo quando è in Bozza o Rifiutata." },
            new[] { "Only draft, rejected or cancelled purchase requests can be deleted.", "Nur Bestellanforderungen im Entwurf, abgelehnte oder stornierte können gelöscht werden.", "Seules les demandes d'achat en brouillon, rejetées ou annulées peuvent être supprimées.", "Si possono eliminare solo richieste di acquisto in bozza, rifiutate o annullate." },
            new[] { "Lines can be changed only while the purchase request is Draft or Rejected.", "Positionen können nur geändert werden, solange die Bestellanforderung im Status Entwurf oder Abgelehnt ist.", "Les lignes ne peuvent être modifiées que lorsque la demande d'achat est Brouillon ou Rejetée.", "Le righe si possono modificare solo quando la richiesta di acquisto è in Bozza o Rifiutata." },
            new[] { "Only draft or rejected purchase requests can be submitted.", "Nur Bestellanforderungen im Entwurf oder abgelehnte können eingereicht werden.", "Seules les demandes d'achat en brouillon ou rejetées peuvent être soumises.", "Si possono inviare solo richieste di acquisto in bozza o rifiutate." },
            new[] { "Only the requester or a manager of the project can submit the purchase request.", "Nur der Anforderer oder ein Projektleiter des Projekts kann die Bestellanforderung einreichen.", "Seul le demandeur ou un chef de projet du projet peut soumettre la demande d'achat.", "Solo il richiedente o un capo commessa della commessa può inviare la richiesta di acquisto." },
            new[] { "Add at least one line before submitting.", "Fügen Sie vor dem Einreichen mindestens eine Position hinzu.", "Ajoutez au moins une ligne avant de soumettre.", "Aggiungi almeno una riga prima dell'invio." },
            new[] { "Add a note to reject the purchase request.", "Fügen Sie eine Notiz hinzu, um die Bestellanforderung abzulehnen.", "Ajoutez une note pour rejeter la demande d'achat.", "Aggiungi una nota per rifiutare la richiesta di acquisto." },
            new[] { "Only submitted purchase requests can be approved or rejected.", "Nur eingereichte Bestellanforderungen können genehmigt oder abgelehnt werden.", "Seules les demandes d'achat soumises peuvent être approuvées ou rejetées.", "Si possono approvare o rifiutare solo richieste di acquisto inviate." },
            new[] { "This purchase request is above the threshold: only the purchasing approver or an administrator can decide it.", "Diese Bestellanforderung liegt über dem Schwellenwert: Nur der Einkaufsgenehmiger oder ein Administrator kann darüber entscheiden.", "Cette demande d'achat dépasse le seuil : seul l'approbateur achats ou un administrateur peut statuer.", "Questa richiesta di acquisto supera la soglia: solo l'approvatore acquisti o un amministratore può deciderla." },
            new[] { "Ordered or cancelled purchase requests cannot be cancelled.", "Bestellte oder stornierte Bestellanforderungen können nicht storniert werden.", "Les demandes d'achat commandées ou annulées ne peuvent pas être annulées.", "Le richieste di acquisto ordinate o annullate non si possono annullare." },
            new[] { "Only approved purchase requests can go to a request for quotation.", "Nur genehmigte Bestellanforderungen können in eine Angebotsanfrage übergehen.", "Seules les demandes d'achat approuvées peuvent passer en demande de prix.", "Solo le richieste di acquisto approvate possono passare a richiesta di offerta." },
            new[] { "The deadline must be today or later.", "Die Frist muss heute oder später sein.", "L'échéance doit être aujourd'hui ou plus tard.", "La scadenza deve essere oggi o successiva." },
            new[] { "Only draft or sent requests for quotation can be sent.", "Nur Angebotsanfragen im Entwurf oder gesendete können gesendet werden.", "Seules les demandes de prix en brouillon ou envoyées peuvent être envoyées.", "Si possono inviare solo richieste di offerta in bozza o inviate." },
            new[] { "The deadline has passed: move it before sending.", "Die Frist ist abgelaufen: Verschieben Sie sie vor dem Senden.", "L'échéance est dépassée : reportez-la avant l'envoi.", "La scadenza è passata: spostala prima dell'invio." },
            new[] { "Invite at least one supplier.", "Laden Sie mindestens einen Lieferanten ein.", "Invitez au moins un fournisseur.", "Invita almeno un fornitore." },
            new[] { "Only sent requests for quotation can be awarded.", "Nur gesendete Angebotsanfragen können vergeben werden.", "Seules les demandes de prix envoyées peuvent être attribuées.", "Si possono aggiudicare solo richieste di offerta inviate." },
            new[] { "The invitation belongs to another request for quotation.", "Die Einladung gehört zu einer anderen Angebotsanfrage.", "L'invitation appartient à une autre demande de prix.", "L'invito appartiene a un'altra richiesta di offerta." },
            new[] { "Award a supplier who sent a quote.", "Vergeben Sie an einen Lieferanten, der ein Angebot gesendet hat.", "Attribuez à un fournisseur qui a envoyé une offre.", "Aggiudica a un fornitore che ha inviato un'offerta." },
            new[] { "The supplier quoted no lines.", "Der Lieferant hat keine Positionen angeboten.", "Le fournisseur n'a chiffré aucune ligne.", "Il fornitore non ha quotato nessuna riga." },
            new[] { "Only draft or sent requests for quotation can be cancelled.", "Nur Angebotsanfragen im Entwurf oder gesendete können storniert werden.", "Seules les demandes de prix en brouillon ou envoyées peuvent être annulées.", "Si possono annullare solo richieste di offerta in bozza o inviate." },
            new[] { "The request for quotation is closed.", "Die Angebotsanfrage ist abgeschlossen.", "La demande de prix est clôturée.", "La richiesta di offerta è chiusa." },
            new[] { "The deadline of the request for quotation has passed.", "Die Frist der Angebotsanfrage ist abgelaufen.", "L'échéance de la demande de prix est dépassée.", "La scadenza della richiesta di offerta è passata." },
            new[] { "Use Send on the request for quotation to invite suppliers.", "Verwenden Sie Senden in der Angebotsanfrage, um Lieferanten einzuladen.", "Utilisez Envoyer sur la demande de prix pour inviter des fournisseurs.", "Usa Invia sulla richiesta di offerta per invitare i fornitori." },
            new[] { "The line belongs to another purchase request.", "Die Position gehört zu einer anderen Bestellanforderung.", "La ligne appartient à une autre demande d'achat.", "La riga appartiene a un'altra richiesta di acquisto." },
            new[] { "This supplier already has a quote for the line: change its price.", "Dieser Lieferant hat bereits ein Angebot für die Position: Ändern Sie dessen Preis.", "Ce fournisseur a déjà une offre pour la ligne : modifiez son prix.", "Questo fornitore ha già un'offerta per la riga: modificane il prezzo." },
            new[] { "Purchase orders can be created only on projects In Progress.", "Bestellungen können nur für Projekte im Status In Bearbeitung erstellt werden.", "Les commandes d'achat ne peuvent être créées que sur des projets En cours.", "Gli ordini di acquisto si possono creare solo su commesse In corso." },
            new[] { "Only approved purchase requests can be ordered.", "Nur genehmigte Bestellanforderungen können bestellt werden.", "Seules les demandes d'achat approuvées peuvent être commandées.", "Si possono ordinare solo richieste di acquisto approvate." },
            new[] { "Choose the supplier: set Preferred Supplier on the request.", "Wählen Sie den Lieferanten: Legen Sie Bevorzugter Lieferant in der Anforderung fest.", "Choisissez le fournisseur : renseignez Fournisseur préféré sur la demande.", "Scegli il fornitore: imposta Fornitore preferito sulla richiesta." },
            new[] { "The purchase request has no lines.", "Die Bestellanforderung hat keine Positionen.", "La demande d'achat n'a pas de lignes.", "La richiesta di acquisto non ha righe." },
            new[] { "New purchase orders start as Draft.", "Neue Bestellungen beginnen als Entwurf.", "Les nouvelles commandes d'achat commencent en Brouillon.", "I nuovi ordini di acquisto partono in Bozza." },
            new[] { "Use Send, Confirm or Cancel to change the status of a purchase order.", "Verwenden Sie Senden, Bestätigen oder Stornieren, um den Status einer Bestellung zu ändern.", "Utilisez Envoyer, Confirmer ou Annuler pour changer le statut d'une commande d'achat.", "Usa Invia, Conferma o Annulla per cambiare lo stato di un ordine di acquisto." },
            new[] { "A purchase order can be changed only while it is Draft.", "Eine Bestellung kann nur im Status Entwurf geändert werden.", "Une commande d'achat ne peut être modifiée que lorsqu'elle est Brouillon.", "Un ordine di acquisto si può modificare solo quando è in Bozza." },
            new[] { "Only draft or cancelled purchase orders can be deleted.", "Nur Bestellungen im Entwurf oder stornierte können gelöscht werden.", "Seules les commandes d'achat en brouillon ou annulées peuvent être supprimées.", "Si possono eliminare solo ordini di acquisto in bozza o annullati." },
            new[] { "Received quantities come from goods receipts.", "Erhaltene Mengen stammen aus Wareneingängen.", "Les quantités reçues proviennent des réceptions de marchandises.", "Le quantità ricevute derivano dai ricevimenti merci." },
            new[] { "Lines can be changed only while the purchase order is Draft.", "Positionen können nur geändert werden, solange die Bestellung im Status Entwurf ist.", "Les lignes ne peuvent être modifiées que lorsque la commande d'achat est Brouillon.", "Le righe si possono modificare solo quando l'ordine di acquisto è in Bozza." },
            new[] { "Status must be Draft, Sent, Confirmed or Cancelled.", "Der Status muss Entwurf, Gesendet, Bestätigt oder Storniert sein.", "Le statut doit être Brouillon, Envoyé, Confirmé ou Annulé.", "Lo stato deve essere Bozza, Inviato, Confermato o Annullato." },
            new[] { "Cancel the goods receipts before cancelling the order.", "Stornieren Sie die Wareneingänge, bevor Sie die Bestellung stornieren.", "Annulez les réceptions de marchandises avant d'annuler la commande.", "Annulla i ricevimenti merci prima di annullare l'ordine." },
            new[] { "An order becomes Received when all its lines are received.", "Eine Bestellung wird Eingegangen, wenn alle Positionen eingegangen sind.", "Une commande devient Reçue lorsque toutes ses lignes sont reçues.", "Un ordine diventa Ricevuto quando tutte le sue righe sono ricevute." },
            new[] { "This status change is not allowed for the purchase order.", "Diese Statusänderung ist für die Bestellung nicht zulässig.", "Ce changement de statut n'est pas autorisé pour la commande d'achat.", "Questo cambio di stato non è consentito per l'ordine di acquisto." },
            new[] { "Add at least one line before sending.", "Fügen Sie vor dem Senden mindestens eine Position hinzu.", "Ajoutez au moins une ligne avant l'envoi.", "Aggiungi almeno una riga prima dell'invio." },
            new[] { "Goods can be received only on sent or confirmed purchase orders.", "Waren können nur für gesendete oder bestätigte Bestellungen empfangen werden.", "Les marchandises ne peuvent être reçues que sur des commandes d'achat envoyées ou confirmées.", "La merce si può ricevere solo su ordini di acquisto inviati o confermati." },
            new[] { "A receipt line belongs to another purchase order.", "Eine Eingangsposition gehört zu einer anderen Bestellung.", "Une ligne de réception appartient à une autre commande d'achat.", "Una riga di ricevimento appartiene a un altro ordine di acquisto." },
            new[] { "Nothing to receive.", "Nichts zu empfangen.", "Rien à recevoir.", "Niente da ricevere." },
            new[] { "{0}: only {1} still to receive.", "{0}: nur noch {1} zu empfangen.", "{0} : seulement {1} restant à recevoir.", "{0}: solo {1} ancora da ricevere." },
            new[] { "Use Register Receipt on the purchase order to receive goods, and Cancel Receipt to undo a receipt.", "Verwenden Sie Eingang erfassen in der Bestellung, um Waren zu empfangen, und Eingang stornieren, um einen Eingang rückgängig zu machen.", "Utilisez Enregistrer la réception sur la commande d'achat pour recevoir des marchandises, et Annuler la réception pour annuler une réception.", "Usa Registra ricevimento sull'ordine di acquisto per ricevere la merce e Annulla ricevimento per annullare un ricevimento." },
            new[] { "This material usage comes from a goods receipt: cancel the receipt to change it.", "Dieser Materialverbrauch stammt aus einem Wareneingang: Stornieren Sie den Eingang, um ihn zu ändern.", "Cette consommation de matériel provient d'une réception de marchandises : annulez la réception pour la modifier.", "Questo consumo di materiale deriva da un ricevimento merci: annulla il ricevimento per modificarlo." },
            new[] { "Use Approve or Reject to decide a supplier invoice.", "Verwenden Sie Genehmigen oder Ablehnen, um über eine Lieferantenrechnung zu entscheiden.", "Utilisez Approuver ou Rejeter pour statuer sur une facture fournisseur.", "Usa Approva o Rifiuta per decidere una fattura fornitore." },
            new[] { "Approved or rejected invoices cannot be changed.", "Genehmigte oder abgelehnte Rechnungen können nicht geändert werden.", "Les factures approuvées ou rejetées ne peuvent pas être modifiées.", "Le fatture approvate o rifiutate non si possono modificare." },
            new[] { "Lines of approved or rejected invoices cannot be changed.", "Positionen genehmigter oder abgelehnter Rechnungen können nicht geändert werden.", "Les lignes des factures approuvées ou rejetées ne peuvent pas être modifiées.", "Le righe delle fatture approvate o rifiutate non si possono modificare." },
            new[] { "Add a note to reject the invoice.", "Fügen Sie eine Notiz hinzu, um die Rechnung abzulehnen.", "Ajoutez une note pour rejeter la facture.", "Aggiungi una nota per rifiutare la fattura." },
            new[] { "Only invoices to review can be approved or rejected.", "Nur zu prüfende Rechnungen können genehmigt oder abgelehnt werden.", "Seules les factures à examiner peuvent être approuvées ou rejetées.", "Si possono approvare o rifiutare solo fatture da verificare." },
            new[] { "Only the purchasing approver or an administrator can decide supplier invoices.", "Nur der Einkaufsgenehmiger oder ein Administrator kann über Lieferantenrechnungen entscheiden.", "Seul l'approbateur achats ou un administrateur peut statuer sur les factures fournisseur.", "Solo l'approvatore acquisti o un amministratore può decidere le fatture fornitore." },

            // ----- actions used in "Only a manager ... can {0}."
            new[] { "cancel the purchase request", "die Bestellanforderung stornieren", "annuler la demande d'achat", "annullare la richiesta di acquisto" },
            new[] { "create a request for quotation", "eine Angebotsanfrage erstellen", "créer une demande de prix", "creare una richiesta di offerta" },
            new[] { "send the request for quotation", "die Angebotsanfrage senden", "envoyer la demande de prix", "inviare la richiesta di offerta" },
            new[] { "award the request for quotation", "die Angebotsanfrage vergeben", "attribuer la demande de prix", "aggiudicare la richiesta di offerta" },
            new[] { "cancel the request for quotation", "die Angebotsanfrage stornieren", "annuler la demande de prix", "annullare la richiesta di offerta" },
            new[] { "create a purchase order", "eine Bestellung erstellen", "créer une commande d'achat", "creare un ordine di acquisto" },
            new[] { "change the status of the purchase order", "den Status der Bestellung ändern", "changer le statut de la commande d'achat", "cambiare lo stato dell'ordine di acquisto" },
            new[] { "register goods receipts", "Wareneingänge erfassen", "enregistrer des réceptions de marchandises", "registrare ricevimenti merci" },
            new[] { "cancel goods receipts", "Wareneingänge stornieren", "annuler des réceptions de marchandises", "annullare ricevimenti merci" },

            new[] { "Use Approve or Reject to review a supplier document.", "Verwenden Sie Genehmigen oder Ablehnen, um ein Lieferantendokument zu prüfen.", "Utilisez Approuver ou Rejeter pour examiner un document fournisseur.", "Usa Approva o Rifiuta per revisionare un documento fornitore." },
            new[] { "Add the e-mail address of the contact before inviting it to the supplier portal.", "Tragen Sie die E-Mail-Adresse des Kontakts ein, bevor Sie ihn zum Lieferantenportal einladen.", "Renseignez l'adresse e-mail du contact avant de l'inviter au portail fournisseurs.", "Inserisci l'indirizzo e-mail del contatto prima di invitarlo al portale fornitori." },
            new[] { "Set a supplier as Company Name of the contact before inviting it to the supplier portal.", "Legen Sie einen Lieferanten als Firmenname des Kontakts fest, bevor Sie ihn zum Lieferantenportal einladen.", "Indiquez un fournisseur comme Nom de la société du contact avant de l'inviter au portail fournisseurs.", "Imposta un fornitore come Nome società del contatto prima di invitarlo al portale fornitori." },
            new[] { "The supplier portal is not installed in this environment.", "Das Lieferantenportal ist in dieser Umgebung nicht installiert.", "Le portail fournisseurs n'est pas installé dans cet environnement.", "Il portale fornitori non è installato in questo ambiente." },
            new[] { "The invitation e-mail could not be sent: check the environment variables op365_SupplierEmailSender and op365_SupplierEmailTemplates (PortalInvitation).", "Die Einladungs-E-Mail konnte nicht gesendet werden: prüfen Sie die Umgebungsvariablen op365_SupplierEmailSender und op365_SupplierEmailTemplates (PortalInvitation).", "L'e-mail d'invitation n'a pas pu être envoyé : vérifiez les variables d'environnement op365_SupplierEmailSender et op365_SupplierEmailTemplates (PortalInvitation).", "Impossibile inviare l'e-mail di invito: verificare le variabili di ambiente op365_SupplierEmailSender e op365_SupplierEmailTemplates (PortalInvitation)." },
            new[] { "Approved documents cannot be changed.", "Genehmigte Dokumente können nicht geändert werden.", "Les documents approuvés ne peuvent pas être modifiés.", "I documenti approvati non si possono modificare." },
            new[] { "Approved documents cannot be deleted.", "Genehmigte Dokumente können nicht gelöscht werden.", "Les documents approuvés ne peuvent pas être supprimés.", "I documenti approvati non si possono eliminare." },
            new[] { "Add a note to reject the supplier document.", "Fügen Sie eine Notiz hinzu, um das Lieferantendokument abzulehnen.", "Ajoutez une note pour rejeter le document fournisseur.", "Aggiungi una nota per rifiutare il documento fornitore." },
            new[] { "Only supplier documents pending review can be approved or rejected.", "Nur Lieferantendokumente in Prüfung können genehmigt oder abgelehnt werden.", "Seuls les documents fournisseur en attente d'examen peuvent être approuvés ou rejetés.", "Si possono approvare o rifiutare solo documenti fornitore in attesa di revisione." },

            // ----- notifications
            new[] { "Supplier document to review", "Lieferantendokument zu prüfen", "Document fournisseur à examiner", "Documento fornitore da revisionare" },
            new[] { "{0} sent a document to review: {1}.", "{0} hat ein Dokument zur Prüfung gesendet: {1}.", "{0} a envoyé un document à examiner : {1}.", "{0} ha inviato un documento da revisionare: {1}." },
            new[] { "Record your hours", "Erfassen Sie Ihre Stunden", "Saisissez vos heures", "Registra le tue ore" },
            new[] { "You have recorded {0} of {1} hours on {2}.", "Sie haben am {2} {0} von {1} Stunden erfasst.", "Vous avez saisi {0} heures sur {1} le {2}.", "Hai registrato {0} ore su {1} il {2}." },
            new[] { "Open timesheet", "Zeiterfassung öffnen", "Ouvrir la feuille de temps", "Apri foglio ore" },
            new[] { "Purchase request to approve", "Bestellanforderung zu genehmigen", "Demande d'achat à approuver", "Richiesta di acquisto da approvare" },
            new[] { "Purchase request approved", "Bestellanforderung genehmigt", "Demande d'achat approuvée", "Richiesta di acquisto approvata" },
            new[] { "Purchase request rejected", "Bestellanforderung abgelehnt", "Demande d'achat rejetée", "Richiesta di acquisto rifiutata" },
            new[] { "{0} is above the approval threshold and needs your approval.", "{0} liegt über dem Genehmigungsschwellenwert und benötigt Ihre Genehmigung.", "{0} dépasse le seuil d'approbation et nécessite votre approbation.", "{0} supera la soglia di approvazione e richiede la tua approvazione." },
            new[] { "Time entries to approve", "Zeiteinträge zu genehmigen", "Saisies de temps à approuver", "Registrazioni ore da approvare" },
            new[] { "Time entries approved", "Zeiteinträge genehmigt", "Saisies de temps approuvées", "Registrazioni ore approvate" },
            new[] { "Time entries rejected", "Zeiteinträge abgelehnt", "Saisies de temps rejetées", "Registrazioni ore rifiutate" },
            new[] { "{0} time entries submitted on {1}.", "{0} Zeiteinträge für {1} eingereicht.", "{0} saisies de temps soumises sur {1}.", "{0} registrazioni ore inviate su {1}." },
            new[] { "{0} of your time entries were approved. Note: {1}", "{0} Ihrer Zeiteinträge wurden genehmigt. Notiz: {1}", "{0} de vos saisies de temps ont été approuvées. Note : {1}", "{0} delle tue registrazioni ore sono state approvate. Nota: {1}" },
            new[] { "{0} of your time entries were rejected. Note: {1}", "{0} Ihrer Zeiteinträge wurden abgelehnt. Notiz: {1}", "{0} de vos saisies de temps ont été rejetées. Note : {1}", "{0} delle tue registrazioni ore sono state rifiutate. Nota: {1}" },
            new[] { "{0} of your time entries were approved.", "{0} Ihrer Zeiteinträge wurden genehmigt.", "{0} de vos saisies de temps ont été approuvées.", "{0} delle tue registrazioni ore sono state approvate." },
            new[] { "{0} of your time entries were rejected.", "{0} Ihrer Zeiteinträge wurden abgelehnt.", "{0} de vos saisies de temps ont été rejetées.", "{0} delle tue registrazioni ore sono state rifiutate." },
            new[] { "{0} was approved. Note: {1}", "{0} wurde genehmigt. Notiz: {1}", "{0} a été approuvée. Note : {1}", "{0} è stata approvata. Nota: {1}" },
            new[] { "{0} was rejected. Note: {1}", "{0} wurde abgelehnt. Notiz: {1}", "{0} a été rejetée. Note : {1}", "{0} è stata rifiutata. Nota: {1}" },
            new[] { "{0} was approved.", "{0} wurde genehmigt.", "{0} a été approuvée.", "{0} è stata approvata." },
            new[] { "{0} was rejected.", "{0} wurde abgelehnt.", "{0} a été rejetée.", "{0} è stata rifiutata." },
            new[] { "{0} on {1}: {2}.", "{0} für {1}: {2}.", "{0} sur {1} : {2}.", "{0} su {1}: {2}." },
        };

        private static readonly Regex[] Patterns = Templates
            .Select(t => new Regex("^" + Regex.Replace(Regex.Escape(t[0]), @"\\\{(\d)}", "(?<p$1>.+?)") + "$", RegexOptions.Singleline))
            .ToArray();

        /// <summary>Column of a Dataverse language in the templates, 0 (English) for any other language.</summary>
        public static int Column(int languageId) =>
            languageId == 1031 ? 1 : languageId == 1036 ? 2 : languageId == 1040 ? 3 : 0;

        /// <summary>The message in the language of the given column; unknown messages stay as they are.</summary>
        public static string Translate(string message, int column)
        {
            if (column == 0 || string.IsNullOrEmpty(message)) return message;
            for (var i = 0; i < Patterns.Length; i++)
            {
                var m = Patterns[i].Match(message);
                if (!m.Success) continue;
                return Regex.Replace(Templates[i][column], @"\{(\d)}", p => Translate(m.Groups["p" + p.Groups[1].Value].Value, column));
            }
            return message;
        }
    }
}
