# Normalización de la Base de Datos

## 1. Primera Forma Normal (1FN)

La base de datos cumple con la Primera Forma Normal debido a que
las tablas utilizan atributos con valores atómicos y no se almacenan
listas o grupos repetitivos dentro de una misma columna.

Cada registro representa una única instancia de la entidad
correspondiente y cada tabla dispone de una clave primaria que
permite identificar de manera única sus registros.

Por ejemplo, la información de los productos se mantiene en la
tabla correspondiente, mientras que la información de sus categorías
y marcas se mantiene en tablas independientes relacionadas mediante
claves foráneas.

## 2. Segunda Forma Normal (2FN)

La base de datos cumple con la Segunda Forma Normal debido a que
los atributos no clave dependen de la totalidad de la clave primaria.

Las entidades principales poseen claves primarias que identifican
individualmente cada registro. En las tablas que representan
relaciones entre entidades, los datos propios de la relación se
mantienen separados de los datos pertenecientes a cada entidad.

Por ejemplo, el detalle de los pedidos mantiene la información
correspondiente a la relación entre un pedido y un producto, mientras
que los datos propios del pedido y del producto permanecen en sus
respectivas tablas.

## 3. Tercera Forma Normal (3FN)

La base de datos se encuentra estructurada siguiendo la Tercera
Forma Normal, evitando almacenar información que dependa de otros
atributos no clave cuando dicha información puede mantenerse en una
entidad independiente.

Por ejemplo, las categorías y marcas de los productos se gestionan
mediante entidades independientes. De esta manera, los datos de una
categoría o una marca no necesitan repetirse en cada registro de
producto.

De forma similar, los estados de los pedidos y los métodos de pago
se manejan mediante entidades independientes relacionadas con las
operaciones correspondientes.

## 4. Conclusión

La estructura de la base de datos aplica los principios de
normalización hasta la Tercera Forma Normal (3FN), utilizando
entidades independientes, claves primarias y claves foráneas para
representar las relaciones.

La normalización permite reducir la duplicación de información,
mejorar la integridad de los datos y facilitar el mantenimiento de
la base de datos.