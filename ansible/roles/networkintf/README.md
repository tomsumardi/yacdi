network_interface
=================

_WARNING: This role can be dangerous to use. If you lose network connectivity
to your target host by incorrectly configuring your networking, you may be
unable to recover without physical access to the machine._

This roles enables users to configure various network components on target
machines. The role can be used to configure:

- Ethernet interfaces
- Bridge interfaces
- Bonded interfaces
- Network routes

Requirements
------------

This role requires Ansible 1.4 or higher, and platform requirements are listed
in the metadata file.

Role Variables
--------------

The variables that can be passed to this role and a brief description about
them are as follows:

    # The list of ethernet interfaces to be added to the system
    ServerConfiguration_Interface_Ether: []

    # The list of bridge interfaces to be added to the system
    network_bridge_interfaces: []

    # The list of bonded interfaces to be added to the system
    ServerConfiguration_Interface_Bond: []

Note: The values for the list are listed in the examples below.

Examples
--------

1) Configure eth1 and eth2 on a host with a static IP and a dhcp IP. Also
define static routes and a GwAddress.

    - hosts: myhost
      roles:
        - role: network
          ServerConfiguration_Interface_Ether:
           - NetworkName: eth1
             Bootproto: static
             IPAddress: 192.168.10.18
             netmask: 255.255.255.0
             GwAddress: 192.168.10.1
             route:
              - network: 192.168.200.0
                netmask: 255.255.255.0
                GwAddress: 192.168.10.1
              - network: 192.168.100.0
                netmask: 255.255.255.0
                GwAddress: 192.168.10.1
           - NetworkName: eth2
             Bootproto: dhcp

2) Configure a bridge interface with multiple NIcs added to the bridge.

    - hosts: myhost
      roles:
        - role: network
          network_bridge_interfaces:
           -  NetworkName: br1
              type: bridge
              IPAddress: 192.168.10.10
              netmask: 255.255.255.0
              Bootproto: static
              stp: "on"
              ports: [eth1, eth2]

Note: Routes can also be added for this interface in the same way routes are
added for ethernet interfaces.

3) Configure a bond interface with an "active-backup" slave configuration.

    - hosts: myhost
      roles:
        - role: network
          ServerConfiguration_Interface_Bond:
            - NetworkName: bond0
              IPAddress: 192.168.10.128
              netmask: 255.255.255.0
              Bootproto: static
              BondType: active-backup
              Bond_miimon: 100
              BondSlaves: [eth1, eth2]
              route:
              - network: 192.168.222.0
                netmask: 255.255.255.0
                GwAddress: 192.168.10.1

4) Configure a bonded interface with "802.3ad" as the bonding mode and IP
IPAddress obtained via DHCP.

    - hosts: myhost
      roles:
        - role: network
          ServerConfiguration_Interface_Bond:
            - NetworkName: bond0
              Bootproto: dhcp
              BondType: 802.3ad
              Bond_miimon: 100
              BondSlaves: [eth1, eth2]

5) All the above examples show how to configure a single host, The below
example shows how to define your network configurations for all your machines.

Assume your host inventory is as follows:

### /etc/ansible/hosts

    [dc1]
    host1
    host2

Describe your network configuration for each host in host vars:

### host_vars/host1

    ServerConfiguration_Interface_Ether:
           - NetworkName: eth1
             Bootproto: static
             IPAddress: 192.168.10.18
             netmask: 255.255.255.0
             GwAddress: 192.168.10.1
             route:
              - network: 192.168.200.0
                netmask: 255.255.255.0
                GwAddress: 192.168.10.1
    ServerConfiguration_Interface_Bond:
            - NetworkName: bond0
              Bootproto: dhcp
              BondType: 802.3ad
              Bond_miimon: 100
              BondSlaves: [eth2, eth3]

### host_vars/host2

    ServerConfiguration_Interface_Ether:
           - NetworkName: eth0
             Bootproto: static
             IPAddress: 192.168.10.18
             netmask: 255.255.255.0
             GwAddress: 192.168.10.1

Create a playbook which applies this role to all hosts as shown below, and run
the playbook. All the servers should have their network interfaces configured
and routed updated.

    - hosts: all
      roles:
        - role: network

Note: Ansible needs network connectivity throughout the playbook process, you
may need to have a control interface that you do *not* modify using this
method so that Ansible has a stable connection to configure the target
systems.

Dependencies
------------

None

License
-------

BSD

Author Information
------------------

Benno Joy

