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
struck_tasks = []  # Liste for oppgaver som blir strøket

def distribute_tasks():
    # Lag en liste over personer som kan presentere hver oppgave
    task_candidates = {answer: data.loc[data[answer] == True, full_name_col].tolist() for answer in answers}

    # Prioriter oppgaver fra høyest til lavest
    for answer in reversed(answers):
        candidates = task_candidates[answer]
        random.shuffle(candidates)

        # Hvis kun én kan svare, tildel til en spesifikk gruppe
        if len(candidates) == 1:
            selected = candidates.pop(0)
            groups[1]["tasks"].setdefault(answer, selected)

            # Fjern kandidaten fra andre oppgaver
            for other_answer in answers:
                if selected in task_candidates[other_answer]:
                    task_candidates[other_answer].remove(selected)
            continue

        # Fordel oppgaven jevnt til grupper hvis flere kan svare
        for group_id in range(1, num_groups + 1):
            if candidates:
                selected = candidates.pop(0)
                groups[group_id]["tasks"].setdefault(answer, selected)

                # Fjern kandidaten fra andre oppgaver
                for other_answer in answers:
                    if selected in task_candidates[other_answer]:
                        task_candidates[other_answer].remove(selected)

    # Håndter resterende oppgaver uten kandidater
    for answer in answers:
        if not any(answer in group["tasks"] for group in groups.values()):
            struck_tasks.append(answer)

    # Fordel gjenværende medlemmer på gruppene
    assigned_names = [name for group in groups.values() for name in group["tasks"].values()]
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)

    for group_id in range(1, num_groups + 1):
        groups[group_id]["members"].extend(remaining_names[:len(remaining_names)//num_groups])
        remaining_names = remaining_names[len(remaining_names)//num_groups:]

print("Fordeler oppgaver...")
distribute_tasks()

# Opprette PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", size=12)

pdf.cell(200, 10, txt="Oppgavefordeling", ln=True, align='L')

# Legg til strøkte oppgaver
if struck_tasks:
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, txt="Strøkte oppgaver", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    for task in struck_tasks:
        pdf.cell(0, 10, txt=task, ln=True, align='L')
    pdf.ln()

for group_id, group in groups.items():
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, txt=f"Gruppe {group_id}", ln=True, align='L')

    # Opprette tabelloverskrifter
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, txt="Q.nr", border=1, align='C')
    pdf.cell(100, 10, txt="Assigned To", border=1, align='L')
    pdf.ln()

    sorted_tasks = sorted(group["tasks"].items(), key=lambda x: answers.index(x[0]))
    for idx, (task, name) in enumerate(sorted_tasks, start=1):
        pdf.cell(40, 10, txt=str(idx), border=1, align='C')
        pdf.cell(100, 10, txt=name, border=1, align='L')
        pdf.ln()

    # Legg til resterende medlemmer
    pdf.set_font("Arial", style="I", size=10)
    if group["members"]:
        pdf.cell(0, 10, txt="Andre medlemmer:", ln=True, align='L')
        for member in group["members"]:
            pdf.cell(40, 10, txt="", border=1, align='C')
            pdf.cell(100, 10, txt=member, border=1, align='L')
            pdf.ln()

# Lagre PDF
output_file = "GroupAllocation.pdf"
pdf.output(output_file)

print(f"Fordeling er lagret i {output_file}")
