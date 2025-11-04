#!/usr/bin/env python3
"""
Enhanced Website HTML Comparison Tool with Side-by-Side Visualization
Compares two HTML files and creates an interactive side-by-side view with highlighted differences
"""

import sys
from bs4 import BeautifulSoup
from difflib import SequenceMatcher, unified_diff
import re
from urllib.parse import urljoin, urlparse
import html
import difflib

def load_html_from_file(filepath):
    """Load and parse HTML from a file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return BeautifulSoup(content, 'html.parser')
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def extract_content_after_marker(soup, marker_text):
    """Extract all content after a specific marker text."""
    if not soup:
        return None
    
    # Find elements containing the marker
    found_elements = []
    for element in soup.find_all(['b', 'strong', 'h1', 'h2', 'h3', 'h4', 'p', 'font']):
        if marker_text.lower() in element.get_text().lower():
            found_elements.append(element)
    
    if not found_elements:
        print(f"Warning: Marker '{marker_text}' not found in page")
        # Return body content as fallback
        return soup.body if soup.body else soup
    
    # Use the first found marker
    marker_elem = found_elements[0]
    print(f"   Found marker in <{marker_elem.name}> tag")
    
    # Collect all content after the marker
    # Strategy: find the parent container and get all siblings after it
    current = marker_elem
    
    # Walk up to find a good container (p, div, td, etc)
    while current.parent and current.parent.name not in ['body', 'html', None]:
        if current.parent.name in ['td', 'div', 'body']:
            break
        current = current.parent
    
    # Now collect everything after current element
    content_elements = []
    for sibling in current.find_next_siblings():
        content_elements.append(sibling)
    
    # If nothing found, try parent level
    if not content_elements and current.parent:
        parent = current.parent
        for sibling in parent.find_next_siblings():
            content_elements.append(sibling)
    
    # Create a container div to hold all content
    container = soup.new_tag('div')
    for elem in content_elements:
        # Deep copy to avoid modifying original
        container.append(elem)
    
    return container

def extract_text_blocks(element):
    """Extract text organized by HTML structure for better comparison."""
    blocks = []
    
    if not element:
        return blocks
    
    # Process each major element
    for child in element.descendants:
        if child.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'div']:
            text = child.get_text(strip=True)
            if text and len(text) > 10:  # Filter out very short text
                blocks.append({
                    'tag': child.name,
                    'text': text,
                    'html': str(child)
                })
    
    return blocks

def extract_links(element):
    """Extract all links from an element."""
    links = []
    if not element:
        return links
    
    for link in element.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True)
        links.append({
            'url': href,
            'text': text,
            'html': str(link)
        })
    
    return links

def normalize_url(url, base_url=''):
    """Normalize a URL for comparison."""
    if url.startswith('http://') or url.startswith('https://'):
        absolute_url = url
    elif base_url:
        absolute_url = urljoin(base_url, url)
    else:
        absolute_url = url
    
    parsed = urlparse(absolute_url)
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    
    return normalized.rstrip('/').lower()

def compare_links(links1, links2, base_url1='', base_url2=''):
    """Compare two sets of links."""
    norm_links1 = {}
    for link in links1:
        try:
            norm_url = normalize_url(link['url'], base_url1)
            norm_links1[norm_url] = link
        except:
            pass
    
    norm_links2 = {}
    for link in links2:
        try:
            norm_url = normalize_url(link['url'], base_url2)
            norm_links2[norm_url] = link
        except:
            pass
    
    keys1 = set(norm_links1.keys())
    keys2 = set(norm_links2.keys())
    
    only_in_1 = keys1 - keys2
    only_in_2 = keys2 - keys1
    in_both = keys1 & keys2
    
    return {
        'only_in_v1': sorted([norm_links1[k] for k in only_in_1], key=lambda x: x.get('text', '')),
        'only_in_v2': sorted([norm_links2[k] for k in only_in_2], key=lambda x: x.get('text', '')),
        'in_both': sorted([norm_links1[k] for k in in_both], key=lambda x: x.get('text', '')),
        'total_v1': len(keys1),
        'total_v2': len(keys2)
    }

def generate_side_by_side_html(content1, content2):
    """Generate side-by-side HTML with diff highlighting."""
    if not content1 or not content2:
        return "<p>No content to compare</p>", "<p>No content to compare</p>"
    
    # Get the HTML strings
    html1 = str(content1)
    html2 = str(content2)
    
    # Split into lines for comparison
    lines1 = html1.split('\n')
    lines2 = html2.split('\n')
    
    # Use difflib to generate HTML diff
    differ = difflib.HtmlDiff(wrapcolumn=80)
    diff_table = differ.make_table(lines1, lines2, 
                                   fromdesc='Version 1',
                                   todesc='Version 2',
                                   context=True,
                                   numlines=3)
    
    return diff_table

def generate_text_diff_view(text1, text2):
    """Generate a character-level diff visualization."""
    matcher = SequenceMatcher(None, text1, text2)
    
    result_v1 = []
    result_v2 = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        text1_part = text1[i1:i2]
        text2_part = text2[j1:j2]
        
        if tag == 'equal':
            result_v1.append(html.escape(text1_part))
            result_v2.append(html.escape(text2_part))
        elif tag == 'delete':
            result_v1.append(f'<span class="diff-removed">{html.escape(text1_part)}</span>')
        elif tag == 'insert':
            result_v2.append(f'<span class="diff-added">{html.escape(text2_part)}</span>')
        elif tag == 'replace':
            result_v1.append(f'<span class="diff-changed">{html.escape(text1_part)}</span>')
            result_v2.append(f'<span class="diff-changed">{html.escape(text2_part)}</span>')
    
    return ''.join(result_v1), ''.join(result_v2)

def calculate_similarity(text1, text2):
    """Calculate similarity between two texts."""
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()

def generate_enhanced_report(file1, file2, content1, content2, links1, links2, 
                            link_comparison, text1, text2, marker):
    """Generate an enhanced HTML report with side-by-side comparison."""
    
    similarity = calculate_similarity(text1, text2)
    
    # Generate diff views
    v1_diff, v2_diff = generate_text_diff_view(text1[:5000], text2[:5000])
    
    html_output = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Side-by-Side HTML Comparison</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        
        .header p {{
            margin: 5px 0;
            opacity: 0.9;
        }}
        
        .container {{
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .stats-bar {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .stat-box {{
            text-align: center;
            padding: 15px 25px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 8px;
            min-width: 140px;
        }}
        
        .stat-label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .similarity-bar {{
            width: 100%;
            height: 40px;
            background: #e0e0e0;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
        }}
        
        .similarity-fill {{
            height: 100%;
            background: linear-gradient(90deg, #e74c3c 0%, #f39c12 30%, #f1c40f 50%, #2ecc71 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.1em;
            transition: width 1s ease;
        }}
        
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .tab {{
            padding: 12px 25px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .tab:hover {{
            background: #e0e0e0;
        }}
        
        .tab.active {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .tab-content {{
            display: none;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .version-panel {{
            background: #fafafa;
            border-radius: 10px;
            padding: 20px;
            border: 2px solid #e0e0e0;
        }}
        
        .version-panel.v1 {{
            border-left: 4px solid #e74c3c;
        }}
        
        .version-panel.v2 {{
            border-left: 4px solid #2ecc71;
        }}
        
        .panel-header {{
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        
        .version-panel.v1 .panel-header {{
            color: #e74c3c;
        }}
        
        .version-panel.v2 .panel-header {{
            color: #2ecc71;
        }}
        
        .content-box {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .diff-removed {{
            background: #ffecec;
            color: #c0392b;
            padding: 2px 4px;
            border-radius: 3px;
            text-decoration: line-through;
        }}
        
        .diff-added {{
            background: #e8f5e9;
            color: #27ae60;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: 600;
        }}
        
        .diff-changed {{
            background: #fff3cd;
            color: #856404;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        .link-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .link-item {{
            padding: 12px;
            margin: 8px 0;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #3498db;
            transition: all 0.3s ease;
        }}
        
        .link-item:hover {{
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .link-item.removed {{
            border-left-color: #e74c3c;
            background: #ffebee;
        }}
        
        .link-item.added {{
            border-left-color: #2ecc71;
            background: #e8f5e9;
        }}
        
        .link-text {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 4px;
        }}
        
        .link-url {{
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            color: #7f8c8d;
            word-break: break-all;
        }}
        
        .section-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin: 30px 0 15px 0;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 10px;
        }}
        
        .badge-danger {{
            background: #e74c3c;
            color: white;
        }}
        
        .badge-success {{
            background: #2ecc71;
            color: white;
        }}
        
        .badge-info {{
            background: #3498db;
            color: white;
        }}
        
        table.diff {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        
        table.diff td {{
            padding: 4px 8px;
            vertical-align: top;
        }}
        
        table.diff .diff_header {{
            background: #e0e0e0;
            font-weight: bold;
            text-align: center;
        }}
        
        table.diff .diff_next {{
            background: #f0f0f0;
        }}
        
        .note {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        
        .legend {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-box {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .scrollable-section {{
            max-height: 500px;
            overflow-y: auto;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Side-by-Side HTML Comparison</h1>
        <p><strong>File 1:</strong> {html.escape(file1)}</p>
        <p><strong>File 2:</strong> {html.escape(file2)}</p>
        <p><strong>Marker:</strong> {html.escape(marker)}</p>
        <p><strong>Generated:</strong> {html.escape(str(__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')))}</p>
    </div>
    
    <div class="container">
        <div class="stats-bar">
            <div class="stat-box">
                <div class="stat-label">Text Similarity</div>
                <div class="stat-value">{similarity:.1%}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Links V1</div>
                <div class="stat-value">{link_comparison['total_v1']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Links V2</div>
                <div class="stat-value">{link_comparison['total_v2']}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Common</div>
                <div class="stat-value">{len(link_comparison['in_both'])}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Removed</div>
                <div class="stat-value">{len(link_comparison['only_in_v1'])}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Added</div>
                <div class="stat-value">{len(link_comparison['only_in_v2'])}</div>
            </div>
        </div>
        
        <div class="similarity-bar">
            <div class="similarity-fill" style="width: {similarity * 100}%">
                {similarity:.1%} Similar
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('side-by-side')">📊 Side-by-Side Text</button>
            <button class="tab" onclick="showTab('links')">🔗 Links Comparison</button>
            <button class="tab" onclick="showTab('html-diff')">💻 HTML Diff</button>
            <button class="tab" onclick="showTab('full-text')">📝 Full Text</button>
        </div>
        
        <div id="side-by-side" class="tab-content active">
            <h2 class="section-title">Side-by-Side Text Comparison</h2>
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-box diff-removed"></div>
                    <span>Removed from V1</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box diff-added"></div>
                    <span>Added in V2</span>
                </div>
                <div class="legend-item">
                    <div class="legend-box diff-changed"></div>
                    <span>Changed</span>
                </div>
            </div>
            
            <div class="comparison-grid">
                <div class="version-panel v1">
                    <div class="panel-header">📄 Version 1 (Original)</div>
                    <div class="content-box">
{v1_diff}
                    </div>
                </div>
                
                <div class="version-panel v2">
                    <div class="panel-header">📄 Version 2 (Updated)</div>
                    <div class="content-box">
{v2_diff}
                    </div>
                </div>
            </div>
        </div>
        
        <div id="links" class="tab-content">
            <h2 class="section-title">Links Comparison</h2>
            
            <div class="comparison-grid">
                <div class="version-panel v1">
                    <div class="panel-header">
                        ❌ Removed Links
                        <span class="badge badge-danger">{len(link_comparison['only_in_v1'])}</span>
                    </div>
                    <div class="scrollable-section">
                        <ul class="link-list">
                            {''.join(f'<li class="link-item removed"><div class="link-text">{html.escape(link.get("text", "(no text)"))}</div><div class="link-url">🔗 {html.escape(link["url"])}</div></li>' for link in link_comparison['only_in_v1']) if link_comparison['only_in_v1'] else '<li class="link-item">No links removed</li>'}
                        </ul>
                    </div>
                </div>
                
                <div class="version-panel v2">
                    <div class="panel-header">
                        ✅ Added Links
                        <span class="badge badge-success">{len(link_comparison['only_in_v2'])}</span>
                    </div>
                    <div class="scrollable-section">
                        <ul class="link-list">
                            {''.join(f'<li class="link-item added"><div class="link-text">{html.escape(link.get("text", "(no text)"))}</div><div class="link-url">🔗 {html.escape(link["url"])}</div></li>' for link in link_comparison['only_in_v2']) if link_comparison['only_in_v2'] else '<li class="link-item">No links added</li>'}
                        </ul>
                    </div>
                </div>
            </div>
            
            <h3 class="section-title">
                ↔️ Common Links
                <span class="badge badge-info">{len(link_comparison['in_both'])}</span>
            </h3>
            <div class="scrollable-section">
                <ul class="link-list">
                    {''.join(f'<li class="link-item"><div class="link-text">{html.escape(link.get("text", "(no text)"))}</div><div class="link-url">🔗 {html.escape(link["url"])}</div></li>' for link in link_comparison['in_both'][:50])}
                    {f'<li class="link-item">... and {len(link_comparison["in_both"]) - 50} more</li>' if len(link_comparison['in_both']) > 50 else ''}
                </ul>
            </div>
        </div>
        
        <div id="html-diff" class="tab-content">
            <h2 class="section-title">HTML Source Diff</h2>
            <div class="note">
                <strong>Note:</strong> This shows a line-by-line comparison of the HTML source code.
                Colors indicate additions, deletions, and changes.
            </div>
            <div style="overflow-x: auto;">
                {generate_side_by_side_html(content1, content2)}
            </div>
        </div>
        
        <div id="full-text" class="tab-content">
            <h2 class="section-title">Full Text Content</h2>
            
            <div class="comparison-grid">
                <div class="version-panel v1">
                    <div class="panel-header">📄 Version 1 Full Text</div>
                    <div class="content-box">
{html.escape(text1)}
                    </div>
                </div>
                
                <div class="version-panel v2">
                    <div class="panel-header">📄 Version 2 Full Text</div>
                    <div class="content-box">
{html.escape(text2)}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            // Remove active class from all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
"""
    
    return html_output

def extract_text(element):
    """Extract text from element."""
    if not element:
        return ""
    return element.get_text(separator='\n', strip=True)

def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_html_sidebyside.py <file1.html> <file2.html> [marker_text]")
        print("\nExample:")
        print("  python compare_html_sidebyside.py version1.html version2.html \"Course Syllabus\"")
        return
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    marker = sys.argv[3] if len(sys.argv) > 3 else "Course Syllabus"
    
    print("🔍 Side-by-Side HTML Comparison Tool")
    print("=" * 80)
    print()
    
    print("📥 Loading HTML files...")
    soup1 = load_html_from_file(file1)
    soup2 = load_html_from_file(file2)
    
    if not soup1 or not soup2:
        print("❌ Error: Could not load one or both files")
        return
    
    print(f"   ✓ Loaded {file1}")
    print(f"   ✓ Loaded {file2}")
    
    print(f"\n📋 Extracting content after marker: '{marker}'...")
    content1 = extract_content_after_marker(soup1, marker)
    content2 = extract_content_after_marker(soup2, marker)
    
    print("\n🔗 Extracting links...")
    links1 = extract_links(content1)
    links2 = extract_links(content2)
    
    print(f"   Version 1: {len(links1)} links found")
    print(f"   Version 2: {len(links2)} links found")
    
    print("\n📝 Extracting text...")
    text1 = extract_text(content1)
    text2 = extract_text(content2)
    
    print(f"   Version 1: {len(text1):,} characters")
    print(f"   Version 2: {len(text2):,} characters")
    
    print("\n⚖️  Comparing links...")
    link_comparison = compare_links(links1, links2)
    
    print(f"   Only in V1: {len(link_comparison['only_in_v1'])}")
    print(f"   Only in V2: {len(link_comparison['only_in_v2'])}")
    print(f"   In both: {len(link_comparison['in_both'])}")
    
    print("\n📄 Generating side-by-side report...")
    report = generate_enhanced_report(
        file1, file2, content1, content2,
        links1, links2, link_comparison,
        text1, text2, marker
    )
    
    output_file = "/mnt/user-data/outputs/sidebyside_comparison.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    similarity = calculate_similarity(text1, text2)
    
    print(f"✅ Report saved to: {output_file}")
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Text Similarity:          {similarity:.1%}")
    print(f"Links removed (V1→V2):    {len(link_comparison['only_in_v1'])}")
    print(f"Links added (V1→V2):      {len(link_comparison['only_in_v2'])}")
    print(f"Links unchanged:          {len(link_comparison['in_both'])}")
    print(f"Total changes:            {len(link_comparison['only_in_v1']) + len(link_comparison['only_in_v2'])}")
    print("="*80)
    print("\n💡 Open the HTML file in your browser to see the interactive side-by-side comparison!")

if __name__ == "__main__":
    main()
