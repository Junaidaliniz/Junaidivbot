# -*- coding: utf-8 -*-
import asyncio
import re
import httpx
from bs4 import BeautifulSoup
import time
import json
import os
import traceback
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CopyTextButton
from telegram.error import TelegramError

YOUR_BOT_TOKEN = "BOT_TOKEN"
INITIAL_OWNER = "OWNER_ID"

DATA_DIR = "data"
PANELS_FILE = os.path.join(DATA_DIR, "panels.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
OWNERS_FILE = os.path.join(DATA_DIR, "owners.json")
WELCOME_FILE = os.path.join(DATA_DIR, "welcome.json")
PROCESSED_FILE = os.path.join(DATA_DIR, "processed_ids.json")
LAST_FETCH_FILE = os.path.join(DATA_DIR, "last_fetch.json")
OTP_TEMPLATES_FILE = os.path.join(DATA_DIR, "otp_templates.json")

POLLING_INTERVAL_SECONDS = 1
LOGIN_REFRESH_INTERVAL = 600

_processed_ids_cache = set()
_processed_ids_loaded = False

# ==================== ULTIMATE COUNTRY FLAGS ====================
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
    "Oman": "\U0001f1f4\U0001f1f2", "Pakistan": "\U0001f1f5\U0001f1f0", "Palestine": "\U0001f1f5\U0001f1f8",
    "Panama": "\U0001f1f5\U0001f1e6", "Paraguay": "\U0001f1f5\U0001f1fe", "Peru": "\U0001f1f5\U0001f1ea",
    "Philippines": "\U0001f1f5\U0001f1ed", "Poland": "\U0001f1f5\U0001f1f1", "Portugal": "\U0001f1f5\U0001f1f9",
    "Puerto Rico": "\U0001f1f5\U0001f1f7", "Qatar": "\U0001f1f6\U0001f1e6", "Romania": "\U0001f1f7\U0001f1f4",
    "Russia": "\U0001f1f7\U0001f1fa", "Rwanda": "\U0001f1f7\U0001f1fc", "Saudi Arabia": "\U0001f1f8\U0001f1e6",
    "Senegal": "\U0001f1f8\U0001f1f3", "Serbia": "\U0001f1f7\U0001f1f8", "Sierra Leone": "\U0001f1f8\U0001f1f1",
    "Singapore": "\U0001f1f8\U0001f1ec", "Slovakia": "\U0001f1f8\U0001f1f0", "Slovenia": "\U0001f1f8\U0001f1ee",
    "Somalia": "\U0001f1f8\U0001f1f4", "South Africa": "\U0001f1ff\U0001f1e6", "South Korea": "\U0001f1f0\U0001f1f7",
    "Spain": "\U0001f1ea\U0001f1f8", "Sri Lanka": "\U0001f1f1\U0001f1f0", "Sudan": "\U0001f1f8\U0001f1e9",
    "Sweden": "\U0001f1f8\U0001f1ea", "Switzerland": "\U0001f1e8\U0001f1ed", "Syria": "\U0001f1f8\U0001f1fe",
    "Taiwan": "\U0001f1f9\U0001f1fc", "Tajikistan": "\U0001f1f9\U0001f1ef", "Tanzania": "\U0001f1f9\U0001f1ff",
    "Thailand": "\U0001f1f9\U0001f1ed", "TOGO": "\U0001f1f9\U0001f1ec", "Tunisia": "\U0001f1f9\U0001f1f3",
    "Turkey": "\U0001f1f9\U0001f1f7", "Turkmenistan": "\U0001f1f9\U0001f1f2", "Uganda": "\U0001f1fa\U0001f1ec",
    "Ukraine": "\U0001f1fa\U0001f1e6", "United Arab Emirates": "\U0001f1e6\U0001f1ea",
    "United Kingdom": "\U0001f1ec\U0001f1e7", "United States": "\U0001f1fa\U0001f1f8", "Uruguay": "\U0001f1fa\U0001f1fe",
    "Uzbekistan": "\U0001f1fa\U0001f1ff", "Venezuela": "\U0001f1fb\U0001f1ea", "Vietnam": "\U0001f1fb\U0001f1f3",
    "Yemen": "\U0001f1fe\U0001f1ea", "Zambia": "\U0001f1ff\U0001f1f2", "Zimbabwe": "\U0001f1ff\U0001f1fc",
    "Unknown Country": "\U0001f3f4\u200d\u2620\ufe0f"
}

# ==================== SERVICE KEYWORDS & ABBREVIATIONS ====================
SERVICE_KEYWORDS = {
    "Facebook": ["facebook"], "Google": ["google", "gmail"], "WhatsApp": ["whatsapp"],
    "WhatsApp Business": ["whatsapp business", "business whatsapp"], "Telegram": ["telegram"],
    "Telegram X": ["telegram x"], "Instagram": ["instagram"], "Amazon": ["amazon"],
    "Netflix": ["netflix"], "LinkedIn": ["linkedin"], "Microsoft": ["microsoft", "outlook", "live.com"],
    "Apple": ["apple", "icloud"], "Twitter": ["twitter"], "Snapchat": ["snapchat"],
    "TikTok": ["tiktok"], "Discord": ["discord"], "Signal": ["signal"],
    "Viber": ["viber"], "IMO": ["imo"], "PayPal": ["paypal"],
    "Binance": ["binance"], "Binance US": ["binance us"], "Uber": ["uber"], "Bolt": ["bolt"],
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

SERVICE_ABBR = {
    "WhatsApp": "WS", "WhatsApp Business": "WB", "Facebook": "FB", "Google": "GG", "Gmail": "GM",
    "Telegram": "TG", "Telegram X": "TX", "Instagram": "IG", "Twitter": "TW", "Snapchat": "SC",
    "TikTok": "TK", "Microsoft": "MS", "Apple": "AP", "Amazon": "AZ", "Netflix": "NF",
    "LinkedIn": "LI", "PayPal": "PP", "Binance": "BN", "Binance US": "BU", "Uber": "UB",
    "Bolt": "BL", "Foodpanda": "FP", "Pathao": "PT", "Messenger": "MG", "YouTube": "YT",
    "X": "XX", "eBay": "EB", "AliExpress": "AE", "Alibaba": "AB", "Flipkart": "FK",
    "Outlook": "OL", "Skype": "SK", "Spotify": "SP", "iCloud": "IC", "Stripe": "ST",
    "Cash App": "CA", "Venmo": "VM", "Zelle": "ZL", "Wise": "WI", "Coinbase": "CB",
    "KuCoin": "KC", "Bybit": "BB", "OKX": "OK", "Huobi": "HB", "Kraken": "KR",
    "MetaMask": "MM", "Epic Games": "EG", "PlayStation": "PS", "Xbox": "XB", "Twitch": "TW",
    "Reddit": "RD", "ProtonMail": "PM", "Zoho": "ZH", "Quora": "QR", "StackOverflow": "SO",
    "Indeed": "ID", "Upwork": "UW", "Fiverr": "FR", "Glassdoor": "GD", "Booking.com": "BK",
    "Careem": "CM", "Swiggy": "SG", "Zomato": "ZM", "McDonald's": "MD", "KFC": "KF",
    "Nike": "NK", "Adidas": "AD", "Shein": "SH", "OnlyFans": "OF", "Tinder": "TR",
    "Bumble": "BM", "Grindr": "GR", "Signal": "SG", "Viber": "VB", "Line": "LN",
    "WeChat": "WC", "VK": "VK", "Unknown": "UN"
}

# ==================== ULTIMATE SERVICE TRANSLATIONS ====================
SERVICE_TRANSLATIONS = {
    "WhatsApp": {
        "Urdu": "واٹس ایپ", "Arabic": "واتساب", "Hindi": "व्हाट्सएप",
        "Bengali": "হোয়াটসঅ্যাপ", "Persian": "واتساپ", "Turkish": "WhatsApp",
        "Russian": "WhatsApp", "Spanish": "WhatsApp", "French": "WhatsApp",
        "German": "WhatsApp", "Indonesian": "WhatsApp"
    },
    "Facebook": {
        "Urdu": "فیس بک", "Arabic": "فيسبوك", "Hindi": "फ़ेसबुक",
        "Bengali": "ফেসবুক", "Persian": "فیسبوک", "Turkish": "Facebook",
        "Russian": "Facebook", "Spanish": "Facebook", "French": "Facebook",
        "German": "Facebook", "Indonesian": "Facebook"
    },
    "Google": {
        "Urdu": "گوگل", "Arabic": "جوجل", "Hindi": "गूगल",
        "Bengali": "গুগল", "Persian": "گوگل", "Turkish": "Google",
        "Russian": "Google", "Spanish": "Google", "French": "Google",
        "German": "Google", "Indonesian": "Google"
    },
    "Telegram": {
        "Urdu": "ٹیلیگرام", "Arabic": "تيليغرام", "Hindi": "टेलीग्राम",
        "Bengali": "টেলিগ্রাম", "Persian": "تلگرام", "Turkish": "Telegram",
        "Russian": "Telegram", "Spanish": "Telegram", "French": "Telegram",
        "German": "Telegram", "Indonesian": "Telegram"
    },
    "Instagram": {
        "Urdu": "انسٹاگرام", "Arabic": "انستغرام", "Hindi": "इंस्टाग्राम",
        "Bengali": "ইনস্টাগ্রাম", "Persian": "اینستاگرام", "Turkish": "Instagram",
        "Russian": "Instagram", "Spanish": "Instagram", "French": "Instagram",
        "German": "Instagram", "Indonesian": "Instagram"
    },
    "Twitter": {
        "Urdu": "ٹوئٹر", "Arabic": "تويتر", "Hindi": "ट्विटर",
        "Bengali": "টুইটার", "Persian": "توییتر", "Turkish": "Twitter",
        "Russian": "Twitter", "Spanish": "Twitter", "French": "Twitter",
        "German": "Twitter", "Indonesian": "Twitter"
    },
    "Gmail": {
        "Urdu": "جی میل", "Arabic": "جيميل", "Hindi": "जीमेल",
        "Bengali": "জিমেইল", "Persian": "جیمیل", "Turkish": "Gmail",
        "Russian": "Gmail", "Spanish": "Gmail", "French": "Gmail",
        "German": "Gmail", "Indonesian": "Gmail"
    },
    "Snapchat": {
        "Urdu": "اسنیپ چیٹ", "Arabic": "سناب شات", "Hindi": "स्नैपचैट",
        "Bengali": "স্ন্যাপচ্যাট", "Persian": "اسنپ چت", "Turkish": "Snapchat",
        "Russian": "Snapchat", "Spanish": "Snapchat", "French": "Snapchat",
        "German": "Snapchat", "Indonesian": "Snapchat"
    },
    "TikTok": {
        "Urdu": "ٹک ٹاک", "Arabic": "تيك توك", "Hindi": "टिकटॉक",
        "Bengali": "টিকটক", "Persian": "تیک تاک", "Turkish": "TikTok",
        "Russian": "TikTok", "Spanish": "TikTok", "French": "TikTok",
        "German": "TikTok", "Indonesian": "TikTok"
    },
    "Microsoft": {
        "Urdu": "مائیکروسافٹ", "Arabic": "مايكروسوفت", "Hindi": "माइक्रोसॉफ्ट",
        "Bengali": "মাইক্রোসফট", "Persian": "مایکروسافت", "Turkish": "Microsoft",
        "Russian": "Microsoft", "Spanish": "Microsoft", "French": "Microsoft",
        "German": "Microsoft", "Indonesian": "Microsoft"
    },
    "Apple": {
        "Urdu": "ایپل", "Arabic": "آبل", "Hindi": "एप्पल",
        "Bengali": "অ্যাপল", "Persian": "اپل", "Turkish": "Apple",
        "Russian": "Apple", "Spanish": "Apple", "French": "Apple",
        "German": "Apple", "Indonesian": "Apple"
    },
    "Amazon": {
        "Urdu": "ایمیزون", "Arabic": "أمازون", "Hindi": "अमेज़न",
        "Bengali": "অ্যামাজন", "Persian": "آمازون", "Turkish": "Amazon",
        "Russian": "Amazon", "Spanish": "Amazon", "French": "Amazon",
        "German": "Amazon", "Indonesian": "Amazon"
    },
    "Netflix": {
        "Urdu": "نیٹ فلکس", "Arabic": "نتفليكس", "Hindi": "नेटफ्लिक्स",
        "Bengali": "নেটফ্লিক্স", "Persian": "نتفلیکس", "Turkish": "Netflix",
        "Russian": "Netflix", "Spanish": "Netflix", "French": "Netflix",
        "German": "Netflix", "Indonesian": "Netflix"
    },
    "PayPal": {
        "Urdu": "پے پال", "Arabic": "باي بال", "Hindi": "पेपाल",
        "Bengali": "পেপ্যাল", "Persian": "پی‌پال", "Turkish": "PayPal",
        "Russian": "PayPal", "Spanish": "PayPal", "French": "PayPal",
        "German": "PayPal", "Indonesian": "PayPal"
    },
    "Binance": {
        "Urdu": "بائننس", "Arabic": "بينانس", "Hindi": "बिनेंस",
        "Bengali": "বাইন্যান্স", "Persian": "بایننس", "Turkish": "Binance",
        "Russian": "Binance", "Spanish": "Binance", "French": "Binance",
        "German": "Binance", "Indonesian": "Binance"
    }
}

def translate_service(service_name, language):
    if language == "English":
        return service_name
    trans_map = SERVICE_TRANSLATIONS.get(service_name, {})
    return trans_map.get(language, service_name)

# ==================== ULTIMATE LANGUAGE DETECTION ====================
def detect_language(text):
    text = str(text).strip()
    text_lower = text.lower()
    
    # Arabic script (Arabic, Urdu, Persian, etc.)
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
        if re.search(r'(\u06a9\u0648\u0688|\u0648\u0627\u0679\u0633|\u0627\u06cc\u067e|\u0646\u0645\u0628\u0631|\u062a\u0635\u062f\u06cc\u0642)', text):
            return "Urdu"
        elif re.search(r'(\u0631\u0645\u0632|\u0643\u0648\u062f|\u0648\u0627\u062a\u0633|\u062a\u0637\u0628\u064a\u0642)', text):
            return "Arabic"
        elif re.search(r'(\u06a9\u062f|\u0648\u0627\u062a\u0633\u0627\u067e|\u0628\u0631\u0646\u0627\u0645\u0647)', text):
            return "Persian"
        else:
            return "Arabic"
    # Chinese
    elif re.search(r'[\u4e00-\u9fff]', text):
        return "Chinese"
    # Japanese
    elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
        return "Japanese"
    # Korean
    elif re.search(r'[\uac00-\ud7af\u1100-\u11ff]', text):
        return "Korean"
    # Hindi/Devanagari
    elif re.search(r'[\u0900-\u097F]', text):
        return "Hindi"
    # Bengali
    elif re.search(r'[\u0980-\u09FF]', text):
        return "Bengali"
    # Thai
    elif re.search(r'[\u0E00-\u0E7F]', text):
        return "Thai"
    # Hebrew
    elif re.search(r'[\u0590-\u05FF]', text):
        return "Hebrew"
    # Russian/Cyrillic
    elif re.search(r'[\u0400-\u04FF]', text):
        return "Russian"
    # Greek
    elif re.search(r'[\u0370-\u03FF]', text):
        return "Greek"
    # Vietnamese
    elif re.search(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', text, re.IGNORECASE):
        return "Vietnamese"
    
    # Keyword-based detection for European languages
    if re.search(r'\b(your|verification|account|security|confirm|authenticate|login|sign|register|password|otp|whatsapp|telegram|facebook|google|instagram)\b', text_lower):
        return "English"
    if re.search(r'\b(código|tu|verificación|cuenta|contraseña|autenticar|iniciar)\b', text_lower):
        return "Spanish"
    if re.search(r'\b(votre|vérification|compte|mot de passe|authentifier|connexion)\b', text_lower):
        return "French"
    if re.search(r'\b(código|seu|verificação|conta|senha|autenticar)\b', text_lower):
        return "Portuguese"
    if re.search(r'\b(ihr|verifizierung|konto|passwort|bestätigen|anmelden)\b', text_lower):
        return "German"
    if re.search(r'\b(codice|tuo|verifica|account|password|autenticare)\b', text_lower):
        return "Italian"
    if re.search(r'\b(kod|sizin|doğrulama|hesap|şifre|oturum)\b', text_lower):
        return "Turkish"
    if re.search(r'\b(kode|anda|verifikasi|akun|kata sandi|masuk)\b', text_lower):
        return "Indonesian"
    if re.search(r'\b(kod|twój|weryfikacja|konto|hasło|zaloguj)\b', text_lower):
        return "Polish"
    if re.search(r'\b(jouw|verificatie|account|wachtwoord|inloggen)\b', text_lower):
        return "Dutch"
    if re.search(r'\b(din|verifiering|konto|lösenord|logga)\b', text_lower):
        return "Swedish"
    
    return "English"

def flag_to_country_code(flag_emoji):
    try:
        cp1 = ord(flag_emoji[0])
        cp2 = ord(flag_emoji[1])
        letter1 = chr(ord('A') + (cp1 - 0x1F1E6))
        letter2 = chr(ord('A') + (cp2 - 0x1F1E6))
        return letter1 + letter2
    except:
        return "UN"

# ==================== MASK FORMATTING FUNCTION ====================
def apply_mask(number, mask_format):
    """Apply custom mask to phone number."""
    if not mask_format:
        # Default mask: +XXXX***XXXX
        if number.startswith('+'):
            return f"{number[:5]}***{number[-4:]}"
        else:
            return f"+{number[:4]}***{number[-4:]}"
    # Custom mask handling
    try:
        def repl_first(match):
            n = int(match.group(1))
            return number[:n] if len(number) >= n else number
        def repl_last(match):
            n = int(match.group(1))
            return number[-n:] if len(number) >= n else number
        mask = re.sub(r'{first(\d+)}', repl_first, mask_format)
        mask = re.sub(r'{last(\d+)}', repl_last, mask)
        mask = mask.replace('{all}', number)
        return mask
    except:
        return number

# ==================== HTML ESCAPING ====================
def escape_html(text):
    text = str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ==================== OTP TEMPLATES FUNCTIONS ====================
def load_otp_templates():
    default_templates = {
        "default": {
            "name": "Default Template",
            "template": "<b>#{service_abbr} #{country_abbr}</b>{flag} {masked_number} <b>#{lang_name}</b>",
            "active": True,
            "is_default": True
        }
    }
    templates = load_json(OTP_TEMPLATES_FILE, default_templates)
    if "default" not in templates:
        templates["default"] = default_templates["default"]
    # Ensure only one active template
    active_found = False
    for tid, tdata in templates.items():
        if tdata.get("active", False):
            if active_found:
                tdata["active"] = False
            else:
                active_found = True
    if not active_found:
        templates["default"]["active"] = True
    return templates

def save_otp_templates(templates):
    save_json(OTP_TEMPLATES_FILE, templates)

def get_active_template():
    templates = load_otp_templates()
    for template_id, template_data in templates.items():
        if template_data.get("active", False):
            return template_id, template_data
    return "default", templates["default"]

def format_otp_message(template, data):
    escaped_data = {k: escape_html(v) for k, v in data.items()}
    try:
        return template.format(**escaped_data)
    except KeyError as e:
        print(f"Template formatting error: Missing key {e}")
        return f"#{data.get('service_abbr','UN')} #{data.get('country_abbr','UN')}{data.get('flag','')} {data.get('masked_number','')} #{data.get('lang_name','EN')}"

# ==================== DATA FUNCTIONS ====================
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(filepath, default):
    if not os.path.exists(filepath):
        save_json(filepath, default)
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_json(filepath, data):
    ensure_data_dir()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_panels():
    return load_json(PANELS_FILE, {
        "": {
            "login_url": "https://ivas.tempnum.qzz.io/login",
            "base_url": "https://ivas.tempnum.qzz.io",
            "sms_url": "https://ivas.tempnum.qzz.io/portal/sms/received/getsms",
            "username": "",
            "password": "",
            "active": True
        }
    })

def save_panels(panels):
    save_json(PANELS_FILE, panels)

def load_groups():
    groups = load_json(GROUPS_FILE, {})
    for gid, info in groups.items():
        if "copy_button" not in info:
            info["copy_button"] = True
        if "otp_template" not in info:
            info["otp_template"] = None
        if "mask_format" not in info:
            info["mask_format"] = None
    return groups

def save_groups(groups):
    save_json(GROUPS_FILE, groups)

def load_owners():
    return load_json(OWNERS_FILE, [INITIAL_OWNER])

def save_owners(owners):
    save_json(OWNERS_FILE, owners)

def load_welcome():
    return load_json(WELCOME_FILE, {
        "message": "POWRED-BY DARK MODS 🚀\n\nClick the button below to join the group where OTPs are posted:",
        "buttons": [
            {"text": "📢 CHANNELS", "url": "https://t.me/DARK0MODS"},
            {"text": "💬 MAIN CHAT", "url": "https://t.me/DARK1MODS"},
            {"text": "☎ NUMBERS", "url": "https://t.me/NUMBER_MOD"}
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
    if len(_processed_ids_cache) > 10000:
        _processed_ids_cache = set(list(_processed_ids_cache)[-8000:])
    save_json(PROCESSED_FILE, list(_processed_ids_cache))

def load_last_fetch():
    return load_json(LAST_FETCH_FILE, {})

def save_last_fetch(data):
    save_json(LAST_FETCH_FILE, data)

def is_owner(user_id):
    owners = load_owners()
    return str(user_id) in owners

def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

# ==================== SEND MESSAGE WITH PER‑GROUP TEMPLATE & MASK ====================
async def send_telegram_message(context, chat_id, message_data, buttons=None):
    try:
        number_str = message_data.get("number", "N/A")
        country_name = message_data.get("country", "N/A")
        flag_emoji = message_data.get("flag", "\U0001f3f4\u200d\u2620\ufe0f")
        if flag_emoji == "\U0001f3f4\u200d\u2620\ufe0f":
            flag_emoji = COUNTRY_FLAGS.get(country_name, None) or COUNTRY_FLAGS.get(country_name.title(), None) or COUNTRY_FLAGS.get(country_name.upper(), None) or COUNTRY_FLAGS.get(country_name.capitalize(), "\U0001f3f4\u200d\u2620\ufe0f")
        
        service_name = message_data.get("service", "N/A")
        code_str = message_data.get("code", "N/A")
        full_sms = message_data.get("full_sms", "")
        time_str = message_data.get("time", "")
        date_str = message_data.get("date", "")

        lang_name = detect_language(full_sms)
        service_name_local = translate_service(service_name, lang_name)

        service_abbr = SERVICE_ABBR.get(service_name, service_name[:2].upper() if service_name != "N/A" else "UN")
        country_abbr = flag_to_country_code(flag_emoji)
        
        groups = load_groups()
        group_info = groups.get(str(chat_id), {})
        mask_format = group_info.get("mask_format")
        masked_number = apply_mask(number_str, mask_format)

        template_data = {
            "service_name": service_name,
            "service_name_local": service_name_local,
            "service_abbr": service_abbr,
            "country_name": country_name,
            "country_abbr": country_abbr,
            "flag": flag_emoji,
            "masked_number": masked_number,
            "number": number_str,
            "code": code_str,
            "full_sms": full_sms,
            "lang_name": lang_name,
            "time": time_str,
            "Date": date_str
        }

        custom_template = group_info.get("otp_template")
        if custom_template:
            msg_text = format_otp_message(custom_template, template_data)
        else:
            _, global_template = get_active_template()
            msg_text = format_otp_message(global_template['template'], template_data)

        keyboard_rows = []
        if group_info.get("copy_button", True):
            copy_button = InlineKeyboardButton(
                text=code_str,
                copy_text=CopyTextButton(text=code_str)
            )
            keyboard_rows.append([copy_button])
        
        if buttons and len(buttons) > 0:
            btn_list = buttons[:4]
            for i in range(0, len(btn_list), 2):
                row = [InlineKeyboardButton(btn_list[i].get("text", "Button"), url=btn_list[i].get("url", "https://t.me"))]
                if i + 1 < len(btn_list):
                    row.append(InlineKeyboardButton(btn_list[i+1].get("text", "Button"), url=btn_list[i+1].get("url", "https://t.me")))
                keyboard_rows.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard_rows) if keyboard_rows else None
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode='HTML', reply_markup=reply_markup)
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode=None, reply_markup=reply_markup)
    except Exception as e:
        print(f"\u274c Error sending to {chat_id}: {e}")
        traceback.print_exc()

# ==================== START COMMAND ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if is_owner(user_id):
        keyboard = [
            [InlineKeyboardButton("\U0001f4c1 Panel List", callback_data="panel_list")],
            [InlineKeyboardButton("\U0001f4c2 Group List", callback_data="group_list")],
            [InlineKeyboardButton("\U0001f527 Owner Panel", callback_data="owner_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Welcome — choose an action:", reply_markup=reply_markup)
    else:
        welcome = load_welcome()
        buttons = welcome.get("buttons", [])
        keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"])] for btn in buttons]
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(welcome.get("message", "Welcome!"), reply_markup=reply_markup)

# ==================== BUTTON CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_owner(user_id):
        await query.edit_message_text("You are not authorized.")
        return
    data = query.data

    if data.startswith("copy_"):
        code = data[5:]
        await query.answer(f"OTP: {code}", show_alert=True)
        return
    
    if data == "noop":
        return

    # ===== Per‑Group OTP Template handlers =====
    if data.startswith("group_otp_template:"):
        group_id = data.split(":", 1)[1]
        await show_group_otp_settings(query, group_id)
        return
    elif data.startswith("group_otp_template_edit:"):
        group_id = data.split(":", 1)[1]
        context.user_data["awaiting"] = f"group_otp_template_edit:{group_id}"
        await query.edit_message_text(
            "Send the new template text for this group.\n\n"
            "**Available variables:**\n"
            "• <code>{service_name}</code> • <code>{service_abbr}</code>\n"
            "• <code>{country_name}</code> • <code>{country_abbr}</code>\n"
            "• <code>{masked_number}</code> • <code>{number}</code>\n"
            "• <code>{flag}</code> • <code>{Date}</code> • <code>{time}</code> • <code>{lang_name}</code>\n"
            "• <code>{code}</code> • <code>{full_sms}</code> \n\n"
            "**You can use HTML tags for formatting:**\n"
            "<pre>&lt;b&gt;bold&lt;/b&gt;\n"
            "&lt;i&gt;italic&lt;/i&gt;\n"
            "&lt;u&gt;underline&lt;/u&gt;\n"
            "&lt;s&gt;strikethrough&lt;/s&gt;\n"
            "&lt;code&gt;mono&lt;/code&gt;\n"
            "&lt;blockquote&gt;quote&lt;/blockquote&gt;\n"
            "&lt;tg-spoiler&gt;spoiler&lt;/tg-spoiler&gt;\n"
            "&lt;a href='https://t.me'&gt;link&lt;/a&gt;</pre>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data=f"group_otp_settings:{group_id}")]])
        )
        return
    elif data.startswith("group_otp_template_clear:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["otp_template"] = None
            save_groups(groups)
            await query.answer("Custom template cleared. Group will use global template.")
        await show_group_otp_settings(query, group_id)
        return

    # ===== Per‑Group Mask Format handlers =====
    if data.startswith("group_mask:"):
        group_id = data.split(":", 1)[1]
        await show_group_otp_settings(query, group_id)
        return
    elif data.startswith("group_mask_edit:"):
        group_id = data.split(":", 1)[1]
        context.user_data["awaiting"] = f"group_mask_edit:{group_id}"
        await query.edit_message_text(
            "Send the mask format for phone numbers.\n\n"
            "Use placeholders:\n"
            "• `{first4}` – first 4 digits\n"
            "• `{last4}` – last 4 digits\n"
            "• `{all}` – full number\n"
            "Example: `+{first4}***{last4}`\n"
            "Send `default` to use the bot's default masking.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data=f"group_otp_settings:{group_id}")]])
        )
        return
    elif data.startswith("group_mask_clear:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["mask_format"] = None
            save_groups(groups)
            await query.answer("Mask format cleared. Using default masking.")
        await show_group_otp_settings(query, group_id)
        return

    # ===== Existing handlers (Panel, Group, Owner) =====
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
        await query.edit_message_text("Welcome — choose an action:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            "Send button in format:\ntext | url\n\nExample:\n\U0001f4ac Join Chat | https://t.me/+example",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_otp_settings:{group_id}")]])
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
    elif data.startswith("group_toggle_copy:"):
        group_id = data.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            current = groups[group_id].get("copy_button", True)
            groups[group_id]["copy_button"] = not current
            save_groups(groups)
            await query.answer(f"Copy button is now {'ON' if not current else 'OFF'}")
        await show_group_otp_settings(query, group_id)

    elif data.startswith("group_otp_settings:"):
        group_id = data.split(":", 1)[1]
        await show_group_otp_settings(query, group_id)

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

# ==================== UI FUNCTIONS ====================
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
    text = f"\U0001f4c1 Panel: {panel_name}\n\nStatus: {status}\nURL: {panel.get('base_url', 'N/A')}\nUsername: {panel.get('username', 'N/A')}"
    keyboard = []
    if panel.get("active", True):
        keyboard.append([InlineKeyboardButton("\U0001f534 Deactivate", callback_data=f"panel_deactivate:{panel_name}")])
    else:
        keyboard.append([InlineKeyboardButton("\U0001f7e2 Activate", callback_data=f"panel_activate:{panel_name}")])
    keyboard.append([InlineKeyboardButton("\U0001f5d1 Delete", callback_data=f"panel_delete:{panel_name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="panel_list")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
    copy_status = "✅" if group.get("copy_button", True) else "❌"
    template_status = "Custom" if group.get("otp_template") else "Global"
    mask_status = "Custom" if group.get("mask_format") else "Default"
    text = (
        f"\U0001f4c2 Group: {group_id}\n\n"
        f"Status: {status}\n"
        f"Assigned Panel: {panel_display}\n"
        f"OTP Settings: Template {template_status}, Copy {copy_status}, Mask {mask_status}, Buttons {btn_count}\n"
    )
    keyboard = []
    if group.get("active", True):
        keyboard.append([InlineKeyboardButton("\U0001f534 Deactivate", callback_data=f"group_deactivate:{group_id}")])
    else:
        keyboard.append([InlineKeyboardButton("\U0001f7e2 Activate", callback_data=f"group_activate:{group_id}")])
    keyboard.append([InlineKeyboardButton("📝 OTP Settings", callback_data=f"group_otp_settings:{group_id}")])
    keyboard.append([InlineKeyboardButton("\U0001f4c1 Change Panel", callback_data=f"group_change_panel:{group_id}")])
    keyboard.append([InlineKeyboardButton("\U0001f5d1 Delete", callback_data=f"group_delete:{group_id}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="group_list")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_group_otp_settings(query, group_id):
    groups = load_groups()
    group = groups.get(group_id, {})
    btn_count = len(group.get("buttons", []))
    copy_status = "✅" if group.get("copy_button", True) else "❌"
    template_status = "Custom" if group.get("otp_template") else "Global"
    mask_status = "Custom" if group.get("mask_format") else "Default"
    custom_template = group.get("otp_template")
    if custom_template:
        template_preview = custom_template[:50] + "..." if len(custom_template) > 50 else custom_template
    else:
        _, global_tmpl = get_active_template()
        template_preview = global_tmpl['template'][:50] + "..." if len(global_tmpl['template']) > 50 else global_tmpl['template']
    mask_format = group.get("mask_format") or "Default"
    text = (
        f"*📝 OTP Settings for Group* `{group_id}`\n\n"
        f"• *URL Buttons*: {btn_count}\n"        
        f"• *Copy Button*: {copy_status}\n"
        f"• *Mask Format*: {mask_status}\n(`{mask_format}`)\n"
        f"• *Template*: {template_status}\n"
        f"  `{template_preview}`\n"      
        f"Choose an option:"
    )
    keyboard = [
        [InlineKeyboardButton(f"({copy_status}) Copy Button", callback_data=f"group_toggle_copy:{group_id}")],
        [InlineKeyboardButton("🔗 Manage Buttons", callback_data=f"group_buttons:{group_id}")],  
        [InlineKeyboardButton("🔢 Set Mask Format", callback_data=f"group_mask_edit:{group_id}")],        
        [InlineKeyboardButton("✏️ OTP Edit Template", callback_data=f"group_otp_template_edit:{group_id}")],       
        [InlineKeyboardButton("🔙 Back to Group", callback_data=f"group_detail:{group_id}")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_group_buttons(query, group_id):
    groups = load_groups()
    group = groups.get(group_id, {})
    btns = group.get("buttons", [])
    keyboard = []
    for i, btn in enumerate(btns):
        keyboard.append([
            InlineKeyboardButton(f"{btn['text']}", callback_data="noop"),
            InlineKeyboardButton("\U0001f5d1", callback_data=f"group_del_btn:{group_id}:{i}")
        ])
    keyboard.append([InlineKeyboardButton("+ Add Button", callback_data=f"group_add_btn:{group_id}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_otp_settings:{group_id}")])
    await query.edit_message_text(f"Buttons for group {group_id}", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_change_panel(query, group_id):
    panels = load_panels()
    keyboard = []
    keyboard.append([InlineKeyboardButton("\U0001f4c1 All Panels", callback_data=f"group_set_panel:{group_id}:all")])
    for name in panels:
        keyboard.append([InlineKeyboardButton(f"\U0001f4c1 {name}", callback_data=f"group_set_panel:{group_id}:{name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_detail:{group_id}")])
    await query.edit_message_text(f"Select panel for group {group_id}:", reply_markup=InlineKeyboardMarkup(keyboard))

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

# ==================== TEXT INPUT HANDLER ====================
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not is_owner(user_id):
        return
    awaiting = context.user_data.get("awaiting", "")
    text = update.message.text.strip()

    # Per‑Group OTP Template edit
    if awaiting.startswith("group_otp_template_edit:"):
        group_id = awaiting.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            groups[group_id]["otp_template"] = text
            save_groups(groups)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(
                f"✅ Custom template saved for group {group_id}!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data=f"group_otp_settings:{group_id}")]])
            )
        else:
            await update.message.reply_text("Group not found.")
        return

    # Per‑Group Mask Format edit
    if awaiting.startswith("group_mask_edit:"):
        group_id = awaiting.split(":", 1)[1]
        groups = load_groups()
        if group_id in groups:
            if text.lower() == "default":
                groups[group_id]["mask_format"] = None
                msg = "Default mask restored."
            else:
                groups[group_id]["mask_format"] = text
                msg = f"Mask format set to: {text}"
            save_groups(groups)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(
                f"✅ {msg}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Settings", callback_data=f"group_otp_settings:{group_id}")]])
            )
        else:
            await update.message.reply_text("Group not found.")
        return

    # Existing handlers (add panel, group, owner, etc.)
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
                soup = BeautifulSoup(login_page.text, 'html.parser')
                token_input = soup.find('input', {'name': '_token'})
                login_data = {'email': username, 'password': password}
                if token_input:
                    login_data['_token'] = token_input['value']
                login_res = await test_client.post(login_url, data=login_data)

                # ----- Enhanced login failure detection -----
                soup = BeautifulSoup(login_res.text, 'html.parser')
                error_div = soup.find('div', class_='alert-danger') or soup.find('span', class_='invalid-feedback')
                if error_div:
                    error_text = error_div.get_text().lower()
                    if 'password' in error_text:
                        await update.message.reply_text("❌ Password Wrong!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
                    else:
                        await update.message.reply_text("❌ Email Wrong!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
                    context.user_data["awaiting"] = ""
                    return

                # Check if still on login page (redirected back)
                if 'login' in str(login_res.url).lower():
                    await update.message.reply_text("❌ Login failed. Check credentials.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
                    context.user_data["awaiting"] = ""
                    return

                # Check for dashboard elements
                if 'dashboard' not in login_res.text.lower() and 'logout' not in login_res.text.lower():
                    await update.message.reply_text("❌ Login failed (unknown reason).", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
                    context.user_data["awaiting"] = ""
                    return

        except Exception as e:
            context.user_data["awaiting"] = ""
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]
            await update.message.reply_text(f"❌ Connection Error!", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # If we get here, login was successful
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
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]
        await update.message.reply_text(f"✅ Login Successful!\n📧 {username}\n📁 Panel: {panel_name}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif awaiting == "add_group_id":
        group_id = text
        groups = load_groups()
        if group_id not in groups:
            groups[group_id] = {"panel": "none", "active": True, "buttons": [], "copy_button": True, "otp_template": None, "mask_format": None}
            save_groups(groups)
            await update.message.reply_text(f"✅ Group {group_id} added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
        else:
            await update.message.reply_text(f"⚠️ Group {group_id} already exists.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
        context.user_data["awaiting"] = ""

    elif awaiting == "add_owner_id":
        owner_id = text.strip()
        try:
            # Verify by sending a test message
            await context.bot.send_message(
                chat_id=owner_id,
                text="✅ You have been added as an owner of the OTP bot."
            )
            owners = load_owners()
            if owner_id not in owners:
                owners.append(owner_id)
                save_owners(owners)
                await update.message.reply_text(
                    f"✅ Owner {owner_id} added successfully!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]
                    ])
                )
            else:
                await update.message.reply_text(
                    f"⚠️ Owner {owner_id} already exists.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]
                    ])
                )
        except TelegramError as e:
            await update.message.reply_text(
                f"❌ Invalid user ID or user hasn't started the bot.\nError: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]
                ])
            )
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
            groups[group_id] = {"panel": panel_name, "active": True, "buttons": [], "copy_button": True, "otp_template": None, "mask_format": None}
        else:
            groups[group_id]["panel"] = panel_name
        save_groups(groups)
        context.user_data["awaiting"] = ""
        if panel_name in panels:
            await update.message.reply_text(f"✅ Panel '{panel_name}' assigned to group {group_id}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))
        else:
            await update.message.reply_text(f"⚠️ Panel '{panel_name}' not found but assigned anyway. Create the panel first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="owner_panel")]]))

    elif awaiting == "welcome_edit_msg":
        welcome = load_welcome()
        welcome["message"] = text
        save_welcome(welcome)
        context.user_data["awaiting"] = ""
        await update.message.reply_text("✅ Welcome message updated!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="welcome_settings")]]))

    elif awaiting == "welcome_add_btn":
        if "|" in text:
            parts = text.split("|", 1)
            btn_text = parts[0].strip()
            btn_url = parts[1].strip()
            welcome = load_welcome()
            welcome.setdefault("buttons", []).append({"text": btn_text, "url": btn_url})
            save_welcome(welcome)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(f"✅ Button '{btn_text}' added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="welcome_settings")]]))
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
                    await update.message.reply_text("⚠️ Maximum 4 buttons allowed!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"group_otp_settings:{group_id}")]]))
                    return
                groups[group_id].setdefault("buttons", []).append({"text": btn_text, "url": btn_url})
                save_groups(groups)
            context.user_data["awaiting"] = ""
            await update.message.reply_text(f"✅ Button added to group {group_id}!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"group_buttons:{group_id}")]]))
        else:
            await update.message.reply_text("Invalid format. Use: text | url")

# ==================== SMS FETCHING FUNCTIONS ====================
_panel_sessions = {}

async def get_panel_session(panel_name, panel_config):
    global _panel_sessions
    now = time.time()
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
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    new_client = httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers, limits=limits, http2=False)
    login_url = panel_config.get("login_url", "")
    try:
        login_page_res = await new_client.get(login_url)
        soup = BeautifulSoup(login_page_res.text, 'html.parser')
        token_input = soup.find('input', {'name': '_token'})
        login_data = {'email': panel_config["username"], 'password': panel_config["password"]}
        if token_input:
            login_data['_token'] = token_input['value']
        login_res = await new_client.post(login_url, data=login_data)

        # Enhanced login failure detection for background job
        if 'login' in str(login_res.url).lower():
            print(f"❌ Login failed for panel '{panel_name}' (redirected to login).")
            await new_client.aclose()
            return None, None

        soup = BeautifulSoup(login_res.text, 'html.parser')
        error_div = soup.find('div', class_='alert-danger') or soup.find('span', class_='invalid-feedback')
        if error_div:
            print(f"❌ Login failed for panel '{panel_name}': {error_div.get_text().strip()}")
            await new_client.aclose()
            return None, None

        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        if not csrf_meta:
            print(f"❌ CSRF token not found after login for panel '{panel_name}'.")
            await new_client.aclose()
            return None, None

        # Optional: check for logout link as additional success indicator
        if 'logout' not in login_res.text.lower():
            print(f"❌ Login may have failed for panel '{panel_name}' (no logout link).")
            await new_client.aclose()
            return None, None

        new_csrf = csrf_meta.get('content')
        _panel_sessions[panel_name] = {"client": new_client, "csrf": new_csrf, "last_login": now}
        return new_client, new_csrf
    except Exception as e:
        print(f"❌ Login error for panel '{panel_name}': {e}")
        try:
            await new_client.aclose()
        except Exception:
            pass
        return None, None

async def fetch_sms_from_panel(client, csrf_token, panel_config, last_fetch_time=None):
    all_messages = []
    base_url = panel_config.get("base_url", "")
    sms_url_endpoint = panel_config.get("sms_url", "")
    try:
        today = datetime.now(timezone.utc)
        if last_fetch_time:
            start_date = last_fetch_time - timedelta(minutes=5)
        else:
            start_date = today - timedelta(days=1)
        from_date_str = start_date.strftime('%m/%d/%Y')
        to_date_str = today.strftime('%m/%d/%Y')
        first_payload = {'from': from_date_str, 'to': to_date_str, '_token': csrf_token}
        summary_response = await client.post(sms_url_endpoint, data=first_payload)
        summary_response.raise_for_status()
        summary_soup = BeautifulSoup(summary_response.text, 'html.parser')
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

        async def fetch_group(group_id):
            msgs = []
            try:
                numbers_payload = {'start': from_date_str, 'end': to_date_str, 'range': group_id, '_token': csrf_token}
                numbers_response = await client.post(numbers_url, data=numbers_payload)
                numbers_soup = BeautifulSoup(numbers_response.text, 'html.parser')
                number_divs = numbers_soup.select("div[onclick*='getDetialsNumber']")
                if not number_divs:
                    return msgs

                async def fetch_number_sms(phone_number):
                    num_msgs = []
                    try:
                        sms_payload = {'start': from_date_str, 'end': to_date_str, 'Number': phone_number, 'Range': group_id, '_token': csrf_token}
                        sms_response = await client.post(sms_detail_url, data=sms_payload)
                        sms_soup = BeautifulSoup(sms_response.text, 'html.parser')
                        final_sms_cards = sms_soup.find_all('div', class_='card-body')
                        for card in final_sms_cards:
                            sms_text_p = card.find('p', class_='mb-0')
                            if sms_text_p:
                                sms_text = sms_text_p.get_text(separator='\n').strip()
                                time_elem = card.find('small', class_='text-muted')
                                if time_elem:
                                    time_str = time_elem.get_text().strip()
                                else:
                                    time_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
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
                                date_part = time_str
                                time_part = ""
                                if ' ' in time_str:
                                    parts = time_str.split(' ', 1)
                                    date_part = parts[0]
                                    time_part = parts[1]
                                num_msgs.append({
                                    "id": unique_id,
                                    "time": time_part,
                                    "date": date_part,
                                    "number": phone_number,
                                    "country": country_name,
                                    "flag": flag,
                                    "service": service,
                                    "code": code,
                                    "full_sms": sms_text
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

        all_messages.sort(key=lambda x: x.get('time', ''))
        return all_messages
    except httpx.RequestError as e:
        print(f"❌ Network issue: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching SMS: {e}")
        traceback.print_exc()
        return []

_job_running = False

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    global _job_running
    if _job_running:
        return
    _job_running = True
    try:
        panels = load_panels()
        groups = load_groups()
        last_fetch = load_last_fetch()
        processed_ids = load_processed_ids()

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

        new_ids = []
        send_tasks = []
        successful_panels = []

        async def process_panel(panel_name, group_ids):
            panel_cfg = active_panels[panel_name]
            client, csrf = await get_panel_session(panel_name, panel_cfg)
            if not client or not csrf:
                return panel_name, False, [], []
            try:
                last_fetch_time = None
                if panel_name in last_fetch:
                    try:
                        last_fetch_time = datetime.fromisoformat(last_fetch[panel_name])
                    except:
                        pass
                messages = await fetch_sms_from_panel(client, csrf, panel_cfg, last_fetch_time)
                p_new_ids = []
                p_send_tasks = []
                if messages:
                    for msg in messages:
                        if msg["id"] not in processed_ids:
                            p_new_ids.append(msg["id"])
                            for gid in group_ids:
                                group_info = groups.get(gid, {})
                                group_buttons = group_info.get("buttons", [])
                                p_send_tasks.append(send_telegram_message(context, gid, msg, buttons=group_buttons))
                return panel_name, True, p_new_ids, p_send_tasks
            except Exception as e:
                print(f"❌ Error checking panel '{panel_name}': {e}")
                if panel_name in _panel_sessions:
                    del _panel_sessions[panel_name]
                return panel_name, False, [], []

        panel_tasks = [process_panel(pn, gids) for pn, gids in panel_to_groups.items()]
        results = await asyncio.gather(*panel_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, tuple) and len(result) == 4:
                pn, success, nids, stasks = result
                if success:
                    successful_panels.append(pn)
                new_ids.extend(nids)
                send_tasks.extend(stasks)

        if send_tasks:
            await asyncio.gather(*send_tasks, return_exceptions=True)
        if new_ids:
            save_processed_ids_bulk(new_ids)
            print(f"✅ Sent {len(new_ids)} new OTP(s).")

        now_iso = datetime.now(timezone.utc).isoformat()
        for pn in successful_panels:
            last_fetch[pn] = now_iso
        save_last_fetch(last_fetch)

    finally:
        _job_running = False

# ==================== MAIN ====================
def main():
    print("🚀 OTP Bot is starting...")
    if not YOUR_BOT_TOKEN or YOUR_BOT_TOKEN == "BOT_TOKEN":
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not set properly!")
        return
    ensure_data_dir()
    application = Application.builder().token(YOUR_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    job_queue = application.job_queue
    job_queue.run_repeating(check_sms_job, interval=POLLING_INTERVAL_SECONDS, first=2)
    print(f"🚀 Polling every {POLLING_INTERVAL_SECONDS}s. Bot online!")
    application.run_polling()

if __name__ == "__main__":
    main()