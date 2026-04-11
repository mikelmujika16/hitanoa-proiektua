from translator import HitanoTranslator


def run_tests() -> None:
    tr = HitanoTranslator()

    # TEST 1
    zuka_1 = "Zu beti zure gauzekin zabiltza. Zeuk egin behar duzu!"
    toka_1 = "Hi beti hire gauzekin habil. Heuk egin behar duk!"
    noka_1 = "Hi beti hire gauzekin habil. Heuk egin behar dun!"
    assert tr.translate_toka(zuka_1) == toka_1
    assert tr.translate_noka(zuka_1) == noka_1

    # TEST 2
    zuka_2 = "Nik zuri txakur zuri bat ekarri dizut."
    toka_2 = "Nik hiri txakur zuri bat ekarri diat."
    noka_2 = "Nik hiri txakur zuri bat ekarri dinat."
    assert tr.translate_toka(zuka_2) == toka_2
    assert tr.translate_noka(zuka_2) == noka_2

    # TEST 3
    zuka_3 = "Orain etxean zaude, baina atzo Bilbora zindoazen."
    toka_3 = "Orain etxean hago, baina atzo Bilbora hihoan."
    noka_3 = "Orain etxean hago, baina atzo Bilbora hihoan."
    assert tr.translate_toka(zuka_3) == toka_3
    assert tr.translate_noka(zuka_3) == noka_3

    # TEST 4
    zuka_4 = "Zuk badakizu autoa hor badagoela."
    toka_4 = "Hik badakik autoa hor badagoela."
    noka_4 = "Hik badakin autoa hor badagoela."
    assert tr.translate_toka(zuka_4) == toka_4
    assert tr.translate_noka(zuka_4) == noka_4

    # TEST 5
    zuka_5 = "Euria ari du eta mendia polita da."
    toka_5 = "Euria ari dik eta mendia polita duk."
    noka_5 = "Euria ari din eta mendia polita dun."
    assert tr.translate_toka(zuka_5) == toka_5
    assert tr.translate_noka(zuka_5) == noka_5

    # TEST 6A
    zuka_6a = "Pozik nago berandu etorri zarelako."
    toka_6a = "Pozik nauk berandu etorri haizelako."
    noka_6a = "Pozik naun berandu etorri haizelako."
    assert tr.translate_toka(zuka_6a) == toka_6a
    assert tr.translate_noka(zuka_6a) == noka_6a

    # TEST 6B
    zuka_6b = "Uste dut Mikel berandu etorri delako haserretu dela."
    toka_6b = "Uste diat Mikel berandu etorri delako haserretu dela."
    noka_6b = "Uste dinat Mikel berandu etorri delako haserretu dela."
    assert tr.translate_toka(zuka_6b) == toka_6b
    assert tr.translate_noka(zuka_6b) == noka_6b

    # TEST 7
    zuka_7 = "Zuk esan duzu Miren haserretzen dela zurekin tabernara joaten naizenean, baina zuri berdin zaizu."
    toka_7 = "Hik esan duk Miren haserretzen dela hirekin tabernara joaten naizenean, baina hiri berdin zaik."
    assert tr.translate_toka(zuka_7) == toka_7

    # TEST 8A - posesibo deklinatuak (zure-)
    zuka_8a = "zurea zureak zureari zurearen zurearekin zurearentzat zureaz"
    expected_8a = "hirea hireak hireari hirearen hirearekin hirearentzat hireaz"
    assert tr.translate_toka(zuka_8a) == expected_8a
    assert tr.translate_noka(zuka_8a) == expected_8a

    # TEST 8B - posesibo deklinatuak (zeure-)
    zuka_8b = "zeurean zeurera zeuretik zeureko zeurerantz zeureraino"
    expected_8b = "heurean heurera heuretik heureko heurerantz heureraino"
    assert tr.translate_toka(zuka_8b) == expected_8b
    assert tr.translate_noka(zuka_8b) == expected_8b

    # TEST 9 - mendeko -n + 2. argumentala: duk/dun + n -> duan/dunan
    zuka_9 = "Zuk esan duzun hori ona da."
    toka_9 = "Hik esan duan hori ona duk."
    noka_9 = "Hik esan dunan hori ona dun."
    assert tr.translate_toka(zuka_9) == toka_9
    assert tr.translate_noka(zuka_9) == noka_9

    # TEST 10 - mendeko -lako + 2. argumentala: duk/dun + lako -> dualako/dunalako
    zuka_10 = "Zuk esan duzulako, nik sinesten dizut."
    toka_10 = "Hik esan dualako, nik sinesten diat."
    noka_10 = "Hik esan dunalako, nik sinesten dinat."
    assert tr.translate_toka(zuka_10) == toka_10
    assert tr.translate_noka(zuka_10) == noka_10

    # TEST 11 - baldintza ondorioko bait- forma: baituzu -> baituk / baitun
    zuka_11 = "baituzu"
    toka_11 = "baituk"
    noka_11 = "baitun"
    assert tr.translate_toka(zuka_11) == toka_11
    assert tr.translate_noka(zuka_11) == noka_11

    print("All tests passed (12/12).")


if __name__ == "__main__":
    run_tests()
