export type StreamEnvelope = {
  event: string
  data: unknown
}

export type UiStage =
  | 'run_started'
  | 'model_streaming'
  | 'tool_calling'
  | 'tool_completed'
  | 'human_review_required'
  | 'final_answer'
  | 'run_done'
  | 'run_error'
