# network

Configuración de red del kit, con **kit01** como router/firewall (host Ubuntu), **sw01** (MikroTik CCR2004-16G-2S+PC usado como switch L2) y **ap01** (TP-Link TL-WA801ND v3).

| Ruta | Contenido |
|---|---|
| `kit01/netplan/` | Interfaces `enp170s0` (rol `wan0`, uplink, que ignora los RA) y `enp171s0` (rol `lan0`, trunk) con `lan0.10` (Interna), el bridge `br-com` (Comunidad, con `lan0.40` y la VM `prueba01` como puertos) y el bridge `br-srv` (red de servidores, con el puerto dummy `srv-dummy0`). Nombres del kernel, sin renombrar; `fe80::1` en cada interfaz interna |
| `kit01/sysctl/` | Reenvío IPv4 e IPv6 de kit01 |
| `kit01/nftables/` | Tabla `inet filtro` con las zonas y las reglas v4/v6, y NAT IPv4 en la tabla aparte `ip nat_kit`, sin tocar las tablas de iptables-nft de NetBird y libvirt; más adelante, filtrado entre VMs (familia `bridge`) |
| `kit01/kea/` | Kea DHCPv4 y DHCPv6 sin estado, solo en `lan0.10` y `br-com` (pools, opciones y reservas por MAC desde el inventario). Roles en `ansible/roles/kea_dhcp4/` y `ansible/roles/kea_dhcp6/` |
| `kit01/radvd/` | RA desde `fe80::1` en `lan0.10` y `br-com` con SLAAC, M=0 y O=1, sin RDNSS. Rol en `ansible/roles/radvd/` |
| `kit01/portal/` | Portal cautivo con la página de aceptación y el inicio con íconos (nginx, solo HTTP en `10.20.40.1` y `fd5a:fc7e:d716:40::1`) y el servicio que autoriza la MAC en el set `portal_ok` por 8 h. Rol en `ansible/roles/kit01_portal/`. Sin Internet se llega abriendo una dirección local por HTTP |
| `switch/` | Configuración de RouterOS de sw01 exportada con `/export`, con el bridge `bridge-kit` y VLAN filtering, puertos ether1-ether8 (chip `switch1`), VLAN 10, 40 y 20 (solo con el +1 equipo), gestión en `vlan10-Interna`, reenvío IP desactivado, DHCP snooping y servicios limitados |
| `ap/` | Configuración del AP en modo Multi-SSID, con `SaludMovil-Clinica` en la VLAN 10, `SaludMovil-Comunidad` en la VLAN 40, AP Isolation, WPS desactivado; respaldo de la configuración sin contraseñas |

El netplan, el sysctl y el firewall de kit01 se despliegan con los roles `kit01_red` y `kit01_firewall` de `ansible/roles/` (`platform/ansible/playbooks/red-kit01.yml`), que solo recargan la red o el firewall si cambia el resultado efectivo, y entonces con restauración programada (D-23).

El diseño de referencia está en `docs/arquitectura/00-punto-de-partida.md` (secciones 5, 6, 7 y 8).
