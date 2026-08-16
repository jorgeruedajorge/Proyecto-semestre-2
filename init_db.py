from app import app
from models import db, ProductoFisico, ProductoDigital, ProductoPerecible, Usuario

with app.app_context():
    print("Creando tablas...")
    db.drop_all()   # Borra todo si ya existía (útil mientras desarrollan)
    db.create_all()
    print("Tablas creadas.")

    # ── Usuarios de prueba ────────────────────────────────────
    admin = Usuario(nombre="Admin Principal", email="admin@tienda.com", rol="admin")
    admin.set_password("admin123")

    cliente = Usuario(nombre="Cliente Demo", email="cliente@tienda.com", rol="cliente")
    cliente.set_password("cliente123")

    db.session.add_all([admin, cliente])

    # ── Productos de prueba ─────────────────────────────────────
    p1 = ProductoFisico(
        codigo="FIS001", nombre="Audífonos Bluetooth", precio_base=25.00,
        stock=40, peso_kg=0.3, costo_envio_por_kg=2.50
    )
    p2 = ProductoDigital(
        codigo="DIG001", nombre="Curso de Python Avanzado", precio_base=40.00,
        stock=999, licencia="personal"
    )
    p3 = ProductoPerecible(
        codigo="PER001", nombre="Caja de fresas orgánicas", precio_base=8.00,
        stock=15, dias_para_vencer=2
    )

    db.session.add_all([p1, p2, p3])
    db.session.commit()

    print("Usuarios y productos de prueba insertados.")
    print("\nCredenciales de prueba:")
    print("  Admin   → admin@tienda.com   / admin123")
    print("  Cliente → cliente@tienda.com / cliente123")