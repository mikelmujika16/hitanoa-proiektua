import stanza

# 'zu' izenordainaren forma guztien mapaketa 'hi'-rako
# Giltza: hitz-forma (minuskulaz); Balioa: hika forma
mapaketa_zu_hi = {
    "zu":         "hi",          # Absolutiboa (NOR)
    "zuk":        "hik",         # Ergatiboa (NORK)
    "zuri":       "hiri",        # Datiboa (NORI)
    "zure":       "hire",        # Jabetza-genitiboa (NOREN)
    "zurekin":    "hirekin",     # Soziatiboa (NOREKIN)
    "zuretzat":   "hiretzat",    # Destinatiboa/Onuraduna (NORENTZAT)
    "zutaz":      "hitaz",       # Instrumentala/Motibazioa (ZERTAZ)
    "zuregan":    "hiregan",     # Inesibo animatua (NOREGAN)
    "zuregandik": "hiregandik",  # Bizi-ablatiboa animatua (NOREGANDIK)
    "zuregana":   "hiregana",    # Bizi-adlatiboa animatua (NOREGANA)
}

# Stanza-k inoiz PRON gisa sailkatzen ez dituen formak, baina anbiguoak ez direnak:
# zutaz (ADV gisa), zuregandik (ADV gisa), zuregana (PROPN gisa)
beti_ordezkatu = {"zutaz", "zuregandik", "zuregana"}

# 1. Modeloa deskargatu (lehen aldiz exekutatzen bada soilik jaitsi behar da)
stanza.download('eu')

# 2. Pipeline-a hasieratu (tokenizazioa, POS eta lematizazioa)
nlp = stanza.Pipeline('eu', processors='tokenize,pos,lemma', download_method=None)


def izenordainak_itzuli_zu_hi(testua):
    dok = nlp(testua)
    hitz_itzuliak = []

    for esaldia in dok.sentences:
        for hitza in esaldia.words:
            hitz_unekoa = hitza.text
            forma = hitza.text.lower()

            # Bide nagusia: stanza-k PRON+lemma=zu gisa sailkatutakoak
            # (zuk, zure, zurekin, zuretzat, zuregan...)
            if hitza.lemma == "zu" and hitza.upos == "PRON":
                if forma in mapaketa_zu_hi:
                    hitz_unekoa = mapaketa_zu_hi[forma]
            # Bigarren bidea: stanza-k oker sailkatzen dituen forma anbiguogabeak
            # zutaz→ADV, zuregandik→ADV, zuregana→PROPN
            elif forma in beti_ordezkatu:
                hitz_unekoa = mapaketa_zu_hi[forma]

            # Jatorrizkoak maiuskula bazuen, mantendu
            if hitz_unekoa != hitza.text and hitza.text.istitle():
                hitz_unekoa = hitz_unekoa.capitalize()

            hitz_itzuliak.append(hitz_unekoa)

    # Esaldia berreraiki (puntuazio-zeinuen tarteak garbitu gabe oraingoz)
    azken_testua = " ".join(hitz_itzuliak)
    return azken_testua


# --- Proba ---
probako_esaldia = "Ni zurekin joango naiz, opari zuri hau zuretzat delako."
emaitza = izenordainak_itzuli_zu_hi(probako_esaldia)

print(f"Jatorrizkoa: {probako_esaldia}")
print(f"Hika:        {emaitza}")
# Espero den emaitza: Ni hirekin joango naiz, opari zuri hau hiretzat delako.
# Oharra: 'zuri' hitzak anbiguotasuna du euskaraz ('zuri' adjektiboa = zuria kolorea),
# eta stanza-k 'ADJ' gisa sailkatzen du testuinguru honetan, ez PRON gisa.
