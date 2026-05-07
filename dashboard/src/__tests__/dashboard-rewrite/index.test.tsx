/**
 * Vitest snapshot + unit tests for the operator home page (Wave-A3).
 *
 * Spec acceptance criteria (per PLAN Wave-A.3):
 *   1. PanelHead title rendered.
 *   2. BigChart SVG present (mock data path).
 *   3. At least 1 KPI rendered.
 *
 * Strategy: test the OperatorHomePage component in isolation by mocking
 * all data hooks (no network). This avoids TanStack Query's async dance
 * while still exercising the render tree.
 *
 * Hooks mocked:
 *   - useUsersStatsQuery  → UsersStatsDefault + overrides
 *   - useTotalTrafficQuery → { usages: [[10,20,30,...]], total: 60 }
 *   - useAuditEvents      → { items: [3 sample events], next_cursor: null }
 *   - useHealthExtended   → { subsystems: [], uptime_seconds: 3600, version: "1.0.0" }
 *
 * Import aliases: the test runs via vitest with the same `@marzneshin`
 * alias as the app. No special mapping needed — vitest.config.ts already
 * mirrors vite.config.ts.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";
import { OperatorHomePage } from "../../routes/_dashboard/index.lazy";

// ---------------------------------------------------------------------------
// Mock dependencies
// ---------------------------------------------------------------------------

vi.mock("@marzneshin/modules/users", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@marzneshin/modules/users")>();
    return {
        ...actual,
        useUsersStatsQuery: () => ({
            data: {
                total: 150,
                active: 42,
                on_hold: 3,
                expired: 5,
                limited: 2,
                online: 7,
                recent_subscription_updates: [],
            },
        }),
    };
});

vi.mock("@marzneshin/features/total-traffic-widget/api", () => ({
    useTotalTrafficQuery: () => ({
        data: {
            // 14 days of per-node traffic (bytes). Two nodes.
            usages: [
                [1e9, 2e9, 1.5e9, 3e9, 2e9, 2.5e9, 4e9, 3e9, 2e9, 1e9, 2e9, 3e9, 4e9, 5e9],
                [5e8, 1e9, 8e8, 1.5e9, 9e8, 1.2e9, 2e9, 1.8e9, 1e9, 5e8, 8e8, 1.2e9, 1.8e9, 2.5e9],
            ],
            total: 42e9,
        },
        isPending: false,
    }),
}));

vi.mock("@marzneshin/modules/audit", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@marzneshin/modules/audit")>();
    return {
        ...actual,
        useAuditEvents: () => ({
            data: {
                items: [
                    {
                        id: 1,
                        actor_id: 1,
                        actor_type: "sudo_admin",
                        actor_username: "root",
                        action: "user.create",
                        method: "POST",
                        path: "/api/users",
                        target_type: "user",
                        target_id: "42",
                        result: "success",
                        status_code: 201,
                        error_message: null,
                        ip: "127.0.0.1",
                        user_agent: null,
                        request_id: null,
                        ts: new Date(Date.now() - 300_000).toISOString(),
                    },
                    {
                        id: 2,
                        actor_id: 2,
                        actor_type: "admin",
                        actor_username: "alice",
                        action: "node.restart",
                        method: "POST",
                        path: "/api/nodes/1/restart",
                        target_type: "node",
                        target_id: "1",
                        result: "failure",
                        status_code: 500,
                        error_message: "timeout",
                        ip: "10.0.0.1",
                        user_agent: null,
                        request_id: null,
                        ts: new Date(Date.now() - 3_600_000).toISOString(),
                    },
                    {
                        id: 3,
                        actor_id: null,
                        actor_type: "anonymous",
                        actor_username: null,
                        action: "auth.login_failed",
                        method: "POST",
                        path: "/api/auth/login",
                        target_type: null,
                        target_id: null,
                        result: "denied",
                        status_code: 401,
                        error_message: null,
                        ip: "203.0.113.1",
                        user_agent: null,
                        request_id: null,
                        ts: new Date(Date.now() - 7_200_000).toISOString(),
                    },
                ],
                next_cursor: null,
                total_returned: 3,
            },
        }),
    };
});

vi.mock("@marzneshin/modules/health", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@marzneshin/modules/health")>();
    // 19 ok / 1 down = 95% — matches the test assertion
    const oks = Array.from({ length: 19 }, (_, i) => ({
        name: `sub_${i}`,
        status: "ok" as const,
        message: "",
        details: {},
    }));
    return {
        ...actual,
        useHealthExtended: () => ({
            data: {
                status: "ok",
                version: "1.0.0",
                uptime_seconds: 7200,
                subsystems: [
                    ...oks,
                    { name: "redis", status: "down" as const, message: "", details: {} },
                ],
            },
            isLoading: false,
            isError: false,
        }),
    };
});

// Mock TanStack Router Link to avoid router context requirement
vi.mock("@tanstack/react-router", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@tanstack/react-router")>();
    return {
        ...actual,
        createLazyFileRoute: () => ({ component }: { component: () => JSX.Element }) => ({ component }),
        Link: ({ children, to, style }: { children: React.ReactNode; to: string; style?: React.CSSProperties }) => (
            <a href={to} style={style}>{children}</a>
        ),
    };
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OperatorHomePage (Wave-A3 / operator home)", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders the PanelHead title", () => {
        renderWithProviders(<OperatorHomePage />);
        // PanelHead renders an h1; i18n key nilou.overview.welcome falls back to "Welcome back"
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
        expect(heading.textContent).toBeTruthy();
    });

    it("renders BigChart SVG when traffic data is available", () => {
        renderWithProviders(<OperatorHomePage />);
        // BigChart renders an <svg> element
        const svgs = document.querySelectorAll("svg");
        expect(svgs.length).toBeGreaterThan(0);
        // At least one svg should be the BigChart (has viewBox 0 0 100 100)
        const bigChart = Array.from(svgs).find(
            (svg) => svg.getAttribute("viewBox") === "0 0 100 100",
        );
        expect(bigChart).toBeTruthy();
    });

    it("renders at least one KPI with the total users count", () => {
        renderWithProviders(<OperatorHomePage />);
        // Total users KPI should display 150 (may render twice — KPI value + sub)
        expect(screen.getAllByText("150").length).toBeGreaterThan(0);
    });

    it("renders the active users KPI", () => {
        renderWithProviders(<OperatorHomePage />);
        expect(screen.getAllByText("42").length).toBeGreaterThan(0);
    });

    it("renders online nodes KPI from user stats", () => {
        renderWithProviders(<OperatorHomePage />);
        // online = 7
        expect(screen.getByText("7")).toBeInTheDocument();
    });

    it("renders audit log entries in Recent activity section", () => {
        renderWithProviders(<OperatorHomePage />);
        // user.create audit event
        expect(screen.getByText("user.create")).toBeInTheDocument();
        // node.restart
        expect(screen.getByText("node.restart")).toBeInTheDocument();
    });

    it("renders StatusDots with varied tones for audit results", () => {
        renderWithProviders(<OperatorHomePage />);
        // There should be 3 status dots (success, failure, denied tones)
        // StatusDot renders a <span> with rounded background
        // We check that there are at least 3 span elements acting as dots
        const dots = document.querySelectorAll("span[style*='border-radius: 50%']");
        expect(dots.length).toBeGreaterThanOrEqual(3);
    });

    it("renders Quick links section with navigation items", () => {
        renderWithProviders(<OperatorHomePage />);
        // Quick links render as anchor elements to /users, /nodes, /audit, /reality
        const links = document.querySelectorAll("a[href]");
        const hrefs = Array.from(links).map((a) => a.getAttribute("href"));
        expect(hrefs).toContain("/users");
        expect(hrefs).toContain("/nodes");
    });

    it("renders RingMeter capacity section", () => {
        renderWithProviders(<OperatorHomePage />);
        // RingMeter renders an SVG with two circles
        const circles = document.querySelectorAll("circle");
        expect(circles.length).toBeGreaterThanOrEqual(2);
    });

    it("renders health score KPI as 95", () => {
        renderWithProviders(<OperatorHomePage />);
        expect(screen.getByText("95")).toBeInTheDocument();
    });
});
