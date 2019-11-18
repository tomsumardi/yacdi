
## YACDI (Yet Another Ceph Deployment Installer)

### Goal: another ceph installation using ansible

### Quick Design Description: 
Python is being used to generate ceph playbook inventories and their arguments similar to hosts such as groups of management, nodes and 
etc with their respected variables within group_vars and host_vars.
The groups are the following "admin, mgmt, nodes, provision, reconfig, unknown". the inventories are generated based on 
template file, which describe ceph cluster. 
example of inventory in nodes:
[provision]
ceph-node1.public

### ceph cluster schema: cluster.schema

### ceph cluster template Examples: 
- templates/micro-cluster.json
- templates/small-cluster.json

### Development environment:
virtualbox with n-th vms

Note: networkintf bonding library using playbook BSD licensed
