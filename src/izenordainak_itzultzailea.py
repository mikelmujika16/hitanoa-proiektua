import re

# 'zu' izenordainaren forma guztien mapaketa 'hi'-rako
# Giltza: hitz-forma (minuskulaz); Balioa: hika forma
mapaketa_zu_hi = {
    # Forma arruntak
    "zu":            "hi",            # NOR
    "zuk":           "hik",           # NORK
    "zuri":          "hiri",          # NORI
    "zure":          "hire",          # NOREN
    "zurekin":       "hirekin",       # NOREKIN
    "zuretzat":      "hiretzat",      # NORENTZAT
    "zutaz":         "hitaz",         # ZERTAZ
    "zuregan":       "hiregan",       # NORENGAN (zu-re-gan)
    "zugan":         "higan",         # NORENGAN (zu-gan)
    "zuregandik":    "hiregandik",    # NORENGANDIK (zu-re-gandik)
    "zugandik":      "higandik",      # NORENGANDIK (zu-gandik)
    "zuregana":      "hiregana",      # NORENGANA (zu-re-gana)
    "zugana":        "higana",        # NORENGANA (zu-gana)
    "zureganantz":   "hireganantz",   # NORENGANANTZ (zu-re-ganantz)
    "zuganantz":     "higanantz",     # NORENGANANTZ (zu-ganantz)
    "zureganaino":   "hireganaino",   # NORENGANAINO (zu-re-ganaino)
    "zuganaino":     "higanaino",     # NORENGANAINO (zu-ganaino)
    "zuregatik":     "hiregatik",     # NORENGATIK (zu-re-gatik)
    "zugatik":       "higatik",       # NORENGATIK (zu-gatik)
    
    # Forma indartuak
    "zeu":           "heu",
    "zeuk":          "heuk",
    "zeuri":         "heuri",
    "zeure":         "heure",
    "zeurekin":      "heurekin",
    "zeuretzat":     "heuretzat",
    "zeutaz":        "heutaz",
    "zeuregan":      "heuregan",      # NORENGAN (zeu-re-gan)
    "zeugan":        "heugan",        # NORENGAN (zeu-gan)
    "zeuregandik":   "heuregandik",   # NORENGANDIK (zeu-re-gandik)
    "zeugandik":     "heugandik",     # NORENGANDIK (zeu-gandik)
    "zeuregana":     "heuregana",     # NORENGANA (zeu-re-gana)
    "zeugana":       "heugana",       # NORENGANA (zeu-gana)
    "zeureganantz":  "heureganantz",  # NORENGANANTZ (zeu-re-ganantz)
    "zeuganantz":    "heuganantz",    # NORENGANANTZ (zeu-ganantz)
    "zeureganaino":  "heureganaino",  # NORENGANAINO (zeu-re-ganaino)
    "zeuganaino":    "heuganaino",    # NORENGANAINO (zeu-ganaino)
    "zeuregatik":    "heuregatik",    # NORENGATIK (zeu-re-gatik)
    "zeugatik":      "heugatik",      # NORENGATIK (zeu-gatik)
}

deklinabide_atzizkiak = [
    "a", "ak", "ari", "aren", "arekin", "arentzat", "az",
    "an", "ra", "tik", "ko", "rantz", "raino",
    "ek", "ei", "en", "ekin", "entzat", "ez",
    "etan", "etara", "etatik", "etako", "etarantz", "etaraino",
]

for jatorria, helburua in (("zure", "hire"), ("zeure", "heure")):
    for atzizkia in deklinabide_atzizkiak:
        mapaketa_zu_hi.setdefault(f"{jatorria}{atzizkia}", f"{helburua}{atzizkia}")


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
