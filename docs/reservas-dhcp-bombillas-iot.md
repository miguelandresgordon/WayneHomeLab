# Reservas DHCP para bombillas IoT (Xiaomi + Antela)

Guía para fijar la IP de cada bombilla por dirección MAC en el router doméstico. Aplica a dispositivos gestionados con **Xiaomi Home**, **Smart Life** (Antela/Tuya) y vinculados a **Alexa**.

## Objetivo

| Problema | Solución |
|----------|----------|
| El router asigna IP distinta tras reinicio | Reserva DHCP por MAC |
| Home Assistant pierde bombilla WiFi | IP estable + token/clave local |
| Alexa deja de responder | **No** suele verse afectada (usa nube) |

Las reservas DHCP **no rompen** la conexión con Alexa ni con las apps móviles. Solo fijan qué IP local recibe cada bombilla.

---

## Plan de direcciones (ejemplo)

Adapta a tu red. Suponiendo LAN `192.168.1.0/24` y router en `192.168.1.1`:

| Dispositivo | MAC (rellenar) | IP reservada | App |
|-------------|----------------|--------------|-----|
| Pi-hole VM (VMID 101) | `bc:24:11:69:81:fe` | `192.168.1.53` | DNS LAN; ver [pihole.md](pihole.md) |
| WireGuard VM (VMID 102) | `bc:24:11:e9:6c:c9` | `192.168.1.55` | VPN + Caddy; ver [wireguard.md](wireguard.md) |
| Host Proxmox (Pi 5) | *(ya fijada)* | `192.168.1.100` | — |
| Home Assistant VM | *(reserva existente)* | `192.168.1.110` | — |
| Bombilla Xiaomi | `AA:BB:CC:DD:EE:01` | `192.168.1.121` | Xiaomi Home |
| Bombilla Antela | `AA:BB:CC:DD:EE:02` | `192.168.1.122` | Smart Life |

**Consejo:** Usa IPs **fuera del rango dinámico** del router. Si el DHCP reparte `.50–`.199`, reserva en `.121–`.130` o por encima de `.200`.

---

## Paso 1 — Obtener la MAC de cada bombilla

Necesitas la MAC **WiFi** de la bombilla (no la del móvil ni la de Alexa).

### Método A — Lista de clientes del router (recomendado)

1. Abre el panel del router: `http://192.168.1.1` (o la IP de tu gateway).
2. Inicia sesión (admin / contraseña del router).
3. Busca una sección como:
   - *Dispositivos conectados*
   - *DHCP Client List*
   - *LAN → Clientes*
4. **Enciende solo una bombilla** (apaga la otra desde la app o el interruptor de pared) para identificarla.
5. Anota **nombre**, **IP actual** y **MAC** (formato `XX:XX:XX:XX:XX:XX`).
6. Repite con la segunda bombilla.

### Método B — App Xiaomi Home

1. Bombilla → **⋮** → **Ajustes** / **Información del dispositivo**.
2. Algunos modelos muestran **IP**; la MAC a veces **no** aparece → usa el router (método A).
3. Si hay **Dirección MAC** o **WiFi MAC**, cópiala.

### Método C — App Smart Life (Antela)

1. Bombilla → icono **lápiz** / **Ajustes del dispositivo**.
2. Busca **Información del dispositivo** → IP o MAC (depende del firmware).
3. Si solo hay IP → confirma la MAC en el router filtrando por esa IP.

### Método D — App Fing (móvil)

1. Instala **Fing** en el iPhone/Android (misma WiFi).
2. Escanea la red; identifica bombillas por fabricante (*Xiaomi*, *Tuya*, *Espressif*).
3. Anota IP y MAC.

### Método E — Alexa (referencia, no siempre muestra MAC)

**Alexa → Dispositivos → Bombilla → Ajustes (⚙) → Información del dispositivo**

A veces indica IP o nombre de red; la MAC **no** siempre está. Usa el router como fuente definitiva.

---

## Paso 2 — Crear la reserva DHCP en el router

Los menús varían por marca. El flujo genérico es el mismo:

1. **LAN** / **Red local** / **DHCP**.
2. **Reserva DHCP** / **Asignación estática** / **Address reservation**.
3. **Añadir**:
   - **MAC:** la de la bombilla.
   - **IP:** la elegida (ej. `.121`).
   - **Nombre:** `bombilla-xiaomi`, `bombilla-antela` (opcional).
4. **Guardar** y **aplicar**.
5. Repite para la segunda bombilla.

### Referencia por tipo de router

| Router / firmware | Ruta habitual |
|-------------------|---------------|
| **Movistar HGU** | `192.168.1.1` → Red local → DHCP → Reserva de direcciones |
| **Orange Livebox** | WiFi / Red local → DHCP → Asignación estática |
| **Vodafone** | Red doméstica → DHCP → Reservas |
| **ASUS (ASUSWRT)** | LAN → DHCP Server → Manually assigned IP |
| **TP-Link** | DHCP → Address Reservation |
| **OpenWrt** | Network → DHCP and DNS → Static Leases |
| **UniFi** | Settings → Networks → [LAN] → DHCP → DHCP Static IP |
| **Google/Nest Wifi** | App Google Home → WiFi → ⋮ → Advanced → DHCP → IP reservations |

Si tu router no tiene reservas DHCP, alternativa: configurar IP estática **solo en el dispositivo** (raro en bombillas) o sustituir el router/AP por uno con reservas.

---

## Paso 3 — Aplicar el cambio en cada bombilla

Tras guardar las reservas:

**Opción 1 — Reinicio suave (recomendado)**

1. Apaga la bombilla (interruptor o app) **10 segundos**.
2. Enciende de nuevo.
3. Espera 1–2 minutos.

**Opción 2 — Renovar DHCP desde el router**

En la lista de clientes: *Desconectar* / *Renew lease* (si existe).

**Opción 3 — Reiniciar el router**

Solo si las bombillas no cogieron la IP reservada (menos habitual).

---

## Paso 4 — Verificar

Desde tu Mac:

```bash
# Sustituye por tus IPs reservadas
ping -c 2 192.168.1.121
ping -c 2 192.168.1.122

# Comprobar que la MAC corresponde (desde el router o arp tras ping)
arp -a | grep 192.168.1.121
arp -a | grep 192.168.1.122
```

En **Xiaomi Home** y **Smart Life**: la IP del dispositivo debe coincidir con la reservada.

En **Alexa**: prueba *«Alexa, enciende [nombre bombilla]»* — debe seguir funcionando igual.

---

## Paso 5 — Home Assistant (después de fijar IP)

### Bombilla Xiaomi (Mi Home)

1. Obtén el **token** local (una vez): [Xiaomi Cloud Tokens Extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor).
2. **Ajustes → Dispositivos y servicios → Xiaomi Home → Configurar manualmente**.
3. IP: `192.168.1.121` · Token: *(el extraído)*.
4. Guarda token y MAC en tu gestor de contraseñas (el token no cambia con la IP).

### Bombilla Antela (Smart Life / Tuya)

1. **Integración Tuya** (nube) o **Local Tuya** (local, más estable ante cortes de nube).
2. Para Local Tuya necesitas: IP fija, `device_id`, `local_key`, `version` (se obtienen con *Tuya IoT* + herramientas de extracción).
3. IP: `192.168.1.122`.

Documentación HA: [Tuya](https://www.home-assistant.io/integrations/tuya/) · [Local Tuya (HACS)](https://github.com/rodpayne/home-assistant-localtuya).

---

## Alexa y las apps móviles

| Canal | ¿Depende de la IP local? |
|-------|---------------------------|
| **Alexa** (skill Xiaomi / Smart Life) | No — cloud |
| **Xiaomi Home** / **Smart Life** | No en uso normal — cloud |
| **Home Assistant** (control local) | **Sí** — por eso fijamos IP |

No hace falta re-vincular Alexa tras la reserva DHCP.

---

## Buenas prácticas

1. **Documenta** MAC, IP reservada y habitación en una tabla (o en este archivo).
2. **No resetees** las bombillas salvo necesidad (puede cambiar token/clave local).
3. **Misma WiFi** que HA y el móvil (evita VLAN IoT aislada hasta que sepas configurar reglas/firewall).
4. **Nombres claros** en router y apps: `bombilla-xiaomi-salon`, `bombilla-antela-dormitorio`.

---

## Solución de problemas

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| Sigue con IP distinta | Reserva mal escrita o MAC incorrecta | Revisa MAC en router; corrige reserva |
| No aparece en clientes DHCP | Bombilla apagada o otra WiFi | Enciende; comprueba SSID 2.4 GHz |
| HA no conecta, Alexa sí | Token/clave local incorrectos | Re-extrae token (Xiaomi) o local_key (Tuya) |
| Tras reserva, app no responde | Caché / timing | Espera 2 min; reinicia bombilla |

---

## Checklist rápido

- [ ] MAC bombilla Xiaomi anotada
- [ ] MAC bombilla Antela anotada
- [ ] Reserva `192.168.1.121` → MAC Xiaomi
- [ ] Reserva `192.168.1.122` → MAC Antela
- [ ] Reserva `192.168.1.53` → MAC Pi-hole VM (si usas Pi-hole; ver [pihole.md](pihole.md))
- [ ] Reinicio bombillas y verificación ping
- [ ] Alexa probada en ambas
- [ ] HA configurado con IP fija (+ token / Tuya)
