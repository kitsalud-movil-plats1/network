# 1970-01-01 20:18:30 by RouterOS 7.13.5
# software id = WDCW-PNZP
#
# model = CCR2004-16G-2S+
# serial number = HGA09ZBSP3T
/interface bridge add name=bridge-kit vlan-filtering=yes
/interface ethernet set [ find default-name=ether1 ] name=ether1-kit01
/interface ethernet set [ find default-name=ether2 ] name=ether2-ap01
/interface ethernet set [ find default-name=ether3 ] disabled=yes name=ether3-laptop
/interface ethernet set [ find default-name=ether4 ] name=ether4-interna
/interface ethernet set [ find default-name=ether5 ] name=ether5-interna
/interface ethernet set [ find default-name=ether6 ] name=ether6-interna
/interface ethernet set [ find default-name=ether7 ] name=ether7-interna
/interface ethernet set [ find default-name=ether8 ] name=ether8-interna
/interface ethernet set [ find default-name=ether9 ] disabled=yes
/interface ethernet set [ find default-name=ether10 ] disabled=yes
/interface ethernet set [ find default-name=ether11 ] disabled=yes
/interface ethernet set [ find default-name=ether12 ] disabled=yes
/interface ethernet set [ find default-name=ether13 ] disabled=yes
/interface ethernet set [ find default-name=ether14 ] disabled=yes
/interface ethernet set [ find default-name=ether15 ] disabled=yes
/interface ethernet set [ find default-name=ether16 ] disabled=yes
/interface ethernet set [ find default-name=sfp-sfpplus1 ] disabled=yes
/interface ethernet set [ find default-name=sfp-sfpplus2 ] disabled=yes
/interface vlan add interface=bridge-kit name=vlan10-Interna vlan-id=10
/interface ethernet switch port-isolation set 8 !forwarding-override
/interface ethernet switch port-isolation set 9 !forwarding-override
/interface ethernet switch port-isolation set 10 !forwarding-override
/interface ethernet switch port-isolation set 11 !forwarding-override
/interface ethernet switch port-isolation set 12 !forwarding-override
/interface ethernet switch port-isolation set 13 !forwarding-override
/interface ethernet switch port-isolation set 14 !forwarding-override
/interface ethernet switch port-isolation set 15 !forwarding-override
/interface ethernet switch port-isolation set 17 !forwarding-override
/port set 0 name=serial0
/port set 1 name=serial1
/interface bridge port add bridge=bridge-kit frame-types=admit-only-vlan-tagged interface=ether1-kit01
/interface bridge port add bridge=bridge-kit interface=ether2-ap01 pvid=10
/interface bridge port add bridge=bridge-kit frame-types=admit-only-vlan-tagged interface=ether3-laptop
/interface bridge port add bridge=bridge-kit frame-types=admit-only-untagged-and-priority-tagged interface=ether4-interna pvid=10
/interface bridge port add bridge=bridge-kit frame-types=admit-only-untagged-and-priority-tagged interface=ether5-interna pvid=10
/interface bridge port add bridge=bridge-kit frame-types=admit-only-untagged-and-priority-tagged interface=ether6-interna pvid=10
/interface bridge port add bridge=bridge-kit frame-types=admit-only-untagged-and-priority-tagged interface=ether7-interna pvid=10
/interface bridge port add bridge=bridge-kit frame-types=admit-only-untagged-and-priority-tagged interface=ether8-interna pvid=10
/ip settings set ip-forward=no
/ipv6 settings set accept-router-advertisements=no forward=no
/interface bridge vlan add bridge=bridge-kit tagged=bridge-kit,ether1-kit01,ether2-ap01,ether3-laptop untagged=ether4-interna,ether5-interna,ether6-interna,ether7-interna,ether8-interna vlan-ids=10
/interface bridge vlan add bridge=bridge-kit tagged=ether1-kit01,ether2-ap01 vlan-ids=40
/interface bridge vlan add bridge=bridge-kit tagged=ether1-kit01,ether3-laptop vlan-ids=20
/ip address add address=10.20.10.2/24 interface=vlan10-Interna network=10.20.10.0
/ip route add gateway=10.20.10.1
/ipv6 route add dst-address=::/0 gateway=fe80::1%vlan10-Interna
/ip service set telnet disabled=yes
/ip service set ftp disabled=yes
/ip service set www disabled=yes
/ip service set ssh address=10.20.10.1/32,10.20.10.10/31,10.20.10.12/30,10.20.10.16/29,10.20.10.24/30,10.20.10.28/31
/ip service set api disabled=yes
/ip service set winbox address=10.20.10.1/32,10.20.10.10/31,10.20.10.12/30,10.20.10.16/29,10.20.10.24/30,10.20.10.28/31
/ip service set api-ssl disabled=yes
/ipv6 address add address=fd5a:fc7e:d716:10::2 advertise=no interface=vlan10-Interna
/system clock set time-zone-name=America/Bogota
/system identity set name=sw01
/system ntp client set enabled=yes
/system ntp client servers add address=10.20.20.10
/system note set show-at-login=no
/system routerboard settings set enter-setup-on=delete-key
