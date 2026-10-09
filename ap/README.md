# ap01, TP-Link TL-WA801ND v3

AP del kit (sección 5.3 del documento). La ficha del equipo, con menús y valores de fábrica, está en `workspace/contexto/equipos/ap01-tl-wa801nd.md`.

**Estado (2026-10-09).** Configurado en la primera sesión de laboratorio y conectado a ether2 de sw01. Gestión verificada desde kit01; falta probar clientes en los SSID (necesita el DHCP de kit01).

## Configuración aplicada

Valores aplicados y confirmados por el equipo desde la interfaz web del AP. Desde kit01 se verificó además la gestión (sección siguiente).

| Parámetro | Valor |
|---|---|
| Modo | Multi-SSID con "Enable VLAN" |
| SSID1 | `SaludMovil-Clinica`, VLAN 10, WPA2-PSK con AES y clave simple por alcance académico (no se escribe aquí) |
| SSID2 | `SaludMovil-Comunidad`, VLAN 40, abierta (portal cautivo en kit01) |
| Radio | 11bgn mixed, ancho de canal 20 MHz, canal automático (valor de fábrica), Short GI activado |
| LAN | `10.20.10.3/24`, gateway `10.20.10.1`, "Allow remote access" desactivado |
| Servidor DHCP del AP | Desactivado |
| WPS, SNMP | Desactivados |
| AP Isolation | Activado (aplica a los dos SSID) |
| Contraseña de administración | La de fábrica, que se mantiene por alcance académico (R-12) |
| Respaldo | Archivo de Backup, guardado fuera del repositorio |

## Comportamiento comprobado

La gestión del AP **recibe** tramas etiquetadas en la VLAN 10 pero **responde sin etiqueta**. Con ether2 de sw01 aceptando solo tramas etiquetadas, las respuestas se descartaban (los contadores de ether2 mostraban 20 broadcasts enviados al AP y 18 unicast recibidos, sin respuesta en kit01). Con ether2 híbrido (PVID 10, acepta tramas sin etiqueta) responde así.

```
$ ping -c3 10.20.10.3
3 packets transmitted, 3 received, 0% packet loss
$ curl -s -o /dev/null -w "%{http_code}\n" http://10.20.10.3/
200
$ ip neigh show 10.20.10.3
10.20.10.3 dev lan0.10 lladdr f4:f2:6d:59:80:b6 REACHABLE
```

## Acceso a la gestión

- Desde kit01 o una estación de administración de la VLAN 10: `http://10.20.10.3`.
- En remoto por NetBird, con `ssh -L 8080:10.20.10.3:80 <usuario>@<ip-netbird-kit01>` y abrir `http://localhost:8080`.

## Pendiente

- Comprobar con celulares que cada SSID entrega dirección de su VLAN (IPv4 e IPv6), el aislamiento y que nadie recibe `192.168.0.x` (`network#7`).
