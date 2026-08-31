# TechStore

Tienda de productos tecnológicos desarrollada con Flask, PostgreSQL,
SQLAlchemy, HTML y CSS.

## Estructura

- app.py
- models.py
- config.py
- init_db.py
- templates/catalogo.html
- templates/detalle.html
- templates/carrito.html
- templates/index.html
- static/css/estilos.css

## Rutas

- `/` -> redirige al catálogo
- `/catalogo` -> catálogo de productos
- `/producto/<id>` -> detalle
- `/carrito` -> carrito
- `/carrito/agregar/<id>` -> agrega producto
- `/carrito/eliminar/<id>` -> elimina producto
- `/carrito/vaciar` -> vacía el carrito

## Ejecución

1. Configura `.env` con DB_USER, DB_PASSWORD, DB_HOST, DB_PORT y DB_NAME.
2. Ejecuta `python init_db.py` una sola vez para crear las tablas y datos de prueba.
3. Ejecuta `python app.py`.
4. Abre la dirección que muestre Flask.

El carrito de esta versión se mantiene en la sesión de Flask, por lo que
no requiere mostrar ni solicitar un usuario en la interfaz.
