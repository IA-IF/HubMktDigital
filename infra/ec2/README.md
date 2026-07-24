# EC2 do HubMktDigital (orquestrador Telegram)

Substitui a instancia criada manualmente (`i-0dab47533bf909d2b`,
`15.229.178.221`). Tudo reproduzivel via CloudFormation, sem clique manual.

## Via Console AWS (sem instalar nada)

Nao precisa de AWS CLI nem credenciais na maquina local -- so um navegador
logado na conta AWS e um terminal (Git Bash, que voce ja tem) pra rodar o
`deploy.sh` no final (isso ai so usa SSH/rsync, nao AWS CLI).

### 1. Descobrir seu IP publico

Abra https://checkip.amazonaws.com no navegador (mostra so o IP). Anota
como `SEU_IP/32`.

### 2. Criar a stack no Console

1. Entra em **CloudFormation** no Console AWS, regiao **sa-east-1** (São
   Paulo) -- confere no seletor de regiao no canto superior direito.
2. **Create stack** -> **With new resources (standard)**.
3. Em "Specify template", escolhe **Upload a template file** e manda o
   arquivo `infra/ec2/template.yaml` (é so um `.yaml`, arrasta ou clica
   pra escolher no seu PC).
4. Stack name: `hubmktdigital-bot`.
5. Na tela de parametros:
   - `KeyPairName`: escolhe `IF-AWS` no dropdown (o Console ja lista as
     key pairs existentes na conta).
   - `SSHAllowedCidr`: cola `SEU_IP/32` do passo 1.
   - `VpcId`: dropdown -- escolhe a VPC marcada como "default".
   - `SubnetId`: dropdown -- escolhe uma subnet dessa VPC (qualquer uma,
     sao todas publicas na VPC default).
   - `InstanceType` e `UbuntuAmiParameter`: deixa o valor default.
6. Avança nas proximas telas (Configure stack options -- pode deixar tudo
   default) ate a ultima.
7. Na revisao final, marca a caixinha **"I acknowledge that AWS
   CloudFormation might create IAM resources"** (aparece porque o template
   cria uma IAM Role/Policy pro bot) e clica **Submit**.
8. Acompanha o progresso na aba **Events** -- leva uns 1-2 minutos ate o
   status virar `CREATE_COMPLETE`.

### 3. Pegar o IP da instancia nova

Na stack criada, aba **Outputs** -- mostra `PublicIp`, `InstanceId` e o
comando de SSH pronto.

### 4. Subir o codigo e iniciar o bot

```bash
infra/ec2/deploy.sh <IP_DA_STACK> "C:/Users/rezen/.ssh/IF-AWS.pem"
```

Isso faz `rsync` do repo (menos `.git`, `.venv`, `.trae*`, segredos) +
`scp` do `.env` a parte + cria venv + instala deps + reinicia o
`hubmkt-bot.service`.

### 5. Validar

```bash
ssh -i "C:/Users/rezen/.ssh/IF-AWS.pem" ubuntu@<IP_DA_STACK> \
  "journalctl -u hubmkt-bot -n 50 --no-pager"
```

Manda uma mensagem no Telegram pro bot e confirma que ele responde.

### 6. Cutover: terminar a instancia antiga

So depois do passo 5 confirmado. Pelo Console: **EC2** -> **Instances**,
seleciona `i-0dab47533bf909d2b` (a antiga, IP `15.229.178.221`) ->
**Instance state** -> **Terminate instance**.

## Redeploy de codigo (dia a dia)

Depois que a stack ja existe, basta rodar de novo o passo 4
(`infra/ec2/deploy.sh`) sempre que quiser subir uma mudanca -- ele
sincroniza e reinicia o servico, sem recriar a instancia.

## O que NAO esta automatizado aqui (decisao consciente, dev-sized)

- **Sem VPC privada / NAT Gateway**: a instancia fica em subnet publica
  (como a atual). Rodar em subnet privada + NAT custaria ~$30+/mes so de
  NAT Gateway, desproporcional pra 1 instancia pequena de projeto solo.
  SSH fica restrito por Security Group ao seu IP.
- **Segredos via `.env` + scp, nao Secrets Manager**: o codigo ja usa
  `python-dotenv` em todo lugar; migrar pra Secrets Manager exigiria mudar
  `julio_config.py` e afins. Deixei anotado, nao fiz -- e mudanca de codigo,
  nao so de infra.
- **`TOOLS/GOOGLE_API/auth.json` nao esta no `.gitignore`** -- ja corrigido
  neste commit (adicionado ao `.gitignore`; nunca tinha sido commitado).
- **Sem detailed monitoring** (`Monitoring: true` custaria ~$2/mes a mais,
  desnecessario pra 1 instancia pequena).
- **Egress liberado (todas as portas/protocolos)** -- o bot fala com
  Telegram, Redis Cloud (porta custom, ver `.env`) e APIs Google; travar
  egress porta-a-porta é hardening de producao (ver `security.md` do
  plugin `deploy-on-aws`), fora de escopo pra um bot solo.

O scanner de compliance (`checkov`/`cfn-guard` via plugin `deploy-on-aws`)
foi rodado no template -- essas 3 sao as unicas violacoes remanescentes,
todas conscientemente aceitas pelo motivo acima (tier dev, nao producao).
