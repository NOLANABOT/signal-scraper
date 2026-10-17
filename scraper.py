import re
import json
import threading
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from supabase import create_client, Client
from flask import Flask

# --- 1. YOUR TELEGRAM CREDENTIALS ---
API_ID = '37547588'          
API_HASH = 'eacf1dc4c35e5a45230da16e4fa58181'      

# --- 2. YOUR STRING SESSION ---
SESSION_STRING = "1BJWap1wBu8U0x4CDPzDHjdWTSI0xJrXmbTqHwelSeo8NJEPb-3wf5HNiHlnnmvlz2xZD9P9fCzd2KsGHaLteHZXUL38yQjzT1tkN-P88sU224PNve4HgGbtG32xdfrQzASScE0418USzSt0Vgsa5P6YPq-PvHH0cn93pBu7N3EwmLLg7jUc0la0JaTH52CY8zJ3M5IDLG9gZT_m-oKUbnZIIEC6XTcy0F9hVPUqqn2DZUq5HXzB6JBUIZEUvuEDablOpq39hma4EQ-AeRuAGkOooEFE5xRhwOpwpophQk1Puop5HPWsbKctmHz46A-OM7XMxzOcDOfCeGLxNglYZTX_hW3830ug="

# --- 3. YOUR SUPABASE CREDENTIALS ---
SUPABASE_URL = "https://zzritokppywwfgyxkcai.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp6cml0b2twcHl3d2ZneXhrY2FpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIxNzg0OTksImV4cCI6MjEwNzc1NDQ5OX0.NeLz7eNzfEb9OKfAOhukp6P1tAAA20C5rGI2BHBrIZI"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 4. YOUR TARGET CHANNELS/GROUPS ---
TARGET_CHATS = [
    '@Binolla_Free_Trade_Binary_Signal',
    '@Olymp_Trade_Signals_Free_Binary',
    '@Iq_Options_Free_Binary_Signals',
    -1002250116987  # Micha Trader VIP private group
]

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- 5. TEMPORARY CACHE ---
pending_signal_ids = {} 

# --- 6. KEEP-ALIVE WEB SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "✅ Bot is running!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web_server, daemon=True).start()

# --- 7. DATABASE FUNCTIONS ---
def insert_signal(data):
    try:
        response = supabase.table("signals").insert(data).execute()
        new_id = response.data[0]['id']
        print("✅ Inserted to DB!")
        return new_id
    except Exception as e:
        print(f"❌ DB Insert Error: {e}")
        return None

def update_signal(signal_id, update_data):
    try:
        supabase.table("signals").update(update_data).eq("id", signal_id).execute()
        print(f"✅ Updated signal {signal_id} in DB!")
    except Exception as e:
        print(f"❌ DB Update Error: {e}")

def update_latest_result(group_name, status):
    try:
        response = supabase.table("signals").select("id").eq("group_name", group_name).in_("status", ["PENDING", "ACTIVE", "WAITING"]).order("timestamp", desc=True).limit(1).execute()
        if response.data and len(response.data) > 0:
            signal_id = response.data[0]['id']
            supabase.table("signals").update({"status": status}).eq("id", signal_id).execute()
            print(f"✅ Updated result to {status}!")
    except Exception as e:
        print(f"❌ DB Result Error: {e}")

# --- 8. ULTRA-FAST MESSAGE HANDLER ---
@client.on(events.NewMessage(chats=TARGET_CHATS))
async def message_handler(event):
    text = event.raw_text
    text_upper = text.upper()
    chat_id = event.chat_id
    chat_title = event.chat.title if hasattr(event.chat, 'title') else str(chat_id)
    
    if not text or len(text.strip()) < 2:
        return

    # 🔥 STEP 1: ULTRA-FAST DIRECTION CHECK (Check this FIRST!)
    if chat_id != -1002250116987:  # Public channels only
        # Look for UP or DOWN anywhere in the message - ultra aggressive detection
        if 'UP' in text_upper or '⬆️' in text or '️' in text or '🟢' in text or 'CALL' in text_upper or 'BUY' in text_upper:
            if chat_id in pending_signal_ids:
                signal_id = pending_signal_ids.pop(chat_id)
                print(f"🚀 FAST CATCH: UP detected! Updating ID {signal_id}")
                update_signal(signal_id, {"direction": "UP", "status": "ACTIVE"})
                return
        
        if 'DOWN' in text_upper or '⬇️' in text or '↘️' in text or '🔴' in text or 'SELL' in text_upper or 'PUT' in text_upper:
            if chat_id in pending_signal_ids:
                signal_id = pending_signal_ids.pop(chat_id)
                print(f"🚀 FAST CATCH: DOWN detected! Updating ID {signal_id}")
                update_signal(signal_id, {"direction": "DOWN", "status": "ACTIVE"})
                return

    #  STEP 2: CHECK FOR RESULTS (WIN/LOSS)
    if 'WIN' in text_upper or 'PROFIT' in text_upper or '✅' in text:
        print(f"🔔 WIN detected for {chat_title}")
        update_latest_result(chat_title, "WIN")
        return
    
    if 'LOSS' in text_upper or '❌' in text:
        print(f"🔔 LOSS detected for {chat_title}")
        update_latest_result(chat_title, "LOSS")
        return

    #  STEP 3: NEW SIGNAL (Asset + Expiry + Investment)
    if chat_id != -1002250116987:
        asset_match = re.search(r'([A-Z]{3,}/[A-Z]{3,}|[A-Z]{4,6})\s*\(?\s*OTC\s*\)?', text_upper)
        expiry_match = re.search(r'(\d+)\s*(MINUTE|MINUTES|MIN)\b', text_upper)
        invest_match = re.search(r'(?:use\s+)?\$?(\d+)\s*\$?\s*from\s+balance', text, re.IGNORECASE)

        if asset_match:
            payload = {
                "group_name": chat_title,
                "type": "SIGNAL",
                "asset": asset_match.group(1),
                "direction": "WAITING",  
                "expiry": f"{expiry_match.group(1)}M" if expiry_match else "UNKNOWN",
                "investment": f"${invest_match.group(1)}" if invest_match else "UNKNOWN",
                "status": "PENDING",
                "timestamp": datetime.now().isoformat()
            }
            print(f"📩 New signal: {payload['asset']} - Waiting for direction...")
            new_id = insert_signal(payload)
            if new_id:
                pending_signal_ids[chat_id] = new_id
                print(f"⏳ Stored ID {new_id} for {chat_id}, waiting for direction...")
            return

    # 🔥 STEP 4: PRIVATE CHANNEL (All-in-one message)
    else:
        asset_match = re.search(r'([A-Z]{3,}/[A-Z]{3,}|[A-Z]{4,6})\s*OTC', text_upper)
        expiry_match = re.search(r'(\d+)\s*(MIN|MINUTE|MINUTES)\b', text_upper)

        if asset_match:
            direction = "DOWN" if ('SELL' in text_upper or 'PUT' in text_upper or 'DOWN' in text_upper or '🔴' in text) else "UP"
            payload = {
                "group_name": chat_title,
                "type": "SIGNAL",
                "asset": asset_match.group(1),
                "direction": direction,
                "expiry": f"{expiry_match.group(1)}M" if expiry_match else "UNKNOWN",
                "investment": "UNKNOWN",  
                "status": "ACTIVE",
                "timestamp": datetime.now().isoformat()
            }
            print(f"🔐 Private signal: {payload['asset']} {payload['direction']}")
            insert_signal(payload)
            return

# --- 9. START ---
print("🚀 Ultra-Fast Signal Scraper Starting...")
print("📡 Listening to 4 channels...")
print("=" * 50)

client.start()
print("✅ Connected to Telegram!")
client.run_until_disconnected()
