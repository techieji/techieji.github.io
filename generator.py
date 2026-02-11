#!/usr/bin/env python3
"""
Portfolio Generator Script
Converts markdown file to HTML with visible markdown syntax styling using markdown library
Includes syntax highlighting for code blocks
"""

import sys
import re
import markdown
from markdown.treeprocessors import Treeprocessor
from markdown.extensions import Extension
from xml.etree import ElementTree as etree
from html.parser import HTMLParser

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    print("Warning: Pygments not installed. Install with: pip install pygments")
    print("Code blocks will not have syntax highlighting.")


class VimStyleFormatter(HtmlFormatter):
    """Custom Pygments formatter with Vim-style color classes"""
    
    def _get_css_class(self, ttype):
        """Map token type to CSS class"""
        token_class_map = {
            Token.Comment: 'syn-comment',
            Token.Comment.Single: 'syn-comment',
            Token.Comment.Multiline: 'syn-comment',
            Token.Comment.Preproc: 'syn-comment',
            Token.String: 'syn-string',
            Token.String.Double: 'syn-string',
            Token.String.Single: 'syn-string',
            Token.String.Doc: 'syn-comment',
            Token.Number: 'syn-number',
            Token.Number.Integer: 'syn-number',
            Token.Number.Float: 'syn-number',
            Token.Keyword: 'syn-keyword',
            Token.Keyword.Constant: 'syn-constant',
            Token.Keyword.Declaration: 'syn-keyword',
            Token.Keyword.Namespace: 'syn-keyword',
            Token.Keyword.Type: 'syn-keyword',
            Token.Name.Function: 'syn-function',
            Token.Name.Class: 'syn-class',
            Token.Name.Builtin: 'syn-builtin',
            Token.Name.Builtin.Pseudo: 'syn-builtin',
            Token.Operator: 'syn-operator',
            Token.Name: 'syn-variable',
        }
        
        while ttype:
            if ttype in token_class_map:
                return token_class_map[ttype]
            ttype = ttype.parent
        return ''
    
    def _format_lines(self, tokensource):
        """Format tokens with custom classes"""
        for ttype, value in tokensource:
            css_class = self._get_css_class(ttype)
            if css_class:
                yield 1, f'<span class="{css_class}">{value}</span>'
            else:
                yield 1, value

def add_indent_guides_to_html(html_content):
    """Add indent guides to HTML content"""
    lines = html_content.split('\n')
    result = []
    
    for line in lines:
        # Count leading spaces in the plain text
        plain_text = re.sub(r'<[^>]+>', '', line)
        indent_level = len(plain_text) - len(plain_text.lstrip(' '))
        
        # Create guides for every 4 spaces
        guides = []
        for i in range(4, indent_level + 1, 4):
            guides.append(f'<span class="md-codeblock-indent" style="left: {i * 0.6}em;"></span>')
        
        guide_html = ''.join(guides)
        result.append(f'<div class="md-codeblock-line">{guide_html}{line}</div>')
    
    return '\n'.join(result)


class VisibleSyntaxTreeprocessor(Treeprocessor):
    """
    Post-process the markdown tree to add visible syntax elements
    """
    
    def __init__(self, md):
        super().__init__(md)
        self.code_blocks = {}  # Store code blocks to process separately
        self.code_counter = 0
    
    def run(self, root):
        self.process_element(root)
        return root
    
    def process_element(self, element):
        """Recursively process elements to add visible syntax"""
        
        # Process children first (bottom-up to handle nested structures)
        for child in list(element):
            self.process_element(child)
        
        # Process code blocks (pre > code)
        # if element.tag == 'pre':
        if element.tag == 'p':
            code_elem = element.find('code')
            if code_elem is not None:
                code_text = ''.join(code_elem.itertext())
                
                if PYGMENTS_AVAILABLE and code_text.strip():
                    # Try to detect language from class attribute
                    lang = None
                    if 'class' in code_elem.attrib:
                        classes = code_elem.attrib['class'].split()
                        for cls in classes:
                            if cls.startswith('language-'):
                                lang = cls.replace('language-', '')
                                break
                    
                    # Syntax highlight the code
                    try:
                        if lang:
                            try:
                                lexer = get_lexer_by_name(lang, stripall=False)
                            except:
                                lexer = TextLexer()
                        else:
                            try:
                                lexer = guess_lexer(code_text)
                            except:
                                lexer = TextLexer()
                        
                        #formatter = VimStyleFormatter(nowrap=True, noclasses=False)
                        formatter = HtmlFormatter(classprefix='syn')
                        print("here")
                        highlighted = highlight(code_text, lexer, formatter)
                        
                        # Add indent guides
                        final_html = add_indent_guides_to_html(highlighted)
                        
                        # Store placeholder and remember the HTML
                        placeholder_id = f'__CODE_BLOCK_{self.code_counter}__'
                        self.code_blocks[placeholder_id] = final_html
                        self.code_counter += 1
                        
                        # Replace element with placeholder
                        element.clear()
                        element.tag = 'div'
                        element.set('class', 'md-codeblock')
                        element.set('data-placeholder', placeholder_id)
                        element.text = placeholder_id
                        
                    except Exception as e:
                        print(f"Warning: Could not highlight code: {e}")
                        import traceback
                        traceback.print_exc()
                
                return
        
        # Process headings
        if element.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(element.tag[1])
            hashes = '#' * level
            
            # Create new structure
            div = etree.Element('div')
            div.set('class', 'md-heading')
            
            hash_span = etree.Element('span')
            hash_span.set('class', 'md-hash')
            hash_span.text = hashes
            hash_span.tail = ' '
            div.append(hash_span)
            
            # Move text and all children
            if element.text:
                if len(div) > 0:
                    div[-1].tail = (div[-1].tail or '') + element.text
                else:
                    div.text = element.text
            
            for child in list(element):
                div.append(child)
            
            # Replace element
            element.clear()
            element.tag = 'div'
            element.append(div)
            return
        
        # Process blockquotes
        if element.tag == 'blockquote':
            # Get all paragraphs in blockquote
            paragraphs = element.findall('.//p')
            
            if paragraphs:
                # Wrap first paragraph specially
                for p in paragraphs:
                    new_div = etree.Element('div')
                    new_div.set('class', 'md-blockquote')
                    
                    marker = etree.Element('span')
                    marker.set('class', 'md-quote-marker')
                    marker.text = '>'
                    marker.tail = ' '
                    new_div.append(marker)
                    
                    text_span = etree.Element('span')
                    text_span.set('class', 'md-quote-text')
                    
                    if p.text:
                        text_span.text = p.text
                    
                    for child in list(p):
                        text_span.append(child)
                    
                    new_div.append(text_span)
                    
                    # Replace paragraph with div
                    parent = element
                    for i, child in enumerate(parent):
                        if child == p:
                            parent[i] = new_div
                            break
        
        # Process lists
        if element.tag in ['ul', 'ol']:
            # Only add class if not already present (avoid nested list issues)
            if 'class' not in element.attrib:
                element.set('class', 'md-list')
            
            # Process direct children only
            for i, li in enumerate([child for child in element if child.tag == 'li']):
                if 'class' not in li.attrib:
                    li.set('class', 'md-list-item')
                    
                    # Add bullet or number marker
                    marker = etree.Element('span')
                    if element.tag == 'ul':
                        marker.set('class', 'md-bullet')
                        marker.text = '*'
                    else:
                        marker.set('class', 'md-number')
                        marker.text = f'{i + 1}.'
                    
                    marker.tail = ' '
                    
                    # Insert marker at the very beginning
                    li.insert(0, marker)
                    if li.text:
                        marker.tail = (marker.tail or '') + li.text
                        li.text = None
        
        # Process inline elements (em, strong, code)
        if element.tag == 'em':
            self.wrap_with_syntax(element, '*', '*', 'md-asterisk', 'md-italic')
            return
        
        if element.tag == 'strong':
            self.wrap_with_syntax(element, '**', '**', 'md-double-asterisk', 'md-bold')
            return
        
        if element.tag == 'code':
            # Only process inline code (not code blocks)
            parent_tag = None
            if hasattr(element, '_parent_tag'):
                parent_tag = element._parent_tag
            
            # Simple heuristic: if parent is not 'pre', treat as inline
            self.wrap_with_syntax(element, '`', '`', 'md-backtick', 'md-code')
            return
    
    def wrap_with_syntax(self, element, prefix, suffix, prefix_class, content_class):
        """Wrap an element with visible syntax markers"""
        original_text = element.text or ''
        original_tail = element.tail or ''
        original_children = list(element)
        
        element.clear()
        element.tag = 'span'
        
        # Before marker
        before = etree.Element('span')
        before.set('class', prefix_class)
        before.text = prefix
        element.append(before)
        
        # Content wrapper
        inner = etree.Element('span')
        inner.set('class', content_class)
        inner.text = original_text
        
        for child in original_children:
            inner.append(child)
        
        element.append(inner)
        
        # After marker
        after = etree.Element('span')
        after.set('class', prefix_class)  # Use prefix_class for suffix as well (both should be same)
        after.text = suffix
        after.tail = original_tail
        element.append(after)


class VisibleSyntaxExtension(Extension):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processor = None
    
    def extendMarkdown(self, md):
        self.processor = VisibleSyntaxTreeprocessor(md)
        md.treeprocessors.register(self.processor, 'visible_syntax', 0)


def generate_portfolio(markdown_file, template_file='template.html', output_file='index.html'):
    """
    Generate portfolio HTML from markdown file
    """
    # Read markdown content
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"Error: Markdown file '{markdown_file}' not found.")
        sys.exit(1)
    
    # Read template
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Error: Template file '{template_file}' not found.")
        sys.exit(1)
    
    # Parse markdown with custom extension
    ext = VisibleSyntaxExtension()
    md = markdown.Markdown(extensions=[ext, 'fenced_code', 'codehilite'])
    html_content = md.convert(md_content)
    
    # Replace code block placeholders with actual HTML
    if ext.processor:
        for placeholder_id, code_html in ext.processor.code_blocks.items():
            html_content = html_content.replace(placeholder_id, code_html)
    
    # Inject content into template
    final_html = template.replace('{{CONTENT}}', html_content)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Portfolio generated successfully: {output_file}")
    print(f"\nTo view: open {output_file} in your browser")
    print(f"Note: Make sure styles.css, script.js, and your photo are in the same directory")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate.py <markdown_file> [template_file] [output_file]")
        print("Example: python generate.py content.md")
        print("\nRequires: pip install markdown")
        print("Optional (for syntax highlighting): pip install pygments")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    template_file = sys.argv[2] if len(sys.argv) > 2 else 'template.html'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'index.html'
    
    generate_portfolio(markdown_file, template_file, output_file)
