# Kali (arm64/amd64) con herramientas del repositorio oficial de Kali vía apt.
# Base fijada por digest (kali-rolling 2026-11-22). Sin herramientas a medida.
FROM kalilinux/kali-rolling@sha256:69a9a33d98a584a537bd0f7144d20c3b6d23f3bafa9ffcf0cadf4c5f186d02ff

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl wget dnsutils iproute2 iputils-ping netcat-openbsd \
      nmap whatweb nikto sqlmap gobuster ffuf dirb wfuzz \
      proxychains4 tmux vim-tiny less jq python3 python3-pip \
      seclists \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# proxychains -> Tor del perfil «tor» (mismo espacio de red: 127.0.0.1:9050)
RUN sed -i 's/^socks4 \+127.0.0.1 9050/socks5 127.0.0.1 9050/' /etc/proxychains4.conf

WORKDIR /root/workspace

# El DNS de este espacio de red es el de Mullvad (por el túnel): los nombres
# de los objetivos internos van a /etc/hosts al arrancar.
COPY lab-hosts /etc/lab-hosts
CMD ["sh", "-c", "cat /etc/lab-hosts >> /etc/hosts; exec bash"]
