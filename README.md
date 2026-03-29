# Hitano Itzultzailea

## Zer da?

Hitano Itzultzailea **zukako euskal testua hikara (toka eta noka)** automatikoki bihurtzen duen web aplikazioa da. Euskaltzaindiaren 14. araua (*Adizki alokutiboez, hikako moldea*) oinarri hartuta, aditz-forma alokutiboak, izenordainak eta posesiboak itzultzen ditu denbora errealean.

Gainera, **Latxa** hizkuntza-eredu handiari galderak egiteko aukera ematen du, eta erantzuna zuzenean hikan (toka/noka) jasotzen da.

---

## Funtzionamendu orokorra

Aplikazioak hiru atal nagusi ditu:

### 1. Aditz-formen erauzketa (PDF → JSON)

`src/aditzak_atera.py` scriptak Euskaltzaindiaren 14. arauaren PDFa (`docs/Araua_0014.pdf`) prozesatzen du `pdfplumber` liburutegiarekin. PDFak ez du benetako taula-egiturarik — testua kokapenaren arabera 3 zutabetan antolatuta dago. Scriptak:

1. Orrialde bakoitzeko hitz guztiak x/y koordenatuekin erauzten ditu.
2. Hitzak y-koordenatuaren arabera lerrotan multzokatzen ditu.
3. Lerro bakoitza sailkatzen du: aditz-izena, saila, aldia, datu-lerroa edo baztertzekoa.
4. Datu-lerroetan, hitzak 3 zutabetan banatzen ditu x-koordenatuaren arabera: **zuka**, **toka** eta **noka**.
5. Hiru mailako baliozkotzea egiten du emaitza garbiak bermatzeko.

Emaitza: `json/` karpetan gordetako JSON fitxategiak, 35 aditz eta 1500+ forma-parekin.

### 2. Itzulpen-motorra (`translator.py`)

`HitanoTranslator` klaseak zukako testua hikara (toka/noka) bihurtzen du. Prozesuak bi fase nagusi ditu: **bilaketa-taulen eraikuntza** eta **token-mailako itzulpena**.

#### 2.1. Bilaketa-taulen eraikuntza (`_build_lookup`)

Hasieran, klaseak 3 JSON fitxategi kargatzen ditu eta bi hiztegi handi eraikitzen ditu (`lookup_toka` eta `lookup_noka`), non gako bakoitza zukako forma bat den eta balioa `MappingMeta` objektu bat:

```
MappingMeta(form, lema_verbo, es_segunda_persona, is_verb, aldia)
```

Taulen edukia hiru iturritatik dator:

| Iturria | Deskribapena | Adibidea |
|---|---|---|
| **Aditz-formak** (JSON) | 3 JSON fitxategietatik kargatutako zuka→toka/noka mapaketak. 2. pertsona den ala ez detektatzen du argumentuen arabera (nor/nork/nori eremuak). | `duzu` → `duk` / `dun` |
| **Izenordain-mapa** (`PRONOUN_MAP`) | 30+ zukako izenordain eta haien hikako baliokideak, kasu deklinatu guztiekin. | `zu` → `hi`, `zuri` → `hiri`, `zurekin` → `hirekin` |
| **Posesibo deklinatuak** | `zure-` eta `zeure-` oinarrietatik 26 deklinazio-atzizkirekin automatikoki sortutako mapaketak. | `zurea` → `hirea`, `zeuretik` → `heuretik` |

Gainera, `FORCED_FORM_OVERRIDES` bidez forma zehatz batzuk gainidazten dira lehentasunez (adib. `nago` → `nauk`/`naun`).

#### 2.2. Tokenizazioa

Sarrerako testua token-zerrendara bihurtzen da regex baten bidez (`TOKEN_RE`). Token bakoitza hitz bat (`is_word=True`) edo ez-hitz bat (zuriuneak, puntuazioa...) izan daiteke. Hitz ez diren tokenak aldatu gabe pasatzen dira.

#### 2.3. Token bakoitzaren itzulpen-prozesua

Hitz-token bakoitzerako, hurrengo pauso hauek jarraitzen dira ordena honetan:

**1) "Zuri" desanbiguazioa**

"Zuri" hitza kolore-adjektiboa (*txakur zuri bat*) edo izenordaina (*zuri esan dizut*) izan daiteke. Bi mekanismo daude:

- **Stanza NLP bidez**: zerbitzariak aldez aurretik testu-analisia egiten du (POS etiketatzea) eta kolore posizioak markatzen ditu. Posizio horietan "zuri" ez da itzultzen.
- **Heuristikoa** (Stanza gabe): aurreko hitza aztertzen du — izenordain-testuinguru batean (`nik`, `zuk`, `baina`...) badago, izenordaina da; bestela, kolorea dela suposatzen du.

**2) Mapaketa-ebazpena (`_resolve_mapping`)**

Hitza bilaketa-tauletan bilatzen da. Zuzeneko bat-etortzea ez badago, hiru estrategia konposatu aplikatzen dira ordena honetan:

| Estrategia | Nola funtzionatzen duen | Adibidea |
|---|---|---|
| **`ba-` aurrizkia** | Aurrizkia kentzen du, barneko forma itzultzen du, eta aurrizkia berriro jartzen du. | `badakizu` → `ba-` + `dakizu` → `dakik` → `badakik` |
| **`bait-` aurrizkia** | `bait-` kendu, `d` gehitu hasieran, itzuli, eta `bait-` formara bihurtu (`d` kenduz). | `baituzu` → `d`+`uzu` = `duzu` → `duk` → `baituk` |
| **Mendeko atzizkiak** | Atzizkia (`-lako`, `-nean`, `-la`, `-n`...) kentzen du, oinarria itzultzen du, eta atzizkia berriz eransten du. 30+ atzizki ezagutzen ditu, luzeenetik laburrenera probatuz. | `zarelako` → `zare` → `haiz` → `haizelako` |

Mendeko atzizkiekin forma konposatzean, **loturazko "a"** txertatzen da 2. pertsonako aditz-formak kontsonantez amaitzen direnean eta atzizkia kontsonantez hasten denean:

```
duk + -n → dukan    (ez *dukn)
dun + -lako → dunalako
```

**3) Mendeko perpaus-blokeoa**

Aditz-forma bat mendeko perpaus batean badago (aurrizkia `ba-`, edo atzizkia `-lako`, `-nean`, `-la`...) **eta** ez bada 2. pertsonakoa, **ez da itzultzen**. Arau honek hirugarren pertsonako mendeko aditzak ukitu gabe uzten ditu:

```
"Uste dut Mikel etorri delako" → "delako" EZ da itzultzen (3. pertsona, mendekoa)
"Zuk esan duzulako"           → "duzulako" BAI itzultzen da → "dukalako" (2. pertsona)
```

Orainaldiaren kasuan, `-n` eta `-en` atzizkiak ere blokeatuz gero, "duen", "den" bezalako mendeko formak ukitu gabe geratzen dira.

**4) Letra larri/xehe transferentzia**

Jatorrizko hitzaren formatua mantentzen da itzulpenean:

```
"Zu"  → "Hi"    (lehen letra larria)
"ZUK" → "HIK"   (guztiz larria)
"zuk" → "hik"   (guztiz xehea)
```

**5) HTML nabarmentzea**

Aldatutako hitz bakoitza `<span class="highlight">` etiketa batekin inguratzen da, web interfazean ikusmenez bereizteko.

#### 2.4. Itzulpen-fluxuaren laburpena

```
Sarrera: "Zuk esan duzulako, nik sinesten dizut."
         ───  ────  ────────  ──── ──────────  ─────
          │    │       │        │      │         │
          │    │       │        │      │         └─ dizut → lookup → diat (toka)
          │    │       │        │      └─ sinesten → ez dago mapan → [mantendu]
          │    │       │        └─ nik → ez dago mapan → [mantendu]
          │    │       └─ duzulako → duzu+lako → duk+lako → duk(a)lako
          │    └─ esan → ez dago mapan → [mantendu]
          └─ Zuk → zuk → hik → Hik (larri transferentzia)

Irteera: "Hik esan dukalako, nik sinesten diat."
```

### 3. Web zerbitzaria (`server.py`)

Flask zerbitzari bat eskaintzen du honako API bidekin:

| Bidea | Metodoa | Funtzioa |
|---|---|---|
| `/` | GET | Orri nagusia (itzultzailea) |
| `/latxa` | GET | Latxa txat-orria |
| `/api/translate` | POST | Testua hikara itzuli (toka + noka) |
| `/api/analyze` | POST | Testua Stanza NLP-rekin aztertu (POS, lema) |
| `/api/latxa` | POST | Latxa LLM-ri galdera egin eta erantzuna hikan itzuli |

**Stanza** NLP liburutegia erabiltzen du euskarazko testu-analisia egiteko (tokenizazioa, POS etiketatzea, lematizazioa), eta horrek "zuri" kolore/izenordain desanbiguazioan laguntzen du.

**Latxa** integratzeko, OpenAI SDK-a erabiltzen du `.env` fitxategiko konfigurazioarekin.

### 4. Web interfazea

- **`index.html`**: SPA (Single Page Application) nagusia. Erabiltzaileak zukako testua idazten du eta toka/noka itzulpenak denbora errealean agertzen dira, aldaketak nabarmenduta. Stanza bidezko analisi linguistikoa ere erakusten du.
- **`latxa.html`**: Latxa hizkuntza-ereduari galderak egiteko interfazea. Erantzuna jatorrizkoan eta hikan (toka/noka) erakusten du.

---

## Proiektuaren egitura

```
hitanoa-proiektua/
├── index.html                  # SPA — Hitano Itzultzailea (orri nagusia)
├── latxa.html                  # Latxa + Hika txat-orria
├── server.py                   # Flask web zerbitzaria eta API-ak
├── translator.py               # Itzulpen-motorra (HitanoTranslator)
├── tests.py                    # Unitate-probak (12 test)
├── requirements.txt            # Python dependentziak
├── src/
│   ├── aditzak_atera.py        # PDF → JSON erauzketa-scripta
│   ├── aditzak_atera_aditzakeus.py
│   └── izenordainak_itzultzailea.py
├── json/
│   ├── aditz_alokutiboak.json           # 14. arautik ateratako formak
│   ├── aditz_trinkoa_argumentala.json   # Aditz trinko argumentalak
│   └── aditzak_argumentala_bateratua.json # Forma bateratuak
├── docs/
│   ├── Araua_0014.pdf          # Euskaltzaindiaren 14. araua
│   ├── EBE-eranskinak.pdf
│   └── EuskalAditzLaguntzailea.pdf
└── README.md
```

---

## Aplikazioa martxan jartzeko pausoak

### 1. Aurrebaldintzak

- **Python 3.10+** instalatuta eduki.
- (Aukerakoa) `git` bertsio-kontrolerako.

### 2. Proiektua deskargatu

```bash
git clone https://github.com/mikelmujika16/hitanoa-proiektua.git
cd hitanoa-proiektua
```

### 3. Ingurune birtuala sortu eta aktibatu

```bash
python -m venv .venv

# Linux / macOS:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 4. Dependentziak instalatu

```bash
pip install -r requirements.txt
```

Honek `flask`, `stanza` eta `openai` instalatuko ditu. Stanza euskarazko eredua automatikoki deskargatuko da lehen aldiz zerbitzaria abiaraztean.

### 5. (Aukerakoa) Latxa konfiguratu

Latxa LLM txat-funtzioa erabili nahi baduzu, sortu `.env` fitxategi bat proiektuaren erroan:

```env
LATXA_API_KEY=zure_api_gakoa
LATXA_API_URL=https://zure-latxa-zerbitzaria/v1
LATXA_MODEL=ereduaren_izena
```

Hau ez da beharrezkoa itzultzaile nagusia erabiltzeko.

### 6. Zerbitzaria abiarazi

```bash
python server.py
```

Lehen aldiz exekutatzen denean, Stanza-k euskarazko NLP eredua deskargatuko du (minutu batzuk). Ondoren:

```
Zerbitzaria abiatzen: http://localhost:5000
```

### 7. Nabigatzailean ireki

- **Itzultzailea**: [http://localhost:5000](http://localhost:5000)
- **Latxa txata**: [http://localhost:5000/latxa](http://localhost:5000/latxa)

### 8. (Aukerakoa) Testak exekutatu

```bash
python tests.py
```

12 unitate-proba exekutatuko dira itzulpen-motorraren zuzentasuna egiaztatzeko.

---

## JSON datu-formatua

Aditz-forma bakoitzak egitura hau du:

```json
{
    "aditza": "izan",
    "saila": "NOR bakarreko saila",
    "aldia": "ORAINALDIA",
    "zuka": "naiz",
    "hika_toka": "nauk",
    "hika_noka": "naun",
    "orrialdea": 3
}
```

| Eremua | Deskribapena |
|---|---|
| `aditza` | Aditzaren izena (adib. *izan*, *Egon*, **edin*) |
| `saila` | Saila (adib. *NOR bakarreko saila*) |
| `aldia` | Aldia (adib. *ORAINALDIA*, *IRAGANALDIA*) |
| `zuka` | Zukako forma |
| `hika_toka` | Hikako forma (toka, maskulinoa) |
| `hika_noka` | Hikako forma (noka, femeninoa) |
| `orrialdea` | PDFaren orrialde-zenbakia |

## Aditzak (35)

| Aditza | Sarrera kopurua |
|--------|-----------------|
| izan | 80 |
| *edin | 48 |
| *edun | 60 |
| *-i- | 120 |
| *ezan | 108 |
| *iro- | 12 |
| Egon | 80 |
| Etorri | 80 |
| Ibili | 80 |
| Joan | 80 |
| Atxeki | 36 |
| Jarraiki | 36 |
| Ekin | 24 |
| Jari | 24 |
| Etzan | 12 |
| Eduki | 36 |
| Ekarri | 72 |
| Eraman | 72 |
| Erabili | 72 |
| Ezagutu | 36 |
| Egin | 96 |
| Ikusi | 24 |
| Jakin | 24 |
| Entzun | 24 |
| Erakutsi | 24 |
| Eroan | 24 |
| Ihardun | 12 |
| Iharduki | 12 |
| Erauntsi | 12 |
| Eutsi | 12 |
| Iraun | 12 |
| Irudi | 12 |
| Iritzi | 36 |
| *Io | 64 |
| Erran | 4 |
| **Guztira** | **1560** |

---

## Teknologiak

- **Python 3.10+** — Backend-a eta erauzketa-scriptak
- **Flask** — Web zerbitzaria eta REST API-a
- **Stanza (Stanford NLP)** — Euskarazko testu-analisia (POS, lema)
- **OpenAI SDK** — Latxa LLM integrazioa
- **pdfplumber** — PDF erauzketa (aditz-formak ateratzeko scripta)
- **HTML/CSS/JS** — Frontend SPA (framework-ik gabe)

## Lizentzia

Proiektu hau ikerketa eta hezkuntza helburuetarako da. Euskaltzaindiaren arauaren edukia Euskaltzaindiarena da.