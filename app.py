# punto de entrada a la aplicacion 

from flask import Flask, render_template
from config import Config
from models import db, Producto

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route("/")

def inicio():
    productos = Producto.query.filter_by(activo = True).all()
    return render_template("index.html", productos = productos)

@app.route("/producto/<int:producto_id>")

def detalle_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    return render_template("detalle.html", producto = producto)

if __name__ == "__main__":
    app.run(debug=True)