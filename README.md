# Vigilante de horas — Primera Licencia (Ñuñoa)

Revisa cada ~5 minutos la agenda de la Municipalidad de Ñuñoa
(<https://nunoa.ingelan.cl/>) y, si hay al menos un día con horas para **Primera Licencia de Conducir**,
envía por Telegram la lista completa de días disponibles (en cada revisión).

## Cómo avisa

- **Telegram:** aviso principal, en cada revisión con cupos.
- **Correo (respaldo):** si Telegram falla, la ejecución termina en "fallida" a
  propósito y GitHub te envía un correo. Revisa que en
  *GitHub → Settings → Notifications → Actions* esté activado
  "Send notifications for failed workflows only" con correo.
- **Configuración de Telegram:** secretos los secretos `TELEGRAM_TOKEN` y
  `TELEGRAM_CHAT_ID` en *Settings → Secrets and variables → Actions*.

## Uso

- Ejecutar a mano: pestaña **Actions → Vigilante Primera Licencia Ñuñoa → Run workflow**.
- Pausar: **Actions → (workflow) → ··· → Disable workflow**.
- Una ejecución en verde = sin cupos. En rojo = **hay horas, entra a reservar**.

> GitHub desactiva las tareas programadas de repositorios sin actividad por 60 días.
