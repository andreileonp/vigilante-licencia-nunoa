"""
Vigilante de horas - Primera Licencia de Conducir, Municipalidad de Ñuñoa.

Abre la agenda (Agenda-T de Ingelan), selecciona el trámite y revisa si el
calendario tiene algún día disponible.

Códigos de salida:
  0 -> sin cupos (o el sitio no respondió; se reintenta en la próxima ejecución)
  1 -> HAY CUPOS  (GitHub marca la ejecución como fallida y te envía un correo)
"""

import os
import sys
import json
import urllib.request
import urllib.parse

from playwright.sync_api import sync_playwright

URL = "https://nunoa.ingelan.cl/"
SUCURSAL = "3"   # Municipalidad de Ñuñoa
CENTRO = "3"     # Licencia de Conducir
SERVICIO = "1"   # Primera Licencia
MESES_A_REVISAR = 4


def buscar_dias_disponibles():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="es-CL")
        page.set_default_timeout(30000)

        page.goto(URL, wait_until="networkidle")

        # Selecciona sucursal -> centro -> servicio (cada uno carga el siguiente)
        page.select_option("#txt_sucursalC", SUCURSAL)
        page.wait_for_selector(f"#txt_centroAtencion option[value='{CENTRO}']", state="attached")
        page.select_option("#txt_centroAtencion", CENTRO)
        page.wait_for_selector(f"#txt_servicios option[value='{SERVICIO}']", state="attached")
        page.select_option("#txt_servicios", SERVICIO)

        # Avanza al calendario
        page.click("a:has-text('Siguiente')")
        page.wait_for_url("**/seleccionarCalendario.view.html")
        page.wait_for_selector("#txt_fecha.hasDatepicker", state="attached")
        page.wait_for_load_state("networkidle")

        # Recorre los meses del calendario buscando días seleccionables
        disponibles = page.evaluate(
            """(meses) => {
                const out = [];
                $('#txt_fecha').datepicker('show');
                for (let m = 0; m < meses; m++) {
                    const titulo = $('.ui-datepicker-title').text().trim();
                    $('.ui-datepicker-calendar td[data-handler="selectDay"]').each((i, td) => {
                        out.push(td.textContent.trim() + ' ' + titulo);
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
        return disponibles


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
        dias = buscar_dias_disponibles()
    except Exception as e:
        print(f"::warning::No se pudo revisar el sitio ({e}). Se reintenta en la próxima ejecución.")
        return 0

    if not dias:
        print("Sin cupos disponibles por ahora.")
        return 0

    lista = ", ".join(dias)
    mensaje = (
        "¡HAY HORAS DISPONIBLES para Primera Licencia en Ñuñoa!\n"
        f"Días: {lista}\n"
        f"Reserva aquí: {URL}"
    )
    print(f"::error title=Hay horas disponibles::{mensaje.replace(chr(10), ' | ')}")
    avisar_telegram(mensaje)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## ✅ Hay horas disponibles\n\n**Días:** {lista}\n\n[Reservar ahora]({URL})\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
