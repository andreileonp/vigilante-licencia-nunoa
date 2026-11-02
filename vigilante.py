"""
Vigilante de horas - Primera Licencia de Conducir, Municipalidad de Ñuñoa.

Abre la agenda (Agenda-T de Ingelan), selecciona el trámite y busca el día
disponible MÁS CERCANO en el calendario.

Solo avisa cuando aparece una fecha más cercana que la ya avisada, para no
repetir el mismo aviso cada 5 minutos. La última fecha avisada se guarda en
el archivo ultimo_aviso.txt del repositorio.

Códigos de salida:
  0 -> sin novedad (sin cupos, misma fecha ya avisada, o el sitio no respondió)
  1 -> NUEVA FECHA MÁS CERCANA (GitHub marca la ejecución en rojo y envía un correo)
"""

import os
import sys
import urllib.request
import urllib.parse
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "https://nunoa.ingelan.cl/"
SUCURSAL = "3"   # Municipalidad de Ñuñoa
CENTRO = "3"     # Licencia de Conducir
SERVICIO = "1"   # Primera Licencia
MESES_A_REVISAR = 4
ESTADO = Path(__file__).with_name("ultimo_aviso.txt")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def buscar_dias_disponibles():
    """Devuelve la lista de fechas (date) disponibles en el calendario."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="es-CL")
        page.set_default_timeout(30000)

        page.goto(URL, wait_until="networkidle")

        # Sucursal -> centro -> servicio (cada uno carga las opciones del siguiente)
        page.select_option("#txt_sucursalC", SUCURSAL)
        page.wait_for_selector(f"#txt_centroAtencion option[value='{CENTRO}']", state="attached")
        page.select_option("#txt_centroAtencion", CENTRO)
        page.wait_for_selector(f"#txt_servicios option[value='{SERVICIO}']", state="attached")
        page.select_option("#txt_servicios", SERVICIO)

        page.click("a:has-text('Siguiente')")
        page.wait_for_url("**/seleccionarCalendario.view.html")
        page.wait_for_selector("#txt_fecha.hasDatepicker", state="attached")
        page.wait_for_load_state("networkidle")

        crudos = page.evaluate(
            """(meses) => {
                const out = [];
                $('#txt_fecha').datepicker('show');
                for (let m = 0; m < meses; m++) {
                    const titulo = $('.ui-datepicker-title').text().trim();
                    $('.ui-datepicker-calendar td[data-handler="selectDay"]').each((i, td) => {
                        out.push([td.textContent.trim(), titulo]);
                    });
                    const next = $('.ui-datepicker-next');
                    if (next.hasClass('ui-state-disabled')) break;
                    next.click();
                }
                $('#txt_fecha').datepicker('hide');
                return out;
            }""",
            MESES_A_REVISAR,
        )
        browser.close()

    fechas = set()
    for dia, titulo in crudos:
        partes = titulo.lower().split()
        mes = MESES.get(partes[0]) if partes else None
        anio = int(partes[-1]) if partes and partes[-1].isdigit() else None
        if mes and anio and dia.isdigit():
            fechas.add(date(anio, mes, int(dia)))
    return sorted(fechas)


def leer_ultimo_aviso():
    try:
        return date.fromisoformat(ESTADO.read_text().strip())
    except Exception:
        return None


def guardar_ultimo_aviso(fecha):
    if fecha is None:
        if ESTADO.exists():
            ESTADO.unlink()
    else:
        ESTADO.write_text(fecha.isoformat() + "\n")


def avisar_telegram(texto):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": texto}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=20)
        print("Aviso enviado por Telegram.")
    except Exception as e:  # el correo de GitHub igual llega
        print(f"No se pudo enviar Telegram: {e}")


def main():
    try:
        fechas = buscar_dias_disponibles()
    except Exception as e:
        print(f"::warning::No se pudo revisar el sitio ({e}). Se reintenta en la próxima ejecución.")
        return 0

    anterior = leer_ultimo_aviso()

    if not fechas:
        print("Sin cupos disponibles por ahora.")
        guardar_ultimo_aviso(None)  # si vuelven a aparecer, se avisará de nuevo
        return 0

    mas_cercana = fechas[0]
    print(f"Fecha más cercana disponible: {mas_cercana.strftime('%d-%m-%Y')}")

    if anterior is not None and mas_cercana >= anterior:
        print(f"Ya se avisó una fecha igual o más cercana ({anterior.strftime('%d-%m-%Y')}). Sin aviso nuevo.")
        if mas_cercana != anterior:
            guardar_ultimo_aviso(mas_cercana)
        return 0

    guardar_ultimo_aviso(mas_cercana)
    texto_fecha = mas_cercana.strftime("%d-%m-%Y")
    mensaje = (
        "¡Hay hora para Primera Licencia en Ñuñoa!\n"
        f"Fecha más cercana: {texto_fecha}\n"
        f"Reserva aquí: {URL}"
    )
    print(f"::error title=Hora disponible {texto_fecha}::{mensaje.replace(chr(10), ' | ')}")
    avisar_telegram(mensaje)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## ✅ Hora disponible: {texto_fecha}\n\n[Reservar ahora]({URL})\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
