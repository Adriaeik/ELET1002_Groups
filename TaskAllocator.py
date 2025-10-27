import pandas as pd
import random
from fpdf import FPDF
import os

# Funksjon for å finne den nyeste filen i mappen
def get_latest_file(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.csv')]
    if not files:
        raise FileNotFoundError(f"Ingen CSV-filer funnet i {folder}")
    return os.path.join(folder, files[0])

# Laste inn CSV-fila frå TicksSheet-mappa
input_folder = "TicksSheet"
file_path = get_latest_file(input_folder)

data = pd.read_csv(file_path, sep=",", encoding="utf-8")

# Definere relevante kolonner
full_name_col = "Fullt namn" 
answers = [col for col in data.columns if col.lower().startswith("svar")]

# Be brukeren om antall grupper
num_groups = int(input("Kor mange grupper ønskjer du? "))

# Opprette grupper
names = data[full_name_col].tolist()
groups = {i: {"members": [], "tasks": {}} for i in range(1, num_groups + 1)}

def distribute_tasks():
    # Lag ei liste over personar som kan presentere kvar oppgåve
    task_candidates = {answer: data.loc[data[answer] == "Sann", full_name_col].tolist() for answer in answers}

    # Start med oppgåva med høgast nummer (prioriter vanskelegaste oppgåver)
    for answer in reversed(answers):
        candidates = task_candidates[answer]
        random.shuffle(candidates)

        for group_id in sorted(groups.keys(), key=lambda x: len(groups[x]["tasks"])):
            eligible_candidates = [c for c in candidates if all(c != groups[g]["tasks"].get(answer, None) for g in groups)]
            if eligible_candidates:
                selected = eligible_candidates.pop(0)
                groups[group_id]["tasks"].setdefault(answer, selected)

                # Fjern denne personen frå alle andre oppgåver
                for other_answer in answers:
                    if selected in task_candidates[other_answer]:
                        task_candidates[other_answer].remove(selected)

     # Finn personar som allereie er tildelt oppgåver
    assigned_names = [name for group in groups.values() for name in group["tasks"].values()]

    # Personar utan oppgåve
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)

    # Hjelpefunksjon: total storleik pr. gruppe (oppgåve-personar tel også)
    def group_size(gid):
        return len(groups[gid]["members"]) + len(groups[gid]["tasks"])

    # Jamn fordeling: legg éin og éin til den gruppa som er minst akkurat no
    while remaining_names:
        # Finn gruppa med minst totalstorleik (stabil sortering på id for determinisme)
        gid = min(groups.keys(), key=lambda k: (group_size(k), k))
        groups[gid]["members"].append(remaining_names.pop(0))

    # Fordel oppgåver der det ikkje er klare kandidatar (uendra logikk)
    for answer in answers:
        for group_id in sorted(groups.keys(), key=lambda x: len(groups[x]["tasks"])):
            if answer not in groups[group_id]["tasks"]:
                eligible_members = [
                    m for m in groups[group_id]["members"] + list(groups[group_id]["tasks"].values())
                    if data.loc[data[full_name_col] == m, answer].values[0] == "Sann"
                ]
                if eligible_members:
                    selected = random.choice(eligible_members)
                    groups[group_id]["tasks"].setdefault(answer, selected)

def create_pdf():
    """PDF med oppgåvefordeling"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Oppgåvefordeling", ln=True, align='L')

    for group_id, group in groups.items():
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 10, txt=f"Gruppe {group_id}", ln=True, align='L')

        pdf.set_font("Arial", size=10)
        pdf.cell(40, 10, txt="Spørsmål nr", border=1, align='C')
        pdf.cell(100, 10, txt="Tildelt til", border=1, align='L')
        pdf.ln()

        sorted_tasks = sorted(group["tasks"].items(), key=lambda x: x[0])
        for task, name in sorted_tasks:
            pdf.cell(40, 10, txt=task, border=1, align='C')
            pdf.cell(100, 10, txt=name, border=1, align='L')
            pdf.ln()

        pdf.set_font("Arial", style="I", size=10)
        for idx, member in enumerate(group["members"], start=1):
            pdf.cell(40, 10, txt=f"Lucky fucker {idx}", border=1, align='C')
            pdf.cell(100, 10, txt=member, border=1, align='L')
            pdf.ln()

    output_file = "GroupAllocation.pdf"
    pdf.output(output_file)
    print(f"Fordeling er lagra i {output_file}")

def create_group_overview_pdf():
    """PDF som berre viser kven som er i kvar gruppe (utan oppgåvedetaljar)"""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Gruppeoversikt (utan oppgåvedetaljar)", ln=True, align='L')

    for group_id, group in groups.items():
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(0, 10, txt=f"Gruppe {group_id}", ln=True, align='L')

        # Unngå duplikat dersom nokon både har oppgåve og vart lagt til som medlem
        seen = set()
        ordered_unique = []
        for member in list(group["tasks"].values()) + group["members"]:
            if member not in seen:
                seen.add(member)
                ordered_unique.append(member)

        pdf.set_font("Arial", size=10)
        for member in ordered_unique:
            pdf.cell(0, 10, txt=f"- {member}", ln=True, align='L')
        pdf.ln(5)

    output_file = "GroupOverview.pdf"
    pdf.output(output_file)
    print(f"Anonym gruppeoversikt er lagra i {output_file}")

print("Fordeler oppgåver...")
distribute_tasks()
create_pdf()
create_group_overview_pdf()
