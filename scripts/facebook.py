#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Julkaisee koosteen Facebook-SIVULLE (Page) Graph APIn kautta.

    python scripts/facebook.py --tiedosto kooste.txt
    python scripts/facebook.py --tiedosto kooste.txt --kuivaharjoitus

Ymparistomuuttujat:
    FB_PAGE_ID        sivun tunniste
    FB_PAGE_TOKEN     sivun pitkaikainen kayttooikeustunnus
    FB_GRAPH_VERSIO   valinnainen, oletus v26.0

Jos tunnuksia ei ole asetettu, skripti ilmoittaa siita ja lopettaa
onnistuneesti - nain ajastettu tyo ei kaadu ennen kuin Facebook on kytketty.

HUOM: Facebook-RYHMAAN ei voi julkaista rajapinnan kautta. Meta poisti
Groups APIn ja publish_to_groups-oikeuden huhtikuussa 2024. Sivun postauksen
voi jakaa ryhmaan kasin yhdella napautuksella.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

for virta in (sys.stdout, sys.stderr):
    if hasattr(virta, "reconfigure"):
        virta.reconfigure(encoding="utf-8", errors="replace")

OLETUSVERSIO = "v26.0"


def julkaise(sivu_id, tunnus, versio, viesti):
    url = "https://graph.facebook.com/%s/%s/feed" % (versio, sivu_id)
    data = urllib.parse.urlencode({
        "message": viesti,
        "access_token": tunnus,
    }).encode("utf-8")
    pyynto = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(pyynto, timeout=30) as vastaus:
            return json.loads(vastaus.read().decode("utf-8"))
    except urllib.error.HTTPError as virhe:
        runko = virhe.read().decode("utf-8", errors="replace")
        raise RuntimeError("Facebook vastasi %s: %s" % (virhe.code, runko[:400]))


def tarkista(sivu_id, tunnus, versio):
    """Lukee sivun nimen. Todentaa etta tunnus kelpaa ja osoittaa oikeaan
    sivuun - julkaisematta mitaan."""
    url = ("https://graph.facebook.com/%s/%s?fields=id,name&access_token=%s"
           % (versio, sivu_id, urllib.parse.quote(tunnus)))
    try:
        with urllib.request.urlopen(url, timeout=30) as vastaus:
            return json.loads(vastaus.read().decode("utf-8"))
    except urllib.error.HTTPError as virhe:
        runko = virhe.read().decode("utf-8", errors="replace")
        raise RuntimeError("Facebook vastasi %s: %s" % (virhe.code, runko[:400]))


def main():
    jasennin = argparse.ArgumentParser(description="Julkaise kooste Facebook-sivulle")
    jasennin.add_argument("--tiedosto",
                          help="tiedosto, jossa julkaistava teksti")
    jasennin.add_argument("--tarkista", action="store_true",
                          help="tarkista vain että tunnus toimii, älä julkaise")
    jasennin.add_argument("--kuivaharjoitus", action="store_true",
                          help="näytä mitä julkaistaisiin, älä lähetä")
    argumentit = jasennin.parse_args()

    sivu_id = os.environ.get("FB_PAGE_ID", "").strip()
    tunnus = os.environ.get("FB_PAGE_TOKEN", "").strip()
    versio = os.environ.get("FB_GRAPH_VERSIO", "").strip() or OLETUSVERSIO

    if argumentit.tarkista:
        if not (sivu_id and tunnus):
            print("FB_PAGE_ID tai FB_PAGE_TOKEN puuttuu - yhteyttä ei voi "
                  "tarkistaa.", file=sys.stderr)
            return 1
        try:
            vastaus = tarkista(sivu_id, tunnus, versio)
        except Exception as virhe:
            print("Facebook-yhteys EI toimi: %s" % virhe, file=sys.stderr)
            return 1
        print("Facebook-yhteys toimii. Sivu: %s (%s)"
              % (vastaus.get("name", "?"), vastaus.get("id", "?")))
        return 0

    if not argumentit.tiedosto:
        print("Anna --tiedosto tai --tarkista.", file=sys.stderr)
        return 1

    with open(argumentit.tiedosto, encoding="utf-8") as tiedosto:
        viesti = tiedosto.read().strip()
    if not viesti:
        print("Tyhjä teksti, ei julkaista.", file=sys.stderr)
        return 0

    if argumentit.kuivaharjoitus or not (sivu_id and tunnus):
        if not (sivu_id and tunnus) and not argumentit.kuivaharjoitus:
            print("FB_PAGE_ID tai FB_PAGE_TOKEN puuttuu - Facebook-julkaisu "
                  "ohitettiin.", file=sys.stderr)
        print("--- julkaistava teksti ---")
        print(viesti)
        return 0

    try:
        vastaus = julkaise(sivu_id, tunnus, versio, viesti)
    except Exception as virhe:
        print("Julkaisu epäonnistui: %s" % virhe, file=sys.stderr)
        return 1

    print("Julkaistu Facebook-sivulle, postauksen tunniste: %s"
          % vastaus.get("id", "?"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
