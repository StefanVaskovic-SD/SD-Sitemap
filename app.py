import streamlit as st
import os
import base64
import urllib.request
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

# Custom CSS to expand sidebar width, style download button, and hide permalink
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        min-width: 380px !important;
        max-width: 380px !important;
    }
    /* Style download button to look like inline link */
    div[data-testid="stDownloadButton"] button {
        background: transparent !important;
        border: none !important;
        color: #1f77b4 !important;
        text-decoration: underline !important;
        padding: 0 !important;
        font-size: inherit !important;
        box-shadow: none !important;
        height: auto !important;
        margin: 0 !important;
        display: inline !important;
        font-weight: normal !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        color: #0d5a8a !important;
        background: transparent !important;
        text-decoration: underline !important;
    }
    /* Hide permalink/anchor link next to H1 */
    [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    /* Remove ID from H1 */
    h1[id] {
        scroll-margin-top: 0;
    }
    /* Hide file size limit text below file uploader */
    div[data-testid="stFileUploader"] > div > small {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🗺️ Sitemap Generator")
st.markdown("Generate a sitemap based on answers in the Discovery questionnaire.")

# Sidebar for instructions
with st.sidebar:
    st.markdown("### 📋 Instructions")
    
    # CSV URL for download link
    csv_url = "https://cdn.prod.website-files.com/69316d64cadab5d24822f841/694e78594d8da777e4cbf125_questionnaire-kolasin-valleys-website.csv"
    
    # Fetch CSV content from URL for download
    try:
        with urllib.request.urlopen(csv_url) as response:
            example_csv = response.read().decode('utf-8')
        # Create base64 encoded data URL for download
        b64_csv = base64.b64encode(example_csv.encode()).decode()
        download_link = f'<a href="data:text/csv;base64,{b64_csv}" download="questionnaire-kolasin-valleys-website.csv" style="color: #1f77b4; text-decoration: underline; cursor: pointer;">questionnaire csv</a>'
    except Exception:
        # Fallback to direct URL link
        download_link = f'<a href="{csv_url}" download="questionnaire-kolasin-valleys-website.csv" style="color: #1f77b4; text-decoration: underline; cursor: pointer;">questionnaire csv</a>'
    
    st.markdown(f"""
**Step 1: Prepare .csv file**

- If you're starting from scratch and you haven't used any other Studio Direction tool:
  - Prepare the questions and answers from your existing questionnaire (Word, PDF, email, notes, etc.).
  - Paste that content into the AI and upload the {download_link} as an example and use this prompt:
    """, unsafe_allow_html=True)
    
    st.code("""Could you return this content in a CSV file, where questions are in column A and answers are in column B? Please also add a header row with the column names: "question" and "answer". Use uploaded csv as an example.""", language=None)
    
    st.markdown("""
  - Download and save the .csv file that the AI returns.

- If you already have the file from some other Studio Direction tool skip step 1.

**Step 2: Import your data**

- Drag and drop or upload the .csv file here on the right.

**Step 3: Setup**

- Select the columns that contain questions and answers.

**Step 4: Generate and download the sitemap**

- Click button Generate Sitemap.
- Download the generated XML sitemap.
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
    
    # Generate HTML with SVG for connections - hierarchical layout
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
        }
        .sitemap-node-wrapper {
            position: relative;
            display: inline-block;
            margin: 20px 15px;
            vertical-align: top;
        }
        .sitemap-node {
            position: relative;
            padding: 8px 14px;
            border-radius: 6px;
            text-align: center;
            font-size: 12px;
            font-weight: 500;
            color: #fff;
            min-width: 90px;
            max-width: 150px;
            word-wrap: break-word;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
            white-space: normal;
            line-height: 1.3;
            z-index: 2;
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
            font-size: 14px;
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
        .node-children {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            justify-content: center;
            align-items: flex-start;
            margin-top: 20px;
            padding-top: 10px;
            position: relative;
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
            z-index: 1;
        }
        .sitemap-tree-root {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            width: 100%;
        }
    </style>
    <div class="sitemap-visual">
        <div class="sitemap-container" id="sitemapContainer">
    """)
    
    # Render nodes hierarchically - each parent with its children directly below
    def render_node_hierarchical(node, level=0, parent_id=None):
        node_class = "node-root" if level == -1 else f"node-level-{min(level, 3)}"
        node_id = node['id'] if level >= 0 else 'root'
        node_name = node['name'] if level >= 0 else 'Homepage'
        
        html_parts.append(f'<div class="sitemap-node-wrapper" id="wrapper_{node_id}">')
        html_parts.append(f'<div class="sitemap-node {node_class}" id="{node_id}" data-name="{node_name}" data-level="{level}">{node_name}</div>')
        
        if node.get('children'):
            html_parts.append('<div class="node-children">')
            for child in node['children']:
                render_node_hierarchical(child, level + 1, node_id)
            html_parts.append('</div>')
        
        html_parts.append('</div>')
    
    # Render root and all nodes hierarchically
    html_parts.append('<div class="sitemap-tree-root">')
    root_node_data = {
        'id': 'root',
        'name': 'Homepage',
        'children': root_nodes,
        'depth': -1
    }
    render_node_hierarchical(root_node_data, -1)
    html_parts.append('</div>')
    
    # Add SVG for connections
    html_parts.append('<svg class="svg-connections" id="connectionsSvg"></svg>')
    html_parts.append('</div></div>')
    
    # Convert connections to JSON for JavaScript
    connections_json = json.dumps(connections)
    
    # JavaScript to draw connections - optimized to prevent freezing
    html_parts.append(f"""
    <script>
        let isDrawing = false;
        let drawTimeout = null;
        
        function drawConnections() {{
            if (isDrawing) return;
            isDrawing = true;
            
            try {{
                const svg = document.getElementById('connectionsSvg');
                const container = document.getElementById('sitemapContainer');
                const connections = {connections_json};
                
                if (!svg || !container) {{
                    isDrawing = false;
                    return;
                }}
                
                // Clear existing lines
                svg.innerHTML = '';
                
                // Get container dimensions
                const containerWidth = Math.max(container.scrollWidth || 0, container.offsetWidth || 0, 1000);
                const containerHeight = Math.max(container.scrollHeight || 0, container.offsetHeight || 0, 1000);
                
                svg.setAttribute('width', containerWidth);
                svg.setAttribute('height', containerHeight);
                
                // Get container's position
                const containerRect = container.getBoundingClientRect();
                const scrollLeft = container.scrollLeft || 0;
                const scrollTop = container.scrollTop || 0;
                
                let drawnCount = 0;
                const maxConnections = 200; // Limit to prevent freezing
                
                connections.slice(0, maxConnections).forEach(conn => {{
                    const fromNode = document.getElementById(conn.from);
                    const toNode = document.getElementById(conn.to);
                    
                    if (fromNode && toNode) {{
                        try {{
                            const fromRect = fromNode.getBoundingClientRect();
                            const toRect = toNode.getBoundingClientRect();
                            
                            const fromX = fromRect.left - containerRect.left + scrollLeft + fromRect.width / 2;
                            const fromY = fromRect.top - containerRect.top + scrollTop + fromRect.height;
                            const toX = toRect.left - containerRect.left + scrollLeft + toRect.width / 2;
                            const toY = toRect.top - containerRect.top + scrollTop;
                            
                            if (fromX >= 0 && fromY >= 0 && toX >= 0 && toY >= 0) {{
                                const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                                // Draw straight vertical line down, then horizontal, then vertical to child
                                const verticalGap = 10; // Gap between parent and horizontal line
                                const horizontalY = fromY + verticalGap;
                                const path = `M ${{fromX}} ${{fromY}} L ${{fromX}} ${{horizontalY}} L ${{toX}} ${{horizontalY}} L ${{toX}} ${{toY}}`;
                                line.setAttribute('d', path);
                                line.setAttribute('class', 'connection-line');
                                svg.appendChild(line);
                                drawnCount++;
                            }}
                        }} catch(e) {{
                            console.error('Error drawing connection:', e);
                        }}
                    }}
                }});
                
                console.log('Drawn', drawnCount, 'connections');
            }} catch(e) {{
                console.error('Error in drawConnections:', e);
            }} finally {{
                isDrawing = false;
            }}
        }}
        
        // Debounce function
        function debounce(func, wait) {{
            return function(...args) {{
                clearTimeout(drawTimeout);
                drawTimeout = setTimeout(() => func.apply(this, args), wait);
            }};
        }}
        
        const debouncedDraw = debounce(drawConnections, 300);
        
        // Draw connections after page load - only once
        setTimeout(() => {{
            drawConnections();
        }}, 500);
        
        // Redraw on scroll and resize with debounce
        const container = document.getElementById('sitemapContainer');
        if (container) {{
            container.addEventListener('scroll', debouncedDraw, {{ passive: true }});
        }}
        window.addEventListener('resize', debouncedDraw, {{ passive: true }});
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

# Function for extracting client name from DataFrame
def extract_client_name(df: pd.DataFrame) -> str:
    """Extracts client name from DataFrame - looks for 'Client Name' column or similar"""
    # Try to find column with 'client' and 'name' in it (case insensitive)
    client_name_col = None
    for col in df.columns:
        col_lower = str(col).lower()
        if 'client' in col_lower and 'name' in col_lower:
            client_name_col = col
            break
    
    if client_name_col is None:
        # Try just 'name' column
        for col in df.columns:
            if 'name' in str(col).lower() and 'client' not in str(col).lower():
                # Check if it's likely a client name (not a generic name field)
                sample_values = df[col].dropna().astype(str).head(5).tolist()
                # If values look like names (not too long, not URLs, etc.)
                if any(len(v) < 100 and not v.startswith('http') for v in sample_values):
                    client_name_col = col
                    break
    
    if client_name_col:
        # Get first non-null value
        client_name = df[client_name_col].dropna().iloc[0] if not df[client_name_col].dropna().empty else None
        if client_name:
            # Clean the name for filename use
            client_name = str(client_name).strip()
            # Remove invalid filename characters
            client_name = re.sub(r'[<>:"/\\|?*]', '', client_name)
            # Replace spaces with hyphens and limit length
            client_name = client_name.replace(' ', '-')[:50]
            return client_name
    
    return "sitemap"

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
    
    prompt = f"""You are creating a WEBSITE SITEMAP based on a client questionnaire. 

═══════════════════════════════════════════════════════════════════════════════
PART 1: WHAT TO INCLUDE vs WHAT TO EXCLUDE
═══════════════════════════════════════════════════════════════════════════════

✅ INCLUDE - Actual Content Pages:

- Pages visitors will navigate to and view

- Main navigation items (About, Services, Products, Contact, etc.)

- Content listing pages (/blog, /news, /products, /projects)

- Single/detail page templates (/blog/single-post, /products/single-product)

- Legal pages if business requires them (Privacy Policy, Terms, Cookies)

- Landing pages explicitly mentioned

- Category/subcategory pages for products, services, projects, etc.

❌ EXCLUDE - These Are NOT Pages:

- Technical features (multilingual-support, crm-functionalities, backend-data, analytics)

- Questionnaire metadata (website-goals, decision-criteria, evaluating-factors)

- Internal processes (content-updates, broken-links, customer-feedback)

- Admin/dashboard pages (/admin, /wp-admin, /dashboard)

- User account pages (/login, /register, /my-account)

- Search results pages (/search?q=)

- Filter pages with URL parameters (/products?category=electronics)

- Paginated pages (/blog/page/2, /blog/page/3)

- Language prefixes as separate pages (/en/, /de/) - unless explicitly using subdirectory approach

- Form submission endpoints

═══════════════════════════════════════════════════════════════════════════════
PART 2: DYNAMIC CONTENT CATEGORIES - CRITICAL RULE
═══════════════════════════════════════════════════════════════════════════════

For ANY dynamic content category mentioned, you MUST include BOTH:

1. Category listing page

2. Single/detail page template

Examples:

- News → /news AND /news/single-news

- Blog → /blog AND /blog/single-post

- Products → /products AND /products/single-product

- Projects → /projects AND /projects/single-project

- Properties → /properties AND /properties/single-property

- Services → /services AND /services/single-service

- Events → /events AND /events/single-event

- Team → /team AND /team/single-member

- Portfolio → /portfolio AND /portfolio/single-work

═══════════════════════════════════════════════════════════════════════════════
PART 3: E-COMMERCE & MULTI-LEVEL HIERARCHIES
═══════════════════════════════════════════════════════════════════════════════

If questionnaire indicates e-commerce or complex categorization:

STRUCTURE:

/products (main listing)

/products/category-name (level 1)

/products/category-name/subcategory (level 2, if needed)

/products/single-product (template)

RULES:

- Include categories only if explicitly mentioned or clearly implied

- Max 3 levels deep unless clearly needed

- Logical parent-child relationship

- Plural for categories, singular for templates

═══════════════════════════════════════════════════════════════════════════════
PART 4: INDUSTRY-SPECIFIC PATTERNS
═══════════════════════════════════════════════════════════════════════════════

RESTAURANT/CAFE: /menu, /reservations, /location, /gallery

REAL ESTATE: /properties, /properties/for-sale, /properties/for-rent, /properties/single-property, /agents

LAW FIRM: /practice-areas, /attorneys, /case-results, /consultation

MEDICAL/DENTAL: /services, /doctors, /appointments, /insurance

E-COMMERCE: /products (with categories), /shipping-information, /returns-policy

PORTFOLIO/AGENCY: /portfolio, /portfolio/single-project, /services, /clients

SaaS/SOFTWARE: /features, /pricing, /documentation, /use-cases

═══════════════════════════════════════════════════════════════════════════════
PART 5: MANDATORY LEGAL/COMPLIANCE PAGES
═══════════════════════════════════════════════════════════════════════════════

IF collecting user data: → /privacy-policy

IF e-commerce: → /terms-and-conditions

IF European audience/GDPR: → /privacy-policy AND /cookie-policy

IF professional services: → /privacy-policy AND /disclaimer

═══════════════════════════════════════════════════════════════════════════════
PART 6: MULTILINGUAL WEBSITES
═══════════════════════════════════════════════════════════════════════════════

APPROACH 1 - Subdirectory: /en/about, /de/about (duplicate structure)

APPROACH 2 - Parameters: /about?lang=en (single structure)

APPROACH 3 - Subdomain: en.example.com/about (separate sitemaps)

DEFAULT: If multilingual mentioned but approach unclear, use APPROACH 2

═══════════════════════════════════════════════════════════════════════════════
PART 7: PRIORITY VALUES (0.0-1.0)
═══════════════════════════════════════════════════════════════════════════════

1.0 = Homepage only

0.9 = Main conversion pages (contact, pricing, services, products main)

0.8 = Important content (about, main services/products)

0.7 = Category listing pages (blog, news, projects)

0.6 = Subcategories, team, individual service pages

0.5 = Single/detail templates, less prominent content

0.4 = Legal pages

0.3 = Archive/tag pages

═══════════════════════════════════════════════════════════════════════════════
PART 8: CHANGEFREQ VALUES
═══════════════════════════════════════════════════════════════════════════════

daily = News/blog listings, active e-commerce, frequently updated homepage

weekly = Service pages with updates, active portfolio, events

monthly = About, team, standard service/product pages, legal pages

yearly = Rarely updated static content

never = Historical content that won't change

DEFAULT: monthly if unsure

═══════════════════════════════════════════════════════════════════════════════
PART 9: LASTMOD DATE (YYYY-MM-DD)
═══════════════════════════════════════════════════════════════════════════════

Homepage: {datetime.now().strftime('%Y-%m-%d')}

Recent/active pages: Last 30 days

Standard pages: Last 90 days

Legal/static: Last 180 days

Vary dates realistically - don't use same date for all.

═══════════════════════════════════════════════════════════════════════════════
PART 10: URL STRUCTURE RULES
═══════════════════════════════════════════════════════════════════════════════

✅ USE: lowercase, hyphens, descriptive names, logical hierarchy, no trailing slash

❌ AVOID: UPPERCASE, underscores, special chars, numbers at start, double slashes, excessive depth (max 3-4 levels), URLs >100 chars

GOOD: /services/web-development

BAD: /Services/Web_Development

═══════════════════════════════════════════════════════════════════════════════
QUESTIONNAIRE DATA
═══════════════════════════════════════════════════════════════════════════════

{qa_text}

═══════════════════════════════════════════════════════════════════════════════
EXECUTION PROCESS - FOLLOW THESE STEPS IN ORDER
═══════════════════════════════════════════════════════════════════════════════

STEP 1: ANALYZE THE QUESTIONNAIRE

First, analyze the questionnaire and output:

```
ANALYSIS:

Business Type: [e.g., e-commerce, restaurant, law firm, blog, portfolio, saas]

Industry: [if identifiable]

Dynamic Content Types: [list: blog, news, products, projects, etc.]

E-commerce: [YES/NO]

Multilingual: [YES/NO - if yes, which approach?]

Explicitly Mentioned Pages: [list]

Implied Pages (from industry): [list]

Required Legal Pages: [based on Part 5]

Estimated Page Count: [number]

```

STEP 2: APPLY RULES

- Check Part 2: Do all dynamic content types have listing + single page?

- Check Part 3: Is e-commerce hierarchy needed?

- Check Part 4: Are industry-specific pages needed?

- Check Part 5: Are legal pages required?

- Check Part 6: Multilingual approach?

STEP 3: GENERATE XML SITEMAP

Create valid XML sitemap with:

- <loc>: https://example.com/page-url

- <lastmod>: YYYY-MM-DD (varied realistically)

- <changefreq>: Based on Part 8

- <priority>: Based on Part 7

Format:

<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <!-- other pages -->
</urlset>

STEP 4: VALIDATE

✓ All dynamic content has listing + single page?

✓ All URLs unique?

✓ Priorities logical?

✓ Changefreq appropriate?

✓ Lastmod dates varied?

✓ Admin/login/search pages excluded?

✓ Legal pages included if needed?

✓ Every page genuinely needed?

✓ URL structure clean?

✓ Page count reasonable?

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Your response MUST include:

1. ANALYSIS (formatted as above)

2. XML SITEMAP (valid XML)

3. NOTES (optional - any clarifications or assumptions)

NOW BEGIN - Start with STEP 1:

"""

    def extract_xml_from_response(text: str) -> str:
        """Extracts XML sitemap from Gemini response that may include analysis"""
        # First, try to find XML inside markdown code blocks (```xml ... ```)
        markdown_xml_pattern = r'```xml\s*(.*?)```'
        match = re.search(markdown_xml_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            xml_content = match.group(1).strip()
            # Ensure it starts with <?xml
            if not xml_content.startswith('<?xml'):
                xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
            return xml_content
        
        # Try to find XML content between <?xml and </urlset>
        xml_pattern = r'<\?xml.*?</urlset>'
        match = re.search(xml_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            xml_content = match.group(0).strip()
            # Clean up any markdown code block markers
            xml_content = re.sub(r'```xml\s*', '', xml_content, flags=re.IGNORECASE)
            xml_content = re.sub(r'```\s*$', '', xml_content, flags=re.IGNORECASE)
            return xml_content.strip()
        
        # If no XML found, try to find just the urlset
        urlset_pattern = r'<urlset.*?</urlset>'
        match = re.search(urlset_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            xml_content = match.group(0).strip()
            # Clean up any markdown code block markers
            xml_content = re.sub(r'```xml\s*', '', xml_content, flags=re.IGNORECASE)
            xml_content = re.sub(r'```\s*$', '', xml_content, flags=re.IGNORECASE)
            if not xml_content.startswith('<?xml'):
                return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_content}'
            return xml_content
        
        # If still no XML, return original text (might be just XML)
        return text
    
    try:
        # Use ONLY gemini-2.5-flash model
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return extract_xml_from_response(response.text)
    except Exception as e:
        # No fallback - raise error with details from Gemini
        error_msg = f"Error communicating with Gemini AI (gemini-2.5-flash): {str(e)}"
        if hasattr(e, 'message'):
            error_msg += f"\nDetails: {e.message}"
        raise Exception(error_msg)

# Main part of application
uploaded_file = st.file_uploader(
    "Drag and drop the file here",
    type=['csv']
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
    
    # Initialize session state for results
    if 'sitemap_results' not in st.session_state:
        st.session_state.sitemap_results = None
    
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
                        st.session_state.sitemap_results = None
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
                        
                        # Extract client name for filename
                        client_name = extract_client_name(df)
                        
                        # Parse sitemap for visualization
                        parsed_urls = parse_sitemap_xml(sitemap)
                        
                        # Store results in session state
                        st.session_state.sitemap_results = {
                            'sitemap': sitemap,
                            'parsed_urls': parsed_urls,
                            'client_name': client_name,
                            'qa_pairs': qa_pairs,
                            'df_rows': len(df),
                            'df_columns': len(df.columns)
                        }
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)
                    st.session_state.sitemap_results = None
    
    # Display results if they exist in session state
    if st.session_state.sitemap_results:
        results = st.session_state.sitemap_results
        sitemap = results['sitemap']
        parsed_urls = results['parsed_urls']
        client_name = results['client_name']
        qa_pairs = results['qa_pairs']
        
        # Ensure client_name is not empty for filename
        if not client_name or client_name == "sitemap":
            # Try to generate a filename from timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_suffix = f"sitemap_{timestamp}"
        else:
            filename_suffix = client_name
        
        # Tabs for displaying results
        tab1, tab2, tab3, tab4 = st.tabs(["📄 XML Sitemap", "🗺️ Visual Sitemap", "📁 Structure", "📊 Statistics"])
        
        with tab1:
            st.subheader("Generated XML Sitemap")
            st.code(sitemap, language="xml")
            
            # Download button with key to prevent refresh
            st.download_button(
                label="💾 Download Sitemap",
                data=sitemap,
                file_name=f"sitemap_xml-{filename_suffix}.xml",
                mime="application/xml",
                key="download_xml_sitemap"
            )
        
        with tab2:
            st.subheader("🗺️ Visual Sitemap - Tree Structure")
            st.info("💡 If the page freezes, use the XML Sitemap tab instead.")
            
            if parsed_urls:
                st.info(f"📊 Displaying {len(parsed_urls)} pages in tree structure")
                
                # Create visual tree with error handling
                try:
                    tree_html = create_visual_tree_html(parsed_urls)
                    st.components.v1.html(tree_html, height=600, scrolling=True)
                except Exception as e:
                    st.error(f"Error creating visual tree: {str(e)}")
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
                    
                    # Download tree structure with key to prevent refresh
                    st.download_button(
                        label="💾 Download Structure",
                        data=tree_structure,
                        file_name=f"sitemap_structure-{filename_suffix}.txt",
                        mime="text/plain",
                        key="download_structure"
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
                st.metric("Total CSV Rows", results['df_rows'])
            
            st.metric("CSV Columns", results['df_columns'])
            
            # Display first few QA pairs
            st.subheader("Sample Questions and Answers")
            for i, pair in enumerate(qa_pairs[:5], 1):
                with st.expander(f"Question {pair['id']}"):
                    st.write("**Question:**", pair['question'])
                    st.write("**Answer:**", pair['answer'][:200] + "..." if len(pair['answer']) > 200 else pair['answer'])

else:
    pass

