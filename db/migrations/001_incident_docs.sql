-- db/migrations/001_incident_docs.sql
create extension if not exists vector;

create table if not exists incident_docs (
    id bigserial primary key,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(768) not null
);

-- Unique constraint for idempotency
create unique index if not exists incident_docs_content_idx on incident_docs (md5(content));

create or replace function match_incident_docs (
  query_embedding vector(768),
  match_count int,
  filter jsonb
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    incident_docs.id,
    incident_docs.content,
    incident_docs.metadata,
    1 - (incident_docs.embedding <=> query_embedding) as similarity
  from incident_docs
  where incident_docs.metadata @> filter
  order by incident_docs.embedding <=> query_embedding
  limit match_count;
end;
$$;
