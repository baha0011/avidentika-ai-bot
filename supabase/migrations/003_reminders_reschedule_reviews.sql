alter table public.appointments add column if not exists confirmed_start_at timestamptz;
alter table public.appointments add column if not exists reminder_24h_sent_at timestamptz;
alter table public.appointments add column if not exists client_confirmation_status text not null default 'pending';
alter table public.appointments add column if not exists reschedule_requested_at timestamptz;
alter table public.appointments add column if not exists rating_requested_at timestamptz;
alter table public.appointments add column if not exists rating smallint;
alter table public.appointments add column if not exists review text;
alter table public.appointments add column if not exists reviewed_at timestamptz;

alter table public.appointments drop constraint if exists appointments_client_confirmation_status_check;
alter table public.appointments add constraint appointments_client_confirmation_status_check
  check (client_confirmation_status in ('pending', 'confirmed', 'reschedule_requested', 'cancelled'));
alter table public.appointments drop constraint if exists appointments_rating_check;
alter table public.appointments add constraint appointments_rating_check check (rating between 1 and 5);
alter table public.appointments drop constraint if exists appointments_review_check;
alter table public.appointments add constraint appointments_review_check check (review is null or char_length(review) <= 2000);

create index if not exists appointments_confirmed_start_idx
  on public.appointments(confirmed_start_at) where status = 'confirmed';
