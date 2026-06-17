// Fire Train API client

import type {
  AvailableModelsResponse,
  DatasetPreview,
  DatasetUploadResponse,
  JobEvent,
  StartJobRequest,
  SystemInfo,
  TestModelResponse,
  TrainedModel,
  TrainingJob,
} from '../types/train'

const BASE = '/api/train'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(options.headers as Record<string, string>) }
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = err.detail
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

export function getSystemInfo() {
  return request<SystemInfo>('/system')
}

export function getAvailableBaseModels() {
  return request<AvailableModelsResponse>('/models/available')
}

export function getTrainedModels() {
  return request<{ models: TrainedModel[]; count: number }>('/models')
}

export function deleteTrainedModel(name: string) {
  return request<{ deleted: boolean; name: string }>(`/models/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  })
}

export function testTrainedModel(
  name: string,
  body: { prompt: string; max_length?: number; temperature?: number },
) {
  return request<TestModelResponse>(`/models/${encodeURIComponent(name)}/test`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function uploadDataset(files: FileList | File[]) {
  const form = new FormData()
  const list = Array.from(files)
  for (const file of list) {
    form.append('files', file, file.webkitRelativePath || file.name)
  }
  const res = await fetch(`${BASE}/datasets/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<DatasetUploadResponse>
}

export function previewDataset(datasetId: string) {
  return request<DatasetPreview>('/datasets/preview', {
    method: 'POST',
    body: JSON.stringify({ dataset_id: datasetId }),
  })
}

export function deleteDataset(datasetId: string) {
  return request<{ deleted: boolean }>(`/datasets/${datasetId}`, { method: 'DELETE' })
}

export function listTrainingJobs() {
  return request<{ jobs: TrainingJob[]; count: number }>('/jobs')
}

export function getTrainingJob(jobId: string) {
  return request<TrainingJob>(`/jobs/${jobId}`)
}

export function getJobEvents(jobId: string, since = 0) {
  return request<{ events: JobEvent[]; since: number; total: number }>(
    `/jobs/${jobId}/events?since=${since}`,
  )
}

export function startTrainingJob(body: StartJobRequest) {
  return request<{ job: TrainingJob; stream_url: string }>('/jobs', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function cancelTrainingJob(jobId: string) {
  return request<{ cancelled: boolean; job: TrainingJob }>(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  })
}

export function createJobWebSocket(jobId: string): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${proto}//${window.location.host}${BASE}/jobs/${jobId}/stream`)
}
