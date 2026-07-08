# Salesforce Tools Suite – Feature Backlog e Roadmap

## Obiettivo
Evolvere `fra-repo/salesforce-tools` da suite focalizzata su query, visualizzazione dati e monitoraggio limiti a una piattaforma operativa più completa per utenti Salesforce tecnici e semi-tecnici.

## Stato attuale della suite
Ad oggi il repository mostra tre capability principali:
- **Massive Query Tool**: estrazione bulk con chunking automatico
- **Data Viewer**: visualizzazione e filtro dei dataset estratti
- **Platform Limits Monitor**: monitoraggio limiti piattaforma

L’architettura è già ben predisposta per l’estensione grazie a:
- separazione tra `core`, `operations` e `ui`
- configurazione persistente centralizzata
- logging centralizzato
- validazione SOQL dedicata
- componenti UI e sistema tema modulari

---

# Feature backlog proposto

## 1. Schema Browser / Object Explorer
### Descrizione
Un modulo dedicato all’esplorazione dello schema Salesforce con supporto a:
- oggetti standard e custom
- campi e tipi
- relazioni
- picklist values
- campi obbligatori / read-only
- ricerca rapida nello schema

### Valore
Riduce drasticamente il tempo necessario per scrivere query corrette e comprendere il modello dati.

### Priorità
**Alta**

### Complessità stimata
**M**

---

## 2. SOQL Query Builder visuale
### Descrizione
Interfaccia guidata per costruire query senza scriverle manualmente:
- scelta oggetto
- selezione campi
- filtri configurabili
- ordinamento
- limit
- anteprima query generata

### Valore
Apre il tool anche a utenti meno esperti e riduce errori di sintassi.

### Priorità
**Alta**

### Complessità stimata
**M/L**

---

## 3. Query History + Saved Queries
### Descrizione
Sistema per memorizzare e riutilizzare query:
- cronologia ultime query
- preferiti
- tag/cartelle
- parametri bind salvati
- “run again”
- export/import libreria query

### Valore
Incrementa produttività e riuso immediato.

### Priorità
**Alta**

### Complessità stimata
**S/M**

---

## 4. Metadata Explorer
### Descrizione
Esplorazione metadata Salesforce oltre ai dati:
- Apex Classes
- Flows
- Validation Rules
- Objects / Fields
- Permission Sets
- Layouts
- Record Types

### Valore
Rende la suite utile anche per admin, developer e attività di governance.

### Priorità
**Media/Alta**

### Complessità stimata
**L**

---

## 5. Record Inspector
### Descrizione
Vista dettagliata del record selezionato nel viewer:
- dettaglio completo campi
- valori raw e formattati
- lookup/relazioni
- copia JSON
- copia API names
- link diretto al record in Salesforce

### Valore
Migliora molto l’analisi puntuale dei dati estratti.

### Priorità
**Alta**

### Complessità stimata
**M**

---

## 6. Data Compare / Diff tra export
### Descrizione
Confronto tra due snapshot o due export:
- record aggiunti
- rimossi
- modificati
- diff per campo
- confronto cross-org opzionale

### Valore
Molto utile per audit, regressioni dati, verifiche post-deploy.

### Priorità
**Media**

### Complessità stimata
**M/L**

---

## 7. Bulk Update / Bulk Upsert Assistant
### Descrizione
Assistente per preparare e validare aggiornamenti massivi:
- mapping campi
- validazione preliminare
- preview cambiamenti
- export file pronto per bulk update/upsert
- eventuale esecuzione guidata via CLI
- dry run e conferma esplicita

### Valore
Aumenta il potenziale operativo della suite.

### Priorità
**Media/Alta**

### Complessità stimata
**L**

---

## 8. Dashboard salute org
### Descrizione
Estensione del monitor limiti in una dashboard più operativa:
- trend utilizzo API
- storage usage
- eventi recenti
- stato autenticazione
- viste aggregate per org

### Valore
Trasforma il monitor in strumento di osservabilità.

### Priorità
**Media**

### Complessità stimata
**M**

---

## 9. Scheduler / Job Runner
### Descrizione
Pianificazione automatica di job:
- query schedulate
- salvataggio export automatico
- naming dinamico output
- retention file
- storico esecuzioni
- notifiche al termine

### Valore
Utile per casi d’uso ricorrenti e reportistica periodica.

### Priorità
**Media**

### Complessità stimata
**M/L**

---

## 10. Report export avanzato
### Descrizione
Miglioramento del motore di export:
- template Excel
- fogli multipli
- statistiche automatiche
- profiling colonne
- null count
- duplicati
- top values

### Valore
Aumenta l’immediatezza analitica dei dati estratti.

### Priorità
**Media**

### Complessità stimata
**M**

---

## 11. Multi-org management
### Descrizione
Gestione di più org/autenticazioni:
- elenco org disponibili
- switch rapido
- default org
- badge DEV/UAT/PROD
- test connessione

### Valore
Essenziale in contesti reali con più ambienti.

### Priorità
**Alta**

### Complessità stimata
**S/M**

---

## 12. Autocomplete SOQL
### Descrizione
Supporto intelligente in input query:
- oggetti
- campi
- relazioni
- keywords SOQL
- suggerimenti contestuali

### Valore
Riduce errori e accelera la stesura di query.

### Priorità
**Alta**

### Complessità stimata
**M**

---

## 13. Template query pronti
### Descrizione
Libreria di query predefinite per oggetti comuni:
- Account
- Contact
- Opportunity
- Case
- User
- oggetti custom più frequenti

### Valore
Quick win ad alto utilizzo.

### Priorità
**Alta**

### Complessità stimata
**S**

---

## 14. Export compressi e naming intelligente
### Descrizione
Migliorie al processo di export:
- zip automatico
- timestamp nei nomi file
- naming basato su oggetto/query/org
- cartelle strutturate automaticamente

### Valore
Molto utile per ordine operativo e archiviazione.

### Priorità
**Alta**

### Complessità stimata
**S**

---

## 15. Log panel integrato
### Descrizione
Pannello UI per visualizzare i log dell’app:
- livelli log
- filtri
- error trace
- copia rapida log
- accesso ai log recenti

### Valore
Ottimo per supporto, debug e troubleshooting.

### Priorità
**Media/Alta**

### Complessità stimata
**S/M**

---

## 16. Retry & resilienza CLI
### Descrizione
Miglioramento robustezza operativa:
- retry automatici
- timeout configurabili
- gestione errori di rete
- messaggi diagnostici migliori

### Valore
Riduce frizione e failure temporanei.

### Priorità
**Alta**

### Complessità stimata
**S/M**

---

## 17. Preview risultati pre-export
### Descrizione
Preview prima del salvataggio finale:
- prime righe
- conteggio record
- warning su campi nested
- stima dimensione file

### Valore
Riduce export inutili o errati.

### Priorità
**Media**

### Complessità stimata
**S**

---

## 18. Field profiler
### Descrizione
Profilazione automatica dei campi del dataset:
- tipo inferito
- null percentage
- cardinalità
- top values
- min/max/avg dove applicabile

### Valore
Aumenta il valore analitico del viewer.

### Priorità
**Media**

### Complessità stimata
**M**

---

## 19. Cross-org compare
### Descrizione
Confronto tra sandbox e production su:
- schema
- record count
- snapshot selezionati
- export differenze

### Valore
Molto utile per governance e verifica ambienti.

### Priorità
**Strategica**

### Complessità stimata
**L**

---

## 20. Dependency explorer
### Descrizione
Mappa di utilizzo di oggetti/campi/metadata:
- dove è usato un campo
- flow collegati
- validation rules
- apex references
- permission set impattati

### Valore
Supporta analisi di impatto e manutenzione evolutiva.

### Priorità
**Strategica**

### Complessità stimata
**L**

---

## 21. Security audit helper
### Descrizione
Supporto analitico per sicurezza e permessi:
- overview permission sets
- accessi a campi sensibili
- export permessi
- gap analysis semplice

### Valore
Apre use case di audit e compliance.

### Priorità
**Strategica**

### Complessità stimata
**L**

---

## 22. Query performance advisor
### Descrizione
Analizzatore pre-esecuzione della query:
- warning su query troppo ampie
- segnali di filtri deboli
- campi potenzialmente costosi
- consigli di chunking / limit

### Valore
Riduce errori e migliora performance operative.

### Priorità
**Media/Alta**

### Complessità stimata
**M**

---

## 23. Natural language to SOQL
### Descrizione
Traduzione guidata da richiesta naturale a query SOQL:
- input in linguaggio naturale
- proposta query
- spiegazione campi/filtri usati
- editing prima dell’esecuzione

### Valore
Feature differenziante e molto visibile.

### Priorità
**Strategica**

### Complessità stimata
**L**

---

# Roadmap proposta

## Fase 1 – Quick wins e produttività immediata
### Obiettivo
Aumentare rapidamente usabilità, riuso e robustezza.

### Feature consigliate
1. Query History + Saved Queries
2. Multi-org management
3. Template query pronti
4. Export compressi e naming intelligente
5. Retry & resilienza CLI
6. Preview risultati pre-export

### Benefici attesi
- maggiore velocità d’uso
- meno errori operativi
- migliore esperienza quotidiana
- adozione più facile

### Durata indicativa
**3–5 settimane**

---

## Fase 2 – Potenziamento esperienza analitica
### Obiettivo
Rendere il tool molto più forte nella discovery e nell’analisi dei dati.

### Feature consigliate
1. Schema Browser / Object Explorer
2. Autocomplete SOQL
3. Record Inspector
4. Field profiler
5. Report export avanzato

### Benefici attesi
- query più corrette
- migliore comprensione del dato
- più valore analitico senza uscire dal tool

### Durata indicativa
**4–7 settimane**

---

## Fase 3 – Workflow avanzati
### Obiettivo
Passare da tool di consultazione a workbench operativo.

### Feature consigliate
1. SOQL Query Builder visuale
2. Data Compare / Diff tra export
3. Scheduler / Job Runner
4. Dashboard salute org
5. Query performance advisor

### Benefici attesi
- automazione dei task ripetitivi
- confronto snapshot e monitoraggio evoluto
- miglior supporto a utenti semi-tecnici

### Durata indicativa
**6–10 settimane**

---

## Fase 4 – Estensioni strategiche
### Obiettivo
Differenziare la suite con capability ad alto impatto.

### Feature consigliate
1. Metadata Explorer
2. Bulk Update / Bulk Upsert Assistant
3. Cross-org compare
4. Security audit helper
5. Dependency explorer
6. Natural language to SOQL

### Benefici attesi
- ampliamento del target utenti
- supporto a governance, audit e operations
- forte differenziazione rispetto a tool interni basici

### Durata indicativa
**8–14 settimane**

---

# Roadmap release-oriented suggerita

## Release 2.1
### Focus
Produttività immediata

### Scope
- Saved Queries
- Query History
- Multi-org switcher
- Query templates
- Export naming intelligente
- Retry/timeout migliorati

---

## Release 2.2
### Focus
Esperienza di query e analisi

### Scope
- Schema Browser
- SOQL autocomplete
- Record Inspector
- Preview risultati
- Field profiler base

---

## Release 2.3
### Focus
Analisi comparativa e automazione

### Scope
- Data Compare
- Scheduler
- Dashboard trend limiti
- Report export avanzato
- Query performance advisor

---

## Release 3.0
### Focus
Capability avanzate e differenzianti

### Scope
- Metadata Explorer
- Bulk Upsert Assistant
- Cross-org compare
- Security audit helper
- Natural language to SOQL

---

# Prioritizzazione finale consigliata

## Top 5 per ROI
1. Query History + Saved Queries
2. Multi-org management
3. Schema Browser
4. Record Inspector
5. SOQL autocomplete

## Top 5 quick wins
1. Template query pronti
2. Export naming intelligente
3. Retry & resilienza CLI
4. Preview risultati pre-export
5. Log panel integrato

## Top 5 strategiche
1. Metadata Explorer
2. Bulk Update / Upsert Assistant
3. Cross-org compare
4. Security audit helper
5. Natural language to SOQL

---

# Considerazioni implementative

## Architettura
L’attuale struttura del progetto si presta bene all’evoluzione:
- `src/core` per validazione, discovery schema, analisi query
- `src/operations` per compare, scheduler, export avanzato, bulk ops
- `src/ui` per nuovi pannelli e workflow guidati
- `src/config.py` per preferenze utente, org, query salvate, job pianificati

## Raccomandazioni tecniche
- introdurre un modello dati condiviso per org, query salvate e job
- mantenere separata la logica CLI dalla UI
- aggiungere test dedicati per parsing, compare e profiling
- introdurre storage locale versionato per settings e query library
- progettare da subito le feature bulk con modalità safe-by-default

---

# Conclusione
La suite ha già una base solida. La direzione più efficace è costruire attorno a tre pilastri:
1. **Produttività sulla query**
2. **Maggiore profondità di analisi del dato**
3. **Automazione e operatività multi-org**

Con questa roadmap, `salesforce-tools` può evolvere da utility tecnica a vero strumento operativo quotidiano per team Salesforce.
