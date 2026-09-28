# network

Configuración de red del kit: **OPNsense** (fw01), **switch** (sw01) y **AP** (ap01).

| Ruta | Contenido |
|---|---|
| `opnsense/` | `config.xml` exportado y **saneado** (sin hashes ni llaves), alias, reglas v4/v6, portal cautivo |
| `switch/` | Running-config del switch (VLAN 10/20/30/40/900/999, trunks, RA Guard) |
| `ap/` | Configuración de SSID ↔ VLAN (Clínica → 30, Comunidad → 40; sin SSID de gestión) |

Referencia de diseño: `docs/arquitectura/00-punto-de-partida.md` (secciones 5, 7, 8 y 11).
