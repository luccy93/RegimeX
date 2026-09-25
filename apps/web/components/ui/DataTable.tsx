/**
 * RegimeX Web — DataTable Component
 * Volume 18 — Commit 02
 *
 * Typed, accessible data table for analytical tabular data.
 * Features:
 *   - Generic column + row typing
 *   - Sticky header option
 *   - Striped rows variant
 *   - Loading skeleton state
 *   - Empty state integration
 *   - Accessible caption + role annotations
 *   - Numeric cell alignment (tabular-nums)
 *
 * Designed for:
 *   - Regime classification tables
 *   - Transition probability matrices
 *   - Market instrument lists
 *   - Risk metric tables (VaR, CVaR, Sharpe)
 *   - Backtest performance tear sheets
 */
import React from "react";
import { cn } from "@/lib/utils/cn";
import { Skeleton } from "./Skeleton";
import { EmptyState } from "./EmptyState";

export interface DataTableColumn<TRow> {
  /** Unique column identifier */
  key: string;
  /** Column header label */
  header: string;
  /** Cell value accessor or render function */
  accessor?: keyof TRow;
  /** Custom cell render function — receives the row object */
  render?: (row: TRow, rowIndex: number) => React.ReactNode;
  /** Align cell content */
  align?: "left" | "center" | "right";
  /** Whether to apply tabular-nums font feature */
  numeric?: boolean;
  /** Minimum column width */
  minWidth?: string;
  /** Column header class override */
  headerClassName?: string;
  /** Cell class override */
  cellClassName?: string;
}

export interface DataTableProps<TRow extends Record<string, unknown>> {
  /** Table data rows */
  data: TRow[];
  /** Column definitions */
  columns: DataTableColumn<TRow>[];
  /** Optional accessible caption */
  caption?: string;
  /** Key field for row uniqueness */
  rowKey?: keyof TRow | ((row: TRow, index: number) => string | number);
  /** Enable zebra-striped rows */
  striped?: boolean;
  /** Enable sticky column header */
  stickyHeader?: boolean;
  /** Show loading skeleton rows */
  isLoading?: boolean;
  /** Number of skeleton rows to show */
  loadingRowCount?: number;
  /** Optional custom empty state */
  emptyMessage?: string;
  /** Table container class */
  className?: string;
}

function resolveRowKey<TRow extends Record<string, unknown>>(
  row: TRow,
  index: number,
  rowKey?: keyof TRow | ((row: TRow, index: number) => string | number)
): string | number {
  if (!rowKey) return index;
  if (typeof rowKey === "function") return (rowKey as (r: TRow, i: number) => string | number)(row, index);
  return String(row[rowKey] ?? index);
}

export function DataTable<TRow extends Record<string, unknown>>({
  data,
  columns,
  caption,
  rowKey,
  striped = false,
  stickyHeader = false,
  isLoading = false,
  loadingRowCount = 5,
  emptyMessage = "No data available.",
  className,
}: DataTableProps<TRow>) {
  const skeletonRows = Array.from({ length: loadingRowCount }, (_, i) => i);

  return (
    <div className={cn("data-table-container", className)}>
      <table
        className={cn(
          "data-table",
          striped && "data-table-striped",
          stickyHeader && "data-table-sticky-header"
        )}
        role="table"
      >
        {caption && (
          <caption className="data-table-caption">{caption}</caption>
        )}

        <thead className="data-table-head">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={cn(
                  "data-table-th",
                  col.align === "center" && "data-table-th-center",
                  col.align === "right" && "data-table-th-right",
                  col.headerClassName
                )}
                style={col.minWidth ? { minWidth: col.minWidth } : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody className="data-table-body">
          {isLoading ? (
            skeletonRows.map((i) => (
              <tr key={i} className="data-table-row">
                {columns.map((col) => (
                  <td key={col.key} className="data-table-td">
                    <Skeleton
                      shape="text"
                      style={{ width: "80%", height: "1rem" }}
                    />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="data-table-empty-cell">
                <EmptyState
                  title="No Data"
                  description={emptyMessage}
                />
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={resolveRowKey(row, rowIndex, rowKey)}
                className={cn(
                  "data-table-row",
                  striped && rowIndex % 2 === 1 && "data-table-row-alt"
                )}
              >
                {columns.map((col) => {
                  const cellValue = col.accessor
                    ? (row[col.accessor as string] as React.ReactNode)
                    : undefined;
                  const rendered = col.render
                    ? col.render(row, rowIndex)
                    : cellValue;

                  return (
                    <td
                      key={col.key}
                      className={cn(
                        "data-table-td",
                        col.align === "center" && "data-table-td-center",
                        col.align === "right" && "data-table-td-right",
                        col.numeric && "tabular-nums",
                        col.cellClassName
                      )}
                    >
                      {rendered as React.ReactNode}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
