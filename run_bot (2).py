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
import psycopg2
from psycopg2 import pool as pg_pool

YOUR_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8225744822:AAEeQEF2V1DVOnTXTmROuvG0cMp0I0kc75A")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_cXbWwm5l2ZtM@ep-broad-frost-aigt0qsl-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require")

POLLING_INTERVAL_SECONDS = 2
LOGIN_REFRESH_INTERVAL = 900
LOGIN_FAIL_COOLDOWN = 120
_login_failures = {}
_range_otp_counts = {}
_processed_ids_cache = set()
_first_run_done = False
_panel_sessions = {}
_group_failures = {}
GROUP_FAIL_COOLDOWN = 30

_db_pool = None
def init_db_pool():
    global _db_pool
    if not _db_pool:
        _db_pool = pg_pool.SimpleConnectionPool(2, 20, DATABASE_URL)

_cache = {}
_cache_ttl = {}
CACHE_TTL_SECONDS = 5

def cache_get(key):
    if key in _cache and time.time() - _cache_ttl.get(key, 0) < CACHE_TTL_SECONDS:
        return _cache[key]
    return None

def cache_set(key, value):
    _cache[key] = value
    _cache_ttl[key] = time.time()

def cache_invalidate(key):
    _cache.pop(key, None)
    _cache_ttl.pop(key, None)

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
    "Messenger": ["messenger", "meta"], "Gmail": ["gmail", "google"],
    "YouTube": ["youtube", "google"], "X": ["x", "twitter"],
    "Spotify": ["spotify"], "Unknown": ["unknown"]
}

SERVICE_EMOJIS = {
    "Telegram": "\U0001f4e9", "WhatsApp": "\U0001f7e2", "Facebook": "\U0001f4d8",
    "Instagram": "\U0001f4f8", "Messenger": "\U0001f4ac", "Google": "\U0001f50d",
    "Gmail": "\u2709\ufe0f", "YouTube": "\u25b6\ufe0f", "Twitter": "\U0001f426",
    "X": "\u274c", "TikTok": "\U0001f3b5", "Snapchat": "\U0001f47b",
    "Amazon": "\U0001f6d2", "Microsoft": "\U0001fa9f", "Netflix": "\U0001f3ac",
    "Spotify": "\U0001f3b6", "Apple": "\U0001f34f", "PayPal": "\U0001f4b0",
    "Binance": "\U0001fa99", "Discord": "\U0001f5e8\ufe0f", "Steam": "\U0001f3ae",
    "LinkedIn": "\U0001f4bc", "Signal": "\U0001f510", "Viber": "\U0001f4de",
    "Yahoo": "\U0001f7e3", "Uber": "\U0001f697", "Bolt": "\U0001f696",
    "Airbnb": "\U0001f3e0", "Unknown": "\u2753"
}


def get_db():
    global _db_pool
    if _db_pool:
        return _db_pool.getconn()
    return psycopg2.connect(DATABASE_URL)


def put_db(conn):
    global _db_pool
    if _db_pool:
        try:
            _db_pool.putconn(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
    else:
        conn.close()


def load_panels():
    cached = cache_get("panels")
    if cached is not None:
        return cached
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, login_url, base_url, sms_url, username, password, active FROM panels")
        rows = cur.fetchall()
        panels = {}
        for row in rows:
            panels[row[0]] = {
                "login_url": row[1],
                "base_url": row[2],
                "sms_url": row[3],
                "username": row[4],
                "password": row[5],
                "active": row[6]
            }
        cache_set("panels", panels)
        return panels
    finally:
        put_db(conn)


def load_groups():
    cached = cache_get("groups")
    if cached is not None:
        return cached
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT group_id, panel, active, buttons FROM groups")
        rows = cur.fetchall()
        groups = {}
        for row in rows:
            groups[row[0]] = {
                "panel": row[1],
                "active": row[2],
                "buttons": row[3] if row[3] else []
            }
        cache_set("groups", groups)
        return groups
    finally:
        put_db(conn)


def load_owners():
    cached = cache_get("owners")
    if cached is not None:
        return cached
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM owners")
        rows = cur.fetchall()
        result = [row[0] for row in rows]
        cache_set("owners", result)
        return result
    finally:
        put_db(conn)


def load_welcome():
    cached = cache_get("welcome")
    if cached is not None:
        return cached
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT message, buttons FROM welcome_settings LIMIT 1")
        row = cur.fetchone()
        if row:
            result = {"message": row[0], "buttons": row[1] if row[1] else []}
        else:
            result = {
                "message": "Welcome! This bot forwards OTP messages in real-time.",
                "buttons": []
            }
        cache_set("welcome", result)
        return result
    finally:
        put_db(conn)


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
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE panels SET active = TRUE WHERE name = %s", (panel_name,))
            conn.commit()
            cache_invalidate("panels")
        finally:
            put_db(conn)
        await show_panel_detail(query, panel_name)
    elif data.startswith("panel_deactivate:"):
        panel_name = data.split(":", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE panels SET active = FALSE WHERE name = %s", (panel_name,))
            conn.commit()
            cache_invalidate("panels")
        finally:
            put_db(conn)
        await show_panel_detail(query, panel_name)
    elif data.startswith("panel_delete:"):
        panel_name = data.split(":", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM panels WHERE name = %s", (panel_name,))
            conn.commit()
            cache_invalidate("panels")
        finally:
            put_db(conn)
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
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE groups SET active = TRUE WHERE group_id = %s", (group_id,))
            conn.commit()
            cache_invalidate("groups")
        finally:
            put_db(conn)
        await show_group_detail(query, group_id)
    elif data.startswith("group_deactivate:"):
        group_id = data.split(":", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE groups SET active = FALSE WHERE group_id = %s", (group_id,))
            conn.commit()
            cache_invalidate("groups")
        finally:
            put_db(conn)
        await show_group_detail(query, group_id)
    elif data.startswith("group_delete:"):
        group_id = data.split(":", 1)[1]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM groups WHERE group_id = %s", (group_id,))
            conn.commit()
            cache_invalidate("groups")
        finally:
            put_db(conn)
        await show_group_list(query)

    elif data.startswith("group_change_panel:"):
        group_id = data.split(":", 1)[1]
        await show_group_panel_select(query, group_id)

    elif data.startswith("group_set_panel:"):
        parts = data.split(":", 2)
        group_id = parts[1]
        panel_val = parts[2]
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE groups SET panel = %s WHERE group_id = %s", (panel_val, group_id))
            conn.commit()
            cache_invalidate("groups")
        finally:
            put_db(conn)
        await show_group_detail(query, group_id)

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
        group = groups.get(group_id, {})
        btns = group.get("buttons", [])
        if isinstance(btns, list) and 0 <= btn_idx < len(btns):
            btns.pop(btn_idx)
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE groups SET buttons = %s WHERE group_id = %s", (json.dumps(btns), group_id))
                conn.commit()
                cache_invalidate("groups")
            finally:
                put_db(conn)
        await show_group_buttons(query, group_id)

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
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE welcome_settings SET buttons = %s", (json.dumps(btns),))
                conn.commit()
                cache_invalidate("welcome")
            finally:
                put_db(conn)
        await show_welcome_settings(query)

    elif data.startswith("panel_add_number:"):
        panel_name = data.split(":", 1)[1]
        context.user_data["awaiting"] = f"add_number:{panel_name}"
        await query.edit_message_text(
            f"\U0001f4f1 Send termination string to add numbers:\n\nPanel: {panel_name}\n\nExample: MADAGASCAR 1488",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")]])
        )


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
    keyboard.append([InlineKeyboardButton("\u2795 Add Number", callback_data=f"panel_add_number:{panel_name}")])
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
                'draw': 1, 'start': start, 'length': length,
                'columns[0][data]': 'number_id', 'columns[0][name]': 'id',
                'columns[1][data]': 'Number', 'columns[1][name]': 'Number',
                'columns[2][data]': 'range', 'columns[2][name]': 'range',
                'columns[3][data]': 'A2P', 'columns[3][name]': 'A2P',
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


async def get_hub_auth_token(panel_name):
    panels = load_panels()
    panel_config = panels.get(panel_name)
    if not panel_config:
        return None, None
    client, csrf = await get_panel_session(panel_name, panel_config)
    if not client or not csrf:
        return None, None
    base_url = panel_config.get("base_url", "")
    try:
        portal_res = await client.get(urljoin(base_url, "/portal"))
        match = re.search(r'hub\.orangecarrier\.com\?system=(\w+)&auth=([A-Za-z0-9+/=]+)', portal_res.text)
        if match:
            system = match.group(1)
            auth_token = match.group(2)
            return system, auth_token
        print(f"\u274c Hub auth token not found on portal page for panel '{panel_name}'")
        return None, None
    except Exception as e:
        print(f"\u274c Error getting hub auth token: {e}")
        return None, None


async def hub_authenticate(system, auth_token):
    try:
        async with httpx.AsyncClient(timeout=10.0) as hc:
            res = await hc.get(f"https://hub.orangecarrier.com/api/auth?token={auth_token}&system={system}")
            if res.status_code == 200:
                data = res.json()
                if data.get("email"):
                    return data
            print(f"\u274c Hub auth failed: {res.status_code} {res.text[:200]}")
    except Exception as e:
        print(f"\u274c Hub auth error: {e}")
    return None


async def add_number_via_hub(panel_name, termination_string):
    import socketio
    system, auth_token = await get_hub_auth_token(panel_name)
    if not system or not auth_token:
        return False, "Could not get hub auth token from panel"
    user_data = await hub_authenticate(system, auth_token)
    if not user_data:
        return False, "Hub authentication failed"
    email = user_data["email"]
    chat_type = "internal"
    result = {"success": False, "message": "Timeout waiting for response"}
    response_event = asyncio.Event()

    sio = socketio.AsyncClient(reconnection=False)

    @sio.on('connect')
    async def on_connect():
        user_room = f"user:{email}:{system}:{chat_type}"
        await sio.emit('join_user_room', {'room': user_room})
        await asyncio.sleep(0.5)
        await sio.emit('menu_selection', {
            'selection': 'add_numbers',
            'email': email,
            'system': system,
            'type': chat_type
        })

    @sio.on('bot_message')
    async def on_bot_message(data):
        content = data.get('content', '') if isinstance(data, dict) else str(data)
        if 'form' in content.lower() or 'termination' in content.lower() or 'input' in content.lower():
            await sio.emit('form_submission', {
                'formType': 'add_numbers',
                'formData': {'termination_string': termination_string},
                'email': email,
                'system': system,
                'type': chat_type
            })
        elif any(kw in content.lower() for kw in ['success', 'added', 'completed', 'done', 'request received']):
            result["success"] = True
            result["message"] = content[:200]
            response_event.set()
        elif any(kw in content.lower() for kw in ['error', 'failed', 'invalid', 'not found', 'blocked']):
            result["success"] = False
            result["message"] = content[:200]
            response_event.set()

    @sio.on('error')
    async def on_error(data):
        msg = data.get('message', str(data)) if isinstance(data, dict) else str(data)
        result["success"] = False
        result["message"] = msg[:200]
        response_event.set()

    try:
        await sio.connect('https://hub.orangecarrier.com', transports=['polling', 'websocket'])
        try:
            await asyncio.wait_for(response_event.wait(), timeout=15)
        except asyncio.TimeoutError:
            result["success"] = True
            result["message"] = f"Add request sent for '{termination_string}'"
        await sio.disconnect()
    except Exception as e:
        print(f"\u274c Hub socket error: {e}")
        result["success"] = False
        result["message"] = str(e)

    return result["success"], result["message"]


async def add_number_to_panel(panel_name, termination_string):
    panels = load_panels()
    panel_config = panels.get(panel_name)
    if not panel_config:
        return False, "Panel not found"
    return await add_number_via_hub(panel_name, termination_string)


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
    country_name = re.sub(r'\s*\d+\s*$', '', real_range).strip()
    if not country_name:
        country_name = real_range
    safe_country = re.sub(r'[^a-zA-Z0-9_]', '_', country_name)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', prefix=f'{safe_country}_', delete=False) as f:
        f.write(file_content)
        tmp_path = f.name
    try:
        chat_id = query.message.chat_id
        with open(tmp_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=chat_id,
                document=InputFile(f, filename=f"{safe_country}_numbers.txt"),
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
        await query.edit_message_text(f"\U0001f4f1 No numbers found.", reply_markup=InlineKeyboardMarkup(keyboard))
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
    await query.edit_message_text(f"\U0001f5d1 Delete numbers from '{real_range}':", reply_markup=InlineKeyboardMarkup(keyboard))


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
    status_icon = "\U0001f7e2" if group.get("active", True) else "\U0001f534"
    status_text = "Active" if group.get("active", True) else "Inactive"
    panel = group.get("panel", "none")
    panel_display = "\U0001f4c1 All Panels" if panel == "all" else panel
    btns = group.get("buttons", [])
    btn_count = len(btns) if isinstance(btns, list) else 0
    text = (
        f"\U0001f4c2 Group: {group_id}\n\n"
        f"Status: {status_icon} {status_text}\n"
        f"Assigned Panel: \U0001f4c1 {panel_display}\n"
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


async def show_group_panel_select(query, group_id):
    panels = load_panels()
    keyboard = []
    keyboard.append([InlineKeyboardButton("\U0001f4c1 All Panels", callback_data=f"group_set_panel:{group_id}:all")])
    for name in panels:
        keyboard.append([InlineKeyboardButton(f"\U0001f4c1 {name}", callback_data=f"group_set_panel:{group_id}:{name}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_detail:{group_id}")])
    await query.edit_message_text(f"Select panel for group {group_id}:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_group_buttons(query, group_id):
    groups = load_groups()
    group = groups.get(group_id, {})
    btns = group.get("buttons", [])
    if not isinstance(btns, list):
        btns = []
    btn_count = len(btns)
    text = f"\U0001f517 Buttons for group {group_id} ({btn_count}/4):"
    if btns:
        for i, btn in enumerate(btns):
            text += f"\n{i+1}. {btn.get('text', '')} -> {btn.get('url', '')}"
    else:
        text += "\nNo buttons configured."
    keyboard = []
    for i, btn in enumerate(btns):
        keyboard.append([InlineKeyboardButton(f"\U0001f5d1 Remove: {btn.get('text', '')}", callback_data=f"group_del_btn:{group_id}:{i}")])
    if btn_count < 4:
        keyboard.append([InlineKeyboardButton("\u2795 Add Button", callback_data=f"group_add_btn:{group_id}")])
    keyboard.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_detail:{group_id}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_owner_panel(query):
    keyboard = [
        [InlineKeyboardButton("+ Add Account", callback_data="add_panel")],
        [InlineKeyboardButton("+ Add Group", callback_data="add_group")],
        [InlineKeyboardButton("+ Add Owner", callback_data="add_owner")],
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
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM panels WHERE name = %s", (panel_name,))
            counter = 1
            orig_name = panel_name
            while cur.fetchone():
                panel_name = f"{orig_name}{counter}"
                counter += 1
                cur.execute("SELECT name FROM panels WHERE name = %s", (panel_name,))

            cur.execute(
                "INSERT INTO panels (id, name, login_url, base_url, sms_url, username, password, active) VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, TRUE)",
                (panel_name, login_url, base_url, sms_url, username, password)
            )
            conn.commit()
            cache_invalidate("panels")
        finally:
            put_db(conn)

        context.user_data["awaiting"] = ""
        keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]
        await update.message.reply_text(f"\u2705 Login Successful!\n\U0001f4e7 {username}\n\U0001f4c1 Panel: {panel_name}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif awaiting == "add_group_id":
        group_id = text
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT group_id FROM groups WHERE group_id = %s", (group_id,))
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO groups (id, group_id, panel, active, buttons) VALUES (gen_random_uuid(), %s, 'none', TRUE, '[]')",
                    (group_id,)
                )
                conn.commit()
                cache_invalidate("groups")
                await update.message.reply_text(f"\u2705 Group {group_id} added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
            else:
                await update.message.reply_text(f"\u26a0\ufe0f Group {group_id} already exists.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        finally:
            put_db(conn)
        context.user_data["awaiting"] = ""

    elif awaiting == "add_owner_id":
        owner_id = text
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM owners WHERE user_id = %s", (owner_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO owners (id, user_id) VALUES (gen_random_uuid(), %s)", (owner_id,))
                conn.commit()
                cache_invalidate("owners")
                await update.message.reply_text(f"\u2705 Owner {owner_id} added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
            else:
                await update.message.reply_text(f"\u26a0\ufe0f Owner {owner_id} already exists.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="owner_panel")]]))
        finally:
            put_db(conn)
        context.user_data["awaiting"] = ""

    elif awaiting == "welcome_edit_msg":
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE welcome_settings SET message = %s", (text,))
            conn.commit()
            cache_invalidate("welcome")
        finally:
            put_db(conn)
        context.user_data["awaiting"] = ""
        await update.message.reply_text("\u2705 Welcome message updated!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="welcome_settings")]]))

    elif awaiting == "welcome_add_btn":
        if "|" in text:
            parts = text.split("|", 1)
            btn_text = parts[0].strip()
            btn_url = parts[1].strip()
            welcome = load_welcome()
            btns = welcome.get("buttons", [])
            btns.append({"text": btn_text, "url": btn_url})
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE welcome_settings SET buttons = %s", (json.dumps(btns),))
                conn.commit()
                cache_invalidate("welcome")
            finally:
                put_db(conn)
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
            group = groups.get(group_id, {})
            btns = group.get("buttons", [])
            if not isinstance(btns, list):
                btns = []
            if len(btns) >= 4:
                context.user_data["awaiting"] = ""
                await update.message.reply_text("\u26a0\ufe0f Maximum 4 buttons allowed!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_buttons:{group_id}")]]))
            else:
                btns.append({"text": btn_text, "url": btn_url})
                conn = get_db()
                try:
                    cur = conn.cursor()
                    cur.execute("UPDATE groups SET buttons = %s WHERE group_id = %s", (json.dumps(btns), group_id))
                    conn.commit()
                    cache_invalidate("groups")
                finally:
                    put_db(conn)
                context.user_data["awaiting"] = ""
                await update.message.reply_text(f"\u2705 Button '{btn_text}' added!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"group_buttons:{group_id}")]]))
        else:
            await update.message.reply_text("Invalid format. Use: text | url")

    elif awaiting and awaiting.startswith("add_number:"):
        panel_name = awaiting[len("add_number:"):]
        termination_string = text.strip()
        if not termination_string:
            await update.message.reply_text("Please send a valid termination string.")
            return
        await update.message.reply_text(f"\u23f3 Adding '{termination_string}' to panel '{panel_name}'...")
        success, msg = await add_number_to_panel(panel_name, termination_string)
        context.user_data["awaiting"] = ""
        if success:
            keyboard = [
                [InlineKeyboardButton("\u2795 Add Another", callback_data=f"panel_add_number:{panel_name}")],
                [InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")]
            ]
            await update.message.reply_text(f"\u2705 {msg}", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton("\u2b05\ufe0f Back", callback_data=f"panel_detail:{panel_name}")]]
            await update.message.reply_text(f"\u274c Failed: {msg}", reply_markup=InlineKeyboardMarkup(keyboard))


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
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
    new_client = httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=headers, limits=limits, http2=False)
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
            print(f"\u274c Login failed for panel '{panel_name}'.")
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
        summary_response = await client.post(sms_url_endpoint, data=first_payload, timeout=5.0)
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
        sem = asyncio.Semaphore(30)

        async def fetch_group(group_id):
            msgs = []
            try:
                numbers_payload = {'start': from_date_str, 'end': to_date_str, 'range': group_id, '_token': csrf_token}
                numbers_response = await client.post(numbers_url, data=numbers_payload, timeout=5.0)
                numbers_soup = BeautifulSoup(numbers_response.text, 'lxml')
                number_divs = numbers_soup.select("div[onclick*='getDetialsNumber']")
                if not number_divs:
                    return msgs

                async def fetch_number_sms(phone_number):
                    async with sem:
                        num_msgs = []
                        try:
                            sms_payload = {'start': from_date_str, 'end': to_date_str, 'Number': phone_number, 'Range': group_id, '_token': csrf_token}
                            sms_response = await client.post(sms_detail_url, data=sms_payload, timeout=5.0)
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
    except Exception as e:
        print(f"\u274c Error fetching SMS: {e}")
        traceback.print_exc()
        return []


def html_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


async def send_telegram_message(context, chat_id, message_data, buttons=None):
    global _group_failures
    fail_info = _group_failures.get(str(chat_id))
    if fail_info:
        cd = fail_info.get("cooldown", GROUP_FAIL_COOLDOWN)
        if time.time() - fail_info.get("time", 0) < cd:
            return "skipped"
        else:
            _group_failures.pop(str(chat_id), None)
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
        formatted_number = number_str
        if len(number_str) > 5:
            formatted_number = f"+{number_str[:2]}*{number_str[-5:]}"

        full_message = (
            f"<b>{flag_emoji} New {html_escape(display_country)} {html_escape(service_name)} OTP!</b>\n\n"
            f"<blockquote>\U0001f570 Time: {html_escape(time_str)}</blockquote>\n"
            f"<blockquote>{flag_emoji} Country: {html_escape(display_country)}</blockquote>\n"
            f"<blockquote>{service_emoji} Service: {html_escape(service_name)}</blockquote>\n"
            f"<blockquote>\U0001f4de Number: {html_escape(formatted_number)}</blockquote>\n"
            f"<blockquote>\U0001f511 OTP: <code>{html_escape(code_str)}</code></blockquote>\n\n"
            f"<blockquote>\U0001f4e9 Full Message:</blockquote>\n"
            f"<pre>{html_escape(full_sms_text)}</pre>\n\n"
            f"Powered By Junaid Niz \U0001f497"
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
            context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode='HTML', reply_markup=reply_markup),
            timeout=10
        )
        return "sent"
    except asyncio.TimeoutError:
        print(f"\u274c Timeout sending to {chat_id}")
        return "failed"
    except Exception as e:
        err_str = str(e).lower()
        if "chat not found" in err_str or "bot was kicked" in err_str or "not enough rights" in err_str or "chat_not_found" in err_str:
            _group_failures[str(chat_id)] = {"time": time.time(), "permanent": False, "cooldown": 600}
            print(f"\u274c Group {chat_id} skipped (10min): {e}")
        elif "flood control" in err_str or "retry in" in err_str:
            retry_match = re.search(r'retry in (\d+)', err_str)
            cooldown = int(retry_match.group(1)) + 2 if retry_match else 10
            _group_failures[str(chat_id)] = {"time": time.time(), "permanent": False, "cooldown": cooldown}
            print(f"\u274c Flood control for {chat_id}, retry in {cooldown}s")
        else:
            print(f"\u274c Error sending to {chat_id}: {e}")
        return "failed"


_job_running = False

async def check_sms_job(context: ContextTypes.DEFAULT_TYPE):
    global _job_running, _first_run_done
    if _job_running:
        return
    _job_running = True
    try:
        panels = load_panels()
        groups = load_groups()
        active_panels = {name: cfg for name, cfg in panels.items() if cfg.get("active", True)}
        if not active_panels:
            return
        active_groups = {}
        for gid, info in groups.items():
            if not info.get("active", True):
                continue
            active_groups[gid] = info
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

        global _processed_ids_cache
        total_new = 0

        async def process_panel_and_send(panel_name, group_ids):
            nonlocal total_new
            panel_cfg = active_panels[panel_name]
            client, csrf = await get_panel_session(panel_name, panel_cfg)
            if not client or not csrf:
                return
            try:
                messages = await fetch_sms_from_panel(client, csrf, panel_cfg)
                if not messages:
                    return
                new_msgs = []
                for msg in reversed(messages):
                    if msg["id"] not in _processed_ids_cache:
                        new_msgs.append(msg)
                if not new_msgs:
                    return
                if not _first_run_done:
                    for msg in new_msgs:
                        _processed_ids_cache.add(msg["id"])
                    return
                for msg in new_msgs:
                    sends = []
                    for gid in group_ids:
                        group_info = groups.get(gid, {})
                        group_buttons = group_info.get("buttons", [])
                        sends.append(send_telegram_message(context, gid, msg, buttons=group_buttons))
                    if sends:
                        results = await asyncio.gather(*sends, return_exceptions=True)
                        any_success = any(r == "sent" for r in results)
                        if any_success:
                            _processed_ids_cache.add(msg["id"])
                            total_new += 1
            except Exception as e:
                print(f"\u274c Error checking panel '{panel_name}': {e}")
                if panel_name in _panel_sessions:
                    del _panel_sessions[panel_name]

        panel_tasks = [process_panel_and_send(pn, gids) for pn, gids in panel_to_groups.items()]
        await asyncio.gather(*panel_tasks, return_exceptions=True)

        if not _first_run_done:
            _first_run_done = True
            cached = len(_processed_ids_cache)
            print(f"\U0001f504 First run: cached {cached} existing SMS IDs. Now watching for new OTPs only.")
        elif total_new > 0:
            if len(_processed_ids_cache) > 5000:
                _processed_ids_cache = set(list(_processed_ids_cache)[-3000:])
            print(f"\u2705 Sent {total_new} new OTP(s).")
    finally:
        _job_running = False


def main():
    print("\U0001f680 OTP Bot is starting...")
    if not YOUR_BOT_TOKEN:
        print("\U0001f534 ERROR: TELEGRAM_BOT_TOKEN not set!")
        return
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
