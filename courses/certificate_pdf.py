from io import BytesIO

import qrcode

from django.utils import timezone

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


BLUE = HexColor("#1D4F91")
DARK_BLUE = HexColor("#17263A")
MUTED = HexColor("#657386")
LIGHT_BACKGROUND = HexColor("#F7FAFD")
LIGHT_BORDER = HexColor("#D2DCE7")
WHITE = HexColor("#FFFFFF")


def _fitted_font_size(
    text,
    font_name,
    maximum_size,
    minimum_size,
    maximum_width,
):
    text = str(text)
    font_size = maximum_size

    while (
        font_size > minimum_size
        and stringWidth(
            text,
            font_name,
            font_size,
        )
        > maximum_width
    ):
        font_size -= 0.5

    return font_size


def _draw_centered_text(
    pdf,
    text,
    center_x,
    y_position,
    maximum_width,
    font_name,
    maximum_size,
    minimum_size,
    color,
):
    font_size = _fitted_font_size(
        text=text,
        font_name=font_name,
        maximum_size=maximum_size,
        minimum_size=minimum_size,
        maximum_width=maximum_width,
    )

    pdf.setFillColor(color)
    pdf.setFont(
        font_name,
        font_size,
    )

    pdf.drawCentredString(
        center_x,
        y_position,
        str(text),
    )


def _create_qr_code(
    verification_url,
):
    qr_code = qrcode.QRCode(
        version=None,
        error_correction=(
            qrcode.constants.ERROR_CORRECT_M
        ),
        box_size=10,
        border=2,
    )

    qr_code.add_data(
        verification_url
    )

    qr_code.make(
        fit=True
    )

    qr_image = qr_code.make_image(
        fill_color="black",
        back_color="white",
    )

    qr_buffer = BytesIO()

    qr_image.save(
        qr_buffer,
        format="PNG",
    )

    qr_buffer.seek(0)

    return qr_buffer


def _draw_detail_card(
    pdf,
    x_position,
    y_position,
    width,
    height,
    label,
    value,
):
    pdf.setFillColor(
        LIGHT_BACKGROUND
    )

    pdf.setStrokeColor(
        LIGHT_BORDER
    )

    pdf.setLineWidth(
        0.8
    )

    pdf.roundRect(
        x_position,
        y_position,
        width,
        height,
        8,
        fill=1,
        stroke=1,
    )

    pdf.setFillColor(
        MUTED
    )

    pdf.setFont(
        "Helvetica",
        8,
    )

    pdf.drawCentredString(
        x_position + width / 2,
        y_position + 38,
        label,
    )

    _draw_centered_text(
        pdf=pdf,
        text=value,
        center_x=x_position + width / 2,
        y_position=y_position + 18,
        maximum_width=width - 20,
        font_name="Helvetica-Bold",
        maximum_size=10,
        minimum_size=7,
        color=DARK_BLUE,
    )


def build_certificate_pdf(
    certificate,
    verification_url,
):
    pdf_buffer = BytesIO()

    page_size = landscape(
        A4
    )

    page_width, page_height = (
        page_size
    )

    pdf = canvas.Canvas(
        pdf_buffer,
        pagesize=page_size,
    )

    center_x = page_width / 2

    student = certificate.student
    course = certificate.course
    attempt = (
        certificate.assessment_attempt
    )

    student_name = (
        student.get_full_name().strip()
        or student.username
    )

    issued_date = timezone.localtime(
        certificate.issued_at
    ).strftime(
        "%d %B %Y"
    )

    # Background

    pdf.setFillColor(
        WHITE
    )

    pdf.rect(
        0,
        0,
        page_width,
        page_height,
        fill=1,
        stroke=0,
    )

    # Borders

    pdf.setStrokeColor(
        BLUE
    )

    pdf.setLineWidth(
        3
    )

    pdf.rect(
        18,
        18,
        page_width - 36,
        page_height - 36,
        fill=0,
        stroke=1,
    )

    pdf.setStrokeColor(
        HexColor("#9FB2C8")
    )

    pdf.setLineWidth(
        0.8
    )

    pdf.rect(
        28,
        28,
        page_width - 56,
        page_height - 56,
        fill=0,
        stroke=1,
    )

    pdf.setStrokeColor(
        HexColor("#D0DAE5")
    )

    pdf.rect(
        36,
        36,
        page_width - 72,
        page_height - 72,
        fill=0,
        stroke=1,
    )

    # Brand mark

    pdf.setFillColor(
        BLUE
    )

    pdf.roundRect(
        center_x - 20,
        page_height - 68,
        40,
        40,
        10,
        fill=1,
        stroke=0,
    )

    pdf.setFillColor(
        WHITE
    )

    pdf.setFont(
        "Helvetica-Bold",
        19,
    )

    pdf.drawCentredString(
        center_x,
        page_height - 55,
        "S",
    )

    pdf.setFillColor(
        BLUE
    )

    pdf.setFont(
        "Helvetica-Bold",
        8,
    )

    pdf.drawCentredString(
        center_x,
        page_height - 82,
        "SKILLSTART IRELAND",
    )

    # Heading

    pdf.setFillColor(
        DARK_BLUE
    )

    pdf.setFont(
        "Times-Bold",
        30,
    )

    pdf.drawCentredString(
        center_x,
        page_height - 117,
        "Certificate of Completion",
    )

    pdf.setFillColor(
        MUTED
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawCentredString(
        center_x,
        page_height - 139,
        "This certificate is proudly presented to",
    )

    # Student

    _draw_centered_text(
        pdf=pdf,
        text=student_name,
        center_x=center_x,
        y_position=page_height - 184,
        maximum_width=540,
        font_name="Times-Bold",
        maximum_size=34,
        minimum_size=20,
        color=BLUE,
    )

    pdf.setStrokeColor(
        BLUE
    )

    pdf.setLineWidth(
        1.5
    )

    pdf.line(
        center_x - 245,
        page_height - 194,
        center_x + 245,
        page_height - 194,
    )

    pdf.setFillColor(
        MUTED
    )

    pdf.setFont(
        "Helvetica",
        10,
    )

    pdf.drawCentredString(
        center_x,
        page_height - 214,
        "for successfully completing the course",
    )

    # Course

    _draw_centered_text(
        pdf=pdf,
        text=course.title,
        center_x=center_x,
        y_position=page_height - 248,
        maximum_width=650,
        font_name="Helvetica-Bold",
        maximum_size=23,
        minimum_size=14,
        color=DARK_BLUE,
    )

    completion_text = (
        "The learner successfully completed all required "
        "lessons and passed the final assessment with a "
        f"score of {attempt.score_percentage}%."
    )

    _draw_centered_text(
        pdf=pdf,
        text=completion_text,
        center_x=center_x,
        y_position=page_height - 276,
        maximum_width=720,
        font_name="Helvetica",
        maximum_size=9,
        minimum_size=7,
        color=MUTED,
    )

    # Detail cards

    cards_y = (
        page_height - 360
    )

    cards_height = 58
    cards_gap = 14
    content_left = 55
    content_right = (
        page_width - 55
    )

    card_width = (
        (
            content_right
            - content_left
            - cards_gap * 2
        )
        / 3
    )

    card_data = [
        (
            "Date issued",
            issued_date,
        ),
        (
            "Final score",
            f"{attempt.score_percentage}%",
        ),
        (
            "Certificate number",
            certificate.certificate_number,
        ),
    ]

    for index, (
        label,
        value,
    ) in enumerate(
        card_data
    ):
        card_x = (
            content_left
            + index
            * (
                card_width
                + cards_gap
            )
        )

        _draw_detail_card(
            pdf=pdf,
            x_position=card_x,
            y_position=cards_y,
            width=card_width,
            height=cards_height,
            label=label,
            value=value,
        )

    # Signature

    pdf.setStrokeColor(
        DARK_BLUE
    )

    pdf.setLineWidth(
        0.7
    )

    pdf.line(
        70,
        75,
        255,
        75,
    )

    pdf.setFillColor(
        DARK_BLUE
    )

    pdf.setFont(
        "Helvetica-Bold",
        8,
    )

    pdf.drawString(
        70,
        59,
        "SkillStart Ireland",
    )

    pdf.setFillColor(
        MUTED
    )

    pdf.setFont(
        "Helvetica",
        7,
    )

    pdf.drawString(
        70,
        47,
        "Course provider",
    )

    # QR Code and verification information

    qr_buffer = _create_qr_code(
        verification_url
    )

    qr_size = 66

    verification_block_width = 270
    verification_right_margin = 70

    verification_block_x = (
        page_width
        - verification_right_margin
        - verification_block_width
    )

    qr_x = verification_block_x
    qr_y = 51

    pdf.drawImage(
        ImageReader(
            qr_buffer
        ),
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto",
    )

    verification_text_x = (
        qr_x
        + qr_size
        + 14
    )

    verification_text_width = (
        verification_block_width
        - qr_size
        - 14
    )

    verification_center_x = (
        verification_text_x
        + verification_text_width / 2
    )

    pdf.setFillColor(
        MUTED
    )

    pdf.setFont(
        "Helvetica",
        7,
    )

    pdf.drawCentredString(
        verification_center_x,
        qr_y + 47,
        "Scan to verify",
    )

    _draw_centered_text(
        pdf=pdf,
        text=str(
            certificate.verification_code
        ),
        center_x=verification_center_x,
        y_position=qr_y + 28,
        maximum_width=verification_text_width,
        font_name="Helvetica-Bold",
        maximum_size=6.5,
        minimum_size=4.5,
        color=DARK_BLUE,
    )

    pdf.setFillColor(
        BLUE
    )

    pdf.setFont(
        "Helvetica-Bold",
        7,
    )

    pdf.drawCentredString(
        verification_center_x,
        qr_y + 9,
        "Verify this certificate",
    )

    pdf.showPage()
    pdf.save()

    pdf_buffer.seek(0)

    return pdf_buffer
