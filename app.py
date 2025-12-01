import streamlit as st
import os
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Load API key from environment (Render uses env vars, not .env file)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Lazy imports - only import when needed
import pandas as pd
import google.generativeai as genai
from typing import List, Dict
from datetime import datetime
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

# Configure Gemini AI with API key (only if available)
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error(f"❌ Error configuring Gemini AI: {str(e)}")

# Streamlit page configuration
st.set_page_config(
    page_title="Sitemap Generator",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Sitemap Generator")
st.markdown("Upload a CSV file with questions and answers, and generate a detailed sitemap using Gemini AI")

# Sidebar for instructions
with st.sidebar:
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. Upload CSV file
    2. Select columns with questions and answers
    3. Click on 'Generate Sitemap'
    """)

# Function for parsing CSV
def parse_csv(file) -> pd.DataFrame:
    """Loads CSV file and returns DataFrame with better error handling"""
    
    # Reset file position to beginning
    file.seek(0)
    
    # Check if file is empty and find header row
    try:
        content = file.read()
        # If content is bytes, decode it
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except:
                try:
                    content = content.decode('latin-1')
                except:
                    content = content.decode('utf-8', errors='ignore')
        
        if not content or len(content.strip()) == 0:
            raise ValueError("CSV file is empty! Please upload a file with data.")
        
        # Find header row (row containing "Section" or "Question" or "Answer")
        lines = content.split('\n')
        header_row_index = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Search for header row containing typical columns for questionnaire CSV
            if any(keyword in line_lower for keyword in ['section', 'question', 'answer']):
                # Check if it has more than one column (not just a metadata row)
                if ',' in line and line.count(',') >= 2:
                    header_row_index = i
                    break
        
        if header_row_index is None:
            # If specific header not found, try to find any row with multiple columns
            for i, line in enumerate(lines):
                if ',' in line and line.count(',') >= 2:
                    header_row_index = i
                    break
        
        if header_row_index is None:
            # If specific header not found, try to parse from the beginning
            # Maybe the file is a standard CSV without metadata rows
            header_row_index = 0
        
        # Check if there is data after header row (if header is not at the beginning)
        if header_row_index > 0:
            data_lines = [line.strip() for line in lines[header_row_index + 1:] if line.strip()]
            if len(data_lines) < 1:
                raise ValueError("CSV file has no data after header row! Please check if the file contains data.")
        
    except Exception as e:
        if "empty" in str(e).lower() or "no data" in str(e).lower():
            raise
        # If error is not related to empty file, continue with header_row_index = 0
        if 'header_row_index' not in locals():
            header_row_index = 0
    
    # Reset position again
    file.seek(0)
    
    # List of parsing options (different delimiters and encodings)
    parse_options = [
        {'encoding': 'utf-8', 'delimiter': ','},
        {'encoding': 'utf-8', 'delimiter': ';'},
        {'encoding': 'utf-8', 'delimiter': '\t'},
        {'encoding': 'utf-8', 'delimiter': '|'},
        {'encoding': 'latin-1', 'delimiter': ','},
        {'encoding': 'latin-1', 'delimiter': ';'},
        {'encoding': 'iso-8859-1', 'delimiter': ','},
        {'encoding': 'cp1252', 'delimiter': ','},
    ]
    
    last_error = None
    
    for i, options in enumerate(parse_options):
        try:
            file.seek(0)  # Reset position for each attempt
            
            # Use header_row_index if found, otherwise try automatically
            skip_rows = header_row_index if header_row_index is not None else 0
            
            # Try with different options depending on pandas version
            try:
                # Latest pandas version
                df = pd.read_csv(
                    file,
                    encoding=options['encoding'],
                    delimiter=options['delimiter'],
                    skiprows=skip_rows,
                    on_bad_lines='skip',
                    engine='python'
                )
            except TypeError:
                try:
                    # Middle pandas version
                    df = pd.read_csv(
                        file,
                        encoding=options['encoding'],
                        delimiter=options['delimiter'],
                        skiprows=skip_rows,
                        error_bad_lines=False,
                        warn_bad_lines=False,
                        engine='python'
                    )
                except TypeError:
                    # Oldest version - without bad lines options
                    df = pd.read_csv(
                        file,
                        encoding=options['encoding'],
                        delimiter=options['delimiter'],
                        skiprows=skip_rows,
                        engine='python'
                    )
            
            # Check if it has columns
            if df.empty and len(df.columns) == 0:
                continue
                
            # Check if it has data
            if len(df.columns) == 0:
                raise ValueError("CSV file has no columns! Please check the file format.")
            
            # If DataFrame is empty but has columns, that's OK (maybe no data)
            return df
            
        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty or has no data! Please check if the file contains data.")
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue
    
    # If nothing works, try with automatic detection
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        if len(df.columns) > 0:
            return df
    except:
        pass
    
    # If everything fails, throw error with details
    error_msg = "Cannot parse CSV file. "
    if last_error:
        error_msg += f"Last error: {str(last_error)}. "
    error_msg += "Please check if the file is a valid CSV format with columns and data."
    raise ValueError(error_msg)

# Function for parsing XML sitemap
def parse_sitemap_xml(xml_content: str) -> List[Dict]:
    """Parses XML sitemap and returns list of URLs with metadata"""
    urls = []
    
    try:
        # Try with BeautifulSoup (better handling of bad XML)
        soup = BeautifulSoup(xml_content, 'xml')
        url_elements = soup.find_all('url')
        
        for url_elem in url_elements:
            loc = url_elem.find('loc')
            lastmod = url_elem.find('lastmod')
            changefreq = url_elem.find('changefreq')
            priority = url_elem.find('priority')
            
            if loc:
                url_data = {
                    'url': loc.get_text().strip(),
                    'lastmod': lastmod.get_text().strip() if lastmod else '',
                    'changefreq': changefreq.get_text().strip() if changefreq else '',
                    'priority': priority.get_text().strip() if priority else ''
                }
                urls.append(url_data)
    except:
        # Fallback na ElementTree
        try:
            root = ET.fromstring(xml_content)
            for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc is not None:
                    url_data = {
                        'url': loc.text.strip() if loc.text else '',
                        'lastmod': '',
                        'changefreq': '',
                        'priority': ''
                    }
                    lastmod = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    if lastmod is not None:
                        url_data['lastmod'] = lastmod.text.strip() if lastmod.text else ''
                    changefreq = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq')
                    if changefreq is not None:
                        url_data['changefreq'] = changefreq.text.strip() if changefreq.text else ''
                    priority = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
                    if priority is not None:
                        url_data['priority'] = priority.text.strip() if priority.text else ''
                    urls.append(url_data)
        except:
            # If nothing works, try regex
            url_pattern = r'<loc>(.*?)</loc>'
            matches = re.findall(url_pattern, xml_content)
            for match in matches:
                urls.append({
                    'url': match.strip(),
                    'lastmod': '',
                    'changefreq': '',
                    'priority': ''
                })
    
    return urls

# Function for creating visual tree HTML with nodes and connections
def create_visual_tree_html(urls: List[Dict]) -> str:
    """Creates visual node-based tree visualization of sitemap"""
    # Build tree structure
    tree = {}
    node_info = {}  # Store node metadata
    
    for url_data in urls:
        url = url_data['url']
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        current = tree
        current_path = []
        for part in path_parts:
            current_path.append(part)
            path_key = '/'.join(current_path)
            if part not in current:
                current[part] = {}
                node_info[path_key] = {
                    'name': part,
                    'path': path_key,
                    'depth': len(current_path),
                    'has_children': False
                }
            current = current[part]
            if path_key in node_info:
                node_info[path_key]['has_children'] = len(current) > 0
    
    # Build hierarchical structure for rendering
    all_nodes = {}
    connections = []
    
    def traverse_tree(node, parent_path="", parent_id=None, depth=0):
        if depth > 4:  # Limit depth for visualization
            return []
        
        level_nodes = []
        items = list(node.items())
        
        for i, (key, value) in enumerate(items):
            node_path = f"{parent_path}/{key}" if parent_path else key
            # Create unique ID
            node_id = f"node_{depth}_{i}_{key.replace('/', '_').replace(' ', '_')}"
            
            is_folder = isinstance(value, dict) and len(value) > 0
            
            node_data = {
                'id': node_id,
                'name': key,
                'path': node_path,
                'depth': depth,
                'is_folder': is_folder,
                'parent_id': parent_id,
                'children': []
            }
            
            all_nodes[node_id] = node_data
            
            if parent_id:
                connections.append({
                    'from': parent_id,
                    'to': node_id
                })
            
            if is_folder:
                children = traverse_tree(value, node_path, node_id, depth + 1)
                node_data['children'] = children
            
            level_nodes.append(node_data)
        
        return level_nodes
    
    root_nodes = traverse_tree(tree, "", "root", 0)
    
    # Generate HTML with SVG for connections
    html_parts = []
    html_parts.append("""
    <style>
        .sitemap-visual {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 30px;
            border-radius: 8px;
            min-height: 600px;
            position: relative;
            overflow: auto;
            width: 100%;
        }
        .sitemap-container {
            position: relative;
            min-width: 100%;
            min-height: 100%;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .sitemap-level {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            flex-wrap: wrap;
            gap: 15px;
            margin: 30px 0;
            position: relative;
            width: 100%;
            min-width: fit-content;
        }
        .sitemap-node {
            position: relative;
            padding: 10px 18px;
            border-radius: 8px;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            color: #fff;
            min-width: 100px;
            max-width: 180px;
            word-wrap: break-word;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
            white-space: normal;
            line-height: 1.3;
        }
        .sitemap-node:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.4);
            z-index: 10;
        }
        .node-root {
            background: #ff6b9d;
            color: #fff;
            font-weight: 700;
            font-size: 15px;
        }
        .node-level-0 {
            background: #ffa94d;
            color: #000;
        }
        .node-level-1 {
            background: #74c0fc;
            color: #000;
        }
        .node-level-2 {
            background: #adb5bd;
            color: #000;
        }
        .node-level-3 {
            background: #868e96;
            color: #fff;
        }
        .connection-line {
            stroke: #6c757d;
            stroke-width: 2;
            fill: none;
        }
        .svg-connections {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
        }
        .sitemap-level {
            z-index: 1;
            position: relative;
        }
    </style>
    <div class="sitemap-visual">
        <div class="sitemap-container" id="sitemapContainer">
    """)
    
    # Render nodes by level
    def render_level(nodes, level=0):
        if not nodes:
            return
        
        html_parts.append(f'<div class="sitemap-level" data-level="{level}">')
        
        for node in nodes:
            node_class = "node-root" if level == -1 else f"node-level-{min(level, 3)}"
            html_parts.append(f'<div class="sitemap-node {node_class}" id="{node["id"]}" data-name="{node["name"]}">{node["name"]}</div>')
        
        html_parts.append('</div>')
        
        # Render children
        for node in nodes:
            if node['children']:
                render_level(node['children'], level + 1)
    
    # Add root node
    html_parts.append('<div class="sitemap-level" data-level="-1">')
    html_parts.append('<div class="sitemap-node node-root" id="root" data-name="Homepage">Homepage</div>')
    html_parts.append('</div>')
    
    # Render all levels
    render_level(root_nodes, 0)
    
    # Add SVG for connections
    html_parts.append('<svg class="svg-connections" id="connectionsSvg"></svg>')
    html_parts.append('</div></div>')
    
    # Convert connections to JSON for JavaScript
    connections_json = json.dumps(connections)
    
    # JavaScript to draw connections
    html_parts.append(f"""
    <script>
        function drawConnections() {{
            const svg = document.getElementById('connectionsSvg');
            const container = document.getElementById('sitemapContainer');
            const connections = {connections_json};
            
            if (!svg || !container) return;
            
            // Clear existing lines
            svg.innerHTML = '';
            
            // Get container dimensions - use scrollWidth/scrollHeight for full content size
            const containerWidth = Math.max(container.scrollWidth, container.offsetWidth);
            const containerHeight = Math.max(container.scrollHeight, container.offsetHeight);
            
            svg.setAttribute('width', containerWidth);
            svg.setAttribute('height', containerHeight);
            
            // Get container's position relative to viewport
            const containerRect = container.getBoundingClientRect();
            const scrollLeft = container.scrollLeft || 0;
            const scrollTop = container.scrollTop || 0;
            
            connections.forEach(conn => {{
                const fromNode = document.getElementById(conn.from);
                const toNode = document.getElementById(conn.to);
                
                if (fromNode && toNode) {{
                    const fromRect = fromNode.getBoundingClientRect();
                    const toRect = toNode.getBoundingClientRect();
                    
                    // Calculate positions relative to container, accounting for scroll
                    const fromX = fromRect.left - containerRect.left + scrollLeft + fromRect.width / 2;
                    const fromY = fromRect.top - containerRect.top + scrollTop + fromRect.height;
                    const toX = toRect.left - containerRect.left + scrollLeft + toRect.width / 2;
                    const toY = toRect.top - containerRect.top + scrollTop;
                    
                    // Only draw if both nodes are visible or in the container bounds
                    if (fromX >= 0 && fromY >= 0 && toX >= 0 && toY >= 0) {{
                        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                        const midY = (fromY + toY) / 2;
                        const path = `M ${{fromX}} ${{fromY}} L ${{fromX}} ${{midY}} L ${{toX}} ${{midY}} L ${{toX}} ${{toY}}`;
                        line.setAttribute('d', path);
                        line.setAttribute('class', 'connection-line');
                        svg.appendChild(line);
                    }}
                }}
            }});
        }}
        
        // Draw connections after page load with multiple attempts
        function initConnections() {{
            setTimeout(drawConnections, 100);
            setTimeout(drawConnections, 300);
            setTimeout(drawConnections, 600);
            setTimeout(drawConnections, 1000);
        }}
        
        initConnections();
        
        // Redraw on scroll and resize
        const container = document.getElementById('sitemapContainer');
        if (container) {{
            container.addEventListener('scroll', drawConnections);
        }}
        window.addEventListener('resize', drawConnections);
        
        // Use MutationObserver to detect layout changes
        const observer = new MutationObserver(drawConnections);
        if (container) {{
            observer.observe(container, {{ 
                childList: true, 
                subtree: true, 
                attributes: true,
                attributeFilter: ['style', 'class']
            }});
        }}
    </script>
    """)
    
    return ''.join(html_parts)

# Function for creating folder tree structure
def create_folder_tree(urls: List[Dict]) -> str:
    """Creates folder tree structure as string"""
    tree = {}
    
    for url_data in urls:
        url = url_data['url']
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        current = tree
        for part in path_parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    
    # Create tree string
    tree_lines = []
    tree_lines.append("📁 /")
    
    def print_tree(node, prefix="", is_last=True, depth=0):
        """Recursively prints tree structure"""
        if depth > 6:  # Limit depth
            return
        
        if isinstance(node, dict):
            items = list(node.items())
            for i, (key, value) in enumerate(items):
                is_last_item = i == len(items) - 1
                connector = "└── " if is_last_item else "├── "
                
                # Add icon depending on whether it has children
                icon = "📁" if isinstance(value, dict) and value else "📄"
                tree_lines.append(prefix + connector + icon + " " + key)
                
                if isinstance(value, dict) and value:
                    extension = "    " if is_last_item else "│   "
                    print_tree(value, prefix + extension, is_last_item, depth + 1)
    
    print_tree(tree)
    
    return "\n".join(tree_lines)

# Function for extracting questions and answers
def extract_qa_pairs(df: pd.DataFrame, question_col: str, answer_col: str) -> List[Dict]:
    """Extracts question-answer pairs from DataFrame"""
    qa_pairs = []
    
    for idx, row in df.iterrows():
        question = str(row[question_col]) if pd.notna(row[question_col]) else ""
        answer = str(row[answer_col]) if pd.notna(row[answer_col]) else ""
        
        if question and answer and question.strip() and answer.strip():
            qa_pairs.append({
                "id": idx + 1,
                "question": question.strip(),
                "answer": answer.strip()
            })
    
    return qa_pairs

# Function for analysis with Gemini AI
def analyze_with_gemini(qa_pairs: List[Dict]) -> str:
    """Analyzes questions and answers using Gemini AI and generates sitemap"""
    
    if not GEMINI_API_KEY:
        raise ValueError("API key not found in .env file")
    
    # Prepare prompt
    qa_text = "\n\n".join([
        f"Question {pair['id']}: {pair['question']}\nAnswer: {pair['answer']}"
        for pair in qa_pairs[:50]  # Limit to first 50 due to token limit
    ])
    
    if len(qa_pairs) > 50:
        qa_text += f"\n\n... and {len(qa_pairs) - 50} more question-answer pairs."
    
    prompt = f"""You are creating a WEBSITE SITEMAP based on a client questionnaire. Your task is to generate ONLY the actual pages that the client needs for their website, NOT every possible option or feature mentioned in the questionnaire.

CRITICAL INSTRUCTIONS:
1. Focus on REAL PAGES that will exist on the website - not metadata, not features, not internal processes
2. DO NOT create pages for questionnaire options, form fields, or technical features (like "multilingual-support", "crm-functionalities", "backend-data", "event-tracking", etc.)
3. DO NOT create separate pages for languages (no /en, /de, /ru, /sr pages - languages are handled via URL parameters or subdomains, not separate pages)
4. Create pages only for actual CONTENT PAGES that visitors will navigate to
5. Keep the sitemap focused and practical - typically 10-30 pages for most websites, not 50+
6. Group related content logically into categories

Questions and answers from client questionnaire:
{qa_text}

Based on this questionnaire, generate a WEBSITE SITEMAP with ONLY the actual pages needed. 

IMPORTANT - Single Pages for Categories:
If the questionnaire mentions content categories like news, blog, products, projects, properties, services, etc., you MUST include:
1. The category listing page (e.g., /news, /blog, /products, /projects)
2. A single/detail page template (e.g., /news/single-news, /blog/single-post, /products/single-product, /projects/single-project)

This applies to ANY dynamic content category mentioned. Examples:
- If "news" is mentioned → include /news AND /news/single-news
- If "blog" is mentioned → include /blog AND /blog/single-post  
- If "products" is mentioned → include /products AND /products/single-product
- If "projects" is mentioned → include /projects AND /projects/single-project
- If "properties" is mentioned → include /properties AND /properties/single-property
- If "services" is mentioned → include /services AND /services/single-service

Examples of GOOD pages:
- /about-us
- /properties (category listing)
- /properties/apartments (subcategory)
- /properties/single-property (single page template)
- /news (category listing)
- /news/single-news (single page template)
- /contact
- /privacy-policy
- /blog (if blog is mentioned)
- /blog/single-post (if blog is mentioned)

Examples of BAD pages to avoid:
- /multilingual-support (this is a feature, not a page)
- /crm-functionalities (this is a feature, not a page)
- /backend-data (this is technical, not a page)
- /en, /de, /ru, /sr (languages are not separate pages)
- /website-features (this is metadata, not a page)
- /decision-criteria (this is questionnaire content, not a page)
- /website-design-goals (this is planning content, not a page)
- /evaluating-factors (this is questionnaire content, not a page)
- /customer-feedback (this is a feature/process, not a standalone page)
- /content-updates (this is a process, not a page)
- /broken-links (this is technical, not a page)
- /competitor-seo (this is analysis, not a page)
- /website-traffic (this is analytics, not a page)

IMPORTANT RULES:
1. If the questionnaire mentions things like "what are your goals" or "what features do you need", these are PLANNING QUESTIONS, not actual pages. Only create pages for actual content sections.
2. For ANY content category (news, blog, products, projects, properties, services, articles, events, etc.), always include BOTH the listing page AND a single/detail page template.
3. Keep the sitemap practical and focused - typically 15-40 pages for most websites, depending on the complexity.
4. Use clear, SEO-friendly URL structures (lowercase, hyphens, descriptive names).

The sitemap format MUST be valid XML:
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/category/page</loc>
    <lastmod>2024-01-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  ...
</urlset>

Requirements:
- Use only valid XML format
- Each <url> element must have <loc>, <lastmod>, <changefreq>, and <priority>
- URLs should be clean, SEO-friendly, and organized by categories
- <lastmod> format: YYYY-MM-DD (use current date: {datetime.now().strftime('%Y-%m-%d')})
- <changefreq> values: always, hourly, daily, weekly, monthly, yearly, never
- <priority> values: 0.0 to 1.0 (homepage: 1.0, main pages: 0.8, subpages: 0.6, less important: 0.4)

Generate a focused, practical sitemap with ONLY the actual website pages the client needs:"""

    try:
        # Try with Gemini 2.5 Flash (latest model)
        # First try with gemini-2.0-flash-exp (experimental, latest)
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            return response.text
        except:
            # Fallback to gemini-1.5-flash if 2.0 doesn't work
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        # Fallback to alternative models
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except:
            raise Exception(f"Error communicating with Gemini AI: {str(e)}")

# Main part of application
uploaded_file = st.file_uploader(
    "Upload CSV file",
    type=['csv'],
    help="Select a CSV file that contains questions and answers"
)

if uploaded_file is not None:
    # Show file info
    st.info(f"📄 File: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
    
    # Parse CSV with error handling
    try:
        df = parse_csv(uploaded_file)
        
        if df.empty:
            st.warning("⚠️ CSV file is loaded but empty (no rows with data).")
        else:
            st.success(f"✅ CSV file loaded! Total rows: {len(df)}")
    except Exception as e:
        st.error(f"❌ Error loading CSV file: {str(e)}")
        
        # Debug information
        with st.expander("🔍 Debug Information", expanded=False):
            st.write("**Error type:**", type(e).__name__)
            st.write("**Details:**", str(e))
            st.info("💡 **Tip:** Please check if the file is a valid CSV format with columns and data. Open the file in a text editor and check the format.")
        
        st.stop()  # Stop execution if file cannot be loaded
    
    # Display first rows
    with st.expander("📊 Data Preview", expanded=False):
        st.dataframe(df.head(10))
        st.info(f"Total columns: {len(df.columns)}")
        st.write("Columns:", list(df.columns))
    
    # Column selection
    st.subheader("🔍 Select Columns")
    
    col1, col2 = st.columns(2)
    
    with col1:
        question_column = st.selectbox(
            "Question column:",
            options=df.columns.tolist(),
            help="Select the column that contains questions"
        )
    
    with col2:
        answer_column = st.selectbox(
            "Answer column:",
            options=df.columns.tolist(),
            help="Select the column that contains answers"
        )
    
    # Generate button
    if st.button("🚀 Generate Sitemap", type="primary", use_container_width=True):
        if not GEMINI_API_KEY:
            st.error("❌ GEMINI_API_KEY not found in .env file! Please check the .env file.")
        else:
            with st.spinner("⏳ Analyzing questions and answers..."):
                try:
                    # Extract QA pairs
                    qa_pairs = extract_qa_pairs(df, question_column, answer_column)
                    
                    if not qa_pairs:
                        st.warning("⚠️ No valid question-answer pairs found!")
                    else:
                        st.info(f"📝 Found {len(qa_pairs)} question-answer pairs")
                        
                        # Analysis with Gemini AI
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("🤖 Communicating with Gemini AI...")
                        progress_bar.progress(30)
                        
                        sitemap = analyze_with_gemini(qa_pairs)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Sitemap generated!")
                        
                        # Display results
                        st.success("✅ Sitemap successfully generated!")
                        
                        # Parse sitemap for visualization
                        parsed_urls = parse_sitemap_xml(sitemap)
                        
                        # Tabs for displaying results
                        tab1, tab2, tab3, tab4 = st.tabs(["📄 XML Sitemap", "🗺️ Visual Sitemap", "📁 Structure", "📊 Statistics"])
                        
                        with tab1:
                            st.subheader("Generated XML Sitemap")
                            st.code(sitemap, language="xml")
                            
                            # Download button
                            st.download_button(
                                label="💾 Download Sitemap",
                                data=sitemap,
                                file_name=f"sitemap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                                mime="application/xml"
                            )
                        
                        with tab2:
                            st.subheader("🗺️ Visual Sitemap - Tree Structure")
                            if parsed_urls:
                                st.info(f"📊 Displaying {len(parsed_urls)} pages in tree structure")
                                
                                # Create visual tree
                                try:
                                    tree_html = create_visual_tree_html(parsed_urls)
                                    st.components.v1.html(tree_html, height=600, scrolling=True)
                                except Exception as e:
                                    st.error(f"Error creating tree: {str(e)}")
                                    st.info("Trying alternative display...")
                                    
                                    # Alternative display - formatted tree text
                                    tree_structure = create_folder_tree(parsed_urls)
                                    st.code(tree_structure, language="text")
                            else:
                                st.warning("⚠️ Cannot parse sitemap for visualization.")
                        
                        with tab3:
                            st.subheader("📁 Application Structure")
                            if parsed_urls:
                                st.info(f"📊 Displaying {len(parsed_urls)} pages in structure")
                                
                                # Create folder tree
                                try:
                                    tree_structure = create_folder_tree(parsed_urls)
                                    st.code(tree_structure, language="text")
                                    
                                    # Download tree structure
                                    st.download_button(
                                        label="💾 Download Structure",
                                        data=tree_structure,
                                        file_name=f"sitemap_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain"
                                    )
                                except Exception as e:
                                    st.error(f"Error creating structure: {str(e)}")
                                    
                                    # Alternative display
                                    st.markdown("### 📋 URL List:")
                                    for url_data in parsed_urls:
                                        st.markdown(f"- `{url_data['url']}`")
                            else:
                                st.warning("⚠️ Cannot parse sitemap for structure.")
                        
                        with tab4:
                            st.subheader("Statistics")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Total Questions", len(qa_pairs))
                            with col2:
                                st.metric("Total Pages", len(parsed_urls) if parsed_urls else 0)
                            with col3:
                                st.metric("Total CSV Rows", len(df))
                            
                            st.metric("CSV Columns", len(df.columns))
                            
                            # Display first few QA pairs
                            st.subheader("Sample Questions and Answers")
                            for i, pair in enumerate(qa_pairs[:5], 1):
                                with st.expander(f"Question {pair['id']}"):
                                    st.write("**Question:**", pair['question'])
                                    st.write("**Answer:**", pair['answer'][:200] + "..." if len(pair['answer']) > 200 else pair['answer'])
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)

else:
    st.info("👆 Please upload a CSV file to get started")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Sitemap Generator - Powered by Gemini AI</div>",
    unsafe_allow_html=True
)

