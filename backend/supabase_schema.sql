-- Run in Supabase: SQL Editor -> New query -> paste -> Run
create extension if not exists "pgcrypto";

create table if not exists public.analyses (
  id          uuid primary key default gen_random_uuid(),
  url         text not null,
  platform    text,
  handle      text,
  profile     jsonb not null default '{}'::jsonb,
  posts       jsonb not null default '[]'::jsonb,
  result      jsonb not null,
  created_at  timestamptz not null default now()
);

create index if not exists analyses_handle_created_idx on public.analyses (handle, created_at desc);

-- The API uses the service-role key (server only). Lock the table from browsers entirely.
alter table public.analyses enable row level security;
