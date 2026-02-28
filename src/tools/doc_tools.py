"""
Document Analysis Tools

Provides forensic tools for analyzing documents:
- PDF text extraction
- Document chunking for RAG-lite approach
- Cross-reference verification
- Image extraction for diagram analysis
- Markdown file parsing and chunking
- Video metadata extraction and frame sampling

Note: Video processing functions (get_video_metadata, extract_frames_from_video)
require ffmpeg to be installed on the system.
"""

import io
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Try to import optional dependencies
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class PDFParseError(Exception):
    """Raised when PDF parsing fails."""
    pass


def convert_github_url_to_raw(url: str) -> str:
    """
    Convert a GitHub web interface URL to a raw file URL.
    
    Examples:
        https://github.com/username/repo/tree/main/path/file.pdf
            -> https://raw.githubusercontent.com/username/repo/main/path/file.pdf
        https://github.com/username/repo/blob/main/path/file.pdf
            -> https://raw.githubusercontent.com/username/repo/main/path/file.pdf
    
    Note: This function does not handle:
    - Branch names containing slashes (e.g., feature/branch-name)
    - GitHub Enterprise instances
    - URLs with query parameters
    
    Args:
        url: GitHub web URL
    
    Returns:
        Raw file URL if conversion successful, original URL otherwise
    """
    # Validate URL scheme for security
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return url  # Don't process non-http schemes
    
    # Check if it's a GitHub.com URL
    if "github.com" not in url:
        return url
    
    # Remove query parameters and fragments from URL before processing
    url_base = url.split('?')[0].split('#')[0]
    
    # Handle tree/ URLs (from GitHub web interface)
    # Pattern: github.com/owner/repo/tree/branch/path
    tree_match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)",
        url_base
    )
    if tree_match:
        owner, repo, branch, path = tree_match.groups()
        # Validate path doesn't contain suspicious patterns
        if '..' in path or path.startswith('/'):
            return url
        # URL decode the path to handle encoded characters
        path = urllib.parse.unquote(path)
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    
    # Handle blob/ URLs (from GitHub web interface)
    # Pattern: github.com/owner/repo/blob/branch/path
    blob_match = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)",
        url_base
    )
    if blob_match:
        owner, repo, branch, path = blob_match.groups()
        # Validate path doesn't contain suspicious patterns
        if '..' in path or path.startswith('/'):
            return url
        # URL decode the path to handle encoded characters
        path = urllib.parse.unquote(path)
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    
    return url


def download_pdf_from_url(url: str) -> str:
    """
    Download a PDF file from a URL (e.g., GitHub raw URL).
    
    Args:
        url: URL to the PDF file (supports both direct raw URLs and GitHub web URLs)
             Examples:
                 - https://raw.githubusercontent.com/.../report.pdf
                 - https://github.com/owner/repo/tree/main/reports/report.pdf
    
    Returns:
        Path to the downloaded PDF file
    
    Raises:
        PDFParseError: If download fails
    """
    
    # Convert GitHub web URL to raw URL if necessary
    url = convert_github_url_to_raw(url)
    
    # Validate URL scheme for security
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in ('http', 'https'):
        raise PDFParseError(f"Unsupported URL scheme: {parsed_url.scheme}. Only http and https are supported.")
    
    # Create a persistent directory for downloaded PDFs
    persistent_dir = tempfile.mkdtemp(prefix="auditor_downloaded_pdf_")
    
    # Extract filename from URL
    filename = url.split("/")[-1]
    # Ensure it's a .pdf file
    if not filename.lower().endswith(".pdf"):
        filename = "downloaded_report.pdf"
    
    local_path = os.path.join(persistent_dir, filename)
    
    try:
        # Download the file with timeout to prevent indefinite hang
        with urllib.request.urlopen(url, timeout=60) as response:
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        
        # Verify it's a valid PDF
        if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            raise PDFParseError(f"Failed to download PDF from {url}")
            
        # Check PDF magic bytes
        with open(local_path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                raise PDFParseError(f"Downloaded file is not a valid PDF: {url}")
                
        return local_path
        
    except urllib.error.URLError as e:
        shutil.rmtree(persistent_dir, ignore_errors=True)
        raise PDFParseError(f"Failed to download PDF from {url}: {str(e)}") from e
    except Exception as e:
        shutil.rmtree(persistent_dir, ignore_errors=True)
        raise PDFParseError(f"Error downloading PDF from {url}: {str(e)}") from e


def resolve_pdf_path(
    pdf_path: str,
    repo_url: Optional[str] = None,
    repo_branch: str = "main"
) -> Tuple[str, bool]:
    """
    Resolve PDF path from local or cloned repository.
    
    This function supports two modes:
    1. Local path: If the PDF exists at the given path, use it directly
    2. Repo-relative path: If not found locally and repo_url is provided,
       clone the repo and search for the PDF there
    
    Args:
        pdf_path: Path to the PDF file (local or relative to repo)
        repo_url: Optional GitHub repository URL to search in
        repo_branch: Branch to clone (default: main)
    
    Returns:
        Tuple of (resolved_path, was_cloned) where:
        - resolved_path: The full path to the PDF file
        - was_cloned: True if repo was cloned to find the PDF
    
    Raises:
        PDFParseError: If PDF is not found in either location
    """
    # First, check if the PDF exists locally (absolute or relative path)
    if os.path.isabs(pdf_path) or pdf_path.startswith("."):
        # Absolute path or relative path from current directory
        if os.path.exists(pdf_path):
            return pdf_path, False
    else:
        # Check current directory first
        local_candidate = os.path.join(os.getcwd(), pdf_path)
        if os.path.exists(local_candidate):
            return local_candidate, False
        # Also check if it exists as-is (might be a relative path that works)
        if os.path.exists(pdf_path):
            return pdf_path, False
    
    # If not found locally and repo_url provided, try to find in cloned repo
    if repo_url:
        from .repo_tools import clone_repository
        try:
            temp_repo_path = clone_repository(repo_url, repo_branch)
            # Try various path combinations
            repo_pdf_path = os.path.join(temp_repo_path, pdf_path)
            if os.path.exists(repo_pdf_path):
                # Copy PDF to a persistent temp location before cleaning up repo
                persistent_dir = tempfile.mkdtemp(prefix="auditor_pdf_")
                persistent_path = os.path.join(persistent_dir, os.path.basename(repo_pdf_path))
                shutil.copy2(repo_pdf_path, persistent_path)
                # Clean up temp repo after copying
                shutil.rmtree(temp_repo_path, ignore_errors=True)
                return persistent_path, True
            
            # Also try with different path separators
            pdf_filename = os.path.basename(pdf_path)
            for root, dirs, files in os.walk(temp_repo_path):
                if pdf_filename in files:
                    found_path = os.path.join(root, pdf_filename)
                    # Copy PDF to a persistent temp location before cleaning up repo
                    persistent_dir = tempfile.mkdtemp(prefix="auditor_pdf_")
                    persistent_path = os.path.join(persistent_dir, pdf_filename)
                    shutil.copy2(found_path, persistent_path)
                    # Clean up temp repo after copying
                    shutil.rmtree(temp_repo_path, ignore_errors=True)
                    return persistent_path, True
            
            # Clean up if PDF not found in repo
            shutil.rmtree(temp_repo_path, ignore_errors=True)
        except Exception as e:
            # Preserve original error context - re-raise with more info
            raise PDFParseError(
                f"Failed to clone repository {repo_url}: {str(e)}. "
                f"Original error type: {type(e).__name__}"
            ) from e
    
    raise PDFParseError(
        f"PDF file not found: {pdf_path}. "
        f"If specifying a path within a GitHub repo, ensure the file exists in the repository."
    )


# =============================================================================
# PDF TEXT EXTRACTION
# =============================================================================


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Extracted text as a string
    
    Raises:
        PDFParseError: If PDF cannot be read
    """
    if not PDF_AVAILABLE:
        raise PDFParseError(
            "pypdf is required for PDF parsing. Install with: pip install pypdf"
        )
    
    if not os.path.exists(pdf_path):
        raise PDFParseError(f"PDF file not found: {pdf_path}")
    
    try:
        reader = PdfReader(pdf_path)
        text_content = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_content.append(f"[Page {page_num + 1}]\n{text}")
        
        return "\n\n".join(text_content)
    
    except Exception as e:
        raise PDFParseError(f"Failed to parse PDF: {str(e)}")


def extract_images_from_pdf(pdf_path: str) -> List[Dict]:
    """
    Extract images embedded in the PDF.
    
    This is used by the VisionInspector to analyze diagrams.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        List of dicts containing image data and metadata
    """
    if not PDF_AVAILABLE:
        raise PDFParseError("pypdf is required for image extraction")
    
    if not PIL_AVAILABLE:
        raise PDFParseError("PIL is required for image extraction")
    
    images = []
    
    try:
        reader = PdfReader(pdf_path)
        
        for page_num, page in enumerate(reader.pages):
            if "/XObject" in page["/Resources"]:
                xobjects = page["/Resources"]["/XObject"].get_object()
                
                for obj in xobjects:
                    if xobjects[obj]["/Subtype"] == "/Image":
                        try:
                            # Extract image data
                            data = xobjects[obj].get_data()
                            images.append({
                                "page": page_num + 1,
                                "name": obj,
                                "size": len(data),
                                "data": data
                            })
                        except Exception:
                            pass
    
    except Exception as e:
        raise PDFParseError(f"Failed to extract images: {str(e)}")
    
    return images


# =============================================================================
# DOCUMENT CHUNKING FOR RAG-LITE
# =============================================================================


def chunk_document(
    text: str, 
    chunk_size: int = 2000, 
    overlap: int = 200
) -> List[Dict]:
    """
    Split a document into overlapping chunks for efficient querying.
    
    This implements a "RAG-lite" approach where we don't dump
    the entire PDF into context, but instead retrieve relevant chunks.
    
    Args:
        text: The full document text
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters between chunks
    
    Returns:
        List of chunks with metadata
    """
    chunks = []
    start = 0
    chunk_num = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        # Try to break at sentence boundaries
        if end < len(text):
            # Find last sentence ending
            last_period = chunk_text.rfind(".")
            last_newline = chunk_text.rfind("\n")
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size // 2:
                end = start + break_point + 1
                chunk_text = text[start:end]
        
        chunks.append({
            "chunk_id": chunk_num,
            "text": chunk_text.strip(),
            "start_char": start,
            "end_char": end,
            "char_count": len(chunk_text)
        })
        
        start = end - overlap
        chunk_num += 1
    
    return chunks


def search_document(
    chunks: List[Dict],
    query: str,
    top_k: int = 3
) -> List[Dict]:
    """
    Search for relevant chunks based on a query.
    
    Uses simple keyword matching for efficiency.
    
    Args:
        chunks: List of document chunks
        query: Search query
        top_k: Number of top results to return
    
    Returns:
        List of relevant chunks sorted by relevance
    """
    query_terms = query.lower().split()
    results = []
    
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        
        # Count matching terms
        matches = sum(1 for term in query_terms if term in text_lower)
        
        if matches > 0:
            results.append({
                **chunk,
                "match_count": matches,
                "relevance_score": matches / len(query_terms)
            })
    
    # Sort by relevance score
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return results[:top_k]


# =============================================================================
# CROSS-REFERENCE VERIFICATION
# =============================================================================


class DocumentAnalyzer:
    """
    Analyzes PDF reports for cross-reference verification.
    
    Used by DocAnalyst to:
    - Extract file paths mentioned in the report
    - Verify if those files actually exist in the repo
    - Check for keyword dropping vs substantive explanations
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text = None
        self.chunks = []
    
    def load(self):
        """Load and chunk the PDF."""
        self.text = extract_text_from_pdf(self.pdf_path)
        self.chunks = chunk_document(self.text)
    
    def extract_file_paths(self) -> List[Dict]:
        """
        Extract all file paths mentioned in the document.
        
        Returns:
            List of dicts with file paths and their contexts
        """
        if not self.text:
            self.load()
        
        # Regex patterns for common file path formats
        patterns = [
            r'(?:src/)?[\w/]+\.py',           # Python files
            r'(?:src/)?[\w/]+\.md',            # Markdown files
            r'(?:src/)?[\w/]+\.json',          # JSON files
            r'`[^`]*\.[^`]*`',                  # Backtick-quoted paths
        ]
        
        found_paths = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, self.text)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(self.text), match.end() + 100)
                context = self.text[start:end].replace("\n", " ")
                
                found_paths.append({
                    "path": match.group(),
                    "context": context,
                    "position": match.start()
                })
        
        # Deduplicate
        unique_paths = {}
        for item in found_paths:
            path = item["path"]
            if path not in unique_paths:
                unique_paths[path] = item
        
        return list(unique_paths.values())
    
    def check_keyword_depth(
        self, 
        keywords: List[str]
    ) -> Dict[str, Dict]:
        """
        Check if keywords appear with substantive explanations.
        
        Args:
            keywords: List of terms to check (e.g., ["Dialectical Synthesis"])
        
        Returns:
            Dict mapping keywords to their analysis
        """
        if not self.text:
            self.load()
        
        results = {}
        
        for keyword in keywords:
            # Find all occurrences
            matches = [
                m.start() 
                for m in re.finditer(re.escape(keyword), self.text, re.IGNORECASE)
            ]
            
            if not matches:
                results[keyword] = {
                    "found": False,
                    "count": 0,
                    "is_buzzword": True
                }
                continue
            
            # For each occurrence, check if there's substantive context
            substantive_count = 0
            
            for pos in matches:
                # Get surrounding text (500 chars before and after)
                start = max(0, pos - 500)
                end = min(len(self.text), pos + len(keyword) + 500)
                context = self.text[start:end].lower()
                
                # Check for substantive indicators
                substantive_indicators = [
                    "implement", "execute", "code", "function",
                    "architecture", "structure", "pattern", "design",
                    "mechanism", "process", "logic"
                ]
                
                if any(ind in context for ind in substantive_indicators):
                    substantive_count += 1
            
            # If keyword appears multiple times but rarely with substance,
            # it's likely just a buzzword
            is_buzzword = (
                len(matches) > 2 and 
                substantive_count == 0
            ) or (
                len(matches) > 5 and 
                substantive_count < len(matches) / 3
            )
            
            results[keyword] = {
                "found": True,
                "count": len(matches),
                "substantive_count": substantive_count,
                "is_buzzword": is_buzzword
            }
        
        return results
    
    def extract_claims(self) -> List[Dict]:
        """
        Extract claims about implementation features.
        
        Looks for patterns like "We implemented X" or "The system uses Y"
        
        Returns:
            List of claims with their contexts
        """
        if not self.text:
            self.load()
        
        # Patterns for implementation claims
        claim_patterns = [
            r'[Ww]e (?:implemented|created|built|developed)\s+([^\.]+)',
            r'The\s+system\s+uses\s+([^\.]+)',
            r'(?:implemented|created|built)\s+(?:in|using)\s+([^\.]+)',
        ]
        
        claims = []
        
        for pattern in claim_patterns:
            matches = re.finditer(pattern, self.text)
            for match in matches:
                # Get context
                start = max(0, match.start() - 200)
                end = min(len(self.text), match.end() + 100)
                context = self.text[start:end]
                
                claims.append({
                    "claim": match.group(0),
                    "feature": match.group(1) if match.groups() else None,
                    "context": context.replace("\n", " "),
                    "position": match.start()
                })
        
        return claims


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def verify_claim_against_repo(
    claims: List[Dict],
    repo_path: str
) -> Dict:
    """
    Verify document claims against actual repository contents.
    
    Args:
        claims: List of claims from the document
        repo_path: Path to the repository
    
    Returns:
        Analysis of verified vs hallucinated claims
    """
    verified = []
    hallucinated = []
    
    for claim in claims:
        feature = claim.get("feature", "")
        if not feature:
            continue
        
        # Look for files mentioned in the claim
        # This is a simplified check
        found = False
        
        # Search in filenames
        repo_files = []
        for root, dirs, files in os.walk(repo_path):
            for f in files:
                if f.endswith(".py"):
                    repo_files.append(f)
        
        # Check if any repo file matches the claim
        for repo_file in repo_files:
            if feature.lower() in repo_file.lower():
                found = True
                break
        
        if found:
            verified.append(claim)
        else:
            hallucinated.append(claim)
    
    return {
        "verified": verified,
        "hallucinated": hallucinated,
        "verified_count": len(verified),
        "hallucinated_count": len(hallucinated)
    }


# =============================================================================
# MARKDOWN (MD) FILE SUPPORT
# =============================================================================


class MDParseError(Exception):
    """Raised when MD file parsing fails."""
    pass


def download_file_from_url(url: str, extensions: tuple = (".pdf", ".md", ".mp4", ".webm", ".mov")) -> str:
    """
    Download any supported file from a URL (PDF, MD, or video).
    
    Args:
        url: URL to the file (supports GitHub web URLs and raw URLs)
        extensions: Tuple of supported file extensions
    
    Returns:
        Path to the downloaded file
    
    Raises:
        ValueError: If file type is not supported
        MDParseError: If file download or processing fails
        VideoParseError: If video file type is not supported
    """
    
    # Convert GitHub web URL to raw URL if necessary
    url = convert_github_url_to_raw(url)
    
    # Validate URL scheme for security
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}. Only http and https are supported.")
    
    # Extract and sanitize filename from URL to prevent path traversal
    # Do this BEFORE creating temp directory to avoid resource leak
    raw_filename = url.split("/")[-1]
    # Remove any path components and sanitize the filename
    filename = os.path.basename(raw_filename)
    # Remove any suspicious characters that could enable path traversal
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    if not filename or filename.startswith('.'):
        raise ValueError(f"Invalid filename in URL: {raw_filename}")
    
    # Check if file extension is supported
    if not filename.lower().endswith(extensions):
        supported = ", ".join(extensions)
        # Use appropriate exception based on file type
        video_extensions = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v')
        if filename.lower().endswith(video_extensions):
            raise VideoParseError(
                f"Unsupported video type. Supported types: {supported}. "
                f"File: {filename}"
            )
        raise MDParseError(
            f"Unsupported file type. Supported types: {supported}. "
            f"File: {filename}"
        )
    
    # Create a persistent directory for downloaded files
    # Only created AFTER validation passes
    persistent_dir = tempfile.mkdtemp(prefix="auditor_downloaded_")
    
    local_path = os.path.join(persistent_dir, filename)
    
    try:
        # Download the file with timeout to prevent indefinite hang
        with urllib.request.urlopen(url, timeout=60) as response:
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(response, f)
        
        # Verify it exists and has content
        if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
            raise MDParseError(f"Failed to download file from {url}")
        
        return local_path
        
    except urllib.error.URLError as e:
        shutil.rmtree(persistent_dir, ignore_errors=True)
        raise MDParseError(f"Failed to download file from {url}: {str(e)}") from e
    except Exception as e:
        shutil.rmtree(persistent_dir, ignore_errors=True)
        raise MDParseError(f"Error downloading file from {url}: {str(e)}") from e


def extract_text_from_md(md_path: str) -> str:
    """
    Extract text content from a Markdown file.
    
    Args:
        md_path: Path to the Markdown file
    
    Returns:
        Extracted text as a string
    
    Raises:
        MDParseError: If file cannot be read
    """
    if not os.path.exists(md_path):
        raise MDParseError(f"Markdown file not found: {md_path}")
    
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise MDParseError(f"Failed to read Markdown file: {str(e)}") from e


def chunk_markdown(text: str, chunk_size: int = 1000):
    """
    Chunk a Markdown document into sections.
    
    Args:
        text: Markdown text content
        chunk_size: Target size for each chunk
    
    Returns:
        List of text chunks with metadata
    """
    import re
    
    # Split by headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    sections = []
    last_pos = 0
    
    for match in heading_pattern.finditer(text):
        if last_pos != 0:
            sections.append(text[last_pos:match.start()])
        last_pos = match.start()
    
    # Add the last section
    if last_pos < len(text):
        sections.append(text[last_pos:])
    
    # If no headings found, use the whole text
    if not sections:
        sections = [text]
    
    # Further chunk if needed and filter out empty chunks
    chunks = []
    for i, section in enumerate(sections):
        section_text = section.strip()
        if not section_text:  # Skip empty sections
            continue
        
        if len(section_text) <= chunk_size:
            chunks.append({
                "text": section_text,
                "chunk_id": i,
                "source": "markdown"
            })
        else:
            # Split long sections
            for j in range(0, len(section_text), chunk_size):
                chunk_text = section_text[j:j + chunk_size].strip()
                if chunk_text:  # Skip empty chunks
                    chunks.append({
                        "text": chunk_text,
                        "chunk_id": f"{i}_{j}",
                        "source": "markdown"
                    })
    
    return chunks


# =============================================================================
# VIDEO FILE SUPPORT
# =============================================================================


class VideoParseError(Exception):
    """Raised when video file processing fails."""
    pass


def get_video_metadata(video_path: str):
    """
    Extract metadata from a video file.
    
    Args:
        video_path: Path to the video file
    
    Returns:
        Dictionary containing video metadata
    
    Raises:
        VideoParseError: If video cannot be read
    """
    try:
        import subprocess
    except ImportError:
        raise VideoParseError("subprocess is required for video metadata extraction")
    
    if not os.path.exists(video_path):
        raise VideoParseError(f"Video file not found: {video_path}")
    
    # Validate file extension to ensure it's a supported video format
    video_extensions = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v')
    if not video_path.lower().endswith(video_extensions):
        raise VideoParseError(
            f"Not a supported video file: {video_path}. "
            f"Supported formats: {', '.join(video_extensions)}"
        )
    
    # Use ffprobe if available, otherwise just return basic info
    try:
        # Try using ffprobe (part of ffmpeg)
        result = subprocess.run(
            [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            
            # Extract relevant metadata
            metadata = {
                "filename": os.path.basename(video_path),
                "format": data.get("format", {}).get("format_name", "unknown"),
                "duration": float(data.get("format", {}).get("duration", 0)),
                "size": int(data.get("format", {}).get("size", 0)),
            }
            
            # Get video stream info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    metadata["width"] = stream.get("width")
                    metadata["height"] = stream.get("height")
                    metadata["codec"] = stream.get("codec_name")
                    metadata["fps"] = stream.get("r_frame_rate", "unknown")
                    break
            
            # Get audio stream info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    metadata["audio_codec"] = stream.get("codec_name")
                    metadata["audio_channels"] = stream.get("channels")
                    break
            
            return metadata
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        # ffprobe not available or timed out - will use fallback
        import logging
        logging.getLogger(__name__).debug(f"ffprobe not available: {e}")
    except Exception as e:
        # Other error - will use fallback
        import logging
        logging.getLogger(__name__).debug(f"Error getting video metadata: {e}")
    
    # Fallback: return basic file info
    file_size = os.path.getsize(video_path)
    return {
        "filename": os.path.basename(video_path),
        "format": os.path.splitext(video_path)[1][1:],
        "duration": None,
        "size": file_size,
        "note": "Install ffmpeg for detailed metadata"
    }


def extract_frames_from_video(
    video_path: str,
    num_frames: int = 10,
    output_dir: Optional[str] = None
):
    """
    Extract frames from a video file for analysis.
    
    Args:
        video_path: Path to the video file
        num_frames: Number of frames to extract
        output_dir: Directory to save frames (optional)
    
    Returns:
        List of paths to extracted frame images
    
    Raises:
        VideoParseError: If frame extraction fails
    """
    try:
        import subprocess
    except ImportError:
        raise VideoParseError("subprocess is required for video frame extraction")
    
    if not os.path.exists(video_path):
        raise VideoParseError(f"Video file not found: {video_path}")
    
    # Validate file extension to ensure it's a supported video format
    video_extensions = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.m4v')
    if not video_path.lower().endswith(video_extensions):
        raise VideoParseError(
            f"Not a supported video file: {video_path}. "
            f"Supported formats: {', '.join(video_extensions)}"
        )
    
    if num_frames <= 0:
        raise VideoParseError("num_frames must be a positive integer")
    
    # Get video duration first
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        duration = float(result.stdout.strip())
    except subprocess.TimeoutExpired:
        raise VideoParseError("Video probe timed out. The file may be corrupted.")
    except Exception:
        raise VideoParseError("Could not determine video duration. Is ffmpeg installed?")
    
    # Calculate frame timestamps
    timestamps = [duration * (i + 1) / (num_frames + 1) for i in range(num_frames)]
    
    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="auditor_video_frames_")
    
    frame_paths = []
    
    for i, timestamp in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")
        
        try:
            subprocess.run(
                [
                    'ffmpeg', '-ss', str(timestamp), '-i', video_path,
                    '-vframes', '1', '-q:v', '2', '-y', output_path
                ],
                capture_output=True,
                timeout=30
            )
            
            if os.path.exists(output_path):
                frame_paths.append(output_path)
        except subprocess.TimeoutExpired:
            # Skip this frame if it times out
            continue
        except Exception:
            # Continue with other frames if one fails
            continue
    
    if not frame_paths:
        raise VideoParseError("Failed to extract any frames from video")
    
    return frame_paths
