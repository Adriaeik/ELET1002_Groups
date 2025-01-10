import pandas as pd
import random
from fpdf import FPDF
import os

# Funksjon for å finne den nyeste filen i mappen
def get_latest_file(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.xlsx')]
    paths = [os.path.join(folder, f) for f in files]
    return max(paths, key=os.path.getctime)

# Konstanter
input_folder = "TicksSheet"
input_file = get_latest_file(input_folder)

data = pd.read_excel(input_file)

# Konvertere kolonneoverskrifter og sjekke data
full_name_col = "Full Name"
answers = [col for col in data.columns if col.startswith("Answer")]

# Be brukeren om antall grupper
num_groups = int(input("Hvor mange grupper ønsker du? "))

# Opprette grupper
names = data[full_name_col].tolist()
groups = {i: {"members": [], "tasks": {}} for i in range(1, num_groups + 1)}

def distribute_tasks():
    # Lag en liste over personer som kan presentere hver oppgave
    task_candidates = {answer: data.loc[data[answer] == True, full_name_col].tolist() for answer in answers}

    # Start med oppgaven med høyest nummer (prioriter vanskeligste oppgaver)
    for answer in reversed(answers):
        candidates = task_candidates[answer]
        random.shuffle(candidates)

        # Fordel kandidater til gruppene for denne oppgaven
        for group_id in range(1, num_groups + 1):
            if candidates:
                selected = candidates.pop(0)
                groups[group_id]["tasks"].setdefault(answer, selected)

                # Fjern denne personen fra alle andre oppgaver
                for other_answer in answers:
                    if selected in task_candidates[other_answer]:
                        task_candidates[other_answer].remove(selected)

    # Finn personer som allerede er tildelt oppgaver
    assigned_names = [name for group in groups.values() for name in group["tasks"].values()]

    # Fordel resterende personer jevnt til grupper
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)

    # Balanser gruppene
    target_size = len(names) // num_groups
    extra_members = len(names) % num_groups

    for group_id in range(1, num_groups + 1):
        while len(groups[group_id]["members"]) + len(groups[group_id]["tasks"]) < target_size + (1 if extra_members > 0 else 0):
            if remaining_names:
                groups[group_id]["members"].append(remaining_names.pop(0))
            else:
                break
        if extra_members > 0:
            extra_members -= 1

    # Sikre at alle oppgaver blir tildelt, selv om det er flere oppgaver enn personer i gruppen
    
    for answer in answers:
        for group_id in range(1, num_groups + 1):
            if answer not in groups[group_id]["tasks"]:
                # Hvis gruppen mangler oppgaven, velg en tilfeldig person fra gruppen
                eligible_members = groups[group_id]["members"] + list(groups[group_id]["tasks"].values())
                if eligible_members:
                    selected = random.choice(eligible_members)
                    groups[group_id]["tasks"].setdefault(answer, selected)

print("Fordeler oppgaver...")
distribute_tasks()

# PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", size=12)

pdf.cell(200, 10, txt="Oppgavefordeling", ln=True, align='L')

# Tabelloverskrifter
for group_id, group in groups.items():
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, txt=f"Gruppe {group_id}", ln=True, align='L')

    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, txt="Q.nr", border=1, align='C')
    pdf.cell(100, 10, txt="Assigned To", border=1, align='L')
    pdf.ln()

    sorted_tasks = sorted(group["tasks"].items(), key=lambda x: float(x[0].split()[1]))
    for idx, (task, name) in enumerate(sorted_tasks, start=1):
        pdf.cell(40, 10, txt=str(idx), border=1, align='C')
        pdf.cell(100, 10, txt=name, border=1, align='L')
        pdf.ln()

    # Adding a gender-neutral 'lucky person'
    pdf.set_font("Arial", style="I", size=10)
    # pdf.cell(0, 10, txt=f"No more tasks assigned", ln=True, align='L')
    for idx, member in enumerate(group["members"], start=1):
        pdf.cell(40, 10, txt=f"Lucky Fucker {idx}", border=1, align='C')
        pdf.cell(100, 10, txt=member, border=1, align='L')
        pdf.ln()

# Lagre PDF
output_file = "GroupAllocation.pdf"
pdf.output(output_file)

print(f"Fordeling er lagret i {output_file}")