# network

Configuración de red del kit: **kit01** como router/firewall (host Ubuntu), **switch** (sw01) y **AP** (ap01).

| Ruta | Contenido |
|---|---|
| `kit01/netplan/` | Interfaces `wan0` (NIC1, DHCPv4) y `lan0` (NIC2, trunk) con las subinterfaces `lan0.10` (Interna) y `lan0.40` (Comunidad), y el bridge `br-srv` (red de servidores). Nombres fijados por MAC; `fe80::1` en cada interfaz interna |
| `kit01/nftables/` | Tabla `inet` con las zonas y las reglas v4/v6, filtrado entre VMs (familia `bridge`) y NAT IPv4 en una tabla aparte |
| `kit01/kea/` | Kea DHCPv4 (pools y reservas por MAC) y DHCPv6 stateless (DNS, dominio y NTP) |
| `kit01/radvd/` | RA con SLAAC, M=0 y O=1, sin RDNSS |
| `kit01/portal/` | Portal cautivo: página de aceptación (nginx), script que autoriza la MAC en nftables y respuestas para la detección de portal sin Internet |
| `switch/` | Running-config del switch (VLAN 10, 40, 20 opcional y 999; trunks; ACL de gestión; RA Guard) |
| `ap/` | Configuración de SSID ↔ VLAN (Clínica → 10, Comunidad → 40; sin SSID de gestión) |

Referencia de diseño: `docs/arquitectura/00-punto-de-partida.md` (secciones 6, 7, 8 y 9).
