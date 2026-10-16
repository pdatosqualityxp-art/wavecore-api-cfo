| table_schema | table_name             | ordinal_position | column_name               | data_type                | udt_name    | is_nullable | column_default                              |
| ------------ | ---------------------- | ---------------- | ------------------------- | ------------------------ | ----------- | ----------- | ------------------------------------------- |
| public       | almacen                | 1                | id_alm                    | character varying        | varchar     | NO          | null                                        |
| public       | almacen                | 2                | nom_alm                   | character varying        | varchar     | NO          | null                                        |
| public       | almacen                | 3                | poblacion_alm             | character varying        | varchar     | NO          | null                                        |
| public       | almacen                | 4                | pais_alm                  | character varying        | varchar     | NO          | null                                        |
| public       | clientes               | 1                | id_cliente                | character varying        | varchar     | NO          | null                                        |
| public       | clientes               | 2                | nom_cliente               | character varying        | varchar     | NO          | null                                        |
| public       | clientes               | 3                | poblacion_cliente         | character varying        | varchar     | NO          | null                                        |
| public       | clientes               | 4                | pais_cliente              | character varying        | varchar     | NO          | null                                        |
| public       | componentes            | 1                | id_compo                  | character varying        | varchar     | NO          | null                                        |
| public       | componentes            | 2                | nom_compo                 | character varying        | varchar     | NO          | null                                        |
| public       | componentes            | 3                | desc_compo                | text                     | text        | YES         | null                                        |
| public       | componentes            | 4                | precio_compo              | numeric                  | numeric     | NO          | null                                        |
| public       | compras                | 1                | id_compra                 | character varying        | varchar     | NO          | null                                        |
| public       | compras                | 2                | id_prov_compo             | character varying        | varchar     | YES         | null                                        |
| public       | compras                | 3                | id_compo                  | character varying        | varchar     | YES         | null                                        |
| public       | compras                | 4                | unidades_compra           | integer                  | int4        | NO          | null                                        |
| public       | compras                | 5                | precio_unidad             | numeric                  | numeric     | NO          | null                                        |
| public       | compras                | 6                | total_compra              | numeric                  | numeric     | NO          | null                                        |
| public       | compras                | 7                | fecha_compra              | date                     | date        | NO          | null                                        |
| public       | document_chunks        | 1                | id                        | integer                  | int4        | NO          | nextval('document_chunks_id_seq'::regclass) |
| public       | document_chunks        | 2                | document_id               | character varying        | varchar     | YES         | null                                        |
| public       | document_chunks        | 3                | chunk_text                | text                     | text        | NO          | null                                        |
| public       | document_chunks        | 4                | page_number               | integer                  | int4        | YES         | null                                        |
| public       | document_chunks        | 5                | embedding                 | USER-DEFINED             | vector      | YES         | null                                        |
| public       | documentos             | 1                | id_documento              | character varying        | varchar     | NO          | null                                        |
| public       | documentos             | 2                | titulo                    | character varying        | varchar     | NO          | null                                        |
| public       | documentos             | 3                | tipo_documento            | character varying        | varchar     | NO          | null                                        |
| public       | documentos             | 4                | departamento_origen       | character varying        | varchar     | NO          | null                                        |
| public       | documentos             | 5                | fecha_emision             | date                     | date        | NO          | null                                        |
| public       | documentos             | 6                | resumen_ejecutivo         | text                     | text        | YES         | null                                        |
| public       | documentos             | 7                | url_storage               | character varying        | varchar     | NO          | null                                        |
| public       | documentos             | 8                | created_at                | timestamp with time zone | timestamptz | YES         | now()                                       |
| public       | establecimientos       | 1                | id_establecimiento        | character varying        | varchar     | NO          | null                                        |
| public       | establecimientos       | 2                | establecimiento           | character varying        | varchar     | NO          | null                                        |
| public       | establecimientos       | 3                | poblacion_establecimiento | character varying        | varchar     | NO          | null                                        |
| public       | establecimientos       | 4                | pais_establecimiento      | character varying        | varchar     | NO          | null                                        |
| public       | estados_intervencion   | 1                | id_estado                 | character varying        | varchar     | NO          | null                                        |
| public       | estados_intervencion   | 2                | nom_estado                | character varying        | varchar     | NO          | null                                        |
| public       | estados_intervencion   | 3                | desc_estado               | text                     | text        | YES         | null                                        |
| public       | intervenciones         | 1                | id_int                    | character varying        | varchar     | NO          | null                                        |
| public       | intervenciones         | 2                | id_prod                   | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 3                | id_serv                   | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 4                | id_estado                 | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 5                | id_cliente                | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 6                | id_establecimiento        | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 7                | id_pro_serv               | character varying        | varchar     | YES         | null                                        |
| public       | intervenciones         | 8                | fecha_aviso               | date                     | date        | NO          | null                                        |
| public       | intervenciones         | 9                | fecha_int                 | date                     | date        | NO          | null                                        |
| public       | intervenciones         | 10               | tiempo_int                | numeric                  | numeric     | NO          | null                                        |
| public       | productos              | 1                | id_prod                   | character varying        | varchar     | NO          | null                                        |
| public       | productos              | 2                | nom_prod                  | character varying        | varchar     | NO          | null                                        |
| public       | productos              | 3                | desc_prod                 | text                     | text        | YES         | null                                        |
| public       | productos              | 4                | precio_prod               | numeric                  | numeric     | NO          | null                                        |
| public       | proveedores_compo      | 1                | id_prov_compo             | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_compo      | 2                | nom_prov_compo            | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_compo      | 3                | poblacion_prov_compo      | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_compo      | 4                | pais_prov_compo           | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_serv       | 1                | id_pro_serv               | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_serv       | 2                | nom_pro_serv              | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_serv       | 3                | poblacio_pro_serv         | character varying        | varchar     | NO          | null                                        |
| public       | proveedores_serv       | 4                | pais_pro_serv             | character varying        | varchar     | NO          | null                                        |
| public       | servicios_intervencion | 1                | id_servicio               | character varying        | varchar     | NO          | null                                        |
| public       | servicios_intervencion | 2                | nom_servicio              | character varying        | varchar     | NO          | null                                        |
| public       | servicios_intervencion | 3                | desc_servicio             | text                     | text        | YES         | null                                        |
| public       | servicios_intervencion | 4                | coste_servicio_prov       | numeric                  | numeric     | NO          | null                                        |
| public       | servicios_intervencion | 5                | ingreso_servicio_cli      | numeric                  | numeric     | NO          | null                                        |
| public       | stock_compo            | 1                | id_compo                  | character varying        | varchar     | NO          | null                                        |
| public       | stock_compo            | 2                | id_alm                    | character varying        | varchar     | NO          | null                                        |
| public       | stock_compo            | 3                | unidades                  | integer                  | int4        | NO          | null                                        |
| public       | stock_prod             | 1                | id_prod                   | character varying        | varchar     | NO          | null                                        |
| public       | stock_prod             | 2                | id_alm                    | character varying        | varchar     | NO          | null                                        |
| public       | stock_prod             | 3                | unidades                  | integer                  | int4        | NO          | null                                        |
| public       | ventas                 | 1                | id_venta                  | character varying        | varchar     | NO          | null                                        |
| public       | ventas                 | 2                | id_prod                   | character varying        | varchar     | YES         | null                                        |
| public       | ventas                 | 3                | id_cliente                | character varying        | varchar     | YES         | null                                        |
| public       | ventas                 | 4                | unidades                  | integer                  | int4        | NO          | null                                        |
| public       | ventas                 | 5                | precio_unidad             | numeric                  | numeric     | NO          | null                                        |
| public       | ventas                 | 6                | total_venta               | numeric                  | numeric     | NO          | null                                        |
| public       | ventas                 | 7                | fecha_venta               | date                     | date        | NO          | null                                        |