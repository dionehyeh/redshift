# Field Shift Database & Storage Architecture

The application uses Neon-hosted PostgreSQL for relational data and local Parquet files for climatological cache data. The canonical PostgreSQL DDL is [backend/data/schema.sql](../backend/data/schema.sql).

---

## 1. Neon PostgreSQL

`DATABASE_URL` must be a PostgreSQL connection string copied from Neon, preferably the pooled connection string, with TLS enabled (`sslmode=require`). The backend uses `psycopg2` and manages each `with get_db()` block as one transaction. Placeholder parameters are converted to PostgreSQL's `%s` format by the connection adapter; generated integer IDs use `RETURNING id`.

The schema is initialized at FastAPI startup and is safe to run repeatedly. It defines:

| Tables | Purpose |
|---|---|
| `users`, `farmer_prefs` | Local application profile and preferences. `users.clerk_user_id` links a profile to a Clerk identity. |
| `fields`, `field_crops`, `climate_cells` | Farmer field records, calculated crop feasibility, and references to climate cache cells. |
| `crops` | Master agronomic crop catalog, seeded from `backend/data/crops.csv`. |
| `seasons`, `findings`, `corrections` | Historical seasons, analysis results, and reviewed corrections. |
| `plans`, `plan_cards` | Generated crop-rotation plans and their strategy cards. |
| `reports`, `report_comments` | Consent-scoped mentor snapshots and advisory comments. |
| `jobs`, `audit_log` | Background job status and security/consultation events. |

`users.role` is an application authorization role. New Clerk profiles default to `farmer`; elevated roles must be set in trusted Clerk `public_metadata` before the account is provisioned. User-editable metadata is never used to grant a role. Password hashes are no longer used for login; the nullable legacy `password_hash` column exists only so an existing PostgreSQL schema can be upgraded without destructive removal.

### Setup

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `DATABASE_URL` to the Neon connection string, and set `CLERK_SECRET_KEY`, `CLERK_ISSUER`, and `CLERK_JWKS_URL`.
3. Run `python scripts/seed_demo.py` from `backend/` to initialize the schema and seed the crop catalog.
4. Start the API. Startup also initializes the schema.

This switches the app from SQLite to Neon; it does **not** copy existing local SQLite records into Neon. Existing local user accounts also need Clerk identity linking/provisioning before they can use the new authentication flow.

---

## 2. File-Based Climatological Cache

- 20-year weekly harmonized weather series and 52-week normal aggregations are stored as Parquet.
- Cache files are located under `backend/data/cache/{cell_id}_weekly.parquet`.
- The relational database stores metadata and references; large series remain outside PostgreSQL.

---

## 3. Operational Guarantees

- Foreign-key constraints and transaction rollback are enforced by PostgreSQL.
- Schema statements are idempotent and can run on every startup.
- Crop seeding is idempotent (`ON CONFLICT` updates catalog rows).
- Never place Neon credentials or Clerk secret keys in source control; the real `.env` files are ignored by Git.
