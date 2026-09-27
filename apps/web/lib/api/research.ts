/**
 * RegimeX Web — AI Quantitative Research Assistant API Client
 * ============================================================
 * Provides typed methods for grounded natural language market research queries,
 * streaming evaluation via Server-Sent Events (SSE), and evidence packet retrieval.
 */

import { apiFetch, buildApiUrl } from "./client";
import { RegimeXApiError } from "./errors";
import type {
  EvidencePacketDTO,
  ResearchQueryRequest,
  ResearchResponseDTO,
} from "./types";

/**
 * Execute a synchronous market research query against the grounded assistant.
 */
export async function queryResearchAssistant(
  payload: ResearchQueryRequest,
  token?: string | null,
  fetchFn?: typeof fetch
): Promise<ResearchResponseDTO> {
  return apiFetch<ResearchResponseDTO>("/research/query", {
    method: "POST",
    body: {
      question: payload.question,
      symbol: payload.symbol || undefined,
      conversation_id: payload.conversation_id || undefined,
      context: payload.context || {},
      stream: false,
    },
    token,
    fetchFn,
  });
}

/**
 * Retrieve verified evidence packets assembled for an instrument symbol.
 */
export async function getInstrumentEvidenceContext(
  symbol: string,
  token?: string | null,
  fetchFn?: typeof fetch
): Promise<EvidencePacketDTO[]> {
  const cleanSymbol = symbol.trim().toUpperCase();
  return apiFetch<EvidencePacketDTO[]>(`/research/context/${encodeURIComponent(cleanSymbol)}`, {
    method: "GET",
    token,
    fetchFn,
  });
}

export interface StreamEventCallbacks {
  onMetadata?: (data: { requestId: string; intent: string; symbol: string | null; model: string }) => void;
  onEvidence?: (data: { evidence: EvidencePacketDTO[] }) => void;
  onToken?: (token: string) => void;
  onCitation?: (data: { citations: ResearchResponseDTO["citations"] }) => void;
  onComplete?: (response: ResearchResponseDTO) => void;
  onError?: (error: Error) => void;
}

/**
 * Stream natural language research queries using Server-Sent Events (SSE).
 * Returns an abort function to cancel in-flight streams.
 */
export async function streamResearchQuery(
  payload: ResearchQueryRequest,
  callbacks: StreamEventCallbacks,
  token?: string | null,
  fetchFn?: typeof fetch
): Promise<() => void> {
  const activeFetch = fetchFn ?? fetch;
  const url = buildApiUrl("/research/query");
  const abortController = new AbortController();

  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  (async () => {
    try {
      const response = await activeFetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question: payload.question,
          symbol: payload.symbol || undefined,
          conversation_id: payload.conversation_id || undefined,
          context: payload.context || {},
          stream: true,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        let errorPayload: unknown;
        try {
          errorPayload = await response.json();
        } catch {
          errorPayload = null;
        }
        const requestId = response.headers.get("x-request-id") || undefined;
        throw RegimeXApiError.fromBackend(response.status, errorPayload, requestId);
      }

      if (!response.body) {
        throw new Error("Response body is not readable for streaming.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() ?? "";

        for (const block of lines) {
          if (!block.trim()) continue;

          let eventType = "message";
          let eventData = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.replace("event:", "").trim();
            } else if (line.startsWith("data:")) {
              eventData = line.replace("data:", "").trim();
            }
          }

          if (eventData) {
            try {
              const parsed = JSON.parse(eventData);

              if (eventType === "metadata" && callbacks.onMetadata) {
                callbacks.onMetadata({
                  requestId: parsed.request_id,
                  intent: parsed.intent,
                  symbol: parsed.symbol,
                  model: parsed.model,
                });
              } else if (eventType === "evidence" && callbacks.onEvidence) {
                callbacks.onEvidence({ evidence: parsed.evidence || [] });
              } else if (eventType === "token" && callbacks.onToken) {
                callbacks.onToken(parsed.token || "");
              } else if (eventType === "citation" && callbacks.onCitation) {
                callbacks.onCitation({ citations: parsed.citations || [] });
              } else if (eventType === "complete" && callbacks.onComplete) {
                callbacks.onComplete({
                  answer: parsed.answer,
                  citations: parsed.citations || [],
                  evidence: parsed.evidence || [],
                  model: parsed.model,
                  generated_at: parsed.generated_at,
                  request_id: parsed.request_id,
                  intent: parsed.intent,
                  symbol: parsed.symbol,
                });
              } else if (eventType === "error") {
                const err = new Error(parsed.error || "Streaming error occurred.");
                if (callbacks.onError) callbacks.onError(err);
              }
            } catch (jsonErr) {
              // Ignore partial JSON parse errors
            }
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error)?.name === "AbortError") {
        // Stream aborted by user
        return;
      }
      if (callbacks.onError) {
        callbacks.onError(err instanceof Error ? err : new Error(String(err)));
      }
    }
  })();

  return () => {
    abortController.abort();
  };
}
