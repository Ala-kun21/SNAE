import subprocess
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# ===== CONFIG (FROM ENV) =====
TOKEN_MAIN = os.getenv("TOKEN_MAIN")

if not TOKEN_MAIN:
    raise RuntimeError("❌ TOKEN_MAIN غير موجود في Environment Variables")

# ===== GLOBALS =====
bot1_process = None
bot2_process = None

# ===== MENUS =====
def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 بوت إدارة بياناتي", callback_data="menu_bot1")],
        [InlineKeyboardButton("📤 إرسال تقارير", callback_data="menu_bot2")],
        [
            InlineKeyboardButton("▶️ تشغيل البوت الرئيسي", callback_data="start_main"),
            InlineKeyboardButton("⏹️ إيقاف البوت الرئيسي", callback_data="stop_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def bot1_menu():
    keyboard = [
        [
            InlineKeyboardButton("▶️ تشغيل بوت 1", callback_data="start_bot1"),
            InlineKeyboardButton("⏹️ إيقاف بوت 1", callback_data="stop_bot1")
        ],
        [InlineKeyboardButton("⬅️ رجوع للقائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def bot2_menu():
    keyboard = [
        [InlineKeyboardButton("📤 إرسال تقرير يومي", callback_data="start_bot2")],
        [InlineKeyboardButton("⬅️ رجوع للقائمة الرئيسية", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ===== SAFE EDIT =====
async def safe_edit(query, text, markup=None):
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except:
        pass

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏠 القائمة الرئيسية", reply_markup=main_menu())

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot1_process, bot2_process
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "main_menu":
        await safe_edit(query, "🏠 القائمة الرئيسية", main_menu())

    elif data == "menu_bot1":
        await safe_edit(query, "📊 بوت إدارة بياناتي", bot1_menu())

    elif data == "menu_bot2":
        await safe_edit(query, "📤 إرسال تقارير", bot2_menu())

    elif data == "start_bot1":
        if not bot1_process or bot1_process.poll() is not None:
            bot1_process = subprocess.Popen(["python3", "run_bot.py"])
            await safe_edit(query, "▶️ تم تشغيل بوت 1", bot1_menu())
        else:
            await safe_edit(query, "⚠️ بوت 1 يعمل بالفعل", bot1_menu())

    elif data == "stop_bot1":
        if bot1_process and bot1_process.poll() is None:
            bot1_process.terminate()
            await safe_edit(query, "⏹️ تم إيقاف بوت 1", bot1_menu())
        else:
            await safe_edit(query, "⚠️ بوت 1 غير شغال", bot1_menu())

    elif data == "start_bot2":
        if not bot2_process or bot2_process.poll() is not None:
            bot2_process = subprocess.Popen(["python3", "SNAE.py"])
            await safe_edit(query, "📤 تم تشغيل بوت 2 (إرسال تقرير يومي)", bot2_menu())
        else:
            await safe_edit(query, "⚠️ بوت 2 يعمل بالفعل", bot2_menu())

    elif data == "start_main":
        await safe_edit(query, "▶️ البوت الرئيسي يعمل...", main_menu())

    elif data == "stop_main":
        await safe_edit(
            query,
            "⏹️ تم إيقاف البوت الرئيسي مؤقتًا.",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ تشغيل البوت الرئيسي", callback_data="start_main")]
            ])
        )

# ===== RUN MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN_MAIN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("💻 Sultan AE")
    print("🤖 BOT SNAE")
    print("✅ Login successful")

    app.run_polling()

if __name__ == "__main__":
    main()
