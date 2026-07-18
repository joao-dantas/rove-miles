#!/usr/bin/env python3
"""
Baixa TODAS as lojas do portal de shopping da Rove (api-v2.rove.com).

Detalhe importante: a API pagina com `page` COMECANDO EM 0 (page=0 e a
primeira pagina). Comecar em page=1 pula as ~1000 primeiras lojas.

Uso:
    export ROVE_TOKEN='<Bearer token, sem a palavra Bearer>'
    python3 rove_scrape.py

Gera:
    rove_stores.json  -> lista completa, todos os campos crus da API
    rove_stores.csv   -> resumo (id, nome, milhas, url, categorias, ...)

O token expira em ~1h. Se der 401, pegue outro no DevTools:
    rove.com/shopping -> Network -> requisicao "stores" -> header Authorization.
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "https://api-v2.rove.com/api/v1/shopping/stores"
PAGE_SIZE = 1000
TOKEN = os.environ.get("ROVE_TOKEN", "").strip()

if not TOKEN:
    sys.exit("Defina ROVE_TOKEN com o Bearer token (veja o cabecalho do arquivo).")

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "authorization": f"Bearer {TOKEN}",
    "origin": "https://www.rove.com",
    "referer": "https://www.rove.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "x-rove-client": "web",
}


def fetch(page):
    url = f"{BASE}?page={page}&size={PAGE_SIZE}&name="
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)["data"]
        except urllib.error.HTTPError as e:
            if e.code == 401:
                sys.exit("401: token expirado. Pegue um novo e rode de novo.")
            print(f"  HTTP {e.code} pagina {page}, tentativa {attempt+1}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"  erro {e} pagina {page}, tentativa {attempt+1}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    sys.exit(f"Falha ao buscar a pagina {page}.")


def main():
    stores = {}
    first = fetch(0)                      # <-- pagina 0 e a primeira!
    total = first["total_elements"]
    pages = first["total_pages"]
    print(f"Total informado pela API: {total} lojas em {pages} paginas (0..{pages-1})")

    for s in first["content"]:
        stores[s["id"]] = s
    print(f"  pagina 0 -> {len(first['content'])} (unico {len(stores)})")

    for p in range(1, pages):
        data = fetch(p)
        for s in data["content"]:
            stores[s["id"]] = s
        print(f"  pagina {p} -> {len(data['content'])} (unico {len(stores)})")
        time.sleep(0.25)

    all_stores = sorted(stores.values(), key=lambda s: s["name"].lower())

    with open("rove_stores.json", "w", encoding="utf-8") as f:
        json.dump(all_stores, f, ensure_ascii=False, indent=2)

    with open("rove_stores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "miles_multiplier", "url", "categories",
                    "type", "home", "description"])
        for s in all_stores:
            mult = (s.get("commission") or {}).get("multiplier", "")
            w.writerow([
                s["id"], s["name"], mult, s.get("url", ""),
                "|".join(s.get("categories") or []),
                s.get("type", ""), s.get("home", ""),
                (s.get("description") or "").replace("\n", " ").strip(),
            ])

    print(f"\nPronto: {len(all_stores)} lojas unicas "
          f"(API dizia {total}) -> rove_stores.json e rove_stores.csv")


if __name__ == "__main__":
    main()
