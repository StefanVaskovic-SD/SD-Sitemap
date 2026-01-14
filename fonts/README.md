# Fonts Folder

Ovaj folder je namenjen za custom fontove koje želite da koristite u aplikaciji.

## Kako dodati fontove

1. **Ubacite font fajlove** u ovaj folder (`fonts/`)
2. **Podržani formati:**
   - `.woff2` (preporučeno - najbolja kompresija)
   - `.woff` (alternativa)
   - `.ttf` (fallback)

3. **Nakon što ubacite fontove:**
   - Otvorite `app.py`
   - Pronađite sekciju sa komentarom `/* Import custom fonts from fonts folder */`
   - Otkomentarišite `@font-face` blokove
   - Zamenite `'your-font-regular.woff2'` sa stvarnim imenima vaših font fajlova
   - Promenite `'CustomFont'` sa imenom vašeg fonta
   - U sekciji `/* Apply custom font to entire app */` dodajte ime vašeg fonta na početak liste

## Primer strukture

```
fonts/
├── custom-font-regular.woff2
├── custom-font-bold.woff2
├── custom-font-italic.woff2
└── README.md
```

## Primer konfiguracije u app.py

```css
@font-face {
    font-family: 'MyCustomFont';
    src: url('fonts/custom-font-regular.woff2') format('woff2'),
         url('fonts/custom-font-regular.woff') format('woff');
    font-weight: normal;
    font-style: normal;
}

* {
    font-family: 'MyCustomFont', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}
```

## Napomena

- Fontovi će biti primenjeni na celu aplikaciju
- Ako ne ubacite fontove, aplikacija će koristiti sistem fontove kao fallback
- Za najbolje performanse, koristite `.woff2` format
