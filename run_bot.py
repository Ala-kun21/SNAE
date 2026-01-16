# =========================================================
# TELEGRAM MANAGER BOT - FINAL FULL WORKING VERSION
# =========================================================
import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

# ================= CONFIG =================
TOKEN = os.getenv("TOKEN")
OPENAI_KEY = os.getenv("OPENAI_KEY")

# ===== فحص OPENAI_KEY =====
if not OPENAI_KEY:
    raise ValueError("❌ Environment variable OPENAI_KEY is not set")

client = OpenAI(api_key=OPENAI_KEY)

# ====== EMAIL CONFIG ======
EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# ===== فحص متغيرات البريد =====
for var_name in ["EMAIL_ACCOUNT", "EMAIL_PASSWORD", "EMAIL_RECEIVER"]:
    if not os.getenv(var_name):
        raise ValueError(f"❌ Environment variable {var_name} is not set")

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
c = db.cursor()

# ===== TABLES =====
c.execute("""CREATE TABLE IF NOT EXISTS phones(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    phone TEXT,
    created_at TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS folders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tg_file_id TEXT,
    name TEXT,
    folder_id INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS images(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tg_file_id TEXT,
    name TEXT,
    folder_id INTEGER
)""")

db.commit()

# ================= HELPERS =================
def ensure_default_folder(uid):
    c.execute("SELECT id FROM folders WHERE user_id=? AND name='افتراضي'", (uid,))
    r = c.fetchone()
    if not r:
        c.execute("INSERT INTO folders(user_id,name) VALUES (?,?)", (uid, "افتراضي"))
        db.commit()
        return c.lastrowid
    return r[0]

def get_folder_id(uid, name):
    c.execute("SELECT id FROM folders WHERE user_id=? AND name=?", (uid, name))
    r = c.fetchone()
    return r[0] if r else None

def list_folders(uid):
    c.execute("SELECT name FROM folders WHERE user_id=?", (uid,))
    return [x[0] for x in c.fetchall()]

def folder_empty(folder_id):
    c.execute("SELECT 1 FROM files WHERE folder_id=? LIMIT 1", (folder_id,))
    if c.fetchone():
        return False
    c.execute("SELECT 1 FROM images WHERE folder_id=? LIMIT 1", (folder_id,))
    if c.fetchone():
        return False
    return True

# ================= STATES =================
STATE, TMP = {}, {}

(
    MAIN, PHONE,
    ADD_NAME, ADD_PHONE,
    EDIT_PHONE_ID, EDIT_PHONE_NEW,
    DEL_PHONE,
    FILE_MENU, IMAGE_MENU,
    CREATE_FOLDER, DELETE_FOLDER,
    DEL_FILE, MOVE_FILE, DOWNLOAD_FILE,
    DEL_IMAGE, MOVE_IMAGE, DOWNLOAD_IMAGE,
    DB_MANAGE,
    AI
) = range(19)

# ================= MENUS =================
MAIN_MENU = ReplyKeyboardMarkup([
    ["📞 الأرقام"],
    ["📁 الملفات", "🖼️ الصور"],
    ["🗄️ إدارة قواعد البيانات"],
    ["🤖 الذكاء الاصطناعي"]
], resize_keyboard=True)

PHONE_MENU = ReplyKeyboardMarkup([
    ["➕ إضافة رقم", "📋 عرض الأرقام"],
    ["✏️ تعديل رقم", "❌ حذف رقم"],
    ["🔙 رجوع"]
], resize_keyboard=True)

DB_MENU = ReplyKeyboardMarkup([
    ["📊 إرسال تقرير يومي إلى الإيميل"],
    ["🔙 رجوع"]
], resize_keyboard=True)

def file_menu():
    return ReplyKeyboardMarkup([
        ["📁 عرض الملفات", "🗂️ إنشاء مجلد"],
        ["📤 نقل ملف", "❌ حذف ملف"],
        ["📁 تنزيل ملفات"],
        ["❌ حذف مجلد"],
        ["📂 عرض المجلدات"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

def image_menu():
    return ReplyKeyboardMarkup([
        ["🖼️ عرض الصور", "🗂️ إنشاء مجلد صور"],
        ["📤 نقل صورة", "❌ حذف صورة"],
        ["🖼️ تنزيل صور"],
        ["❌ حذف مجلد"],
        ["📂 عرض مجلدات الصور"],
        ["🔙 رجوع"]
    ], resize_keyboard=True)

# ================= REPORT & EMAIL =================
def generate_daily_report(user_id):
    c.execute("SELECT COUNT(*) FROM phones WHERE user_id=?", (user_id,))
    phones = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM files WHERE user_id=?", (user_id,))
    files = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM images WHERE user_id=?", (user_id,))
    images = c.fetchone()[0]

    report = (
        "📊 تقرير إدارة قاعدة البيانات\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📞 عدد الأرقام : {phones}\n"
        f"📁 عدد الملفات : {files}\n"
        f"🖼️ عدد الصور   : {images}\n\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return report

def send_report_email(report_text):
    msg = MIMEText(report_text, "plain", "utf-8")
    msg["Subject"] = "📊 التقرير اليومي - Telegram Manager Bot"
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = EMAIL_RECEIVER

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    STATE[uid] = MAIN
    ensure_default_folder(uid)
    await update.message.reply_text("👋 أهلاً بك", reply_markup=MAIN_MENU)

# ================= TEXT HANDLER =================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text
    state = STATE.get(uid, MAIN)

    # ===== MAIN =====
    if state == MAIN:
        if msg == "📞 الأرقام":
            STATE[uid] = PHONE
            await update.message.reply_text("📞 إدارة الأرقام", reply_markup=PHONE_MENU)

        elif msg == "📁 الملفات":
            STATE[uid] = FILE_MENU
            await update.message.reply_text("📁 إدارة الملفات", reply_markup=file_menu())

        elif msg == "🖼️ الصور":
            STATE[uid] = IMAGE_MENU
            await update.message.reply_text("🖼️ إدارة الصور", reply_markup=image_menu())

        elif msg == "🗄️ إدارة قواعد البيانات":
            STATE[uid] = DB_MANAGE
            await update.message.reply_text("🗄️ إدارة قواعد البيانات", reply_markup=DB_MENU)

        elif msg == "🤖 الذكاء الاصطناعي":
            STATE[uid] = AI
            await update.message.reply_text("🤖 اكتب سؤالك:", reply_markup=ReplyKeyboardRemove())

    # ===== PHONE =====
    elif state == PHONE:
        if msg == "➕ إضافة رقم":
            STATE[uid] = ADD_NAME
            await update.message.reply_text("👤 اسم الشخص:")

        elif msg == "📋 عرض الأرقام":
            c.execute("SELECT id,name,phone FROM phones WHERE user_id=?", (uid,))
            rows = c.fetchall()
            await update.message.reply_text(
                "\n".join([f"ID:{i} | {n} : {p}" for i,n,p in rows]) or "📭 لا توجد أرقام"
            )

        elif msg == "✏️ تعديل رقم":
            STATE[uid] = EDIT_PHONE_ID
            await update.message.reply_text("✏️ اكتب ID الرقم:")

        elif msg == "❌ حذف رقم":
            STATE[uid] = DEL_PHONE
            await update.message.reply_text("❌ اكتب ID الرقم:")

        elif msg == "🔙 رجوع":
            await start(update, context)

    elif state == ADD_NAME:
        TMP[uid] = msg
        STATE[uid] = ADD_PHONE
        await update.message.reply_text("📞 رقم الهاتف:")

    elif state == ADD_PHONE:
        c.execute(
            "INSERT INTO phones(user_id,name,phone,created_at) VALUES (?,?,?,?)",
            (uid, TMP[uid], msg, datetime.now().isoformat())
        )
        db.commit()
        await update.message.reply_text("✅ تم حفظ الرقم")
        STATE[uid] = PHONE

    elif state == EDIT_PHONE_ID:
        TMP[uid] = msg
        STATE[uid] = EDIT_PHONE_NEW
        await update.message.reply_text("📞 الرقم الجديد:")

    elif state == EDIT_PHONE_NEW:
        c.execute(
            "UPDATE phones SET phone=? WHERE id=? AND user_id=?",
            (msg, TMP[uid], uid)
        )
        db.commit()
        await update.message.reply_text("✏️ تم التعديل")
        STATE[uid] = PHONE

    elif state == DEL_PHONE:
        c.execute("DELETE FROM phones WHERE id=? AND user_id=?", (msg, uid))
        db.commit()
        await update.message.reply_text("🗑️ تم الحذف")
        STATE[uid] = PHONE

    # ===== DATABASE MANAGEMENT MENU =====
    elif state == DB_MANAGE:
        if msg == "📊 إرسال تقرير يومي إلى الإيميل":
            report = generate_daily_report(uid)
            await update.message.reply_text(report)
            try:
                send_report_email(report)
                await update.message.reply_text("📧 تم إرسال التقرير إلى الإيميل")
            except Exception:
                await update.message.reply_text("❌ فشل إرسال التقرير")
        elif msg == "🔙 رجوع":
            await start(update, context)

    # ===== FILE MENU =====
    elif state == FILE_MENU:
        if msg == "📁 عرض الملفات":
            c.execute("""SELECT files.id,files.name,folders.name
                         FROM files JOIN folders ON files.folder_id=folders.id
                         WHERE files.user_id=?""", (uid,))
            rows = c.fetchall()
            await update.message.reply_text(
                "\n".join([f"ID:{i} {n} ({f})" for i,n,f in rows]) or "لا توجد ملفات"
            )

        elif msg == "🗂️ إنشاء مجلد":
            STATE[uid] = CREATE_FOLDER
            TMP[uid] = "file"
            await update.message.reply_text("اسم المجلد:")

        elif msg == "📤 نقل ملف":
            STATE[uid] = MOVE_FILE
            await update.message.reply_text("ID الملف + اسم المجلد الجديد")

        elif msg == "❌ حذف ملف":
            STATE[uid] = DEL_FILE
            await update.message.reply_text("ID الملف:")

        elif msg == "📁 تنزيل ملفات":
            STATE[uid] = DOWNLOAD_FILE
            await update.message.reply_text("ID الملف:")

        elif msg == "❌ حذف مجلد":
            STATE[uid] = DELETE_FOLDER
            TMP[uid] = "file"
            await update.message.reply_text("🗑️ اسم المجلد:")

        elif msg == "📂 عرض المجلدات":
            await update.message.reply_text("\n".join(list_folders(uid)) or "لا توجد")

        elif msg == "🔙 رجوع":
            await start(update, context)

    # ===== IMAGE MENU =====
    elif state == IMAGE_MENU:
        if msg == "🖼️ عرض الصور":
            c.execute("""SELECT images.id,images.name,folders.name
                         FROM images JOIN folders ON images.folder_id=folders.id
                         WHERE images.user_id=?""", (uid,))
            rows = c.fetchall()
            await update.message.reply_text(
                "\n".join([f"ID:{i} {n} ({f})" for i,n,f in rows]) or "لا توجد صور"
            )

        elif msg == "🗂️ إنشاء مجلد صور":
            STATE[uid] = CREATE_FOLDER
            TMP[uid] = "image"
            await update.message.reply_text("اسم مجلد الصور:")

        elif msg == "📤 نقل صورة":
            STATE[uid] = MOVE_IMAGE
            await update.message.reply_text("ID الصورة + اسم المجلد الجديد")

        elif msg == "❌ حذف صورة":
            STATE[uid] = DEL_IMAGE
            await update.message.reply_text("ID الصورة:")

        elif msg == "🖼️ تنزيل صور":
            STATE[uid] = DOWNLOAD_IMAGE
            await update.message.reply_text("ID الصورة:")

        elif msg == "❌ حذف مجلد":
            STATE[uid] = DELETE_FOLDER
            TMP[uid] = "image"
            await update.message.reply_text("🗑️ اسم المجلد:")

        elif msg == "📂 عرض مجلدات الصور":
            await update.message.reply_text("\n".join(list_folders(uid)) or "لا توجد")

        elif msg == "🔙 رجوع":
            await start(update, context)

    # ===== CREATE / DELETE FOLDER =====
    elif state == CREATE_FOLDER:
        if get_folder_id(uid, msg):
            await update.message.reply_text("❌ المجلد موجود")
        else:
            c.execute("INSERT INTO folders(user_id,name) VALUES (?,?)", (uid, msg))
            db.commit()
            await update.message.reply_text("✅ تم إنشاء المجلد")
        STATE[uid] = FILE_MENU if TMP[uid]=="file" else IMAGE_MENU

    elif state == DELETE_FOLDER:
        if msg == "افتراضي":
            await update.message.reply_text("❌ لا يمكن حذف المجلد الافتراضي")
        else:
            fid = get_folder_id(uid, msg)
            if not fid:
                await update.message.reply_text("❌ المجلد غير موجود")
            elif not folder_empty(fid):
                await update.message.reply_text("❌ المجلد غير فارغ")
            else:
                c.execute("DELETE FROM folders WHERE id=? AND user_id=?", (fid, uid))
                db.commit()
                await update.message.reply_text("🗑️ تم حذف المجلد")
        STATE[uid] = FILE_MENU if TMP[uid]=="file" else IMAGE_MENU

    # ===== FILE ACTIONS =====
    elif state == MOVE_FILE:
        fid, fname = msg.split(maxsplit=1)
        folder = get_folder_id(uid, fname)
        if folder:
            c.execute("UPDATE files SET folder_id=? WHERE id=? AND user_id=?", (folder, fid, uid))
            db.commit()
            await update.message.reply_text("📤 تم النقل")
        else:
            await update.message.reply_text("❌ المجلد غير موجود")
        STATE[uid] = FILE_MENU

    elif state == DEL_FILE:
        c.execute("DELETE FROM files WHERE id=? AND user_id=?", (msg, uid))
        db.commit()
        await update.message.reply_text("🗑️ تم حذف الملف")
        STATE[uid] = FILE_MENU

    elif state == DOWNLOAD_FILE:
        c.execute("SELECT tg_file_id FROM files WHERE id=? AND user_id=?", (msg, uid))
        r = c.fetchone()
        if r:
            await context.bot.send_document(uid, r[0])
        else:
            await update.message.reply_text("❌ غير موجود")
        STATE[uid] = FILE_MENU

    # ===== IMAGE ACTIONS =====
    elif state == MOVE_IMAGE:
        iid, fname = msg.split(maxsplit=1)
        folder = get_folder_id(uid, fname)
        if folder:
            c.execute("UPDATE images SET folder_id=? WHERE id=? AND user_id=?", (folder, iid, uid))
            db.commit()
            await update.message.reply_text("📤 تم النقل")
        else:
            await update.message.reply_text("❌ المجلد غير موجود")
        STATE[uid] = IMAGE_MENU

    elif state == DEL_IMAGE:
        c.execute("DELETE FROM images WHERE id=? AND user_id=?", (msg, uid))
        db.commit()
        await update.message.reply_text("🗑️ تم حذف الصورة")
        STATE[uid] = IMAGE_MENU

    elif state == DOWNLOAD_IMAGE:
        c.execute("SELECT tg_file_id FROM images WHERE id=? AND user_id=?", (msg, uid))
        r = c.fetchone()
        if r:
            await context.bot.send_photo(uid, r[0])
        else:
            await update.message.reply_text("❌ غير موجود")
        STATE[uid] = IMAGE_MENU

    # ===== AI =====
    elif state == AI:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg}]
        )
        content = res.choices[0].message["content"]
        await update.message.reply_text(content)

# ================= FILE / IMAGE HANDLERS =================
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    folder = ensure_default_folder(uid)
    d = update.message.document
    c.execute(
        "INSERT INTO files(user_id,tg_file_id,name,folder_id) VALUES (?,?,?,?)",
        (uid, d.file_id, d.file_name, folder)
    )
    db.commit()
    await update.message.reply_text("📁 تم حفظ الملف")

async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    folder = ensure_default_folder(uid)
    p = update.message.photo[-1]
    name = f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    c.execute(
        "INSERT INTO images(user_id,tg_file_id,name,folder_id) VALUES (?,?,?,?)",
        (uid, p.file_id, name, folder)
    )
    db.commit()
    await update.message.reply_text("🖼️ تم حفظ الصورة")

# ================= RUN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    app.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    app.add
