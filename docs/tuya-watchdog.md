# Watchdog Tuya Local: Luz Habitación (bombilla Antela)

Runbook de la bombilla Antela del dormitorio cuando pasa a `unavailable` aunque tenga corriente.
Código: [home-assistant/packages/tuya_watchdog.yaml](../home-assistant/packages/tuya_watchdog.yaml).

## Estado real (2026-10-29)

| Dato | Valor |
|------|-------|
| Entidad | `light.luz_habitacion` (no existe `light.tuya_bombilla`) |
| Integración | `tuya_local` (HACS, make-all/tuya-local 2026.7.2): **local**, protocolo 3.3, `rgbcw_lightbulb` |
| Host en la config entry | `192.168.1.118:6668/tcp` |
| Device ID | `bf834ca221fca20947wvem` |
| Tuya oficial (nube) | Sigue cargada; `light.dormitorio_luz_habitacion` deshabilitada (no duplica) |

Síntoma en el log: `tuya_local … Luz Habitación … error 901: Network Error: Unable to Connect`, cada ~10 min.
`tuya_local` **ya reintenta solo**: el 901 indica que el socket TCP no llega a la bombilla. Es un fallo de red, no de la integración.

Comprobado el 2026-10-29 tras el reinicio completo del router: sin ping ni ARP en `.118`, sin 6668/tcp en ningún host de `192.168.1.0/24` (nmap) y sin anuncios UDP Tuya en 6666/6667. **La bombilla no está en la LAN**, ni en `.118` ni en otra IP. Satellite1 y la lámpara Xiaomi sí volvieron.

## Capa física / red (lo primero)

Ningún watchdog de software reconecta un dispositivo que no está asociado al Wi-Fi. Por orden:

1. **Ciclo de corriente** desde el interruptor de pared (apagado 10 s). Si el radio 2,4 GHz del router se colgó y luego se reinició, muchos módulos Tuya (BK7231/ESP) no vuelven a asociarse solos hasta un *power-cycle*.
2. **Reserva DHCP por MAC** para la IP que usa HA (`192.168.1.118`). La doc de reservas aún tiene MACs de ejemplo, así que la bombilla **no tiene reserva**. Tras un reinicio del router puede coger otra IP, y `tuya_local` seguiría apuntando a `.118` con error 901 para siempre. Pasos: [reservas-dhcp-bombillas-iot.md](reservas-dhcp-bombillas-iot.md) (MAC en el router o en Smart Life → Información del dispositivo). Si prefieres `.122`, cambia a la vez la reserva, la IP de la config entry (Tuya Local → Configurar) y la sonda del package.
3. **Wi-Fi 2,4 GHz**: si caen a la vez Satellite1, la lámpara y la bombilla, es el router: `bash infrastructure/nodes/core/verify_iot_wifi.sh` (ver AGENTS.md, «Wi-Fi 2,4 GHz»). Usa canal fijo 1/6/11 a 20 MHz, WPA2 y sin band-steering ni «Smart WiFi».
4. **Una sola conexión local**: la v3.3 admite muy pocas sesiones TCP. Si Smart Life está abierta en el móvil en modo LAN, puede ocupar el socket. En ese caso la bombilla responde al ping pero HA no conecta.
5. **Apagado por software**: según el diagnóstico de [lights.yaml](../home-assistant/includes/lights.yaml), esta bombilla dejaba de anunciarse al apagarla desde la app. Si el historial muestra `caida` con detalle `off → unavailable`, el firmware duerme el Wi-Fi al apagar. Mitigaciones: brillo mínimo en vez de `off`, o reflashear con OpenBeken.

### Micro-cortes Wi-Fi

- Corte de menos de 2 min: `tuya_local` reconecta solo y el watchdog **no actúa**. Aun así se registra `caida` → `reconectada` («sola (tuya_local)»), de modo que se puede medir con qué frecuencia ocurre.
- Muchas reconexiones cortas en `counter.tuya_luz_habitacion_reconexiones` indican RSSI bajo o interferencias, no un problema de HA. Acerca el AP o cambia el canal de 2,4 GHz.

## Watchdog (capa HA)

```
light.luz_habitacion → unavailable/unknown
  ├─ < 2 min: gracia (tuya_local reintenta; micro-cortes)
  └─ ≥ 2 min y now ≥ input_datetime.tuya_watchdog_proximo_intento:
       intento += 1; próximo = now + min(2·2^(n-1), 60) min
       sonda bash /dev/tcp 192.168.1.118:6668 desde el contenedor de HA
         up    → reload_config_entry (si < 3 recargas en la última hora; si no, limite_hora)
         down  → inalcanzable (no recarga: no serviría)
         error → recarga a ciegas (sonda rota; mismo tope)
       intento 4 (~16 min) → notificación persistente con pasos manuales
light.luz_habitacion vuelve → reconexiones += 1; reset de intentos/backoff; retira la notificación
```

| Pieza | Entidad |
|-------|---------|
| Interruptor de pausa | `input_boolean.tuya_watchdog_pausado` (on = no actúa; sigue registrando) |
| Próximo intento (backoff) | `input_datetime.tuya_watchdog_proximo_intento` (sobrevive a reinicios) |
| Intentos en la caída actual | `counter.tuya_watchdog_intentos` |
| Reconexiones acumuladas | `counter.tuya_luz_habitacion_reconexiones` |
| Último evento + historial (30) | `sensor.tuya_watchdog_luz_habitacion`, atributo `historial` |
| Sonda | `shell_command.tuya_watchdog_probe_luz_habitacion` (stdout `up`/`down`/`error`) |
| Automatizaciones | `tuya_watchdog_luz_habitacion_estado`, `tuya_watchdog_luz_habitacion_recuperar` |

Estados del sensor: `caida`, `reconectada`, `recarga`, `inalcanzable`, `limite_hora`.

Ajustes (variables de la automatización `…_recuperar`): `backoff_base_min` (2), `backoff_max_min` (60), `max_recargas_hora` (3) y `notificar_en_intento` (4). La gracia es el `for: "00:02:00"` de la condición.

Coste en una caída larga: una conexión TCP y una línea de log por hora. El tick de 1 min solo evalúa condiciones.

Por qué `reload_config_entry` y no otra acción: es la única que rehace el socket de `tuya_local` sin reiniciar HA. Se apunta por entidad (`target.entity_id`), así que no depende del `entry_id`.

## Operación

```bash
# Desplegar (copia configuration.yaml + includes + packages, ha core check, restart)
bash infrastructure/voice/wake-word/deploy_ha_voice_config.sh

# Log del watchdog y de tuya_local
ssh homeassistant 'ha core logs | grep -E "tuya_watchdog|tuya_local"'

# ¿Está la bombilla en la LAN? (desde el Mac)
bash infrastructure/nodes/core/verify_iot_wifi.sh
```

En la UI:

- Historial: Herramientas de desarrollo → Estados → `sensor.tuya_watchdog_luz_habitacion` → `historial`.
- Probar la sonda: Herramientas de desarrollo → Acciones → `shell_command.tuya_watchdog_probe_luz_habitacion` con «Devolver respuesta».

Rollback: borra `/config/packages/tuya_watchdog.yaml` y reinicia Core. Los helpers YAML desaparecen solos. `configuration.yaml` puede mantener `packages:` aunque la carpeta esté vacía.
