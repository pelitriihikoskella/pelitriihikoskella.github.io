#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kokoaa lyhyen tekstin PoKan ja PoUn tulevista peleista.
Tekstia kaytetaan Facebook-postauksessa ja paivittaisessa muistutuksessa.

    python scripts/kooste.py --tila viikko    # taman viikon ohjelma
    python scripts/kooste.py --tila tanaan    # tanaan pelattavat ottelut
    python scripts/kooste.py --paivat 5       # seuraavat 5 paivaa

Jos otteluita ei ole, teksti on tyhja ja paluuarvo 1. Nain ajastettu tyo voi
ohittaa julkaisun sen sijaan, etta lahettaisi "ei peleja" -viestin.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import paivita  # noqa: E402

# Windowsin konsoli on oletuksena cp1252 eika osaa emojeja.
for virta in (sys.stdout, sys.stderr):
    if hasattr(virta, "reconfigure"):
        virta.reconfigure(encoding="utf-8", errors="replace")

VIIKONPAIVAT = ["Ma", "Ti", "Ke", "To", "Pe", "La", "Su"]
MERKIT = {"Jalkapallo": "⚽", "Futsal": "⚽", "Salibandy": "\U0001f3d1"}


def jakso(tila, paivat, tanaan):
    """Palauttaa (alkupaiva, loppupaiva, otsikko) valitun tilan mukaan."""
    if tila == "viikko":
        return tanaan, tanaan + timedelta(days=6), "Tämän viikon pelit Riihikoskella"
    if tila == "tanaan":
        return tanaan, tanaan, "Tänään Riihikoskella"
    return (tanaan, tanaan + timedelta(days=paivat - 1),
            "Pelit Riihikoskella – seuraavat %d päivää" % paivat)


def muotoile_paiva(pvm, tanaan):
    paiva = datetime.strptime(pvm, "%Y-%m-%d").date()
    nimi = VIIKONPAIVAT[paiva.weekday()] + " %d.%d." % (paiva.day, paiva.month)
    if paiva == tanaan:
        return nimi + " (tänään)"
    if paiva == tanaan + timedelta(days=1):
        return nimi + " (huomenna)"
    return nimi


def otteluteksti(ottelu):
    merkki = MERKIT.get(ottelu["laji"], "")
    paikka = ("Urheilukenttä" if ottelu["paikka"] == "Riihikosken urheilupuisto"
              else ottelu["paikka"])
    return "%s %s  %s – %s  (%s, %s)" % (
        merkki, ottelu["klo"], ottelu["koti"], ottelu["vieras"],
        ottelu["sarja"] or ottelu["laji"], paikka)


def kooste(ottelut, seurat, tila, paivat, osoite, tanaan=None, alustavat=False):
    tanaan = tanaan or datetime.now().date()
    alku, loppu, otsikko = jakso(tila, paivat, tanaan)

    valitut = [o for o in ottelut
               if any(s in (o.get("seurat") or []) for s in seurat)
               and alku.isoformat() <= o["pvm"] <= loppu.isoformat()
               # Käsin poimittu siemendata ei mene ulos sivulta: julkaistussa
               # postauksessa ei ole sitä varoitusta, joka sivulla on.
               and (alustavat or not o.get("alustava"))]
    if not valitut:
        return ""

    rivit = [otsikko, ""]
    nykyinen = None
    for ottelu in paivita.jarjesta(valitut):
        # Yhden paivan koosteessa paivaotsikko olisi turha toisto.
        if alku != loppu and ottelu["pvm"] != nykyinen:
            nykyinen = ottelu["pvm"]
            if rivit[-1] != "":
                rivit.append("")
            rivit.append(muotoile_paiva(nykyinen, tanaan))
        rivit.append(otteluteksti(ottelu))

    if osoite:
        rivit += ["", "Koko ohjelma ja kalenteri puhelimeen: " + osoite]
    return "\n".join(rivit)


def main():
    jasennin = argparse.ArgumentParser(description="Kokoa tulevien pelien teksti")
    jasennin.add_argument("--tila", choices=["viikko", "tanaan", "paivat"],
                          default="paivat", help="koosteen jakso (oletus paivat)")
    jasennin.add_argument("--paivat", type=int, default=5,
                          help="montako päivää eteenpäin, kun tila on paivat")
    jasennin.add_argument("--seurat", default="poka,pou",
                          help="seurojen tunnukset pilkulla eroteltuna")
    jasennin.add_argument("--tiedosto", help="kirjoita teksti myös tiedostoon")
    jasennin.add_argument("--salli-alustavat", action="store_true",
                          help="ota mukaan myös käsin poimittu siemendata")
    argumentit = jasennin.parse_args()

    config = paivita.lue_config()
    data = paivita.lue_data()
    seurat = [s.strip() for s in argumentit.seurat.split(",") if s.strip()]
    osoite = config.get("sivu", {}).get("julkinen_osoite", "")
    if "KAYTTAJATUNNUS" in osoite:      # osoitetta ei ole vielä asetettu
        osoite = ""

    teksti = kooste(data.get("ottelut", []), seurat, argumentit.tila,
                    argumentit.paivat, osoite,
                    alustavat=argumentit.salli_alustavat)

    if argumentit.tiedosto:
        with open(argumentit.tiedosto, "w", encoding="utf-8") as tiedosto:
            tiedosto.write(teksti + ("\n" if teksti else ""))

    if not teksti:
        print("Ei julkaistavaa (tila: %s)." % argumentit.tila, file=sys.stderr)
        return 1

    print(teksti)
    return 0


if __name__ == "__main__":
    sys.exit(main())
