# sysctl de kit01

[`60-kit01-router.conf`](60-kit01-router.conf) activa el reenvío IPv4 e IPv6, porque kit01 es el router de las redes internas (D-02). Va en `/etc/sysctl.d/60-kit01-router.conf`.

`enp170s0` ignora los RA del uplink (`accept-ra: false` en [`../netplan/`](../netplan/)), así que kit01 no tiene ruta IPv6 hacia la WAN. El tráfico que reenvía lo filtra la cadena `forward` de [`../nftables/`](../nftables/).

## Cómo se aplica

Con el rol `kit01_red` (`playbooks/red-kit01.yml` en `platform/ansible/`, ver [`../netplan/`](../netplan/)), que copia el archivo tal cual y, si cambió, lo carga con `sysctl --load`. Cargarlo no baja ningún enlace.

## Cómo se verifica

| Comando | Resultado esperado |
|---|---|
| `sysctl net.ipv4.ip_forward net.ipv6.conf.all.forwarding` | `1` y `1` |
| `tracepath` entre un equipo de la VLAN 10 y otro de la VLAN 40 (en el laboratorio virtual) | Llega en dos saltos, con kit01 en el primero, en IPv4 e IPv6 |
