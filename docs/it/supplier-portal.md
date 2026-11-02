# Portale fornitori

> **Lingua:** [English](../en/supplier-portal.md) · Italiano · [Français](../fr/supplier-portal.md) · [Deutsch](../de/supplier-portal.md)
> **Indice dei manuali:** [README](../../README.md#user-manuals)

Il **portale fornitori** è un sito web, realizzato con Microsoft Power Pages sullo stesso database Dataverse di ProjectIQ, dove i tuoi fornitori possono lavorare con te senza email e fogli di calcolo che vanno avanti e indietro. Sul portale un fornitore:

- trova in una **dashboard** ciò che stai aspettando: RdO da quotare, ordini da confermare, documenti da rinnovare;
- vede le **richieste d'offerta** (RdO) che gli hai inviato, inserisce **prezzi unitari**, **giorni di consegna** e **note**, e invia l'offerta — oppure rinuncia;
- vede gli **ordini d'acquisto** che gli hai inviato, con righe e importi, e li **conferma**;
- vede quanto di ogni ordine è già stato **ricevuto**;
- **carica le sue fatture** (XML FatturaPA o PDF): i dati vengono letti automaticamente e controllati rispetto ai suoi ordini, poi ne segue l'approvazione e il **pagamento**;
- vede le **commesse** su cui lavora, con le attività del piano (WBS) assegnate a lui e, se lo consenti, ne aggiorna l'**avanzamento**;
- carica i suoi **documenti aziendali** (DURC, certificazioni, assicurazioni), che il tuo buyer approva, e viene avvisato quando scadono.

Tutto ciò che il fornitore fa è subito visibile in ProjectIQ: le offerte compaiono nel Quote Comparison della RdO, le conferme cambiano lo stato dell'ordine, i documenti caricati attendono la tua revisione.

Questo manuale ha due parti: la **Parte 1 per i fornitori** (puoi inviarla a loro) e la **Parte 2 per il personale interno**, che dà accesso ai fornitori e segue le loro risposte.

> Il portale è oggi in **inglese**: i nomi di pagine e pulsanti sono riportati come appaiono a schermo.

```mermaid
sequenceDiagram
    participant B as Buyer (ProjectIQ)
    participant DV as Dataverse
    participant S as Fornitore (portale)
    B->>DV: Send RFQ (invito + righe d'offerta vuote)
    S->>DV: Requests for quotation → Open → prezzi, giorni consegna → Send quote
    DV-->>B: Invito Responded, Quote Comparison aggiornato
    B->>DV: Award → ordine → Send to Supplier
    S->>DV: Purchase orders → Open → Confirm order
    DV-->>B: Ordine Confirmed
    B->>DV: Register Receipt
    S->>DV: Vede le quantita Received
    S->>DV: Documents → Upload document (DURC...)
    B->>DV: Approve o Reject
    DV-->>S: Email di scadenza e avviso nella Dashboard
```

## Parte 1 — Guida per i fornitori

### Accesso

Il tuo cliente ti dà accesso al suo portale fornitori. Ricevi l'indirizzo del portale (per esempio `https://<cliente>-suppliers.powerappsportals.com`) e le istruzioni per creare o attivare il tuo account. Usa l'indirizzo email che il cliente ha registrato per te.

1. Apri l'indirizzo del portale e clicca **Sign in**.
2. Accedi con il tuo account: in **Sign in with a local account** inserisci **Email** e **Password** (**Forgot your password?** ti invia un link per reimpostarla), oppure usa **Microsoft Entra ID** se il cliente ti ha dato un account aziendale. Non hai ancora un account? Clicca **Register**, oppure **Redeem invitation** se hai ricevuto un codice d'invito.
3. Dopo l'accesso il portale apre la **Dashboard** (la home page ti porta lì; se il tuo account non è ancora collegato a un fornitore, ti chiede di rivolgerti al cliente). A sinistra, la barra laterale mostra i moduli: **Dashboard**, **Projects** (commesse), **Requests for quotation** (richieste d'offerta), **Purchase orders** (ordini d'acquisto), **Invoices** (fatture) e **Documents** (documenti). Un contatore blu indica le RdO da quotare e gli ordini da confermare; un contatore arancione i documenti da rinnovare o correggere. In fondo trovi la tua azienda, il tuo nome e **Sign out**.

Se una pagina dice "This area is reserved to suppliers. Sign in with the account your customer invited.", non hai effettuato l'accesso, oppure il tuo account non è ancora abilitato come fornitore: contatta il tuo cliente.

Vedi solo i dati **della tua azienda**. I colleghi della tua azienda con un proprio account vedono gli stessi dati.

### La dashboard

La **Dashboard** è la pagina iniziale:

| Parte | Cosa mostra |
|---|---|
| Contatori | **Requests to quote** (RdO da quotare), **Orders to confirm** (ordini da confermare), l'importo **Ordered** nell'anno in corso (ordini confermati e ricevuti) e le **Invoices under review** (fatture in verifica) |
| **Document compliance** | Un anello con la quota dei tuoi documenti approvati validi (verde), in scadenza entro 30 giorni (arancione) e scaduti (rosso), più quanti attendono la revisione o sono stati rifiutati |
| **To do** | Una riga per ogni cosa che il cliente aspetta: documenti scaduti da rinnovare, documenti rifiutati da correggere, RdO da quotare (con la scadenza), ordini da confermare, documenti in scadenza. Clicca una riga per aprire la pagina in cui farlo |
| **Your projects** | Le prime schede commessa (vedi sotto), con **All projects** per l'elenco completo |

### Commesse

**Projects** mostra una scheda per ogni commessa che il cliente ha assegnato alla tua azienda: codice e nome (con il tuo **ruolo**, se indicato), **Project progress** (avanzamento della commessa), **Your deliveries** (la quota del tuo importo ordinato già ricevuta, solo se hai ordini), **Start date**, **End date** e il numero di **Orders**. Una commessa compare quando il cliente ti invita a una richiesta d'offerta (badge **Invited**), ti invia un ordine d'acquisto o ti aggiunge alla commessa. Una commessa con un ordine da confermare ha il bordo arancione.

**Open project** mostra l'intestazione della commessa (codice, data inizio e fine, avanzamento) e, sotto **Your work**, le attività del piano assegnate alla tua azienda: **Code**, **Activity**, **Start**, **End** e **Progress**. Budget e costi non sono mai mostrati.

### Aggiornare l'avanzamento delle tue attività

Se il cliente lo consente, il **Progress** di ogni attività senza sotto-attività è una casella con **Save**: scrivi la percentuale (0–100) e clicca **Save**. L'avanzamento delle attività di riepilogo (in grassetto) e della commessa è calcolato da queste, quindi non si può scrivere. Se il cliente non lo consente, vedi solo le barre di avanzamento.

### Rispondere a una richiesta d'offerta

1. Clicca **Requests for quotation**. Ogni RdO è una scheda con data d'invito, numero, oggetto, l'importo **Quoted** dopo che hai risposto e una barra che mostra quanto tempo resta prima della **Deadline** (scadenza; diventa arancione e poi rossa man mano che la scadenza si avvicina). I pulsanti in alto filtrano le schede: **All**, **To quote**, **Quoted**, **Closed**.

| Etichetta della scheda | Significato |
|---|---|
| **To quote** | In attesa della tua offerta (bordo arancione) |
| **Quoted** | Hai inviato un'offerta (puoi ancora modificarla fino alla scadenza) |
| **Declined** / **Closed** | Hai rinunciato, oppure la scadenza è passata |

2. Clicca **Quote now** (oppure **Change quote**, **Open**) sulla scheda. Vedi numero, scadenza, le note del cliente e l'elenco degli articoli con quantità e unità.
3. Per ogni riga scrivi lo **Unit price** (prezzo unitario) e, se serve, le **Notes** (marca, prodotto alternativo, condizioni...).
4. Scrivi i **Delivery days** (in quanti giorni dall'ordine puoi consegnare) ed eventuali **Notes for the buyer**.
5. Clicca **Send quote**. Un messaggio verde conferma: "Your quote has been sent. You can change it until the deadline."

Da sapere:

- Puoi lasciare una riga senza prezzo se non fornisci quell'articolo: "Lines without a price are not quoted." Quotare tutte le righe aumenta le tue possibilità, perché il miglior totale si calcola solo tra i fornitori che hanno quotato tutte le righe.
- Puoi tornare e **modificare i prezzi fino alla scadenza**. Dopo la scadenza (o dopo la rinuncia) i campi sono in sola lettura.
- Se non puoi quotare, clicca **Decline** e conferma. La RdO viene marcata Declined.
- L'importo **Quoted** nell'elenco è quantità × prezzo unitario su tutte le tue righe.

### Confermare un ordine d'acquisto

1. Clicca **Purchase orders**. Ogni ordine è una scheda con commessa, data ordine, numero e totale. Gli ordini in attesa della tua conferma sono marcati **To confirm** e mostrano consegna prevista, condizioni di pagamento e luogo di consegna; gli altri mostrano una barra **Received** (ricevuto). I pulsanti in alto filtrano le schede: **All**, **To confirm**, **Confirmed**, **Received**.
2. Clicca **Review and confirm** (oppure **Open**). Vedi data ordine, consegna prevista, **Delivery place** (luogo di consegna), **Payment terms** (condizioni di pagamento), stato, e le righe con quantità, prezzo unitario, importo e quantità già **Received** (ricevuta).
3. Controlla l'ordine e clicca **Confirm order**, poi conferma. Lo stato diventa **Confirmed** con la data di conferma.

| Stato mostrato | Significato |
|---|---|
| **To confirm** | L'ordine ti è stato inviato e attende la tua conferma |
| **Confirmed** | Tu (o il buyer per tuo conto) lo avete confermato |
| **Received** | Tutta la merce è stata ricevuta dal tuo cliente |

Se qualcosa nell'ordine non va (prezzo, quantità, data), non confermarlo: contatta il buyer, che correggerà l'ordine e lo invierà di nuovo.

### Fatture

**Invoices** è dove invii le fatture al cliente e le segui fino al pagamento.

**Inviare le fatture**

1. Trascina i file delle fatture sull'area di caricamento, oppure clicca **Choose files**. Puoi inviarne più di una insieme: **XML** FatturaPA (anche firmato `.p7m`), **PDF** o immagini, fino a 10 MB ciascuno.
2. Ogni file compare in **To send** con *Reading…*: il portale legge i dati da solo in pochi secondi (la pagina si aggiorna).
3. Ogni fattura riceve uno stato:

| Stato | Significato | Cosa fare |
|---|---|---|
| **Ready** | Dati letti, ordine trovato, importi coerenti | Nulla: inviala |
| **To check** | Qualcosa va guardato: un valore letto con bassa confidenza, l'ordine da scegliere, una differenza rispetto all'ordine | Clicca **Check** |
| **Blocked** | Hai già inviato quest'anno una fattura con questo numero | Clicca **Delete** |

4. Clicca **Send the N ready invoices** per inviare insieme tutte quelle pronte.

**Controllare una fattura**

**Check** (o **Open**) mostra il file a sinistra e i dati letti a destra. I campi da controllare sono evidenziati in arancione e il riquadro giallo spiega perché. Sotto **Lines and order** ogni riga è confrontata con l'ordine: **Same** (uguale), la differenza (per esempio **+84.00**) oppure **Not on the order** (non nell'ordine). Correggi se serve **Invoice number**, **Invoice date**, **Due date** o **Purchase order**, e scrivi una **Note for your customer** se fatturi qualcosa di diverso dall'ordine (ad esempio ore extra concordate in cantiere). **Save and check** salva e ricontrolla; poi **Send invoice**. **Delete** elimina una fattura non ancora inviata.

Da un file XML ogni valore viene dalla fattura elettronica; da un PDF i valori sono letti dall'AI: controllali sempre prima di inviare. Una volta inviata, la fattura non si può più modificare: se è sbagliata, chiedi al cliente di rifiutarla e inviala di nuovo.

**Seguire le fatture inviate**

Sotto **Sent** trovi i totali **Under review** (in verifica), **To be paid** (da pagare), **Paid** nell'anno in corso e **Rejected**, poi una scheda per fattura con ordine e commessa, numero, importo, tipo documento e date. I passi **Sent → Approved → Scheduled → Paid** (oppure **Rejected**, in rosso) mostrano a che punto è; una fattura rifiutata mostra la **Reason** (motivo), una pagata l'importo, la data e il riferimento del bonifico. I pulsanti in alto filtrano le schede.

### Documenti aziendali

**Documents** elenca i documenti che il cliente richiede alla tua azienda (DURC, visura camerale, certificazioni, assicurazioni, contratti) con **Number**, **Issued** (emissione), **Expires** (scadenza) e due etichette:

| Colonna | Etichette |
|---|---|
| **Expiry** | **Valid** (valido), **Expiring** (in scadenza entro 30 giorni), **Expired** (scaduto), **Replaced** (è stato approvato un documento più recente dello stesso tipo), **No expiry** (senza scadenza) |
| **Review** | **Pending review** (il buyer non l'ha ancora controllato), **Approved**, **Rejected** (con il motivo) |

Per caricare un documento:

1. Clicca **New document** (oppure scorri fino al modulo in fondo alla pagina).
2. Scegli il **Type** (tipo), scrivi una **Description** e, se presenti, **Number**, **Issue date**, **Expiry date** e **Notes**.
3. Scegli il **File** (PDF o immagine, fino a 32 MB) e clicca **Upload document**.

Il documento resta **Pending review** finché il buyer non lo approva. Finché è in revisione o rifiutato puoi cliccare **Edit** (modifica dati o file, poi **Save changes**) o **Delete**. Correggere un documento rifiutato lo rimanda in revisione. Una volta **Approved** il documento si può solo consultare: per rinnovarlo carica un nuovo documento dello stesso tipo; quando il buyer lo approva, il vecchio diventa **Replaced**. Quando il buyer lo approva, il file passa nell'archivio del cliente: l'elenco mostra **Filed by your customer** al posto del nome del file.

Ricevi un'email quando un documento approvato sta per scadere (30 giorni prima) e quando scade; la Dashboard mostra gli stessi avvisi.

### Errori

Se un'azione non riesce, un messaggio rosso spiega il motivo. Casi comuni: "Session expired: sign in again." (accedi di nuovo e ripeti), "The deadline of the request for quotation has passed." (contatta il buyer per una proroga), "The request for quotation is closed." (è stata aggiudicata o annullata), "Approved documents cannot be changed." o "Approved documents cannot be deleted." (carica invece un nuovo documento), "Choose the file of the document." (un nuovo documento richiede il suo file), "Progress must be between 0 and 100.", "Progress updates from the supplier portal are disabled." (il cliente li ha disattivati), "Sent invoices cannot be changed." (chiedi al cliente di rifiutare la fattura), "The invoice cannot be sent while it is being read or when it is a duplicate." (attendi qualche secondo, oppure elimina il duplicato), "Fill in the invoice number and date.".

## Parte 2 — Guida per il personale interno

### Cosa espone il portale

Il portale è volutamente ristretto. I fornitori possono leggere solo i propri record e scrivere solo pochi campi:

| Dati | Il fornitore può leggere | Il fornitore può modificare |
|---|---|---|
| Inviti RdO della sua azienda | Numero, scadenza, note, stato, importo quotato | **Delivery days**, **supplier notes**, **status** (solo verso Responded o Declined) |
| Righe d'offerta di quegli inviti | Articolo, quantità, unità, prezzo, note | **Unit price**, **notes** |
| Ordini d'acquisto della sua azienda (Sent, Confirmed, Received) | Testata e importi | **Supplier confirmed** (che conferma l'ordine) |
| Righe di quegli ordini | Articolo, quantità, prezzo, importo, quantità ricevuta | Nulla |
| Fornitori di commessa della sua azienda (Active e Invited) | Commessa, ruolo, stato | Nulla |
| Commesse di quei fornitori di commessa e dei suoi ordini | Codice, nome, data inizio e fine, avanzamento | Nulla |
| Nodi WBS del suo perimetro | Codice, nome, data inizio e fine, avanzamento | **Progress %** dei nodi senza nodi figli, solo se **Supplier Progress Updates** è Yes |
| Fatture fornitore della sua azienda | Numero, date, importi, righe, stato, nota della decisione, pagamento, note di estrazione | Caricare il file, **numero fattura**, **date**, **ordine d'acquisto** e **nota del fornitore** finché è Draft; **inviarla** (Draft → To Review) se non è Pending o Blocked; eliminare le bozze |
| Documenti fornitore della sua azienda | Tutti i campi, compresa la nota di revisione | Tipo, descrizione, numero, date, note, file; può crearli ed eliminarli, solo finché il documento non è approvato |

Ordini in bozza o annullati e RdO non ancora inviate non vengono mai mostrati. I prezzi degli altri fornitori, i budget e i costi non sono mai visibili.

### Fornitori di commessa e perimetro WBS

Un **Project Supplier** (fornitore di commessa) indica che un fornitore lavora su una commessa e quali attività della WBS vede sul portale (il suo **WBS Scope**). Li trovi nell'elenco **Suppliers** della commessa (scheda Purchasing) e nell'elenco **Projects** dell'account fornitore.

```mermaid
flowchart LR
    I[RFQ Send: invitation Invited] -->|creates| PS[Project Supplier<br/>status Invited]
    O[Send to Supplier] -->|creates or activates| PS2[Project Supplier<br/>status Active]
    O -->|adds| W[WBS nodes of the order lines<br/>with their branches]
    M[+ New Project Supplier<br/>by hand] --> PS2
    PS2 --> P[Portal: project card<br/>+ Your work]
    PS --> P
```

- **Send** su una RdO rende ogni fornitore invitato un fornitore di commessa **Invited** (se non c'è già).
- **Send to Supplier** su un ordine rende il fornitore **Active** e aggiunge al suo WBS Scope i nodi WBS delle righe dell'ordine. Se poi l'ordine viene annullato, il fornitore di commessa e il suo perimetro restano.
- Puoi aggiungere un fornitore di commessa a mano dall'elenco **Suppliers** della commessa (**Project**, **Supplier**, **Role**) e aggiungere nodi WBS nel suo elenco **WBS Scope** (**Add Existing WBS Node**). Un nodo porta sempre con sé tutte le sue sotto-attività, anche quelle create dopo.
- Per nascondere attività, rimuovile dal WBS Scope (rimuovere un nodo non rimuove le sue sotto-attività: rimuovi anche quelle), oppure disattiva il fornitore di commessa per nascondere l'intera commessa.
- Se i fornitori possono aggiornare l'avanzamento è un'impostazione aziendale, **Supplier Progress Updates** ([Amministrazione](administration.md#impostazioni-aziendali)); il valore predefinito è No. *Can Update Progress* sul fornitore di commessa mostra il valore attuale.

### Dare accesso a un fornitore

Un utente fornitore è un **contatto** la cui **Company Name** è l'account del fornitore. ProjectIQ assegna automaticamente a questo contatto il web role **Supplier** e lo toglie quando la Company Name non è più un fornitore: non assegni mai i web role a mano.

```mermaid
flowchart LR
    A[Contatto con Company Name = fornitore] -->|automatico| R[Web role Supplier]
    A --> I[Invite to Portal] --> M[E-mail con codice d'invito] --> S[Il fornitore si registra] --> P[Portale]
    X[Persona autoregistrata] -->|imposti la Company Name| A
```

1. In ProjectIQ verifica che l'account del fornitore sia **Is Supplier**, **Active** e non **Blocked**.
2. Crea (o apri) il **contatto** della persona, con **Company Name** = il fornitore e la sua **Email**.
3. Sul contatto clicca **Invite to Portal** e conferma. La persona riceve un'e-mail con un invito (valido 30 giorni, utilizzabile una volta): seguendolo crea il suo account (e-mail e password, oppure Microsoft) già collegato al fornitore.
4. Invia alla persona la [Parte 1](#parte-1--guida-per-i-fornitori) di questo manuale.

**Invite to Portal** rifiuta un contatto senza e-mail ("Add the e-mail address of the contact before inviting it to the supplier portal.") o la cui Company Name non è un fornitore ("Set a supplier as Company Name of the contact before inviting it to the supplier portal."). L'e-mail è scritta nella **Language** del fornitore e parte con la stessa configurazione delle e-mail di scadenza ([Amministrazione](administration.md#scadenza-giornaliera-dei-documenti)); senza di essa ricevi "The invitation e-mail could not be sent: check the environment variables op365_SupplierEmailSender and op365_SupplierEmailTemplates (PortalInvitation)." e nessun invito viene creato. Gli inviti si trovano in Power Pages Management → *Invitations*.

Per togliere l'accesso cambia la Company Name del contatto (il web role Supplier viene rimosso) o disattiva il contatto.

**Metodi di accesso.** Oltre a Microsoft Entra ID, il portale offre **account locali** (e-mail e password), così possono accedere anche i fornitori esterni al tuo tenant. Le persone possono anche **registrarsi** da sole: una persona autoregistrata non vede nulla finché non imposti la **Company Name** del suo contatto sul fornitore, cosa che le assegna il web role Supplier; controlla regolarmente i nuovi contatti. L'amministratore può disattivare gli account locali o l'autoregistrazione (allora possono registrarsi solo le persone invitate), vedi [Configurazione dell'ambiente di sviluppo](../dev-environment.md#supplier-portal-power-pages).

### Revisione dei documenti

Un documento caricato sul portale è **Pending Review** e il proprietario dell'account del fornitore riceve la notifica "Supplier document to review". Aprilo dalla notifica, o dalla vista **Supplier Documents to Review**, controlla il file e clicca **Approve** o **Reject** (con una nota che il fornitore leggerà). Vedi [Anagrafiche](master-data.md#revisione). Le email di scadenza ai fornitori richiedono la configurazione descritta in [Amministrazione](administration.md#scadenza-giornaliera-dei-documenti).

### Seguire le risposte

- Nella RdO, l'elenco **Invitations** mostra per ogni fornitore stato, **Responded On**, **Quoted Amount** e **Delivery Days**; il contatore **Responses** mostra quanti hanno risposto.
- La tab **Quote Comparison** mostra le offerte del portale accanto a quelle inserite da te. Aggiudica come descritto in [Acquisti](purchasing.md#confronto-e-aggiudicazione).
- Quando un fornitore conferma un ordine dal portale, l'ordine diventa **Confirmed** e vengono compilati *Supplier Confirmed* / *Confirmed On*, esattamente come se avessi cliccato **Confirm**.

### Da ricordare

- Una RdO compare sul portale solo dopo **Send**; un ordine solo dopo **Send to Supplier**.
- Nessuna delle due azioni invia da sola un'email: avvisa il fornitore che c'è una nuova RdO o un nuovo ordine (con la tua email abituale, o con un'automazione che l'amministratore può aggiungere).
- Se riporti un ordine **Back to Draft**, sparisce dal portale finché non lo invii di nuovo (la commessa resta, tramite il fornitore di commessa).
- Dopo la scadenza il fornitore non può più modificare l'offerta: proroga la **Deadline** e clicca di nuovo **Send** se vuoi altre risposte.

### Per gli amministratori

Il portale è distribuito come soluzione separata, **OpenProject365SupplierPortal**, che dipende dalla soluzione principale. L'aspetto del portale (barra laterale, schede, anello di conformità) è solo Liquid e CSS nei web template **OP365 Supplier Style**, **OP365 Supplier Nav** e **OP365 Supplier Project Cards**. Configurazione, permessi sulle tabelle, impostazioni della Web API e passi di distribuzione sono documentati in [Development environment setup](../dev-environment.md#supplier-portal-power-pages) (in inglese). Dopo ogni distribuzione del portale, svuota la cache del sito (`/_services/about` → *Clear cache*, web role Administrators) e accedi di nuovo. In un nuovo ambiente, il sito importato va riattivato (Power Pages → *Inactive sites*) prima dell'uso.
