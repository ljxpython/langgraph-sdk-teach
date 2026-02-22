export type SessionState = {
  userId: string
  threadId: string | null
}

export const initialSessionState: SessionState = {
  userId: 'u-demo',
  threadId: null,
}
