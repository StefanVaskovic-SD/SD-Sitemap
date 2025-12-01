import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from typing import List, Dict, Tuple
import json
from datetime import datetime
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import networkx as nx
from pyvis.network import Network
import re
from urllib.parse import urlparse

# Load .env file
load_dotenv()

# Load API key from .env file
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini AI with API key
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("❌ GEMINI_API_KEY not found in .env file! Please check the .env file.")

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

# Function for creating visual graph
def create_visual_graph(urls: List[Dict]) -> str:
    """Creates interactive sitemap graph using pyvis"""
    net = Network(height='600px', width='100%', bgcolor='#222222', font_color='white', directed=True)
    
    # Add nodes and edges
    nodes = {}
    
    for url_data in urls:
        url = url_data['url']
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Add root domain
        domain = parsed.netloc or 'root'
        if domain not in nodes:
            net.add_node(domain, label=domain, color='#FF6B6B', size=30, title=domain, shape='box')
            nodes[domain] = domain
        
        # Add nodes for each path part
        current_path = domain
        for i, part in enumerate(path_parts):
            node_id = f"{current_path}/{part}"
            if node_id not in nodes:
                # Color depends on level
                if i == 0:
                    color = '#4ECDC4'
                    size = 25
                    shape = 'box'
                elif i == 1:
                    color = '#95E1D3'
                    size = 20
                    shape = 'ellipse'
                else:
                    color = '#F38181'
                    size = 15
                    shape = 'dot'
                
                # Shorten label if too long
                label = part[:20] + '...' if len(part) > 20 else part
                
                net.add_node(
                    node_id, 
                    label=label, 
                    color=color, 
                    size=size,
                    title=url_data['url'],
                    shape=shape
                )
                nodes[node_id] = node_id
                
                # Add edge only if it doesn't already exist
                if current_path != node_id:
                    net.add_edge(current_path, node_id, arrows='to', color='#888888')
            
            current_path = node_id
    
    # Generate HTML with better options
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "stabilization": {"iterations": 100},
        "barnesHut": {
          "gravitationalConstant": -2000,
          "centralGravity": 0.3,
          "springLength": 95,
          "springConstant": 0.04,
          "damping": 0.09
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200
      }
    }
    """)
    
    return net.generate_html()

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
    
    prompt = f"""Analyze the following questions and answers and generate a detailed sitemap in XML format.

Questions and answers:
{qa_text}

Generate a sitemap that:
1. Organizes content into logical categories and sections based on topics from questions
2. Creates URL structure that reflects content hierarchy (e.g. /category/subcategory/page)
3. Includes all relevant pages based on topics from questions and answers
4. Uses standard XML sitemap format

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

Important:
- Use only valid XML format
- Each <url> element must have <loc>, <lastmod>, <changefreq>, and <priority>
- URLs should be meaningful and organized by categories
- <lastmod> format: YYYY-MM-DD
- <changefreq> values: always, hourly, daily, weekly, monthly, yearly, never
- <priority> values: 0.0 to 1.0

Generate complete sitemap with all relevant pages:"""

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
                            st.subheader("🗺️ Visual Sitemap - Connection Graph")
                            if parsed_urls:
                                st.info(f"📊 Displaying {len(parsed_urls)} pages in graph")
                                
                                # Create visual graph
                                try:
                                    graph_html = create_visual_graph(parsed_urls)
                                    st.components.v1.html(graph_html, height=600, scrolling=True)
                                except Exception as e:
                                    st.error(f"Error creating graph: {str(e)}")
                                    st.info("Trying alternative display...")
                                    
                                    # Alternative display - list with hierarchy
                                    st.markdown("### 📋 Page Hierarchy:")
                                    for url_data in parsed_urls[:20]:  # Show first 20
                                        url = url_data['url']
                                        parsed = urlparse(url)
                                        path_parts = [p for p in parsed.path.split('/') if p]
                                        indent = "  " * len(path_parts)
                                        st.markdown(f"{indent}📄 `{path_parts[-1] if path_parts else '/'}`")
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

