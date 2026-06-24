# aumann-eco.de — WordPress bearbeiten (auch vom Zweit-Laptop)

Die Live-Seite **aumann-eco.de** läuft auf WordPress. Dieses Verzeichnis macht das
Bearbeiten von **jedem Rechner** reproduzierbar — ohne den alten, nur lokal
existierenden Setup-Kram und **ohne Gefahr, WP-Änderungen zu überschreiben**.

## Wichtig: zwei verschiedene Quellen

| Ort | Was | Maßgeblich für |
|---|---|---|
| `wp-live-export/*.raw.html` | 1:1-Spiegel des **echten WordPress-Inhalts** (`content.raw`) | **Alles, was live ist** — Rechtstexte, Link-Umbiegungen, E-Mails, Slugs |
| `<ordner>/index.html` (z. B. `bauphysik/index.html`) | die **Original-Designquellen** (statische Vercel-Seiten) | Nur das ursprüngliche Design; **kann hinter WP zurückliegen** |

➡️ Für WP-Änderungen ist **`wp-live-export/` die Wahrheit**, nicht die alten `index.html`.

## Erstmaliges Setup auf einem neuen Laptop

```bash
# 1. Repo klonen (NICHT in iCloud/Documents ablegen — sonst hängt git)
git clone https://github.com/ostend-digital/aumann-eco-preview.git
cd aumann-eco-preview

# 2. Zugangsdaten anlegen (wird NICHT committet)
cp wp-tools/.env.example wp-tools/.env
#    dann wp-tools/.env öffnen und WP_USER + WP_APP_PW eintragen.
#    App-Passwort: aumann-eco.de/wp-admin -> Benutzer -> Profil -> Anwendungspasswörter
```

Voraussetzung: nur **Python 3** (Standardbibliothek reicht, keine Pakete nötig).

## Der sichere Arbeitsablauf — IMMER in dieser Reihenfolge

```bash
# A) Aktuellen Live-Stand holen (überschreibt wp-live-export/ mit dem, was online ist)
python3 wp-tools/wp-sync.py pull

# B) Prüfen, ob lokal == live (sollte direkt nach pull "synchron" sagen)
python3 wp-tools/wp-sync.py diff

# C) Jetzt die gewünschte Seite bearbeiten, z. B.:
#    wp-live-export/19-bauphysik.raw.html

# D) Nochmal diff: zeigt genau die Seite(n), die du geändert hast
python3 wp-tools/wp-sync.py diff

# E) Genau diese eine Seite zurückschreiben (fragt nach Bestätigung "JA")
python3 wp-tools/wp-sync.py push 19
```

> **Goldene Regel:** vor jedem `push` ein frisches `pull`/`diff`. Dann kann nichts
> überschrieben werden, was jemand anderes (oder du am anderen Laptop) in WP geändert hat.
> `push` lässt den Veröffentlichungs-Status unangetastet (publish bleibt publish, draft bleibt draft).

## Seiten-Übersicht (Stand Launch 22.06.2026)

| id | slug | status |
|---|---|---|
| 8 | energieberatung-koeln (Startseite) | publish |
| 15 | sanierungsfahrplan | publish |
| 19 | bauphysik | publish |
| 21 | blower-door | publish |
| 23 | foerderberatung | publish |
| 25 | ueber-uns | publish |
| 27 | karriere-vollversion | **draft** |
| 30 | kontakt | publish |
| 40 | impressum | publish |
| 41 | datenschutz | publish |
| 42 | agb | publish |
| 43 | cookie-einstellungen | publish |
| 89 | karriere (schlanke Live-Version) | publish |

`list` zeigt den aktuellen Stand jederzeit: `python3 wp-tools/wp-sync.py list`

## Hinweise / Grenzen

- **Bilder/Assets:** Viele Seiten laden Fonts/Bilder noch von
  `aumann-eco-preview.vercel.app`; einige Fotos liegen in der WP-Mediathek. Das Skript
  fasst Inhalte (Text/HTML) an, **nicht** Medien-Uploads. Neue Bilder weiterhin über
  WP-Admin → Mediathek hochladen.
- **Yoast SEO** (Title/Meta/Focus-KW) ist über die REST-API nicht schreibbar →
  immer direkt im WP-Admin im Yoast-Feld pflegen.
- **Kleine Textänderungen** gehen am schnellsten direkt im **WP-Admin** (Browser, jeder
  Rechner). Dieses Tool ist für größere/strukturierte Edits gedacht, die man versioniert
  haben will.
- **App-Passwort widerrufen:** jederzeit unter wp-admin → Profil → Anwendungspasswörter.
