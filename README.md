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
│   ├── theme.py             # Sistema tema (light, dark, embedded)
│   ├── components.py        # 7 widget riutilizzabili
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

# Installa dipendenze
pip install -r requirements.txt

# Avvia suite
python salesforce_tool.py
```

### Autenticazione Salesforce

```bash
# Login con alias
sf org login web --alias my-org

# Verifica org autenticate
sf org list
```

---

## 📖 Configurazione

File config: `~/.salesforce-tools/config.json`

```json
{
  "chunk_size": 200,
  "page_size": 100,
  "export_formats": ["csv", "json"],
  "theme": "light",
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

## 📊 Tema & Customizzazione

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
