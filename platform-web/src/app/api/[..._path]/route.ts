import { initApiPassthrough } from "langgraph-nextjs-api-passthrough";
import { NextResponse } from "next/server";

// This file acts as a proxy for requests to your LangGraph server.
// Read the [Going to Production](https://github.com/langchain-ai/agent-chat-ui?tab=readme-ov-file#going-to-production) section for more information.

const langGraphApiUrl = process.env.LANGGRAPH_API_URL;
const langSmithApiKey = process.env.LANGSMITH_API_KEY;

// Allow local/dev usage without configuring the passthrough.
// If this endpoint is hit without LANGGRAPH_API_URL set, return a helpful error
// instead of failing with a low-level network error.
const misconfigured = async () =>
  NextResponse.json(
    {
      error: "LANGGRAPH_API_URL is not configured",
      hint: "If you want to use the Next.js /api passthrough, set LANGGRAPH_API_URL (and optionally LANGSMITH_API_KEY). Otherwise, set NEXT_PUBLIC_API_URL to your LangGraph server URL (e.g. http://localhost:2024).",
    },
    { status: 500 },
  );

const passthrough = langGraphApiUrl
  ? initApiPassthrough({
      apiUrl: langGraphApiUrl,
      ...(langSmithApiKey ? { apiKey: langSmithApiKey } : {}),
      runtime: "edge",
    })
  : null;

export const GET = passthrough?.GET ?? misconfigured;
export const POST = passthrough?.POST ?? misconfigured;
export const PUT = passthrough?.PUT ?? misconfigured;
export const PATCH = passthrough?.PATCH ?? misconfigured;
export const DELETE = passthrough?.DELETE ?? misconfigured;
export const OPTIONS = passthrough?.OPTIONS ?? (() => new NextResponse(null, { status: 204 }));
export const runtime = "edge";
