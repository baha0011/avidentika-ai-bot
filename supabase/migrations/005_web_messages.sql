create table if not exists public.web_messages (
  id bigserial primary key,
  web_session_id text not null,
  public_id text,
  kind text not null,
  event_type text not null,
  message text not null,
  created_at timestamptz not null default now()
);

create index if not exists web_messages_session_id_idx
  on public.web_messages(web_session_id, id);

create index if not exists web_messages_public_id_idx
  on public.web_messages(public_id);
