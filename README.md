# Clusterização de endereços de sextortion

Tópicos Especiais de Segurança - (P1)

Lucas Panonko Assis Belchior - 12311BCC068

Repositório: [Clusterização (ML) de endereços ilícitos](https://github.com/LuksbellN/Clusteriza-o-ML-de-endere-os-ilicitos).

## Objetivo

Agrupar os endereços do arquivo fornecido usando K-Means e DBSCAN. Comparar os grupos pelas movimentações financeiras e pelo grafo das transações, conforme o enunciado.

O relatório está em `report/Clusterizacao_ML_Lucas_Belchior.pdf`. Tem seis páginas, incluindo a capa, e links para este repositório. O PDF não contém arquivos anexados.

Este repositório publica apenas o código e as instruções. As pastas `results/` e `report/` são geradas localmente pelos scripts e não são versionadas. O arquivo original deve ser obtido com a disciplina.

## Como executar

Requer Python 3.12 ou superior. Coloque o arquivo original `ExercCluster.tgz` na pasta acima desta. Não é necessário extrair o TAR nem usar APIs, banco de dados ou GPU.

Execute nesta pasta:

```powershell
python -m pip install -r requirements.txt
python analyze.py
python build_report.py
python verify.py
```

No Windows, use o caminho de um interpretador instalado se o comando `python` abrir a Microsoft Store. Os scripts leem e escrevem caminhos relativos à própria pasta, independentemente da pasta do terminal.

## O que cada script faz

- `analyze.py`: lê os JSONs, remove transações repetidas, calcula as medidas de cada endereço, executa os modelos e salva tabelas e gráficos.
- `build_report.py`: monta o PDF com os resultados e o link do repositório.
- `verify.py`: reabre o dataset, confere contagens, valores, taxas e conexões. Também recalcula os modelos, confere o texto e os links do PDF e verifica a ausência de anexos.

O código usa bibliotecas prontas para os algoritmos e os gráficos. Não há implementação própria de K-Means ou DBSCAN. A geração do PDF fica separada da análise.

## Método

Foram usados todos os 38 endereços do arquivo. As 334 ocorrências correspondem a 329 transações únicas; as cinco cópias repetidas são idênticas.

Cada endereço tem quatro atributos para o agrupamento:

1. Número de transações em que recebe valores.
2. Número de transações em que gasta valores.
3. Total recebido, em satoshis.
4. Dias entre sua primeira e última transação observada.

O total gasto é quase igual ao recebido nesta base. Ele foi mantido nas tabelas financeiras, mas não entra no modelo para evitar contar o volume duas vezes. Os valores monetários são somados em satoshis inteiros; 1 BTC = 100.000.000 satoshis.

Antes do agrupamento, aplica-se `log1p` e depois `StandardScaler`. Isso reduz o efeito de valores muito grandes e torna as escalas comparáveis. Os dois algoritmos usam os mesmos quatro atributos e distância euclidiana.

K-Means: k de 2 a 6, `random_state=42`, `n_init=10`. Foi escolhido o k com maior silhouette média. DBSCAN: `min_samples=3` e quatro tentativas de eps (0,5; 1; 1,5; 2). Foi usado eps=1,5 por manter dois grupos e deixar menos ruído que os raios menores. Com eps=2, resta apenas um grupo. Essa escolha foi feita para a amostra e não significa que 1,5 funciona para qualquer dataset.

Os gráficos de dispersão mostram valor recebido e número de transações. O eixo do valor recebido tem escala logarítmica. O modelo usa os quatro atributos, não apenas as medidas dos eixos.

## Resultados

- K-Means: três grupos com 3, 30 e 5 endereços; silhouette 0,469. C1, C2 e C3 estão em ordem crescente da mediana de recebimentos.
- DBSCAN: dois grupos com 30 e 3 endereços; cinco pontos de ruído; silhouette 0,509 calculada nos 33 pontos agrupados. Esse score não é diretamente comparável ao do K-Means, que inclui os 38 endereços.
- Total recebido: 3.170.598.704 sat. Total gasto: 3.170.582.158 sat. Diferença observada: 16.546 sat; não deve ser tratada como saldo atual.
- Grafo dos alvos: 38 nós, seis arestas, 33 componentes e 29 nós isolados. Quatro transações geram as seis arestas. Cada aresta indica presença na mesma transação, não um pagamento direto entre os dois endereços.

O grafo de exemplo mostra endereços de entrada, a transação e endereços de saída. Os endereços que não são alvos são somados como Outros, separadamente em cada lado. Os valores dos rótulos são arredondados; os totais exatos e a taxa estão no texto e nos CSVs.

## Limitações

Os arquivos informam `limit=50` e `offset=0`, mas contêm de 2 a 58 registros. Não foi possível confirmar se os históricos estão completos. A análise usa somente a base entregue, entre 09/09/2018 e 07/05/2021 (UTC).

A indicação de sextortion vem do enunciado. Os demais endereços encontrados nas transações não foram classificados como ilícitos. Os clusters descrevem semelhanças nas medidas escolhidas; não identificam pessoas, campanhas ou lucro com extorsão. O ruído do DBSCAN também não é uma classificação de risco.

## Tabelas em results/

- `addresses.csv`: endereços completos, IDs A01-A38, medidas e grupos. DBSCAN=-1 significa ruído.
- `clusters.csv`: totais e medianas por grupo K-Means.
- `transactions.csv`: as 329 transações únicas, com seus totais.
- `shared_transactions.csv`: pares de alvos que aparecem na mesma transação e os txIds correspondentes.
- `kmeans_grid.csv` e `dbscan_grid.csv`: todas as tentativas de parâmetros.
- `summary.json`: resumo, parâmetros de padronização e versões das bibliotecas.
- `verification.json`: resultado das conferências.
- `figures/`: os quatro gráficos do relatório.

O arquivo original não é modificado nem publicado no repositório. SHA-256: `ef60f142a9faec08a99f403966d8c513a5c0da7ca4b310132db62c905823a69c`.

## Roteiro sugerido para estudar e apresentar

É um escopo compatível com uma semana de estudo, supondo familiaridade básica com Python e tempo diário para a atividade. Uma divisão possível: dois dias para entender os JSONs e calcular atributos; dois para estudar os modelos e comparar parâmetros; um para finanças e grafo; dois para escrever e conferir o relatório. Isso é uma estimativa de estudo, não um registro do tempo gasto neste projeto.

Antes de apresentar, é importante conseguir explicar o que uma linha representa, por que padronizar os atributos, o que k e eps alteram, por que um ponto vira ruído e por que estar no mesmo cluster não prova controle pela mesma pessoa.

## Referências

Documentação oficial: [Clustering](https://scikit-learn.org/stable/modules/clustering.html) e [silhouette_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html), consultadas em 11/11/2026. Enunciado e ExercCluster.tgz fornecidos pela disciplina.
