#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import subprocess
from datetime import datetime
import smtplib
from email.message import EmailMessage
import asyncio
from telegram import Bot
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import ParagraphStyle

# =============================
# إعدادات أساسية
# =============================
DB_PATH = "bot.db"
PDF_DIR = "backups"
RCLONE_REMOTE = "SNAE:TelegramBackups"

FONT_DIR = "fonts"
FONT_FILE = "NotoSans-Regular.ttf"
FONT_PATH = os.path.join(FONT_DIR, FONT_FILE)
FONT_NAME = "NotoSans"

OWNER_NAME = "Sultan AE"
BOT_NAME = "SNAE"
PHONES = ["+249911032152", "+249119785938"]

# تيليجرام
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = 6452610519  # ضع chat_id الخاص بك

# البريد الإلكتروني
EMAIL_FROM = "toya.san.13@gmail.com"
EMAIL_TO   = "ala.kun.1600@gmail.com"
EMAIL_APP_PASSWORD = ""  # كلمة مرور التطبيقات

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

# =============================
# تحميل الخط إذا غير موجود
# =============================
if not os.path.isfile(FONT_PATH):
    os.system(f"wget https://noto-website-2.storage.googleapis.com/pkgs/NotoSans-unhinted.zip -O {FONT_DIR}/font.zip")
    os.system(f"unzip -o {FONT_DIR}/font.zip -d {FONT_DIR}")
    os.system(f"mv {FONT_DIR}/NotoSans-Regular.ttf {FONT_PATH}")
    os.system(f"rm {FONT_DIR}/font.zip")

pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

# =============================
# تنظيف النصوص من None
# =============================
def clean(text):
    if text is None:
        return ""
    return str(text)

# =============================
# إعداد جدول PDF
# =============================
def auto_column_widths(data, page_width):
    cols = len(data[0])
    max_lens = []
    for i in range(cols):
        max_len = max(len(str(row[i])) for row in data)
        if i == 0:  # العمود الأول id
            max_len *= 2.5
        else:
            max_len *= 1.2
        max_lens.append(max_len)
    total = sum(max_lens) or cols
    widths = [(l / total) * page_width for l in max_lens]
    return widths

def build_table(data, page_width):
    table = Table(data, colWidths=auto_column_widths(data, page_width), repeatRows=1)
    style = TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, (0.5,0.5,0.5)),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,0), (0.95,0.95,0.95)),
        ('FONTNAME', (0,0), (-1,0), FONT_NAME),
        ('FONTSIZE', (0,0), (-1,0), 16),
        ('FONTNAME', (0,1), (-1,-1), FONT_NAME),
        ('FONTSIZE', (0,1), (-1,-1), 12),
    ])
    table.setStyle(style)
    return table

# =============================
# Header/Footer PDF
# =============================
def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 9)
    canvas.drawString(40, 25, f"{OWNER_NAME} | {' - '.join(PHONES)}")
    canvas.drawRightString(A4[0]-40, 25, f"Page {doc.page}")
    canvas.restoreState()

# =============================
# التحقق من البيانات الجديدة
# =============================
def check_new_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables = ["phones", "sqlite_sequence"]

    new_data_found = False
    for t in tables:
        cur.execute(f"SELECT MAX(rowid) FROM {t}")
        last = cur.fetchone()[0] or 0

        state_file = f"{t}_last.txt"
        last_saved = int(open(state_file).read().strip()) if os.path.isfile(state_file) else 0

        if last > last_saved:
            new_data_found = True
            with open(state_file, 'w') as f:
                f.write(str(last))
    conn.close()
    return new_data_found

# =============================
# إنشاء PDF
# =============================
def create_pdf(new_data=True):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    page_width = A4[0]-60
    pdf_paths = []

    tables = ["phones", "sqlite_sequence"]
    status_msg = "تم تحديث بيانات" if new_data else "لم يتم تحديث قاعدة بيانات يا سيدي"

    for name in tables:
        cur.execute(f"PRAGMA table_info({name})")
        cols = [clean(c[1]) for c in cur.fetchall()]

        cur.execute(f"SELECT * FROM {name}")
        rows = cur.fetchall()
        data = [cols] + [[clean(v) for v in r] for r in rows]

        pdf_path = os.path.join(PDF_DIR, f"DailyReport_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf_paths.append(pdf_path)

        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=70, bottomMargin=50)
        elements = []
        elements.append(Paragraph(f'<font size=26 color="#1e40af">{OWNER_NAME}</font> : <font size=18 color="#1e40af">{name}</font>',
                                  ParagraphStyle("title", fontName=FONT_NAME, alignment=1, spaceAfter=25)))
        elements.append(Spacer(1,20))
        elements.append(Paragraph(f"Bot Name: {BOT_NAME} | Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {status_msg}",
                                  ParagraphStyle("sub", fontName=FONT_NAME, fontSize=12, alignment=1, spaceAfter=20)))
        elements.append(build_table(data, page_width))
        elements.append(PageBreak())
        doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)

        subprocess.run(["rclone", "copy", pdf_path, RCLONE_REMOTE])
        print(f"[OK] PDF CREATED → {pdf_path}")

    conn.close()
    return pdf_paths, status_msg

# =============================
# إرسال بريد إلكتروني
# =============================
def send_email(pdf_paths, status_msg):
    msg = EmailMessage()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO
    msg['Subject'] = f"تقرير يومي - {BOT_NAME}"
    msg.set_content(f"{status_msg}\n\nتوقيع البوت: {BOT_NAME}")

    for pdf in pdf_paths:
        with open(pdf,'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)
        print("[OK] Email sent successfully.")

# =============================
# إرسال رسالة تيليجرام (بدون تحذير asyncio)
# =============================
def send_telegram_message(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    asyncio.run(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))

# =============================
# المهمة اليومية
# =============================
def daily_report():
    new_data = check_new_data()
    pdf_paths, status_msg = create_pdf(new_data)
    send_email(pdf_paths, status_msg)
    send_telegram_message(f"تم ارسال تقرير يومي يا سيد {OWNER_NAME}\n{status_msg}")

# =============================
# تشغيل مرة واحدة للتجربة أو Cron
# =============================
if __name__ == "__main__":
    daily_report()
