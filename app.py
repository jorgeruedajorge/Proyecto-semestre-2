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
import re
from werkzeug.utils import secure_filename

from decimal import Decimal
from sqlalchemy import text
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.lib.units import mm

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


# =========================================================
# CONFIGURACIÓN
# =========================================================

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)

# La SECRET_KEY ya viene desde Config.
# No se sobrescribe aquí para mantener una sola configuración.


# =========================================================
# INICIO
# =========================================================

@app.route("/")
def inicio():

    return redirect(
        url_for("catalogo")
    )



# =========================================================
# LOGIN
# =========================================================

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


# =========================================================
# LOGOUT
# =========================================================

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


# =========================================================
# CATÁLOGO
# =========================================================

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


# =========================================================
# DETALLE
# =========================================================

@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):

    producto = Producto.query.get_or_404(
        producto_id
    )

    return render_template(
        "detalle.html",
        producto=producto
    )


# =========================================================
# CARRITO
# =========================================================

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


# =========================================================
# AGREGAR AL CARRITO
# =========================================================

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


# =========================================================
# ELIMINAR
# =========================================================

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


# =========================================================
# VACIAR
# =========================================================

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


# =========================================================
# CONTADOR DEL CARRITO
# =========================================================

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


# =========================================================
# CHECKOUT
# =========================================================

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

        cedula = request.form.get(
            "cedula",
            ""
        ).strip()

        metodo_id = request.form.get(
            "metodo_pago",
            type=int
        )

        if not nombre or not correo or not cedula:

            flash(
                "Ingrese nombre, cédula y correo.",
                "error"
            )

            return redirect(
                url_for("checkout")
            )

        if not re.fullmatch(r"\d{10}", cedula):

            flash(
                "La cédula debe contener exactamente 10 dígitos.",
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

            # =============================================
            # BUSCAR O CREAR USUARIO
            # =============================================

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
                    cedula=cedula,
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
                usuario.cedula = cedula

            # =============================================
            # ESTADO PAGADO
            # =============================================

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

            # =============================================
            # CREAR PEDIDO
            # =============================================

            pedido = Pedido(
                usuario_id=usuario.id_usuario,
                fecha=datetime.now(),
                estado_id=estado.id_estado,
                total=total
            )

            db.session.add(pedido)

            db.session.flush()

            # =============================================
            # DETALLES DEL PEDIDO
            # =============================================

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

            # =============================================
            # PAGO
            # =============================================

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

            # =============================================
            # FACTURA
            # =============================================

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

            # =============================================
            # DETALLE FACTURA
            # =============================================

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

            # =============================================
            # GUARDAR TODO
            # =============================================

            db.session.commit()

            # Vaciar carrito
            session["carrito"] = {}
            session.modified = True

            # Confirmación visual de la compra
            flash(
                f"¡Compra realizada con éxito! "
                f"Tu pedido #{pedido.id_pedido} fue confirmado y "
                f"la factura {factura.numero_factura} ha sido generada.",
                "success"
            )

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



# =========================================================
# ADMINISTRACIÓN DE PRODUCTOS
# =========================================================

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


@app.route("/admin/dashboard/pdf")
def dashboard_pdf():

    if not usuario_es_admin():
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for("login"))

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
        print("ERROR GENERANDO PDF DEL DASHBOARD:", e)
        return "No se pudieron consultar los datos del dashboard.", 500

    productos = Producto.query.order_by(Producto.id_producto.desc()).all()
    dashboard = datos["dashboard"][0] if datos["dashboard"] else {}

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=12*mm, leftMargin=12*mm,
        topMargin=15*mm, bottomMargin=17*mm,
        title="Dashboard TechStore", author="TechStore"
    )

    azul = colors.HexColor("#2563EB")
    oscuro = colors.HexColor("#0F172A")
    gris = colors.HexColor("#64748B")
    claro = colors.HexColor("#EFF6FF")
    borde = colors.HexColor("#CBD5E1")

    styles = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=styles["Heading1"], fontName="Helvetica-Bold",
                       fontSize=20, textColor=oscuro, spaceAfter=2*mm)
    SH = ParagraphStyle("SH", parent=styles["Normal"], fontSize=8.5, textColor=gris)
    TH = ParagraphStyle("TH", parent=styles["Normal"], fontName="Helvetica-Bold",
                        fontSize=7.2, textColor=colors.white)
    TD = ParagraphStyle("TD", parent=styles["Normal"], fontSize=7.2,
                        leading=9, textColor=oscuro)
    TDR = ParagraphStyle("TDR", parent=TD, alignment=TA_RIGHT)

    story = [
        Paragraph("TECHSTORE", H),
        Paragraph("Dashboard administrativo · Inventario, ventas y gestión", SH),
        Spacer(1, 5*mm)
    ]

    # KPIs
    kpis = [
        ("Total productos", dashboard.get("total_productos", 0)),
        ("Unidades en inventario", dashboard.get("unidades_totales", 0)),
        ("Stock bajo", dashboard.get("productos_stock_bajo", 0)),
        ("Agotados", dashboard.get("productos_agotados", 0)),
        ("Valor del inventario", f"${float(dashboard.get('valor_total_inventario', 0)):,.2f}")
    ]
    kdata = [[Paragraph(k, SH) for k,v in kpis],
             [Paragraph(str(v), ParagraphStyle("KV", parent=TD, fontSize=12,
                                                fontName="Helvetica-Bold", textColor=oscuro))
              for k,v in kpis]]
    kt = Table(kdata, colWidths=[36*mm]*5)
    kt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),claro),
        ("BOX",(0,0),(-1,-1),.5,borde),
        ("INNERGRID",(0,0),(-1,-1),.5,borde),
        ("LEFTPADDING",(0,0),(-1,-1),3*mm),
        ("RIGHTPADDING",(0,0),(-1,-1),3*mm),
        ("TOPPADDING",(0,0),(-1,-1),2.5*mm),
        ("BOTTOMPADDING",(0,0),(-1,-1),2.5*mm),
    ]))
    story += [kt, Spacer(1, 7*mm)]

    def add_section(title, data, columns, widths=None, max_rows=None):
        story.append(Paragraph(title, ParagraphStyle(
            "Sec"+str(len(story)), parent=styles["Heading2"],
            fontName="Helvetica-Bold", fontSize=11, textColor=azul,
            spaceBefore=3*mm, spaceAfter=2*mm
        )))
        if not data:
            story.append(Paragraph("Sin registros.", SH))
            return
        shown=data if max_rows is None else data[:max_rows]
        rows=[[Paragraph(str(c[0]),TH) for c in columns]]
        for r in shown:
            vals=[]
            for key,align in columns:
                val=r.get(key,"")
                if val is None: val=""
                if isinstance(val,(float,Decimal)):
                    val=f"{float(val):,.2f}"
                vals.append(Paragraph(str(val), TDR if align=="right" else TD))
            rows.append(vals)
        if widths is None:
            widths=[(doc.width/len(columns))]*len(columns)
        t=Table(rows,colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),oscuro),
            ("BOX",(0,0),(-1,-1),.45,borde),
            ("INNERGRID",(0,0),(-1,-1),.3,borde),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING",(0,0),(-1,-1),2*mm),
            ("RIGHTPADDING",(0,0),(-1,-1),2*mm),
            ("TOPPADDING",(0,0),(-1,-1),2*mm),
            ("BOTTOMPADDING",(0,0),(-1,-1),2*mm),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ]))
        story.append(t)
        story.append(Spacer(1, 3*mm))

    add_section("1. Inventario completo", datos["inventario"],
        [("id_producto","left"),("codigo","left"),("nombre","left"),("tipo","left"),
         ("categoria","left"),("marca","left"),("precio","right"),("stock","right"),
         ("valor_inventario","right"),("estado_stock","left")],
        [10*mm,20*mm,39*mm,18*mm,24*mm,22*mm,18*mm,13*mm,22*mm,22*mm])

    add_section("2. Productos con stock bajo", datos["stock_bajo"],
        [("id_producto","left"),("codigo","left"),("nombre","left"),("categoria","left"),
         ("marca","left"),("precio","right"),("stock","right")],
        [12*mm,24*mm,52*mm,27*mm,27*mm,22*mm,17*mm])

    add_section("3. Productos agotados", datos["agotados"],
        [("id_producto","left"),("codigo","left"),("nombre","left"),("tipo","left"),
         ("categoria","left"),("marca","left"),("precio","right")],
        [12*mm,24*mm,52*mm,20*mm,28*mm,27*mm,20*mm])

    add_section("4. Ventas / pedidos", datos["ventas"],
        [(k,"right" if k in ["id_pedido","total"] else "left")
         for k in (list(datos["ventas"][0].keys()) if datos["ventas"] else [])],
        None)

    add_section("5. Resumen de ventas", datos["resumen_ventas"],
        [(k,"right" if any(x in k.lower() for x in ["total","cantidad","monto","ventas"])
          else "left")
         for k in (list(datos["resumen_ventas"][0].keys()) if datos["resumen_ventas"] else [])])

    add_section("6. Detalle de ventas", datos["detalle_ventas"],
        [(k,"right" if any(x in k.lower() for x in ["cantidad","precio","subtotal","total"])
          else "left")
         for k in (list(datos["detalle_ventas"][0].keys()) if datos["detalle_ventas"] else [])])

    add_section("7. Productos más vendidos", datos["mas_vendidos"],
        [(k,"right" if any(x in k.lower() for x in ["cantidad","ventas","total"])
          else "left")
         for k in (list(datos["mas_vendidos"][0].keys()) if datos["mas_vendidos"] else [])])

    add_section("8. Inventario por categoría", datos["inventario_categoria"],
        [(k,"right" if any(x in k.lower() for x in ["cantidad","stock","valor"])
          else "left")
         for k in (list(datos["inventario_categoria"][0].keys()) if datos["inventario_categoria"] else [])])

    # Gestión de productos: todos los elementos visibles en el dashboard.
    prod_rows=[]
    for p in productos:
        prod_rows.append({
            "id_producto": p.id_producto, "codigo": p.codigo,
            "nombre": p.nombre, "tipo": p.tipo,
            "categoria": p.categoria.nombre if p.categoria else "",
            "marca": p.marca.nombre if p.marca else "",
            "precio": p.precio, "stock": p.stock
        })
    add_section("9. Gestión de productos", prod_rows,
        [("id_producto","right"),("codigo","left"),("nombre","left"),("tipo","left"),
         ("categoria","left"),("marca","left"),("precio","right"),("stock","right")],
        [12*mm,25*mm,49*mm,20*mm,27*mm,27*mm,20*mm,17*mm])

    def footer(c, d):
        c.saveState()
        c.setStrokeColor(borde)
        c.line(12*mm, 11*mm, 198*mm, 11*mm)
        c.setFont("Helvetica", 7)
        c.setFillColor(gris)
        c.drawString(12*mm, 7*mm, "TechStore · Dashboard administrativo")
        c.drawRightString(198*mm, 7*mm, f"Página {d.page}")
        c.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return send_file(
        buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"dashboard_techstore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )



@app.route("/admin/reporte/<reporte>/pdf")
def reporte_dashboard_pdf(reporte):
    """Genera un PDF independiente para cada módulo del dashboard."""
    if not usuario_es_admin():
        flash("Debes iniciar sesión como administrador.", "error")
        return redirect(url_for("login"))

    vistas = {
        "inventario": ("Inventario completo", "vw_inventario"),
        "stock-bajo": ("Productos con stock bajo", "vw_stock_bajo"),
        "agotados": ("Productos agotados", "vw_productos_agotados"),
        "ventas": ("Ventas y pedidos", "vw_ventas"),
        "resumen-ventas": ("Resumen de ventas", "vw_resumen_ventas"),
        "detalle-ventas": ("Detalle de ventas", "vw_detalle_ventas"),
        "mas-vendidos": ("Productos más vendidos", "vw_productos_mas_vendidos"),
        "categorias": ("Inventario por categoría", "vw_inventario_categoria"),
    }

    if reporte == "dashboard":
        try:
            result = db.session.execute(text('SELECT * FROM "vw_dashboard_inventario"'))
            dashboard = result.mappings().first() or {}
        except Exception as e:
            db.session.rollback()
            print("ERROR PDF DASHBOARD:", e)
            return "No se pudieron consultar los datos.", 500

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=16*mm,
                                leftMargin=16*mm, topMargin=18*mm, bottomMargin=18*mm,
                                title="Resumen del Dashboard - TechStore")
        styles = getSampleStyleSheet()
        azul = colors.HexColor("#2563EB")
        oscuro = colors.HexColor("#0F172A")
        gris = colors.HexColor("#64748B")
        claro = colors.HexColor("#EFF6FF")
        borde = colors.HexColor("#CBD5E1")
        story = [Paragraph("TECHSTORE", ParagraphStyle("dh", parent=styles["Heading1"], fontSize=22,
                    fontName="Helvetica-Bold", textColor=oscuro)),
                 Paragraph("Resumen ejecutivo del dashboard", ParagraphStyle("ds", parent=styles["Normal"],
                    fontSize=9, textColor=gris)), Spacer(1, 8*mm)]
        kpis = [
            ("Total productos", dashboard.get("total_productos", 0)),
            ("Unidades en inventario", dashboard.get("unidades_totales", 0)),
            ("Stock bajo", dashboard.get("productos_stock_bajo", 0)),
            ("Productos agotados", dashboard.get("productos_agotados", 0)),
            ("Valor del inventario", f"${float(dashboard.get('valor_total_inventario', 0)):,.2f}"),
        ]
        for titulo, valor in kpis:
            t = Table([[Paragraph(titulo, ParagraphStyle("kl", parent=styles["Normal"], fontSize=9, textColor=gris))],
                       [Paragraph(str(valor), ParagraphStyle("kv", parent=styles["Normal"], fontSize=19,
                            fontName="Helvetica-Bold", textColor=oscuro))]], colWidths=[doc.width])
            t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), claro), ("BOX", (0,0), (-1,-1), .6, borde),
                                   ("LEFTPADDING", (0,0), (-1,-1), 6*mm), ("RIGHTPADDING", (0,0), (-1,-1), 6*mm),
                                   ("TOPPADDING", (0,0), (-1,-1), 4*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 4*mm)]))
            story += [t, Spacer(1, 4*mm)]
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("Generado automáticamente por TechStore · " + datetime.now().strftime("%d/%m/%Y %H:%M"),
            ParagraphStyle("df", parent=styles["Normal"], fontSize=8, textColor=gris)))
        doc.build(story)
        buffer.seek(0)
        return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                         download_name=f"dashboard_resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

    if reporte == "productos":
        titulo = "Gestión de productos"
        productos = Producto.query.order_by(Producto.id_producto.desc()).all()
        data = [{"id_producto": p.id_producto, "codigo": p.codigo, "nombre": p.nombre,
                 "tipo": p.tipo, "categoria": p.categoria.nombre if p.categoria else "",
                 "marca": p.marca.nombre if p.marca else "", "precio": p.precio, "stock": p.stock}
                for p in productos]
        keys = ["id_producto", "codigo", "nombre", "tipo", "categoria", "marca", "precio", "stock"]
    elif reporte in vistas:
        titulo, vista = vistas[reporte]
        try:
            result = db.session.execute(text(f'SELECT * FROM "{vista}"'))
            data = result.mappings().all()
        except Exception as e:
            db.session.rollback()
            print("ERROR PDF REPORTE:", e)
            return "No se pudieron consultar los datos.", 500
        keys = list(data[0].keys()) if data else []
    else:
        return "Reporte no encontrado.", 404

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=__import__('reportlab.lib.pagesizes', fromlist=['landscape']).landscape(letter),
                            rightMargin=10*mm, leftMargin=10*mm, topMargin=15*mm, bottomMargin=17*mm,
                            title=f"{titulo} - TechStore")
    styles = getSampleStyleSheet()
    azul = colors.HexColor("#2563EB")
    oscuro = colors.HexColor("#0F172A")
    gris = colors.HexColor("#64748B")
    borde = colors.HexColor("#CBD5E1")
    blanco = colors.white
    H = ParagraphStyle("RH", parent=styles["Heading1"], fontSize=18, fontName="Helvetica-Bold", textColor=oscuro, spaceAfter=2*mm)
    SH = ParagraphStyle("RS", parent=styles["Normal"], fontSize=8, textColor=gris, spaceAfter=5*mm)
    TH = ParagraphStyle("RTH", parent=styles["Normal"], fontSize=6.5, leading=8, fontName="Helvetica-Bold", textColor=blanco)
    TD = ParagraphStyle("RTD", parent=styles["Normal"], fontSize=6.5, leading=8, textColor=oscuro)
    TR = ParagraphStyle("RTR", parent=TD, alignment=TA_RIGHT)
    story = [Paragraph("TECHSTORE", H), Paragraph(titulo, ParagraphStyle("RT", parent=styles["Heading2"],
                fontSize=12, fontName="Helvetica-Bold", textColor=azul)),
             Paragraph(f"Reporte independiente · Generado {datetime.now().strftime('%d/%m/%Y %H:%M')}", SH)]

    if not data:
        story.append(Paragraph("No existen registros para este reporte.", TD))
    else:
        def label(k):
            return str(k).replace("_", " ").title()
        rows = [[Paragraph(label(k), TH) for k in keys]]
        for r in data:
            row=[]
            for k in keys:
                v=r.get(k, "")
                if v is None: v=""
                if isinstance(v, (float, Decimal)):
                    v=f"{float(v):,.2f}"
                txt=str(v)
                align = "right" if isinstance(v, (int,float,Decimal)) or any(x in k.lower() for x in ["precio","total","valor","cantidad","stock","monto"]) else "left"
                row.append(Paragraph(txt.replace("&", "&amp;"), TR if align == "right" else TD))
            rows.append(row)
        n=len(keys)
        widths=[doc.width/n]*n
        table=Table(rows, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), oscuro), ("TEXTCOLOR", (0,0), (-1,0), blanco),
            ("BOX", (0,0), (-1,-1), .5, borde), ("INNERGRID", (0,0), (-1,-1), .3, borde),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0,0), (-1,-1), 1.8*mm), ("RIGHTPADDING", (0,0), (-1,-1), 1.8*mm),
            ("TOPPADDING", (0,0), (-1,-1), 1.8*mm), ("BOTTOMPADDING", (0,0), (-1,-1), 1.8*mm),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(table)

    def footer(c, d):
        c.saveState(); c.setStrokeColor(borde); c.line(10*mm, 11*mm, 287*mm, 11*mm)
        c.setFont("Helvetica", 7); c.setFillColor(gris)
        c.drawString(10*mm, 7*mm, "TechStore · Reporte independiente del dashboard")
        c.drawRightString(287*mm, 7*mm, f"Página {d.page}"); c.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{reporte.replace('-', '_')}_techstore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

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



# =========================================================
# FACTURA PDF
# =========================================================

@app.route(
    "/factura/<int:factura_id>/pdf"
)
def factura_pdf(factura_id):

    factura = db.session.get(FacturaCabecera, factura_id)

    if not factura:
        return "Factura no encontrada", 404

    buffer = BytesIO()

    # Documento A4 con márgenes profesionales.
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Factura {factura.numero_factura}",
        author="TechStore"
    )

    styles = getSampleStyleSheet()
    azul = colors.HexColor("#2563EB")
    azul_oscuro = colors.HexColor("#0F172A")
    gris = colors.HexColor("#64748B")
    gris_claro = colors.HexColor("#F1F5F9")
    borde = colors.HexColor("#CBD5E1")
    verde = colors.HexColor("#16A34A")

    titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=25,
        textColor=azul_oscuro,
        spaceAfter=3
    )
    subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=gris
    )
    etiqueta = ParagraphStyle(
        "Etiqueta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=gris
    )
    normal = ParagraphStyle(
        "NormalFactura",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=azul_oscuro
    )
    total_style = ParagraphStyle(
        "Total",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=azul_oscuro,
        alignment=TA_RIGHT
    )

    story = []

    # Encabezado.
    encabezado_izq = [
        Paragraph("TECHSTORE", titulo),
        Paragraph("Tecnología que impulsa tus ideas", subtitulo),
        Spacer(1, 3 * mm),
        Paragraph("FACTURA DE VENTA", ParagraphStyle(
            "FacturaLabel", parent=etiqueta, textColor=azul
        ))
    ]

    encabezado_der = [
        Paragraph("<b>N.º " + str(factura.numero_factura) + "</b>", ParagraphStyle(
            "Num", parent=normal, fontSize=11, alignment=TA_RIGHT
        )),
        Paragraph(
            factura.fecha.strftime("%d/%m/%Y %H:%M"),
            ParagraphStyle("Fecha", parent=subtitulo, alignment=TA_RIGHT)
        ),
        Spacer(1, 3 * mm),
        Paragraph("✓ PAGADO", ParagraphStyle(
            "Pagado", parent=normal, textColor=verde,
            fontName="Helvetica-Bold", alignment=TA_RIGHT
        ))
    ]

    head = Table([[encabezado_izq, encabezado_der]], colWidths=[112*mm, 64*mm])
    head.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("LINEBELOW", (0,0), (-1,-1), 2, azul),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5*mm),
    ]))
    story += [head, Spacer(1, 7*mm)]

    # Cliente.
    cliente_data = [
        [Paragraph("DATOS DEL CLIENTE", etiqueta),
         Paragraph("INFORMACIÓN DE PAGO", etiqueta)],
        [Paragraph(
            f"<b>{factura.usuario.nombre}</b><br/>"
            f"Cédula: {factura.usuario.cedula or 'No registrada'}<br/>"
            f"Correo: {factura.usuario.correo}",
            normal
        ),
         Paragraph(
            f"Método: {factura.pedido.pagos[0].metodo.nombre if factura.pedido and factura.pedido.pagos else 'No registrado'}<br/>"
            f"Estado: <b>Pagado</b><br/>"
            f"Pedido: #{factura.pedido_id}",
            normal
        )]
    ]
    cliente = Table(cliente_data, colWidths=[88*mm, 88*mm])
    cliente.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), gris_claro),
        ("BOX", (0,0), (-1,-1), .6, borde),
        ("INNERGRID", (0,0), (-1,-1), .5, borde),
        ("LEFTPADDING", (0,0), (-1,-1), 4*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 4*mm),
        ("TOPPADDING", (0,0), (-1,-1), 3*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3*mm),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story += [cliente, Spacer(1, 7*mm)]

    # Detalle.
    rows = [[
        Paragraph("PRODUCTO", etiqueta),
        Paragraph("CANT.", etiqueta),
        Paragraph("PRECIO UNIT.", etiqueta),
        Paragraph("SUBTOTAL", etiqueta)
    ]]

    for detalle in factura.detalles:
        rows.append([
            Paragraph(detalle.producto.nombre, normal),
            Paragraph(str(detalle.cantidad), normal),
            Paragraph(f"${float(detalle.precio_unitario):,.2f}",
                      ParagraphStyle("r1", parent=normal, alignment=TA_RIGHT)),
            Paragraph(f"${float(detalle.subtotal):,.2f}",
                      ParagraphStyle("r2", parent=normal, alignment=TA_RIGHT))
        ])

    tabla = Table(rows, colWidths=[91*mm, 20*mm, 33*mm, 32*mm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), azul_oscuro),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BOX", (0,0), (-1,-1), .6, borde),
        ("INNERGRID", (0,0), (-1,-1), .35, borde),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("LEFTPADDING", (0,0), (-1,-1), 3*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 3*mm),
        ("TOPPADDING", (0,0), (-1,-1), 3*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3*mm),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    story += [tabla, Spacer(1, 6*mm)]

    # Totales.
    totales = [
        ["Subtotal", f"${float(factura.subtotal):,.2f}"],
        ["IVA 15%", f"${float(factura.impuestos):,.2f}"],
        ["TOTAL", f"${float(factura.total):,.2f}"]
    ]
    tt = Table(totales, colWidths=[43*mm, 38*mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,1), "Helvetica"),
        ("FONTNAME", (0,2), (-1,2), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("FONTSIZE", (0,2), (-1,2), 13),
        ("TEXTCOLOR", (0,0), (-1,-1), azul_oscuro),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 2.5*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2.5*mm),
        ("LINEABOVE", (0,2), (-1,2), 1.5, azul),
        ("BACKGROUND", (0,2), (-1,2), colors.HexColor("#EFF6FF")),
        ("LEFTPADDING", (0,0), (-1,-1), 3*mm),
        ("RIGHTPADDING", (0,0), (-1,-1), 3*mm),
    ]))
    story += [tt, Spacer(1, 12*mm)]

    story.append(Paragraph(
        "Gracias por confiar en TechStore. Conserve esta factura como comprobante de su compra.",
        ParagraphStyle("Gracias", parent=subtitulo, alignment=TA_CENTER, fontSize=8.5)
    ))

    def pie_pagina(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(borde)
        canvas_obj.line(16*mm, 12*mm, 194*mm, 12*mm)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(gris)
        canvas_obj.drawString(16*mm, 8*mm, "TechStore · Factura electrónica de referencia")
        canvas_obj.drawRightString(194*mm, 8*mm, f"Página {doc_obj.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=pie_pagina, onLaterPages=pie_pagina)

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{factura.numero_factura}.pdf"
    )


# =========================================================
# EJECUTAR
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )