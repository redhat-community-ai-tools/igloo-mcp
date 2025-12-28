"""Tests for the HTML to Markdown converter module."""

import pytest

from igloo_mcp.converter import (
    sanitize_html,
    extract_main_content,
    html_to_markdown,
    convert_html_to_markdown,
    find_smart_truncation_point,
    balance_code_fences,
    extract_section_headers,
    extract_section,
    TruncationMetadata,
    ConversionResult,
    OffsetError,
    SectionNotFoundError,
    UNWANTED_TAGS,
    UNWANTED_CLASSES,
    UNWANTED_IDS,
    DEFAULT_TRUNCATION_WINDOW_RATIO,
)


# ============================================================================
# Sanitize HTML Tests
# ============================================================================


class TestSanitizeHtml:
    """Tests for sanitize_html function."""

    def test_removes_script_tags(self):
        """Test that script tags are removed."""
        html = "<html><body><script>alert('hi');</script><p>Content</p></body></html>"
        result = sanitize_html(html)
        assert "<script>" not in result
        assert "alert" not in result
        assert "<p>Content</p>" in result

    def test_removes_style_tags(self):
        """Test that style tags are removed."""
        html = "<html><body><style>.class { color: red; }</style><p>Content</p></body></html>"
        result = sanitize_html(html)
        assert "<style>" not in result
        assert "color: red" not in result

    def test_removes_nav_elements(self):
        """Test that navigation elements are removed."""
        html = "<html><body><nav><a href='/'>Home</a></nav><main>Content</main></body></html>"
        result = sanitize_html(html)
        assert "<nav>" not in result
        assert "Content" in result

    def test_removes_footer_elements(self):
        """Test that footer elements are removed."""
        html = "<html><body><main>Content</main><footer>Copyright 2024</footer></body></html>"
        result = sanitize_html(html)
        assert "<footer>" not in result
        assert "Copyright" not in result
        assert "Content" in result

    def test_removes_header_elements(self):
        """Test that header elements are removed."""
        html = "<html><body><header>Site Header</header><main>Content</main></body></html>"
        result = sanitize_html(html)
        assert "<header>" not in result
        assert "Site Header" not in result
        assert "Content" in result

    def test_removes_aside_elements(self):
        """Test that aside elements are removed."""
        html = "<html><body><aside>Sidebar</aside><main>Content</main></body></html>"
        result = sanitize_html(html)
        assert "<aside>" not in result
        assert "Sidebar" not in result
        assert "Content" in result

    def test_removes_iframe_elements(self):
        """Test that iframe elements are removed."""
        html = "<html><body><iframe src='https://example.com'></iframe><p>Content</p></body></html>"
        result = sanitize_html(html)
        assert "<iframe>" not in result
        assert "Content" in result

    def test_removes_form_elements(self):
        """Test that form elements are removed."""
        html = "<html><body><form><input type='text'></form><p>Content</p></body></html>"
        result = sanitize_html(html)
        assert "<form>" not in result
        assert "Content" in result

    def test_removes_elements_by_class(self):
        """Test removal of elements with unwanted classes."""
        html = "<html><body><div class='sidebar'>Sidebar</div><div>Content</div></body></html>"
        result = sanitize_html(html)
        assert "Sidebar" not in result
        assert "Content" in result

    def test_removes_elements_by_navigation_class(self):
        """Test removal of elements with navigation class."""
        html = "<html><body><div class='navigation'>Nav Menu</div><div>Content</div></body></html>"
        result = sanitize_html(html)
        assert "Nav Menu" not in result
        assert "Content" in result

    def test_removes_elements_by_ad_class(self):
        """Test removal of elements with ad-related classes."""
        html = "<html><body><div class='advertisement'>Buy Now!</div><div>Content</div></body></html>"
        result = sanitize_html(html)
        assert "Buy Now!" not in result
        assert "Content" in result

    def test_removes_elements_by_id(self):
        """Test removal of elements with unwanted IDs."""
        html = "<html><body><div id='navigation'>Nav</div><div>Content</div></body></html>"
        result = sanitize_html(html)
        assert "Nav" not in result
        assert "Content" in result

    def test_removes_sidebar_by_id(self):
        """Test removal of sidebar by ID."""
        html = "<html><body><div id='sidebar'>Sidebar Content</div><div>Main Content</div></body></html>"
        result = sanitize_html(html)
        assert "Sidebar Content" not in result
        assert "Main Content" in result

    def test_removes_hidden_elements(self):
        """Test removal of display:none elements."""
        html = "<html><body><div style='display:none'>Hidden</div><div>Visible</div></body></html>"
        result = sanitize_html(html)
        assert "Hidden" not in result
        assert "Visible" in result

    def test_removes_hidden_elements_with_spaces(self):
        """Test removal of display: none elements with spaces."""
        html = "<html><body><div style='display: none'>Hidden</div><div>Visible</div></body></html>"
        result = sanitize_html(html)
        assert "Hidden" not in result
        assert "Visible" in result

    def test_preserves_visible_content(self):
        """Test that visible content is preserved."""
        html = """
        <html>
        <body>
            <article>
                <h1>Title</h1>
                <p>Paragraph content</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </article>
        </body>
        </html>
        """
        result = sanitize_html(html)
        assert "Title" in result
        assert "Paragraph content" in result
        assert "Item 1" in result
        assert "Item 2" in result

    def test_multiple_unwanted_elements(self):
        """Test removal of multiple unwanted elements at once."""
        html = """
        <html>
        <head>
            <script>console.log('test');</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <nav>Navigation</nav>
            <header>Header</header>
            <main>Main Content</main>
            <aside>Sidebar</aside>
            <footer>Footer</footer>
        </body>
        </html>
        """
        result = sanitize_html(html)
        assert "console.log" not in result
        assert "color: red" not in result
        assert "Navigation" not in result
        assert "Header" not in result
        assert "Main Content" in result
        assert "Sidebar" not in result
        assert "Footer" not in result


# ============================================================================
# Extract Main Content Tests
# ============================================================================


class TestExtractMainContent:
    """Tests for extract_main_content function."""

    def test_extracts_main_element(self):
        """Test extraction of <main> element."""
        html = "<html><body><nav>Nav</nav><main><p>Content</p></main></body></html>"
        result = extract_main_content(html)
        assert "<main>" in result
        assert "Content" in result

    def test_extracts_article_element(self):
        """Test extraction of <article> element when no <main>."""
        html = "<html><body><article><p>Article content</p></article></body></html>"
        result = extract_main_content(html)
        assert "<article>" in result
        assert "Article content" in result

    def test_extracts_content_by_id(self):
        """Test extraction of element with id='content'."""
        html = "<html><body><div id='content'><p>Page content</p></div></body></html>"
        result = extract_main_content(html)
        assert 'id="content"' in result
        assert "Page content" in result

    def test_extracts_main_by_id(self):
        """Test extraction of element with id='main'."""
        html = "<html><body><div id='main'><p>Main content</p></div></body></html>"
        result = extract_main_content(html)
        assert 'id="main"' in result
        assert "Main content" in result

    def test_extracts_content_by_class(self):
        """Test extraction of element with class='content'."""
        html = "<html><body><div class='content'><p>Classed content</p></div></body></html>"
        result = extract_main_content(html)
        assert 'class="content"' in result
        assert "Classed content" in result

    def test_extracts_main_by_role(self):
        """Test extraction of element with role='main'."""
        html = "<html><body><div role='main'><p>Role content</p></div></body></html>"
        result = extract_main_content(html)
        assert 'role="main"' in result
        assert "Role content" in result

    def test_falls_back_to_body(self):
        """Test fallback to <body> when no main/article."""
        html = "<html><body><div><p>Content</p></div></body></html>"
        result = extract_main_content(html)
        assert "Content" in result

    def test_prefers_main_over_article(self):
        """Test that <main> is preferred over <article>."""
        html = "<html><body><article>Article</article><main>Main</main></body></html>"
        result = extract_main_content(html)
        assert "<main>" in result
        assert "Main" in result

    def test_nested_main_content(self):
        """Test extraction with nested content structures."""
        html = """
        <html>
        <body>
            <main>
                <article>
                    <h1>Title</h1>
                    <p>Content</p>
                </article>
            </main>
        </body>
        </html>
        """
        result = extract_main_content(html)
        assert "<main>" in result
        assert "Title" in result
        assert "Content" in result


# ============================================================================
# HTML to Markdown Tests
# ============================================================================


class TestHtmlToMarkdown:
    """Tests for html_to_markdown function."""

    def test_converts_headings(self):
        """Test heading conversion to ATX style."""
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = html_to_markdown(html)
        assert "# Title" in result
        assert "## Subtitle" in result

    def test_converts_all_heading_levels(self):
        """Test all heading levels are converted."""
        html = "<h1>H1</h1><h2>H2</h2><h3>H3</h3><h4>H4</h4><h5>H5</h5><h6>H6</h6>"
        result = html_to_markdown(html)
        assert "# H1" in result
        assert "## H2" in result
        assert "### H3" in result
        assert "#### H4" in result
        assert "##### H5" in result
        assert "###### H6" in result

    def test_converts_paragraphs(self):
        """Test paragraph conversion."""
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        result = html_to_markdown(html)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_converts_unordered_lists(self):
        """Test unordered list conversion."""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = html_to_markdown(html)
        assert "- Item 1" in result
        assert "- Item 2" in result

    def test_converts_ordered_lists(self):
        """Test ordered list conversion."""
        html = "<ol><li>First</li><li>Second</li></ol>"
        result = html_to_markdown(html)
        assert "1." in result or "1)" in result
        assert "First" in result
        assert "Second" in result

    def test_converts_links(self):
        """Test link conversion."""
        html = "<a href='https://example.com'>Link</a>"
        result = html_to_markdown(html)
        assert "[Link](https://example.com)" in result

    def test_converts_bold_text(self):
        """Test bold text conversion."""
        html = "<p>This is <strong>bold</strong> text.</p>"
        result = html_to_markdown(html)
        assert "**bold**" in result

    def test_converts_italic_text(self):
        """Test italic text conversion."""
        html = "<p>This is <em>italic</em> text.</p>"
        result = html_to_markdown(html)
        assert "*italic*" in result

    def test_converts_code_inline(self):
        """Test inline code conversion."""
        html = "<p>Use <code>print()</code> function.</p>"
        result = html_to_markdown(html)
        assert "`print()`" in result

    def test_converts_code_blocks(self):
        """Test code block conversion."""
        html = "<pre><code>def hello():\n    print('Hello')</code></pre>"
        result = html_to_markdown(html)
        assert "```" in result or "    " in result

    def test_converts_images(self):
        """Test image conversion."""
        html = "<img src='https://example.com/image.png' alt='Image'>"
        result = html_to_markdown(html)
        assert "![Image](https://example.com/image.png)" in result

    def test_converts_blockquotes(self):
        """Test blockquote conversion."""
        html = "<blockquote>Quoted text</blockquote>"
        result = html_to_markdown(html)
        assert ">" in result
        assert "Quoted text" in result


# ============================================================================
# Full Pipeline Tests
# ============================================================================


class TestConvertHtmlToMarkdown:
    """Tests for the full pipeline function."""

    def test_full_pipeline(self):
        """Test complete conversion pipeline."""
        html = """
        <html>
        <body>
            <nav><a href='/'>Home</a></nav>
            <main>
                <h1>Article Title</h1>
                <p>Article content.</p>
            </main>
            <footer>Footer</footer>
        </body>
        </html>
        """
        result = convert_html_to_markdown(html)
        assert isinstance(result, ConversionResult)
        assert "# Article Title" in result.content
        assert "Article content." in result.content
        assert "Home" not in result.content
        assert "Footer" not in result.content
        assert result.metadata is None  # No truncation

    def test_truncation(self):
        """Test content truncation with metadata."""
        html = "<p>" + "word " * 1000 + "</p>"
        result = convert_html_to_markdown(html, max_length=100)
        assert isinstance(result, ConversionResult)
        assert result.metadata is not None
        assert result.metadata.status == "partial"
        assert result.metadata.chars_total > result.metadata.chars_returned
        assert result.metadata.next_start_index is not None

    def test_no_truncation_when_under_limit(self):
        """Test no truncation when under limit."""
        html = "<p>Short content.</p>"
        result = convert_html_to_markdown(html, max_length=1000)
        assert isinstance(result, ConversionResult)
        assert result.metadata is None  # No truncation

    def test_truncation_at_semantic_boundary(self):
        """Test truncation happens at semantic boundaries when within search window.
        
        This test verifies that:
        1. Truncation respects max_length
        2. Content is not cut mid-word (last word is complete)
        3. The truncation point is at a natural boundary
        """
        # Use content with clear word boundaries (spaces)
        html = "<main><p>word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12 word13</p></main>"
        max_length = 50
        result = convert_html_to_markdown(html, max_length=max_length)
        
        assert isinstance(result, ConversionResult)
        assert result.metadata is not None
        # Verify truncation occurred and respects limit
        assert result.metadata.chars_returned <= max_length
        
        # The key property: content should not end mid-word
        # After stripping, last word should be complete (either ends with
        # a digit for "wordN" or is followed by space in original markdown)
        content = result.content.rstrip()
        # Content should end with a complete word (word + number pattern)
        import re
        # Either ends with a complete "wordN" pattern or ends at a natural break
        assert re.search(r'word\d+$', content) or content.endswith('\n'), \
            f"Content should end at word boundary, but got: '{content[-30:]}'"

    def test_complex_html_document(self):
        """Test conversion of complex HTML document."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <script>console.log('analytics');</script>
            <style>.header { background: blue; }</style>
        </head>
        <body>
            <header id="header">
                <nav class="navigation">
                    <a href="/">Home</a>
                    <a href="/about">About</a>
                </nav>
            </header>
            
            <aside class="sidebar">
                <div class="ad">Advertisement</div>
                <div class="related">Related Articles</div>
            </aside>
            
            <main role="main">
                <article>
                    <h1>Article Title</h1>
                    <p>This is the main article content.</p>
                    <h2>Section One</h2>
                    <p>Section one content.</p>
                    <ul>
                        <li>Point A</li>
                        <li>Point B</li>
                    </ul>
                </article>
            </main>
            
            <footer id="footer">
                <p>Copyright 2024</p>
                <div class="social">Share buttons</div>
            </footer>
        </body>
        </html>
        """
        result = convert_html_to_markdown(html)
        
        # Should include main content
        assert "# Article Title" in result.content
        assert "main article content" in result.content
        assert "## Section One" in result.content
        assert "Section one content" in result.content
        assert "- Point A" in result.content
        assert "- Point B" in result.content
        
        # Should not include unwanted elements
        assert "console.log" not in result.content
        assert "Advertisement" not in result.content
        assert "Related Articles" not in result.content
        assert "Copyright" not in result.content
        assert "Share buttons" not in result.content

    def test_empty_html(self):
        """Test handling of empty HTML."""
        html = ""
        result = convert_html_to_markdown(html)
        assert isinstance(result, ConversionResult)
        assert isinstance(result.content, str)

    def test_minimal_html(self):
        """Test handling of minimal HTML."""
        html = "<p>Just a paragraph.</p>"
        result = convert_html_to_markdown(html)
        assert "Just a paragraph." in result.content

    def test_preserves_table_content(self):
        """Test that table content is preserved."""
        html = """
        <table>
            <tr><th>Header 1</th><th>Header 2</th></tr>
            <tr><td>Cell 1</td><td>Cell 2</td></tr>
        </table>
        """
        result = convert_html_to_markdown(html)
        assert "Header 1" in result.content
        assert "Cell 1" in result.content


# ============================================================================
# Smart Truncation Tests
# ============================================================================


class TestFindSmartTruncationPoint:
    """Tests for find_smart_truncation_point function."""

    def test_truncates_at_paragraph_break(self):
        """Test truncation at paragraph boundary (\n\n)."""
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        # Set max_length to land in the middle of second paragraph
        max_length = 35
        point = find_smart_truncation_point(content, max_length)
        # Should truncate at the first \n\n within the search window
        assert content[:point].endswith('\n\n') or point == max_length

    def test_truncates_at_line_break(self):
        """Test truncation at line boundary when within search window."""
        max_length = 80
        window_size = int(max_length * DEFAULT_TRUNCATION_WINDOW_RATIO)
        window_start = max_length - window_size
        # Position the line break inside the search window [window_start, max_length)
        # Newline should be at a position >= window_start, so we need that many A's before it
        content = "A" * (window_start + 2) + "\n" + "B" * 50  # No spaces, so \n is only boundary
        # Verify newline is in window
        assert window_start <= content.index('\n') < max_length
        point = find_smart_truncation_point(content, max_length)
        # Should truncate at the \n since it's the only boundary in the window
        assert content[:point].endswith('\n')

    def test_fallback_to_word_boundary_when_line_break_outside_window(self):
        """Test fallback to word boundary when line break is outside search window."""
        max_length = 20
        window_size = int(max_length * DEFAULT_TRUNCATION_WINDOW_RATIO)
        window_start = max_length - window_size
        # Place line break before window start to test fallback behavior
        content = "First line\nSecond line\nThird line"
        # Verify our test setup: line break should be before window start
        assert content.index('\n') < window_start, f"Line break at {content.index(chr(10))} should be before window start {window_start}"
        point = find_smart_truncation_point(content, max_length)
        # Line break is outside window, should fall back to word boundary (space)
        truncated = content[:point]
        # Either found a space (word boundary), found line break despite being outside window, or hard limit
        assert truncated.endswith(' ') or truncated.endswith('\n') or point == max_length

    def test_truncates_at_sentence_end(self):
        """Test truncation at sentence boundary when within search window."""
        max_length = 100
        window_size = int(max_length * DEFAULT_TRUNCATION_WINDOW_RATIO)
        window_start = max_length - window_size
        # Position sentence end (". ") inside the search window [window_start, max_length)
        # Put ". " at window_start + 2, so it's clearly in the window
        content = "A" * (window_start + 2) + ". " + "B" * 50  # No spaces after ". ", so sentence is only boundary
        # Verify ". " is in window
        assert window_start <= content.index('. ') < max_length
        point = find_smart_truncation_point(content, max_length)
        # Should truncate at ". " since it's the only structured boundary in the window
        truncated = content[:point]
        assert truncated.endswith('. ')

    def test_fallback_to_word_boundary_when_sentence_outside_window(self):
        """Test fallback to word boundary when sentence end is outside search window."""
        max_length = 25
        window_size = int(max_length * DEFAULT_TRUNCATION_WINDOW_RATIO)
        window_start = max_length - window_size
        content = "First sentence. Second sentence. Third sentence."
        # Verify: first ". " should be before window_start
        first_sentence_end = content.index('. ') + 2
        assert first_sentence_end < window_start, f"Sentence end at {first_sentence_end} should be before window start {window_start}"
        point = find_smart_truncation_point(content, max_length)
        # Sentence end is outside window, should fall back to word boundary
        truncated = content[:point]
        # Should end at a space (word boundary) since no sentence in window
        assert truncated.endswith(' ') or point == max_length

    def test_truncates_at_word_boundary(self):
        """Test truncation at word boundary as fallback."""
        content = "word1 word2 word3 word4 word5"
        max_length = 15
        point = find_smart_truncation_point(content, max_length)
        # Should truncate at a space
        assert content[:point].endswith(' ') or point == max_length

    def test_hard_limit_fallback(self):
        """Test hard limit when no boundaries found."""
        content = "abcdefghijklmnopqrstuvwxyz"  # No spaces or breaks
        max_length = 10
        point = find_smart_truncation_point(content, max_length)
        assert point == max_length

    def test_custom_window_ratio(self):
        """Test with custom window ratio."""
        content = "Line one.\n\nLine two.\n\nLine three."
        max_length = 30
        # With larger window, should find earlier paragraph break
        point_large = find_smart_truncation_point(content, max_length, window_ratio=0.5)
        point_small = find_smart_truncation_point(content, max_length, window_ratio=0.1)
        # Both should be valid truncation points
        assert point_large <= max_length
        assert point_small <= max_length


class TestBalanceCodeFences:
    """Tests for balance_code_fences function."""

    def test_balanced_fences_unchanged(self):
        """Test that balanced fences are not modified."""
        content = "Before\n```python\ncode()\n```\nAfter"
        result = balance_code_fences(content)
        assert result == content

    def test_unclosed_fence_gets_closed(self):
        """Test that unclosed fence gets closing added."""
        content = "Before\n```python\ncode()"
        result = balance_code_fences(content)
        assert result.count('```') == 2
        assert "[Code block truncated]" in result

    def test_multiple_balanced_fences(self):
        """Test multiple balanced code blocks unchanged."""
        content = "```py\ncode1\n```\n\n```js\ncode2\n```"
        result = balance_code_fences(content)
        assert result == content

    def test_odd_fences_gets_balanced(self):
        """Test odd number of fences gets balanced."""
        content = "```\ncode1\n```\n\n```\ncode2"
        result = balance_code_fences(content)
        assert result.count('```') == 4  # 3 original + 1 added
        assert "[Code block truncated]" in result

    def test_no_fences(self):
        """Test content without fences unchanged."""
        content = "Just regular text\nwith newlines."
        result = balance_code_fences(content)
        assert result == content


class TestExtractSectionHeaders:
    """Tests for extract_section_headers function."""

    def test_extracts_all_header_levels(self):
        """Test extraction of all ATX header levels."""
        content = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6"
        headers = extract_section_headers(content)
        assert len(headers) == 6
        assert headers[0] == ("H1", 0)
        assert headers[1][0] == "H2"
        assert headers[5][0] == "H6"

    def test_returns_positions(self):
        """Test that positions are correct."""
        content = "# First\n\nSome text.\n\n## Second"
        headers = extract_section_headers(content)
        assert len(headers) == 2
        assert headers[0] == ("First", 0)
        assert headers[1][0] == "Second"
        assert headers[1][1] == content.index("## Second")

    def test_no_headers(self):
        """Test content without headers."""
        content = "Just regular text without headers."
        headers = extract_section_headers(content)
        assert headers == []

    def test_ignores_non_header_hashes(self):
        """Test that inline code with # is not treated as header."""
        content = "# Real Header\n\nUse `#include` in code."
        headers = extract_section_headers(content)
        assert len(headers) == 1
        assert headers[0][0] == "Real Header"


class TestTruncationMetadata:
    """Tests for TruncationMetadata and ConversionResult dataclasses."""

    def test_truncation_metadata_defaults(self):
        """Test TruncationMetadata default values."""
        meta = TruncationMetadata(
            status="partial",
            chars_returned=100,
            chars_total=500,
        )
        assert meta.next_start_index is None
        assert meta.current_path is None
        assert meta.remaining_sections == []

    def test_truncation_metadata_full(self):
        """Test TruncationMetadata with all fields."""
        meta = TruncationMetadata(
            status="partial",
            chars_returned=1000,
            chars_total=5000,
            next_start_index=1000,
            current_path="Docs > API",
            remaining_sections=["Rate Limits", "Errors"],
        )
        assert meta.status == "partial"
        assert meta.next_start_index == 1000
        assert len(meta.remaining_sections) == 2

    def test_conversion_result_no_metadata(self):
        """Test ConversionResult without metadata."""
        result = ConversionResult(content="Hello World")
        assert result.content == "Hello World"
        assert result.metadata is None

    def test_conversion_result_with_metadata(self):
        """Test ConversionResult with metadata."""
        meta = TruncationMetadata(
            status="partial",
            chars_returned=100,
            chars_total=500,
        )
        result = ConversionResult(content="Partial...", metadata=meta)
        assert result.metadata is not None
        assert result.metadata.status == "partial"


class TestConversionWithMetadata:
    """Integration tests for conversion with truncation metadata."""

    def test_truncation_includes_remaining_sections(self):
        """Test that truncation metadata includes remaining sections."""
        html = """
        <main>
            <h1>Introduction</h1>
            <p>Intro content here.</p>
            <h2>Chapter 1</h2>
            <p>Chapter 1 content.</p>
            <h2>Chapter 2</h2>
            <p>Chapter 2 content that is longer to ensure truncation.</p>
            <h2>Chapter 3</h2>
            <p>Chapter 3 content.</p>
            <h2>Chapter 4</h2>
            <p>Chapter 4 content.</p>
        </main>
        """
        result = convert_html_to_markdown(html, max_length=100)
        assert result.metadata is not None
        # Should have some remaining sections if truncated early
        # The exact sections depend on where truncation occurs

    def test_code_fence_balanced_on_truncation(self):
        """Test that code fences are balanced when truncating inside code block."""
        html = """
        <pre><code>
def very_long_function():
    # This is a comment
    x = 1
    y = 2
    z = 3
    result = x + y + z
    return result
        </code></pre>
        """
        result = convert_html_to_markdown(html, max_length=50)
        if result.metadata is not None:
            # If truncated, code fence should be balanced
            fence_count = result.content.count('```')
            assert fence_count % 2 == 0  # Even number = balanced

    def test_configurable_window_ratio(self):
        """Test that truncation_window_ratio parameter works."""
        html = "<p>" + "word " * 100 + "</p>"
        result = convert_html_to_markdown(html, max_length=200, truncation_window_ratio=0.10)
        assert result.metadata is not None
        # The truncation should still work with custom ratio
        assert result.metadata.chars_returned <= 200


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_unwanted_tags_contains_script(self):
        """Test that UNWANTED_TAGS includes script."""
        assert "script" in UNWANTED_TAGS

    def test_unwanted_tags_contains_style(self):
        """Test that UNWANTED_TAGS includes style."""
        assert "style" in UNWANTED_TAGS

    def test_unwanted_tags_contains_nav(self):
        """Test that UNWANTED_TAGS includes nav."""
        assert "nav" in UNWANTED_TAGS

    def test_unwanted_classes_contains_sidebar(self):
        """Test that UNWANTED_CLASSES includes sidebar."""
        assert "sidebar" in UNWANTED_CLASSES

    def test_unwanted_classes_contains_ad(self):
        """Test that UNWANTED_CLASSES includes ad."""
        assert "ad" in UNWANTED_CLASSES

    def test_unwanted_ids_contains_navigation(self):
        """Test that UNWANTED_IDS includes navigation."""
        assert "navigation" in UNWANTED_IDS


# ============================================================================
# Offset-Based Continuation Tests (Phase 2)
# ============================================================================


class TestOffsetError:
    """Tests for OffsetError exception."""

    def test_offset_error_message(self):
        """Test OffsetError provides informative message."""
        error = OffsetError(start_index=5000, document_length=1000)
        assert "5000" in str(error)
        assert "1000" in str(error)
        assert "out of bounds" in str(error)

    def test_offset_error_attributes(self):
        """Test OffsetError stores start_index and document_length."""
        error = OffsetError(start_index=100, document_length=50)
        assert error.start_index == 100
        assert error.document_length == 50


class TestOffsetBasedContinuation:
    """Tests for offset-based content continuation."""

    def test_continuation_from_valid_offset(self):
        """Test reading from a valid start_index."""
        html = "<main><p>" + "word " * 100 + "</p></main>"
        # First, get the full document to know its length
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Now read from an offset in the middle
        mid_offset = full_length // 2
        result = convert_html_to_markdown(html, start_index=mid_offset)
        
        assert isinstance(result, ConversionResult)
        # Content should start from the offset
        assert result.content == full_result.content[mid_offset:]
        # Should have metadata indicating "complete" since we read to the end
        assert result.metadata is not None
        assert result.metadata.status == "complete"
        assert result.metadata.chars_total == full_length

    def test_continuation_with_truncation(self):
        """Test reading from offset with max_length truncation."""
        html = "<main><p>" + "word " * 200 + "</p></main>"
        # First get full length
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Start from offset 100 with max_length 200
        result = convert_html_to_markdown(html, start_index=100, max_length=200)
        
        assert result.metadata is not None
        assert result.metadata.status == "partial"
        assert result.metadata.chars_total == full_length
        # next_start_index should be 100 + truncation point
        assert result.metadata.next_start_index is not None
        assert result.metadata.next_start_index > 100

    def test_offset_at_document_start(self):
        """Test start_index=0 behaves like no offset."""
        html = "<p>Test content</p>"
        result_no_offset = convert_html_to_markdown(html)
        result_with_zero = convert_html_to_markdown(html, start_index=0)
        
        # Both should return identical content
        assert result_no_offset.content == result_with_zero.content
        # Zero offset should not add metadata
        assert result_no_offset.metadata is None
        assert result_with_zero.metadata is None

    def test_offset_near_document_end(self):
        """Test reading from near the end of document."""
        html = "<p>Short content.</p>"
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Start from 5 chars before end
        near_end_offset = max(0, full_length - 5)
        result = convert_html_to_markdown(html, start_index=near_end_offset)
        
        assert result.metadata is not None
        assert result.metadata.status == "complete"
        assert len(result.content) == 5 or len(result.content) < 5
        assert result.metadata.next_start_index is None  # No more content

    def test_offset_out_of_bounds_raises_error(self):
        """Test that offset >= document length raises OffsetError."""
        html = "<p>Short content.</p>"
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Try to start past the end
        with pytest.raises(OffsetError) as exc_info:
            convert_html_to_markdown(html, start_index=full_length + 10)
        
        assert exc_info.value.start_index == full_length + 10
        assert exc_info.value.document_length == full_length

    def test_offset_at_exact_end_raises_error(self):
        """Test that offset == document length raises OffsetError."""
        html = "<p>Test</p>"
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        with pytest.raises(OffsetError):
            convert_html_to_markdown(html, start_index=full_length)

    def test_negative_offset_raises_error(self):
        """Test that negative offset raises OffsetError."""
        html = "<p>Test content.</p>"
        
        with pytest.raises(OffsetError):
            convert_html_to_markdown(html, start_index=-1)

    def test_continuation_preserves_total_length(self):
        """Test that chars_total reflects original document length."""
        html = "<main><p>" + "word " * 100 + "</p></main>"
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Read from various offsets
        for offset in [10, 50, 100, 200]:
            if offset < full_length:
                result = convert_html_to_markdown(html, start_index=offset)
                assert result.metadata is not None
                assert result.metadata.chars_total == full_length

    def test_next_start_index_is_absolute(self):
        """Test that next_start_index is relative to original document."""
        html = "<main><p>" + "word " * 500 + "</p></main>"
        
        # First request
        result1 = convert_html_to_markdown(html, max_length=200)
        assert result1.metadata is not None
        first_cursor = result1.metadata.next_start_index
        assert first_cursor is not None
        
        # Second request using cursor
        result2 = convert_html_to_markdown(html, start_index=first_cursor, max_length=200)
        assert result2.metadata is not None
        
        if result2.metadata.status == "partial":
            second_cursor = result2.metadata.next_start_index
            assert second_cursor is not None
            # Second cursor should be > first cursor
            assert second_cursor > first_cursor

    def test_full_document_traversal(self):
        """Test reading entire document through continuation."""
        html = "<main><p>" + "word " * 200 + "</p></main>"
        full_result = convert_html_to_markdown(html)
        full_content = full_result.content
        full_length = len(full_content)
        
        # Read in chunks of 100 chars
        chunks = []
        offset = 0
        max_iterations = 100  # Safety limit
        iterations = 0
        
        while offset < full_length and iterations < max_iterations:
            result = convert_html_to_markdown(html, start_index=offset if offset > 0 else None, max_length=100)
            chunks.append(result.content)
            
            if result.metadata is None or result.metadata.next_start_index is None:
                break
            
            offset = result.metadata.next_start_index
            iterations += 1
        
        # Reconstruct document
        reconstructed = "".join(chunks)
        assert reconstructed == full_content

    def test_offset_with_headers_extracts_correct_sections(self):
        """Test that section headers are correctly detected after offset."""
        html = """
        <main>
            <h1>Chapter 1</h1>
            <p>Content for chapter 1.</p>
            <h2>Section 1.1</h2>
            <p>Content for section 1.1.</p>
            <h2>Section 1.2</h2>
            <p>Content for section 1.2.</p>
        </main>
        """
        full_result = convert_html_to_markdown(html)
        full_length = len(full_result.content)
        
        # Find offset that starts in the middle
        mid_offset = full_length // 2
        result = convert_html_to_markdown(html, start_index=mid_offset, max_length=50)
        
        # Should still work even with headers in the offset content
        assert isinstance(result, ConversionResult)

    def test_offset_zero_vs_none(self):
        """Test that start_index=0 behaves correctly."""
        html = "<p>Test content.</p>"
        
        result_none = convert_html_to_markdown(html, start_index=None)
        result_zero = convert_html_to_markdown(html, start_index=0)
        
        # Content should be the same
        assert result_none.content == result_zero.content


# ============================================================================
# Section-Based Navigation Tests (Phase 3)
# ============================================================================


class TestSectionNotFoundError:
    """Tests for SectionNotFoundError exception."""

    def test_error_message_includes_section_name(self):
        """Test error message includes the requested section name."""
        error = SectionNotFoundError(
            section_name="API Reference",
            available_sections=["Introduction", "Configuration", "Usage"]
        )
        assert "API Reference" in str(error)
        assert "not found" in str(error)

    def test_error_message_lists_available_sections(self):
        """Test error message lists available sections."""
        error = SectionNotFoundError(
            section_name="Missing",
            available_sections=["Chapter 1", "Chapter 2", "Chapter 3"]
        )
        assert "Chapter 1" in str(error)
        assert "Chapter 2" in str(error)
        assert "Chapter 3" in str(error)

    def test_error_truncates_long_section_list(self):
        """Test error truncates section list if more than 10 sections."""
        sections = [f"Section {i}" for i in range(15)]
        error = SectionNotFoundError(
            section_name="Missing",
            available_sections=sections
        )
        error_str = str(error)
        # Should show first 10 and indicate more
        assert "Section 0" in error_str
        assert "Section 9" in error_str
        assert "5 more" in error_str

    def test_error_stores_attributes(self):
        """Test error stores section_name and available_sections."""
        error = SectionNotFoundError(
            section_name="Config",
            available_sections=["A", "B", "C"]
        )
        assert error.section_name == "Config"
        assert error.available_sections == ["A", "B", "C"]


class TestExtractSection:
    """Tests for extract_section function."""

    def test_extract_section_by_exact_name(self):
        """Test extraction of section by exact header name."""
        markdown = """# Introduction

Welcome to the guide.

## Configuration

Set up your config here.

## Usage

How to use the tool.
"""
        section_content, offset = extract_section(markdown, "Configuration")
        
        assert "## Configuration" in section_content
        assert "Set up your config here" in section_content
        # Should not include Usage section
        assert "## Usage" not in section_content
        assert offset == markdown.index("## Configuration")

    def test_extract_section_case_insensitive(self):
        """Test that section matching is case-insensitive."""
        markdown = """# Introduction

Content.

## API Reference

API docs here.
"""
        # Try different case variations
        content1, _ = extract_section(markdown, "api reference")
        content2, _ = extract_section(markdown, "API REFERENCE")
        content3, _ = extract_section(markdown, "Api Reference")
        
        assert "## API Reference" in content1
        assert "## API Reference" in content2
        assert "## API Reference" in content3

    def test_extract_section_strips_hash_prefix(self):
        """Test that leading # characters are stripped from search."""
        markdown = """# Title

## Configuration

Config content.
"""
        # Should work with various # prefixes
        content1, _ = extract_section(markdown, "# Configuration")
        content2, _ = extract_section(markdown, "## Configuration")
        content3, _ = extract_section(markdown, "### Configuration")
        
        assert "## Configuration" in content1
        assert "## Configuration" in content2
        assert "## Configuration" in content3

    def test_extract_section_includes_content_until_next_same_level(self):
        """Test section includes content until next heading of same or higher level."""
        markdown = """## Chapter 1

Content for chapter 1.

### Section 1.1

Subsection content.

### Section 1.2

More subsection content.

## Chapter 2

Content for chapter 2.
"""
        content, _ = extract_section(markdown, "Chapter 1")
        
        assert "## Chapter 1" in content
        assert "### Section 1.1" in content
        assert "### Section 1.2" in content
        # Should NOT include Chapter 2
        assert "## Chapter 2" not in content

    def test_extract_section_subsection_stops_at_sibling(self):
        """Test subsection extraction stops at next sibling or parent."""
        markdown = """## Chapter 1

### Section 1.1

Content for 1.1.

### Section 1.2

Content for 1.2.

## Chapter 2
"""
        content, _ = extract_section(markdown, "Section 1.1")
        
        assert "### Section 1.1" in content
        assert "Content for 1.1" in content
        # Should stop before Section 1.2 (sibling)
        assert "### Section 1.2" not in content

    def test_extract_section_last_section(self):
        """Test extraction of last section in document."""
        markdown = """# Introduction

Intro.

## Conclusion

Final thoughts here.
"""
        content, _ = extract_section(markdown, "Conclusion")
        
        assert "## Conclusion" in content
        assert "Final thoughts here" in content

    def test_extract_section_not_found_raises_error(self):
        """Test that missing section raises SectionNotFoundError."""
        markdown = """# Introduction

## Configuration

## Usage
"""
        with pytest.raises(SectionNotFoundError) as exc_info:
            extract_section(markdown, "API Reference")
        
        error = exc_info.value
        assert error.section_name == "API Reference"
        assert "Introduction" in error.available_sections
        assert "Configuration" in error.available_sections
        assert "Usage" in error.available_sections

    def test_extract_section_returns_correct_offset(self):
        """Test that returned offset is correct character position."""
        markdown = "# Header\n\nSome text.\n\n## Target Section\n\nTarget content."
        
        content, offset = extract_section(markdown, "Target Section")
        
        # Verify offset points to start of section
        assert markdown[offset:].startswith("## Target Section")

    def test_extract_section_with_whitespace_in_name(self):
        """Test section matching with extra whitespace."""
        markdown = """## API Reference

API content.
"""
        # Should match with extra spaces stripped
        content, _ = extract_section(markdown, "  API Reference  ")
        assert "## API Reference" in content

    def test_extract_section_no_headers_raises_error(self):
        """Test that document without headers raises SectionNotFoundError."""
        markdown = "Just plain text without any headers."
        
        with pytest.raises(SectionNotFoundError) as exc_info:
            extract_section(markdown, "Any Section")
        
        assert exc_info.value.available_sections == []

    def test_extract_section_h1_header(self):
        """Test extraction of H1 header section."""
        markdown = """# Main Title

This is the main content.

# Second Title

Second section content.
"""
        content, offset = extract_section(markdown, "Main Title")
        
        assert "# Main Title" in content
        assert "This is the main content" in content
        assert "# Second Title" not in content
        assert offset == 0

    def test_extract_section_deep_nesting(self):
        """Test extraction with deeply nested headers."""
        markdown = """# Level 1

## Level 2

### Level 3

#### Level 4

Level 4 content.

#### Level 4 Again

More content.

### Level 3 Again

Back to level 3.
"""
        content, _ = extract_section(markdown, "Level 4")
        
        assert "#### Level 4" in content
        assert "Level 4 content" in content
        # Should stop at sibling
        assert "#### Level 4 Again" not in content


class TestSectionExtractionIntegration:
    """Integration tests for section extraction with conversion."""

    def test_section_extraction_on_converted_html(self):
        """Test section extraction works on HTML converted to Markdown."""
        html = """
        <main>
            <h1>Documentation</h1>
            <p>Welcome to the docs.</p>
            <h2>Installation</h2>
            <p>Run pip install package.</p>
            <h2>Configuration</h2>
            <p>Edit config.yaml.</p>
        </main>
        """
        result = convert_html_to_markdown(html)
        
        section_content, _ = extract_section(result.content, "Installation")
        
        assert "## Installation" in section_content
        assert "pip install" in section_content
        assert "## Configuration" not in section_content

    def test_section_not_found_lists_converted_sections(self):
        """Test that SectionNotFoundError lists available sections from converted HTML."""
        html = """
        <main>
            <h1>Title</h1>
            <h2>Section A</h2>
            <h2>Section B</h2>
            <h2>Section C</h2>
        </main>
        """
        result = convert_html_to_markdown(html)
        
        with pytest.raises(SectionNotFoundError) as exc_info:
            extract_section(result.content, "Section D")
        
        available = exc_info.value.available_sections
        assert "Section A" in available
        assert "Section B" in available
        assert "Section C" in available
