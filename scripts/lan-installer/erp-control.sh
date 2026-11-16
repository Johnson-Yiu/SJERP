#!/bin/sh
set -eu

usage() {
    printf '%s\n' '用法：sh erp-control.sh 实例名 status|start|stop|restart|logs|health [HTTPS地址]'
}
instance=${1:-}
action=${2:-}
case "$instance" in ''|*[!a-z0-9-]*) usage; exit 2 ;; esac
unit="sjerp-local@$instance.service"

case "$action" in
    status) exec systemctl --no-pager status "$unit" ;;
    start|stop|restart) exec systemctl "$action" "$unit" ;;
    logs) exec journalctl --no-pager --lines=100 --unit="$unit" ;;
    health)
        url=${3:-}
        case "$url" in https://?*) ;; *) usage; exit 2 ;; esac
        systemctl is-active --quiet "$unit" || { echo 'ERP 服务未运行'; exit 1; }
        status=$(curl --silent --show-error --proto '=https' --max-time 15 \
            --output /dev/null --write-out '%{http_code}' "${url%/}/api/session/csrf/")
        [ "$status" = 200 ] || { echo "HTTPS 健康检查失败：HTTP $status"; exit 1; }
        echo 'ERP 服务运行中，HTTPS 检查通过。'
        ;;
    *) usage; exit 2 ;;
esac
