from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import os


def convert_all_to_pdf(input_dir: str, output_dir: str):
    """
    Convert all Markdown files in input_dir into PDF files in output_dir.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    styles = getSampleStyleSheet()

    md_files = [f for f in os.listdir(input_dir) if f.endswith(".md")]

    if not md_files:
        print("  ⚠ No Markdown files found")
        return

    for md_file in md_files:
        md_path = os.path.join(input_dir, md_file)
        pdf_path = os.path.join(output_dir, md_file.replace(".md", ".pdf"))

        print(f"  → Converting {md_file} → {os.path.basename(pdf_path)}")

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple parsing : split lignes
            lines = content.split("\n")

            elements = []

            for line in lines:
                line = line.strip()

                if not line:
                    elements.append(Spacer(1, 8))
                    continue

                # Titre principal
                if line.startswith("# "):
                    style = styles["Heading1"]
                    text = line[2:]

                # Sous-titre
                elif line.startswith("## "):
                    style = styles["Heading2"]
                    text = line[3:]

                elif line.startswith("### "):
                    style = styles["Heading3"]
                    text = line[4:]

                # Texte normal
                else:
                    style = styles["Normal"]
                    text = line

                elements.append(Paragraph(text, style))
                elements.append(Spacer(1, 6))

            doc = SimpleDocTemplate(pdf_path, pagesize=A4)
            doc.build(elements)

            print(f"    ✓ Done ({pdf_path})")

        except Exception as e:
            print(f"    ✗ Error converting {md_file}: {e}")