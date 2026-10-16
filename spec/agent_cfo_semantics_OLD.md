# CFO agent data semantics

This catalog documents the business meaning and query conventions used by the
CFO agent. Database structure and deployed foreign keys are recorded separately
in `schema_col_type_null.sql` and `schema_foreing_keys.sql`.

## Relationships

- `ventas.id_cliente` references `clientes.id_cliente`.
- `ventas.id_prod` references `productos.id_prod`.
- `compras.id_prov_compo` references `proveedores_compo.id_prov_compo`.
- `compras.id_compo` references `componentes.id_compo`.
- `stock_prod.id_prod` references `productos.id_prod`.
- `stock_prod.id_alm` references `almacen.id_alm`.
- `stock_compo.id_compo` references `componentes.id_compo`.
- `stock_compo.id_alm` references `almacen.id_alm`.
- `intervenciones.id_prod` references `productos.id_prod`.
- `intervenciones.id_serv` references `servicios_intervencion.id_servicio`.
- `intervenciones.id_estado` references `estados_intervencion.id_estado`.
- `intervenciones.id_cliente` references `clientes.id_cliente`.
- `intervenciones.id_establecimiento` references
  `establecimientos.id_establecimiento`.
- `intervenciones.id_pro_serv` references `proveedores_serv.id_pro_serv`.
- `document_chunks.document_id` references `documentos.id_documento`.

## Business definitions

- A row in `ventas` is one sales transaction.
- `ventas.total_venta` is the transaction amount; `ventas.unidades` is the
  quantity sold; `ventas.fecha_venta` is its date.
- A row in `compras` is one purchase transaction.
- `compras.total_compra` is the transaction amount;
  `compras.unidades_compra` is the purchased quantity; `compras.fecha_compra`
  is its date.
- Product, component, customer, supplier, warehouse, service and establishment
  names are labels. Their IDs are the join keys.
- Stock is represented per product/component and warehouse, not as one row per
  item across all warehouses.
- `intervenciones.fecha_int` is the intervention date and `fecha_aviso` is the
  notice date.

## Query behavior

- Phrases such as "dime", "lista" or "muestra las ventas del cliente" request
  individual transactions. The agent resolves the customer name first, then
  retrieves that customer's sales and product names.
- Requests for a sales total, amount, count or summary use an aggregate report
  filtered by customer. "Number of sales" means transaction count, not units.
- The detailed customer-sales tool prefers a case-insensitive exact name. If
  there is no exact match, a unique substring match can be used. Multiple exact
  or partial matches are returned as ambiguous; their sales are not combined.
- A customer-filtered aggregate labels each result with the customer name, so
  partial name matches remain separate groups rather than being merged.
- A customer with no matching sales is distinct from a customer that could not
  be found.
- Detail queries include date bounds inclusively when supplied, return newest
  sales first, and page through at most 50 rows. A response at that maximum
  must disclose that it may be incomplete.
- A missing product relationship does not discard a sale; its product name is
  returned as null. Sales without a customer cannot belong to a customer-name
  query and are therefore not included.
- Reads are performed by predefined, read-only RPCs. The model must not create
  SQL or infer results not present in returned evidence.

## Scope

This is the initial semantic contract for CFO data access, with customer sales
as the first name-resolved detail tool. Add or revise definitions when new
business metrics or query tools are introduced. It is not a promise that every
arbitrary business question can be answered without clarification.
