from datetime import datetime
from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# =========================================================
# ROLES
# =========================================================

class RolUsuario(db.Model):
    __tablename__ = "rolesusuario"

    id_rol = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(50),
        nullable=False
    )

    usuarios = db.relationship(
        "Usuario",
        back_populates="rol"
    )

    def __repr__(self):
        return f"<RolUsuario {self.nombre}>"


# =========================================================
# USUARIOS
# =========================================================

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(100),
        nullable=False
    )

    correo = db.Column(
        db.String(100),
        nullable=False
    )

    # Cédula ecuatoriana de 10 dígitos. Se solicita en el checkout.
    cedula = db.Column(
        db.String(10),
        nullable=True
    )

    password = db.Column(
        "contraseña",
        db.String(255),
        nullable=False
    )

    rol_id = db.Column(
        db.Integer,
        db.ForeignKey("rolesusuario.id_rol"),
        nullable=False
    )

    rol = db.relationship(
        "RolUsuario",
        back_populates="usuarios"
    )

    carritos = db.relationship(
        "Carrito",
        back_populates="usuario"
    )

    pedidos = db.relationship(
        "Pedido",
        back_populates="usuario"
    )

    facturas = db.relationship(
        "FacturaCabecera",
        back_populates="usuario"
    )

    def set_password(self, password_plano):
        # Proyecto académico: contraseña almacenada en texto plano.
        self.password = password_plano

    def check_password(self, password_plano):
        return self.password == password_plano

    def es_admin(self):
        if self.rol is None:
            return False

        return self.rol.nombre.lower() in [
            "admin",
            "administrador"
        ]

    def __repr__(self):
        return f"<Usuario {self.correo}>"


# =========================================================
# CATEGORÍAS
# =========================================================

class CategoriaProducto(db.Model):
    __tablename__ = "categoriaproducto"

    id_categoria = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(50),
        nullable=False
    )

    productos = db.relationship(
        "Producto",
        back_populates="categoria"
    )

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


# =========================================================
# MARCAS
# =========================================================

class Marca(db.Model):
    __tablename__ = "marcas"

    id_marca = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(50),
        nullable=False
    )

    productos = db.relationship(
        "Producto",
        back_populates="marca"
    )

    def __repr__(self):
        return f"<Marca {self.nombre}>"


# =========================================================
# PRODUCTOS
# =========================================================

class Producto(db.Model):
    __tablename__ = "productos"

    id_producto = db.Column(
        db.Integer,
        primary_key=True
    )

    tipo = db.Column(
        db.String(30),
        nullable=False
    )

    codigo = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    nombre = db.Column(
        db.String(150),
        nullable=False
    )

    descripcion = db.Column(
        db.Text
    )

    precio = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    stock = db.Column(
        db.Integer,
        nullable=False
    )

    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "categoriaproducto.id_categoria"
        ),
        nullable=False
    )

    marca_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "marcas.id_marca"
        ),
        nullable=False
    )

    # Ruta/URL de la imagen de referencia del producto.
    # Se almacena la ruta relativa y no el archivo binario dentro de PostgreSQL.
    imagen_url = db.Column(
        db.String(255),
        nullable=True
    )

    ultima_actualizacion = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    __mapper_args__ = {
        "polymorphic_on": tipo,
        "polymorphic_identity": "general"
    }

    categoria = db.relationship(
        "CategoriaProducto",
        back_populates="productos"
    )

    marca = db.relationship(
        "Marca",
        back_populates="productos"
    )

    carritos = db.relationship(
        "Carrito",
        back_populates="producto"
    )

    detalles_pedido = db.relationship(
        "DetallePedido",
        back_populates="producto"
    )

    detalles_factura = db.relationship(
        "FacturaDetalle",
        back_populates="producto"
    )

    def precio_final(self):
        return self.precio

    def descripcion_tipo(self):
        return "Producto general"

    def ficha(self):
        return (
            f"{self.nombre} | "
            f"Precio: ${self.precio:.2f} | "
            f"Stock: {self.stock}"
        )

    def tiene_imagen(self):
        return bool(self.imagen_url)

    def __repr__(self):
        return (
            f"<Producto "
            f"{self.id_producto} - {self.nombre}>"
        )


# =========================================================
# PRODUCTO FÍSICO
# =========================================================

class ProductoFisico(Producto):

    __tablename__ = "productos_fisicos"

    id_producto = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        primary_key=True
    )

    peso_kg = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    costo_envio_por_kg = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    __mapper_args__ = {
        "polymorphic_identity": "fisico",
        # Carga la tabla hija junto con Producto para evitar
        # errores de Deferred loader al acceder a peso_kg.
        "polymorphic_load": "inline"
    }

    def costo_envio(self):
        return (
            self.peso_kg *
            self.costo_envio_por_kg
        )

    def precio_final(self):
        return (
            self.precio +
            self.costo_envio()
        )

    def descripcion_tipo(self):
        return "Producto físico"


# =========================================================
# PRODUCTO DIGITAL
# =========================================================

class ProductoDigital(Producto):

    __tablename__ = "productos_digitales"

    id_producto = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        primary_key=True
    )

    licencia = db.Column(
        db.String(50),
        nullable=False
    )

    __mapper_args__ = {
        "polymorphic_identity": "digital",
        "polymorphic_load": "inline"
    }

    def costo_envio(self):
        return Decimal("0.00")

    def precio_final(self):
        return self.precio

    def descripcion_tipo(self):
        return "Producto digital"


# =========================================================
# PRODUCTO PERECIBLE
# =========================================================

class ProductoPerecible(Producto):

    __tablename__ = "productos_perecibles"

    id_producto = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        primary_key=True
    )

    dias_para_vencer = db.Column(
        db.Integer,
        nullable=False
    )

    __mapper_args__ = {
        "polymorphic_identity": "perecible",
        "polymorphic_load": "inline"
    }

    def esta_por_vencer(self):
        return self.dias_para_vencer <= 3

    def precio_final(self):

        if self.esta_por_vencer():
            return self.precio * Decimal("0.90")

        return self.precio

    def descripcion_tipo(self):
        return "Producto perecible"


# =========================================================
# CARRITO
# =========================================================

class Carrito(db.Model):
    __tablename__ = "carrito"

    id_carrito = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "usuarios.id_usuario"
        ),
        nullable=False
    )

    producto_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        nullable=False
    )

    cantidad = db.Column(
        db.Integer,
        nullable=False
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="carritos"
    )

    producto = db.relationship(
        "Producto",
        back_populates="carritos"
    )

    def subtotal(self):
        return (
            self.producto.precio *
            self.cantidad
        )


# =========================================================
# ESTADOS DEL PEDIDO
# =========================================================

class EstadoPedido(db.Model):
    __tablename__ = "estadospedido"

    id_estado = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(50),
        nullable=False
    )

    pedidos = db.relationship(
        "Pedido",
        back_populates="estado"
    )


# =========================================================
# PEDIDOS
# =========================================================

class Pedido(db.Model):
    __tablename__ = "pedidos"

    id_pedido = db.Column(
        db.Integer,
        primary_key=True
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "usuarios.id_usuario"
        ),
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    estado_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "estadospedido.id_estado"
        ),
        nullable=False
    )

    total = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="pedidos"
    )

    estado = db.relationship(
        "EstadoPedido",
        back_populates="pedidos"
    )

    detalles = db.relationship(
        "DetallePedido",
        back_populates="pedido",
        cascade="all, delete-orphan"
    )

    pagos = db.relationship(
        "Pago",
        back_populates="pedido",
        cascade="all, delete-orphan"
    )

    facturas = db.relationship(
        "FacturaCabecera",
        back_populates="pedido",
        cascade="all, delete-orphan"
    )


# =========================================================
# DETALLE DEL PEDIDO
# =========================================================

class DetallePedido(db.Model):
    __tablename__ = "detalledespedidos"

    id_detalle = db.Column(
        db.Integer,
        primary_key=True
    )

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "pedidos.id_pedido"
        ),
        nullable=False
    )

    producto_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        nullable=False
    )

    cantidad = db.Column(
        db.Integer,
        nullable=False
    )

    subtotal = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    pedido = db.relationship(
        "Pedido",
        back_populates="detalles"
    )

    producto = db.relationship(
        "Producto",
        back_populates="detalles_pedido"
    )


# =========================================================
# MÉTODOS DE PAGO
# =========================================================

class MetodoPago(db.Model):
    __tablename__ = "metodospago"

    id_metodo = db.Column(
        db.Integer,
        primary_key=True
    )

    nombre = db.Column(
        db.String(50),
        nullable=False
    )

    pagos = db.relationship(
        "Pago",
        back_populates="metodo"
    )


# =========================================================
# PAGOS
# =========================================================

class Pago(db.Model):
    __tablename__ = "pagos"

    id_pago = db.Column(
        db.Integer,
        primary_key=True
    )

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "pedidos.id_pedido"
        ),
        nullable=False
    )

    metodo_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "metodospago.id_metodo"
        ),
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    monto = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    pedido = db.relationship(
        "Pedido",
        back_populates="pagos"
    )

    metodo = db.relationship(
        "MetodoPago",
        back_populates="pagos"
    )


# =========================================================
# FACTURA CABECERA
# =========================================================

class FacturaCabecera(db.Model):
    __tablename__ = "facturacabecera"

    id_factura = db.Column(
        db.Integer,
        primary_key=True
    )

    numero_factura = db.Column(
        db.String(20),
        nullable=False,
        unique=True
    )

    pedido_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "pedidos.id_pedido"
        ),
        nullable=False
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "usuarios.id_usuario"
        ),
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    subtotal = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    impuestos = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    total = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    pedido = db.relationship(
        "Pedido",
        back_populates="facturas"
    )

    usuario = db.relationship(
        "Usuario",
        back_populates="facturas"
    )

    detalles = db.relationship(
        "FacturaDetalle",
        back_populates="factura",
        cascade="all, delete-orphan"
    )


# =========================================================
# FACTURA DETALLE
# =========================================================

class FacturaDetalle(db.Model):
    __tablename__ = "facturadetalle"

    id_detalle = db.Column(
        db.Integer,
        primary_key=True
    )

    factura_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "facturacabecera.id_factura"
        ),
        nullable=False
    )

    producto_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "productos.id_producto"
        ),
        nullable=False
    )

    cantidad = db.Column(
        db.Integer,
        nullable=False
    )

    precio_unitario = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    subtotal = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    factura = db.relationship(
        "FacturaCabecera",
        back_populates="detalles"
    )

    producto = db.relationship(
        "Producto",
        back_populates="detalles_factura"
    )