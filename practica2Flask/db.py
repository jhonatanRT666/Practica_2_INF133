import mysql.connector
from mysql.connector import Error


# FUNCIÓN PARA CONECTAR A MYSQL
def conectar():
    try:
        conexion = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="bdacademico",
            port=3306
        )

        return conexion

    except Error as e:
        print("Error al conectar con MySQL:", e)
        return None


# ---------------------------------------------------------------
# FUNCIONES AUXILIARES (todas usan cursor y parámetros %s)
# ---------------------------------------------------------------
def _consultar(sql, params=(), uno=False):
    """Ejecuta un SELECT. Devuelve una fila (dict) o una lista de filas."""
    conexion = conectar()
    if conexion is None:
        raise Error("No se pudo conectar con la base de datos.")
    cursor = None
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchone() if uno else cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        conexion.close()


def _modificar(sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE: confirma, o revierte si hay error."""
    conexion = conectar()
    if conexion is None:
        raise Error("No se pudo conectar con la base de datos.")
    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, params)
        conexion.commit()
        return cursor.lastrowid
    except Error:
        conexion.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        conexion.close()


# ---------------------------------------------------------------
# CARRERAS
# ---------------------------------------------------------------
def obtener_carreras():
    """Lista las carreras con la cantidad de estudiantes de cada una."""
    return _consultar(
        """SELECT c.id, c.nombre, c.descripcion,
                  COUNT(e.id) AS total_estudiantes
           FROM carreras c
           LEFT JOIN estudiantes e ON e.carrera_id = c.id
           GROUP BY c.id, c.nombre, c.descripcion
           ORDER BY c.nombre"""
    )


def obtener_carrera(id):
    return _consultar(
        "SELECT id, nombre, descripcion FROM carreras WHERE id = %s",
        (id,), uno=True
    )


def nombre_carrera_existe(nombre, excluir_id=None):
    """True si ya hay otra carrera con ese nombre (excluir_id sirve al editar)."""
    if excluir_id is None:
        fila = _consultar("SELECT id FROM carreras WHERE nombre = %s", (nombre,), uno=True)
    else:
        fila = _consultar(
            "SELECT id FROM carreras WHERE nombre = %s AND id <> %s",
            (nombre, excluir_id), uno=True
        )
    return fila is not None


def insertar_carrera(nombre, descripcion):
    return _modificar(
        "INSERT INTO carreras (nombre, descripcion) VALUES (%s, %s)",
        (nombre, descripcion)
    )


def actualizar_carrera(id, nombre, descripcion):
    _modificar(
        "UPDATE carreras SET nombre = %s, descripcion = %s WHERE id = %s",
        (nombre, descripcion, id)
    )


def contar_estudiantes_de_carrera(id):
    fila = _consultar(
        "SELECT COUNT(*) AS total FROM estudiantes WHERE carrera_id = %s",
        (id,), uno=True
    )
    return fila["total"]


def borrar_carrera(id):
    _modificar("DELETE FROM carreras WHERE id = %s", (id,))


# ---------------------------------------------------------------
# ESTUDIANTES
# ---------------------------------------------------------------
def _escapar_like(texto):
    """Escapa \\, % y _ para que se busquen como texto literal en un LIKE."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtros_estudiantes(texto, carrera_id):
    """Arma el WHERE (solo con fragmentos fijos) y la lista de parámetros."""
    condiciones = []
    params = []

    if texto:
        patron = "%" + _escapar_like(texto) + "%"
        condiciones.append("(e.apellido LIKE %s OR e.correo LIKE %s)")
        params.extend([patron, patron])

    if carrera_id:
        condiciones.append("e.carrera_id = %s")
        params.append(carrera_id)

    where = " WHERE " + " AND ".join(condiciones) if condiciones else ""
    return where, params


def contar_estudiantes(texto="", carrera_id=None):
    where, params = _filtros_estudiantes(texto, carrera_id)
    fila = _consultar(
        "SELECT COUNT(*) AS total FROM estudiantes e" + where,
        tuple(params), uno=True
    )
    return fila["total"]


def obtener_estudiantes(texto="", carrera_id=None, limite=10, desplazamiento=0):
    """Estudiantes con el nombre de su carrera; búsqueda, filtro y paginación."""
    where, params = _filtros_estudiantes(texto, carrera_id)
    sql = (
        """SELECT e.id, e.nombre, e.apellido, e.correo, e.carrera_id,
                  c.nombre AS carrera
           FROM estudiantes e
           JOIN carreras c ON c.id = e.carrera_id"""
        + where +
        " ORDER BY e.apellido, e.nombre LIMIT %s OFFSET %s"
    )
    params.extend([limite, desplazamiento])
    return _consultar(sql, tuple(params))


def obtener_estudiantes_de_carrera(carrera_id):
    return _consultar(
        """SELECT id, nombre, apellido, correo
           FROM estudiantes
           WHERE carrera_id = %s
           ORDER BY apellido, nombre""",
        (carrera_id,)
    )


def obtener_estudiante(id):
    return _consultar(
        "SELECT id, nombre, apellido, correo, carrera_id FROM estudiantes WHERE id = %s",
        (id,), uno=True
    )


def correo_existe(correo, excluir_id=None):
    """True si ya hay otro estudiante con ese correo."""
    if excluir_id is None:
        fila = _consultar("SELECT id FROM estudiantes WHERE correo = %s", (correo,), uno=True)
    else:
        fila = _consultar(
            "SELECT id FROM estudiantes WHERE correo = %s AND id <> %s",
            (correo, excluir_id), uno=True
        )
    return fila is not None


def insertar_estudiante(nombre, apellido, correo, carrera_id):
    return _modificar(
        """INSERT INTO estudiantes (nombre, apellido, correo, carrera_id)
           VALUES (%s, %s, %s, %s)""",
        (nombre, apellido, correo, carrera_id)
    )


def actualizar_estudiante(id, nombre, apellido, correo, carrera_id):
    _modificar(
        """UPDATE estudiantes
           SET nombre = %s, apellido = %s, correo = %s, carrera_id = %s
           WHERE id = %s""",
        (nombre, apellido, correo, carrera_id, id)
    )


def borrar_estudiante(id):
    _modificar("DELETE FROM estudiantes WHERE id = %s", (id,))