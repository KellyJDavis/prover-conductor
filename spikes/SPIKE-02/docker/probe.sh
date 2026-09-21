#!/usr/bin/env bash
# Runs INSIDE the sandbox. Prints one line per probe: PROBE <name> REACHED|BLOCKED.
probe() { name=$1; shift; if "$@" >/dev/null 2>&1; then echo "PROBE $name REACHED"; else echo "PROBE $name BLOCKED"; fi; }
gw=$(python3 - <<'PY'
import socket, struct
for l in open('/proc/net/route').read().splitlines()[1:]:
    f = l.split()
    if f[1] == '00000000':
        print(socket.inet_ntoa(struct.pack('<L', int(f[2], 16)))); break
PY
)
echo "INFO interfaces: $(ls /sys/class/net 2>/dev/null | tr '\n' ' ') gateway=${gw:-none}"
probe internet-ip-tcp        curl -sS -m 5 -o /dev/null https://1.1.1.1
probe internet-dns-name      curl -sS -m 5 -o /dev/null https://github.com
probe dns-resolve            python3 -c 'import socket; socket.gethostbyname("github.com")'
probe metadata-169.254.169.254 curl -sS -m 3 -o /dev/null http://169.254.169.254/
probe internal-service-eth0-ip curl -sS -m 3 -o /dev/null "http://${SVC_IP}:8080/"
probe container-gateway      curl -sS -m 3 -o /dev/null "http://${gw:-172.17.0.1}:1/"
probe docker-bridge-172.17.0.1 curl -sS -m 3 -o /dev/null http://172.17.0.1:1/
probe private-10.0.0.1       curl -sS -m 3 -o /dev/null http://10.0.0.1/
probe private-192.168.65.254 curl -sS -m 3 -o /dev/null http://192.168.65.254/
probe udp-53-1.1.1.1         python3 -c 'import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(3);s.sendto(b"x",("1.1.1.1",53));s.recvfrom(10)'
probe raw-socket             python3 -c 'import socket;socket.socket(socket.AF_INET,socket.SOCK_RAW,1)'
