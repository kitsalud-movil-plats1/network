# sw01, MikroTik CCR2004-16G-2S+PC

Switch L2 del kit (D-03, sección 5.2 del documento). La ficha del equipo está en `workspace/contexto/equipos/sw01-ccr2004.md`.

**Estado (2026-10-09).** Configuración base aplicada en la primera sesión de laboratorio. El archivo es [`sw01.rsc`](sw01.rsc) (`/export terse`; RouterOS 7 omite los datos sensibles).

## Puertos

| Puerto | Nombre | Conectado a | VLAN | Estado |
|---|---|---|---|---|
| ether1 | `ether1-kit01` | kit01 `enp171s0` (futuro `lan0`) | 10, 40 y 20 etiquetadas; solo tramas etiquetadas | Enlace 1 Gb/s |
| ether2 | `ether2-ap01` | AP (puerto LAN del inyector PoE) | Híbrido, 10 y 40 etiquetadas hacia el AP; desde el AP acepta etiquetadas y sin etiqueta (PVID 10) | Enlace 100 Mb/s |
| ether3 | `ether3-laptop` | - | 10 y 20 etiquetadas | Deshabilitado |
| ether4-ether8 | `ether4-interna` … `ether8-interna` | Estaciones (sin conectar) | Acceso VLAN 10 | Habilitados |
| ether9-ether16, SFP+ | - | - | - | Deshabilitados, fuera del bridge |

ether2 es híbrido porque la gestión del AP responde sin etiqueta (S-03).

## Configuración aplicada

- Bridge `bridge-kit` con `vlan-filtering=yes`; tabla de VLAN 10, 40 y 20 según la tabla anterior.
- Gestión en `vlan10-Interna` sobre el bridge, con `10.20.10.2/24` y `fd5a:fc7e:d716:10::2/64`; ruta por defecto IPv4 a `10.20.10.1` e IPv6 a `fe80::1%vlan10-Interna`.
- Reenvío IPv4 e IPv6 desactivado; sin aceptar RA.
- Servicios telnet, FTP, web y API apagados; SSH y Winbox solo desde `10.20.10.1` y las IPs de administración `10.20.10.10-29`, que son IPv4, así que por IPv6 no entra nadie.
- **DHCP snooping** en `bridge-kit`, con `ether1-kit01` como único puerto de confianza (`trusted=yes`). Las respuestas de un servidor DHCP que entren por cualquier otro puerto se descartan, y las peticiones de los clientes solo salen por ether1, hacia Kea en kit01. Sin opción 82.
- **RA desde los puertos de acceso.** La lista de interfaces `acceso` tiene ether2 (el AP, con los clientes Wi-Fi de las dos VLAN) y ether4 a ether8. Una regla de `/interface bridge filter` descarta en `forward` el IPv6 hacia `33:33:00:00:00:01` (la MAC de `ff02::1`, todos los nodos) que entre por esos puertos, que es donde van los RA. RouterOS no tiene RA Guard ni distingue el tipo de ICMPv6 en el bridge, así que la regla también descarta los NA no solicitados de los clientes, que no hacen falta. Los RA de kit01 entran por ether1 y no se tocan.
- **Puertos de acceso por la CPU.** El chip (Marvell 88E6191X) no acepta reglas de switch, y con conmutación por hardware el filtro del bridge no ve el multicast. Por eso ether2 y ether4 a ether8 tienen `hw=no`. ether1 sigue con conmutación por hardware. Con el AP de 100 Mb/s y pocas estaciones, la CPU del CCR2004 queda cerca de 0 %.
- Nombre `sw01`, zona horaria `America/Bogota` y cliente NTP de `10.20.20.10` (`ntp.salud.movil`, Chrony en kit01); `/system ntp client print` debe decir `synchronized`.
- Syslog hacia kit01 (F-16, observability#3). La acción `remote` envía a `10.20.20.10:514` por UDP en formato BSD (`bsd-syslog=yes`), con los temas `info`, `warning`, `error` y `critical`, además de la memoria. Los mensajes quedan en `/var/log/kitsalud/sw01/syslog.log` de kit01. Se aplicó por SSH a través de kit01 en Safe Mode.
- Usuario `admin`, que es el usuario compartido del grupo (D-18). Su contraseña se mantiene por alcance académico (R-14) y no se escribe en el repositorio.

La base se aplicó por la consola serial (RJ45, 115200 8N1) en el orden de la guía. Primero los nombres y los puertos deshabilitados, luego bridge y VLAN con el filtrado apagado, gestión movida al bridge, servicios y, al final, el filtrado de VLAN.

## Verificación

**Gestión solo desde admin (criterio de network#11).** Desde kit01, con una dirección temporal fuera del rango admin, `sudo ip addr add 10.20.10.250/32 dev lan0.10`, después `ssh -b 10.20.10.250 admin@10.20.10.2` responde `Connection closed by 10.20.10.2 port 22`, y `ssh -b 10.20.10.1 ...` llega a pedir la contraseña. `ssh admin@fd5a:fc7e:d716:10::2` también se cierra. Al terminar, `sudo ip addr del 10.20.10.250/32 dev lan0.10`.

**Snooping y filtro de RA.** En sw01, `/interface bridge print` (`dhcp-snooping=yes`), `/interface bridge port print detail where interface=ether1-kit01` (`trusted=yes`), `/interface bridge port print` (columna `HW`, `no` en ether2 y ether4 a ether8) y `/interface bridge filter print stats` (el contador sube con cada RA o NA hacia todos los nodos que llega por un puerto de acceso).

Desde kit01:

```
$ ping -c3 10.20.10.2
3 packets transmitted, 3 received, 0% packet loss
$ ping -6 -c2 fd5a:fc7e:d716:10::2
2 packets transmitted, 2 received, 0% packet loss
$ nc -zv 10.20.10.2 22
Connection to 10.20.10.2 22 port [tcp/ssh] succeeded!
$ ssh admin@10.20.10.2 '/ip settings print'   # ip-forward: no
```

Syslog: después de entrar a sw01, `sudo tail /var/log/kitsalud/sw01/syslog.log` en kit01 muestra `user admin logged in from 10.20.10.1 via ssh`. En sw01, `/system logging action print detail where name=remote` y `/system logging print`.

En sw01: `/interface bridge port print`, `/interface bridge vlan print`, `/ip settings print` (`ip-forward: no`), `/ipv6 settings print` (`forward: no`), `/ip address print` (solo la gestión).

## Pruebas en la visita

Necesitan un equipo en un puerto de acceso. Con una laptop Linux en ether4 (VLAN 10, sin etiqueta) y un cliente en ether5 o por el SSID de la Clínica.

1. **DHCP falso.** En la laptop, `sudo ip addr add 10.20.10.240/24 dev <if>` y `sudo dnsmasq --no-daemon --interface=<if> --dhcp-range=192.168.99.10,192.168.99.50,5m --port=0`. El cliente pide dirección (`sudo dhclient -v` o reconectar el Wi-Fi) y tiene que recibir una de `10.20.10.100-199` de Kea, nunca `192.168.99.x`. dnsmasq ve los DISCOVER solo si llegan, y sus OFFER no salen de sw01.
2. **RA falso.** En la laptop, `radvd` anunciando `2001:db8:bad::/64`, o `sudo python3 -c` con scapy enviando un RA a `ff02::1`. En el cliente, `ip -6 addr` no debe mostrar `2001:db8:bad::` y `ip -6 route` solo `default via fe80::1`. En sw01, el contador de la regla de `/interface bridge filter print stats` sube.
3. **Lo legítimo sigue.** El cliente recibe dirección de Kea, SLAAC de kit01 y llega a sus servicios, y `ansible-playbook playbooks/verificar-flujos.yml` pasa completo.

**Lo que no cubre.** Un RA unicast, que solo se envía en respuesta a un RS y apunta a un cliente concreto, no se filtra (R-06). Entre clientes Wi-Fi lo evita el aislamiento del AP, y la regla corta los RA multicast de cualquier puerto de acceso.

## Restaurar

Desde un equipo sin configuración (`/system reset-configuration no-defaults=yes`), copiar `sw01.rsc` al MikroTik y ejecutar `/import file-name=sw01.rsc` por la consola serial.
