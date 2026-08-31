#!/usr/bin/env python3
"""
Outlook Spam Killer using Microsoft Graph API
Works with PERSONAL Hotmail/Outlook accounts - NO AZURE REGISTRATION REQUIRED!
Supports selective deletion: gibberish domains get permanently deleted, others go to Trash.
"""

import requests
import json
import re
import time
import logging
import sys
from pathlib import Path

# --- CONFIGURATION ---
EMAIL = "email@domain.com"  # CHANGE THIS TO YOUR EMAIL

CLIENT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" # SEARCH THIS ONLINE

SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "offline_access"
]

TOKEN_FILE = Path.home() / ".outlook_spam_graph_token.json"
TARGET_FOLDER = "Junk Email"

# WHITELIST - Legitimate senders (never delete)
WHITELIST = [
    "good01@domain.com",
    "good02@domain.com",
    "good03@domain.com",
    "good04@domain.com",
    "good05@domain.com",
]

# BLACKLISTED SENDER NAME PATTERNS
BLACKLISTED_SENDER_NAMES = [
    "affiliate", "associate", "timeshare", "promo", "promotion",
    "credit", "debt", "consolidation", "relief", "settlement",
    "casino", "slots", "gambling", "jackpot", "lottery",
    "winner", "prize", "reward", "bonus", "free", "trial",
    "offer", "deal", "discount", "sale", "clearance",
    "urgent", "alert", "security alert", "account alert",
    "verify", "confirm", "update", "upgrade",
    "newsletter", "marketing", "advertisement",
    "sponsor", "partner", "representative", "advisor",
    "consultant", "specialist", "expert", "coach", "mentor",
    "guru", "academy", "institute", "university", "college",
    "degree", "diploma", "certification", "training",
    "workshop", "seminar", "webinar", "conference",
    "summit", "expo", "fair", "festival", "celebration",
    "anniversary", "birthday", "holiday", "special",
    "exclusive", "limited", "private", "invitation",
    "invite", "guest", "member", "membership", "club",
    "community", "network", "group", "team", "staff",
    "crew", "agent", "broker", "dealer", "distributor",
    "supplier", "vendor", "merchant", "retailer",
    "wholesale", "outlet", "store", "shop", "shopping",
    "purchase", "order", "delivery", "shipping", "tracking",
    "return", "refund", "exchange", "repair", "service",
    "support", "help", "assistance", "guide", "tips",
    "advice", "information", "news", "report", "analysis",
    "forecast", "prediction", "strategy", "secret", "hidden",
    "insider", "behind", "exposed", "revealed", "unveiled",
    "launch", "release", "new", "latest", "hot", "trending",
    "viral", "popular", "top", "best", "great", "amazing",
    "incredible", "unbelievable", "shocking", "surprising",
    "stunning", "spectacular", "fantastic", "wonderful",
    "awesome", "excellent", "superb", "outstanding",
    "exceptional", "extraordinary", "remarkable", "notable",
    "significant", "important", "critical", "essential",
    "vital", "crucial", "necessary", "required", "mandatory",
    "obligation", "commitment", "responsibility", "liability",
    "insurance", "warranty", "guarantee", "protection",
    "security", "safety", "privacy", "confidential",
    "personal", "individual", "unique", "specific",
    "particular", "certain", "selected", "chosen",
    "preferred", "favorite", "like", "share", "comment",
    "follow", "subscribe", "click", "tap", "swipe", "scroll",
    "view", "watch", "listen", "read", "learn", "discover",
    "explore", "experience", "enjoy", "celebrate",
    "congratulations", "congrats", "good job", "great job",
    "awesome job", "fantastic job",
]

# SPAM KEYWORDS in subject line
SPAM_KEYWORDS = [
    "relief", "tax", "taxes", "tax relief",
    "bitcoin", "crypto", "forex", "binary options",
    "loan", "mortgage", "refinance",
    "casino", "slots", "jackpot", "gambling",
    "viagra", "cialis", "pharmacy",
    "weight loss", "diet pill",
    "lottery", "winner", "prize",
    "inheritance", "nigerian prince",
    "click here", "act now", "limited time",
    "free trial", "money back",
    "pounds in", "lbs in", "lose weight", "fat loss",
]

# ============================================================
# SELECTIVE DELETION CONFIGURATION
# ============================================================
# Reasons that trigger PERMANENT DELETE (bypass Trash)
# Remove any reason from this list to move to Trash instead
PERMANENT_DELETE_REASONS = [
    "GIBBERISH_DOMAIN",      # Domain is random gibberish
    "GIBBERISH_LOCAL",       # Local-part is gibberish
    "GIBBERISH_BOTH",        # Both local and domain are gibberish
    "CONSONANT_ONLY",        # Domain is all consonants (no vowels)
    "NO_TLD",                # Domain has no .com, .org, etc.
    "MULTIPLE_DASHES",       # Multiple consecutive dashes
    "DASH_PATTERN",          # Suspicious dash pattern
    "RANDOM_SUBDOMAIN",      # Random subdomain like mail-we4-cj4
    "SPOOFED",               # Spoofing your email address
]

# Reasons that go to TRASH (safe delete)
# These are more likely to have false positives
TRASH_DELETE_REASONS = [
    "BLACKLIST_NAME",        # Sender name contains spam word
    "FAKE_BRAND",            # Pretending to be Amazon, PayPal, etc.
    "SUBJECT_KEYWORD",       # Subject contains spam keyword
]

# ============================================================

# LOG_FILE = Path.home() / "spam_killer_graph.log" # Disabled - use cron log instead
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler(LOG_FILE), # Disabled - use cron log instead
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- OAUTH2 TOKEN MANAGEMENT ---

def get_oauth2_token():
    token_data = None
    
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            logger.info("Found saved token file")
        except Exception as e:
            logger.warning(f"Could not read token file: {e}")
    
    if token_data and 'refresh_token' in token_data:
        logger.info("Attempting to refresh token...")
        try:
            refresh_data = {
                'client_id': CLIENT_ID,
                'grant_type': 'refresh_token',
                'refresh_token': token_data['refresh_token'],
                'scope': ' '.join(SCOPES)
            }
            
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data=refresh_data
            )
            
            if response.status_code == 200:
                new_token = response.json()
                if 'access_token' in new_token:
                    token_data.update(new_token)
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump(token_data, f)
                    logger.info("Token refreshed successfully")
                    return new_token['access_token']
        except Exception as e:
            logger.warning(f"Token refresh error: {e}")
    
    logger.info("Starting device code authentication...")
    
    try:
        device_data = {
            'client_id': CLIENT_ID,
            'scope': ' '.join(SCOPES)
        }
        
        response = requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/devicecode',
            data=device_data
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get device code: {response.text}")
            return None
            
        device_info = response.json()
        
        if 'user_code' not in device_info:
            logger.error(f"Unexpected response: {device_info}")
            return None
            
        user_code = device_info['user_code']
        device_code = device_info['device_code']
        verification_uri = device_info.get('verification_uri', 'https://microsoft.com/devicelogin')
        interval = device_info.get('interval', 5)
        
        print("\n" + "="*70)
        print("OUTLOOK SPAM KILLER - AUTHENTICATION REQUIRED")
        print("="*70)
        print(f"\n1. On ANY device with a browser, go to:")
        print(f"\n   {verification_uri}")
        print(f"\n2. Enter this code: {user_code}")
        print(f"\n3. Log in with your Microsoft account ({EMAIL})")
        print(f"4. Click 'Accept' to grant permissions")
        print("\n" + "="*70)
        print("Waiting for authentication... (timeout in 5 minutes)\n")
        
        max_attempts = 60
        for attempt in range(max_attempts):
            time.sleep(interval)
            
            token_data = {
                'client_id': CLIENT_ID,
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'device_code': device_code
            }
            
            response = requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data=token_data
            )
            
            if response.status_code == 200:
                token_response = response.json()
                if 'access_token' in token_response:
                    with open(TOKEN_FILE, 'w') as f:
                        json.dump(token_response, f)
                    logger.info("Authentication successful! Token saved.")
                    return token_response['access_token']
            
            if response.status_code == 400:
                error_data = response.json()
                error = error_data.get('error')
                if error == 'authorization_pending':
                    if attempt % 6 == 0:
                        print(f"Still waiting... ({attempt * interval}s elapsed)")
                    continue
                elif error == 'expired_token':
                    logger.error("Device code expired.")
                    return None
                elif error:
                    logger.error(f"Authentication error: {error}")
                    return None
        
        logger.error("Authentication timed out")
        return None
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return None

def graph_request(token, method, url, data=None, params=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers, params=params)
    elif method.upper() == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method.upper() == 'DELETE':
        response = requests.delete(url, headers=headers)
    elif method.upper() == 'PATCH':
        response = requests.patch(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 5))
        logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after + 1)
        return graph_request(token, method, url, data, params)
    
    return response

# --- SPAM DETECTION LOGIC (Returns reason for deletion) ---

def is_spam(email_address, from_name="", subject=""):
    """
    Returns: (is_spam, reason)
    reason is a string describing WHY it was flagged as spam
    """
    if not email_address:
        return False, ""

    # WHITELIST CHECK
    if email_address.lower() in [w.lower() for w in WHITELIST]:
        return False, ""

    if '@' in email_address:
        local, domain = email_address.rsplit('@', 1)
        for w in WHITELIST:
            if '@' in w and w.split('@')[1].lower() == domain.lower():
                return False, ""
    
    # SUBJECT KEYWORD CHECK
    if subject:
        subject_lower = subject.lower()
        for keyword in SPAM_KEYWORDS:
            if keyword.lower() in subject_lower:
                return True, f"SUBJECT_KEYWORD:{keyword}"
    
    if '@' not in email_address:
        return False, ""
        
    local, domain = email_address.rsplit('@', 1)
    
    # Skip legitimate Microsoft emails
    if domain.lower().endswith("hotmail.com") or domain.lower().endswith("outlook.com"):
        return False, ""

    # RULE 1: Your email spoofed in sender
    if "email" in email_address.lower():
        return True, "SPOOFED"

    # RULE 2: FAKE BRAND DETECTION
    fake_brands = ['amazon', 'paypal', 'apple', 'microsoft', 'google', 'netflix', 'spotify', 'ebay']
    if from_name:
        from_name_lower = from_name.lower()
        for brand in fake_brands:
            if brand in from_name_lower:
                if brand not in domain.lower():
                    return True, f"FAKE_BRAND:{brand}"

    # RULE 3: NO TLD IN DOMAIN
    if '.' not in domain:
        if len(domain) > 8:
            vowels = sum(1 for c in domain.lower() if c in 'aeiou')
            if vowels < 4:
                return True, "NO_TLD"
    
    # RULE 4: DOMAIN WITH DASHES AND RANDOM PATTERNS
    clean_domain = domain.lower()
    clean_domain = re.sub(r'\.(com|org|net|xyz|info|biz|club|online|site|tech|io|co|uk|us|ca|au|de|fr|eu|it|es|br|com\.br|org\.br|net\.br|gov\.br|edu\.br|tv)$', '', clean_domain)
    clean_domain = re.sub(r'^(mail|email|smtp|imap|pop|www|web|api|app|news|info|secure|login|auth|service|support|help|admin|manager|portal|no-reply|noreply)\.', '', clean_domain)
    
    if '-' in domain:
        if re.search(r'-{2,}', domain):
            return True, "MULTIPLE_DASHES"
        parts = domain.split('-')
        if len(parts) > 3:
            for part in parts:
                if len(part) > 5:
                    vowels = sum(1 for c in part.lower() if c in 'aeiou')
                    if vowels < 2 and re.search(r'[A-Z0-9]', part):
                        return True, "DASH_PATTERN"
    
    domain_parts = domain.split('.')
    if len(domain_parts) >= 3:
        first_part = domain_parts[0]
        if re.search(r'-', first_part) and len(first_part) > 8:
            if re.search(r'[a-z]+\d+[a-z]+\d+', first_part):
                return True, "RANDOM_SUBDOMAIN"
    
    if len(clean_domain) > 8:
        vowels = sum(1 for c in clean_domain.lower() if c in 'aeiou')
        uppercase = sum(1 for c in clean_domain if c.isupper())
        lowercase = sum(1 for c in clean_domain if c.islower())
        has_numbers = bool(re.search(r'\d', clean_domain))
        
        if vowels < 3 and (uppercase > lowercase * 2 or has_numbers):
            return True, "GIBBERISH_DOMAIN"
        
        if uppercase > 0 and lowercase == 0 and vowels == 0:
            return True, "GIBBERISH_DOMAIN"
        
        if re.search(r'[A-Z0-9]{5,}[0-9][A-Z]{5,}', clean_domain, re.IGNORECASE):
            return True, "GIBBERISH_DOMAIN"

    # RULE 5: LOCAL-PART gibberish
    local_clean = re.sub(r'^(noreply|support|info|admin|sales|help|service|team|update|alert|notification|mailer|sender|no-reply|contato|atendimento|comercial|financeiro|rh)\.?', '', local, flags=re.IGNORECASE)
    
    if len(local_clean) > 8:
        vowels = sum(1 for c in local_clean.lower() if c in 'aeiou')
        uppercase = sum(1 for c in local_clean if c.isupper())
        lowercase = sum(1 for c in local_clean if c.islower())
        has_numbers = bool(re.search(r'\d', local_clean))
        
        if vowels < 3 and (uppercase > lowercase * 2 or has_numbers):
            return True, "GIBBERISH_LOCAL"
        
        if uppercase > 0 and lowercase == 0 and vowels == 0:
            return True, "GIBBERISH_LOCAL"

    # RULE 6: Classic spam pattern - both local and domain are gibberish
    if re.match(r'^[A-Z0-9]{6,}$', local, re.IGNORECASE) and re.match(r'^[A-Z0-9]{10,}\.(com|org|net|xyz|info|biz|club|online|site|tech)$', domain, re.IGNORECASE):
        local_vowels = sum(1 for c in local.lower() if c in 'aeiou')
        domain_vowels = sum(1 for c in domain.lower() if c in 'aeiou')
        if local_vowels < 2 and domain_vowels < 3:
            return True, "GIBBERISH_BOTH"

    # RULE 7: Consonant-only domain
    if len(domain) > 6:
        vowels = sum(1 for c in domain.lower() if c in 'aeiou')
        if vowels <= 2 and len(domain) > 6:
            common_words = ['crypto', 'trust', 'fund', 'bank', 'cash', 'gold', 'deal', 'shop', 'cart', 'gift']
            if not any(word in domain.lower() for word in common_words):
                return True, "CONSONANT_ONLY"

    # RULE 0: BLACKLISTED SENDER NAME (check last because it's the least specific)
    if from_name:
        from_name_lower = from_name.lower()
        for bad_word in BLACKLISTED_SENDER_NAMES:
            if bad_word.lower() in from_name_lower:
                return True, f"BLACKLIST_NAME:{bad_word}"

    return False, ""

# --- MAIN CLEANUP FUNCTION ---

def clean_junk_folder():
    logger.info("="*50)
    logger.info("Starting Outlook Spam Killer (Graph API)")
    logger.info(f"Checking email: {EMAIL}")
    logger.info(f"Permanent delete reasons: {PERMANENT_DELETE_REASONS}")
    
    token = get_oauth2_token()
    if not token:
        logger.error("Failed to get access token")
        return

    try:
        logger.info(f"Looking for '{TARGET_FOLDER}' folder...")
        
        response = graph_request(token, 'GET', 'https://graph.microsoft.com/v1.0/me/mailFolders')
        if response.status_code != 200:
            logger.error(f"Failed to get mail folders: {response.status_code}")
            return
            
        folders = response.json().get('value', [])
        target_folder_id = None
        target_folder_name = None
        
        for folder in folders:
            display_name = folder.get('displayName', '')
            if display_name.lower() == TARGET_FOLDER.lower():
                target_folder_id = folder.get('id')
                target_folder_name = display_name
                break
            elif 'junk' in display_name.lower():
                target_folder_id = folder.get('id')
                target_folder_name = display_name
                logger.info(f"Found Junk folder as '{target_folder_name}'")
                break
        
        if not target_folder_id:
            logger.error(f"Could not find '{TARGET_FOLDER}' folder")
            logger.info("Available folders:")
            for folder in folders:
                logger.info(f"  - {folder.get('displayName')}")
            return
            
        logger.info(f"Found '{target_folder_name}' folder: {target_folder_id}")
        
        logger.info("Fetching messages from Junk folder...")
        
        response = graph_request(
            token, 'GET',
            f'https://graph.microsoft.com/v1.0/me/mailFolders/{target_folder_id}/messages',
            params={'$select': 'id,subject,from,receivedDateTime,replyTo,sender', '$top': 200}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get messages: {response.status_code}")
            return
            
        messages = response.json().get('value', [])
        total_count = len(messages)
        logger.info(f"Found {total_count} messages in Junk folder")
        
        if total_count == 0:
            logger.info("No messages to process")
            return
        
        deleted_count = 0
        processed_count = 0
        permanent_count = 0
        trash_count = 0
        
        for msg in messages:
            processed_count += 1
            
            try:
                from_data = msg.get('from', {})
                email_address = from_data.get('emailAddress', {})
                sender_email = email_address.get('address', '')
                sender_name = email_address.get('name', '')
                
                sender_data = msg.get('sender', {})
                sender_email_addr = sender_data.get('emailAddress', {}).get('address', '')
                
                subject = msg.get('subject', 'No Subject')
                msg_id = msg.get('id')
                
                reply_to = msg.get('replyTo', [])
                reply_to_email = ""
                if reply_to and len(reply_to) > 0:
                    reply_to_email = reply_to[0].get('emailAddress', {}).get('address', '')
                
                if sender_email_addr and sender_email_addr != sender_email:
                    if is_spam(sender_email_addr, "", subject):
                        pass
                
                if reply_to_email and sender_email:
                    reply_domain = reply_to_email.split('@')[-1] if '@' in reply_to_email else ''
                    sender_domain = sender_email.split('@')[-1] if '@' in sender_email else ''
                    if reply_domain and sender_domain and reply_domain != sender_domain:
                        if '-' in reply_domain or re.search(r'[A-Z0-9]{8,}', reply_domain, re.IGNORECASE):
                            logger.info(f"REPLY-TO SPOOF: From={sender_domain}, Reply-To={reply_domain}")
                
                # Check if spam and get the reason
                is_spam_email = False
                spam_reason = ""
                
                if sender_email:
                    is_spam_email, spam_reason = is_spam(sender_email, sender_name, subject)
                elif sender_email_addr:
                    is_spam_email, spam_reason = is_spam(sender_email_addr, "", subject)
                elif reply_to_email:
                    is_spam_email, spam_reason = is_spam(reply_to_email, "", subject)
                
                if is_spam_email:
                    logger.info(f"DELETING SPAM: {sender_email} - Reason: {spam_reason} - Subject: {subject[:50]}")
                    
                    # ============================================================
                    # SELECTIVE DELETION LOGIC
                    # ============================================================
                    
                    # Check if this reason should be permanently deleted
                    should_permanent_delete = False
                    for reason_pattern in PERMANENT_DELETE_REASONS:
                        if reason_pattern in spam_reason:
                            should_permanent_delete = True
                            break
                    
                    if should_permanent_delete:
                        # PERMANENT DELETE - bypass trash
                        response = graph_request(
                            token, 'DELETE',
                            f'https://graph.microsoft.com/v1.0/me/messages/{msg_id}'
                        )
                        if response.status_code in [200, 204]:
                            deleted_count += 1
                            permanent_count += 1
                            logger.info(f"  ✓ PERMANENTLY DELETED (reason: {spam_reason})")
                        else:
                            logger.warning(f"  ✗ Failed to delete: {response.status_code}")
                    else:
                        # MOVE TO TRASH (safe delete)
                        response = graph_request(
                            token, 'POST',
                            f'https://graph.microsoft.com/v1.0/me/messages/{msg_id}/move',
                            data={'destinationId': 'deleteditems'}
                        )
                        
                        if response.status_code == 201:
                            deleted_count += 1
                            trash_count += 1
                            logger.info(f"  ✓ Moved to Trash (reason: {spam_reason})")
                        else:
                            # Fallback: try permanent delete if move fails
                            response = graph_request(
                                token, 'DELETE',
                                f'https://graph.microsoft.com/v1.0/me/messages/{msg_id}'
                            )
                            if response.status_code in [200, 204]:
                                deleted_count += 1
                                permanent_count += 1
                                logger.info(f"  ✓ PERMANENTLY DELETED (move failed)")
                            else:
                                logger.warning(f"  ✗ Failed to delete: {response.status_code}")
                
                if processed_count % 10 == 0:
                    logger.info(f"Progress: {processed_count}/{total_count} messages processed")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
            
            time.sleep(0.2)
        
        logger.info(f"✅ Successfully deleted {deleted_count} spam emails")
        logger.info(f"   - Permanently deleted: {permanent_count}")
        logger.info(f"   - Moved to Trash: {trash_count}")
        logger.info("Spam Killer run completed")
        logger.info("="*50)

    except Exception as e:
        logger.error(f"Script failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    try:
        if "--first-time" in sys.argv:
            logger.info("First-time setup mode - forcing authentication")
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
                logger.info("Deleted existing token file")
        
        clean_junk_folder()
        
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
