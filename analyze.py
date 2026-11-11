"""Análise reproduzível dos endereços fornecidos em ExercCluster.tgz."""
import csv
import hashlib
import itertools
import json
import platform
import tarfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import sklearn
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results'
FEATURES = ['incoming_tx', 'outgoing_tx', 'received_sat', 'span_days']
COLORS = ['#335f80', '#b35b32', '#558657', '#8663a0', '#b49a37', '#444444']


def write_csv(name, rows):
    with (OUT/name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def load(archive):
    docs, txs, occurrences = {}, {}, 0
    with tarfile.open(archive) as t:
        for m in sorted(t.getmembers(), key=lambda m:m.name):
            if not m.isfile(): continue
            address = Path(m.name).name
            assert address not in docs
            d = json.load(t.extractfile(m)); docs[address] = d
            assert d['offset'] == 0
            assert len({tx['txId'] for tx in d['transactions']}) == len(d['transactions'])
            for tx in d['transactions']:
                assert any(x.get('address') == address for x in tx['inputs']+tx['outputs'])
                h = tx['txId']; occurrences += 1
                if h in txs: assert txs[h] == tx, 'Cópias divergentes'
                txs[h] = tx
    for tx in txs.values():
        assert not tx['mempool']
        assert all(isinstance(x['value'], int) and x['value'] >= 0 for x in tx['inputs']+tx['outputs'])
        assert sum(x['value'] for x in tx['inputs'])-sum(x['value'] for x in tx['outputs']) == tx['fee']
    return docs, txs, occurrences


def analyze():
    OUT.mkdir(exist_ok=True); (OUT/'figures').mkdir(exist_ok=True)
    archive = ROOT.parent/'ExercCluster.tgz'
    docs, txs, occurrences = load(archive)
    seeds = sorted(docs)
    rows = []
    for idx, a in enumerate(seeds, 1):
        # Use a união deduplicada, inclusive transações eventualmente presentes em outro arquivo.
        relevant = [tx for tx in txs.values() if any(x.get('address')==a for x in tx['inputs']+tx['outputs'])]
        incoming = [tx for tx in relevant if any(x.get('address')==a for x in tx['outputs'])]
        outgoing = [tx for tx in relevant if any(x.get('address')==a for x in tx['inputs'])]
        recv = sum(x['value'] for tx in relevant for x in tx['outputs'] if x.get('address')==a)
        spent = sum(x['value'] for tx in relevant for x in tx['inputs'] if x.get('address')==a)
        times = [tx['time'] for tx in relevant]
        rows.append(dict(id=f'A{idx:02d}',address=a,source_transactions=len(docs[a]['transactions']),
                         n_tx=len(relevant),incoming_tx=len(incoming),outgoing_tx=len(outgoing),
                         received_sat=recv,spent_sat=spent,net_sat=recv-spent,
                         span_days=(max(times)-min(times))/86400,
                         first_utc=datetime.fromtimestamp(min(times),timezone.utc).isoformat(),
                         last_utc=datetime.fromtimestamp(max(times),timezone.utc).isoformat()))
    raw = np.array([[r[f] for f in FEATURES] for r in rows],dtype=float)
    scaler = StandardScaler(); X = scaler.fit_transform(np.log1p(raw))
    km_grid, models = [], {}
    for k in range(2,7):
        model = KMeans(n_clusters=k,random_state=42,n_init=10).fit(X)
        models[k] = model
        km_grid.append(dict(k=k,silhouette=float(silhouette_score(X,model.labels_)),
                            inertia=float(model.inertia_),sizes=';'.join(map(str,np.bincount(model.labels_)))))
    best = max(km_grid,key=lambda x:x['silhouette']); model = models[best['k']]
    # Números estáveis: C1 é o grupo com menor mediana de recebimentos.
    order = sorted(set(model.labels_),key=lambda c:np.median(raw[model.labels_==c,2]))
    mapping = {old:new for new,old in enumerate(order)}
    labels = np.array([mapping[c] for c in model.labels_])
    db_grid = []
    # Comparação pequena de raios; min_samples=3 é fixo por serem apenas 38 endereços.
    for eps in [0.5,1.0,1.5,2.0]:
        lb = DBSCAN(eps=eps,min_samples=3).fit_predict(X)
        mask = lb>=0; nc = len(set(lb[mask]))
        sil = float(silhouette_score(X[mask],lb[mask])) if 2<=nc<sum(mask) else None
        db_grid.append(dict(eps=eps,min_samples=3,clusters=nc,noise=int(sum(~mask)),
                            coverage=float(np.mean(mask)),silhouette=sil))
    # eps=1,5 mantém dois grupos e deixa menos ruído que os raios menores.
    # É uma escolha para descrever esta amostra, não um parâmetro universal.
    dbbest = next(d for d in db_grid if d['eps']==1.5)
    dblabels = DBSCAN(eps=1.5,min_samples=3).fit_predict(X)
    for r,lb,db in zip(rows,labels,dblabels): r['kmeans']=f'C{lb+1}'; r['dbscan']=int(db)
    # Projeção de coparticipação: uma aresta NÃO é uma transferência endereço-endereço.
    graph = nx.Graph(); graph.add_nodes_from(seeds)
    memberships = {}
    for h,tx in txs.items():
        involved = sorted(set(x['address'] for x in tx['inputs']+tx['outputs']) & set(seeds))
        memberships[h] = involved
        for a,b in itertools.combinations(involved,2):
            if not graph.has_edge(a,b): graph.add_edge(a,b,transactions=[])
            graph[a][b]['transactions'].append(h)
    edges = [dict(a=a,b=b,shared_transactions=len(v['transactions']),txids=';'.join(v['transactions'])) for a,b,v in graph.edges(data=True)]
    if edges: write_csv('shared_transactions.csv',edges)
    groups = []
    for c in sorted(set(labels)):
        rr = [r for r in rows if r['kmeans']==f'C{c+1}']
        aa = [r['address'] for r in rr]; g=graph.subgraph(aa)
        groups.append(dict(cluster=f'C{c+1}',n=len(rr),received_sat=sum(r['received_sat'] for r in rr),
                           spent_sat=sum(r['spent_sat'] for r in rr),net_sat=sum(r['net_sat'] for r in rr),
                           median_received_sat=float(np.median([r['received_sat'] for r in rr])),
                           median_n_tx=float(np.median([r['n_tx'] for r in rr])),
                           median_span_days=float(np.median([r['span_days'] for r in rr])),
                           edges=g.number_of_edges(),isolates=len(list(nx.isolates(g)))))
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':180})
    fig,axs=plt.subplots(1,2,figsize=(9,2.7))
    for ax,lbs,title in [(axs[0],labels,'K-Means'),(axs[1],dblabels,'DBSCAN')]:
        for c in sorted(set(lbs)):
            mask=lbs==c; color='#999999' if c==-1 else COLORS[c%len(COLORS)]
            label=('Ruído' if c==-1 else f'C{c+1}' if title=='K-Means' else f'D{c}')
            ax.scatter(raw[mask,2]/1e8,np.array([r['n_tx'] for r in rows])[mask],s=35,c=color,label=label,edgecolor='white',linewidth=.4)
        ax.set_xscale('log')
        ax.set_xticks([.0001,.001,.01,.1,1,10],['0,0001','0,001','0,01','0,1','1','10'])
        ax.minorticks_off()
        ax.set_yticks([0,20,40,60])
        ax.set_ylim(0,65)
        ax.set(title=title,xlabel='Total recebido (BTC, escala log)',ylabel='Número de transações')
        ax.legend(frameon=False,fontsize=7)
    fig.tight_layout(); fig.savefig(OUT/'figures/clusters.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.4)); pos=nx.spring_layout(graph,seed=42,k=.6)
    nx.draw_networkx_edges(graph,pos,ax=ax,edge_color='#777777',width=1.3)
    nx.draw_networkx_nodes(graph,pos,ax=ax,node_color=[COLORS[c] for c in labels],node_size=270,edgecolors='white')
    nx.draw_networkx_labels(graph,pos,ax=ax,labels={r['address']:r['id'] for r in rows},font_size=7,font_color='white')
    ax.set_axis_off(); fig.tight_layout();fig.savefig(OUT/'figures/graph.png');plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(9,2.8))
    axs[0].bar([g['cluster'] for g in groups],[g['received_sat']/1e8 for g in groups],color=COLORS[:len(groups)])
    axs[0].set(ylabel='BTC recebidos (bruto observado)',xlabel='Cluster K-Means')
    axs[1].bar([g['cluster'] for g in groups],[g['median_n_tx'] for g in groups],color=COLORS[:len(groups)])
    axs[1].set(ylabel='Mediana de transações por endereço',xlabel='Cluster K-Means')
    fig.tight_layout();fig.savefig(OUT/'figures/finance.png');plt.close(fig)
    # Exemplo real com o máximo de endereços-alvo em uma transação.
    example_id=max(sorted(txs),key=lambda h:len(memberships[h])); example=txs[example_id]
    eg=nx.DiGraph(); values={}
    for side in ['inputs','outputs']:
        for x in example[side]:
            a=x['address']; key=(side,a);values[key]=values.get(key,0)+x['value']
    # Grafo legível: exibe todos os alvos e agrega endereços de contexto por lado.
    for side in ['inputs','outputs']:
        for (s,a),v in values.items():
            if s!=side: continue
            node=(side,a if a in seeds else 'Outros')
            edge=(node,'TX') if side=='inputs' else ('TX',node)
            if not eg.has_edge(*edge):eg.add_edge(*edge,value=0)
            eg.edges[edge]['value']+=v
    ep={'TX':(0,0)}; el={'TX':'TX'}
    for side,x in [('inputs',-1),('outputs',1)]:
        ns=[n for n in eg if isinstance(n,tuple) and n[0]==side]
        for node,y in zip(ns,np.linspace(-1,1,len(ns)) if len(ns)>1 else [0]):
            ep[node]=(x,float(y)); a=node[1]
            el[node]=next((r['id'] for r in rows if r['address']==a),'Outros')
    fig,ax=plt.subplots(figsize=(9,2.8))
    nx.draw_networkx(eg,ep,ax=ax,labels=el,node_color='#eeeeee',node_size=850,font_size=9,arrowsize=15)
    nx.draw_networkx_edge_labels(eg,ep,ax=ax,edge_labels={(u,v):f"{d['value']/1e8:.4f} BTC" for u,v,d in eg.edges(data=True)},font_size=7)
    ax.set_xlim(-1.5,1.5);ax.set_ylim(-1.4,1.4);ax.set_axis_off();fig.tight_layout();fig.savefig(OUT/'figures/example.png');plt.close(fig)
    dates=[tx['time'] for tx in txs.values()]
    summary=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),addresses=len(rows),
                 occurrences=occurrences,transactions=len(txs),duplicates=occurrences-len(txs),
                 date_min=datetime.fromtimestamp(min(dates),timezone.utc).isoformat(),
                 date_max=datetime.fromtimestamp(max(dates),timezone.utc).isoformat(),
                 source_limit_counts=dict(Counter(d['limit'] for d in docs.values())),source_offset=0,
                 added_by_union=sum(r['n_tx']-r['source_transactions'] for r in rows),
                 context_addresses=len({x['address'] for tx in txs.values() for x in tx['inputs']+tx['outputs']}),
                 features=FEATURES,scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
                 kmeans=best,dbscan=dbbest,groups=groups,
                 graph_edges=graph.number_of_edges(),graph_components=nx.number_connected_components(graph),
                 graph_isolates=len(list(nx.isolates(graph))),
                 graph_largest_component=max(map(len,nx.connected_components(graph))),
                 graph_within_edges=sum(rows[seeds.index(a)]['kmeans']==rows[seeds.index(b)]['kmeans'] for a,b in graph.edges()),
                 example=dict(txid=example_id,seed_ids=[r['id'] for r in rows if r['address'] in memberships[example_id]],
                              fee_sat=example['fee'],input_sat=sum(x['value'] for x in example['inputs']),
                              output_sat=sum(x['value'] for x in example['outputs']),
                              input_addresses=len({x['address'] for x in example['inputs']}),
                              output_addresses=len({x['address'] for x in example['outputs']})),
                 versions=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__,
                               networkx=nx.__version__,matplotlib=matplotlib.__version__))
    write_csv('addresses.csv',rows);write_csv('clusters.csv',groups)
    write_csv('kmeans_grid.csv',km_grid);write_csv('dbscan_grid.csv',db_grid)
    write_csv('transactions.csv',[dict(txid=h,time=tx['time'],fee_sat=tx['fee'],input_sat=sum(x['value'] for x in tx['inputs']),output_sat=sum(x['value'] for x in tx['outputs']),seed_addresses=';'.join(memberships[h])) for h,tx in sorted(txs.items())])
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))


if __name__=='__main__': analyze()
