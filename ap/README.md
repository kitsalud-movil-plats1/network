# ap01, TP-Link TL-WA801ND v3

AP del kit. La ficha del equipo, con menús y valores de fábrica, está en `workspace/contexto/equipos/ap01-tl-wa801nd.md`.

**Estado (2026-11-02).** Configurado y conectado a ether2 de sw01. La configuración se comprueba en remoto desde kit01 con `revisar-ap.sh`, y un cliente de la Comunidad (`prueba01`) recibe IPv4 e IPv6 de su red y no llega a la gestión del AP. Los celulares en cada SSID y el aislamiento entre clientes del mismo SSID se demuestran en la sustentación.

## Configuración aplicada

Valores aplicados desde la interfaz web del AP y comprobados con `revisar-ap.sh`.

| Parámetro | Valor |
|---|---|
| Modo | Multi-SSID con "Enable VLAN" |
| SSID1 | `SaludMovil-Clinica`, VLAN 10, WPA2-PSK con AES y clave simple por alcance académico (no se escribe aquí) |
| SSID2 | `SaludMovil-Comunidad`, VLAN 40, abierta (portal cautivo en kit01) |
| SSID3, SSID4 | Desactivados |
| Radio | 11bgn mixed, ancho de canal 20 MHz, canal automático (valor de fábrica), Short GI activado |
| LAN | `10.20.10.3/24` fija, gateway `10.20.10.1`, "Allow remote access" desactivado |
| Servidor DHCP del AP | Desactivado |
| WPS, SNMP | Desactivados |
| AP Isolation | Activado (aplica a los dos SSID) |
| Contraseña de administración | La de fábrica, que se mantiene por alcance académico |
| Respaldo | Archivo de Backup, guardado fuera del repositorio |

## Revisar la configuración

`revisar-ap.sh` lee la página de gestión del AP sin cambiar nada. Inicia sesión, pide las páginas de Wi-Fi, avanzado, DHCP, WPS, SNMP y red, compara cada valor con la tabla de arriba y cierra la sesión. Nunca envía un formulario. Desde la máquina de control (con el Ansible de `platform/ansible`) se copia a kit01 y se ejecuta ahí con la clave del vault, que no se imprime.

```bash
./ap/revisar-ap.sh
```

```
== ap01 (http://10.20.10.3), 2026-11-02 16:28:13 -0500
    Firmware 3.16.9 Build 150723 Rel.62240n, hardware WA801ND v3

## Wi-Fi
  [ OK ]  Modo Multi-SSID (sí)
  [ OK ]  VLAN por SSID activada (sí)
  [ OK ]  SSID1 (SaludMovil-Clinica)
  [ OK ]  VLAN del SSID1 (10)
  [ OK ]  SSID2 (SaludMovil-Comunidad)
  [ OK ]  VLAN del SSID2 (40)
  [ OK ]  SSID2 activo (sí)
  [ OK ]  SSID3 activo (no)
  [ OK ]  SSID4 activo (no)
  [ OK ]  Aislamiento de clientes (AP Isolation) (sí)

## Servicios del AP
  [ OK ]  Servidor DHCP activo (no)
  [ OK ]  WPS activo (no)
  [ OK ]  SNMP activo (no)

## Gestión
  [ OK ]  Dirección IP fija (sí)
  [ OK ]  Dirección (10.20.10.3)
  [ OK ]  Gateway (10.20.10.1)
  [ OK ]  Acceso remoto (Allow remote access) (no)

Resultado: 17 bien y 0 con falla. Sesión cerrada.
```

El AP guarda la configuración en arreglos de JavaScript dentro de cada página (`wlanPara`, `vlanPara`, `wlanAdv`, `DHCPPara`, `wpsInf`, `snmpParam`, `lanPara`). El script toma de ahí los índices que usa la propia interfaz para llenar el formulario. El inicio de sesión a veces devuelve la página de entrada en el primer intento después de cerrar otra sesión, así que se intenta hasta tres veces.

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

**Cliente de la Comunidad.** `prueba01`, la VM de kit01 conectada a `br-com` (la VLAN 40, la misma red que el SSID2), recibe dirección de su red en las dos familias y no llega a la gestión del AP. El intento queda en el registro del firewall de kit01.

Con el script de P1 en `prueba01` (2026-11-02).

```
## IPv4 (Kea DHCPv4)
  [ OK ]  Dirección 10.20.40.114 del rango del kit
  [ OK ]  Gateway IPv4 (10.20.40.1)
  [ OK ]  El gateway responde al ping IPv4

## IPv6 (SLAAC con el anuncio de radvd)
  [ OK ]  Dirección fd5a:fc7e:d716:40:5054:ff:fe40:50 del prefijo fd5a:fc7e:d716:40::/64
  [ OK ]  Gateway IPv6 (fe80::1)
  [ OK ]  El gateway responde al ping IPv6 (fe80::1%eth0)

## DNS (DHCPv4 y DHCPv6 stateless)
  [ OK ]  DNS IPv4 del kit (10.20.20.10)
  [ OK ]  DNS IPv6 del kit (fd5a:fc7e:d716:20::10)
  [ OK ]  Resuelve portal.salud.movil (10.20.40.1)
```

Con el script de P3 en `prueba01`, con el portal aceptado. La gestión del AP solo tiene IPv4, así que por IPv6 se prueba la Interna (kit01 y el SSH del switch).

```
## Interna y gestión de los equipos de red
  [ OK ]  IPv4 la Interna (10.20.10.1) no responde
  [ OK ]  IPv4 bloqueado: gestión del AP (http://10.20.10.3)
  [ OK ]  IPv4 bloqueado: SSH del switch (10.20.10.2 puerto 22)
  [ OK ]  IPv6 la Interna (fd5a:fc7e:d716:10::1) no responde
  [ OK ]  IPv6 bloqueado: SSH del switch (fd5a:fc7e:d716:10::2 puerto 22)
```

En kit01, `/var/log/kitsalud/kit01/firewall.log` registra cada intento con el origen de `prueba01`.

```
2026-11-02T16:48:20 kit01 kernel: fw-drop F-20 IN=br-com OUT=lan0.10 SRC=10.20.40.114 DST=10.20.10.3 PROTO=TCP SPT=51220 DPT=80 SYN
2026-11-02T16:48:25 kit01 kernel: fw-drop F-20 IN=br-com OUT=lan0.10 SRC=10.20.40.114 DST=10.20.10.2 PROTO=TCP SPT=35922 DPT=22 SYN
2026-11-02T16:48:28 kit01 kernel: fw-drop IN=br-com OUT= SRC=fd5a:fc7e:d716:0040:5054:00ff:fe40:0050 DST=fd5a:fc7e:d716:0010:0000:0000:0000:0001 PROTO=ICMPv6 TYPE=128
2026-11-02T16:52:35 kit01 kernel: fw-drop F-20 IN=br-com OUT=lan0.10 SRC=fd5a:fc7e:d716:0040:5054:00ff:fe40:0050 DST=fd5a:fc7e:d716:0010:0000:0000:0000:0002 PROTO=TCP SPT=42008 DPT=22 SYN
```

Las líneas están recortadas (sin la MAC, el largo ni la ventana). El ping a kit01 por IPv6 queda con el prefijo general porque va dirigido a kit01 y lo descarta la cadena de entrada; lo que cruza hacia la Interna lo descarta la regla de la Comunidad hacia la Interna.

## Acceso a la gestión

- Desde kit01 o una estación de administración de la VLAN 10, en `http://10.20.10.3`.
- En remoto por NetBird, con `ssh -L 8080:10.20.10.3:80 <usuario>@<ip-netbird-kit01>` y abrir `http://localhost:8080`.

## En la sustentación

Con un celular en cada SSID y el script de P1 se muestra que cada SSID entrega dirección de su VLAN en IPv4 e IPv6, que ninguno recibe `192.168.0.x` y que dos clientes del mismo SSID no se ven (P3 con la IP del otro celular).
