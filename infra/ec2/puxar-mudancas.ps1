# Traz pro local os commits que a EC2 fez sozinha (pedidos de projeto
# aplicados pelo Julio via pedidos_projeto.aplicar) -- busca direto da
# instancia por SSH, sem depender de push pro GitHub (a EC2 so tem uma
# deploy key de LEITURA, de proposito -- ver infra/ec2/README.md).
#
# NAO mescla sozinho em master -- so traz pra uma branch local
# "ec2-master" pra voce revisar antes:
#   git log master..ec2-master --oneline   # ve o que tem de novo
#   git merge ec2-master                   # quando quiser trazer pra master
#
# Uso: .\infra\ec2\puxar-mudancas.ps1

$ErrorActionPreference = "Stop"
$key = "C:/Users/rezen/.ssh/IF-AWS.pem"
$host_ = "ubuntu@54.94.213.217"

$env:GIT_SSH_COMMAND = "ssh -i $key"
git fetch "ssh://$host_/home/ubuntu/HubMktDigital" "master:ec2-master"

Write-Host "`nNovidades na EC2 que ainda nao estao em master local:"
git log master..ec2-master --oneline
