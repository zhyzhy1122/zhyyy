"""
文件解析模块：把上传的 PDF / DOCX / TXT 转成纯文本
用途：知识库文档支持文件上传（管理端）
"""
import io
import os

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def parse_pdf(data: bytes) -> str:
    """用 pypdf 逐页提取文本"""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def parse_docx(data: bytes) -> str:
    """用 python-docx 提取段落文本（注意：只支持 .docx，老版 .doc 不支持）"""
    from docx import Document

    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_txt(data: bytes) -> str:
    """尝试多种编码解码（中文 txt 常见 gbk）"""
    for encoding in ("utf-8", "gbk", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def is_supported(filename: str) -> bool:
    """判断文件类型是否支持"""
    return os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS


def extract_text(filename: str, data: bytes) -> str:
    """根据扩展名分发解析；不支持的类型抛 ValueError"""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return parse_pdf(data)
    if ext == ".docx":
        return parse_docx(data)
    if ext == ".txt":
        return parse_txt(data)
    raise ValueError(f"不支持的文件类型：{ext or '无扩展名'}（支持 pdf / docx / txt）")
