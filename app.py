#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OTP FORWARDER - WITH NUMBER LIST FEATURE
=============================================
Developer: @junaidniz786

"""

import os
import re
import time
import json
import requests
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import sys
import asyncio
from bs4 import BeautifulSoup

# ================== CONFIGURATION ==================

TELEGRAM_BOT_TOKEN = "8225744822:AAEDhMi-9u2GlgZstgVPBzai_sXCCFAyb14"

# Mode 1: Secret Key API
SECRET_KEY_MODE = {
    "ENABLED": False,  # True karo dono modes try karega
    "API_URL": "5qQRKCMH3J7eXBbNP4T8",
    "SECRET_KEY": "socket.io/?token=eyJpdiI6IkFGT294QWpNdmUvTFVlNW5IWjBSZkE9PSIsInZhbHVlIjoiSXQvaWg2U0dwcHRWRjUxWnRwYzFxaktZbnlGUUpoQitGZXUwZDZQMVNSODJPVDVqYjEwZWYyUHo2a2JaZDdhWEZReWdSbFh5dHBkMTNjaEdvbEdrTXpwalBlUkh5Ny9DUVExN2krbzBXNmdnVUF3WTlpZjlPZ1ZtT1dMTEdKaXo4Ty9nT2lrUGF0ZUZ5R2hoWWk3Ykt6NWNmckxzZ21UajFhVDlXUnVHU3JmaUxaQzgzRWpSb0swdDlOVlptNjBxWXF4TXU2UU0yMmxIOTA1SHdXdzhmSVdEckwyUHBzWVVDTVZ1bzNvTDZueFVtbWRpNE0wL2R5cXZSYkVIS1pDSjRpa0xQdkRicHdBbnRneG1WMEw4dnB6TFAxWktNT1dHRnc0RHl1SUs4OUl0eUw0d1VkTmdPWkloeWNFYjRISXZJSEJMNGwvWFlJUHBYS292M21NRUNiNkVtU2hUQVhZb2ZBcVdrK1NsWmozbXRWOWkyWEtFVi9BTC9ZamdXRTNZeDJFeEFpaXFyeldDdmRCeHUrTU9BRnR6MTdOcFRtSFBEZHlrWkViOFlVSlQ2elFjblpRNm5DcFp5cmZRR0Fvb1VTUE5VVmErUVpqaGF6TUlscUN5UWZrbzZQK3hYbFZHR0ZHMnhqa3NpcTNvMFBWVEdBZVF6M0lBNm9KQy9WV3RmRU5pa2Y1blc3MVBwRVg0TXRXWnBqU2NVMzZZYzYwV2hRSVNZVHUxdXJ3PSIsIm1hYyI6ImQ4ZTY5MDNkZGE2ODAxYWQwZWVmODljMzZkZjcyMTA4MTg3OTZlMDczMTY3NjM3NDA3ZjUwYWFhMTljNTIzYzYiLCJ0YWciOiIifQ%3D%3D&user=45647a9e337790a72f927d374e271ffc&EIO=4&transport=websocket",
    "PARAMS": {"records": "20"}
}

# Mode 2: IVASMS Login Mode - FIXED VERSION
IVASMS_MODE = {
    "ENABLED": True,
    "USERNAME": "kumailahmed1947@gmail.com",
    "PASSWORD": "@Kumail1947",
    "BASE_URL": "https://www.ivasms.com",
    "LOGIN_URL": "https://www.ivasms.com/login",  # Changed from login.php
    "INBOX_URL": "https://www.ivasms.com/portal/live/my_sms"   # Changed from inbox.php
}
#right bro
# === Interval Setting ===
CHECK_INTERVAL = 4
# =======================

DEBUG_MODE = True

# ====================================================

logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Store groups
authorized_groups = {}
DATA_FILE = "groups.json"

# Store numbers to monitor
monitored_numbers = {}

def load_groups():
    global authorized_groups, monitored_numbers
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                authorized_groups = data.get("groups", {})
                monitored_numbers = data.get("numbers", {})
    except: pass

def save_groups():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({
                "groups": authorized_groups,
                "numbers": monitored_numbers
            }, f)
    except: pass

load_groups()

# ================ COUNTRY DETECTION ================

COUNTRY_CODES = {
    "1": "USA/Canada", "54": "Argentina", "55": "Brazil", "56": "Chile",
    "57": "Colombia", "58": "Venezuela", "51": "Peru", "52": "Mexico",
    "44": "United Kingdom", "49": "Germany", "33": "France", "39": "Italy",
    "34": "Spain", "91": "India", "92": "Pakistan", "880": "Bangladesh",
    "966": "Saudi Arabia", "971": "UAE", "20": "Egypt", "27": "South Africa",
    "7": "Russia", "81": "Japan", "82": "South Korea", "86": "China",
    "90": "Turkey", "31": "Netherlands", "41": "Switzerland", "61": "Australia",
}

def detect_country(phone):
    """Detect country from phone number"""
    try:
        phone = re.sub(r'\D', '', str(phone))
        if not phone:
            return "Unknown", ""
        
        for code in sorted(COUNTRY_CODES.keys(), key=len, reverse=True):
            if phone.startswith(code):
                return COUNTRY_CODES[code], code
        
        first_digit = phone[0]
        if first_digit == '1': return "USA/Canada", "1"
        if first_digit == '7': return "Russia", "7"
        return "Unknown", phone[:3]
    except:
        return "Unknown", ""

def format_phone_number(phone):
    """Format phone number"""
    try:
        clean = re.sub(r'\D', '', str(phone))
        if not clean:
            return str(phone), "Unknown", ""
        
        country, code = detect_country(clean)
        
        if code == "58":  # Venezuela
            if len(clean) >= 10:
                formatted = f"+{clean[:2]} {clean[2:5]} {clean[5:9]} {clean[9:]}"
            elif len(clean) == 7:
                formatted = f"+58 {clean[:3]} {clean[3:]}"
            else:
                formatted = f"+{clean}"
        elif code == "91":  # India
            if len(clean) >= 10:
                formatted = f"+91 {clean[2:7]} {clean[7:]}"
            else:
                formatted = f"+{clean}"
        elif code == "1":  # USA/Canada
            if len(clean) >= 10:
                formatted = f"+1 ({clean[1:4]}) {clean[4:7]}-{clean[7:11]}"
            else:
                formatted = f"+{clean}"
        else:
            if len(clean) > 10:
                parts = [clean[:3], clean[3:7], clean[7:]]
                formatted = f"+{parts[0]} {parts[1]} {parts[2]}"
            else:
                formatted = f"+{clean}"
        
        return formatted, country, code
    except:
        return str(phone), "Unknown", ""

# ================ OTP EXTRACTION ================

def extract_otp_from_message(message):
    """Extract OTP from message"""
    if not message:
        return "N/A"
    
    message = str(message)
    
    # WhatsApp style with hyphen (569-193)
    wa_match = re.search(r'(\d{3})[-](\d{3})', message)
    if wa_match:
        return wa_match.group(1) + wa_match.group(2)
    
    # Common OTP patterns
    keywords = ['code', 'otp', 'verification', 'pin', 'is']
    for keyword in keywords:
        pattern = rf'{keyword}[\s:]*(\d{{4,8}})'
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Any 4-8 digit number
    numbers = re.findall(r'\b(\d{4,8})\b', message)
    if numbers:
        for otp in numbers:
            if otp not in ['2024', '2025', '2026', '2027', '2028']:
                return otp
    
    return "N/A"

# ================ SECRET KEY MODULE ================

class SecretKeyModule:
    def __init__(self):
        self.name = "Secret Key API"
        self.enabled = SECRET_KEY_MODE["ENABLED"]
        self.api_url = SECRET_KEY_MODE["API_URL"]
        self.secret_key = SECRET_KEY_MODE["SECRET_KEY"]
        self.sent_ids = set()
        
        if self.enabled:
            self.test_api()

    def test_api(self):
        print(f"\n{'='*50}")
        print("🔍 TESTING SECRET KEY API")
        print(f"{'='*50}")
        try:
            params = SECRET_KEY_MODE["PARAMS"].copy()
            params["token"] = self.secret_key
            response = requests.get(self.api_url, params=params, timeout=10)
            if response.status_code == 200:
                print(f"✅ Secret Key API OK")
            else:
                print(f"❌ Secret Key API Error")
                self.enabled = False
        except Exception as e:
            print(f"❌ Secret Key Connection Error")
            self.enabled = False
        print(f"{'='*50}\n")

    def fetch_otps(self):
        if not self.enabled:
            return []
        try:
            params = SECRET_KEY_MODE["PARAMS"].copy()
            params["token"] = self.secret_key
            response = requests.get(self.api_url, params=params, timeout=10)
            data = response.json()
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "data" in data:
                return data["data"]
            return []
        except:
            return []

    def process_otps(self):
        if not self.enabled:
            return []
            
        all_otps = self.fetch_otps()
        if not all_otps:
            return []
            
        new_otps = []
        
        for otp in all_otps[:20]:
            try:
                if isinstance(otp, (list, tuple)) and len(otp) >= 3:
                    app = str(otp[0]) if len(otp) > 0 and otp[0] else "Unknown"
                    phone = str(otp[1]) if len(otp) > 1 and otp[1] else ""
                    message = str(otp[2]) if len(otp) > 2 and otp[2] else ""
                    timestamp = str(otp[3]) if len(otp) > 3 and otp[3] else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    formatted_phone, country, country_code = format_phone_number(phone)
                    extracted_otp = extract_otp_from_message(message)
                    clean_phone = re.sub(r'\D', '', phone)
                    
                    otp_id = f"sk_{phone}_{timestamp}_{message[:20]}"
                    
                    if otp_id not in self.sent_ids:
                        self.sent_ids.add(otp_id)
                        
                        new_otp = {
                            'source': '🔑',
                            'app': app,
                            'phone': phone,
                            'clean_phone': clean_phone,
                            'formatted_phone': formatted_phone,
                            'message': message,
                            'timestamp': timestamp,
                            'country': country,
                            'country_code': country_code,
                            'otp': extracted_otp
                        }
                        new_otps.append(new_otp)
                        
                        print(f"🎯 [Secret Key] {country}: {app} - {formatted_phone}")
            except:
                continue
        
        if len(self.sent_ids) > 2000:
            self.sent_ids = set(list(self.sent_ids)[-1000:])
        
        return new_otps

# ================ IVASMS MODULE - FIXED VERSION ================

class IVASMSModule:
    def __init__(self):
        self.name = "IVASMS"
        self.enabled = IVASMS_MODE["ENABLED"]
        self.username = IVASMS_MODE["USERNAME"]
        self.password = IVASMS_MODE["PASSWORD"]
        self.base_url = IVASMS_MODE["BASE_URL"]
        self.login_url = IVASMS_MODE["LOGIN_URL"]
        self.inbox_url = IVASMS_MODE["INBOX_URL"]
        self.session = requests.Session()
        self.logged_in = False
        self.sent_ids = set()
        
        if self.enabled:
            self.test_login()

    def test_login(self):
        print(f"\n{'='*50}")
        print("🔍 TESTING IVASMS LOGIN")
        print(f"{'='*50}")
        
        try:
            # Try different login methods
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Method 1: Try to get login page first
            login_page = self.session.get(self.login_url, headers=headers, timeout=10)
            
            # Look for CSRF token if any
            soup = BeautifulSoup(login_page.text, 'html.parser')
            csrf_token = None
            token_input = soup.find('input', {'name': 'csrf_token'}) or soup.find('input', {'name': 'token'})
            if token_input:
                csrf_token = token_input.get('value')
            
            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password
            }
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            # Try POST login
            response = self.session.post(
                self.login_url, 
                data=login_data, 
                headers=headers,
                allow_redirects=True,
                timeout=10
            )
            
            # Check if login successful
            if response.status_code == 200:
                # Check if redirected to dashboard or contains success message
                if 'inbox' in response.url or 'dashboard' in response.url or 'logout' in response.text.lower():
                    print("✅ IVASMS Login Successful!")
                    self.logged_in = True
                else:
                    print("❌ IVASMS Login Failed - Invalid credentials or page structure changed")
                    self.enabled = False
            else:
                print(f"❌ IVASMS Login Failed! Status: {response.status_code}")
                self.enabled = False
                
        except Exception as e:
            print(f"❌ IVASMS Connection Error: {e}")
            self.enabled = False
        
        print(f"{'='*50}\n")

    def fetch_otps(self):
        if not self.enabled or not self.logged_in:
            return []
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = self.session.get(self.inbox_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                messages = []
                
                # Try different table structures
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            phone = cols[0].text.strip()
                            message = cols[1].text.strip()
                            timestamp = cols[2].text.strip()
                            
                            if phone and message:
                                messages.append({
                                    'phone': phone,
                                    'message': message,
                                    'time': timestamp
                                })
                
                # If no tables found, try div structure
                if not messages:
                    msg_divs = soup.find_all('div', class_='message')
                    for div in msg_divs:
                        phone_div = div.find('div', class_='phone')
                        msg_div = div.find('div', class_='text')
                        time_div = div.find('div', class_='time')
                        
                        if phone_div and msg_div:
                            messages.append({
                                'phone': phone_div.text.strip(),
                                'message': msg_div.text.strip(),
                                'time': time_div.text.strip() if time_div else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                
                return messages
            else:
                print(f"IVASMS fetch failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"IVASMS fetch error: {e}")
            return []

    def process_otps(self):
        if not self.enabled or not self.logged_in:
            return []
            
        all_otps = self.fetch_otps()
        if not all_otps:
            return []
            
        new_otps = []
        
        for otp in all_otps[:10]:
            try:
                phone = otp.get('phone', '')
                message = otp.get('message', '')
                timestamp = otp.get('time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                # Detect app
                app = "SMS"
                msg_lower = message.lower()
                if "facebook" in msg_lower: app = "Facebook"
                elif "whatsapp" in msg_lower: app = "WhatsApp"
                elif "google" in msg_lower: app = "Google"
                elif "instagram" in msg_lower: app = "Instagram"
                elif "twitter" in msg_lower: app = "Twitter"
                elif "amazon" in msg_lower: app = "Amazon"
                elif "paypal" in msg_lower: app = "PayPal"
                elif "bank" in msg_lower: app = "Bank"
                elif "imo" in msg_lower: app = "IMO"
                elif "telegram" in msg_lower: app = "Telegram"
                
                formatted_phone, country, country_code = format_phone_number(phone)
                extracted_otp = extract_otp_from_message(message)
                clean_phone = re.sub(r'\D', '', phone)
                
                otp_id = f"ivasms_{phone}_{timestamp}_{message[:20]}"
                
                if otp_id not in self.sent_ids:
                    self.sent_ids.add(otp_id)
                    
                    new_otp = {
                        'source': '📱',
                        'app': app,
                        'phone': phone,
                        'clean_phone': clean_phone,
                        'formatted_phone': formatted_phone,
                        'message': message,
                        'timestamp': timestamp,
                        'country': country,
                        'country_code': country_code,
                        'otp': extracted_otp
                    }
                    new_otps.append(new_otp)
                    
                    print(f"🎯 [IVASMS] {country}: {app} - {formatted_phone}")
            except:
                continue
        
        if len(self.sent_ids) > 2000:
            self.sent_ids = set(list(self.sent_ids)[-1000:])
        
        return new_otps

# ================ TELEGRAM HANDLERS ================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    
    if chat.type in ['group', 'supergroup']:
        group_id = str(chat.id)
        
        if group_id not in authorized_groups:
            authorized_groups[group_id] = {
                "active": True,
                "added_by": user.id,
                "added_at": datetime.now().isoformat(),
                "title": chat.title
            }
            save_groups()
            
            if group_id not in monitored_numbers:
                monitored_numbers[group_id] = {"numbers": [], "added_by": user.id}
                save_groups()
            
            active_modes = []
            if SECRET_KEY_MODE["ENABLED"]: active_modes.append("🔑 Secret Key")
            if IVASMS_MODE["ENABLED"] and ivasms_module and ivasms_module.logged_in: active_modes.append("📱 IVASMS")
            modes_text = ", ".join(active_modes) if active_modes else "⚠️ No active source"
            
            msg = f"""✅ *GROUP AUTHORIZED!*

📢 {chat.title}
🆔 `{group_id}`
👤 Added by: {user.first_name}

📡 Sources: {modes_text}
📋 Numbers: {len(monitored_numbers[group_id]['numbers'])}/20
⏱️ Check: Every {CHECK_INTERVAL}s
👥 Total: {len(authorized_groups)}"""
        else:
            active_modes = []
            if SECRET_KEY_MODE["ENABLED"]: active_modes.append("🔑 Secret Key")
            if IVASMS_MODE["ENABLED"] and ivasms_module and ivasms_module.logged_in: active_modes.append("📱 IVASMS")
            modes_text = ", ".join(active_modes) if active_modes else "⚠️ No active source"
            
            msg = f"""✅ *GROUP ACTIVE!*

📢 {chat.title}
🆔 `{group_id}`

📡 Sources: {modes_text}
📋 Numbers: {len(monitored_numbers.get(group_id, {}).get('numbers', []))}/20
⏱️ Check: Every {CHECK_INTERVAL}s"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Numbers", callback_data=f"show_{group_id}")],
            [InlineKeyboardButton("📊 Stats", callback_data=f"stats_{group_id}")]
        ]
        
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        welcome = f"""👋 *Welcome {user.first_name}!*

📡 *OTP Forwarder Bot*

🔹 *Commands:*
/start - Menu
/number - Manage numbers
/stats - Statistics
/test - Test connections

🔹 *Status:*
• Groups: {len(authorized_groups)}
• Interval: {CHECK_INTERVAL}s"""
        
        keyboard = [[
            InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ]]
        
        await update.message.reply_text(welcome, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# ================ NUMBER LIST FEATURE ================

async def number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    group_id = str(chat.id)
    
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("❌ This command only works in groups!")
        return
    
    if group_id not in monitored_numbers:
        monitored_numbers[group_id] = {"numbers": [], "added_by": user.id}
        save_groups()
    
    if not context.args:
        numbers = monitored_numbers[group_id]["numbers"]
        if not numbers:
            text = "📋 *No numbers added*\n\nUse `/number add +919876543210`"
        else:
            text = "📋 *Monitored Numbers*\n\n"
            for i, num in enumerate(numbers, 1):
                formatted, country, _ = format_phone_number(num)
                text += f"{i}. `{formatted}` ({country})\n"
            text += f"\nTotal: {len(numbers)}/20"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        return
    
    cmd = context.args[0].lower()
    
    if cmd == "add" and len(context.args) >= 2:
        number = context.args[1]
        number = re.sub(r'\s+', '', number)
        if not number.startswith('+'):
            number = '+' + number
        
        if not re.match(r'^\+\d{7,15}$', number):
            await update.message.reply_text("❌ Invalid format! Use: +919876543210")
            return
        
        if len(monitored_numbers[group_id]["numbers"]) >= 20:
            await update.message.reply_text("❌ Maximum 20 numbers allowed!")
            return
        
        if number not in monitored_numbers[group_id]["numbers"]:
            monitored_numbers[group_id]["numbers"].append(number)
            save_groups()
            formatted, country, _ = format_phone_number(number)
            await update.message.reply_text(f"✅ Added `{formatted}` ({country})!", parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Number already in list!")
    
    elif cmd == "clear":
        monitored_numbers[group_id]["numbers"] = []
        save_groups()
        await update.message.reply_text("✅ Cleared all numbers!")

# ================ MAIN FORWARDER ================

class OTPForwarder:
    def __init__(self, application):
        self.application = application
        self.bot = application.bot
        self.running = True
        self.modules = []
        
        global sk_module, ivasms_module
        
        sk_module = SecretKeyModule()
        if sk_module.enabled:
            self.modules.append(sk_module)
        
        ivasms_module = IVASMSModule()
        if ivasms_module.enabled and ivasms_module.logged_in:
            self.modules.append(ivasms_module)
        
        print(f"\n{'='*50}")
        print(f"✅ Bot Started!")
        print(f"👥 Groups: {len(authorized_groups)}")
        print(f"📋 Numbers: {sum(len(info.get('numbers', [])) for info in monitored_numbers.values())}")
        print(f"📡 Modules: {len(self.modules)}")
        for m in self.modules:
            print(f"   • {m.name}")
        print(f"⏱️ Interval: {CHECK_INTERVAL}s")
        print(f"{'='*50}\n")

    def should_forward(self, group_id, clean_phone):
        if group_id not in monitored_numbers:
            return False
        numbers = monitored_numbers[group_id].get("numbers", [])
        if not numbers:
            return True
        for num in numbers:
            num_clean = re.sub(r'\D', '', num)
            if clean_phone.endswith(num_clean[-10:]) or num_clean.endswith(clean_phone[-10:]):
                return True
        return False

    async def send_otp(self, otp_data):
        if not authorized_groups:
            return
        
        source = otp_data.get('source', '📡')
        phone = otp_data.get('formatted_phone', 'Unknown')
        clean_phone = otp_data.get('clean_phone', '')
        country = otp_data.get('country', 'Unknown')
        app = otp_data.get('app', 'Unknown')
        otp = otp_data.get('otp', 'N/A')
        message = otp_data.get('message', '')[:100]
        timestamp = otp_data.get('timestamp', datetime.now().strftime('%H:%M:%S'))

        text = f"""{source} *New OTP*

┌────────────────────┐
│ 🕒 {timestamp}
│ 🌍 {country}
│ 📱 `{phone}`
│ 🔑 OTP: *{otp}*
│ 📲 {app}
└────────────────────┘

📨 {message}

👑 @GAURAVZEX"""

        sent = 0
        for gid in list(authorized_groups.keys()):
            if self.should_forward(gid, clean_phone):
                try:
                    await self.bot.send_message(chat_id=int(gid), text=text, parse_mode='Markdown')
                    sent += 1
                except:
                    pass
        
        if sent > 0:
            print(f"✅ {source} {country}: {app} - {phone} - OTP: {otp}")

    async def run_loop(self):
        cycle = 0
        while self.running:
            try:
                cycle += 1
                for module in self.modules:
                    new_otps = module.process_otps()
                    if new_otps:
                        print(f"\n🎯 {module.name}: {len(new_otps)} new OTPs")
                        for otp in new_otps:
                            await self.send_otp(otp)
                            await asyncio.sleep(1)
                
                if cycle % 15 == 0:
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"\n📊 [{now}] Cycle: {cycle} | Groups: {len(authorized_groups)}")
                
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

# ================ MAIN ================

async def main():
    global application, sk_module, ivasms_module, forwarder
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("number", number_command))
    
    forwarder = OTPForwarder(application)
    asyncio.create_task(forwarder.run_loop())
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ Bot running!")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        forwarder.running = False
        await application.stop()
        print("\n⏹ Stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ Stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)
        #yooooooooooo

