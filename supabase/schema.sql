-- Monitor System: run once in Supabase Dashboard → SQL Editor.
-- Stores only the latest snapshot per device (no history).

create table if not exists public.device_metrics (
  device_id  text primary key,
  data       jsonb not null,
  updated_at timestamptz not null default now()
);

-- Emails allowed to read metrics. Add rows in Table Editor (never commit emails to the repo):
--   insert into public.allowed_viewers (email) values ('you@example.com');
create table if not exists public.allowed_viewers (
  email text primary key
);

alter table public.device_metrics  enable row level security;
alter table public.allowed_viewers enable row level security;
-- allowed_viewers has no policies: clients can neither read nor change it.

-- security definer so the check can read allowed_viewers despite its RLS.
create or replace function public.is_allowed_viewer()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.allowed_viewers
    where lower(email) = lower(auth.jwt() ->> 'email')
  );
$$;

revoke execute on function public.is_allowed_viewer() from public, anon;
grant  execute on function public.is_allowed_viewer() to authenticated;

drop policy if exists "allowed viewers can read metrics" on public.device_metrics;
create policy "allowed viewers can read metrics"
  on public.device_metrics for select
  to authenticated
  using (public.is_allowed_viewer());

-- No insert/update/delete policies: only the agent's secret key (bypasses RLS) can write.
