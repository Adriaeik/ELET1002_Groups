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
MAX_SUBGROUPS = 4         # Maks 4 subgrupper per gruppe


def get_latest_file(folder):
    """Finn den nyaste CSV-fila i mappa"""
    files = [f for f in os.listdir(folder) if f.endswith('.csv')]
    if not files:
        raise FileNotFoundError(f"Ingen CSV-filer funnet i {folder}")
    return os.path.join(folder, files[0])


def load_data(file_path):
    """Last inn data og behald berre siste forsøk per student"""
    data = pd.read_csv(file_path, sep=",", encoding="utf-8")
    
    # Sorter etter attempt (fallande) og behald høgaste attempt per student
    data = data.sort_values('attempt', ascending=False)
    data = data.drop_duplicates(subset=['id'], keep='first')
    
    return data


def find_group_column(data):
    """Finn kolonna som inneheld gruppenummer"""
    for col in data.columns:
        if 'hvilken slt-gruppe' in col.lower() or 'tilhører du' in col.lower():
            return col
    raise ValueError("Fann ikkje gruppekolonna i CSV")


def find_answer_columns(data):
    """Finn oppgåvekolonner. Returnerer dict med {oppgåvenummer: kolonnenamn}"""
    answers = {}
    for col in data.columns:
        match = re.search(r'presentere oppgave (\d+)', col.lower())
        if match:
            task_num = int(match.group(1))
            answers[task_num] = col
    return dict(sorted(answers.items()))


def get_groups(data, group_col):
    """Hent ut gyldige gruppenummer frå data"""
    groups = set()
    for val in data[group_col].dropna().unique():
        val_str = str(val).strip()
        if ',' in val_str:
            continue  # Hopp over ugyldige svar
        try:
            groups.add(int(float(val_str)))
        except ValueError:
            continue
    return sorted(groups)


def filter_by_group(data, group_col, group_num):
    """Filtrer data til berre den valde gruppa"""
    return data[data[group_col].apply(
        lambda x: str(x).strip() == str(group_num) if pd.notna(x) else False
    )].copy()


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
    val = str(row.values[0]).strip().lower()
    return val == 'ja'


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
        candidates = data.loc[
            data[col].astype(str).str.strip().str.lower() == 'ja',
            'name'
        ].tolist()
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


def main():
    # Last inn data
    input_folder = "TicksSheet"
    file_path = get_latest_file(input_folder)
    print(f"Lastar inn: {file_path}")
    
    data = load_data(file_path)
    group_col = find_group_column(data)
    answers = find_answer_columns(data)
    
    print(f"Fann {len(answers)} oppgåver: {list(answers.keys())}")
    
    # Finn alle grupper
    all_groups = get_groups(data, group_col)
    print(f"Fann {len(all_groups)} grupper i data: {all_groups}")
    
    # Spør om SLT-nummer (berre for mappenamn)
    slt_num = input("\nKva SLT-nummer er dette? ")
    
    # Opprett hovudmappe
    base_folder = f"SLT/SLT{slt_num}"
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


if __name__ == "__main__":
    main()