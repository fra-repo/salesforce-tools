import type { HealthResponse, LimitsItem, MassiveQueryPayload, MassiveQueryResult } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { error?: string }
  if (!response.ok) {
    throw new Error(payload.error ?? `Request failed with status ${response.status}`)
  }
  return payload
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`)
  return parseResponse<HealthResponse>(response)
}

export async function fetchOrgs(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/orgs`)
  const payload = await parseResponse<{ items: string[] }>(response)
  return payload.items
}

export async function fetchLimits(orgAlias: string): Promise<LimitsItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/limits?org=${encodeURIComponent(orgAlias)}`)
  const payload = await parseResponse<{ items: LimitsItem[] }>(response)
  return payload.items
}

export async function executeMassiveQuery(payload: MassiveQueryPayload): Promise<MassiveQueryResult> {
  const response = await fetch(`${API_BASE_URL}/api/massive-query/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return parseResponse<MassiveQueryResult>(response)
}
