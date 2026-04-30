import { type FC, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuditEvents } from "../api";
import type { AuditListParams, AuditResult } from "../types";

/*
 * Top-level renderer for the audit-log page.
 *
 * Owns:
 *   - Filter state (actor / action / result)
 *   - Pagination cursor stack
 *   - List query
 *   - Loading / empty / error rendering
 *
 * Detail rendering (decrypted before/after state) lands in a
 * follow-up PR alongside before/after capture in middleware
 * (AL.2c.4) — without state capture there's nothing to show in
 * a detail dialog beyond the row metadata.
 */

type ResultOption = { value: "" | AuditResult };

const RESULT_OPTIONS: ResultOption[] = [
    { value: "" },
    { value: "success" },
    { value: "denied" },
    { value: "failure" },
];

const formatTimestamp = (iso: string): string => {
    try {
        return new Date(iso).toLocaleString();
    } catch {
        return iso;
    }
};

export const AuditEventsTable: FC = () => {
    const { t } = useTranslation();

    const [filters, setFilters] = useState<{
        actor_username: string;
        action: string;
        result: "" | AuditResult;
    }>({
        actor_username: "",
        action: "",
        result: "",
    });
    // Stack of cursor values; pop on "back". Empty = first page.
    const [cursorStack, setCursorStack] = useState<number[]>([]);
    const currentCursor =
        cursorStack.length > 0 ? cursorStack[cursorStack.length - 1] : undefined;

    const params: AuditListParams = {
        actor_username: filters.actor_username || undefined,
        action: filters.action || undefined,
        result: filters.result || undefined,
        cursor: currentCursor,
        limit: 50,
    };

    const { data, isLoading, isError, error, refetch } = useAuditEvents(params);

    const handleNext = () => {
        if (data?.next_cursor != null) {
            setCursorStack([...cursorStack, data.next_cursor]);
        }
    };

    const handlePrev = () => {
        setCursorStack(cursorStack.slice(0, -1));
    };

    const handleResetFilters = () => {
        setFilters({ actor_username: "", action: "", result: "" });
        setCursorStack([]);
    };

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap gap-2 items-end">
                <div>
                    <label className="block text-xs">
                        {t("page.audit.filter.actor")}
                    </label>
                    <input
                        type="text"
                        className="border rounded px-2 py-1"
                        value={filters.actor_username}
                        onChange={(e) => {
                            setFilters({
                                ...filters,
                                actor_username: e.target.value,
                            });
                            setCursorStack([]);
                        }}
                        placeholder="alice"
                    />
                </div>
                <div>
                    <label className="block text-xs">
                        {t("page.audit.filter.action")}
                    </label>
                    <input
                        type="text"
                        className="border rounded px-2 py-1"
                        value={filters.action}
                        onChange={(e) => {
                            setFilters({ ...filters, action: e.target.value });
                            setCursorStack([]);
                        }}
                        placeholder="billing.plan"
                    />
                </div>
                <div>
                    <label className="block text-xs">
                        {t("page.audit.filter.result.label")}
                    </label>
                    <select
                        className="border rounded px-2 py-1"
                        value={filters.result}
                        onChange={(e) => {
                            setFilters({
                                ...filters,
                                result: e.target.value as "" | AuditResult,
                            });
                            setCursorStack([]);
                        }}
                    >
                        {RESULT_OPTIONS.map((opt) => {
                            // Inline t() per option so the drift checker
                            // (grep-based, can't follow indirection) sees
                            // every key as a literal string.
                            const label =
                                opt.value === ""
                                    ? t("page.audit.filter.result.all")
                                    : opt.value === "success"
                                      ? t("page.audit.filter.result.success")
                                      : opt.value === "denied"
                                        ? t("page.audit.filter.result.denied")
                                        : t("page.audit.filter.result.failure");
                            return (
                                <option key={opt.value} value={opt.value}>
                                    {label}
                                </option>
                            );
                        })}
                    </select>
                </div>
                <button
                    type="button"
                    className="border rounded px-3 py-1"
                    onClick={handleResetFilters}
                >
                    {t("page.audit.filter.reset")}
                </button>
                <button
                    type="button"
                    className="border rounded px-3 py-1"
                    onClick={() => refetch()}
                >
                    {t("page.audit.action.refresh")}
                </button>
            </div>

            {isLoading && <div>{t("page.audit.loading")}</div>}
            {isError && (
                <div className="text-red-600">
                    {t("page.audit.error", {
                        message:
                            (error as Error)?.message ?? "unknown",
                    })}
                </div>
            )}
            {data && data.items.length === 0 && (
                <div>{t("page.audit.empty")}</div>
            )}

            {data && data.items.length > 0 && (
                <table className="min-w-full text-sm">
                    <thead>
                        <tr>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.ts")}
                            </th>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.actor")}
                            </th>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.action")}
                            </th>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.result")}
                            </th>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.status")}
                            </th>
                            <th className="text-left px-2 py-1">
                                {t("page.audit.column.ip")}
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.items.map((row) => (
                            <tr key={row.id} className="border-t">
                                <td className="px-2 py-1">
                                    {formatTimestamp(row.ts)}
                                </td>
                                <td className="px-2 py-1">
                                    {row.actor_username ?? (
                                        <span className="text-gray-400">
                                            {t("page.audit.actor.anonymous")}
                                        </span>
                                    )}
                                </td>
                                <td className="px-2 py-1">{row.action}</td>
                                <td className="px-2 py-1">
                                    <span
                                        className={
                                            row.result === "success"
                                                ? "text-green-600"
                                                : row.result === "denied"
                                                  ? "text-yellow-600"
                                                  : "text-red-600"
                                        }
                                    >
                                        {row.result}
                                    </span>
                                </td>
                                <td className="px-2 py-1">{row.status_code}</td>
                                <td className="px-2 py-1">{row.ip}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            )}

            <div className="flex gap-2">
                <button
                    type="button"
                    className="border rounded px-3 py-1 disabled:opacity-50"
                    onClick={handlePrev}
                    disabled={cursorStack.length === 0}
                >
                    {t("page.audit.pagination.prev")}
                </button>
                <button
                    type="button"
                    className="border rounded px-3 py-1 disabled:opacity-50"
                    onClick={handleNext}
                    disabled={data?.next_cursor == null}
                >
                    {t("page.audit.pagination.next")}
                </button>
            </div>
        </div>
    );
};
