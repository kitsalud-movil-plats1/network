# radvd en kit01

Anuncios de router (RA) para los clientes de la Interna y la Comunidad (D-20, secciones 8.2 y 8.3). Lo instala y configura el rol `radvd` de [`../../ansible/roles/radvd/`](../../ansible/roles/radvd/) con `platform/ansible/playbooks/dhcp.yml`, junto con Kea DHCPv4 y DHCPv6.

| Elemento | Valor |
|---|---|
| Paquete | `radvd` 1:2.19-1ubuntu1, retenido con `hold` (versión en `paquetes.yml`) |
| Interfaces | Solo `lan0.10` y `br-com`. Nunca la WAN ni `br-srv`, donde los servidores tienen direcciones fijas |
| Origen | `fe80::1` (`AdvRASrcAddress`), la puerta de enlace IPv6 de los clientes |
| Flags | M=0 (sin DHCPv6 con estado), O=1 (DNS, dominio y NTP por DHCPv6 sin estado), sin RDNSS |
| Prefijos | `fd5a:fc7e:d716:10::/64` y `fd5a:fc7e:d716:40::/64` (de `red.yml`), con `AdvOnLink` y `AdvAutonomous` (SLAAC) |
| Tiempos | Por defecto: ruta por defecto de 1800 s, prefijo válido 1 día y preferido 4 h |

Android no implementa DHCPv6: toma su IPv6 por SLAAC y usa el DNS que recibe por DHCPv4, que también responde AAAA.

## Cómo se despliega

```bash
ansible-playbook playbooks/dhcp.yml      # desde platform/ansible/
```

El rol instala el paquete sin arrancarlo, valida la configuración con `radvd -c -C` antes de escribirla y reinicia el servicio solo si cambió.

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `grep ^interface /etc/radvd.conf` | `lan0.10` y `br-com` |
| `sudo tcpdump -n -v -i br-com 'icmp6 and ip6[40]==134'` | `fe80::1 > ff02::1 ... router advertisement`, `Flags [other stateful]`, `router lifetime 1800s` y el prefijo con `Flags [onlink, auto]` |
| En `prueba01`: `ip -6 -br addr show eth0` y `ip -6 route show default` | Dirección en `fd5a:fc7e:d716:40::/64` y `default via fe80::1 ... proto ra` |

## Diagnóstico

- **El cliente no toma dirección IPv6.** Ver si llegan los RA con el `tcpdump` de arriba. El firewall de kit01 deja pasar los RS desde `fe80::/10` (F-19), y el cliente tiene que aceptar RA.
- **La ruta por defecto IPv6 no es `fe80::1`.** Revisar `AdvRASrcAddress` y que `fe80::1/64` esté en la interfaz (`ip -6 addr show br-com`).
- **Aparecen RA de otro equipo.** Solo kit01 debe anunciar; el filtro de RA en sw01 es network#11.
