# T10 Notes

- Added controlled assistants read endpoints: `POST /assistants/search` and `GET /assistants/{assistant_id}`.
- Both endpoints require identity via `Depends(require_identity)`.
- Exposed only one default assistant: `agent`.
- Assistant mutations remain unavailable (for example, `POST /assistants` is still not implemented).
