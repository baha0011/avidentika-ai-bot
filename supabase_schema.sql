-- AVIDENTIKA AI administrator schema for Supabase/PostgreSQL
create extension if not exists pgcrypto;
create extension if not exists vector;

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  telegram_user_id bigint not null unique,
  username text,
  first_name text,
  last_name text,
  preferred_language text not null default 'uk' check (preferred_language in ('uk', 'ru')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.appointments (
  id uuid primary key default gen_random_uuid(),
  public_id text not null unique check (public_id ~ '^A-[A-F0-9]{8}$'),
  user_id uuid not null references public.profiles(id) on delete restrict,
  patient_name text not null check (char_length(patient_name) between 2 and 80),
  phone text not null check (phone ~ '^\+380[0-9]{9}$'),
  service text not null check (char_length(service) between 1 and 200),
  preferred_date text,
  preferred_time text,
  comment text check (comment is null or char_length(comment) <= 500),
  confirmed_date text,
  confirmed_time text,
  confirmed_service text,
  confirmed_doctor text,
  confirmation_comment text,
  confirmed_at timestamptz,
  confirmed_start_at timestamptz,
  reminder_24h_sent_at timestamptz,
  client_confirmation_status text not null default 'pending' check (client_confirmation_status in ('pending', 'confirmed', 'reschedule_requested', 'cancelled')),
  reschedule_requested_at timestamptz,
  rating_requested_at timestamptz,
  rating smallint check (rating between 1 and 5),
  review text check (review is null or char_length(review) <= 2000),
  reviewed_at timestamptz,
  status text not null default 'new' check (status in ('new', 'in_progress', 'confirmed', 'closed', 'cancelled')),
  assigned_admin_telegram_id bigint,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  closed_at timestamptz
);

create table if not exists public.support_requests (
  id uuid primary key default gen_random_uuid(),
  public_id text not null unique check (public_id ~ '^S-[A-F0-9]{8}$'),
  user_id uuid not null references public.profiles(id) on delete restrict,
  patient_name text not null check (char_length(patient_name) between 2 and 80),
  phone text not null check (phone ~ '^\+380[0-9]{9}$'),
  question text not null check (char_length(question) between 3 and 1000),
  status text not null default 'new' check (status in ('new', 'in_progress', 'closed', 'cancelled')),
  assigned_admin_telegram_id bigint,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  closed_at timestamptz
);

create table if not exists public.conversations (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  message text not null check (char_length(message) <= 1000),
  language text not null check (language in ('uk', 'ru')),
  source_urls text[] not null default '{}',
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.knowledge_documents (
  id bigint generated always as identity primary key,
  source_url text not null,
  page_title text not null,
  content text not null,
  content_hash text not null check (char_length(content_hash) = 64),
  language text not null default 'uk' check (language in ('uk', 'ru')),
  embedding vector(1536),
  is_active boolean not null default true,
  scraped_at timestamptz not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (source_url, content_hash)
);

create table if not exists public.knowledge_update_logs (
  id bigint generated always as identity primary key,
  status text not null check (status in ('running', 'success', 'partial', 'failed')),
  pages_found integer not null default 0 check (pages_found >= 0),
  pages_updated integer not null default 0 check (pages_updated >= 0),
  pages_failed integer not null default 0 check (pages_failed >= 0),
  error_details text,
  started_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz
);

create index if not exists profiles_telegram_user_id_idx on public.profiles(telegram_user_id);
create index if not exists appointments_status_idx on public.appointments(status, created_at desc);
create index if not exists support_requests_status_idx on public.support_requests(status, created_at desc);
create index if not exists knowledge_source_url_idx on public.knowledge_documents(source_url);
create index if not exists knowledge_active_idx on public.knowledge_documents(is_active) where is_active;
create index if not exists knowledge_content_fts_idx
  on public.knowledge_documents using gin (to_tsvector('simple', coalesce(content, '')));
create index if not exists knowledge_embedding_hnsw_idx
  on public.knowledge_documents using hnsw (embedding vector_cosine_ops);

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function public.set_updated_at();
drop trigger if exists appointments_set_updated_at on public.appointments;
create trigger appointments_set_updated_at before update on public.appointments
for each row execute function public.set_updated_at();
drop trigger if exists support_set_updated_at on public.support_requests;
create trigger support_set_updated_at before update on public.support_requests
for each row execute function public.set_updated_at();
drop trigger if exists knowledge_set_updated_at on public.knowledge_documents;
create trigger knowledge_set_updated_at before update on public.knowledge_documents
for each row execute function public.set_updated_at();

create or replace function public.match_knowledge_documents(
  query_embedding vector(1536),
  match_threshold double precision default 0.72,
  match_count integer default 6
)
returns table (
  id bigint,
  source_url text,
  page_title text,
  content text,
  similarity double precision
)
language sql stable
set search_path = public
as $$
  select d.id, d.source_url, d.page_title, d.content,
         (1 - (d.embedding <=> query_embedding))::double precision as similarity
  from public.knowledge_documents d
  where d.is_active = true
    and d.embedding is not null
    and 1 - (d.embedding <=> query_embedding) >= match_threshold
  order by d.embedding <=> query_embedding
  limit greatest(1, least(match_count, 20));
$$;

create or replace function public.search_knowledge_documents(
  search_query text,
  result_limit integer default 6
)
returns table (
  id bigint,
  source_url text,
  page_title text,
  content text,
  rank real
)
language sql stable
set search_path = public
as $$
  select d.id, d.source_url, d.page_title, d.content,
         ts_rank_cd(to_tsvector('simple', coalesce(d.content, '')), websearch_to_tsquery('simple', search_query)) as rank
  from public.knowledge_documents d
  where d.is_active = true
    and to_tsvector('simple', coalesce(d.content, '')) @@ websearch_to_tsquery('simple', search_query)
  order by rank desc
  limit greatest(1, least(result_limit, 20));
$$;

alter table public.profiles enable row level security;
alter table public.appointments enable row level security;
alter table public.support_requests enable row level security;
alter table public.conversations enable row level security;
alter table public.knowledge_documents enable row level security;
alter table public.knowledge_update_logs enable row level security;

-- No anon/authenticated policies are intentionally created. The server-side service_role
-- bypasses RLS; browser and mobile clients receive no access.
revoke all on table public.profiles, public.appointments, public.support_requests,
  public.conversations, public.knowledge_documents, public.knowledge_update_logs from anon, authenticated;
revoke execute on function public.match_knowledge_documents(vector, double precision, integer) from public, anon, authenticated;
revoke execute on function public.search_knowledge_documents(text, integer) from public, anon, authenticated;
grant execute on function public.match_knowledge_documents(vector, double precision, integer) to service_role;
grant execute on function public.search_knowledge_documents(text, integer) to service_role;
