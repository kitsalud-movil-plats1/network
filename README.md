# network

Configuración de red del kit: **kit01** como router/firewall (host Ubuntu), **sw01** (MikroTik CCR2004-16G-2S+PC usado como switch L2) y **ap01** (TP-Link TL-WA801ND v3).

| Ruta | Contenido |
|---|---|
| `kit01/netplan/` | Interfaces `wan0` (NIC1, DHCPv4) y `lan0` (NIC2, trunk) con las subinterfaces `lan0.10` (Interna) y `lan0.40` (Comunidad), y el bridge `br-srv` (red de servidores). Nombres fijados por MAC; `fe80::1` en cada interfaz interna |
| `kit01/nftables/` | Tabla `inet` con las zonas y las reglas v4/v6, filtrado entre VMs (familia `bridge`) y NAT IPv4 en una tabla aparte |
| `kit01/kea/` | Kea DHCPv4 (pools y reservas por MAC) y DHCPv6 stateless (DNS, dominio y NTP) |
| `kit01/radvd/` | RA con SLAAC, M=0 y O=1, sin RDNSS |
| `kit01/portal/` | Portal cautivo: página de aceptación (nginx), script que autoriza la MAC en nftables y respuestas para la detección de portal sin Internet |
| `switch/` | Configuración de RouterOS de sw01 exportada con `/export` y saneada: bridge `bridge-kit` con VLAN filtering, puertos ether1-ether8 (chip `switch1`), VLAN 10, 40 y 20 (solo con el +1 equipo), gestión en `vlan10-Interna`, reenvío IP desactivado, DHCP snooping y servicios limitados |
| `ap/` | Configuración del AP en modo Multi-SSID: `SaludMovil-Clinica` con VLAN ID 1 (sin etiqueta → VLAN 10), `SaludMovil-Comunidad` con VLAN ID 40, AP Isolation, WPS desactivado; respaldo de la configuración sin contraseñas |

Referencia de diseño: `docs/arquitectura/00-punto-de-partida.md` (secciones 5, 6, 7 y 8).
