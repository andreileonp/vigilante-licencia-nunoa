"""
Vigilante de horas - Primera Licencia de Conducir, Municipalidad de Ñuñoa.

Abre la agenda (Agenda-T de Ingelan), selecciona el trámite y busca el día
disponible MÁS CERCANO en el calendario.

En cada revisión, si hay al menos un día disponible, envía por Telegram la
lista completa de días disponibles.

Códigos de salida:
  0 -> sin cupos, aviso enviado por Telegram, o el sitio no respondió
  1 -> hay cupos pero Telegram falló (GitHub envía un correo de respaldo)
"""

import os
import sys
import urllib.request
import urllib.parse
from datetime import date

from playwright.sync_api import sync_playwright

URL = "https://nunoa.ingelan.cl/"
SUCURSAL = "3"   # Municipalidad de Ñuñoa
CENTRO = "3"     # Licencia de Conducir
SERVICIO = "1"   # Primera Licencia
MESES_A_REVISAR = 4

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
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)

        mensajes = []
        page.on("dialog", lambda d: (mensajes.append(d.message), d.accept()))

        try:
            with page.expect_navigation(url="**/seleccionarCalendario.view.html", timeout=45000):
                page.evaluate("generarA()")
            page.wait_for_selector("#txt_fecha.hasDatepicker", state="attached", timeout=45000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
        except Exception:
            page.screenshot(path="error.png", full_page=True)
            raise RuntimeError(f"No se llegó al calendario. URL={page.url} dialogos={mensajes}")

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


def avisar_telegram(texto):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram no configurado.")
        return False
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": texto}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data, timeout=20)
        print("Aviso enviado por Telegram.")
        return True
    except Exception as e:
        print(f"No se pudo enviar Telegram: {e}")
        return False


def main():
    if os.environ.get("PRUEBA") == "true":
        mensaje = (
            "🔔 PRUEBA del vigilante de Primera Licencia Ñuñoa.\n"
            "Si recibes esto, los avisos funcionan. (No es una hora real.)"
        )
        print(f"::error title=PRUEBA de aviso::{mensaje.replace(chr(10), ' | ')}")
        avisar_telegram(mensaje)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as f:
                f.write("## 🔔 Aviso de PRUEBA\n\nSi te llegó el correo, las alertas funcionan.\n")
        return 1

    try:
        fechas = buscar_dias_disponibles()
    except Exception as e:
        print(f"::warning::No se pudo revisar el sitio ({e}). Se reintenta en la próxima ejecución.")
        return 0

    if not fechas:
        print("Sin cupos disponibles por ahora.")
        return 0

    dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    lineas = [f"• {dias_semana[f.weekday()]} {f.strftime('%d-%m-%Y')}" for f in fechas]
    mensaje = (
        f"¡Hay {len(fechas)} día(s) con horas para Primera Licencia en Ñuñoa!\n"
        + "\n".join(lineas)
        + f"\n\nReserva aquí: {URL}"
    )
    print(mensaje)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## ✅ Días disponibles\n\n" + "\n".join(lineas) + f"\n\n[Reservar ahora]({URL})\n")

    if avisar_telegram(mensaje):
        return 0
    # Si Telegram falla, la ejecución queda en rojo y GitHub envía un correo de respaldo
    print("::error title=Hay horas disponibles::Telegram falló; revisa la agenda.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
