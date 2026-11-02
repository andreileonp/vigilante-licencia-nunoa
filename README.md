# Vigilante de horas — Primera Licencia (Ñuñoa)

Revisa cada ~10 minutos la agenda de la Municipalidad de Ñuñoa
(<https://nunoa.ingelan.cl/>) y avisa cuando aparece un día disponible para
**Primera Licencia de Conducir**.

## Cómo avisa

- **Correo (automático):** cuando hay cupos, la ejecución termina en "fallida" a
  propósito, y GitHub te envía un correo con el aviso. Revisa que en
  *GitHub → Settings → Notifications → Actions* esté activado
  "Send notifications for failed workflows only" con correo.
- **Telegram (opcional, instantáneo):** agrega los secretos `TELEGRAM_TOKEN` y
  `TELEGRAM_CHAT_ID` en *Settings → Secrets and variables → Actions*.

## Uso

- Ejecutar a mano: pestaña **Actions → Vigilante Primera Licencia Ñuñoa → Run workflow**.
- Pausar: **Actions → (workflow) → ··· → Disable workflow**.
- Una ejecución en verde = sin cupos. En rojo = **hay horas, entra a reservar**.

> GitHub desactiva las tareas programadas de repositorios sin actividad por 60 días.
