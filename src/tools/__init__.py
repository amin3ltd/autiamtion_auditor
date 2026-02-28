"""
Tools package for Automaton Auditor.

This package contains the forensic tools used by detective agents:
- repo_tools.py: Git operations and AST-based code analysis
- doc_tools.py: PDF parsing and document analysis
"""

from .repo_tools import (
    clone_repository,
    get_git_history,
    analyze_graph_structure,
    analyze_state_definitions,
    check_sandboxing,
)

from .doc_tools import (
    extract_text_from_pdf,
    chunk_document,
    search_document,
    extract_images_from_pdf,
    resolve_pdf_path,
    download_pdf_from_url,
    convert_github_url_to_raw,
    download_file_from_url,
    extract_text_from_md,
    chunk_markdown,
    get_video_metadata,
    extract_frames_from_video,
    MDParseError,
    VideoParseError,
)

__all__ = [
    # Repo tools
    "clone_repository",
    "get_git_history", 
    "analyze_graph_structure",
    "analyze_state_definitions",
    "check_sandboxing",
    # Doc tools
    "extract_text_from_pdf",
    "chunk_document",
    "search_document",
    "extract_images_from_pdf",
    "resolve_pdf_path",
    "download_pdf_from_url",
    "convert_github_url_to_raw",
    "download_file_from_url",
    "extract_text_from_md",
    "chunk_markdown",
    "get_video_metadata",
    "extract_frames_from_video",
    "MDParseError",
    "VideoParseError",
]
