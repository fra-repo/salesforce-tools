export type UiEntry = {
  path: string
  kind: string
  details: string
}

export type FeatureStatus = 'migrated-initial' | 'todo'

export type Feature = {
  id: string
  title: string
  status: FeatureStatus
  notes: string
}

export type HealthResponse = {
  status: string
  cliAvailable: boolean
  cliError: string | null
  orgCount: number
  appName: string
  version: string
  defaults: {
    chunkSize: number
    outputDir: string
    exportFormats: string[]
    theme: string
    pageSize: number
  }
  features: Feature[]
  uiDiscovery: {
    hasWebUi: boolean
    summary: string
    activeUi: UiEntry[]
    legacyUi: UiEntry[]
    notUi: UiEntry[]
    futureUiEntryPoints: Array<{ path: string; details: string }>
  }
}

export type LimitsItem = {
  name: string
  used: number
  total: number
  percentage: number
}

export type MassiveQueryPayload = {
  orgAlias: string
  soql: string
  bindValues: string
  chunkSize: number
  outputDir: string
  exportFormats: string[]
}

export type MassiveQueryResult = {
  orgAlias: string
  chunkCount: number
  bindValueCount: number
  recordCount: number
  headers: string[]
  previewRows: string[][]
  exportedFiles: string[]
  outputDir: string
}

export type ViewerData = {
  fileName: string
  headers: string[]
  rows: string[][]
  rawText: string
}
