#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hakee Riihikosken urheilukentän ja Kisariihen tulevat pelit Torneopal-rajapinnasta
ja kirjoittaa niistä sivun datatiedoston sekä kalenteritiedostot (.ics).

Ajo:
    python scripts/paivita.py                   # hae rajapinnasta ja rakenna kaikki
    python scripts/paivita.py --vain-kalenteri  # rakenna .ics olemassa olevasta datasta
    python scripts/paivita.py --testi           # kokeile rajapintaa, älä kirjoita mitään

API-avaimet annetaan ympäristömuuttujina (ks. config.json -> avain_ymparistomuuttuja):
    SPL_API_KEY         jalkapallo ja futsal
    SALIBANDY_API_KEY   salibandy

Ilman avainta lähde ohitetaan ja sen vanha data säilytetään.
Riippuvuuksia ei ole - pelkkä Pythonin vakiokirjasto.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

JUURI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(JUURI, "config.json")
DATA = os.path.join(JUURI, "docs", "data", "pelit.json")
KALENTERIT = os.path.join(JUURI, "docs", "kalenteri")

# Ottelun oletuskesto minuuteissa lajeittain (kalenterimerkinnan pituus).
KESTO = {"Jalkapallo": 120, "Futsal": 90, "Salibandy": 90}
KESTO_OLETUS = 90


# --------------------------------------------------------------------------
# Rajapintakutsut
# --------------------------------------------------------------------------

def hae_json(api, polku, params, avain, aikakatkaisu=30):
    """Yksi kutsu Torneopal-rajapintaan. Avain menee seka Accept-otsakkeessa etta
    api_key-parametrina - eri liittojen asennukset odottavat eri tapaa."""
    kysely = dict(params)
    kysely["api_key"] = avain
    url = api.rstrip("/") + "/" + polku + "?" + urllib.parse.urlencode(kysely)
    pyynto = urllib.request.Request(url, headers={
        "Accept": "json/" + avain,
        "User-Agent": "riihikoski-pelit/1.0",
    })
    with urllib.request.urlopen(pyynto, timeout=aikakatkaisu) as vastaus:
        raaka = vastaus.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raaka)
    except json.JSONDecodeError:
        raise RuntimeError("rajapinta ei palauttanut JSONia: " + raaka[:200])


def paikkavaihtoehdot(params):
    """Sama kysely molemmilla paikkaparametrin nimilla - eri liittojen
    Torneopal-asennukset nimeavat kentan eri tavalla."""
    vaihtoehdot = [dict(params)]
    for nimi, toinen in (("location_id", "venue_id"), ("venue_id", "location_id")):
        if nimi in params:
            vaihto = dict(params)
            vaihto[toinen] = vaihto.pop(nimi)
            vaihtoehdot.append(vaihto)
    return vaihtoehdot


def hae_ottelut(lahde, kysely, avain):
    """Hakee yhden paikan tulevat ottelut.

    start_date karsii haun tahan paivaan - ilman sita rajapinta palauttaa koko
    historian (satoja otteluita), joista lahes kaikki heitettaisiin heti pois.
    Jos jokin asennus ei tunne start_datea, kokeillaan sama ilman sita."""
    tanaan = datetime.now().strftime("%Y-%m-%d")
    yritykset = [dict(p, start_date=tanaan) for p in paikkavaihtoehdot(kysely["params"])]
    yritykset += paikkavaihtoehdot(kysely["params"])

    viimeinen_virhe = None
    for params in yritykset:
        try:
            vastaus = hae_json(lahde["api"], "getMatches", params, avain)
        except Exception as virhe:
            viimeinen_virhe = virhe
            continue
        if vastaus.get("call", {}).get("status") == "error":
            viimeinen_virhe = RuntimeError(vastaus["call"].get("error", "tuntematon virhe"))
            continue
        # Onnistunut vastaus kelpaa, vaikka otteluita ei olisi - kesken kauden
        # tyhja tulos on oikea tulos, ei virhe.
        return vastaus.get("matches") or [], params

    if viimeinen_virhe is not None:
        raise viimeinen_virhe
    return [], yritykset[0]


def tarkista_paikka(ottelut, nimi):
    """Jos rajapinta ei tunne annettua paikkaparametria, se voi jattaa sen
    huomiotta ja palauttaa koko sarjan ottelut. Se nakyy siina, etta tuloksessa
    on monta eri paikkaa - varoitetaan siita aanen."""
    paikat = sorted({teksti(o.get("venue_name")) for o in ottelut if o.get("venue_name")})
    if len(paikat) > 3:
        return ("%s: vastauksessa %d eri paikkaa (%s, ...) - tarkista "
                "paikkaparametri" % (nimi, len(paikat), ", ".join(paikat[:3])))
    return None


# --------------------------------------------------------------------------
# Otteluiden normalisointi
# --------------------------------------------------------------------------

def teksti(arvo):
    if arvo is None:
        return ""
    return arvo.strip() if isinstance(arvo, str) else str(arvo)


def tunnista_seurat(ottelu, seurat):
    """Mitka konfiguroidut seurat ovat tassa ottelussa mukana."""
    kentat = " | ".join(teksti(ottelu.get(kentta)) for kentta in
                        ("koti", "vieras", "koti_seura", "vieras_seura"))
    loydetyt = []
    for seura in seurat:
        for tunniste in seura["tunnisteet"]:
            # sanarajaus, jottei lyhenne osu vahingossa keskelle toista nimea
            kaava = (r"(?<![0-9A-Za-zÅÄÖåäö])" + re.escape(tunniste) +
                     r"(?![0-9A-Za-zÅÄÖåäö])")
            if re.search(kaava, kentat, re.IGNORECASE):
                loydetyt.append(seura["id"])
                break
    return loydetyt


def normalisoi(raaka, lahde, kysely, seurat):
    """Torneopalin ottelu -> sivun oma, kevyt muoto."""
    pvm = teksti(raaka.get("date"))
    klo = teksti(raaka.get("time"))[:5]
    if not pvm or not klo:
        return None

    sarja = teksti(raaka.get("category_name"))
    ryhma = teksti(raaka.get("group_name"))
    if ryhma and ryhma.lower() not in sarja.lower():
        sarja = (sarja + " " + ryhma).strip()

    match_id = teksti(raaka.get("match_id"))
    pohja = lahde.get("ottelu_linkki") or ""
    ottelu = {
        "id": lahde["id"] + "-" + match_id,
        "laji": kysely["laji"],
        "paikka": kysely["paikka"],
        "paikka_tarkenne": teksti(raaka.get("venue_name")) or kysely["paikka"],
        "pvm": pvm,
        "klo": klo,
        "sarja": sarja,
        "koti": teksti(raaka.get("team_A_name")) or teksti(raaka.get("team_home_name")),
        "vieras": teksti(raaka.get("team_B_name")) or teksti(raaka.get("team_away_name")),
        "koti_seura": teksti(raaka.get("club_A_name")),
        "vieras_seura": teksti(raaka.get("club_B_name")),
        "linkki": (pohja.replace("{id}", match_id) if pohja and match_id
                   else kysely.get("linkki", "")),
        "lahde": lahde["id"],
    }
    ottelu["seurat"] = tunnista_seurat(ottelu, seurat)
    ottelu["kesto"] = KESTO.get(ottelu["laji"], KESTO_OLETUS)
    return ottelu


def tulevat(ottelut, nyt=None):
    """Vain tasta paivasta eteenpain - menneet pelit eivat kuulu listaan."""
    raja = (nyt or datetime.now()).strftime("%Y-%m-%d")
    return [o for o in ottelut if o.get("pvm", "") >= raja]


# --------------------------------------------------------------------------
# Kalenteritiedostot
# --------------------------------------------------------------------------

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Helsinki
X-LIC-LOCATION:Europe/Helsinki
BEGIN:STANDARD
DTSTART:19701025T040000
TZOFFSETFROM:+0300
TZOFFSETTO:+0200
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
TZNAME:EET
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700329T030000
TZOFFSETFROM:+0200
TZOFFSETTO:+0300
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
TZNAME:EEST
END:DAYLIGHT
END:VTIMEZONE"""


def ics_teksti(arvo):
    return (teksti(arvo).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def taita(rivi):
    """iCalendar sallii 75 tavua rivia kohden; pidemmat taitetaan valilyonnilla."""
    tavut = rivi.encode("utf-8")
    if len(tavut) <= 75:
        return rivi

    def katkaise(data, pituus):
        """Katkaise tavujonon alusta enintaan 'pituus' tavua monitavuisen
        merkin keskelta osumatta."""
        loppu = min(pituus, len(data))
        while loppu > 0 and loppu < len(data) and (data[loppu] & 0xC0) == 0x80:
            loppu -= 1
        return data[:loppu], data[loppu:]

    pala, loput = katkaise(tavut, 75)
    palat = [pala.decode("utf-8")]
    while loput:
        pala, loput = katkaise(loput, 74)
        palat.append(" " + pala.decode("utf-8"))
    return "\r\n".join(palat)


def otsikko(ottelu):
    nimi = ottelu["koti"] + " - " + ottelu["vieras"]
    return (ottelu["sarja"] + ": " + nimi) if ottelu["sarja"] else nimi


def vevent(ottelu, leimattu):
    alku = datetime.strptime(ottelu["pvm"] + " " + ottelu["klo"], "%Y-%m-%d %H:%M")
    loppu = alku + timedelta(minutes=ottelu.get("kesto", KESTO_OLETUS))
    kuvaus = ottelu["laji"]
    if ottelu["sarja"]:
        kuvaus += " - " + ottelu["sarja"]
    if ottelu.get("linkki"):
        kuvaus += "\n" + ottelu["linkki"]
    rivit = [
        "BEGIN:VEVENT",
        "UID:" + ottelu["id"] + "@riihikoski-pelit",
        "DTSTAMP:" + leimattu,
        "DTSTART;TZID=Europe/Helsinki:" + alku.strftime("%Y%m%dT%H%M%S"),
        "DTEND;TZID=Europe/Helsinki:" + loppu.strftime("%Y%m%dT%H%M%S"),
        "SUMMARY:" + ics_teksti(otsikko(ottelu)),
        "LOCATION:" + ics_teksti(ottelu["paikka_tarkenne"] + ", Riihikoski"),
        "DESCRIPTION:" + ics_teksti(kuvaus),
        "CATEGORIES:" + ics_teksti(ottelu["laji"]),
    ]
    if ottelu.get("linkki"):
        rivit.append("URL:" + ottelu["linkki"])
    rivit.append("END:VEVENT")
    return rivit


def kirjoita_ics(polku, nimi, ottelut):
    leimattu = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rivit = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Pelit Riihikoskella//FI",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + ics_teksti(nimi),
        "X-WR-TIMEZONE:Europe/Helsinki",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]
    rivit += VTIMEZONE.split("\n")
    for ottelu in ottelut:
        rivit += vevent(ottelu, leimattu)
    rivit.append("END:VCALENDAR")
    sisalto = "\r\n".join(taita(rivi) for rivi in rivit) + "\r\n"
    with open(polku, "w", encoding="utf-8", newline="") as tiedosto:
        tiedosto.write(sisalto)
    return len(ottelut)


def sopii(ottelu, suodatin):
    if "paikka" in suodatin and ottelu.get("paikka") != suodatin["paikka"]:
        return False
    if "laji" in suodatin and ottelu.get("laji") != suodatin["laji"]:
        return False
    if "seura" in suodatin and suodatin["seura"] not in ottelu.get("seurat", []):
        return False
    return True


def rakenna_kalenterit(config, ottelut):
    os.makedirs(KALENTERIT, exist_ok=True)
    tulos = []
    for kalenteri in config["kalenterit"]:
        osuma = [o for o in ottelut if sopii(o, kalenteri["suodatin"])]
        kirjoita_ics(os.path.join(KALENTERIT, kalenteri["tiedosto"]),
                     kalenteri["nimi"], osuma)
        tulos.append((kalenteri["tiedosto"], len(osuma)))
    kirjoita_asetukset(config)
    return tulos


def kirjoita_asetukset(config):
    """Sivu tarvitsee configista vain seurat ja kalenterilistan - kirjoitetaan
    ne erikseen, jottei selaimelle tarvitse tarjoilla koko config.jsonia."""
    polku = os.path.join(os.path.dirname(DATA), "asetukset.json")
    asetukset = {
        "sivu": config.get("sivu", {}),
        "suodattimet": config.get("suodattimet", {}),
        "seurat": [{"id": s["id"], "nimi": s["nimi"], "lyhenne": s["lyhenne"],
                    "logo": s.get("logo", "")}
                   for s in config.get("seurat", [])],
        "kalenterit": config.get("kalenterit", []),
    }
    os.makedirs(os.path.dirname(polku), exist_ok=True)
    with open(polku, "w", encoding="utf-8") as tiedosto:
        json.dump(asetukset, tiedosto, ensure_ascii=False, indent=1)
        tiedosto.write("\n")


# --------------------------------------------------------------------------
# Paaohjelma
# --------------------------------------------------------------------------

def lue_config():
    with open(CONFIG, encoding="utf-8") as tiedosto:
        return json.load(tiedosto)


def lue_data():
    if not os.path.exists(DATA):
        return {"paivitetty": None, "ottelut": []}
    with open(DATA, encoding="utf-8") as tiedosto:
        return json.load(tiedosto)


def kirjoita_data(data):
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    with open(DATA, "w", encoding="utf-8") as tiedosto:
        json.dump(data, tiedosto, ensure_ascii=False, indent=1)
        tiedosto.write("\n")


def jarjesta(ottelut):
    return sorted(ottelut, key=lambda o: (o.get("pvm", ""), o.get("klo", ""),
                                          o.get("laji", ""), o.get("koti", "")))


def main():
    jasennin = argparse.ArgumentParser(description="Paivita Riihikosken pelikalenteri")
    jasennin.add_argument("--vain-kalenteri", action="store_true",
                          help="ala hae rajapinnasta, rakenna .ics vanhasta datasta")
    jasennin.add_argument("--testi", action="store_true",
                          help="kokeile rajapintaa, ala kirjoita tiedostoja")
    argumentit = jasennin.parse_args()

    config = lue_config()
    vanha = lue_data()

    if argumentit.vain_kalenteri:
        ottelut = jarjesta(tulevat(vanha.get("ottelut", [])))
        for tiedosto, maara in rakenna_kalenterit(config, ottelut):
            print("  %-22s %3d ottelua" % (tiedosto, maara))
        print("Valmis: %d ottelua." % len(ottelut))
        return 0

    kaikki, ongelmat, haetut = [], [], set()

    for lahde in config["lahteet"]:
        avain = os.environ.get(lahde["avain_ymparistomuuttuja"], "").strip()
        if not avain:
            ongelmat.append("%s: API-avain puuttuu (%s), lahde ohitettiin"
                            % (lahde["nimi"], lahde["avain_ymparistomuuttuja"]))
            continue
        for kysely in lahde["kyselyt"]:
            nimi = "%s / %s" % (kysely["laji"], kysely["paikka"])
            try:
                raa_at, kaytetyt = hae_ottelut(lahde, kysely, avain)
            except Exception as virhe:
                ongelmat.append("%s: haku epaonnistui (%s)" % (nimi, virhe))
                continue
            haetut.add(lahde["id"])
            varoitus = tarkista_paikka(raa_at, nimi)
            if varoitus:
                ongelmat.append(varoitus)
            osuma = [normalisoi(r, lahde, kysely, config["seurat"]) for r in raa_at]
            osuma = [o for o in osuma if o]
            kaikki += osuma
            print("  %-34s %3d ottelua  %s" % (nimi, len(osuma), kaytetyt))

    if argumentit.testi:
        for ottelu in jarjesta(tulevat(kaikki))[:15]:
            print("   %s %s  %-12s %s - %s" % (ottelu["pvm"], ottelu["klo"],
                                               ottelu["laji"], ottelu["koti"],
                                               ottelu["vieras"]))
        for ongelma in ongelmat:
            print("  ! " + ongelma)
        return 0

    # Sailyta niiden lahteiden data, joita ei nyt saatu haettua - yksi kaatunut
    # rajapinta ei saa tyhjentaa koko sivua.
    for ottelu in vanha.get("ottelut", []):
        if ottelu.get("lahde") not in haetut:
            kaikki.append(ottelu)

    yksiloidyt = {}
    for ottelu in kaikki:
        yksiloidyt[ottelu["id"]] = ottelu
    ottelut = jarjesta(tulevat(list(yksiloidyt.values())))

    kirjoita_data({
        "paivitetty": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lahteet_haettu": sorted(haetut),
        "huomiot": ongelmat,
        "ottelut": ottelut,
    })
    for tiedosto, maara in rakenna_kalenterit(config, ottelut):
        print("  %-22s %3d ottelua" % (tiedosto, maara))
    for ongelma in ongelmat:
        print("  ! " + ongelma)
    print("Valmis: %d tulevaa ottelua." % len(ottelut))
    return 0


if __name__ == "__main__":
    sys.exit(main())
