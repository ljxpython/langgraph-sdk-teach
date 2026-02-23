export type SessionState = {
  user_id: string
  thread_id: string | null
}

export const initialSessionState: SessionState = {
  user_id: 'u-demo',
  thread_id: null,
}
