# Firewall de kit01 (nftables)

Firewall base de kit01 (D-02, secciones 6.3, 8.4 y 11 del documento). Una sola tabla `inet filtro` filtra IPv4 e IPv6, y el NAT de salida va aparte en `ip nat_kit`.

| Archivo | Dónde va en kit01 | Qué hace |
|---|---|---|
| [`nftables.conf`](nftables.conf) | `/etc/nftables.conf` (`755`) | Tablas `inet filtro` e `ip nat_kit`. Los nombres de interfaz y las direcciones están en `define` al principio |
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
| F-03 | Interna, Comunidad y `br-srv` | DNS (`53` tcp/udp) y NTP (`udp/123`) hacia `10.20.20.10` y `fd5a:fc7e:d716:20::10` |
| F-01, F-21 | Admin (`10.20.10.10-29` en la Interna) y `wt0` | SSH (22) y monitoreo (443) |
| - | `enp170s0` | WireGuard de NetBird (`udp/51820`) |

**Reenvío (`forward`, política drop).** Conexiones establecidas, errores ICMPv6 en tránsito (F-19), la Interna hacia `enp170s0` solo por IPv4 (F-24) y las VMs (`10.20.20.11` y `.12`) hacia `enp170s0` por 80 y 443, solo IPv4 (F-17), todo con masquerade de `10.20.0.0/16` en `ip nat_kit`. Las VMs resuelven por BIND9 en kit01 (`10.20.20.10`), así que no necesitan salir por el 53. Los demás flujos de la sección 11 se agregan en la matriz de flujos (network#10) y el portal en network#8.

**Salida de kit01 (`output`).** Sin filtrar en esta base. La restricción de F-18 va en la matriz de flujos.

**Registro.** Lo que no se acepta en `input` y `forward` se registra en el kernel con el prefijo `fw-drop ` (como máximo 10 por segundo, ráfagas de 50) y se descarta.

El SSH por IPv6 desde la Interna queda bloqueado para todos, porque las estaciones admin solo tienen IP fija en IPv4. El SSH desde la WAN también queda bloqueado. Si NetBird no estuviera disponible, en el sitio se entra con una laptop en un puerto de la Interna con IP fija entre `10.20.10.10` y `10.20.10.29`.

## Cómo se aplica

Se prueba antes en el laboratorio virtual, cambiando `if_wan` a `wan0` e `if_netbird` a `wan0` (la máquina anfitriona hace de NetBird). En kit01, con restauración programada (D-23, `AGENTS.md` sección 6) y una segunda sesión abierta.

```bash
sudo mkdir -p /etc/nftables
sudo install -m 644 quitar.nft /etc/nftables/quitar.nft
sudo nft -c -f nftables.conf
sudo systemd-run --on-active=120 --unit=fw-rollback nft -f /etc/nftables/quitar.nft
sudo nft -f nftables.conf
# desde una sesión nueva, si el acceso sigue
sudo systemctl stop fw-rollback.timer

# persistencia
sudo install -m 755 nftables.conf /etc/nftables.conf
sudo install -D -m 644 nftables.service.d/kit01.conf /etc/systemd/system/nftables.service.d/kit01.conf
sudo systemctl daemon-reload
sudo systemctl enable --now nftables
```

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `sudo nft list tables` | Las tablas de iptables-nft más `inet filtro` e `ip nat_kit` |
| `sudo iptables-save \| grep -c NETBIRD` | El mismo número que antes de aplicar |
| `sudo netbird status` | `Management` y `Signal` en `Connected` |
| Desde una IP no admin de la Interna (por ejemplo sw01), SSH a `10.20.10.1` y a `fd5a:fc7e:d716:10::1` | Sin respuesta |
| `sudo journalctl -k \| grep fw-drop` | Las líneas del intento anterior, con `IN=lan0.10` y `DPT=22` en las dos familias |
| Desde sw01, `/ping 1.1.1.1` | Responde (sale por NAT) |
| `sudo nft list table ip nat_kit` | El contador del masquerade sube |
| `systemctl restart nftables` y luego `nft list tables` | Las mismas tablas; las de iptables-nft no se tocan |

## Diagnóstico

- **Algo no responde y no se sabe por qué.** `sudo journalctl -k -f | grep fw-drop` muestra lo que se descarta, con interfaz de entrada y salida, origen, destino y puerto.
- **Se perdieron las reglas de NetBird.** Alguien aplicó un archivo con `flush ruleset` o corrió `nft flush ruleset`. NetBird crea sus reglas al iniciar, así que se recuperan con `sudo systemctl restart netbird`. Ese reinicio corta NetBird unos segundos, así que conviene hacerlo desde una sesión que no dependa de él.
- **Las reglas no cargan al arrancar.** `systemctl status nftables` y `journalctl -u nftables`; el archivo se puede revisar con `sudo nft -c -f /etc/nftables.conf`.
- **El log se llena con broadcasts del uplink o el MNDP de sw01 (`udp/5678`).** Es ruido esperado y el límite de frecuencia lo contiene.
