# Kea en kit01 (DHCPv4 y DHCPv6 sin estado)

Servidores DHCPv4 y DHCPv6 sin estado del kit. Los instalan y configuran los roles `kea_dhcp4` y `kea_dhcp6` de [`../../ansible/roles/`](../../ansible/roles/) con `platform/ansible/playbooks/dhcp.yml`, junto con radvd ([`../radvd/`](../radvd/)). Pools, préstamos y gateways salen de `red.yml` y las reservas de `dhcp.yml` (inventario de `platform/ansible`), así que cada valor se define una sola vez.

| Elemento | Valor |
|---|---|
| Paquetes | `kea-dhcp4-server`, `kea-dhcp6-server` y `kea-common` 2.4.1-3ubuntu0.2, retenidos con `hold` (versión en `paquetes.yml`) |
| Interfaces | Solo `lan0.10` y `br-com`, con sockets *raw*. **Nunca la WAN**: un DHCP en la red del sitio sería grave |
| Interna (`lan0.10`) | Pool `10.20.10.100 - 10.20.10.199`, préstamo de 8 h, gateway `10.20.10.1` |
| Comunidad (`br-com`) | Pool `10.20.40.100 - 10.20.40.250`, préstamo de 1 h, gateway `10.20.40.1` |
| Opciones | DNS `10.20.20.10`, dominio y búsqueda `salud.movil`, NTP `10.20.20.10` (opción 42) |
| Administración | Cualquier equipo conectado a un puerto de `dhcp_puertos_admin` recibe una dirección de `dhcp_pool_admin` (`10.20.10.10 - 10.20.10.28`), con préstamo de 1 h. Kea reconoce el puerto por la opción 82 que agrega sw01 (clase `puerto_admin`, `relay4[2].hex`). Los demás clientes de la Interna usan el pool normal (clase `puerto_normal`). No hay reservas por MAC |
| Préstamos | `memfile` en `/var/lib/kea/kea-leases4.csv` |
| Log | Al journal, con nivel INFO (`DHCP4_LEASE_ALLOC` por cada asignación) |
| DHCPv6 | Sin estado y sin pools: responde los `Information-Request` en `lan0.10` y `br-com` con DNS `fd5a:fc7e:d716:20::10`, búsqueda `salud.movil` y NTP `fd5a:fc7e:d716:20::10` (opción `sntp-servers`, enviada siempre). Kea responde desde la primera link-local de la interfaz; en kit01 es `fe80::1` |

## Cómo se despliega

Desde `platform/ansible/`:

```bash
ansible-playbook playbooks/dhcp.yml --check --diff
ansible-playbook playbooks/dhcp.yml
```

- **Arranque restringido.** El paquete se instala con un `policy-rc.d` temporal que impide arrancar el servicio. Arranca recién con la configuración del kit, aunque la de fábrica tampoco reparte en ninguna interfaz.
- **Validación.** Cada configuración se valida con `kea-dhcp4 -t` antes de escribirse. AppArmor solo deja leer a `kea-dhcp4` en `/etc/kea/`, así que la validación usa una copia temporal ahí.
- **Apt solo si hace falta.** El rol usa apt solo si el paquete falta o no tiene la versión fija, así no hace `apt update` en cada ejecución.

Para agregar un puerto de administración se agrega su nombre en `inventarios/kit/group_vars/all/dhcp.yml` y se vuelve a ejecutar el playbook. sw01 debe tener `add-dhcp-option82=yes`.

```yaml
dhcp_puertos_admin: ["ether4-interna", "ether5-interna"]
```

La `.29` queda fuera del pool, para usarla como dirección fija a mano si el DHCP falla.

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `systemctl is-active kea-dhcp4-server` | `active` |
| `sudo journalctl -u kea-dhcp4-server \| grep ADD_IFACE` | `listening on interface lan0.10` y `br-com`, nada más |
| `sudo ss -0 -lp \| grep kea` | Sockets solo en `lan0.10` y `br-com` |
| En `prueba01` (Comunidad): `ip -4 -br addr`, `ip -4 route`, `resolvectl dns eth0`, `resolvectl domain eth0` | Dirección en `.100-.250`, `default via 10.20.40.1`, `10.20.20.10`, `salud.movil` |
| `sudo journalctl -u kea-dhcp4-server \| grep LEASE_ALLOC` | Una línea por asignación, con MAC e IP |
| `sudo tcpdump -n -v -i br-com 'udp port 547 or udp port 546'` mientras un cliente se conecta | `dhcp6 inf-req` del cliente y `dhcp6 reply` de kit01 |
| En `prueba01`: `resolvectl dns eth0` y `networkctl status eth0` | `fd5a:fc7e:d716:20::10` como DNS y NTP, además de los de IPv4 |

En el laboratorio virtual, el cliente de la VLAN 10 recibe la reserva de prueba `10.20.10.10` (y `10.20.10.100` del pool sin reserva). Ahí Kea se instala desde `.deb` descargados por kit01, porque el laboratorio no tiene Internet.

## Diagnóstico

- **Un cliente no recibe dirección.** Revisar que el firewall lo deje pasar (`udp/67` desde la Interna y la Comunidad) y el journal de Kea. Si no aparece `DHCP4_BUFFER_RECEIVED`, el pedido no llega (VLAN del puerto en sw01 o del SSID en el AP).
- **La configuración no valida.** El playbook muestra el error de `kea-dhcp4 -t` con la línea; la configuración anterior sigue en uso.
- **Una reserva no se entrega.** La MAC tiene que estar en minúsculas con `:` y la IP dentro de `10.20.10.0/24`; los préstamos viejos se ven en `/var/lib/kea/kea-leases4.csv`.
