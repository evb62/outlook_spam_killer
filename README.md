# Outlook Spam Killer

My Outlook "Junk Email" folder gets dozens of spam messages every day, and I could not find a filter to automatically delete or trash them. The built-in filters in Outlook do not act on the Junk Email folder.

This script will read the `Junk Email` folder and give a destination to each message: permanently delete it, move to trash, or leave it in the junk folder.

## Requirements

- Python

## Installation

In the shell, type:
```
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install --break-system-packages requests
```
Then place the  script where you want to run it. Your home directory is fine. Make it executable:
```
chmod +x outlook_spam_killer_graph.py
```

### Configuration

**First, find a Client ID**. For that, you can try public IDs for Outlook, Thunderbird, Office, Azure, etc. Search them online, ymmv. For instance, in a search page, type:
`"What is the public ID of em Client/Mozilla Thunderbird/Mailbird?"`
The Cliend ID, or **GUID (Globally Unique Identifier)**, is a 128-bit number, written in 32 hexadecimal digits, used as a unique reference number (e.g., `123e4567-e89b-12d3-a456-426614174000` &mdash; just an example, do not use).


**Edit** the script, and search the following strings:
| String | Edit |
| :--- | :--- |
| `EMAIL = "email@domain.com"` | Insert your email address here |
| `CLIENT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"` | Replace with the client ID you found on your search |
| `# WHITELIST - Legitimate senders` | In the list below replace `"goodxx@domain.com"` with your legitimate sender list. Use quotes, and end with a comma. |
| `# BLACKLISTED SENDER NAME PATTERNS`| A default list is provided. Add or delete keywords at will. Use quotes, end with a comma. |
| `# SPAM KEYWORDS in subject line`| A default list is provided. Add or delete keywords at will. Use quotes, end with a comma. |
| `# SELECTIVE DELETION CONFIGURATION`| A list of reasons for deletion. Move those between a *permanent delete* (not recoverable) and *send to trash* (temporarily recoverable from the trash folder). |
| `# RULE 1: Your email spoofed in sender`| In the line below, replace `"email"` with the first part of your actual email. For instance, if your email address is `"johndoe@company.com"`, replace `"email"` with `"johndoe"`.
  
## Usage

First time run:
```
python3 ~/outlook_spam_killer_graph.py --first-time
```
You'll see:
```
======================================================================
OUTLOOK SPAM KILLER - AUTHENTICATION REQUIRED
======================================================================

1. On ANY device with a browser, go to:
   https://microsoft.com/devicelogin

2. Enter this code: ABC123XYZ (copy whatever you see here)

3. Log in with your Microsoft account
4. Click 'Accept' to grant permissions
======================================================================
Waiting for authentication... (timeout in 5 minutes)
```
The script will then process your Junk folder.

### Quick Commands Reference
| Action | Command |
| :--- | :--- |
| Run manually | `python3 ~/outlook_spam_killer_graph.py` |
| Force re-authentication | `python3 ~/outlook_spam_killer_graph.py --first-time` |
| Watch live log | `tail -f ~/spam_killer.log` |
| Edit script | `nano ~/outlook_spam_killer_graph.py` |
| Edit cron | `crontab -e` |
| View current cron | `crontab -l` |

### Where Everything Is Stored
| File | Purpose |
| :--- | :--- |
| `~/outlook_spam_killer_graph.py` | Main script |
| `~/.outlook_spam_graph_token.json` | Authentication token (auto-refreshed) |
| `~/spam_killer.log` | Script activity log |

### Troubleshooting

| Problem | Solution |
| :--- | :--- |
| Script not running | Check if it's executable: `chmod +x ~/outlook_spam_killer_graph.py` |
| Cron not running | Check log: `cat ~/spam_killer.log` |
| Authentication failed | Run with `--first-time` flag to re-authenticate |
| "Module not found" |  Install requests: `pip3 install --break-system-packages requests` |
| Token expired | Script auto-refreshes, or run with `--first-time` |

## Set Up Cron for Automatic Execution

Open your crontab:
```
crontab -e
```
If prompted, select **nano** as your editor.
Add this line to run the script every 15 minutes:
```
# Outlook Spam Killer - runs every 15 minutes
*/15 * * * * /usr/bin/python3 /home/pi/outlook_spam_killer_graph.py >> /home/pi/spam_killer.log 2>&1
```
Edit time interval and log output as you wish. In the example above, it runs every 15 minutes and writes the output to `home/pi`.
Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`

Verify cron is working:
```
crontab -l
```
You should see your spam killer entry.

## Default behavior
This is the default script behavior. You can customize this, see "Configuration" above.

| Reason |  Action | Why |
| :--- | :--- | :--- |
| `GIBBERISH_DOMAIN` | ✅ **Permanent Delete** | Domain is obviously fake/spam |
| `GIBBERISH_LOCAL` | ✅ **Permanent Delete** | Local-part is gibberish |
| `GIBBERISH_BOTH` | ✅ **Permanent Delete** | Both are gibberish |
| `CONSONANT_ONLY` | ✅ **Permanent Delete** | Random consonant string |
| `NO_TLD` | ✅ **Permanent Delete** | Missing .com, etc. |
| `MULTIPLE_DASHES` | ✅ **Permanent Delete** | Multiple dashes = spam |
| `DASH_PATTERN` | ✅ **Permanent Delete** | Suspicious dash pattern |
| `RANDOM_SUBDOMAIN` | ✅ **Permanent Delete** | Random subdomain |
| `SPOOFED` | ✅ **Permanent Delete** | Spoofing your email |
| `BLACKLIST_NAME:xxx` | ⚠️ **Move to Trash** | Could be a false positive |
| `FAKE_BRAND:xxx` | ⚠️ **Move to Trash** | Could be a mistaken brand |
| `SUBJECT_KEYWORD:xxx` | ⚠️ **Move to Trash** | Could be a legitimate email with "free" |

## Housekeeping
You might want to clean the log file from time to time. Here is a suggestion for setting up `logrotate`.
- Create an entry in logrotate:
```
sudo nano /etc/logrotate.d/spam_killer
```
- Insert the following text:
```
 /home/pi/spam_killer.log {
    weekly
    rotate 4
    copytruncate
    compress
    missingok
    notifempty
}
```
This is what it does:
-   **`weekly`**: Rotates the log file once every month.
-   **`rotate 4`**: Keeps 4 weeks of history (older files are deleted).
-   **`copytruncate`**: Copies the active log, then truncates (empties) the original in place so your active script never loses access to the file.
-   **`compress`**: Compresses the older logs using gzip to save disk space.
-   **`missingok`**: Prevents error messages if the log file is temporarily missing.
-   **`notifempty`**: Skips the rotation if the log file is completely empty.
