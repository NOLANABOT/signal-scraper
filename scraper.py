import re
import json
from datetime import datetime
from telethon import TelegramClient, events
from supabase import create_client, Client

# --- 1. YOUR TELEGRAM CREDENTIALS ---
API_ID = '37547588'          
API_HASH = 'eacf1dc4c35e5a45230da16e4fa58181'      

# --- 2. YOUR SUPABASE CREDENTIALS ---
SUPABASE_URL = "https://zzritokppywwfgyxkcai.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp6cml0b2twcHl3d2ZneXhrY2FpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIxNzg0OTksImV4cCI6MjEwNzc1NDQ5OX0.NeLz7eNzfEb9OKfAOhukp6P1tAAA20C5rGI2BHBrIZI"

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 3. YOUR TARGET CHANNELS/GROUPS ---
TARGET_CHATS = [
    '@Binolla_Free_Trade_Binary_Signal',
    '@Olymp_Trade_Signals_Free_Binary',
    '@Iq_Options_Free_Binary_Signals',
    -1002250116987  # Micha Trader VIP private group
]

# Initialize the Telegram client
client = TelegramClient('signal_bot', API_ID, API_HASH)

# --- 4. TEMPORARY CACHE ---
# Stores the database ID of the pending signal for each chat
pending_signal_ids = {} 

# --- 5. DATABASE FUNCTIONS ---
def insert_signal(data):
    """Inserts a new signal into the database and returns the new row's ID."""
    try:
        response = supabase.table("signals").insert(data).execute()
        new_id = response.data[0]['id']
        print("✅ Successfully inserted to Database!")
        return new_id
    except Exception as e:
        print(f"❌ Database Insert Error: {e}")
        return None

def update_signal(signal_id, update_data):
    """Updates an existing signal in the database."""
    try:
        response = supabase.table("signals").update(update_data).eq("id", signal_id).execute()
        print("✅ Successfully updated signal in Database!")
    except Exception as e:
        print(f"❌ Database Update Error: {e}")

def update_latest_result(group_name, status):
    """Finds the latest active signal for a group and updates its status to WIN/LOSS."""
    try:
        # Find the most recent signal for this group that is still PENDING or ACTIVE
        response = supabase.table("signals").select("id").eq("group_name", group_name).in_("status", ["PENDING", "ACTIVE"]).order("timestamp", desc=True).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            signal_id = response.data[0]['id']
            supabase.table("signals").update({"status": status}).eq("id", signal_id).execute()
            print(f"✅ Successfully updated latest signal for {group_name} to {status}!")
        else:
            print(f"⚠️ No pending signal found to update for {group_name}.")
    except Exception as e:
        print(f"❌ Database Result Update Error: {e}")

# --- 6. MAIN MESSAGE HANDLER ---
@client.on(events.NewMessage(chats=TARGET_CHATS))
async def message_handler(event):
    text = event.raw_text
    text_upper = text.upper()
    chat_id = event.chat_id
    
    chat_title = event.chat.title if hasattr(event.chat, 'title') else str(chat_id)
    
    if not text or len(text.strip()) < 5:
        return

    # ==========================================
    # STEP 1: CHECK FOR RESULTS (WIN/LOSS)
    # ==========================================
    is_win = bool(re.search(r'TRADE\s+WIN|TRADE\s+CLOSED\s+IN\s+PROFIT|PROFIT', text_upper))
    is_loss = bool(re.search(r'TRADE\s+LOSS|TRADE\s+CLOSED\s+IN\s+LOSS|LOSS', text_upper))

    if is_win or is_loss:
        status = "WIN" if is_win else "LOSS"
        print(f"🔔 Result detected: {status} for {chat_title}")
        update_latest_result(chat_title, status)
        return  

    # ==========================================
    # STEP 2: CHECK FOR DIRECTION (Message 2 for Public Channels)
    # ==========================================
    if chat_id != -1002250116987:  
        if re.search(r'\b(CALL|PUT|BUY|SELL|UP|DOWN)\b', text_upper) or '🟢' in text or '🔴' in text:
            if chat_id in pending_signal_ids:
                signal_id = pending_signal_ids.pop(chat_id)
                
                direction = "UP" if re.search(r'CALL|BUY|UP|🟢', text_upper) else "DOWN"
                
                print(f"🔔 Direction detected: {direction}. Updating signal ID {signal_id}...")
                update_signal(signal_id, {"direction": direction, "status": "ACTIVE"})
                return
            else:
                return  

    # ==========================================
    # STEP 3: CHECK FOR SIGNAL PART 1 (Public Channels)
    # ==========================================
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
            print(f"🔔 New signal detected: {payload['asset']}. Inserting into database immediately...")
            new_id = insert_signal(payload)
            if new_id:
                pending_signal_ids[chat_id] = new_id
            return

    # ==========================================
    # STEP 4: CHECK FOR PRIVATE CHANNEL (Micha Trader)
    # ==========================================
    else:
        asset_match = re.search(r'([A-Z]{3,}/[A-Z]{3,}|[A-Z]{4,6})\s*OTC', text_upper)
        expiry_match = re.search(r'(\d+)\s*(MIN|MINUTE|MINUTES)\b', text_upper)

        if asset_match:
            direction = "DOWN" if re.search(r'SELL|PUT|DOWN|🔴', text_upper) else "UP"
                
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
            print(f"🔔 Private signal detected: {payload['asset']}. Inserting into database...")
            insert_signal(payload)
            return

# --- 7. START THE CLIENT ---
print("🚀 Binary Options Signal Scraper Starting...")
print("📡 Listening to 4 channels/groups...")
print("=" * 50)

client.start()
print("✅ Successfully connected to Telegram!")
print("📊 Waiting for signals...")
client.run_until_disconnected()