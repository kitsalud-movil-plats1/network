# sysctl de kit01

[`60-kit01-router.conf`](60-kit01-router.conf) activa el reenvío IPv4 e IPv6, porque kit01 es el router de las redes internas (D-02). Va en `/etc/sysctl.d/60-kit01-router.conf`.

`enp170s0` ignora los RA del uplink (`accept-ra: false` en [`../netplan/`](../netplan/)), así que kit01 no tiene ruta IPv6 hacia la WAN. Hasta que esté el firewall base (network#4), la cadena `FORWARD` no filtra el tráfico que kit01 reenvía.

## Cómo se aplica

```bash
sudo systemd-run --on-active=120 --unit=sysctl-rollback sh -c 'rm -f /etc/sysctl.d/60-kit01-router.conf; sysctl -w net.ipv6.conf.all.forwarding=0'
sudo install -o root -g root -m 644 60-kit01-router.conf /etc/sysctl.d/60-kit01-router.conf
sudo sysctl -p /etc/sysctl.d/60-kit01-router.conf
# desde una sesión nueva, si el acceso sigue
sudo systemctl stop sysctl-rollback.timer
```

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding` | `1` y `1` |
| `tracepath` entre un equipo de la VLAN 10 y otro de la VLAN 40 (en el laboratorio virtual) | Llega en dos saltos, con kit01 en el primero, en IPv4 e IPv6 |
