# WayneHomeLab

Este repositorio contiene todo lo necesario para levantar un cluster k3s usando Ansible.

## Estructura del proyecto

- `ansible/`: Contiene los playbooks y roles de Ansible.
- `cloudflare-ddns-updater.sh`: Script para actualizar Cloudflare DDNS.
- `.github/`: Contiene los workflows de GitHub Actions.
- `kubeconfig`: Configuración de Kubernetes.
- `README.md`: Documentación del proyecto.

## Uso

1. Clona el repositorio.
2. Configura tus variables de Ansible.
3. Ejecuta los playbooks de Ansible para desplegar el cluster k3s y el cronjob de Cloudflare DDNS.
4. Realiza push sobre el repositorio para sincronizar los nodos automáticamente.

## Comandos útiles

- Para desplegar el cluster k3s:
  ```sh
  ansible-playbook ansible/playbooks/setup.yml -i ansible/inventory/hosts.ini --key-file ~/.ssh/id_rsa
