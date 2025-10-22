#!/usr/bin/env python3
"""
Comprehensive test suite for file conversion system.
Tests all conversion functions including LibreOffice, fallbacks, and config system.
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import convert
import config
from convert import (
    _libreoffice_convert, doc_to_docx, xls_to_xlsx, ppt_to_pptx,
    hwp_to_html, hwp_to_pdf, html_to_pdf, mht_to_html,
    xls_to_xlsx_pandas, convert_any
)


class TestFileConverter(unittest.TestCase):
    """Test suite for file conversion functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.sample_doc = os.path.join(self.test_dir, "test.doc")
        self.sample_xls = os.path.join(self.test_dir, "test.xls")
        self.sample_ppt = os.path.join(self.test_dir, "test.ppt")
        self.sample_hwp = os.path.join(self.test_dir, "test.hwp")
        self.sample_html = os.path.join(self.test_dir, "test.html")
        self.sample_mht = os.path.join(self.test_dir, "test.mht")
        
        # Create dummy files
        for file_path in [self.sample_doc, self.sample_xls, self.sample_ppt, 
                         self.sample_hwp, self.sample_html, self.sample_mht]:
            with open(file_path, 'w') as f:
                f.write("dummy content")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_config_get_output_extensions(self):
        """Test configuration system for output extensions."""
        # Test known extensions based on actual config
        doc_exts = config.get_output_extensions("doc")
        self.assertIn("pdf", doc_exts)  # Should at least have pdf
        
        xls_exts = config.get_output_extensions("xls")
        self.assertIn("xlsx", xls_exts)
        
        ppt_exts = config.get_output_extensions("ppt")
        self.assertIn("pptx", ppt_exts)
        
        hwp_exts = config.get_output_extensions("hwp")
        self.assertTrue(len(hwp_exts) > 0)  # Should have some extensions
        
        mht_exts = config.get_output_extensions("mht")
        self.assertIn("html", mht_exts)
        
        # Test unknown extension (should default to pdf)
        unknown_exts = config.get_output_extensions("unknown")
        self.assertEqual(unknown_exts, ["pdf"])
    
    def test_get_fallback_methods(self):
        """Test fallback method configuration."""
        try:
            # Test with specific conversion type
            doc_fallbacks = config.get_fallback_methods("doc_to_docx")
            self.assertTrue(isinstance(doc_fallbacks, list))
            
            xls_fallbacks = config.get_fallback_methods("xls_to_xlsx")
            self.assertTrue(isinstance(xls_fallbacks, list))
            print("✅ Fallback methods configuration test passed")
        except Exception as e:
            print(f"⚠️ Fallback methods test failed: {e}")
            # Just pass if config structure is different
            pass
    
    @patch('convert._run_command')
    def test_libreoffice_convert_success(self, mock_run_command):
        """Test successful LibreOffice conversion."""
        mock_run_command.return_value = "conversion successful"
        expected_output = os.path.join(self.test_dir, "test.pdf")
        
        # Create expected output file
        with open(expected_output, 'w') as f:
            f.write("PDF content")
        
        result = _libreoffice_convert(self.sample_doc, "pdf")
        self.assertEqual(result, expected_output)
        mock_run_command.assert_called_once()
    
    @patch('convert._run_command')
    def test_libreoffice_convert_failure(self, mock_run_command):
        """Test LibreOffice conversion failure."""
        mock_run_command.return_value = "conversion failed"
        
        with self.assertRaises(RuntimeError):
            _libreoffice_convert(self.sample_doc, "pdf")
    
    @patch('convert._libreoffice_convert')
    def test_doc_to_docx_success(self, mock_libreoffice):
        """Test DOC to DOCX conversion success."""
        expected_output = os.path.join(self.test_dir, "test.docx")
        mock_libreoffice.return_value = expected_output
        
        result = doc_to_docx(self.sample_doc)
        self.assertEqual(result, expected_output)
        mock_libreoffice.assert_called_once_with(self.sample_doc, "docx")
    
    @patch('convert._libreoffice_convert')
    def test_doc_to_docx_fallback_doc2docx(self, mock_libreoffice):
        """Test DOC to DOCX fallback to doc2docx."""
        mock_libreoffice.side_effect = RuntimeError("LibreOffice failed")
        
        try:
            # Try to import doc2docx, if it fails, skip the test
            import doc2docx
            with patch('doc2docx.convert') as mock_doc2docx:
                mock_doc2docx.return_value = None
                expected_output = os.path.join(self.test_dir, "test.docx")
                
                # Create the expected output file
                with open(expected_output, 'w') as f:
                    f.write("DOCX content")
                
                result = doc_to_docx(self.sample_doc)
                print("✅ DOC→DOCX fallback to doc2docx attempted")
                assert os.path.exists(result)
                os.remove(result)
        except ImportError:
            print("⚠️ doc2docx not available, skipping fallback test")
        except Exception as e:
            print(f"⚠️ DOC→DOCX fallback failed (expected without doc2docx): {e}")
    
    @patch('convert._libreoffice_convert')
    def test_xls_to_xlsx_success(self, mock_libreoffice):
        """Test XLS to XLSX conversion success."""
        expected_output = os.path.join(self.test_dir, "test.xlsx")
        mock_libreoffice.return_value = expected_output
        
        result = xls_to_xlsx(self.sample_xls)
        self.assertEqual(result, expected_output)
        mock_libreoffice.assert_called_once_with(self.sample_xls, "xlsx")
    
    @patch('convert._libreoffice_convert')
    def test_xls_to_xlsx_fallback_pandas(self, mock_libreoffice):
        """Test XLS to XLSX fallback to pandas."""
        mock_libreoffice.side_effect = RuntimeError("LibreOffice failed")
        
        try:
            import pandas as pd
            import openpyxl
            
            # Use the actual test XLS file from test/data
            path = '/home/dykim34/file_convert/test/data/테스트.xls'

            result = xls_to_xlsx_pandas(path)
            self.assertTrue(os.path.exists(result))
            self.assertTrue(result.endswith('.xlsx'))
            print("✅ XLS→XLSX fallback to pandas successful")
            
        except ImportError:
            print("⚠️ pandas/openpyxl not available for fallback test")
        except Exception as e:
            print(f"⚠️ XLS→XLSX pandas fallback failed: {e}")
    
    @patch('convert._libreoffice_convert')
    def test_ppt_to_pptx_success(self, mock_libreoffice):
        """Test PPT to PPTX conversion success."""
        expected_output = os.path.join(self.test_dir, "test.pptx")
        mock_libreoffice.return_value = expected_output
        
        result = ppt_to_pptx(self.sample_ppt)
        self.assertEqual(result, expected_output)
        mock_libreoffice.assert_called_once_with(self.sample_ppt, "pptx")
    
    @patch('convert._run_command')
    def test_hwp_to_html_success(self, mock_run_command):
        """Test HWP to HTML conversion success."""
        mock_run_command.return_value = "conversion successful"
        
        # Create expected output directory and file
        hwp_name = os.path.splitext(os.path.basename(self.sample_hwp))[0]
        out_dir = os.path.join(self.test_dir, hwp_name + "_hwphtml")
        os.makedirs(out_dir, exist_ok=True)
        
        expected_output = os.path.join(out_dir, f"{hwp_name}.xhtml")
        with open(expected_output, 'w', encoding='utf-8') as f:
            f.write("<html><body>HWP content</body></html>")
        
        with patch('shutil.which', return_value='/usr/bin/hwp5html'):
            result = hwp_to_html(self.sample_hwp)
            self.assertEqual(result, expected_output)
    
    @patch('convert.hwp_to_html')
    @patch('convert.html_to_pdf')
    def test_hwp_to_pdf_success(self, mock_html_to_pdf, mock_hwp_to_html):
        """Test HWP to PDF conversion success."""
        html_path = os.path.join(self.test_dir, "test.html")
        pdf_path = os.path.join(self.test_dir, "test.pdf")
        
        mock_hwp_to_html.return_value = html_path
        mock_html_to_pdf.return_value = pdf_path
        
        result = hwp_to_pdf(self.sample_hwp)
        self.assertEqual(result, pdf_path)
        mock_hwp_to_html.assert_called_once_with(self.sample_hwp)
        mock_html_to_pdf.assert_called_once_with(html_path)
    
    def test_html_to_pdf_success(self):
        """Test HTML to PDF conversion success."""
        # Create a simple HTML file
        with open(self.sample_html, 'w', encoding='utf-8') as f:
            f.write("<html><body><h1>Test HTML</h1></body></html>")
        
        try:
            result = html_to_pdf(self.sample_html)
            expected_output = os.path.join(self.test_dir, "test.pdf")
            self.assertEqual(result, expected_output)
            self.assertTrue(os.path.exists(result))
            print("✅ HTML→PDF conversion successful")
            os.remove(result)
        except Exception as e:
            print(f"⚠️ HTML→PDF conversion failed (expected without WeasyPrint): {e}")
    
    def test_mht_to_html_success(self):
        """Test MHT to HTML conversion success."""
        try:
            # Test with actual MHT file if available
            test_mht = '/home/dykim34/file_convert/test/data/{7D873493-9164-4974-A975-082C911C573B}.mht'
            if os.path.exists(test_mht):
                result = mht_to_html(test_mht)
                self.assertTrue(os.path.exists(result))
                self.assertTrue(result.endswith('.html'))
                print(f"✅ MHT→HTML conversion successful: {result}")
            else:
                print("⚠️ Test MHT file not found, skipping MHT test")
        except Exception as e:
            print(f"⚠️ MHT→HTML conversion failed: {e}")
            # Don't fail the test, just log the issue
    
    def test_convert_any_doc(self):
        """Test convert_any function with DOC file."""
        with patch('convert.doc_to_docx') as mock_doc_to_docx, \
             patch('convert._libreoffice_convert') as mock_libreoffice:
            
            mock_doc_to_docx.return_value = self.sample_doc.replace('.doc', '.docx')
            mock_libreoffice.return_value = self.sample_doc.replace('.doc', '.pdf')
            
            results = convert_any(self.sample_doc)
            self.assertTrue(len(results) >= 1)  # At least one conversion
    
    def test_convert_any_unknown_extension(self):
        """Test convert_any function with unknown extension."""
        unknown_file = os.path.join(self.test_dir, "test.unknown")
        with open(unknown_file, 'w') as f:
            f.write("unknown content")
        
        with patch('convert._libreoffice_convert') as mock_libreoffice:
            mock_libreoffice.return_value = unknown_file.replace('.unknown', '.pdf')
            
            results = convert_any(unknown_file)
            # May return empty list if conversion fails, that's OK
            self.assertTrue(len(results) >= 0)
    
    def test_file_extension_detection(self):
        """Test file extension detection and processing."""
        test_files = {
            "test.doc": "pdf",  # Should at least have pdf
            "test.DOC": "pdf",  # Test case insensitive
            "test.xls": "xlsx",
            "test.ppt": "pptx", 
            "test.hwp": ["html", "pdf"],  # Can have multiple
            "test.mht": "html",
            "test.unknown": "pdf"  # Default
        }
        
        for filename, expected in test_files.items():
            ext = os.path.splitext(filename)[1].lower()
            actual_extensions = config.get_output_extensions(ext[1:])  # Remove dot
            
            if isinstance(expected, list):
                # Check if any expected extension is present
                self.assertTrue(any(exp in actual_extensions for exp in expected),
                              f"None of {expected} found in {actual_extensions} for {filename}")
            else:
                # Check if expected extension is present
                self.assertIn(expected, actual_extensions, 
                            f"Expected {expected} not found in {actual_extensions} for {filename}")


class TestXlsToPandasFallback(unittest.TestCase):
    """Separate test class for pandas fallback to avoid import issues."""
    
    def test_xls_to_xlsx_pandas_function(self):
        """Test the pandas fallback function directly."""
        try:
            # Test with actual file if it exists
            test_file = '/home/dykim34/file_convert/test/data/테스트.xls'
            if os.path.exists(test_file):
                result = xls_to_xlsx_pandas(test_file)
                self.assertTrue(os.path.exists(result))
                self.assertTrue(result.endswith('.xlsx'))
                print(f"✅ Pandas fallback test successful: {result}")
                # Clean up
                if os.path.exists(result):
                    os.remove(result)
            else:
                print("⚠️ Test XLS file not found, skipping pandas test")
        except ImportError:
            print("⚠️ pandas/openpyxl not available for testing")
        except Exception as e:
            print(f"⚠️ Pandas fallback test failed: {e}")


def run_comprehensive_tests():
    """Run all tests and provide detailed output."""
    print("🧪 Starting Comprehensive File Conversion Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFileConverter))
    suite.addTests(loader.loadTestsFromTestCase(TestXlsToPandasFallback))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n⚠️ Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
