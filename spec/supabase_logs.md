| column_name     | data_type                   | character_maximum_length | is_nullable | column_default                        |
| --------------- | --------------------------- | ------------------------ | ----------- | ------------------------------------- |
| id              | integer                     | null                     | NO          | nextval('chat_logs_id_seq'::regclass) |
| model_used      | character varying           | 50                       | YES         | null                                  |
| prompt          | text                        | null                     | YES         | null                                  |
| reply           | text                        | null                     | YES         | null                                  |
| prompt_tokens   | integer                     | null                     | YES         | null                                  |
| response_tokens | integer                     | null                     | YES         | null                                  |
| total_tokens    | integer                     | null                     | YES         | null                                  |
| client_ip       | character varying           | 50                       | YES         | null                                  |
| conversation_id | uuid                        | null                     | YES         | null                                  |
| created_at      | timestamp without time zone | null                     | YES         | now()                                 |
| api             | character varying           | null                     | YES         | null                                  |

`conversation_id` agrupa las consultas de una ventana de chat. El cliente debe
reutilizar el UUID devuelto por la API en las siguientes peticiones. Para
instalaciones existentes, añadir la columna nullable y un índice para recuperar
el historial:

```sql
ALTER TABLE chat_logs
ADD COLUMN IF NOT EXISTS conversation_id UUID NULL;

CREATE INDEX IF NOT EXISTS idx_chat_logs_conversation_id_created_at
ON chat_logs (conversation_id, created_at DESC, id DESC);
```