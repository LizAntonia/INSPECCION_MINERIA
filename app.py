from flask import Flask, render_template, request, send_file, redirect
import sqlite3
import os

from werkzeug.utils import secure_filename

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)

DB = "inspecciones.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("pdfs", exist_ok=True)


# ==================================================
# BASE DE DATOS
# ==================================================
def init_db():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS inspecciones(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ot TEXT,
        fecha_inspeccion TEXT,
        inspector TEXT,
        area TEXT,
        recomendaciones TEXT,
        detalles TEXT,
        firma TEXT,
        pdf_path TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS equipos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspeccion_id INTEGER,

        tag TEXT,
        nombre TEXT,

        estructura TEXT,
        deformaciones TEXT,
        corrosion TEXT,
        desgaste TEXT,
        apernadura TEXT,
        soldadura TEXT,
        fugas TEXT,
        filtraciones TEXT,
        acumulacion TEXT,
        reparaciones TEXT,
        operatividad TEXT,

        hallazgo TEXT,
        equipo_relacionado TEXT,
        ubicacion TEXT,

        foto TEXT
    )
    """)

    conn.commit()
    conn.close()


# ==================================================
# HOME
# ==================================================
@app.route("/")
def index():
    return render_template("formulario.html")


# ==================================================
# HISTORIAL
# ==================================================
@app.route("/historial")
def historial():

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT
        id,
        ot,
        inspector,
        area
        FROM inspecciones
        ORDER BY id DESC
    """)

    inspecciones = c.fetchall()

    conn.close()

    return render_template(
        "historial.html",
        inspecciones=inspecciones
    )
    # ==================================================
# GUARDAR INSPECCIÓN
# ==================================================
@app.route("/guardar", methods=["POST"])
def guardar():

    ot = request.form.get("ot")
    fecha_inspeccion = request.form.get("fecha_inspeccion")
    inspector = request.form.get("inspector")
    area = request.form.get("area")

    recomendaciones = ", ".join(
        request.form.getlist("recomendaciones")
    )

    detalles = request.form.get("detalles")
    firma = request.form.get("firma")

    tags = request.form.getlist("tag[]")
    nombres = request.form.getlist("nombre[]")

    estructuras = request.form.getlist("estructura[]")
    deformaciones = request.form.getlist("deformaciones[]")
    corrosiones = request.form.getlist("corrosion[]")
    desgastes = request.form.getlist("desgaste[]")
    apernaduras = request.form.getlist("apernadura[]")
    soldaduras = request.form.getlist("soldadura[]")
    fugas = request.form.getlist("fugas[]")
    filtraciones = request.form.getlist("filtraciones[]")
    acumulaciones = request.form.getlist("acumulacion[]")
    reparaciones = request.form.getlist("reparaciones[]")
    operatividades = request.form.getlist("operatividad[]")

    hallazgos = request.form.getlist("hallazgo[]")
    relacionados = request.form.getlist("equipo_relacionado[]")
    ubicaciones = request.form.getlist("ubicacion[]")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        INSERT INTO inspecciones(
            ot,
            fecha_inspeccion,
            inspector,
            area,
            recomendaciones,
            detalles,
            firma,
            pdf_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, '')
    """, (
        ot,
        fecha_inspeccion,
        inspector,
        area,
        recomendaciones,
        detalles,
        firma
    ))

    inspeccion_id = c.lastrowid

    for i in range(len(tags)):

        ruta_foto = ""

        fotos = request.files.getlist(f"foto_{i}")

        rutas_fotos = []

        for num, foto in enumerate(fotos):

            if foto and foto.filename:

                nombre_archivo = secure_filename(
                    f"{inspeccion_id}_{i}_{num}_{foto.filename}"
                )

                ruta_archivo = os.path.join(
                    UPLOAD_FOLDER,
                    nombre_archivo
                )

                foto.save(ruta_archivo)

                rutas_fotos.append(ruta_archivo)

        ruta_foto = "|".join(rutas_fotos)

        c.execute("""
            INSERT INTO equipos(
                inspeccion_id,
                tag,
                nombre,
                estructura,
                deformaciones,
                corrosion,
                desgaste,
                apernadura,
                soldadura,
                fugas,
                filtraciones,
                acumulacion,
                reparaciones,
                operatividad,
                hallazgo,
                equipo_relacionado,
                ubicacion,
                foto
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inspeccion_id,
            tags[i],
            nombres[i],
            estructuras[i],
            deformaciones[i],
            corrosiones[i],
            desgastes[i],
            apernaduras[i],
            soldaduras[i],
            fugas[i],
            filtraciones[i],
            acumulaciones[i],
            reparaciones[i],
            operatividades[i],
            hallazgos[i],
            relacionados[i],
            ubicaciones[i],
            ruta_foto
        ))

    conn.commit()
    conn.close()

    return redirect(f"/pdf/{inspeccion_id}")
    # ==================================================
# GENERAR PDF
# ==================================================
@app.route("/pdf/<int:id>")
def pdf(id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        SELECT
        ot,
        fecha_inspeccion,
        inspector,
        area,
        recomendaciones,
        detalles,
        firma
        FROM inspecciones
        WHERE id=?
    """, (id,))

    inspeccion = c.fetchone()

    if not inspeccion:
        conn.close()
        return "Inspección no encontrada"

    c.execute("""
        SELECT
        tag,
        nombre,
        estructura,
        deformaciones,
        corrosion,
        desgaste,
        apernadura,
        soldadura,
        fugas,
        filtraciones,
        acumulacion,
        reparaciones,
        operatividad,
        hallazgo,
        equipo_relacionado,
        ubicacion,
        foto
        FROM equipos
        WHERE inspeccion_id=?
    """, (id,))

    equipos = c.fetchall()

    conn.close()

    pdf_path = f"pdfs/informe_{id}.pdf"

    pdf = canvas.Canvas(pdf_path, pagesize=letter)

    ancho, alto = letter
    y = alto - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "INFORME DE INSPECCIÓN MINERA")
    y -= 30

    pdf.setFont("Helvetica", 11)

    pdf.drawString(50, y, f"OT: {inspeccion[0]}")
    y -= 18

    pdf.drawString(50, y, f"Fecha de inspección: {inspeccion[1]}")
    y -= 18

    pdf.drawString(50, y, f"Inspector: {inspeccion[2]}")
    y -= 18

    pdf.drawString(50, y, f"Área: {inspeccion[3]}")
    y -= 30

    for equipo in equipos:

        if y < 250:
            pdf.showPage()
            y = alto - 50

        (
            tag,
            nombre,
            estructura,
            deformaciones,
            corrosion,
            desgaste,
            apernadura,
            soldadura,
            fugas,
            filtraciones,
            acumulacion,
            reparaciones,
            operatividad,
            hallazgo,
            relacionado,
            ubicacion,
            foto
        ) = equipo

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(50, y, f"TAG: {tag}")
        y -= 18

        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Equipo: {nombre}")
        y -= 15

        pdf.drawString(50, y, f"Estructura: {estructura}")
        y -= 15

        pdf.drawString(50, y, f"Deformaciones: {deformaciones}")
        y -= 15

        pdf.drawString(50, y, f"Corrosión activa: {corrosion}")
        y -= 15

        pdf.drawString(50, y, f"Desgaste significativo: {desgaste}")
        y -= 15

        pdf.drawString(50, y, f"Apernadura: {apernadura}")
        y -= 15

        pdf.drawString(50, y, f"Soldadura: {soldadura}")
        y -= 15

        pdf.drawString(50, y, f"Fugas de material: {fugas}")
        y -= 15

        pdf.drawString(50, y, f"Filtraciones: {filtraciones}")
        y -= 15

        pdf.drawString(50, y, f"Acumulación de material: {acumulacion}")
        y -= 15

        pdf.drawString(50, y, f"Reparaciones anteriores visibles: {reparaciones}")
        y -= 15

        pdf.drawString(50, y, f"Operatividad: {operatividad}")
        y -= 20

        pdf.drawString(50, y, f"Hallazgo: {hallazgo}")
        y -= 15

        pdf.drawString(50, y, f"Equipo relacionado: {relacionado}")
        y -= 15

        pdf.drawString(50, y, f"Ubicación: {ubicacion}")
        y -= 20

    if foto:

        try:

            lista_fotos = foto.split("|")
            print("Fotos encontradas:", len(lista_fotos))

            x = 50
            contador_fotos = 0

            for ruta in lista_fotos:

                if os.path.exists(ruta):

                    imagen = ImageReader(ruta)

                    pdf.drawImage(
                        imagen,
                        x,
                        y - 120,
                        width=120,
                        height=90,
                        preserveAspectRatio=True
                    )

                    contador_fotos += 1

                    if contador_fotos % 2 == 0:
                        x = 50
                        y -= 100
                    else:
                        x = 200

            if contador_fotos % 2 != 0:
                y -= 100

        except Exception as e:
            print(e)

        y -= 20

    if y < 180:
        pdf.showPage()
        y = alto - 50

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "RECOMENDACIONES")
    y -= 20

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, y, inspeccion[4] or "")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "DETALLES Y COMENTARIOS")
    y -= 20

    texto = pdf.beginText()
    texto.setTextOrigin(50, y)
    texto.setLeading(15)

    for linea in (inspeccion[5] or "").split("\n"):
        texto.textLine(linea)

    pdf.drawText(texto)

    y = texto.getY() - 20

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, f"Firma Inspector: {inspeccion[6]}")

    pdf.save()

    return send_file(
        pdf_path,
        as_attachment=True
    )


# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )