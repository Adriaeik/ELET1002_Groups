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
    # Lag ein liste over personar som kan presentere kvar oppgåve
    task_candidates = {answer: data.loc[data[answer] == True, full_name_col].tolist() for answer in answers}

    # Start med oppgåva med høgast nummer (prioriter vanskelegaste oppgåver)
    for answer in reversed(answers):
        candidates = task_candidates[answer]
        random.shuffle(candidates)

        # Fordel kandidatar til gruppene for denne oppgåva
        for group_id in sorted(groups.keys(), key=lambda x: len(groups[x]["tasks"])):
            eligible_candidates = [candidate for candidate in candidates if all(candidate != groups[g]["tasks"].get(answer, None) for g in groups)]
            if eligible_candidates:
                selected = eligible_candidates.pop(0)
                groups[group_id]["tasks"].setdefault(answer, selected)

                # Fjern denne personen frå alle andre oppgåver
                for other_answer in answers:
                    if selected in task_candidates[other_answer]:
                        task_candidates[other_answer].remove(selected)

    # Finn personar som allereie er tildelt oppgåver
    assigned_names = [name for group in groups.values() for name in group["tasks"].values()]

    # Fordel resterande personar jevnt til grupper
    remaining_names = [name for name in names if name not in assigned_names]
    random.shuffle(remaining_names)

    # Balanser gruppene
    target_size = len(names) // num_groups
    extra_members = len(names) % num_groups

    for group_id in range(1, num_groups + 1):
        while len(groups[group_id]["members"]) < target_size + (1 if extra_members > 0 else 0):
            if remaining_names:
                groups[group_id]["members"].append(remaining_names.pop(0))
            else:
                break
        if extra_members > 0:
            extra_members -= 1

    # Fordel oppgåver der det ikkje er klare kandidatar
    for answer in answers:
        for group_id in sorted(groups.keys(), key=lambda x: len(groups[x]["tasks"])):
            if answer not in groups[group_id]["tasks"]:
                eligible_members = [member for member in groups[group_id]["members"] + list(groups[group_id]["tasks"].values()) if data.loc[data[full_name_col] == member, answer].values[0] == True]
                if eligible_members:
                    selected = random.choice(eligible_members)
                    groups[group_id]["tasks"].setdefault(answer, selected)

def create_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Oppgavefordeling", ln=True, align='L')

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

        pdf.set_font("Arial", style="I", size=10)
        for idx, member in enumerate(group["members"], start=1):
            pdf.cell(40, 10, txt=f"Lucky fucker {idx}", border=1, align='C')
            pdf.cell(100, 10, txt=member, border=1, align='L')
            pdf.ln()

    output_file = "GroupAllocation.pdf"
    pdf.output(output_file)
    print(f"Fordeling er lagret i {output_file}")

print("Fordeler oppgaver...")
distribute_tasks()
create_pdf()
