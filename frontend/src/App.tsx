import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent } from 'react'
import './App.css'
import { executeMassiveQuery, fetchHealth, fetchLimits, fetchOrgs } from './api'
import type { HealthResponse, LimitsItem, MassiveQueryPayload, MassiveQueryResult, ViewerData } from './types'

type TabId = 'overview' | 'massive-query' | 'viewer' | 'limits'

type QueryFormState = MassiveQueryPayload

const DEFAULT_QUERY = 'SELECT Id, Name FROM Account WHERE Id IN :bind_values'

const EMPTY_VIEWER: ViewerData = {
  fileName: '',
  headers: [],
  rows: [],
  rawText: '',
}

function parseCsvLine(line: string): string[] {
  const values: string[] = []
  let current = ''
  let inQuotes = false

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index]
    const next = line[index + 1]

    if (char === '"') {
      if (inQuotes && next === '"') {
        current += '"'
        index += 1
      } else {
        inQuotes = !inQuotes
      }
      continue
    }

    if (char === ',' && !inQuotes) {
      values.push(current)
      current = ''
      continue
    }

    current += char
  }

  values.push(current)
  return values.map((value) => value.trim())
}

function parseCsv(text: string): { headers: string[]; rows: string[][] } {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length === 0) {
    return { headers: [], rows: [] }
  }

  const headers = parseCsvLine(lines[0])
  const rows = lines.slice(1).map(parseCsvLine)
  return { headers, rows }
}

function parseJson(text: string): { headers: string[]; rows: string[][] } {
  const payload = JSON.parse(text)
  const items = Array.isArray(payload) ? payload : [payload]
  const headers = Array.from(
    new Set(items.flatMap((item) => (item && typeof item === 'object' ? Object.keys(item) : []))),
  )
  const rows = items.map((item) => headers.map((header) => String(item?.[header] ?? '')))
  return { headers, rows }
}

function getRowKey(headers: string[], row: string[], fallback: string): string {
  const stableHeader = ['Id', 'ID', 'id', 'Name'].find((header) => headers.includes(header))
  if (stableHeader) {
    const index = headers.indexOf(stableHeader)
    const value = row[index]
    if (value) {
      return `${stableHeader}:${value}`
    }
  }

  return `${fallback}:${JSON.stringify(row)}`
}

function App() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string>('')
  const [orgs, setOrgs] = useState<string[]>([])
  const [orgsError, setOrgsError] = useState<string>('')
  const [queryForm, setQueryForm] = useState<QueryFormState>({
    orgAlias: '',
    soql: DEFAULT_QUERY,
    bindValues: '',
    chunkSize: 200,
    outputDir: '',
    exportFormats: ['csv', 'json'],
  })
  const [queryResult, setQueryResult] = useState<MassiveQueryResult | null>(null)
  const [queryError, setQueryError] = useState<string>('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [limits, setLimits] = useState<LimitsItem[]>([])
  const [limitsError, setLimitsError] = useState<string>('')
  const [limitsLoading, setLimitsLoading] = useState(false)
  const [viewerData, setViewerData] = useState<ViewerData>(EMPTY_VIEWER)
  const [viewerError, setViewerError] = useState<string>('')
  const [viewerSearch, setViewerSearch] = useState('')
  const [viewerPageSize, setViewerPageSize] = useState(50)
  const [viewerPage, setViewerPage] = useState(1)
  const [showRawViewer, setShowRawViewer] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const healthResponse = await fetchHealth()
        setHealth(healthResponse)
        setQueryForm((current) => ({
          ...current,
          chunkSize: healthResponse.defaults.chunkSize,
          outputDir: healthResponse.defaults.outputDir,
          exportFormats: healthResponse.defaults.exportFormats,
        }))
        setViewerPageSize(healthResponse.defaults.pageSize)
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Errore caricamento stato applicazione'
        setHealthError(message)
      }

      try {
        const orgItems = await fetchOrgs()
        setOrgs(orgItems)
        setQueryForm((current) => ({
          ...current,
          orgAlias: orgItems[0] ?? current.orgAlias,
        }))
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Errore aggiornamento org'
        setOrgsError(message)
      }
    }

    void load()
  }, [])

  const filteredViewerRows = useMemo(() => {
    const normalized = viewerSearch.trim().toLowerCase()
    if (!normalized) {
      return viewerData.rows
    }

    return viewerData.rows.filter((row) => row.some((cell) => cell.toLowerCase().includes(normalized)))
  }, [viewerData.rows, viewerSearch])

  const totalViewerPages = Math.max(1, Math.ceil(filteredViewerRows.length / viewerPageSize))

  useEffect(() => {
    setViewerPage((current) => Math.min(current, totalViewerPages))
  }, [totalViewerPages])

  const paginatedViewerRows = useMemo(() => {
    const start = (viewerPage - 1) * viewerPageSize
    return filteredViewerRows.slice(start, start + viewerPageSize)
  }, [filteredViewerRows, viewerPage, viewerPageSize])

  const toggleExportFormat = (format: string) => {
    setQueryForm((current) => {
      const alreadySelected = current.exportFormats.includes(format)
      const next = alreadySelected
        ? current.exportFormats.filter((item) => item !== format)
        : [...current.exportFormats, format]
      return {
        ...current,
        exportFormats: next,
      }
    })
  }

  const handleMassiveQuerySubmit = async () => {
    setQueryLoading(true)
    setQueryError('')
    setQueryResult(null)
    try {
      const result = await executeMassiveQuery(queryForm)
      setQueryResult(result)
    } catch (error) {
      setQueryError(error instanceof Error ? error.message : 'Errore esecuzione massive query')
    } finally {
      setQueryLoading(false)
    }
  }

  const handleLoadLimits = async () => {
    if (!queryForm.orgAlias) {
      setLimitsError('Seleziona un org')
      return
    }

    setLimitsLoading(true)
    setLimitsError('')
    try {
      const result = await fetchLimits(queryForm.orgAlias)
      setLimits(result)
    } catch (error) {
      setLimitsError(error instanceof Error ? error.message : 'Errore caricamento limiti')
    } finally {
      setLimitsLoading(false)
    }
  }

  const handleRefreshOrgs = async () => {
    setOrgsError('')
    try {
      const items = await fetchOrgs()
      setOrgs(items)
      setQueryForm((current) => ({
        ...current,
        orgAlias: items[0] ?? current.orgAlias,
      }))
    } catch (error) {
      setOrgsError(error instanceof Error ? error.message : 'Errore aggiornamento org')
    }
  }

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    setViewerError('')
    setViewerPage(1)

    try {
      const rawText = await file.text()
      const parser = file.name.toLowerCase().endsWith('.json') ? parseJson : parseCsv
      const parsed = parser(rawText)
      setViewerData({
        fileName: file.name,
        headers: parsed.headers,
        rows: parsed.rows,
        rawText,
      })
    } catch (error) {
      setViewerError(error instanceof Error ? error.message : 'Impossibile leggere il file selezionato')
      setViewerData(EMPTY_VIEWER)
    }
  }

  const statusClassName = health?.cliAvailable ? 'pill pill-success' : 'pill pill-warning'

  return (
    <div className="app-shell">
      <header className="hero-panel">
        <div>
          <p className="eyebrow">Frontend TypeScript iniziale</p>
          <h1>{health?.appName ?? 'Salesforce Tools Suite'}</h1>
          <p className="hero-copy">
            {health?.uiDiscovery.summary ??
              'Analisi UI in corso: la migrazione parte dalla GUI desktop Python esistente.'}
          </p>
        </div>
        <div className="hero-meta">
          <span className={statusClassName}>{health?.cliAvailable ? 'CLI disponibile' : 'CLI da verificare'}</span>
          <span className="pill">Versione {health?.version ?? '2.0'}</span>
          <span className="pill">Org rilevate: {health?.orgCount ?? 0}</span>
        </div>
      </header>

      {(healthError || orgsError) && <div className="alert alert-error">{healthError || orgsError}</div>}
      {health?.cliError && <div className="alert alert-warning">{health.cliError}</div>}

      <nav className="tab-bar" aria-label="Sezioni applicazione">
        {[
          ['overview', 'Overview'],
          ['massive-query', 'Massive Query'],
          ['viewer', 'Data Viewer'],
          ['limits', 'Platform Limits'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={activeTab === id ? 'tab tab-active' : 'tab'}
            onClick={() => setActiveTab(id as TabId)}
          >
            {label}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' && health && (
        <section className="grid-layout overview-grid">
          <article className="card">
            <h2>Decisioni e assunzioni</h2>
            <ul className="bullet-list">
              <li>UI attuale identificata come GUI desktop `tkinter/customtkinter`.</li>
              <li>Nessuna web UI preesistente o template HTML nel repository.</li>
              <li>L’adapter HTTP espone solo integrazioni minime per non rendere invasivo il backend Python.</li>
              <li>Il Data Viewer web legge CSV/JSON lato browser perché la UI originale apriva file locali.</li>
            </ul>
          </article>

          <article className="card">
            <h2>Mappa UI esistente</h2>
            <div className="inventory-columns">
              <div>
                <h3>UI attiva</h3>
                <ul className="inventory-list">
                  {health.uiDiscovery.activeUi.map((entry) => (
                    <li key={entry.path}>
                      <strong>{entry.path}</strong>
                      <span>{entry.details}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3>Legacy / standalone</h3>
                <ul className="inventory-list">
                  {health.uiDiscovery.legacyUi.map((entry) => (
                    <li key={entry.path}>
                      <strong>{entry.path}</strong>
                      <span>{entry.details}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </article>

          <article className="card">
            <h2>Cosa non è UI</h2>
            <ul className="inventory-list">
              {health.uiDiscovery.notUi.map((entry) => (
                <li key={entry.path}>
                  <strong>{entry.path}</strong>
                  <span>{entry.details}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="card">
            <h2>Punti di ingresso per la UI web</h2>
            <ul className="inventory-list">
              {health.uiDiscovery.futureUiEntryPoints.map((entry) => (
                <li key={entry.path}>
                  <strong>{entry.path}</strong>
                  <span>{entry.details}</span>
                </li>
              ))}
            </ul>
          </article>

          <article className="card card-wide">
            <h2>Stato migrazione</h2>
            <div className="feature-grid">
              {health.features.map((feature) => (
                <div key={feature.id} className="feature-tile">
                  <span className={feature.status === 'todo' ? 'pill pill-warning' : 'pill pill-success'}>
                    {feature.status === 'todo' ? 'TODO' : 'Portato in TS'}
                  </span>
                  <h3>{feature.title}</h3>
                  <p>{feature.notes}</p>
                </div>
              ))}
            </div>
          </article>
        </section>
      )}

      {activeTab === 'massive-query' && (
        <section className="grid-layout">
          <article className="card card-wide">
            <div className="section-header">
              <div>
                <h2>Massive Query</h2>
                <p>Porting iniziale della schermata desktop con collegamento ai servizi Python esistenti.</p>
              </div>
              <div className="inline-actions">
                <button type="button" className="secondary-button" onClick={() => void handleRefreshOrgs()}>
                  Aggiorna org
                </button>
              </div>
            </div>

            <div className="form-grid">
              <label>
                Salesforce Org
                <select
                  value={queryForm.orgAlias}
                  onChange={(event) => setQueryForm((current) => ({ ...current, orgAlias: event.target.value }))}
                >
                  <option value="">Seleziona un org</option>
                  {orgs.map((org) => (
                    <option key={org} value={org}>
                      {org}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Chunk size
                <input
                  type="number"
                  min={1}
                  value={queryForm.chunkSize}
                  onChange={(event) =>
                    setQueryForm((current) => ({ ...current, chunkSize: Number(event.target.value) || 1 }))
                  }
                />
              </label>

              <label className="field-span-2">
                Cartella output backend (fissata per sicurezza)
                <input
                  type="text"
                  value={queryForm.outputDir}
                  readOnly
                />
              </label>

              <label className="field-span-2">
                Query SOQL
                <textarea
                  rows={5}
                  value={queryForm.soql}
                  onChange={(event) => setQueryForm((current) => ({ ...current, soql: event.target.value }))}
                />
              </label>

              <label className="field-span-2">
                Bind values
                <textarea
                  rows={6}
                  value={queryForm.bindValues}
                  onChange={(event) => setQueryForm((current) => ({ ...current, bindValues: event.target.value }))}
                  placeholder="001..., 001... oppure un valore per riga"
                />
              </label>
            </div>

            <div className="checkbox-row">
              {['csv', 'json', 'xlsx'].map((format) => (
                <label key={format} className="checkbox-pill">
                  <input
                    type="checkbox"
                    checked={queryForm.exportFormats.includes(format)}
                    onChange={() => toggleExportFormat(format)}
                  />
                  {format.toUpperCase()}
                </label>
              ))}
            </div>

            <div className="inline-actions">
              <button type="button" className="primary-button" onClick={() => void handleMassiveQuerySubmit()}>
                {queryLoading ? 'Esecuzione...' : 'Esegui estrazione'}
              </button>
            </div>

            {queryError && <div className="alert alert-error">{queryError}</div>}
          </article>

          <article className="card">
            <h2>Risultato</h2>
            {queryResult ? (
              <>
                <div className="stats-grid">
                  <div>
                    <strong>{queryResult.recordCount}</strong>
                    <span>record</span>
                  </div>
                  <div>
                    <strong>{queryResult.chunkCount}</strong>
                    <span>chunk</span>
                  </div>
                  <div>
                    <strong>{queryResult.bindValueCount}</strong>
                    <span>bind values</span>
                  </div>
                </div>
                <p className="muted-copy">Output server-side: {queryResult.outputDir}</p>
                <h3>File esportati</h3>
                <ul className="bullet-list">
                  {queryResult.exportedFiles.map((file) => (
                    <li key={file}>{file}</li>
                  ))}
                </ul>
                <h3>Preview tabellare</h3>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {queryResult.headers.map((header) => (
                          <th key={header}>{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {queryResult.previewRows.map((row, index) => (
                        <tr key={getRowKey(queryResult.headers, row, `preview-${index}`)}>
                          {row.map((cell, cellIndex) => (
                            <td key={`${index}-${cellIndex}`}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <p className="muted-copy">Nessuna estrazione eseguita. La preview mostrerà i primi 10 record flattenati.</p>
            )}
          </article>
        </section>
      )}

      {activeTab === 'viewer' && (
        <section className="grid-layout">
          <article className="card card-wide">
            <div className="section-header">
              <div>
                <h2>Data Viewer</h2>
                <p>Porting web della schermata desktop: upload locale, filtro globale, paginazione e raw view.</p>
              </div>
              <div className="inline-actions">
                <button type="button" className="secondary-button" onClick={() => setShowRawViewer(false)}>
                  Tabella
                </button>
                <button type="button" className="secondary-button" onClick={() => setShowRawViewer(true)}>
                  Raw
                </button>
              </div>
            </div>

            <div className="viewer-toolbar">
              <input type="file" accept=".csv,.json" onChange={(event) => void handleFileUpload(event)} />
              <input
                type="search"
                placeholder="Filtro globale"
                value={viewerSearch}
                onChange={(event) => {
                  setViewerSearch(event.target.value)
                  setViewerPage(1)
                }}
              />
              <select
                value={viewerPageSize}
                onChange={(event) => {
                  setViewerPageSize(Number(event.target.value))
                  setViewerPage(1)
                }}
              >
                {[50, 100, 200, 500].map((size) => (
                  <option key={size} value={size}>
                    {size} righe
                  </option>
                ))}
              </select>
            </div>

            {viewerError && <div className="alert alert-error">{viewerError}</div>}
            {!viewerData.fileName && <p className="muted-copy">Carica un CSV o JSON esportato dal tool per iniziare.</p>}
            {viewerData.fileName && <p className="muted-copy">File corrente: {viewerData.fileName}</p>}

            {showRawViewer ? (
              <pre className="raw-view">{viewerData.rawText || 'Nessun contenuto disponibile.'}</pre>
            ) : (
              <>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {viewerData.headers.map((header) => (
                          <th key={header}>{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedViewerRows.map((row, rowIndex) => (
                        <tr key={getRowKey(viewerData.headers, row, `viewer-${rowIndex}`)}>
                          {row.map((cell, cellIndex) => (
                            <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination-row">
                  <span>
                    Pagina {viewerPage} di {totalViewerPages}
                  </span>
                  <div className="inline-actions">
                    <button type="button" className="secondary-button" onClick={() => setViewerPage(1)}>
                      Prima
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setViewerPage((current) => Math.max(1, current - 1))}
                    >
                      Prec
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setViewerPage((current) => Math.min(totalViewerPages, current + 1))}
                    >
                      Succ
                    </button>
                    <button type="button" className="secondary-button" onClick={() => setViewerPage(totalViewerPages)}>
                      Ultima
                    </button>
                  </div>
                </div>
              </>
            )}
          </article>
        </section>
      )}

      {activeTab === 'limits' && (
        <section className="grid-layout">
          <article className="card card-wide">
            <div className="section-header">
              <div>
                <h2>Platform Limits</h2>
                <p>Porting iniziale della dashboard limiti con integrazione diretta al backend Python.</p>
              </div>
              <div className="inline-actions">
                <button type="button" className="secondary-button" onClick={() => void handleRefreshOrgs()}>
                  Aggiorna org
                </button>
                <button type="button" className="primary-button" onClick={() => void handleLoadLimits()}>
                  {limitsLoading ? 'Caricamento...' : 'Verifica limiti'}
                </button>
              </div>
            </div>

            {limitsError && <div className="alert alert-error">{limitsError}</div>}
            {!limits.length && !limitsLoading && (
              <p className="muted-copy">Seleziona un org nella sezione Massive Query o aggiorna la lista per avviare il monitor.</p>
            )}
            <div className="limits-grid">
              {limits.map((limit) => (
                <div key={limit.name} className="limit-card">
                  <div className="limit-header">
                    <h3>{limit.name}</h3>
                    <span>{limit.percentage}%</span>
                  </div>
                  <div className="progress-track">
                    <div
                      className={
                        limit.percentage >= 90
                          ? 'progress-value progress-danger'
                          : limit.percentage >= 70
                            ? 'progress-value progress-warning'
                            : 'progress-value progress-success'
                      }
                      style={{ width: `${Math.min(limit.percentage, 100)}%` }}
                    />
                  </div>
                  <p className="muted-copy">
                    {limit.used.toLocaleString()} / {limit.total.toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          </article>
        </section>
      )}
    </div>
  )
}

export default App
