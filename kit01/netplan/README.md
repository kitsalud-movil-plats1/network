# Netplan de kit01

[`50-cloud-init.yaml.j2`](50-cloud-init.yaml.j2) es la plantilla del netplan de kit01, que queda en `/etc/netplan/50-cloud-init.yaml` (permisos `600`). cloud-init está desactivado en kit01, así que el archivo no se regenera. Las NIC conservan los nombres del kernel (D-14).

| Interfaz | Uso | Direcciones |
|---|---|---|
| `enp170s0` (MAC `78:55:36:09:07:0b`, rol `wan0`) | Uplink del laboratorio | `192.168.160.69/24` fija, gateway `192.168.160.1`, DNS `192.168.215.20` y `.30`. Con `accept-ra: false` ignora los RA del uplink y no toma dirección del prefijo que anuncia el laboratorio (`2001:db8:a:c::/64`), porque el IPv6 del kit es solo interno (D-12, S-04, 8.3) |
| `enp171s0` (MAC `78:55:36:09:07:0a`, rol `lan0`) | Trunk hacia ether1 de sw01 | Sin dirección propia |
| `lan0.10` (VLAN 10 sobre `enp171s0`) | Red Interna y gestión | `10.20.10.1/24`, `fd5a:fc7e:d716:10::1/64`, `fe80::1/64` |
| `lan0.40` (VLAN 40 sobre `enp171s0`) | Puerto de `br-com` | Sin dirección |
| `br-com` | Comunidad, con `lan0.40` como puerto (y la VM `prueba01` en platform#17) | `10.20.40.1/24`, `fd5a:fc7e:d716:40::1/64`, `fe80::1/64` |
| `srv-dummy0` (dummy) | Puerto de `br-srv` | Sin dirección |
| `br-srv` | Red de servidores, sin puerto físico | `10.20.20.1/24`, `10.20.20.10/24`, `fd5a:fc7e:d716:20::1/64`, `fd5a:fc7e:d716:20::10/64`, `fe80::1/64` |

Los bridges tienen STP apagado y `forward-delay: 0`, y ninguna interfaz interna acepta RA. El reenvío IPv4 e IPv6 está en [`../sysctl/`](../sysctl/).

**Por qué `srv-dummy0`.** Un bridge sin puertos queda sin portadora. Sus IPv6 quedan en `tentative`, su ruta en `linkdown` y ningún servicio puede escuchar en ellas (`bind` responde `Cannot assign requested address`). Con la interfaz dummy como puerto, `br-srv` tiene portadora antes de que existan las VMs y BIND9 y Chrony pueden usar `10.20.20.10` y `fd5a:fc7e:d716:20::10`.

**RA en `enp170s0`.** systemd-networkd procesa los RA por su cuenta (el `accept_ra` del kernel queda en `0`), así que se controlan con `accept-ra` en el netplan y un sysctl `accept_ra` no tiene efecto. `accept-ra: false` deja la WAN sin IPv6 global ni ruta por defecto IPv6, como pide la sección 8.3.

## Cómo se aplica

Con el rol `kit01_red` de [`../../ansible/roles/`](../../ansible/roles/), desde `platform/ansible/` y siempre primero con `--check --diff`.

```bash
ansible-playbook playbooks/red-kit01.yml --check --diff   # qué cambiaría en el archivo y si cambiaría la red activa
ansible-playbook playbooks/red-kit01.yml                  # firewall (kit01_firewall) y red (kit01_red)
```

La plantilla toma las redes de `group_vars/all/red.yml`, los nombres de `iface_wan` e `iface_lan` y la WAN del sitio de `wan` en `host_vars/kit01.yml` (en el laboratorio, DHCP con `match` por MAC). El archivo generado no lleva cabecera, para que sea igual al que se escribió a mano.

El rol nunca usa `netplan apply` ni `netplan try`, y aplica solo cuando hace falta (D-23, `AGENTS.md` sección 6).

1. **Candidato aparte.** Genera el netplan en `/run/kitsalud-red/netplan/etc/netplan/` (tmpfs), junto con los demás archivos de `/etc/netplan`, y ejecuta `netplan generate --root-dir` sobre esa copia, lo que también lo valida. Lo hace también con `--check`.
2. **Comparación.** Compara lo que genera con `/run/systemd/network` y con las reglas de udev de netplan. Si es igual, la red activa no cambia y no se recarga nada, aunque el archivo cambie (por ejemplo, un comentario).
3. **Red tocada a mano.** Si el archivo no cambia pero lo activo no sale de él, el rol se detiene sin aplicar, porque ese estado no se podría restaurar.
4. **Aplicación.** Si hay que aplicar, copia el archivo anterior en `/root/netplan-anterior/` y programa `net-rollback-<época>` a los 120 s (`cp` + `netplan generate` + `networkctl reload`). Después escribe el archivo y ejecuta `netplan generate && networkctl reload`.
5. **Comprobación.** Cierra la conexión de Ansible y entra con una nueva. Compara la huella de las reglas de NetBird en iptables con la de antes y revisa `netbird status`. Solo si la restauración sigue pendiente la cancela; si ya actuó, falla con un aviso.
6. **Restauración pendiente.** Si al empezar hay una `net-rollback-*` o una `fw-rollback-*` pendiente, el rol se detiene.

Para revisar a mano lo que se va a generar, sin tocar `/etc` ni `/run`, se usa `netplan generate --root-dir <directorio>` con el archivo en `<directorio>/etc/netplan/`.

`networkctl reload` también reconfigura `enp170s0`, porque netplan reescribe todos los archivos de `/run/systemd/network/`. La dirección y las rutas se mantienen y el acceso por NetBird no se interrumpe (0 % de pérdida en un ping por NetBird durante el reload).

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `ip -br addr` | Las direcciones de la tabla en `lan0.10`, `br-com` y `br-srv`; `enp170s0` con `192.168.160.69/24` y solo su link-local IPv6 |
| `ip -6 addr \| grep -c tentative` | `0` |
| `bridge link` | `lan0.40` en `br-com` y `srv-dummy0` en `br-srv`, los dos en `forwarding` |
| `ip -6 route show dev enp170s0` | Solo `fe80::/64`, sin ruta por defecto IPv6 |
| `ping 10.20.10.2` y `ping -6 fd5a:fc7e:d716:10::2` | sw01 responde |
| `/interface bridge host print where vid=40` en sw01 | La MAC de `br-com` aprendida en `ether1-kit01` |
| `sudo netbird status` | `Management` y `Signal` en `Connected` |
| `ansible-playbook playbooks/red-kit01.yml --check --diff` | `changed=0` |

## Diagnóstico

- **El rol se detiene con `Lo que hay en /run/systemd/network no coincide`.** Alguien cambió la red sin el netplan, o el archivo de `/etc/netplan` se editó a mano y después se recargó. Se compara con `netplan generate --root-dir` y se decide qué estado vale antes de ejecutar el rol.
- **El rol falla con `La restauración ... ya actuó`.** El acceso no volvió a tiempo con el cambio y todo quedó como antes. Se revisa el cambio en el laboratorio virtual.
- **El rol se detiene por una restauración pendiente.** Se espera a que actúe (`systemctl list-timers 'net-rollback-*'`) o, si el acceso funciona, se cancela con `sudo systemctl stop <nombre>.timer`.

- **Las IPv6 de `br-srv` aparecen en `tentative`.** `srv-dummy0` no está en el bridge; revisar `bridge link` y `networkctl status srv-dummy0`.
- **`enp170s0` toma una IPv6 del uplink.** Falta `IPv6AcceptRA=no` en `/run/systemd/network/10-netplan-enp170s0.network`, es decir, `accept-ra: false` en el netplan.
- **sw01 no aprende la MAC de `br-com`.** Revisar que ether1 lleve la VLAN 40 etiquetada (`/interface bridge vlan print`) y que `lan0.40` esté en `br-com`.

## Pendiente

- Comprobar que las direcciones se mantienen después de reiniciar (P12, platform#13).
