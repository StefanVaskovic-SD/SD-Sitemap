# 📖 Detaljno Uputstvo za Korišćenje

## 🚀 Kako pokrenuti aplikaciju

### 1. Otvorite Terminal
- Na Mac-u: `Cmd + Space` → kucajte "Terminal" → Enter

### 2. Navigirajte do foldera aplikacije
```bash
cd /Users/stefanvaskovic/Desktop/Sitemap-Generator
```

### 3. Pokrenite aplikaciju
```bash
python3 -m streamlit run app.py
```

### 4. Aplikacija će se otvoriti automatski
- Ako se ne otvori, idite na: **http://localhost:8501**
- Aplikacija će se otvoriti u vašem web pretraživaču

---

## 🔑 GDE DA DODATE GEMINI API KLJUČ

### Korak 1: Dobijte API ključ
1. Idite na: https://makersuite.google.com/app/apikey
2. Ulogujte se sa vašim Google nalogom
3. Kliknite na **"Create API Key"** ili **"Get API Key"**
4. Kopirajte ključ (izgleda ovako: `AIzaSy...`)

### Korak 2: Dodajte ključ u .env fajl
1. **Otvorite `.env` fajl** u folderu aplikacije (`/Users/stefanvaskovic/Desktop/Sitemap-Generator/.env`)
2. **Zamenite** `your_api_key_here` sa vašim stvarnim API ključem
3. **Sačuvajte** fajl

**Primer .env fajla:**
```
GEMINI_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567
```

**⚠️ VAŽNO:** 
- `.env` fajl je već kreiran u folderu aplikacije
- Nikada ne commit-ujte `.env` fajl na Git (već je u .gitignore)
- API ključ se automatski učitava iz `.env` fajla pri pokretanju aplikacije

---

## 📋 Kako koristiti aplikaciju

### Korak 1: Upload CSV fajla
1. Kliknite na **"Browse files"** ili **"Upload CSV fajl"**
2. Izaberite vaš CSV fajl sa pitanjima i odgovorima
3. Sačekajte da se fajl učita

### Korak 2: Pregled podataka
- Aplikacija će prikazati koliko redova ima u CSV-u
- Kliknite na **"📊 Pregled podataka"** da vidite prvih 10 redova
- Proverite koje kolone postoje

### Korak 3: Izaberite kolone
- **"Kolona sa pitanjima"** - izaberite kolonu koja sadrži pitanja
- **"Kolona sa odgovorima"** - izaberite kolonu koja sadrži odgovore

### Korak 4: Generiši sitemapu
1. Kliknite na veliko dugme **"🚀 Generiši Sitemapu"**
2. Sačekajte da AI analizira podatke (može potrajati 30-60 sekundi)
3. Sitemapa će se prikazati u tabu **"📄 Sitemapa"**

### Korak 5: Download sitemape
1. Kliknite na dugme **"💾 Download Sitemape"**
2. Fajl će se preuzeti sa imenom: `sitemap_YYYYMMDD_HHMMSS.xml`

---

## ⚙️ Tehnički Detalji

### Model koji se koristi:
- **Primarni:** `gemini-2.0-flash-exp` (najnoviji eksperimentalni)
- **Fallback:** `gemini-1.5-flash` (stabilan model)

### Format CSV fajla:
- CSV može imati bilo koji delimiter (`,`, `;`, itd.)
- Može imati bilo koje kolone - vi birate koje koristite
- Pitanja i odgovori mogu biti u bilo kojoj koloni

### Primer CSV strukture:
```csv
id,question,answer,category,other_info
1,"Šta je Python?","Python je programski jezik",programming,info1
2,"Kako se koristi?","Koristi se za...",programming,info2
```

---

## ❓ Rešavanje Problema

### Problem: "GEMINI_API_KEY nije pronađen u .env fajlu"
**Rešenje:** 
1. Proverite da li postoji `.env` fajl u folderu aplikacije
2. Proverite da li je API ključ ispravno unet u `.env` fajl
3. Format treba da bude: `GEMINI_API_KEY=vaš_ključ_ovde` (bez razmaka oko `=`)
4. Restartujte aplikaciju nakon izmene `.env` fajla

### Problem: "Greška pri komunikaciji sa Gemini AI"
**Rešenje:** 
- Proverite da li je API ključ validan
- Proverite internet konekciju
- Pokušajte ponovo

### Problem: Aplikacija se ne pokreće
**Rešenje:**
```bash
# Proverite da li su paketi instalirani
pip3 install -r requirements.txt

# Pokušajte ponovo
python3 -m streamlit run app.py
```

### Problem: Port 8501 je zauzet
**Rešenje:**
```bash
# Koristite drugi port
streamlit run app.py --server.port 8502
```

### Problem: "No columns to parse from file" ili "CSV fajl je prazan"
**Rešenje:**
1. **Proverite da li je fajl stvarno CSV format:**
   - Otvorite fajl u Excel-u ili text editoru
   - Proverite da li ima kolone (header red)
   - Proverite da li ima podatke (barem jedan red)

2. **Proverite format fajla:**
   - CSV fajl mora imati kolone odvojene delimiterom (`,`, `;`, `\t`, itd.)
   - Prvi red obično sadrži nazive kolona
   - Primer validnog CSV-a:
     ```csv
     question,answer
     "Šta je Python?","Python je programski jezik"
     "Kako se koristi?","Koristi se za..."
     ```

3. **Proverite encoding:**
   - Ako fajl ima specijalne karaktere (ć, č, š, đ, ž), proverite encoding
   - Pokušajte da sačuvate fajl kao UTF-8

4. **Proverite da li fajl nije korumpiran:**
   - Pokušajte da otvorite fajl u drugom programu
   - Proverite da li možete da ga čitate normalno

5. **Ako problem i dalje postoji:**
   - Pokušajte da konvertujete fajl u Excel format pa nazad u CSV
   - Ili kreirajte novi CSV fajl sa istim podacima

---

## 📞 Podrška

Ako imate problema, proverite:
1. Da li je Python 3.9+ instaliran
2. Da li su svi paketi instalirani
3. Da li je API ključ validan
4. Da li CSV fajl ima validne podatke

