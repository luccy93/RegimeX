"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import type {
  CurrentRegimeContextDTO,
  EvidencePacketDTO,
  MarketItemResponse,
  ResearchMessage,
  ResearchResponseDTO,
} from "@/lib/api/types";
import { listMarkets, getMarketRegime } from "@/lib/api/markets";
import {
  queryResearchAssistant,
  streamResearchQuery,
} from "@/lib/api/research";

import { ResearchHeader } from "./ResearchHeader";
import { ResearchMarketContextStrip } from "./ResearchMarketContextStrip";
import { ResearchEmptyState } from "./ResearchEmptyState";
import { ResearchMessageCard } from "./ResearchMessageCard";
import { ResearchComposer } from "./ResearchComposer";
import { ResearchEvidencePanel } from "./ResearchEvidencePanel";

export function ResearchWorkspace() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // URL state: ?symbol=SPY
  const urlSymbol = searchParams.get("symbol");

  // Markets Catalog State
  const [markets, setMarkets] = useState<MarketItemResponse[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    urlSymbol?.toUpperCase() || ""
  );

  // Market Regime Context State
  const [regimeContext, setRegimeContext] =
    useState<CurrentRegimeContextDTO | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [isLoadingRegime, setIsLoadingRegime] = useState<boolean>(false);

  // Conversation State
  const [messages, setMessages] = useState<ResearchMessage[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Evidence Drawer / Panel State
  const [isEvidencePanelOpen, setIsEvidencePanelOpen] =
    useState<boolean>(false);
  const [selectedCitationId, setSelectedCitationId] = useState<number | null>(
    null
  );
  const [activeEvidencePackets, setActiveEvidencePackets] = useState<
    EvidencePacketDTO[]
  >([]);
  const [activeCitations, setActiveCitations] = useState<
    ResearchResponseDTO["citations"]
  >([]);

  // Abort controller reference for active generation
  const cancelStreamRef = useRef<(() => void) | null>(null);
  const conversationEndRef = useRef<HTMLDivElement>(null);

  // 1. Fetch Market Catalog
  useEffect(() => {
    let isMounted = true;
    async function loadCatalog() {
      try {
        const resp = await listMarkets({ limit: 100 });
        if (isMounted && resp.items?.length > 0) {
          setMarkets(resp.items);
          if (!selectedSymbol) {
            const querySym = urlSymbol?.toUpperCase();
            const matched = resp.items.find(
              (m) => m.symbol.toUpperCase() === querySym
            );
            if (matched) {
              setSelectedSymbol(matched.symbol);
            } else if (!querySym) {
              // Default to SPY or first available market
              const spy = resp.items.find((m) => m.symbol.toUpperCase() === "SPY");
              setSelectedSymbol(spy ? spy.symbol : resp.items[0].symbol);
            }
          }
        }
      } catch {
        // Fallback gracefully without blocking workspace
      }
    }
    loadCatalog();
    return () => {
      isMounted = false;
    };
  }, [urlSymbol, selectedSymbol]);

  // 2. Fetch Active Market Regime Context when symbol changes
  useEffect(() => {
    let isMounted = true;
    if (!selectedSymbol) {
      setRegimeContext(null);
      setConfidence(null);
      return;
    }

    async function loadRegime() {
      setIsLoadingRegime(true);
      try {
        const resp = await getMarketRegime(selectedSymbol);
        if (isMounted) {
          setRegimeContext(resp.current_context || null);
          setConfidence(resp.confidence ?? null);
        }
      } catch {
        if (isMounted) {
          setRegimeContext(null);
          setConfidence(null);
        }
      } finally {
        if (isMounted) setIsLoadingRegime(false);
      }
    }

    loadRegime();
    return () => {
      isMounted = false;
    };
  }, [selectedSymbol]);

  // Auto-scroll to bottom of conversation
  useEffect(() => {
    if (messages.length > 0) {
      conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Handle symbol change
  const handleSelectSymbol = useCallback(
    (sym: string) => {
      const clean = sym.trim().toUpperCase();
      setSelectedSymbol(clean);
      const params = new URLSearchParams(window.location.search);
      if (clean) {
        params.set("symbol", clean);
      } else {
        params.delete("symbol");
      }
      router.replace(`?${params.toString()}`);
    },
    [router]
  );

  // Clear conversation
  const handleClearConversation = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setMessages([]);
    setIsLoading(false);
    setIsEvidencePanelOpen(false);
    setSelectedCitationId(null);
    setActiveEvidencePackets([]);
    setActiveCitations([]);
  }, []);

  // Cancel generation
  const handleCancelGeneration = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setIsLoading(false);
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (last.role === "assistant" && (last.status === "loading" || last.status === "streaming")) {
        return [
          ...prev.slice(0, -1),
          {
            ...last,
            status: "complete",
            content: last.content
              ? `${last.content} [Generation stopped by user]`
              : "Inquiry evaluation was cancelled.",
          },
        ];
      }
      return prev;
    });
  }, []);

  // Send message & execute inquiry
  const handleSendMessage = useCallback(
    async (question: string) => {
      const cleanQuestion = question.trim();
      if (!cleanQuestion || isLoading) return;

      const userMsgId = `user-${Date.now()}`;
      const assistantMsgId = `asst-${Date.now() + 1}`;

      const userMessage: ResearchMessage = {
        id: userMsgId,
        role: "user",
        content: cleanQuestion,
        timestamp: new Date().toISOString(),
        symbol: selectedSymbol || null,
      };

      const assistantMessage: ResearchMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        symbol: selectedSymbol || null,
        status: "loading",
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      // Attempt streaming with fallback
      try {
        let accumulatedText = "";
        let finalCitations: ResearchResponseDTO["citations"] = [];
        let finalEvidence: EvidencePacketDTO[] = [];
        let modelName = "";
        let intentName = "";

        const abortFn = await streamResearchQuery(
          {
            question: cleanQuestion,
            symbol: selectedSymbol || null,
            stream: true,
          },
          {
            onMetadata: (meta) => {
              modelName = meta.model;
              intentName = meta.intent;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        model: meta.model,
                        intent: meta.intent,
                        status: "streaming",
                      }
                    : msg
                )
              );
            },
            onEvidence: (evData) => {
              finalEvidence = evData.evidence;
              setActiveEvidencePackets(evData.evidence);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, evidence: evData.evidence }
                    : msg
                )
              );
            },
            onToken: (token) => {
              accumulatedText += token;
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        content: accumulatedText,
                        status: "streaming",
                      }
                    : msg
                )
              );
            },
            onCitation: (citData) => {
              finalCitations = citData.citations;
              setActiveCitations(citData.citations);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? { ...msg, citations: citData.citations }
                    : msg
                )
              );
            },
            onComplete: (res) => {
              setIsLoading(false);
              cancelStreamRef.current = null;
              setActiveEvidencePackets(res.evidence);
              setActiveCitations(res.citations);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantMsgId
                    ? {
                        ...msg,
                        content: res.answer,
                        citations: res.citations,
                        evidence: res.evidence,
                        model: res.model,
                        intent: res.intent,
                        status: "complete",
                      }
                    : msg
                )
              );
            },
            onError: async (err) => {
              // Fallback to synchronous query if streaming connection fails
              try {
                const syncResp = await queryResearchAssistant({
                  question: cleanQuestion,
                  symbol: selectedSymbol || null,
                });
                setIsLoading(false);
                cancelStreamRef.current = null;
                setActiveEvidencePackets(syncResp.evidence);
                setActiveCitations(syncResp.citations);
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsgId
                      ? {
                          ...msg,
                          content: syncResp.answer,
                          citations: syncResp.citations,
                          evidence: syncResp.evidence,
                          model: syncResp.model,
                          intent: syncResp.intent,
                          status: "complete",
                        }
                      : msg
                  )
                );
              } catch (syncErr: unknown) {
                setIsLoading(false);
                cancelStreamRef.current = null;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMsgId
                      ? {
                          ...msg,
                          status: "error",
                          error:
                            (syncErr as Error)?.message ||
                            "Failed to generate grounded research response.",
                        }
                      : msg
                  )
                );
              }
            },
          }
        );

        cancelStreamRef.current = abortFn;
      } catch (err: unknown) {
        setIsLoading(false);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  status: "error",
                  error:
                    (err as Error)?.message ||
                    "An error occurred while connecting to the research assistant.",
                }
              : msg
          )
        );
      }
    },
    [isLoading, selectedSymbol]
  );

  const selectedMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  return (
    <div
      className={`research-workspace-root ${
        isEvidencePanelOpen ? "evidence-panel-open" : ""
      }`}
    >
      <div className="research-main-column">
        {/* Header */}
        <ResearchHeader
          markets={markets}
          selectedSymbol={selectedSymbol}
          onSelectSymbol={handleSelectSymbol}
          onClearConversation={handleClearConversation}
          messageCount={messages.length}
          isLoading={isLoading}
        />

        {/* Selected Market Context Strip */}
        <ResearchMarketContextStrip
          selectedSymbol={selectedSymbol}
          marketItem={selectedMarket}
          regimeContext={regimeContext}
          confidence={confidence}
          isLoadingRegime={isLoadingRegime}
        />

        {/* Conversation Stream or Empty State */}
        <div className="research-conversation-area" role="feed" aria-label="Conversation messages">
          {messages.length === 0 ? (
            <ResearchEmptyState
              onSelectPrompt={handleSendMessage}
              selectedSymbol={selectedSymbol}
            />
          ) : (
            <div className="research-messages-list">
              {messages.map((msg) => (
                <ResearchMessageCard
                  key={msg.id}
                  message={msg}
                  onSelectCitation={(id) => setSelectedCitationId(id)}
                  onOpenEvidencePanel={() => setIsEvidencePanelOpen(true)}
                  onRetry={(q) => handleSendMessage(q)}
                  selectedCitationId={selectedCitationId}
                />
              ))}
              <div ref={conversationEndRef} />
            </div>
          )}
        </div>

        {/* Composer */}
        <ResearchComposer
          onSendMessage={handleSendMessage}
          onCancelGeneration={handleCancelGeneration}
          isLoading={isLoading}
          selectedSymbol={selectedSymbol}
        />
      </div>

      {/* Auditable Evidence Panel */}
      <ResearchEvidencePanel
        isOpen={isEvidencePanelOpen}
        onClose={() => setIsEvidencePanelOpen(false)}
        citations={activeCitations}
        evidence={activeEvidencePackets}
        selectedCitationId={selectedCitationId}
        onSelectCitation={(id) => setSelectedCitationId(id)}
      />
    </div>
  );
}
