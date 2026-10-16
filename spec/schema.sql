## Table `clientes`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_cliente` | `varchar` | Primary |
| `nom_cliente` | `varchar` |  |
| `poblacion_cliente` | `varchar` |  |
| `pais_cliente` | `varchar` |  |

## Table `proveedores_compo`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_prov_compo` | `varchar` | Primary |
| `nom_prov_compo` | `varchar` |  |
| `poblacion_prov_compo` | `varchar` |  |
| `pais_prov_compo` | `varchar` |  |

## Table `proveedores_serv`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_pro_serv` | `varchar` | Primary |
| `nom_pro_serv` | `varchar` |  |
| `poblacio_pro_serv` | `varchar` |  |
| `pais_pro_serv` | `varchar` |  |

## Table `productos`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_prod` | `varchar` | Primary |
| `nom_prod` | `varchar` |  |
| `desc_prod` | `text` |  Nullable |
| `precio_prod` | `numeric` |  |

## Table `componentes`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_compo` | `varchar` | Primary |
| `nom_compo` | `varchar` |  |
| `desc_compo` | `text` |  Nullable |
| `precio_compo` | `numeric` |  |

## Table `almacen`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_alm` | `varchar` | Primary |
| `nom_alm` | `varchar` |  |
| `poblacion_alm` | `varchar` |  |
| `pais_alm` | `varchar` |  |

## Table `stock_prod`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_prod` | `varchar` | Primary |
| `id_alm` | `varchar` | Primary |
| `unidades` | `int4` |  |

## Table `stock_compo`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_compo` | `varchar` | Primary |
| `id_alm` | `varchar` | Primary |
| `unidades` | `int4` |  |

## Table `ventas`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_venta` | `varchar` | Primary |
| `id_prod` | `varchar` |  Nullable |
| `id_cliente` | `varchar` |  Nullable |
| `unidades` | `int4` |  |
| `precio_unidad` | `numeric` |  |
| `total_venta` | `numeric` |  |
| `fecha_venta` | `date` |  |

## Table `compras`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_compra` | `varchar` | Primary |
| `id_prov_compo` | `varchar` |  Nullable |
| `id_compo` | `varchar` |  Nullable |
| `unidades_compra` | `int4` |  |
| `precio_unidad` | `numeric` |  |
| `total_compra` | `numeric` |  |
| `fecha_compra` | `date` |  |

## Table `estados_intervencion`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_estado` | `varchar` | Primary |
| `nom_estado` | `varchar` |  |
| `desc_estado` | `text` |  Nullable |

## Table `servicios_intervencion`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_servicio` | `varchar` | Primary |
| `nom_servicio` | `varchar` |  |
| `desc_servicio` | `text` |  Nullable |
| `coste_servicio_prov` | `numeric` |  |
| `ingreso_servicio_cli` | `numeric` |  |

## Table `establecimientos`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_establecimiento` | `varchar` | Primary |
| `establecimiento` | `varchar` |  |
| `poblacion_establecimiento` | `varchar` |  |
| `pais_establecimiento` | `varchar` |  |

## Table `documentos`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_documento` | `varchar` | Primary |
| `titulo` | `varchar` |  |
| `tipo_documento` | `varchar` |  |
| `departamento_origen` | `varchar` |  |
| `fecha_emision` | `date` |  |
| `resumen_ejecutivo` | `text` |  Nullable |
| `url_storage` | `varchar` |  |
| `created_at` | `timestamptz` |  Nullable |

## Table `document_chunks`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id` | `int4` | Primary |
| `document_id` | `varchar` |  Nullable |
| `chunk_text` | `text` |  |
| `page_number` | `int4` |  Nullable |
| `embedding` | `vector` |  Nullable |

## Table `intervenciones`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `id_int` | `varchar` | Primary |
| `id_prod` | `varchar` |  Nullable |
| `id_serv` | `varchar` |  Nullable |
| `id_estado` | `varchar` |  Nullable |
| `id_cliente` | `varchar` |  Nullable |
| `id_establecimiento` | `varchar` |  Nullable |
| `id_pro_serv` | `varchar` |  Nullable |
| `fecha_aviso` | `date` |  |
| `fecha_int` | `date` |  |
| `tiempo_int` | `numeric` |  |

