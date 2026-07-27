ssh -i "C:/Users/rezen/.ssh/IF-AWS.pem" ubuntu@54.94.213.217


aws cli

Credenciais configuradas via `aws configure` local (não versionar aqui — ver mydata.md).

## Controle do bot sem SSH (status_server.py)

Endpoint HTTP separado do bot (sobrevive mesmo se `main_telegram.py`
travar) pra iniciar/parar/checar sem precisar entrar na EC2 — ver
`AGENTES/julio/status_server.py` e o plano
`docs/superpowers/plans/2026-07-27-status-controle-bot-ec2.md`.

Subir na EC2 (uma vez, ou depois de cada deploy):

```
cd AGENTES/julio
pkill -f status_server.py
nohup python3 status_server.py >> data/status_server.log 2>> data/status_server.err.log &
```

Requer `STATUS_TOKEN` e `AMBIENTE=EC2` definidos em `REDIS/.env` da EC2
(ver `REDIS/.env.example`). Chamar de fora:

```
curl -H "X-Status-Token: <token>" http://<ip-ec2>:8765/status
curl -X POST -H "X-Status-Token: <token>" http://<ip-ec2>:8765/iniciar
curl -X POST -H "X-Status-Token: <token>" http://<ip-ec2>:8765/parar
```

Sem HTTPS por enquanto (uso interno, baixo tráfego) — o token vai em
header, nunca em querystring, pra não vazar em log de acesso.