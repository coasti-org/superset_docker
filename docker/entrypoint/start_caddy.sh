#!/bin/sh

TLS_MODE_VALUE="${TLS_MODE:-selfsigned}";
case "${TLS_MODE_VALUE}" in
acme|ACME)
    echo "[caddy] TLS_MODE=${TLS_MODE_VALUE} -> Using Let's Encrypt/ACME config";
    cp -f /etc/caddy/Caddyfile.acme /etc/caddy/Caddyfile ;;
selfsigned|SELF_SIGNED|self-signed)
    echo "[caddy] TLS_MODE=${TLS_MODE_VALUE} -> Using internal PKI config (linkFISH Consulting CA)";
    cp -f /etc/caddy/Caddyfile.selfsigned /etc/caddy/Caddyfile ;;
internal|INTERNAL|custom|CUSTOM)
    echo "[caddy] TLS_MODE=${TLS_MODE_VALUE} -> Using custom certificate config";
    if [ ! -r "${TLS_CERT_FILE}" ]; then
    echo "[caddy] ERROR: TLS_MODE=internal but TLS_CERT_FILE is missing/unreadable: ${TLS_CERT_FILE}";
    echo "[caddy]        Provide the cert via ./certs and/or set TLS_CERT_FILE in .env";
    exit 2;
    fi;
    if [ ! -r "${TLS_KEY_FILE}" ]; then
    echo "[caddy] ERROR: TLS_MODE=internal but TLS_KEY_FILE is missing/unreadable: ${TLS_KEY_FILE}";
    echo "[caddy]        Provide the key via ./certs and/or set TLS_KEY_FILE in .env";
    exit 2;
    fi;
    cp -f /etc/caddy/Caddyfile.internal /etc/caddy/Caddyfile ;;
*)
    echo "[caddy] ERROR: Unknown TLS_MODE='${TLS_MODE_VALUE}'. Expected one of: acme, selfsigned, internal";
    exit 2 ;;
esac;
exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
