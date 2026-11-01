# Documenti in SharePoint

> **Lingua:** [English](../en/documents.md) · Italiano · [Français](../fr/documents.md) · [Deutsch](../de/documents.md)
> **Indice dei manuali:** [README](../../README.md#user-manuals)

Contratti, disegni, SAL, offerte e DDT appartengono a una commessa, ma non al database. ProjectIQ li tiene in **SharePoint**, con la gestione documentale standard di Dataverse: ogni **Project**, **Purchase Order** e **Supplier Document** ha la sua cartella SharePoint, aperta dal record. I file mantengono il versioning di SharePoint, la co-redazione in Office, la ricerca e la condivisione; ProjectIQ memorizza solo dove si trova la cartella.

Questo manuale è per chi lavora con i documenti di commessa (parte 1) e per gli amministratori che collegano ProjectIQ a SharePoint (parte 2).

## Come funziona

```mermaid
flowchart LR
    subgraph DV[ProjectIQ - Dataverse]
        P[Project<br/>Purchase Order<br/>Supplier Document] -->|Regarding| L[Document location<br/>cartella del record]
        L --> LL[Document location<br/>raccolta]
        LL --> S[Sito SharePoint]
    end
    subgraph SP[Sito SharePoint]
        LIB[Raccolta op365_project<br/>op365_purchaseorder<br/>op365_supplierdocument] --> F[Una cartella per record]
    end
    S -.-> LIB
    L -.-> F
    U[Utente nell'app<br/>Related > Documents] --> F
    A[Portfolio Agent<br/>Documenti di commessa] --> F
```

| Tabella | Raccolta SharePoint | Cartella |
|---|---|---|
| Project | `op365_project` | Una per commessa, con il nome della commessa e il suo id |
| Purchase Order | `op365_purchaseorder` | Una per ordine |
| Supplier Document | `op365_supplierdocument` | Una per documento (per esempio il DURC scansionato con i suoi allegati) |

La cartella viene creata la **prima volta che qualcuno apre Documents** sul record. Dataverse salva una *document location* che collega il record alla cartella; l'agente e l'app trovano la cartella tramite questa. Un progetto creato in Copilot da un documento ha già la sua cartella, con il documento dentro (vedi [Portfolio Agent](portfolio-agent.md#nuovo-progetto-da-documento)).

## Parte 1: lavorare con i documenti

### Aprire i documenti di un record

1. Apri la commessa (o l'ordine d'acquisto, o il documento fornitore).
2. Seleziona **Related** → **Documents**. La prima volta ProjectIQ crea la cartella SharePoint del record.
3. La griglia elenca i file della cartella: **Upload**, **New** (Word, Excel, PowerPoint, OneNote), **Open in SharePoint**, **Delete**, **Check Out** / **Check In** e **Edit Properties** lavorano direttamente su SharePoint.

| Comando | Cosa fa |
|---|---|
| **Upload** | Carica uno o più file nella cartella (o in una sottocartella) |
| **New** | Crea un documento Office nella cartella e lo apre nel browser |
| **Open Location** / **Open in SharePoint** | Apre la cartella in SharePoint, per sottocartelle, condivisione, versioni e spostamenti massivi |
| **Document Location** → **Add Location** | Collega al record un'altra cartella SharePoint esistente (per esempio una cartella di un team Teams) |

### Chi vede quali file

- Per vedere la scheda **Documents** serve il ruolo ProjectIQ (vedi [Amministrazione](administration.md#ruoli-di-sicurezza)): **OP365 User** può creare la cartella dei record che può aprire e leggere tutte le document location.
- **Sono i permessi SharePoint a decidere quali file vedi.** ProjectIQ non copia la condivisione delle commesse in SharePoint: dai al team di commessa l'accesso al sito (o a una raccolta o cartella) in SharePoint.

### Colonne ProjectIQ

Ogni file aggiunto alla cartella di un record riceve, entro pochi minuti e senza che nessuno le digiti, le informazioni di quel record in colonne SharePoint. Puoi ordinare, filtrare e raggruppare la raccolta in base a queste colonne. Microsoft Search e Copilot le usano per trovare "i documenti della commessa PRJ-000123" o "i file del fornitore Rossi" anche quando il testo del file non li cita.

| Colonna | Project | Purchase Order | Supplier Document |
|---|---|---|---|
| **ProjectIQ Record Type** | Project | Purchase Order | Supplier Document |
| **Project Code** | Codice della commessa | Codice della commessa dell'ordine | – |
| **Project Name** | Nome della commessa | Nome della commessa dell'ordine | – |
| **Customer** | Cliente della commessa | Cliente della commessa dell'ordine | – |
| **Project Manager** | Project manager | Project manager della commessa dell'ordine | – |
| **PO Number** | – | Numero dell'ordine (PO-#####) | – |
| **Supplier** | – | Fornitore dell'ordine | Fornitore del documento |

- I valori sono quelli del record **nel momento in cui il file viene aggiunto**. Se rinomini una commessa o ne cambi il cliente, i file già presenti non vengono aggiornati.
- I file fuori dalla cartella di un record non vengono classificati: per esempio quelli nella radice della raccolta o in una cartella aggiunta con **Add Location**.
- Le colonne si modificano come qualsiasi altra colonna SharePoint e ProjectIQ non le sovrascrive. **ProjectIQ Record Id** è nascosta nei moduli e conserva il record a cui appartiene il file.

### Documenti in Copilot

Nel [Portfolio Agent](portfolio-agent.md#documenti-di-commessa) chiedi "mostra i documenti della commessa PRJ-000123": la card elenca file e sottocartelle della cartella della commessa, dai più recenti, con il link a ogni file e alla cartella. Se è impostata una fonte di conoscenza SharePoint, puoi chiedere anche cosa dice un documento (vedi [Portfolio Agent](portfolio-agent.md#domande-sul-contenuto-dei-documenti)).

### Documenti fornitore

Un **Supplier Document** (DURC, certificazione, assicurazione) ha una colonna **File**, usata dal [portale fornitori](supplier-portal.md). Quando il buyer approva un documento, il flusso **File approved supplier documents** sposta il file nella cartella SharePoint del record e svuota la colonna, così i documenti approvati stanno tutti in SharePoint (vedi [sotto](#documenti-fornitore-approvati-in-sharepoint)). La cartella SharePoint contiene anche gli altri file che accompagnano il documento (rinnovi, corrispondenza). Scadenze e conformità fornitori continuano a basarsi sui campi del Supplier Document come prima.

## Parte 2: configurazione (amministratori)

Si fa una volta per ambiente, dall'amministratore Power Platform insieme a un amministratore SharePoint.

```mermaid
flowchart TD
    A[1. Sito SharePoint per i documenti<br/>es. /sites/ProjectIQDocuments] --> B[2. Registrare il sito in ProjectIQ<br/>Document Management Settings]
    B --> C[3. Raccolte create per<br/>Project, Purchase Order, Supplier Document]
    C --> D[4. Dare al team di commessa<br/>l'accesso al sito]
    D --> E[5. Gli utenti aprono Related > Documents]
```

| Passo | Chi | Cosa |
|---|---|---|
| 1 | Amministratore SharePoint | Crea un sito SharePoint di team o di comunicazione per i documenti, nello stesso tenant Microsoft 365 dell'ambiente |
| 2 | Amministratore Power Platform | Nell'app apri **Settings** (ingranaggio) → **Advanced Settings** → **Document Management** → **Document Management Settings**, seleziona **Project**, **Purchase Order** e **Supplier Document**, inserisci l'URL del sito, seleziona **Next** e **Finish**. Le raccolte vengono create sul sito. Per aggiungere una tabella in seguito, ripeti la procedura guidata selezionando anche quella: viene creata la raccolta mancante |
| 3 | Amministratore Power Platform | Alternativa al passo 2 per ambienti gestiti da script: `SHAREPOINT_SITE_URL=<URL del sito> python3 tools/dataverse/documents.py` registra il sito come sito predefinito; le raccolte vengono create quando il primo record di ogni tabella apre Documents; se una raccolta manca ancora, usa il passo 2 |
| 4 | Amministratore SharePoint | Dai alle persone che usano ProjectIQ almeno **Edit** (o **Read**) sul sito |
| 5 | Ogni utente | Apri **Related** → **Documents** su un record |

L'integrazione SharePoint server-based è attiva per impostazione predefinita in Dataverse online; se **Document Management Settings** segnala che è disattivata, attivala da **Advanced Settings** → **Document Management** → **Enable Server-Based SharePoint Integration**.

La gestione documentale sulle tre tabelle e i privilegi su document location e sito SharePoint dei ruoli **OP365 User** e **OP365 Administrator** fanno parte della soluzione ProjectIQ: un aggiornamento della soluzione li porta. Il sito SharePoint è un'impostazione di ogni ambiente e non è nella soluzione.

### Colonne ProjectIQ sui file

Le [colonne ProjectIQ](#colonne-projectiq) sono compilate da tre flussi cloud della soluzione, uno per raccolta:
- **Tag project documents**
- **Tag purchase order documents**
- **Tag supplier documents**

I flussi controllano la raccolta ogni 3 minuti e usano due riferimenti di connessione:
- **op365_sharepoint** (SharePoint), che deve appartenere a un **utente dedicato** con permesso **Edit** sul sito;
- **op365_dataverse**.

| Passo | Chi | Cosa |
|---|---|---|
| 1 | Admin SharePoint | Le tre raccolte devono esistere (vedi [Parte 2](#parte-2-configurazione-amministratori)). Con la CLI for Microsoft 365 (`npm i -g @pnp/cli-microsoft365`, poi `m365 login`) autenticata come proprietario del sito, esegui `SHAREPOINT_SITE_URL=<URL del sito> python3 tools/sharepoint/document_metadata.py`, con l'URL registrato in **Document Management Settings**. Lo script aggiunge le colonne mancanti alle tre raccolte e alla loro vista predefinita (`ok`), lascia quelle esistenti (`skip`) e stampa i tre id; si può rieseguire |
| 2 | Admin Power Platform | Imposta le variabili d'ambiente **SharePoint Site URL** (`op365_SharePointSiteUrl`), **Project Library Id**, **Purchase Order Library Id** e **Supplier Document Library Id** con l'URL del sito e gli id stampati. In Test si impostano tramite il deploy, con i secret `OP365_SHAREPOINT_SITE_URL`, `OP365_PROJECT_LIBRARY_ID`, `OP365_PURCHASE_ORDER_LIBRARY_ID` e `OP365_SUPPLIER_DOCUMENT_LIBRARY_ID` dell'ambiente GitHub `test`, vedi [dev-environment](../dev-environment.md#4-deploy-to-test) |
| 3 | Admin Power Platform | Crea la connessione SharePoint con l'utente dedicato nell'ambiente stesso, Test compreso: una connessione non fa parte della soluzione e non arriva da Dev. Condividila con l'utente applicativo del deploy (**Can use**). In Dev collegala a **op365_sharepoint**. In Test non collegarla a mano: metti il suo id (nell'URL della pagina della connessione) nel secret `OP365_SHAREPOINT_CONNECTION_ID` ed esegui `deploy-test`, che collega il riferimento; modificare a mano il riferimento o i flussi in Test aggiunge un livello non gestito sopra la soluzione gestita. Poi attiva i tre flussi (**Solutions** → **ProjectIQ** → **Cloud flows**) |
| 4 | Admin SharePoint | Facoltativo, per i file già presenti: ripeti il passo 1 con `--backfill` e le variabili `PAC_*` dell'ambiente |

I flussi vengono importati **disattivati**: dopo ogni aggiornamento della soluzione controlla che siano ancora attivi.

### Documenti fornitore approvati in SharePoint

Il flusso **File approved supplier documents** parte quando un documento fornitore diventa **Approved** (**Approve** nell'app). Se il documento ha un file nella colonna **File**, il flusso:
1. trova la cartella SharePoint del record, oppure ne registra una nuova (`<descrizione>_<id del record>`) nella raccolta **op365_supplierdocument**;
2. crea il file in quella cartella con il nome originale (il flusso **Tag supplier documents** compila poi le sue colonne ProjectIQ);
3. rimuove il file dalla colonna **File**. Sul portale il fornitore vede allora **Filed by your customer** al posto del file.

Usa gli stessi riferimenti di connessione **op365_dataverse** e **op365_sharepoint** e la variabile **SharePoint Site URL**; la raccolta **op365_supplierdocument** e la sua document location devono esistere ([Parte 2](#parte-2-configurazione-amministratori), passo 2). Se la copia non riesce, il file resta nella colonna **File**: controlla la cronologia delle esecuzioni e rilancia il flusso dall'esecuzione fallita (**Resubmit**), senza approvare di nuovo.

## Messaggi che potresti vedere

| Messaggio | Significato e soluzione |
|---|---|
| Nessun **Documents** sotto **Related**, o un messaggio che la gestione documentale non è configurata | Il sito non è registrato (vedi [Parte 2](#parte-2-configurazione-amministratori), passo 2), oppure l'app ProjectIQ non contiene le tabelle **SharePoint Document** e **Document Location**: esegui `tools/dataverse/app.py` o aggiungi le tabelle nel designer dell'app e pubblica |
| La griglia Documents dice che non hai permessi sulla posizione | Il tuo account SharePoint non ha accesso al sito o alla cartella: chiedi all'amministratore SharePoint (passo 4) |
| Accesso negato alla creazione della cartella | Non puoi scrivere nella raccolta: chiedi **Edit** sul sito |
| Card: "No document folder yet" | Nessuno ha aperto Documents sulla commessa: apri la commessa in ProjectIQ e seleziona **Related** → **Documents** |
| Card: "You have no access to the SharePoint folder of this project." | Come sopra: manca l'accesso SharePoint al sito |
| `document_metadata.py`: `Error: File Not Found.` | La raccolta non esiste sul sito: ripeti **Document Management Settings** selezionando la sua tabella ([Parte 2](#parte-2-configurazione-amministratori), passo 2), poi riesegui lo script |
| `document_metadata.py`: `A duplicate field name "…" was found.` | La raccolta ha una colonna con lo stesso id ma un altro nome interno, creata da una versione precedente dello script: se la colonna è vuota, eliminala dalle impostazioni della raccolta e riesegui lo script |
| Le colonne ProjectIQ di un file nuovo restano vuote | Il flusso della raccolta è disattivato oppure la sua esecuzione è fallita. Controlla la cronologia delle esecuzioni del flusso: la connessione di **op365_sharepoint** deve essere valida e il suo utente deve avere **Edit** sul sito |
