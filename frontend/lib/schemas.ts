import { z } from "zod";

export const loginSchema = z.object({
  contact: z.string().min(3, "Contact is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const registerSchema = loginSchema
  .extend({
    name: z.string().min(2, "Name must be at least 2 characters"),
    role: z.enum(["farmer", "mentor"]),
    language: z.enum(["en", "ml"]),
    helper_type: z.enum(["student", "volunteer", "college", "officer"]).optional(),
  })
  .refine((v) => v.role !== "mentor" || !!v.helper_type, {
    path: ["helper_type"],
    message: "Helper type is required for mentors",
  });

export const fieldSchema = z.object({
  name: z.string().min(2, "Field name must be at least 2 characters").max(60),
  lat: z.number().min(-90).max(90),
  lon: z.number().min(-180).max(180),
  water_source: z.enum(["rainfed", "borewell", "canal", "unknown"]),
  water_quality: z.enum(["good", "saline", "unknown"]),
  area_ha: z.number().positive().optional(),
});

export const seasonSchema = z
  .object({
    crop: z.string().min(1, "Crop is required"),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().min(1, "End date is required"),
    outcome: z.enum(["good", "average", "poor", "failed"]),
    loss_percent: z.number().min(0).max(100).optional(),
    suspected_cause: z.enum(["water_shortage", "excess_rain", "pests", "unsure"]).optional(),
  })
  .refine((v) => v.end_date > v.start_date, {
    path: ["end_date"],
    message: "End date must be after start date",
  });

export const planSchema = z
  .object({
    mode: z.enum(["suggest", "farmer_led"]),
    season: z.enum(["virippu", "mundakan", "puncha"]),
    toggle: z.enum(["earn_more", "play_safe"]).nullable(),
    stored_water_answer: z.enum(["dry", "moist", "wet"]).nullable(),
    crop: z.string().optional(),
    reason: z.enum(["market", "finance", "other"]).optional(),
  })
  .refine((v) => v.mode !== "farmer_led" || !!v.crop, {
    path: ["crop"],
    message: "A target crop is required in farmer-led mode",
  });

export const shareSchema = z.object({
  mentor_id: z.number(),
  share: z.array(z.enum(["field_profile", "history", "cards", "findings"])).min(1, "Select at least one section to share"),
  expires_days: z.union([z.literal(7), z.literal(14), z.literal(30)]),
});
