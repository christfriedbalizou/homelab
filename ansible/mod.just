set quiet
set shell := ['bash', '-euo', 'pipefail', '-c']
set script-interpreter := ['bash', '-euo', 'pipefail']

ansible_dir := justfile_dir() + '/ansible'

[private]
default:
    just -l pihole

[doc('Prepare Pi-hole box')]
[group('pihole')]
prepare:
    cd "{{ ansible_dir }}" && ansible-playbook -i "{{ ansible_dir }}/inventory/hosts.yaml" "{{ ansible_dir }}/playbooks/pihole-prepare.yaml"

[doc('Install Pi-hole')]
[group('pihole')]
install:
    cd "{{ ansible_dir }}" && ansible-playbook -i "{{ ansible_dir }}/inventory/hosts.yaml" "{{ ansible_dir }}/playbooks/pihole-installation.yaml"

[doc('Perform Pi-hole operating system updates')]
[group('pihole')]
update:
    cd "{{ ansible_dir }}" && ansible-playbook -i "{{ ansible_dir }}/inventory/hosts.yaml" "{{ ansible_dir }}/playbooks/pihole-update.yaml"

[doc('Uninstall Pi-hole')]
[group('pihole')]
nuke:
    cd "{{ ansible_dir }}" && ansible-playbook -i "{{ ansible_dir }}/inventory/hosts.yaml" "{{ ansible_dir }}/playbooks/pihole-nuke.yaml"

[doc('Reboot Pi-hole box')]
[group('pihole')]
reboot:
    cd "{{ ansible_dir }}" && ansible-playbook -i "{{ ansible_dir }}/inventory/hosts.yaml" "{{ ansible_dir }}/playbooks/pihole-reboot.yaml"

[doc('Ping Pi-hole host')]
[group('pihole')]
ping:
    cd "{{ ansible_dir }}" && ansible pihole -i "{{ ansible_dir }}/inventory/hosts.yaml" --one-line -m 'ping'

[doc('Show uptime of Pi-hole host')]
[group('pihole')]
uptime:
    cd "{{ ansible_dir }}" && ansible pihole -i "{{ ansible_dir }}/inventory/hosts.yaml" --one-line -a 'uptime'
