CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(768),
    match_count integer DEFAULT 5
)
RETURNS TABLE (
    id integer,
    document_id varchar,
    titulo varchar,
    chunk_text text,
    page_number integer,
    similarity double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        dc.id,
        dc.document_id,
        d.titulo,
        dc.chunk_text,
        dc.page_number,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks AS dc
    JOIN documentos AS d ON d.id_documento = dc.document_id
    WHERE dc.embedding IS NOT NULL
    ORDER BY dc.embedding <=> query_embedding
    LIMIT LEAST(GREATEST(match_count, 1), 10);
$$;

CREATE OR REPLACE FUNCTION match_document_chunks_filtered(
    query_embedding vector(768),
    match_count integer DEFAULT 5,
    p_document_title text DEFAULT NULL,
    p_page_number integer DEFAULT NULL
)
RETURNS TABLE (
    id integer,
    document_id varchar,
    titulo varchar,
    chunk_text text,
    page_number integer,
    similarity double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        dc.id,
        dc.document_id,
        d.titulo,
        dc.chunk_text,
        dc.page_number,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks AS dc
    JOIN documentos AS d ON d.id_documento = dc.document_id
    WHERE dc.embedding IS NOT NULL
      AND (
          p_document_title IS NULL
          OR d.titulo ILIKE '%' || p_document_title || '%'
      )
      AND (p_page_number IS NULL OR dc.page_number = p_page_number)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT LEAST(GREATEST(match_count, 1), 10);
$$;

CREATE OR REPLACE FUNCTION agent_cfo_sales_report(
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL,
    p_group_by text DEFAULT 'total',
    p_filter_by text DEFAULT NULL,
    p_search text DEFAULT NULL,
    p_limit integer DEFAULT 8
)
RETURNS TABLE (
    group_label text,
    record_count bigint,
    units bigint,
    amount numeric
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_group_by NOT IN ('total', 'month', 'product', 'customer') THEN
        RAISE EXCEPTION 'Unsupported sales grouping';
    END IF;
    IF p_filter_by IS NOT NULL AND p_filter_by NOT IN ('product', 'customer') THEN
        RAISE EXCEPTION 'Unsupported sales filter';
    END IF;

    RETURN QUERY
    SELECT
        CASE p_group_by
            WHEN 'month' THEN to_char(date_trunc('month', v.fecha_venta), 'YYYY-MM')
            WHEN 'product' THEN COALESCE(p.nom_prod, '(sin producto)')
            WHEN 'customer' THEN COALESCE(c.nom_cliente, '(sin cliente)')
            ELSE 'Total'
        END,
        count(*)::bigint,
        COALESCE(sum(v.unidades), 0)::bigint,
        COALESCE(sum(v.total_venta), 0)::numeric
    FROM ventas AS v
    LEFT JOIN productos AS p ON p.id_prod = v.id_prod
    LEFT JOIN clientes AS c ON c.id_cliente = v.id_cliente
    WHERE (p_start_date IS NULL OR v.fecha_venta >= p_start_date)
      AND (p_end_date IS NULL OR v.fecha_venta <= p_end_date)
      AND (
          p_search IS NULL
          OR (
              p_filter_by IS NULL
              AND (
                  p.nom_prod ILIKE '%' || p_search || '%'
                  OR c.nom_cliente ILIKE '%' || p_search || '%'
              )
          )
          OR (p_filter_by = 'product' AND p.nom_prod ILIKE '%' || p_search || '%')
          OR (p_filter_by = 'customer' AND c.nom_cliente ILIKE '%' || p_search || '%')
      )
    GROUP BY 1
    ORDER BY
        CASE WHEN p_group_by = 'month' THEN min(v.fecha_venta) END DESC NULLS LAST,
        CASE WHEN p_group_by <> 'month' THEN sum(v.total_venta) END DESC NULLS LAST
    LIMIT LEAST(GREATEST(p_limit, 1), 10);
END;
$$;

CREATE OR REPLACE FUNCTION agent_cfo_purchases_report(
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL,
    p_group_by text DEFAULT 'total',
    p_filter_by text DEFAULT NULL,
    p_search text DEFAULT NULL,
    p_limit integer DEFAULT 8
)
RETURNS TABLE (
    group_label text,
    record_count bigint,
    units bigint,
    amount numeric
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_group_by NOT IN ('total', 'month', 'component', 'supplier') THEN
        RAISE EXCEPTION 'Unsupported purchases grouping';
    END IF;
    IF p_filter_by IS NOT NULL AND p_filter_by NOT IN ('component', 'supplier') THEN
        RAISE EXCEPTION 'Unsupported purchases filter';
    END IF;

    RETURN QUERY
    SELECT
        CASE p_group_by
            WHEN 'month' THEN to_char(date_trunc('month', c.fecha_compra), 'YYYY-MM')
            WHEN 'component' THEN COALESCE(co.nom_compo, '(sin componente)')
            WHEN 'supplier' THEN COALESCE(pc.nom_prov_compo, '(sin proveedor)')
            ELSE 'Total'
        END,
        count(*)::bigint,
        COALESCE(sum(c.unidades_compra), 0)::bigint,
        COALESCE(sum(c.total_compra), 0)::numeric
    FROM compras AS c
    LEFT JOIN componentes AS co ON co.id_compo = c.id_compo
    LEFT JOIN proveedores_compo AS pc
        ON pc.id_prov_compo = c.id_prov_compo
    WHERE (p_start_date IS NULL OR c.fecha_compra >= p_start_date)
      AND (p_end_date IS NULL OR c.fecha_compra <= p_end_date)
      AND (
          p_search IS NULL
          OR (
              p_filter_by IS NULL
              AND (
                  co.nom_compo ILIKE '%' || p_search || '%'
                  OR pc.nom_prov_compo ILIKE '%' || p_search || '%'
              )
          )
          OR (p_filter_by = 'component' AND co.nom_compo ILIKE '%' || p_search || '%')
          OR (p_filter_by = 'supplier' AND pc.nom_prov_compo ILIKE '%' || p_search || '%')
      )
    GROUP BY 1
    ORDER BY
        CASE WHEN p_group_by = 'month' THEN min(c.fecha_compra) END DESC NULLS LAST,
        CASE WHEN p_group_by <> 'month' THEN sum(c.total_compra) END DESC NULLS LAST
    LIMIT LEAST(GREATEST(p_limit, 1), 10);
END;
$$;

DROP FUNCTION IF EXISTS agent_cfo_stock_report(text, text, text, integer);

CREATE OR REPLACE FUNCTION agent_cfo_stock_report(
    p_item_type text,
    p_search text DEFAULT NULL,
    p_warehouse text DEFAULT NULL,
    p_limit integer DEFAULT 10,
    p_offset integer DEFAULT 0
)
RETURNS TABLE (
    item_type text,
    item_id text,
    item_name text,
    warehouse_id text,
    warehouse_name text,
    units integer
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_item_type = 'product' THEN
        RETURN QUERY
        SELECT
            'product'::text,
            p.id_prod::text,
            p.nom_prod::text,
            a.id_alm::text,
            a.nom_alm::text,
            sp.unidades
        FROM stock_prod AS sp
        JOIN productos AS p ON p.id_prod = sp.id_prod
        JOIN almacen AS a ON a.id_alm = sp.id_alm
        WHERE (p_search IS NULL OR p.nom_prod ILIKE '%' || p_search || '%')
          AND (p_warehouse IS NULL OR a.nom_alm ILIKE '%' || p_warehouse || '%')
        ORDER BY p.nom_prod, p.id_prod, a.nom_alm, a.id_alm
        LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_item_type = 'component' THEN
        RETURN QUERY
        SELECT
            'component'::text,
            c.id_compo::text,
            c.nom_compo::text,
            a.id_alm::text,
            a.nom_alm::text,
            sc.unidades
        FROM stock_compo AS sc
        JOIN componentes AS c ON c.id_compo = sc.id_compo
        JOIN almacen AS a ON a.id_alm = sc.id_alm
        WHERE (p_search IS NULL OR c.nom_compo ILIKE '%' || p_search || '%')
          AND (p_warehouse IS NULL OR a.nom_alm ILIKE '%' || p_warehouse || '%')
        ORDER BY c.nom_compo, c.id_compo, a.nom_alm, a.id_alm
        LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSE
        RAISE EXCEPTION 'Unsupported stock item type';
    END IF;
END;
$$;

DROP FUNCTION IF EXISTS agent_cfo_products_catalog(text, integer);

CREATE OR REPLACE FUNCTION agent_cfo_products_catalog(
    p_search text DEFAULT NULL,
    p_limit integer DEFAULT 10,
    p_offset integer DEFAULT 0
)
RETURNS TABLE (
    id_prod text,
    nom_prod text,
    desc_prod text,
    precio_prod numeric
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        p.id_prod::text,
        p.nom_prod::text,
        p.desc_prod,
        p.precio_prod::numeric
    FROM productos AS p
    WHERE p_search IS NULL
       OR p.id_prod ILIKE '%' || p_search || '%'
       OR p.nom_prod ILIKE '%' || p_search || '%'
       OR p.desc_prod ILIKE '%' || p_search || '%'
    ORDER BY p.nom_prod, p.id_prod
    LIMIT LEAST(GREATEST(p_limit, 1), 10)
    OFFSET GREATEST(p_offset, 0);
$$;

CREATE OR REPLACE FUNCTION agent_cfo_interventions_report(
    p_search text DEFAULT NULL,
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL,
    p_limit integer DEFAULT 8
)
RETURNS TABLE (
    id_establecimiento text,
    establecimiento text,
    intervention_count bigint
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.id_establecimiento::text,
        e.establecimiento::text,
        count(i.id_int)::bigint AS intervention_count
    FROM establecimientos AS e
    LEFT JOIN intervenciones AS i
        ON i.id_establecimiento = e.id_establecimiento
        AND (p_start_date IS NULL OR i.fecha_int >= p_start_date)
        AND (p_end_date IS NULL OR i.fecha_int <= p_end_date)
    WHERE p_search IS NULL
       OR e.id_establecimiento ILIKE '%' || p_search || '%'
       OR e.establecimiento ILIKE '%' || p_search || '%'
    GROUP BY e.id_establecimiento, e.establecimiento
    ORDER BY intervention_count DESC, e.establecimiento, e.id_establecimiento
    LIMIT LEAST(GREATEST(p_limit, 1), 10);
$$;

DROP FUNCTION IF EXISTS agent_cfo_table_read(text, text, date, date, integer);

CREATE OR REPLACE FUNCTION agent_cfo_table_read(
    p_table text,
    p_search text DEFAULT NULL,
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL,
    p_limit integer DEFAULT 10,
    p_offset integer DEFAULT 0
)
RETURNS TABLE (row_data jsonb)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_start_date IS NOT NULL
       AND p_end_date IS NOT NULL
       AND p_start_date > p_end_date THEN
        RAISE EXCEPTION 'start_date must not be after end_date';
    END IF;

    IF (p_start_date IS NOT NULL OR p_end_date IS NOT NULL)
       AND p_table NOT IN ('ventas', 'compras', 'intervenciones') THEN
        RAISE EXCEPTION 'Date filters are not supported for this table';
    END IF;

    IF p_table = 'clientes' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM clientes AS t
        WHERE p_search IS NULL OR t.id_cliente ILIKE '%' || p_search || '%'
            OR t.nom_cliente ILIKE '%' || p_search || '%'
            OR t.poblacion_cliente ILIKE '%' || p_search || '%'
            OR t.pais_cliente ILIKE '%' || p_search || '%'
        ORDER BY t.id_cliente LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'proveedores_compo' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM proveedores_compo AS t
        WHERE p_search IS NULL OR t.id_prov_compo ILIKE '%' || p_search || '%'
            OR t.nom_prov_compo ILIKE '%' || p_search || '%'
            OR t.poblacion_prov_compo ILIKE '%' || p_search || '%'
            OR t.pais_prov_compo ILIKE '%' || p_search || '%'
        ORDER BY t.id_prov_compo LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'proveedores_serv' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM proveedores_serv AS t
        WHERE p_search IS NULL OR t.id_pro_serv ILIKE '%' || p_search || '%'
            OR t.nom_pro_serv ILIKE '%' || p_search || '%'
            OR t.poblacio_pro_serv ILIKE '%' || p_search || '%'
            OR t.pais_pro_serv ILIKE '%' || p_search || '%'
        ORDER BY t.id_pro_serv LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'componentes' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM componentes AS t
        WHERE p_search IS NULL OR t.id_compo ILIKE '%' || p_search || '%'
            OR t.nom_compo ILIKE '%' || p_search || '%'
            OR t.desc_compo ILIKE '%' || p_search || '%'
            OR t.precio_compo::text ILIKE '%' || p_search || '%'
        ORDER BY t.id_compo LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'almacen' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM almacen AS t
        WHERE p_search IS NULL OR t.id_alm ILIKE '%' || p_search || '%'
            OR t.nom_alm ILIKE '%' || p_search || '%'
            OR t.poblacion_alm ILIKE '%' || p_search || '%'
            OR t.pais_alm ILIKE '%' || p_search || '%'
        ORDER BY t.id_alm LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'stock_prod' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM stock_prod AS t
        WHERE p_search IS NULL OR t.id_prod ILIKE '%' || p_search || '%'
            OR t.id_alm ILIKE '%' || p_search || '%'
            OR t.unidades::text ILIKE '%' || p_search || '%'
        ORDER BY t.id_prod, t.id_alm LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'stock_compo' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM stock_compo AS t
        WHERE p_search IS NULL OR t.id_compo ILIKE '%' || p_search || '%'
            OR t.id_alm ILIKE '%' || p_search || '%'
            OR t.unidades::text ILIKE '%' || p_search || '%'
        ORDER BY t.id_compo, t.id_alm LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'ventas' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM ventas AS t
        WHERE (p_search IS NULL OR t.id_venta ILIKE '%' || p_search || '%'
            OR t.id_prod ILIKE '%' || p_search || '%'
            OR t.id_cliente ILIKE '%' || p_search || '%')
          AND (p_start_date IS NULL OR t.fecha_venta >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_venta <= p_end_date)
        ORDER BY t.fecha_venta DESC, t.id_venta
        LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'compras' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM compras AS t
        WHERE (p_search IS NULL OR t.id_compra ILIKE '%' || p_search || '%'
            OR t.id_prov_compo ILIKE '%' || p_search || '%'
            OR t.id_compo ILIKE '%' || p_search || '%')
          AND (p_start_date IS NULL OR t.fecha_compra >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_compra <= p_end_date)
        ORDER BY t.fecha_compra DESC, t.id_compra
        LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'estados_intervencion' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM estados_intervencion AS t
        WHERE p_search IS NULL OR t.id_estado ILIKE '%' || p_search || '%'
            OR t.nom_estado ILIKE '%' || p_search || '%'
            OR t.desc_estado ILIKE '%' || p_search || '%'
        ORDER BY t.id_estado LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'servicios_intervencion' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM servicios_intervencion AS t
        WHERE p_search IS NULL OR t.id_servicio ILIKE '%' || p_search || '%'
            OR t.nom_servicio ILIKE '%' || p_search || '%'
            OR t.desc_servicio ILIKE '%' || p_search || '%'
            OR t.coste_servicio_prov::text ILIKE '%' || p_search || '%'
            OR t.ingreso_servicio_cli::text ILIKE '%' || p_search || '%'
        ORDER BY t.id_servicio LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'establecimientos' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM establecimientos AS t
        WHERE p_search IS NULL OR t.id_establecimiento ILIKE '%' || p_search || '%'
            OR t.establecimiento ILIKE '%' || p_search || '%'
            OR t.poblacion_establecimiento ILIKE '%' || p_search || '%'
            OR t.pais_establecimiento ILIKE '%' || p_search || '%'
        ORDER BY t.id_establecimiento LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSIF p_table = 'intervenciones' THEN
        RETURN QUERY
        SELECT to_jsonb(t) FROM intervenciones AS t
        WHERE (p_search IS NULL OR t.id_int ILIKE '%' || p_search || '%'
            OR t.id_prod ILIKE '%' || p_search || '%'
            OR t.id_serv ILIKE '%' || p_search || '%'
            OR t.id_estado ILIKE '%' || p_search || '%'
            OR t.id_cliente ILIKE '%' || p_search || '%'
            OR t.id_establecimiento ILIKE '%' || p_search || '%'
            OR t.id_pro_serv ILIKE '%' || p_search || '%')
          AND (p_start_date IS NULL OR t.fecha_int >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_int <= p_end_date)
        ORDER BY t.fecha_int DESC, t.id_int
        LIMIT LEAST(GREATEST(p_limit, 1), 10)
        OFFSET GREATEST(p_offset, 0);
    ELSE
        RAISE EXCEPTION 'Unsupported table for CFO agent';
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION agent_cfo_table_count(
    p_table text,
    p_search text DEFAULT NULL,
    p_start_date date DEFAULT NULL,
    p_end_date date DEFAULT NULL
)
RETURNS TABLE (table_name text, total_count bigint)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    IF p_start_date IS NOT NULL
       AND p_end_date IS NOT NULL
       AND p_start_date > p_end_date THEN
        RAISE EXCEPTION 'start_date must not be after end_date';
    END IF;

    IF (p_start_date IS NOT NULL OR p_end_date IS NOT NULL)
       AND p_table NOT IN ('ventas', 'compras', 'intervenciones') THEN
        RAISE EXCEPTION 'Date filters are not supported for this table';
    END IF;

    IF p_table = 'clientes' THEN
        RETURN QUERY SELECT p_table, count(*) FROM clientes AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'proveedores_compo' THEN
        RETURN QUERY SELECT p_table, count(*) FROM proveedores_compo AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'proveedores_serv' THEN
        RETURN QUERY SELECT p_table, count(*) FROM proveedores_serv AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'productos' THEN
        RETURN QUERY SELECT p_table, count(*) FROM productos AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'componentes' THEN
        RETURN QUERY SELECT p_table, count(*) FROM componentes AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'almacen' THEN
        RETURN QUERY SELECT p_table, count(*) FROM almacen AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'stock_prod' THEN
        RETURN QUERY SELECT p_table, count(*) FROM stock_prod AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'stock_compo' THEN
        RETURN QUERY SELECT p_table, count(*) FROM stock_compo AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'ventas' THEN
        RETURN QUERY SELECT p_table, count(*) FROM ventas AS t
        WHERE (p_search IS NULL OR EXISTS (
                SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
                WHERE field.value ILIKE '%' || p_search || '%'
            ))
          AND (p_start_date IS NULL OR t.fecha_venta >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_venta <= p_end_date);
    ELSIF p_table = 'compras' THEN
        RETURN QUERY SELECT p_table, count(*) FROM compras AS t
        WHERE (p_search IS NULL OR EXISTS (
                SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
                WHERE field.value ILIKE '%' || p_search || '%'
            ))
          AND (p_start_date IS NULL OR t.fecha_compra >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_compra <= p_end_date);
    ELSIF p_table = 'estados_intervencion' THEN
        RETURN QUERY SELECT p_table, count(*) FROM estados_intervencion AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'servicios_intervencion' THEN
        RETURN QUERY SELECT p_table, count(*) FROM servicios_intervencion AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'establecimientos' THEN
        RETURN QUERY SELECT p_table, count(*) FROM establecimientos AS t
        WHERE p_search IS NULL OR EXISTS (
            SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
            WHERE field.value ILIKE '%' || p_search || '%'
        );
    ELSIF p_table = 'intervenciones' THEN
        RETURN QUERY SELECT p_table, count(*) FROM intervenciones AS t
        WHERE (p_search IS NULL OR EXISTS (
                SELECT 1 FROM jsonb_each_text(to_jsonb(t)) AS field
                WHERE field.value ILIKE '%' || p_search || '%'
            ))
          AND (p_start_date IS NULL OR t.fecha_int >= p_start_date)
          AND (p_end_date IS NULL OR t.fecha_int <= p_end_date);
    ELSE
        RAISE EXCEPTION 'Unsupported table for CFO agent count';
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION match_document_chunks(vector, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION match_document_chunks_filtered(vector, integer, text, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_sales_report(date, date, text, text, text, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_purchases_report(date, date, text, text, text, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_stock_report(text, text, text, integer, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_products_catalog(text, integer, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_interventions_report(text, date, date, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_table_read(text, text, date, date, integer, integer)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION agent_cfo_table_count(text, text, date, date)
    FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION match_document_chunks(vector, integer) TO service_role;
GRANT EXECUTE ON FUNCTION match_document_chunks_filtered(vector, integer, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_sales_report(date, date, text, text, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_purchases_report(date, date, text, text, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_stock_report(text, text, text, integer, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_products_catalog(text, integer, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_interventions_report(text, date, date, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_table_read(text, text, date, date, integer, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_table_count(text, text, date, date)
    TO service_role;
