# Firewall de kit01 (nftables)

Firewall base de kit01 (D-02, secciones 6.3, 8.4 y 11 del documento). Una sola tabla `inet filtro` filtra IPv4 e IPv6, y el NAT de salida va aparte en `ip nat_kit`.

| Archivo | Dónde va en kit01 | Qué hace |
|---|---|---|
| [`nftables.conf.j2`](nftables.conf.j2) | `/etc/nftables.conf` (`755`) | Tablas `inet filtro` e `ip nat_kit`. Los nombres de interfaz y las direcciones están en `define` al principio y salen del inventario (`red.yml`, `iface_wan` y `kit01_firewall_if_netbird`) |
| [`quitar.nft`](quitar.nft) | `/etc/nftables/quitar.nft` | Borra solo las tablas de kit01. Lo usan la restauración programada y el `ExecStop` del servicio |
| [`nftables.service.d/kit01.conf`](nftables.service.d/kit01.conf) | `/etc/systemd/system/nftables.service.d/kit01.conf` | Cambia el `ExecStop` de Ubuntu (`nft flush ruleset`) por `quitar.nft` |
| [`ruleset-kit01.txt`](ruleset-kit01.txt) | - | Listado de las dos tablas aplicadas en kit01 (`nft -s list table ...`) |

## Convivencia con NetBird y libvirt

NetBird y libvirt usan iptables-nft, que crea sus propias tablas (`ip filter`, `ip nat`, `ip mangle`, `ip raw`, `ip6 filter`, `ip6 nat`, `ip6 mangle`). Por eso este firewall sigue tres reglas.

- **Sin `flush ruleset`.** Cada tabla se declara, se borra y se vuelve a crear en la misma transacción (`table inet filtro` / `delete table inet filtro` / `table inet filtro { ... }`). Aplicar el archivo no toca las demás tablas y una segunda aplicación no cambia nada.
- **NAT en `ip nat_kit`.** `ip nat` es la tabla de iptables-nft; si se usara ese nombre, las reglas se mezclarían con las de NetBird.
- **`ExecStop` propio.** `systemctl stop` o `restart nftables` solo quitan las tablas de kit01.

Un paquete tiene que pasar todas las cadenas del mismo gancho, las de iptables-nft y las de `inet filtro`. Por eso `inet filtro` acepta lo que NetBird necesita, el SSH por `wt0` y WireGuard (`udp/51820`) por `enp170s0`. Lo demás de NetBird son conexiones que abre kit01 (management, signal y relays por TCP 443), y vuelven como `established`.

## Qué permite

**Entrada a kit01 (`input`, política drop).**

| Flujo | Origen | Qué |
|---|---|---|
| - | `lo`, conexiones establecidas | Todo |
| F-19 | `fe80::/10` y la ULA (`::` para DAD y MLD) | ICMPv6 imprescindible (RFC 4890) |
| F-01, F-22 | Interna y `wt0` | Eco ICMP (IPv6 solo desde la Interna) |
| F-23 | Comunidad y Servidores (`br-srv`) | Eco ICMP solo hacia su gateway (`10.20.40.1`, `fd5a:fc7e:d716:40::1`; `10.20.20.1`, `fd5a:fc7e:d716:20::1`; y `fe80::1`) |
| F-04 | Interna y Comunidad | DHCPv4 (`udp/67`) y DHCPv6 (`udp/547` desde `fe80::/10`) |
| F-08 | Comunidad | Página del portal cautivo, solo HTTP (`tcp/80`) hacia `10.20.40.1` y `fd5a:fc7e:d716:40::1` ([`../portal/`](../portal/)) |
| F-03 | Interna, Comunidad y `br-srv` | DNS (`53` tcp/udp) y NTP (`udp/123`) hacia `10.20.20.10` y `fd5a:fc7e:d716:20::10` |
| F-15 | clinica01 y comunidad01 (`10.20.20.11`, `.12` y sus `::11`, `::12`) por `br-srv` | rsyslog (`tcp/514`) hacia `10.20.20.10` y `fd5a:fc7e:d716:20::10` |
| F-16 | sw01 (`10.20.10.2` y `fd5a:fc7e:d716:10::2`) por la Interna | rsyslog (`udp/514`) hacia `10.20.20.10` y `fd5a:fc7e:d716:20::10` |
| F-01, F-21 | Admin (`10.20.10.10-29` en la Interna) y `wt0` | SSH (22) y monitoreo (443) |
| - | `enp170s0` | WireGuard de NetBird (`udp/51820`) |

**Reenvío (`forward`, política drop).** Conexiones establecidas, errores ICMPv6 en tránsito (F-19), la Interna hacia `enp170s0` solo por IPv4 (F-24) y las VMs (`10.20.20.11` y `.12`) hacia `enp170s0` por 80 y 443, solo IPv4 (F-17), todo con masquerade de `10.20.0.0/16` en `ip nat_kit`. La Interna llega a DHIS2 y a los recursos SMB de clinica01 (`10.20.20.11` y `fd5a:fc7e:d716:20::11`, `tcp/443` y `tcp/445`, F-05). También llega al 80 y al 443 de comunidad01 (`10.20.20.12` y `fd5a:fc7e:d716:20::12`, F-07), para la biblioteca, los videos y el registro. La Comunidad llega a esos mismos puertos de comunidad01 en IPv4 e IPv6 (F-09) y a Internet solo por IPv4 (F-10), únicamente con la MAC en el set `portal_ok`; sin ella, su HTTPS se rechaza con RST. Las VMs resuelven por BIND9 en kit01 (`10.20.20.10`), así que no necesitan salir por el 53. Los demás flujos de la sección 11 se agregan en la matriz de flujos (network#10).

**Portal cautivo.** El set `portal_ok` (`type ether_addr`, `timeout 8h`) guarda las MAC que aceptaron las condiciones, y lo llena el servicio del portal. La cadena `portal_redireccion` (`nat`, prerouting) manda el HTTP de la Comunidad sin aceptar, hacia cualquier destino que no sea kit01, a `10.20.40.1` o `fd5a:fc7e:d716:40::1`. Los dos están en `inet filtro` porque un set solo se usa dentro de su tabla, y así falla cerrado, porque sin el set nadie de la Comunidad pasa.

**Salida de kit01 (`output`).** Sin filtrar en esta base. La restricción de F-18 va en la matriz de flujos.

**Registro.** Lo que no se acepta en `input` y `forward` se registra en el kernel con el prefijo `fw-drop ` (como máximo 10 por segundo, ráfagas de 50) y se descarta.

El SSH por IPv6 desde la Interna queda bloqueado para todos, porque las estaciones admin solo tienen IP fija en IPv4. El SSH desde la WAN también queda bloqueado. Si NetBird no estuviera disponible, en el sitio se entra con una laptop en un puerto de la Interna con IP fija entre `10.20.10.10` y `10.20.10.29`.

## Cómo se aplica

Con el rol `kit01_firewall` de [`../../ansible/roles/`](../../ansible/roles/), desde `platform/ansible/` y siempre primero con `--check --diff`. El playbook aplica el firewall y después la red ([`../netplan/`](../netplan/)).

```bash
ansible-playbook playbooks/red-kit01.yml --check --diff   # qué cambiaría en el archivo y si cambiaría el ruleset activo
ansible-playbook playbooks/red-kit01.yml
```

`quitar.nft` y el drop-in se copian tal cual, y `nftables.service` queda habilitado sin reiniciarlo. En el laboratorio virtual `kit01_firewall_if_netbird` es `wan0`, porque la máquina anfitriona hace de NetBird.

El rol aplica solo cuando cambia el ruleset efectivo (D-23, `AGENTS.md` sección 6).

1. **Candidato aparte.** Genera el archivo en `/run/kitsalud-red/nftables.conf` (tmpfs) y lo valida con `nft -c`. Lo hace también con `--check`.
2. **Comparación.** Lo carga en un *network namespace* desechable (`unshare --net`) y compara `nft -s list ruleset` con las tablas `inet filtro` e `ip nat_kit` activas. El firewall del host no cambia. Si son iguales, solo se actualiza `/etc/nftables.conf`, sin recargar nada.
3. **Aplicación.** Si hay que aplicar, guarda el ruleset activo en `/run/kitsalud-red/anterior.nft` (cada tabla se declara, se borra y se vuelve a crear) y la copia del archivo en `/etc/nftables.conf.anterior`. Programa `fw-rollback-<época>` a los 120 s, que carga ese ruleset y devuelve el archivo, y ejecuta `nft -f /etc/nftables.conf`.
4. **Comprobación.** Cierra la conexión de Ansible y entra con una nueva. Comprueba que el ruleset activo sea el del archivo, que la huella de las reglas de NetBird en iptables no cambie y que `netbird status` siga conectado. Solo si la restauración sigue pendiente la cancela; si ya actuó, falla con un aviso.
5. **Restauración pendiente.** Si al empezar hay una `fw-rollback-*` o una `net-rollback-*` pendiente, el rol se detiene.

Para comparar a mano un archivo con lo activo sin aplicarlo, se compara `sudo unshare --net sh -c 'nft -f <archivo> && nft -s list ruleset'` con `sudo nft -s list table inet filtro; sudo nft -s list table ip nat_kit`.

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `sudo nft list tables` | Las tablas de iptables-nft más `inet filtro` e `ip nat_kit` |
| `sudo iptables-save \| grep -c NETBIRD` | El mismo número que antes de aplicar |
| `sudo netbird status` | `Management` y `Signal` en `Connected` |
| Desde una IP no admin de la Interna (por ejemplo sw01), SSH a `10.20.10.1` y a `fd5a:fc7e:d716:10::1` | Sin respuesta |
| `sudo journalctl -k \| grep fw-drop` | Las líneas del intento anterior, con `IN=lan0.10` y `DPT=22` en las dos familias |
| Desde sw01, `/ping 1.1.1.1` | Responde (sale por NAT) |
| Desde sw01, `/tool fetch url="http://10.20.20.11:445/" keep-result=no` y con `http://[fd5a:fc7e:d716:20::11]:445/` | Pasa de `connecting` a `requesting` (la conexión TCP se abre; falla después porque smbd no habla HTTP) y sube el contador de la regla del 445 en `forward` |
| Desde sw01, `/tool fetch url="https://10.20.20.11/dhis-web-login/" http-header-field="Host: pacientes.salud.movil" check-certificate=no output=user` y con `[fd5a:fc7e:d716:20::11]` | `status: finished` con el login de DHIS2 |
| Desde la Comunidad (`prueba01`), `nc -zv -w4 10.20.20.11 445` (y `443`) y con `fd5a:fc7e:d716:20::11` | `timed out` y `fw-drop IN=br-com OUT=br-srv ... DPT=445` (o `443`) en el log (P3) |
| Desde sw01, `/tool fetch url="http://10.20.20.12/" http-header-field="Host: biblioteca.salud.movil" output=user` y con `http://[fd5a:fc7e:d716:20::12]/` | `status: finished` con la página de Kiwix |
| Desde sw01, `/tool fetch url="https://10.20.20.12/" http-header-field="Host: registro.salud.movil" check-certificate=no output=user` y con `[fd5a:fc7e:d716:20::12]` | `status: finished` con el formulario de prerregistro |
| Desde la Comunidad (`prueba01`), `curl http://biblioteca.salud.movil/` antes y después de aceptar el portal, con `-4` y `-6` | `302` hacia el portal y después `200` (ver [`../portal/`](../portal/)) |
| `sudo nft list chain inet filtro input \| grep 'dport 514'` | Los contadores de F-15 y F-16 suben con el reenvío de las VMs y los mensajes de sw01 (`observability/rsyslog/`) |
| `sudo nft list table ip nat_kit` | El contador del masquerade sube |
| `systemctl restart nftables` y luego `nft list tables` | Las mismas tablas; las de iptables-nft no se tocan |
| `ansible-playbook playbooks/red-kit01.yml --check --diff` | `changed=0` |

## Diagnóstico

- **El rol falla con `La restauración ... ya actuó`.** El acceso no volvió a tiempo con el cambio y el ruleset volvió a lo anterior. Se revisa el cambio en el laboratorio virtual antes de repetir.
- **El rol se detiene por una restauración pendiente.** Se espera a que actúe (`systemctl list-timers 'fw-rollback-*'`) o, si el acceso funciona, se cancela con `sudo systemctl stop <nombre>.timer`.

- **Algo no responde y no se sabe por qué.** `sudo journalctl -k -f | grep fw-drop` muestra lo que se descarta, con interfaz de entrada y salida, origen, destino y puerto.
- **Se perdieron las reglas de NetBird.** Alguien aplicó un archivo con `flush ruleset` o corrió `nft flush ruleset`. NetBird crea sus reglas al iniciar, así que se recuperan con `sudo systemctl restart netbird`. Ese reinicio corta NetBird unos segundos, así que conviene hacerlo desde una sesión que no dependa de él.
- **Las reglas no cargan al arrancar.** `systemctl status nftables` y `journalctl -u nftables`; el archivo se puede revisar con `sudo nft -c -f /etc/nftables.conf`.
- **El log se llena con broadcasts del uplink o el MNDP de sw01 (`udp/5678`).** Es ruido esperado y el límite de frecuencia lo contiene.
