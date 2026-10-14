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
| created_at      | timestamp without time zone | null                     | YES         | now()                                 |
| api             | character varying           | null                     | YES         | null                                  |