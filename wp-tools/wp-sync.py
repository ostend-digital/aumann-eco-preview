#!/usr/bin/env python3
"""
wp-sync.py — aumann-eco.de WordPress <-> Git-Repo Sync (App-Password / Basic Auth).

Zweck: NIE wieder versehentlich WP-only-Verfeinerungen ueberschreiben.
Arbeitsweise immer: ERST `pull` -> dann lokal aendern -> dann `push`.

Zugangsdaten:
  Aus wp-tools/.env (gitignored) oder Umgebungsvariablen WP_USER / WP_APP_PW.
  .env-Format (eine Zeile je Var):
      WP_USER=ostend
      WP_APP_PW=xxxx xxxx xxxx xxxx xxxx xxxx   (Leerzeichen sind ok)

Befehle:
  python3 wp-tools/wp-sync.py pull
      Holt content.raw ALLER Seiten -> wp-live-export/<id>-<slug>.raw.html
      + _index.raw.json. Das ist die autoritative WP-Spiegelung.

  python3 wp-tools/wp-sync.py list
      Listet alle Seiten (id, status, slug, modified) ohne zu schreiben.

  python3 wp-tools/wp-sync.py diff
      Zeigt, welche wp-live-export/*.raw.html lokal vom Live-WP abweichen
      (ohne etwas zu aendern) — der Pflicht-Check VOR jedem push.

  python3 wp-tools/wp-sync.py push <id> [datei]
      Schreibt eine Seite zurueck nach WP (status bleibt unveraendert).
      datei default = wp-live-export/<id>-<slug>.raw.html
      Fragt vorher nach Bestaetigung und warnt, wenn Live-WP neuer ist
      als der lokale Stand (Schutz gegen Ueberschreiben).
"""
import sys, os, json, base64, urllib.request, urllib.error, hashlib

SITE = "https://aumann-eco.de"
API = SITE + "/wp-json/wp/v2/pages"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "wp-live-export")
STATUSES = "publish,draft,private,pending"
FIELDS = "id,slug,status,title,modified,modified_gmt,link,content,template"


def creds():
    user = os.environ.get("WP_USER")
    pw = os.environ.get("WP_APP_PW")
    env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if (not user or not pw) and os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "WP_USER" and not user:
                user = v.strip()
            if k.strip() == "WP_APP_PW" and not pw:
                pw = v.strip()
    if not user or not pw:
        sys.exit("FEHLER: WP_USER / WP_APP_PW fehlen (wp-tools/.env anlegen).")
    return user, pw


def auth_header():
    user, pw = creds()
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def api(url, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": auth_header(),
        "User-Agent": "ae-wp-sync",
        "Content-Type": "application/json",
    })
    try:
        return json.load(urllib.request.urlopen(r, timeout=90))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")


def fetch_all():
    return sorted(api(f"{API}?context=edit&per_page=100&status={STATUSES}&_fields={FIELDS}"),
                  key=lambda x: x["id"])


def fname(p):
    return os.path.join(EXPORT, f"{p['id']}-{p['slug']}.raw.html")


def cmd_list():
    for p in fetch_all():
        print(f"  {p['id']:>3} {p['status']:<7} {p['slug']:<24} mod {p['modified']}")


def cmd_pull():
    os.makedirs(EXPORT, exist_ok=True)
    pages = fetch_all()
    idx = []
    for p in pages:
        raw = p["content"]["raw"]
        open(fname(p), "w").write(raw)
        idx.append({"id": p["id"], "slug": p["slug"], "status": p["status"],
                    "title": p["title"]["raw"], "template": p.get("template", ""),
                    "modified": p["modified"], "modified_gmt": p.get("modified_gmt", ""),
                    "link": p["link"], "file": os.path.basename(fname(p)),
                    "bytes": len(raw)})
    json.dump(idx, open(os.path.join(EXPORT, "_index.raw.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"PULL ok: {len(idx)} Seiten -> {EXPORT}")
    for i in idx:
        print(f"  {i['id']:>3} {i['status']:<7} {i['slug']:<24} {i['bytes']:>7} B")


def cmd_diff():
    pages = fetch_all()
    any_diff = False
    for p in pages:
        f = fname(p)
        live = p["content"]["raw"]
        if not os.path.exists(f):
            print(f"  NEU-LIVE   {p['id']:>3} {p['slug']}  (lokal nicht vorhanden -> erst pull)")
            any_diff = True
            continue
        local = open(f).read()
        if hashlib.sha1(local.encode()).hexdigest() != hashlib.sha1(live.encode()).hexdigest():
            print(f"  ABWEICHUNG {p['id']:>3} {p['slug']}  (lokal {len(local)} B vs live {len(live)} B)")
            any_diff = True
    # local files without live match
    if not any_diff:
        print("  Alles synchron: lokal == Live-WP.")


def cmd_push(args):
    if not args:
        sys.exit("Nutzung: push <id> [datei]")
    pid = int(args[0])
    pages = {p["id"]: p for p in fetch_all()}
    if pid not in pages:
        sys.exit(f"Seite id {pid} existiert nicht in WP.")
    live = pages[pid]
    f = args[1] if len(args) > 1 else fname(live)
    if not os.path.exists(f):
        sys.exit(f"Datei nicht gefunden: {f}")
    new = open(f).read()
    live_raw = live["content"]["raw"]
    if hashlib.sha1(new.encode()).hexdigest() == hashlib.sha1(live_raw.encode()).hexdigest():
        print("Keine Aenderung gegenueber Live-WP — nichts zu tun.")
        return
    # Schutz: warnen, wenn Live-WP von der zuletzt gezogenen Basis abweicht
    print(f"PUSH-Vorschau  id={pid}  slug={live['slug']}  status={live['status']}")
    print(f"  lokal {len(new)} B  ->  Live {len(live_raw)} B   (Live zuletzt geaendert: {live['modified']})")
    print("  WICHTIG: Hast du vorher 'pull'/'diff' gemacht? Sonst koenntest du WP-Aenderungen ueberschreiben.")
    if input("  Wirklich pushen? [tippe JA]: ").strip() != "JA":
        print("Abgebrochen.")
        return
    api(f"{API}/{pid}", method="POST", payload={"content": new})
    print(f"PUSH ok: Seite {pid} aktualisiert (status unveraendert: {live['status']}).")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    c = sys.argv[1]
    if c == "pull":
        cmd_pull()
    elif c == "list":
        cmd_list()
    elif c == "diff":
        cmd_diff()
    elif c == "push":
        cmd_push(sys.argv[2:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
