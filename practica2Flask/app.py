import re
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from mysql.connector import Error

import db

app = Flask(__name__)
app.secret_key = "clave-secreta-practica-inf133"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
POR_PAGINA = 10


# ---------------------------------------------------------------
# VALIDACIONES
# ---------------------------------------------------------------
def validar_carrera(datos, id=None):
    errores = []
    nombre = datos["nombre"]

    if not nombre:
        errores.append("El nombre de la carrera es obligatorio.")
    elif len(nombre) > 100:
        errores.append("El nombre no puede superar los 100 caracteres.")
    elif db.nombre_carrera_existe(nombre, id):
        errores.append("Ya existe una carrera con ese nombre.")

    if len(datos["descripcion"]) > 255:
        errores.append("La descripción no puede superar los 255 caracteres.")

    return errores


def validar_estudiante(datos, id=None):
    errores = []

    if not datos["nombre"]:
        errores.append("El nombre es obligatorio.")
    elif len(datos["nombre"]) > 80:
        errores.append("El nombre no puede superar los 80 caracteres.")

    if not datos["apellido"]:
        errores.append("El apellido es obligatorio.")
    elif len(datos["apellido"]) > 80:
        errores.append("El apellido no puede superar los 80 caracteres.")

    correo = datos["correo"]
    if not correo:
        errores.append("El correo es obligatorio.")
    elif len(correo) > 120:
        errores.append("El correo no puede superar los 120 caracteres.")
    elif not EMAIL_RE.match(correo):
        errores.append("El correo no tiene un formato válido.")
    elif db.correo_existe(correo, id):
        errores.append("Ya existe un estudiante con ese correo.")

    if not datos["carrera_id"]:
        errores.append("Debe elegir una carrera.")
    else:
        try:
            carrera_id = int(datos["carrera_id"])
        except ValueError:
            errores.append("La carrera elegida no es válida.")
        else:
            if db.obtener_carrera(carrera_id) is None:
                errores.append("La carrera elegida no existe.")

    return errores


def leer_form_carrera():
    return {
        "nombre": request.form.get("nombre", "").strip(),
        "descripcion": request.form.get("descripcion", "").strip(),
    }


def leer_form_estudiante():
    return {
        "nombre": request.form.get("nombre", "").strip(),
        "apellido": request.form.get("apellido", "").strip(),
        "correo": request.form.get("correo", "").strip(),
        "carrera_id": request.form.get("carrera_id", "").strip(),
    }


# ---------------------------------------------------------------
# RAÍZ
# ---------------------------------------------------------------
@app.route("/")
def inicio():
    return redirect(url_for("listar_carreras"))


# ---------------------------------------------------------------
# CARRERAS
# ---------------------------------------------------------------
@app.route("/carreras")
def listar_carreras():
    try:
        carreras = db.obtener_carreras()
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")
        carreras = []
    return render_template("carreras/lista.html", carreras=carreras)


@app.route("/carreras/<int:id>")
def detalle_carrera(id):
    try:
        carrera = db.obtener_carrera(id)
        if carrera is None:
            abort(404)
        estudiantes = db.obtener_estudiantes_de_carrera(id)
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")
        return redirect(url_for("listar_carreras"))
    return render_template("carreras/detalle.html", carrera=carrera, estudiantes=estudiantes)


@app.route("/carreras/nueva", methods=["GET", "POST"])
def crear_carrera():
    carrera = {"nombre": "", "descripcion": ""}

    if request.method == "POST":
        carrera = leer_form_carrera()
        try:
            errores = validar_carrera(carrera)
            if not errores:
                db.insertar_carrera(carrera["nombre"], carrera["descripcion"])
                flash("Carrera creada correctamente.", "success")
                return redirect(url_for("listar_carreras"))
            for error in errores:
                flash(error, "danger")
        except Error as e:
            flash(f"Error de base de datos: {e}", "danger")

    return render_template("carreras/form.html", carrera=carrera, titulo="Nueva carrera")


@app.route("/carreras/<int:id>/editar", methods=["GET", "POST"])
def editar_carrera(id):
    try:
        existente = db.obtener_carrera(id)
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")
        return redirect(url_for("listar_carreras"))

    if existente is None:
        abort(404)

    carrera = existente

    if request.method == "POST":
        carrera = leer_form_carrera()
        carrera["id"] = id
        try:
            errores = validar_carrera(carrera, id)
            if not errores:
                db.actualizar_carrera(id, carrera["nombre"], carrera["descripcion"])
                flash("Carrera actualizada correctamente.", "success")
                return redirect(url_for("listar_carreras"))
            for error in errores:
                flash(error, "danger")
        except Error as e:
            flash(f"Error de base de datos: {e}", "danger")

    return render_template("carreras/form.html", carrera=carrera, titulo="Editar carrera")


@app.route("/carreras/<int:id>/eliminar", methods=["POST"])
def eliminar_carrera(id):
    try:
        if db.obtener_carrera(id) is None:
            abort(404)

        if db.contar_estudiantes_de_carrera(id) > 0:
            flash("No se puede eliminar la carrera porque tiene estudiantes.", "warning")
        else:
            db.borrar_carrera(id)
            flash("Carrera eliminada correctamente.", "success")
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")

    return redirect(url_for("listar_carreras"))


# ---------------------------------------------------------------
# ESTUDIANTES
# ---------------------------------------------------------------
@app.route("/estudiantes")
def listar_estudiantes():
    texto = request.args.get("q", "").strip()

    # El filtro de carrera y la página llegan como texto: se convierten con cuidado
    try:
        carrera_id = int(request.args.get("carrera", ""))
    except ValueError:
        carrera_id = None

    try:
        pagina = int(request.args.get("pagina", "1"))
    except ValueError:
        pagina = 1

    estudiantes, carreras = [], []
    total, total_paginas = 0, 1

    try:
        carreras = db.obtener_carreras()
        total = db.contar_estudiantes(texto, carrera_id)
        total_paginas = max(1, -(-total // POR_PAGINA))  # división hacia arriba
        pagina = min(max(pagina, 1), total_paginas)
        estudiantes = db.obtener_estudiantes(
            texto, carrera_id, POR_PAGINA, (pagina - 1) * POR_PAGINA
        )
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")

    return render_template(
        "estudiantes/lista.html",
        estudiantes=estudiantes, carreras=carreras,
        q=texto, carrera_id=carrera_id,
        pagina=pagina, total_paginas=total_paginas, total=total
    )


@app.route("/estudiantes/nuevo", methods=["GET", "POST"])
def crear_estudiante():
    estudiante = {"nombre": "", "apellido": "", "correo": "", "carrera_id": ""}

    try:
        carreras = db.obtener_carreras()

        if request.method == "POST":
            estudiante = leer_form_estudiante()
            errores = validar_estudiante(estudiante)
            if not errores:
                db.insertar_estudiante(
                    estudiante["nombre"], estudiante["apellido"],
                    estudiante["correo"], int(estudiante["carrera_id"])
                )
                flash("Estudiante creado correctamente.", "success")
                return redirect(url_for("listar_estudiantes"))
            for error in errores:
                flash(error, "danger")
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")
        carreras = []

    return render_template("estudiantes/form.html", estudiante=estudiante,
                           carreras=carreras, titulo="Nuevo estudiante")


@app.route("/estudiantes/<int:id>/editar", methods=["GET", "POST"])
def editar_estudiante(id):
    try:
        existente = db.obtener_estudiante(id)
        if existente is None:
            abort(404)

        carreras = db.obtener_carreras()
        estudiante = existente

        if request.method == "POST":
            estudiante = leer_form_estudiante()
            estudiante["id"] = id
            errores = validar_estudiante(estudiante, id)
            if not errores:
                db.actualizar_estudiante(
                    id, estudiante["nombre"], estudiante["apellido"],
                    estudiante["correo"], int(estudiante["carrera_id"])
                )
                flash("Estudiante actualizado correctamente.", "success")
                return redirect(url_for("listar_estudiantes"))
            for error in errores:
                flash(error, "danger")
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")
        return redirect(url_for("listar_estudiantes"))

    return render_template("estudiantes/form.html", estudiante=estudiante,
                           carreras=carreras, titulo="Editar estudiante")


@app.route("/estudiantes/<int:id>/eliminar", methods=["POST"])
def eliminar_estudiante(id):
    try:
        if db.obtener_estudiante(id) is None:
            abort(404)
        db.borrar_estudiante(id)
        flash("Estudiante eliminado correctamente.", "success")
    except Error as e:
        flash(f"Error de base de datos: {e}", "danger")

    return redirect(url_for("listar_estudiantes"))


@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)