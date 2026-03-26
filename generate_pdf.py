from markdown_pdf import MarkdownPdf, Section

pdf = MarkdownPdf(toc_level=0)
with open("Placement_Portal_Report.md", "r", encoding="utf-8") as f:
    text = f.read()

pdf.add_section(Section(text))
pdf.save("Placement_Portal_Report.pdf")
print("PDF generated successfully.")
