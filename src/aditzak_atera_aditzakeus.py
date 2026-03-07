"""Aditzak.eus web scraper — Extract zu→hi verb conjugation mappings.

Uses Playwright to interact with https://aditzak.eus/ and extract all verb
forms where the 2nd person formal (zu/zuk/zuri) participates, paired with
their 2nd person informal (hi/hik/hiri) equivalents.

Output: json/aditzak_zu_to_hi.json
"""

from playwright.sync_api import sync_playwright
import json
import time
import itertools
import os

# ── CONFIGURATION ──────────────────────────────────────────────────────────────

# Modua × Aldia combinations
# Each aldia entry: (label, click_text, nth_index_within_aldia_group)
MODUAK = [
    ("indikatiboa", [
        ("ORAINALDIA",       "orain",       0),
        ("LEHENALDIA",       "lehen",       0),
        ("BALDINTZA",        "baldintza",   0),
        ("ONDORIOA",         "orain",       1),  # baldintzazkoa > ondorioa > orain
        ("ONDORIOA_IRAGANA", "lehen",       1),  # baldintzazkoa > ondorioa > lehen
    ]),
    ("ahalera", [
        ("AHALERA_ORAIN",       "orain",       0),
        ("AHALERA_LEHEN",       "lehen",       0),
        ("AHALERA_HIPOTETIKOA", "hipotetikoa", 0),
    ]),
    ("subjuntiboa", [
        ("SUBJUNTIBOA_ORAIN", "orain", 0),
        ("SUBJUNTIBOA_LEHEN", "lehen", 0),
    ]),
    ("agintera", [
        ("AGINTERA", "orain", 0),
    ]),
]

# Persons for iteration (excluding zu/hi/zuek — the formal/informal pair)
NOR_ITER  = ["ni", "hura", "gu", "haiek"]
NORK_ITER = ["nik", "hark", "guk", "halek"]
NORI_ITER = ["niri", "hari", "guri", "halei"]

# For NOR-NORI-NORK, the absolutive (Nor) is 3rd person only (1st/2nd disabled)
NOR_3RD = ["hura", "haiek"]

# Zu ↔ Hi mapping per person group
ZU_HI = {
    "nor":  ("zu",   "hi"),
    "nork": ("zuk",  "hik"),
    "nori": ("zuri", "hiri"),
}

# Extraction scenarios per mota: which group has "zu" and what to iterate
SCENARIOS = {
    "nor": [
        {"zu_group": "nor", "iterate": {}},
    ],
    "nor-nork": [
        {"zu_group": "nork", "iterate": {"nor": NOR_ITER}},
        {"zu_group": "nor",  "iterate": {"nork": NORK_ITER}},
    ],
    "nor-nori": [
        {"zu_group": "nori", "iterate": {"nor": NOR_ITER}},
        {"zu_group": "nor",  "iterate": {"nori": NORI_ITER}},
    ],
    "nor-nori-nork": [
        {"zu_group": "nork", "iterate": {"nori": NORI_ITER, "nor": NOR_3RD}},
        {"zu_group": "nori", "iterate": {"nork": NORK_ITER, "nor": NOR_3RD}},
    ],
}


def parse_hika(text):
    """Parse toka/noka from wordName. 'nauk / naun' → ('nauk','naun')."""
    if " / " in text:
        a, b = text.split(" / ", 1)
        return a.strip(), b.strip()
    return text.strip(), text.strip()


def run():
    results = []
    skipped = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://aditzak.eus/")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # The 6 .appGroup containers in DOM order
        groups  = page.locator(".appGroup")
        modua_g = groups.nth(0)
        aldia_g = groups.nth(1)
        mota_g  = groups.nth(2)
        nork_g  = groups.nth(3)
        nori_g  = groups.nth(4)
        nor_g   = groups.nth(5)

        group_loc = {"nor": nor_g, "nork": nork_g, "nori": nori_g}

        # ── Helpers ────────────────────────────────────────────────────────────

        def click(grp, text, nth=0, wait=0.25):
            grp.get_by_text(text, exact=True).nth(nth).click()
            time.sleep(wait)

        def read_word():
            """Read the displayed verb form from .wordName."""
            try:
                wn = page.locator(".wordName")
                if wn.count() > 0 and wn.first.is_visible():
                    return wn.first.inner_text().strip() or None
            except Exception:
                pass
            return None

        # ── Main extraction loop ───────────────────────────────────────────────

        current_modua = None
        count = 0

        for modua, aldiak in MODUAK:
            if modua != current_modua:
                click(modua_g, modua)
                current_modua = modua

            for aldia_label, aldia_click, aldia_nth in aldiak:
                click(aldia_g, aldia_click, aldia_nth)

                for mota, scenarios in SCENARIOS.items():
                    click(mota_g, mota)

                    for scenario in scenarios:
                        zu_grp  = scenario["zu_group"]
                        zu_text, hi_text = ZU_HI[zu_grp]
                        iterate = scenario["iterate"]

                        # Build person combinations for the "other" groups
                        if iterate:
                            keys   = list(iterate.keys())
                            values = [iterate[k] for k in keys]
                            combos = [
                                dict(zip(keys, c))
                                for c in itertools.product(*values)
                            ]
                        else:
                            combos = [{}]

                        for combo in combos:
                            # ── 1. Get HIKA form: set others first, then hi ──
                            # (others must be set before hi/hik/hiri to avoid
                            #  disabled-state conflicts from stale selections)
                            for g, person in combo.items():
                                click(group_loc[g], person)
                            click(group_loc[zu_grp], hi_text)
                            time.sleep(0.8)
                            hika_raw = read_word()

                            # ── 2. Get ZUKA form: switch only zu_group ──
                            click(group_loc[zu_grp], zu_text)
                            time.sleep(0.8)
                            zuka = read_word()

                            # Record if both valid and different
                            if hika_raw and zuka and hika_raw != zuka:
                                toka, noka = parse_hika(hika_raw)
                                entry = {
                                    "mota":  mota,
                                    "modua": modua,
                                    "aldia": aldia_label,
                                    zu_grp:  zu_text,
                                }
                                for g, person in combo.items():
                                    entry[g] = person
                                entry["zuka"]      = zuka
                                entry["hika_toka"] = toka
                                entry["hika_noka"] = noka
                                results.append(entry)
                                count += 1
                                print(
                                    f"[{count:>4d}] {modua}/{aldia_label}/{mota} "
                                    f"{zu_text}+{combo}: "
                                    f"{zuka} -> {toka} / {noka}"
                                )
                            else:
                                skipped += 1

        browser.close()

    # ── Save output ────────────────────────────────────────────────────────────
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(project_root, "json", "aditzak_zu_to_hi.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nDone: {count} entries saved to {out_path}")
    print(f"Skipped: {skipped} invalid/unchanged combinations")


if __name__ == "__main__":
    run()
