from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    session,
    request,
    send_file,
    flash
)

import os
import uuid
from werkzeug.utils import secure_filename

from decimal import Decimal
from sqlalchemy import text
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from config import Config

from models import (
    db,
    Producto,
    ProductoFisico,
    ProductoDigital,
    CategoriaProducto,
    Marca,
    Usuario,
    RolUsuario,
    Pedido,
    DetallePedido,
    EstadoPedido,
    MetodoPago,
    Pago,
    FacturaCabecera,
    FacturaDetalle
)


# CONFIGURACIÓN


app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)

# La SECRET_KEY ya viene desde Config.
# No se sobrescribe aquí para mantener una sola configuración.


# INICIO


@app.route("/")
def inicio():

    return redirect(
        url_for("catalogo")
    )



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        correo = request.form.get("correo", "").strip()
        password = request.form.get("password", "")

        if not correo or not password:
            flash("Ingrese correo y contraseña.", "error")
            return redirect(url_for("login"))

        usuario = Usuario.query.filter_by(
            correo=correo
        ).first()

        if not usuario or not usuario.check_password(password):

            flash(
                "Correo o contraseña incorrectos.",
                "error"
            )

            return redirect(url_for("login"))

        session["usuario_id"] = usuario.id_usuario
        session["es_admin"] = usuario.es_admin()
        session["usuario_nombre"] = usuario.nombre
        session["usuario_correo"] = usuario.correo
        session.modified = True

        flash(
            f"Bienvenido, {usuario.nombre}.",
            "success"
        )

        return redirect(url_for("catalogo"))

    return render_template("login.html")




@app.route("/logout")
def logout():

    session.pop("usuario_id", None)
    session.pop("es_admin", None)
    session.pop("usuario_nombre", None)
    session.pop("usuario_correo", None)

    flash(
        "Sesión cerrada correctamente.",
        "success"
    )

    return redirect(url_for("catalogo"))




@app.route("/catalogo")
def catalogo():

    categoria_id = request.args.get(
        "categoria",
        type=int
    )

    if categoria_id:

        productos = (
            Producto.query
            .filter_by(
                categoria_id=categoria_id
            )
            .all()
        )

    else:

        productos = Producto.query.all()

    categorias = (
        CategoriaProducto.query
        .order_by(
            CategoriaProducto.nombre
        )
        .all()
    )

    return render_template(
        "catalogo.html",
        productos=productos,
        categorias=categorias,
        categoria_seleccionada=categoria_id
    )



@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):

    producto = Producto.query.get_or_404(
        producto_id
    )

    return render_template(
        "detalle.html",
        producto=producto
    )


@app.route("/carrito")
def carrito():

    carrito = session.get(
        "carrito",
        {}
    )

    productos = []
    total = Decimal("0.00")

    for id_producto, cantidad in carrito.items():

        try:
            producto_id = int(id_producto)
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue

        if cantidad <= 0:
            continue

        producto = db.session.get(Producto, producto_id)

        if producto:

            cantidad = min(cantidad, max(producto.stock, 0))

            if cantidad <= 0:
                continue

            subtotal = (
                Decimal(str(producto.precio))
                * cantidad
            )

            productos.append({
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": subtotal
            })

            total += subtotal

    return render_template(
        "carrito.html",
        productos=productos,
        total=total
    )


@app.route(
    "/carrito/agregar/<int:producto_id>",
    methods=["POST"]
)
def agregar_carrito(producto_id):

    producto = db.session.get(
        Producto,
        producto_id
    )

    if not producto:

        return redirect(
            url_for("catalogo")
        )

    if producto.stock <= 0:

        flash(
            "Producto sin stock.",
            "error"
        )

        return redirect(
            request.referrer
            or url_for("catalogo")
        )

    carrito = session.get(
        "carrito",
        {}
    )

    clave = str(producto_id)

    cantidad = carrito.get(
        clave,
        0
    )

    if cantidad < producto.stock:

        carrito[clave] = cantidad + 1

    else:

        flash(
            "No hay más unidades disponibles.",
            "error"
        )

    session["carrito"] = carrito
    session.modified = True

    return redirect(
        request.referrer
        or url_for("catalogo")
    )



@app.route(
    "/carrito/eliminar/<int:producto_id>",
    methods=["POST"]
)
def eliminar_carrito(producto_id):

    carrito = session.get(
        "carrito",
        {}
    )

    clave = str(producto_id)

    if clave in carrito:

        del carrito[clave]

    session["carrito"] = carrito
    session.modified = True

    return redirect(
        url_for("carrito")
    )



# VACIAR


@app.route(
    "/carrito/vaciar",
    methods=["POST"]
)
def vaciar_carrito():

    session["carrito"] = {}

    session.modified = True

    return redirect(
        url_for("carrito")
    )



# CONTADOR DEL CARRITO


@app.context_processor
def datos_carrito():

    carrito = session.get(
        "carrito",
        {}
    )

    return {
        "cantidad_carrito": sum(
            carrito.values()
        )
    }


# CHECKOUT


@app.route(
    "/checkout",
    methods=["GET", "POST"]
)
def checkout():

    carrito = session.get(
        "carrito",
        {}
    )

    if not carrito:

        flash(
            "El carrito está vacío.",
            "error"
        )

        return redirect(
            url_for("carrito")
        )

    productos = []
    subtotal = Decimal("0.00")

    for id_producto, cantidad in carrito.items():

        try:
            producto_id = int(id_producto)
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            continue

        if cantidad <= 0:
            continue

        producto = db.session.get(Producto, producto_id)

        if not producto:
            continue

        if cantidad > producto.stock:

            flash(
                f"No hay suficiente stock de {producto.nombre}.",
                "error"
            )

            return redirect(
                url_for("carrito")
            )

        precio = Decimal(
            str(producto.precio)
        )

        subtotal_producto = (
            precio * cantidad
        )

        productos.append({
            "producto": producto,
            "cantidad": cantidad,
            "subtotal": subtotal_producto
        })

        subtotal += subtotal_producto

    iva = (
        subtotal *
        Decimal("0.15")
    ).quantize(
        Decimal("0.01")
    )

    total = subtotal + iva

    if request.method == "POST":

        nombre = request.form.get(
            "nombre",
            ""
        ).strip()

        correo = request.form.get(
            "correo",
            ""
        ).strip()

        metodo_id = request.form.get(
            "metodo_pago",
            type=int
        )

        if not nombre or not correo:

            flash(
                "Ingrese nombre y correo.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

        metodo = db.session.get(
            MetodoPago,
            metodo_id
        )

        if not metodo:

            flash(
                "Seleccione un método de pago.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

        try:

            # BUSCAR O CREAR USUARIO


            usuario = (
                Usuario.query
                .filter_by(
                    correo=correo
                )
                .first()
            )

            if not usuario:

                rol_cliente = (
                    RolUsuario.query
                    .filter(
                        db.func.lower(
                            RolUsuario.nombre
                        ) == "cliente"
                    )
                    .first()
                )

                if not rol_cliente:

                    rol_cliente = RolUsuario(
                        nombre="Cliente"
                    )

                    db.session.add(
                        rol_cliente
                    )

                    db.session.flush()

                usuario = Usuario(
                    nombre=nombre,
                    correo=correo,
                    password="cliente"
                    + datetime.now().strftime(
                        "%Y%m%d%H%M%S"
                    ),
                    rol_id=rol_cliente.id_rol
                )

                db.session.add(usuario)

                db.session.flush()

            else:

                usuario.nombre = nombre


            # ESTADO PAGADO


            estado = (
                EstadoPedido.query
                .filter(
                    db.func.lower(
                        EstadoPedido.nombre
                    ) == "pagado"
                )
                .first()
            )

            if not estado:

                estado = EstadoPedido(
                    nombre="Pagado"
                )

                db.session.add(
                    estado
                )

                db.session.flush()

            # CREACION DE PEDIDO


            pedido = Pedido(
                usuario_id=usuario.id_usuario,
                fecha=datetime.now(),
                estado_id=estado.id_estado,
                total=total
            )

            db.session.add(pedido)

            db.session.flush()


            # DETALLES DEL PEDIDO


            for item in productos:

                producto = item["producto"]

                detalle = DetallePedido(
                    pedido_id=pedido.id_pedido,
                    producto_id=producto.id_producto,
                    cantidad=item["cantidad"],
                    subtotal=item["subtotal"]
                )

                db.session.add(
                    detalle
                )

                # Descontar stock
                producto.stock -= item["cantidad"]

                producto.ultima_actualizacion = (
                    datetime.now()
                )

            # PAGO
            

            pago = Pago(
                pedido_id=pedido.id_pedido,
                metodo_id=metodo.id_metodo,
                fecha=datetime.now(),
                monto=total
            )

            db.session.add(
                pago
            )

            db.session.flush()

            # FACTURA
            

            numero_factura = (
                f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                f"-{pedido.id_pedido}"
            )

            factura = FacturaCabecera(
                numero_factura=numero_factura,
                pedido_id=pedido.id_pedido,
                usuario_id=usuario.id_usuario,
                fecha=datetime.now(),
                subtotal=subtotal,
                impuestos=iva,
                total=total
            )

            db.session.add(
                factura
            )

            db.session.flush()

            
            # DETALLE FACTURA
            

            for item in productos:

                producto = item["producto"]

                detalle_factura = FacturaDetalle(
                    factura_id=factura.id_factura,
                    producto_id=producto.id_producto,
                    cantidad=item["cantidad"],
                    precio_unitario=producto.precio,
                    subtotal=item["subtotal"]
                )

                db.session.add(
                    detalle_factura
                )

            
            # GUARDAR 
           

            db.session.commit()

            # Vaciar carrito
            session["carrito"] = {}
            session.modified = True

            return redirect(
                url_for(
                    "factura_pdf",
                    factura_id=factura.id_factura
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR EN LA COMPRA:",
                e
            )

            flash(
                "No se pudo completar la compra.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

    metodos = (
        MetodoPago.query
        .order_by(
            MetodoPago.nombre
        )
        .all()
    )

    return render_template(
        "checkout.html",
        productos=productos,
        subtotal=subtotal,
        iva=iva,
        total=total,
        metodos=metodos
    )


# ADMINISTRACION DE PRODUCTOS


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def usuario_es_admin():
    return bool(
        session.get("usuario_id")
        and session.get("es_admin")
    )


def guardar_imagen(imagen):
    if not imagen or not imagen.filename:
        return None

    extension = os.path.splitext(imagen.filename)[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            "Formato no permitido. Use JPG, JPEG, PNG, WEBP o AVIF."
        )

    imagen.stream.seek(0, os.SEEK_END)
    tamano = imagen.stream.tell()
    imagen.stream.seek(0)

    if tamano > MAX_IMAGE_SIZE:
        raise ValueError("La imagen no puede superar los 5 MB.")

    nombre_original = secure_filename(imagen.filename)
    nombre_base = os.path.splitext(nombre_original)[0] or "producto"
    nombre_archivo = (
        f"{nombre_base}_{uuid.uuid4().hex[:8]}{extension}"
    )

    carpeta = os.path.join(
        app.root_path,
        "static",
        "img"
    )

    os.makedirs(carpeta, exist_ok=True)

    ruta = os.path.join(carpeta, nombre_archivo)
    imagen.save(ruta)

    return f"img/{nombre_archivo}"


@app.route("/admin")
@app.route("/admin/productos")
def admin_productos():
    """Panel administrativo con gestión de productos y reportes de BD."""

    if not usuario_es_admin():
        flash(
            "Debes iniciar sesión como administrador.",
            "error"
        )
        return redirect(url_for("login"))

    productos = (
        Producto.query
        .order_by(Producto.id_producto.desc())
        .all()
    )

    # Las siguientes consultas leen directamente las vistas PostgreSQL.
    # Se usan mappings para poder acceder a las columnas desde Jinja.
    vistas = {
        "inventario": "vw_inventario",
        "stock_bajo": "vw_stock_bajo",
        "agotados": "vw_productos_agotados",
        "ventas": "vw_ventas",
        "detalle_ventas": "vw_detalle_ventas",
        "resumen_ventas": "vw_resumen_ventas",
        "mas_vendidos": "vw_productos_mas_vendidos",
        "inventario_categoria": "vw_inventario_categoria",
        "dashboard": "vw_dashboard_inventario",
    }

    datos = {}

    try:
        for clave, nombre_vista in vistas.items():
            resultado = db.session.execute(
                text(f'SELECT * FROM "{nombre_vista}"')
            )
            datos[clave] = resultado.mappings().all()

    except Exception as e:
        db.session.rollback()
        print("ERROR CONSULTANDO VISTAS ADMIN:", e)
        flash(
            "No se pudieron cargar las vistas de inventario y ventas. "
            "Verifica que ejecutaste objetos_bd.sql.",
            "error"
        )
        datos = {clave: [] for clave in vistas}

    dashboard = datos["dashboard"][0] if datos["dashboard"] else {}

    return render_template(
        "admin_productos.html",
        productos=productos,
        dashboard=dashboard,
        inventario=datos["inventario"],
        stock_bajo=datos["stock_bajo"],
        agotados=datos["agotados"],
        ventas=datos["ventas"],
        detalle_ventas=datos["detalle_ventas"],
        resumen_ventas=datos["resumen_ventas"],
        mas_vendidos=datos["mas_vendidos"],
        inventario_categoria=datos["inventario_categoria"]
    )


@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
def nuevo_producto():

    if not usuario_es_admin():
        flash(
            "Debes iniciar sesión como administrador.",
            "error"
        )
        return redirect(url_for("login"))

    categorias = (
        CategoriaProducto.query
        .order_by(CategoriaProducto.nombre)
        .all()
    )

    marcas = (
        Marca.query
        .order_by(Marca.nombre)
        .all()
    )

    if request.method == "POST":

        codigo = request.form.get("codigo", "").strip()
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        tipo = request.form.get("tipo", "fisico").strip().lower()

        precio = request.form.get("precio", type=float)
        stock = request.form.get("stock", type=int)
        categoria_id = request.form.get("categoria_id", type=int)
        marca_id = request.form.get("marca_id", type=int)

        if not codigo or not nombre:
            flash("Código y nombre son obligatorios.", "error")
            return redirect(url_for("nuevo_producto"))

        if precio is None or precio < 0:
            flash("Ingrese un precio válido.", "error")
            return redirect(url_for("nuevo_producto"))

        precio = Decimal(str(precio)).quantize(Decimal("0.01"))

        if stock is None or stock < 0:
            flash("Ingrese un stock válido.", "error")
            return redirect(url_for("nuevo_producto"))

        if not categoria_id or not marca_id:
            flash("Seleccione categoría y marca.", "error")
            return redirect(url_for("nuevo_producto"))

        if tipo not in {"fisico", "digital"}:
            flash(
                "El tipo de producto debe ser físico o digital.",
                "error"
            )
            return redirect(url_for("nuevo_producto"))

        if Producto.query.filter_by(codigo=codigo).first():
            flash(
                "Ya existe un producto con ese código.",
                "error"
            )
            return redirect(url_for("nuevo_producto"))

        try:
            imagen_url = guardar_imagen(
                request.files.get("imagen")
            )

            datos = dict(
                tipo=tipo,
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                stock=stock,
                categoria_id=categoria_id,
                marca_id=marca_id,
                imagen_url=imagen_url
            )

            if tipo == "fisico":
                producto = ProductoFisico(
                    **datos,
                    peso_kg=Decimal("0.10"),
                    costo_envio_por_kg=Decimal("0.00")
                )
            else:
                producto = ProductoDigital(
                    **datos,
                    licencia="Licencia digital"
                )

            db.session.add(producto)
            db.session.commit()

            flash(
                f"Producto '{nombre}' registrado correctamente.",
                "success"
            )

            return redirect(url_for("admin_productos"))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(url_for("nuevo_producto"))

        except Exception as e:
            db.session.rollback()
            print("ERROR REGISTRANDO PRODUCTO:", e)
            flash(
                "No se pudo registrar el producto.",
                "error"
            )
            return redirect(url_for("nuevo_producto"))

    return render_template(
        "admin_producto_form.html",
        producto=None,
        categorias=categorias,
        marcas=marcas
    )


@app.route(
    "/admin/productos/editar/<int:producto_id>",
    methods=["GET", "POST"]
)
def editar_producto(producto_id):

    if not usuario_es_admin():
        flash(
            "Debes iniciar sesión como administrador.",
            "error"
        )
        return redirect(url_for("login"))

    producto = db.session.get(
        Producto,
        producto_id
    )

    if not producto:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("admin_productos"))

    categorias = (
        CategoriaProducto.query
        .order_by(CategoriaProducto.nombre)
        .all()
    )

    marcas = (
        Marca.query
        .order_by(Marca.nombre)
        .all()
    )

    if request.method == "POST":

        codigo = request.form.get("codigo", "").strip()
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio = request.form.get("precio", type=float)
        stock = request.form.get("stock", type=int)
        categoria_id = request.form.get("categoria_id", type=int)
        marca_id = request.form.get("marca_id", type=int)

        existente = (
            Producto.query
            .filter(
                Producto.codigo == codigo,
                Producto.id_producto != producto_id
            )
            .first()
        )

        if not codigo or not nombre:
            flash("Código y nombre son obligatorios.", "error")
            return redirect(
                url_for("editar_producto", producto_id=producto_id)
            )

        if existente:
            flash(
                "Ese código ya pertenece a otro producto.",
                "error"
            )
            return redirect(
                url_for("editar_producto", producto_id=producto_id)
            )

        if (
            precio is None
            or precio < 0
            or stock is None
            or stock < 0
            or not categoria_id
            or not marca_id
        ):
            flash("Revise los datos ingresados.", "error")
            return redirect(
                url_for("editar_producto", producto_id=producto_id)
            )

        precio = Decimal(str(precio)).quantize(Decimal("0.01"))

        try:
            imagen = request.files.get("imagen")

            if imagen and imagen.filename:
                producto.imagen_url = guardar_imagen(imagen)

            producto.codigo = codigo
            producto.nombre = nombre
            producto.descripcion = descripcion
            producto.precio = precio
            producto.stock = stock
            producto.categoria_id = categoria_id
            producto.marca_id = marca_id
            producto.ultima_actualizacion = datetime.now()

            db.session.commit()

            flash(
                "Producto actualizado correctamente.",
                "success"
            )

            return redirect(url_for("admin_productos"))

        except ValueError as e:
            db.session.rollback()
            flash(str(e), "error")
            return redirect(
                url_for("editar_producto", producto_id=producto_id)
            )

        except Exception as e:
            db.session.rollback()
            print("ERROR EDITANDO PRODUCTO:", e)
            flash(
                "No se pudo actualizar el producto.",
                "error"
            )
            return redirect(
                url_for("editar_producto", producto_id=producto_id)
            )

    return render_template(
        "admin_producto_form.html",
        producto=producto,
        categorias=categorias,
        marcas=marcas
    )


@app.route(
    "/admin/productos/eliminar/<int:producto_id>",
    methods=["POST"]
)
def eliminar_producto(producto_id):

    if not usuario_es_admin():
        flash(
            "Debes iniciar sesión como administrador.",
            "error"
        )
        return redirect(url_for("login"))

    producto = db.session.get(
        Producto,
        producto_id
    )

    if not producto:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("admin_productos"))

    try:
        tiene_pedidos = (
            DetallePedido.query
            .filter_by(producto_id=producto_id)
            .first()
        )

        tiene_facturas = (
            FacturaDetalle.query
            .filter_by(producto_id=producto_id)
            .first()
        )

        if tiene_pedidos or tiene_facturas:
            flash(
                "No se puede eliminar: el producto tiene "
                "historial de ventas o facturas.",
                "error"
            )
            return redirect(url_for("admin_productos"))

        # También elimina una posible fila del carrito persistente.
        from models import Carrito
        Carrito.query.filter_by(
            producto_id=producto_id
        ).delete(synchronize_session=False)

        db.session.delete(producto)
        db.session.commit()

        flash(
            "Producto eliminado correctamente.",
            "success"
        )

    except Exception as e:
        db.session.rollback()
        print("ERROR ELIMINANDO PRODUCTO:", e)
        flash(
            "No se pudo eliminar el producto.",
            "error"
        )

    return redirect(url_for("admin_productos"))


# FACTURA PDF


@app.route(
    "/factura/<int:factura_id>/pdf"
)
def factura_pdf(factura_id):

    factura = db.session.get(
        FacturaCabecera,
        factura_id
    )

    if not factura:

        return "Factura no encontrada", 404

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=letter
    )

    ancho, alto = letter

    y = alto - 50


    # ENCABEZADO

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawString(
        50,
        y,
        "TECHSTORE"
    )

    y -= 30

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        y,
        "FACTURA DE VENTA"
    )

    y -= 25

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        50,
        y,
        f"Factura: {factura.numero_factura}"
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f"Fecha: {factura.fecha.strftime('%d/%m/%Y %H:%M')}"
    )

    y -= 30


    # CLIENTE

    pdf.setFont(
        "Helvetica-Bold",
        11
    )

    pdf.drawString(
        50,
        y,
        "Cliente"
    )

    y -= 18

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        50,
        y,
        f"Nombre: {factura.usuario.nombre}"
    )

    y -= 18

    pdf.drawString(
        50,
        y,
        f"Correo: {factura.usuario.correo}"
    )

    y -= 30

    # PRODUCTOS

    pdf.setFont(
        "Helvetica-Bold",
        10
    )

    pdf.drawString(
        50,
        y,
        "Producto"
    )

    pdf.drawString(
        300,
        y,
        "Cantidad"
    )

    pdf.drawString(
        370,
        y,
        "Precio"
    )

    pdf.drawString(
        450,
        y,
        "Subtotal"
    )

    y -= 18

    pdf.setFont(
        "Helvetica",
        9
    )

    for detalle in factura.detalles:

        nombre = detalle.producto.nombre

        if len(nombre) > 38:
            nombre = nombre[:38] + "..."

        pdf.drawString(
            50,
            y,
            nombre
        )

        pdf.drawString(
            300,
            y,
            str(detalle.cantidad)
        )

        pdf.drawString(
            370,
            y,
            f"${detalle.precio_unitario:.2f}"
        )

        pdf.drawString(
            450,
            y,
            f"${detalle.subtotal:.2f}"
        )

        y -= 18

        if y < 100:

            pdf.showPage()

            y = alto - 50


    # TOTALES

    y -= 15

    pdf.setFont(
        "Helvetica-Bold",
        10
    )

    pdf.drawString(
        350,
        y,
        "Subtotal:"
    )

    pdf.drawString(
        450,
        y,
        f"${factura.subtotal:.2f}"
    )

    y -= 18

    pdf.drawString(
        350,
        y,
        "IVA 15%:"
    )

    pdf.drawString(
        450,
        y,
        f"${factura.impuestos:.2f}"
    )

    y -= 20

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        350,
        y,
        "TOTAL:"
    )

    pdf.drawString(
        450,
        y,
        f"${factura.total:.2f}"
    )

    y -= 40

    pdf.setFont(
        "Helvetica",
        9
    )

    pdf.drawString(
        50,
        y,
        "Gracias por su compra."
    )

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            f"{factura.numero_factura}.pdf"
        )
    )



if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )