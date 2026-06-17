// Fire Train — TypeScript interfaces mirroring the Python API

export interface SystemInfo {
  training_available: boolean
  training_error?: string | null
  install_hint: string
  cuda_available: boolean
  cuda_device?: string | null
  device: string
  models_dir: string
  default_model_name: string
  local_only: boolean
  cost: string
}

export interface BaseModelInfo {
  id: string
  hf_id: string
  local_free: boolean
  recommended: boolean
}

export interface AvailableModelsResponse {
  local_free: BaseModelInfo[]
  gated: BaseModelInfo[]
  default: string
}

export interface TrainedModel {
  name: string
  description?: string
  base_model?: string
  epochs?: number
  num_files?: number
  total_characters?: number
  created_at?: string
  local_only?: boolean
  provider?: string
}

export interface DatasetUploadResponse {
  dataset_id: string
  path: string
  files: string[]
  file_count: number
}

export interface DatasetPreview {
  dataset_id: string
  stats: Record<string, unknown>
  sample_count: number
  preview: string[]
  ready: boolean
}

export interface TrainingJob {
  id: string
  name: string
  base_model: string
  data_path: string
  status: JobStatus
  progress: number
  phase: string
  message: string
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  error?: string | null
  result?: Record<string, unknown> | null
  config: Record<string, unknown>
  event_count: number
}

export type JobStatus =
  | 'pending'
  | 'processing_data'
  | 'loading_model'
  | 'training'
  | 'saving'
  | 'completed'
  | 'failed'
  | 'cancelled'

export interface JobEvent {
  ts: string
  phase: string
  message: string
  progress: number
  logs?: Record<string, number>
  error?: string
}

export interface StartJobRequest {
  name: string
  dataset_id: string
  base_model: string
  description?: string
  epochs: number
  batch_size: number
  learning_rate: number
  max_length: number
  force: boolean
}

export interface TestModelResponse {
  name: string
  prompt: string
  response: string
  generation_time?: number
  local_only: boolean
}

export interface StreamFrame {
  event?: JobEvent
  status?: JobStatus
  progress?: number
  phase?: string
  message?: string
  done?: boolean
  error?: string
}
