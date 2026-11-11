"""PDF acadêmico: capa simples e cinco páginas de análise."""
import csv
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results'
REPO='https://github.com/LuksbellN/Clusteriza-o-ML-de-endere-os-ilicitos'
W,H=A4
M=43; CW=W-2*M


def n(x,d=0):
    return f'{x:,.{d}f}'.replace(',','_').replace('.',',').replace('_','.')


class Report:
    def __init__(self, stream):
        fd=Path(matplotlib.get_data_path())/'fonts/ttf'
        for name,file in [('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf'),('Mono','DejaVuSansMono.ttf')]:
            pdfmetrics.registerFont(TTFont(name,str(fd/file)))
        self.c=canvas.Canvas(stream,pagesize=A4)
        self.c.setTitle('Clusterização (ML) de endereços ilícitos - Sextortion')
        self.c.setAuthor('Lucas Panonko Assis Belchior')
        self.page=1;self.y=0;self.bottoms={}

    def new(self,title):
        if self.page>1:self.bottoms[self.page]=self.y
        self.c.showPage();self.page+=1;c=self.c
        c.setFillColor(colors.HexColor('#666666'));c.setStrokeColor(colors.HexColor('#666666'))
        c.setLineWidth(.5);c.line(M,H-35,W-M,H-35)
        c.setFont('Body',7.6);c.drawString(M,H-27,'TÓPICOS ESPECIAIS DE SEGURANÇA | CLUSTERIZAÇÃO - ML')
        c.setFont('Body',7.2);c.drawString(M,25,'Lucas Panonko Assis Belchior | 12311BCC068 | 11/11/2026')
        c.drawRightString(W-M,25,f'{self.page} / 6')
        self.y=H-60;self.p(title,18,'Bold',24);self.y-=5

    def p(self,text,size=9.3,font='Body',leading=None):
        p=Paragraph(text,ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.4,textColor=colors.HexColor('#202020')))
        _,h=p.wrap(CW,H)
        if self.y-h<46:raise ValueError(f'Página {self.page} excedida: {text[:60]} (y={self.y},h={h})')
        p.drawOn(self.c,M,self.y-h);self.y-=h+8

    def table(self,rows,widths=None,size=8.2):
        st=ParagraphStyle('t',fontName='Body',fontSize=size,leading=size*1.3)
        tt=Table([[Paragraph(escape(str(v)),st) for v in row] for row in rows],colWidths=widths or [CW/len(rows[0])]*len(rows[0]))
        tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee')),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#444444')),
                               ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#dddddd')),
                               ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                               ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        _,h=tt.wrap(CW,H)
        if self.y-h<46:raise ValueError(f'Tabela excedida na página {self.page}')
        tt.drawOn(self.c,M,self.y-h);self.y-=h+10

    def image(self,name,height):
        if self.y-height<46:raise ValueError(f'Figura excedida na página {self.page}')
        self.c.drawImage(str(OUT/'figures'/name),M,self.y-height,CW,height,preserveAspectRatio=True,anchor='c')
        self.y-=height+7


def build():
    s=json.loads((OUT/'summary.json').read_text(encoding='utf-8'))
    km=list(csv.DictReader((OUT/'kmeans_grid.csv').open(encoding='utf-8-sig')))
    db=list(csv.DictReader((OUT/'dbscan_grid.csv').open(encoding='utf-8-sig')))
    groups=s['groups'];total=sum(g['received_sat'] for g in groups)
    stream=io.BytesIO();r=Report(stream);c=r.c
    def center(y,text,size=11,font='Body'):
        c.setFillColor(colors.HexColor('#202020'));c.setFont(font,size);c.drawCentredString(W/2,y,text)
    center(H-115,'Tópicos Especiais de Segurança',12,'Bold')
    center(H-185,'Lucas Panonko Assis Belchior')
    center(H-205,'Matrícula: 12311BCC068',10)
    center(H/2+28,'Clusterização de endereços ilícitos',20,'Bold')
    center(H/2-3,'Aprendizado de máquina aplicado ao subconjunto de sextortion',9.5)
    center(H/2-67,'(P1) K-Means, DBSCAN e análise dos clusters',10)
    center(H/2-96,'Repositório do projeto',10,'Bold')
    center(H/2-115,REPO,8)
    c.linkURL(REPO,(M,H/2-120,W-M,H/2-105),relative=0)
    center(110,'11 de novembro de 2026',10)

    r.new('Objetivo, dados e preparação')
    r.p('01 / VISÃO GERAL',8.5,'Bold')
    r.p('Aplicar algoritmos de <b>clusterização</b> aos endereços do subconjunto de '
        '<i>sextortion</i> fornecido pela disciplina e analisar os grupos pelas '
        '<b>movimentações financeiras e pelo grafo das transações</b>. Foram usados '
        'K-Means e DBSCAN. Os algoritmos agrupam endereços parecidos; não recebem '
        'uma classificação pronta de cada endereço.')
    r.table([['Endereços analisados','Transações únicas','Período observado (UTC)'],
             [38,329,'09/09/2018 a 07/05/2021']],size=10)
    r.p('Dados utilizados',11,'Bold')
    r.p('O TAR contém 38 arquivos JSON em ENDERECOS/, um por endereço-alvo. Todos '
        'foram usados. Os arquivos somam 334 ocorrências: cinco são cópias idênticas '
        'de transações compartilhadas e foram removidas por <b>txId</b>, o identificador '
        'da transação. O agrupamento foi feito por endereço, e não por transação.')
    r.p('Os registros contêm entradas, saídas, valores em satoshis, taxa e horário. '
        'Para as 329 transações únicas, a soma das entradas menos a soma das saídas '
        'confere com a taxa informada. Não há registros marcados como mempool, '
        'endereços ausentes nas entradas/saídas nem cópias divergentes.')
    r.p('Como os atributos foram construídos',11,'Bold')
    r.table([['Atributo por endereço','Definição no recorte observado'],
             ['Recebimentos e gastos (2 atributos)','Contagem de transações com o endereço nas saídas e nas entradas, respectivamente.'],
             ['Total recebido','Soma dos valores das saídas destinadas ao endereço, em satoshis.'],
             ['Intervalo de atividade','Dias entre a primeira e a última transação observada do endereço.']],
            [CW*.37,CW*.63])
    r.p('Esses quatro atributos descrevem quantidade, valor e duração da atividade. '
        'O total gasto foi calculado para a análise financeira, mas ficou fora do '
        'modelo por ser quase igual ao recebido nesta base. Assim, o volume não '
        'entra duas vezes no agrupamento. O texto do endereço também não é usado '
        'para calcular a semelhança.',9)
    r.p('Limite dos dados',11,'Bold')
    r.p('Todos os arquivos informam limit=50 e offset=0, mas têm entre 2 e 58 '
        'transações. Portanto, não foi possível confirmar se os históricos estão '
        'completos. A análise usa apenas o arquivo entregue pela disciplina, sem '
        'consultar outras páginas ou serviços. A indicação de sextortion vem do '
        'enunciado, não de uma verificação de cada pagamento.',9)

    r.new('Métodos e comparação dos modelos')
    r.p('02 / CLUSTERIZAÇÃO NÃO SUPERVISIONADA',8.5,'Bold')
    r.p('Para cada um dos quatro atributos, foi aplicado <b>log(1+x)</b> '
        'e depois <b>StandardScaler</b> (média zero e desvio padrão unitário). '
        'O logaritmo reduz a diferença entre valores muito grandes e pequenos. '
        'A padronização coloca as medidas em escalas comparáveis, pois uma '
        'contagem de transações não tem a mesma unidade que um valor em satoshis [1].')
    r.p('K-Means',11,'Bold')
    r.p('Minimiza a soma das distâncias quadráticas aos centroides. Foram testados '
        '<b>k=2 a 6</b>, inicialização k-means++, n_init=10 e random_state=42. '
        'Isso significa testar de dois a seis grupos, com dez inicializações '
        'por tentativa. A semente fixa permite repetir o resultado. Foi escolhido '
        'o k com maior silhouette média [1, 2].')
    r.table([['k','2','3','4','5','6'],['Silhouette']+[n(float(v['silhouette']),3) for v in km]],
            [CW*.25]+[CW*.15]*5)
    r.p(f'Resultado: <b>k={s["kmeans"]["k"]}, silhouette={n(s["kmeans"]["silhouette"],3)}</b>, '
        f'com grupos de {groups[0]["n"]}, {groups[1]["n"]} e {groups[2]["n"]} endereços. '
        'A silhouette varia de -1 a 1; valores maiores indicam maior separação '
        'entre os grupos nas medidas usadas [2].',8.9)
    r.p('DBSCAN',11,'Bold')
    r.p('Agrupa regiões densas e marca pontos isolados como ruído. Testaram-se '
        '<b>eps=0,5; 1; 1,5; 2</b>, mantendo <b>min_samples=3</b>. '
        'O eps é o raio de vizinhança; min_samples=3 exige pelo menos três '
        'pontos nessa vizinhança, contando o próprio ponto, para formar um núcleo [1].',8.9)
    r.table([['eps','Clusters','Ruído','Silhouette*']]+[
        [n(float(v['eps']),1),v['clusters'],v['noise'],n(float(v['silhouette']),3) if v['silhouette'] else '-'] for v in db])
    r.p('Foi usado <b>eps=1,5</b>: ele mantém dois grupos e deixa cinco endereços '
        'como ruído. Com raios menores há mais ruído; com eps=2 resta só um '
        'grupo. Essa escolha serve para descrever a amostra, não como regra geral.',8.6)
    r.p('*Calculada sem os pontos de ruído; não é uma comparação direta com a '
        'silhouette do K-Means, que inclui todos os endereços.',8)
    r.image('clusters.png',155)
    r.p('Cada ponto é um endereço. O eixo do valor recebido tem escala logarítmica '
        'para mostrar valores de tamanhos diferentes. A figura mostra duas medidas, mas os '
        'algoritmos usam os quatro atributos. Pontos podem ficar sobrepostos.',8)

    r.new('Perfis dos clusters e análise financeira')
    r.p('03 / RESULTADOS OBSERVADOS',8.5,'Bold')
    r.p('Os grupos do K-Means foram chamados de C1, C2 e C3, em ordem crescente '
        'da mediana de recebimentos. A mediana representa o valor central entre '
        'os endereços de cada grupo.')
    r.table([['Grupo','n','Recebido (BTC)','Gasto (BTC)','Tx/endereço¹','Dias¹']]+[
        [g['cluster'],g['n'],n(g['received_sat']/1e8,8),n(g['spent_sat']/1e8,8),
         n(g['median_n_tx'],1),n(g['median_span_days'],1)] for g in groups],
        [CW*.09,CW*.06,CW*.26,CW*.26,CW*.18,CW*.15],7.8)
    r.p('¹ Medianas por endereço. Dias representam o intervalo observado, não dias com transações.',7.8)
    r.p(f'<b>C1 - baixo volume:</b> {groups[0]["n"]} endereços, mediana de '
        f'{n(groups[0]["median_n_tx"])} transações e '
        f'{n(groups[0]["median_received_sat"]/1e8,8)} BTC recebidos por endereço. '
        'O intervalo mediano de 145,1 dias é longo apesar da pouca atividade registrada.',9)
    r.p(f'<b>C2 - volume intermediário:</b> {groups[1]["n"]} endereços, mediana de '
        f'{n(groups[1]["median_n_tx"])} transações e '
        f'{n(groups[1]["median_received_sat"]/1e8,8)} BTC recebidos por endereço. '
        f'O intervalo mediano é de {n(groups[1]["median_span_days"],1)} dias. '
        'É o grupo que reúne a maioria dos endereços.',9)
    r.p(f'<b>C3 - maior movimentação:</b> {groups[2]["n"]} endereços concentram '
        f'<b>{n(groups[2]["received_sat"]/total*100,1)}%</b> do valor recebido pelos '
        f'alvos. A mediana é de {n(groups[2]["median_n_tx"])} transações e '
        f'{n(groups[2]["median_received_sat"]/1e8,8)} BTC recebidos por endereço.',9)
    r.image('finance.png',154)
    r.p('O total recebido pelos 38 endereços é <b>31,70598704 BTC</b>; o total '
        'gasto é <b>31,70582158 BTC</b>. A diferença contábil observada é '
        '<b>16.546 satoshis</b>. Essa diferença não pode ser tratada como saldo '
        'atual, pois os históricos podem ser incompletos. O gasto soma os valores '
        'das entradas do endereço, antes de descontar as taxas da transação.',8.8)
    r.p('Recebimentos são valores brutos de saídas para os alvos. Troco, '
        'reutilização e circulação entre endereços podem inflar o volume em '
        'relação ao dinheiro recebido de vítimas. Por isso, o total movimentado '
        'não foi tratado como lucro nem como valor comprovadamente extorquido.',8.8)
    r.p('Concordância entre algoritmos',10.5,'Bold')
    r.p('O DBSCAN reúne os 30 endereços de C2 em D0 e três dos cinco de C3 em '
        'D1. Os três de C1 e dois de C3 são ruído. Os métodos concordam sobre '
        'o grupo intermediário, mas tratam de forma diferente os endereços '
        'menos comuns. Ruído significa que o endereço não entrou em um grupo '
        'com os parâmetros usados.',8.8)

    r.new('Grafo das transações')
    r.p('04 / CONEXÕES E EXEMPLO REAL',8.5,'Bold')
    r.p('No grafo abaixo, cada nó é um dos 38 endereços-alvo, com cor do cluster '
        'K-Means. Uma aresta indica que dois alvos aparecem na <b>mesma transação</b>, '
        'nas entradas ou nas saídas. A ligação não tem direção e '
        '<b>não representa necessariamente pagamento entre os dois endereços</b>.')
    r.image('graph.png',186)
    r.p('IDs A01-A38 correspondem aos endereços completos em results/addresses.csv, '
        'gerado pelo código da análise. Cores: C1 azul, C2 laranja, C3 verde.',7.8)
    r.table([['Arestas','Componentes','Nós isolados','Maior componente'],[6,33,29,'3 endereços']],size=9)
    r.p('Há quatro arestas dentro de C2, uma dentro de C3 e uma entre C2 e C3. '
        'C1 não possui arestas. Os seis pares surgem de quatro transações '
        'distintas. Apesar da semelhança nas medidas usadas no agrupamento, '
        'a maioria dos endereços não aparece na mesma transação que outro alvo.',8.8)
    r.p('Endereço → transação → endereço',11,'Bold')
    r.image('example.png',149)
    r.p('Exemplo com três alvos em entradas: A02, A07 e A22, todos em C2. '
        'A figura agrega endereços que não são alvos como “Outros”; os rótulos '
        'em BTC são arredondados. São 20 endereços distintos nas entradas e '
        'um nas saídas. O nó TX mantém a transação entre as entradas e a saída.',8.5)
    r.p('Entrada total: <b>184.186.601 sat</b>; saída total: <b>183.981.683 sat</b>; '
        'taxa: <b>204.918 sat</b>. A diferença confere com o JSON original. '
        'A presença conjunta dos três alvos mostra consolidação de valores '
        'nesta transação, sem provar controle pela mesma pessoa.',8.5)
    r.p('txId: '+s['example']['txid'][:32]+'<br/>'+s['example']['txid'][32:],7.7,'Mono')

    r.new('Conclusão e referências')
    r.p('05 / CONCLUSÃO',8.5,'Bold')
    r.p('O K-Means separou os 38 endereços em três grupos: baixo volume, '
        'volume intermediário e maior movimentação. O grupo intermediário '
        'reúne 30 endereços, enquanto os cinco do grupo mais ativo concentram '
        f'{n(groups[2]["received_sat"]/total*100,1)}% do valor recebido. '
        'O DBSCAN também reuniu os 30 intermediários, formou outro grupo com '
        'três endereços e deixou cinco como ruído.')
    r.p('O grafo acrescenta uma informação diferente: há apenas seis ligações '
        'entre os alvos, e 29 endereços estão isolados. Estar no mesmo cluster '
        'indica semelhança nas medidas analisadas, mas não prova que os '
        'endereços fizeram transações entre si ou pertencem à mesma pessoa.')
    r.p('Limitações',11,'Bold')
    r.p('Foram analisados apenas 38 endereços do arquivo da disciplina. Os '
        'históricos podem ser incompletos, e os resultados dependem dos '
        'atributos e parâmetros escolhidos. As tentativas foram comparadas '
        'nessa mesma base; não houve validação com outra amostra. A silhouette '
        'mede a separação entre os grupos, não se o agrupamento identifica '
        'corretamente campanhas de sextortion [1, 2].')
    r.p('Os outros 7.168 endereços que aparecem nas transações não foram '
        'classificados como ilícitos. Também não há dados para identificar '
        'vítimas, confirmar autoria ou calcular quanto foi obtido com extorsão.')
    r.p('Como repetir a análise',11,'Bold')
    r.p(f'Código e instruções: <link href="{REPO}">{REPO}</link>.',8.2)
    r.p('Para reproduzir, é necessário ter Python e o ExercCluster.tgz original. '
        'Após instalar requirements.txt, executar analyze.py, build_report.py e '
        'verify.py. As tabelas e figuras são geradas na pasta results/.',8.8)
    r.p('SHA-256 do ExercCluster.tgz:',8,'Bold')
    r.p(s['archive_sha256'][:32]+'<br/>'+s['archive_sha256'][32:],7.8,'Mono')
    r.p('Referências',10.5,'Bold')
    r.p('[1] SCIKIT-LEARN. Clustering: K-Means, DBSCAN e avaliação. '
        '<link href="https://scikit-learn.org/stable/modules/clustering.html">'
        'scikit-learn.org/stable/modules/clustering.html</link>.<br/>'
        '[2] SCIKIT-LEARN. silhouette_score. '
        '<link href="https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html">'
        'scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html</link>.<br/>'
        '[3] Enunciado “(P1) Clusterização (ML) de endereços ilícitos” e '
        'ExercCluster.tgz fornecidos pela disciplina. Documentação consultada em 11/11/2026.',7.3)
    r.bottoms[r.page]=r.y;r.c.save()
    assert r.page==6
    writer=PdfWriter();writer.append(PdfReader(stream))
    writer.add_metadata({'/Title':'Clusterização (ML) de endereços ilícitos - Sextortion',
                         '/Author':'Lucas Panonko Assis Belchior','/Subject':'ESP_SEC - (P1) - K-Means, DBSCAN, grafo e finanças'})
    dest=ROOT/'report/Clusterizacao_ML_Lucas_Belchior.pdf';dest.parent.mkdir(exist_ok=True)
    with dest.open('wb') as f:writer.write(f)
    print(json.dumps(dict(pdf=str(dest),pages=r.page,bottoms=r.bottoms,attachments=0),indent=2))


if __name__=='__main__':build()
