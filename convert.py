import os
import re
import base64
import glob
import mimetypes
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from config import get_output_extensions, get_fallback_methods
from weasyprint import HTML, CSS
import pandas as pd
import sys


def _run_command(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stdout}")
    return result.stdout


# ---------------------------
# LibreOffice-based conversions (DOC/XLS/PPT → DOCX/XLSX/PPTX)
# ---------------------------
def _libreoffice_convert(input_path: str, target_ext: str) -> str:
    input_abs = os.path.abspath(input_path)
    out_dir = os.path.dirname(input_abs)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        # macOS default installation path  # linux에서 되어야 해
        mac_soffice = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(mac_soffice):
            soffice = mac_soffice
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) not found in PATH. Please install LibreOffice.")

    cmd = [
        soffice,
        "--headless",
        "--nologo",
        "--convert-to",
        target_ext,
        "--outdir",
        out_dir,
        input_abs,
    ]
    log = _run_command(cmd)

    base = os.path.splitext(os.path.basename(input_abs))[0]
    expected = os.path.join(out_dir, f"{base}.{target_ext}")
    if not os.path.exists(expected):
        # Fallback: try to find any file matching base and target extension
        for name in os.listdir(out_dir):
            if name.lower().startswith(base.lower()) and name.lower().endswith(f".{target_ext}"):
                expected = os.path.join(out_dir, name)
                break
        else:
            raise RuntimeError(f"LibreOffice conversion did not produce expected output. Log:\n{log}")

    print(f"✅ Converted {input_abs} → {expected}")
    return expected


def doc_to_docx(doc_path: str) -> str:
    try:
        return _libreoffice_convert(doc_path, "docx")
    except RuntimeError:
        # Fallback 1: Try doc2docx
        try:
            from doc2docx import convert
            docx_path = os.path.splitext(doc_path)[0] + ".docx"
            convert(doc_path, docx_path)
            print(f"✅ Converted {doc_path} → {docx_path} (via doc2docx)")
            return docx_path
        except Exception as e:
            raise RuntimeError(e)

def xls_to_xlsx(xls_path: str) -> str:
    try:
        return _libreoffice_convert(xls_path, "xlsx")
    except RuntimeError as e:
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas and openpyxl are required for XLS fallback. Install them or ensure LibreOffice is available.")

        return xls_to_xlsx_pandas(xls_path)

def xls_to_xlsx_pandas(xls_path: str) -> str:
    xlsx_path = os.path.splitext(xls_path)[0] + ".xlsx"
    sheets = pd.read_excel(xls_path, sheet_name=None)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return xlsx_path

# ---------------------------
# PPT → PPTX
# ---------------------------
def ppt_to_pptx(ppt_path: str) -> str:
    return _libreoffice_convert(ppt_path, "pptx")

# ---------------------------
# HWP → PDF (via hwp5html CLI)
# ---------------------------
# ---------------------------
# HWP → HTML (via hwp5html CLI)
# ---------------------------
def hwp_to_html(hwp_path: str, zoom: float = 0.9) -> str:
    hwp_abs = os.path.abspath(hwp_path)
    hwp_name = os.path.splitext(os.path.basename(hwp_abs))[0]
    out_dir = os.path.join(
        os.path.dirname(hwp_abs),
        hwp_name,
    )

    hwp5html = shutil.which("hwp5html")
    if not hwp5html:
        raise RuntimeError("hwp5html not found. Install pyhwp or hwp5 tools.")

    log = _run_command([hwp5html, hwp_abs, "--output", out_dir])

    html_path = os.path.join(out_dir, f"index.xhtml")
    css_path = os.path.join(out_dir, f"styles.css")

    output_pdf = os.path.join(out_dir, f"{hwp_name}.pdf")

    # 3️⃣ 기본 PDF 맞춤 CSS
    fix_css = CSS(string="""
        @page { size: A4; margin: 0; }
        html, body { width: 210mm; height: 297mm; margin: 0; padding: 0; overflow: hidden; }
        * { box-sizing: border-box; max-width: 100%; }
        img, table, div { max-width: 100%; height: auto; }
    """)

    css_list = [fix_css]
    if os.path.exists(css_path):
        css_list.insert(0, CSS(filename=str(css_path)))

    # 4️⃣ PDF 변환 실행
    HTML(filename=html_path, base_url=out_dir).write_pdf(
        output_pdf,
        stylesheets=css_list,
        zoom=zoom
    )

    print(f"✅ Converted {hwp_abs} → {index_path}")
    shutil.rmtree(out_dir)
    return output_pdf


# ---------------------------
# HWP → PDF (via hwp5html → WeasyPrint)
# ---------------------------

def hwp_to_pdf(hwp_path: str, zoom: float = 0.9, remove_html: bool = True):
    """
    Convert .hwp file -> HTML (via hwp5html) -> PDF (via WeasyPrint)

    Args:
        hwp_path (str): Input .hwp file path
        zoom (float, optional): Scale factor for PDF size adjustment (default: 0.9)
        remove_html (bool, optional): Remove HTML files after conversion (default: True)
    """
    hwp_path = Path(hwp_path).resolve()
    if not hwp_path.exists():
        raise FileNotFoundError(f"❌ HWP file not found: {hwp_path}")

    output_dir = hwp_path.parent / hwp_path.stem

    # 1️⃣ hwp5html 변환 실행
    print(f"📄 변환 중: {hwp_path.name}")
    subprocess.run(["hwp5html", str(hwp_path), "--output", output_dir], check=True)

    html_path = output_dir / "index.xhtml"
    css_path = output_dir / "styles.css"

    if not html_path.exists():
        raise FileNotFoundError(f"❌ index.xhtml not found: {html_path}")

    output_pdf = output_dir.with_suffix(".pdf")

    # 3️⃣ 기본 PDF 맞춤 CSS
    fix_css = CSS(string="""
        @page { size: A4; margin: 0; }
        html, body { width: 210mm; height: 297mm; margin: 0; padding: 0; overflow: hidden; }
        * { box-sizing: border-box; max-width: 100%; }
        img, table, div { max-width: 100%; height: auto; }
    """)

    css_list = [fix_css]
    if css_path.exists():
        css_list.insert(0, CSS(filename=str(css_path)))

    # 4️⃣ PDF 변환 실행
    HTML(filename=str(html_path), base_url=str(output_dir)).write_pdf(
        output_pdf,
        stylesheets=css_list,
        zoom=zoom
    )

    print(f"✅ PDF 변환 완료: {output_pdf}")
    if remove_html:
        shutil.rmtree(output_dir)
    return output_pdf


# ---------------------------
# HTML → PDF
# ---------------------------
def html_to_pdf(html_path: str) -> str:
    try:
        from weasyprint import HTML, CSS
    except Exception:
        raise RuntimeError("WeasyPrint is not installed. Ensure 'weasyprint' and system libs are available.")

    html_abs = os.path.abspath(html_path)
    base_dir = os.path.dirname(html_abs)
    pdf_out = os.path.splitext(html_abs)[0] + ".pdf"

    # Read HTML content and create PDF with better CSS
    with open(html_abs, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Add basic PDF styling
    pdf_css = CSS(string="""
        @page { size: A4; margin: 20mm; }
        body { font-family: 'DejaVu Sans', sans-serif; font-size: 12pt; line-height: 1.4; }
        img { max-width: 100%; height: auto; }
        table { width: 100%; border-collapse: collapse; }
        td, th { padding: 4px; border: 1px solid #ccc; }
    """)

    HTML(string=html_content, base_url=base_dir).write_pdf(pdf_out, stylesheets=[pdf_css])
    print(f"✅ Converted {html_abs} → {pdf_out}")
    return pdf_out

# ---------------------------
# MHT → HTML
# ---------------------------
def mht_to_html(mht_path: str) -> str:
    try:
        from MhtmlExtractor import extract_single_html
        return extract_single_html(mht_path)
    except ImportError:
        # Fallback to simple email parser if MhtmlExtractor is not available
        from email import policy
        from email.parser import BytesParser
        
        mht_abs = os.path.abspath(mht_path)
        base_name = os.path.splitext(os.path.basename(mht_abs))[0]
        html_out = os.path.join(os.path.dirname(mht_abs), base_name + ".html")
        
        with open(mht_abs, 'rb') as rf:
            msg = BytesParser(policy=policy.default).parse(rf)
        
        html_content = None
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                html_content = part.get_content()
                break
        
        if html_content is None:
            raise RuntimeError("No HTML content found in MHT file")
        
        with open(html_out, 'w', encoding='utf-8') as wf:
            wf.write(html_content)
        
        print(f"✅ Converted {mht_abs} → {html_out}")
        return html_out

# ---------------------------
# Main Dispatcher
# ---------------------------
def convert_any(file_path):
    outputs: List[str] = []
    ext = os.path.splitext(file_path)[1].lower()
    
    # Get output extensions from config
    output_exts = get_output_extensions(ext)
    
    if not output_exts:
        print(f"⚠️ Unsupported file format: {ext}")
        return outputs
    
    # Handle each conversion based on config
    for target_ext in output_exts:
        try:
            if ext == ".doc":
                if target_ext == "docx":
                    outputs.append(doc_to_docx(file_path))
                elif target_ext == "pdf":
                    outputs.append(_libreoffice_convert(file_path, "pdf"))
            elif ext in [".xls", ".xlsm"]:
                if target_ext == "xlsx":
                    outputs.append(xls_to_xlsx(file_path))
            elif ext == ".ppt":
                if target_ext == "pptx":
                    outputs.append(ppt_to_pptx(file_path))
                elif target_ext == "pdf":
                    outputs.append(_libreoffice_convert(file_path, "pdf"))
            elif ext == ".hwp":
                if target_ext == "pdf":
                    outputs.append(hwp_to_pdf(file_path))
            elif ext == ".mht":
                if target_ext == "html":
                    outputs.append(mht_to_html(file_path))
        except Exception as e:
            print(f"⚠️ {ext.upper()}→{target_ext.upper()} failed for {file_path}: {e}")
            import traceback
            traceback.print_exc()

    
    return outputs

def convert_path(path: str) -> Dict[str, List[str]]:
    path_abs = os.path.abspath(path)
    results: Dict[str, List[str]] = {}
    if os.path.isdir(path_abs):
        for entry in sorted(os.listdir(path_abs)):
            full = os.path.join(path_abs, entry)
            if os.path.isdir(full):
                continue
            if os.path.splitext(entry)[1].lower() in [
                ".doc", ".docx", ".xls", ".xlsm", ".ppt", ".hwp", ".mht",
            ]:
                try:
                    outputs = convert_any(full)
                    if outputs:
                        results[full] = outputs
                except Exception as e:
                    print(f"❌ Failed to convert {full}: {e}")
    else:
        try:
            outputs = convert_any(path_abs)
            if outputs:
                results[path_abs] = outputs
        except Exception as e:
            print(f"❌ Failed to convert {path_abs}: {e}")
    return results

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) >= 2 else os.getcwd()
    summary = convert_path(target)
    print("\n=== Conversion Summary ===")
    for src, outs in summary.items():
        print(f"{src}")
        for o in outs:
            print(f"  → {o}")
