# ELET1002 Group Task Allocator

This Python script automates the allocation of tasks among groups and generates a well-formatted PDF summarizing the results. The script reads an Excel file containing participants' names and their task availability, then assigns tasks and balances group membership based on user-defined group sizes.

---

## Features

1. **Task Allocation**:
   - Distributes tasks among groups based on availability.
   - Ensures tasks are distributed evenly across groups, with flexibility for some members to have multiple tasks if necessary.

2. **Group Balancing**:
   - Balances group sizes by assigning remaining members to groups.

3. **PDF Report**:
   - Generates a PDF summarizing task assignments and group memberships.
   - Tasks are presented in a table with columns for question numbers and assigned members.
   - Includes a "Lucky Fucker" section listing group members without specific task assignments.

---

## Requirements

### Dependencies
The following Python libraries are required:
- `pandas`: For handling Excel files.
- `fpdf`: For generating the PDF report.
---

## Input Format

The script expects **ONE** Excel file in the `TicksSheet` folder. The file must include:

1. A column labeled `Full Name`, containing the names of participants.
2. Columns labeled `Answer 1`, `Answer 2`, ..., `Answer n`, indicating task availability (with `TRUE` or `FALSE` values).

Example:

| Full Name                | Answer 1 | Answer 2 | Answer 3 |
|--------------------------|----------|----------|----------|
| Alice Johnson            | TRUE     | FALSE    | TRUE     |
| Bob Smith                | TRUE     | TRUE     | FALSE    |
| Charlie Davis            | FALSE    | TRUE     | TRUE     |

---

## Usage

1. Place the Excel file in the `TicksSheet` folder.
2. Run the script:
   ```bash
   python TaskAllocator.py
   ```
3. Enter the number of groups when prompted.
4. The script will generate a PDF named `GroupAllocation.pdf` in the current directory.

---

## Output

The generated PDF includes:

1. **Task Table**:
   - Lists questions (`Q.nr`) and the assigned participants for each group.

2. **"Lucky Fucker" Section**:
   - Lists participants in each group who were not assigned specific tasks.

Example Output:

```
Oppgavefordeling

Gruppe 1

Q.nr    Assigned To
1       Alice Johnson
2       Bob Smith
3       Charlie Davis

No more tasks assigned
Lucky Fucker 1    Bob Smith
Lucky Fucker 2    Alice Johnson
```

---

## Customization

- Modify `input_folder` to change the directory where the script looks for the Excel file.
- Update PDF formatting in the `# PDF` section to customize the appearance.

---

