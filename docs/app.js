/* Pelit Riihikoskella - sivun logiikka.
   Ei riippuvuuksia. Data tulee tiedostoista data/pelit.json ja data/asetukset.json,
   jotka scripts/paivita.py kirjoittaa. */

(function () {
  "use strict";

  var VIIKONPAIVAT = ["su", "ma", "ti", "ke", "to", "pe", "la"];
  var KUUKAUDET = ["tammikuuta", "helmikuuta", "maaliskuuta", "huhtikuuta",
                   "toukokuuta", "kesäkuuta", "heinäkuuta", "elokuuta",
                   "syyskuuta", "lokakuuta", "marraskuuta", "joulukuuta"];

  var tila = {
    ottelut: [],
    seurat: [],
    kalenterit: [],
    suodattimet: { lajit: [], paikat: [] },
    valinta: { laji: "", paikka: "", seura: "" },
    haku: ""
  };

  // ---------------------------------------------------------------- apurit

  function elementti(tagi, luokka, teksti) {
    var e = document.createElement(tagi);
    if (luokka) { e.className = luokka; }
    if (teksti !== undefined && teksti !== null) { e.textContent = teksti; }
    return e;
  }

  function paivaObjekti(ottelu) {
    var osat = ottelu.pvm.split("-");
    var kello = (ottelu.klo || "00:00").split(":");
    return new Date(+osat[0], +osat[1] - 1, +osat[2], +kello[0], +kello[1]);
  }

  function paivaOtsikko(pvm) {
    var osat = pvm.split("-");
    var d = new Date(+osat[0], +osat[1] - 1, +osat[2]);
    return VIIKONPAIVAT[d.getDay()] + " " + d.getDate() + ". " +
           KUUKAUDET[d.getMonth()] + " " + d.getFullYear();
  }

  function lajiLuokka(laji) {
    return (laji || "").toLowerCase().replace(/[^a-z]/g, "");
  }

  /* "Riihikosken urheilupuisto" on tulospalvelun nimi; kyläläiselle se on
     urheilukenttä. Lyhyt nimi tulee asetuksista. */
  function paikanNimi(arvo) {
    var osuma = (tila.suodattimet.paikat || []).filter(function (p) {
      return p.arvo === arvo;
    })[0];
    return osuma ? osuma.nimi : arvo;
  }

  function onOmaJoukkue(nimi, ottelu) {
    // Korostetaan se joukkue, jonka perusteella ottelu tunnistettiin omaksi.
    if (!ottelu.seurat || !ottelu.seurat.length) { return false; }
    var lyhenteet = tila.seurat.filter(function (s) {
      return ottelu.seurat.indexOf(s.id) !== -1;
    }).map(function (s) { return s.lyhenne.toLowerCase(); });
    var pieni = (nimi || "").toLowerCase();
    return lyhenteet.some(function (l) { return pieni.indexOf(l) === 0; });
  }

  // ------------------------------------------------------------- suodatus

  function suodatetut() {
    var haku = tila.haku.trim().toLowerCase();
    return tila.ottelut.filter(function (o) {
      if (tila.valinta.laji && o.laji !== tila.valinta.laji) { return false; }
      if (tila.valinta.paikka && o.paikka !== tila.valinta.paikka) { return false; }
      if (tila.valinta.seura &&
          (o.seurat || []).indexOf(tila.valinta.seura) === -1) { return false; }
      if (haku) {
        var kasa = (o.koti + " " + o.vieras + " " + (o.sarja || "")).toLowerCase();
        if (kasa.indexOf(haku) === -1) { return false; }
      }
      return true;
    });
  }

  // ----------------------------------------------------- suodatinpainikkeet

  function rakennaNapit(sailio, vaihtoehdot, kentta) {
    sailio.textContent = "";
    vaihtoehdot.forEach(function (vaihtoehto) {
      var nappi = elementti("button", vaihtoehto.tyhja ? "ei-otteluita" : null,
                            vaihtoehto.nimi);
      nappi.type = "button";
      nappi.setAttribute("aria-pressed",
        String(tila.valinta[kentta] === vaihtoehto.arvo));
      if (vaihtoehto.tyhja) {
        nappi.title = vaihtoehto.nimi + ": ei tulevia otteluita juuri nyt";
      }
      nappi.addEventListener("click", function () {
        tila.valinta[kentta] = vaihtoehto.arvo;
        piirra();
      });
      sailio.appendChild(nappi);
    });
  }

  function onOtteluita(kentta, arvo) {
    return tila.ottelut.some(function (o) {
      return kentta === "seura"
        ? (o.seurat || []).indexOf(arvo) !== -1
        : o[kentta] === arvo;
    });
  }

  /* Vaihtoehdot tulevat asetuksista, ei datasta: napit pysyvät paikallaan
     myös silloin kun lajin kausi ei ole käynnissä. Tyhjät himmennetään. */
  function suodatinVaihtoehdot() {
    var lajit = (tila.suodattimet.lajit || []).map(function (laji) {
      return { arvo: laji, nimi: laji, tyhja: !onOtteluita("laji", laji) };
    });
    var paikat = (tila.suodattimet.paikat || []).map(function (paikka) {
      return { arvo: paikka.arvo, nimi: paikka.nimi,
               tyhja: !onOtteluita("paikka", paikka.arvo) };
    });
    var seurat = tila.seurat.map(function (seura) {
      return { arvo: seura.id, nimi: seura.lyhenne,
               tyhja: !onOtteluita("seura", seura.id) };
    });

    var kaikki = { arvo: "", nimi: "Kaikki" };
    rakennaNapit(document.querySelector('[data-suodatin="laji"]'),
                 [kaikki].concat(lajit), "laji");
    rakennaNapit(document.querySelector('[data-suodatin="paikka"]'),
                 [kaikki].concat(paikat), "paikka");
    rakennaNapit(document.querySelector('[data-suodatin="seura"]'),
                 [kaikki].concat(seurat), "seura");
    document.getElementById("ryhma-seura").hidden = seurat.length === 0;
  }

  // ------------------------------------------------------------ ottelulista

  function otteluRivi(ottelu) {
    var rivi = elementti("article", "ottelu");
    rivi.appendChild(elementti("div", "kello", ottelu.klo));

    var joukkueet = elementti("div", "joukkueet");
    var koti = elementti("span", onOmaJoukkue(ottelu.koti, ottelu) ? "oma" : null,
                         ottelu.koti);
    var vieras = elementti("span", onOmaJoukkue(ottelu.vieras, ottelu) ? "oma" : null,
                           ottelu.vieras);
    joukkueet.appendChild(koti);
    joukkueet.appendChild(elementti("span", "vs", " – "));
    joukkueet.appendChild(vieras);
    rivi.appendChild(joukkueet);

    var tiedot = elementti("div", "tiedot");
    tiedot.appendChild(elementti("span", "merkki " + lajiLuokka(ottelu.laji), ottelu.laji));
    if (ottelu.sarja) { tiedot.appendChild(elementti("span", null, ottelu.sarja)); }
    tiedot.appendChild(elementti("span", null, paikanNimi(ottelu.paikka)));
    rivi.appendChild(tiedot);

    var nappi = elementti("button", "lisaa", "Kalenteriin");
    nappi.type = "button";
    nappi.addEventListener("click", function () { lataaYksiOttelu(ottelu); });
    rivi.appendChild(nappi);

    return rivi;
  }

  function piirraLista(ottelut) {
    var lista = document.getElementById("lista");
    lista.textContent = "";

    if (!ottelut.length) {
      lista.appendChild(elementti("p", "tyhja",
        tila.ottelut.length
          ? "Ei otteluita näillä rajauksilla."
          : "Tulevia otteluita ei ole tällä hetkellä tiedossa."));
      return;
    }

    var nykyinen = null, ryhma = null;
    ottelut.forEach(function (ottelu) {
      if (ottelu.pvm !== nykyinen) {
        nykyinen = ottelu.pvm;
        ryhma = elementti("section", "paiva");
        ryhma.appendChild(elementti("h2", "paiva-otsikko", paivaOtsikko(ottelu.pvm)));
        lista.appendChild(ryhma);
      }
      ryhma.appendChild(otteluRivi(ottelu));
    });
  }

  // ---------------------------------------------------------- kalenterit

  function kalenteriOsoite(tiedosto) {
    return new URL("kalenteri/" + tiedosto, window.location.href).href;
  }

  function sopiiSuodattimeen(ottelu, suodatin) {
    if (suodatin.paikka && ottelu.paikka !== suodatin.paikka) { return false; }
    if (suodatin.laji && ottelu.laji !== suodatin.laji) { return false; }
    if (suodatin.seura && (ottelu.seurat || []).indexOf(suodatin.seura) === -1) {
      return false;
    }
    return true;
  }

  function piirraKalenterit() {
    var lista = document.getElementById("kalenterit");
    lista.textContent = "";

    tila.kalenterit.forEach(function (kalenteri) {
      var maara = tila.ottelut.filter(function (o) {
        return sopiiSuodattimeen(o, kalenteri.suodatin || {});
      }).length;

      // Myös tyhjä kalenteri kannattaa tarjota: sen voi tilata nyt, ja ottelut
      // ilmestyvät siihen itsestään kun kausi alkaa.
      var rivi = elementti("li");

      // Seuran logo, jos kalenteri koskee yhtä seuraa ja logo on asetettu.
      var seura = tila.seurat.filter(function (s) {
        return s.id === (kalenteri.suodatin || {}).seura;
      })[0];
      if (seura && seura.logo) {
        var logo = document.createElement("img");
        logo.className = "logo";
        logo.src = seura.logo;
        logo.alt = "";
        logo.loading = "lazy";
        rivi.appendChild(logo);
      } else if (seura) {
        rivi.appendChild(elementti("span", "logo-tyhja", seura.lyhenne));
      }

      rivi.appendChild(elementti("span", "nimi", kalenteri.nimi));
      rivi.appendChild(elementti("span", "maara", maara
        ? maara + (maara === 1 ? " ottelu" : " ottelua")
        : "ei vielä otteluita"));

      var osoite = kalenteriOsoite(kalenteri.tiedosto);
      var tilaa = elementti("a", null, "Tilaa kalenteri");
      tilaa.href = osoite.replace(/^https?:/, "webcal:");
      rivi.appendChild(tilaa);

      var kopioi = elementti("button", null, "Kopioi osoite");
      kopioi.type = "button";
      kopioi.addEventListener("click", function () {
        kopioiLeikepoydalle(osoite, kopioi);
      });
      rivi.appendChild(kopioi);

      lista.appendChild(rivi);
    });
  }

  function kopioiLeikepoydalle(teksti, nappi) {
    var alkuperainen = nappi.textContent;
    function valmis(onnistui) {
      nappi.textContent = onnistui ? "Kopioitu" : "Kopiointi ei onnistunut";
      setTimeout(function () { nappi.textContent = alkuperainen; }, 2000);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(teksti).then(function () { valmis(true); },
                                                 function () { valmis(false); });
    } else {
      window.prompt("Kopioi kalenterin osoite:", teksti);
    }
  }

  // ------------------------------------------- yksittäinen kalenterimerkintä

  function pad(luku) { return (luku < 10 ? "0" : "") + luku; }

  function icsAika(d) {
    return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + "T" +
           pad(d.getHours()) + pad(d.getMinutes()) + "00";
  }

  function icsPakene(arvo) {
    return String(arvo || "").replace(/\\/g, "\\\\").replace(/;/g, "\\;")
      .replace(/,/g, "\\,").replace(/\n/g, "\\n");
  }

  function lataaYksiOttelu(ottelu) {
    var alku = paivaObjekti(ottelu);
    var loppu = new Date(alku.getTime() + (ottelu.kesto || 90) * 60000);
    var nimi = (ottelu.sarja ? ottelu.sarja + ": " : "") +
               ottelu.koti + " - " + ottelu.vieras;

    var rivit = [
      "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Pelit Riihikoskella//FI",
      "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
      "BEGIN:VTIMEZONE", "TZID:Europe/Helsinki",
      "BEGIN:STANDARD", "DTSTART:19701025T040000",
      "TZOFFSETFROM:+0300", "TZOFFSETTO:+0200",
      "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "TZNAME:EET", "END:STANDARD",
      "BEGIN:DAYLIGHT", "DTSTART:19700329T030000",
      "TZOFFSETFROM:+0200", "TZOFFSETTO:+0300",
      "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "TZNAME:EEST", "END:DAYLIGHT",
      "END:VTIMEZONE",
      "BEGIN:VEVENT",
      "UID:" + ottelu.id + "@riihikoski-pelit",
      "DTSTAMP:" + icsAika(new Date()),
      "DTSTART;TZID=Europe/Helsinki:" + icsAika(alku),
      "DTEND;TZID=Europe/Helsinki:" + icsAika(loppu),
      "SUMMARY:" + icsPakene(nimi),
      "LOCATION:" + icsPakene((ottelu.paikka_tarkenne || ottelu.paikka) + ", Riihikoski"),
      "DESCRIPTION:" + icsPakene(ottelu.laji + (ottelu.sarja ? " - " + ottelu.sarja : "")),
      "END:VEVENT", "END:VCALENDAR"
    ];

    var sisalto = rivit.join("\r\n") + "\r\n";
    var blob = new Blob([sisalto], { type: "text/calendar;charset=utf-8" });
    var osoite = URL.createObjectURL(blob);
    var linkki = document.createElement("a");
    linkki.href = osoite;
    linkki.download = ottelu.pvm + "-" + ottelu.koti.replace(/[^\wåäöÅÄÖ]+/g, "") + ".ics";
    document.body.appendChild(linkki);
    linkki.click();
    document.body.removeChild(linkki);
    setTimeout(function () { URL.revokeObjectURL(osoite); }, 1000);
  }

  // ------------------------------------------------------------------ piirto

  function piirra() {
    var ottelut = suodatetut();
    suodatinVaihtoehdot();
    piirraLista(ottelut);

    var osumat = document.getElementById("osumat");
    if (!tila.ottelut.length) {
      osumat.textContent = "";
    } else if (ottelut.length === tila.ottelut.length) {
      osumat.textContent = tila.ottelut.length + " tulevaa ottelua";
    } else {
      osumat.textContent = ottelut.length + " / " + tila.ottelut.length + " ottelua";
    }
  }

  function naytaPaivitetty(aikaleima) {
    if (!aikaleima) { return; }
    var d = new Date(aikaleima);
    if (isNaN(d.getTime())) { return; }
    document.getElementById("paivitetty").textContent =
      "Tiedot päivitetty " + d.getDate() + "." + (d.getMonth() + 1) + "." +
      d.getFullYear() + " klo " + pad(d.getHours()) + "." + pad(d.getMinutes());
  }

  /* Ylätunnisteen kuvan lähdemerkintä. CC-lisensoitu kuva vaatii tekijän nimen,
     lisenssin ja maininnan muokkauksesta, joten ne rakennetaan omina osinaan
     ja lisenssi sekä lähde linkitetään. */
  function naytaKuvateksti(sivu) {
    var kohta = document.getElementById("kuvateksti");
    kohta.textContent = "";
    var lahde = sivu.kuva_lahde;
    if (!lahde) { return; }
    if (typeof lahde === "string") { kohta.textContent = lahde; return; }

    function linkki(teksti, osoite) {
      if (!osoite) { return elementti("span", null, teksti); }
      var a = elementti("a", null, teksti);
      a.href = osoite;
      a.rel = "noopener";
      return a;
    }

    kohta.appendChild(document.createTextNode("Kuva: " + (lahde.tekija || "")));
    if (lahde.lahde_nimi) {
      kohta.appendChild(document.createTextNode(" / "));
      kohta.appendChild(linkki(lahde.lahde_nimi, lahde.linkki));
    }
    if (lahde.lisenssi) {
      kohta.appendChild(document.createTextNode(", "));
      kohta.appendChild(linkki(lahde.lisenssi, lahde.lisenssi_linkki));
    }
    if (lahde.muutos) {
      kohta.appendChild(document.createTextNode(" · " + lahde.muutos));
    }
  }

  function naytaHuomio(data) {
    var alustavia = data.ottelut.some(function (o) { return o.alustava; });
    if (!alustavia) { return; }
    var laatikko = document.getElementById("huomio");
    laatikko.textContent = "Sivu näyttää toistaiseksi käsin poimittua ohjelmaa. " +
      "Kun tulospalvelun rajapinta on otettu käyttöön, tiedot päivittyvät itsestään.";
    laatikko.hidden = false;
  }

  function virhe(viesti) {
    document.getElementById("lista").textContent = "";
    var laatikko = elementti("p", "tyhja", viesti);
    document.getElementById("lista").appendChild(laatikko);
  }

  function kaynnista() {
    document.getElementById("haku").addEventListener("input", function (tapahtuma) {
      tila.haku = tapahtuma.target.value;
      piirra();
    });

    Promise.all([
      fetch("data/pelit.json", { cache: "no-cache" }).then(function (v) { return v.json(); }),
      fetch("data/asetukset.json", { cache: "no-cache" }).then(function (v) { return v.json(); })
    ]).then(function (tulokset) {
      var data = tulokset[0], asetukset = tulokset[1];
      tila.ottelut = data.ottelut || [];
      tila.seurat = asetukset.seurat || [];
      tila.kalenterit = asetukset.kalenterit || [];
      tila.suodattimet = asetukset.suodattimet || { lajit: [], paikat: [] };
      naytaKuvateksti(asetukset.sivu || {});
      naytaPaivitetty(data.paivitetty);
      naytaHuomio(data);
      piirra();
      piirraKalenterit();
    }).catch(function () {
      virhe("Ottelutietoja ei saatu ladattua. Jos avasit sivun suoraan tiedostosta, " +
            "käynnistä paikallinen palvelin: python -m http.server");
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", kaynnista);
  } else {
    kaynnista();
  }
})();
