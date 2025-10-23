import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

import pandas as pd
from weasyprint import CSS, HTML

from src.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

CONVERSION_MAPPINGS = {
    ".doc": ["pdf"],
    # ".docx": ["pdf"],
    ".rtf": ["pdf"],
    ".odt": ["pdf"],
    ".xls": ["xlsx"],
    ".xlsm": ["xlsx"],
    ".ppt": ["pptx"],
    ".hwp": ["pdf"],
    ".mht": ["html"],
}

def execute_shell_command(cmd: List[str]) -> str:
    """Execute shell command and return output."""
    logger.debug(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if result.returncode != 0:
        logger.error(f"Command failed: {' '.join(cmd)}\nOutput: {result.stdout}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stdout}")
    logger.debug(f"Command successful: {' '.join(cmd)}")
    return result.stdout


class BaseConverter:
    """Base class for all file converters."""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    def is_available(self) -> bool:
        """Check if the converter is available on the system."""
        raise NotImplementedError

    def convert(self, input_path: str, target_ext: str) -> str:
        """Convert file to target extension."""
        raise NotImplementedError


class LibreOfficeConverter(BaseConverter):
    """Handles LibreOffice-based conversions."""

    def __init__(self):
        super().__init__()
        self.executable = self._find_executable()

    def _find_executable(self) -> Optional[str]:
        """Find LibreOffice executable."""
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            return soffice

        # Check macOS default path
        mac_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(mac_path):
            return mac_path

        return None

    def is_available(self) -> bool:
        """Check if LibreOffice is available."""
        return self.executable is not None

    def convert(self, input_path: str, target_ext: str) -> str:
        """Convert file using LibreOffice."""
        if not self.is_available():
            raise RuntimeError("LibreOffice not found. Please install LibreOffice.")

        self.logger.info(f"Converting {input_path} -> {target_ext}")

        input_abs = os.path.abspath(input_path)
        output_dir = os.path.dirname(input_abs)
        base_name = os.path.splitext(os.path.basename(input_abs))[0]
        expected_output = os.path.join(output_dir, f"{base_name}.{target_ext}")

        cmd = [
            self.executable,
            "--headless",
            "--nologo",
            "--norestore",
            "--convert-to",
            target_ext,
            "--outdir",
            output_dir,
            input_abs,
        ]

        execute_shell_command(cmd)

        if not os.path.exists(expected_output):
            for filename in os.listdir(output_dir):
                if filename.lower().startswith(
                    base_name.lower()
                ) and filename.lower().endswith(f".{target_ext}"):
                    expected_output = os.path.join(output_dir, filename)
                    break
            else:
                raise RuntimeError(f"LibreOffice conversion failed: {expected_output}")

        self.logger.info(f"Conversion successful: {input_abs} -> {expected_output}")
        return expected_output


class AbiWordConverter(BaseConverter):
    """Handles AbiWord-based conversions."""

    def is_available(self) -> bool:
        """Check if AbiWord is available."""
        return shutil.which("abiword") is not None

    def convert(self, input_path: str, target_ext: str) -> str:
        """Convert file using AbiWord."""
        if not self.is_available():
            raise RuntimeError("AbiWord not found. Please install AbiWord.")

        self.logger.info(f"Converting {input_path} -> {target_ext} (AbiWord)")

        input_abs = os.path.abspath(input_path)
        input_dir = os.path.dirname(input_abs)
        base_name = os.path.splitext(os.path.basename(input_abs))[0]

        # AbiWord creates output in input directory
        abiword_output = os.path.join(input_dir, f"{base_name}.{target_ext}")
        current_dir = os.getcwd()
        final_output = os.path.join(current_dir, f"{base_name}.{target_ext}")

        # Prepare command for headless environment
        display = os.environ.get("DISPLAY")
        if not display or display == ":99":
            if not shutil.which("xvfb-run"):
                raise RuntimeError("xvfb-run required for headless AbiWord operation.")

            cmd = [
                "xvfb-run",
                "-a",
                "abiword",
                f"--to={target_ext}",
                input_abs,
                "--plugin=AbiCommand",
            ]
        else:
            cmd = ["abiword", f"--to={target_ext}", input_abs, "--plugin=AbiCommand"]

        execute_shell_command(cmd)

        # Handle output file location
        if os.path.exists(abiword_output):
            if abiword_output != final_output:
                if os.path.exists(final_output):
                    os.remove(final_output)
                shutil.move(abiword_output, final_output)
                self.logger.info(f"Moved output: {abiword_output} -> {final_output}")
            return final_output
        else:
            raise RuntimeError(f"AbiWord conversion failed: {abiword_output}")


class HWPConverter(BaseConverter):
    """Handles HWP file conversions."""

    def __init__(self):
        super().__init__()
        self.hwp5html_path = self._find_hwp5html()

    def _find_hwp5html(self) -> Optional[str]:
        """Find hwp5html executable."""
        hwp5html = shutil.which("hwp5html")
        if hwp5html:
            return hwp5html

        venv_path = "/app/.venv/bin/hwp5html"
        if os.path.exists(venv_path):
            return venv_path

        return None

    def is_available(self) -> bool:
        """Check if hwp5html is available."""
        return self.hwp5html_path is not None

    def to_html(self, hwp_path: str, zoom: float = 0.9) -> str:
        """Convert HWP to HTML."""
        if not self.is_available():
            raise RuntimeError("hwp5html not found. Please install pyhwp.")

        self.logger.info(f"Converting HWP to HTML: {hwp_path}")

        hwp_abs = os.path.abspath(hwp_path)
        base_name = os.path.splitext(os.path.basename(hwp_abs))[0]
        output_dir = os.path.join(os.getcwd(), f"{base_name}_html")
        html_output = os.path.join(output_dir, "index.xhtml")
        css_path = os.path.join(output_dir, "styles.css")
        
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info(f"HTML output: {html_output}")

        cmd = [self.hwp5html_path, hwp_abs, "--output", output_dir]
        execute_shell_command(cmd)

        self.logger.info(f"[After convert] HTML output: {html_output}, exists: {os.path.exists(html_output)}")

        if not os.path.exists(html_output):
            raise RuntimeError(f"HWP to HTML conversion failed: {html_output}")

        self.logger.info(f"HWP to HTML successful: {hwp_abs} -> {html_output}")
        return output_dir

    def to_pdf(self, hwp_path: str, zoom: float = 0.9, remove_html: bool = True) -> str:
        """Convert HWP to PDF via HTML."""
        self.logger.info(f"Converting HWP to PDF: {hwp_path}")

        # Convert to HTML first
        output_dir = self.to_html(hwp_path, zoom)

        # Generate PDF
        base_name = os.path.splitext(os.path.basename(hwp_path))[0]
        pdf_output = os.path.join(os.getcwd(), f"{base_name}.pdf")
        html_path = os.path.join(output_dir, "index.xhtml")
        css_path = os.path.join(output_dir, "styles.css")

        try:
            css = CSS(
                string="""
                @page { size: A4; margin: 0; }
                html, body { width: 210mm; height: 297mm; margin: 0; padding: 0; overflow: hidden; }
                * { box-sizing: border-box; max-width: 100%; }
                img, table, div { max-width: 100%; height: auto; }
            """
            )
            css_list = [css]
            if os.path.exists(css_path):
                css_list.insert(0, CSS(filename=str(css_path)))

            HTML(filename=html_path, base_url=output_dir).write_pdf(
                pdf_output, stylesheets=css_list, zoom=zoom
            )

            self.logger.info(f"HWP to PDF successful: {hwp_path} -> {pdf_output}")

            if remove_html:
                shutil.rmtree(output_dir, ignore_errors=True)

            return pdf_output

        except Exception as e:
            if remove_html:
                shutil.rmtree(output_dir, ignore_errors=True)
            raise RuntimeError(f"HWP to PDF conversion failed: {e}")


class HTMLToPDFConverter(BaseConverter):
    """Handles HTML to PDF conversions."""

    def is_available(self) -> bool:
        """WeasyPrint should be available if imported successfully."""
        return True

    def convert(self, html_path: str) -> str:
        """Convert HTML to PDF."""
        self.logger.info(f"Converting HTML to PDF: {html_path}")

        html_abs = os.path.abspath(html_path)
        base_name = os.path.splitext(os.path.basename(html_abs))[0]
        pdf_output = os.path.join(os.path.dirname(html_abs), f"{base_name}.pdf")
        base_dir = os.path.dirname(html_abs)

        try:
            with open(html_abs, "r", encoding="utf-8") as f:
                html_content = f.read()

            css = CSS(
                string="""
                @page { size: A4; margin: 20mm; }
                body { font-family: 'DejaVu Sans', sans-serif; font-size: 12pt; line-height: 1.4; }
                img { max-width: 100%; height: auto; }
                table { width: 100%; border-collapse: collapse; }
                td, th { padding: 4px; border: 1px solid #ccc; }
            """
            )

            HTML(string=html_content, base_url=base_dir).write_pdf(
                pdf_output, stylesheets=[css]
            )

            self.logger.info(f"HTML to PDF successful: {html_abs} -> {pdf_output}")
            return pdf_output

        except Exception as e:
            raise RuntimeError(f"HTML to PDF conversion failed: {e}")


class MHTConverter(BaseConverter):
    """Handles MHT file conversions."""

    def is_available(self) -> bool:
        """MHT converter is always available (has fallback)."""
        return True

    def to_html(self, mht_path: str) -> str:
        """Convert MHT to HTML."""
        self.logger.info(f"Converting MHT to HTML: {mht_path}")

        try:
            from src.MhtmlExtractor import extract_single_html

            return extract_single_html(mht_path)
        except ImportError:
            return self._fallback_conversion(mht_path)

    def _fallback_conversion(self, mht_path: str) -> str:
        """Fallback MHT conversion using email parser."""
        from email import policy
        from email.parser import BytesParser

        mht_abs = os.path.abspath(mht_path)
        base_name = os.path.splitext(os.path.basename(mht_abs))[0]
        html_output = os.path.join(os.path.dirname(mht_abs), f"{base_name}.html")

        with open(mht_abs, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        html_content = None
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                html_content = part.get_content()
                break

        if html_content is None:
            raise RuntimeError("No HTML content found in MHT file")

        with open(html_output, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"MHT to HTML successful: {mht_abs} -> {html_output}")
        return html_output


class PandasXLSConverter(BaseConverter):
    """Handles XLS to XLSX conversion using pandas."""

    def is_available(self) -> bool:
        """Check if pandas and required engines are available."""
        try:
            import pandas  # noqa: F401

            return True
        except ImportError:
            return False

    def convert(self, xls_path: str) -> str:
        """Convert XLS to XLSX using pandas."""
        if not self.is_available():
            raise RuntimeError("pandas and openpyxl required for XLS conversion.")

        self.logger.info(f"Converting XLS to XLSX: {xls_path}")

        xls_abs = os.path.abspath(xls_path)
        base_name = os.path.splitext(os.path.basename(xls_abs))[0]
        xlsx_output = os.path.join(os.path.dirname(xls_abs), f"{base_name}.xlsx")

        try:
            df = pd.read_excel(xls_abs, engine="xlrd")
            df.to_excel(xlsx_output, index=False, engine="openpyxl")

            self.logger.info(f"XLS to XLSX successful: {xls_abs} -> {xlsx_output}")
            return xlsx_output

        except Exception as e:
            raise RuntimeError(f"XLS to XLSX conversion failed: {e}")


class FileConverterManager:
    """Main converter manager that coordinates all conversion operations."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.libreoffice = LibreOfficeConverter()
        self.abiword = AbiWordConverter()
        self.hwp = HWPConverter()
        self.html_to_pdf = HTMLToPDFConverter()
        self.mht = MHTConverter()
        self.pandas_xls = PandasXLSConverter()

    def convert_any(
        self, file_path: str, convert_to: Optional[str] = None
    ) -> List[str]:
        """Convert file to specified format or default formats."""
        outputs = []
        ext = os.path.splitext(file_path)[1].lower()
        self.logger.info(f"Converting {file_path} -> {convert_to}")

        if convert_to:
            target_ext = convert_to.lower().lstrip(".")
            output_exts = [target_ext]
            self.logger.info(f"🎯 Converting {ext} -> {target_ext}")
        else:
            output_exts = CONVERSION_MAPPINGS.get(ext.lower(), [".pdf"])
            if not output_exts:
                self.logger.info(f"⚠️ Unsupported file format: {ext}")
                return outputs

        for target_ext in output_exts:
            try:
                converted = False

                if ext == ".doc" and target_ext == "docx":
                    outputs.append(self._convert_doc_to_docx(file_path))
                    converted = True
                elif ext == ".xls" and target_ext == "xlsx":
                    outputs.append(self._convert_xls_to_xlsx(file_path))
                    converted = True
                elif ext == ".ppt" and target_ext == "pptx":
                    outputs.append(self.libreoffice.convert(file_path, target_ext))
                    converted = True
                elif ext == ".hwp" and target_ext == "pdf":
                    outputs.append(self.hwp.to_pdf(file_path))
                    converted = True
                elif ext == ".mht" and target_ext == "html":
                    outputs.append(self.mht.to_html(file_path))
                    converted = True

                # Fallback conversions for convert_to parameter
                if convert_to and not converted:
                    converted_file = self._try_fallback_conversion(
                        file_path, target_ext
                    )
                    if converted_file:
                        outputs.append(converted_file)
                        converted = True

                if convert_to and not converted:
                    self.logger.info(
                        f"⚠️ Conversion {ext} -> {target_ext} not supported"
                    )

            except Exception as e:
                self.logger.info(f"⚠️ {ext.upper()}->{target_ext.upper()} failed: {e}")
                if convert_to:
                    self.logger.info(f"❌ Conversion to {target_ext} failed")
                else:
                    import traceback

                    traceback.print_exc()

        return outputs

    def _convert_doc_to_docx(self, doc_path: str) -> str:
        """Convert DOC to DOCX with fallback."""
        try:
            return self.libreoffice.convert(doc_path, "docx")
        except RuntimeError:
            try:
                return self.abiword.convert(doc_path, "docx")
            except Exception as e:
                raise RuntimeError(f"All DOC conversion methods failed: {e}")

    def _convert_xls_to_xlsx(self, xls_path: str) -> str:
        """Convert XLS to XLSX with fallback."""
        try:
            return self.libreoffice.convert(xls_path, "xlsx")
        except RuntimeError:
            return self.pandas_xls.convert(xls_path)

    def _try_fallback_conversion(
        self, file_path: str, target_ext: str
    ) -> Optional[str]:
        """Try fallback conversions for unsupported direct conversions."""
        try:
            # Try LibreOffice first
            self.logger.info(f"🔄 Trying LibreOffice: {file_path} -> {target_ext}")
            return self.libreoffice.convert(file_path, target_ext)
        except Exception as lo_e:
            self.logger.info(f"❌ LibreOffice failed: {lo_e}")

            # Try AbiWord for document formats
            if target_ext in ["pdf", "docx", "rtf", "odt", "txt"]:
                try:
                    self.logger.info(f"🔄 Trying AbiWord: {file_path} -> {target_ext}")
                    return self.abiword.convert(file_path, target_ext)
                except Exception as abi_e:
                    self.logger.info(f"❌ AbiWord failed: {abi_e}")

        return None

    def convert_path(self, path: str) -> Dict[str, List[str]]:
        """Convert all supported files in a path."""
        path_abs = os.path.abspath(path)
        results = {}

        if os.path.isfile(path_abs):
            outputs = self.convert_any(path_abs)
            if outputs:
                results[path_abs] = outputs
        else:
            for root, dirs, files in os.walk(path_abs):
                for file in files:
                    if file.startswith("."):
                        continue

                    file_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1].lower()

                    if ext in CONVERSION_MAPPINGS.keys():
                        try:
                            outputs = self.convert_any(file_path)
                            if outputs:
                                results[file_path] = outputs
                        except Exception as e:
                            self.logger.error(f"Failed to convert {file_path}: {e}")

        return results


# Create global converter instance
converter_manager = FileConverterManager()


# Backward compatibility functions
def convert_any(file_path: str, convert_to: Optional[str] = None) -> List[str]:
    """Convert file using the global converter manager."""
    return converter_manager.convert_any(file_path, convert_to)


def convert_path(path: str) -> Dict[str, List[str]]:
    """Convert all files in path using the global converter manager."""
    return converter_manager.convert_path(path)


# Legacy function aliases for backward compatibility (used by tests)
def convert_with_libreoffice(input_path: str, target_ext: str) -> str:
    return converter_manager.libreoffice.convert(input_path, target_ext)


def convert_with_abiword(input_path: str, target_ext: str) -> str:
    return converter_manager.abiword.convert(input_path, target_ext)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) >= 2 else os.getcwd()
    summary = convert_path(target)
    print(f"Conversion summary: {summary}")
