# Custom Email Merge Tool

This directory contains a custom mail merge tool primarily used for sending bulk emails, such as to 5K race participants. It's designed to send personalized mass emails while maintaining a personal touch and avoiding spam filters.

**Current Version:** The most up-to-date notebook for this tool is **`mass_email_app_v2.ipynb`**. This version has extensive documentation within the notebook itself.

## Key Features of `mass_email_app_v2.ipynb`

* Reads participant data from a CSV file (First Name, Last Name, Email).
* Converts DOCX email templates into HTML, supporting personalized greetings (e.g., "Hi John" or "Hi Mary, Bob, and Jane").
* Groups multiple participants sharing the same email address into a single email.
* Supports adding attachments to emails.
* Uses the Gmail API for reliable email delivery and handles Google OAuth2 authentication with token persistence.
* Implements smart exponential backoff with jittering to manage rate limiting.
* Includes email address validation and logs failed deliveries with automatic retry logic.
* Option to customize the email subject line with family name(s).

## Dependencies

* pandas
* google-auth-oauthlib
* google-auth
* google-api-python-client
* pypandoc

## Required Files for `mass_email_app_v2.ipynb`

1.  **`credentials.json`**: Google API credentials. Obtain from Google Cloud Console if needed.
2.  **Participant CSV file**:
    * Must NOT contain a header row.
    * Must contain exactly 3 columns in the order: First Name, Last Name, Email Address (e.g., "John,Smith,john.smith@email.com").
3.  **DOCX Email Template**:
    * Must contain the placeholder `"{person or persons}"` where names should be inserted. This will be replaced with individual or family names.
4.  **Attachments (Optional)**: Any files to be attached to the email.

## General Usage Workflow (for `mass_email_app_v2.ipynb`)

1.  **Configure Variables:** At the top of the `mass_email_app_v2.ipynb` script, set:
    * `base_subject`: Email subject line template.
    * `csv_file_path`: Path to your participant CSV data.
    * `docx_template_path`: Path to your DOCX email template.
    * `attachments`: List of file paths for attachments (can be empty).
2.  **Run the Notebook:** The script will:
    * Process participant data.
    * Convert the DOCX template to HTML.
    * Authenticate with Gmail.
    * Send personalized emails.

## General Setup for Running the Notebooks

1.  **Activate Conda Environment:**
    ```bash
    conda activate gmail_gcal_interface
    ```
   
2.  **Launch Jupyter Lab:**
    ```bash
    jupyter lab --no-browser
    ```
   
3.  Open and run the appropriate Jupyter Notebook (currently `mass_email_app_v2.ipynb`).

---

## Process for Emailing 2025 5K Participants (using `mass_email_app_v2.ipynb`)

1.  **Download Tickets:**
    * From Givebutter, export event attendees (Event > Attendees > Export).
    * Include only the "first name," "last name," "email," and "ticket type" columns.
2.  **Prepare CSV File:**
    * **To exclude virtual tickets:**
        ```bash
        grep -v "Virtual" tickets-2025-06-02-467515950.csv | cut -d',' -f1,2,3 > tickets-2025-06-02-467515950_cleaned.csv
        ```
        *Remember to manually delete the header line from the `_cleaned.csv` file (e.g., using `vi`).*
    * **To email ONLY virtual participants:**
        ```bash
        grep "Virtual" tickets-2025-06-02-467515950.csv | cut -d',' -f1,2,3 > tickets-2025-06-02-467515950_VIRTUAL_cleaned.csv
        ```
        *Remember to manually delete the header line if it exists.*
3.  **Email Template:** Save your email template as a `.docx` file (e.g., using Google Docs). Make sure it includes the `"{person or persons}"` placeholder.
4.  **Configure and Run Notebook:** Follow the "General Usage Workflow" and "General Setup" steps above, using `mass_email_app_v2.ipynb`.

---

## Process for Emailing 2024 5K Participants (Legacy)

*Note: This uses the older `mass_email_app.ipynb` notebook.*

1.  **Download Tickets:** From Givebutter.
2.  **Prepare CSV File:**
    * **To exclude virtual tickets:**
        ```bash
        cut -d',' -f5,6,7,9 tickets-2024-05-29-1167014355.csv | grep -v "Virtual" | cut -d',' -f1,2,3 > tickets-2024-05-29-1167014355_cleaned.csv
        ```
        *Remember to manually delete the header line.*
    * **To email ONLY virtual participants:**
        ```bash
        cut -d',' -f5,6,7,9 tickets-2024-05-29-1167014355.csv | grep "Virtual" | cut -d',' -f1,2,3 > tickets-2024-05-29-1167014355_cleaned_virtual.csv
        ```
        *Remember to manually delete the header line if it exists.*
3.  **Email Template:** Save as a `.docx` file.
4.  **Configure and Run Notebook:** Follow the "General Setup" steps and run `mass_email_app.ipynb`.

---

## Process for Emailing All Contacts

1.  Use the "cleaned" tab of the listserv, which can be found in Ada's Spark Shared Google Drive.
2.  Ensure the list is up-to-date with all emails.
3.  Follow the "General Usage Workflow" and "General Setup" (likely using `mass_email_app_v2.ipynb`).
