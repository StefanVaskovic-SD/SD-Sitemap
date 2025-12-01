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

## ☁️ Deploy na Render

Aplikacija je spremna za deploy na Render! Slede ove korake:

### Korak 1: Push na GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push
```

### Korak 2: Konektuj GitHub repo na Render
1. Idite na [Render Dashboard](https://dashboard.render.com/)
2. Kliknite na **"New +"** → **"Web Service"**
3. Konektujte GitHub nalog i izaberite repozitorijum `SD-Sitemap`
4. Render će automatski detektovati konfiguraciju iz `Procfile` i `render.yaml`

### Korak 3: Dodaj Environment Variable
1. U Render Dashboard-u, idite na **"Environment"** sekciju
2. Dodajte novu env varijablu:
   - **Key:** `GEMINI_API_KEY`
   - **Value:** Vaš Gemini API ključ
3. Kliknite **"Save Changes"**

### Korak 4: Deploy
- Render će automatski pokrenuti build i deploy
- Sačekajte da se deploy završi (obično 2-5 minuta)
- Vaša aplikacija će biti dostupna na Render URL-u

**⚠️ VAŽNO:** Na Render-u koristite **Environment Variables**, ne `.env` fajl!

## 🛠️ Tehnologije

- **Streamlit** - Web aplikacija
- **Pandas** - Parsiranje CSV fajlova
- **Google Generative AI** - Gemini AI integracija

## 📄 Licenca

Ovaj projekat je open source.

