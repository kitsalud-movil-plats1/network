#!/usr/bin/env python3
"""Servicio de aceptación del portal cautivo de kit01 (R5, D-22, sección 6.4).

nginx le pasa el POST /aceptar con la IP del cliente en X-Real-IP. El servicio
busca la MAC de esa IP en la tabla de vecinos de la interfaz de la Comunidad y
la agrega al set de nftables, que la deja autorizada por su timeout (8 h). Si
ya estaba, la vuelve a agregar y el plazo empieza de nuevo. La MAC sale del
kernel, nunca de lo que mande el cliente.

nginx también le pasa el GET /, y el servicio contesta con X-Accel-Redirect qué
página mostrar. El menú de servicios si la MAC ya está en el set y las
condiciones si no, así portal.salud.movil sirve para volver al menú.

GET /estado responde el estado de los servicios que usa la comunidad, a partir de
las sondas de Prometheus. No dice direcciones ni nombres internos, y guarda la
respuesta unos segundos para que los clientes no lleguen hasta Prometheus.

Solo usa la biblioteca estándar, así que funciona sin Internet (R-05).
"""
import ipaddress
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ESCUCHA = os.environ.get("PORTAL_ESCUCHA", "127.0.0.1:8081")
INTERFAZ = os.environ.get("PORTAL_INTERFAZ", "br-com")
SET = os.environ.get("PORTAL_SET", "inet filtro portal_ok")
REDES = [ipaddress.ip_network(r) for r in os.environ.get("PORTAL_REDES", "").split()]
INICIO = os.environ.get("PORTAL_INICIO", "/inicio")
PAGINA_INICIO = os.environ.get("PORTAL_PAGINA_INICIO", "/inicio.html")
PAGINA_CONDICIONES = os.environ.get("PORTAL_PAGINA_CONDICIONES", "/condiciones.html")
PROMETHEUS = os.environ.get("PORTAL_PROMETHEUS", "127.0.0.1:9090")
# servicio de las sondas=nombre para la comunidad, separados por punto y coma
SERVICIOS = [par.split("=", 1) for par in os.environ.get("PORTAL_SERVICIOS", "").split(";") if par]
VIGENCIA_S = 15

_estado = {"hasta": 0, "datos": None}
_candado = threading.Lock()


def registrar(mensaje):
    print(mensaje, file=sys.stderr, flush=True)


def mac_de(ip):
    """MAC de la IP en la tabla de vecinos de la Comunidad, o None."""
    salida = subprocess.run(
        ["ip", "-j", "neigh", "show", "to", str(ip), "dev", INTERFAZ],
        capture_output=True, text=True, check=False,
    ).stdout
    for vecino in json.loads(salida or "[]"):
        if vecino.get("lladdr") and "FAILED" not in vecino.get("state", []):
            return vecino["lladdr"]
    return None


def autorizar(mac):
    elemento = "{ %s }" % mac
    familia, tabla, nombre = SET.split()
    orden = "destroy element %s %s %s %s; add element %s %s %s %s" % (
        familia, tabla, nombre, elemento, familia, tabla, nombre, elemento)
    return subprocess.run(["nft", orden], capture_output=True, text=True, check=False)


def autorizada(mac):
    familia, tabla, nombre = SET.split()
    orden = "get element %s %s %s { %s }" % (familia, tabla, nombre, mac)
    return subprocess.run(["nft", orden], capture_output=True, text=True, check=False).returncode == 0


def color(valores):
    """Verde si todas las sondas responden, rojo si ninguna y amarillo si algunas."""
    if not valores:
        return "desconocido"
    if all(valores):
        return "verde"
    return "amarillo" if any(valores) else "rojo"


def consultar_sondas():
    nombres = "|".join(clave for clave, _ in SERVICIOS)
    consulta = urllib.parse.urlencode({"query": 'probe_success{servicio=~"%s"}' % nombres})
    with urllib.request.urlopen("http://%s/api/v1/query?%s" % (PROMETHEUS, consulta), timeout=2) as r:
        resultado = json.load(r)["data"]["result"]
    sondas = {clave: [] for clave, _ in SERVICIOS}
    for sonda in resultado:
        sondas[sonda["metric"]["servicio"]].append(sonda["value"][1] == "1")
    return sondas


def estado_servicios():
    with _candado:
        ahora = time.monotonic()
        if ahora < _estado["hasta"]:
            return _estado["datos"]
        try:
            sondas = consultar_sondas()
        except (OSError, ValueError, KeyError) as error:
            registrar("sin estado de los servicios: %s" % error)
            sondas = {}
        servicios = [{"nombre": nombre, "estado": color(sondas.get(clave))} for clave, nombre in SERVICIOS]
        _estado.update(hasta=ahora + VIGENCIA_S, datos={"servicios": servicios})
        return _estado["datos"]


class Portal(BaseHTTPRequestHandler):
    server_version = "portal"
    sys_version = ""

    def responder(self, codigo, texto, ubicacion=None):
        cuerpo = texto.encode()
        self.send_response(codigo)
        if ubicacion:
            self.send_header("Location", ubicacion)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def responder_json(self, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path == "/estado":
            return self.responder_json(estado_servicios())
        if self.path != "/":
            return self.responder(404, "No existe")
        pagina = PAGINA_CONDICIONES
        try:
            ip = ipaddress.ip_address(self.headers.get("X-Real-IP", ""))
        except ValueError:
            ip = None
        if ip and any(ip in red for red in REDES):
            mac = mac_de(ip)
            if mac and autorizada(mac):
                pagina = PAGINA_INICIO
        self.send_response(200)
        self.send_header("X-Accel-Redirect", pagina)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if self.path != "/aceptar":
            return self.responder(404, "No existe")
        try:
            ip = ipaddress.ip_address(self.headers.get("X-Real-IP", ""))
        except ValueError:
            return self.responder(400, "Sin dirección del cliente")
        if not any(ip in red for red in REDES):
            registrar("rechazada: %s no es de la Comunidad" % ip)
            return self.responder(403, "El portal es solo para la red de la Comunidad")
        mac = mac_de(ip)
        if not mac:
            registrar("rechazada: sin MAC para %s" % ip)
            return self.responder(409, "No se encontró su equipo. Vuelva a intentarlo")
        resultado = autorizar(mac)
        if resultado.returncode != 0:
            registrar("error al autorizar %s (%s): %s" % (mac, ip, resultado.stderr.strip()))
            return self.responder(500, "No se pudo dar acceso. Avise al personal")
        registrar("autorizada %s desde %s" % (mac, ip))
        return self.responder(303, "Acceso concedido", INICIO)

    def log_message(self, formato, *args):
        pass


if __name__ == "__main__":
    host, puerto = ESCUCHA.rsplit(":", 1)
    registrar("portal escuchando en %s, set %s, interfaz %s" % (ESCUCHA, SET, INTERFAZ))
    ThreadingHTTPServer((host, int(puerto)), Portal).serve_forever()
