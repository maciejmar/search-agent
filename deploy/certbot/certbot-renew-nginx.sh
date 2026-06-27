#!/usr/bin/env bash
set -e

certbot renew --quiet --deploy-hook "systemctl reload nginx"
