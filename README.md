# Agente de Atendimento — Empório da Música

Agente de atendimento com regras de negócio determinísticas, dados consultados por repositórios e recuperação versionada do manual de políticas. O projeto separa domínio, aplicação e infraestrutura: o modelo de linguagem apenas classifica casos ambíguos e redige respostas fundamentadas; ele não executa SQL nem decide elegibilidade de políticas.

## Requisitos e instalação

- Python 3.11 ou superior;
- `pdftotext` (Poppler) para extrair o texto do manual durante a publicação;
- uma chave OpenRouter somente no modo de produção com embeddings remotos.

Crie um ambiente virtual e instale as dependências de desenvolvimento:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Para usar Chroma como armazenamento vetorial, instale também o extra opcional:

```bash
.venv/bin/python -m pip install -e ".[dev,rag]"
```

Execute a suíte local:

```bash
.venv/bin/python -m pytest -q
```

## Arquitetura

```text
Interface de canal -> Router/Orquestração -> Domínio <- Infraestrutura
                                      |                 |
                              PolicyEngine/RAG     SQL, vetores, LLM
```

- `src/domain/`: entidades, resultados, PolicyEngine e contratos de repositório.
- `src/application/`: decisões de roteamento, geração de resposta e portas para clientes externos.
- `src/application/policies/`: portas de embedding, índice e armazenamento vetorial.
- `src/infrastructure/database/`: SQLAlchemy, repositórios e o registro de versão ativa de políticas.
- `src/infrastructure/retrieval/`: índice de políticas, adaptador local e adaptador opcional Chroma.
- `src/composition.py`: único ponto que monta os adaptadores de política conforme a configuração.

As regras objetivas (prazos, descontos, elegibilidade) são avaliadas no `PolicyEngine`. O RAG recupera explicações e exceções do manual; a resposta final deve usar apenas o Evidence Bundle produzido pela aplicação.

## Atendimento ao cliente

O repositório fornece os componentes do atendimento, mas ainda não expõe um chat de terminal ou integração pronta com WhatsApp. O canal de entrada deve enviar cada mensagem ao `Router` junto do contexto da conversa e usar a decisão retornada para acionar o orquestrador.

Exemplos de perguntas esperadas:

- “Qual é o preço do violão?” → consulta de dados.
- “Como funciona a política de devolução?” → RAG de políticas.
- “Posso trocar o pedido 17 por defeito?” → fluxo híbrido: identidade, pedido, PolicyEngine e RAG.
- “Quero falar com um atendente humano” → escalonamento.

O cliente não informa `customer_id` pelo texto. A identidade vem do número do canal e a consulta de pedidos deve ser sempre filtrada pelo cliente autenticado. Pedidos de reembolso, troca ou alteração crítica são pré-analisados e encaminhados à equipe humana, nunca confirmados pelo modelo.

## Modos de política e RAG

### Offline / desenvolvimento

Este é o padrão. Usa vetores determinísticos locais, sem chave de API nem serviço externo. Ele é adequado para testes e para validar publicação, contratos e isolamento por versão, mas não oferece a qualidade semântica de um modelo de embeddings treinado.

```bash
POLICY_EMBEDDING_PROVIDER=hash
POLICY_VECTOR_BACKEND=file
```

As coleções locais são arquivos versionados em `data/policies/policy_vectors/` por padrão. O SQLite fica em `data/emporio.db` por padrão.

### Produção

Para recuperação semântica, use o adaptador de embeddings do OpenRouter e um armazenamento vetorial dedicado, como Chroma:

```bash
export POLICY_EMBEDDING_PROVIDER=openrouter
export OPENROUTER_EMBEDDING_API_KEY='sua-chave'
export POLICY_VECTOR_BACKEND=chroma
export POLICY_VECTOR_DIRECTORY=/caminho/persistente/policy_vectors
export DATABASE_URL='sqlite:////caminho/persistente/emporio.db'
```

O adaptador vetorial está atrás de interfaces. Assim, Chroma pode ser trocado por Qdrant ou pgvector sem modificar `domain/` ou `application/`.

## Variáveis de ambiente

| Variável | Padrão | Uso |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///data/emporio.db` | Banco de dados de negócio e ponteiro de versão ativa. |
| `POLICY_VECTOR_BACKEND` | `file` | `file` para o adaptador local ou `chroma` para Chroma. |
| `POLICY_VECTOR_DIRECTORY` | `data/policies/policy_vectors` | Diretório persistente das coleções vetoriais. |
| `POLICY_EMBEDDING_PROVIDER` | `hash` | `hash` offline ou `openrouter` para embeddings semânticos. |
| `OPENROUTER_EMBEDDING_API_KEY` | vazio | Obrigatória quando o provedor é `openrouter`. |
| `OPENROUTER_DECISION_API_KEY` | vazio | Cliente de decisão para roteamento ambíguo, quando configurado. |
| `OPENROUTER_TEXT_API_KEY` | vazio | Cliente de redação de respostas, quando configurado. |

Nunca versione chaves. Use um gerenciador de segredos ou variáveis configuradas no ambiente de execução.

## Operação administrativa de políticas

Uma versão de política é um diretório `data/policies/v<versão>/` contendo:

```text
manifest.yaml       # versão, vigência, PDF associado e indicação de conteúdo sintético
rules.yaml          # regras estruturadas do PolicyEngine
<manual>.pdf        # manual da mesma versão
```

Para publicar a versão real atual:

```bash
.venv/bin/python -m src.main publish 2.1
```

A publicação valida manifesto e regras, confere se cada seção citada pelas regras existe no PDF, gera a coleção vetorial da versão e só então troca, em uma transação SQL, o ponteiro da versão ativa. Em caso de falha, o ponteiro atual permanece inalterado.

Outros comandos:

```bash
.venv/bin/python -m src.main active
.venv/bin/python -m src.main rollback
```

`rollback` reaponta para a versão previamente ativada; ele só terá efeito depois que houver mais de uma versão real publicada. Não altere o manual ou as regras de uma versão já ativa: publique um novo diretório versionado, valide-o e use `publish`.

## Limitações atuais

- A interface conversacional de canal (WhatsApp, web ou CLI de chat) e o orquestrador ponta a ponta ainda precisam ser conectados aos componentes existentes.
- O adaptador local de vetores é útil para testes; produção deve usar embeddings semânticos e um armazenamento vetorial persistente.
- Migrações formais para PostgreSQL/Alembic e integração com rastreamento de transportadora ainda não foram implementadas.
