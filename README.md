# Hitano Itzultzailea

Proiektu honen helburua **Euskaltzaindiaren 14. araua** (*Adizki alokutiboez, hikako moldea*) PDF formatutik irakurri eta bertako aditz-forma guztiak JSON datu-egitura batera erauztea da, eta web aplikazio bat eskaintzea zukako testua hikara (toka/noka) automatikoki itzultzeko.

## Zer da?

Euskaltzaindiaren 14. arauak hikako moldeko adizki alokutiboak biltzen ditu: **zuka**, **toka** eta **noka** formak, 35 aditzentzat. PDF dokumentuan datuak 3 zutabetan agertzen dira, baina ez dute benetako taula-egiturarik — testu kokatuak dira soilik.

Proiektu honek bi gauza egiten ditu:
1. **Erauzketa**: PDF-tik 1560 aditz-forma automatikoki erauzten ditu JSON formatuan.
2. **Itzulpena**: SPA (Single Page Application) bat eskaintzen du, non zukako testua idaztean hikako baliokideak (toka eta noka) denbora errealean erakusten diren.

## Proiektuaren egitura

```
hitanoa-proiektua/
├── index.html             # SPA — Hitano Itzultzailea (web aplikazioa)
├── src/
│   └── aditzak_atera.py   # Erauzketa-scripta (Python)
├── json/
│   └── aditzak_hika.json  # Irteerako JSON fitxategia (1560 sarrera)
├── docs/
│   └── Araua_0014.pdf     # Euskaltzaindiaren 14. araua (61 orrialde)
└── README.md
```

## Nola funtzionatzen du?

`aditzak_atera.py` scriptak `pdfplumber` liburutegia erabiltzen du PDFa prozesatzeko. Prozesua honela doa:

1. **Hitz-mailako erauzketa**: `pdfplumber.extract_words()` erabiliz, orrialde bakoitzeko hitz guztiak ateratzen dira beren x/y koordenatuekin.
2. **Lerroka multzokatzea**: Hitzak y-koordenatuaren arabera (tolerantzia: 3.0 pixel) lerrotan biltzen dira.
3. **Lerroen klasifikazioa**: Lerro bakoitza mota batean sailkatzen da:
   - `verb` — Aditz-izena (35 ezagun)
   - `section` — Saila (NOR, NOR-NORI, NOR-NORK, etab.)
   - `tense` — Aldia (ORAINALDIA, IRAGANALDIA, ALEGIAZKOA, etab.)
   - `data` — Aditz-formak dituen datu-lerroa
   - `footer` / `other` — Baztertzekoak
4. **Zutabe-banaketa x-koordenatuen bidez**: Datu-lerroetan, hitzak 3 zutabetan banatzen dira koordenatuak erabiliz:
   - Zuka: `x0 < 130`
   - Toka: `130 ≤ x0 < 270`
   - Noka: `x0 ≥ 270`
5. **Hiru mailako baliozkotzea**:
   - Hitz-maila: hitz bakoitza `[a-z(),\-]+` patroiarekin bat datorren egiaztatzen da.
   - Zutabe-maila: 3 zutabeek edukia izan behar dute.
   - Eduki-maila: zutabe bakoitzeko koma bidez bereizitako elementu bakoitza hitz bakarra da (prosa baztertzeko).

## Irteerako JSON formatua

Sarrera bakoitzak egitura hau du:

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

| Eremua       | Deskribapena                                    |
|--------------|------------------------------------------------|
| `aditza`     | Aditzaren izena (adib. *izan*, *Egon*, **edin*) |
| `saila`      | Saila (adib. *NOR bakarreko saila*)             |
| `aldia`      | Aldia (adib. *ORAINALDIA*, *IRAGANALDIA*)       |
| `zuka`       | Zukako forma                                    |
| `hika_toka`  | Hikako forma (toka, masculinoa)                 |
| `hika_noka`  | Hikako forma (noka, femeninoa)                  |
| `orrialdea`  | PDFaren orrialde-zenbakia                       |

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

## Instalazioa eta erabilera

### Aurrebaldintzak

- Python 3.10+
- `pdfplumber` liburutegia

### Erauzketa-scripta

```bash
pip install pdfplumber
python src/aditzak_atera.py
```

Scriptak `docs/Araua_0014.pdf` irakurriko du eta `json/aditzak_hika.json` fitxategia sortuko du.

### Web aplikazioa (SPA)

Web aplikazioa HTTP zerbitzari baten bidez zerbitzatu behar da (`fetch` erabiliz JSON kargatzen duelako):

```bash
python -m http.server 8000
```

Ondoren, ireki [http://localhost:8000](http://localhost:8000) nabigatzailean.

**Nola erabili:**
1. Idatzi zukako testua sarrera-eremuan.
2. Denbora errealean, tokako eta nokako baliokideak irteerako eremuetan agertuko dira.
3. Ordezkatutako aditz-formak nabarmenduta agertzen dira.
4. "Kopiatu" botoia erabiliz itzulpena arbelean kopiatu daiteke.

## Erronka teknikoak

PDFa ez zen ohiko taulak zituen dokumentu bat. Erronka nagusiak:

- **Taula-egiturarik eza**: `pdfplumber.extract_tables()` ezerk ez zuen itzultzen, 0 taula 61 orrialdeetan. Testua posizio bidez kokatuta zegoen soilik.
- **Zutabe-banaketa**: Testu-moduan, hitz luzeak zutabe arteko espazioak laburtzen zituzten, eta hitz batetik bestera espazio bakarra zegoen. X-koordenatuen bidezko banaketak arazo hau konpondu zuen.
- **Prosa-testuak**: 1-2. eta 17-18. orrialdeek sarrera-testua zuten (prosa), formatuz datu-lerroaren antza zutenak. Hiru mailako baliozkotzeak positibo faltsuak baztertu zituen.

## Lizentzia

Proiektu hau ikerketa eta hezkuntza helburuetarako da. Euskaltzaindiaren arauaren edukia Euskaltzaindiarena da.