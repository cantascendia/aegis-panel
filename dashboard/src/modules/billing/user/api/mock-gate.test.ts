/**
 * Unit tests for mock-gate decision logic.
 *
 * shouldUseMock() combines a Vite env flag + a URL `?mock=1` override.
 * These are the two knobs reviewers and CI actually manipulate; the
 * logic is small enough that a bug here (e.g. env=on being ignored)
 * would silently render fixtures in production. So we nail it down.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mockResolve, shouldUseMock } from "./mock-gate";

// Capture original so we can restore after tampering.
const originalEnv = { ...import.meta.env };

function setEnv(flag: unknown) {
    (import.meta.env as Record<string, unknown>).VITE_BILLING_USER_UI = flag;
}

function setUrl(search: string) {
    // vitest default `jsdom` gives us window.location; navigate by
    // history.replaceState so we don't reload.
    window.history.replaceState({}, "", `/test${search}`);
}

beforeEach(() => {
    setUrl("");
    setEnv(undefined);
});

afterEach(() => {
    setEnv(originalEnv.VITE_BILLING_USER_UI);
    setUrl("");
});

describe("shouldUseMock", () => {
    it("returns true when env flag is missing (mock mode default)", () => {
        expect(shouldUseMock()).toBe(true);
    });

    it("returns false when env flag is 'on'", () => {
        setEnv("on");
        expect(shouldUseMock()).toBe(false);
    });

    it.each(["true", "1"])(
        "treats '%s' as enabled (live API)",
        (value) => {
            setEnv(value);
            expect(shouldUseMock()).toBe(false);
        },
    );

    it("treats 'off' / 'false' / empty as mock mode", () => {
        setEnv("off");
        expect(shouldUseMock()).toBe(true);
        setEnv("false");
        expect(shouldUseMock()).toBe(true);
        setEnv("");
        expect(shouldUseMock()).toBe(true);
    });

    it("URL ?mock=1 forces mock mode even when env is 'on'", () => {
        // Reviewer-preview override: env says live but URL insists
        // on fixtures. This is the "reviewer previews a PR running
        // against staging" use case.
        setEnv("on");
        setUrl("?mock=1");
        expect(shouldUseMock()).toBe(true);
    });

    it("URL ?mock=0 does NOT toggle live mode when env is 'off'", () => {
        // Deliberate asymmetry: URL override only flips TO mock, not
        // FROM mock. Production (env=on) can be temporarily mocked
        // for a preview; staging/dev (env=off) can't accidentally go
        // live from a URL trick.
        setEnv(undefined);
        setUrl("?mock=0");
        expect(shouldUseMock()).toBe(true);
    });
});

describe("mockResolve", () => {
    it("resolves the provided value after the delay", async () => {
        vi.useFakeTimers();
        const promise = mockResolve({ hello: "world" }, 100);

        // Advance time so the inner setTimeout fires; otherwise the
        // await below never resolves inside fake-timer mode.
        await vi.advanceTimersByTimeAsync(100);

        await expect(promise).resolves.toEqual({ hello: "world" });
        vi.useRealTimers();
    });
});
