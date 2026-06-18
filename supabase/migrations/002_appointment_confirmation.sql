-- Adds persistent confirmed appointment details to an existing Supabase project.
alter table public.appointments add column if not exists confirmed_date text;
alter table public.appointments add column if not exists confirmed_time text;
alter table public.appointments add column if not exists confirmed_service text;
alter table public.appointments add column if not exists confirmed_doctor text;
alter table public.appointments add column if not exists confirmation_comment text;
alter table public.appointments add column if not exists confirmed_at timestamptz;

alter table public.appointments drop constraint if exists appointments_status_check;
alter table public.appointments
  add constraint appointments_status_check
  check (status in ('new', 'in_progress', 'confirmed', 'closed', 'cancelled'));
