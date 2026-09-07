import pandas as pd
import random
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re
import zipfile

# Registrer font med norsk støtte
try:
    pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    DEFAULT_FONT = 'DejaVu'
    BOLD_FONT = 'DejaVu-Bold'
except:
    DEFAULT_FONT = 'Helvetica'
    BOLD_FONT = 'Helvetica-Bold'

# Konfigurasjon
TARGET_SUBGROUP_SIZE = 6  # Mål: 6 personar per subgruppe
MAX_SUBGROUPS = 3         # Maks 3 subgrupper per gruppe

# Verdiar som tyder "ja". Gammalt format svarte "Ja"/"Nei",
# nytt format brukar avkryssing som Canvas eksporterer som True/False.
YES_VALUES = {'ja', 'j', 'yes', 'y', 'true', 'sant', '1', '1.0'}

# Gruppenummer i section-kolonna (nytt format), t.d.
# "TET4100-26H-9 :: 5 - The Mighty Power Nappers" -> 5
SECTION_GROUP_RE = re.compile(r'::\s*(?:slt\s*)?(?:gr\.?|gruppe|group)?\s*(\d+)', re.IGNORECASE)

# Oppgåvekolonner: "presentere oppgave 1" (gammalt) / "present Task #1" (nytt)
TASK_COL_RE = re.compile(r'present(?:ere)?\s+(?:oppgave|task)\s*#?\s*(\d+)', re.IGNORECASE)


def is_yes(val):
    """Sjekk om ein svarverdi tyder ja (True, "Ja", "Yes", ...)"""
    if isinstance(val, bool):
        return val
    if pd.isna(val):
        return False
    return str(val).strip().lower() in YES_VALUES


def get_latest_file(folder):
    """Finn den nyaste CSV-fila i mappa (etter endringstidspunkt).

    Viktig når gamle rapportar ligg att i mappa - alfabetisk rekkjefølgje
    ville plukka feil fil.
    """
    files = [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith('.csv')]
    if not files:
        raise FileNotFoundError(f"Ingen CSV-filer funnet i {folder}")
    return max(files, key=os.path.getmtime)


def load_data(file_path):
    """Last inn data og behald berre siste forsøk per student"""
    data = pd.read_csv(file_path, sep=",", encoding="utf-8-sig")
    
    # Sorter etter attempt (fallande) og behald høgaste attempt per student
    data = data.sort_values('attempt', ascending=False)
    # data = data.drop_duplicates(subset=['id'], keep='first')
    
    return data


def find_group_column(data):
    """Finn kolonna som inneheld gruppetilhøyrsle.

    Gammalt format: eit eige quiz-spørsmål om SLT-gruppe.
    Nytt format: spørsmålet finst ikkje - gruppa ligg i Canvas-seksjonen,
    t.d. "TET4100-26H-9 :: 5 - The Mighty Power Nappers".
    """
    for col in data.columns:
        if 'hvilken slt-gruppe' in col.lower() or 'tilhører du' in col.lower():
            return col

    if 'section' in data.columns:
        has_group = data['section'].astype(str).apply(
            lambda s: SECTION_GROUP_RE.search(s) is not None
        )
        if has_group.any():
            return 'section'

    raise ValueError("Fann ikkje gruppekolonna i CSV")


def find_answer_columns(data):
    """Finn oppgåvekolonner. Returnerer dict med {oppgåvenummer: kolonnenamn}"""
    answers = {}
    for col in data.columns:
        match = TASK_COL_RE.search(str(col))
        if match:
            task_num = int(match.group(1))
            answers[task_num] = col
    return dict(sorted(answers.items()))


def extract_group_number(val):
    """Trekk ut gruppenummer frå ein verdi.

    Nytt format (section): "TET4100-26H-9 :: 5 - The Mighty Power Nappers, TET4100-26H" -> 5
    Gammalt format:        "SLT gr. 7 - Kretsmesterne" -> 7
    """
    val_str = str(val).strip()

    # Nytt format: ein student kan stå i fleire seksjonar (kommaseparert),
    # men berre éi av dei er ei SLT-gruppe.
    section_groups = {int(n) for n in SECTION_GROUP_RE.findall(val_str)}
    if len(section_groups) == 1:
        return section_groups.pop()
    if section_groups or '::' in val_str:
        # Fleire grupper, eller berre emneseksjonen utan gruppe
        return None

    # Ignorer verdiar med komma (t.d. "1,2,3,4,5" - ugyldig multi-val)
    if ',' in val_str:
        return None
    
    # Prøv først som rein tal
    try:
        return int(float(val_str))
    except ValueError:
        pass
    
    # Søk etter tal i strengen (t.d. "SLT gr. 7 - Kretsmesterne")
    match = re.search(r'\b(\d+)\b', val_str)
    if match:
        return int(match.group(1))
    
    return None


def get_groups(data, group_col):
    """Hent ut gyldige gruppenummer frå data"""
    groups = set()
    for val in data[group_col].dropna().unique():
        group_num = extract_group_number(val)
        if group_num is not None:
            groups.add(group_num)
    return sorted(groups)


def filter_by_group(data, group_col, group_num):
    """Filtrer data til berre den valde gruppa"""
    def matches_group(val):
        if pd.isna(val):
            return False
        extracted = extract_group_number(val)
        return extracted == group_num
    
    return data[data[group_col].apply(matches_group)].copy()


def calculate_num_subgroups(num_students):
    """Rekn ut antal subgrupper basert på antal studentar"""
    if num_students <= TARGET_SUBGROUP_SIZE:
        return 1
    
    # Prøv å få så nær TARGET_SUBGROUP_SIZE som mogleg
    num_subgroups = max(1, round(num_students / TARGET_SUBGROUP_SIZE))
    
    # Avgrens til maks
    return min(num_subgroups, MAX_SUBGROUPS)


def is_willing(data, name, answer_col):
    """Sjekk om ein person er villig til å presentere (svara 'Ja')"""
    row = data.loc[data['name'] == name, answer_col]
    if row.empty:
        return False
    return is_yes(row.values[0])


def distribute_tasks(data, answers, num_subgroups):
    """
    Fordel oppgåver mellom N subgrupper.
    Basert på original logikk frå Blackboard-versjonen.
    """
    names = data['name'].tolist()
    subgroups = {i: {"members": [], "tasks": {}} for i in range(1, num_subgroups + 1)}
    
    # Lag ei liste over personar som kan presentere kvar oppgåve
    task_candidates = {}
    for task_num, col in answers.items():
        candidates = data.loc[data[col].apply(is_yes), 'name'].tolist()
        task_candidates[task_num] = candidates
    
    # Start med oppgåva med høgast nummer (prioriter vanskelegaste oppgåver)
    for task_num in reversed(list(answers.keys())):
        candidates = task_candidates[task_num].copy()
        random.shuffle(candidates)
        
        for subgroup_id in sorted(subgroups.keys(), key=lambda x: len(subgroups[x]["tasks"])):
            eligible_candidates = [
                c for c in candidates 
                if all(c != subgroups[g]["tasks"].get(task_num, None) for g in subgroups)
            ]
            if eligible_candidates:
                selected = eligible_candidates.pop(0)
                subgroups[subgroup_id]["tasks"].setdefault(task_num, selected)
                
                # Fjern denne personen frå alle andre oppgåver
                for other_task in answers.keys():
                    if selected in task_candidates[other_task]:
                        task_candidates[other_task].remove(selected)
    
    # Finn personar som allereie er tildelt oppgåver
    assigned_names = [name for sg in subgroups.values() for name in sg["tasks"].values()]
    
    # Personar utan oppgåve
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)
    
    # Hjelpefunksjon: total storleik pr. subgruppe
    def subgroup_size(sid):
        return len(subgroups[sid]["members"]) + len(subgroups[sid]["tasks"])
    
    # Jamn fordeling: legg éin og éin til den subgruppa som er minst
    while remaining_names:
        sid = min(subgroups.keys(), key=lambda k: (subgroup_size(k), k))
        subgroups[sid]["members"].append(remaining_names.pop(0))
    
    # Fordel oppgåver der det ikkje er klare kandidatar
    for task_num, col in answers.items():
        for subgroup_id in sorted(subgroups.keys(), key=lambda x: len(subgroups[x]["tasks"])):
            if task_num not in subgroups[subgroup_id]["tasks"]:
                all_members = list(subgroups[subgroup_id]["tasks"].values()) + subgroups[subgroup_id]["members"]
                eligible_members = [m for m in all_members if is_willing(data, m, col)]
                if eligible_members:
                    selected = random.choice(eligible_members)
                    subgroups[subgroup_id]["tasks"].setdefault(task_num, selected)
    
    return subgroups


def get_willing_tasks(data, name, answers):
    """Finn kva oppgåver ein student har svara Ja på"""
    willing = []
    for task_num, col in answers.items():
        if is_willing(data, name, col):
            willing.append(str(task_num))
    return ", ".join(willing) if willing else "-"


def create_task_allocation_pdf(subgroups, data, answers, output_path):
    """Lag TaskAllocation.pdf med alle subgrupper i same fil"""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    title_style = ParagraphStyle('Title', fontName=BOLD_FONT, fontSize=14, spaceAfter=10)
    subtitle_style = ParagraphStyle('Subtitle', fontName=BOLD_FONT, fontSize=12, spaceBefore=15, spaceAfter=5)
    
    elements = []
    elements.append(Paragraph("Oppgåvefordeling", title_style))
    
    for subgroup_id, subgroup in subgroups.items():
        elements.append(Paragraph(f"Gruppe {subgroup_id}", subtitle_style))
        
        # Lag tabell med ekstra kolonne for villige oppgåver
        table_data = [["Spørsmål nr", "Tildelt til", "Villig til"]]
        
        sorted_tasks = sorted(subgroup["tasks"].items(), key=lambda x: x[0])
        for task_num, name in sorted_tasks:
            willing = get_willing_tasks(data, name, answers)
            table_data.append([f"Svar {task_num}", name, willing])
        
        # Legg til medlemmar utan oppgåve
        for idx, member in enumerate(subgroup["members"], start=1):
            willing = get_willing_tasks(data, member, answers)
            table_data.append([f"Lucky fucker {idx}", member, willing])
        
        table = Table(table_data, colWidths=[3*cm, 8*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (-1, -1), DEFAULT_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    
    doc.build(elements)


def create_group_overview_pdf(subgroups, output_path):
    """Lag GroupOverview.pdf med alle subgrupper - berre medlemsliste"""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    title_style = ParagraphStyle('Title', fontName=BOLD_FONT, fontSize=14, spaceAfter=10)
    subtitle_style = ParagraphStyle('Subtitle', fontName=BOLD_FONT, fontSize=12, spaceBefore=15, spaceAfter=5)
    normal_style = ParagraphStyle('Normal', fontName=DEFAULT_FONT, fontSize=10, leftIndent=10)
    
    elements = []
    elements.append(Paragraph("Gruppeoversikt (utan oppgåvedetaljar)", title_style))
    
    for subgroup_id, subgroup in subgroups.items():
        elements.append(Paragraph(f"Gruppe {subgroup_id}", subtitle_style))
        
        # Unngå duplikat
        seen = set()
        members = []
        for member in list(subgroup["tasks"].values()) + subgroup["members"]:
            if member not in seen:
                seen.add(member)
                members.append(member)
        
        for member in members:
            elements.append(Paragraph(f"- {member}", normal_style))
        
        elements.append(Spacer(1, 0.3*cm))
    
    doc.build(elements)


def create_zip(base_folder, zip_path):
    """Pakk alle PDF-ane under base_folder i ein zip.

    Zip-fila blir lagd utanfor base_folder slik at ho ikkje pakkar seg sjølv.
    Stiane i zipen er relative til mappa over, t.d. "SLT1/gruppe1/TaskAllocation.pdf".
    """
    root = os.path.dirname(os.path.abspath(base_folder))

    pdfs = []
    for folder, _, files in os.walk(base_folder):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdfs.append(os.path.join(folder, f))
    pdfs.sort()

    if not pdfs:
        return 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for pdf in pdfs:
            arcname = os.path.relpath(pdf, root).replace(os.sep, '/')
            zf.write(pdf, arcname)

    return len(pdfs)


def main():
    # Last inn data
    input_folder = "TicksSheet"
    file_path = get_latest_file(input_folder)
    print(f"Lastar inn: {file_path}")
    
    data = load_data(file_path)
    group_col = find_group_column(data)
    answers = find_answer_columns(data)
    
    if not answers:
        raise ValueError("Fann ingen oppgåvekolonner i CSV")

    kjelde = "section (nytt format)" if group_col == 'section' else "quiz-spørsmål (gammalt format)"
    print(f"Gruppekjelde: {kjelde}")
    print(f"Fann {len(answers)} oppgåver: {list(answers.keys())}")
    
    # Finn alle grupper
    all_groups = get_groups(data, group_col)
    print(f"Fann {len(all_groups)} grupper i data: {all_groups}")

    # Studentar som ikkje kan plasserast i noko gruppe (t.d. berre registrert
    # på emnet). Eit forsøk utan gruppe tel ikkje viss eit anna forsøk har gruppe.
    has_group = data[group_col].apply(lambda v: extract_group_number(v) is not None)
    ungrouped = sorted(set(data.loc[~has_group, 'name']) - set(data.loc[has_group, 'name']))
    if ungrouped:
        print(f"Åtvaring: {len(ungrouped)} utan gruppe: {', '.join(ungrouped)}")
    
    # Spør om SLT-nummer (berre for mappenamn)
    slt_num = input("\nKva SLT-nummer er dette? ")
    
    # Opprett hovudmappe
    slt_root = "SLT"
    os.makedirs(slt_root, exist_ok=True)
    base_folder = os.path.join(slt_root, f"SLT{slt_num}")
    os.makedirs(base_folder, exist_ok=True)
    
    print()
    
    # Prosesser kvar gruppe
    for group_num in all_groups:
        group_data = filter_by_group(data, group_col, group_num)
        num_students = len(group_data)
        
        if num_students == 0:
            print(f"Gruppe {group_num}: Ingen studentar, hoppar over")
            continue
        
        # Rekn ut antal subgrupper
        num_subgroups = calculate_num_subgroups(num_students)
        
        print(f"Prosesserer gruppe {group_num}: {num_students} studentar → {num_subgroups} subgruppe(r)")
        
        # Fordel oppgåver i subgrupper
        subgroups = distribute_tasks(group_data, answers, num_subgroups)
        
        # Opprett gruppemappe
        group_folder = os.path.join(base_folder, f"gruppe{group_num}")
        os.makedirs(group_folder, exist_ok=True)
        
        # Lag PDF-ar (alle subgrupper i same fil)
        task_pdf = os.path.join(group_folder, "TaskAllocation.pdf")
        overview_pdf = os.path.join(group_folder, "GroupOverview.pdf")
        
        create_task_allocation_pdf(subgroups, group_data, answers, task_pdf)
        create_group_overview_pdf(subgroups, overview_pdf)
    
    print(f"\nFerdig! Grupper lagra i {base_folder}/")

    # Pakk alle PDF-ane i éi zip-fil
    zip_path = f"{base_folder}.zip"
    num_pdfs = create_zip(base_folder, zip_path)
    if num_pdfs:
        print(f"Zip med {num_pdfs} PDF-ar: {zip_path}")
    else:
        print("Åtvaring: fann ingen PDF-ar å pakke")


if __name__ == "__main__":
    main()