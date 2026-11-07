from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, abort
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from io import BytesIO
from database import get_db_connection, initialize_database
import re
import os
import secrets
import hmac
from datetime import datetime, date
import qrcode

app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production"
)

@app.context_processor
def inject_csrf_token():
    def csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return session["_csrf_token"]
    return {"csrf_token": csrf_token}

@app.before_request
def protect_post_requests():
    if request.method == "POST":
        submitted_token = request.form.get("_csrf_token", "")
        session_token = session.get("_csrf_token", "")
        if not submitted_token or not session_token or not hmac.compare_digest(
            submitted_token, session_token
        ):
            abort(400, description="Invalid or missing CSRF token.")

initialize_database()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about-us")
def about_us():
    return render_template("about-us.html")

@app.route("/academics")
def academics():
    return render_template("academics.html")

@app.route("/admissions", methods=["GET", "POST"])
def admissions():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        guardian_name = request.form.get("guardian_name", "").strip()
        address = request.form.get("address", "").strip()
        dob = request.form.get("dob", "").strip()
        applying_class = request.form.get("class", "").strip()
        student_phone = request.form.get("student_phone", "").strip()
        guardian_phone = request.form.get("guardian_phone", "").strip()
        student_email = request.form.get("student_email", "").strip()
        guardian_email = request.form.get("guardian_email", "").strip()
        if (
            not full_name
            or not guardian_name
            or not address
            or not dob
            or not applying_class
            or not guardian_phone
            or not guardian_email
        ):
            flash("Please fill in all required fields.", "error")
            return redirect(
                url_for("admissions") + "#application-section"
            )
        email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(email_pattern, guardian_email):
            flash(
                "Please enter a valid guardian email address.",
                "error"
            )
            return redirect(
                url_for("admissions") + "#application-section"
            )
        if student_email and not re.match(email_pattern, student_email):
            flash(
                "Please enter a valid student email address.",
                "error"
            )
            return redirect(
                url_for("admissions") + "#application-section"
            )
        phone_pattern = r"^[6-9][0-9]{9}$"
        if not re.match(phone_pattern, guardian_phone):
            flash(
                "Please enter a valid 10-digit guardian mobile number.",
                "error"
            )
            return redirect(
                url_for("admissions") + "#application-section"
            )
        if student_phone and not re.match(phone_pattern, student_phone):
            flash(
                "Please enter a valid 10-digit student mobile number.",
                "error"
            )
            return redirect(
                url_for("admissions") + "#application-section"
            )
        allowed_classes = {
            "play-group", "nursery", "lkg", "ukg",
            "class-1", "class-2", "class-3", "class-4", "class-5",
            "class-6", "class-7", "class-8", "class-9",
            "class-10", "class-11", "class-12"
        }
        try:
            birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            flash("Please enter a valid date of birth.", "error")
            return redirect(url_for("admissions") + "#application-section")

        if birth_date > date.today():
            flash("Date of birth cannot be in the future.", "error")
            return redirect(url_for("admissions") + "#application-section")

        if applying_class not in allowed_classes:
            flash("Please select a valid class.", "error")
            return redirect(url_for("admissions") + "#application-section")

        application_token = secrets.token_urlsafe(32)

        connection = get_db_connection()
        existing_application = connection.execute("""
            SELECT id
            FROM applications
            WHERE LOWER(full_name) = LOWER(?)
                AND dob = ?
                AND applying_class = ?
            LIMIT 1
        """, (
            full_name,
            dob,
            applying_class
        )).fetchone()
        if existing_application:
            connection.close()
            flash(
                "An application for this student has already been submitted.",
                "error"
            )
            return redirect(
                url_for("admissions") + "#application-section"
            )
        connection.execute("""
            INSERT INTO applications (
                full_name,
                guardian_name,
                address,
                dob,
                applying_class,
                student_phone,
                guardian_phone,
                student_email,
                guardian_email,
                public_token
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
                full_name,
                guardian_name,
                address,
                dob,
                applying_class,
                student_phone,
                guardian_phone,
                student_email,
                guardian_email,
                application_token
        ))
        connection.commit()
        application_id = connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]
        connection.close()
        session["application_token"] = application_token
        flash(
            "Your admission application has been submitted successfully!",
            "success"
        )
        return redirect(
            url_for("admissions") + "#application-section"
        )
    return render_template("admissions.html")

@app.route("/application-acknowledgement/<token>")
def application_acknowledgement(token):
    connection = get_db_connection()
    application = connection.execute("""
        SELECT *
        FROM applications
        WHERE public_token = ?
    """, (token,)).fetchone()
    connection.close()
    if not application:
        flash("Application acknowledgement could not be found.", "error")
        return redirect(url_for("admissions") + "#application-section")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        leading=24,
        spaceAfter=8,
        textColor=colors.HexColor("#003366")
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=12,
        leading=16,
        spaceAfter=18
    )
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontSize=11,
        leading=15
    )
    def format_pdf_text(value, style=normal_style):
        text = str(value or "Not provided")
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = escape(text)
        text = text.replace("\n", "<br/>")
        return Paragraph(text, style)
    elements = []
    elements.append(
        Paragraph(
            "NEXTGEN EDUCATIONAL INSTITUTE",
            title_style
        )
    )
    elements.append(
        Paragraph(
            "APPLICATION ACKNOWLEDGEMENT",
            subtitle_style
        )
    )
    application_number = f"NGEI-{application['id']:05d}"
    verification_code = f"NG-{application['id']:05d}"
    elements.append(
        Paragraph(
            f"<b>Application No.:</b> {application_number}",
            normal_style
        )
    )
    elements.append(
        Paragraph(
            f"<b>Submission Date:</b> {application['submitted_at']}",
            normal_style
        )
    )
    elements.append(
        Paragraph(
            f"<b>Verification Code:</b> {verification_code}",
            normal_style
        )
    )
    elements.append(Spacer(1, 18))
    verification_url = url_for(
        "verify_application",
        token=application["public_token"],
        _external=True
    )
    qr = qrcode.make(verification_url)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_image = Image(
        qr_buffer,
        width=80,
        height=80
    )
    elements.append(qr_image)
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "Scan the QR code to verify this application.",
            normal_style
        )
    )
    elements.append(Spacer(1, 15))
    class_names = {
        "play-group": "Play Group",
        "nursery": "Nursery",
        "lkg": "LKG",
        "ukg": "UKG",
        "class-1": "Class I",
        "class-2": "Class II",
        "class-3": "Class III",
        "class-4": "Class IV",
        "class-5": "Class V",
        "class-6": "Class VI",
        "class-7": "Class VII",
        "class-8": "Class VIII",
        "class-9": "Class IX",
        "class-10": "Class X",
        "class-11": "Class XI",
        "class-12": "Class XII"
    }
    applying_class = class_names.get(
        application["applying_class"],
        application["applying_class"]
    )
    student_phone = application["student_phone"] or "Not provided"
    student_email = application["student_email"] or "Not provided"
    data = [
        ["Particular", "Details"],
        ["Student's Full Name", application["full_name"]],
        ["Guardian's Name", application["guardian_name"]],
        ["Address", application["address"]],
        ["Date of Birth", application["dob"]],
        ["Class Applying For", applying_class],
        ["Student's Phone Number", student_phone],
        ["Guardian's Phone Number", application["guardian_phone"]],
        ["Student's Email ID", student_email],
        ["Guardian's Email ID", application["guardian_email"]]
    ]
    header_style = ParagraphStyle(
        "HeaderStyle",
        parent=normal_style,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER
    )
    data = [
        [
            format_pdf_text(cell, header_style)
            if row_index == 0
            else format_pdf_text(cell)
            for cell in row
        ]
        for row_index, row in enumerate(data)
    ]
    table = Table(
        data,
        colWidths=[160, 320],
        repeatRows=1
    )
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003366")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEADING", (0, 0), (-1, -1), 14),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(
        Paragraph(
            "<b>Important:</b> This acknowledgement confirms that the admission "
            "application has been successfully submitted. Submission of an "
            "application does not guarantee admission.",
            normal_style
        )
    )
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            "Please retain this acknowledgement for future reference. "
            "This acknowledgement is electronically generated by "
            "NextGen Educational Institute. Its authenticity can be "
            "verified using the Application Number or QR code.",
            normal_style
        )
    )
    document.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="Application_Acknowledgement_{application_number}.pdf"'
    )
    return response

@app.route("/verify/<token>")
def verify_application(token):
    connection = get_db_connection()
    application = connection.execute("""
        SELECT id, applying_class, submitted_at
        FROM applications
        WHERE public_token = ?
    """, (token,)).fetchone()
    connection.close()

    if not application:
        return render_template("verification.html", application=None), 404

    class_names = {
        "play-group": "Play Group",
        "nursery": "Nursery",
        "lkg": "LKG",
        "ukg": "UKG",
        "class-1": "Class I",
        "class-2": "Class II",
        "class-3": "Class III",
        "class-4": "Class IV",
        "class-5": "Class V",
        "class-6": "Class VI",
        "class-7": "Class VII",
        "class-8": "Class VIII",
        "class-9": "Class IX",
        "class-10": "Class X",
        "class-11": "Class XI",
        "class-12": "Class XII"
    }
    return render_template(
        "verification.html",
        application=application,
        application_number=f"NGEI-{application['id']:05d}",
        applying_class=class_names.get(
            application["applying_class"],
            "Not available"
        )
    )

@app.route("/announcements")
def announcements():
    return render_template("announcements.html")

@app.route("/facilities")
def facilities():
    return render_template("facilities.html")

@app.route("/gallery")
def gallery():
    return render_template("gallery.html")

@app.route("/contact-us", methods=["GET", "POST"])
def contact_us():
    if request.method == "POST":
        full_name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        if not full_name or not email or not phone or not message:
            flash("Please fill in all fields.", "error")
            return redirect(
                url_for("contact_us") + "#contact-form-section"
            )
        email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(email_pattern, email):
            flash(
                "Please enter a valid email address.",
                "error"
            )
            return redirect(
                url_for("contact_us") + "#contact-form-section"
            )
        phone_pattern = r"^[6-9][0-9]{9}$"
        if not re.match(phone_pattern, phone):
            flash(
                "Please enter a valid 10-digit mobile number.",
                "error"
            )
            return redirect(
                url_for("contact_us") + "#contact-form-section"
            )
        connection = get_db_connection()
        connection.execute("""
            INSERT INTO queries (full_name, email, phone, message)
            VALUES (?, ?, ?, ?)
        """, (
                full_name,
                email,
                phone,
                message
        ))
        connection.commit()
        connection.close()
        flash(
            "Your query has been submitted successfully!",
            "success"
        )
        return redirect(
            url_for("contact_us") + "#contact-form-section"
        )
    return render_template("contact-us.html")

@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy-policy.html")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )