# Vecinos IPv6 de los clientes Wi-Fi

`kit-vecinos.py` aprende en kit01 las direcciones IPv6 de los clientes a partir de su tráfico. Lo instala el rol `kit01_vecinos` con `playbooks/vecinos.yml`.

## Por qué existe

Para responderle a un cliente, kit01 resuelve su dirección con una solicitud de vecino multicast (`ff02::1:ffXX:XXXX`). Los clientes del Wi-Fi no responden esas solicitudes, aunque sw01 las entrega al AP, y sí responden las unicast. Sin este servicio, un cliente no recibe respuestas por IPv6 hasta que habla directo con una dirección de su red. `prueba01` no tiene el problema porque está conectada a `br-com` sin pasar por el AP.

## Qué hace

Lee los encabezados de las tramas IPv6 que entran por `lan0.10` y `lan0.40`, con un filtro BPF que solo deja pasar el prefijo de cada red. Con la dirección y la MAC de origen agrega el vecino en estado `STALE`, y el kernel lo comprueba después con solicitudes unicast. Repite cada 30 s por cliente. Corre sin usuario fijo y solo con `CAP_NET_RAW` y `CAP_NET_ADMIN`.

Un cliente puede declarar una dirección de su propio prefijo, igual que con una respuesta de vecino normal. Las direcciones de infraestructura (la parte de host menor que `0x100`) se ignoran.

## Cómo se verifica

```bash
systemctl is-active kit-vecinos
journalctl -u kit-vecinos -n 20 -o cat      # aprendido <ip6> <mac> <interfaz>
ip -6 neigh show dev br-com                 # la dirección global en REACHABLE o STALE
```

Desde un cliente Wi-Fi recién conectado, `P02-dns.sh` y `P10-firewall-ipv6.sh` deben pasar a la primera.

## Cómo se diagnostica

Si un cliente sigue sin respuestas por IPv6, se revisa si aparece en el journal. Si no aparece, `tcpdump -ni lan0.40 ip6` muestra si su tráfico llega a kit01. Una entrada `FAILED` en `ip -6 neigh` indica que el kernel no pudo comprobarlo, y que el cliente ya no usa esa dirección o no responde.
