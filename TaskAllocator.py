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
        num_groups_ = min(num_groups, len(candidates))  # Juster antall grupper basert på tilgjengelige kandidater

        # Fordel kandidater til gruppene for denne oppgaven
        for group_id in range(1, num_groups_ + 1):
            if candidates:
                selected = candidates.pop(0)
                groups[group_id]["tasks"].setdefault(answer, selected)

                # Fjern denne personen fra alle andre oppgaver
                for other_answer in answers:
                    if selected in task_candidates[other_answer]:
                        task_candidates[other_answer].remove(selected)

    # Fjern oppgaver uten tilgjengelige kandidater
    for answer in answers:
        if not any(answer in group["tasks"] for group in groups.values()):
            print(f"Oppgave '{answer}' ble strøket på grunn av manglende kandidater.")

    # Finn personer som allerede er tildelt oppgaver
    assigned_names = [name for group in groups.values() for name in group["tasks"].values()]

    # Fordel resterende personer jevnt til grupper
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)

    # Balanser gruppene uten å havne i evig løkke
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

print("Fordeler oppgaver...")
distribute_tasks()

# Opprette PDF
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
pdf.set_font("Arial", size=12)

pdf.cell(200, 10, txt="Oppgavefordeling", ln=True, align='L')

for group_id, group in groups.items():
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, txt=f"Gruppe {group_id}", ln=True, align='L')

    # Opprette tabelloverskrifter
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, txt="Q.nr", border=1, align='C')
    pdf.cell(100, 10, txt="Assigned To", border=1, align='L')
    pdf.ln()

    def parse_question_number(task):
        try:
            return float(task.split()[1])  # Håndter både heltall og desimaltall
        except ValueError:
            return float('inf')  # Sett uforståelige verdier til en høy verdi for sortering

    sorted_tasks = sorted(group["tasks"].items(), key=lambda x: parse_question_number(x[0]))
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
