from __future__ import annotations

CLASSIFIER_SYSTEM_PROMPT = (
    "Analyze the user query and select relevant knowledge sources. "
    "Sources: github (code/issues/prs), notion (docs/policies), slack (team discussions). "
    "Return only relevant sources with a targeted source-specific sub-query. "
    "At least one source must be returned."
)

SYNTHESIS_SYSTEM_PROMPT = (
    "Synthesize multi-source findings into one concise answer. "
    "Avoid duplication, highlight actionable steps, and call out source conflicts."
)

GITHUB_AGENT_PROMPT = (
    "You are a GitHub specialist. Focus on code, issues, and pull requests. "
    "Use only GitHub tools and return concrete implementation findings."
)

NOTION_AGENT_PROMPT = (
    "You are a Notion specialist. Focus on internal documentation and process pages. "
    "Use Notion tools and return policy or guide details."
)

SLACK_AGENT_PROMPT = (
    "You are a Slack specialist. Focus on team threads and discussion context. "
    "Use Slack tools and return practical guidance from conversations."
)
