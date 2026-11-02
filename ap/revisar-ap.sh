#!/usr/bin/env bash
# Revisa la configuración de ap01 leyendo su página de gestión, sin cambiar nada.
# Desde la máquina de control (con el Ansible del kit en ../../platform/ansible)
# se copia a kit01 y se ejecuta allí con la clave del vault, que no se imprime:
#   ./revisar-ap.sh
# En kit01 se puede ejecutar directamente con la clave en AP_CLAVE.
# Solo pide páginas (nunca Save) y al final cierra la sesión.
set -u
AP=http://10.20.10.3

if [ -z "${AP_CLAVE:-}" ]; then
  ESTE=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
  cd "${ANSIBLE_DIR:-$(dirname "$ESTE")/../../platform/ansible}" || exit 2
  # Sin esto Ansible escribe el comando, con la clave, en el syslog de kit01
  export ANSIBLE_NO_TARGET_SYSLOG=True
  ansible kit01 -m copy -a "src=$ESTE dest=/tmp/revisar-ap.sh mode=0700" >/dev/null || exit 2
  ansible kit01 -m shell -a "AP_CLAVE='{{ vault_ap01_password }}' /tmp/revisar-ap.sh; e=\$?; rm -f /tmp/revisar-ap.sh; exit \$e" 2>&1 | sed '1{/ | /d;}'
  exit "${PIPESTATUS[0]}"
fi

D=$(mktemp -d)
trap 'rm -rf "$D"' EXIT
BIEN=0
MAL=0

# La página de inicio de sesión pide una cookie con el usuario y el md5 de la
# clave; responde con una ruta de sesión. A veces el primer intento después de
# cerrar otra sesión devuelve el inicio, así que se intenta hasta tres veces
COOKIE="Authorization=Basic%20$(printf 'admin:%s' "$(printf %s "$AP_CLAVE" | md5sum | cut -d' ' -f1)" | base64 -w0)"
for i in 1 2 3; do
  SES=$(curl -s -m 10 -b "$COOKIE" -e "$AP/" "$AP/userRpm/LoginRpm.htm?Save=Save" |
    grep -oE '10\.20\.10\.3/[A-Z]{16}/userRpm' | head -1 | cut -d/ -f2)
  [ -n "$SES" ] && break
  sleep 3
done
[ -n "$SES" ] || { echo "No se pudo iniciar sesión en $AP"; exit 1; }
BASE="$AP/$SES/userRpm"
pagina() { curl -s -m 10 -b "$COOKIE" -e "$1" "$BASE/$2.htm" -o "$D/$2.htm"; }
pagina "$AP/userRpm/LoginRpm.htm?Save=Save" Index
for p in StatusRpm WlanNetworkRpm WlanAdvRpm LanDhcpServerRpm WpsCfgRpm SnmpRpm NetworkCfgRpm; do
  pagina "$BASE/Index.htm" $p
done
curl -s -m 10 -b "$COOKIE" -e "$BASE/Index.htm" "$BASE/LogoutRpm.htm" -o /dev/null

# Elemento de un arreglo de JavaScript de una página: valor <página> <arreglo> <índice>
valor() {
  python3 - "$D/$1.htm" "$2" "$3" <<'FIN'
import csv, re, sys
html = open(sys.argv[1], encoding="latin-1").read()
m = re.search(r"var %s = new Array\((.*?)\);" % sys.argv[2], html, re.S)
if m:
    campos = next(csv.reader([" ".join(m.group(1).split())], skipinitialspace=True))
    print(campos[int(sys.argv[3])].strip())
FIN
}

comprobar() {  # comprobar "descripción" esperado obtenido
  if [ "$2" = "$3" ]; then echo "  [ OK ]  $1 ($3)"; BIEN=$((BIEN + 1)); else echo "  [FALLA] $1 (esperado $2, obtenido ${3:-nada})"; MAL=$((MAL + 1)); fi
}
si_no() { [ "$1" = 1 ] && echo sí || echo no; }

echo "== ap01 ($AP), $(date '+%Y-%m-%d %H:%M:%S %z')"
echo "    Firmware $(valor StatusRpm statusPara 5), hardware $(valor StatusRpm statusPara 6 | cut -d' ' -f1-2)"
echo
echo "## Wi-Fi"
comprobar "Modo Multi-SSID" sí "$(si_no "$(valor WlanNetworkRpm wlanPara 15)")"
comprobar "VLAN por SSID activada" sí "$(si_no "$(valor WlanNetworkRpm vlanPara 0)")"
comprobar "SSID1" SaludMovil-Clinica "$(valor WlanNetworkRpm wlanPara 3)"
comprobar "VLAN del SSID1" 10 "$(valor WlanNetworkRpm vlanPara 1)"
comprobar "SSID2" SaludMovil-Comunidad "$(valor WlanNetworkRpm wlanPara 16)"
comprobar "VLAN del SSID2" 40 "$(valor WlanNetworkRpm vlanPara 2)"
comprobar "SSID2 activo" sí "$(si_no "$(valor WlanNetworkRpm wlanPara 19)")"
comprobar "SSID3 activo" no "$(si_no "$(valor WlanNetworkRpm wlanPara 20)")"
comprobar "SSID4 activo" no "$(si_no "$(valor WlanNetworkRpm wlanPara 21)")"
comprobar "Aislamiento de clientes (AP Isolation)" sí "$(si_no "$(valor WlanAdvRpm wlanAdv 7)")"
echo
echo "## Servicios del AP"
comprobar "Servidor DHCP activo" no "$(si_no "$(valor LanDhcpServerRpm DHCPPara 0)")"
comprobar "WPS activo" no "$(si_no "$(valor WpsCfgRpm wpsInf 0)")"
comprobar "SNMP activo" no "$(si_no "$(valor SnmpRpm snmpParam 0)")"
echo
echo "## Gestión"
comprobar "Dirección IP fija" sí "$([ "$(valor NetworkCfgRpm lanPara 4)" = 0 ] && echo sí || echo no)"
comprobar "Dirección" 10.20.10.3 "$(valor NetworkCfgRpm lanPara 1)"
comprobar "Gateway" 10.20.10.1 "$(valor NetworkCfgRpm lanPara 5)"
comprobar "Acceso remoto (Allow remote access)" no "$([ "$(valor NetworkCfgRpm lanPara 9)" = 0 ] && echo sí || echo no)"
echo
echo "Resultado: $BIEN bien y $MAL con falla. Sesión cerrada."
[ "$MAL" -eq 0 ]
