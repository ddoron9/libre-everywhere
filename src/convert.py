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
from src.config import get_output_extensions, get_fallback_methods
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


def _abiword_convert(input_path: str, target_ext: str) -> str:
    """
    Convert documents using AbiWord as fallback when LibreOffice fails.
    AbiWord always creates output in the same directory as input file.
    """
    input_abs = os.path.abspath(input_path)
    input_dir = os.path.dirname(input_abs)
    base = os.path.splitext(os.path.basename(input_abs))[0]
    
    # AbiWord creates output in input file's directory
    abiword_output = os.path.join(input_dir, f"{base}.{target_ext}")
    
    # Final output path (current working directory)
    current_dir = os.getcwd()
    final_output = os.path.join(current_dir, f"{base}.{target_ext}")
    
    # Check if AbiWord is available
    abiword = shutil.which("abiword")
    if not abiword:
        raise RuntimeError("AbiWord not found in PATH. Please install AbiWord.")
    
    # Check if we're in a headless environment (Docker)
    display = os.environ.get('DISPLAY')
    if not display or display == ':99':
        # Use xvfb-run for headless operation
        xvfb_run = shutil.which("xvfb-run")
        if not xvfb_run:
            raise RuntimeError("xvfb-run not found. Required for headless AbiWord operation.")
        
        cmd = [
            xvfb_run, "-a",
            abiword,
            f"--to={target_ext}",
            input_abs,
            "--plugin=AbiCommand"
        ]
    else:
        # Direct AbiWord execution
        cmd = [
            abiword,
            f"--to={target_ext}",
            input_abs,
            "--plugin=AbiCommand"
        ]
    
    try:
        log = _run_command(cmd)
        
        # Check if AbiWord created the output file
        if os.path.exists(abiword_output):
            # Move file to current working directory if different
            if abiword_output != final_output:
                if os.path.exists(final_output):
                    os.remove(final_output)  # Remove existing file
                shutil.move(abiword_output, final_output)
                print(f"✅ Converted {input_abs} → {final_output} (via AbiWord)")
            else:
                print(f"✅ Converted {input_abs} → {abiword_output} (via AbiWord)")
                final_output = abiword_output
            
            return final_output
        else:
            raise RuntimeError(f"AbiWord conversion did not produce expected output: {abiword_output}")
            
    except Exception as e:
        raise RuntimeError(f"AbiWord conversion failed: {e}")


def doc_to_docx(doc_path: str) -> str:
    try:
        return _libreoffice_convert(doc_path, "docx")
    except RuntimeError:
        # Fallback 1: Try AbiWord
        try:
            return _abiword_convert(doc_path, "docx")
        except Exception as e:
            raise RuntimeError(f"All conversion methods failed: {e}")

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
def convert_any(file_path, convert_to=None):
    outputs: List[str] = []
    ext = os.path.splitext(file_path)[1].lower()
    
    # convert_to가 지정된 경우 해당 확장자로만 변환 시도
    if convert_to:
        target_ext = convert_to.lower().lstrip('.')  # 점 제거
        output_exts = [target_ext]
        print(f"🎯 Attempting to convert {ext} → {target_ext}")
    else:
        # 기존 방식: config에서 출력 확장자 가져오기
        output_exts = get_output_extensions(ext)
        if not output_exts:
            print(f"⚠️ Unsupported file format: {ext}")
            return outputs
    
    # Handle each conversion based on config or convert_to
    for target_ext in output_exts:
        try:
            converted = False
            
            if ext == ".doc":
                if target_ext == "docx":
                    outputs.append(doc_to_docx(file_path))
                    converted = True
                elif target_ext == "pdf":
                    try:
                        outputs.append(_libreoffice_convert(file_path, "pdf"))
                        converted = True
                    except RuntimeError:
                        outputs.append(_abiword_convert(file_path, "pdf"))
                        converted = True
            elif ext in [".docx", ".rtf", ".odt"]:
                if target_ext == "pdf":
                    try:
                        outputs.append(_libreoffice_convert(file_path, "pdf"))
                        converted = True
                    except RuntimeError:
                        outputs.append(_abiword_convert(file_path, "pdf"))
                        converted = True
            elif ext in [".xls", ".xlsm"]:
                if target_ext == "xlsx":
                    outputs.append(xls_to_xlsx(file_path))
                    converted = True
            elif ext == ".ppt":
                if target_ext == "pptx":
                    outputs.append(ppt_to_pptx(file_path))
                    converted = True
                elif target_ext == "pdf":
                    outputs.append(_libreoffice_convert(file_path, "pdf"))
                    converted = True
            elif ext == ".hwp":
                if target_ext == "pdf":
                    outputs.append(hwp_to_pdf(file_path))
                    converted = True
            elif ext == ".mht":
                if target_ext == "html":
                    outputs.append(mht_to_html(file_path))
                    converted = True
            
            # convert_to가 지정되었지만 지원하지 않는 변환인 경우 fallback 시도
            if convert_to and not converted:
                print(f"🔄 Trying LibreOffice conversion: {ext} → {target_ext}")
                try:
                    outputs.append(_libreoffice_convert(file_path, target_ext))
                    converted = True
                except Exception as lo_e:
                    print(f"❌ LibreOffice conversion failed: {lo_e}")
                    # Try AbiWord as fallback for document formats
                    if target_ext in ["pdf", "docx", "rtf", "odt", "txt"]:
                        print(f"🔄 Trying AbiWord conversion: {ext} → {target_ext}")
                        try:
                            outputs.append(_abiword_convert(file_path, target_ext))
                            converted = True
                        except Exception as abi_e:
                            print(f"❌ AbiWord conversion failed: {abi_e}")
            
            if convert_to and not converted:
                print(f"⚠️ Conversion {ext} → {target_ext} is not supported")
            

        except Exception as e:
            print(f"⚠️ {ext.upper()}→{target_ext.upper()} failed for {file_path}: {e}")
            if convert_to:
                # convert_to가 지정된 경우 실패해도 계속 진행하지 않음
                print(f"❌ Conversion to {target_ext} failed, skipping...")
            else:
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
