-- Datos de arranque del corte vertical: pequeños, limpios y sintéticos.
-- Se cargan con `supabase db reset`. Los datos de la Parte A con errores plantados llegan después (05).

insert into erp.comerciales (id, nombre, email) values
  ('COM-1', 'Marta Soler', 'marta.soler@orvalle.example'),
  ('COM-2', 'Pere Vidal',  'pere.vidal@orvalle.example');

insert into erp.productos (codigo, descripcion, unidad_venta, embalaje, minimo, precio_general) values
  ('TOR-M8X30-ZN',  'Tornillo hexagonal DIN 933 M8x30 cincado',   'ud',    100, 100, 0.0950),
  ('TOR-M10X40-ZN', 'Tornillo hexagonal DIN 933 M10x40 cincado',  'ud',    100, 100, 0.1820),
  ('TUE-M8-ZN',     'Tuerca hexagonal DIN 934 M8 cincada',        'ud',    100, 100, 0.0310),
  ('TUE-M10-ZN',    'Tuerca hexagonal DIN 934 M10 cincada',       'ud',    100, 100, 0.0480),
  ('ARA-M8-ZN',     'Arandela plana DIN 125 M8 cincada',          'ud',    100, 100, 0.0120),
  ('ARA-M10-ZN',    'Arandela plana DIN 125 M10 cincada',         'ud',    100, 100, 0.0170),
  ('GUA-NIT-L',     'Guante de nitrilo desechable talla L',       'caja',    1,   1, 6.9000),
  ('GAF-PROT-INC',  'Gafas de protección incoloras EN 166',       'ud',      1,   1, 3.4500),
  ('DIS-COR-125',   'Disco de corte para metal 125x1,0 mm',       'ud',     25,  25, 0.8900),
  ('BRO-HSS-8',     'Broca HSS para metal 8 mm',                  'ud',     10,  10, 1.6500);

insert into erp.clientes (codigo, cif, razon_social, telefono, comercial_id) values
  ('C0001', 'B60000011', 'Talleres Ferran, S.L.',         '+34 930 000 001', 'COM-1'),
  ('C0002', 'B60000022', 'Manteniments Vallès, S.L.',     '+34 930 000 002', 'COM-1'),
  ('C0003', 'B60000033', 'Instal·lacions Puig, S.C.P.',   '+34 930 000 003', 'COM-2');

insert into erp.direcciones (cliente, calle, numero, nave, cp, poblacion) values
  ('C0001', 'Carrer de la Indústria', '14', 'Nave 3', '08400', 'Granollers'),
  ('C0002', 'Avinguda del Vallès',    '220', null,     '08227', 'Terrassa'),
  ('C0003', 'Carrer Major',           '5',   null,     '08100', 'Mollet del Vallès');

insert into erp.contactos (cliente, email, nombre) values
  ('C0001', 'compras@talleresferran.example',     'Ferran Roca'),
  ('C0001', 'taller@talleresferran.example',      'Jordi Mas'),
  ('C0002', 'pedidos@mantenimentsvalles.example', 'Laia Puig'),
  ('C0003', 'oficina@instalacionspuig.example',   'Núria Puig');

insert into erp.tarifas (cliente, producto, precio_neto, desde, hasta, origen) values
  ('C0001', 'TOR-M8X30-ZN',  0.0820, '2026-01-01', '2026-12-31', 'seed'),
  ('C0001', 'TUE-M8-ZN',     0.0270, '2026-01-01', '2026-12-31', 'seed'),
  ('C0001', 'ARA-M8-ZN',     0.0100, '2026-01-01', '2026-12-31', 'seed'),
  ('C0002', 'GUA-NIT-L',     6.2000, '2026-01-01', '2026-12-31', 'seed'),
  ('C0003', 'DIS-COR-125',   0.7900, '2026-01-01', '2026-12-31', 'seed');

insert into erp.equivalencias (cliente, referencia_cliente, producto, origen, creada_por) values
  ('C0001', 'TORN 8X30', 'TOR-M8X30-ZN', 'migracion', 'seed'),
  ('C0001', 'ARAND 8',   'ARA-M8-ZN',    'migracion', 'seed');

insert into intake.configuracion (parametro, valor) values
  ('r11_tolerancia_precio_eur',  '0.01'),
  ('r13_importe_maximo_eur',     '3000'),
  ('fecha_migracion',            '"2026-10-30"');
