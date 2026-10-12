# Kea DHCPv4 en kit01

Servidor DHCPv4 del kit (R1, sección 7.1). Lo instala y configura el rol `kea_dhcp4` de [`../../ansible/roles/kea_dhcp4/`](../../ansible/roles/kea_dhcp4/) con `platform/ansible/playbooks/dhcp.yml`. Pools, préstamos y gateways salen de `red.yml` y las reservas de `dhcp.yml` (inventario de `platform/ansible`), así que cada valor se define una sola vez.

| Elemento | Valor |
|---|---|
| Paquetes | `kea-dhcp4-server` y `kea-common` 2.4.1-3ubuntu0.2, retenidos con `hold` |
| Interfaces | Solo `lan0.10` y `br-com`, con sockets *raw*. **Nunca la WAN**: un DHCP en la red del sitio sería grave |
| Interna (`lan0.10`) | Pool `10.20.10.100 - 10.20.10.199`, préstamo de 8 h, gateway `10.20.10.1` |
| Comunidad (`br-com`) | Pool `10.20.40.100 - 10.20.40.250`, préstamo de 1 h, gateway `10.20.40.1` |
| Opciones | DNS `10.20.20.10`, dominio y búsqueda `salud.movil`, NTP `10.20.20.10` (opción 42) |
| Reservas | `dhcp_reservas` (MAC, IP en `10.20.10.10-29`, nombre), para las estaciones de administración (D-18). En el kit está vacía hasta tener las MAC de las laptops del grupo |
| Préstamos | `memfile` en `/var/lib/kea/kea-leases4.csv` |
| Log | Al journal, con nivel INFO (`DHCP4_LEASE_ALLOC` por cada asignación) |

## Cómo se despliega

Desde `platform/ansible/`:

```bash
ansible-playbook playbooks/dhcp.yml --check --diff
ansible-playbook playbooks/dhcp.yml
```

- **Arranque restringido.** El paquete se instala con un `policy-rc.d` temporal que impide arrancar el servicio. Arranca recién con la configuración del kit, aunque la de fábrica tampoco reparte en ninguna interfaz.
- **Validación.** Cada configuración se valida con `kea-dhcp4 -t` antes de escribirse. AppArmor solo deja leer a `kea-dhcp4` en `/etc/kea/`, así que la validación usa una copia temporal ahí.
- **Apt solo si hace falta.** El rol usa apt solo si el paquete falta o no tiene la versión fija, así no hace `apt update` en cada ejecución.

Para reservar una estación de administración se agrega a `inventarios/kit/group_vars/all/dhcp.yml` y se vuelve a ejecutar el playbook:

```yaml
dhcp_reservas:
  - { nombre: admin-ana, mac: "aa:bb:cc:dd:ee:ff", ipv4: 10.20.10.10 }
```

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `systemctl is-active kea-dhcp4-server` | `active` |
| `sudo journalctl -u kea-dhcp4-server \| grep ADD_IFACE` | `listening on interface lan0.10` y `br-com`, nada más |
| `sudo ss -0 -lp \| grep kea` | Sockets solo en `lan0.10` y `br-com` |
| En `prueba01` (Comunidad): `ip -4 -br addr`, `ip -4 route`, `resolvectl dns eth0`, `resolvectl domain eth0` | Dirección en `.100-.250`, `default via 10.20.40.1`, `10.20.20.10`, `salud.movil` |
| `sudo journalctl -u kea-dhcp4-server \| grep LEASE_ALLOC` | Una línea por asignación, con MAC e IP |

En el laboratorio virtual, el cliente de la VLAN 10 recibe la reserva de prueba `10.20.10.10` (y `10.20.10.100` del pool sin reserva). Ahí Kea se instala desde `.deb` descargados por kit01, porque el laboratorio no tiene Internet.

## Diagnóstico

- **Un cliente no recibe dirección.** Revisar que el firewall lo deje pasar (`udp/67` desde la Interna y la Comunidad) y el journal de Kea. Si no aparece `DHCP4_BUFFER_RECEIVED`, el pedido no llega (VLAN del puerto en sw01 o del SSID en el AP).
- **La configuración no valida.** El playbook muestra el error de `kea-dhcp4 -t` con la línea; la configuración anterior sigue en uso.
- **Una reserva no se entrega.** La MAC tiene que estar en minúsculas con `:` y la IP dentro de `10.20.10.0/24`; los préstamos viejos se ven en `/var/lib/kea/kea-leases4.csv`.
