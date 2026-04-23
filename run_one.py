#!/usr/bin/env python3
"""
Runs a single BBR/CUBIC experiment in Mininet.
Usage: sudo python3 run_one.py <algo> <rtt> <bw> <buffer> <rep> <duration> <csvfile>
"""

import sys
import time
import json
from mininet.net import Mininet
from mininet.node import OVSBridge
from mininet.link import TCLink
from mininet.log import setLogLevel

def run_experiment(algo, rtt, bw, buf, rep, duration, csvfile):
    setLogLevel('warning')

    net = Mininet(switch=OVSBridge, link=TCLink)

    # Create the hosts, router, and switches for the dumbbell topology
    h1 = net.addHost('h1', ip='10.0.1.1/24')
    h2 = net.addHost('h2', ip='10.0.2.1/24')
    r1 = net.addHost('r1', ip='10.0.1.254/24')
    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    # Add links between the hosts, switches, and routers
    net.addLink(h1, s1, bw=1000)
    net.addLink(s1, r1, bw=1000)
    net.addLink(r1, s2, bw=1000)
    net.addLink(s2, h2, bw=1000)

    # Start the network simulation
    net.start()

    # Set up routing
    r1.cmd('ifconfig r1-eth1 10.0.2.254/24') # Assigns an IP address to r1 facing h2
    r1.cmd('sysctl -w net.ipv4.ip_forward=1') # Treat the Linux host as a router to forward packets to h2
    h1.cmd('ip route add default via 10.0.1.254') # Default route h1 to r1
    h2.cmd('ip route add default via 10.0.2.254') # Default route return from h2 to r1

    # Set congestion control
    r1.cmd('sysctl -w net.ipv4.tcp_congestion_control={}'.format(algo)) # Set router r1 to use the congestion control algorithm (BBR or CUBIC)
    h1.cmd('sysctl -w net.ipv4.tcp_congestion_control={}'.format(algo)) # Set sender host h1 to use the congestion control algorithm (BBR or CUBIC)
    h2.cmd('sysctl -w net.ipv4.tcp_congestion_control={}'.format(algo)) # Set reciever host h2 to use the congestion control algorithm (BBR or CUBIC)

    # Apply bottleneck on r1-eth1 (toward h2)
    half_rtt = rtt / 2.0 # Cuts the rtt in half to simulate each directional leg of the 

    # Convert bandwidth from megabits to bytes to determine burst size
    # Ensures burst is at least 15,000 bytes so packets can pass through
    burst = max(int(bw * 1000 / 8), 15000)


    r1.cmd('tc qdisc del dev r1-eth1 root 2>/dev/null') # Delete existing traffic shaping rules delay, bandwidth, buffer) before applying a new one
    r1.cmd('tc qdisc add dev r1-eth1 root handle 1: netem delay {:.1f}ms'.format(half_rtt)) # Adds delay to the outgoing interface, e.g. allowing half_rtt = 50.0 to become 50ms
    r1.cmd('tc qdisc add dev r1-eth1 parent 1: handle 2: tbf rate {}mbit burst {} limit {}'.format(bw, burst, buf)) # Adds bandwidth cap, burst size, and buffer limit (100KB or 10MB)

    # Add delay on return path
    r1.cmd('tc qdisc del dev r1-eth0 root 2>/dev/null') # Delete existing traffic shaping rules before applying a new one - same as previously stated
    r1.cmd('tc qdisc add dev r1-eth0 root handle 1: netem delay {:.1f}ms'.format(half_rtt)) # Adds delay to the return interface - same as previously stated

    time.sleep(1) # 1s buffer for traffic shaping rules to update

    # Verify our network connection is working as intended
    ping_result = h1.cmd('ping -c 2 -W 5 10.0.2.1') # Send 2 pings to h2 and wait up to 5s for a reply
    if '0 received' in ping_result: # If no pings returned, the network is not working correctly
        print("  PING FAILED - skipping")
        with open(csvfile, 'a') as f: # Open csv file
            f.write('{},{},{},{},{},0,0\n'.format(algo, rtt, bw, buf, rep)) # Write 0's for the run
        net.stop() # Stop virtual network
        return # Skip to next run

    # Run iperf3 experiment run, sending data through the bottleneck and saving the results to a JSON format in the 'result'
    h2.cmd('iperf3 -s -D -p 5201') # Start iperf3 on host h2, port 5201
    time.sleep(1) # Wait 1s for connection to establish
    result = h1.cmd('iperf3 -c 10.0.2.1 -p 5201 -t {} -J'.format(duration)) # Run iperf3 on host h1 for 1 minute, and output in JSON format

    # Parse JSON output
    try:
        data = json.loads(result)
        goodput = data['end']['sum_sent']['bits_per_second'] / 1e6
        retransmits = data['end']['sum_sent'].get('retransmits', 0)
    except:
        goodput = 0
        retransmits = 0

    # Write result
    with open(csvfile, 'a') as f:
        f.write('{},{},{},{},{},{:.2f},{}\n'.format(algo, rtt, bw, buf, rep, goodput, retransmits))

    print("  Goodput: {:.2f} Mbps | Retransmits: {}".format(goodput, retransmits))

    h2.cmd('killall iperf3 2>/dev/null')
    net.stop()

if __name__ == '__main__':
    algo = sys.argv[1]
    rtt = float(sys.argv[2])
    bw = float(sys.argv[3])
    buf = int(sys.argv[4])
    rep = int(sys.argv[5])
    duration = int(sys.argv[6])
    csvfile = sys.argv[7]
    run_experiment(algo, rtt, bw, buf, rep, duration, csvfile)