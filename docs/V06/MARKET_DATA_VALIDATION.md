# Market Data Validation Pipeline Architecture

## Overview

The Market Data Validation Pipeline (`apps/api/app/modules/data_quality/`) provides deterministic, audit-ready data verification for incoming market data records. It acts as an integrity barrier between data acquisition (V05) and persistence/analytics (V06 Commit 02 & V07).

> [!IMPORTANT]
> **V06 Commit 01 Scope Guarantee:**
> V06 Commit 01 detects and reports data-quality problems; it does **not** persist or silently repair market data.

---

## Architectural Flow

```
┌────────────────────────────────────────────────────────┐
│                   Market Data Provider                 │
│                 (e.g. YahooFinanceProvider)            │
└───────────────────────────┬────────────────────────────┘
                            │ MarketDataResult
                            ▼
┌────────────────────────────────────────────────────────┐
│              MarketDataValidationPipeline              │
│                                                        │
│  1. Schema Validation       (DQ-SCHEMA-001)           │
│  2. Timestamp Integrity     (DQ-TIME-001, DQ-TIME-002)│
│  3. OHLC Price Integrity    (DQ-OHLC-001 to 003)      │
│  4. Volume Integrity        (DQ-VOL-001)              │
│  5. Duplicate Detection     (DQ-DUP-001)              │
│  6. Ordering Validation     (DQ-ORDER-001)            │
│  7. Trading Calendar Check  (DQ-CAL-001, DQ-CAL-002)  │
│  8. Missing / Gap Detection (DQ-GAP-001)              │
│  9. Staleness Evaluation    (DQ-STALE-001)            │
└───────────────────────────┬────────────────────────────┘
                            │ QualityReport
                            ▼
           ┌─────────────────────────────────┐
           │      Quality Gate Status        │
           │                                 │
           │  PASS: Zero errors or warnings  │
           │  WARN: Warnings (gaps/staleness)│
           │  FAIL: Structural violations    │
           └────────────────┬────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
         [is_valid == True]       [is_valid == False]
               │                         │
               ▼                         ▼
     V06 Commit 02 Storage       Logged & Blocked from
                                 Analytics / Hypertables
```

---

## Quality Categories & Rule IDs

| Category | Rule ID | Description | Default Severity | Gate Impact |
|---|---|---|---|---|
| **SCHEMA** | `DQ-SCHEMA-001` | Detects non-finite numbers (NaN, +Inf, -Inf) in OHLCV fields | `CRITICAL` | `FAIL` |
| **TIMESTAMP** | `DQ-TIME-001` | Enforces timezone awareness and canonical UTC offsets | `CRITICAL` | `FAIL` |
| **TIMESTAMP** | `DQ-TIME-002` | Detects future observation timestamps relative to reference clock | `CRITICAL` | `FAIL` |
| **OHLC** | `DQ-OHLC-001` | Verifies `high >= max(open, close, low)` | `CRITICAL` | `FAIL` |
| **OHLC** | `DQ-OHLC-002` | Verifies `low <= min(open, close, high)` | `CRITICAL` | `FAIL` |
| **OHLC** | `DQ-OHLC-003` | Enforces strictly positive price values (`open, high, low, close > 0`) | `CRITICAL` | `FAIL` |
| **VOLUME** | `DQ-VOL-001` | Enforces non-negative and finite traded volume (`volume >= 0`) | `CRITICAL` | `FAIL` |
| **DUPLICATE** | `DQ-DUP-001` | Flags duplicate observations matching `(symbol, timestamp, interval)` | `CRITICAL` | `FAIL` |
| **ORDERING** | `DQ-ORDER-001` | Enforces strictly increasing chronological ordering of bars | `CRITICAL` | `FAIL` |
| **CALENDAR** | `DQ-CAL-001` | Flags observations occurring on non-trading days (weekends, holidays) | `WARNING` | `WARN` |
| **CALENDAR** | `DQ-CAL-002` | Flags intraday observations falling outside regular trading hours | `WARNING` | `WARN` |
| **GAPS** | `DQ-GAP-001` | Detects missing expected trading sessions or missing intraday bars | `WARNING` | `WARN` |
| **STALENESS** | `DQ-STALE-001` | Flags datasets whose latest bar exceeds configured freshness threshold | `WARNING` | `WARN` |

---

## Severity & Quality Gate Model

The pipeline maps issues to three severity tiers:
- **`CRITICAL`**: Structural data integrity failures (invalid prices, non-finite values, duplicate bars, future timestamps). Any critical issue immediately transitions the report status to **`QualityStatus.FAIL`**.
- **`WARNING`**: Non-fatal anomalies (missing bars/gaps, older dataset staleness, off-hours trades). If no critical issues are present, one or more warnings result in **`QualityStatus.WARN`**.
- **`INFO`**: Diagnostic context. Does not alter pass status.

```python
# Gate evaluation rule:
if critical_count > 0:
    status = QualityStatus.FAIL
elif warning_count > 0:
    status = QualityStatus.WARN
else:
    status = QualityStatus.PASS
```

---

## Trading Calendar Abstraction

Exchange calendars inherit from `TradingCalendar` (`domain/calendar.py`):

```
         TradingCalendar (ABC)
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
NYSECalendar  NSECalendar  ContinuousCalendar
(US Equities) (IN Equities) (Crypto & FX 24/7)
```

- **`NYSECalendar`**: Covers regular hours (09:30–16:00 ET) and standard US market holidays (New Year's, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas).
- **`NSECalendar`**: Covers regular hours (09:15–15:30 IST) and standard Indian national market holidays (Republic Day, Good Friday, Independence Day, Gandhi Jayanti, Christmas).
- **`ContinuousCalendar`**: Covers 24/7/365 digital asset markets where every day is a trading session and no market closures exist.
- **`CalendarRegistry`**: Resolves the appropriate calendar automatically using `instrument.asset_class` and `instrument.exchange`.

---

## Gap Detection & Staleness Policy

### Gap Detection (`DQ-GAP-001`)
- **Daily bars**: Evaluates the date interval between the first and last observation against `calendar.expected_trading_days(min_date, max_date)`. Normal exchange weekend and holiday closures are recognized by the calendar and **not** flagged as gaps. Only missing active business sessions trigger `DQ-GAP-001`.
- **Intraday bars**: Flags gaps when consecutive bars within the same trading session exceed 1.5x the expected interval delta.

### Staleness Policy (`DQ-STALE-001`)
- Compares the latest bar timestamp against an explicit `reference_time` clock.
- If `reference_time - latest_timestamp > staleness_threshold_hours` (default 72h), a warning is emitted.
- In automated unit testing, an explicit deterministic clock is passed to prevent reliance on `datetime.now()`.

---

## What Validation Does NOT Do (Explicit Non-Goals)

To prevent data corruption and maintain quantitative auditability, this pipeline strictly adheres to the following boundaries:
1. **No Silent Repair:** Missing bars are not fabricated or imputed with interpolated prices.
2. **No Silent Sorting:** Out-of-order records are flagged as `DQ-ORDER-001`, not reordered secretly during validation.
3. **No Silent Deduplication:** Duplicates are recorded with full provenance diagnostics, not deleted silently.
4. **No Database Persistence:** Storing validated data in PostgreSQL / Timescale hypertables is deferred to V06 Commit 02.
5. **No Feature Engineering:** Computing technical indicators, returns, or volatility features is deferred to V07.
