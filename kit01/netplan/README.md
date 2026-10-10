# Netplan de kit01

**Estado (2026-10-09), provisional.** [`50-cloud-init.yaml`](50-cloud-init.yaml) es el netplan que tiene hoy kit01 (respaldo del anterior en `/root/netplan-respaldo/` del equipo).

| Interfaz | Uso | Direcciones |
|---|---|---|
| `enp170s0` (MAC `78:55:36:09:07:0b`, rol `wan0`) | Uplink del laboratorio | `192.168.160.69/24` fija, gateway `192.168.160.1`, DNS `192.168.215.20` y `.30` |
| `enp171s0` (MAC `78:55:36:09:07:0a`, rol `lan0`) | Trunk hacia ether1 de sw01 | Sin dirección propia |
| `lan0.10` (VLAN 10 sobre `enp171s0`) | Red Interna y gestión | `10.20.10.1/24`, `fd5a:fc7e:d716:10::1/64`, `fe80::1/64` |

Se verificó con `ping` a sw01 (`10.20.10.2` y `fd5a:fc7e:d716:10::2`) y al AP (`10.20.10.3`) sin pérdida.

## Pendiente (`network#3` y `platform#2`)

- `br-com` (Comunidad, con `lan0.40` como puerto), `br-srv` y reenvío IPv4/IPv6.
- `accept_ra=2` en `enp170s0` por sysctl, para que siga tomando la dirección IPv6 del laboratorio (`2001:db8:a:c::/64`) al activar el reenvío. nftables no reenvía IPv6 hacia la WAN.
- Las interfaces no se renombran y `enp170s0` no se modifica (D-14, D-23). Los cambios se aplican con `netplan generate` y `networkctl reload`, con restauración programada (`AGENTS.md`, sección 6).
