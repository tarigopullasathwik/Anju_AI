import os

def generate_pdf(title: str, content: str, output_filename: str = "output.pdf") -> str:
    """
    Generate a simple PDF document with a title and content.
    Returns the absolute path to the generated PDF.
    """
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError("PDF generation requires the fpdf2 package") from exc

    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)

    # Content
    pdf.set_font("helvetica", "", 12)
    # multi_cell allows simple text wrapping
    pdf.multi_cell(0, 10, content)

    output_path = os.path.abspath(output_filename)
    pdf.output(output_path)
    return output_path
