-- =============================================================================
-- Row Level Security (RLS) Policies — Facilitador Docente
-- =============================================================================
-- Apply via Supabase SQL editor or `supabase db push`.
-- Each table gets:
--   1. ALTER TABLE ... ENABLE ROW LEVEL SECURITY
--   2. One or more CREATE POLICY statements
--
-- JWT claim helper:
--   auth.uid()  → Supabase user UUID (maps to clerk_user_id via sync)
--   auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
--       → UUID of the institution this user belongs to (set by Clerk webhook sync)
--   auth.jwt() -> 'public_metadata' ->> 'role'
--       → 'institution_admin' | 'teacher' | etc.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- institution_tenants
-- ---------------------------------------------------------------------------
ALTER TABLE institution_tenants ENABLE ROW LEVEL SECURITY;

-- Users can only see their own tenant row
CREATE POLICY "institution_tenants: select own tenant"
  ON institution_tenants
  FOR SELECT
  USING (
    id = (auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id')::uuid
  );

-- Only institution_admin can update their own tenant
CREATE POLICY "institution_tenants: update own tenant (admin only)"
  ON institution_tenants
  FOR UPDATE
  USING (
    id = (auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id')::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  )
  WITH CHECK (
    id = (auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id')::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  );


-- ---------------------------------------------------------------------------
-- licenses
-- ---------------------------------------------------------------------------
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "licenses: select own tenant"
  ON licenses
  FOR SELECT
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

CREATE POLICY "licenses: insert own tenant (admin only)"
  ON licenses
  FOR INSERT
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  );

CREATE POLICY "licenses: update own tenant (admin only)"
  ON licenses
  FOR UPDATE
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  )
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );


-- ---------------------------------------------------------------------------
-- institution_tenant_units
-- ---------------------------------------------------------------------------
ALTER TABLE institution_tenant_units ENABLE ROW LEVEL SECURITY;

CREATE POLICY "institution_tenant_units: select own tenant"
  ON institution_tenant_units
  FOR SELECT
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

CREATE POLICY "institution_tenant_units: insert own tenant (admin only)"
  ON institution_tenant_units
  FOR INSERT
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  );

CREATE POLICY "institution_tenant_units: update own tenant (admin only)"
  ON institution_tenant_units
  FOR UPDATE
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  )
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );


-- ---------------------------------------------------------------------------
-- institution_members
-- ---------------------------------------------------------------------------
ALTER TABLE institution_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "institution_members: select own tenant"
  ON institution_members
  FOR SELECT
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

CREATE POLICY "institution_members: insert own tenant (admin only)"
  ON institution_members
  FOR INSERT
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  );

CREATE POLICY "institution_members: update own tenant (admin only)"
  ON institution_members
  FOR UPDATE
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  )
  WITH CHECK (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

CREATE POLICY "institution_members: delete own tenant (admin only)"
  ON institution_members
  FOR DELETE
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
    AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
  );


-- ---------------------------------------------------------------------------
-- institution_billing_cycles
-- ---------------------------------------------------------------------------
ALTER TABLE institution_billing_cycles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "institution_billing_cycles: select own tenant"
  ON institution_billing_cycles
  FOR SELECT
  USING (
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

-- Billing cycles are created/updated by the backend service role only.
-- Regular users cannot INSERT or UPDATE billing cycles directly.


-- ---------------------------------------------------------------------------
-- educational_centers
-- ---------------------------------------------------------------------------
ALTER TABLE educational_centers ENABLE ROW LEVEL SECURITY;

-- Teachers can only see their own educational centers
CREATE POLICY "educational_centers: select own"
  ON educational_centers
  FOR SELECT
  USING (user_id = auth.uid()::text);

CREATE POLICY "educational_centers: insert own"
  ON educational_centers
  FOR INSERT
  WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "educational_centers: update own"
  ON educational_centers
  FOR UPDATE
  USING (user_id = auth.uid()::text)
  WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "educational_centers: delete own"
  ON educational_centers
  FOR DELETE
  USING (user_id = auth.uid()::text);


-- ---------------------------------------------------------------------------
-- students
-- ---------------------------------------------------------------------------
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

-- A teacher can see students that belong to their educational centers.
-- An institution admin can see students of any center in their tenant.
CREATE POLICY "students: select — owner or same tenant"
  ON students
  FOR SELECT
  USING (
    -- Direct ownership via educational_center
    educational_center_id IN (
      SELECT id FROM educational_centers
      WHERE user_id = auth.uid()::text
    )
    OR
    -- Institution admin sees all students within their tenant
    institution_tenant_id = (
      auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
    )::uuid
  );

CREATE POLICY "students: insert — own center or own tenant (admin)"
  ON students
  FOR INSERT
  WITH CHECK (
    educational_center_id IN (
      SELECT id FROM educational_centers
      WHERE user_id = auth.uid()::text
    )
    OR (
      institution_tenant_id = (
        auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
      )::uuid
      AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
    )
  );

CREATE POLICY "students: update — own center or own tenant (admin)"
  ON students
  FOR UPDATE
  USING (
    educational_center_id IN (
      SELECT id FROM educational_centers
      WHERE user_id = auth.uid()::text
    )
    OR (
      institution_tenant_id = (
        auth.jwt() -> 'public_metadata' ->> 'institution_tenant_id'
      )::uuid
      AND (auth.jwt() -> 'public_metadata' ->> 'role') = 'institution_admin'
    )
  );

CREATE POLICY "students: delete — own center only"
  ON students
  FOR DELETE
  USING (
    educational_center_id IN (
      SELECT id FROM educational_centers
      WHERE user_id = auth.uid()::text
    )
  );


-- ---------------------------------------------------------------------------
-- planificaciones
-- ---------------------------------------------------------------------------
ALTER TABLE planificaciones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "planificaciones: select own"
  ON planificaciones
  FOR SELECT
  USING (user_id = auth.uid()::text);

CREATE POLICY "planificaciones: insert own"
  ON planificaciones
  FOR INSERT
  WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "planificaciones: update own"
  ON planificaciones
  FOR UPDATE
  USING (user_id = auth.uid()::text)
  WITH CHECK (user_id = auth.uid()::text);

CREATE POLICY "planificaciones: delete own"
  ON planificaciones
  FOR DELETE
  USING (user_id = auth.uid()::text);


-- ---------------------------------------------------------------------------
-- individual_subscriptions
-- ---------------------------------------------------------------------------
ALTER TABLE individual_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "individual_subscriptions: select own"
  ON individual_subscriptions
  FOR SELECT
  USING (user_id = auth.uid()::text);

-- Subscriptions are created/updated by backend (service role) via MP webhook.
-- Users cannot INSERT or UPDATE their own subscription rows directly.


-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- Run the following queries as the respective tenant/user JWT to verify
-- isolation is enforced. Expected result for each: 0 rows.
--
-- How to test in Supabase SQL Editor:
--   1. Open SQL Editor
--   2. Set the role with: SET LOCAL role TO authenticated;
--   3. Set the JWT claims with:
--        SET LOCAL request.jwt.claims TO '{"sub":"<uid>","public_metadata":{"institution_tenant_id":"<tid>","role":"teacher"}}';
--   4. Run the query — it must return 0 rows if RLS is working.
-- =============================================================================

-- ── Verification 1: Tenant A cannot see Tenant B's institution row ─────────
--
-- Replace <TENANT_A_ID> and <TENANT_B_ID> with real UUIDs.
-- Run this as a user whose JWT has institution_tenant_id = <TENANT_A_ID>.
-- Should return 0 rows.
--
-- SELECT id, name
-- FROM institution_tenants
-- WHERE id = '<TENANT_B_ID>';
--
-- Expected: 0 rows (RLS filters it out because id != jwt claim).


-- ── Verification 2: Tenant A cannot see Tenant B's licenses ───────────────
--
-- Run as a user belonging to <TENANT_A_ID>.
-- Should return 0 rows for <TENANT_B_ID>'s licenses.
--
-- SELECT id, status
-- FROM licenses
-- WHERE institution_tenant_id = '<TENANT_B_ID>';
--
-- Expected: 0 rows.


-- ── Verification 3: Teacher A cannot see Teacher B's educational centers ───
--
-- Run as teacher A (auth.uid() = <TEACHER_A_UID>).
-- Should return 0 rows.
--
-- SELECT id, name
-- FROM educational_centers
-- WHERE user_id = '<TEACHER_B_UID>';
--
-- Expected: 0 rows (user_id != auth.uid()).


-- ── Verification 4: Teacher A cannot see Teacher B's planificaciones ───────
--
-- Run as teacher A.
-- Should return 0 rows.
--
-- SELECT id
-- FROM planificaciones
-- WHERE user_id = '<TEACHER_B_UID>';
--
-- Expected: 0 rows.


-- ── Verification 5: User A cannot see User B's subscriptions ──────────────
--
-- Run as user A.
-- Should return 0 rows.
--
-- SELECT id, status
-- FROM individual_subscriptions
-- WHERE user_id = '<USER_B_UID>';
--
-- Expected: 0 rows.


-- ── Verification 6: Tenant A cannot see Tenant B's billing cycles ─────────
--
-- Run as a user belonging to <TENANT_A_ID>.
-- Should return 0 rows.
--
-- SELECT id, status, total_amount_usd
-- FROM institution_billing_cycles
-- WHERE institution_tenant_id = '<TENANT_B_ID>';
--
-- Expected: 0 rows.


-- ── Verification 7: Teacher cannot see members of a different tenant ───────
--
-- Run as a user whose JWT has institution_tenant_id = <TENANT_A_ID>.
-- Should return 0 rows for <TENANT_B_ID>.
--
-- SELECT id, user_id, role
-- FROM institution_members
-- WHERE institution_tenant_id = '<TENANT_B_ID>';
--
-- Expected: 0 rows.
