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

CREATE OR REPLACE FUNCTION agent_cfo_stock_report(
    p_item_type text,
    p_search text DEFAULT NULL,
    p_warehouse text DEFAULT NULL,
    p_limit integer DEFAULT 8
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
        ORDER BY p.nom_prod, a.nom_alm
        LIMIT LEAST(GREATEST(p_limit, 1), 10);
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
        ORDER BY c.nom_compo, a.nom_alm
        LIMIT LEAST(GREATEST(p_limit, 1), 10);
    ELSE
        RAISE EXCEPTION 'Unsupported stock item type';
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
REVOKE ALL ON FUNCTION agent_cfo_stock_report(text, text, text, integer)
    FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION match_document_chunks(vector, integer) TO service_role;
GRANT EXECUTE ON FUNCTION match_document_chunks_filtered(vector, integer, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_sales_report(date, date, text, text, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_purchases_report(date, date, text, text, text, integer)
    TO service_role;
GRANT EXECUTE ON FUNCTION agent_cfo_stock_report(text, text, text, integer)
    TO service_role;
