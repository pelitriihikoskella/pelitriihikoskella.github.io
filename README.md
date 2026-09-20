# Pelit Riihikoskella

Yhden sivun pelikalenteri **Riihikosken urheilukentälle** ja **Kisariihelle**.
Näyttää tulevat jalkapallo-, futsal- ja salibandyottelut, ja tarjoaa ne
tilattavana kalenterina puhelimeen.

- Ottelut haetaan Palloliiton ja Salibandyliiton **Torneopal-tulospalvelusta**.
- Haku tehdään **paikan** perusteella, joten mukaan tulevat myös turnauspäivien
  ottelut, joissa PöKa tai PöU ei itse pelaa.
- Sivulla voi rajata lajin, paikan ja seuran mukaan.
- Tilattavia `.ics`-kalentereita on kaksi: **PöKa:n** ja **PöU:n** kotipelit.
  Kumpikin kattaa kaikki lajit, joten yksi tilaus riittää koko vuodeksi.

---

## Mitä tarvitset

1. **GitHub-tunnus** (ilmainen) — sivun koti ja automaattinen päivitys.
2. **Kaksi Torneopal-API-avainta:**
   - `SPL_API_KEY` — Palloliitto, jalkapallo ja futsal
   - `SALIBANDY_API_KEY` — Salibandyliitto

   Avaimet pyydetään seuran kautta Torneopalilta. Kerro pyynnössä mihin
   avainta käytetään (kylän julkinen pelikalenteri), mitkä paikat ovat
   kyseessä ja että kyse on lukukäytöstä. Ilman avaimia sivu toimii, mutta
   näyttää vain tiedostoon `scripts/siemendata.txt` käsin poimittua ohjelmaa.

---

## Käyttöönotto

### 1. Vie projekti GitHubiin

```bash
cd riihikoski-pelit
git init
git add .
git commit -m "Ensimmäinen versio"
git branch -M main
git remote add origin https://github.com/KAYTTAJATUNNUS/riihikoski-pelit.git
git push -u origin main
```

### 2. Kytke GitHub Pages päälle

GitHubissa **Settings → Pages → Source: GitHub Actions**.

Sivun osoitteeksi tulee `https://KAYTTAJATUNNUS.github.io/riihikoski-pelit`.
Merkitse sama osoite tiedostoon `config.json` kohtaan `julkinen_osoite`.

### 3. Tallenna API-avaimet

**Settings → Secrets and variables → Actions → New repository secret**

| Nimi | Arvo |
|---|---|
| `SPL_API_KEY` | Palloliiton avain |
| `SALIBANDY_API_KEY` | Salibandyliiton avain |

Avaimet eivät näy sivulla eivätkä koodissa — vain GitHubin ajoympäristössä.

### 4. Aja päivitys ensimmäisen kerran

**Actions → Päivitä pelit → Run workflow.**

Sen jälkeen päivitys tapahtuu joka yö itsestään.

---

## Paikallinen käyttö

Sivun voi katsoa ja päivittää myös omalta koneelta. Python 3 riittää,
asennettavia kirjastoja ei ole.

```bash
python -m http.server 8765 --directory docs
```

Avaa selaimessa <http://localhost:8765>.

Otteluiden haku omalla koneella (PowerShell):

```powershell
$env:SPL_API_KEY = "avain"
$env:SALIBANDY_API_KEY = "avain"
python scripts/paivita.py
```

Muita komentoja:

| Komento | Mitä tekee |
|---|---|
| `python scripts/paivita.py` | hakee ottelut ja rakentaa sivun datan + kalenterit |
| `python scripts/paivita.py --testi` | kokeilee rajapintaa, ei kirjoita tiedostoja |
| `python scripts/paivita.py --vain-kalenteri` | rakentaa `.ics`-tiedostot olemassa olevasta datasta |
| `python scripts/siemenna.py` | kirjoittaa väliaikaisen käsin poimitun ohjelman |
| `python scripts/kooste.py --tila viikko` | tulostaa viikon ohjelman tekstinä |
| `python scripts/kooste.py --tila tanaan` | tulostaa tämän päivän pelit |
| `python scripts/facebook.py --tiedosto kooste.txt --kuivaharjoitus` | näyttää mitä Facebookiin julkaistaisiin |

---

## Asetukset: `config.json`

Kaikki muutettava on yhdessä tiedostossa.

**Paikat ja lähteet** — `lahteet[].kyselyt[]`. Numerot ovat samat kuin
tulospalvelun osoitteessa:

| Paikka | Osoite tulospalvelussa | Tunnus |
|---|---|---|
| Riihikosken urheilupuisto (jalkapallo) | `tulospalvelu.palloliitto.fi/location/133` | `venue_id: 133` |
| Kisariihi (futsal) | `tulospalvelu.palloliitto.fi/venue/865` | `venue_id: 865` |
| Kisariihi (salibandy) | `tulospalvelu.salibandy.fi/location/734827322` | `location_id: 734827322` |

**Suodatinnapit** — `suodattimet`. Tässä luetellaan lajit ja paikat, jotka
näkyvät sivun nappeina. Ne ovat kiinteä lista eivätkä riipu siitä, onko lajilla
juuri nyt otteluita: napit pysyvät paikallaan ympäri vuoden, ja laji tai paikka
ilman tulevia otteluita näkyy katkoviivalla. Paikan `arvo` on tulospalvelun
nimi ja `nimi` se, joka sivulla näytetään (*Riihikosken urheilupuisto* →
*Urheilukenttä*). Seuranapit tulevat `seurat`-listasta samalla tavalla.

**Kuvat** — kaikki kuvat ovat kansiossa `docs/kuvat/`.

Ylätunnisteen kansikuva on `docs/kuvat/kansikuva.webp`, ja siihen viitataan
suoraan tiedostossa `docs/index.html`. Se on tarkoituksella HTML:ssä eikä
asetuksissa: selain alkaa ladata kuvaa heti, ilman että se odottaa
JavaScriptiä. Kuvan vaihtaminen on siis tiedoston korvaaminen (tai uusi nimi
ja yhden rivin muutos `index.html`:ään). Kuva näytetään kokonaisena
kuvakaistana, ei tummennettuna taustana, jotta piirroksen yksityiskohdat
säilyvät. Kuva on panoraama (suhde 2.34), joten leveällä näytöllä sitä rajataan ensisijaisesti leveydestä: enintään 1200 px leveä ja 420 px korkea, keskitettynä.

`seurat[].logo` on seuran logo kalenterilistassa, polku `docs/`-kansiosta
katsoen (esim. `kuvat/poka.png`). Seura ilman logoa saa tilalle lyhenteestä
tehdyn merkin, joten rivit pysyvät suorassa.

`sivu.kuva_lahde` on kansikuvan lähdemerkintä, joka näkyy pienellä
ylätunnisteen alla. Tyhjänä riviä ei näytetä lainkaan. Jos otat käyttöön kuvan,
joka ei ole omasi, täytä kentät `tekija`, `lahde_nimi`, `linkki`, `lisenssi`,
`lisenssi_linkki` ja `muutos` — lähde ja lisenssi linkittyvät automaattisesti.
Esimerkiksi Wikimedia Commonsin CC BY-SA -kuva vaatii tekijän nimen, lisenssin
ja maininnan siitä, että kuvaa on muokattu.

**Seurat** — `seurat[]`. `tunnisteet` on lista nimiä, joiden perusteella ottelu
tunnistetaan seuran otteluksi. Jos joukkuenimet eivät täsmää, lisää puuttuva
kirjoitusasu listaan.

> **Tarkista tämä:** `poka`-kohdan nimi on kirjoitettu muotoon *Pöytyän Kaima*.
> Jos seuran virallinen nimi tai lyhenne tulospalvelussa on toinen, korjaa
> `nimi`, `lyhenne` ja `tunnisteet` — muuten PöKa-kalenteri jää tyhjäksi.

**Kalenterit** — `kalenterit[]`. Jokainen rivi tuottaa yhden `.ics`-tiedoston.
Suodattimena voi käyttää `paikka`, `laji` ja `seura` -kenttiä, yhdessä tai
erikseen. Tyhjä suodatin `{}` tarkoittaa kaikkia otteluita — sillä saa
halutessaan takaisin esimerkiksi koko kentän tai koko hallin ohjelman.
Myös tyhjä kalenteri näytetään sivulla, koska sen voi tilata jo ennen kauden
alkua ja ottelut ilmestyvät siihen itsestään.

---

## Hakemistot

```
config.json                  kaikki asetukset
scripts/paivita.py           haku Torneopalista + .ics-tiedostojen teko
scripts/siemenna.py          väliaikainen data ennen API-avaimia
scripts/siemendata.txt       käsin poimittu ohjelma (poistettavissa myöhemmin)
scripts/kooste.py            viikko- ja pelipäiväkoosteen teksti
scripts/facebook.py          koosteen julkaisu Facebook-sivulle
docs/                        julkaistava sivu (GitHub Pagesin juuri)
  kuvat/                     kansikuva ja seurojen logot
  index.html  style.css  app.js
  data/pelit.json            ottelut
  data/asetukset.json        seurat ja kalenterit sivua varten
  kalenteri/*.ics            tilattavat kalenterit
.github/workflows/paivita.yml  yöllinen automaattipäivitys
.github/workflows/kooste.yml   viikko-ohjelma ja pelipäivän muistutus
```

---

## Facebook-julkaisu

Työ `.github/workflows/kooste.yml` ajetaan joka aamu klo 7 (talvella 6):

- **maanantaisin** koko viikon ohjelma
- **muina päivinä** muistutus vain, jos Riihikoskella pelataan sinä päivänä
- jos pelejä ei ole, mitään ei julkaista — ryhmään ei mene tyhjiä viestejä

Kooste menee kahteen paikkaan: **GitHub luo siitä ilmoituksen**, josta saat
sähköpostin automaattisesti (ei vaadi mitään tunnuksia), ja **Facebook-sivulle**,
jos alla olevat salaisuudet on asetettu.

> **Ryhmään ei voi julkaista automaattisesti.** Meta poisti Groups APIn ja
> `publish_to_groups`-oikeuden huhtikuussa 2024. Sivun postauksen voi jakaa
> ryhmään käsin yhdellä napautuksella, tai voit kopioida tekstin sähköpostista.
> Selainlaajennukset, jotka lupaavat automaattista ryhmäpostausta, toimivat
> Facebookin käyttöehtoja vastaan ja vaarantavat henkilökohtaisen tilin.

### Sivun kytkeminen

1. Luo Facebook-**sivu** (esim. *Pelit Riihikoskella*), jos sellaista ei ole.
2. Mene [developers.facebook.com](https://developers.facebook.com/) ja luo
   sovellus, tyypiksi **Business**. Sovellus voi jäädä kehitystilaan: koska olet
   itse sekä sovelluksen että sivun ylläpitäjä, App Reviewia ei tarvita.
3. Avaa **Graph API Explorer**, valitse sovelluksesi ja pyydä oikeudet
   `pages_show_list`, `pages_read_engagement` ja `pages_manage_posts`.
   Paina *Generate Access Token*.
4. Vaihda lyhytikäinen tunnus pitkäikäiseksi:
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=SOVELLUS_ID&client_secret=SOVELLUS_SALAISUUS&fb_exchange_token=LYHYT_TUNNUS`
5. Hae sivun oma tunnus pitkäikäisellä käyttäjätunnuksella: `GET /me/accounts`.
   Vastauksesta löytyvät sivun `id` ja `access_token`. **Sivun tunnus ei
   vanhene**, toisin kuin käyttäjätunnus.
6. Tallenna GitHubiin **Settings → Secrets and variables → Actions**:

| Nimi | Arvo |
|---|---|
| `FB_PAGE_ID` | sivun `id` kohdasta `/me/accounts` |
| `FB_PAGE_TOKEN` | sivun `access_token` samasta kohdasta |

Ilman näitä salaisuuksia työ toimii normaalisti, mutta ohittaa Facebook-osuuden
ja lähettää pelkän sähköposti-ilmoituksen.

Kokeile ensin ilman julkaisua:

```bash
python scripts/kooste.py --tila viikko --tiedosto kooste.txt
python scripts/facebook.py --tiedosto kooste.txt --kuivaharjoitus
```

Sivun tunnus lakkaa toimimasta, jos vaihdat Facebook-salasanasi, poistat
sovelluksen oikeudet tai menetät sivun ylläpito-oikeuden. Silloin toista
vaiheet 3–6. Graph APIn versio on `v26.0`; sen voi vaihtaa ympäristömuuttujalla
`FB_GRAPH_VERSIO`, kun Meta julkaisee uuden version.

---

## Myöhemmin: muut kylän tapahtumat

Sivu on rakennettu niin, että muut tapahtumat (esim. eläkeläisten kesätori,
talkoot, kesäteatteri) voidaan lisätä samaan listaan ja samaan kalenteriin
ilman että pelien haku muuttuu: ne ovat vain otteluita, joilla on eri `laji`
ja oma lähde. Helpoin tapa on oma tekstitiedosto `scripts/siemendata.txt`:n
tapaan ja sille pieni lukija, jonka tulos yhdistetään otteluihin.

---

## Muistettavaa

- Ottelut voivat siirtyä tai peruuntua. Sivu näyttää sen, mikä tulospalvelussa
  lukee viimeisimmän päivityksen hetkellä.
- Jos toinen liitto on alhaalla päivityshetkellä, sen vanha data säilyy — yksi
  kaatunut rajapinta ei tyhjennä koko sivua.
- Menneet ottelut poistuvat listalta automaattisesti.
