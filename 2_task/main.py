import os
import csv
import zipfile
import tempfile
from docx import Document
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from shutil import rmtree

BASE = "data"
os.makedirs(BASE, exist_ok=True)

BASE2 = os.path.join(BASE, "data2")
os.makedirs(BASE2, exist_ok=True)

# --- Helpers ---------------------------------------------------------

def write_txt(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def write_csv(path, content):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow([content])

def write_docx(path, content):
    doc = Document()
    doc.add_paragraph(content)
    doc.save(path)

def write_xlsx(path, content):
    wb = Workbook()
    ws = wb.active
    ws.append([content])
    wb.save(path)

def write_pdf(path, content):
    c = canvas.Canvas(path)
    c.drawString(50, 800, content)
    c.save()

# --- Create files ----------------------------------------------------

files = {
    "file1.txt": "txt file number 1",
    "file2.csv": "csv file number 2",
    "file3.docx": "docx file number 3",
    "file4.xlsx": "xlsx file number 4",
    "file5.pdf": "pdf file number 5"
}

for fname, text in files.items():
    path = os.path.join(BASE, fname)
    ext = fname.split(".")[-1]

    if ext == "txt":
        write_txt(path, text)
    elif ext == "csv":
        write_csv(path, text)
    elif ext == "docx":
        write_docx(path, text)
    elif ext == "xlsx":
        write_xlsx(path, text)
    elif ext == "pdf":
        write_pdf(path, text)

# создаём дополнительную подпапку с отдельным txt-файлом
data2_txt_path = os.path.join(BASE2, "file2.txt")
write_txt(data2_txt_path, "txt file number 2")

# --- Create archives with specific file combinations -----------------

# ZIP archive: pdf + txt
zip_path = os.path.join(BASE, "archive.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    with tempfile.TemporaryDirectory() as tmpdir:
        # PDF для архива
        pdf_path = os.path.join(tmpdir, "zip_pdf.pdf")
        write_pdf(pdf_path, "pdf file 1 inside zip archive")
        z.write(pdf_path, "zip_pdf.pdf")

        # TXT для архива
        txt_path = os.path.join(tmpdir, "zip_txt.txt")
        write_txt(txt_path, "txt file 1 inside zip archive")
        z.write(txt_path, "zip_txt.txt")

# RAR archive: csv + docx
rar_path = os.path.join(BASE, "archive.rar")
with zipfile.ZipFile(rar_path, "w", zipfile.ZIP_DEFLATED) as z:
    with tempfile.TemporaryDirectory() as tmpdir:
        # CSV для архива
        csv_path = os.path.join(tmpdir, "rar_csv.csv")
        write_csv(csv_path, "csv file 1 inside rar archive")
        z.write(csv_path, "rar_csv.csv")

        # DOCX для архива
        docx_path = os.path.join(tmpdir, "rar_docx.docx")
        write_docx(docx_path, "docx file 1 inside rar archive")
        z.write(docx_path, "rar_docx.docx")

# 7Z archive: csv + xlsx
sevenz_path = os.path.join(BASE, "archive.7z")
with zipfile.ZipFile(sevenz_path, "w", zipfile.ZIP_DEFLATED) as z:
    with tempfile.TemporaryDirectory() as tmpdir:
        # CSV для архива
        csv_path2 = os.path.join(tmpdir, "7z_csv.csv")
        write_csv(csv_path2, "csv file 1 inside 7z archive")
        z.write(csv_path2, "7z_csv.csv")

        # XLSX для архива
        xlsx_path2 = os.path.join(tmpdir, "7z_xlsx.xlsx")
        write_xlsx(xlsx_path2, "xlsx file 1 inside 7z archive")
        z.write(xlsx_path2, "7z_xlsx.xlsx")

print("Готово: файлы и архивы созданы в папке data/")
print("\nАрхивы содержат:")
print("  - archive.zip: pdf + txt")
print("  - archive.rar: csv + docx")
print("  - archive.7z: csv + xlsx")
print("\nВременные файлы удалены, в основной папке только архивы и исходные файлы")