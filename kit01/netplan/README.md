# Netplan de kit01

**Estado (2026-10-09): provisional.** [`50-cloud-init.yaml`](50-cloud-init.yaml) es el netplan que tiene hoy kit01 (respaldo del anterior en `/root/netplan-respaldo/` del equipo).

| Interfaz | Uso | Direcciones |
|---|---|---|
| `enp170s0` (MAC `78:55:36:09:07:0b`, futuro `wan0`) | Uplink del laboratorio | `192.168.160.69/24` fija, gateway `192.168.160.1`, DNS `192.168.215.20` y `.30` |
| `enp171s0` (MAC `78:55:36:09:07:0a`, futuro `lan0`) | Trunk hacia ether1 de sw01 | Sin dirección propia |
| `lan0.10` (VLAN 10 sobre `enp171s0`) | Red Interna y gestión | `10.20.10.1/24`, `fd5a:fc7e:d716:10::1/64`, `fe80::1/64` |

Verificado: `ping` a sw01 (`10.20.10.2` y `fd5a:fc7e:d716:10::2`) y al AP (`10.20.10.3`) sin pérdida.

## Pendiente (`network#3` y `platform#2`)

- Fijar los nombres por MAC (`wan0`, `lan0`); requiere reiniciar.
- `wan0` sin aceptar RA: hoy `enp170s0` toma una dirección del prefijo IPv6 que anuncia el laboratorio (`2001:db8:a:c::/64`).
- `lan0.40`, `br-srv` y reenvío IPv4/IPv6.
