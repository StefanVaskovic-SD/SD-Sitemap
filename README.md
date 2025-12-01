# 🗺️ Sitemap Generator

Aplikacija za generisanje detaljne sitemape na osnovu pitanja i odgovora iz CSV fajla, koristeći Gemini AI (Gemini 2.5 Flash).

## 📋 Funkcionalnosti

- ✅ Upload CSV fajlova sa pitanjima i odgovorima
- ✅ Automatsko parsiranje i izdvajanje pitanja i odgovora
- ✅ Analiza sadržaja pomoću Gemini AI-ja
- ✅ Generisanje detaljne XML sitemape
- ✅ Download generisane sitemape

## 🚀 Instalacija i Pokretanje

### ✅ Paketi su već instalirani!

Svi potrebni paketi su već instalirani. Ako treba da reinstalirate, koristite:
```bash
pip3 install -r requirements.txt
```

### 🎯 Kako pokrenuti aplikaciju:

**Opcija 1: Koristeći Python modul (preporučeno)**
```bash
cd /Users/stefanvaskovic/Desktop/Sitemap-Generator
python3 -m streamlit run app.py
```

**Opcija 2: Direktno sa streamlit komandom**
```bash
cd /Users/stefanvaskovic/Desktop/Sitemap-Generator
streamlit run app.py
```

**Nakon pokretanja:**
- Aplikacija će se automatski otvoriti u vašem web pretraživaču
- Ako se ne otvori automatski, idite na: `http://localhost:8501`

## 🔑 Dobijanje i Dodavanje Gemini API ključa

1. Idite na [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Kreirajte novi API ključ
3. Kopirajte ključ

## 📍 GDE DA DODATE API KLJUČ

**API ključ se dodaje u `.env` fajl:**

1. **Otvorite `.env` fajl** u folderu aplikacije
2. **Dodajte** vaš API ključ u formatu:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
3. **Sačuvajte** fajl

**⚠️ VAŽNO:** `.env` fajl je već kreiran u folderu aplikacije. Samo zamenite placeholder sa vašim API ključem!

## 📖 Kako koristiti

1. **Unesite Gemini API ključ** u sidebar-u aplikacije
2. **Uploadujte CSV fajl** koji sadrži pitanja i odgovore
3. **Izaberite kolone** koje sadrže pitanja i odgovore
4. **Kliknite na "Generiši Sitemapu"**
5. **Preuzmite generisanu sitemapu** u XML formatu

## 📝 Format CSV fajla

CSV fajl može imati više kolona, ali mora sadržati:
- Jednu kolonu sa pitanjima
- Jednu kolonu sa odgovorima

Primer strukture:
```csv
id,question,answer,category,other_info
1,"Šta je Python?","Python je programski jezik",programming,info1
2,"Kako se koristi?","Koristi se za...",programming,info2
```

## 🛠️ Tehnologije

- **Streamlit** - Web aplikacija
- **Pandas** - Parsiranje CSV fajlova
- **Google Generative AI** - Gemini AI integracija

## 📄 Licenca

Ovaj projekat je open source.

