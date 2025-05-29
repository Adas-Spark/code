NOTE THAT mass_email_app_v2.ipynb IS THE MOST CURRENT VERSION AND HAS EXTENSIVE
DOCUMENTATION. Both versions run by:
conda activate gmail_gcal_interface
jupyter lab --no-browser



For emailing participants of the 2024 5K I did the below
1. Download tickets from Givebutter (there is an export option)
2. Grab just the first name, last name, email, and ticket type column. Then exclude virtual tickets:
cut -d',' -f5,6,7,9 tickets-2024-05-29-1167014355.csv|grep -v "Virtual"|cut -d',' -f1,2,3>tickets-2024-05-29-1167014355_cleaned.csv
# Remember to delete the header line...just do it manually with vi
2.5 IF you want to only email virtual participants instead then:
cut -d',' -f5,6,7,9 tickets-2024-05-29-1167014355.csv|grep "Virtual"|cut -d',' -f1,2,3>tickets-2024-05-29-1167014355_cleaned_virtual.csv
# Remember to delete the header line if it exists...just do it manually with vi
3. Save email template as a docx (using Google Docs)
4. Open Jupyter Lab in Ada's Spark profile:
conda activate gmail_gcal_interface
jupyter lab --no-browser
5. run mass_email_app.ipynb


For emailing all contacts
1. Use "cleaned" tab of listserv which can be found in Ada's Spark Shared gDrive. Check that it is up to date with all the emails



 
