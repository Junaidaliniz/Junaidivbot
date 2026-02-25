# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
import tempfile
from urllib.parse import urljoin
from datetime import datetime, timedelta
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile

YOUR_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "7674691123:AAEMKKzUSxkJQK0Obv0ptIRBixYEui_6y78")

DATA_DIR = "data"
PANELS_FILE = os.path.join(DATA_DIR, "panels.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
OWNERS_FILE = os.path.join(DATA_DIR, "owners.json")
WELCOME_FILE = os.path.join(DATA_DIR, "welcome.json")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed_ids.json")

POLLING_INTERVAL_SECONDS = 5
LOGIN_REFRESH_INTERVAL = 600
LOGIN_FAIL_COOLDOWN = 300
_login_failures = {}
_range_otp_counts = {}

INITIAL_OWNER = "7011937754"

_processed_ids_cache = set()
_processed_ids_loaded = False

COUNTRY_FLAGS = {
    "Afghanistan": "\U0001f1e6\U0001f1eb", "Albania": "\U0001f1e6\U0001f1f1", "Algeria": "\U0001f1e9\U0001f1ff",
    "Andorra": "\U0001f1e6\U0001f1e9", "Angola": "\U0001f1e6\U0001f1f4", "Argentina": "\U0001f1e6\U0001f1f7",
    "Armenia": "\U0001f1e6\U0001f1f2", "Australia": "\U0001f1e6\U0001f1fa", "Austria": "\U0001f1e6\U0001f1f9",
    "Azerbaijan": "\U0001f1e6\U0001f1ff", "Bahrain": "\U0001f1e7\U0001f1ed", "Bangladesh": "\U0001f1e7\U0001f1e9",
    "Belarus": "\U0001f1e7\U0001f1fe", "Belgium": "\U0001f1e7\U0001f1ea", "Benin": "\U0001f1e7\U0001f1ef",
    "Bhutan": "\U0001f1e7\U0001f1f9", "Bolivia": "\U0001f1e7\U0001f1f4", "Brazil": "\U0001f1e7\U0001f1f7",
    "Bulgaria": "\U0001f1e7\U0001f1ec", "Burkina Faso": "\U0001f1e7\U0001f1eb", "Cambodia": "\U0001f1f0\U0001f1ed",
    "Cameroon": "\U0001f1e8\U0001f1f2", "Canada": "\U0001f1e8\U0001f1e6", "Chad": "\U0001f1f9\U0001f1e9",
    "Chile": "\U0001f1e8\U0001f1f1", "China": "\U0001f1e8\U0001f1f3", "Colombia": "\U0001f1e8\U0001f1f4",
    "Congo": "\U0001f1e8\U0001f1ec", "Croatia": "\U0001f1ed\U0001f1f7", "Cuba": "\U0001f1e8\U0001f1fa",
    "Cyprus": "\U0001f1e8\U0001f1fe", "Czech Republic": "\U0001f1e8\U0001f1ff", "Denmark": "\U0001f1e9\U0001f1f0",
    "Egypt": "\U0001f1ea\U0001f1ec", "Estonia": "\U0001f1ea\U0001f1ea", "Ethiopia": "\U0001f1ea\U0001f1f9",
    "Finland": "\U0001f1eb\U0001f1ee", "France": "\U0001f1eb\U0001f1f7", "Gabon": "\U0001f1ec\U0001f1e6",
    "Gambia": "\U0001f1ec\U0001f1f2", "Georgia": "\U0001f1ec\U0001f1ea", "Germany": "\U0001f1e9\U0001f1ea",
    "Ghana": "\U0001f1ec\U0001f1ed", "Greece": "\U0001f1ec\U0001f1f7", "Guatemala": "\U0001f1ec\U0001f1f9",
    "Guinea": "\U0001f1ec\U0001f1f3", "Haiti": "\U0001f1ed\U0001f1f9", "Honduras": "\U0001f1ed\U0001f1f3",
    "Hong Kong": "\U0001f1ed\U0001f1f0", "Hungary": "\U0001f1ed\U0001f1fa", "Iceland": "\U0001f1ee\U0001f1f8",
    "India": "\U0001f1ee\U0001f1f3", "Indonesia": "\U0001f1ee\U0001f1e9", "Iran": "\U0001f1ee\U0001f1f7",
    "Iraq": "\U0001f1ee\U0001f1f6", "Ireland": "\U0001f1ee\U0001f1ea", "Israel": "\U0001f1ee\U0001f1f1",
    "Italy": "\U0001f1ee\U0001f1f9", "IVORY COAST": "\U0001f1e8\U0001f1ee", "Ivory Coast": "\U0001f1e8\U0001f1ee",
    "Jamaica": "\U0001f1ef\U0001f1f2", "Japan": "\U0001f1ef\U0001f1f5", "Jordan": "\U0001f1ef\U0001f1f4",
    "Kazakhstan": "\U0001f1f0\U0001f1ff", "Kenya": "\U0001f1f0\U0001f1ea", "Kuwait": "\U0001f1f0\U0001f1fc",
    "Kyrgyzstan": "\U0001f1f0\U0001f1ec", "Laos": "\U0001f1f1\U0001f1e6", "Latvia": "\U0001f1f1\U0001f1fb",
    "Lebanon": "\U0001f1f1\U0001f1e7", "Liberia": "\U0001f1f1\U0001f1f7", "Libya": "\U0001f1f1\U0001f1fe",
    "Lithuania": "\U0001f1f1\U0001f1f9", "Luxembourg": "\U0001f1f1\U0001f1fa", "Madagascar": "\U0001f1f2\U0001f1ec",
    "Malaysia": "\U0001f1f2\U0001f1fe", "Mali": "\U0001f1f2\U0001f1f1", "Malta": "\U0001f1f2\U0001f1f9",
    "Mexico": "\U0001f1f2\U0001f1fd", "Moldova": "\U0001f1f2\U0001f1e9", "Monaco": "\U0001f1f2\U0001f1e8",
    "Mongolia": "\U0001f1f2\U0001f1f3", "Montenegro": "\U0001f1f2\U0001f1ea", "Morocco": "\U0001f1f2\U0001f1e6",
    "Mozambique": "\U0001f1f2\U0001f1ff", "Myanmar": "\U0001f1f2\U0001f1f2", "Namibia": "\U0001f1f3\U0001f1e6",
    "Nepal": "\U0001f1f3\U0001f1f5", "Netherlands": "\U0001f1f3\U0001f1f1", "New Zealand": "\U0001f1f3\U0001f1ff",
    "Nicaragua": "\U0001f1f3\U0001f1ee", "Niger": "\U0001f1f3\U0001f1ea", "Nigeria": "\U0001f1f3\U0001f1ec",
    "North Korea": "\U0001f1f0\U0001f1f5", "North Macedonia": "\U0001f1f2\U0001f1f0", "Norway": "\U0001f1f3\U0001f1f4",
    "Oman": "\U0001f1f4\U0001f1f2", "Pakistan": "\U0001f1f5\U0001f1f0", "Panama": "\U0001f1f5\U0001f1e6",
    "Paraguay": "\U0001f1f5\U0001f1fe", "Peru": "\U0001f1f5\U0001f1ea", "Philippines": "\U0001f1f5\U0001f1ed",
    "Poland": "\U0001f1f5\U0001f1f1", "Portugal": "\U0001f1f5\U0001f1f9", "Qatar": "\U0001f1f6\U0001f1e6",
    "Romania": "\U0001f1f7\U0001f1f4", "Russia": "\U0001f1f7\U0001f1fa", "Rwanda": "\U0001f1f7\U0001f1fc",
    "Saudi Arabia": "\U0001f1f8\U0001f1e6", "Senegal": "\U0001f1f8\U0001f1f3", "Serbia": "\U0001f1f7\U0001f1f8",
    "Sierra Leone": "\U0001f1f8\U0001f1f1", "Singapore": "\U0001f1f8\U0001f1ec", "Slovakia": "\U0001f1f8\U0001f1f0",
    "Slovenia": "\U0001f1f8\U0001f1ee", "Somalia": "\U0001f1f8\U0001f1f4", "South Africa": "\U0001f1ff\U0001f1e6",
    "South Korea": "\U0001f1f0\U0001f1f7", "Spain": "\U0001f1ea\U0001f1f8", "Sri Lanka": "\U0001f1f1\U0001f1f0",
    "Sudan": "\U0001f1f8\U0001f1e9", "Sweden": "\U0001f1f8\U0001f1ea", "Switzerland": "\U0001f1e8\U0001f1ed",
    "Syria": "\U0001f1f8\U0001f1fe", "Taiwan": "\U0001f1f9\U0001f1fc", "Tajikistan": "\U0001f1f9\U0001f1ef",
    "Tanzania": "\U0001f1f9\U0001f1ff", "Thailand": "\U0001f1f9\U0001f1ed", "TOGO": "\U0001f1f9\U0001f1ec",
    "Tunisia": "\U0001f1f9\U0001f1f3", "Turkey": "\U0001f1f9\U0001f1f7", "Turkmenistan": "\U0001f1f9\U0001f1f2",
    "Uganda": "\U0001f1fa\U0001f1ec", "Ukraine": "\U0001f1fa\U0001f1e6", "United Arab Emirates": "\U0001f1e6\U0001f1ea",
    "United Kingdom": "\U0001f1ec\U0001f1e7", "United States": "\U0001f1fa\U0001f1f8", "Uruguay": "\U0001f1fa\U0001f1fe",
    "Uzbekistan": "\U0001f1fa\U0001f1ff", "Venezuela": "\U0001f1fb\U0001f1ea", "Vietnam": "\U0001f1fb\U0001f1f3",
    "Yemen": "\U0001f1fe\U0001f1ea", "Zambia": "\U0001f1ff\U0001f1f2", "Zimbabwe": "\U0001f1ff\U0001f1fc",
    "Unknown Country": "\U0001f3f4\u200d\u2620\ufe0f"
}

SERVICE_KEYWORDS = {
    "Facebook": ["facebook"], "Google": ["google", "gmail"], "WhatsApp": ["whatsapp"],
    "Telegram": ["telegram"], "Instagram": ["instagram"], "Amazon": ["amazon"],
    "Netflix": ["netflix"], "LinkedIn": ["linkedin"], "Microsoft": ["microsoft", "outlook", "live.com"],
    "Apple": ["apple", "icloud"], "Twitter": ["twitter"], "Snapchat": ["snapchat"],
    "TikTok": ["tiktok"], "Discord": ["discord"], "Signal": ["signal"],
    "Viber": ["viber"], "IMO": ["imo"], "PayPal": ["paypal"],
    "Binance": ["binance"], "Uber": ["uber"], "Bolt": ["bolt"],
    "Airbnb": ["airbnb"], "Yahoo": ["yahoo"], "Steam": ["steam"],
    "Blizzard": ["blizzard"], "Foodpanda": ["foodpanda"], "Pathao": ["pathao"],
    "Messenger": ["messenger", "meta"], "Gmail": ["gmail", "google"],
    "YouTube": ["youtube", "google"], "X": ["x", "twitter"],
    "eBay": ["ebay"], "AliExpress": ["aliexpress"], "Alibaba": ["alibaba"],
    "Flipkart": ["flipkart"], "Outlook": ["outlook", "microsoft"],
    "Skype": ["skype", "microsoft"], "Spotify": ["spotify"],
    "iCloud": ["icloud", "apple"], "Stripe": ["stripe"],
    "Cash App": ["cash app", "square cash"], "Venmo": ["venmo"],
    "Zelle": ["zelle"], "Wise": ["wise", "transferwise"],
    "Coinbase": ["coinbase"], "KuCoin": ["kucoin"], "Bybit": ["bybit"],
    "OKX": ["okx"], "Huobi": ["huobi"], "Kraken": ["kraken"],
    "MetaMask": ["metamask"], "Epic Games": ["epic games", "epicgames"],
    "PlayStation": ["playstation", "psn"], "Xbox": ["xbox", "microsoft"],
    "Twitch": ["twitch"], "Reddit": ["reddit"],
    "ProtonMail": ["protonmail", "proton"], "Zoho": ["zoho"],
    "Quora": ["quora"], "StackOverflow": ["stackoverflow"],
    "Indeed": ["indeed"], "Upwork": ["upwork"], "Fiverr": ["fiverr"],
    "Glassdoor": ["glassdoor"], "Booking.com": ["booking.com", "booking"],
    "Careem": ["careem"], "Swiggy": ["swiggy"], "Zomato": ["zomato"],
    "McDonald's": ["mcdonalds", "mcdonald's"], "KFC": ["kfc"],
    "Nike": ["nike"], "Adidas": ["adidas"], "Shein": ["shein"],
    "OnlyFans": ["onlyfans"], "Tinder": ["tinder"], "Bumble": ["bumble"],
    "Grindr": ["grindr"], "Line": ["line"], "WeChat": ["wechat"],
    "VK": ["vk", "vkontakte"], "Unknown": ["unknown"]
}

SERVICE_EMOJIS = {
    "Telegram": "\U0001f4e9", "WhatsApp": "\U0001f7e2", "Facebook": "\U0001f4d8",
    "Instagram": "\U0001f4f8", "Messenger": "\U0001f4ac", "Google": "\U0001f50d",
    "Gmail": "\u2709\ufe0f", "YouTube": "\u25b6\ufe0f", "Twitter": "\U0001f426",
    "X": "\u274c", "TikTok": "\U0001f3b5", "Snapchat": "\U0001f47b",
    "Amazon": "\U0001f6d2", "eBay": "\U0001f4e6", "AliExpress": "\U0001f4e6",
    "Alibaba": "\U0001f3ed", "Flipkart": "\U0001f4e6", "Microsoft": "\U0001fa9f",
    "Outlook": "\U0001f4e7", "Skype": "\U0001f4de", "Netflix": "\U0001f3ac",
    "Spotify": "\U0001f3b6", "Apple": "\U0001f34f", "iCloud": "\u2601\ufe0f",
    "PayPal": "\U0001f4b0", "Stripe": "\U0001f4b3", "Cash App": "\U0001f4b5",
    "Venmo": "\U0001f4b8", "Zelle": "\U0001f3e6", "Wise": "\U0001f310",
    "Binance": "\U0001fa99", "Coinbase": "\U0001fa99", "KuCoin": "\U0001fa99",
    "Bybit": "\U0001f4c8", "OKX": "\U0001f7e0", "Huobi": "\U0001f525",
    "Kraken": "\U0001f419", "MetaMask": "\U0001f98a", "Discord": "\U0001f5e8\ufe0f",
    "Steam": "\U0001f3ae", "Epic Games": "\U0001f579\ufe0f", "PlayStation": "\U0001f3ae",
    "Xbox": "\U0001f3ae", "Twitch": "\U0001f4fa", "Reddit": "\U0001f47d",
    "Yahoo": "\U0001f7e3", "ProtonMail": "\U0001f510", "Zoho": "\U0001f4ec",
    "Quora": "\u2753", "StackOverflow": "\U0001f9d1\u200d\U0001f4bb",
    "LinkedIn": "\U0001f4bc", "Indeed": "\U0001f4cb", "Upwork": "\U0001f9d1\u200d\U0001f4bb",
    "Fiverr": "\U0001f4bb", "Glassdoor": "\U0001f50e", "Airbnb": "\U0001f3e0",
    "Booking.com": "\U0001f6cf\ufe0f", "Uber": "\U0001f697", "Lyft": "\U0001f695",
    "Bolt": "\U0001f696", "Careem": "\U0001f697", "Swiggy": "\U0001f354",
    "Zomato": "\U0001f37d\ufe0f", "Foodpanda": "\U0001f371",
    "McDonald's": "\U0001f35f", "KFC": "\U0001f357", "Nike": "\U0001f45f",
    "Adidas": "\U0001f45f", "Shein": "\U0001f457", "OnlyFans": "\U0001f51e",
    "Tinder": "\U0001f525", "Bumble": "\U0001f41d", "Grindr": "\U0001f608",
    "Signal": "\U0001f510", "Viber": "\U0001f4de", "Line": "\U0001f4ac",
    "WeChat": "\U0001f4ac", "VK": "\U0001f310", "Unknown": "\u2753"
}

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filepath, default):
    if not os.path.exists(filepath):
        save_json(filepath, default)
        return default
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_json(filepath, data):
    ensure_data_dir()
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_panels():
    return load_json(PANELS_FILE, {
        "cr": {
            "login_url": "https://ivas.tempnum.qzz.io/login",
            "base_url": "https://ivas.tempnum.qzz.io",
            "sms_url": "https://ivas.tempnum.qzz.io/portal/sms/received/getsms",
            "username": "tgonly712@gmail.com",
            "password": "Yuvraj@2008",
            "active": True
        }
    })

def save_panels(panels):
    save_json(PANELS_FILE, panels)

def load_groups():
    return load_json(GROUPS_FILE, {})

def save_groups(groups):
    save_json(GROUPS_FILE, groups)

def load_owners():
    return load_json(OWNERS_FILE, [INITIAL_OWNER, "8221767181", "7011937754"])

def save_owners(owners):
    save_json(OWNERS_FILE, owners)

def load_welcome():
    return load_json(WELCOME_FILE, {
        "message": "\U0001f44b Welcome! This bot forwards OTP messages in real-time.\n\nClick the button below to join the group where OTPs are posted:",
        "buttons": [
            {"text": "\U0001f3e8 Available Numbers", "url": "https://ivas.tempnum.qzz.io"},
            {"text": "\U0001f4ac Main Chat", "url": "https://t.me/+example"},
            {"text": "\U0001f511 Otp Group", "url": "https://t.me/+example"}
        ]
    })

def save_welcome(welcome):
    save_json(WELCOME_FILE, welcome)

def load_processed_ids():
    global _processed_ids_cache, _processed_ids_loaded
    if not _processed_ids_loaded:
        _processed_ids_cache = set(load_json(PROCESSED_FILE, []))
        _processed_ids_loaded = True
    return _processed_ids_cache

def save_processed_ids_bulk(new_ids):
    global _processed_ids_cache
    _processed_ids_cache.update(new_ids)
    if len(_processed_ids_cache) > 5000:
        _processed_ids_cache = set(list(_processed_ids_cache)[-3000:])
    save_json(PROCESSED_FILE, list(_processed_ids_cache))

def is_owner(user_id):
    owners = load_owners()
    return str(user_id) in owners

def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if is_owner(user_id):
        keyboard = [
            [InlineKeyboardButton("\U0001f4c1 Panel List", callback_data="panel_list")],
            [InlineKeyboardButton("\U0001f4c2 Group List", callback_data="group_list")],
            [InlineKeyboardButton("\U0001f527 Owner Panel", callback_data="owner_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Welcome \u2014 choose an action:", reply_markup=reply_markup)
    else:
        welcome = load_welcome()
        buttons = welcome.get("buttons", [])
        keyboard = []
        for btn in buttons:
            keyboard.append([InlineKeyboardButton(btn["text"], url=btn["url"])])
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(welcome.get("message", "Welcome!"), reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_owner(user_id):
        await query.edit_message_text("You are not authorized.")
        return
    data = query.data
    if data == "noop":
        return

    if data == "panel_list":
        await show_panel_list(query)
    elif data == "group_list":
        await show_group_list(query)
    elif data == "owner_panel":
        await show_owner_panel(query)
    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("\U0001f4c1 Panel List", callback_data="panel_list")],
            [InlineKeyboardButton("\U0001f4c2 Group List", callback_data="group_list")],
            [InlineKeyboardButton("\U0001f527 Owner Panel", callback_data="owner_panel")]
        ]
        await query.edit_message_text("Welcome \u2014 choose an action:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("panel_detail:"):
        panel_name = data.split(":", 1)[1]
        await show_panel_detail(query, panel_name)
    elif data.startswith("panel_activate:"):
        panel_name = data.split(":", 1)[1]
        panels = load_panels()
        if panel_name in panels:
            panels[panel_name]["active"] = True
            save_panels(panels)
        await show_panel_detail(query, panel_name)
    elif data.startswith("panel_deactivate:"):
        panel_name = data.split(":", 1)[1]
        panels = load_panels()
        if panel_name in panels:
            panels[panel_name]["active"] = False
            save_panels(panels)
        await show_panel_detail(query, panel_name)
    elif data.startswith("panel_delete:"):
        panel_name = data.split(":", 1)[1]
        panels = load_panels()
        if panel_name in panels:
            del panels[panel_name]
            save_panels(panels)
        await show_panel_list(query)

    elif data.startswith("panel_numbers:"):
        panel_name = data.split(":", 1)[1]
        await show_panel_ranges(query, panel_name, context)

    elif data.startswith("range_numbers:"):
        parts = data.split(":", 2)
        panel_name = parts[1]
        range_id = parts[2]
        await send_range_numbers_file(query, panel_name, range_id, context)

    elif data.startswith("range_delete_menu:"):
        parts = data.split(":", 2)
        panel_name = parts[1]
        range_id = parts[2]
        await show_range_delete_menu(query, panel_name, range_id, context)

    elif data.startswith("del_all_confirm:"):
        parts = data.split(":", 2)
        panel_name = parts[1]
        range_id = parts[2]
        grouped = context.user_data.get(f"numbers_{panel_name}", {})
        real_range = find_range_by_safe_name(grouped, range_id)
        count = len(grouped.get(real_range, []))
        keyboard = [
            [InlineKeyboardButton(f"\u2705 Yes, Delete All {count}", callback_data=f"del_all_yes:{panel_name}:{range_id}")],
            [InlineKeyboardButton("\u274c Cancel", callback_data=f"range_delete_menu:{panel_name}:{range_id}")]
        ]
        await query.edit_message_text(f"\u26a0\ufe0f Are you sure?\nThis will delete ALL {count} numbers from '{real_range}'.", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("del_all_yes:"):
        parts = data.split(":", 2)
        panel_name = parts[1]
        range_id = parts[2]
        await delete_all_numbers_from_range(query, panel_name, range_id, context)

    elif data.startswith("del_number:"):
        parts = data.split(":", 3)
        panel_name = parts[1]
        range_id = parts[2]
        phone_number = parts[3]
        await delete_number_from_panel(query, panel_name, range_id, phone_number, context)

    elif data.startswith("group_detail:"):
        group_id = data.split(":", 1)[1]
        await show_group_detail(query, group_id)
    elif data.startswith("group_activate:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["active"] = True
            save_groups(groups)
        await show_group_detail(query, group_id)
    elif data.startswith("group_deactivate:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["active"] = False
            save_groups(groups)
        await show_group_detail(query, group_id)
    elif data.startswith("group_delete:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            del groups[group_id]
            save_groups(groups)
        await show_group_list(query)
    elif data.startswith("group_buttons:"):
        group_id = data.split(":", 1)[1]
        await show_group_buttons(query, group_id)
    elif data.startswith("group_add_btn:"):
        group_id = data.split(":", 1)[1]
        context.user_data["awaiting"] = f"group_add_btn:{group_id}"
        await query.edit_message_text(
            f"Send button in format:\ntext | url\n\nExample:\n\U0001f4ac Join Chat | https://t.me/+example",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_buttons:{group_id}")]])
        )
    elif data.startswith("group_del_btn:"):
        parts = data.split(":", 2)
        group_id = parts[1]
        btn_idx = int(parts[2])
        groups = load_groups()
        if group_id in groups:
            btns = groups[group_id].get("buttons", [])
            if 0 <= btn_idx < len(btns):
                btns.pop(btn_idx)
                groups[group_id]["buttons"] = btns
                save_groups(groups)
        await show_group_buttons(query, group_id)
    elif data.startswith("group_change_panel:"):
        group_id = data.split(":", 1)[1]
        await show_change_panel(query, group_id)
    elif data.startswith("group_set_panel:"):
        parts = data.split(":", 2)
        group_id = parts[1]
        panel_name = parts[2]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["panel"] = panel_name
            save_groups(groups)
        await show_group_detail(query, group_id)

    elif data == "add_panel":
        context.user_data["awaiting"] = "add_panel_email"
        await query.edit_message_text(
            "\U0001f4e7 Send Your Email:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]])
        )
    elif data == "add_group":
        context.user_data["awaiting"] = "add_group_id"
        await query.edit_message_text(
            "Send Group ID:\n(e.g., -1003087662000)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]])
        )
    elif data == "add_owner":
        context.user_data["awaiting"] = "add_owner_id"
        await query.edit_message_text(
            "Send User ID:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]])
        )
    elif data == "assign_panel":
        context.user_data["awaiting"] = "assign_panel_group"
        await query.edit_message_text(
            "Send Group ID:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]])
        )
    elif data == "welcome_settings":
        await show_welcome_settings(query)
    elif data == "welcome_edit_msg":
        context.user_data["awaiting"] = "welcome_edit_msg"
        await query.edit_message_text(
            "Send new welcome message text:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="welcome_settings")]])
        )
    elif data == "welcome_add_btn":
        context.user_data["awaiting"] = "welcome_add_btn"
        await query.edit_message_text(
            "Send button in format:\ntext | url\n\nExample:\n\U0001f4ac Join Chat | https://t.me/+example",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="welcome_settings")]])
        )
    elif data.startswith("welcome_del_btn:"):
        btn_idx = int(data.split(":", 1)[1])
        welcome = load_welcome()
        btns = welcome.get("buttons", [])
        if 0 <= btn_idx < len(btns):
            btns.pop(btn_idx)
            welcome["buttons"] = btns
            save_welcome(welcome)
        await show_welcome_settings(query)

async def show_panel_list(query):
    panels = load_panels()
    keyboard = []
    for name, info in panels.items():
        status = "\U0001f7e2" if info.get("active", True) else "\U0001f534"
        email = info.get("username", "")
        keyboard.append([InlineKeyboardButton(f"{status} {name} | {email}", callback_data=f"panel_detail:{name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="back_main")])
    await query.edit_message_text("\U0001f4c1 All Panels:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_panel_detail(query, panel_name):
    panels = load_panels()
    panel = panels.get(panel_name)
    if not panel:
        await query.edit_message_text("Panel not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="panel_list")]]))
        return
    status = "\U0001f7e2 Active" if panel.get("active", True) else "\U0001f534 Inactive"
    text = (
        f"\U0001f4c1 Panel: {panel_name}\n\n"
        f"Status: {status}\n"
        f"URL: {panel.get('base_url', 'N/A')}\n"
        f"Username: {panel.get('username', 'N/A')}"
    )
    keyboard = []
    if panel.get("active", True):
        keyboard.append([InlineKeyboardButton("\U0001f534 Deactivate", callback_data=f"panel_deactivate:{panel_name}")])
    else:
        keyboard.append([InlineKeyboardButton("\U0001f7e2 Activate", callback_data=f"panel_activate:{panel_name}")])
    keyboard.append([InlineKeyboardButton("\U0001f4f1 View Numbers", callback_data=f"panel_numbers:{panel_name}")])
    keyboard.append([InlineKeyboardButton("\U0001f5d1 Delete", callback_data=f"panel_delete:{panel_name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="panel_list")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def fetch_all_numbers(panel_name):
    panels = load_panels()
    panel_config = panels.get(panel_name)
    if not panel_config:
        return None
    client, csrf = await get_panel_session(panel_name, panel_config)
    if not client or not csrf:
        return None
    base_url = panel_config.get("base_url", "")
    numbers_url = urljoin(base_url, "/portal/numbers")
    try:
        grouped = {}
        start = 0
        length = 200
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-CSRF-TOKEN': csrf,
        }
        while True:
            params = {
                'draw': 1,
                'start': start,
                'length': length,
                'columns[0][data]': 'number_id',
                'columns[0][name]': 'id',
                'columns[1][data]': 'Number',
                'columns[1][name]': 'Number',
                'columns[2][data]': 'range',
                'columns[2][name]': 'range',
                'columns[3][data]': 'A2P',
                'columns[3][name]': 'A2P',
            }
            res = await client.get(numbers_url, params=params, headers=ajax_headers)
            res.raise_for_status()
            data = res.json()
            records = data.get("data", [])
            if not records:
                break
            for rec in records:
                number_id_html = rec.get("number_id", "")
                number_id_clean = ""
                if isinstance(number_id_html, str):
                    match = re.search(r'value="(\d+)"', number_id_html)
                    if match:
                        number_id_clean = match.group(1)
                number = str(rec.get("Number", ""))
                range_name = str(rec.get("range", "Unknown")).strip()
                if number:
                    if range_name not in grouped:
                        grouped[range_name] = []
                    grouped[range_name].append({"number": number, "id": number_id_clean})
            total = data.get("recordsTotal", 0)
            start += length
            if start >= total:
                break
        print(f"\u2705 Fetched {sum(len(v) for v in grouped.values())} numbers in {len(grouped)} ranges for panel '{panel_name}'")
        return grouped
    except Exception as e:
        print(f"\u274c Error fetching numbers for panel '{panel_name}': {e}")
        traceback.print_exc()
        return None

async def delete_number_api(panel_name, number_id):
    panels = load_panels()
    panel_config = panels.get(panel_name)
    if not panel_config:
        return False
    client, csrf = await get_panel_session(panel_name, panel_config)
    if not client or not csrf:
        return False
    base_url = panel_config.get("base_url", "")
    delete_url = urljoin(base_url, "/portal/numbers/return/number")
    try:
        payload = {'NumberID': number_id, '_token': csrf}
        res = await client.post(delete_url, data=payload)
        res.raise_for_status()
        return True
    except Exception as e:
        print(f"\u274c Error deleting number ID '{number_id}': {e}")
        return False

async def show_panel_ranges(query, panel_name, context):
    await query.edit_message_text(f"\u23f3 Loading numbers for panel '{panel_name}'...")
    grouped = await fetch_all_numbers(panel_name)
    if grouped is None:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")]]
        await query.edit_message_text(f"\u274c Could not fetch numbers. Login may have failed.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if not grouped:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")]]
        await query.edit_message_text(f"\U0001f4f1 No numbers found for panel '{panel_name}'.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    context.user_data[f"numbers_{panel_name}"] = grouped
    keyboard = []
    for range_name, nums in grouped.items():
        safe_range = range_name.replace(":", "_")[:30]
        keyboard.append([
            InlineKeyboardButton(f"\U0001f4c4 {range_name} ({len(nums)})", callback_data=f"range_numbers:{panel_name}:{safe_range}"),
            InlineKeyboardButton(f"\U0001f5d1", callback_data=f"range_delete_menu:{panel_name}:{safe_range}")
        ])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")])
    total = sum(len(v) for v in grouped.values())
    await query.edit_message_text(
        f"\U0001f4f1 Panel '{panel_name}' - {total} numbers in {len(grouped)} ranges:\nClick range for .txt file, \U0001f5d1 to delete numbers.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def find_range_by_safe_name(grouped, safe_range):
    for range_name in grouped:
        if range_name.replace(":", "_")[:30] == safe_range:
            return range_name
    return safe_range

async def send_range_numbers_file(query, panel_name, range_id, context):
    grouped = context.user_data.get(f"numbers_{panel_name}")
    if not grouped:
        await query.edit_message_text(f"\u23f3 Reloading numbers...")
        grouped = await fetch_all_numbers(panel_name)
        if grouped:
            context.user_data[f"numbers_{panel_name}"] = grouped
    if not grouped:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")]]
        await query.edit_message_text(f"\u274c Could not fetch numbers.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    real_range = find_range_by_safe_name(grouped, range_id)
    numbers = grouped.get(real_range, [])
    if not numbers:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")]]
        await query.edit_message_text(f"\U0001f4f1 No numbers found in range '{real_range}'.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    number_lines = [n["number"] if isinstance(n, dict) else n for n in numbers]
    file_content = "\n".join(number_lines)
    safe_filename = re.sub(r'[^a-zA-Z0-9_]', '_', real_range)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', prefix=f'{safe_filename}_', delete=False) as f:
        f.write(file_content)
        tmp_path = f.name
    try:
        chat_id = query.message.chat_id
        with open(tmp_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=f"{safe_filename}_numbers.txt"),
                caption=f"\U0001f4f1 {real_range} - {len(numbers)} numbers\nPanel: {panel_name}"
            )
    finally:
        os.unlink(tmp_path)
    keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back to Ranges", callback_data=f"panel_numbers:{panel_name}")]]
    await query.edit_message_text(f"\u2705 Sent {len(numbers)} numbers for range '{real_range}'.", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_range_delete_menu(query, panel_name, range_id, context):
    grouped = context.user_data.get(f"numbers_{panel_name}")
    if not grouped:
        await query.edit_message_text(f"\u23f3 Reloading numbers...")
        grouped = await fetch_all_numbers(panel_name)
        if grouped:
            context.user_data[f"numbers_{panel_name}"] = grouped
    if not grouped:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")]]
        await query.edit_message_text(f"\u274c Could not fetch numbers.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    real_range = find_range_by_safe_name(grouped, range_id)
    numbers = grouped.get(real_range, [])
    if not numbers:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")]]
        await query.edit_message_text(f"\U0001f4f1 No numbers found in range '{real_range}'.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = []
    del_all_cb = f"del_all_confirm:{panel_name}:{range_id}"
    if len(del_all_cb) <= 64:
        keyboard.append([InlineKeyboardButton(f"\u26a0\ufe0f Delete All ({len(numbers)})", callback_data=del_all_cb)])
    for entry in numbers[:50]:
        if isinstance(entry, dict):
            num_display = entry["number"]
            num_id = entry.get("id", "")
        else:
            num_display = entry
            num_id = entry
        cb_data = f"del_number:{panel_name}:{range_id}:{num_id}"
        if len(cb_data) <= 64:
            keyboard.append([InlineKeyboardButton(f"\U0001f5d1 {num_display}", callback_data=cb_data)])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")])
    await query.edit_message_text(f"\U0001f5d1 Delete numbers from '{real_range}':\nClick to delete:", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_number_from_panel(query, panel_name, range_id, number_id, context):
    await query.edit_message_text(f"\u23f3 Deleting number...")
    success = await delete_number_api(panel_name, number_id)
    if success:
        grouped = context.user_data.get(f"numbers_{panel_name}", {})
        real_range = find_range_by_safe_name(grouped, range_id)
        if real_range in grouped:
            grouped[real_range] = [n for n in grouped[real_range] if not (isinstance(n, dict) and n.get("id") == number_id)]
            if not grouped[real_range]:
                del grouped[real_range]
            context.user_data[f"numbers_{panel_name}"] = grouped
        await query.edit_message_text(f"\u2705 Number deleted!")
    else:
        await query.edit_message_text(f"\u274c Failed to delete number.")
    await asyncio.sleep(1)
    await show_range_delete_menu(query, panel_name, range_id, context)

async def delete_all_numbers_from_range(query, panel_name, range_id, context):
    grouped = context.user_data.get(f"numbers_{panel_name}", {})
    real_range = find_range_by_safe_name(grouped, range_id)
    numbers = grouped.get(real_range, [])
    if not numbers:
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_numbers:{panel_name}")]]
        await query.edit_message_text(f"\u274c No numbers to delete.", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    total = len(numbers)
    await query.edit_message_text(f"\u23f3 Deleting {total} numbers from '{real_range}'...")
    success_count = 0
    fail_count = 0
    batch_size = 30
    for i in range(0, total, batch_size):
        batch = numbers[i:i+batch_size]
        tasks = []
        for entry in batch:
            num_id = entry.get("id", "") if isinstance(entry, dict) else entry
            if num_id:
                tasks.append(delete_number_api(panel_name, num_id))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if r is True:
                success_count += 1
            else:
                fail_count += 1
    if real_range in grouped:
        del grouped[real_range]
        context.user_data[f"numbers_{panel_name}"] = grouped
    keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back to Ranges", callback_data=f"panel_numbers:{panel_name}")]]
    await query.edit_message_text(
        f"\u2705 Deleted {success_count}/{total} numbers from '{real_range}'." + (f"\n\u274c {fail_count} failed." if fail_count else ""),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_group_list(query):
    groups = load_groups()
    keyboard = []
    for gid, info in groups.items():
        status = "\U0001f7e2" if info.get("active", True) else "\U0001f534"
        panel = info.get("panel", "none")
        keyboard.append([InlineKeyboardButton(f"{status} {gid} [{panel}]", callback_data=f"group_detail:{gid}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="back_main")])
    await query.edit_message_text("\U0001f4c2 All Groups:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_group_detail(query, group_id):
    groups = load_groups()
    group = groups.get(group_id)
    if not group:
        await query.edit_message_text("Group not found.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="group_list")]]))
        return
    status = "\U0001f7e2 Active" if group.get("active", True) else "\U0001f534 Inactive"
    panel = group.get("panel", "none")
    panel_display = "\U0001f4c1 All Panels" if panel == "all" else panel
    btn_count = len(group.get("buttons", []))
    text = (
        f"\U0001f4c2 Group: {group_id}\n\n"
        f"Status: {status}\n"
        f"Assigned Panel: {panel_display}\n"
        f"Buttons: {btn_count}"
    )
    keyboard = []
    if group.get("active", True):
        keyboard.append([InlineKeyboardButton("\U0001f534 Deactivate", callback_data=f"group_deactivate:{group_id}")])
    else:
        keyboard.append([InlineKeyboardButton("\U0001f7e2 Activate", callback_data=f"group_activate:{group_id}")])
    keyboard.append([InlineKeyboardButton(f"\u25cb Buttons ({btn_count})", callback_data=f"group_buttons:{group_id}")])
    keyboard.append([InlineKeyboardButton("\U0001f4c1 Change Panel", callback_data=f"group_change_panel:{group_id}")])
    keyboard.append([InlineKeyboardButton("\U0001f5d1 Delete", callback_data=f"group_delete:{group_id}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="group_list")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_group_buttons(query, group_id):
    groups = load_groups()
    group = groups.get(group_id, {})
    btns = group.get("buttons", [])
    keyboard = []
    for i, btn in enumerate(btns):
        keyboard.append([
            InlineKeyboardButton(f"{btn['text']}", callback_data=f"noop"),
            InlineKeyboardButton("\U0001f5d1", callback_data=f"group_del_btn:{group_id}:{i}")
        ])
    keyboard.append([InlineKeyboardButton("+ Add Button", callback_data=f"group_add_btn:{group_id}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_detail:{group_id}")])
    await query.edit_message_text(f"Buttons for group {group_id}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_change_panel(query, group_id):
    panels = load_panels()
    keyboard = []
    keyboard.append([InlineKeyboardButton("\U0001f4c1 All Panels", callback_data=f"group_set_panel:{group_id}:all")])
    for name in panels:
        keyboard.append([InlineKeyboardButton(f"\U0001f4c1 {name}", callback_data=f"group_set_panel:{group_id}:{name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_detail:{group_id}")])
    await query.edit_message_text(f"Select panel for group {group_id}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_owner_panel(query):
    keyboard = [
        [InlineKeyboardButton("+ Add Account", callback_data="add_panel")],
        [InlineKeyboardButton("+ Add Group", callback_data="add_group")],
        [InlineKeyboardButton("+ Add Owner", callback_data="add_owner")],
        [InlineKeyboardButton("\U0001f4c1 Assign Panel to Group", callback_data="assign_panel")],
        [InlineKeyboardButton("\U0001f44b Welcome Settings", callback_data="welcome_settings")],
        [InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="back_main")]
    ]
    await query.edit_message_text("\U0001f527 Owner Panel:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_welcome_settings(query):
    welcome = load_welcome()
    msg = welcome.get("message", "No message set")
    btns = welcome.get("buttons", [])
    text = f"\U0001f44b Welcome Settings\n\nCurrent message:\n{msg}\n\nButtons ({len(btns)}):"
    for i, btn in enumerate(btns):
        text += f"\n{i+1}. {btn['text']} -> {btn['url']}"
    keyboard = [
        [InlineKeyboardButton("Edit Message", callback_data="welcome_edit_msg")],
        [InlineKeyboardButton("+ Add Button", callback_data="welcome_add_btn")]
    ]
    for i, btn in enumerate(btns):
        keyboard.append([InlineKeyboardButton(f"\U0001f5d1 Remove: {btn['text']}", callback_data=f"welcome_del_btn:{i}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_owner(user_id):
        return
    awaiting = context.user_data.get("awaiting", "")
    text = update.message.text.strip()

    if awaiting == "add_panel_email":
        context.user_data["new_panel_email"] = text
        context.user_data["awaiting"] = "add_panel_password"
        await update.message.reply_text("\U0001f511 Send Password:")
    elif awaiting == "add_panel_password":
        username = context.user_data.get("new_panel_email", "")
        password = text
        base_url = "https://ivas.tempnum.qzz.io"
        login_url = f"{base_url}/login"
        sms_url = f"{base_url}/portal/sms/received/getsms"
        await update.message.reply_text("\u23f3 Checking login...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as test_client:
                login_page = await test_client.get(login_url)
                soup = BeautifulSoup(login_page.text, 'lxml')
                token_input = soup.find('input', {'name': '_token'})
                login_data = {'email': username, 'password': password}
                if token_input:
                    login_data['_token'] = token_input['value']
                login_res = await test_client.post(login_url, data=login_data)
                if "login" in str(login_res.url):
                    context.user_data["awaiting"] = ""
                    keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]
                    error_soup = BeautifulSoup(login_res.text, 'lxml')
                    error_div = error_soup.find('div', class_='alert-danger') or error_soup.find('span', class_='invalid-feedback')
                    if error_div and 'password' in error_div.get_text().lower():
                        await update.message.reply_text("\U0001f6ab Password Wrong!", reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await update.message.reply_text("\U0001f6ab Gmail Wrong!", reply_markup=InlineKeyboardMarkup(keyboard))
                    return
        except Exception as e:
            context.user_data["awaiting"] = ""
            keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]
            await update.message.reply_text(f"\U0001f6ab Connection Error!", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        panel_name = username.split("@")[0].replace(".", "").replace("+", "")[:10]
        panels = load_panels()
        counter = 1
        orig_name = panel_name
        while panel_name in panels:
            panel_name = f"{orig_name}{counter}"
            counter += 1
        panels[panel_name] = {
            "login_url": login_url,
            "base_url": base_url,
            "sms_url": sms_url,
            "username": username,
            "password": password,
            "active": True
        }
        save_panels(panels)
        context.user_data["awaiting"] = ""
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]
        await update.message.reply_text(f"\u2705 Login Successful!\n\U0001f4e7 {username}\n\U0001f4c1 Panel: {panel_name}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif awaiting == "add_group_id":
        group_id = text
        groups = load_groups()
        if group_id not in groups:
            groups[group_id] = {"panel": "none", "active": True, "buttons": []}
            save_groups(groups)
            await update.message.reply_text(f"\u2705 Group {group_id} added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        else:
            await update.message.reply_text(f"\u26a0\ufe0f Group {group_id} already exists.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        context.user_data["awaiting"] = ""

    elif awaiting == "add_owner_id":
        owner_id = text
        owners = load_owners()
        if owner_id not in owners:
            owners.append(owner_id)
            save_owners(owners)
            await update.message.reply_text(f"\u2705 Owner {owner_id} added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        else:
            await update.message.reply_text(f"\u26a0\ufe0f Owner {owner_id} already exists.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        context.user_data["awaiting"] = ""

    elif awaiting == "assign_panel_group":
        context.user_data["assign_group_id"] = text
        context.user_data["awaiting"] = "assign_panel_name"
        panels = load_panels()
        panel_names = ", ".join(panels.keys()) if panels else "No panels available"
        await update.message.reply_text(f"Send Panel name to assign:\nAvailable: {panel_names}")
    elif awaiting == "assign_panel_name":
        group_id = context.user_data.get("assign_group_id", "")
        panel_name = text
        groups = load_groups()
        panels = load_panels()
        if group_id not in groups:
            groups[group_id] = {"panel": panel_name, "active": True, "buttons": []}
        else:
            groups[group_id]["panel"] = panel_name
        save_groups(groups)
        context.user_data["awaiting"] = ""
        if panel_name in panels:
            await update.message.reply_text(f"\u2705 Panel '{panel_name}' assigned to group {group_id}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        else:
            await update.message.reply_text(f"\u26a0\ufe0f Panel '{panel_name}' not found but assigned anyway. Create the panel first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))

    elif awaiting == "welcome_edit_msg":
        welcome = load_welcome()
        welcome["message"] = text
        save_welcome(welcome)
        context.user_data["awaiting"] = ""
        await update.message.reply_text("\u2705 Welcome message updated!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="welcome_settings")]]))

    elif awaiting == "welcome_add_btn":
        if "|" in text:
            parts = text.split("|", 1)
            btn_text = parts[0].strip()
            btn_url = parts[1].strip()
            welcome = load_welcome()
            welcome.setdefault("buttons", []).append({"text": btn_text, "url": btn_url})
            save_welcome(welcome)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(f"\u2705 Button '{btn_text}' added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="welcome_settings")]]))
        else:
            await update.message.reply_text("Invalid format. Use: text | url")

    elif awaiting and awaiting.startswith("group_add_btn:"):
        group_id = awaiting.split(":", 1)[1]
        if "|" in text:
            parts = text.split("|", 1)
            btn_text = parts[0].strip()
            btn_url = parts[1].strip()
            groups = load_groups()
            if group_id in groups:
                existing_btns = groups[group_id].get("buttons", [])
                if len(existing_btns) >= 4:
                    context.user_data["awaiting"] = ""
                    await update.message.reply_text("\u26a0\ufe0f Maximum 4 buttons allowed!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_buttons:{group_id}")]]))
                    return
                groups[group_id].setdefault("buttons", []).append({"text": btn_text, "url": btn_url})
                save_groups(groups)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(f"\u2705 Button added to group {group_id}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_buttons:{group_id}")]]))
        else:
            await update.message.reply_text("Invalid format. Use: text | url")

_panel_sessions = {}

async def get_panel_session(panel_name, panel_config):
    global _panel_sessions, _login_failures
    now = time.time()

    last_fail = _login_failures.get(panel_name, 0)
    if (now - last_fail) < LOGIN_FAIL_COOLDOWN:
        return None, None

    session_info = _panel_sessions.get(panel_name, {})
    client = session_info.get("client")
    csrf = session_info.get("csrf")
    last_login = session_info.get("last_login", 0)

    if client and csrf and (now - last_login) < LOGIN_REFRESH_INTERVAL:
        return client, csrf

    if client:
        try:
            await client.aclose()
        except Exception:
            pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    new_client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers, limits=limits, http2=False)
    login_url = panel_config.get("login_url", "")
    try:
        login_page_res = await new_client.get(login_url)
        soup = BeautifulSoup(login_page_res.text, 'lxml')
        token_input = soup.find('input', {'name': '_token'})
        login_data = {'email': panel_config["username"], 'password': panel_config["password"]}
        if token_input:
            login_data['_token'] = token_input['value']
        login_res = await new_client.post(login_url, data=login_data)
        if "login" in str(login_res.url):
            print(f"\u274c Login failed for panel '{panel_name}'. Skipping for {LOGIN_FAIL_COOLDOWN}s.")
            _login_failures[panel_name] = now
            await new_client.aclose()
            return None, None
        print(f"\u2705 Login successful for panel '{panel_name}'!")
        _login_failures.pop(panel_name, None)
        dashboard_soup = BeautifulSoup(login_res.text, 'lxml')
        csrf_meta = dashboard_soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta:
            print(f"\u274c CSRF not found for panel '{panel_name}'.")
            await new_client.aclose()
            return None, None
        new_csrf = csrf_meta.get('content')
        _panel_sessions[panel_name] = {"client": new_client, "csrf": new_csrf, "last_login": now}
        return new_client, new_csrf
    except Exception as e:
        print(f"\u274c Login error for panel '{panel_name}': {e}")
        _login_failures[panel_name] = now
        try:
            await new_client.aclose()
        except Exception:
            pass
        return None, None

async def fetch_sms_from_panel(client, csrf_token, panel_config):
    all_messages = []
    base_url = panel_config.get("base_url", "")
    sms_url_endpoint = panel_config.get("sms_url", "")
    try:
        t0 = time.time()
        today = datetime.utcnow()
        from_date_str = today.strftime('%m/%d/%Y')
        to_date_str = today.strftime('%m/%d/%Y')
        first_payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        summary_response = await client.post(sms_url_endpoint, data=first_payload)
        summary_response.raise_for_status()
        summary_soup = BeautifulSoup(summary_response.text, 'lxml')
        group_divs = summary_soup.find_all('div', {'class': 'pointer'})
        if not group_divs:
            return []
        group_ids = []
        for div in group_divs:
            match = re.search(r"getDetials\('(.+?)'\)", div.get('onclick', ''))
            if match:
                group_ids.append(match.group(1))
        numbers_url = urljoin(base_url, "/portal/sms/received/getsms/number")
        sms_detail_url = urljoin(base_url, "/portal/sms/received/getsms/number/sms")

        sem = asyncio.Semaphore(20)

        async def fetch_group(group_id):
            msgs = []
            try:
                numbers_payload = {'start': from_date_str, 'end': to_date_str, 'range': group_id, '_token': csrf_token}
                numbers_response = await client.post(numbers_url, data=numbers_payload)
                numbers_soup = BeautifulSoup(numbers_response.text, 'lxml')
                number_divs = numbers_soup.select("div[onclick*='getDetialsNumber']")
                if not number_divs:
                    return msgs

                async def fetch_number_sms(phone_number):
                    async with sem:
                        num_msgs = []
                        try:
                            sms_payload = {'start': from_date_str, 'end': to_date_str, 'Number': phone_number, 'Range': group_id, '_token': csrf_token}
                            sms_response = await client.post(sms_detail_url, data=sms_payload, timeout=15.0)
                            sms_soup = BeautifulSoup(sms_response.text, 'lxml')
                            final_sms_cards = sms_soup.find_all('div', class_='card-body')
                            for card in final_sms_cards:
                                sms_text_p = card.find('p', class_='mb-0')
                                if sms_text_p:
                                    sms_text = sms_text_p.get_text(separator='\n').strip()
                                    date_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                                    country_name_match = re.match(r'([a-zA-Z\s]+)', group_id)
                                    country_name = country_name_match.group(1).strip() if country_name_match else group_id.strip()
                                    service = "Unknown"
                                    lower_sms = sms_text.lower()
                                    for svc, kws in SERVICE_KEYWORDS.items():
                                        if any(kw in lower_sms for kw in kws):
                                            service = svc
                                            break
                                    code_match = re.search(r'(\d{3}-\d{3})', sms_text) or re.search(r'\b(\d{4,8})\b', sms_text)
                                    code = code_match.group(1) if code_match else "N/A"
                                    unique_id = f"{phone_number}-{sms_text}"
                                    flag = COUNTRY_FLAGS.get(country_name, None) or COUNTRY_FLAGS.get(country_name.title(), None) or COUNTRY_FLAGS.get(country_name.upper(), None) or COUNTRY_FLAGS.get(country_name.capitalize(), "\U0001f3f4\u200d\u2620\ufe0f")
                                    num_msgs.append({
                                        "id": unique_id, "time": date_str, "number": phone_number,
                                        "country": country_name, "flag": flag, "service": service,
                                        "code": code, "full_sms": sms_text, "range_id": group_id
                                    })
                        except Exception as e:
                            print(f"Error fetching SMS for {phone_number}: {e}")
                        return num_msgs

                phone_numbers = [div.text.strip() for div in number_divs]
                tasks = [fetch_number_sms(pn) for pn in phone_numbers]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, list):
                        msgs.extend(result)
            except Exception as e:
                print(f"Error fetching group {group_id}: {e}")
            return msgs

        tasks = [fetch_group(gid) for gid in group_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_messages.extend(result)
        elapsed = time.time() - t0
        if all_messages:
            print(f"\u23f1 Fetched {len(all_messages)} SMS from {len(group_ids)} groups in {elapsed:.1f}s")
        return all_messages
    except httpx.RequestError as e:
        print(f"\u274c Network issue: {e}")
        return []
    except Exception as e:
        print(f"\u274c Error fetching SMS: {e}")
        traceback.print_exc()
        return []

async def send_telegram_message(context, chat_id, message_data, buttons=None):
    try:
        time_str = message_data.get("time", "N/A")
        number_str = message_data.get("number", "N/A")
        country_name = message_data.get("country", "N/A")
        flag_emoji = message_data.get("flag", "\U0001f3f4\u200d\u2620\ufe0f")
        if flag_emoji == "\U0001f3f4\u200d\u2620\ufe0f":
            flag_emoji = COUNTRY_FLAGS.get(country_name, None) or COUNTRY_FLAGS.get(country_name.title(), None) or COUNTRY_FLAGS.get(country_name.upper(), None) or COUNTRY_FLAGS.get(country_name.capitalize(), "\U0001f3f4\u200d\u2620\ufe0f")
        service_name = message_data.get("service", "N/A")
        code_str = message_data.get("code", "N/A")
        full_sms_text = message_data.get("full_sms", "N/A")
        service_emoji = SERVICE_EMOJIS.get(service_name, "\u2753")
        display_country = country_name.title()
        masked_number = number_str
        if len(number_str) > 5:
            masked_number = f"+{number_str[:2]}*{number_str[-5:]}"
        sms_lines = full_sms_text.split('\n')
        nested_sms = '\n'.join([f">>{escape_markdown(line)}" for line in sms_lines])
        full_message = (
            f"\U0001f525 {escape_markdown(display_country)} {escape_markdown(service_name)} OTP Recieved\\!\n"
            f"\u2728\n"
            f">\U0001f30d Country: {escape_markdown(display_country)} {flag_emoji}\n"
            f">\U0001f4df Service: {service_emoji} {escape_markdown(service_name)}\n"
            f">\U0001f4f1 Number: {escape_markdown(masked_number)}\n"
            f">\U0001f511OTP: {escape_markdown(code_str)}\n"
            f">\U0001f608 *Full Message*\n"
            f"{nested_sms}"
        )
        reply_markup = None
        if buttons and len(buttons) > 0:
            btn_list = buttons[:4]
            keyboard = []
            for i in range(0, len(btn_list), 2):
                row = [InlineKeyboardButton(btn_list[i].get("text", "Button"), url=btn_list[i].get("url", "https://t.me"))]
                if i + 1 < len(btn_list):
                    row.append(InlineKeyboardButton(btn_list[i+1].get("text", "Button"), url=btn_list[i+1].get("url", "https://t.me")))
                keyboard.append(row)
            reply_markup = InlineKeyboardMarkup(keyboard)
        await asyncio.wait_for(
            context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode='MarkdownV2', reply_markup=reply_markup),
            timeout=10
        )
    except asyncio.TimeoutError:
        print(f"\u274c Timeout sending to {chat_id}")
    except Exception as e:
        print(f"\u274c Error sending to {chat_id}: {e}")

_job_running = False

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    global _job_running
    if _job_running:
        return
    _job_running = True
    try:
        panels = load_panels()
        groups = load_groups()
        active_panels = {name: cfg for name, cfg in panels.items() if cfg.get("active", True)}
        if not active_panels:
            return
        active_groups = {gid: info for gid, info in groups.items() if info.get("active", True)}
        if not active_groups:
            return
        panel_to_groups = {}
        all_panel_groups = []
        for gid, info in active_groups.items():
            p = info.get("panel", "none")
            if p == "all":
                all_panel_groups.append(gid)
            elif p in active_panels:
                panel_to_groups.setdefault(p, []).append(gid)
        if all_panel_groups:
            for panel_name in active_panels:
                panel_to_groups.setdefault(panel_name, [])
                for gid in all_panel_groups:
                    if gid not in panel_to_groups[panel_name]:
                        panel_to_groups[panel_name].append(gid)
        if not panel_to_groups:
            return

        processed_ids = load_processed_ids()
        new_ids = []
        send_tasks = []

        async def process_panel(panel_name, group_ids):
            global _range_otp_counts
            panel_cfg = active_panels[panel_name]
            client, csrf = await get_panel_session(panel_name, panel_cfg)
            if not client or not csrf:
                return [], []
            try:
                messages = await fetch_sms_from_panel(client, csrf, panel_cfg)
                p_new_ids = []
                p_send_tasks = []
                if messages:
                    range_counts = {}
                    for msg in messages:
                        rng = msg.get("range_id", msg.get("country", "Unknown"))
                        range_counts[rng] = range_counts.get(rng, 0) + 1
                    _range_otp_counts[panel_name] = range_counts
                    for msg in reversed(messages):
                        if msg["id"] not in processed_ids:
                            p_new_ids.append(msg["id"])
                            for gid in group_ids:
                                group_info = groups.get(gid, {})
                                group_buttons = group_info.get("buttons", [])
                                p_send_tasks.append(send_telegram_message(context, gid, msg, buttons=group_buttons))
                return p_new_ids, p_send_tasks
            except Exception as e:
                print(f"\u274c Error checking panel '{panel_name}': {e}")
                if panel_name in _panel_sessions:
                    del _panel_sessions[panel_name]
                return [], []

        panel_tasks = [process_panel(pn, gids) for pn, gids in panel_to_groups.items()]
        results = await asyncio.gather(*panel_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, tuple):
                nids, stasks = result
                new_ids.extend(nids)
                send_tasks.extend(stasks)

        if send_tasks:
            batch_size = 15
            for i in range(0, len(send_tasks), batch_size):
                batch = send_tasks[i:i+batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
        if new_ids:
            save_processed_ids_bulk(new_ids)
            print(f"\u2705 Sent {len(new_ids)} new OTP(s).")
    finally:
        _job_running = False

def main():
    print("\U0001f680 OTP Bot is starting...")
    if not YOUR_BOT_TOKEN:
        print("\U0001f534 ERROR: TELEGRAM_BOT_TOKEN not set!")
        return
    ensure_data_dir()
    application = Application.builder().token(YOUR_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    job_queue = application.job_queue
    job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=2)
    print(f"\U0001f680 Polling every {POLLING_INTERVAL_SECONDS}s. Bot online!")
    application.run_polling()

if __name__ == "__main__":
    main()
