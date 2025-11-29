# python.exe -m venv .venv
# cd .venv/Scripts
# activate.bat
# py -m ensurepip --upgrade
# pip install -r requirements.txt

from functools import wraps
from flask import Flask, render_template, request, jsonify, make_response, session

from flask_cors import CORS, cross_origin

import mysql.connector.pooling
# import pusher
import pytz
import datetime

app            = Flask(__name__)
app.secret_key = "Test12345"
CORS(app)
con_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    host="185.232.14.52",
    database="u760464709_22005483_bd",
    user="u760464709_22005483_usr",
    password="XHIUfrIjh7|"
)


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")

@app.route("/pwa-sw.js")
def pwaSW():
    return app.send_static_file("pwa-sw.js")

# def pusherModulo():
#     pusher_client = pusher.Pusher()
    
#     pusher_client.trigger("canalModulos", "eventoModulo", {})
#     return make_response(jsonify({}))

def login(fun):
    @wraps(fun)
    def decorador(*args, **kwargs):
        if not session.get("login2"):
            return jsonify({
                "estado": "error",
                "respuesta": "No has iniciado sesión"
            }), 401
        return fun(*args, **kwargs)
    return decorador


@app.route("/")
def landingPage():
    return render_template("landing-page.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/login")
def appLogin():
    return render_template("login.html")
    # return "<h5>Hola, soy la view app</h5>"

@app.route("/resenas")
def resenas():
    return render_template("resenas.html")

@app.route("/resena")
def resena():
    return render_template("resena.html")

# @app.route("/notificaciones")
# def notificaciones():
#     return render_template("notificaciones.html")

@app.route("/offline")
def offline():
    return render_template("offline.html")

@app.route("/ping")
def ping():
    return "ping"

@app.route("/fechaHora")
def fechaHora():
    tz    = pytz.timezone("America/Matamoros")
    ahora = datetime.datetime.now(tz)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

@app.route("/iniciarSesion", methods=["POST"])
# Usar cuando solo se quiera usar CORS en rutas específicas
# @cross_origin()
def iniciarSesion():
    usuario    = request.form["usuario"]
    contrasena = request.form["contrasena"]

    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT id, usuario
    FROM usuarios
    WHERE usuario  = %s
    AND contrasena = %s
    """
    val    = (usuario, contrasena)

    cursor.execute(sql, val)
    usuarios = cursor.fetchall()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    session["login2"]     = False
    session["login2-id"]  = None
    session["login2-usr"] = None
    if usuarios:
        usuario = usuarios[0]
        session["login2"]     = True
        session["login2-id"]  = usuario["id"]
        session["login2-usr"] = usuario["usuario"]

    return make_response(jsonify(usuarios))

@app.route("/cerrarSesion", methods=["POST"])
@login
def cerrarSesion():
    session["login2"]     = False
    session["login2-id"]  = None
    session["login2-usr"] = None
    return make_response(jsonify({}))

@app.route("/preferencias")
@login
def preferencias():
    return make_response(jsonify({
        "usr": session.get("login2-usr")
    }))


@app.route("/resenas/buscar", methods=["GET"])
@login
def buscarResenas():
    args     = request.args
    busqueda = args["busqueda"]
    busqueda = f"%{busqueda}%"

    try:
        con    = con_pool.get_connection()
        cursor = con.cursor(dictionary=True)
        sql    = """
        SELECT id,
            nombre,
            restaurante,
            direccion,
            resena,
            calificacion
        FROM resenas_comidas
        WHERE nombre LIKE %s
        ORDER BY id DESC
        LIMIT 25 OFFSET 0
        """
        val    = (busqueda, )

        cursor.execute(sql, val)
        resenas = cursor.fetchall()

    except mysql.connector.errors.ProgrammingError as error:
        resenas = []

    finally:
        if cursor:
            cursor.close()
        if con and con.is_connected():
            con.close()

    return make_response(jsonify(resenas))

@app.route("/resena/guardar", methods=["POST"])
@login
def guardarResena():
    id          = request.form["id"]
    nombre     = request.form["nombre"]
    restaurante  = request.form["restaurante"]
    direccion   = request.form["direccion"]
    resena = request.form["resena"]
    calificacion = request.form["calificacion"]
    tz          = pytz.timezone("America/Matamoros")
    ahora       = datetime.datetime.now(tz)
    fechaHora   = ahora.strftime("%Y-%m-%d %H:%M:%S")

    con    = con_pool.get_connection()
    cursor = con.cursor()

    if id:
        sql = """
        UPDATE resenas_comidas
        SET nombre = %s,
            restaurante = %s,
            direccion = %s,
            resena = %s,
            calificacion = %s
        WHERE id = %s
        """
        val = (nombre, restaurante, direccion, resena, calificacion, id)
    else:
        sql = """
        INSERT INTO resenas_comidas (nombre, restaurante, direccion, resena, calificacion)
        VALUES                (%s, %s, %s, %s, %s)
        """
        val =                 (nombre, restaurante, direccion, resena, calificacion)
    
    cursor.execute(sql, val)
    con.commit()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    lastInsertId = id
    if not id:
        lastInsertId = cursor.lastrowid

    return make_response(jsonify({
        "id": lastInsertId,
        "fechaHora": fechaHora
    }))

@app.route("/resena/<int:id>")
@login
def editarResena(id):
    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    SELECT id, nombre, restaurante, direccion, resena, calificacion
    FROM resenas_comidas
    WHERE id = %s
    """
    val    = (id,)

    cursor.execute(sql, val)
    resenas = cursor.fetchall()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    return make_response(jsonify(resenas))

@app.route("/resena/eliminar", methods=["POST"])
def eliminarResena():
    id = request.form["id"]

    con    = con_pool.get_connection()
    cursor = con.cursor(dictionary=True)
    sql    = """
    DELETE FROM resenas_comidas
    WHERE id = %s
    """
    val    = (id,)

    cursor.execute(sql, val)
    con.commit()
    if cursor:
        cursor.close()
    if con and con.is_connected():
        con.close()

    return make_response(jsonify({}))

if __name__ == "__main__":
    app.run()
