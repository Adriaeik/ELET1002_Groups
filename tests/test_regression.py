"""Regresjonstestar for TaskAllocator.

Fixturane i tests/fixtures/ er anonymiserte kopiar av ekte Canvas-rapportar:
namn og id-ar er bytta ut, alt anna (kolonnenamn, svarmønster, fleire forsøk,
studentar utan gruppe) er bevart slik at testane fangar dei faktiske kvirkane.
"""
import os
import random
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import TaskAllocator as T  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
NY = FIXTURES / "new_format.csv"
GAMMAL = FIXTURES / "old_format.csv"

# Talet på seed vi køyrer fordelinga med. Fordelinga er tilfeldig, so éin
# einskild køyring kan lett gå klar av ein feil som slår inn ~50 % av tida.
SEEDS = 25


@pytest.fixture(params=[NY, GAMMAL], ids=["nytt", "gammalt"])
def datasett(request):
    data = T.load_data(request.param)
    return data, T.find_group_column(data), T.find_answer_columns(data), request.param


# --------------------------------------------------------------------------
# Formatgjenkjenning - begge format skal handterast av same kodesti
# --------------------------------------------------------------------------

def test_nytt_format_hentar_gruppe_fra_section():
    assert T.find_group_column(T.load_data(NY)) == "section"


def test_gammalt_format_hentar_gruppe_fra_quiz_sporsmal():
    col = T.find_group_column(T.load_data(GAMMAL))
    assert col != "section"
    assert "slt-gruppe" in col.lower()


def test_finn_alle_seks_oppgavene(datasett):
    _, _, answers, _ = datasett
    assert list(answers.keys()) == [1, 2, 3, 4, 5, 6]


def test_finn_forventa_grupper():
    assert T.get_groups(T.load_data(NY), "section") == [1, 2, 3, 4, 5, 6, 7, 8]
    gammal = T.load_data(GAMMAL)
    assert T.get_groups(gammal, T.find_group_column(gammal)) == list(range(1, 11))


@pytest.mark.parametrize("verdi, forventa", [
    # Nytt format: gruppenummeret står etter "::", ikkje i seksjonskoden
    ("TET4100-26H-9 :: 5 - The Mighty Power Nappers, TET4100-26H", 5),
    ("TET4100-26H, TET4100-26H-9 :: 5 - The Mighty Power Nappers", 5),
    ("TET4100-26H-12 :: 8 - We Who Shall Not Be Named, TET4100-26H", 8),
    ("TET4100-26H", None),                                     # berre emnet
    ("TET4100-26H-5 :: 1 - A, TET4100-26H-6 :: 2 - B", None),  # tvetydig
    # Gammalt format
    ("SLT gr. 7 - Kretsmesterne", 7),
    ("SLT gr. 10 - Watt sitt kaos", 10),
    ("3", 3),
    ("1,2,3", None),
])
def test_extract_group_number(verdi, forventa):
    assert T.extract_group_number(verdi) == forventa


@pytest.mark.parametrize("verdi, forventa", [
    (True, True), (False, False),
    ("True", True), ("False", False),
    ("Ja", True), ("Nei", False),
    ("ja", True), ("JA", True), (" ja ", True),
    ("yes", True), ("", False), (float("nan"), False), (None, False),
])
def test_is_yes(verdi, forventa):
    assert T.is_yes(verdi) is forventa


# --------------------------------------------------------------------------
# Alltid nyaste forsøk
# --------------------------------------------------------------------------

def test_berre_siste_forsok_per_student(datasett):
    data, _, _, _ = datasett
    assert not data.duplicated(subset=["name", "id"]).any()


def test_siste_forsok_vinn_over_tidlegare(datasett):
    """Kryssar ein student av og so vekk igjen, skal siste forsøk gjelde."""
    data, _, answers, path = datasett
    raa = pd.read_csv(path, encoding="utf-8-sig")

    sjekka = 0
    for namn, rader in raa.groupby("name"):
        if len(rader) < 2:
            continue
        siste = rader.sort_values("attempt").iloc[-1]
        for task, col in answers.items():
            assert T.is_willing(data, namn, col) is T.is_yes(siste[col]), (
                f"{namn} oppgåve {task}: brukte ikkje siste forsøk"
            )
            sjekka += 1
    assert sjekka > 0, "fixturen manglar studentar med fleire forsøk"


def test_angra_avkryssing_gjev_ikkje_oppgave():
    """Regresjon: gamle forsøk lak inn i kandidatlista, so folk kunne få
    oppgåver dei hadde kryssa vekk igjen."""
    data = T.load_data(NY)
    answers = T.find_answer_columns(data)
    raa = pd.read_csv(NY, encoding="utf-8-sig")

    angra = [
        (namn, task)
        for namn, rader in raa.groupby("name") if len(rader) > 1
        for task, col in answers.items()
        if T.is_yes(rader.sort_values("attempt").iloc[0][col])
        and not T.is_yes(rader.sort_values("attempt").iloc[-1][col])
    ]
    assert angra, "fixturen manglar ein student som har angra ei avkryssing"

    for namn, task in angra:
        gruppe = T.extract_group_number(
            raa.loc[raa["name"] == namn, "section"].iloc[0])
        sub = T.filter_by_group(data, "section", gruppe)
        for seed in range(SEEDS):
            random.seed(seed)
            sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
            for sg in sgs.values():
                assert sg["tasks"].get(task) != namn, (
                    f"seed {seed}: {namn} fekk oppgåve {task} trass i angra avkryssing"
                )


# --------------------------------------------------------------------------
# Invariantar i fordelinga
# --------------------------------------------------------------------------

def test_ingen_far_oppgave_dei_ikkje_kryssa_av(datasett):
    data, group_col, answers, _ = datasett
    for seed in range(SEEDS):
        random.seed(seed)
        for gruppe in T.get_groups(data, group_col):
            sub = T.filter_by_group(data, group_col, gruppe)
            sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
            for sid, sg in sgs.items():
                for task, namn in sg["tasks"].items():
                    assert T.is_willing(sub, namn, answers[task]), (
                        f"seed {seed} gr{gruppe}/sub{sid}: {namn} fekk oppgåve "
                        f"{task} utan å ha kryssa av"
                    )


def test_ingen_hamnar_i_to_subgrupper(datasett):
    """Regresjon: dupliserte forsøksrader gjorde at same person kunne bli
    plukka til fleire subgrupper samstundes."""
    data, group_col, answers, _ = datasett
    for seed in range(SEEDS):
        random.seed(seed)
        for gruppe in T.get_groups(data, group_col):
            sub = T.filter_by_group(data, group_col, gruppe)
            sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
            plassering = {}
            for sid, sg in sgs.items():
                for namn in set(list(sg["tasks"].values()) + sg["members"]):
                    assert namn not in plassering, (
                        f"seed {seed} gr{gruppe}: {namn} er i både subgruppe "
                        f"{plassering[namn]} og {sid}"
                    )
                    plassering[namn] = sid


def test_ingen_studentar_forsvinn(datasett):
    data, group_col, answers, _ = datasett
    for seed in range(SEEDS):
        random.seed(seed)
        for gruppe in T.get_groups(data, group_col):
            sub = T.filter_by_group(data, group_col, gruppe)
            sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
            plasserte = {n for sg in sgs.values()
                         for n in list(sg["tasks"].values()) + sg["members"]}
            assert plasserte == set(sub["name"]), (
                f"seed {seed} gr{gruppe}: manglar {set(sub['name']) - plasserte}"
            )


def test_oppgave_star_berre_tom_om_ingen_i_subgruppa_er_villig(datasett):
    data, group_col, answers, _ = datasett
    for seed in range(SEEDS):
        random.seed(seed)
        for gruppe in T.get_groups(data, group_col):
            sub = T.filter_by_group(data, group_col, gruppe)
            sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
            for sid, sg in sgs.items():
                medlemmer = set(list(sg["tasks"].values()) + sg["members"])
                for task, col in answers.items():
                    if task not in sg["tasks"]:
                        assert not any(T.is_willing(sub, m, col) for m in medlemmer), (
                            f"seed {seed} gr{gruppe}/sub{sid}: oppgåve {task} står "
                            f"tom sjølv om nokon i subgruppa er villig"
                        )


def test_subgruppene_er_jamt_store(datasett):
    data, group_col, answers, _ = datasett
    random.seed(0)
    for gruppe in T.get_groups(data, group_col):
        sub = T.filter_by_group(data, group_col, gruppe)
        sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))
        storleikar = [len(set(list(sg["tasks"].values()) + sg["members"]))
                      for sg in sgs.values()]
        assert max(storleikar) - min(storleikar) <= 1, storleikar


@pytest.mark.parametrize("tal, forventa", [
    (1, 1), (6, 1), (7, 1), (11, 2), (12, 2), (18, 3), (40, T.MAX_SUBGROUPS),
])
def test_calculate_num_subgroups(tal, forventa):
    assert T.calculate_num_subgroups(tal) == forventa


# --------------------------------------------------------------------------
# Filval og zip
# --------------------------------------------------------------------------

def test_get_latest_file_vel_nyaste_ikkje_forste_alfabetisk(tmp_path):
    gammal = tmp_path / "A gammal.csv"
    ny = tmp_path / "Z ny.csv"
    gammal.write_text("name\n", encoding="utf-8")
    ny.write_text("name\n", encoding="utf-8")
    os.utime(gammal, (1_000_000, 1_000_000))
    os.utime(ny, (2_000_000, 2_000_000))
    assert T.get_latest_file(str(tmp_path)) == str(ny)


def test_get_latest_file_utan_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        T.get_latest_file(str(tmp_path))


def test_create_zip_tek_med_alle_pdfar_og_ikkje_seg_sjolv(tmp_path):
    base = tmp_path / "SLT1"
    for gruppe in (1, 2):
        mappe = base / f"gruppe{gruppe}"
        mappe.mkdir(parents=True)
        for namn in ("TaskAllocation.pdf", "GroupOverview.pdf"):
            (mappe / namn).write_bytes(b"%PDF-1.4 test")
    (base / "gruppe1" / "notat.txt").write_text("skal ikkje med", encoding="utf-8")

    zip_path = tmp_path / "SLT1.zip"
    assert T.create_zip(str(base), str(zip_path)) == 4

    with zipfile.ZipFile(zip_path) as zf:
        namn = sorted(zf.namelist())
        assert zf.testzip() is None
        assert namn == [
            "SLT1/gruppe1/GroupOverview.pdf", "SLT1/gruppe1/TaskAllocation.pdf",
            "SLT1/gruppe2/GroupOverview.pdf", "SLT1/gruppe2/TaskAllocation.pdf",
        ]
        assert not any(n.endswith(".zip") for n in namn)
        assert not any(n.endswith(".txt") for n in namn)


def test_create_zip_utan_pdfar(tmp_path):
    tom = tmp_path / "tom"
    tom.mkdir()
    assert T.create_zip(str(tom), str(tmp_path / "tom.zip")) == 0


# --------------------------------------------------------------------------
# PDF-generering
# --------------------------------------------------------------------------

def test_pdfar_blir_laga_for_begge_format(datasett, tmp_path):
    data, group_col, answers, _ = datasett
    random.seed(0)
    gruppe = T.get_groups(data, group_col)[0]
    sub = T.filter_by_group(data, group_col, gruppe)
    sgs = T.distribute_tasks(sub, answers, T.calculate_num_subgroups(len(sub)))

    task_pdf = tmp_path / "TaskAllocation.pdf"
    overview_pdf = tmp_path / "GroupOverview.pdf"
    T.create_task_allocation_pdf(sgs, sub, answers, str(task_pdf))
    T.create_group_overview_pdf(sgs, str(overview_pdf))

    for pdf in (task_pdf, overview_pdf):
        assert pdf.stat().st_size > 0
        assert pdf.read_bytes().startswith(b"%PDF")


# --------------------------------------------------------------------------
# Personvern: fixturane skal ikkje innehalde ekte studentdata
# --------------------------------------------------------------------------

def test_fixturane_er_anonymiserte():
    for fixture in (NY, GAMMAL):
        data = pd.read_csv(fixture, encoding="utf-8-sig")
        assert data["id"].min() >= 900000, "id-ane ser ikkje syntetiske ut"
        assert data["name"].nunique() == len(set(data["name"]))
