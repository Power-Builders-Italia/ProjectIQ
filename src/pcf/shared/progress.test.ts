import { progressLabel, progressPercent } from "./progress";

test("value is clamped to 0-100 and empty stays empty", () => {
    expect(progressPercent(33.36)).toBe(33.36);
    expect(progressPercent("48.77")).toBe(48.77);
    expect(progressPercent(-5)).toBe(0);
    expect(progressPercent(140)).toBe(100);
    expect(progressPercent(null)).toBeNull();
    expect(progressPercent(undefined)).toBeNull();
    expect(progressPercent("abc")).toBeNull();
});

test("label is the whole percent", () => {
    expect(progressLabel(33.36)).toBe("33%");
    expect(progressLabel(76.86)).toBe("77%");
    expect(progressLabel(0)).toBe("0%");
});
