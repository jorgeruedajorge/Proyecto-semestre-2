from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key = True)
    nombre = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(120), unique = True, nullable = False)
    password_hash = db.Column(db.String(255), nullable = False)
    rol = db.Column(db.String(20), nullable=False, default="cliente")
    fecha_registro = db.Column(db.DateTime, default = datetime.utcnow)

    def set_password(self, password_plano):
        self.password_hash = generate_password_hash(password_plano)

    def check_password(self, password_plano):
        return check_password_hash(self.password_hash, password_plano)

    def es_admin(self):
        return self.rol == "admin"

    def __repr__(self):
        return f"<Usuario {self.email} {self.rol}>"

class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key = True)
    codigo = db.Column(db.String(20), unique = True, nullable = False)
    nombre = db.Column(db.String(150), nullable = False)
    precio_base = db.Column(db.Float, nullable = False)
    stock = db.Column(db.Integer, default = 0)
    activo = db.Column(db.Boolean, default = True)

    #Columna para producto fisico
    peso_kg = db.Column(db.Float, nullable = True)
    costo_envio_por_kg = db.Column(db.Float, nullable = True)

    #columna para producto digital
    licencia = db.Column(db.String(20), nullable = True)

    #columna para producto perecible
    dias_para_vencer = db.Column(db.Integer, nullable = True)

    #columna que indica que clase usar
    tipo = db.Column(db.String(30))

    __mapper_args__ = {
        "polymorphic_identity":"producto",
        "polymorphic_on":tipo
    }

    def precio_final(self):
        return self.precio_base

    def ficha(self):
        return (f"{self.codigo} {self.nombre} | Precio final: ${self.precio_final():.2f} | Stock: {self.stock}")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.codigo} - {self.nombre}>"

class ProductoFisico(Producto):
    __mapper_args__ = {"polymorphic_identity": "fisico"}

    def precio_final(self):
        envio = (self.peso_kg or 0) * (self.costo_envio_por_kg or 0)
        return self.precio_base + envio


class ProductoDigital(Producto):
    __mapper_args__ = {"polymorphic_identity": "digital"}

    MULTIPLICADORES = {
        "personal": 1.0,
        "comercial": 2.5,
        "educativa": 0.6,
    }

    def precio_final(self):
        multiplicador = self.MULTIPLICADORES.get(self.licencia, 1.0)
        return self.precio_base * multiplicador


class ProductoPerecible(Producto):
    __mapper_args__ = {"polymorphic_identity": "perecible"}

    def precio_final(self):
        dias = self.dias_para_vencer
        if dias is None:
            return self.precio_base
        if dias <= 3:
            return self.precio_base * 0.50
        elif dias <= 7:
            return self.precio_base * 0.80
        return self.precio_base