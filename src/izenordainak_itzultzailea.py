import re

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


def izenordainak_itzuli_zu_hi(testua):
    def ordezkatu(match):
        hitza = match.group(0)
        itzulpena = mapaketa_zu_hi.get(hitza.lower())
        if itzulpena is None:
            return hitza
        # Maiuskula-patroia mantendu
        if hitza.isupper():
            return itzulpena.upper()
        if hitza.istitle():
            return itzulpena.capitalize()
        return itzulpena

    # Hitzen mugak errespetatu (adib. 'zureak' ez ordezkatzeko)
    eredua = r'\b(' + '|'.join(re.escape(k) for k in mapaketa_zu_hi) + r')\b'
    return re.sub(eredua, ordezkatu, testua, flags=re.IGNORECASE)


# --- Proba ---
probako_esaldiak = [
    "Ni zurekin joango naiz, opari zuri hau zuretzat delako.",
    "Zuk badakizu egia.",
    "Zutaz hitz egiten dute.",
    "Zuregana noa eta zuregandik itzuliko naiz.",
]
for esaldia in probako_esaldiak:
    print(f"Jat: {esaldia}")
    print(f"Hika: {izenordainak_itzuli_zu_hi(esaldia)}")
    print()
