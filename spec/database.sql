
CREATE TABLE clientes (
    id_cliente VARCHAR(20) PRIMARY KEY,
    nom_cliente VARCHAR(100) NOT NULL,
    poblacion_cliente VARCHAR(100) NOT NULL,
    pais_cliente VARCHAR(50) NOT NULL
);

CREATE TABLE proveedores_compo (
    id_prov_compo VARCHAR(20) PRIMARY KEY,
    nom_prov_compo VARCHAR(100) NOT NULL,
    poblacion_prov_compo VARCHAR(100) NOT NULL,
    pais_prov_compo VARCHAR(50) NOT NULL
);

CREATE TABLE proveedores_serv (
    id_pro_serv VARCHAR(20) PRIMARY KEY,
    nom_pro_serv VARCHAR(100) NOT NULL,
    poblacio_pro_serv VARCHAR(100) NOT NULL,
    pais_pro_serv VARCHAR(50) NOT NULL
);

CREATE TABLE productos (
    id_prod VARCHAR(20) PRIMARY KEY,
    nom_prod VARCHAR(100) NOT NULL,
    desc_prod TEXT,
    precio_prod DECIMAL(10, 2) NOT NULL
);

CREATE TABLE componentes (
    id_compo VARCHAR(20) PRIMARY KEY,
    nom_compo VARCHAR(100) NOT NULL,
    desc_compo TEXT,
    precio_compo DECIMAL(10, 2) NOT NULL
);

CREATE TABLE almacen (
    id_alm VARCHAR(20) PRIMARY KEY,
    nom_alm VARCHAR(100) NOT NULL,
    poblacion_alm VARCHAR(100) NOT NULL,
    pais_alm VARCHAR(50) NOT NULL
);

CREATE TABLE stock_prod (
    id_prod VARCHAR(20) REFERENCES productos(id_prod),
    id_alm VARCHAR(20) REFERENCES almacen(id_alm),
    unidades INT NOT NULL,
    PRIMARY KEY (id_prod, id_alm)
);

CREATE TABLE stock_compo (
    id_compo VARCHAR(20) REFERENCES componentes(id_compo),
    id_alm VARCHAR(20) REFERENCES almacen(id_alm),
    unidades INT NOT NULL,
    PRIMARY KEY (id_compo, id_alm)
);

CREATE TABLE ventas (
    id_venta VARCHAR(20) PRIMARY KEY,
    id_prod VARCHAR(20) REFERENCES productos(id_prod),
    id_cliente VARCHAR(20) REFERENCES clientes(id_cliente),
    unidades INT NOT NULL,
    precio_unidad DECIMAL(10, 2) NOT NULL,
    total_venta DECIMAL(10, 2) NOT NULL,
    fecha_venta DATE NOT NULL
);

CREATE TABLE compras (
    id_compra VARCHAR(20) PRIMARY KEY,
    id_prov_compo VARCHAR(20) REFERENCES proveedores_compo(id_prov_compo),
    id_compo VARCHAR(20) REFERENCES componentes(id_compo),
    unidades_compra INT NOT NULL,
    precio_unidad DECIMAL(10, 2) NOT NULL,
    total_compra DECIMAL(10, 2) NOT NULL,
    fecha_compra DATE NOT NULL
);

CREATE TABLE estados_intervencion (
    id_estado VARCHAR(20) PRIMARY KEY,
    nom_estado VARCHAR(50) NOT NULL,
    desc_estado TEXT
);

CREATE TABLE servicios_intervencion (
    id_servicio VARCHAR(20) PRIMARY KEY,
    nom_servicio VARCHAR(50) NOT NULL,
    desc_servicio TEXT,
    coste_servicio_prov DECIMAL(10, 2) NOT NULL,
    ingreso_servicio_cli DECIMAL(10, 2) NOT NULL
);

CREATE TABLE establecimientos (
    id_establecimiento VARCHAR(20) PRIMARY KEY,
    establecimiento VARCHAR(100) NOT NULL,
    poblacion_establecimiento VARCHAR(100) NOT NULL,
    pais_establecimiento VARCHAR(50) NOT NULL
);

CREATE TABLE intervenciones (
    id_int VARCHAR(20) PRIMARY KEY,
    id_prod VARCHAR(20) REFERENCES productos(id_prod),
    id_serv VARCHAR(20) REFERENCES servicios_intervencion(id_servicio),
    id_estado VARCHAR(20) REFERENCES estados_intervencion(id_estado),
    id_cliente VARCHAR(20) REFERENCES clientes(id_cliente),
    id_establecimiento VARCHAR(20) REFERENCES establecimientos(id_establecimiento),
    id_pro_serv VARCHAR(20) REFERENCES proveedores_serv(id_pro_serv),
    fecha_aviso DATE NOT NULL,
    fecha_int DATE NOT NULL,
    tiempo_int DECIMAL(4, 2) NOT NULL
);