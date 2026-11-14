import { describe, it, expect } from "vitest";
import { loginSchema, fieldSchema, seasonSchema } from "../lib/schemas";

describe("Frontend Zod Schemas", () => {
  it("validates login credentials correctly", () => {
    const valid = loginSchema.safeParse({ contact: "farmer@demo.org", password: "password123" });
    expect(valid.success).toBe(true);

    const invalid = loginSchema.safeParse({ contact: "", password: "123" });
    expect(invalid.success).toBe(false);
  });

  it("validates field creation bounds", () => {
    const valid = fieldSchema.safeParse({
      name: "North Paddy",
      lat: 9.50,
      lon: 76.40,
      water_source: "rainfed",
      water_quality: "unknown",
    });
    expect(valid.success).toBe(true);

    const invalidLat = fieldSchema.safeParse({
      name: "Plot",
      lat: 95.0, // Out of bounds
      lon: 76.40,
      water_source: "rainfed",
      water_quality: "unknown",
    });
    expect(invalidLat.success).toBe(false);
  });

  it("enforces season end date after start date", () => {
    const invalidDates = seasonSchema.safeParse({
      crop: "paddy",
      start_date: "2026-01-15",
      end_date: "2025-09-20", // Before start date
      outcome: "poor",
    });
    expect(invalidDates.success).toBe(false);
  });
});
