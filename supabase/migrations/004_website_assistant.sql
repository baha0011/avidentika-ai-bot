-- Website AI assistant extension. Safe to run after 001-003 migrations.

alter table public.profiles
  alter column telegram_user_id drop not null;

alter table public.profiles
  add column if not exists web_session_id text;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'profiles_web_session_id_key'
  ) then
    alter table public.profiles add constraint profiles_web_session_id_key unique (web_session_id);
  end if;
end $$;

alter table public.appointments
  add column if not exists source text not null default 'telegram' check (source in ('telegram', 'website')),
  add column if not exists web_session_id text,
  add column if not exists contact_method text,
  add column if not exists telegram_username text,
  add column if not exists doctor text,
  add column if not exists user_agent text,
  add column if not exists created_from_url text;

alter table public.support_requests
  add column if not exists source text not null default 'telegram' check (source in ('telegram', 'website')),
  add column if not exists web_session_id text,
  add column if not exists contact_method text,
  add column if not exists telegram_username text,
  add column if not exists user_agent text,
  add column if not exists created_from_url text;

create index if not exists appointments_source_status_idx
  on public.appointments(source, status, created_at desc);

create index if not exists appointments_web_session_id_idx
  on public.appointments(web_session_id)
  where web_session_id is not null;

create index if not exists support_requests_source_status_idx
  on public.support_requests(source, status, created_at desc);

create index if not exists support_requests_web_session_id_idx
  on public.support_requests(web_session_id)
  where web_session_id is not null;
