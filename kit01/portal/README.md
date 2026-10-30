# Portal cautivo de kit01

La Comunidad acepta las condiciones antes de usar la red, y el portal nunca da acceso a la red Interna, a clinica01 ni a la gestión (R5, D-22, sección 6.4). Todo vive en kit01, así que funciona aunque las VMs estén apagadas.

| Archivo | Dónde queda en kit01 | Qué es |
|---|---|---|
| [`portal.nginx.j2`](portal.nginx.j2) | `/etc/nginx/sites-available/portal` (enlazado en `sites-enabled`) | Sitio de nginx solo en `10.20.40.1:80` y `[fd5a:fc7e:d716:40::1]:80`. Cualquier nombre que no sea `portal.salud.movil` recibe un `302` hacia `http://portal.salud.movil/` |
| [`paginas/`](paginas/) | `/usr/share/kitsalud-portal/` | `condiciones.html` (`/`, con el botón «Acepto»), `inicio.html` (`/inicio`, con los íconos de biblioteca, videos y prerregistro y el enlace a `ca.salud.movil`) y `estilo.css` |
| [`portal.py`](portal.py) | `/usr/local/lib/kitsalud-portal/portal.py` | Servicio `kitsalud-portal` en `127.0.0.1:8081` que atiende el `POST /aceptar` |

Lo instala el rol `kit01_portal` de [`../../ansible/roles/`](../../ansible/roles/). El set, la redirección y los flujos son parte del firewall ([`../nftables/`](../nftables/)). Las variables (`portal_set`, `portal_timeout` y `portal_app`) están en `platform/ansible/inventarios/kit/group_vars/all/portal.yml`.

## Cómo funciona

1. **Cliente nuevo.** Un equipo de la Comunidad (`br-com`) recibe dirección por DHCPv4 y SLAAC y resuelve por BIND9. Mientras su MAC no esté en el set `portal_ok` de `inet filtro`, solo llega a DHCP, DNS y el 80 del portal.
2. **Redirección.** La cadena `portal_redireccion` (`nat`, prerouting) manda a `10.20.40.1` o a `fd5a:fc7e:d716:40::1` todo su HTTP hacia cualquier destino que no sea kit01, y nginx lo lleva a `portal.salud.movil`. El HTTPS se rechaza con RST en `forward`, para que el navegador falle enseguida en lugar de quedarse esperando.
3. **Aceptación.** El formulario hace `POST /aceptar`. nginx lo pasa al servicio con la IP del cliente en `X-Real-IP`. El servicio comprueba que la IP sea de la Comunidad, busca su MAC en la tabla de vecinos de `br-com` (`ip -j neigh`), que vale para IPv4 y para IPv6, y la agrega al set con `destroy element` y `add element`. Si ya estaba, el plazo empieza de nuevo. Responde `303` hacia `/inicio`.
4. **Ya autorizado.** Con la MAC en el set llega a comunidad01 por el 80 y el 443 en IPv4 e IPv6 (F-09) y, si hay Internet, sale por IPv4 con NAT (F-10). IPv6 no sale a Internet, porque la red es ULA. Nunca llega a la Interna, a clinica01 ni al SSH o el monitoreo de kit01.
5. **Vencimiento.** El set tiene `timeout 8h`, así que cada MAC sale sola a las 8 horas y el cliente vuelve a ver el portal. Las conexiones que ya estaban abiertas siguen hasta cerrarse.

**Falla cerrada.** Sin el servicio, nadie nuevo queda autorizado, y sin el set (o con el set vacío) nadie de la Comunidad pasa de kit01. Las autorizaciones no sobreviven a un reinicio de kit01, porque el set arranca vacío; hay que volver a aceptar.

**Servicio.** Solo usa la biblioteca estándar de Python, así que funciona sin Internet (R-05). Corre con `DynamicUser`, solo con `CAP_NET_ADMIN` (para `nft`), `ProtectSystem=strict` y sin acceso a `/home`. La MAC sale de la tabla de vecinos del kernel y nunca de lo que mande el cliente. Cada autorización queda en el journal (`autorizada <MAC> desde <IP>`), y también los rechazos.

**Aplicar el firewall.** `kit01_firewall` ignora el contenido del set al comparar (`nft -t`) y, cuando tiene que aplicar, vuelve a agregar cada MAC con el tiempo que le quedaba, en el mismo comando que recrea la tabla. Así aplicar el firewall no desconecta a la Comunidad.

## Cómo se despliega

Desde `platform/ansible/`:

```bash
ansible-playbook playbooks/red-kit01.yml --check --diff   # el set, la redirección y los flujos (kit01_firewall)
ansible-playbook playbooks/red-kit01.yml
ansible-playbook playbooks/portal.yml                     # nginx (rol nginx), páginas y servicio (rol kit01_portal)
```

Una segunda ejecución de los dos termina con `changed=0`, aunque haya MAC autorizadas.

## Cómo se verifica

Desde `prueba01` (D-24), que se enciende con `ansible-playbook playbooks/prueba01.yml`, y en IPv4 e IPv6.

| Prueba | Sin aceptar | Después de `curl -X POST http://portal.salud.movil/aceptar` |
|---|---|---|
| `curl -4` y `curl -6 http://biblioteca.salud.movil/` | `302` hacia `http://portal.salud.movil/` | `200` |
| `curl -4` y `curl -6 -k https://registro.salud.movil/` | Conexión rechazada al instante (`curl` sale con `7`) | `200` |
| `curl http://1.1.1.1/` | `302` hacia el portal | Respuesta del sitio (con Internet) |
| `curl -4 https://ubuntu.com/` | Rechazada | `200` (con Internet) |
| `curl -6` hacia una dirección de Internet | Sin respuesta | Sin respuesta (la red es ULA) |
| TCP a `10.20.20.11:443` y `:445`, y a `fd5a:fc7e:d716:20::11` | Bloqueado | Bloqueado |
| TCP al 22 de `10.20.40.1` y `fd5a:fc7e:d716:40::1` | Bloqueado | Bloqueado |
| `curl http://portal.salud.movil/` | Página de condiciones | Página de condiciones (aceptar renueva las 8 h) |

En kit01:

| Comando | Resultado esperado |
|---|---|
| `sudo nft list set inet filtro portal_ok` | `timeout 8h` y la MAC del cliente con `expires` de unas 8 h |
| `sudo journalctl -u kitsalud-portal` | `autorizada 52:54:00:40:00:50 desde ...` |
| `sudo ss -tlnp \| grep -E ':80 \|:8081 '` | nginx solo en `10.20.40.1:80` y `[fd5a:fc7e:d716:40::1]:80`; el servicio en `127.0.0.1:8081` |
| `sudo nft list chain inet filtro portal_redireccion` | Los contadores de `dnat` suben con el HTTP de los clientes sin aceptar |
| Sonda `portal` en Prometheus (`probe_success{servicio="portal"}`) | `1` en `ipv4` y en `ipv6`; aparece en **Estado del kit** como «Portal de la Comunidad» |

**Vencimiento sin esperar 8 horas.** `sudo nft "destroy element inet filtro portal_ok { <MAC> }; add element inet filtro portal_ok { <MAC> timeout 60s }"`. Al minuto la MAC ya no está y el cliente vuelve al portal.

## Diagnóstico

- **El cliente no ve el portal.** Desde el cliente, `curl -v http://1.1.1.1/` tiene que dar `302`. Si no responde, revisar que tenga dirección de la Comunidad y que nginx escuche (`ss -tlnp`). Los sistemas que solo prueban por HTTPS no ven el portal; se abre a mano `http://portal.salud.movil`. Sin Internet, el sistema operativo puede no abrir el portal solo; se abre en el navegador una dirección local por HTTP, como `http://biblioteca.salud.movil`, y la redirección lleva al portal.
- **«No se encontró su equipo» (`409`).** La IP del cliente no está en la tabla de vecinos de `br-com` (`ip neigh show dev br-com`). Pasa si el cliente cambió de dirección; se recarga la página y se acepta otra vez.
- **«No se pudo dar acceso» (`500`).** `journalctl -u kitsalud-portal` muestra el error de `nft`. Lo más común es que el set no exista porque el firewall no está cargado (`sudo nft list set inet filtro portal_ok`).
- **Aceptó pero no llega a comunidad01.** `sudo nft list set inet filtro portal_ok` tiene que mostrar su MAC. Si está, revisar `journalctl -k | grep fw-drop` con `IN=br-com`.
- **Después de un reinicio nadie tiene acceso.** Es lo esperado, porque el set arranca vacío. Cada cliente acepta otra vez.
