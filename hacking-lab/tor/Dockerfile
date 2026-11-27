# Tor (cliente SOCKS en 127.0.0.1:9050) sobre el túnel de Mullvad (perfil «tor»).
FROM debian:bookworm-slim@sha256:e67eeead736ff7bbe258ef088bff683635c561b1fcfefad0806c1df4ab49ce0e

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends tor ca-certificates \
 && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN printf 'SocksPort 127.0.0.1:9050\nLog notice stdout\nDataDirectory /var/lib/tor\n' > /etc/tor/torrc
USER debian-tor
CMD ["tor", "-f", "/etc/tor/torrc"]
