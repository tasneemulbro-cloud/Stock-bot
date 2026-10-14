import os
import json
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- Flask Server (বটকে জাগিয়ে রাখার জন্য) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- বটের কনফিগারেশন ---
TOKEN = os.getenv("BOT_TOKEN")
PASSWORD = os.getenv("PASSWORD", "1234")
DATA_FILE = "database.json"

AUTH, MENU, GET_NAME, GET_DATA = range(4)

def load_db():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {}

def save_db(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- বটের ফাংশনসমূহ ---
def main_menu():
    return ReplyKeyboardMarkup([["📦 PRODUCTS"], ["➕ Add Product"]], resize_keyboard=True)

def cancel_menu():
    return ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Password please:")
    return AUTH

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == PASSWORD:
        await update.message.reply_text("✅ Welcome!", reply_markup=main_menu())
        return MENU
    await update.message.reply_text("❌ Wrong Password! Try again:")
    return AUTH

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Product Name:", reply_markup=cancel_menu())
    return GET_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("Main Menu:", reply_markup=main_menu())
        return MENU
    context.user_data['p_name'] = update.message.text
    await update.message.reply_text(f"📥 Paste data for '{update.message.text}':", reply_markup=cancel_menu())
    return GET_DATA

async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("Main Menu:", reply_markup=main_menu())
        return MENU
    
    lines = update.message.text.split('\n')
    valid_items = [l.strip() for l in lines if l.strip().endswith("53")]
    
    if not valid_items:
        await update.message.reply_text("⚠️ No valid data found. Try again:")
        return GET_DATA

    name = context.user_data['p_name']
    db = load_db()
    if name not in db: db[name] = []
    db[name].extend(valid_items)
    save_db(db)

    await update.message.reply_text(f"✅ Added {len(valid_items)} items.\nStock: {len(db[name])}", reply_markup=main_menu())
    return MENU

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not db:
        await update.message.reply_text("Empty Stock!")
        return MENU
    buttons = [[n] for n in db.keys() if len(db[n]) > 0]
    buttons.append(["❌ Cancel"])
    await update.message.reply_text("Choose Product:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return MENU

async def deliver_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice == "❌ Cancel":
        await update.message.reply_text("Main Menu:", reply_markup=main_menu())
        return MENU
    db = load_db()
    if choice in db and len(db[choice]) > 0:
        item = db[choice].pop(0)
        save_db(db)
        await update.message.reply_text(f"🎁 Product:\n`{item}`\n\nRemains: {len(db[choice])}\n\n💖 Thank You!", parse_mode="Markdown", reply_markup=main_menu())
    else:
        await update.message.reply_text("Out of stock!", reply_markup=main_menu())
    return MENU

def main():
    # Keep alive সার্ভার চালু করা
    keep_alive()
    
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth)],
            MENU: [
                MessageHandler(filters.Regex("^📦 PRODUCTS$"), list_products),
                MessageHandler(filters.Regex("^➕ Add Product$"), add_start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, deliver_product)
            ],
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GET_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_data)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
