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

# Učitaj .env fajl
load_dotenv()

# Učitaj API ključ iz .env fajla
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Konfiguriši Gemini AI sa API ključem
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("❌ GEMINI_API_KEY nije pronađen u .env fajlu! Molimo proverite .env fajl.")

# Konfiguracija Streamlit stranice
st.set_page_config(
    page_title="Sitemap Generator",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Sitemap Generator")
st.markdown("Uploaduj CSV fajl sa pitanjima i odgovorima, i generiši detaljnu sitemapu pomoću Gemini AI-ja")

# Sidebar za konfiguraciju
with st.sidebar:
    st.header("⚙️ Status")
    
    if GEMINI_API_KEY:
        st.success("✅ API ključ je učitan iz .env fajla")
    else:
        st.error("❌ API ključ nije pronađen!")
        st.info("Proverite da li postoji .env fajl sa GEMINI_API_KEY")
    
    st.markdown("---")
    st.markdown("### 📋 Instrukcije")
    st.markdown("""
    1. Uploadujte CSV fajl
    2. Odaberite kolone sa pitanjima i odgovorima
    3. Kliknite na 'Generiši Sitemapu'
    """)

# Funkcija za parsiranje CSV-a
def parse_csv(file) -> pd.DataFrame:
    """Učitava CSV fajl i vraća DataFrame sa boljim error handling-om"""
    
    # Resetuj poziciju fajla na početak
    file.seek(0)
    
    # Proveri da li je fajl prazan i pronađi header red
    try:
        content = file.read()
        # Ako je content bytes, dekodiraj ga
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except:
                try:
                    content = content.decode('latin-1')
                except:
                    content = content.decode('utf-8', errors='ignore')
        
        if not content or len(content.strip()) == 0:
            raise ValueError("CSV fajl je prazan! Molimo uploadujte fajl sa podacima.")
        
        # Pronađi header red (red koji sadrži "Section" ili "Question" ili "Answer")
        lines = content.split('\n')
        header_row_index = None
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Traži header red koji sadrži tipične kolone za questionnaire CSV
            if any(keyword in line_lower for keyword in ['section', 'question', 'answer']):
                # Proveri da li ima više od jedne kolone (da nije samo metadata red)
                if ',' in line and line.count(',') >= 2:
                    header_row_index = i
                    break
        
        if header_row_index is None:
            # Ako nije pronađen specifičan header, pokušaj da nađeš bilo koji red sa više kolona
            for i, line in enumerate(lines):
                if ',' in line and line.count(',') >= 2:
                    header_row_index = i
                    break
        
        if header_row_index is None:
            # Ako nije pronađen specifičan header, pokušaj da parsiraš od početka
            # Možda je fajl standardni CSV bez metadata redova
            header_row_index = 0
        
        # Proveri da li ima podatke posle header reda (ako header nije na početku)
        if header_row_index > 0:
            data_lines = [line.strip() for line in lines[header_row_index + 1:] if line.strip()]
            if len(data_lines) < 1:
                raise ValueError("CSV fajl nema podatke posle header reda! Proverite da li fajl sadrži podatke.")
        
    except Exception as e:
        if "prazan" in str(e).lower() or "nema podatke" in str(e).lower():
            raise
        # Ako greška nije vezana za prazan fajl, nastavi dalje sa header_row_index = 0
        if 'header_row_index' not in locals():
            header_row_index = 0
    
    # Resetuj poziciju ponovo
    file.seek(0)
    
    # Lista opcija za parsiranje (različiti delimiteri i encoding-i)
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
            file.seek(0)  # Resetuj poziciju za svaki pokušaj
            
            # Koristi header_row_index ako je pronađen, inače pokušaj automatski
            skip_rows = header_row_index if header_row_index is not None else 0
            
            # Pokušaj sa različitim opcijama zavisno od verzije pandas-a
            try:
                # Najnovija verzija pandas-a
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
                    # Srednja verzija pandas-a
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
                    # Najstarija verzija - bez opcija za loše linije
                    df = pd.read_csv(
                        file,
                        encoding=options['encoding'],
                        delimiter=options['delimiter'],
                        skiprows=skip_rows,
                        engine='python'
                    )
            
            # Proveri da li ima kolone
            if df.empty and len(df.columns) == 0:
                continue
                
            # Proveri da li ima podatke
            if len(df.columns) == 0:
                raise ValueError("CSV fajl nema kolone! Proverite format fajla.")
            
            # Ako je DataFrame prazan ali ima kolone, to je OK (možda nema podataka)
            return df
            
        except pd.errors.EmptyDataError:
            raise ValueError("CSV fajl je prazan ili nema podataka! Proverite da li fajl sadrži podatke.")
        except UnicodeDecodeError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue
    
    # Ako ništa ne radi, pokušaj sa automatskim detekcijom
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        if len(df.columns) > 0:
            return df
    except:
        pass
    
    # Ako sve ne uspe, baci grešku sa detaljima
    error_msg = "Ne mogu da parsujem CSV fajl. "
    if last_error:
        error_msg += f"Poslednja greška: {str(last_error)}. "
    error_msg += "Proverite da li je fajl validan CSV format sa kolonama i podacima."
    raise ValueError(error_msg)

# Funkcija za parsiranje XML sitemape
def parse_sitemap_xml(xml_content: str) -> List[Dict]:
    """Parsira XML sitemapu i vraća listu URL-ova sa metapodacima"""
    urls = []
    
    try:
        # Pokušaj sa BeautifulSoup (bolje rukovanje sa lošim XML-om)
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
            # Ako ništa ne radi, pokušaj regex
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

# Funkcija za kreiranje vizuelnog grafa
def create_visual_graph(urls: List[Dict]) -> str:
    """Kreira interaktivni graf sitemape koristeći pyvis"""
    net = Network(height='600px', width='100%', bgcolor='#222222', font_color='white', directed=True)
    
    # Dodaj čvorove i veze
    nodes = {}
    
    for url_data in urls:
        url = url_data['url']
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Dodaj root domen
        domain = parsed.netloc or 'root'
        if domain not in nodes:
            net.add_node(domain, label=domain, color='#FF6B6B', size=30, title=domain, shape='box')
            nodes[domain] = domain
        
        # Dodaj čvorove za svaki deo putanje
        current_path = domain
        for i, part in enumerate(path_parts):
            node_id = f"{current_path}/{part}"
            if node_id not in nodes:
                # Boja zavisi od nivoa
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
                
                # Skrati label ako je previše dug
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
                
                # Dodaj vezu samo ako već ne postoji
                if current_path != node_id:
                    net.add_edge(current_path, node_id, arrows='to', color='#888888')
            
            current_path = node_id
    
    # Generiši HTML sa boljim opcijama
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

# Funkcija za kreiranje folder tree strukture
def create_folder_tree(urls: List[Dict]) -> str:
    """Kreira folder tree strukturu kao string"""
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
    
    # Kreiraj tree string
    tree_lines = []
    tree_lines.append("📁 /")
    
    def print_tree(node, prefix="", is_last=True, depth=0):
        """Rekurzivno štampa tree strukturu"""
        if depth > 6:  # Ograniči dubinu
            return
        
        if isinstance(node, dict):
            items = list(node.items())
            for i, (key, value) in enumerate(items):
                is_last_item = i == len(items) - 1
                connector = "└── " if is_last_item else "├── "
                
                # Dodaj ikonicu zavisno od toga da li ima decu
                icon = "📁" if isinstance(value, dict) and value else "📄"
                tree_lines.append(prefix + connector + icon + " " + key)
                
                if isinstance(value, dict) and value:
                    extension = "    " if is_last_item else "│   "
                    print_tree(value, prefix + extension, is_last_item, depth + 1)
    
    print_tree(tree)
    
    return "\n".join(tree_lines)

# Funkcija za izdvajanje pitanja i odgovora
def extract_qa_pairs(df: pd.DataFrame, question_col: str, answer_col: str) -> List[Dict]:
    """Izdvaja parove pitanja-odgovor iz DataFrame-a"""
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

# Funkcija za analizu sa Gemini AI-jem
def analyze_with_gemini(qa_pairs: List[Dict]) -> str:
    """Analizira pitanja i odgovore pomoću Gemini AI-ja i generiše sitemapu"""
    
    if not GEMINI_API_KEY:
        raise ValueError("API ključ nije pronađen u .env fajlu")
    
    # Priprema prompta
    qa_text = "\n\n".join([
        f"Pitanje {pair['id']}: {pair['question']}\nOdgovor: {pair['answer']}"
        for pair in qa_pairs[:50]  # Ograničavamo na prva 50 zbog token limita
    ])
    
    if len(qa_pairs) > 50:
        qa_text += f"\n\n... i još {len(qa_pairs) - 50} parova pitanja-odgovor."
    
    prompt = f"""Analiziraj sledeća pitanja i odgovore i generiši detaljnu sitemapu u XML formatu.

Pitanja i odgovori:
{qa_text}

Generiši sitemapu koja:
1. Organizuje sadržaj u logičke kategorije i sekcije bazirane na temama iz pitanja
2. Kreira URL strukturu koja odražava hijerarhiju sadržaja (npr. /kategorija/podkategorija/stranica)
3. Uključuje sve relevantne stranice bazirane na temama iz pitanja i odgovora
4. Koristi standardni XML sitemap format

Format sitemape MORA biti validan XML:
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/kategorija/stranica</loc>
    <lastmod>2024-01-01</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  ...
</urlset>

Važno:
- Koristi samo validan XML format
- Svaki <url> element mora imati <loc>, <lastmod>, <changefreq>, i <priority>
- URL-ovi treba da budu smisleni i organizovani po kategorijama
- <lastmod> format: YYYY-MM-DD
- <changefreq> vrednosti: always, hourly, daily, weekly, monthly, yearly, never
- <priority> vrednosti: 0.0 do 1.0

Generiši kompletnu sitemapu sa svim relevantnim stranicama:"""

    try:
        # Pokušaj sa Gemini 2.5 Flash (najnoviji model)
        # Prvo pokušaj sa gemini-2.0-flash-exp (eksperimentalni, najnoviji)
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(prompt)
            return response.text
        except:
            # Fallback na gemini-1.5-flash ako 2.0 ne radi
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        # Fallback na alternativne modele
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except:
            raise Exception(f"Greška pri komunikaciji sa Gemini AI: {str(e)}")

# Glavni deo aplikacije
uploaded_file = st.file_uploader(
    "Uploaduj CSV fajl",
    type=['csv'],
    help="Izaberite CSV fajl koji sadrži pitanja i odgovore"
)

if uploaded_file is not None:
    # Prikaži info o fajlu
    st.info(f"📄 Fajl: **{uploaded_file.name}** ({uploaded_file.size} bytes)")
    
    # Parsiranje CSV-a sa error handling-om
    try:
        df = parse_csv(uploaded_file)
        
        if df.empty:
            st.warning("⚠️ CSV fajl je učitan ali je prazan (nema redova sa podacima).")
        else:
            st.success(f"✅ CSV fajl je učitan! Ukupno redova: {len(df)}")
    except Exception as e:
        st.error(f"❌ Greška pri učitavanju CSV fajla: {str(e)}")
        
        # Debug informacije
        with st.expander("🔍 Debug informacije", expanded=False):
            st.write("**Tip greške:**", type(e).__name__)
            st.write("**Detalji:**", str(e))
            st.info("💡 **Savet:** Proverite da li je fajl validan CSV format sa kolonama i podacima. Otvorite fajl u text editoru i proverite format.")
        
        st.stop()  # Zaustavi izvršavanje ako fajl ne može da se učita
    
    # Prikaz prvih redova
    with st.expander("📊 Pregled podataka", expanded=False):
        st.dataframe(df.head(10))
        st.info(f"Ukupno kolona: {len(df.columns)}")
        st.write("Kolone:", list(df.columns))
    
    # Izbor kolona
    st.subheader("🔍 Izaberite kolone")
    
    col1, col2 = st.columns(2)
    
    with col1:
        question_column = st.selectbox(
            "Kolona sa pitanjima:",
            options=df.columns.tolist(),
            help="Izaberite kolonu koja sadrži pitanja"
        )
    
    with col2:
        answer_column = st.selectbox(
            "Kolona sa odgovorima:",
            options=df.columns.tolist(),
            help="Izaberite kolonu koja sadrži odgovore"
        )
    
    # Dugme za generisanje
    if st.button("🚀 Generiši Sitemapu", type="primary", use_container_width=True):
        if not GEMINI_API_KEY:
            st.error("❌ GEMINI_API_KEY nije pronađen u .env fajlu! Molimo proverite .env fajl.")
        else:
            with st.spinner("⏳ Analiziram pitanja i odgovore..."):
                try:
                    # Izdvajanje QA parova
                    qa_pairs = extract_qa_pairs(df, question_column, answer_column)
                    
                    if not qa_pairs:
                        st.warning("⚠️ Nisu pronađeni validni parovi pitanja-odgovor!")
                    else:
                        st.info(f"📝 Pronađeno {len(qa_pairs)} parova pitanja-odgovor")
                        
                        # Analiza sa Gemini AI-jem
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        status_text.text("🤖 Komuniciram sa Gemini AI-jem...")
                        progress_bar.progress(30)
                        
                        sitemap = analyze_with_gemini(qa_pairs)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Sitemapa je generisana!")
                        
                        # Prikaz rezultata
                        st.success("✅ Sitemapa je uspešno generisana!")
                        
                        # Parsiraj sitemapu za vizuelizaciju
                        parsed_urls = parse_sitemap_xml(sitemap)
                        
                        # Tabs za prikaz rezultata
                        tab1, tab2, tab3, tab4 = st.tabs(["📄 XML Sitemapa", "🗺️ Vizuelna Sitemapa", "📁 Struktura", "📊 Statistika"])
                        
                        with tab1:
                            st.subheader("Generisana XML Sitemapa")
                            st.code(sitemap, language="xml")
                            
                            # Download dugme
                            st.download_button(
                                label="💾 Download Sitemape",
                                data=sitemap,
                                file_name=f"sitemap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
                                mime="application/xml"
                            )
                        
                        with tab2:
                            st.subheader("🗺️ Vizuelna Sitemapa - Graf Veza")
                            if parsed_urls:
                                st.info(f"📊 Prikazano {len(parsed_urls)} stranica u grafu")
                                
                                # Kreiraj vizuelni graf
                                try:
                                    graph_html = create_visual_graph(parsed_urls)
                                    st.components.v1.html(graph_html, height=600, scrolling=True)
                                except Exception as e:
                                    st.error(f"Greška pri kreiranju grafa: {str(e)}")
                                    st.info("Pokušavam alternativni prikaz...")
                                    
                                    # Alternativni prikaz - lista sa hijerarhijom
                                    st.markdown("### 📋 Hijerarhija stranica:")
                                    for url_data in parsed_urls[:20]:  # Prikaži prvih 20
                                        url = url_data['url']
                                        parsed = urlparse(url)
                                        path_parts = [p for p in parsed.path.split('/') if p]
                                        indent = "  " * len(path_parts)
                                        st.markdown(f"{indent}📄 `{path_parts[-1] if path_parts else '/'}`")
                            else:
                                st.warning("⚠️ Nije moguće parsirati sitemapu za vizuelizaciju.")
                        
                        with tab3:
                            st.subheader("📁 Struktura Aplikacije")
                            if parsed_urls:
                                st.info(f"📊 Prikazano {len(parsed_urls)} stranica u strukturi")
                                
                                # Kreiraj folder tree
                                try:
                                    tree_structure = create_folder_tree(parsed_urls)
                                    st.code(tree_structure, language="text")
                                    
                                    # Download tree strukture
                                    st.download_button(
                                        label="💾 Download Strukture",
                                        data=tree_structure,
                                        file_name=f"sitemap_structure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                        mime="text/plain"
                                    )
                                except Exception as e:
                                    st.error(f"Greška pri kreiranju strukture: {str(e)}")
                                    
                                    # Alternativni prikaz
                                    st.markdown("### 📋 Lista URL-ova:")
                                    for url_data in parsed_urls:
                                        st.markdown(f"- `{url_data['url']}`")
                            else:
                                st.warning("⚠️ Nije moguće parsirati sitemapu za strukturu.")
                        
                        with tab4:
                            st.subheader("Statistika")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Ukupno pitanja", len(qa_pairs))
                            with col2:
                                st.metric("Ukupno stranica", len(parsed_urls) if parsed_urls else 0)
                            with col3:
                                st.metric("Ukupno redova u CSV-u", len(df))
                            
                            st.metric("Kolone u CSV-u", len(df.columns))
                            
                            # Prikaz prvih nekoliko QA parova
                            st.subheader("Primeri pitanja i odgovora")
                            for i, pair in enumerate(qa_pairs[:5], 1):
                                with st.expander(f"Pitanje {pair['id']}"):
                                    st.write("**Pitanje:**", pair['question'])
                                    st.write("**Odgovor:**", pair['answer'][:200] + "..." if len(pair['answer']) > 200 else pair['answer'])
                
                except Exception as e:
                    st.error(f"❌ Greška: {str(e)}")
                    st.exception(e)

else:
    st.info("👆 Molimo uploadujte CSV fajl da biste počeli")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Sitemap Generator - Powered by Gemini AI</div>",
    unsafe_allow_html=True
)

