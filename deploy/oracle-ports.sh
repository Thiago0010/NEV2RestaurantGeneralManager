#!/usr/bin/env bash
# =============================================================
# oracle-ports.sh
# Libera as portas 80/443 no iptables da Oracle Cloud
# (Oracle Ubuntu 22.04 vem com iptables-nft, e o UFW às vezes
#  não sincroniza direito com a Security List. Esse script
#  garante via iptables direto.)
# Rode como root:  sudo bash deploy/oracle-ports.sh
# =============================================================
set -euo pipefail

echo "Liberando 80 e 443 no iptables..."

iptables -I INPUT 1 -p tcp --dport 80  -j ACCEPT
iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT

# Tenta salvar via netfilter-persistent (se existir)
if command -v netfilter-persistent &> /dev/null; then
  netfilter-persistent save
  echo "Regras persistidas via netfilter-persistent."
else
  # Fallback: instala iptables-persistent
  echo "iptables-persistent não está instalado. Salvando manualmente..."
  apt-get install -y iptables-persistent
  netfilter-persistent save
fi

echo "Regras atuais (porta 80/443):"
iptables -L INPUT -n | grep -E "80|443" || echo "(nenhuma regra encontrada, mas liberei acima)"

cat <<EOF

✅ Portas liberadas!

LEMBRE-SE: além desse script, você também precisa liberar as
portas no painel da Oracle Cloud:

  Networking → Virtual Cloud Networks → sua VCN →
  Subnet Details → Security Lists → Default Security List →
  Add Ingress Rules:
    Source:        0.0.0.0/0
    Protocol:      TCP
    Destination Port:  80
    Destination Port:  443

EOF
