/**
 * Vitest tests for the /health page (Wave-A3).
 *
 * Spec acceptance criteria (per PLAN Wave-A.3 / SPEC §14 health route):
 *   1. PanelHead title rendered.
 *   2. At least 3 subsystem cards rendered.
 *   3. StatusDot tones vary across subsystem states.
 *
 * Strategy: mount HealthPage internals directly by extracting the inner
 * component. We mock useHealthExtended to return a rich fixture with
 * ok / degraded / down subsystems covering all three tone paths.
 *
 * Note: HealthPage is wrapped in SudoRoute in the Route export. We test
 * the internal HealthPage component to avoid needing an auth context.
 * SudoRoute itself is not the unit under test here.
 */

import { describe, expect, it, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { renderWithProviders } from "@marzneshin/test-utils/render";
import { HealthPage as HealthPageComponent } from "../../routes/_dashboard/health.lazy";

// ---------------------------------------------------------------------------
// Mock dependencies before importing the component
// ---------------------------------------------------------------------------

vi.mock("@marzneshin/modules/health", async (importOriginal) => {
    const actual = await importOriginal<typeof import("@marzneshin/modules/health")>();
    return {
        ...actual,
        HealthExtendedQueryKey: "aegis-health-extended",
        useHealthExtended: () => ({
            data: {
                status: "degraded",
                version: "1.2.3",
                uptime_seconds: 172800, // 2 days
                subsystems: [
                    {
                        name: "db",
                        status: "ok",
                        message: "PostgreSQL 16 responding in 2ms",
                        details: { last_check: "2026-05-07T10:00:00Z" },
                    },
                    {
                        name: "billing_scheduler",
                        status: "degraded",
                        message: "APScheduler lag > 5s on last tick",
                        details: {},
                    },
                    {
                        name: "trc20",
                        status: "down",
                        message: "USDT provider unreachable — connection timeout",
                        details: {},
                    },
                    {
                        name: "reality_seeds",
                        status: "ok",
                        message: "Seed list fresh (updated 3 h ago)",
                        details: {},
                    },
                ],
            },
            isLoading: false,
            isError: false,
        }),
    };
});

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

// SudoRoute: render children unconditionally for tests
vi.mock("@marzneshin/libs/sudo-routes", () => ({
    SudoRoute: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ---------------------------------------------------------------------------
// Component import is at the top of file (static) — vitest hoists vi.mock()
// calls above all imports, so the mocks defined here run before
// health.lazy's module-load-time effects. Previous version used a dynamic
// `await import(...)` inside `beforeEach` with a 30s timeout because of
// vitest module-cache races; static import is reliable and ~1ms.

beforeEach(() => {
    vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("HealthPage (Wave-A3 / /health route)", () => {
    it("renders the PanelHead title for system health", () => {
        renderWithProviders(<HealthPageComponent />);
        const heading = screen.getByRole("heading", { level: 1 });
        expect(heading).toBeInTheDocument();
        // Title includes the i18n key text "System health" or the key itself
        expect(heading.textContent).toBeTruthy();
    });

    it("renders at least 3 subsystem cards", () => {
        renderWithProviders(<HealthPageComponent />);
        // Each subsystem card shows the subsystem name or a StatusDot.
        // We check by known subsystem messages rendered:
        expect(screen.getByText("PostgreSQL 16 responding in 2ms")).toBeInTheDocument();
        expect(screen.getByText("APScheduler lag > 5s on last tick")).toBeInTheDocument();
        expect(screen.getByText("USDT provider unreachable — connection timeout")).toBeInTheDocument();
    });

    it("renders StatusDot with emerald tone for ok subsystem (db)", () => {
        renderWithProviders(<HealthPageComponent />);
        // emerald StatusDot has box-shadow set; we check that at least one
        // span has the emerald glow style. The db subsystem is "ok".
        const dots = document.querySelectorAll("span[style*='border-radius: 50%']");
        const emeraldDot = Array.from(dots).find((d) =>
            (d as HTMLElement).style.background?.includes("5bc0be") ||
            (d as HTMLElement).style.boxShadow?.includes("5bc0be"),
        );
        expect(emeraldDot).toBeTruthy();
    });

    it("renders StatusDot with coral/amber tones for non-ok subsystems", () => {
        renderWithProviders(<HealthPageComponent />);
        // amber (degraded) and coral (down) dots must appear
        // Browsers normalize hex colors to rgb() — match either form.
        const dots = Array.from(document.querySelectorAll("span[style*='border-radius: 50%']")) as HTMLElement[];
        const hasColor = (dot: HTMLElement, hex: string, rgb: string) => {
            const bg = dot.style.background ?? '';
            const bgColor = dot.style.backgroundColor ?? '';
            return [bg, bgColor].some((v) => v.toLowerCase().includes(hex.toLowerCase()) || v.includes(rgb));
        };
        const coralDot = dots.find((d) => hasColor(d, 'e07856', 'rgb(224, 120, 86)'));
        const amberDot = dots.find((d) => hasColor(d, 'e8b04b', 'rgb(232, 176, 75)'));
        expect(coralDot).toBeTruthy();
        expect(amberDot).toBeTruthy();
    });

    it("renders 4 KPI cards (overall score, online, degraded, last check)", () => {
        renderWithProviders(<HealthPageComponent />);
        // Score derived: 100 - 20(degraded) - 50(down) = 30
        // The KPI for "Online subsystems" shows 2 (db + reality_seeds are ok)
        expect(screen.getByText("2")).toBeInTheDocument();
        // Degraded count = 1
        expect(screen.getByText("1")).toBeInTheDocument();
    });

    it("renders down-subsystem callout banner when a subsystem is down", () => {
        renderWithProviders(<HealthPageComponent />);
        // The ⚠ callout is only shown when downCount > 0
        // Our fixture has trc20 as "down"
        const callout = screen.getByText(/subsystem.*DOWN/i);
        expect(callout).toBeInTheDocument();
    });

    it("renders the version string in a KPI sub-label", () => {
        renderWithProviders(<HealthPageComponent />);
        // health.version = "1.2.3" → KPI sub = "v1.2.3"
        expect(screen.getByText("v1.2.3")).toBeInTheDocument();
    });

    it("renders the subsystem section heading", () => {
        renderWithProviders(<HealthPageComponent />);
        // h2 for "Subsystem status"
        const h2 = screen.getByRole("heading", { level: 2 });
        expect(h2).toBeInTheDocument();
    });
});
