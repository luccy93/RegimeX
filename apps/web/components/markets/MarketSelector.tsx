"use client";

import React, { useState, useRef, useEffect, useId } from "react";
import { cn } from "@/lib/utils/cn";
import type { MarketItemResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

export interface MarketSelectorProps {
  markets: MarketItemResponse[];
  selectedSymbol: string;
  onSelectMarket: (symbol: string) => void;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

export function MarketSelector({
  markets,
  selectedSymbol,
  onSelectMarket,
  isLoading = false,
  error = null,
  onRetry,
  className,
}: MarketSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();

  // Find currently selected market metadata
  const selectedMarket = markets.find(
    (m) => m.symbol.toUpperCase() === selectedSymbol.toUpperCase()
  );

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      // Focus search input when opened
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  // Filter markets
  const query = searchQuery.trim().toLowerCase();
  const filteredMarkets = markets.filter((m) => {
    if (!query) return true;
    return (
      m.symbol.toLowerCase().includes(query) ||
      m.description?.toLowerCase().includes(query) ||
      m.asset_class?.toLowerCase().includes(query)
    );
  });

  const handleSelect = (symbol: string) => {
    onSelectMarket(symbol);
    setIsOpen(false);
    setSearchQuery("");
  };

  return (
    <div
      ref={containerRef}
      className={cn("market-selector-container", className)}
      onKeyDown={handleKeyDown}
    >
      {/* Trigger Button */}
      <button
        type="button"
        className={cn(
          "market-selector-trigger",
          isOpen && "market-selector-trigger-open",
          isLoading && "market-selector-trigger-loading"
        )}
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label="Select market instrument"
        disabled={isLoading && markets.length === 0}
      >
        <span className="market-selector-trigger-content">
          <span className="market-selector-symbol">
            {selectedMarket ? selectedMarket.symbol : selectedSymbol || "Select Market"}
          </span>
          {selectedMarket && (
            <>
              <span className="market-selector-divider" aria-hidden="true">|</span>
              <span className="market-selector-desc" title={selectedMarket.description}>
                {selectedMarket.description || selectedMarket.asset_class}
              </span>
              <Badge variant="outline" size="sm" className="market-selector-badge">
                {selectedMarket.asset_class.replace("_", " ").toUpperCase()}
              </Badge>
            </>
          )}
        </span>
        <span className="market-selector-trigger-icon" aria-hidden="true">
          {isLoading ? <Spinner size="sm" /> : "▾"}
        </span>
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Available Markets"
          className="market-selector-dropdown animate-scale-in"
        >
          {/* Search Input Bar */}
          <div className="market-selector-search-box">
            <span className="market-selector-search-icon" aria-hidden="true">🔍</span>
            <input
              ref={searchInputRef}
              type="text"
              className="market-selector-search-input"
              placeholder="Search symbol, asset class..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Filter markets"
            />
            {searchQuery && (
              <button
                type="button"
                className="market-selector-clear-btn"
                onClick={() => setSearchQuery("")}
                aria-label="Clear search query"
              >
                ✕
              </button>
            )}
          </div>

          {/* Error State inside dropdown */}
          {error && (
            <div className="market-selector-state-msg error-state-box">
              <p className="market-selector-state-text">{error}</p>
              {onRetry && (
                <Button variant="secondary" size="sm" onClick={onRetry}>
                  Retry
                </Button>
              )}
            </div>
          )}

          {/* Loading State inside dropdown */}
          {isLoading && markets.length === 0 && !error && (
            <div className="market-selector-state-msg">
              <Spinner size="md" />
              <p className="market-selector-state-text">Loading catalog…</p>
            </div>
          )}

          {/* Market List */}
          <div className="market-selector-list">
            {!isLoading && filteredMarkets.length === 0 && !error ? (
              <div className="market-selector-empty">
                <p>No matching markets found.</p>
              </div>
            ) : (
              filteredMarkets.map((m) => {
                const isSelected =
                  m.symbol.toUpperCase() === selectedSymbol.toUpperCase();
                return (
                  <button
                    key={m.symbol}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    className={cn(
                      "market-selector-item",
                      isSelected && "market-selector-item-selected"
                    )}
                    onClick={() => handleSelect(m.symbol)}
                  >
                    <div className="market-selector-item-left">
                      <span className="market-selector-item-symbol">{m.symbol}</span>
                      <span className="market-selector-item-desc">{m.description}</span>
                    </div>
                    <div className="market-selector-item-right">
                      <Badge variant="outline" size="sm">
                        {m.asset_class}
                      </Badge>
                      {m.currency && (
                        <span className="market-selector-item-currency">{m.currency}</span>
                      )}
                      {isSelected && (
                        <span className="market-selector-check" aria-hidden="true">✓</span>
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="market-selector-footer">
            <span className="market-selector-footer-count">
              {filteredMarkets.length} of {markets.length} market{markets.length === 1 ? "" : "s"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
