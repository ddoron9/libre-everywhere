# 📄 File Converter System

A comprehensive file conversion system with LibreOffice integration and multiple fallback mechanisms.

## 🎯 Supported Conversions

Based on the configuration system, the following conversions are supported:

| Input Format | Output Formats | Primary Method | Fallback Methods |
|-------------|---------------|----------------|------------------|
| `.doc` | `docx`, `pdf` | LibreOffice | doc2docx, Spire.Doc |
| `.docx` | `pdf` | LibreOffice | - |
| `.xls` | `xlsx` | LibreOffice | pandas + openpyxl |
| `.xlsm` | `xlsx` | LibreOffice | pandas + openpyxl |
| `.ppt` | `pptx` | LibreOffice | - |
| `.hwp` | `html`, `pdf` | hwp5html + WeasyPrint | - |
| `.mht` | `html` | MhtmlExtractor | email parser |

## 🔧 Configuration System

The conversion mappings are defined in `config.py`:

```python
from config import get_output_extensions, get_fallback_methods

# Get output extensions for an input format
outputs = get_output_extensions('.doc')  # Returns ['docx', 'pdf']

# Get fallback methods for a conversion
fallbacks = get_fallback_methods('doc_to_docx')  # Returns ['libreoffice', 'doc2docx', 'spire_doc']
```

### Default Behavior
- **Known extensions**: Convert according to configuration
- **Unknown extensions**: Default to PDF conversion
- **Multiple outputs**: All configured outputs are generated

## 🚀 Usage

### Basic Usage

```bash
# Convert a single file
python convert.py input_file.doc

# Convert all files in a directory
python convert.py /path/to/directory

# Convert current directory
python convert.py .
```

### Using Virtual Environment

```bash
# Activate the uv virtual environment
source file-converter-env/bin/activate

# Run conversions
python convert.py input_file.doc
```

### Docker Usage

```bash
# Build the Docker image
sudo docker build -t file-converter:latest .

# Convert all files in a directory
sudo docker run --rm \
  -v /path/to/files:/data file-converter:latest

# Convert a specific file
sudo docker run --rm -u $(id -u):$(id -g) \
  -v /path/to/files:/data file-converter:latest /data/filename.doc

### 대량 파일 처리 (Batch Processing)

#### 1. 디렉토리 전체 처리
```bash
# 디렉토리 내 모든 파일 변환
sudo docker run --rm -u $(id -u):$(id -g) \
  -v /path/to/files:/data file-converter:latest /data

# 특정 디렉토리만 처리
sudo docker run --rm -u $(id -u):$(id -g) \
  -v /home/user/documents:/data file-converter:latest /data
```

#### 2. 병렬 처리 (여러 컨테이너 동시 실행)
```bash
# 여러 파일을 병렬로 처리
for file in /path/to/files/*.{doc,hwp,xls,ppt,mht}; do
  sudo docker run --rm -d -u $(id -u):$(id -g) \
    -v "$(dirname "$file"):/data" \
    file-converter:latest "/data/$(basename "$file")" &
done
wait  # 모든 작업 완료까지 대기
```

#### 3. Docker Compose를 사용한 스케일링
```yaml
# docker-compose.yml
version: '3.8'
services:
  file-converter:
    image: file-converter:latest
    volumes:
      - /path/to/input:/data
    user: "${UID}:${GID}"
    deploy:
      replicas: 4  # 4개 인스턴스 동시 실행
```

```bash
# 실행
UID=$(id -u) GID=$(id -g) docker-compose up --scale file-converter=4
```

#### 4. 대용량 처리를 위한 최적화된 명령
```bash
# CPU 코어 수만큼 병렬 처리
CORES=$(nproc)
find /path/to/files -type f \( -name "*.doc" -o -name "*.hwp" -o -name "*.xls" -o -name "*.ppt" -o -name "*.mht" \) | \
xargs -n 1 -P $CORES -I {} sudo docker run --rm -u $(id -u):$(id -g) \
  -v "$(dirname "{}"):/data" file-converter:latest "/data/$(basename "{}")"
```

#### 5. 진행 상황 모니터링
```bash
# 진행 상황을 보면서 처리
total_files=$(find /path/to/files -type f \( -name "*.doc" -o -name "*.hwp" -o -name "*.xls" -o -name "*.ppt" -o -name "*.mht" \) | wc -l)
echo "총 $total_files 개 파일 처리 시작..."

find /path/to/files -type f \( -name "*.doc" -o -name "*.hwp" -o -name "*.xls" -o -name "*.ppt" -o -name "*.mht" \) | \
while read file; do
  echo "처리 중: $(basename "$file")"
  sudo docker run --rm -u $(id -u):$(id -g) \
    -v "$(dirname "$file"):/data" \
    file-converter:latest "/data/$(basename "$file")"
done
```
```

## 🧪 Testing

### Run Comprehensive Tests

```bash
# Activate virtual environment
source file-converter-env/bin/activate

# Run all tests
python test_converter.py
```

### Test Individual Components

```bash
# Test LibreOffice availability
python -c "from convert import _run_command; print(_run_command(['soffice', '--version']))"

# Test config system
python -c "from config import get_output_extensions; print(get_output_extensions('.doc'))"

# Test actual conversions
python -c "from convert import convert_any; print(convert_any('sample.doc'))"
```

## 📦 Dependencies

### Core Dependencies (installed in virtual environment)
- `pandas>=1.3.0` - Excel file processing fallback
- `openpyxl>=3.0.0` - Excel file writing
- `xlrd>=2.0.0` - Excel file reading
- `weasyprint>=52.0` - HTML to PDF conversion
- `beautifulsoup4>=4.9.0` - HTML parsing
- `lxml>=4.6.0` - XML processing
- `python-docx>=0.8.11` - DOCX manipulation

### Optional Dependencies (Python 3.9+ only)
- `doc2docx>=0.2.0` - DOC to DOCX fallback
- `spire.doc>=12.0.0` - Commercial DOC conversion library

### System Dependencies
- **LibreOffice** - Primary conversion engine
- **Java Runtime** - Required for LibreOffice PPT conversions
- **pyhwp/hwp5html** - HWP file processing (Docker only)

## 🔄 Fallback Mechanisms

### DOC to DOCX Conversion
1. **LibreOffice** (Primary) - System LibreOffice installation
2. **doc2docx** (Fallback 1) - Python library for DOC conversion
3. **Spire.Doc** (Fallback 2) - Commercial library with advanced features

### XLS to XLSX Conversion
1. **LibreOffice** (Primary) - System LibreOffice installation
2. **pandas + openpyxl** (Fallback) - Pure Python solution

### MHT to HTML Conversion
1. **MhtmlExtractor** (Primary) - Custom MHTML parser with base64 inlining
2. **email parser** (Fallback) - Simple email-based MHTML parsing

## 🐳 Virtual Environment Setup

The project uses `uv` for fast Python package management:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv file-converter-env

# Activate environment
source file-converter-env/bin/activate

# Install dependencies
uv pip install pandas openpyxl xlrd weasyprint beautifulsoup4 lxml python-docx
```

## 📊 Test Results

Recent test results show:
- ✅ **LibreOffice Integration**: Working
- ✅ **Config System**: All tests passed
- ✅ **MHT → HTML**: Successful with base64 image inlining
- ✅ **DOC → DOCX/PDF**: LibreOffice working
- ✅ **XLS → XLSX**: Both LibreOffice and pandas fallback working
- ⚠️ **PPT → PPTX**: Requires Java Runtime for LibreOffice
- ⚠️ **HWP → HTML**: Requires hwp5html (available in Docker)

## 🔍 Troubleshooting

### LibreOffice Issues
```bash
# Check LibreOffice installation
soffice --version

# Install LibreOffice (Ubuntu/Debian)
sudo apt-get install libreoffice

# Install Java for PPT conversion
sudo apt-get install default-jre libreoffice-java-common
```

### Python Dependencies
```bash
# Check if pandas is available
python -c "import pandas; print('pandas OK')"

# Check if WeasyPrint is available  
python -c "import weasyprint; print('WeasyPrint OK')"
```

### HWP Conversion (Docker Required)
```bash
# HWP conversion only works in Docker environment
docker run --rm -v $(pwd):/data file-converter:latest /data/file.hwp
```

## 📁 File Structure

```
file_convert/
├── convert.py              # Main conversion script
├── config.py               # Configuration system
├── MhtmlExtractor.py       # MHT to HTML converter
├── test_converter.py       # Comprehensive test suite
├── Dockerfile              # Docker environment
├── pyproject.toml          # Python project configuration
├── README.md               # This file
└── file-converter-env/     # uv virtual environment
```

## 🎉 Features

- **Config-driven conversions**: Easy to modify conversion mappings
- **Multiple fallback mechanisms**: Ensures high success rate
- **Base64 image inlining**: MHT and HWP conversions include embedded images
- **Comprehensive testing**: Full test suite with mock and real file tests
- **Docker support**: Complete runtime environment
- **Virtual environment**: Isolated Python dependencies with uv
- **Error handling**: Detailed error messages and graceful degradation
- **Batch processing**: Directory-wide conversions
- **Progress reporting**: Clear success/failure indicators

## 📝 License

This project includes code from:
- [MHTMLExtractor](https://github.com/AScriver/MHTMLExtractor) - MHTML parsing functionality

## 🤝 Contributing

1. Modify `config.py` to add new conversion mappings
2. Implement conversion functions in `convert.py`
3. Add tests in `test_converter.py`
4. Update Docker dependencies in `Dockerfile`
5. Test with `python test_converter.py`
