# topo.py
# This file withholds the dumbbell topology which the script is manufactured to run on
# The topology is as follows : H1 --- S1 --- R1 --- S2 --- H2
# Julijan Garbek - CIS 437

from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
import sys

def create_network():
    net = Mininet(switch=OVSBridge, link=TCLink)

    # Add hosts
    h1 = net.addHost('h1', ip='10.0.1.1/24')
    h2 = net.addHost('h2', ip='10.0.2.1/24')

    # Add router (a host acting as a router)
    r1 = net.addHost('r1', ip='10.0.1.254/24')

    # Add switches
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    # Links - high capacity links to hosts, bottleneck is controlled via tc on r1
    net.addLink(h1, s1, bw=1000)
    net.addLink(s1, r1, bw=1000)
    net.addLink(r1, s2, bw=1000)
    net.addLink(s2, h2, bw=1000)

    net.start()

    # Set up routing
    r1.cmd('ifconfig r1-eth1 10.0.2.254/24')
    r1.cmd('sysctl -w net.ipv4.ip_forward=1')
    h1.cmd('ip route add default via 10.0.1.254')
    h2.cmd('ip route add default via 10.0.2.254')

    # Verify connectivity
    print("Testing connectivity...")
    result = h1.cmd('ping -c 2 10.0.2.1')
    print(result)

    if '--cli' in sys.argv:
        CLI(net)
    
    return net

if __name__ == '__main__':
    setLogLevel('info')
    net = create_network()
    if '--cli' not in sys.argv:
        net.stop()
