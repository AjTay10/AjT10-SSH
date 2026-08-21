#!/usr/bin/env python3
"""Build The Budget Reset — a 14-page printable budget & debt payoff planner.

Usage:
    python3 generate_planner.py [out.pdf]

Requires reportlab (the one deliberate exception to this repo's stdlib-only
rule: this is a product build script, not a tools/ utility, and the built
PDF is committed so nobody needs to re-run it).
"""

import sys

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

W, H = letter
MARGIN = 54
INNER_W = W - 2 * MARGIN

ACCENT = HexColor("#0E5E56")
ACCENT_SOFT = HexColor("#E3EEEC")
INK = HexColor("#26241F")
SOFT = HexColor("#8A857B")
LINE = HexColor("#D9D3C7")
FILL = HexColor("#F5F1E9")


def header(c, kicker, title, note=""):
    """Standard page header; returns the y where content may start."""
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN, H - 56, kicker.upper())
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGIN, H - 80, title)
    if note:
        c.setFillColor(SOFT)
        c.setFont("Helvetica", 9)
        c.drawRightString(W - MARGIN, H - 80, note)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(2)
    c.line(MARGIN, H - 92, MARGIN + 42, H - 92)
    return H - 116


def footer(c, page_label):
    c.setFillColor(SOFT)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGIN, 40, "THE BUDGET RESET")
    c.drawRightString(W - MARGIN, 40, page_label)


def section_label(c, x, y, text):
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x, y, text.upper())
    return y - 14


def table(c, x, y, widths, n_rows, headers=None, row_h=20, shade_header=True):
    """Draw a ruled table top-down from y; returns y below the table."""
    total_w = sum(widths)
    top = y
    if headers:
        if shade_header:
            c.setFillColor(FILL)
            c.rect(x, top - row_h, total_w, row_h, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8)
        cx = x
        for wd, htext in zip(widths, headers):
            c.drawString(cx + 6, top - row_h + 6.5, htext.upper())
            cx += wd
        top -= row_h
    bottom = top - n_rows * row_h
    c.setStrokeColor(LINE)
    c.setLineWidth(0.75)
    for i in range(n_rows + 1):
        yy = top - i * row_h
        c.line(x, yy, x + total_w, yy)
    cx = x
    table_top = y if headers else top
    for wd in widths[:-1]:
        cx += wd
        c.line(cx, table_top, cx, bottom)
    c.rect(x, bottom, total_w, table_top - bottom, stroke=1, fill=0)
    return bottom


def write_lines(c, x, y, lines, size=9.5, leading=15, color=INK, font="Helvetica"):
    c.setFillColor(color)
    c.setFont(font, size)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    return y


def checkbox(c, x, y, size=9):
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.9)
    c.rect(x, y, size, size, stroke=1, fill=0)


def summary_box(c, x, y, w, h, title, rows):
    c.setFillColor(ACCENT_SOFT)
    c.rect(x, y - h, w, h, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x + 12, y - 20, title.upper())
    yy = y - 42
    for label in rows:
        c.setFillColor(INK)
        c.setFont("Helvetica", 9.5)
        c.drawString(x + 12, yy, label)
        c.setStrokeColor(SOFT)
        c.setLineWidth(0.75)
        c.line(x + w * 0.55, yy - 2, x + w - 12, yy - 2)
        yy -= 22


# ---------------------------------------------------------------- pages


def p01_cover(c):
    c.setFillColor(HexColor("#FBF9F4"))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.rect(0, H - 26, W, 26, stroke=0, fill=1)
    c.rect(0, 0, W, 26, stroke=0, fill=1)
    # concentric-arc motif
    c.setStrokeColor(ACCENT)
    cx, cy = W / 2, H - 300
    for i, r in enumerate(range(30, 111, 20)):
        c.setLineWidth(2.2 - i * 0.35)
        c.arc(cx - r, cy - r, cx + r, cy + r, 200, 140)
    c.setFillColor(ACCENT)
    c.circle(cx, cy, 7, stroke=0, fill=1)
    c.setFillColor(SOFT)
    c.setFont("Helvetica-Bold", 11)
    t = "A  1 2 - M O N T H   M O N E Y   S Y S T E M"
    c.drawCentredString(W / 2, H - 430, t)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(W / 2, H - 480, "THE BUDGET RESET")
    c.setFillColor(SOFT)
    c.setFont("Helvetica", 13)
    c.drawCentredString(W / 2, H - 508, "Budget  ·  Debt Payoff  ·  Savings  —  Undated Printable Planner")
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(W / 2 - 90, H - 540, W / 2 + 90, H - 540)
    c.setFillColor(SOFT)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, 60, "US Letter  ·  Print at 100% scale  ·  Reprint any page as often as you need")


def p02_welcome(c):
    y = header(c, "Start here", "How This Planner Works")
    intro = [
        "This planner is a system, not a diary. It runs on one monthly ritual and three",
        "habits. Every page is undated, so print what you need, when you need it —",
        "the Monthly Budget and Expense Log pages are designed to be printed twelve",
        "times each. Nothing here requires an app, a spreadsheet, or a subscription.",
    ]
    y = write_lines(c, MARGIN, y, intro, size=10.5, leading=17)
    y -= 14
    steps = [
        ("1", "Take the snapshot", "Fill in the Money Snapshot once. It is your before photo — be honest, not optimistic."),
        ("2", "Budget monthly", "On the last weekend of each month, print a fresh Monthly Budget page and give every dollar a job."),
        ("3", "Log as you spend", "Keep the Expense Log where you will see it. A budget you never check against reality is a wish."),
        ("4", "Attack one debt", "List every debt, order them smallest to largest, and aim every spare dollar at the first one only."),
    ]
    for num, title, body in steps:
        c.setFillColor(ACCENT)
        c.circle(MARGIN + 10, y - 2, 10, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(MARGIN + 10, y - 5.5, num)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(MARGIN + 30, y - 2, title)
        c.setFillColor(SOFT)
        c.setFont("Helvetica", 9.5)
        c.drawString(MARGIN + 30, y - 17, body)
        y -= 46
    y -= 8
    c.setFillColor(FILL)
    c.rect(MARGIN, y - 96, INNER_W, 96, stroke=0, fill=1)
    write_lines(
        c, MARGIN + 16, y - 26,
        [
            "The one rule that makes this work:",
            "",
            "When you blow the budget — and some month you will — you do not quit,",
            "and you do not wait for January. You print a fresh page and start the next",
            "month clean. Consistency beats perfection by a very wide margin.",
        ],
        size=10, leading=15.5,
    )
    footer(c, "01 · START HERE")


def p03_snapshot(c):
    y = header(c, "Once, at the start", "Money Snapshot", "Date: ______________")
    y = section_label(c, MARGIN, y, "Where the money comes from")
    y = table(c, MARGIN, y, [INNER_W * 0.62, INNER_W * 0.38], 4,
              headers=["Income source", "Monthly amount (after tax)"])
    y -= 24
    y = section_label(c, MARGIN, y, "What you own / what you owe")
    half = INNER_W / 2 - 10
    left_bottom = table(c, MARGIN, y, [half * 0.62, half * 0.38], 6,
                        headers=["Savings & assets", "Value"])
    table(c, MARGIN + half + 20, y, [half * 0.62, half * 0.38], 6,
          headers=["Debts (all of them)", "Balance"])
    y = left_bottom - 24
    summary_box(c, MARGIN, y, INNER_W, 78, "The starting line", [])
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    third = INNER_W / 3
    for i, label in enumerate(["Total monthly income", "Total debt", "Total savings"]):
        x = MARGIN + 14 + i * third
        c.drawString(x, y - 44, label)
        c.setStrokeColor(SOFT)
        c.line(x, y - 62, x + third - 40, y - 62)
    y -= 100
    y = section_label(c, MARGIN, y, "Three things that will be true a year from now")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.75)
    for i in range(3):
        c.setFillColor(SOFT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN, y - 6, f"{i + 1}.")
        c.line(MARGIN + 18, y - 8, W - MARGIN, y - 8)
        y -= 28
    footer(c, "02 · SNAPSHOT")


def p04_monthly_budget(c):
    y = header(c, "Print one per month", "Monthly Budget", "Month: ______________")
    y = section_label(c, MARGIN, y, "Income")
    y = table(c, MARGIN, y, [INNER_W * 0.62, INNER_W * 0.19, INNER_W * 0.19], 3,
              headers=["Source", "Expected", "Actual"], row_h=17)
    y -= 18
    y = section_label(c, MARGIN, y, "Fixed expenses  ·  rent, utilities, insurance, minimum payments")
    y = table(c, MARGIN, y, [INNER_W * 0.43, INNER_W * 0.19, INNER_W * 0.19, INNER_W * 0.19], 9,
              headers=["Expense", "Planned", "Actual", "+ / –"], row_h=17)
    y -= 18
    y = section_label(c, MARGIN, y, "Variable spending  ·  groceries, gas, fun, everything else")
    y = table(c, MARGIN, y, [INNER_W * 0.43, INNER_W * 0.19, INNER_W * 0.19, INNER_W * 0.19], 7,
              headers=["Category", "Planned", "Actual", "+ / –"], row_h=17)
    y -= 20
    box_h = 64
    c.setFillColor(ACCENT)
    c.rect(MARGIN, y - box_h, INNER_W, box_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    third = INNER_W / 3
    for i, label in enumerate(["TOTAL IN", "TOTAL OUT", "LEFT OVER  →  GOALS"]):
        x = MARGIN + 14 + i * third
        c.drawString(x, y - 24, label)
        c.setStrokeColor(white)
        c.setLineWidth(0.9)
        c.line(x, y - 48, x + third - 40, y - 48)
    footer(c, "03 · MONTHLY BUDGET")


def p05_bill_tracker(c):
    y = header(c, "Fill once, tick monthly", "Bill Payment Tracker", "Year: ________")
    y = write_lines(c, MARGIN, y, [
        "List every recurring bill with its due day, then tick the month box when it is paid.",
        "One glance tells you what is still outstanding — no more late fees.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 10
    months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    name_w, due_w, amt_w = 150, 40, 62
    cell = (INNER_W - name_w - due_w - amt_w) / 12
    widths = [name_w, due_w, amt_w] + [cell] * 12
    table(c, MARGIN, y, widths, 18, headers=["Bill", "Due", "Amount"] + months, row_h=22)
    footer(c, "04 · BILL TRACKER")


def p06_expense_log(c):
    y = header(c, "Print one per month", "Expense Log", "Month: ______________")
    y = write_lines(c, MARGIN, y, [
        "Every purchase gets a line, same day it happens. This page is the difference",
        "between a budget and a guess.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 10
    y = table(c, MARGIN, y,
              [INNER_W * 0.12, INNER_W * 0.46, INNER_W * 0.24, INNER_W * 0.18], 27,
              headers=["Date", "What", "Category", "Amount"], row_h=18)
    y -= 4
    c.setFillColor(FILL)
    c.rect(MARGIN, y - 26, INNER_W, 26, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN + 8, y - 17, "MONTH TOTAL")
    c.setStrokeColor(SOFT)
    c.line(W - MARGIN - INNER_W * 0.16, y - 19, W - MARGIN - 8, y - 19)
    footer(c, "05 · EXPENSE LOG")


def p07_debt_inventory(c):
    y = header(c, "The honest list", "Debt Inventory", "Date: ______________")
    y = write_lines(c, MARGIN, y, [
        "Every debt goes on this page — cards, loans, car, medical, the one you would",
        "rather not write down. You cannot pay off a number you refuse to look at.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 10
    y = table(c, MARGIN, y,
              [INNER_W * 0.30, INNER_W * 0.18, INNER_W * 0.12, INNER_W * 0.16,
               INNER_W * 0.12, INNER_W * 0.12], 12,
              headers=["Owed to", "Balance", "APR %", "Min / month", "Due day", "Payoff #"],
              row_h=24)
    y -= 22
    summary_box(c, MARGIN, y, INNER_W * 0.55, 84, "Totals",
                ["Total owed", "Total minimums / month"])
    write_lines(
        c, MARGIN + INNER_W * 0.60, y - 22,
        ["“Payoff #” is the order you will",
         "attack them — smallest balance",
         "first. Rank them on the next page."],
        size=9.5, leading=14, color=SOFT,
    )
    footer(c, "06 · DEBT INVENTORY")


def p08_snowball(c):
    y = header(c, "The method", "Debt Snowball Plan")
    y = write_lines(c, MARGIN, y, [
        "Order your debts smallest balance to largest. Pay minimums on everything,",
        "then aim every spare dollar at debt #1. When it dies, its whole payment rolls",
        "into debt #2 — the snowball. Momentum is the strategy: quick wins keep you in",
        "the game long enough for the math to work.",
    ], size=10, leading=15.5)
    y -= 12
    y = table(c, MARGIN, y,
              [INNER_W * 0.08, INNER_W * 0.34, INNER_W * 0.19, INNER_W * 0.19, INNER_W * 0.20], 8,
              headers=["#", "Debt", "Balance", "Payment", "Paid off (date)"], row_h=24)
    y -= 22
    c.setFillColor(ACCENT_SOFT)
    c.rect(MARGIN, y - 96, INNER_W, 96, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGIN + 14, y - 22, "THIS MONTH'S TARGET")
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN + 14, y - 46, "Focus debt:")
    c.drawString(MARGIN + 14, y - 72, "Extra I will throw at it this month:  $")
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.75)
    c.line(MARGIN + 74, y - 48, MARGIN + INNER_W - 20, y - 48)
    c.line(MARGIN + 196, y - 74, MARGIN + INNER_W * 0.6, y - 74)
    footer(c, "07 · SNOWBALL PLAN")


def p09_payoff_tracker(c):
    y = header(c, "Color it in", "Debt Payoff Tracker", "One row per debt")
    y = write_lines(c, MARGIN, y, [
        "Each bar is one debt. Split it into ten equal chunks of the starting balance and",
        "shade a segment every time you knock out a chunk. Stick it on the fridge —",
        "visible progress is what keeps a payoff alive in month seven.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 14
    seg_w = INNER_W / 10
    for row in range(8):
        c.setFillColor(INK)
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN, y - 2, "Debt:")
        c.setStrokeColor(SOFT)
        c.setLineWidth(0.75)
        c.line(MARGIN + 30, y - 4, MARGIN + 240, y - 4)
        c.drawRightString(W - MARGIN - 100, y - 2, "Starting balance:")
        c.line(W - MARGIN - 96, y - 4, W - MARGIN, y - 4)
        bar_y = y - 34
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1)
        for s in range(10):
            c.rect(MARGIN + s * seg_w, bar_y, seg_w, 22, stroke=1, fill=0)
        y -= 72
    footer(c, "08 · PAYOFF TRACKER")


def p10_sinking_funds(c):
    y = header(c, "Expected surprises", "Sinking Funds", "Save small, monthly")
    y = write_lines(c, MARGIN, y, [
        "Christmas, car repairs, and annual insurance are not emergencies — they are",
        "scheduled. Give each one a fund, set aside a little every month, and tick the",
        "month when you have funded it.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 12
    months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    box_w = INNER_W / 2 - 8
    box_h = 128
    for i in range(6):
        col, row = i % 2, i // 2
        x = MARGIN + col * (box_w + 16)
        top = y - row * (box_h + 16)
        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.setFillColor(white)
        c.rect(x, top - box_h, box_w, box_h, stroke=1, fill=1)
        c.setFillColor(FILL)
        c.rect(x, top - 24, box_w, 24, stroke=0, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 8, top - 16, "FUND:")
        c.setStrokeColor(SOFT)
        c.setLineWidth(0.75)
        c.line(x + 42, top - 18, x + box_w - 8, top - 18)
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 8, top - 42, "Goal:  $")
        c.line(x + 42, top - 44, x + box_w * 0.5, top - 44)
        c.drawString(x + box_w * 0.55, top - 42, "Monthly:  $")
        c.line(x + box_w * 0.55 + 44, top - 44, x + box_w - 8, top - 44)
        cell = (box_w - 16) / 12
        for m, label in enumerate(months):
            mx = x + 8 + m * cell
            checkbox(c, mx + cell / 2 - 4.5, top - 78, 9)
            c.setFillColor(SOFT)
            c.setFont("Helvetica", 6.5)
            c.drawCentredString(mx + cell / 2, top - 90, label)
        c.setFillColor(INK)
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 8, top - 112, "Saved so far:  $")
        c.setStrokeColor(SOFT)
        c.line(x + 74, top - 114, x + box_w - 8, top - 114)
    footer(c, "09 · SINKING FUNDS")


def p11_savings_goal(c):
    y = header(c, "One big goal", "Savings Goal Tracker")
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN, y - 4, "I am saving for:")
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.75)
    c.line(MARGIN + 80, y - 6, W - MARGIN - 170, y - 6)
    c.drawString(W - MARGIN - 160, y - 4, "Target:  $")
    c.line(W - MARGIN - 112, y - 6, W - MARGIN, y - 6)
    y -= 36
    y = section_label(c, MARGIN, y, "Shade one block per 5% saved")
    block_w = (INNER_W - 19 * 4) / 20
    for i in range(20):
        x = MARGIN + i * (block_w + 4)
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1)
        c.rect(x, y - 30, block_w, 26, stroke=1, fill=0)
        if (i + 1) % 5 == 0:
            c.setFillColor(SOFT)
            c.setFont("Helvetica", 7)
            c.drawCentredString(x + block_w / 2, y - 42, f"{(i + 1) * 5}%")
    y -= 66
    y = section_label(c, MARGIN, y, "Deposits")
    y = table(c, MARGIN, y,
              [INNER_W * 0.16, INNER_W * 0.40, INNER_W * 0.22, INNER_W * 0.22], 14,
              headers=["Date", "Where it came from", "Amount", "New total"], row_h=20)
    footer(c, "10 · SAVINGS GOAL")


def p12_subscription_audit(c):
    y = header(c, "The quiet leak", "Subscription Audit", "Do this twice a year")
    y = write_lines(c, MARGIN, y, [
        "Go through your last two bank statements and list every recurring charge —",
        "streaming, apps, memberships, the gym you have not visited since March.",
        "Then decide, line by line: keep it or cancel it. Most households find real money here.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 10
    y = table(c, MARGIN, y,
              [INNER_W * 0.34, INNER_W * 0.16, INNER_W * 0.16, INNER_W * 0.10,
               INNER_W * 0.10, INNER_W * 0.14], 15,
              headers=["Service", "$ / month", "$ / year", "Keep", "Cancel", "Cancelled on"],
              row_h=21)
    y -= 20
    c.setFillColor(ACCENT)
    c.rect(MARGIN, y - 52, INNER_W, 52, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 14, y - 31, "FOUND MONEY  —  total yearly cost of everything cancelled:   $")
    c.setStrokeColor(white)
    c.setLineWidth(1)
    c.line(MARGIN + 356, y - 34, W - MARGIN - 20, y - 34)
    footer(c, "11 · SUBSCRIPTION AUDIT")


def p13_no_spend(c):
    y = header(c, "The circuit breaker", "30-Day No-Spend Challenge")
    y = write_lines(c, MARGIN, y, [
        "For thirty days, nothing but the essentials you define below. Mark every clean",
        "day. A no-spend month will not fix your finances — it exists to show you how",
        "much of your spending is habit rather than need.",
    ], size=9.5, leading=14, color=SOFT)
    y -= 8
    c.setFillColor(INK)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN, y - 4, "Allowed essentials:")
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.75)
    c.line(MARGIN + 92, y - 6, W - MARGIN, y - 6)
    c.line(MARGIN, y - 26, W - MARGIN, y - 26)
    y -= 52
    cell = INNER_W / 6
    for d in range(30):
        col, row = d % 6, d // 6
        cx = MARGIN + col * cell + cell / 2
        cy = y - row * 74 - 24
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.4)
        c.circle(cx, cy, 22, stroke=1, fill=0)
        c.setFillColor(SOFT)
        c.setFont("Helvetica", 8)
        c.drawCentredString(cx, cy + 30, f"DAY {d + 1}")
    y -= 5 * 74 + 16
    c.setFillColor(INK)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN, y, "What I did not buy, and what that tells me:")
    c.setStrokeColor(LINE)
    for i in range(2):
        c.line(MARGIN, y - 20 - i * 20, W - MARGIN, y - 20 - i * 20)
    footer(c, "12 · NO-SPEND CHALLENGE")


def p14_review(c):
    y = header(c, "Twelve months later", "Year in Review", "Date: ______________")
    y = section_label(c, MARGIN, y, "The before and after")
    y = table(c, MARGIN, y,
              [INNER_W * 0.40, INNER_W * 0.20, INNER_W * 0.20, INNER_W * 0.20], 4,
              headers=["", "Snapshot", "Today", "Change"], row_h=26)
    c.setFillColor(INK)
    c.setFont("Helvetica", 9.5)
    labels = ["Total debt", "Total savings", "Monthly income", "Subscriptions / month"]
    for i, label in enumerate(labels):
        c.drawString(MARGIN + 8, y + (4 - i) * 26 - 17, label)
    y -= 26
    y = section_label(c, MARGIN, y, "Three wins worth remembering")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.75)
    for i in range(3):
        c.setFillColor(SOFT)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(MARGIN, y - 6, f"{i + 1}.")
        c.line(MARGIN + 18, y - 8, W - MARGIN, y - 8)
        y -= 26
    y -= 12
    y = section_label(c, MARGIN, y, "What broke, and what I will do differently")
    for i in range(3):
        c.line(MARGIN, y - 8, W - MARGIN, y - 8)
        y -= 24
    y -= 16
    c.setFillColor(ACCENT_SOFT)
    c.rect(MARGIN, y - 88, INNER_W, 88, stroke=0, fill=1)
    write_lines(
        c, MARGIN + 16, y - 26,
        [
            "Next year's single financial priority:",
            "",
            "",
        ],
        size=10, leading=16, font="Helvetica-Bold",
    )
    c.setStrokeColor(SOFT)
    c.setLineWidth(0.75)
    c.line(MARGIN + 16, y - 58, W - MARGIN - 16, y - 58)
    footer(c, "13 · YEAR IN REVIEW")


PAGES = [
    p01_cover, p02_welcome, p03_snapshot, p04_monthly_budget, p05_bill_tracker,
    p06_expense_log, p07_debt_inventory, p08_snowball, p09_payoff_tracker,
    p10_sinking_funds, p11_savings_goal, p12_subscription_audit, p13_no_spend,
    p14_review,
]


def build(out_path):
    c = canvas.Canvas(out_path, pagesize=letter)
    c.setTitle("The Budget Reset — Budget & Debt Payoff Planner")
    c.setAuthor("The Budget Reset")
    c.setSubject("Undated printable budget, debt payoff, and savings planner")
    for draw in PAGES:
        draw(c)
        c.showPage()
    c.save()
    print(f"wrote {out_path} ({len(PAGES)} pages)")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "The-Budget-Reset-Planner.pdf")
