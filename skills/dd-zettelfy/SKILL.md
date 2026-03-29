---
name: dd-zettelfy
description: Assign zettel IDs to unorganized dd Due Diligence prospect folders, create child zettels with PDF links, rename folders, and update the parent index. Use when the user says /dd-zettelfy, asks to "zettelfy due diligence", "organize dd folders", "assign zettel IDs to prospects", or wants to integrate new prospect folders into the zettelkasten system.
---

# dd-zettelfy

Scan `dd Due Diligence/` for prospect folders that don't have zettel IDs yet, assign them sequential IDs, create child zettel markdown files with PDF links, rename the folders, and update `dd Due Diligence.md`.

## Workflow

### Step 1: Discover current state

Run the following bash command to list all folders directly under `dd Due Diligence/`:

```bash
ls -d "dd Due Diligence"/*/ 2>/dev/null | sed 's|dd Due Diligence/||;s|/||'
```

From this list, identify:
- **Already zettelfied:** Folders whose names start with `dd` followed by a digit (e.g. `dd1 CSU`, `dd2 TOI.V`). Skip these.
- **Excluded:** The folder named `No Zettel`. Skip this.
- **Candidates:** All remaining folders. These will be processed.

If there are no candidates, inform the user that all folders are already zettelfied and stop.

### Step 2: Determine the next zettel number

From the already-zettelfied folders, extract the highest existing number. For example, if `dd3 LMN.V` is the highest, the next number is `4`.

Parse the number by extracting the digits immediately after `dd` in each zettelfied folder name.

### Step 3: Process each candidate folder

Sort the candidate folders **alphabetically**. For each candidate folder, in order:

#### 3a. Assign zettel ID

The zettel name is `dd<N> <FOLDER_NAME>` where `<N>` is the next sequential number and `<FOLDER_NAME>` is the current folder name.

Example: If the next number is `4` and the folder is `ALLY`, the zettel name is `dd4 ALLY`.

#### 3b. Create the child zettel markdown file

Create a file named `dd<N> <FOLDER_NAME>.md` **inside the folder** (before renaming). Use this exact format:

```
---
aliases: []
tags:
---
```

Then, list all `.pdf` files in the folder as Obsidian links, one per line:

```
- [[filename.pdf]]
```

Sort the PDF links alphabetically. Only include files ending in `.pdf` (case-insensitive). Do NOT include `.json`, `.py`, or any other file types.

#### 3c. Rename the folder

Rename the folder from its current name to the zettel name:

```bash
mv "dd Due Diligence/<FOLDER_NAME>" "dd Due Diligence/dd<N> <FOLDER_NAME>"
```

#### 3d. Update the parent zettel

Append a new line to `dd Due Diligence/dd Due Diligence.md`:

```
- [[dd<N> <FOLDER_NAME>]]
```

#### 3e. Create Background subfolder and move files

Create a subfolder named `dd<N> <FOLDER_NAME> Background` inside the renamed folder. Then move all files from the folder into this subfolder **except** the newly created zettel file (`dd<N> <FOLDER_NAME>.md`). This includes PDFs, `.json` files, `.py` files, and any other files.

```bash
mkdir "dd Due Diligence/dd<N> <FOLDER_NAME>/dd<N> <FOLDER_NAME> Background"
# Move all files except the zettel .md into the Background subfolder
find "dd Due Diligence/dd<N> <FOLDER_NAME>" -maxdepth 1 -type f ! -name "dd<N> <FOLDER_NAME>.md" -exec mv {} "dd Due Diligence/dd<N> <FOLDER_NAME>/dd<N> <FOLDER_NAME> Background/" \;
```

Also move any existing subfolders (except the newly created Background folder) into the Background subfolder.

#### 3f. Increment the counter

Increment `<N>` by 1 for the next candidate.

### Step 4: Print summary

After processing all candidates, print a summary table:

```
## dd-zettelfy Summary

| Old Folder | New Zettel | PDFs Linked |
|------------|-----------|-------------|
| ALLY       | dd4 ALLY  | 5           |
| ...        | ...       | ...         |

Parent zettel `dd Due Diligence.md` updated with N new links.
```

## Important Notes

- This skill is **idempotent**: running it again will skip already-zettelfied folders.
- Never rename files inside the folders — only the folder itself.
- The "No Zettel" folder is always excluded regardless of its contents.
- If a folder contains no PDFs, still create the zettel file (with just the YAML frontmatter and no links) and rename the folder.
