#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lukee scripts/siemendata.txt ja kirjoittaa siita sivun datatiedoston, jotta
sivulla on nayttettavaa ennen kuin Torneopal-API-avaimet ovat kaytossa.

    python scripts/siemenna.py

Kun paivita.py ajetaan oikealla avaimella, nama rivit korvautuvat rajapinnan
omalla datalla - siementen "lahde" on sama kuin oikean haun, joten ne
poistuvat automaattisesti.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import paivita  # noqa: E402  - sama hakemisto

SIEMEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "siemendata.txt")

# Siemendata koskee vain salibandya Kisariihessa.
LAHDE = "salibandy"
LAJI = "Salibandy"
PAIKKA = "Kisariihi"
PAIKKA_TARKENNE = "Kisariihi Pöytyä"
LINKKI = "https://tulospalvelu.salibandy.fi/location/734827322/fixtures"


def lue_siemenet():
    ottelut, pvm, numero = [], None, 0
    with open(SIEMEN, encoding="utf-8") as tiedosto:
        for rivi in tiedosto:
            rivi = rivi.strip()
            if not rivi:
                continue
            if rivi.startswith("#"):
                if rivi.startswith("# pvm "):
                    pvm = rivi[len("# pvm "):].strip()
                continue
            osat = [o.strip() for o in rivi.split("|")]
            if len(osat) != 4 or pvm is None:
                raise ValueError("virheellinen rivi: " + rivi)
            sarja, koti, klo, vieras = osat
            numero += 1
            ottelut.append({
                "id": "%s-siemen-%03d" % (LAHDE, numero),
                "laji": LAJI,
                "paikka": PAIKKA,
                "paikka_tarkenne": PAIKKA_TARKENNE,
                "pvm": pvm,
                "klo": klo,
                "sarja": sarja,
                "koti": koti,
                "vieras": vieras,
                "koti_seura": "",
                "vieras_seura": "",
                "linkki": LINKKI,
                "lahde": LAHDE,
                "alustava": True,
            })
    return ottelut


def main():
    config = paivita.lue_config()
    ottelut = lue_siemenet()
    for ottelu in ottelut:
        ottelu["seurat"] = paivita.tunnista_seurat(ottelu, config["seurat"])
        ottelu["kesto"] = paivita.KESTO.get(LAJI, paivita.KESTO_OLETUS)
    ottelut = paivita.jarjesta(paivita.tulevat(ottelut))

    paivita.kirjoita_data({
        "paivitetty": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lahteet_haettu": [],
        "huomiot": ["Alustava siemendata, luettu tulospalvelusta 20.9.2026. "
                    "Korvautuu automaattisesti, kun API-avaimet on otettu kayttoon."],
        "ottelut": ottelut,
    })
    for tiedosto, maara in paivita.rakenna_kalenterit(config, ottelut):
        print("  %-22s %3d ottelua" % (tiedosto, maara))
    print("Valmis: %d ottelua siemendatasta." % len(ottelut))
    return 0


if __name__ == "__main__":
    sys.exit(main())
