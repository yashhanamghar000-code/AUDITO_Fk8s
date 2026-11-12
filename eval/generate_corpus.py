"""Generate the synthetic evaluation corpus (fictional companies/policies - no real data).

Usage:  python generate_corpus.py <output_dir>

Every fact is deliberately unique so a correct answer can only come from the
documents. Documents are designed to exercise: single-page facts, tables,
multi-page procedures, version conflicts across documents, calculations,
long documents, scanned (image-only, OCR) pages and cross-user isolation.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

S = getSampleStyleSheet()
H1, H2, P = S["Heading1"], S["Heading2"], S["BodyText"]


def table(rows, widths=None):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ]))
    return t


def build(path, pages):
    """pages: list of lists of flowables; each inner list is one page."""
    doc = SimpleDocTemplate(path, pagesize=A4, title=os.path.basename(path))
    story = []
    for i, flow in enumerate(pages):
        story.extend(flow)
        if i < len(pages) - 1:
            story.append(PageBreak())
    doc.build(story)


def zorblax_2025(out):
    build(os.path.join(out, "Zorblax_Annual_Report_FY2025.pdf"), [
        [Paragraph("Zorblax Industries Limited - Annual Report FY2025", H1),
         Paragraph("Company Overview", H2),
         Paragraph("Zorblax Industries Limited manufactures industrial valves and precision pumps. Its headquarters are located in Pune, Maharashtra, "
                   "to which the company relocated in March 2025. The Chief Executive Officer is Meera Kulkarni, appointed in March 2022. "
                   "The Chief Financial Officer is Arjun Deshpande.", P)],
        [Paragraph("Financial Summary FY2025", H2),
         Paragraph("The table below summarises audited results for the fiscal year ended 31 March 2025 (amounts in INR crore).", P),
         Spacer(1, 8),
         table([["Metric", "FY2025", "FY2024"],
                ["Total revenue", "482", "430"],
                ["Operating profit", "96", "81"],
                ["Net profit", "61", "54"],
                ["Capital expenditure", "38", "29"]]),
         Spacer(1, 8),
         Paragraph("Net profit rose by approximately 12 percent over fiscal 2024, driven mainly by the Valves segment.", P)],
        [Paragraph("Business Segments", H2),
         Paragraph("Zorblax reports three segments. The Valves segment contributed 58 percent of FY2025 revenue (about 280 crore). "
                   "The Pumps segment contributed 31 percent (about 149 crore). The Services segment contributed the remaining 11 percent (about 53 crore). "
                   "The Valves segment's largest customer is Helios Energy.", P)],
        [Paragraph("Principal Risk Factors", H2),
         Paragraph("1. Raw material price volatility: steel and nickel account for 44 percent of the cost of goods sold.", P),
         Paragraph("2. Customer concentration: the top three customers represent 39 percent of revenue.", P),
         Paragraph("3. Currency exposure: 22 percent of revenue is invoiced in euros.", P),
         Paragraph("4. Regulatory change: new pressure-vessel safety norms take effect on 1 January 2026.", P),
         Paragraph("5. Supply disruption: the sole supplier of forged castings is located in Rajkot.", P)],
        [Paragraph("Workforce and Sustainability", H2),
         Paragraph("At the end of fiscal 2025 Zorblax employed 3,150 people across 7 manufacturing plants in India. "
                   "The company targets a 35 percent reduction in Scope 1 and 2 emissions by 2030 against a 2023 baseline, "
                   "and plans to source 60 percent of its electricity from renewables by 2028.", P)],
        [Paragraph("Auditor's Report", H2),
         Paragraph("The statutory auditor for fiscal 2025 was Deshmukh and Partners LLP. The auditor issued an unmodified opinion dated 14 May 2025. "
                   "The Annual General Meeting is scheduled for 19 August 2025.", P)],
    ])


def zorblax_2024(out):
    build(os.path.join(out, "Zorblax_Annual_Report_FY2024.pdf"), [
        [Paragraph("Zorblax Industries Limited - Annual Report FY2024", H1),
         Paragraph("Company Overview", H2),
         Paragraph("Zorblax Industries Limited manufactures industrial valves and precision pumps. Its headquarters during fiscal 2024 were located in Mumbai, Maharashtra. "
                   "The Chief Executive Officer is Meera Kulkarni. The Chief Financial Officer is Sanjay Rao.", P)],
        [Paragraph("Financial Summary FY2024", H2),
         table([["Metric", "FY2024", "FY2023"],
                ["Total revenue", "430", "391"],
                ["Net profit", "54", "47"]]),
         Spacer(1, 8),
         Paragraph("Total revenue for fiscal 2024 was 430 crore rupees.", P)],
        [Paragraph("Workforce", H2),
         Paragraph("At the end of fiscal 2024 Zorblax employed 2,900 people across 6 manufacturing plants in India. The statutory auditor for fiscal 2024 was Kapoor and Associates.", P)],
        [Paragraph("Dividend", H2),
         Paragraph("The board recommended a dividend of 3.50 rupees per share for fiscal 2024.", P)],
    ])


def leave_policy(out):
    build(os.path.join(out, "Employee_Leave_Policy.pdf"), [
        [Paragraph("Northwind Logistics - Employee Leave Policy", H1),
         Paragraph("1. Purpose and Scope", H2),
         Paragraph("This policy applies to all permanent employees of Northwind Logistics. Contract staff are governed by their individual agreements.", P)],
        [Paragraph("2. Annual Leave Entitlement", H2),
         table([["Service period", "Annual leave days"],
                ["Less than 2 years", "18"],
                ["2 to 5 years", "21"],
                ["More than 5 years", "24"]]),
         Spacer(1, 8),
         Paragraph("Leave accrues monthly. New joiners receive leave pro-rata from their date of joining.", P)],
        [Paragraph("3. Procedure to Apply for Planned Leave", H2),
         Paragraph("Step 1: The employee submits a leave request in the HR portal at least 10 working days before the first day of leave.", P),
         Paragraph("Step 2: The reporting manager reviews the request and must approve or reject it within 3 working days.", P),
         Paragraph("Step 3: If the leave exceeds 5 consecutive working days, the department head must also approve it.", P),
         Paragraph("Step 4: HR verifies the available balance and confirms the leave by email.", P),
         Paragraph("Step 5: The employee hands over pending work to a named colleague before departure.", P)],
        [Paragraph("4. Carry-Forward and Encashment", H2),
         Paragraph("Up to 12 unused leave days may be carried forward to the next calendar year. Carried-forward days expire on 31 March. "
                   "Encashment is permitted only on separation and only for a maximum of 30 days.", P),
         Paragraph("Exception: employees posted at the Leh depot may carry forward up to 15 days because of seasonal access restrictions.", P)],
        [Paragraph("5. Emergency and Medical Leave", H2),
         Paragraph("Emergency leave of up to 3 working days may be taken without prior approval, with intimation to the manager within 24 hours. "
                   "Medical leave beyond 2 consecutive days requires a certificate from a registered medical practitioner.", P)],
    ])


def helios_contract(out):
    build(os.path.join(out, "Vendor_Contract_Helios.pdf"), [
        [Paragraph("Master Supply Agreement - Helios Energy and Zorblax Industries", H1),
         Paragraph("Clause 1 - Term", H2),
         Paragraph("This Agreement commences on 1 April 2025 and continues for 36 months unless terminated earlier in accordance with Clause 6.", P)],
        [Paragraph("Clause 2 - Payment", H2),
         Paragraph("Helios shall pay each undisputed invoice within 45 days of the invoice date.", P),
         Paragraph("Clause 3 - Late Payment", H2),
         Paragraph("Late payments attract a penalty of 1.5 percent of the invoice value per month or part thereof of delay.", P)],
        [Paragraph("Clause 4 - Liability", H2),
         Paragraph("The aggregate liability of Zorblax under this Agreement is capped at 2 crore rupees.", P),
         Paragraph("Clause 5 - Confidentiality", H2),
         Paragraph("Each party shall keep confidential information secret for 5 years after termination.", P)],
        [Paragraph("Clause 6 - Termination", H2),
         Paragraph("Either party may terminate for convenience on 90 days written notice. Termination for material breach requires a 30 day cure period.", P)],
        [Paragraph("Clause 7 - Governing Law", H2),
         Paragraph("This Agreement is governed by the laws of India and the courts of Pune have exclusive jurisdiction.", P)],
    ])


def long_handbook(out):
    filler = ("The facility follows standard operating procedures that are reviewed periodically by the operations committee. "
              "Staff are expected to read the relevant sections before beginning work in a new area. ")
    pages = []
    for i in range(1, 41):
        flow = [Paragraph(f"Section {i}: Operating Guidelines", H2), Paragraph(filler * 6, P)]
        if i == 27:
            flow.append(Paragraph("The emergency assembly point for Building C is the northern car park, designated Zone Gamma-7.", P))
        if i == 38:
            flow.append(Paragraph("The fire marshal for night shifts is Priya Nambiar, reachable on extension 4417.", P))
        pages.append(flow)
    build(os.path.join(out, "Long_Facility_Handbook.pdf"), pages)


def scanned_page(out):
    """An image-only PDF page (no text layer) so only OCR can read it."""
    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype("arial.ttf", 54)
        mid = ImageFont.truetype("arial.ttf", 40)
    except Exception:
        big = mid = ImageFont.load_default()
    d.text((100, 120), "HEALTH ADVISORY NOTICE", fill="black", font=big)
    lines = ["The mandatory quarantine period for arriving staff is 14 days.",
             "Quarantine hotels are booked through the Kestrel Travel Desk.",
             "The advisory helpline number is 1800-555-0199.",
             "This notice was issued on 3 September 2025."]
    y = 280
    for ln in lines:
        d.text((100, y), ln, fill="black", font=mid)
        y += 110
    p = os.path.join(out, "Scanned_Health_Advisory.pdf")
    img.save(p, "PDF", resolution=150.0)


def user_b_secret(out):
    build(os.path.join(out, "UserB_Confidential.pdf"), [
        [Paragraph("Project Nightingale - Confidential Budget", H1),
         Paragraph("The approved budget for Project Nightingale is 77 crore rupees. The programme director is Ishaan Verma. "
                   "The launch codename is 'Blue Heron'.", P)],
    ])


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    os.makedirs(out, exist_ok=True)
    for fn in (zorblax_2025, zorblax_2024, leave_policy, helios_contract, long_handbook, scanned_page, user_b_secret):
        fn(out)
    print("generated:", sorted(os.listdir(out)))
