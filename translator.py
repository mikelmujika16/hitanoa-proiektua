import json
import os
import re
import html
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


DATA_FILES = [
    "json/aditz_alokutiboak.json",
    "json/aditzak_argumentala_bateratua.json",
    "json/aditz_trinkoa_argumentala.json",
]

FORCED_FORM_OVERRIDES = {
    "toka": {
        "nago": "nauk",
    },
    "noka": {
        "nago": "naun",
    },
}

PRONOUN_MAP = {
    "zu": "hi",
    "zuk": "hik",
    "zuri": "hiri",
    "zure": "hire",
    "zurekin": "hirekin",
    "zuretzat": "hiretzat",
    "zutaz": "hitaz",
    "zuregan": "hiregan",
    "zugan": "higan",
    "zuregandik": "hiregandik",
    "zugandik": "higandik",
    "zuregana": "hiregana",
    "zugana": "higana",
    "zureganantz": "hireganantz",
    "zuganantz": "higanantz",
    "zureganaino": "hireganaino",
    "zuganaino": "higanaino",
    "zuregatik": "hiregatik",
    "zugatik": "higatik",
    "zeu": "heu",
    "zeuk": "heuk",
    "zeuri": "heuri",
    "zeure": "heure",
    "zeurekin": "heurekin",
    "zeuretzat": "heuretzat",
    "zeutaz": "heutaz",
    "zeuregan": "heuregan",
    "zeugan": "heugan",
    "zeuregandik": "heuregandik",
    "zeugandik": "heugandik",
    "zeuregana": "heuregana",
    "zeugana": "heugana",
    "zeureganantz": "heureganantz",
    "zeuganantz": "heuganantz",
    "zeureganaino": "heureganaino",
    "zeuganaino": "heuganaino",
    "zeuregatik": "heuregatik",
    "zeugatik": "heugatik",
}

POSSESSIVE_DECLINED_SUFFIXES = (
    "a", "ak", "ari", "aren", "arekin", "arentzat", "az",
    "an", "ra", "tik", "ko", "rantz", "raino",
    "ek", "ei", "en", "ekin", "entzat", "ez",
    "etan", "etara", "etatik", "etako", "etarantz", "etaraino",
)

for source_base, target_base in (("zure", "hire"), ("zeure", "heure")):
    for suffix in POSSESSIVE_DECLINED_SUFFIXES:
        PRONOUN_MAP.setdefault(f"{source_base}{suffix}", f"{target_base}{suffix}")

SUBORDINATE_SUFFIXES = (
    "eino", "eno", "larik", "elarik", "nean", "enean", "neko", "eneko",
    "nerako", "enerako", "netik", "enetik", "lako", "elako", "lakoz",
    "elakoz", "lakotz", "elakotz", "lakoan", "elakoan", "na", "ena",
    "nentz", "enentz", "netz", "enetz", "nez", "enez", "nik", "enik",
    "la", "ela",
)

# Longest first, to avoid partial matches.
COMPOSITION_SUFFIXES = tuple(sorted(set(SUBORDINATE_SUFFIXES + ("n", "en")), key=len, reverse=True))

# Atzizkien "e"-rik gabeko bertsio multzoa: "elako" -> "lako", "enean" -> "nean", etab.
# _compose_with_suffix funtzioan erabiltzen da loturazko "e" kentzeko.
_VOWEL_LINK_STRIPPED = frozenset(
    s[1:] for s in SUBORDINATE_SUFFIXES if s.startswith("e") and len(s) > 1
) | {"n"}  # "en" -> "n" ere kontuan hartu

TOKEN_RE = re.compile(r"([a-zA-ZñÑçÇáéíóúàèìòùäëïöüâêîôû]+)|([^a-zA-ZñÑçÇáéíóúàèìòùäëïöüâêîôû]+)")

# Small context list for the "zuri" color-vs-pronoun heuristic.
ZURI_LEFT_PRONOUN_CONTEXT = {
    "ni", "nik", "hi", "hik", "hura", "hark", "gu", "guk", "haiek", "haiek",
    "zu", "zuk", "zuek", "baina", "eta", "edo", "zeuk", "heuk",
}


@dataclass
class MappingMeta:
    form: str
    lema_verbo: str
    es_segunda_persona: bool
    is_verb: bool
    aldia: str = ""
    source: str = ""


@dataclass
class Token:
    text: str
    is_word: bool


def _normalize_aditza(entry: dict) -> str:
    aditza = entry.get("aditza")
    if not isinstance(aditza, str):
        return ""
    return aditza.strip().lower()


def _detect_second_person_argumental(entry: dict, source_url: str) -> bool:
    if source_url != "json/aditz_alokutiboak.json":
        return True

    values = [entry.get("nor"), entry.get("nork"), entry.get("nori")]
    values = [str(v).strip().lower() for v in values if v]
    if any(v in {"zu", "zuk", "zuri"} for v in values):
        return True

    saila = entry.get("saila")
    if isinstance(saila, str) and re.search(r"\(zu\s+(nork|nori)\)", saila, flags=re.IGNORECASE):
        return True

    return False


def no_es_verbo_como_bada(verbo_original: str) -> bool:
    return verbo_original != "bada"


def es_subordinada_bloqueada(verbo_original: str, meta: MappingMeta) -> bool:
    if meta.es_segunda_persona:
        return False

    if verbo_original.startswith("ba") and no_es_verbo_como_bada(verbo_original):
        return True

    if verbo_original.endswith(SUBORDINATE_SUFFIXES):
        return True

    # -n / -en bakarrik blokeatu ORAINALDIA denean.
    if verbo_original.endswith(("n", "en")) and meta.aldia == "ORAINALDIA":
        return True

    return False


def _transfer_case(original: str, translated: str) -> str:
    if original.isupper() and original != original.lower():
        return translated.upper()
    if original[:1].isupper() and original[:1] != original[:1].lower():
        return translated[:1].upper() + translated[1:]
    return translated


def _tokenize(text: str) -> List[Token]:
    return [Token(text=m.group(0), is_word=bool(m.group(1))) for m in TOKEN_RE.finditer(text)]


def _is_probably_color_zuri(tokens: List[Token], index: int) -> bool:
    token = tokens[index]
    if token.text.lower() != "zuri":
        return False

    prev_word = next((t.text.lower() for t in reversed(tokens[:index]) if t.is_word), None)
    next_word = next((t.text.lower() for t in tokens[index + 1:] if t.is_word), None)

    if prev_word and prev_word not in ZURI_LEFT_PRONOUN_CONTEXT and next_word:
        return True
    return False


def _ends_with_consonant(word: str) -> bool:
    if not word:
        return False
    last = word[-1].lower()
    return last.isalpha() and last not in {"a", "e", "i", "o", "u"}


def _ends_with_vowel(word: str) -> bool:
    if not word:
        return False
    return word[-1].lower() in {"a", "e", "i", "o", "u"}


def _compose_with_suffix(base_form: str, suffix: str, meta: MappingMeta) -> str:
    # Argumentala bateratua: forma "k"-z amaitzen denean mendeko atzizkia gehitzean,
    # "k" -> "a" bihurtu: duk + lako -> dualako, duk + n -> duan.
    if (meta.is_verb and meta.source == "json/aditzak_argumentala_bateratua.json"
            and base_form.endswith("k") and suffix):
        base_form = base_form[:-1] + "a"
    # 2. argumentaleko aditzetan, forma kontsonantez amaitzen denean,
    # mendeko atzizkien aurretik loturazko "a" txertatu:
    # duk + n -> dukan, duk + lako -> dukalako.
    if meta.is_verb and meta.es_segunda_persona and _ends_with_consonant(base_form) and suffix:
        if suffix[0].lower() not in {"a", "e", "i", "o", "u"}:
            return f"{base_form}a{suffix}"
    # 2. argumentaleko aditzetan, hikako forma "a"-z amaitzen denean
    # eta atzizkiak loturazko "e"-z hasten denean (elako, enean, ela...),
    # "e" hori kendu: hoa + elako -> hoalako (ez *hoaelako).
    # "a"-z ez amaitzen denean "e" mantendu: hago + elako -> hagoelako.
    if meta.is_verb and meta.es_segunda_persona and base_form.endswith("a") and suffix:
        if suffix.startswith("e") and len(suffix) > 1 and suffix[1:] in _VOWEL_LINK_STRIPPED:
            return f"{base_form}{suffix[1:]}"
    # Hikako forma "a"-z ez den bokala amaitzen denean eta atzizkia "e-gabeko" bertsioa
    # denean (_VOWEL_LINK_STRIPPED-en), loturazko "e" txertatu:
    # hago + la -> hagoela, hago + lako -> hagoelako.
    if meta.is_verb and meta.es_segunda_persona and _ends_with_vowel(base_form) and not base_form.endswith("a") and suffix:
        if suffix in _VOWEL_LINK_STRIPPED:
            return f"{base_form}e{suffix}"
    return f"{base_form}{suffix}"


def _to_bait_form(mapped_form: str) -> str:
    if mapped_form.startswith("d"):
        return f"bait{mapped_form[1:]}"
    if mapped_form.startswith("g"):
        return f"baik{mapped_form[1:]}"
    return f"bait{mapped_form}"


def _resolve_mapping(key: str, lookup: Dict[str, MappingMeta]) -> Tuple[Optional[MappingMeta], str]:
    direct = lookup.get(key)
    if direct:
        return direct, ""

    # Peel and re-attach ba- prefix.
    if key.startswith("ba") and len(key) > 2 and no_es_verbo_como_bada(key):
        sub = key[2:]
        mapped, built = _resolve_mapping(sub, lookup)
        if mapped:
            composed = MappingMeta(
                form="ba" + (built if built else mapped.form),
                lema_verbo=mapped.lema_verbo,
                es_segunda_persona=mapped.es_segunda_persona,
                is_verb=mapped.is_verb,
                aldia=mapped.aldia,
                source=mapped.source,
            )
            return composed, composed.form

    # Conditional-conclusion bait- forms: baituzu -> (duzu -> duk) -> baituk.
    # Also: baitzara -> (zara -> haiz) -> baithaiz,
    #        baikaituzu -> (gaituzu -> gaituk) -> baikaituk.
    bait_candidates: list[str] = []
    if key.startswith("bait") and len(key) > 4:
        bait_candidates = ["d" + key[4:], key[4:]]
    elif key.startswith("baik") and len(key) > 4:
        bait_candidates = ["g" + key[4:]]

    for normalized in bait_candidates:
        mapped, built = _resolve_mapping(normalized, lookup)
        if mapped and mapped.is_verb and mapped.es_segunda_persona:
            hika_base = built if built else mapped.form
            bait_form = _to_bait_form(hika_base)
            composed = MappingMeta(
                form=bait_form,
                lema_verbo=mapped.lema_verbo,
                es_segunda_persona=mapped.es_segunda_persona,
                is_verb=mapped.is_verb,
                aldia=mapped.aldia,
                source=mapped.source,
            )
            return composed, composed.form

    # Suffix composition for subordinated variants (zarelako, naizenean, ...).
    for suffix in COMPOSITION_SUFFIXES:
        if not key.endswith(suffix) or len(key) <= len(suffix):
            continue

        raw_base = key[:-len(suffix)]
        for candidate_base, strip_trailing_n in (
            (raw_base, False),
            (raw_base + "n", True),
            (raw_base + "a", False),
        ):
            meta = lookup.get(candidate_base)
            if not meta:
                continue

            # "duzuelako" bezalako formak "zuek"-en forma dira (duzu + e + lako),
            # ez "zu"-ren forma (duzu + elako). Itzulpena ez egin.
            if (meta.source == "json/aditzak_argumentala_bateratua.json"
                    and candidate_base.endswith("zu")
                    and suffix.startswith("e")):
                continue

            hika_form = meta.form
            # Oinarrizko formari amaierako "n" kendu atzizkia gehitu aurretik
            # (zenuen -> huan: zenuelako = zenue+lako -> hua+lako = hualako).
            if strip_trailing_n and hika_form.endswith("n"):
                hika_form = hika_form[:-1]

            composed = MappingMeta(
                form=_compose_with_suffix(hika_form, suffix, meta),
                lema_verbo=meta.lema_verbo,
                es_segunda_persona=meta.es_segunda_persona,
                is_verb=meta.is_verb,
                aldia=meta.aldia,
                source=meta.source,
            )
            return composed, composed.form

    return None, ""


class HitanoTranslator:
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.dirname(os.path.abspath(__file__))
        self.lookup_toka, self.lookup_noka = self._build_lookup()

    def _load_data(self) -> List[dict]:
        all_data: List[dict] = []
        for rel_path in DATA_FILES:
            full_path = os.path.join(self.project_root, rel_path)
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data:
                if "zuka" not in entry or "hika_toka" not in entry or "hika_noka" not in entry:
                    continue
                item = dict(entry)
                item["__source_url"] = rel_path
                all_data.append(item)
        return all_data

    def _build_lookup(self) -> Tuple[Dict[str, MappingMeta], Dict[str, MappingMeta]]:
        toka: Dict[str, MappingMeta] = {}
        noka: Dict[str, MappingMeta] = {}

        for entry in self._load_data():
            zukas = [s.strip() for s in entry["zuka"].split(",") if s.strip()]
            tokas = [s.strip() for s in entry["hika_toka"].split(",") if s.strip()]
            nokas = [s.strip() for s in entry["hika_noka"].split(",") if s.strip()]

            for i, zu in enumerate(zukas):
                key = zu.lower()
                t_val = tokas[i] if i < len(tokas) else (tokas[0] if tokas else "")
                n_val = nokas[i] if i < len(nokas) else (nokas[0] if nokas else "")
                lemma = _normalize_aditza(entry)
                aldia = str(entry.get("aldia", "")).strip().upper()
                es_segunda = _detect_second_person_argumental(entry, entry["__source_url"])

                source = entry["__source_url"]
                t_meta = MappingMeta(t_val, lemma, es_segunda, True, aldia, source)
                n_meta = MappingMeta(n_val, lemma, es_segunda, True, aldia, source)

                if key not in toka:
                    toka[key] = t_meta
                elif es_segunda:
                    prev = toka[key]
                    prev.es_segunda_persona = True
                    if not prev.lema_verbo and lemma:
                        prev.lema_verbo = lemma
                    if not prev.aldia and aldia:
                        prev.aldia = aldia

                if key not in noka:
                    noka[key] = n_meta
                elif es_segunda:
                    prev = noka[key]
                    prev.es_segunda_persona = True
                    if not prev.lema_verbo and lemma:
                        prev.lema_verbo = lemma
                    if not prev.aldia and aldia:
                        prev.aldia = aldia

        for zu, hi in PRONOUN_MAP.items():
            pron_meta = MappingMeta(hi, "", True, False, "")
            if zu not in toka:
                toka[zu] = pron_meta
            if zu not in noka:
                noka[zu] = pron_meta

        # Lexical preference overrides for expected hitano outputs.
        for zuka, hika in FORCED_FORM_OVERRIDES["toka"].items():
            toka[zuka] = MappingMeta(hika, "izan", False, True, "")
        for zuka, hika in FORCED_FORM_OVERRIDES["noka"].items():
            noka[zuka] = MappingMeta(hika, "izan", False, True, "")

        return toka, noka

    def _translate_with_lookup_detailed(
        self,
        text: str,
        lookup: Dict[str, MappingMeta],
        zuri_color_word_positions: Optional[set[int]] = None,
    ) -> Tuple[str, str, int]:
        tokens = _tokenize(text)
        out_plain: List[str] = []
        out_html: List[str] = []
        count = 0
        word_index = -1
        zuri_positions = zuri_color_word_positions or set()

        for i, token in enumerate(tokens):
            if not token.is_word:
                out_plain.append(token.text)
                out_html.append(html.escape(token.text))
                continue

            word_index += 1

            key = token.text.lower()

            # Stanza bidez markatutako kasuetan, "zuri" kolore gisa mantendu.
            if key == "zuri" and word_index in zuri_positions:
                out_plain.append(token.text)
                out_html.append(html.escape(token.text))
                continue

            # Heuristic disambiguation: txakur zuri bat -> color adjective, do not map to "hiri".
            if key == "zuri" and not zuri_positions and _is_probably_color_zuri(tokens, i):
                out_plain.append(token.text)
                out_html.append(html.escape(token.text))
                continue

            mapped, built = _resolve_mapping(key, lookup)
            if not mapped:
                out_plain.append(token.text)
                out_html.append(html.escape(token.text))
                continue

            if mapped.is_verb and es_subordinada_bloqueada(key, mapped):
                out_plain.append(token.text)
                out_html.append(html.escape(token.text))
                continue

            translated = built if built else mapped.form
            translated = _transfer_case(token.text, translated)
            out_plain.append(translated)
            out_html.append(f'<span class="highlight">{html.escape(translated)}</span>')
            count += 1

        return "".join(out_plain), "".join(out_html), count

    def _translate_with_lookup(
        self,
        text: str,
        lookup: Dict[str, MappingMeta],
        zuri_color_word_positions: Optional[set[int]] = None,
    ) -> str:
        plain, _, _ = self._translate_with_lookup_detailed(text, lookup, zuri_color_word_positions)
        return plain

    def translate_toka(self, text: str, zuri_color_word_positions: Optional[set[int]] = None) -> str:
        return self._translate_with_lookup(text, self.lookup_toka, zuri_color_word_positions)

    def translate_noka(self, text: str, zuri_color_word_positions: Optional[set[int]] = None) -> str:
        return self._translate_with_lookup(text, self.lookup_noka, zuri_color_word_positions)

    def translate_toka_detailed(
        self,
        text: str,
        zuri_color_word_positions: Optional[set[int]] = None,
    ) -> dict:
        plain, rendered_html, count = self._translate_with_lookup_detailed(
            text,
            self.lookup_toka,
            zuri_color_word_positions,
        )
        return {"plain": plain, "html": rendered_html, "count": count}

    def translate_noka_detailed(
        self,
        text: str,
        zuri_color_word_positions: Optional[set[int]] = None,
    ) -> dict:
        plain, rendered_html, count = self._translate_with_lookup_detailed(
            text,
            self.lookup_noka,
            zuri_color_word_positions,
        )
        return {"plain": plain, "html": rendered_html, "count": count}

    def translate_both(self, text: str, zuri_color_word_positions: Optional[set[int]] = None) -> Tuple[str, str]:
        return (
            self.translate_toka(text, zuri_color_word_positions),
            self.translate_noka(text, zuri_color_word_positions),
        )

    def translate_both_detailed(self, text: str, zuri_color_word_positions: Optional[set[int]] = None) -> dict:
        toka = self.translate_toka_detailed(text, zuri_color_word_positions)
        noka = self.translate_noka_detailed(text, zuri_color_word_positions)
        return {"toka": toka, "noka": noka}

    def explain(self, text: str, zuri_color_word_positions: Optional[set[int]] = None) -> List[dict]:
        """Return a step-by-step trace of the translation for each token."""
        tokens = _tokenize(text)
        steps: List[dict] = []
        word_index = -1
        zuri_positions = zuri_color_word_positions or set()

        for i, token in enumerate(tokens):
            if not token.is_word:
                steps.append({"token": token.text, "type": "separator"})
                continue

            word_index += 1
            key = token.text.lower()
            step: dict = {
                "token": token.text,
                "type": "word",
                "key": key,
            }

            # "zuri" color check
            if key == "zuri" and word_index in zuri_positions:
                step["action"] = "unchanged"
                step["reason"] = '"zuri" kolore gisa detektatua (Stanza NLP)'
                steps.append(step)
                continue

            if key == "zuri" and not zuri_positions and _is_probably_color_zuri(tokens, i):
                step["action"] = "unchanged"
                step["reason"] = '"zuri" kolore-adjektiboa (heuristikoa)'
                steps.append(step)
                continue

            # Try toka lookup for explanation (toka as representative)
            toka_mapped, toka_built = _resolve_mapping(key, self.lookup_toka)
            noka_mapped, noka_built = _resolve_mapping(key, self.lookup_noka)

            if not toka_mapped and not noka_mapped:
                step["action"] = "unchanged"
                step["reason"] = "Ez dago mapan (ez aditz-forma, ez izenordain)"
                steps.append(step)
                continue

            # Use toka as representative for rule explanation
            mapped = toka_mapped or noka_mapped
            built = toka_built or noka_built

            # Check subordinate blocking
            if mapped.is_verb and es_subordinada_bloqueada(key, mapped):
                step["action"] = "blocked"
                reason_parts = []
                if key.startswith("ba") and no_es_verbo_como_bada(key):
                    reason_parts.append('ba- aurrizkia')
                elif key.endswith(SUBORDINATE_SUFFIXES):
                    reason_parts.append('mendeko atzizkia')
                elif key.endswith(("n", "en")) and mapped.aldia == "ORAINALDIA":
                    reason_parts.append('-n/-en atzizkia (orainaldia)')
                step["reason"] = f"Mendeko perpausa blokeatua ({', '.join(reason_parts) if reason_parts else '3. pertsona'})"
                step["category"] = "aditz-forma (mendekoa)"
                steps.append(step)
                continue

            # Determine category and rule
            step["action"] = "translated"
            toka_form = (toka_built if toka_built else toka_mapped.form) if toka_mapped else ""
            noka_form = (noka_built if noka_built else noka_mapped.form) if noka_mapped else ""
            step["toka"] = _transfer_case(token.text, toka_form)
            step["noka"] = _transfer_case(token.text, noka_form)

            # Figure out the category and rule description
            rule_parts = []
            if not mapped.is_verb:
                step["category"] = "izenordaina"
                if key in PRONOUN_MAP:
                    rule_parts.append(f"PRONOUN_MAP: {key} → {PRONOUN_MAP[key]}")
                else:
                    # Possessive declined
                    step["category"] = "posesiboa"
                    for base_src, base_tgt in (("zure", "hire"), ("zeure", "heure")):
                        if key.startswith(base_src):
                            suffix = key[len(base_src):]
                            rule_parts.append(f"Posesiboa: {base_src}- → {base_tgt}- + -{suffix}")
                            break
            else:
                step["category"] = "aditz-forma"
                direct = self.lookup_toka.get(key)
                if direct and not built:
                    rule_parts.append(f"Zuzeneko bilaketa: {key} → {direct.form} (toka)")
                    if direct.lema_verbo:
                        rule_parts.append(f"Aditza: {direct.lema_verbo}")
                elif built:
                    # Composed form — explain the composition
                    if key.startswith("bait") and len(key) > 4:
                        rule_parts.append(f"bait- aurrizkia: {key} → bilatu → bait- berriz jarri")
                        step["category"] = "aditz-forma (bait-)"
                    elif key.startswith("baik") and len(key) > 4:
                        rule_parts.append(f"baik- aurrizkia (g→k): {key} → g{key[4:]} → bilatu → baik- berriz jarri")
                        step["category"] = "aditz-forma (bait-)"
                    elif key.startswith("ba") and no_es_verbo_como_bada(key):
                        sub = key[2:]
                        rule_parts.append(f"ba- aurrizkia: {key} = ba- + {sub} → itzuli {sub} → ba- berriz jarri")
                        step["category"] = "aditz-forma (ba-)"
                    else:
                        # Suffix composition
                        for suffix in COMPOSITION_SUFFIXES:
                            if key.endswith(suffix) and len(key) > len(suffix):
                                raw_base = key[:-len(suffix)]
                                base_found = self.lookup_toka.get(raw_base) or self.lookup_toka.get(raw_base + "a")
                                if base_found:
                                    base_key = raw_base if self.lookup_toka.get(raw_base) else raw_base + "a"
                                    rule_parts.append(f"Atzizkia: {key} = {base_key} + -{suffix}")
                                    toka_base = base_found.form
                                    composed = _compose_with_suffix(toka_base, suffix, base_found)
                                    rule_parts.append(f"Konposaketa: {toka_base} + -{suffix} → {composed}")
                                    step["category"] = "aditz-forma (mendeko atzizkia)"
                                    break

            # Case transfer note
            if step.get("toka") and step["toka"] != toka_form:
                rule_parts.append(f"Larri/xehe: {token.text} → {step['toka']}")

            step["rules"] = rule_parts
            steps.append(step)

        return steps
