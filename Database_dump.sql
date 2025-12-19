DROP TABLE IF EXISTS "auth"."oauth_client_states";
-- Table Definition
CREATE TABLE "auth"."oauth_client_states" (
    "id" uuid NOT NULL,
    "provider_type" text NOT NULL,
    "code_verifier" text,
    "created_at" timestamptz NOT NULL,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."oauth_client_states" IS 'Stores OAuth states for third-party provider authentication flows where Supabase acts as the OAuth client.';


-- Indices
CREATE INDEX idx_oauth_client_states_created_at ON auth.oauth_client_states USING btree (created_at);

DROP TABLE IF EXISTS "auth"."sso_domains";
-- Table Definition
CREATE TABLE "auth"."sso_domains" (
    "id" uuid NOT NULL,
    "sso_provider_id" uuid NOT NULL,
    "domain" text NOT NULL,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    CONSTRAINT "sso_domains_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."sso_domains" IS 'Auth: Manages SSO email address domain mapping to an SSO Identity Provider.';


-- Indices
CREATE INDEX sso_domains_sso_provider_id_idx ON auth.sso_domains USING btree (sso_provider_id);
CREATE UNIQUE INDEX sso_domains_domain_idx ON auth.sso_domains USING btree (lower(domain));

DROP TABLE IF EXISTS "auth"."mfa_amr_claims";
-- Table Definition
CREATE TABLE "auth"."mfa_amr_claims" (
    "session_id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "authentication_method" text NOT NULL,
    "id" uuid NOT NULL,
    CONSTRAINT "mfa_amr_claims_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "auth"."sessions"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."mfa_amr_claims" IS 'auth: stores authenticator method reference claims for multi factor authentication';


-- Indices
CREATE UNIQUE INDEX mfa_amr_claims_session_id_authentication_method_pkey ON auth.mfa_amr_claims USING btree (session_id, authentication_method);
CREATE UNIQUE INDEX amr_id_pk ON auth.mfa_amr_claims USING btree (id);

DROP TABLE IF EXISTS "auth"."saml_providers";
-- Table Definition
CREATE TABLE "auth"."saml_providers" (
    "id" uuid NOT NULL,
    "sso_provider_id" uuid NOT NULL,
    "entity_id" text NOT NULL,
    "metadata_xml" text NOT NULL,
    "metadata_url" text,
    "attribute_mapping" jsonb,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "name_id_format" text,
    CONSTRAINT "saml_providers_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."saml_providers" IS 'Auth: Manages SAML Identity Provider connections.';


-- Indices
CREATE UNIQUE INDEX saml_providers_entity_id_key ON auth.saml_providers USING btree (entity_id);
CREATE INDEX saml_providers_sso_provider_id_idx ON auth.saml_providers USING btree (sso_provider_id);

DROP TABLE IF EXISTS "auth"."sso_providers";
-- Table Definition
CREATE TABLE "auth"."sso_providers" (
    "id" uuid NOT NULL,
    "resource_id" text,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "disabled" bool,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "auth"."sso_providers"."resource_id" IS 'Auth: Uniquely identifies a SSO provider according to a user-chosen resource ID (case insensitive), useful in infrastructure as code.';


-- Comments
COMMENT ON TABLE "auth"."sso_providers" IS 'Auth: Manages SSO identity provider information; see saml_providers for SAML.';


-- Indices
CREATE UNIQUE INDEX sso_providers_resource_id_idx ON auth.sso_providers USING btree (lower(resource_id));
CREATE INDEX sso_providers_resource_id_pattern_idx ON auth.sso_providers USING btree (resource_id text_pattern_ops);

DROP TABLE IF EXISTS "auth"."instances";
-- Table Definition
CREATE TABLE "auth"."instances" (
    "id" uuid NOT NULL,
    "uuid" uuid,
    "raw_base_config" text,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."instances" IS 'Auth: Manages users across multiple sites.';

DROP TABLE IF EXISTS "auth"."schema_migrations";
-- Table Definition
CREATE TABLE "auth"."schema_migrations" (
    "version" varchar(255) NOT NULL
);


-- Comments
COMMENT ON TABLE "auth"."schema_migrations" IS 'Auth: Manages updates to the auth system.';

DROP TABLE IF EXISTS "auth"."users";
-- Table Definition
CREATE TABLE "auth"."users" (
    "instance_id" uuid,
    "id" uuid NOT NULL,
    "aud" varchar(255),
    "role" varchar(255),
    "email" varchar(255),
    "encrypted_password" varchar(255),
    "email_confirmed_at" timestamptz,
    "invited_at" timestamptz,
    "confirmation_token" varchar(255),
    "confirmation_sent_at" timestamptz,
    "recovery_token" varchar(255),
    "recovery_sent_at" timestamptz,
    "email_change_token_new" varchar(255),
    "email_change" varchar(255),
    "email_change_sent_at" timestamptz,
    "last_sign_in_at" timestamptz,
    "raw_app_meta_data" jsonb,
    "raw_user_meta_data" jsonb,
    "is_super_admin" bool,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "phone" text DEFAULT NULL::character varying,
    "phone_confirmed_at" timestamptz,
    "phone_change" text DEFAULT ''::character varying,
    "phone_change_token" varchar(255) DEFAULT ''::character varying,
    "phone_change_sent_at" timestamptz,
    "confirmed_at" timestamptz,
    "email_change_token_current" varchar(255) DEFAULT ''::character varying,
    "email_change_confirm_status" int2 DEFAULT 0,
    "banned_until" timestamptz,
    "reauthentication_token" varchar(255) DEFAULT ''::character varying,
    "reauthentication_sent_at" timestamptz,
    "is_sso_user" bool NOT NULL DEFAULT false,
    "deleted_at" timestamptz,
    "is_anonymous" bool NOT NULL DEFAULT false,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "auth"."users"."is_sso_user" IS 'Auth: Set this column to true when the account comes from SSO. These accounts can have duplicate emails.';


-- Comments
COMMENT ON TABLE "auth"."users" IS 'Auth: Stores user login data within a secure schema.';


-- Indices
CREATE INDEX users_instance_id_idx ON auth.users USING btree (instance_id);
CREATE INDEX users_instance_id_email_idx ON auth.users USING btree (instance_id, lower((email)::text));
CREATE UNIQUE INDEX confirmation_token_idx ON auth.users USING btree (confirmation_token) WHERE ((confirmation_token)::text !~ '^[0-9 ]*$'::text);
CREATE UNIQUE INDEX recovery_token_idx ON auth.users USING btree (recovery_token) WHERE ((recovery_token)::text !~ '^[0-9 ]*$'::text);
CREATE UNIQUE INDEX email_change_token_current_idx ON auth.users USING btree (email_change_token_current) WHERE ((email_change_token_current)::text !~ '^[0-9 ]*$'::text);
CREATE UNIQUE INDEX email_change_token_new_idx ON auth.users USING btree (email_change_token_new) WHERE ((email_change_token_new)::text !~ '^[0-9 ]*$'::text);
CREATE UNIQUE INDEX reauthentication_token_idx ON auth.users USING btree (reauthentication_token) WHERE ((reauthentication_token)::text !~ '^[0-9 ]*$'::text);
CREATE UNIQUE INDEX users_email_partial_key ON auth.users USING btree (email) WHERE (is_sso_user = false);
CREATE UNIQUE INDEX users_phone_key ON auth.users USING btree (phone);
CREATE INDEX users_is_anonymous_idx ON auth.users USING btree (is_anonymous);

DROP TABLE IF EXISTS "auth"."audit_log_entries";
-- Table Definition
CREATE TABLE "auth"."audit_log_entries" (
    "instance_id" uuid,
    "id" uuid NOT NULL,
    "payload" json,
    "created_at" timestamptz,
    "ip_address" varchar(64) NOT NULL DEFAULT ''::character varying,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."audit_log_entries" IS 'Auth: Audit trail for user actions.';


-- Indices
CREATE INDEX audit_logs_instance_id_idx ON auth.audit_log_entries USING btree (instance_id);

DROP TABLE IF EXISTS "auth"."saml_relay_states";
-- Table Definition
CREATE TABLE "auth"."saml_relay_states" (
    "id" uuid NOT NULL,
    "sso_provider_id" uuid NOT NULL,
    "request_id" text NOT NULL,
    "for_email" text,
    "redirect_to" text,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "flow_state_id" uuid,
    CONSTRAINT "saml_relay_states_flow_state_id_fkey" FOREIGN KEY ("flow_state_id") REFERENCES "auth"."flow_state"("id") ON DELETE CASCADE,
    CONSTRAINT "saml_relay_states_sso_provider_id_fkey" FOREIGN KEY ("sso_provider_id") REFERENCES "auth"."sso_providers"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."saml_relay_states" IS 'Auth: Contains SAML Relay State information for each Service Provider initiated login.';


-- Indices
CREATE INDEX saml_relay_states_sso_provider_id_idx ON auth.saml_relay_states USING btree (sso_provider_id);
CREATE INDEX saml_relay_states_for_email_idx ON auth.saml_relay_states USING btree (for_email);
CREATE INDEX saml_relay_states_created_at_idx ON auth.saml_relay_states USING btree (created_at DESC);

DROP TABLE IF EXISTS "auth"."refresh_tokens";
-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS auth.refresh_tokens_id_seq;

-- Table Definition
CREATE TABLE "auth"."refresh_tokens" (
    "instance_id" uuid,
    "id" int8 NOT NULL DEFAULT nextval('auth.refresh_tokens_id_seq'::regclass),
    "token" varchar(255),
    "user_id" varchar(255),
    "revoked" bool,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "parent" varchar(255),
    "session_id" uuid,
    CONSTRAINT "refresh_tokens_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "auth"."sessions"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."refresh_tokens" IS 'Auth: Store of tokens used to refresh JWT tokens once they expire.';


-- Indices
CREATE INDEX refresh_tokens_instance_id_idx ON auth.refresh_tokens USING btree (instance_id);
CREATE INDEX refresh_tokens_instance_id_user_id_idx ON auth.refresh_tokens USING btree (instance_id, user_id);
CREATE UNIQUE INDEX refresh_tokens_token_unique ON auth.refresh_tokens USING btree (token);
CREATE INDEX refresh_tokens_parent_idx ON auth.refresh_tokens USING btree (parent);
CREATE INDEX refresh_tokens_session_id_revoked_idx ON auth.refresh_tokens USING btree (session_id, revoked);
CREATE INDEX refresh_tokens_updated_at_idx ON auth.refresh_tokens USING btree (updated_at DESC);

DROP TABLE IF EXISTS "auth"."flow_state";
DROP TYPE IF EXISTS "auth"."code_challenge_method";
CREATE TYPE "auth"."code_challenge_method" AS ENUM ('s256', 'plain');

-- Table Definition
CREATE TABLE "auth"."flow_state" (
    "id" uuid NOT NULL,
    "user_id" uuid,
    "auth_code" text NOT NULL,
    "code_challenge_method" "auth"."code_challenge_method" NOT NULL,
    "code_challenge" text NOT NULL,
    "provider_type" text NOT NULL,
    "provider_access_token" text,
    "provider_refresh_token" text,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "authentication_method" text NOT NULL,
    "auth_code_issued_at" timestamptz,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."flow_state" IS 'stores metadata for pkce logins';


-- Indices
CREATE INDEX idx_auth_code ON auth.flow_state USING btree (auth_code);
CREATE INDEX idx_user_id_auth_method ON auth.flow_state USING btree (user_id, authentication_method);
CREATE INDEX flow_state_created_at_idx ON auth.flow_state USING btree (created_at DESC);

DROP TABLE IF EXISTS "auth"."identities";
-- Table Definition
CREATE TABLE "auth"."identities" (
    "provider_id" text NOT NULL,
    "user_id" uuid NOT NULL,
    "identity_data" jsonb NOT NULL,
    "provider" text NOT NULL,
    "last_sign_in_at" timestamptz,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "email" text,
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    CONSTRAINT "identities_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "auth"."identities"."email" IS 'Auth: Email is a generated column that references the optional email property in the identity_data';


-- Comments
COMMENT ON TABLE "auth"."identities" IS 'Auth: Stores identities associated to a user.';


-- Indices
CREATE INDEX identities_user_id_idx ON auth.identities USING btree (user_id);
CREATE INDEX identities_email_idx ON auth.identities USING btree (email text_pattern_ops);
CREATE UNIQUE INDEX identities_provider_id_provider_unique ON auth.identities USING btree (provider_id, provider);

DROP TABLE IF EXISTS "auth"."one_time_tokens";
DROP TYPE IF EXISTS "auth"."one_time_token_type";
CREATE TYPE "auth"."one_time_token_type" AS ENUM ('confirmation_token', 'reauthentication_token', 'recovery_token', 'email_change_token_new', 'email_change_token_current', 'phone_change_token');

-- Table Definition
CREATE TABLE "auth"."one_time_tokens" (
    "id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    "token_type" "auth"."one_time_token_type" NOT NULL,
    "token_hash" text NOT NULL,
    "relates_to" text NOT NULL,
    "created_at" timestamp NOT NULL DEFAULT now(),
    "updated_at" timestamp NOT NULL DEFAULT now(),
    CONSTRAINT "one_time_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Indices
CREATE INDEX one_time_tokens_token_hash_hash_idx ON auth.one_time_tokens USING hash (token_hash);
CREATE INDEX one_time_tokens_relates_to_hash_idx ON auth.one_time_tokens USING hash (relates_to);
CREATE UNIQUE INDEX one_time_tokens_user_id_token_type_key ON auth.one_time_tokens USING btree (user_id, token_type);

DROP TABLE IF EXISTS "auth"."oauth_authorizations";
DROP TYPE IF EXISTS "auth"."code_challenge_method";
CREATE TYPE "auth"."code_challenge_method" AS ENUM ('s256', 'plain');
DROP TYPE IF EXISTS "auth"."oauth_response_type";
CREATE TYPE "auth"."oauth_response_type" AS ENUM ('code');
DROP TYPE IF EXISTS "auth"."oauth_authorization_status";
CREATE TYPE "auth"."oauth_authorization_status" AS ENUM ('pending', 'approved', 'denied', 'expired');

-- Table Definition
CREATE TABLE "auth"."oauth_authorizations" (
    "id" uuid NOT NULL,
    "authorization_id" text NOT NULL,
    "client_id" uuid NOT NULL,
    "user_id" uuid,
    "redirect_uri" text NOT NULL,
    "scope" text NOT NULL,
    "state" text,
    "resource" text,
    "code_challenge" text,
    "code_challenge_method" "auth"."code_challenge_method",
    "response_type" "auth"."oauth_response_type" NOT NULL DEFAULT 'code'::auth.oauth_response_type,
    "status" "auth"."oauth_authorization_status" NOT NULL DEFAULT 'pending'::auth.oauth_authorization_status,
    "authorization_code" text,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "expires_at" timestamptz NOT NULL DEFAULT (now() + '00:03:00'::interval),
    "approved_at" timestamptz,
    "nonce" text,
    CONSTRAINT "oauth_authorizations_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE,
    CONSTRAINT "oauth_authorizations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Indices
CREATE UNIQUE INDEX oauth_authorizations_authorization_id_key ON auth.oauth_authorizations USING btree (authorization_id);
CREATE UNIQUE INDEX oauth_authorizations_authorization_code_key ON auth.oauth_authorizations USING btree (authorization_code);
CREATE INDEX oauth_auth_pending_exp_idx ON auth.oauth_authorizations USING btree (expires_at) WHERE (status = 'pending'::auth.oauth_authorization_status);

DROP TABLE IF EXISTS "auth"."mfa_challenges";
-- Table Definition
CREATE TABLE "auth"."mfa_challenges" (
    "id" uuid NOT NULL,
    "factor_id" uuid NOT NULL,
    "created_at" timestamptz NOT NULL,
    "verified_at" timestamptz,
    "ip_address" inet NOT NULL,
    "otp_code" text,
    "web_authn_session_data" jsonb,
    CONSTRAINT "mfa_challenges_auth_factor_id_fkey" FOREIGN KEY ("factor_id") REFERENCES "auth"."mfa_factors"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "auth"."mfa_challenges" IS 'auth: stores metadata about challenge requests made';


-- Indices
CREATE INDEX mfa_challenge_created_at_idx ON auth.mfa_challenges USING btree (created_at DESC);

DROP TABLE IF EXISTS "auth"."mfa_factors";
DROP TYPE IF EXISTS "auth"."factor_type";
CREATE TYPE "auth"."factor_type" AS ENUM ('totp', 'webauthn', 'phone');
DROP TYPE IF EXISTS "auth"."factor_status";
CREATE TYPE "auth"."factor_status" AS ENUM ('unverified', 'verified');

-- Table Definition
CREATE TABLE "auth"."mfa_factors" (
    "id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    "friendly_name" text,
    "factor_type" "auth"."factor_type" NOT NULL,
    "status" "auth"."factor_status" NOT NULL,
    "created_at" timestamptz NOT NULL,
    "updated_at" timestamptz NOT NULL,
    "secret" text,
    "phone" text,
    "last_challenged_at" timestamptz,
    "web_authn_credential" jsonb,
    "web_authn_aaguid" uuid,
    "last_webauthn_challenge_data" jsonb,
    CONSTRAINT "mfa_factors_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "auth"."mfa_factors"."last_webauthn_challenge_data" IS 'Stores the latest WebAuthn challenge data including attestation/assertion for customer verification';


-- Comments
COMMENT ON TABLE "auth"."mfa_factors" IS 'auth: stores metadata about factors';


-- Indices
CREATE UNIQUE INDEX mfa_factors_user_friendly_name_unique ON auth.mfa_factors USING btree (friendly_name, user_id) WHERE (TRIM(BOTH FROM friendly_name) <> ''::text);
CREATE INDEX factor_id_created_at_idx ON auth.mfa_factors USING btree (user_id, created_at);
CREATE INDEX mfa_factors_user_id_idx ON auth.mfa_factors USING btree (user_id);
CREATE UNIQUE INDEX unique_phone_factor_per_user ON auth.mfa_factors USING btree (user_id, phone);
CREATE UNIQUE INDEX mfa_factors_last_challenged_at_key ON auth.mfa_factors USING btree (last_challenged_at);

DROP TABLE IF EXISTS "auth"."oauth_consents";
-- Table Definition
CREATE TABLE "auth"."oauth_consents" (
    "id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    "client_id" uuid NOT NULL,
    "scopes" text NOT NULL,
    "granted_at" timestamptz NOT NULL DEFAULT now(),
    "revoked_at" timestamptz,
    CONSTRAINT "oauth_consents_client_id_fkey" FOREIGN KEY ("client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE,
    CONSTRAINT "oauth_consents_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);


-- Indices
CREATE UNIQUE INDEX oauth_consents_user_client_unique ON auth.oauth_consents USING btree (user_id, client_id);
CREATE INDEX oauth_consents_active_user_client_idx ON auth.oauth_consents USING btree (user_id, client_id) WHERE (revoked_at IS NULL);
CREATE INDEX oauth_consents_user_order_idx ON auth.oauth_consents USING btree (user_id, granted_at DESC);
CREATE INDEX oauth_consents_active_client_idx ON auth.oauth_consents USING btree (client_id) WHERE (revoked_at IS NULL);

DROP TABLE IF EXISTS "auth"."oauth_clients";
DROP TYPE IF EXISTS "auth"."oauth_registration_type";
CREATE TYPE "auth"."oauth_registration_type" AS ENUM ('dynamic', 'manual');
DROP TYPE IF EXISTS "auth"."oauth_client_type";
CREATE TYPE "auth"."oauth_client_type" AS ENUM ('public', 'confidential');

-- Table Definition
CREATE TABLE "auth"."oauth_clients" (
    "id" uuid NOT NULL,
    "client_secret_hash" text,
    "registration_type" "auth"."oauth_registration_type" NOT NULL,
    "redirect_uris" text NOT NULL,
    "grant_types" text NOT NULL,
    "client_name" text,
    "client_uri" text,
    "logo_uri" text,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now(),
    "deleted_at" timestamptz,
    "client_type" "auth"."oauth_client_type" NOT NULL DEFAULT 'confidential'::auth.oauth_client_type,
    PRIMARY KEY ("id")
);


-- Indices
CREATE INDEX oauth_clients_deleted_at_idx ON auth.oauth_clients USING btree (deleted_at);

DROP TABLE IF EXISTS "auth"."sessions";
DROP TYPE IF EXISTS "auth"."aal_level";
CREATE TYPE "auth"."aal_level" AS ENUM ('aal1', 'aal2', 'aal3');

-- Table Definition
CREATE TABLE "auth"."sessions" (
    "id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    "created_at" timestamptz,
    "updated_at" timestamptz,
    "factor_id" uuid,
    "aal" "auth"."aal_level",
    "not_after" timestamptz,
    "refreshed_at" timestamp,
    "user_agent" text,
    "ip" inet,
    "tag" text,
    "oauth_client_id" uuid,
    "refresh_token_hmac_key" text,
    "refresh_token_counter" int8,
    "scopes" text,
    CONSTRAINT "sessions_oauth_client_id_fkey" FOREIGN KEY ("oauth_client_id") REFERENCES "auth"."oauth_clients"("id") ON DELETE CASCADE,
    CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "auth"."sessions"."not_after" IS 'Auth: Not after is a nullable column that contains a timestamp after which the session should be regarded as expired.';
COMMENT ON COLUMN "auth"."sessions"."refresh_token_hmac_key" IS 'Holds a HMAC-SHA256 key used to sign refresh tokens for this session.';
COMMENT ON COLUMN "auth"."sessions"."refresh_token_counter" IS 'Holds the ID (counter) of the last issued refresh token.';


-- Comments
COMMENT ON TABLE "auth"."sessions" IS 'Auth: Stores session data associated to a user.';


-- Indices
CREATE INDEX user_id_created_at_idx ON auth.sessions USING btree (user_id, created_at);
CREATE INDEX sessions_user_id_idx ON auth.sessions USING btree (user_id);
CREATE INDEX sessions_not_after_idx ON auth.sessions USING btree (not_after DESC);
CREATE INDEX sessions_oauth_client_id_idx ON auth.sessions USING btree (oauth_client_id);

DROP VIEW IF EXISTS "extensions"."pg_stat_statements_info";
 SELECT dealloc,
    stats_reset
   FROM pg_stat_statements_info() pg_stat_statements_info(dealloc, stats_reset);

DROP VIEW IF EXISTS "extensions"."pg_stat_statements";
 SELECT userid,
    dbid,
    toplevel,
    queryid,
    query,
    plans,
    total_plan_time,
    min_plan_time,
    max_plan_time,
    mean_plan_time,
    stddev_plan_time,
    calls,
    total_exec_time,
    min_exec_time,
    max_exec_time,
    mean_exec_time,
    stddev_exec_time,
    rows,
    shared_blks_hit,
    shared_blks_read,
    shared_blks_dirtied,
    shared_blks_written,
    local_blks_hit,
    local_blks_read,
    local_blks_dirtied,
    local_blks_written,
    temp_blks_read,
    temp_blks_written,
    shared_blk_read_time,
    shared_blk_write_time,
    local_blk_read_time,
    local_blk_write_time,
    temp_blk_read_time,
    temp_blk_write_time,
    wal_records,
    wal_fpi,
    wal_bytes,
    jit_functions,
    jit_generation_time,
    jit_inlining_count,
    jit_inlining_time,
    jit_optimization_count,
    jit_optimization_time,
    jit_emission_count,
    jit_emission_time,
    jit_deform_count,
    jit_deform_time,
    stats_since,
    minmax_stats_since
   FROM pg_stat_statements(true) pg_stat_statements(userid, dbid, toplevel, queryid, query, plans, total_plan_time, min_plan_time, max_plan_time, mean_plan_time, stddev_plan_time, calls, total_exec_time, min_exec_time, max_exec_time, mean_exec_time, stddev_exec_time, rows, shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, temp_blks_written, shared_blk_read_time, shared_blk_write_time, local_blk_read_time, local_blk_write_time, temp_blk_read_time, temp_blk_write_time, wal_records, wal_fpi, wal_bytes, jit_functions, jit_generation_time, jit_inlining_count, jit_inlining_time, jit_optimization_count, jit_optimization_time, jit_emission_count, jit_emission_time, jit_deform_count, jit_deform_time, stats_since, minmax_stats_since);

DROP TABLE IF EXISTS "public"."completed_lessons";
-- Table Definition
CREATE TABLE "public"."completed_lessons" (
    "id" int8 NOT NULL,
    "player_id" int8 NOT NULL,
    "coach_id" int8,
    "date" date,
    "lesson_id" int8,
    "start_time" time,
    "end_time" time,
    "rating" numeric,
    "coach_feedback" text,
    "created_at" timestamptz,
    "evaluation" jsonb,
    PRIMARY KEY ("id")
);

DROP TABLE IF EXISTS "public"."coach_players";
-- Table Definition
CREATE TABLE "public"."coach_players" (
    "coach_id" int8 NOT NULL,
    "player_id" int8 NOT NULL,
    "created_at" timestamptz DEFAULT now(),
    CONSTRAINT "coach_players_coach_fkey" FOREIGN KEY ("coach_id") REFERENCES "public"."coaches"("coach_id") ON DELETE CASCADE,
    CONSTRAINT "coach_players_player_fkey" FOREIGN KEY ("player_id") REFERENCES "public"."players"("player_id") ON DELETE CASCADE,
    PRIMARY KEY ("coach_id","player_id")
);

DROP TABLE IF EXISTS "public"."group_lesson_requests";
-- Table Definition
CREATE TABLE "public"."group_lesson_requests" (
    "request_id" int8 NOT NULL,
    "player_id" int8 NOT NULL,
    "date" date,
    "time" time,
    "created_at" time,
    "lesson_focus" text,
    "coach_id" int8,
    PRIMARY KEY ("request_id")
);

DROP TABLE IF EXISTS "public"."players";
DROP TYPE IF EXISTS "public"."rankingchoice";
CREATE TYPE "public"."rankingchoice" AS ENUM ('P50', 'P100', 'P200', 'P300', 'P400', 'P500', 'P700', 'P1000', 'Geen');
DROP TYPE IF EXISTS "public"."gender_enum";
CREATE TYPE "public"."gender_enum" AS ENUM ('man', 'vrouw', 'anders');
DROP TYPE IF EXISTS "public"."lesson_pref_enum";
CREATE TYPE "public"."lesson_pref_enum" AS ENUM ('individual', 'group');
DROP TYPE IF EXISTS "public"."intensity_enum";
CREATE TYPE "public"."intensity_enum" AS ENUM ('recreational', 'competitive');

-- Table Definition
CREATE TABLE "public"."players" (
    "player_id" int8 NOT NULL,
    "first_name" text NOT NULL,
    "last_name" text NOT NULL,
    "email" text NOT NULL,
    "phone" text,
    "hand_preference" text,
    "ranking" "public"."rankingchoice",
    "created_at" timestamptz DEFAULT now(),
    "gender" "public"."gender_enum",
    "strengths" text,
    "weaknesses" text,
    "profile_image" text,
    "date_of_birth" date,
    "lesson_type_preference" "public"."lesson_pref_enum",
    "playing_intensity" "public"."intensity_enum",
    PRIMARY KEY ("player_id")
);

DROP TABLE IF EXISTS "public"."clubs";
-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS clubs_club_id_seq;

-- Table Definition
CREATE TABLE "public"."clubs" (
    "club_id" int4 NOT NULL DEFAULT nextval('clubs_club_id_seq'::regclass),
    "club_name" varchar NOT NULL,
    "location" varchar,
    "contact_info" jsonb,
    "sports_supported" jsonb,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now(),
    PRIMARY KEY ("club_id")
);

DROP TABLE IF EXISTS "public"."coach_availability";
-- Table Definition
CREATE TABLE "public"."coach_availability" (
    "id" int8 NOT NULL,
    "created_at" timestamp,
    "coach_id" int8,
    "date" timestamptz NOT NULL DEFAULT now(),
    "start_time" time,
    "end_time" time,
    PRIMARY KEY ("id")
);


-- Indices
CREATE UNIQUE INDEX "CoachAvailability_pkey" ON public.coach_availability USING btree (id);

DROP TABLE IF EXISTS "public"."lesson_focus";
-- Table Definition
CREATE TABLE "public"."lesson_focus" (
    "id" int8 NOT NULL,
    "name" text NOT NULL,
    PRIMARY KEY ("id")
);

DROP TABLE IF EXISTS "public"."lessons";
-- Sequence and defined type
CREATE SEQUENCE IF NOT EXISTS lessons_lesson_id_seq;

-- Table Definition
CREATE TABLE "public"."lessons" (
    "lesson_id" int4 NOT NULL DEFAULT nextval('lessons_lesson_id_seq'::regclass),
    "club_id" int4,
    "lesson_type" varchar,
    "date" date,
    "start_time" time,
    "end_time" time,
    "created_at" timestamp DEFAULT now(),
    "updated_at" timestamp DEFAULT now(),
    "coach_id" int4,
    "lesson_focus_id" int8,
    "lesson_focus" text,
    CONSTRAINT "lessons_club_id_fkey" FOREIGN KEY ("club_id") REFERENCES "public"."clubs"("club_id") ON DELETE CASCADE,
    CONSTRAINT "lessons_lesson_focus_id_fkey" FOREIGN KEY ("lesson_focus_id") REFERENCES "public"."lesson_focus"("id"),
    PRIMARY KEY ("lesson_id")
);

DROP TABLE IF EXISTS "public"."coaches";
DROP TYPE IF EXISTS "public"."gender_enum";
CREATE TYPE "public"."gender_enum" AS ENUM ('man', 'vrouw', 'anders');
DROP TYPE IF EXISTS "public"."rankingchoice";
CREATE TYPE "public"."rankingchoice" AS ENUM ('P50', 'P100', 'P200', 'P300', 'P400', 'P500', 'P700', 'P1000', 'Geen');
DROP TYPE IF EXISTS "public"."lesson_pref_enum";
CREATE TYPE "public"."lesson_pref_enum" AS ENUM ('individual', 'group');
DROP TYPE IF EXISTS "public"."intensity_enum";
CREATE TYPE "public"."intensity_enum" AS ENUM ('recreational', 'competitive');

-- Table Definition
CREATE TABLE "public"."coaches" (
    "coach_id" int8 NOT NULL,
    "first_name" text NOT NULL,
    "last_name" text NOT NULL,
    "email" text NOT NULL,
    "phone" text,
    "bio" text,
    "created_at" timestamptz DEFAULT now(),
    "gender" "public"."gender_enum",
    "is_active" bool DEFAULT true,
    "ranking" "public"."rankingchoice",
    "profile_image" text,
    "date_of_birth" date,
    "hand_preference" text,
    "lesson_type_preference" "public"."lesson_pref_enum",
    "playing_intensity" "public"."intensity_enum",
    "ranking_value" int4,
    PRIMARY KEY ("coach_id")
);

DROP TABLE IF EXISTS "public"."lesson_players";
-- Table Definition
CREATE TABLE "public"."lesson_players" (
    "lesson_id" int4 NOT NULL,
    "player_id" int4 NOT NULL,
    CONSTRAINT "lesson_players_lesson_id_fkey" FOREIGN KEY ("lesson_id") REFERENCES "public"."lessons"("lesson_id") ON DELETE CASCADE,
    PRIMARY KEY ("lesson_id","player_id")
);

DROP TABLE IF EXISTS "public"."alembic_version";
-- Table Definition
CREATE TABLE "public"."alembic_version" (
    "version_num" varchar(32) NOT NULL,
    PRIMARY KEY ("version_num")
);


-- Indices
CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num);

DROP TABLE IF EXISTS "realtime"."messages";
-- Table Definition
CREATE TABLE "realtime"."messages" (
    "topic" text NOT NULL,
    "extension" text NOT NULL,
    "payload" jsonb,
    "event" text,
    "private" bool DEFAULT false,
    "updated_at" timestamp NOT NULL DEFAULT now(),
    "inserted_at" timestamp NOT NULL DEFAULT now(),
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    PRIMARY KEY ("id","inserted_at")
);


-- Indices
CREATE INDEX messages_inserted_at_topic_index ON ONLY realtime.messages USING btree (inserted_at DESC, topic) WHERE ((extension = 'broadcast'::text) AND (private IS TRUE));

DROP TABLE IF EXISTS "realtime"."schema_migrations";
-- Table Definition
CREATE TABLE "realtime"."schema_migrations" (
    "version" int8 NOT NULL,
    "inserted_at" timestamp(0),
    PRIMARY KEY ("version")
);

DROP TABLE IF EXISTS "realtime"."subscription";
-- Table Definition
CREATE TABLE "realtime"."subscription" (
    "id" int8 NOT NULL,
    "subscription_id" uuid NOT NULL,
    "entity" regclass NOT NULL,
    "filters" _user_defined_filter NOT NULL DEFAULT '{}'::realtime.user_defined_filter[],
    "claims" jsonb NOT NULL,
    "claims_role" regrole NOT NULL,
    "created_at" timestamp NOT NULL DEFAULT timezone('utc'::text, now()),
    PRIMARY KEY ("id")
);


-- Indices
CREATE UNIQUE INDEX pk_subscription ON realtime.subscription USING btree (id);
CREATE UNIQUE INDEX subscription_subscription_id_entity_filters_key ON realtime.subscription USING btree (subscription_id, entity, filters);
CREATE INDEX ix_realtime_subscription_entity ON realtime.subscription USING btree (entity);

DROP TABLE IF EXISTS "storage"."buckets";
DROP TYPE IF EXISTS "storage"."buckettype";
CREATE TYPE "storage"."buckettype" AS ENUM ('STANDARD', 'ANALYTICS', 'VECTOR');

-- Table Definition
CREATE TABLE "storage"."buckets" (
    "id" text NOT NULL,
    "name" text NOT NULL,
    "owner" uuid,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "public" bool DEFAULT false,
    "avif_autodetection" bool DEFAULT false,
    "file_size_limit" int8,
    "allowed_mime_types" _text,
    "owner_id" text,
    "type" "storage"."buckettype" NOT NULL DEFAULT 'STANDARD'::storage.buckettype,
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "storage"."buckets"."owner" IS 'Field is deprecated, use owner_id instead';


-- Indices
CREATE UNIQUE INDEX bname ON storage.buckets USING btree (name);

DROP TABLE IF EXISTS "storage"."objects";
-- Table Definition
CREATE TABLE "storage"."objects" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "bucket_id" text,
    "name" text,
    "owner" uuid,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    "last_accessed_at" timestamptz DEFAULT now(),
    "metadata" jsonb,
    "path_tokens" _text,
    "version" text,
    "owner_id" text,
    "user_metadata" jsonb,
    "level" int4,
    CONSTRAINT "objects_bucketId_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id"),
    PRIMARY KEY ("id")
);

-- Column Comments
COMMENT ON COLUMN "storage"."objects"."owner" IS 'Field is deprecated, use owner_id instead';


-- Indices
CREATE UNIQUE INDEX bucketid_objname ON storage.objects USING btree (bucket_id, name);
CREATE INDEX name_prefix_search ON storage.objects USING btree (name text_pattern_ops);
CREATE INDEX idx_objects_bucket_id_name ON storage.objects USING btree (bucket_id, name COLLATE "C");
CREATE UNIQUE INDEX idx_name_bucket_level_unique ON storage.objects USING btree (name COLLATE "C", bucket_id, level);
CREATE UNIQUE INDEX objects_bucket_id_level_idx ON storage.objects USING btree (bucket_id, level, name COLLATE "C");
CREATE INDEX idx_objects_lower_name ON storage.objects USING btree ((path_tokens[level]), lower(name) text_pattern_ops, bucket_id, level);

DROP TABLE IF EXISTS "storage"."migrations";
-- Table Definition
CREATE TABLE "storage"."migrations" (
    "id" int4 NOT NULL,
    "name" varchar(100) NOT NULL,
    "hash" varchar(40) NOT NULL,
    "executed_at" timestamp DEFAULT CURRENT_TIMESTAMP
);


-- Indices
CREATE UNIQUE INDEX migrations_name_key ON storage.migrations USING btree (name);

DROP TABLE IF EXISTS "storage"."buckets_vectors";
DROP TYPE IF EXISTS "storage"."buckettype";
CREATE TYPE "storage"."buckettype" AS ENUM ('STANDARD', 'ANALYTICS', 'VECTOR');

-- Table Definition
CREATE TABLE "storage"."buckets_vectors" (
    "id" text NOT NULL,
    "type" "storage"."buckettype" NOT NULL DEFAULT 'VECTOR'::storage.buckettype,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now()
);

DROP TABLE IF EXISTS "storage"."vector_indexes";
-- Table Definition
CREATE TABLE "storage"."vector_indexes" (
    "id" text NOT NULL DEFAULT gen_random_uuid(),
    "name" text NOT NULL,
    "bucket_id" text NOT NULL,
    "data_type" text NOT NULL,
    "dimension" int4 NOT NULL,
    "distance_metric" text NOT NULL,
    "metadata_configuration" jsonb,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT "vector_indexes_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets_vectors"("id")
);


-- Indices
CREATE UNIQUE INDEX vector_indexes_name_bucket_id_idx ON storage.vector_indexes USING btree (name, bucket_id);

DROP TABLE IF EXISTS "storage"."s3_multipart_uploads_parts";
-- Table Definition
CREATE TABLE "storage"."s3_multipart_uploads_parts" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "upload_id" text NOT NULL,
    "size" int8 NOT NULL DEFAULT 0,
    "part_number" int4 NOT NULL,
    "bucket_id" text NOT NULL,
    "key" text NOT NULL,
    "etag" text NOT NULL,
    "owner_id" text,
    "version" text NOT NULL,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT "s3_multipart_uploads_parts_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id"),
    CONSTRAINT "s3_multipart_uploads_parts_upload_id_fkey" FOREIGN KEY ("upload_id") REFERENCES "storage"."s3_multipart_uploads"("id") ON DELETE CASCADE,
    PRIMARY KEY ("id")
);

DROP TABLE IF EXISTS "storage"."s3_multipart_uploads";
-- Table Definition
CREATE TABLE "storage"."s3_multipart_uploads" (
    "id" text NOT NULL,
    "in_progress_size" int8 NOT NULL DEFAULT 0,
    "upload_signature" text NOT NULL,
    "bucket_id" text NOT NULL,
    "key" text NOT NULL,
    "version" text NOT NULL,
    "owner_id" text,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "user_metadata" jsonb,
    CONSTRAINT "s3_multipart_uploads_bucket_id_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id"),
    PRIMARY KEY ("id")
);


-- Indices
CREATE INDEX idx_multipart_uploads_list ON storage.s3_multipart_uploads USING btree (bucket_id, key, created_at);

DROP TABLE IF EXISTS "storage"."prefixes";
-- Table Definition
CREATE TABLE "storage"."prefixes" (
    "bucket_id" text NOT NULL,
    "name" text NOT NULL,
    "level" int4 NOT NULL,
    "created_at" timestamptz DEFAULT now(),
    "updated_at" timestamptz DEFAULT now(),
    CONSTRAINT "prefixes_bucketId_fkey" FOREIGN KEY ("bucket_id") REFERENCES "storage"."buckets"("id"),
    PRIMARY KEY ("bucket_id","level","name")
);


-- Indices
CREATE INDEX idx_prefixes_lower_name ON storage.prefixes USING btree (bucket_id, level, ((string_to_array(name, '/'::text))[level]), lower(name) text_pattern_ops);

DROP TABLE IF EXISTS "storage"."buckets_analytics";
DROP TYPE IF EXISTS "storage"."buckettype";
CREATE TYPE "storage"."buckettype" AS ENUM ('STANDARD', 'ANALYTICS', 'VECTOR');

-- Table Definition
CREATE TABLE "storage"."buckets_analytics" (
    "name" text NOT NULL,
    "type" "storage"."buckettype" NOT NULL DEFAULT 'ANALYTICS'::storage.buckettype,
    "format" text NOT NULL DEFAULT 'ICEBERG'::text,
    "created_at" timestamptz NOT NULL DEFAULT now(),
    "updated_at" timestamptz NOT NULL DEFAULT now(),
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "deleted_at" timestamptz,
    PRIMARY KEY ("id")
);


-- Indices
CREATE UNIQUE INDEX buckets_analytics_unique_name_idx ON storage.buckets_analytics USING btree (name) WHERE (deleted_at IS NULL);

DROP TABLE IF EXISTS "vault"."secrets";
-- Table Definition
CREATE TABLE "vault"."secrets" (
    "id" uuid NOT NULL DEFAULT gen_random_uuid(),
    "name" text,
    "description" text NOT NULL DEFAULT ''::text,
    "secret" text NOT NULL,
    "key_id" uuid,
    "nonce" bytea DEFAULT vault._crypto_aead_det_noncegen(),
    "created_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("id")
);


-- Comments
COMMENT ON TABLE "vault"."secrets" IS 'Table with encrypted `secret` column for storing sensitive information on disk.';


-- Indices
CREATE UNIQUE INDEX secrets_name_idx ON vault.secrets USING btree (name) WHERE (name IS NOT NULL);

DROP VIEW IF EXISTS "vault"."decrypted_secrets";
 SELECT id,
    name,
    description,
    secret,
    convert_from(vault._crypto_aead_det_decrypt(message => decode(secret, 'base64'::text), additional => convert_to((id)::text, 'utf8'::name), key_id => (0)::bigint, context => '\x7067736f6469756d'::bytea, nonce => nonce), 'utf8'::name) AS decrypted_secret,
    key_id,
    nonce,
    created_at,
    updated_at
   FROM vault.secrets s;







INSERT INTO "auth"."schema_migrations" ("version") VALUES
('20171026211738'),
('20171026211808'),
('20171026211834'),
('20180103212743'),
('20180108183307'),
('20180119214651'),
('20180125194653'),
('00'),
('20210710035447'),
('20210722035447'),
('20210730183235'),
('20210909172000'),
('20210927181326'),
('20211122151130'),
('20211124214934'),
('20211202183645'),
('20220114185221'),
('20220114185340'),
('20220224000811'),
('20220323170000'),
('20220429102000'),
('20220531120530'),
('20220614074223'),
('20220811173540'),
('20221003041349'),
('20221003041400'),
('20221011041400'),
('20221020193600'),
('20221021073300'),
('20221021082433'),
('20221027105023'),
('20221114143122'),
('20221114143410'),
('20221125140132'),
('20221208132122'),
('20221215195500'),
('20221215195800'),
('20221215195900'),
('20230116124310'),
('20230116124412'),
('20230131181311'),
('20230322519590'),
('20230402418590'),
('20230411005111'),
('20230508135423'),
('20230523124323'),
('20230818113222'),
('20230914180801'),
('20231027141322'),
('20231114161723'),
('20231117164230'),
('20240115144230'),
('20240214120130'),
('20240306115329'),
('20240314092811'),
('20240427152123'),
('20240612123726'),
('20240729123726'),
('20240802193726'),
('20240806073726'),
('20241009103726'),
('20250717082212'),
('20250731150234'),
('20250804100000'),
('20250901200500'),
('20250903112500'),
('20250904133000'),
('20250925093508'),
('20251007112900'),
('20251104100000'),
('20251111201300'),
('20251201000000');















INSERT INTO "public"."completed_lessons" ("id", "player_id", "coach_id", "date", "lesson_id", "start_time", "end_time", "rating", "coach_feedback", "created_at", "evaluation") VALUES
(5, 3, 1, '2025-11-27', 2, '09:00:00', '10:00:00', NULL, NULL, NULL, '{"techniek": {"smash": "6", "volley": "7", "backhand": "8", "forehand": "6", "opmerking": "aa"}}'),
(6, 3, 1, '2025-11-28', 3, '09:00:00', '10:00:00', NULL, NULL, NULL, '{"fysiek": {"conditie": "7", "opmerking": "Matig", "explosiviteit": "7", "reactiesnelheid": "7"}, "mentaal": {"focus": "7", "opmerking": "", "doorzettingsvermogen": "8"}, "tactiek": {"opmerking": "Positiespel nog een serieus werkpunt", "positiespel": "3", "keuze_slagen": "6", "samenwerking": "10", "speelstrategie": "7"}, "techniek": {"smash": "3", "volley": "7", "backhand": "6", "forehand": "6", "opmerking": "Goede vooruitgang ten opzichte van vorige weken, welk nog werk aan de smash"}}'),
(7, 3, 2, '2025-11-22', 5, '17:00:00', '18:00:00', NULL, '{"fysiek": {"conditie": "7", "explosiviteit": "6", "opmerking": "", "reactiesnelheid": "4"}, "mentaal": {"doorzettingsvermogen": "10", "focus": "6", "opmerking": ""}, "tactiek": {"keuze_slagen": "3", "opmerking": "", "positiespel": "5", "samenwerking": "2", "speelstrategie": "5"}, "techniek": {"backhand": "4", "forehand": "3", "opmerking": "", "smash": "4", "volley": "2"}}', NULL, NULL),
(8, 5, 1, '2025-11-28', 6, '10:00:00', '11:00:00', NULL, NULL, NULL, '{"fysiek": {"conditie": "7", "opmerking": "/", "explosiviteit": "5", "reactiesnelheid": "6"}, "mentaal": {"focus": "7", "opmerking": "/", "doorzettingsvermogen": "4"}, "tactiek": {"opmerking": "/", "positiespel": "7", "keuze_slagen": "6", "samenwerking": "6", "speelstrategie": "8"}, "techniek": {"smash": "10", "volley": "7", "backhand": "5", "forehand": "4", "opmerking": "/"}}'),
(9, 3, 2, '2025-11-14', 7, '13:00:00', '14:00:00', NULL, NULL, NULL, NULL),
(10, 8, 4, '2025-11-29', 10, '16:00:00', '17:00:00', NULL, '{"fysiek": {"conditie": "6", "explosiviteit": "4", "opmerking": "", "reactiesnelheid": "6"}, "mentaal": {"doorzettingsvermogen": "5", "focus": "4", "opmerking": ""}, "tactiek": {"keuze_slagen": "6", "opmerking": "", "positiespel": "5", "samenwerking": "6", "speelstrategie": "1"}, "techniek": {"backhand": "5", "forehand": "6", "opmerking": "", "smash": "7", "volley": "5"}}', NULL, '{"fysiek": {"conditie": "6", "opmerking": "", "explosiviteit": "4", "reactiesnelheid": "7"}, "mentaal": {"focus": "9", "opmerking": "goed", "doorzettingsvermogen": "8"}, "tactiek": {"opmerking": "", "positiespel": "4", "keuze_slagen": "4", "samenwerking": "2", "speelstrategie": "4"}, "techniek": {"smash": "4", "volley": "5", "backhand": "5", "forehand": "3", "opmerking": ""}}'),
(11, 1, 1, '2025-11-29', 17, '15:00:00', '16:00:00', NULL, NULL, NULL, '{"fysiek": {"conditie": "6", "opmerking": "", "explosiviteit": "8", "reactiesnelheid": "6"}, "mentaal": {"focus": "4", "opmerking": "", "doorzettingsvermogen": "7"}, "tactiek": {"opmerking": "", "positiespel": "6", "keuze_slagen": "4", "samenwerking": "3", "speelstrategie": "6"}, "techniek": {"smash": "2", "volley": "7", "backhand": "6", "forehand": "3", "opmerking": ""}}'),
(12, 8, 4, '2025-11-29', 18, '12:00:00', '13:00:00', NULL, '{"fysiek": {"conditie": "6", "explosiviteit": "5", "opmerking": "", "reactiesnelheid": "7"}, "mentaal": {"doorzettingsvermogen": "2", "focus": "3", "opmerking": ""}, "tactiek": {"keuze_slagen": "5", "opmerking": "", "positiespel": "7", "samenwerking": "5", "speelstrategie": "5"}, "techniek": {"backhand": "5", "forehand": "5", "opmerking": "", "smash": "5", "volley": "5"}}', NULL, '{"fysiek": {"conditie": "6", "opmerking": "", "explosiviteit": "8", "reactiesnelheid": "6"}, "mentaal": {"focus": "5", "opmerking": "", "doorzettingsvermogen": "6"}, "tactiek": {"opmerking": "", "positiespel": "4", "keuze_slagen": "5", "samenwerking": "6", "speelstrategie": "7"}, "techniek": {"smash": "5", "volley": "5", "backhand": "7", "forehand": "6", "opmerking": "goed"}}'),
(13, 8, 4, '2025-11-27', 19, '11:00:00', '12:00:00', 80, '{"fysiek": {"conditie": "1", "explosiviteit": "1", "opmerking": "kan beter", "reactiesnelheid": "1"}, "mentaal": {"doorzettingsvermogen": "2", "focus": "2", "opmerking": ""}, "tactiek": {"keuze_slagen": "7", "opmerking": "top\r\n", "positiespel": "6", "samenwerking": "7", "speelstrategie": "7"}, "techniek": {"backhand": "6", "forehand": "7", "opmerking": "goed\r\n", "smash": "6", "volley": "7"}}', NULL, '{"fysiek": {"conditie": "8", "opmerking": "", "explosiviteit": "8", "reactiesnelheid": "8"}, "mentaal": {"focus": "7", "opmerking": "super", "doorzettingsvermogen": "5"}, "tactiek": {"opmerking": "", "positiespel": "7", "keuze_slagen": "6", "samenwerking": "7", "speelstrategie": "6"}, "techniek": {"smash": "6", "volley": "5", "backhand": "4", "forehand": "5", "opmerking": ""}}'),
(14, 3, 1, '2025-11-29', 4, '19:00:00', '20:00:00', NULL, NULL, NULL, NULL),
(15, 3, 1, '2025-11-30', 12, '09:00:00', '10:00:00', NULL, NULL, NULL, NULL),
(16, 8, 4, '2025-11-29', 21, '12:00:00', '13:00:00', NULL, '{"fysiek": {"conditie": "9", "explosiviteit": "5", "opmerking": "", "reactiesnelheid": "4"}, "mentaal": {"doorzettingsvermogen": "5", "focus": "4", "opmerking": ""}, "tactiek": {"keuze_slagen": "5", "opmerking": "", "positiespel": "5", "samenwerking": "3", "speelstrategie": "6"}, "techniek": {"backhand": "5", "forehand": "3", "opmerking": "", "smash": "4", "volley": "5"}}', NULL, '{"fysiek": {"conditie": "10", "opmerking": "", "explosiviteit": "6", "reactiesnelheid": "7"}, "mentaal": {"focus": "7", "opmerking": "", "doorzettingsvermogen": "6"}, "tactiek": {"opmerking": "", "positiespel": "6", "keuze_slagen": "8", "samenwerking": "6", "speelstrategie": "8"}, "techniek": {"smash": "8", "volley": "6", "backhand": "7", "forehand": "6", "opmerking": "goed"}}'),
(17, 12, 4, '2025-11-28', 22, '18:00:00', '19:00:00', NULL, '{"fysiek": {"conditie": "6", "explosiviteit": "6", "opmerking": "", "reactiesnelheid": "6"}, "mentaal": {"doorzettingsvermogen": "6", "focus": "4", "opmerking": ""}, "tactiek": {"keuze_slagen": "6", "opmerking": "", "positiespel": "4", "samenwerking": "6", "speelstrategie": "6"}, "techniek": {"backhand": "4", "forehand": "5", "opmerking": "", "smash": "7", "volley": "6"}}', NULL, '{"fysiek": {"conditie": "10", "opmerking": "", "explosiviteit": "10", "reactiesnelheid": "10"}, "mentaal": {"focus": "10", "opmerking": "", "doorzettingsvermogen": "10"}, "tactiek": {"opmerking": "", "positiespel": "10", "keuze_slagen": "10", "samenwerking": "10", "speelstrategie": "10"}, "techniek": {"smash": "10", "volley": "9", "backhand": "10", "forehand": "10", "opmerking": "Top! Gemotiveerd! "}}'),
(18, 11, 1, '2025-12-01', 20, '14:00:00', '15:00:00', NULL, '{"fysiek": {"conditie": "8", "explosiviteit": "2", "opmerking": "", "reactiesnelheid": "7"}, "mentaal": {"doorzettingsvermogen": "4", "focus": "3", "opmerking": ""}, "tactiek": {"keuze_slagen": "7", "opmerking": "", "positiespel": "9", "samenwerking": "6", "speelstrategie": "9"}, "techniek": {"backhand": "5", "forehand": "7", "opmerking": "", "smash": "7", "volley": "6"}}', NULL, NULL),
(19, 19, 9, '2025-12-02', 29, '10:00:00', '11:00:00', NULL, '{"fysiek": {"conditie": "6", "explosiviteit": "6", "opmerking": "", "reactiesnelheid": "7"}, "mentaal": {"doorzettingsvermogen": "5", "focus": "6", "opmerking": ""}, "tactiek": {"keuze_slagen": "5", "opmerking": "", "positiespel": "6", "samenwerking": "6", "speelstrategie": "6"}, "techniek": {"backhand": "4", "forehand": "5", "opmerking": "", "smash": "5", "volley": "7"}}', NULL, '{"fysiek": {"conditie": "7", "opmerking": "", "explosiviteit": "7", "reactiesnelheid": "8"}, "mentaal": {"focus": "6", "opmerking": "kan beter", "doorzettingsvermogen": "5"}, "tactiek": {"opmerking": "", "positiespel": "9", "keuze_slagen": "9", "samenwerking": "4", "speelstrategie": "7"}, "techniek": {"smash": "7", "volley": "5", "backhand": "8", "forehand": "7", "opmerking": "zeer goed"}}'),
(20, 10, 5, '2025-12-04', 27, '13:00:00', '14:00:00', NULL, '{"fysiek": {"conditie": "5", "explosiviteit": "7", "opmerking": "", "reactiesnelheid": "4"}, "mentaal": {"doorzettingsvermogen": "6", "focus": "6", "opmerking": ""}, "tactiek": {"keuze_slagen": "6", "opmerking": "", "positiespel": "9", "samenwerking": "3", "speelstrategie": "5"}, "techniek": {"backhand": "5", "forehand": "3", "opmerking": "", "smash": "7", "volley": "5"}}', NULL, NULL),
(21, 13, 1, '2025-12-05', 31, '15:00:00', '16:00:00', NULL, '{"fysiek": {"conditie": "5", "explosiviteit": "2", "opmerking": "", "reactiesnelheid": "5"}, "mentaal": {"doorzettingsvermogen": "6", "focus": "9", "opmerking": ""}, "tactiek": {"keuze_slagen": "4", "opmerking": "", "positiespel": "4", "samenwerking": "6", "speelstrategie": "5"}, "techniek": {"backhand": "7", "forehand": "3", "opmerking": "", "smash": "5", "volley": "6"}}', NULL, NULL),
(22, 21, 1, '2025-12-06', 32, '09:00:00', '10:00:00', NULL, '{"fysiek": {"conditie": "3", "explosiviteit": "4", "opmerking": "", "reactiesnelheid": "3"}, "mentaal": {"doorzettingsvermogen": "6", "focus": "5", "opmerking": ""}, "tactiek": {"keuze_slagen": "5", "opmerking": "", "positiespel": "6", "samenwerking": "6", "speelstrategie": "4"}, "techniek": {"backhand": "6", "forehand": "6", "opmerking": "", "smash": "5", "volley": "4"}}', NULL, NULL),
(23, 22, 1, '2025-12-07', 33, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(24, 9, 4, '2025-12-07', 34, '18:00:00', '19:00:00', NULL, '{"fysiek": {"conditie": "7", "explosiviteit": "4", "opmerking": "", "reactiesnelheid": "6"}, "mentaal": {"doorzettingsvermogen": "5", "focus": "4", "opmerking": ""}, "tactiek": {"keuze_slagen": "3", "opmerking": "", "positiespel": "7", "samenwerking": "1", "speelstrategie": "7"}, "techniek": {"backhand": "5", "forehand": "5", "opmerking": "", "smash": "3", "volley": "5"}}', NULL, NULL),
(25, 40, 17, '2025-12-07', 69, '11:00:00', '12:00:00', NULL, '{"fysiek": {"conditie": "5", "explosiviteit": "3", "opmerking": "123", "reactiesnelheid": "4"}, "mentaal": {"doorzettingsvermogen": "5", "focus": "6", "opmerking": "67"}, "tactiek": {"keuze_slagen": "6", "opmerking": "inorde\r\n", "positiespel": "5", "samenwerking": "2", "speelstrategie": "7"}, "techniek": {"backhand": "3", "forehand": "7", "opmerking": "goed\r\n", "smash": "10", "volley": "4"}}', NULL, NULL),
(26, 40, 17, '2025-12-08', 68, '15:00:00', '16:00:00', NULL, NULL, NULL, NULL),
(27, 8, 10, '2025-12-08', 38, '17:00:00', '18:00:00', NULL, NULL, NULL, NULL),
(28, 20, 10, '2025-12-08', 39, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(29, 8, 10, '2025-12-09', 40, '14:00:00', '15:00:00', NULL, NULL, NULL, NULL),
(30, 8, 10, '2025-12-09', 43, '15:00:00', '16:00:00', NULL, NULL, NULL, NULL),
(31, 45, 17, '2025-12-09', 104, '15:00:00', '16:00:00', NULL, '{"fysiek": {"conditie": "4", "explosiviteit": "2", "opmerking": "", "reactiesnelheid": "5"}, "mentaal": {"doorzettingsvermogen": "2", "focus": "6", "opmerking": ""}, "tactiek": {"keuze_slagen": "4", "opmerking": "", "positiespel": "5", "samenwerking": "10", "speelstrategie": "10"}, "techniek": {"backhand": "8", "forehand": "7", "opmerking": "", "smash": "6", "volley": "4"}}', NULL, NULL),
(32, 8, 10, '2025-12-09', 41, '21:00:00', '22:00:00', NULL, NULL, NULL, NULL),
(33, 8, 10, '2025-12-09', 42, '21:00:00', '22:00:00', NULL, NULL, NULL, NULL),
(34, 3, 7, '2025-12-08', 115, '09:00:00', '10:00:00', NULL, '{"fysiek": {"conditie": "7", "explosiviteit": "4", "opmerking": "", "reactiesnelheid": "5"}, "mentaal": {"doorzettingsvermogen": "8", "focus": "7", "opmerking": ""}, "tactiek": {"keuze_slagen": "3", "opmerking": "", "positiespel": "3", "samenwerking": "4", "speelstrategie": "4"}, "techniek": {"backhand": "3", "forehand": "4", "opmerking": "", "smash": "6", "volley": "5"}}', NULL, NULL),
(35, 1, 9, '2025-12-05', 117, '12:00:00', '13:00:00', NULL, '{"fysiek": {"conditie": null, "explosiviteit": null, "opmerking": "", "reactiesnelheid": null}, "mentaal": {"doorzettingsvermogen": null, "focus": null, "opmerking": ""}, "tactiek": {"keuze_slagen": null, "opmerking": "", "positiespel": null, "samenwerking": null, "speelstrategie": null}, "techniek": {"backhand": null, "forehand": null, "opmerking": "", "smash": null, "volley": null}}', NULL, NULL),
(36, 8, 9, '2025-12-05', 117, '12:00:00', '13:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "8"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "goed", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "7", "bandeja": "5", "forehand": "7", "opmerking": "", "service": "5", "smash": "5", "volley": "5"}}', NULL, NULL),
(37, 20, 9, '2025-12-05', 117, '12:00:00', '13:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "5", "bandeja": "5", "forehand": "5", "opmerking": "", "service": "5", "smash": "5", "volley": "5"}}', NULL, NULL),
(38, 1, 4, '2025-12-10', 76, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(39, 20, 4, '2025-12-10', 76, '18:00:00', '19:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "extra oefenen op bal-keuzes", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "5", "bandeja": "5", "forehand": "7", "opmerking": "", "service": "7", "smash": "5", "volley": "5"}}', NULL, NULL),
(40, 8, 4, '2025-12-10', 76, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(41, 5, 13, '2025-12-11', 106, '19:00:00', '20:00:00', NULL, NULL, NULL, NULL),
(42, 10, 9, '2025-12-12', 109, '11:00:00', '12:00:00', NULL, '{}', NULL, NULL),
(43, 19, 9, '2025-12-12', 44, '10:00:00', '11:00:00', NULL, '{"fysiek": {"kracht": "2", "mobiliteit": "4", "opmerking": "", "snelheid": "7", "uithouding": "7"}, "mentaal": {"focus": "7", "inzet": "8", "opmerking": "", "sportiviteit": "8", "veerkracht": "8"}, "tactiek": {"keuze_slagen": "6", "netspel": "3", "opmerking": "", "positiespel": "6", "samenwerking": "5", "verdediging": "7"}, "techniek": {"backhand": "8", "bandeja": "5", "forehand": "8", "opmerking": "goed", "service": "8", "smash": "2", "volley": "7"}}', NULL, NULL),
(44, 8, 9, '2025-12-12', 47, '11:00:00', '12:00:00', NULL, '{"fysiek": {"kracht": "9", "mobiliteit": "9", "opmerking": "", "snelheid": "9", "uithouding": "9"}, "mentaal": {"focus": "9", "inzet": "8", "opmerking": "", "sportiviteit": "3", "veerkracht": "9"}, "tactiek": {"keuze_slagen": "9", "netspel": "9", "opmerking": "", "positiespel": "9", "samenwerking": "9", "verdediging": "9"}, "techniek": {"backhand": "8", "bandeja": "9", "forehand": "9", "opmerking": "Super ", "service": "9", "smash": "9", "volley": "3"}}', NULL, NULL),
(45, 31, 16, '2025-12-12', 64, '10:00:00', '11:00:00', NULL, NULL, NULL, NULL),
(46, 8, 1, '2025-12-12', 84, '13:00:00', '14:00:00', NULL, '{"fysiek": {"conditie": null, "explosiviteit": null, "opmerking": "", "reactiesnelheid": null}, "mentaal": {"doorzettingsvermogen": null, "focus": null, "opmerking": ""}, "tactiek": {"keuze_slagen": null, "opmerking": "", "positiespel": null, "samenwerking": null, "speelstrategie": null}, "techniek": {"backhand": null, "forehand": null, "opmerking": "", "smash": null, "volley": null}}', NULL, NULL),
(47, 1, 1, '2025-12-12', 84, '13:00:00', '14:00:00', NULL, '{"fysiek": {"conditie": null, "explosiviteit": null, "opmerking": "", "reactiesnelheid": null}, "mentaal": {"doorzettingsvermogen": null, "focus": null, "opmerking": ""}, "tactiek": {"keuze_slagen": null, "opmerking": "", "positiespel": null, "samenwerking": null, "speelstrategie": null}, "techniek": {"backhand": null, "forehand": null, "opmerking": "", "smash": null, "volley": null}}', NULL, NULL),
(48, 20, 1, '2025-12-12', 84, '13:00:00', '14:00:00', NULL, NULL, NULL, NULL),
(49, 19, 9, '2025-12-12', 45, '21:00:00', '22:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "top", "snelheid": "7", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "10", "opmerking": "zeer goed", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "wauw", "positiespel": "5", "samenwerking": "5", "verdediging": "10"}, "techniek": {"backhand": "5", "bandeja": "5", "forehand": "8", "opmerking": "goed", "service": "5", "smash": "5", "volley": "5"}}', NULL, NULL),
(50, 52, 4, '2025-12-12', 135, '13:00:00', '14:00:00', NULL, '{"fysiek": {"conditie": "6", "explosiviteit": "6", "opmerking": "goed bezig!", "reactiesnelheid": "7"}, "mentaal": {"doorzettingsvermogen": "8", "focus": "9", "opmerking": ""}, "tactiek": {"keuze_slagen": "7", "opmerking": "", "positiespel": "8", "samenwerking": "9", "speelstrategie": "7"}, "techniek": {"backhand": "4", "forehand": "8", "opmerking": "", "smash": "5", "volley": "4"}}', NULL, NULL),
(51, 52, 21, '2025-12-13', 128, '10:00:00', '11:00:00', NULL, NULL, NULL, NULL),
(52, 52, 21, '2025-12-13', 131, '09:00:00', '10:00:00', NULL, NULL, NULL, NULL),
(53, 1, 5, '2025-12-12', 139, '11:00:00', '12:00:00', NULL, '{"fysiek": {"conditie": "9", "explosiviteit": "6", "opmerking": "", "reactiesnelheid": "7"}, "mentaal": {"doorzettingsvermogen": "4", "focus": "7", "opmerking": ""}, "tactiek": {"keuze_slagen": "5", "opmerking": "", "positiespel": "10", "samenwerking": "6", "speelstrategie": "5"}, "techniek": {"backhand": "9", "forehand": "10", "opmerking": "/", "smash": "7", "volley": "9"}}', NULL, NULL),
(54, 19, 9, '2025-12-13', 48, '11:00:00', '12:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "oke", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "8", "bandeja": "5", "forehand": "9", "opmerking": "", "service": "5", "smash": "5", "volley": "8"}}', NULL, NULL),
(55, 52, 5, '2025-12-13', 129, '11:00:00', '12:00:00', NULL, '{"fysiek": {"conditie": null, "explosiviteit": null, "opmerking": "", "reactiesnelheid": null}, "mentaal": {"doorzettingsvermogen": null, "focus": null, "opmerking": ""}, "tactiek": {"keuze_slagen": null, "opmerking": "", "positiespel": null, "samenwerking": null, "speelstrategie": null}, "techniek": {"backhand": null, "forehand": null, "opmerking": "", "smash": null, "volley": null}}', NULL, NULL),
(56, 52, 21, '2025-12-13', 130, '12:00:00', '13:00:00', NULL, NULL, NULL, NULL),
(57, 8, 21, '2025-12-13', 130, '12:00:00', '13:00:00', NULL, NULL, NULL, NULL),
(58, 20, 21, '2025-12-13', 130, '12:00:00', '13:00:00', NULL, NULL, NULL, NULL),
(59, 66, 26, '2025-10-10', 156, '13:00:00', '14:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "8", "bandeja": "8", "forehand": "6", "opmerking": "oefenen!", "service": "3", "smash": "7", "volley": "3"}}', NULL, NULL),
(60, 1, 26, '2025-10-10', 157, '10:00:00', '11:00:00', NULL, '{"fysiek": {"kracht": "5", "mobiliteit": "5", "opmerking": "", "snelheid": "5", "uithouding": "5"}, "mentaal": {"focus": "5", "inzet": "5", "opmerking": "", "sportiviteit": "5", "veerkracht": "5"}, "tactiek": {"keuze_slagen": "5", "netspel": "5", "opmerking": "", "positiespel": "5", "samenwerking": "5", "verdediging": "5"}, "techniek": {"backhand": "5", "bandeja": "5", "forehand": "5", "opmerking": "", "service": "7", "smash": "5", "volley": "5"}}', NULL, NULL),
(61, 66, 26, '2025-10-10', 157, '10:00:00', '11:00:00', NULL, '{"fysiek": {"kracht": "8", "mobiliteit": "8", "opmerking": "", "snelheid": "8", "uithouding": "8"}, "mentaal": {"focus": "8", "inzet": "1", "opmerking": "", "sportiviteit": "8", "veerkracht": "7"}, "tactiek": {"keuze_slagen": "6", "netspel": "8", "opmerking": "", "positiespel": "9", "samenwerking": "7", "verdediging": "8"}, "techniek": {"backhand": "8", "bandeja": "7", "forehand": "9", "opmerking": "", "service": "3", "smash": "7", "volley": "1"}}', NULL, NULL),
(62, 8, 26, '2025-10-10', 157, '10:00:00', '11:00:00', NULL, '{"fysiek": {"kracht": "7", "mobiliteit": "7", "opmerking": "", "snelheid": "7", "uithouding": "7"}, "mentaal": {"focus": "7", "inzet": "7", "opmerking": "", "sportiviteit": "7", "veerkracht": "7"}, "tactiek": {"keuze_slagen": "5", "netspel": "7", "opmerking": "", "positiespel": "5", "samenwerking": "7", "verdediging": "7"}, "techniek": {"backhand": "7", "bandeja": "7", "forehand": "5", "opmerking": "", "service": "7", "smash": "8", "volley": "8"}}', NULL, NULL),
(63, 65, 9, '2025-12-14', 154, '22:00:00', '23:00:00', NULL, '{"fysiek": {"kracht": "9", "mobiliteit": "9", "opmerking": "", "snelheid": "9", "uithouding": "9"}, "mentaal": {"focus": "9", "inzet": "8", "opmerking": "", "sportiviteit": "3", "veerkracht": "2"}, "tactiek": {"keuze_slagen": "9", "netspel": "9", "opmerking": "", "positiespel": "9", "samenwerking": "9", "verdediging": "9"}, "techniek": {"backhand": "2", "bandeja": "8", "forehand": "8", "opmerking": "Goed ", "service": "8", "smash": "9", "volley": "2"}}', NULL, NULL),
(64, 67, 27, '2025-12-08', 161, '21:00:00', '22:00:00', NULL, '{"fysiek": {"kracht": "7", "mobiliteit": "6", "opmerking": "", "snelheid": "7", "uithouding": "7"}, "mentaal": {"focus": "8", "inzet": "8", "opmerking": "", "sportiviteit": "7", "veerkracht": "6"}, "tactiek": {"keuze_slagen": "5", "netspel": "7", "opmerking": "", "positiespel": "5", "samenwerking": "7", "verdediging": "7"}, "techniek": {"backhand": "7", "bandeja": "7", "forehand": "7", "opmerking": "goed zo!", "service": "7", "smash": "6", "volley": "3"}}', NULL, NULL),
(65, 60, 4, '2025-03-11', 163, '14:00:00', '15:00:00', NULL, '{"fysiek": {"kracht": "8", "mobiliteit": "3", "opmerking": "", "snelheid": "7", "uithouding": "8"}, "mentaal": {"focus": "8", "inzet": "3", "opmerking": "super\r\n", "sportiviteit": "3", "veerkracht": "7"}, "tactiek": {"keuze_slagen": "4", "netspel": "8", "opmerking": "", "positiespel": "3", "samenwerking": "7", "verdediging": "4"}, "techniek": {"backhand": "8", "bandeja": "8", "forehand": "8", "opmerking": "goed!\r\n", "service": "8", "smash": "2", "volley": "7"}}', NULL, NULL),
(66, 66, 4, '2025-03-11', 163, '14:00:00', '15:00:00', NULL, NULL, NULL, NULL),
(67, 1, 4, '2025-03-11', 163, '14:00:00', '15:00:00', NULL, NULL, NULL, NULL),
(68, 55, 7, '2025-12-15', 138, '10:00:00', '11:00:00', NULL, NULL, NULL, NULL),
(69, 56, 5, '2025-12-15', 140, '12:00:00', '13:00:00', NULL, NULL, NULL, NULL),
(70, 19, 9, '2025-12-15', 75, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(71, 8, 9, '2025-12-15', 75, '18:00:00', '19:00:00', NULL, NULL, NULL, NULL),
(72, 1, 31, '2025-12-13', 168, '15:00:00', '16:00:00', NULL, '{"fysiek": {"kracht": "7", "mobiliteit": "9", "opmerking": "", "snelheid": "8", "uithouding": "7"}, "mentaal": {"focus": "7", "inzet": "7", "opmerking": "", "sportiviteit": "8", "veerkracht": "3"}, "tactiek": {"keuze_slagen": "7", "netspel": "7", "opmerking": "", "positiespel": "7", "samenwerking": "8", "verdediging": "8"}, "techniek": {"backhand": "7", "bandeja": "7", "forehand": "7", "opmerking": "Oefenen op volley", "service": "8", "smash": "8", "volley": "3"}}', NULL, NULL),
(73, 20, 9, '2025-12-18', 144, '13:00:00', '14:00:00', NULL, NULL, NULL, NULL),
(74, 30, 9, '2025-12-17', 60, '13:00:00', '14:00:00', NULL, NULL, NULL, NULL),
(75, 30, 9, '2025-12-17', 61, '14:00:00', '15:00:00', NULL, NULL, NULL, NULL),
(76, 19, 9, '2025-12-19', 30, '09:00:00', '10:00:00', NULL, NULL, NULL, NULL),
(77, 65, 9, '2025-12-18', 145, '17:00:00', '18:00:00', NULL, NULL, NULL, NULL);
INSERT INTO "public"."coach_players" ("coach_id", "player_id", "created_at") VALUES
(4, 8, '2025-12-09 21:15:42.91995+00'),
(4, 9, '2025-12-09 21:15:42.91995+00'),
(4, 12, '2025-12-09 21:15:42.91995+00'),
(4, 20, '2025-12-14 20:24:23.065746+00'),
(4, 24, '2025-12-09 21:15:42.91995+00'),
(4, 25, '2025-12-09 21:15:42.91995+00'),
(4, 26, '2025-12-09 21:15:42.91995+00'),
(4, 52, '2025-12-12 21:07:16.427302+00'),
(4, 66, '2025-12-14 21:07:50.064584+00'),
(5, 1, '2025-12-13 11:01:49.950753+00'),
(5, 3, '2025-12-10 09:40:17.901211+00'),
(5, 8, '2025-12-14 22:10:24.864424+00'),
(5, 10, '2025-12-09 21:15:42.91995+00'),
(5, 17, '2025-12-14 16:55:21.502942+00'),
(5, 19, '2025-12-14 17:23:09.413263+00'),
(5, 27, '2025-12-14 16:55:17.597533+00'),
(5, 39, '2025-12-09 21:15:42.91995+00'),
(5, 42, '2025-12-09 21:15:42.91995+00'),
(5, 43, '2025-12-14 16:55:25.190946+00'),
(5, 47, '2025-12-14 11:30:09.869111+00'),
(5, 56, '2025-12-13 11:07:12.34688+00'),
(5, 65, '2025-12-15 13:49:08.323665+00'),
(5, 66, '2025-12-14 22:13:38.649978+00'),
(7, 1, '2025-12-09 22:53:01.577246+00'),
(7, 2, '2025-12-09 21:15:42.91995+00'),
(7, 3, '2025-12-09 21:15:42.91995+00'),
(7, 4, '2025-12-09 21:15:42.91995+00'),
(7, 5, '2025-12-09 21:15:42.91995+00'),
(7, 7, '2025-12-09 21:15:42.91995+00'),
(7, 11, '2025-12-09 21:15:42.91995+00'),
(7, 14, '2025-12-09 21:15:42.91995+00'),
(7, 15, '2025-12-09 21:15:42.91995+00'),
(7, 16, '2025-12-09 21:15:42.91995+00'),
(7, 18, '2025-12-09 21:15:42.91995+00'),
(7, 20, '2025-12-09 22:52:59.533398+00'),
(7, 21, '2025-12-09 21:15:42.91995+00'),
(7, 22, '2025-12-09 21:15:42.91995+00'),
(7, 28, '2025-12-09 21:15:42.91995+00'),
(7, 29, '2025-12-09 21:15:42.91995+00'),
(7, 32, '2025-12-09 21:15:42.91995+00'),
(7, 33, '2025-12-09 21:15:42.91995+00'),
(7, 34, '2025-12-09 21:15:42.91995+00'),
(7, 35, '2025-12-09 21:15:42.91995+00'),
(7, 36, '2025-12-09 21:15:42.91995+00'),
(7, 37, '2025-12-09 21:15:42.91995+00'),
(7, 38, '2025-12-09 21:15:42.91995+00'),
(7, 44, '2025-12-09 21:15:42.91995+00'),
(7, 55, '2025-12-13 10:53:28.61515+00'),
(9, 1, '2025-12-11 16:41:53.36979+00'),
(9, 5, '2025-12-09 23:33:50.769993+00'),
(9, 8, '2025-12-14 22:05:51.838196+00'),
(9, 10, '2025-12-10 09:42:36.776026+00'),
(9, 19, '2025-12-09 21:15:42.91995+00'),
(9, 20, '2025-12-10 09:39:54.463973+00'),
(9, 27, '2025-12-09 21:15:42.91995+00'),
(9, 30, '2025-12-09 21:15:42.91995+00'),
(9, 33, '2025-12-11 16:41:47.000949+00'),
(9, 43, '2025-12-14 19:29:33.806934+00'),
(9, 52, '2025-12-12 21:16:42.397842+00'),
(9, 59, '2025-12-14 22:08:27.009883+00'),
(9, 60, '2025-12-14 16:57:57.546601+00'),
(9, 61, '2025-12-14 09:09:19.89369+00'),
(9, 65, '2025-12-14 13:32:33.836637+00'),
(9, 66, '2025-12-14 21:43:56.693784+00'),
(9, 67, '2025-12-14 23:23:46.371137+00'),
(9, 70, '2025-12-15 13:30:02.954167+00'),
(9, 71, '2025-12-15 13:44:21.619052+00'),
(10, 20, '2025-12-09 21:15:42.91995+00'),
(14, 1, '2025-12-09 21:15:42.91995+00'),
(14, 43, '2025-12-09 21:15:42.91995+00'),
(14, 47, '2025-12-10 20:59:43.411044+00'),
(14, 48, '2025-12-10 20:59:41.138183+00'),
(15, 5, '2025-12-09 23:30:17.985488+00'),
(15, 17, '2025-12-09 21:15:42.91995+00'),
(16, 31, '2025-12-09 21:15:42.91995+00'),
(16, 48, '2025-12-10 21:00:06.224417+00'),
(17, 40, '2025-12-09 21:15:42.91995+00'),
(17, 41, '2025-12-09 21:15:42.91995+00'),
(21, 52, '2025-12-12 20:44:56.252281+00'),
(25, 47, '2025-12-14 17:41:55.264932+00'),
(26, 1, '2025-12-14 21:13:41.181228+00'),
(26, 8, '2025-12-14 22:05:04.318301+00'),
(26, 60, '2025-12-14 23:36:36.910323+00'),
(26, 66, '2025-12-14 21:05:29.132894+00'),
(27, 67, '2025-12-14 23:18:43.78353+00'),
(31, 1, '2025-12-16 22:00:29.80442+00'),
(31, 3, '2025-12-16 22:01:14.522604+00'),
(31, 20, '2025-12-16 22:01:03.129173+00'),
(31, 77, '2025-12-16 22:45:39.31749+00');
INSERT INTO "public"."group_lesson_requests" ("request_id", "player_id", "date", "time", "created_at", "lesson_focus", "coach_id") VALUES
(3, 1, '2026-02-19', '15:00:00', '15:38:32.665366', NULL, NULL),
(5, 8, '2026-02-19', '14:00:00', '15:48:47.889524', NULL, NULL),
(15, 8, '2026-05-05', '18:00:00', '16:51:59.948823', NULL, NULL),
(16, 8, '2025-12-15', '18:00:00', '17:00:11.093267', 'volleys', NULL),
(17, 20, '2025-12-15', '18:00:00', '17:06:24.008933', 'volleys', NULL),
(18, 19, '2025-12-15', '18:00:00', '17:07:00.812551', 'volleys', NULL),
(19, 20, '2026-04-04', '19:00:00', '17:11:26.116538', 'volleys', NULL),
(20, 8, '2026-04-04', '19:00:00', '17:11:50.203788', 'volleys', NULL),
(21, 19, '2026-04-04', '19:00:00', '17:13:04.594669', 'volleys', NULL),
(22, 19, '2026-10-06', '19:00:00', '17:26:48.191217', 'bandeja_vibora', NULL),
(23, 20, '2026-10-06', '19:00:00', '17:27:23.122144', 'bandeja_vibora', NULL),
(26, 19, '2026-10-07', '19:00:00', '17:34:44.480836', 'bandeja_vibora', NULL),
(28, 20, '2025-12-17', '20:00:00', '17:43:11.099964', 'volleys', NULL),
(29, 20, '2026-10-10', '19:00:00', '19:37:16.945398', 'bandeja_vibora', NULL),
(30, 8, '2026-10-10', '18:00:00', '19:47:04.259507', 'bandeja_vibora', 9),
(33, 19, '2026-10-10', '19:00:00', '19:49:07.789088', 'bandeja_vibora', 9),
(37, 19, '2026-01-01', '17:00:00', '20:07:29.191839', 'volleys', 16),
(38, 1, '2026-01-01', '17:00:00', '20:08:09.427298', 'bandeja_vibora', 16),
(42, 19, '2026-12-20', '11:00:00', '20:27:16.633801', 'bandeja_vibora', 14),
(43, 1, '2026-12-20', '11:00:00', '20:27:58.274118', 'volleys', 14),
(45, 20, '2026-12-20', '19:00:00', '20:33:33.849345', 'tactics', 14),
(46, 20, '2026-12-20', '19:00:00', '20:38:17.228789', 'bandeja_vibora', 14),
(49, 19, '2025-12-12', '13:00:00', '20:48:25.50988', 'tactics', 1),
(51, 3, '2025-12-28', '09:00:00', '08:39:00.239966', 'tactics', 1),
(52, 19, '2025-12-28', '09:00:00', '08:39:50.090889', 'tactics', 1),
(53, 40, '2025-12-28', '09:00:00', '08:40:37.235461', 'tactics', 1),
(58, 10, '2025-12-28', '11:00:00', '08:59:38.349431', 'tactics', 1),
(61, 10, '2025-12-12', '10:00:00', '09:50:01.770465', 'volleys', 5),
(62, 3, '2025-12-28', '18:00:00', '09:54:52.332749', 'tactics', 2),
(63, 10, '2025-12-28', '18:00:00', '13:07:10.191472', 'tactics', 7),
(64, 10, '2025-12-28', '16:00:00', '13:24:58.306249', 'tactics', 5),
(65, 5, '2025-12-11', '17:00:00', '23:12:02.579132', 'volleys', 6),
(67, 2, '2025-12-28', '18:00:00', '08:56:54.030354', 'tactics', 7),
(68, 9, '2025-12-28', '17:00:00', '08:58:30.482044', 'tactics', 5),
(69, 9, '2025-12-28', '18:00:00', '08:59:03.651276', 'tactics', 5),
(70, 9, '2025-12-28', '20:00:00', '09:00:11.387427', 'tactics', 5),
(71, 9, '2025-12-28', '18:00:00', '09:00:37.89525', 'tactics', 5),
(74, 47, '2025-12-12', '10:00:00', '09:15:42.049216', 'tactics', 5),
(75, 3, '2025-12-28', '09:00:00', '09:23:20.952506', 'tactics', 7),
(76, 16, '2025-12-28', '12:00:00', '09:33:12.650178', 'tactics', 7),
(77, 47, '2025-12-28', '09:00:00', '09:42:45.286569', 'tactics', 5),
(81, 20, '2025-12-12', '12:00:00', '12:38:20.805017', 'bandeja_vibora', 5),
(84, 19, '2025-12-28', '14:00:00', '21:05:19.466328', 'tactics', 9),
(86, 3, '2025-12-28', '15:00:00', '17:18:47.731525', 'tactics', 5),
(87, 47, '2025-12-12', '10:00:00', '13:49:52.395807', 'tactics', 5),
(99, 19, '2026-01-03', '14:00:00', '08:28:18.8335', 'bandeja_vibora', 5),
(101, 55, '2025-12-15', '17:00:00', '10:55:18.191656', 'tactics', 5),
(102, 56, '2025-12-15', '13:00:00', '11:13:11.522532', 'tactics', 7),
(103, 20, '2025-12-28', '16:00:00', '14:19:14.900674', 'tactics', 5),
(104, 8, '2025-12-28', '16:00:00', '21:29:19.933691', 'bandeja_vibora', 9),
(105, 20, '2025-12-18', '17:00:00', '12:59:33.934349', 'bandeja_vibora', 9),
(106, 1, '2025-12-19', '20:00:00', '14:01:08.280879', 'Forehand', 5),
(107, 1, '2025-12-19', '18:00:00', '14:05:27.679277', 'Techniek (Algemeen)', 5),
(108, 1, '2025-12-19', '20:00:00', '14:14:58.406139', 'Forehand', 5),
(109, 1, '2025-12-19', '19:00:00', '16:54:14.088065', 'Tactiek & Positiespel', 5),
(110, 1, '2025-12-28', '18:00:00', '17:15:35.119321', 'Smash / Bandeja', 5),
(111, 20, '2025-12-28', '18:00:00', '17:32:58.779979', 'Smash / Bandeja', 9),
(112, 20, '2025-12-28', '17:00:00', '20:55:42.516003', 'Conditie / Fysiek', 7),
(113, 20, '2025-12-28', '17:00:00', '20:59:50.937872', 'Conditie / Fysiek', 7),
(116, 19, '2025-10-10', '10:00:00', '21:11:52.35994', 'Wedstrijdvorm', 26),
(118, 66, '2026-03-27', '21:00:00', '22:31:45.726338', 'Wedstrijdvorm', 5),
(121, 19, '2026-03-11', '14:00:00', '23:29:00.364144', 'Backhand', 27),
(123, 19, '2025-03-11', '14:00:00', '23:31:34.475094', 'Forehand', 9),
(126, 20, '2025-03-11', '14:00:00', '23:33:42.477326', 'Forehand', 9),
(128, 70, '2026-01-28', '09:00:00', '13:34:03.405313', 'Backhand', 28),
(129, 3, '2026-01-30', '10:00:00', '22:09:14.058888', 'Backhand', 31),
(130, 1, '2026-01-30', '10:00:00', '22:10:12.707156', 'Backhand', 31),
(131, 20, '2026-01-30', '10:00:00', '22:10:45.53283', 'Backhand', 31),
(132, 57, '2026-01-30', '10:00:00', '22:13:19.942271', 'Backhand', 31);
INSERT INTO "public"."players" ("player_id", "first_name", "last_name", "email", "phone", "hand_preference", "ranking", "created_at", "gender", "strengths", "weaknesses", "profile_image", "date_of_birth", "lesson_type_preference", "playing_intensity") VALUES
(1, 'Thomas', 'Speler', 'speler@thomas.be', '0499123456', NULL, 'P100', '2025-11-25 11:28:45.631272+00', 'man', 'forehand', 'backhand', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/speler_thomas_be_1765572911.jpg', NULL, 'group', 'recreational'),
(2, 'Karel', 'Van Den Bogaert', 'maxym@coach.be', '123123', NULL, 'P700', '2025-11-25 11:45:55.102717+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(3, 'Tiebe', 'Roggeman', 'tiebe.roggeman@icloud.com', '+32 490 86 35 57', NULL, 'P1000', '2025-11-25 14:14:41.277792+00', 'man', 'smash', 'geen', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_3_1765268041.png', NULL, 'individual', 'competitive'),
(4, 'jo', 'tt', 'jo@tt.be', '123', NULL, NULL, '2025-11-26 09:37:19.224254+00', 'anders', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(5, 'Karel', 'Peeters', 'karel.peeters@gmail.com', '112', 'Rechts', 'P300', '2025-11-26 10:39:35.239979+00', 'man', 'netballen', 'rebound - glass ', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_5_1765320974.jpg', NULL, 'group', 'competitive'),
(7, 'rr', 'tt', 'rr.tt@gmail.com', '123', NULL, NULL, '2025-11-26 11:06:08.61016+00', NULL, NULL, NULL, NULL, NULL, 'group', 'competitive'),
(8, 'Jan', 'Janssens', 'j.j@gmail.com', '045', 'Rechts', 'P100', '2025-11-27 21:05:41.479261+00', 'man', 'conditie', 'backhands', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_8_1765123338.jpg', NULL, 'group', 'recreational'),
(9, 'Geert', 'Janssens', 'geert.janssens@gmail.com', '047', 'Links', 'P100', '2025-11-29 11:40:51.573581+00', 'man', 'aa', 'bb', NULL, NULL, 'group', 'competitive'),
(10, 'Riete', 'De Rouck', 'riete@speler.be', '045', 'Rechts', 'P100', '2025-11-29 14:56:22.081093+00', 'vrouw', 'forehand', 'backhand', NULL, NULL, 'individual', 'recreational'),
(11, 'Henri', 'Baeten', 'henri.baeten@gmail.com', '0474 67 65 54', 'Rechts', 'P300', '2025-11-29 19:53:16.718044+00', 'man', 'forehand', 'serve ', NULL, NULL, 'group', 'competitive'),
(12, 'June', 'Meert', 'june.meert@gmail.com', '0489754212', 'Rechts', 'P100', '2025-11-30 18:51:17.637661+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(14, 'Jan', 'Paternoster', 'Jan@paternoster.be', '4878286', 'Links', 'P200', '2025-12-02 22:34:24.519114+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(15, 'Na', 'overzetcoach', 'na.overzet@coach.be', '0477889966', 'Links', 'P400', '2025-12-03 14:13:35.840556+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(16, 'coach', 'nieuw', 'coach@nieuw.be', '0478996655', 'Beide', 'P300', '2025-12-03 14:33:00.36921+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(17, 'aa', 'bb', 'aa@bb.be', '0477889966', 'links', 'P400', '2025-12-03 14:42:18.433499+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(18, 'bb', 'aa', 'bb@aa.be', '0456093240', 'links', 'P700', '2025-12-03 14:43:17.024237+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(19, 'Dries', 'Mertens', 'dries.mertens@padel.be', '047315', 'Links', 'P1000', '2025-12-03 17:00:44.272349+00', 'man', 'Slag', 'Snelheid', NULL, NULL, 'group', 'recreational'),
(20, 'Kevin ', 'De Bruyne', 'kevin.db@padel.com', '0473121450', 'Links', 'P200', '2025-12-03 19:15:35.59613+00', 'man', 'opslag', '', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_20_1765114437.webp', NULL, 'group', 'recreational'),
(21, 'Tim', 'peeters ', 'tim.peeters@gmail.com', '0456 56 67 67', 'Rechts', 'P400', '2025-12-04 11:00:33.010258+00', 'man', 'forehand', 'backhand ', NULL, NULL, 'group', 'competitive'),
(22, 'Tom', 'pieters', 'tom.pieters@gmail.com', '046999', 'Rechts', 'P300', '2025-12-04 12:05:00.490367+00', 'man', 'forehand', 'backhand', NULL, NULL, 'group', 'competitive'),
(23, 'Hallo', 'Test', 'hallo.test@gmail.com', '0473313689', 'links', 'P100', '2025-12-05 20:50:47.018425+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(24, 'Xavier', 'ww', 'xavier.ww@gmail.com', '0478954512', 'beide', 'P200', '2025-12-05 21:16:57.725421+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(25, 'Rik', 'cc', 'rik.c@padel.be', '0473313688', 'links', 'Geen', '2025-12-06 08:58:33.99321+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(26, 'Nathan', 'aa', 'nathan.aa@padel.be', '0473313675', 'links', 'P100', '2025-12-06 09:48:56.416143+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(27, 'Alex', 'Carlier', 'alex.carlier@padel.be', '0473313682', 'links', 'P100', '2025-12-06 17:29:12.143173+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(28, 'Aa11', 'Be11', 'aa.be@padel.be', '0473313689', 'rechts', 'P100', '2025-12-06 17:39:03.395501+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(29, 'Test1a', 'Hallo', 'max@speler.be', '0475584987', 'rechts', 'P50', '2025-12-06 17:45:11.651693+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(30, 'Thomas ', 'Meunier', 'thomas.meunier@padel.be', '0473313689', 'rechts', 'P200', '2025-12-06 17:56:54.503074+00', 'man', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(31, 'Lionel J.', 'Messi', 'lionel.messi@padel', '0489754212', 'links', 'P200', '2025-12-07 11:22:26.996239+00', 'man', 'snelheid', '', NULL, '1985-05-07', 'group', 'competitive'),
(32, 'Wout', 'Faes', 'wout.faes@padel.be', '0473313658', 'links', 'P100', '2025-12-07 11:57:36.120906+00', 'man', NULL, NULL, NULL, '1999-12-07', 'group', 'competitive'),
(33, 'Thomas', 'Carlier', 'thomas.carlier@padel.be', '0478451262', 'links', 'P200', '2025-12-07 13:03:33.73802+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_33_1765114318.JPG', '2000-12-12', 'group', 'competitive'),
(34, 'Fernand', 'dd', 'fernand@padel.be', '0447154545', 'links', 'P100', '2025-12-07 16:21:04.46087+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/fernand_padel_be_1765124457.jpg', '2004-10-19', 'group', 'competitive'),
(35, 'guy', 'vdb', 'guy@vdb.be', '0455663322', 'beide', 'P300', '2025-12-08 08:42:27.65426+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/guy_vdb_be_1765183345.jpg', '1745-05-04', 'group', 'competitive'),
(36, 'jan', 'piet', 'janpiet@gmail.com', '0471', 'Links', 'P200', '2025-12-08 08:59:18.440512+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(37, 'dqmf', 'mjdf', 'mdjfq@mfdqjk.be', '0477889965', 'links', 'P400', '2025-12-08 09:18:49.091558+00', 'vrouw', NULL, NULL, NULL, '1456-12-25', 'group', 'competitive'),
(38, 'riete', 'dr', 'riete@speler.com', '0456443223', 'rechts', 'P500', '2025-12-08 09:53:12.986797+00', 'vrouw', NULL, NULL, NULL, NULL, 'group', 'competitive'),
(39, 'test', 'test', 'test@test.nbe', '0434567890', 'beide', 'P200', '2025-12-08 10:28:54.002186+00', 'vrouw', NULL, NULL, NULL, '2025-12-19', 'group', 'competitive'),
(40, 'fernando', 'sucre', 'fernando@gmail.com', '0471123460', 'links', 'P1000', '2025-12-08 11:47:55.523525+00', 'vrouw', 'communicatie', 'minder zagen', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/fernando_gmail_com_1765194471.png', '1478-02-22', 'individual', 'competitive'),
(41, 'Jasper', 'De Rouck', 'jasper@speler.com', '0467263774', 'beide', 'P300', '2025-12-08 13:29:58.37644+00', 'man', NULL, NULL, NULL, '2006-10-16', 'individual', 'competitive'),
(42, 'steven', 'penne', 'steven@speler.be', '0453857462', 'beide', 'P400', '2025-12-08 13:32:05.542629+00', 'man', NULL, NULL, NULL, '2001-11-23', 'group', 'recreational'),
(43, 'Andreas', 'Janssens', 'andreas.janssens@gmail.com', '0489754212', 'rechts', 'P100', '2025-12-08 14:37:21.969852+00', 'man', 'Snelheid', 'Opslag', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/andreas_janssens_gmail_com_1765204640.webp', '2000-10-10', 'group', 'competitive'),
(44, 'Jef', 'Maartens', 'jef.maartens@padel.be', '0473313656', 'rechts', 'P100', '2025-12-08 19:25:59.771467+00', 'man', NULL, NULL, NULL, '2001-10-10', 'group', 'recreational'),
(46, 'maurits', 'ampe', 'mampe@gmail.com', '0477699873', 'links', 'P50', '2025-12-10 08:47:50.37158+00', 'man', NULL, NULL, NULL, '2005-02-22', 'group', 'competitive'),
(47, '11', '22', '12@gmail.com', '0471123499', 'links', 'P200', '2025-12-10 08:52:53.16874+00', 'vrouw', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_47_1765558064.png', '1988-02-22', 'group', 'competitive'),
(48, 'Vince', 'Claessens', 'vince.claessens@padel.be', '0473313689', 'rechts', 'P200', '2025-12-10 20:56:12.076854+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/vince_claessens_padel_be_1765400169.webp', '2000-10-10', 'group', 'recreational'),
(49, 'Jan', 'De Man', 'jan.deman@padel.be', '0473136584', 'links', 'P200', '2025-12-11 17:43:54.097037+00', 'man', NULL, NULL, NULL, '2000-10-10', 'group', 'recreational'),
(50, 'axel', 'bat', 'axel@padel.be', '0455662233', 'rechts', 'P200', '2025-12-11 17:52:10.145909+00', 'anders', NULL, NULL, NULL, '2000-12-25', 'group', 'recreational'),
(51, 'Laurine', 'Tibrlo', 'laurinelovehorses@gmail.com', '0474525698', 'rechts', 'P100', '2025-12-11 19:51:05.214596+00', 'vrouw', NULL, NULL, NULL, '2004-11-03', 'individual', 'competitive'),
(52, 'Kato', 'Carlier', 'kato.carlier@padel.be', '0473313258', 'rechts', 'P300', '2025-12-12 19:48:26.882781+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_52_1765569764.jpg', '2000-10-10', 'individual', 'recreational'),
(53, 'Willy', 'Aa', 'willy@padel.be', '0478452157', 'links', 'P300', '2025-12-12 19:59:23.321877+00', 'man', NULL, NULL, NULL, '2000-12-20', 'group', 'recreational'),
(54, 'Erika', 'Ta', 'erika@padel.be', '0473312548', 'links', 'P100', '2025-12-12 20:05:42.508964+00', 'vrouw', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/erika_padel_be_1765569940.jpg', '2000-12-12', 'group', 'recreational'),
(55, 'lisa', 'deman', 'lisa@deman.be', '0495565434', 'rechts', 'P100', '2025-12-13 10:52:22.069423+00', 'vrouw', NULL, NULL, NULL, '2003-12-21', 'group', 'recreational'),
(56, 'lisa', 'deroo', 'lisa.deroo@gmail.com', '0456655678', 'rechts', 'P100', '2025-12-13 11:05:22.504393+00', 'vrouw', NULL, NULL, NULL, '2003-12-13', 'group', 'recreational'),
(57, 'Thomas', 'Carlier', 'thomas.carlier@telenet.be', '0473313654', 'rechts', 'P200', '2025-12-13 21:21:11.845496+00', 'man', NULL, NULL, NULL, '2004-10-19', 'individual', 'recreational'),
(58, 'Fille', 'Janssens', 'fjan@gmail.com', '0458639824', 'links', 'P50', '2025-12-13 21:25:53.349684+00', 'anders', NULL, NULL, NULL, '2006-11-13', 'individual', 'competitive'),
(59, 'Bruce', 'Vandijk', 'bruce.vandijk@padel.com', '0479314525', 'links', 'P100', '2025-12-13 21:39:49.610202+00', 'man', NULL, NULL, NULL, '2003-12-26', 'group', 'recreational'),
(60, 'Arne', 'Beeckmans', 'Arne.beeckmans@gmail.com', '0478496090', 'links', 'P200', '2025-12-13 21:57:55.213808+00', 'man', NULL, NULL, NULL, '2004-04-08', 'group', 'recreational'),
(61, 'Laurence', 'Heeman', 'laurence.heeman@gmail.com', '0479447270', 'rechts', 'Geen', '2025-12-13 22:57:50.314624+00', 'vrouw', NULL, NULL, NULL, '1973-04-13', 'group', 'recreational'),
(62, 'tibo', 'bekaert', 'tibo@bekaert.be', '0411111122', 'rechts', 'P300', '2025-12-14 08:46:00.102882+00', 'man', NULL, NULL, NULL, '2007-03-18', 'individual', 'recreational'),
(63, 'jos', 'wemmels', 'jos@wemmels.be', '0455223311', 'links', 'P200', '2025-12-14 09:51:42.255001+00', 'man', NULL, NULL, NULL, '2005-05-12', 'individual', 'recreational'),
(64, 'Leen', 'Carlier', 'leencarlier@gmail.com', '0473372963', 'rechts', 'Geen', '2025-12-14 12:10:11.124485+00', 'vrouw', NULL, NULL, NULL, '1979-09-14', 'group', 'recreational'),
(65, 'Liv', 'Claessens', 'liv.claessens@gmail.com', '0456860887', 'rechts', 'P1000', '2025-12-14 13:31:24.324628+00', 'vrouw', NULL, NULL, '/static/1F95F7D0-80A0-4DDF-9BB5-7116BBBF961B.jpg', '2013-08-01', 'individual', 'recreational'),
(66, 'Ingrid ', 'Van Den Breen', 'ingrid.vdb@padel.be', '0473313648', 'links', 'P200', '2025-12-14 21:01:10.424877+00', 'vrouw', NULL, NULL, NULL, '1960-10-10', 'group', 'recreational'),
(67, 'Billy', 'Mertens', 'billy.mertens@gmail.com', '0478457541', 'rechts', 'P400', '2025-12-14 23:10:35.587143+00', 'vrouw', 'snelheid', 'opslag', '/static/KDB.webp', '2000-10-20', 'group', 'recreational'),
(68, 'Adriaan', 'Va', 'adriaan.v@padel.be', '0478546214', 'links', 'P300', '2025-12-14 23:16:11.278906+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/adriaan_v_padel_be_1765754168.jpg', '2000-10-10', 'group', 'recreational'),
(69, 'Test', 'Test', 'test.test@gmail.com', '0476215877', 'links', 'P300', '2025-12-14 23:46:12.212924+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/test_test_gmail_com_1765755969.png', '2000-10-10', 'group', 'recreational'),
(70, 'Thomas ', 'C', 'thomas.c@padel.be', '0476165618', 'links', 'P100', '2025-12-15 13:23:07.962144+00', 'man', NULL, NULL, '/static/IMG_2158.png', '2005-11-15', 'group', 'recreational'),
(71, 'Tim', 'Janssens', 'tim.janssens@padel.be', '0475125487', 'rechts', 'P200', '2025-12-15 13:42:45.865465+00', 'man', 'Snelheid ', 'Opslag', NULL, '1995-11-03', 'group', 'recreational'),
(72, 'Max', 'Zelensky', 'maxzel@hotmail.com', '0466789123', 'rechts', 'P50', '2025-12-15 16:51:18.955789+00', 'man', NULL, NULL, NULL, '1993-12-15', 'group', 'recreational'),
(73, 'Jef', 'Aa', 'jef.aa@padel.be', '0478153224', 'links', 'P200', '2025-12-16 11:29:27.197571+00', 'man', NULL, NULL, 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/players/jef_aa_padel_be_1765884563.jpg', '2000-10-20', 'group', 'recreational'),
(77, 'Jan', 'Verthongen', 'jan.verthongen@padel.be', '0478541254', 'rechts', 'P100', '2025-12-16 22:44:51.771865+00', 'man', 'Snelheid', 'Backhand', NULL, '1998-10-10', 'group', 'recreational');
INSERT INTO "public"."clubs" ("club_id", "club_name", "location", "contact_info", "sports_supported", "created_at", "updated_at") VALUES
(1, 'Fit Out Padel Destelbergen', 'Destelbergen', '{"email": "maxime_baetsle@hotmail.be"}', '["padel"]', '2025-11-12 17:32:00', '2025-11-12 16:33:53.935772');
INSERT INTO "public"."coach_availability" ("id", "created_at", "coach_id", "date", "start_time", "end_time") VALUES
(1, NULL, 4, '2026-07-06 00:00:00+00', '17:00:00', '18:00:00'),
(2, NULL, 4, '2026-07-06 00:00:00+00', '18:00:00', '19:00:00'),
(5, NULL, 10, '2025-12-08 00:00:00+00', '17:00:00', '18:00:00'),
(6, NULL, 10, '2025-12-08 00:00:00+00', '18:00:00', '19:00:00'),
(7, NULL, 10, '2025-12-09 00:00:00+00', '14:00:00', '15:00:00'),
(8, NULL, 10, '2025-12-09 00:00:00+00', '15:00:00', '16:00:00'),
(9, NULL, 3, '2025-12-26 00:00:00+00', '11:00:00', '12:00:00'),
(10, NULL, 9, '2025-12-12 00:00:00+00', '10:00:00', '11:00:00'),
(12, NULL, 9, '2025-12-12 00:00:00+00', '11:00:00', '12:00:00'),
(13, NULL, 9, '2025-12-13 00:00:00+00', '11:00:00', '12:00:00'),
(24, NULL, 9, '2025-12-17 00:00:00+00', '15:00:00', '16:00:00'),
(34, NULL, 15, '2025-12-20 00:00:00+00', '11:00:00', '12:00:00'),
(35, NULL, 15, '2025-12-20 00:00:00+00', '12:00:00', '13:00:00'),
(39, NULL, 16, '2025-12-12 00:00:00+00', '11:00:00', '12:00:00'),
(40, NULL, 14, '2025-12-18 00:00:00+00', '18:00:00', '19:00:00'),
(41, NULL, 14, '2025-12-18 00:00:00+00', '19:00:00', '20:00:00'),
(42, NULL, 14, '2025-12-19 00:00:00+00', '18:00:00', '19:00:00'),
(64, NULL, 1, '2025-12-09 00:00:00+00', '16:00:00', '17:00:00'),
(65, NULL, 1, '2025-12-09 00:00:00+00', '17:00:00', '18:00:00'),
(67, NULL, 1, '2025-12-09 00:00:00+00', '19:00:00', '20:00:00'),
(68, NULL, 1, '2025-12-09 00:00:00+00', '20:00:00', '21:00:00'),
(69, NULL, 1, '2025-12-09 00:00:00+00', '21:00:00', '22:00:00'),
(70, NULL, 14, '2025-12-20 00:00:00+00', '13:00:00', '14:00:00'),
(71, NULL, 14, '2025-12-20 00:00:00+00', '15:00:00', '16:00:00'),
(72, NULL, 14, '2025-12-20 00:00:00+00', '16:00:00', '17:00:00'),
(73, NULL, 14, '2025-12-20 00:00:00+00', '17:00:00', '18:00:00'),
(81, NULL, 5, '2025-12-09 00:00:00+00', '09:00:00', '10:00:00'),
(82, NULL, 5, '2025-12-09 00:00:00+00', '10:00:00', '11:00:00'),
(83, NULL, 5, '2025-12-09 00:00:00+00', '11:00:00', '12:00:00'),
(84, NULL, 5, '2025-12-09 00:00:00+00', '12:00:00', '13:00:00'),
(85, NULL, 5, '2025-12-09 00:00:00+00', '13:00:00', '14:00:00'),
(86, NULL, 5, '2025-12-09 00:00:00+00', '14:00:00', '15:00:00'),
(87, NULL, 5, '2025-12-09 00:00:00+00', '15:00:00', '16:00:00'),
(92, NULL, 17, '2025-12-08 00:00:00+00', '16:00:00', '17:00:00'),
(93, NULL, 17, '2025-12-08 00:00:00+00', '17:00:00', '18:00:00'),
(98, NULL, 1, '2025-12-28 00:00:00+00', '12:00:00', '13:00:00'),
(100, NULL, 1, '2025-12-28 00:00:00+00', '14:00:00', '15:00:00'),
(101, NULL, 1, '2025-12-28 00:00:00+00', '15:00:00', '16:00:00'),
(103, NULL, 1, '2025-12-28 00:00:00+00', '17:00:00', '18:00:00'),
(104, NULL, 1, '2025-12-28 00:00:00+00', '18:00:00', '19:00:00'),
(105, NULL, 1, '2025-12-28 00:00:00+00', '19:00:00', '20:00:00'),
(106, NULL, 1, '2025-12-28 00:00:00+00', '20:00:00', '21:00:00'),
(107, NULL, 1, '2025-12-28 00:00:00+00', '21:00:00', '22:00:00'),
(109, NULL, 14, '2025-12-26 00:00:00+00', '16:00:00', '17:00:00'),
(111, NULL, 9, '2026-10-10 00:00:00+00', '19:00:00', '20:00:00'),
(113, NULL, 16, '2026-01-01 00:00:00+00', '17:00:00', '18:00:00'),
(115, NULL, 14, '2026-12-20 00:00:00+00', '19:00:00', '20:00:00'),
(116, NULL, 14, '2026-12-20 00:00:00+00', '20:00:00', '21:00:00'),
(119, NULL, 1, '2026-01-25 00:00:00+00', '12:00:00', '13:00:00'),
(120, NULL, 2, '2025-12-28 00:00:00+00', '09:00:00', '10:00:00'),
(121, NULL, 2, '2025-12-28 00:00:00+00', '10:00:00', '11:00:00'),
(122, NULL, 2, '2025-12-28 00:00:00+00', '11:00:00', '12:00:00'),
(123, NULL, 2, '2025-12-28 00:00:00+00', '12:00:00', '13:00:00'),
(124, NULL, 2, '2025-12-28 00:00:00+00', '13:00:00', '14:00:00'),
(125, NULL, 2, '2025-12-28 00:00:00+00', '14:00:00', '15:00:00'),
(126, NULL, 2, '2025-12-28 00:00:00+00', '15:00:00', '16:00:00'),
(127, NULL, 2, '2025-12-28 00:00:00+00', '16:00:00', '17:00:00'),
(128, NULL, 2, '2025-12-28 00:00:00+00', '17:00:00', '18:00:00'),
(129, NULL, 2, '2025-12-28 00:00:00+00', '18:00:00', '19:00:00'),
(130, NULL, 2, '2025-12-28 00:00:00+00', '19:00:00', '20:00:00'),
(131, NULL, 2, '2025-12-28 00:00:00+00', '20:00:00', '21:00:00'),
(132, NULL, 2, '2025-12-28 00:00:00+00', '21:00:00', '22:00:00'),
(136, NULL, 5, '2025-12-12 00:00:00+00', '12:00:00', '13:00:00'),
(152, NULL, 7, '2025-12-28 00:00:00+00', '11:00:00', '12:00:00'),
(154, NULL, 7, '2025-12-28 00:00:00+00', '13:00:00', '14:00:00'),
(158, NULL, 7, '2025-12-28 00:00:00+00', '17:00:00', '18:00:00'),
(159, NULL, 7, '2025-12-28 00:00:00+00', '18:00:00', '19:00:00'),
(163, NULL, 1, '2025-12-28 00:00:00+00', '16:00:00', '17:00:00'),
(164, NULL, 1, '2025-12-28 00:00:00+00', '09:00:00', '10:00:00'),
(165, NULL, 1, '2025-12-28 00:00:00+00', '13:00:00', '14:00:00'),
(198, NULL, 7, '2025-12-28 00:00:00+00', '09:00:00', '10:00:00'),
(199, NULL, 1, '2025-12-09 00:00:00+00', '18:00:00', '19:00:00'),
(202, NULL, 17, '2025-12-10 00:00:00+00', '13:00:00', '14:00:00'),
(203, NULL, 7, '2025-12-12 00:00:00+00', '11:00:00', '12:00:00'),
(204, NULL, 7, '2025-12-12 00:00:00+00', '12:00:00', '13:00:00'),
(205, NULL, 7, '2025-12-12 00:00:00+00', '13:00:00', '14:00:00'),
(206, NULL, 7, '2025-12-12 00:00:00+00', '14:00:00', '15:00:00'),
(207, NULL, 7, '2025-12-12 00:00:00+00', '15:00:00', '16:00:00'),
(208, NULL, 7, '2025-12-12 00:00:00+00', '16:00:00', '17:00:00'),
(209, NULL, 7, '2025-12-12 00:00:00+00', '17:00:00', '18:00:00'),
(210, NULL, 6, '2025-12-11 00:00:00+00', '09:00:00', '10:00:00'),
(211, NULL, 6, '2025-12-11 00:00:00+00', '10:00:00', '11:00:00'),
(212, NULL, 6, '2025-12-11 00:00:00+00', '11:00:00', '12:00:00'),
(213, NULL, 6, '2025-12-11 00:00:00+00', '12:00:00', '13:00:00'),
(214, NULL, 6, '2025-12-11 00:00:00+00', '13:00:00', '14:00:00'),
(215, NULL, 6, '2025-12-11 00:00:00+00', '14:00:00', '15:00:00'),
(216, NULL, 6, '2025-12-11 00:00:00+00', '15:00:00', '16:00:00'),
(217, NULL, 6, '2025-12-11 00:00:00+00', '16:00:00', '17:00:00'),
(218, NULL, 6, '2025-12-11 00:00:00+00', '17:00:00', '18:00:00'),
(219, NULL, 6, '2025-12-11 00:00:00+00', '18:00:00', '19:00:00'),
(220, NULL, 6, '2025-12-11 00:00:00+00', '19:00:00', '20:00:00'),
(221, NULL, 6, '2025-12-11 00:00:00+00', '20:00:00', '21:00:00'),
(222, NULL, 6, '2025-12-11 00:00:00+00', '21:00:00', '22:00:00'),
(224, NULL, 13, '2025-12-11 00:00:00+00', '20:00:00', '21:00:00'),
(225, NULL, 13, '2025-12-11 00:00:00+00', '21:00:00', '22:00:00'),
(226, NULL, 17, '2025-12-11 00:00:00+00', '12:00:00', '13:00:00'),
(227, NULL, 17, '2025-12-11 00:00:00+00', '13:00:00', '14:00:00'),
(228, NULL, 17, '2025-12-11 00:00:00+00', '14:00:00', '15:00:00'),
(229, NULL, 17, '2025-12-11 00:00:00+00', '15:00:00', '16:00:00'),
(230, NULL, 17, '2025-12-11 00:00:00+00', '16:00:00', '17:00:00'),
(231, NULL, 5, '2025-12-12 00:00:00+00', '10:00:00', '11:00:00'),
(232, NULL, 7, '2025-12-11 00:00:00+00', '09:00:00', '10:00:00'),
(233, NULL, 7, '2025-12-11 00:00:00+00', '10:00:00', '11:00:00'),
(234, NULL, 7, '2025-12-11 00:00:00+00', '11:00:00', '12:00:00'),
(235, NULL, 7, '2025-12-11 00:00:00+00', '12:00:00', '13:00:00'),
(236, NULL, 7, '2025-12-11 00:00:00+00', '13:00:00', '14:00:00'),
(237, NULL, 7, '2025-12-11 00:00:00+00', '14:00:00', '15:00:00'),
(238, NULL, 7, '2025-12-11 00:00:00+00', '15:00:00', '16:00:00'),
(239, NULL, 7, '2025-12-11 00:00:00+00', '16:00:00', '17:00:00'),
(240, NULL, 7, '2025-12-11 00:00:00+00', '17:00:00', '18:00:00'),
(241, NULL, 7, '2025-12-11 00:00:00+00', '18:00:00', '19:00:00'),
(242, NULL, 7, '2025-12-11 00:00:00+00', '19:00:00', '20:00:00'),
(243, NULL, 7, '2025-12-11 00:00:00+00', '20:00:00', '21:00:00'),
(244, NULL, 7, '2025-12-11 00:00:00+00', '21:00:00', '22:00:00'),
(245, NULL, 5, '2025-12-12 00:00:00+00', '09:00:00', '10:00:00'),
(247, NULL, 7, '2025-12-08 00:00:00+00', '10:00:00', '11:00:00'),
(273, NULL, 5, '2025-12-28 00:00:00+00', '12:00:00', '13:00:00'),
(274, NULL, 5, '2025-12-28 00:00:00+00', '13:00:00', '14:00:00'),
(275, NULL, 5, '2025-12-28 00:00:00+00', '14:00:00', '15:00:00'),
(277, NULL, 5, '2025-12-28 00:00:00+00', '16:00:00', '17:00:00'),
(279, NULL, 5, '2025-12-28 00:00:00+00', '18:00:00', '19:00:00'),
(288, NULL, 21, '2025-12-13 00:00:00+00', '11:00:00', '12:00:00'),
(294, NULL, 9, '2025-12-29 00:00:00+00', '14:00:00', '15:00:00'),
(296, NULL, 5, '2025-12-29 00:00:00+00', '09:00:00', '10:00:00'),
(297, NULL, 5, '2025-12-29 00:00:00+00', '10:00:00', '11:00:00'),
(298, NULL, 5, '2025-12-29 00:00:00+00', '11:00:00', '12:00:00'),
(299, NULL, 5, '2025-12-29 00:00:00+00', '12:00:00', '13:00:00'),
(300, NULL, 5, '2025-12-29 00:00:00+00', '13:00:00', '14:00:00'),
(301, NULL, 5, '2025-12-29 00:00:00+00', '14:00:00', '15:00:00'),
(302, NULL, 5, '2025-12-29 00:00:00+00', '15:00:00', '16:00:00'),
(303, NULL, 5, '2025-12-29 00:00:00+00', '16:00:00', '17:00:00'),
(304, NULL, 5, '2025-12-29 00:00:00+00', '17:00:00', '18:00:00'),
(305, NULL, 5, '2025-12-29 00:00:00+00', '18:00:00', '19:00:00'),
(306, NULL, 5, '2025-12-29 00:00:00+00', '19:00:00', '20:00:00'),
(307, NULL, 5, '2025-12-29 00:00:00+00', '20:00:00', '21:00:00'),
(308, NULL, 5, '2025-12-29 00:00:00+00', '21:00:00', '22:00:00'),
(309, NULL, 9, '2025-12-30 00:00:00+00', '14:00:00', '15:00:00'),
(367, NULL, 7, '2025-12-15 00:00:00+00', '09:00:00', '10:00:00'),
(369, NULL, 7, '2025-12-15 00:00:00+00', '11:00:00', '12:00:00'),
(370, NULL, 7, '2025-12-15 00:00:00+00', '12:00:00', '13:00:00'),
(371, NULL, 7, '2025-12-15 00:00:00+00', '13:00:00', '14:00:00'),
(372, NULL, 7, '2025-12-15 00:00:00+00', '14:00:00', '15:00:00'),
(373, NULL, 7, '2025-12-15 00:00:00+00', '15:00:00', '16:00:00'),
(374, NULL, 7, '2025-12-15 00:00:00+00', '16:00:00', '17:00:00'),
(375, NULL, 7, '2025-12-15 00:00:00+00', '17:00:00', '18:00:00'),
(376, NULL, 7, '2025-12-15 00:00:00+00', '18:00:00', '19:00:00'),
(377, NULL, 7, '2025-12-15 00:00:00+00', '19:00:00', '20:00:00'),
(378, NULL, 7, '2025-12-15 00:00:00+00', '20:00:00', '21:00:00'),
(379, NULL, 7, '2025-12-15 00:00:00+00', '21:00:00', '22:00:00'),
(380, NULL, 5, '2025-12-13 00:00:00+00', '09:00:00', '10:00:00'),
(381, NULL, 5, '2025-12-13 00:00:00+00', '10:00:00', '11:00:00'),
(382, NULL, 5, '2025-12-13 00:00:00+00', '11:00:00', '12:00:00'),
(383, NULL, 5, '2025-12-13 00:00:00+00', '12:00:00', '13:00:00'),
(384, NULL, 5, '2025-12-13 00:00:00+00', '13:00:00', '14:00:00'),
(385, NULL, 5, '2025-12-13 00:00:00+00', '14:00:00', '15:00:00'),
(386, NULL, 5, '2025-12-13 00:00:00+00', '15:00:00', '16:00:00'),
(387, NULL, 5, '2025-12-13 00:00:00+00', '16:00:00', '17:00:00'),
(388, NULL, 5, '2025-12-13 00:00:00+00', '17:00:00', '18:00:00'),
(389, NULL, 5, '2025-12-13 00:00:00+00', '18:00:00', '19:00:00'),
(390, NULL, 5, '2025-12-13 00:00:00+00', '19:00:00', '20:00:00'),
(391, NULL, 5, '2025-12-13 00:00:00+00', '20:00:00', '21:00:00'),
(392, NULL, 5, '2025-12-13 00:00:00+00', '21:00:00', '22:00:00'),
(404, NULL, 7, '2025-12-21 00:00:00+00', '09:00:00', '10:00:00'),
(405, NULL, 7, '2025-12-21 00:00:00+00', '10:00:00', '11:00:00'),
(406, NULL, 7, '2025-12-21 00:00:00+00', '11:00:00', '12:00:00'),
(407, NULL, 7, '2025-12-21 00:00:00+00', '12:00:00', '13:00:00'),
(408, NULL, 7, '2025-12-21 00:00:00+00', '13:00:00', '14:00:00'),
(409, NULL, 7, '2025-12-21 00:00:00+00', '14:00:00', '15:00:00'),
(410, NULL, 7, '2025-12-21 00:00:00+00', '15:00:00', '16:00:00'),
(411, NULL, 7, '2025-12-21 00:00:00+00', '16:00:00', '17:00:00'),
(412, NULL, 7, '2025-12-21 00:00:00+00', '17:00:00', '18:00:00'),
(413, NULL, 7, '2025-12-21 00:00:00+00', '18:00:00', '19:00:00'),
(414, NULL, 7, '2025-12-21 00:00:00+00', '19:00:00', '20:00:00'),
(415, NULL, 7, '2025-12-21 00:00:00+00', '20:00:00', '21:00:00'),
(416, NULL, 7, '2025-12-21 00:00:00+00', '21:00:00', '22:00:00'),
(417, NULL, 9, '2025-12-31 00:00:00+00', '12:00:00', '13:00:00'),
(418, NULL, 5, '2025-12-25 00:00:00+00', '10:00:00', '11:00:00'),
(419, NULL, 5, '2025-12-25 00:00:00+00', '11:00:00', '12:00:00'),
(420, NULL, 5, '2025-12-25 00:00:00+00', '12:00:00', '13:00:00'),
(421, NULL, 5, '2025-12-25 00:00:00+00', '14:00:00', '15:00:00'),
(422, NULL, 5, '2025-12-25 00:00:00+00', '15:00:00', '16:00:00'),
(423, NULL, 5, '2025-12-25 00:00:00+00', '16:00:00', '17:00:00'),
(424, NULL, 5, '2025-12-25 00:00:00+00', '18:00:00', '19:00:00'),
(425, NULL, 5, '2025-12-25 00:00:00+00', '19:00:00', '20:00:00'),
(426, NULL, 5, '2025-12-25 00:00:00+00', '20:00:00', '21:00:00'),
(427, NULL, 5, '2025-12-15 00:00:00+00', '14:00:00', '15:00:00'),
(428, NULL, 5, '2025-12-15 00:00:00+00', '15:00:00', '16:00:00'),
(429, NULL, 5, '2025-12-15 00:00:00+00', '16:00:00', '17:00:00'),
(430, NULL, 5, '2025-12-15 00:00:00+00', '18:00:00', '19:00:00'),
(431, NULL, 5, '2025-12-15 00:00:00+00', '19:00:00', '20:00:00'),
(432, NULL, 5, '2025-12-15 00:00:00+00', '20:00:00', '21:00:00'),
(433, NULL, 5, '2030-12-31 00:00:00+00', '10:00:00', '11:00:00'),
(434, NULL, 5, '2030-12-31 00:00:00+00', '11:00:00', '12:00:00'),
(435, NULL, 5, '2030-12-31 00:00:00+00', '12:00:00', '13:00:00'),
(436, NULL, 5, '2030-12-31 00:00:00+00', '14:00:00', '15:00:00'),
(437, NULL, 5, '2030-12-31 00:00:00+00', '15:00:00', '16:00:00'),
(438, NULL, 5, '2030-12-31 00:00:00+00', '16:00:00', '17:00:00'),
(439, NULL, 5, '2030-12-31 00:00:00+00', '18:00:00', '19:00:00'),
(440, NULL, 5, '2030-12-31 00:00:00+00', '19:00:00', '20:00:00'),
(441, NULL, 5, '2030-12-31 00:00:00+00', '20:00:00', '21:00:00'),
(442, NULL, 9, '2025-12-18 00:00:00+00', '09:00:00', '10:00:00'),
(443, NULL, 9, '2025-12-18 00:00:00+00', '10:00:00', '11:00:00'),
(444, NULL, 9, '2025-12-18 00:00:00+00', '11:00:00', '12:00:00'),
(445, NULL, 9, '2025-12-18 00:00:00+00', '12:00:00', '13:00:00'),
(447, NULL, 9, '2025-12-18 00:00:00+00', '14:00:00', '15:00:00'),
(448, NULL, 9, '2025-12-18 00:00:00+00', '15:00:00', '16:00:00'),
(449, NULL, 9, '2025-12-18 00:00:00+00', '16:00:00', '17:00:00'),
(451, NULL, 9, '2025-12-18 00:00:00+00', '18:00:00', '19:00:00'),
(452, NULL, 9, '2025-12-18 00:00:00+00', '19:00:00', '20:00:00'),
(453, NULL, 9, '2025-12-18 00:00:00+00', '20:00:00', '21:00:00'),
(454, NULL, 9, '2025-12-18 00:00:00+00', '21:00:00', '22:00:00'),
(455, NULL, 5, '2025-12-19 00:00:00+00', '10:00:00', '11:00:00'),
(458, NULL, 5, '2025-12-19 00:00:00+00', '14:00:00', '15:00:00'),
(460, NULL, 5, '2025-12-19 00:00:00+00', '16:00:00', '17:00:00'),
(462, NULL, 5, '2025-12-19 00:00:00+00', '19:00:00', '20:00:00'),
(463, NULL, 5, '2025-12-19 00:00:00+00', '20:00:00', '21:00:00'),
(464, NULL, 9, '2026-05-14 00:00:00+00', '13:00:00', '14:00:00'),
(465, NULL, 5, '2026-05-14 00:00:00+00', '13:00:00', '14:00:00'),
(466, NULL, 17, '2025-12-15 00:00:00+00', '09:00:00', '10:00:00'),
(467, NULL, 17, '2025-12-15 00:00:00+00', '10:00:00', '11:00:00'),
(468, NULL, 17, '2025-12-15 00:00:00+00', '11:00:00', '12:00:00'),
(469, NULL, 17, '2025-12-15 00:00:00+00', '12:00:00', '13:00:00'),
(470, NULL, 17, '2025-12-15 00:00:00+00', '13:00:00', '14:00:00'),
(471, NULL, 17, '2025-12-15 00:00:00+00', '14:00:00', '15:00:00'),
(472, NULL, 17, '2025-12-15 00:00:00+00', '15:00:00', '16:00:00'),
(473, NULL, 17, '2025-12-15 00:00:00+00', '16:00:00', '17:00:00'),
(474, NULL, 17, '2025-12-15 00:00:00+00', '17:00:00', '18:00:00'),
(475, NULL, 17, '2025-12-15 00:00:00+00', '18:00:00', '19:00:00'),
(476, NULL, 17, '2025-12-15 00:00:00+00', '19:00:00', '20:00:00'),
(477, NULL, 17, '2025-12-15 00:00:00+00', '20:00:00', '21:00:00'),
(478, NULL, 17, '2025-12-15 00:00:00+00', '21:00:00', '22:00:00'),
(479, NULL, 17, '2025-12-14 00:00:00+00', '09:00:00', '10:00:00'),
(480, NULL, 17, '2025-12-14 00:00:00+00', '10:00:00', '11:00:00'),
(481, NULL, 17, '2025-12-14 00:00:00+00', '11:00:00', '12:00:00'),
(482, NULL, 17, '2025-12-14 00:00:00+00', '12:00:00', '13:00:00'),
(483, NULL, 17, '2025-12-14 00:00:00+00', '13:00:00', '14:00:00'),
(484, NULL, 17, '2025-12-14 00:00:00+00', '14:00:00', '15:00:00'),
(485, NULL, 17, '2025-12-14 00:00:00+00', '15:00:00', '16:00:00'),
(486, NULL, 17, '2025-12-14 00:00:00+00', '16:00:00', '17:00:00'),
(487, NULL, 17, '2025-12-14 00:00:00+00', '17:00:00', '18:00:00'),
(488, NULL, 17, '2025-12-14 00:00:00+00', '18:00:00', '19:00:00'),
(489, NULL, 17, '2025-12-14 00:00:00+00', '19:00:00', '20:00:00'),
(490, NULL, 17, '2025-12-14 00:00:00+00', '20:00:00', '21:00:00'),
(491, NULL, 17, '2025-12-14 00:00:00+00', '21:00:00', '22:00:00'),
(492, NULL, 5, '2025-12-20 00:00:00+00', '14:00:00', '15:00:00'),
(493, NULL, 5, '2025-12-20 00:00:00+00', '15:00:00', '16:00:00'),
(494, NULL, 5, '2025-12-20 00:00:00+00', '16:00:00', '17:00:00'),
(495, NULL, 5, '2025-12-20 00:00:00+00', '17:00:00', '18:00:00'),
(496, NULL, 5, '2025-12-20 00:00:00+00', '18:00:00', '19:00:00'),
(497, NULL, 5, '2025-12-20 00:00:00+00', '19:00:00', '20:00:00'),
(498, NULL, 5, '2025-12-20 00:00:00+00', '20:00:00', '21:00:00'),
(499, NULL, 5, '2025-12-20 00:00:00+00', '21:00:00', '22:00:00'),
(500, NULL, 25, '2025-12-20 00:00:00+00', '18:00:00', '19:00:00'),
(501, NULL, 9, '2025-12-25 00:00:00+00', '09:00:00', '10:00:00'),
(502, NULL, 9, '2025-12-25 00:00:00+00', '10:00:00', '11:00:00'),
(503, NULL, 9, '2025-12-25 00:00:00+00', '11:00:00', '12:00:00'),
(504, NULL, 9, '2025-12-25 00:00:00+00', '12:00:00', '13:00:00'),
(505, NULL, 9, '2025-12-25 00:00:00+00', '13:00:00', '14:00:00'),
(506, NULL, 9, '2025-12-25 00:00:00+00', '14:00:00', '15:00:00'),
(507, NULL, 9, '2025-12-25 00:00:00+00', '15:00:00', '16:00:00'),
(508, NULL, 9, '2025-12-25 00:00:00+00', '16:00:00', '17:00:00'),
(509, NULL, 9, '2025-12-25 00:00:00+00', '17:00:00', '18:00:00'),
(510, NULL, 9, '2025-12-25 00:00:00+00', '18:00:00', '19:00:00'),
(511, NULL, 9, '2025-12-25 00:00:00+00', '19:00:00', '20:00:00'),
(512, NULL, 9, '2025-12-25 00:00:00+00', '20:00:00', '21:00:00'),
(513, NULL, 9, '2025-12-25 00:00:00+00', '21:00:00', '22:00:00'),
(515, NULL, 9, '2027-12-28 00:00:00+00', '14:00:00', '15:00:00'),
(529, NULL, 9, '2025-12-28 00:00:00+00', '17:00:00', '18:00:00'),
(533, NULL, 9, '2025-12-15 00:00:00+00', '09:00:00', '10:00:00'),
(534, NULL, 9, '2025-12-15 00:00:00+00', '10:00:00', '11:00:00'),
(535, NULL, 9, '2025-12-15 00:00:00+00', '11:00:00', '12:00:00'),
(536, NULL, 9, '2025-12-15 00:00:00+00', '12:00:00', '13:00:00'),
(537, NULL, 9, '2025-12-15 00:00:00+00', '13:00:00', '14:00:00'),
(538, NULL, 9, '2025-12-15 00:00:00+00', '14:00:00', '15:00:00'),
(539, NULL, 9, '2025-12-15 00:00:00+00', '15:00:00', '16:00:00'),
(540, NULL, 9, '2025-12-15 00:00:00+00', '16:00:00', '17:00:00'),
(541, NULL, 9, '2025-12-15 00:00:00+00', '17:00:00', '18:00:00'),
(542, NULL, 9, '2025-12-15 00:00:00+00', '18:00:00', '19:00:00'),
(543, NULL, 9, '2025-12-15 00:00:00+00', '19:00:00', '20:00:00'),
(544, NULL, 9, '2025-12-15 00:00:00+00', '20:00:00', '21:00:00'),
(545, NULL, 9, '2025-12-15 00:00:00+00', '21:00:00', '22:00:00'),
(546, NULL, 9, '2026-02-25 00:00:00+00', '12:00:00', '13:00:00'),
(548, NULL, 9, '2026-03-26 00:00:00+00', '09:00:00', '10:00:00'),
(550, NULL, 9, '2026-03-27 00:00:00+00', '21:00:00', '22:00:00'),
(551, NULL, 5, '2026-03-27 00:00:00+00', '21:00:00', '22:00:00'),
(552, NULL, 27, '2026-03-11 00:00:00+00', '14:00:00', '15:00:00'),
(556, NULL, 9, '2025-03-11 00:00:00+00', '14:00:00', '15:00:00'),
(557, NULL, 5, '2025-12-28 00:00:00+00', '16:00:00', '17:00:00'),
(559, NULL, 5, '2025-05-19 00:00:00+00', '12:00:00', '13:00:00'),
(560, NULL, 28, '2026-01-28 00:00:00+00', '09:00:00', '10:00:00'),
(561, NULL, 9, '2026-01-28 00:00:00+00', '09:00:00', '10:00:00'),
(562, NULL, 28, '2026-02-17 00:00:00+00', '09:00:00', '10:00:00'),
(564, NULL, 9, '2026-02-20 00:00:00+00', '10:00:00', '11:00:00'),
(567, NULL, 9, '2026-12-12 00:00:00+00', '10:00:00', '11:00:00'),
(568, NULL, 5, '2026-01-03 00:00:00+00', '14:00:00', '15:00:00'),
(569, NULL, 5, '2025-12-19 00:00:00+00', '12:00:00', '13:00:00'),
(570, NULL, 10, '2026-10-07 00:00:00+00', '19:00:00', '20:00:00'),
(571, NULL, 9, '2026-10-10 00:00:00+00', '19:00:00', '20:00:00'),
(572, NULL, 16, '2026-01-01 00:00:00+00', '17:00:00', '18:00:00'),
(573, NULL, 14, '2026-12-20 00:00:00+00', '11:00:00', '12:00:00'),
(574, NULL, 5, '2025-12-19 00:00:00+00', '15:00:00', '16:00:00'),
(575, NULL, 1, '2025-12-28 00:00:00+00', '11:00:00', '12:00:00'),
(576, NULL, 5, '2025-12-28 00:00:00+00', '18:00:00', '19:00:00'),
(577, NULL, 10, '2026-02-19 00:00:00+00', '14:00:00', '15:00:00'),
(578, NULL, 5, '2026-12-12 00:00:00+00', '10:00:00', '11:00:00'),
(579, NULL, 5, '2026-03-26 00:00:00+00', '09:00:00', '10:00:00'),
(580, NULL, 5, '2025-12-28 00:00:00+00', '19:00:00', '20:00:00'),
(581, NULL, 9, '2025-12-28 00:00:00+00', '15:00:00', '16:00:00'),
(582, NULL, 5, '2025-12-19 00:00:00+00', '11:00:00', '12:00:00'),
(583, NULL, 5, '2025-12-19 00:00:00+00', '18:00:00', '19:00:00'),
(584, NULL, 31, '2025-12-14 00:00:00+00', '15:00:00', '16:00:00'),
(589, NULL, 31, '2026-01-30 00:00:00+00', '12:00:00', '13:00:00'),
(590, NULL, 31, '2026-02-01 00:00:00+00', '14:00:00', '15:00:00'),
(591, NULL, 31, '2026-02-01 00:00:00+00', '15:00:00', '16:00:00'),
(592, NULL, 31, '2026-02-01 00:00:00+00', '16:00:00', '17:00:00'),
(593, NULL, 31, '2026-02-01 00:00:00+00', '17:00:00', '18:00:00'),
(599, NULL, 5, '2026-02-02 00:00:00+00', '14:00:00', '15:00:00'),
(600, NULL, 5, '2026-02-02 00:00:00+00', '15:00:00', '16:00:00'),
(601, NULL, 5, '2026-02-02 00:00:00+00', '16:00:00', '17:00:00'),
(602, NULL, 31, '2026-02-02 00:00:00+00', '13:00:00', '14:00:00'),
(603, NULL, 31, '2026-02-02 00:00:00+00', '14:00:00', '15:00:00'),
(604, NULL, 31, '2026-02-02 00:00:00+00', '15:00:00', '16:00:00'),
(605, NULL, 31, '2026-02-02 00:00:00+00', '16:00:00', '17:00:00');
INSERT INTO "public"."lesson_focus" ("id", "name") VALUES
(1, 'tactics'),
(2, 'bandeja_vibora'),
(3, 'volleys');
INSERT INTO "public"."lessons" ("lesson_id", "club_id", "lesson_type", "date", "start_time", "end_time", "created_at", "updated_at", "coach_id", "lesson_focus_id", "lesson_focus") VALUES
(28, NULL, NULL, '2025-12-30', '12:00:00', '13:00:00', '2025-12-03 17:02:49.639933', '2025-12-03 17:02:49.639933', 9, NULL, NULL),
(35, NULL, 'Individueel', '2026-07-06', '17:00:00', '18:00:00', '2025-12-06 11:12:04.82423', '2025-12-06 11:12:04.82423', 4, NULL, NULL),
(65, NULL, 'Individueel', '2025-12-20', '19:00:00', '20:00:00', '2025-12-08 08:04:25.90481', '2025-12-08 08:04:25.90481', 4, NULL, NULL),
(66, NULL, NULL, '2026-02-22', '13:00:00', '14:00:00', '2025-12-08 09:00:03.260302', '2025-12-08 09:00:03.260302', 13, NULL, NULL),
(70, NULL, 'Individueel', '2025-12-28', '10:00:00', '11:00:00', '2025-12-08 12:18:06.890779', '2025-12-08 12:18:06.890779', 1, NULL, NULL),
(71, NULL, 'Individueel', '2025-12-26', '15:00:00', '16:00:00', '2025-12-08 14:42:56.628245', '2025-12-08 14:42:56.628245', 14, NULL, NULL),
(73, NULL, NULL, '2026-02-18', '16:00:00', '17:00:00', '2025-12-08 16:01:15.377519', '2025-12-08 16:01:15.377519', 10, NULL, NULL),
(74, NULL, NULL, '2026-02-18', '16:00:00', '17:00:00', '2025-12-08 16:03:57.347054', '2025-12-08 16:03:57.347054', 10, NULL, NULL),
(77, NULL, 'Groepsles', '2026-04-04', '19:00:00', '20:00:00', '2025-12-08 17:23:26.327683', '2025-12-08 17:23:26.327683', 10, 3, 'volleys'),
(80, NULL, 'Individueel', '2026-10-10', '18:00:00', '19:00:00', '2025-12-08 19:57:21.898921', '2025-12-08 19:57:21.898921', 9, NULL, NULL),
(81, NULL, 'Individueel', '2026-10-10', '20:00:00', '21:00:00', '2025-12-08 19:58:10.026422', '2025-12-08 19:58:10.026422', 9, NULL, NULL),
(92, NULL, 'Individueel', '2025-12-28', '10:00:00', '11:00:00', '2025-12-09 10:47:06.991884', '2025-12-09 10:47:06.991884', 7, NULL, NULL),
(98, NULL, 'Individueel', '2025-12-28', '19:00:00', '20:00:00', '2025-12-09 11:18:44.602268', '2025-12-09 11:18:44.602268', 7, NULL, NULL),
(99, NULL, 'Individueel', '2025-12-28', '21:00:00', '22:00:00', '2025-12-09 11:22:11.734014', '2025-12-09 11:22:11.734014', 7, NULL, NULL),
(111, NULL, 'Individueel', '2025-12-28', '20:00:00', '21:00:00', '2025-12-10 08:54:16.69675', '2025-12-10 08:54:16.69675', 7, NULL, NULL),
(112, NULL, 'Individueel', '2025-12-28', '12:00:00', '13:00:00', '2025-12-10 08:55:46.975531', '2025-12-10 08:55:46.975531', 5, NULL, NULL),
(113, NULL, 'Individueel', '2025-12-28', '11:00:00', '12:00:00', '2025-12-10 09:11:49.710464', '2025-12-10 09:11:49.710464', 5, NULL, NULL),
(118, NULL, 'Individueel', '2025-12-28', '14:00:00', '15:00:00', '2025-12-10 14:38:07.360955', '2025-12-10 14:38:07.360955', 5, NULL, NULL),
(119, NULL, 'Individueel', '2025-12-28', '13:00:00', '14:00:00', '2025-12-10 14:39:17.095672', '2025-12-10 14:39:17.095672', 5, NULL, NULL),
(120, NULL, 'Individueel', '2025-12-28', '12:00:00', '13:00:00', '2025-12-10 14:39:55.131569', '2025-12-10 14:39:55.131569', 7, NULL, NULL),
(121, NULL, 'Individueel', '2025-12-28', '09:00:00', '10:00:00', '2025-12-10 14:43:53.186435', '2025-12-10 14:43:53.186435', 5, NULL, NULL),
(122, NULL, 'Individueel', '2025-12-28', '16:00:00', '17:00:00', '2025-12-10 21:00:39.300771', '2025-12-10 21:00:39.300771', 7, NULL, NULL),
(123, NULL, 'Individueel', '2025-12-28', '13:00:00', '14:00:00', '2025-12-10 21:03:10.922434', '2025-12-10 21:03:10.922434', 5, NULL, NULL),
(124, NULL, 'Groepsles', '2025-12-28', '14:00:00', '15:00:00', '2025-12-10 21:06:52.539576', '2025-12-10 21:06:52.539576', 7, NULL, 'tactics'),
(126, NULL, 'Individueel', '2025-12-28', '10:00:00', '11:00:00', '2025-12-11 19:54:13.783611', '2025-12-11 19:54:13.783611', 5, NULL, NULL),
(127, NULL, 'Individueel', '2025-12-28', '15:00:00', '16:00:00', '2025-12-11 19:56:55.715472', '2025-12-11 19:56:55.715472', 5, NULL, NULL),
(132, NULL, 'Groepsles', '2025-12-29', '15:00:00', '16:00:00', '2025-12-12 20:50:59.785149', '2025-12-12 20:50:59.785149', 9, NULL, 'bandeja_vibora'),
(133, NULL, 'Individueel', '2025-12-30', '21:00:00', '22:00:00', '2025-12-12 20:54:08.15141', '2025-12-12 20:54:08.15141', 9, NULL, NULL),
(134, NULL, 'Individueel', '2025-12-31', '10:00:00', '11:00:00', '2025-12-12 21:07:16.427302', '2025-12-12 21:07:16.427302', 4, NULL, NULL),
(136, NULL, 'Groepsles', '2026-02-15', '13:00:00', '14:00:00', '2025-12-13 08:23:40.339369', '2025-12-13 08:23:40.339369', 9, NULL, 'volleys'),
(141, NULL, 'Individueel', '2025-12-28', '17:00:00', '18:00:00', '2025-12-13 14:18:23.277354', '2025-12-13 14:18:23.277354', 5, NULL, NULL),
(142, NULL, 'Individueel', '2025-12-28', '15:00:00', '16:00:00', '2025-12-13 14:40:32.021047', '2025-12-13 14:40:32.021047', 7, NULL, NULL),
(143, NULL, 'Individueel', '2025-12-28', '21:00:00', '22:00:00', '2025-12-13 21:28:34.367384', '2025-12-13 21:28:34.367384', 5, NULL, NULL),
(153, NULL, 'Individueel', '2025-12-28', '14:00:00', '15:00:00', '2025-12-14 19:46:12.979733', '2025-12-14 19:46:12.979733', 9, NULL, NULL),
(155, NULL, 'Individueel', '2027-12-28', '10:00:00', '11:00:00', '2025-12-14 20:45:23.281724', '2025-12-14 20:45:23.281724', 9, NULL, NULL),
(158, NULL, 'Individueel', '2025-12-28', '20:00:00', '21:00:00', '2025-12-14 22:10:24.864424', '2025-12-14 22:10:24.864424', 5, NULL, NULL),
(159, NULL, 'Individueel', '2026-02-25', '12:00:00', '13:00:00', '2025-12-14 22:13:38.649978', '2025-12-14 22:13:38.649978', 5, NULL, NULL),
(162, NULL, 'Groepsles', '2026-03-11', '14:00:00', '15:00:00', '2025-12-14 23:30:02.997256', '2025-12-14 23:30:02.997256', 4, NULL, 'Backhand'),
(164, NULL, 'Individueel', '2026-05-19', '12:00:00', '13:00:00', '2025-12-15 13:30:02.954167', '2025-12-15 13:30:02.954167', 9, NULL, NULL),
(165, NULL, 'Individueel', '2026-02-17', '09:00:00', '10:00:00', '2025-12-15 13:36:12.386294', '2025-12-15 13:36:12.386294', 9, NULL, NULL),
(166, NULL, 'Individueel', '2026-02-20', '10:00:00', '11:00:00', '2025-12-15 13:46:52.891229', '2025-12-15 13:46:52.891229', 5, NULL, NULL),
(169, NULL, 'Individueel', '2026-01-28', '16:00:00', '17:00:00', '2025-12-16 22:03:31.13123', '2025-12-16 22:03:31.13123', 31, NULL, NULL),
(170, NULL, 'Individueel', '2026-01-29', '18:00:00', '19:00:00', '2025-12-16 22:06:23.969907', '2025-12-16 22:06:23.969907', 31, NULL, NULL),
(171, NULL, 'Individueel', '2026-01-30', '10:00:00', '11:00:00', '2025-12-16 22:14:50.370994', '2025-12-16 22:14:50.370994', 31, NULL, NULL),
(172, NULL, 'Groepsles', '2026-02-02', '13:00:00', '14:00:00', '2025-12-16 22:47:38.756861', '2025-12-16 22:47:38.756861', 5, NULL, 'Backhand');
INSERT INTO "public"."coaches" ("coach_id", "first_name", "last_name", "email", "phone", "bio", "created_at", "gender", "is_active", "ranking", "profile_image", "date_of_birth", "hand_preference", "lesson_type_preference", "playing_intensity", "ranking_value") VALUES
(3, 'Lars', 'Van Acker', 'Lars9vanacker@gmail.com', '1461', NULL, '2025-11-27 18:13:32.478915+00', 'man', 't', 'P500', NULL, NULL, NULL, 'group', 'competitive', 500),
(4, 'Donald J', 'Trump', 'donald@trump.be', '0473316892', NULL, '2025-11-27 21:03:15.301542+00', 'man', 't', 'P400', '/static/1F95F7D0-80A0-4DDF-9BB5-7116BBBF961B.jpg', NULL, NULL, 'group', 'recreational', 400),
(5, 'Riete', 'De Rouck', 'riete@coach.be', '04544559911', NULL, '2025-11-29 14:54:11.051427+00', 'vrouw', 't', 'P200', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/riete_coach_be_1765623691.png', NULL, NULL, 'group', 'recreational', 100),
(6, 'Robbe', 'Heyvaert', 'rob.heyvaert@gmail.com', '1461645', NULL, '2025-12-02 08:53:49.217646+00', 'vrouw', 't', 'Geen', NULL, NULL, NULL, 'group', 'competitive', NULL),
(7, 'Tiebe', 'coach', 'tiebe@coach.be', '0492 45 34 25', NULL, '2025-12-02 09:17:12.648641+00', 'man', 't', 'P500', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_7_1765275638.png', NULL, NULL, 'individual', 'competitive', 500),
(8, 'cc', 'aa', 'cc@aa.be', '0411223366', NULL, '2025-12-03 14:45:10.627764+00', 'man', 't', 'P400', NULL, NULL, NULL, 'group', 'competitive', 400),
(9, 'Romelu ', 'Lu', 'romelu@coach.be', '047', NULL, '2025-12-03 17:01:40.798333+00', 'man', 't', 'P1000', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_9_1765569802.jpg', NULL, NULL, 'group', 'recreational', 1000),
(10, 'Milan', 'Carlier', 'milan.carlier@padel.be', '04', NULL, '2025-12-03 21:10:16.142315+00', 'man', 't', 'P700', NULL, NULL, NULL, 'group', 'competitive', 700),
(11, 'Kevin ', 'De Witte', 'kdb@padel.be', '0473313689', NULL, '2025-12-05 21:18:43.304089+00', 'man', 't', 'P200', NULL, NULL, NULL, 'group', 'competitive', 200),
(12, 'Jeremy', 'Doku', 'jeremy.doku@padel.be', '0489754212', NULL, '2025-12-05 21:21:44.825968+00', 'man', 't', 'P50', NULL, NULL, NULL, 'group', 'competitive', 50),
(13, 'Erik', 'vv', 'erik@padel.be', '0489754212', NULL, '2025-12-05 21:28:51.345711+00', 'man', 't', 'P100', NULL, NULL, NULL, 'group', 'competitive', 100),
(14, 'Rudi', 'Garcia', 'rudi.garcia@padel.be', '0473313687', NULL, '2025-12-06 09:00:04.79759+00', 'man', 't', 'P300', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_14_1765125304.jpg', NULL, NULL, 'group', 'competitive', 300),
(15, 'Eden', 'Hazard', 'eden.hazard@padel.be', '0473316892', NULL, '2025-12-07 11:24:59.172626+00', 'vrouw', 't', 'P100', NULL, '2000-12-19', 'Rechts', 'group', 'competitive', 100),
(16, 'Roberto', 'Martinez', 'roberto.martinez@padel.be', '0475854562', NULL, '2025-12-07 16:28:38.325042+00', 'man', 't', 'P100', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/roberto_martinez_padel_be_1765124913.jpg', '1975-10-10', 'Rechts', 'group', 'competitive', 100),
(17, 'coach', 'jan', 'coachjan@gmail.com', '0471123456', NULL, '2025-12-08 11:52:26.135065+00', 'vrouw', 't', 'P400', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/profile_17_1765556187.png', '2000-12-15', 'Links', 'group', 'competitive', 400),
(18, 'Maarten', 'AZ', 'maarten@padel.be', '0473135485', NULL, '2025-12-11 17:48:57.37972+00', 'anders', 't', 'P200', NULL, '2000-10-10', 'Links', 'individual', 'competitive', NULL),
(19, 'ax', 'bat', 'ax@padel.be', '0444552211', NULL, '2025-12-11 17:56:58.48225+00', 'man', 't', 'P400', NULL, '2005-12-12', 'Rechts', 'group', 'competitive', NULL),
(20, 'Jan', 'ver', 'jan@coach.be', '0477884411', NULL, '2025-12-11 18:03:19.848353+00', 'anders', 't', 'P200', NULL, '2005-11-25', 'Links', 'group', 'recreational', NULL),
(21, 'Jan', 'Cornelis', 'jan.cornelis@padel.be', '0431524952', NULL, '2025-12-12 19:47:07.879528+00', 'man', 't', 'P1000', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/jan_cornelis_padel_be_1765568824.jpg', '2000-10-10', 'Links', 'group', 'recreational', NULL),
(22, 'Vincent', 'Kompany', 'vince@padel.be', '0473313654', NULL, '2025-12-12 19:58:03.896393+00', 'man', 't', 'P400', NULL, '2000-12-12', 'Links', 'group', 'recreational', NULL),
(23, 'Erik', 'G', 'erikg@padel.be', '0473313654', NULL, '2025-12-12 20:04:41.577519+00', 'man', 't', 'P200', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/erikg_padel_be_1765569880.jpg', '2000-12-20', 'Rechts', 'group', 'recreational', NULL),
(24, 'tom', 'wemmels', 'tom@wemmels.be', '0411889966', NULL, '2025-12-14 09:52:41.125102+00', 'man', 't', 'P200', NULL, '2006-03-12', 'Rechts', 'individual', 'recreational', NULL),
(25, 'Aa', 'bb', 'aa.bb@gmail.com', '0478954264', NULL, '2025-12-14 17:41:38.663276+00', 'man', 't', 'P500', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/aa_bb_gmail_com_1765734097.png', '2000-12-28', 'Links', 'group', 'recreational', NULL),
(26, 'Kathleen', 'Collaert', 'kathleen.collaert@padel.be', '0478754715', NULL, '2025-12-14 21:02:17.369175+00', 'vrouw', 't', 'P300', NULL, '2000-10-10', 'Rechts', 'group', 'competitive', NULL),
(27, 'Jan', 'Peeters', 'jan.peeters@padel.be', '0478784512', NULL, '2025-12-14 23:15:00.387923+00', 'man', 't', 'P1000', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/jan_peeters_padel_be_1765754098.png', '2000-10-20', 'Rechts', 'group', 'recreational', NULL),
(28, 'Maarten', 'Cc', 'maarten.cc@padel.be', '0471741384', NULL, '2025-12-15 13:31:55.527817+00', 'man', 't', 'P100', NULL, '1980-10-15', 'Rechts', 'group', 'recreational', NULL),
(29, 'Jan ', 'VDB', 'jan.vdb@padel.be', '0478452354', NULL, '2025-12-16 11:26:52.016651+00', 'man', 't', 'P100', 'https://xilmcifkjefxwdtgzgkw.supabase.co/storage/v1/object/public/profile_pictures/coaches/jan_vdb_padel_be_1765884407.webp', '2000-10-20', 'Rechts', 'individual', 'recreational', NULL),
(31, 'Romelu', 'Lukaku', 'romelu.lukaku@coach.be', '0428675412', NULL, '2025-12-16 21:48:23.798357+00', 'man', 't', 'P1000', '/static/Romelu_Lukaku.webp', '1999-10-19', 'Rechts', 'group', 'recreational', NULL),
(32, 'Jef', 'Patat', 'lars.vanacker@hogent.be', '', NULL, '2025-12-19 10:51:20.843199+00', 'anders', 't', 'P1000', NULL, '1890-12-19', 'Rechts', 'individual', 'recreational', NULL);
INSERT INTO "public"."lesson_players" ("lesson_id", "player_id") VALUES
(28, 19),
(35, 8),
(65, 20),
(66, 36),
(70, 22),
(71, 43),
(74, 20),
(80, 20),
(81, 20),
(92, 3),
(98, 3),
(99, 3),
(111, 10),
(112, 10),
(113, 10),
(118, 19),
(119, 19),
(120, 8),
(121, 8),
(122, 48),
(123, 48),
(124, 1),
(124, 8),
(124, 48),
(126, 19),
(127, 19),
(132, 1),
(132, 8),
(132, 20),
(133, 1),
(134, 52),
(136, 8),
(141, 20),
(142, 20),
(143, 8),
(153, 20),
(155, 20),
(158, 8),
(159, 66),
(162, 60),
(162, 66),
(162, 67),
(164, 70),
(165, 70),
(166, 71),
(169, 20),
(170, 1),
(171, 3),
(172, 1),
(172, 20),
(172, 77);
INSERT INTO "public"."alembic_version" ("version_num") VALUES
('64d11a672d21');

INSERT INTO "realtime"."schema_migrations" ("version", "inserted_at") VALUES
(20211116024918, '2025-10-29 22:18:25'),
(20211116045059, '2025-10-29 22:18:27'),
(20211116050929, '2025-10-29 22:18:29'),
(20211116051442, '2025-10-29 22:18:31'),
(20211116212300, '2025-10-29 22:18:33'),
(20211116213355, '2025-10-29 22:18:35'),
(20211116213934, '2025-10-29 22:18:37'),
(20211116214523, '2025-10-29 22:18:39'),
(20211122062447, '2025-10-29 22:18:41'),
(20211124070109, '2025-10-29 22:18:43'),
(20211202204204, '2025-10-29 22:18:45'),
(20211202204605, '2025-10-29 22:18:46'),
(20211210212804, '2025-10-29 22:18:52'),
(20211228014915, '2025-10-29 22:18:54'),
(20220107221237, '2025-10-29 22:18:56'),
(20220228202821, '2025-10-29 22:18:58'),
(20220312004840, '2025-10-29 22:19:00'),
(20220603231003, '2025-10-29 22:19:03'),
(20220603232444, '2025-10-29 22:19:04'),
(20220615214548, '2025-10-29 22:19:07'),
(20220712093339, '2025-10-29 22:19:08'),
(20220908172859, '2025-10-29 22:19:10'),
(20220916233421, '2025-10-29 22:19:12'),
(20230119133233, '2025-10-29 22:19:14'),
(20230128025114, '2025-10-29 22:19:16'),
(20230128025212, '2025-10-29 22:19:18'),
(20230227211149, '2025-10-29 22:19:20'),
(20230228184745, '2025-10-29 22:19:22'),
(20230308225145, '2025-10-29 22:19:24'),
(20230328144023, '2025-10-29 22:19:26'),
(20231018144023, '2025-10-29 22:19:28'),
(20231204144023, '2025-10-29 22:19:31'),
(20231204144024, '2025-10-29 22:19:33'),
(20231204144025, '2025-10-29 22:19:35'),
(20240108234812, '2025-10-29 22:19:37'),
(20240109165339, '2025-10-29 22:19:38'),
(20240227174441, '2025-10-29 22:19:42'),
(20240311171622, '2025-10-29 22:19:44'),
(20240321100241, '2025-10-29 22:19:48'),
(20240401105812, '2025-10-29 22:19:53'),
(20240418121054, '2025-10-29 22:19:56'),
(20240523004032, '2025-10-29 22:20:02'),
(20240618124746, '2025-10-29 22:20:04'),
(20240801235015, '2025-10-29 22:20:06'),
(20240805133720, '2025-10-29 22:20:08'),
(20240827160934, '2025-10-29 22:20:10'),
(20240919163303, '2025-10-29 22:20:12'),
(20240919163305, '2025-10-29 22:20:14'),
(20241019105805, '2025-10-29 22:20:16'),
(20241030150047, '2025-10-29 22:20:23'),
(20241108114728, '2025-10-29 22:20:26'),
(20241121104152, '2025-10-29 22:20:27'),
(20241130184212, '2025-10-29 22:20:30'),
(20241220035512, '2025-10-29 22:20:31'),
(20241220123912, '2025-10-29 22:20:33'),
(20241224161212, '2025-10-29 22:20:35'),
(20250107150512, '2025-10-29 22:20:37'),
(20250110162412, '2025-10-29 22:20:39'),
(20250123174212, '2025-10-29 22:20:41'),
(20250128220012, '2025-10-29 22:20:43'),
(20250506224012, '2025-10-29 22:20:44'),
(20250523164012, '2025-10-29 22:20:46'),
(20250714121412, '2025-10-29 22:20:48'),
(20250905041441, '2025-10-29 22:20:50'),
(20251103001201, '2025-11-11 21:20:52');

INSERT INTO "storage"."buckets" ("id", "name", "owner", "created_at", "updated_at", "public", "avif_autodetection", "file_size_limit", "allowed_mime_types", "owner_id", "type") VALUES
('profile_pictures', 'profile_pictures', NULL, '2025-12-07 13:13:27.26442+00', '2025-12-07 13:13:27.26442+00', 't', 'f', NULL, NULL, NULL, 'STANDARD'),
('profile-photos', 'profile-photos', NULL, '2025-12-07 11:31:40.657014+00', '2025-12-07 11:31:40.657014+00', 't', 'f', NULL, NULL, NULL, 'STANDARD');
INSERT INTO "storage"."objects" ("id", "bucket_id", "name", "owner", "created_at", "updated_at", "last_accessed_at", "metadata", "path_tokens", "version", "owner_id", "user_metadata", "level") VALUES
('07b002bd-f3e4-47cb-a094-a9720d430114', 'profile_pictures', 'profile_5_1765320974.jpg', NULL, '2025-12-09 22:56:16.654073+00', '2025-12-09 22:56:16.654073+00', '2025-12-09 22:56:16.654073+00', '{"eTag": "\"e3d42cd5150bde942b7e24244db929c7\"", "size": 3051646, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-09T22:56:17.000Z", "contentLength": 3051646, "httpStatusCode": 200}', '{profile_5_1765320974.jpg}', '540a48d1-ddb9-4944-a2da-ba03936618e3', NULL, '{}', 1),
('09f8899c-7b6b-4570-8806-7ebb812d3175', 'profile_pictures', 'coaches/aa_bb_gmail_com_1765734097.png', NULL, '2025-12-14 17:41:38.592327+00', '2025-12-14 17:41:38.592327+00', '2025-12-14 17:41:38.592327+00', '{"eTag": "\"83613d82e31e1dde75b4c97eaa470184\"", "size": 870263, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-14T17:41:39.000Z", "contentLength": 870263, "httpStatusCode": 200}', '{coaches,aa_bb_gmail_com_1765734097.png}', '3c67bcef-acd4-4fdd-ad7a-34979601c74f', NULL, '{}', 2),
('13333c29-efa5-43da-ae93-fe69450b73d8', 'profile_pictures', 'coaches/erikg_padel_be_1765569880.jpg', NULL, '2025-12-12 20:04:41.474921+00', '2025-12-12 20:04:41.474921+00', '2025-12-12 20:04:41.474921+00', '{"eTag": "\"ddd258abe4f64de80f5d58a082d5fde2\"", "size": 689324, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T20:04:42.000Z", "contentLength": 689324, "httpStatusCode": 200}', '{coaches,erikg_padel_be_1765569880.jpg}', '634c412b-4dab-4d25-a99a-cae5da6a5131', NULL, '{}', 2),
('14e53fad-c574-47c9-9b7b-0f310f0612e2', 'profile_pictures', 'profile_14_1765125304.jpg', NULL, '2025-12-07 16:35:07.082183+00', '2025-12-07 16:35:07.082183+00', '2025-12-07 16:35:07.082183+00', '{"eTag": "\"b3eeac814b3f01c46b54bb3df974a9db\"", "size": 31924, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T16:35:08.000Z", "contentLength": 31924, "httpStatusCode": 200}', '{profile_14_1765125304.jpg}', 'a68ae96e-ce8b-447b-85b3-5752bc63180f', NULL, '{}', 1),
('1b20662f-e7c0-4541-b348-30afc8183686', 'profile_pictures', 'players/laurence_heeman_gmail_com_1765666669.jpeg', NULL, '2025-12-13 22:57:50.235425+00', '2025-12-13 22:57:50.235425+00', '2025-12-13 22:57:50.235425+00', '{"eTag": "\"04cf3f4478e20e9e081f2d03a6efc50c\"", "size": 2519805, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-13T22:57:51.000Z", "contentLength": 2519805, "httpStatusCode": 200}', '{players,laurence_heeman_gmail_com_1765666669.jpeg}', '991feae0-5649-4bb2-b617-30423bbd80e5', NULL, '{}', 2),
('1f5581e3-519a-486d-b47c-b94e5e83b344', 'profile_pictures', 'players/guy_vdb_be_1765183345.jpg', NULL, '2025-12-08 08:42:27.560784+00', '2025-12-08 08:42:27.560784+00', '2025-12-08 08:42:27.560784+00', '{"eTag": "\"026d042ff49bcdac1216b246e9881edb\"", "size": 3088666, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T08:42:28.000Z", "contentLength": 3088666, "httpStatusCode": 200}', '{players,guy_vdb_be_1765183345.jpg}', 'e6abebf8-1187-4884-a3be-d86de556c273', NULL, '{}', 2),
('25d1fce6-4298-4eb9-8563-a25c56e84096', 'profile_pictures', 'players/boma_gmail_com_1765191812.png', NULL, '2025-12-08 11:03:33.201872+00', '2025-12-08 11:03:33.201872+00', '2025-12-08 11:03:33.201872+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T11:03:34.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,boma_gmail_com_1765191812.png}', 'c4383056-bac7-408b-baee-cd2ffe544772', NULL, '{}', 2),
('2bdf7d39-01e0-4380-935b-c8ea34af6ba2', 'profile_pictures', 'players/maxv_gmail_com_1765190356.png', NULL, '2025-12-08 10:39:18.364026+00', '2025-12-08 10:39:18.364026+00', '2025-12-08 10:39:18.364026+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T10:39:19.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,maxv_gmail_com_1765190356.png}', '290cb208-a4e1-4e9f-af24-a397d10a5109', NULL, '{}', 2),
('2de767c7-4e40-4cae-82a1-ed457f15c119', 'profile_pictures', 'player_jan.verthongen@padel.be.jpg', NULL, '2025-12-07 15:43:52.060571+00', '2025-12-07 15:43:52.060571+00', '2025-12-07 15:43:52.060571+00', '{"eTag": "\"1b69b88c136a3bce8665d067074e40db\"", "size": 730478, "mimetype": "image/jpeg", "cacheControl": "no-cache", "lastModified": "2025-12-07T15:43:52.000Z", "contentLength": 730478, "httpStatusCode": 200}', '{player_jan.verthongen@padel.be.jpg}', 'fa352159-13c9-42e9-8951-77d7f0e4b1e5', NULL, '{}', 1),
('301ccf04-1058-49ee-b3aa-bbaba7f04009', 'profile_pictures', 'profile_3_1765268041.png', NULL, '2025-12-09 08:14:02.295821+00', '2025-12-09 08:14:02.295821+00', '2025-12-09 08:14:02.295821+00', '{"eTag": "\"9e94883fb609b7a7d67c126cf81e6910\"", "size": 45465, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-09T08:14:03.000Z", "contentLength": 45465, "httpStatusCode": 200}', '{profile_3_1765268041.png}', 'dc35cc04-a413-45fa-9aab-de075b7ac0ce', NULL, '{}', 1),
('3340e7f8-0676-414f-bc6f-d470bd610124', 'profile_pictures', 'profile_1_1765182839.jpg', NULL, '2025-12-08 08:34:02.620733+00', '2025-12-08 08:34:02.620733+00', '2025-12-08 08:34:02.620733+00', '{"eTag": "\"39c7314f11540dfcfcdfbf31a21aff8a\"", "size": 2976371, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T08:34:03.000Z", "contentLength": 2976371, "httpStatusCode": 200}', '{profile_1_1765182839.jpg}', 'a264f07a-1e43-4b32-8961-43d088c49438', NULL, '{}', 1),
('488116c2-760e-4d78-abdd-a98ae5d5a9f2', 'profile_pictures', 'players/ferre_trogh_padel_be_1765398153.webp', NULL, '2025-12-10 20:22:34.605369+00', '2025-12-10 20:22:34.605369+00', '2025-12-10 20:22:34.605369+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-10T20:22:35.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{players,ferre_trogh_padel_be_1765398153.webp}', '35855b7b-1dd0-4786-8766-9944913de126', NULL, '{}', 2),
('4c77ddd4-c61e-4d76-9fda-7362cb16e003', 'profile_pictures', 'players/maxv_gmail_com_1765191096.png', NULL, '2025-12-08 10:51:39.577923+00', '2025-12-08 10:51:39.577923+00', '2025-12-08 10:51:39.577923+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T10:51:40.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,maxv_gmail_com_1765191096.png}', 'ebf6c822-c138-4a4d-8bea-a2670ad57e4a', NULL, '{}', 2),
('52bcae1d-aaf3-425e-8728-fb965d80b2f3', 'profile_pictures', 'players/jan_denul_padel_be_1765396954.webp', NULL, '2025-12-10 20:02:36.067064+00', '2025-12-10 20:02:36.067064+00', '2025-12-10 20:02:36.067064+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-10T20:02:37.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{players,jan_denul_padel_be_1765396954.webp}', '44e45b81-b98f-4108-b230-352b0aa77637', NULL, '{}', 2),
('5411b45d-2eeb-4572-8f3d-6a33fb324170', 'profile_pictures', 'players/fernando_gmail_com_1765194471.png', NULL, '2025-12-08 11:47:55.33457+00', '2025-12-08 11:47:55.33457+00', '2025-12-08 11:47:55.33457+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T11:47:56.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,fernando_gmail_com_1765194471.png}', '688b7ed4-d142-47b6-96ba-a0e4f9c59b20', NULL, '{}', 2),
('590958ad-5d8c-449e-baae-833781ad7e2e', 'profile_pictures', 'profile_52_1765569764.jpg', NULL, '2025-12-12 20:02:46.275057+00', '2025-12-12 20:02:46.275057+00', '2025-12-12 20:02:46.275057+00', '{"eTag": "\"ddd258abe4f64de80f5d58a082d5fde2\"", "size": 689324, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T20:02:47.000Z", "contentLength": 689324, "httpStatusCode": 200}', '{profile_52_1765569764.jpg}', '16ee3148-d788-4092-8653-5954f5d6375b', NULL, '{}', 1),
('60d03de3-da5e-4b3d-818a-32d9e7798353', 'profile_pictures', 'players/billy_mertens_gmail_com_1765753830.heic', NULL, '2025-12-14 23:10:35.377468+00', '2025-12-14 23:10:35.377468+00', '2025-12-14 23:10:35.377468+00', '{"eTag": "\"f099a1aab87423582f7cc119d214d54c\"", "size": 2763543, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-14T23:10:36.000Z", "contentLength": 2763543, "httpStatusCode": 200}', '{players,billy_mertens_gmail_com_1765753830.heic}', 'aebdce12-4e48-4356-841b-ecaf9828b349', NULL, '{}', 2),
('664f6ccb-1edc-4ceb-a6c7-8daf047878dd', 'profile_pictures', 'profile_2_1765272522.png', NULL, '2025-12-09 09:28:43.563265+00', '2025-12-09 09:28:43.563265+00', '2025-12-09 09:28:43.563265+00', '{"eTag": "\"da8101bdc8b2198259656e4b30d34cae\"", "size": 66212, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-09T09:28:44.000Z", "contentLength": 66212, "httpStatusCode": 200}', '{profile_2_1765272522.png}', 'de558543-4750-4f2e-b2dd-e9af7237ea11', NULL, '{}', 1),
('68328398-bc81-4d9d-bcdc-6b3ac0a93577', 'profile_pictures', 'players/andreas_janssens_gmail_com_1765204640.webp', NULL, '2025-12-08 14:37:21.883785+00', '2025-12-08 14:37:21.883785+00', '2025-12-08 14:37:21.883785+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T14:37:22.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{players,andreas_janssens_gmail_com_1765204640.webp}', '59b172bb-88e2-4a9c-bbba-5dfb8da4560a', NULL, '{}', 2),
('6a4decaf-15f2-4120-88e3-b217b2c185c9', 'profile_pictures', 'profile_33_1765114318.JPG', NULL, '2025-12-07 13:32:01.592591+00', '2025-12-07 13:32:01.592591+00', '2025-12-07 13:32:01.592591+00', '{"eTag": "\"5dbe12a6b370a5b0cafa3e52be0bc8d0\"", "size": 3385444, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T13:32:02.000Z", "contentLength": 3385444, "httpStatusCode": 200}', '{profile_33_1765114318.JPG}', '690d5980-f196-4068-9869-542ff29651e9', NULL, '{}', 1),
('6b867e30-09de-48e6-b34f-7441a3460a89', 'profile_pictures', 'players/speler_thomas_be_1765572911.jpg', NULL, '2025-12-12 20:55:14.987725+00', '2025-12-12 20:55:14.987725+00', '2025-12-12 20:55:14.987725+00', '{"eTag": "\"5dbe12a6b370a5b0cafa3e52be0bc8d0\"", "size": 3385444, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T20:55:15.000Z", "contentLength": 3385444, "httpStatusCode": 200}', '{players,speler_thomas_be_1765572911.jpg}', 'f448c7ed-1f68-49f3-b390-655479acbf99', NULL, '{}', 2),
('6e762154-3b27-4bf2-85c5-00965fcbd73c', 'profile_pictures', 'profile_20_1765114437.webp', NULL, '2025-12-07 13:34:00.810143+00', '2025-12-07 13:34:00.810143+00', '2025-12-07 13:34:00.810143+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T13:34:01.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{profile_20_1765114437.webp}', '5ae3c3cb-0664-48fc-8028-8233828ce1bc', NULL, '{}', 1),
('7bf10b87-d3fa-4424-be3b-c971dffd3ca9', 'profile_pictures', 'players/erika_padel_be_1765569940.jpg', NULL, '2025-12-12 20:05:42.402242+00', '2025-12-12 20:05:42.402242+00', '2025-12-12 20:05:42.402242+00', '{"eTag": "\"ddd258abe4f64de80f5d58a082d5fde2\"", "size": 689324, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T20:05:43.000Z", "contentLength": 689324, "httpStatusCode": 200}', '{players,erika_padel_be_1765569940.jpg}', '111e5e68-c892-48bd-b89e-2f6572db652f', NULL, '{}', 2),
('7ec75338-9e87-4e1f-9f74-98c4efbf0328', 'profile_pictures', 'players/fa_gmail_com_1765191275.png', NULL, '2025-12-08 10:54:38.758416+00', '2025-12-08 10:54:38.758416+00', '2025-12-08 10:54:38.758416+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T10:54:39.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,fa_gmail_com_1765191275.png}', 'd953be9b-fd48-4fce-bd7d-77abbdeac7f3', NULL, '{}', 2),
('82a25eee-950a-49cf-ab65-a9437cebc9ce', 'profile_pictures', 'profile_8_1765123338.jpg', NULL, '2025-12-07 16:02:24.717636+00', '2025-12-07 16:02:24.717636+00', '2025-12-07 16:02:24.717636+00', '{"eTag": "\"1b69b88c136a3bce8665d067074e40db\"", "size": 730478, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T16:02:25.000Z", "contentLength": 730478, "httpStatusCode": 200}', '{profile_8_1765123338.jpg}', '47082bb7-583f-426a-92a7-ccd2d87cfa69', NULL, '{}', 1),
('8799dbef-e470-43ef-9c4f-15886bd69023', 'profile_pictures', 'players/jan_denul_padel_be_1765397038.webp', NULL, '2025-12-10 20:04:00.612989+00', '2025-12-10 20:04:00.612989+00', '2025-12-10 20:04:00.612989+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-10T20:04:01.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{players,jan_denul_padel_be_1765397038.webp}', '531fe406-3442-4285-840d-7798578aed9d', NULL, '{}', 2),
('8ab57f05-8a5d-4da5-82bd-7e30b07a5b8b', 'profile_pictures', 'players/jef_aa_padel_be_1765884563.jpg', NULL, '2025-12-16 11:29:27.089011+00', '2025-12-16 11:29:27.089011+00', '2025-12-16 11:29:27.089011+00', '{"eTag": "\"b3eeac814b3f01c46b54bb3df974a9db\"", "size": 31924, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-16T11:29:28.000Z", "contentLength": 31924, "httpStatusCode": 200}', '{players,jef_aa_padel_be_1765884563.jpg}', '6237f26d-efff-496b-90f2-12df6d1a923e', NULL, '{}', 2),
('8e07b18f-55d8-4949-912e-607c565f4739', 'profile_pictures', 'players/janpie_gmail_com_1765186361.png', NULL, '2025-12-08 09:32:44.259348+00', '2025-12-08 09:32:44.259348+00', '2025-12-08 09:32:44.259348+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T09:32:45.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,janpie_gmail_com_1765186361.png}', 'a5e209df-681f-4a11-9ac1-7a0365fed042', NULL, '{}', 2),
('97291949-61a2-4aa3-a7e3-e848982f78b1', 'profile_pictures', 'coaches/jan_peeters_padel_be_1765754098.png', NULL, '2025-12-14 23:15:00.196254+00', '2025-12-14 23:15:00.196254+00', '2025-12-14 23:15:00.196254+00', '{"eTag": "\"3d20f40f121c8975a134318e72718974\"", "size": 30401, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-14T23:15:01.000Z", "contentLength": 30401, "httpStatusCode": 200}', '{coaches,jan_peeters_padel_be_1765754098.png}', '6916db8b-86f7-4530-acc2-09e45899292a', NULL, '{}', 2),
('97424bdc-0578-4029-b8cc-c839b7d30fb9', 'profile_pictures', 'players/ferre_trogh_padel_be_1765397945.jpg', NULL, '2025-12-10 20:19:07.508817+00', '2025-12-10 20:19:07.508817+00', '2025-12-10 20:19:07.508817+00', '{"eTag": "\"1b69b88c136a3bce8665d067074e40db\"", "size": 730478, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-10T20:19:08.000Z", "contentLength": 730478, "httpStatusCode": 200}', '{players,ferre_trogh_padel_be_1765397945.jpg}', 'fa11652e-079b-4773-ad83-82fcc1b6ce0a', NULL, '{}', 2),
('9f25cb3d-c68b-488d-87cb-bcb700e3d3f0', 'profile_pictures', 'profile_17_1765556187.png', NULL, '2025-12-12 16:16:29.858837+00', '2025-12-12 16:16:29.858837+00', '2025-12-12 16:16:29.858837+00', '{"eTag": "\"2c56f99737af476635fca8a7ec6bfc74\"", "size": 274008, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T16:16:30.000Z", "contentLength": 274008, "httpStatusCode": 200}', '{profile_17_1765556187.png}', '27acedee-fa78-47e3-a16f-638bf717edca', NULL, '{}', 1),
('acdf47cb-1c10-49a5-9aac-474808bb4825', 'profile_pictures', 'profile_9_1765569802.jpg', NULL, '2025-12-12 20:03:24.200583+00', '2025-12-12 20:03:24.200583+00', '2025-12-12 20:03:24.200583+00', '{"eTag": "\"c94fa267f6512253e59fb40d3000741e\"", "size": 694250, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T20:03:25.000Z", "contentLength": 694250, "httpStatusCode": 200}', '{profile_9_1765569802.jpg}', '454ca4de-79d3-4302-a8c0-4ea28126af61', NULL, '{}', 1),
('ade6bfe7-ef2c-4109-8529-f5d5fe05012e', 'profile_pictures', 'players/fernand_padel_be_1765124457.jpg', NULL, '2025-12-07 16:21:02.729666+00', '2025-12-07 16:21:02.729666+00', '2025-12-07 16:21:02.729666+00', '{"eTag": "\"1b69b88c136a3bce8665d067074e40db\"", "size": 730478, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T16:21:03.000Z", "contentLength": 730478, "httpStatusCode": 200}', '{players,fernand_padel_be_1765124457.jpg}', '900e0601-4014-461f-a972-08e58f1c33da', NULL, '{}', 2),
('b54bdb8c-c5a7-43d3-b7b7-cafadfb58905', 'profile_pictures', 'players/test_test_gmail_com_1765755969.png', NULL, '2025-12-14 23:46:12.050769+00', '2025-12-14 23:46:12.050769+00', '2025-12-14 23:46:12.050769+00', '{"eTag": "\"3d20f40f121c8975a134318e72718974\"", "size": 30401, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-14T23:46:12.000Z", "contentLength": 30401, "httpStatusCode": 200}', '{players,test_test_gmail_com_1765755969.png}', '55ed7f07-d2be-4400-81ef-c92b2df60ebc', NULL, '{}', 2),
('be31ce2f-dce3-43be-9f09-901b14354677', 'profile_pictures', 'players/thomas_carlier_telenet_be_1765646701.jpeg', NULL, '2025-12-13 17:25:01.69386+00', '2025-12-13 17:25:01.69386+00', '2025-12-13 17:25:01.69386+00', '{"eTag": "\"68713042c99f251990ad7c81d1dedf50\"", "size": 135387, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-13T17:25:02.000Z", "contentLength": 135387, "httpStatusCode": 200}', '{players,thomas_carlier_telenet_be_1765646701.jpeg}', '0e832894-c9b2-4d62-abb2-f726c08ad11e', NULL, '{}', 2),
('cc382157-df6b-4222-8e8e-3edefbf19ca8', 'profile_pictures', 'profile_47_1765558064.png', NULL, '2025-12-12 16:47:51.198532+00', '2025-12-12 16:47:51.198532+00', '2025-12-12 16:47:51.198532+00', '{"eTag": "\"e64042e3a2a6537425f2221b1e445ca2\"", "size": 3156639, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T16:47:52.000Z", "contentLength": 3156639, "httpStatusCode": 200}', '{profile_47_1765558064.png}', 'd911ccc4-7751-4174-b273-91dabed8b929', NULL, '{}', 1),
('cd30db81-7c60-40d5-9e94-7dee516d7a2b', 'profile_pictures', 'coaches/riete_coach_be_1765623691.png', NULL, '2025-12-13 11:01:31.426367+00', '2025-12-13 11:01:31.426367+00', '2025-12-13 11:01:31.426367+00', '{"eTag": "\"281ac9bd75703703e7a9b75b744d3210\"", "size": 64946, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-13T11:01:32.000Z", "contentLength": 64946, "httpStatusCode": 200}', '{coaches,riete_coach_be_1765623691.png}', '4ef92f8a-0d8f-47a0-9405-4c642f372d65', NULL, '{}', 2),
('cdb17f6b-8d3d-41a3-8d6f-18cea9d33d38', 'profile_pictures', 'coaches/jan_cornelis_padel_be_1765568824.jpg', NULL, '2025-12-12 19:47:07.801417+00', '2025-12-12 19:47:07.801417+00', '2025-12-12 19:47:07.801417+00', '{"eTag": "\"b3eeac814b3f01c46b54bb3df974a9db\"", "size": 31924, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-12T19:47:08.000Z", "contentLength": 31924, "httpStatusCode": 200}', '{coaches,jan_cornelis_padel_be_1765568824.jpg}', '50a81e87-0de0-4816-ba7f-dd31408487d3', NULL, '{}', 2),
('d05f4f4d-83ce-459c-b747-5ed644176c6f', 'profile_pictures', 'players/vince_claessens_padel_be_1765400169.webp', NULL, '2025-12-10 20:56:11.84156+00', '2025-12-10 20:56:11.84156+00', '2025-12-10 20:56:11.84156+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-10T20:56:12.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{players,vince_claessens_padel_be_1765400169.webp}', 'c0d88e9b-c33b-4e40-ae67-609684be5f46', NULL, '{}', 2),
('e7355035-aca1-467d-b669-872c3f79faa6', 'profile_pictures', 'players/adriaan_v_padel_be_1765754168.jpg', NULL, '2025-12-14 23:16:11.210014+00', '2025-12-14 23:16:11.210014+00', '2025-12-14 23:16:11.210014+00', '{"eTag": "\"cc9777880e96d84f4a00a3ee75bf0013\"", "size": 210024, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-14T23:16:12.000Z", "contentLength": 210024, "httpStatusCode": 200}', '{players,adriaan_v_padel_be_1765754168.jpg}', 'e1226422-4b24-46c8-9b86-8e99bfe8b280', NULL, '{}', 2),
('e7401a62-42ef-48a5-ab93-9fed37011936', 'profile_pictures', 'coaches/roberto_martinez_padel_be_1765124913.jpg', NULL, '2025-12-07 16:28:38.156271+00', '2025-12-07 16:28:38.156271+00', '2025-12-07 16:28:38.156271+00', '{"eTag": "\"cc9777880e96d84f4a00a3ee75bf0013\"", "size": 210024, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-07T16:28:39.000Z", "contentLength": 210024, "httpStatusCode": 200}', '{coaches,roberto_martinez_padel_be_1765124913.jpg}', 'c62a65e1-2810-47fa-836e-3a83a26ab711', NULL, '{}', 2),
('e791c0ab-570f-47d0-bd86-d974b984006e', 'profile_pictures', 'players/phebe_gmail_com_1765313628.png', NULL, '2025-12-09 20:53:49.692018+00', '2025-12-09 20:53:49.692018+00', '2025-12-09 20:53:49.692018+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-09T20:53:50.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,phebe_gmail_com_1765313628.png}', 'cde6127c-c110-476f-941e-e2718833415f', NULL, '{}', 2),
('ea80bbf3-f98f-4f55-af9c-6463b8efebbb', 'profile_pictures', 'players/maxv_gmail_com_1765190384.jpg', NULL, '2025-12-08 10:39:45.270827+00', '2025-12-08 10:39:45.270827+00', '2025-12-08 10:39:45.270827+00', '{"eTag": "\"46795f74f1d1f9cdad433cc1e3e4e470\"", "size": 509659, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T10:39:46.000Z", "contentLength": 509659, "httpStatusCode": 200}', '{players,maxv_gmail_com_1765190384.jpg}', '79543e47-680b-406c-9698-937c5d035105', NULL, '{}', 2),
('f02111db-f987-4171-a6dd-7722be4a0951', 'profile_pictures', 'players/boma_gmail_com_1765190102.png', NULL, '2025-12-08 10:35:07.295178+00', '2025-12-08 10:35:07.295178+00', '2025-12-08 10:35:07.295178+00', '{"eTag": "\"70aed8581c684e97474edcda22f3db4b\"", "size": 511064, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-08T10:35:08.000Z", "contentLength": 511064, "httpStatusCode": 200}', '{players,boma_gmail_com_1765190102.png}', 'c4bfb380-171d-413b-ad68-48aae1700954', NULL, '{}', 2),
('f4deaa21-193e-45ae-8e02-eb0613eeb1e8', 'profile_pictures', 'player_jan.verthongenj@padel.be.jpg', NULL, '2025-12-07 15:55:33.074765+00', '2025-12-07 15:55:33.074765+00', '2025-12-07 15:55:33.074765+00', '{"eTag": "\"1b69b88c136a3bce8665d067074e40db\"", "size": 730478, "mimetype": "image/jpeg", "cacheControl": "no-cache", "lastModified": "2025-12-07T15:55:33.000Z", "contentLength": 730478, "httpStatusCode": 200}', '{player_jan.verthongenj@padel.be.jpg}', '2e5c8fcd-4a25-4d38-a22e-1fd880963874', NULL, '{}', 1),
('f930065f-da8b-4a35-9be1-491e540ac114', 'profile_pictures', 'profile_7_1765275638.png', NULL, '2025-12-09 10:20:38.667863+00', '2025-12-09 10:20:38.667863+00', '2025-12-09 10:20:38.667863+00', '{"eTag": "\"c069f5377603a2bad90c07d6af0a7aea\"", "size": 78425, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-09T10:20:39.000Z", "contentLength": 78425, "httpStatusCode": 200}', '{profile_7_1765275638.png}', '87d2ee1f-cfaf-446f-8486-358b9831fe70', NULL, '{}', 1),
('f9796df8-43cf-4ef0-be08-5e7e96288226', 'profile_pictures', 'coaches/riete_coach_be_1765623646.png', NULL, '2025-12-13 11:00:47.361545+00', '2025-12-13 11:00:47.361545+00', '2025-12-13 11:00:47.361545+00', '{"eTag": "\"281ac9bd75703703e7a9b75b744d3210\"", "size": 64946, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-13T11:00:48.000Z", "contentLength": 64946, "httpStatusCode": 200}', '{coaches,riete_coach_be_1765623646.png}', '02c6db8f-3522-44a2-bebd-d5f19b9faaf8', NULL, '{}', 2),
('fb1b8564-343d-4631-a6db-dd8c76f419b6', 'profile_pictures', 'coaches/jan_vdb_padel_be_1765884407.webp', NULL, '2025-12-16 11:26:51.823732+00', '2025-12-16 11:26:51.823732+00', '2025-12-16 11:26:51.823732+00', '{"eTag": "\"83f1f0f3e21613d5e50427b2f8859a8d\"", "size": 24168, "mimetype": "text/plain", "cacheControl": "no-cache", "lastModified": "2025-12-16T11:26:52.000Z", "contentLength": 24168, "httpStatusCode": 200}', '{coaches,jan_vdb_padel_be_1765884407.webp}', '0db7b860-2d23-4706-b412-c2a45d239a66', NULL, '{}', 2);
INSERT INTO "storage"."migrations" ("id", "name", "hash", "executed_at") VALUES
(0, 'create-migrations-table', 'e18db593bcde2aca2a408c4d1100f6abba2195df', '2025-10-29 22:18:21.076831'),
(1, 'initialmigration', '6ab16121fbaa08bbd11b712d05f358f9b555d777', '2025-10-29 22:18:21.088286'),
(2, 'storage-schema', '5c7968fd083fcea04050c1b7f6253c9771b99011', '2025-10-29 22:18:21.093589'),
(3, 'pathtoken-column', '2cb1b0004b817b29d5b0a971af16bafeede4b70d', '2025-10-29 22:18:21.161594'),
(4, 'add-migrations-rls', '427c5b63fe1c5937495d9c635c263ee7a5905058', '2025-10-29 22:18:21.23425'),
(5, 'add-size-functions', '79e081a1455b63666c1294a440f8ad4b1e6a7f84', '2025-10-29 22:18:21.23853'),
(6, 'change-column-name-in-get-size', 'f93f62afdf6613ee5e7e815b30d02dc990201044', '2025-10-29 22:18:21.244644'),
(7, 'add-rls-to-buckets', 'e7e7f86adbc51049f341dfe8d30256c1abca17aa', '2025-10-29 22:18:21.249916'),
(8, 'add-public-to-buckets', 'fd670db39ed65f9d08b01db09d6202503ca2bab3', '2025-10-29 22:18:21.253339'),
(9, 'fix-search-function', '3a0af29f42e35a4d101c259ed955b67e1bee6825', '2025-10-29 22:18:21.260683'),
(10, 'search-files-search-function', '68dc14822daad0ffac3746a502234f486182ef6e', '2025-10-29 22:18:21.268663'),
(11, 'add-trigger-to-auto-update-updated_at-column', '7425bdb14366d1739fa8a18c83100636d74dcaa2', '2025-10-29 22:18:21.275425'),
(12, 'add-automatic-avif-detection-flag', '8e92e1266eb29518b6a4c5313ab8f29dd0d08df9', '2025-10-29 22:18:21.286824'),
(13, 'add-bucket-custom-limits', 'cce962054138135cd9a8c4bcd531598684b25e7d', '2025-10-29 22:18:21.293242'),
(14, 'use-bytes-for-max-size', '941c41b346f9802b411f06f30e972ad4744dad27', '2025-10-29 22:18:21.296796'),
(15, 'add-can-insert-object-function', '934146bc38ead475f4ef4b555c524ee5d66799e5', '2025-10-29 22:18:21.329283'),
(16, 'add-version', '76debf38d3fd07dcfc747ca49096457d95b1221b', '2025-10-29 22:18:21.33462'),
(17, 'drop-owner-foreign-key', 'f1cbb288f1b7a4c1eb8c38504b80ae2a0153d101', '2025-10-29 22:18:21.337774'),
(18, 'add_owner_id_column_deprecate_owner', 'e7a511b379110b08e2f214be852c35414749fe66', '2025-10-29 22:18:21.34372'),
(19, 'alter-default-value-objects-id', '02e5e22a78626187e00d173dc45f58fa66a4f043', '2025-10-29 22:18:21.348868'),
(20, 'list-objects-with-delimiter', 'cd694ae708e51ba82bf012bba00caf4f3b6393b7', '2025-10-29 22:18:21.354064'),
(21, 's3-multipart-uploads', '8c804d4a566c40cd1e4cc5b3725a664a9303657f', '2025-10-29 22:18:21.359938'),
(22, 's3-multipart-uploads-big-ints', '9737dc258d2397953c9953d9b86920b8be0cdb73', '2025-10-29 22:18:21.38182'),
(23, 'optimize-search-function', '9d7e604cddc4b56a5422dc68c9313f4a1b6f132c', '2025-10-29 22:18:21.396206'),
(24, 'operation-function', '8312e37c2bf9e76bbe841aa5fda889206d2bf8aa', '2025-10-29 22:18:21.401073'),
(25, 'custom-metadata', 'd974c6057c3db1c1f847afa0e291e6165693b990', '2025-10-29 22:18:21.404146'),
(26, 'objects-prefixes', 'ef3f7871121cdc47a65308e6702519e853422ae2', '2025-10-29 22:18:21.407578'),
(27, 'search-v2', '33b8f2a7ae53105f028e13e9fcda9dc4f356b4a2', '2025-10-29 22:18:21.418421'),
(28, 'object-bucket-name-sorting', 'ba85ec41b62c6a30a3f136788227ee47f311c436', '2025-10-29 22:18:22.068345'),
(29, 'create-prefixes', 'a7b1a22c0dc3ab630e3055bfec7ce7d2045c5b7b', '2025-10-29 22:18:22.07558'),
(30, 'update-object-levels', '6c6f6cc9430d570f26284a24cf7b210599032db7', '2025-10-29 22:18:22.081152'),
(31, 'objects-level-index', '33f1fef7ec7fea08bb892222f4f0f5d79bab5eb8', '2025-10-29 22:18:22.088662'),
(32, 'backward-compatible-index-on-objects', '2d51eeb437a96868b36fcdfb1ddefdf13bef1647', '2025-10-29 22:18:22.095577'),
(33, 'backward-compatible-index-on-prefixes', 'fe473390e1b8c407434c0e470655945b110507bf', '2025-10-29 22:18:22.103173'),
(34, 'optimize-search-function-v1', '82b0e469a00e8ebce495e29bfa70a0797f7ebd2c', '2025-10-29 22:18:22.104785'),
(35, 'add-insert-trigger-prefixes', '63bb9fd05deb3dc5e9fa66c83e82b152f0caf589', '2025-10-29 22:18:22.109719'),
(36, 'optimise-existing-functions', '81cf92eb0c36612865a18016a38496c530443899', '2025-10-29 22:18:22.112969'),
(37, 'add-bucket-name-length-trigger', '3944135b4e3e8b22d6d4cbb568fe3b0b51df15c1', '2025-10-29 22:18:22.120055'),
(38, 'iceberg-catalog-flag-on-buckets', '19a8bd89d5dfa69af7f222a46c726b7c41e462c5', '2025-10-29 22:18:22.123938'),
(39, 'add-search-v2-sort-support', '39cf7d1e6bf515f4b02e41237aba845a7b492853', '2025-10-29 22:18:22.134487'),
(40, 'fix-prefix-race-conditions-optimized', 'fd02297e1c67df25a9fc110bf8c8a9af7fb06d1f', '2025-10-29 22:18:22.138477'),
(41, 'add-object-level-update-trigger', '44c22478bf01744b2129efc480cd2edc9a7d60e9', '2025-10-29 22:18:22.145671'),
(42, 'rollback-prefix-triggers', 'f2ab4f526ab7f979541082992593938c05ee4b47', '2025-10-29 22:18:22.150486'),
(43, 'fix-object-level', 'ab837ad8f1c7d00cc0b7310e989a23388ff29fc6', '2025-10-29 22:18:22.155602'),
(44, 'vector-bucket-type', '99c20c0ffd52bb1ff1f32fb992f3b351e3ef8fb3', '2025-11-20 11:51:44.627688'),
(45, 'vector-buckets', '049e27196d77a7cb76497a85afae669d8b230953', '2025-11-20 11:51:44.66535'),
(46, 'buckets-objects-grants', 'fedeb96d60fefd8e02ab3ded9fbde05632f84aed', '2025-11-20 11:51:44.765785'),
(47, 'iceberg-table-metadata', '649df56855c24d8b36dd4cc1aeb8251aa9ad42c2', '2025-11-20 11:51:44.775631'),
(48, 'iceberg-catalog-ids', '2666dff93346e5d04e0a878416be1d5fec345d6f', '2025-11-20 11:51:44.783898'),
(49, 'buckets-objects-grants-postgres', '072b1195d0d5a2f888af6b2302a1938dd94b8b3d', '2025-12-19 09:40:31.697222');




INSERT INTO "storage"."prefixes" ("bucket_id", "name", "level", "created_at", "updated_at") VALUES
('profile_pictures', 'coaches', 1, '2025-12-07 16:28:38.156271+00', '2025-12-07 16:28:38.156271+00'),
('profile_pictures', 'players', 1, '2025-12-07 16:21:02.729666+00', '2025-12-07 16:21:02.729666+00');



