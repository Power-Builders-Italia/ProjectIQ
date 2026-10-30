# Dokumente in SharePoint

> **Sprache:** [English](../en/documents.md) · [Italiano](../it/documents.md) · [Français](../fr/documents.md) · Deutsch
> **Handbuchindex:** [README](../../README.md#user-manuals)

Verträge, Zeichnungen, Baufortschrittsberichte, Angebote und Lieferscheine gehören zu einem Projekt, aber nicht in die Datenbank. ProjectIQ legt sie in **SharePoint** ab, mit der Standard-Dokumentverwaltung von Dataverse: Jedes **Project**, jede **Purchase Order** und jedes **Supplier Document** erhält einen eigenen SharePoint-Ordner, der vom Datensatz aus geöffnet wird. Die Dateien behalten SharePoint-Versionierung, gemeinsames Bearbeiten in Office, Suche und Freigabe; ProjectIQ speichert nur, wo der Ordner liegt.

Dieses Handbuch richtet sich an alle, die mit Projektdokumenten arbeiten (Teil 1), und an die Administratoren, die ProjectIQ mit SharePoint verbinden (Teil 2).

## Funktionsweise

```mermaid
flowchart LR
    subgraph DV[ProjectIQ - Dataverse]
        P[Project<br/>Purchase Order<br/>Supplier Document] -->|Regarding| L[Document location<br/>Ordner des Datensatzes]
        L --> LL[Document location<br/>Bibliothek]
        LL --> S[SharePoint-Website]
    end
    subgraph SP[SharePoint-Website]
        LIB[Bibliothek op365_project<br/>op365_purchaseorder<br/>op365_supplierdocument] --> F[Ein Ordner pro Datensatz]
    end
    S -.-> LIB
    L -.-> F
    U[Benutzer in der App<br/>Related > Documents] --> F
    A[Portfolio Agent<br/>Projektdokumente] --> F
```

| Tabelle | SharePoint-Bibliothek | Ordner |
|---|---|---|
| Project | `op365_project` | Einer pro Projekt, benannt nach dem Projekt und seiner Id |
| Purchase Order | `op365_purchaseorder` | Einer pro Bestellung |
| Supplier Document | `op365_supplierdocument` | Einer pro Dokument (zum Beispiel der gescannte DURC mit seinen Anlagen) |

Der Ordner wird angelegt, wenn **zum ersten Mal jemand Documents** am Datensatz öffnet. Dataverse speichert einen *Dokumentspeicherort* (document location), der den Datensatz mit dem Ordner verknüpft; Agent und App finden den Ordner darüber. Ein in Copilot aus einem Dokument angelegtes Projekt hat seinen Ordner bereits, mit dem Dokument darin (siehe [Portfolio Agent](portfolio-agent.md#neues-projekt-aus-einem-dokument)).

## Teil 1: mit Dokumenten arbeiten

### Dokumente eines Datensatzes öffnen

1. Öffnen Sie das Projekt (oder die Bestellung oder das Lieferantendokument).
2. Wählen Sie **Related** → **Documents**. Beim ersten Mal legt ProjectIQ den SharePoint-Ordner des Datensatzes an.
3. Das Raster listet die Dateien des Ordners: **Upload**, **New** (Word, Excel, PowerPoint, OneNote), **Open in SharePoint**, **Delete**, **Check Out** / **Check In** und **Edit Properties** arbeiten direkt in SharePoint.

| Befehl | Wirkung |
|---|---|
| **Upload** | Lädt eine oder mehrere Dateien in den Ordner (oder einen Unterordner) hoch |
| **New** | Legt ein Office-Dokument im Ordner an und öffnet es im Browser |
| **Open Location** / **Open in SharePoint** | Öffnet den Ordner in SharePoint, für Unterordner, Freigabe, Versionen und Massenverschiebungen |
| **Document Location** → **Add Location** | Verknüpft einen weiteren vorhandenen SharePoint-Ordner mit dem Datensatz (zum Beispiel einen Ordner eines Teams-Teams) |

### Wer welche Dateien sieht

- Für die Registerkarte **Documents** brauchen Sie die ProjectIQ-Rolle (siehe [Administration](administration.md#sicherheitsrollen)): **OP365 User** kann den Ordner der Datensätze anlegen, die er öffnen kann, und alle Dokumentspeicherorte lesen.
- **Welche Dateien Sie sehen, entscheiden die SharePoint-Berechtigungen.** ProjectIQ überträgt die Freigabe seiner Projekte nicht nach SharePoint: Geben Sie dem Projektteam in SharePoint Zugriff auf die Website (oder eine Bibliothek oder einen Ordner).

### Dokumente in Copilot

Fragen Sie im [Portfolio Agent](portfolio-agent.md#projektdokumente) „zeige die Dokumente von PRJ-000123“: Die Karte listet die Dateien und Unterordner des Projektordners, neueste zuerst, mit einem Link zu jeder Datei und zum Ordner.

### Lieferantendokumente

Ein **Supplier Document** (DURC, Zertifizierung, Versicherung) behält seine Spalte **File**, die das [Lieferantenportal](supplier-portal.md) nutzt. Der SharePoint-Ordner des Datensatzes ist für die übrigen zugehörigen Dateien (Erneuerungen, Korrespondenz). Ablaufdaten und Lieferanten-Compliance beruhen wie bisher auf den Feldern des Supplier Document.

## Teil 2: Einrichtung (Administratoren)

Einmal pro Umgebung, durch den Power-Platform-Administrator gemeinsam mit einem SharePoint-Administrator.

```mermaid
flowchart TD
    A[1. SharePoint-Website für die Dokumente<br/>z. B. /sites/ProjectIQDocuments] --> B[2. Website in ProjectIQ registrieren<br/>Document Management Settings]
    B --> C[3. Bibliotheken für<br/>Project, Purchase Order, Supplier Document angelegt]
    C --> D[4. Dem Projektteam<br/>Zugriff auf die Website geben]
    D --> E[5. Benutzer öffnen Related > Documents]
```

| Schritt | Wer | Was |
|---|---|---|
| 1 | SharePoint-Administrator | Legen Sie eine SharePoint-Team- oder Kommunikationswebsite für die Dokumente an, im selben Microsoft-365-Tenant wie die Umgebung |
| 2 | Power-Platform-Administrator | Öffnen Sie in der App **Settings** (Zahnrad) → **Advanced Settings** → **Document Management** → **Document Management Settings**, wählen Sie **Project**, **Purchase Order** und **Supplier Document**, geben Sie die URL der Website ein, wählen Sie **Next** und **Finish**. Die Bibliotheken werden auf der Website angelegt |
| 3 | Power-Platform-Administrator | Alternative zu Schritt 2 für skriptgesteuerte Umgebungen: `SHAREPOINT_SITE_URL=<URL der Website> python3 tools/dataverse/documents.py` registriert die Website als Standardwebsite; die Bibliotheken werden angelegt, wenn der erste Datensatz jeder Tabelle Documents öffnet |
| 4 | SharePoint-Administrator | Geben Sie den Personen, die ProjectIQ nutzen, mindestens **Edit** (oder **Read**) auf der Website |
| 5 | Jeder Benutzer | Öffnen Sie **Related** → **Documents** an einem Datensatz |

Die serverbasierte SharePoint-Integration ist in Dataverse online standardmäßig aktiv; meldet **Document Management Settings**, dass sie deaktiviert ist, aktivieren Sie sie unter **Advanced Settings** → **Document Management** → **Enable Server-Based SharePoint Integration**.

Die Dokumentverwaltung der drei Tabellen sowie die Berechtigungen für Dokumentspeicherorte und SharePoint-Website der Rollen **OP365 User** und **OP365 Administrator** sind Teil der ProjectIQ-Lösung: Ein Update der Lösung bringt sie mit. Die SharePoint-Website ist eine Einstellung jeder Umgebung und nicht Teil der Lösung.

## Mögliche Meldungen

| Meldung | Bedeutung und Lösung |
|---|---|
| Kein **Documents** unter **Related**, oder eine Meldung, dass die Dokumentverwaltung nicht konfiguriert ist | Die Website ist nicht registriert: siehe [Teil 2](#teil-2-einrichtung-administratoren), Schritt 2 |
| Das Documents-Raster meldet fehlende Berechtigungen für den Speicherort | Ihr SharePoint-Konto hat keinen Zugriff auf die Website oder den Ordner: wenden Sie sich an den SharePoint-Administrator (Schritt 4) |
| Zugriff verweigert beim Anlegen des Ordners | Sie können nicht in die Bibliothek schreiben: fordern Sie **Edit** auf der Website an |
| Karte: "No document folder yet" | Niemand hat Documents am Projekt geöffnet: öffnen Sie das Projekt in ProjectIQ und wählen Sie **Related** → **Documents** |
| Karte: "You have no access to the SharePoint folder of this project." | Wie oben: der SharePoint-Zugriff auf die Website fehlt |
