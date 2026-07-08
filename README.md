# Salesforce Tools Suite v2.0

**Architettura modularizzata e completamente refactorizzata** per migliorare manutenibilità, testabilità e estensibilità.

## 📋 Panoramica

Suite di tre tool complementari per gestire Salesforce:

### 🚀 **Massive Query Tool**
Estrai dati Salesforce in bulk con chunking automatico:
- Supporto query SOQL con bind values
- Suddivisione automatica in chunk se query troppo lunga
- Export in CSV, JSON, Excel
- Interfaccia progress con ETA

### 👁️ **Data Viewer**
Visualizza e filtra dati estratti:
- Caricamento CSV/JSON
- Paginazione (50, 100, 200, 500 righe)
- Ricerca globale
- Vista raw code per debug

### 📊 **Platform Limits Monitor**
Monitora i limiti della piattaforma Salesforce:
- Gauge visivi per utilizzo risorse
- Colori dinamici (verde, arancio, rosso)
- Aggiornamento real-time

---

## 🏗️ Architettura

```
src/
├── core/                      # Logica pura (zero UI)
│   ├── exceptions.py         # Gerarchia eccezioni strutturata
│   ├── sf_cli.py             # Wrapper centralizzato Salesforce CLI
│   └── soql_validator.py     # Validazione SOQL e sanitizzazione
├── operations/               # Business logic
│   ├── data_extractor.py    # Estrazione con chunking automatico
│   └── data_exporter.py     # Export CSV, JSON, Excel
├── ui/                       # Componenti UI
│   ├── modern_theme.py      # Sistema tema moderno (dark, light, glass)
│   ├── modern_components.py # Componenti UI moderni (card, badge, toast, tabs)
│   ├── styles.py            # Token styling centralizzati
│   ├── theme.py             # Wrapper compatibilità tema
│   ├── components.py        # Wrapper compatibilità componenti
│   ├── massive_query_app.py # Tool estrazione refactorizzato
│   ├── viewer_app.py        # Tool visualizzatore refactorizzato
│   └── limit_monitor_app.py # Tool limiti refactorizzato
├── config.py                 # Configurazione persistente
└── logging_config.py         # Setup logging centralizzato

salesforce_tool.py           # Suite principale (entry point)
requirements.txt             # Dipendenze
```

### ✨ Vantaggi dell'architettura

| Aspetto | Prima | Dopo |
|---------|-------|------|
| **Duplicazione codice** | Alto (30%+) | ~5% |
| **Testabilità** | Difficile | Unit test ready |
| **Error handling** | Generico (Exception) | 7 tipi custom |
| **Configurazione** | Hardcoded | Persistente (.json) |
| **Logging** | Nessuno | Centralizzato + file |
| **Tema UI** | 1 variant | 3 variant (light/dark/embedded) |
| **Manutenibilità** | Media | Alta |

---

## 🚀 Installazione & Uso

### Prerequisiti
- Python 3.8+
- Salesforce CLI (`sf`) installato e autenticato
- Git

### Setup

```bash
# Clone repository
git clone https://github.com/fra-repo/salesforce-tools.git
cd salesforce-tools

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Unix
# oppure
venv\Scripts\activate  # Windows

# Installa dipendenze backend / desktop UI legacy
pip install -r requirements.txt
```

### Avvio UI desktop Python (esistente)

```bash
python salesforce_tool.py
```

### Avvio backend adapter + nuovo frontend TypeScript

```bash
# 1) Backend adapter HTTP minimale
python -m src.api.server

# 2) In un secondo terminale
cd frontend
cp .env.example .env.local  # opzionale
npm install
npm run dev
```

### Build frontend TypeScript

```bash
cd frontend
npm run build
npm run preview
```

### Autenticazione Salesforce

```bash
# Login con alias
sf org login web --alias my-org

# Verifica org autenticate
sf org list
```

---

## 🌐 Migrazione UI Python → TypeScript

### Individuazione UI attuale

**UI attiva (desktop Python):**
- `salesforce_tool.py` → shell principale CustomTkinter con sidebar e navigazione tool
- `src/ui/massive_query_app.py` → schermata Massive Query
- `src/ui/viewer_app.py` → schermata Data Viewer
- `src/ui/limit_monitor_app.py` → schermata Platform Limits
- `src/ui/modern_components.py`, `src/ui/modern_theme.py`, `src/ui/styles.py` → design system desktop

**UI legacy / standalone:**
- `massive_query_salesforce.py`
- `salesforce_viewer.py`
- `platform_limit.py`

**Cosa non è UI:**
- `src/core/*` → wrapper Salesforce CLI, validazione SOQL, eccezioni
- `src/operations/*` → estrazione dati ed export
- `src/config.py`, `src/logging_config.py` → configurazione e logging

**Conclusione:** nel repository **non esisteva una web UI vera e propria**. La UI Python esistente è una GUI desktop `tkinter/customtkinter`, quindi la migrazione frontend è partita con uno scaffold React + Vite collegato a un adapter HTTP minimale.

### Mappa migrazione UI

| Origine Python | Destinazione TypeScript | Stato | Note |
|---|---|---|---|
| `salesforce_tool.py` | `frontend/src/App.tsx` overview + tab navigation | iniziale | shell web che documenta stato app e UI discovery |
| `src/ui/massive_query_app.py` | tab **Massive Query** | iniziale | collegata a `POST /api/massive-query/execute` |
| `src/ui/viewer_app.py` | tab **Data Viewer** | iniziale | upload CSV/JSON, filtro globale, paginazione, raw view client-side |
| `src/ui/limit_monitor_app.py` | tab **Platform Limits** | iniziale | collegata a `GET /api/limits` |
| backlog futuro (schema browser, saved queries) | placeholder overview | TODO | richiede API backend dedicate |

### Decisioni e assunzioni

- Nessun template HTML, Streamlit, Gradio, Flet, Flask o FastAPI è presente nel repository.
- Per minimizzare modifiche invasive al backend, il nuovo layer web usa `python -m src.api.server` basato su `http.server` standard library.
- Nel primo adapter web l'export server-side è volutamente fissato a `./salesforce_extracts` dentro la repository, così il browser non può richiedere scritture arbitrarie sul filesystem del server.
- Il **Data Viewer** è stato portato lato browser perché la UI originale apriva file locali; non serviva introdurre un endpoint upload dedicato per una prima migrazione verificabile.
- Il **Massive Query** e il **Limits Monitor** riusano i servizi Python esistenti (`src/core` + `src/operations`) tramite adapter HTTP minimale.
- La presenza della Salesforce CLI resta un prerequisito anche per la nuova UI web quando si vogliono usare org discovery, query o limiti live.

## 📝 Configurazione

File config: `~/.salesforce-tools/config.json`

### Variabili d'ambiente frontend/backend

- `SALESFORCE_TOOLS_API_HOST` (default `127.0.0.1`)
- `SALESFORCE_TOOLS_API_PORT` (default `8000`)
- `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`, vedi `frontend/.env.example`)


```json
{
  "chunk_size": 200,
  "page_size": 100,
  "export_formats": ["csv", "json"],
  "theme": "dark",
  "default_output_dir": "./salesforce_extracts"
}
```

I log si salvano in: `~/.salesforce-tools/logs/salesforce-tools.log`

---

## 🔧 Moduli Chiave

### `SalesforceCliManager` (core/sf_cli.py)
Wrapper centralizzato per Salesforce CLI:

```python
from src.core.sf_cli import SalesforceCliManager

cli = SalesforceCliManager()

# Scopri org autenticate
orgs = cli.discover_org_aliases()

# Esegui query SOQL
records = cli.execute_soql(
    soql="SELECT Id, Name FROM Account LIMIT 100",
    org_alias="my-org"
)
```

### `SalesforceDataExtractor` (operations/data_extractor.py)
Estrazione con chunking automatico:

```python
from src.operations.data_extractor import SalesforceDataExtractor

extractor = SalesforceDataExtractor(cli, "my-org")

# Chunk automaticamente se query troppo lunga
chunks = extractor.chunk_bind_values(bind_values, chunk_size=200)

# Processa per export
headers, flat_rows = extractor.process_records_for_export(
    records, 
    soql_structure
)
```

### `DataExporter` (operations/data_exporter.py)
Export multi-formato:

```python
from src.operations.data_exporter import DataExporter

exporter = DataExporter(Path("./output"))

exporter.export_csv(headers, rows, "export")
exporter.export_json(records, "export")
exporter.export_xlsx(headers, rows, "export")
```

### `SOQLValidator` (core/soql_validator.py)
Validazione SOQL:

```python
from src.core.soql_validator import SOQLValidator, SOQLSanitizer

# Validazione
SOQLValidator.validate_soql(soql)
SOQLValidator.check_bind_values_in_query(soql)

# Escape sicuro
escaped = SOQLSanitizer.escape_string(user_input)
formatted = SOQLSanitizer.format_bind_values_for_query(values)
```

---

## 📝 Error Handling

Eccezioni strutturate per ogni scenario:

```python
from src.core.exceptions import (
    SalesforceError,       # Base
    CliNotFound,          # CLI non trovato
    OrgNotFound,          # Org non autenticata
    QueryLimitExceeded,   # Query troppo lunga
    QueryExecutionError,  # Errore query Salesforce
    ValidationError,      # Input validation
    ExportError,          # Errore export
)
```

---

## 🧪 Testing

I moduli core sono testabili in isolamento (zero dipendenze UI):

```python
import unittest
from unittest.mock import patch, MagicMock
from src.operations.data_extractor import SalesforceDataExtractor

class TestExtractor(unittest.TestCase):
    @patch('src.core.sf_cli.SalesforceCliManager.execute_soql')
    def test_query_execution(self, mock_exec):
        mock_exec.return_value = [{"Id": "001", "Name": "Test"}]
        # Test...
```

---

## 🎨 Tema & Customizzazione

Tema centralizzato (src/ui/theme.py):

```python
from src.ui.theme import get_theme

theme = get_theme("light")  # light, dark, embedded

# Accedi colori
print(theme.primary)    # #2563eb
print(theme.card_bg)    # #ffffff
```

---

## 📈 Performance

### Chunking Automatico
- Query SOQL max 18,000 caratteri
- Chunking ridimensionabile se limit superato
- Multi-threading per estrazione parallela (4 worker default)

### Paginazione
- Supporto 50-500 righe per pagina
- Ricerca live (ILIKE)
- Rendering ottimizzato

---

## 🐛 Troubleshooting

### "Salesforce CLI non trovato"
```bash
# Installa SF CLI
choco install salesforcecli  # Windows
brew install salesforcecli   # Mac
npm install -g @salesforce/cli  # Linux
```

### "Org non trovata"
```bash
# Autentica org
sf org login web --alias my-org
```

### Query size exceeded
- Riduci chunk_size in config.json
- Estrai meno colonne
- Filtra meglio con WHERE clause

---

## 📄 License

MIT License

---

## 🚀 Roadmap Future

- [ ] Batch API per estrazione massiva
- [ ] Web UI alternative
- [ ] Scheduled exports
- [ ] Data sync multi-org
- [ ] Custom report builder
- [ ] CLI mode (headless)

---

## 💬 Support

Per issues e feature requests: [GitHub Issues](https://github.com/fra-repo/salesforce-tools/issues)
