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

### Documenti in Copilot

Nel [Portfolio Agent](portfolio-agent.md#documenti-di-commessa) chiedi "mostra i documenti della commessa PRJ-000123": la card elenca file e sottocartelle della cartella della commessa, dai più recenti, con il link a ogni file e alla cartella.

### Documenti fornitore

Un **Supplier Document** (DURC, certificazione, assicurazione) mantiene la colonna **File**, usata dal [portale fornitori](supplier-portal.md). La cartella SharePoint del record serve per gli altri file che lo accompagnano (rinnovi, corrispondenza). Scadenze e conformità fornitori continuano a basarsi sui campi del Supplier Document come prima.

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
| 2 | Amministratore Power Platform | Nell'app apri **Settings** (ingranaggio) → **Advanced Settings** → **Document Management** → **Document Management Settings**, seleziona **Project**, **Purchase Order** e **Supplier Document**, inserisci l'URL del sito, seleziona **Next** e **Finish**. Le raccolte vengono create sul sito |
| 3 | Amministratore Power Platform | Alternativa al passo 2 per ambienti gestiti da script: `SHAREPOINT_SITE_URL=<URL del sito> python3 tools/dataverse/documents.py` registra il sito come sito predefinito; le raccolte vengono create quando il primo record di ogni tabella apre Documents |
| 4 | Amministratore SharePoint | Dai alle persone che usano ProjectIQ almeno **Edit** (o **Read**) sul sito |
| 5 | Ogni utente | Apri **Related** → **Documents** su un record |

L'integrazione SharePoint server-based è attiva per impostazione predefinita in Dataverse online; se **Document Management Settings** segnala che è disattivata, attivala da **Advanced Settings** → **Document Management** → **Enable Server-Based SharePoint Integration**.

La gestione documentale sulle tre tabelle e i privilegi su document location e sito SharePoint dei ruoli **OP365 User** e **OP365 Administrator** fanno parte della soluzione ProjectIQ: un aggiornamento della soluzione li porta. Il sito SharePoint è un'impostazione di ogni ambiente e non è nella soluzione.

## Messaggi che potresti vedere

| Messaggio | Significato e soluzione |
|---|---|
| Nessun **Documents** sotto **Related**, o un messaggio che la gestione documentale non è configurata | Il sito non è registrato (vedi [Parte 2](#parte-2-configurazione-amministratori), passo 2), oppure l'app ProjectIQ non contiene le tabelle **SharePoint Document** e **Document Location**: esegui `tools/dataverse/app.py` o aggiungi le tabelle nel designer dell'app e pubblica |
| La griglia Documents dice che non hai permessi sulla posizione | Il tuo account SharePoint non ha accesso al sito o alla cartella: chiedi all'amministratore SharePoint (passo 4) |
| Accesso negato alla creazione della cartella | Non puoi scrivere nella raccolta: chiedi **Edit** sul sito |
| Card: "No document folder yet" | Nessuno ha aperto Documents sulla commessa: apri la commessa in ProjectIQ e seleziona **Related** → **Documents** |
| Card: "You have no access to the SharePoint folder of this project." | Come sopra: manca l'accesso SharePoint al sito |
