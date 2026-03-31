from datetime import datetime
from pathlib import Path
import csv

from flask import Flask, render_template, request, send_file
import requests

app = Flask(__name__)
HISTORIAL_CSV = Path("historial.csv")
URLS_TXT = Path("urls.txt")


def revisar_url(url: str, palabra_clave: str) -> dict:
    try:
        respuesta = requests.get(url, timeout=10)
    except Exception as e:
        return {
            "ok": False,
            "mensaje": f"No se pudo conectar a la pagina. Error: {e}",
            "status_code": None,
            "conteo": 0,
        }

    contenido = respuesta.text
    conteo = contenido.count(palabra_clave)

    if respuesta.status_code == 200:
        mensaje = f"La pagina esta ONLINE (codigo {respuesta.status_code})."
    else:
        mensaje = f"La pagina respondio con codigo {respuesta.status_code}."

    return {
        "ok": respuesta.status_code == 200,
        "mensaje": mensaje,
        "status_code": respuesta.status_code,
        "conteo": conteo,
    }


def asegurar_historial() -> None:
    if not HISTORIAL_CSV.exists():
        with HISTORIAL_CSV.open("w", newline="", encoding="utf-8") as archivo:
            writer = csv.writer(archivo)
            writer.writerow(["fecha_hora", "url", "palabra_clave", "status_code", "conteo"])


def guardar_en_historial(url: str, palabra_clave: str, resultado: dict) -> None:
    asegurar_historial()
    with HISTORIAL_CSV.open("a", newline="", encoding="utf-8") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url,
                palabra_clave,
                resultado.get("status_code"),
                resultado.get("conteo", 0),
            ]
        )


def leer_ultimos_registros(limite: int = 10) -> list[dict]:
    asegurar_historial()
    with HISTORIAL_CSV.open("r", newline="", encoding="utf-8") as archivo:
        reader = csv.DictReader(archivo)
        filas = list(reader)
    return list(reversed(filas[-limite:]))


def asegurar_urls_txt() -> None:
    if not URLS_TXT.exists():
        URLS_TXT.write_text("", encoding="utf-8")


def parsear_urls(texto: str) -> list[str]:
    urls = []
    for linea in texto.splitlines():
        url = linea.strip()
        if url:
            urls.append(url)
    # Quita repetidas manteniendo orden.
    return list(dict.fromkeys(urls))


@app.route("/", methods=["GET", "POST"])
def inicio():
    url = "https://www.google.com"
    palabra_clave = "Google"
    urls_texto = ""
    resultado_lote = []
    resumen_lote = None
    # Ejecutamos una prueba automáticamente al abrir la página.
    # Si luego envías el formulario, se vuelve a calcular con tus datos.
    resultado = revisar_url(url, palabra_clave)
    guardar_en_historial(url, palabra_clave, resultado)

    if request.method == "POST":
        accion = request.form.get("accion", "single")
        palabra_clave = request.form.get("palabra", "").strip() or palabra_clave

        if accion == "single":
            url = request.form.get("url", "").strip() or url
            resultado = revisar_url(url, palabra_clave)
            guardar_en_historial(url, palabra_clave, resultado)
        else:
            if accion == "txt":
                asegurar_urls_txt()
                urls_texto = URLS_TXT.read_text(encoding="utf-8")
            else:
                urls_texto = request.form.get("urls_lote", "").strip()

            urls_lote = parsear_urls(urls_texto)
            for item_url in urls_lote:
                r = revisar_url(item_url, palabra_clave)
                guardar_en_historial(item_url, palabra_clave, r)
                resultado_lote.append(
                    {
                        "url": item_url,
                        "status_code": r.get("status_code"),
                        "conteo": r.get("conteo", 0),
                        "mensaje": r.get("mensaje", ""),
                    }
                )

            ok_count = sum(1 for item in resultado_lote if item["status_code"] == 200)
            resumen_lote = {
                "total": len(resultado_lote),
                "ok": ok_count,
                "fallo": len(resultado_lote) - ok_count,
            }

    ultimos_registros = leer_ultimos_registros(10)

    return render_template(
        "index.html",
        url=url,
        palabra_clave=palabra_clave,
        resultado=resultado,
        ultimos_registros=ultimos_registros,
        urls_texto=urls_texto,
        resultado_lote=resultado_lote,
        resumen_lote=resumen_lote,
    )


@app.route("/descargar-historial")
def descargar_historial():
    asegurar_historial()
    return send_file(HISTORIAL_CSV, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
