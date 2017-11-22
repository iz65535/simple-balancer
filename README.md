# simple-balancer
simple gateway failover switcher

Sometimes you'd need something more than just failover balancing between
multiple default gateways. For example, if gateways require advanced setup.

So, this script
- periodically pings each gateway to check its availability
- if current gateway is unreachable, it changes default routing and replaces iptables.service config file
- restarts firewall service

Script was made for centos7, but can be easily tuned/adapted.
