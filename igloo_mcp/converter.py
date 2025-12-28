"""HTML to Markdown converter for Igloo pages."""

import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from html_to_markdown import convert, ConversionOptions, PreprocessingOptions
from typing import Literal, Optional


# Tags to remove during sanitization
UNWANTED_TAGS: list[str] = [
    "script",
    "style",
    "nav",
    "footer",
    "aside",
    "header",
    "noscript",
    "iframe",
    "form",
    "svg",
    "canvas",
    "video",
    "audio",
]

# Class names indicating non-content elements
UNWANTED_CLASSES: list[str] = [
    "sidebar",
    "navigation",
    "nav",
    "footer",
    "header",
    "menu",
    "ad",
    "advertisement",
    "social",
    "share",
    "comment",
    "comments",
    "related",
    "recommended",
    "popup",
    "modal",
    "cookie",
    "banner",
]

# IDs indicating non-content elements
UNWANTED_IDS: list[str] = [
    "sidebar",
    "nav",
    "navigation",
    "footer",
    "header",
    "menu",
    "comments",
]

# Default search window ratio for smart truncation (15% of max_length)
DEFAULT_TRUNCATION_WINDOW_RATIO: float = 0.15


@dataclass
class TruncationMetadata:
    """Metadata about content truncation for navigation."""
    
    status: Literal["complete", "partial"]
    chars_returned: int
    chars_total: int
    next_start_index: int | None = None  # Cursor for continuation
    current_path: str | None = None      # e.g., "Docs > API > Rate Limits"
    remaining_sections: list[str] = field(default_factory=list)  # Navigational scent


@dataclass
class ConversionResult:
    """Result of HTML to Markdown conversion with optional truncation metadata."""
    
    content: str
    metadata: TruncationMetadata | None = None  # None if not truncated


def find_smart_truncation_point(
    markdown: str,
    max_length: int,
    window_ratio: float = DEFAULT_TRUNCATION_WINDOW_RATIO,
) -> int:
    """
    Find the best semantic boundary for truncation using hierarchical search.
    
    Searches within a window before max_length to find the best place to
    truncate while preserving meaning.
    
    Args:
        markdown: The Markdown content to truncate.
        max_length: The maximum allowed length.
        window_ratio: Fraction of max_length to use as search window (default: 0.15).
    
    Returns:
        The character index to truncate at.
    """
    # Search window based on configurable ratio
    window_size = int(max_length * window_ratio)
    search_start = max(0, max_length - window_size)
    search_region = markdown[search_start:max_length]
    
    # Priority 1: Paragraph break (\n\n)
    para_pos = search_region.rfind('\n\n')
    if para_pos != -1:
        return search_start + para_pos + 2
    
    # Priority 2: Line break (\n)
    line_pos = search_region.rfind('\n')
    if line_pos != -1:
        return search_start + line_pos + 1
    
    # Priority 3: Sentence end (. or ! or ?)
    for pattern in ['. ', '! ', '? ']:
        sent_pos = search_region.rfind(pattern)
        if sent_pos != -1:
            return search_start + sent_pos + len(pattern)
    
    # Priority 4: Word boundary (space)
    word_pos = search_region.rfind(' ')
    if word_pos != -1:
        return search_start + word_pos + 1
    
    # Fallback: hard limit
    return max_length


def balance_code_fences(content: str) -> str:
    """
    Ensure code fences are properly closed after truncation.
    
    Counts code fence markers (```) and adds a closing fence if odd
    (indicating an unclosed code block).
    
    Args:
        content: The truncated Markdown content.
    
    Returns:
        Content with balanced code fences.
    """
    fence_count = content.count('```')
    if fence_count % 2 == 1:  # Odd = unclosed fence
        content += '\n```\n[Code block truncated]'
    return content


def extract_section_headers(markdown: str) -> list[tuple[str, int]]:
    """
    Extract Markdown headers with their positions for navigation metadata.
    
    Parses ATX-style headers (# Header) and returns a list of tuples
    containing the header text and its starting offset in the content.
    
    Args:
        markdown: The full Markdown content.
    
    Returns:
        List of (header_name, start_offset) tuples.
    """
    headers: list[tuple[str, int]] = []
    # Match ATX headers: lines starting with 1-6 # followed by space and text
    header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s*#*)?$', re.MULTILINE)
    
    for match in header_pattern.finditer(markdown):
        header_text = match.group(2).strip()
        start_offset = match.start()
        headers.append((header_text, start_offset))
    
    return headers


def _get_current_section_path(headers: list[tuple[str, int]], truncation_point: int) -> str | None:
    """
    Determine the current section path at the truncation point.
    
    Args:
        headers: List of (header_name, start_offset) tuples.
        truncation_point: The character offset where truncation occurs.
    
    Returns:
        A string like "Docs > API > Rate Limits" or None if no headers found.
    """
    if not headers:
        return None
    
    # Find all headers before the truncation point
    headers_before = [h for h in headers if h[1] < truncation_point]
    if not headers_before:
        return None
    
    # Return the most recent header (simplified path for now)
    return headers_before[-1][0]


def _get_remaining_sections(headers: list[tuple[str, int]], truncation_point: int) -> list[str]:
    """
    Get the list of section headers that come after the truncation point.
    
    Args:
        headers: List of (header_name, start_offset) tuples.
        truncation_point: The character offset where truncation occurs.
    
    Returns:
        List of header names that appear after the truncation point.
    """
    remaining = [h[0] for h in headers if h[1] >= truncation_point]
    # Limit to first 5 for token efficiency
    return remaining[:5]


def sanitize_html(html_string: str) -> str:
    """
    Remove unwanted elements from HTML.

    Removes scripts, styles, navigation, ads, and other non-content elements.

    Args:
        html_string: Raw HTML content.

    Returns:
        Sanitized HTML string.
    """
    soup = BeautifulSoup(html_string, "lxml")

    # Remove unwanted tags
    for tag_name in UNWANTED_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()

    # Remove elements by class
    for class_name in UNWANTED_CLASSES:
        for element in soup.find_all(class_=class_name):
            element.decompose()

    # Remove elements by ID
    for id_name in UNWANTED_IDS:
        element = soup.find(id=id_name)
        if element:
            element.decompose()

    # Remove hidden elements
    for element in soup.find_all(
        style=lambda x: x and "display:none" in x.replace(" ", "")
    ):
        element.decompose()

    return str(soup)


def extract_main_content(html_string: str) -> str:
    """
    Extract the main content container from HTML.

    Tries common content container patterns in order of specificity.

    Args:
        html_string: HTML content.

    Returns:
        HTML string of main content container.
    """
    soup = BeautifulSoup(html_string, "lxml")

    # Try content containers in order of specificity
    selectors = [
        soup.find(name="main"),
        soup.find(name="article"),
        soup.find(id="content"),
        soup.find(id="main"),
        soup.find(id="main-content"),
        soup.find(class_="content"),
        soup.find(class_="main-content"),
        soup.find(class_="article-content"),
        soup.find(attrs={"role": "main"}),
        soup.find(name="body"),
    ]

    for container in selectors:
        if container:
            return str(container)

    return html_string


def html_to_markdown(
    html_string: str,
    heading_style: Literal["underlined", "atx", "atx_closed"] = "atx",
    bullets: str = "-",
) -> str:
    """
    Convert HTML to Markdown using html-to-markdown library.

    Args:
        html_string: HTML content to convert.
        heading_style: Style for Markdown headings. Default: atx.
        bullets: Character for unordered list items. Default: -.

    Returns:
        Markdown string.
    """
    options = ConversionOptions(
        heading_style=heading_style,
        list_indent_width=2,
        bullets=bullets,
        strong_em_symbol="*",
        wrap=False,
    )

    preprocessing = PreprocessingOptions(
        enabled=True,
        preset="aggressive",
        remove_navigation=True,
        remove_forms=True,
    )

    return convert(html_string, options, preprocessing)


class OffsetError(ValueError):
    """Raised when start_index is out of bounds."""
    
    def __init__(self, start_index: int, document_length: int):
        self.start_index = start_index
        self.document_length = document_length
        super().__init__(
            f"start_index {start_index} is out of bounds. "
            f"Document length is {document_length} characters. "
            f"Valid range: 0 to {document_length - 1}."
        )


class SectionNotFoundError(ValueError):
    """Raised when a requested section is not found in the document."""
    
    def __init__(self, section_name: str, available_sections: list[str]):
        self.section_name = section_name
        self.available_sections = available_sections
        sections_list = ", ".join(f'"{s}"' for s in available_sections[:10])
        if len(available_sections) > 10:
            sections_list += f" ... and {len(available_sections) - 10} more"
        super().__init__(
            f'Section "{section_name}" not found. '
            f"Available sections: [{sections_list}]"
        )


def extract_section(markdown: str, section_name: str) -> tuple[str, int]:
    """
    Extract a specific section from Markdown by heading name.
    
    Uses fuzzy matching: case-insensitive, strips leading '#' characters.
    The section includes all content until the next heading of same or higher level.
    
    Args:
        markdown: The full Markdown content.
        section_name: Name of section to extract (e.g., "API Reference", "Configuration").
            Matches are case-insensitive and leading '#' characters are stripped.
    
    Returns:
        Tuple of (section_content, section_start_offset).
    
    Raises:
        SectionNotFoundError: If section name not found in document.
    """
    # Normalize the search term: strip leading # and whitespace, lowercase
    normalized_search = section_name.lstrip('#').strip().lower()
    
    # Extract all headers with their positions and levels
    header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s*#*)?$', re.MULTILINE)
    headers: list[tuple[int, int, str, int]] = []  # (level, start, text, end)
    
    for match in header_pattern.finditer(markdown):
        level = len(match.group(1))
        header_text = match.group(2).strip()
        start_offset = match.start()
        end_offset = match.end()
        headers.append((level, start_offset, header_text, end_offset))
    
    # Get available section names for error message
    available_sections = [h[2] for h in headers]
    
    # Find the matching section (case-insensitive fuzzy match)
    target_index = None
    for i, (level, start, text, end) in enumerate(headers):
        if text.lower() == normalized_search:
            target_index = i
            break
    
    if target_index is None:
        raise SectionNotFoundError(section_name, available_sections)
    
    target_level, target_start, _, target_header_end = headers[target_index]
    
    # Find where this section ends (next header of same or higher level)
    section_end = len(markdown)
    for i in range(target_index + 1, len(headers)):
        next_level = headers[i][0]
        if next_level <= target_level:
            section_end = headers[i][1]
            break
    
    # Extract section content (including the header itself)
    section_content = markdown[target_start:section_end].rstrip()
    
    return (section_content, target_start)


def convert_html_to_markdown(
    html_string: str,
    max_length: Optional[int] = None,
    truncation_window_ratio: float = DEFAULT_TRUNCATION_WINDOW_RATIO,
    start_index: Optional[int] = None,
) -> ConversionResult:
    """
    Full pipeline: sanitize HTML and convert to Markdown.

    This is the main entry point for the converter module.

    Args:
        html_string: Raw HTML content.
        max_length: Maximum length of output Markdown. None for no limit.
        truncation_window_ratio: Fraction of max_length to search for semantic
            boundaries when truncating (default: 0.15 = 15%).
        start_index: Character offset to start reading from (for continuation).
            When provided, content is sliced from this offset before applying
            max_length truncation. Used with cursor from previous truncated response.

    Returns:
        ConversionResult with content and optional truncation metadata.
        
    Raises:
        OffsetError: If start_index is out of bounds (>= document length or < 0).
    """
    # Step 1: Sanitize HTML
    sanitized = sanitize_html(html_string)

    # Step 2: Extract main content
    main_content = extract_main_content(sanitized)

    # Step 3: Convert to Markdown
    markdown = html_to_markdown(main_content)
    total_length = len(markdown)

    # Step 4: Handle offset-based continuation
    effective_start = 0
    if start_index is not None:
        # Validate start_index bounds
        if start_index < 0 or start_index >= total_length:
            raise OffsetError(start_index, total_length)
        
        effective_start = start_index
        markdown = markdown[start_index:]
    
    # Calculate remaining length from the starting position
    remaining_length = len(markdown)

    # Step 5: Truncate if needed with smart truncation
    if max_length is not None and remaining_length > max_length:
        # Extract section headers for navigation metadata (from full document for accurate positions)
        # We need headers from the sliced content for remaining_sections
        headers = extract_section_headers(markdown)
        
        # Find smart truncation point
        truncation_point = find_smart_truncation_point(
            markdown, max_length, truncation_window_ratio
        )
        truncated = markdown[:truncation_point]
        
        # Balance code fences
        truncated = balance_code_fences(truncated)
        
        # Calculate the next_start_index relative to the original document
        next_start_index_absolute = effective_start + truncation_point
        
        # Build truncation metadata with position context
        metadata = TruncationMetadata(
            status="partial",
            chars_returned=len(truncated),
            chars_total=total_length,
            next_start_index=next_start_index_absolute,
            current_path=_get_current_section_path(headers, truncation_point),
            remaining_sections=_get_remaining_sections(headers, truncation_point),
        )
        
        return ConversionResult(content=truncated, metadata=metadata)

    # No truncation needed - return all remaining content
    # If we started from an offset, indicate position context
    if start_index is not None and start_index > 0:
        # Content is complete from this offset onwards
        metadata = TruncationMetadata(
            status="complete",
            chars_returned=len(markdown),
            chars_total=total_length,
            next_start_index=None,  # No more content
            current_path=None,
            remaining_sections=[],
        )
        return ConversionResult(content=markdown, metadata=metadata)
    
    # Full document returned without any offset
    return ConversionResult(content=markdown, metadata=None)
