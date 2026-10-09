# sw01 — MikroTik CCR2004-16G-2S+PC

Switch L2 del kit (D-03, sección 5.2 del documento). Ficha del equipo: `workspace/contexto/equipos/sw01-ccr2004.md`.

**Estado (2026-10-09):** configuración base aplicada en la primera sesión de laboratorio. Archivo: [`sw01.rsc`](sw01.rsc) (`/export terse`; RouterOS 7 omite los datos sensibles).

## Puertos

| Puerto | Nombre | Conectado a | VLAN | Estado |
|---|---|---|---|---|
| ether1 | `ether1-kit01` | kit01 `enp171s0` (futuro `lan0`) | 10, 40 y 20 etiquetadas; solo tramas etiquetadas | Enlace 1 Gb/s |
| ether2 | `ether2-ap01` | AP (puerto LAN del inyector PoE) | Híbrido: 10 y 40 etiquetadas hacia el AP; desde el AP acepta etiquetadas y sin etiqueta (PVID 10) | Enlace 100 Mb/s |
| ether3 | `ether3-laptop` | - | 10 y 20 etiquetadas | Deshabilitado |
| ether4-ether8 | `ether4-interna` … `ether8-interna` | Estaciones (sin conectar) | Acceso VLAN 10 | Habilitados |
| ether9-ether16, SFP+ | - | - | - | Deshabilitados, fuera del bridge |

ether2 es híbrido porque la gestión del AP responde sin etiqueta (S-03).

## Configuración aplicada

- Bridge `bridge-kit` con `vlan-filtering=yes`; tabla de VLAN 10, 40 y 20 según la tabla anterior.
- Gestión: `vlan10-Interna` sobre el bridge, `10.20.10.2/24` y `fd5a:fc7e:d716:10::2/64`; ruta por defecto IPv4 a `10.20.10.1` e IPv6 a `fe80::1%vlan10-Interna`.
- Reenvío IPv4 e IPv6 desactivado; sin aceptar RA.
- Servicios: telnet, FTP, web y API apagados; SSH y Winbox solo desde `10.20.10.1` y las IPs de administración `10.20.10.10-29`.
- Nombre `sw01`, zona horaria `America/Bogota`.

Se aplicó por la consola serial (RJ45, 115200 8N1) en el orden de la guía: nombres y puertos deshabilitados, bridge y VLAN con el filtrado apagado, gestión movida al bridge, servicios y, al final, el filtrado de VLAN.

## Verificación

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

En sw01: `/interface bridge port print`, `/interface bridge vlan print`, `/ip settings print` (`ip-forward: no`), `/ipv6 settings print` (`forward: no`), `/ip address print` (solo la gestión).

## Pendiente

- Usuario compartido del grupo y eliminar `admin` (D-18).
- DHCP snooping y filtro de RA (`network#11`).
- Hora: el reloj está en 1970 hasta que exista `ntp.salud.movil`.

## Restaurar

Desde un equipo sin configuración (`/system reset-configuration no-defaults=yes`), copiar `sw01.rsc` al MikroTik y ejecutar `/import file-name=sw01.rsc` por la consola serial. Después, recrear el usuario del grupo.
