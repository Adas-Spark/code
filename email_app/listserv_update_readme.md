# Listserv Update Script

## Purpose
Compare event ticket signups against the official listserv and add new contacts.
NOTE THAT THIS IS NOT QUITE PERFECT YET BECAUSE IF SOMEONE ADDS A NEW FAMILY MEMBER, IE THE EMAIL EXISTS
BUT THE FIRST NAME DOESNT THEN NOTHING WILL GET UPDATED


## Files
- `listserv_cleaned_12-6-25.csv` - Official listserv
- `tickets-2025-06-02-467515950_cleaned.csv` - Event signup list

## Step 1: Find New Emails
Find emails in the ticket file that aren't in the listserv:

```bash
comm -13 <(tr -d '"' < listserv_cleaned_12-6-25.csv | cut -f3 -d',' | tr -d ' \r' | sort -u) <(tr -d '"' < tickets-2025-06-02-467515950_cleaned.csv | cut -f3 -d',' | tr -d ' \r' | sort -u) > new_emails.txt
```

**What this does:**
- Strips quotes and whitespace from both files
- Extracts email column (field 3)
- Compares sorted unique emails
- Outputs emails only in ticket file

## Step 2: Extract Full Rows for New Emails
Get complete contact info for new emails and add to listserv:

```bash
echo "" >> listserv_cleaned_12-6-25.csv  # Add newline before appending
while IFS= read -r email; do
  grep -F "$email" tickets-2025-06-02-467515950_cleaned.csv | tr -d '"'
done < new_emails.txt >> listserv_cleaned_12-6-25.csv
```

**What this does:**
- For each new email, finds its full row in ticket file
- Strips quotes
- Appends to official listserv

## Step 3: Clean Line Endings (if needed)
If you see `^M` characters at line ends, remove them:

```bash
# macOS
sed -i '' 's/\r$//' listserv_cleaned_12-6-25.csv

# Linux
sed -i 's/\r$//' listserv_cleaned_12-6-25.csv
```

## Backup
Always backup before running:
```bash
cp listserv_cleaned_12-6-25.csv listserv_cleaned_12-6-25.csv.backup
```

## Common Issues
- **^M characters**: Run the line ending cleanup command above
- **Duplicate emails**: The script automatically handles this by checking existing emails first
