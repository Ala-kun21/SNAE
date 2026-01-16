#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
import subprocess
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak
)
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
EMAIL = "ala.kun.1600@gmail.com"
PHONES = ["+249911032152", "+249119785938"]

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(FONT_DIR, exist_ok=True)

# =============================
# تحميل الخط إذا غير موجود
# =============================
if not os.path.isfile(FONT_PATH):
    os.system(
        f"wget https://noto-website-2.storage.googleapis.com/pkgs/NotoSans-unhinted.zip -O {FONT_DIR}/font.zip"
    )
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
# عرض الأعمدة محسّن (توسيع عمود id لتجنب الانكسار)
# =============================
def auto_column_widths(data, page_width):
    cols = len(data[0])
    max_lens = []
    for i in range(cols):
        max_len = max(len(str(row[i])) for row in data)
        # إذا العمود هو id (أول عمود)، زد العرض قليلاً
        if i == 0:
            max_len *= 2.0
        else:
            max_len *= 1.2
        max_lens.append(max_len)
    total = sum(max_lens) or cols
    widths = [(l / total) * page_width for l in max_lens]
    return widths

# =============================
# بناء جدول منسق
# =============================
def build_table(data, page_width):
    table = Table(
        data,
        colWidths=auto_column_widths(data, page_width),
        repeatRows=1
    )

    style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, 0), 16),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 1), (-1, -1), 12)
    ])

    table.setStyle(style)
    return table

# =============================
# Header / Footer
# =============================
def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 9)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        40, 25,
        f"{OWNER_NAME} | {EMAIL} | {' - '.join(PHONES)}"
    )
    canvas.drawRightString(
        A4[0] - 40, 25,
        f"Page {doc.page}"
    )
    canvas.restoreState()

# =============================
# إنشاء PDF لكل جدول
# =============================
def create_pdf(tables):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    page_width = A4[0] - 60

    for name in tables:
        cur.execute(f"PRAGMA table_info({name})")
        cols = [clean(c[1]) for c in cur.fetchall()]

        cur.execute(f"SELECT * FROM {name}")
        rows = cur.fetchall()

        data = [cols] + [[clean(v) for v in r] for r in rows]

        pdf_path = os.path.join(
            PDF_DIR,
            f"SultanAE_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=70,
            bottomMargin=50
        )

        elements = []

        # ===== Title: Sultan AE : Table name =====
        elements.append(Paragraph(
            f'<font size=26 color="#1e40af">{OWNER_NAME}</font> : '
            f'<font size=18 color="#1e40af">{name}</font>',
            ParagraphStyle(
                "title",
                fontName=FONT_NAME,
                alignment=1,
                spaceAfter=25
            )
        ))

        # Subtitle: Bot Name & Report Date
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Bot Name: {BOT_NAME} | Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ParagraphStyle(
                "sub",
                fontName=FONT_NAME,
                fontSize=12,
                alignment=1,
                spaceAfter=20
            )
        ))

        # Table
        elements.append(build_table(data, page_width))
        elements.append(PageBreak())

        doc.build(elements, onFirstPage=header_footer, onLaterPages=header_footer)

        subprocess.run(["rclone", "copy", pdf_path, RCLONE_REMOTE])
        print(f"[OK] PDF CREATED → {pdf_path}")

    conn.close()

# =============================
# تشغيل
# =============================
tables_needed = ["phones", "sqlite_sequence"]  # حذف folders
create_pdf(tables_needed)
