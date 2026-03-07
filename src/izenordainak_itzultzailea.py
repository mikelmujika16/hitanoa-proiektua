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

            # Lema 'zu' den eta izenordaina den egiaztatzen dugu
            # Oharra: stanza-ren euskal modelak ez du 'Case' ezaugarria itzultzen,
            # beraz hitz-forma zuzenean erabiltzen dugu mapaketan bilatzeko
            if hitza.lemma == "zu" and hitza.upos == "PRON":
                forma = hitza.text.lower()

                # Hitz-forma gure mapaketan badago, ordezkapena egiten dugu
                if forma in mapaketa_zu_hi:
                    hitz_unekoa = mapaketa_zu_hi[forma]

                    # Jatorrizkoak maiuskula bazuen, mantendu
                    if hitza.text.istitle():
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
# Espero den emaitza: Ni hirekin joango naiz, hiri opari hau hiretzat delako.
# Oharra: 'zuri' hitzak anbiguotasuna du euskaraz ('zuri' adjektiboa = zuria kolorea),
# eta stanza-k 'ADJ' gisa sailkatzen du testuinguru honetan, ez PRON gisa.
