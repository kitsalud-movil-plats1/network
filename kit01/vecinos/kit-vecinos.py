#!/usr/bin/env python3
"""Aprende las direcciones IPv6 de los clientes Wi-Fi a partir de su tráfico.

ap01 no entrega a los clientes las solicitudes de vecino multicast
(ff02::1:ffXX:XXXX), así que kit01 no puede resolver la dirección de un cliente
para responderle. Cada paquete que entra trae la pareja de dirección y MAC del
cliente, y con ella se carga la tabla de vecinos. Después el kernel comprueba el
vecino con solicitudes unicast, que sí llegan.

Uso: kit-vecinos.py <puerto>=<interfaz>=<prefijo/64> [...]
     kit-vecinos.py lan0.40=br-com=fd5a:fc7e:d716:40::/64
"""
import ctypes
import ipaddress
import select
import socket
import struct
import subprocess
import sys
import time

ETH_P_ALL = 0x0003
ETH_P_IPV6 = 0x86DD
SO_ATTACH_FILTER = 26
PACKET_OUTGOING = 4
SKF_AD_PKTTYPE = 0xFFFFF000 + 4
REFRESCO_S = 30


def filtro_bpf(prefijo):
    """Solo paquetes que entran con origen en el prefijo, para no despertar en cada trama."""
    alto = prefijo.network_address.packed
    a = struct.unpack("!I", alto[:4])[0]
    b = struct.unpack("!I", alto[4:8])[0]
    # (código, salto si cierto, salto si falso, operando)
    programa = [
        (0x28, 0, 0, 12),              # ldh tipo de trama
        (0x15, 0, 7, ETH_P_IPV6),      # jeq IPv6, si no descarta
        (0x20, 0, 0, 22),              # ldw origen[0:4]
        (0x15, 0, 5, a),               # jeq a, si no descarta
        (0x20, 0, 0, 26),              # ldw origen[4:8]
        (0x15, 0, 3, b),               # jeq b, si no descarta
        (0x28, 0, 0, SKF_AD_PKTTYPE),  # ldh tipo de paquete
        (0x15, 1, 0, PACKET_OUTGOING), # jeq saliente, descarta
        (0x06, 0, 0, 86),              # ret, encabezados
        (0x06, 0, 0, 0),               # ret 0, descarta
    ]
    return b"".join(struct.pack("HBBI", *i) for i in programa), len(programa)


def abrir(puerto, prefijo):
    # ETH_P_ALL porque en un puerto de bridge los sockets ligados a un protocolo no reciben
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
    s.bind((puerto, ETH_P_ALL))
    codigo, largo = filtro_bpf(prefijo)
    area = ctypes.create_string_buffer(codigo)
    fprog = struct.pack("HL", largo, ctypes.addressof(area))
    s.setsockopt(socket.SOL_SOCKET, SO_ATTACH_FILTER, fprog)
    return s


def aprender(ip6, mac, interfaz):
    r = subprocess.run(
        ["ip", "-6", "neigh", "replace", ip6, "lladdr", mac, "dev", interfaz, "nud", "stale"],
        capture_output=True, text=True, timeout=5,
    )
    if r.returncode:
        print(f"error {ip6} {mac} {interfaz}: {r.stderr.strip()}", flush=True)
    else:
        print(f"aprendido {ip6} {mac} {interfaz}", flush=True)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    por_socket = {}
    for arg in sys.argv[1:]:
        puerto, interfaz, prefijo = arg.split("=")
        red = ipaddress.ip_network(prefijo)
        s = abrir(puerto, red)
        por_socket[s] = (interfaz, red)
    vistos = {}
    while True:
        listos, _, _ = select.select(list(por_socket), [], [])
        ahora = time.monotonic()
        for s in listos:
            trama, dir_ = s.recvfrom(128)
            if dir_[2] == PACKET_OUTGOING or len(trama) < 54:
                continue
            interfaz, red = por_socket[s]
            mac_b, ip_b = trama[6:12], trama[22:38]
            if mac_b[0] & 1:
                continue
            ip6 = ipaddress.IPv6Address(ip_b)
            if ip6 not in red or int(ip6) & 0xFFFFFFFFFFFFFFFF < 0x100:
                continue
            clave = (interfaz, ip_b, mac_b)
            if ahora - vistos.get(clave, -REFRESCO_S) < REFRESCO_S:
                continue
            vistos[clave] = ahora
            if len(vistos) > 4096:
                vistos.clear()
            aprender(str(ip6), mac_b.hex(":"), interfaz)


if __name__ == "__main__":
    main()
