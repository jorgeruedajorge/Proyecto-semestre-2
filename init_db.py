from app import app, db

from models import (
    RolUsuario,
    Usuario,
    CategoriaProducto,
    Marca,
    EstadoPedido,
    MetodoPago,
    Producto,
    ProductoFisico,
    ProductoDigital
)


with app.app_context():

    print("Eliminando tablas y objetos anteriores...")

    # Reinicio completo del esquema PostgreSQL.
    # Esto elimina tablas, vistas y demás objetos dependientes.
    db.session.execute(
        db.text("DROP SCHEMA IF EXISTS public CASCADE")
    )

    db.session.execute(
        db.text("CREATE SCHEMA public")
    )

    db.session.commit()

    print("Creando tablas...")
    db.create_all()

    # =====================================================
    # ROLES
    # =====================================================

    rol_admin = RolUsuario(
        nombre="Administrador"
    )

    rol_cliente = RolUsuario(
        nombre="Cliente"
    )

    db.session.add_all([
        rol_admin,
        rol_cliente
    ])

    db.session.commit()


    # =====================================================
    # USUARIO ADMINISTRADOR
    # =====================================================

    admin = Usuario(
        nombre="Administrador",
        correo="admin@tiendatecnologia.com",
        password="admin123",
        rol_id=rol_admin.id_rol
    )
    db.session.add(admin)
    db.session.commit()


    # =====================================================
    # CATEGORÍAS
    # =====================================================

    laptops = CategoriaProducto(
        nombre="Laptops"
    )

    componentes = CategoriaProducto(
        nombre="Componentes"
    )

    accesorios = CategoriaProducto(
        nombre="Accesorios"
    )

    software = CategoriaProducto(
        nombre="Software"
    )

    db.session.add_all([
        laptops,
        componentes,
        accesorios,
        software
    ])

    db.session.commit()


    # =====================================================
    # MARCAS
    # =====================================================

    asus = Marca(
        nombre="ASUS"
    )

    lenovo = Marca(
        nombre="Lenovo"
    )

    logitech = Marca(
        nombre="Logitech"
    )

    kingston = Marca(
        nombre="Kingston"
    )

    microsoft = Marca(
        nombre="Microsoft"
    )

    hyperx = Marca(
        nombre="HyperX"
    )

    nvidia = Marca(
        nombre="NVIDIA"
    )

    db.session.add_all([
        asus,
        lenovo,
        logitech,
        kingston,
        microsoft,
        hyperx,
        nvidia
    ])

    db.session.commit()


    # =====================================================
    # ESTADOS DE PEDIDO
    # =====================================================

    pendiente = EstadoPedido(
        nombre="Pendiente"
    )

    pagado = EstadoPedido(
        nombre="Pagado"
    )

    enviado = EstadoPedido(
        nombre="Enviado"
    )

    entregado = EstadoPedido(
        nombre="Entregado"
    )

    cancelado = EstadoPedido(
        nombre="Cancelado"
    )

    db.session.add_all([
        pendiente,
        pagado,
        enviado,
        entregado,
        cancelado
    ])

    db.session.commit()


    # =====================================================
    # MÉTODOS DE PAGO
    # =====================================================

    tarjeta = MetodoPago(
        nombre="Tarjeta"
    )

    transferencia = MetodoPago(
        nombre="Transferencia"
    )

    efectivo = MetodoPago(
        nombre="Efectivo"
    )

    db.session.add_all([
        tarjeta,
        transferencia,
        efectivo
    ])

    db.session.commit()


    # =====================================================
    # PRODUCTOS TECNOLÓGICOS
    # =====================================================

    # =====================================================
    # LAPTOPS
    # =====================================================

    laptop_asus = ProductoFisico(
        tipo="fisico",
        codigo="LAP-ASUS-001",
        nombre="ASUS TUF Gaming F15",
        descripcion=(
            "Laptop gaming con procesador Intel Core i7, "
            "16 GB de RAM y SSD de 512 GB."
        ),
        precio=1299.99,
        stock=10,
        categoria_id=laptops.id_categoria,
        marca_id=asus.id_marca,
        peso_kg=2.30,
        costo_envio_por_kg=5.00,
        imagen_url="img/tuf.png"
    )

    laptop_lenovo = ProductoFisico(
        tipo="fisico",
        codigo="LAP-LEN-001",
        nombre="Lenovo IdeaPad 3",
        descripcion=(
            "Laptop para estudio y trabajo con "
            "16 GB de RAM y SSD de 512 GB."
        ),
        precio=899.99,
        stock=8,
        categoria_id=laptops.id_categoria,
        marca_id=lenovo.id_marca,
        peso_kg=1.65,
        costo_envio_por_kg=5.00,
        imagen_url="img/lenovo.jpg"
    )

    laptop_vivobook = ProductoFisico(
        tipo="fisico",
        codigo="LAP-ASUS-002",
        nombre="ASUS Vivobook 16",
        descripcion=(
            "Laptop de 16 pulgadas para productividad, "
            "estudio y entretenimiento."
        ),
        precio=999.99,
        stock=7,
        categoria_id=laptops.id_categoria,
        marca_id=asus.id_marca,
        peso_kg=1.88,
        costo_envio_por_kg=5.00,
        imagen_url="img/vivobook.webp"
    )


    # =====================================================
    # COMPONENTES
    # =====================================================

    tarjeta_grafica = ProductoFisico(
        tipo="fisico",
        codigo="GPU-NVD-001",
        nombre="NVIDIA GeForce RTX 4060",
        descripcion=(
            "Tarjeta gráfica para gaming y "
            "aplicaciones de alto rendimiento."
        ),
        precio=399.99,
        stock=6,
        categoria_id=componentes.id_categoria,
        marca_id=nvidia.id_marca,
        peso_kg=0.95,
        costo_envio_por_kg=5.00,
        imagen_url="img/nvidia.jpg"
    )

    memoria_ram = ProductoFisico(
        tipo="fisico",
        codigo="RAM-KNG-001",
        nombre="Kingston Fury 16 GB DDR4",
        descripcion=(
            "Memoria RAM DDR4 de 16 GB "
            "para equipos de escritorio."
        ),
        precio=59.99,
        stock=20,
        categoria_id=componentes.id_categoria,
        marca_id=kingston.id_marca,
        peso_kg=0.10,
        costo_envio_por_kg=5.00,
        imagen_url="img/fury.webp"
    )

    ssd = ProductoFisico(
        tipo="fisico",
        codigo="SSD-KNG-001",
        nombre="Kingston NV2 1 TB",
        descripcion=(
            "Unidad SSD NVMe de 1 TB para "
            "almacenamiento de alta velocidad."
        ),
        precio=79.99,
        stock=15,
        categoria_id=componentes.id_categoria,
        marca_id=kingston.id_marca,
        peso_kg=0.08,
        costo_envio_por_kg=5.00,
        imagen_url="img/nv2.webp"
    )


    # =====================================================
    # ACCESORIOS
    # =====================================================

    mouse = ProductoFisico(
        tipo="fisico",
        codigo="MOU-LOG-001",
        nombre="Logitech G203",
        descripcion=(
            "Mouse gaming con sensor de alta precisión "
            "y seis botones programables."
        ),
        precio=39.99,
        stock=25,
        categoria_id=accesorios.id_categoria,
        marca_id=logitech.id_marca,
        peso_kg=0.09,
        costo_envio_por_kg=5.00,
        imagen_url="img/logitech.webp"
    )

    teclado = ProductoFisico(
        tipo="fisico",
        codigo="TEC-LOG-001",
        nombre="Logitech K380",
        descripcion=(
            "Teclado inalámbrico compacto compatible "
            "con múltiples dispositivos."
        ),
        precio=49.99,
        stock=18,
        categoria_id=accesorios.id_categoria,
        marca_id=logitech.id_marca,
        peso_kg=0.42,
        costo_envio_por_kg=5.00,
        imagen_url="img/logitech cable.webp"
    )

    audifonos = ProductoFisico(
        tipo="fisico",
        codigo="AUD-HYP-001",
        nombre="HyperX Cloud II",
        descripcion=(
            "Audífonos gaming con sonido envolvente 7.1 "
            "y micrófono desmontable."
        ),
        precio=89.99,
        stock=12,
        categoria_id=accesorios.id_categoria,
        marca_id=hyperx.id_marca,
        peso_kg=0.32,
        costo_envio_por_kg=5.00,
        imagen_url="img/hyper.jpg"
    )


    # =====================================================
    # SOFTWARE
    # =====================================================

    office = ProductoDigital(
        tipo="digital",
        codigo="SW-MIC-001",
        nombre="Microsoft 365 Personal",
        descripcion=(
            "Suscripción de Microsoft 365 con "
            "aplicaciones de productividad."
        ),
        precio=69.99,
        stock=100,
        categoria_id=software.id_categoria,
        marca_id=microsoft.id_marca,
        licencia="Licencia personal por 1 año",
        imagen_url="img/microsoft.webp"
    )

    windows = ProductoDigital(
        tipo="digital",
        codigo="SW-MIC-002",
        nombre="Windows 11 Pro",
        descripcion=(
            "Sistema operativo Windows 11 Pro para "
            "equipos personales y profesionales."
        ),
        precio=199.99,
        stock=100,
        categoria_id=software.id_categoria,
        marca_id=microsoft.id_marca,
        licencia="Licencia digital permanente",
        imagen_url="img/windows.avif"
    )


    # =====================================================
    # GUARDAR PRODUCTOS
    # =====================================================

    db.session.add_all([
        laptop_asus,
        laptop_lenovo,
        laptop_vivobook,
        tarjeta_grafica,
        memoria_ram,
        ssd,
        mouse,
        teclado,
        audifonos,
        office,
        windows
    ])

    db.session.commit()


    # =====================================================
    # RESULTADO
    # =====================================================

    print()
    print("==============================================")
    print(" BASE DE DATOS CREADA CORRECTAMENTE")
    print("==============================================")
    print()

    print("Usuario administrador:")
    print("Correo: admin@tiendatecnologia.com")
    print("Contraseña: admin123")
    print()

    cantidad = Producto.query.count()

    print("Productos tecnológicos registrados:", cantidad)
    print()

    print("La base tiendatecnologia está lista.")