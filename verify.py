"""Reconferência independente dos CSVs diretamente no arquivo fornecido."""
import csv
import hashlib
import io
import json
import tarfile
import zipfile
from itertools import combinations
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def verify():
    out=ROOT/'results'
    s=json.loads((out/'summary.json').read_text(encoding='utf-8'))
    rows=list(csv.DictReader((out/'addresses.csv').open(encoding='utf-8-sig')))
    archive=ROOT.parent/'ExercCluster.tgz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==s['archive_sha256']
    txs={};addresses=set();occurrences=0
    with tarfile.open(archive) as t:
        for m in t:
            if not m.isfile():continue
            a=Path(m.name).name;addresses.add(a)
            for tx in json.load(t.extractfile(m))['transactions']:
                occurrences+=1
                if tx['txId'] in txs: assert txs[tx['txId']]==tx
                txs[tx['txId']]=tx
    assert len(rows)==len(addresses)==38
    assert {r['address'] for r in rows}==addresses
    assert len({r['id'] for r in rows})==38
    assert len(txs)==s['transactions']==329 and occurrences==334
    for r in rows:
        a=r['address'];incoming=set();outgoing=set();observed=set();rec=spent=0;times=[]
        for h,tx in txs.items():
            iv=sum(x['value'] for x in tx['inputs'] if x['address']==a)
            ov=sum(x['value'] for x in tx['outputs'] if x['address']==a)
            hasin=any(x['address']==a for x in tx['inputs'])
            hasout=any(x['address']==a for x in tx['outputs'])
            if hasin:
                outgoing.add(h);spent+=iv
            if hasout: incoming.add(h);rec+=ov
            if hasin or hasout:observed.add(h);times.append(tx['time'])
        assert int(r['received_sat'])==rec and int(r['spent_sat'])==spent
        assert int(r['net_sat'])==rec-spent
        assert int(r['n_tx'])==len(observed)
        assert int(r['incoming_tx'])==len(incoming) and int(r['outgoing_tx'])==len(outgoing)
        assert abs(float(r['span_days'])-(max(times)-min(times))/86400)<1e-9
    for g in s['groups']:
        rr=[r for r in rows if r['kmeans']==g['cluster']]
        assert len(rr)==g['n']
        for key in ['received_sat','spent_sat','net_sat']:assert sum(int(r[key]) for r in rr)==g[key]
    edges=set();shared_tx=0
    for tx in txs.values():
        aa=sorted(addresses & {x['address'] for x in tx['inputs']+tx['outputs']})
        edges.update(combinations(aa,2));shared_tx+=len(aa)>1
        assert sum(x['value'] for x in tx['inputs'])-sum(x['value'] for x in tx['outputs'])==tx['fee']
    assert len(edges)==s['graph_edges']==6 and shared_tx==4
    ex=txs[s['example']['txid']]
    assert sum(x['value'] for x in ex['inputs'])==s['example']['input_sat']
    assert sum(x['value'] for x in ex['outputs'])==s['example']['output_sat']
    assert ex['fee']==s['example']['fee_sat']
    assert sum(int(r['received_sat']) for r in rows)==3170598704
    assert sum(int(r['spent_sat']) for r in rows)==3170582158
    # Recalcula os modelos para detectar CSVs ou resumos de uma execução antiga.
    import numpy as np
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    features=['incoming_tx','outgoing_tx','received_sat','span_days']
    assert s['features']==features
    X=StandardScaler().fit_transform(np.log1p([[float(r[f]) for f in features] for r in rows]))
    scores={}
    for k in range(2,7):
        labels=KMeans(n_clusters=k,random_state=42,n_init=10).fit_predict(X)
        scores[k]=silhouette_score(X,labels)
    assert max(scores,key=scores.get)==s['kmeans']['k']==3
    assert abs(scores[3]-s['kmeans']['silhouette'])<1e-10
    labels=KMeans(n_clusters=3,random_state=42,n_init=10).fit_predict(X)
    for i in range(len(rows)):
        for j in range(len(rows)):
            assert (labels[i]==labels[j])==(rows[i]['kmeans']==rows[j]['kmeans'])
    db=DBSCAN(eps=1.5,min_samples=3).fit_predict(X)
    assert all(int(r['dbscan'])==int(label) for r,label in zip(rows,db))
    assert sum(db==-1)==s['dbscan']['noise']==5
    mask=db>=0
    assert abs(silhouette_score(X[mask],db[mask])-s['dbscan']['silhouette'])<1e-10
    report=dict(status='passed',addresses_checked=38,unique_transactions_checked=329,
                fees_checked=329,shared_transaction_edges_checked=6,shared_transactions=4,
                total_received_sat=3170598704,total_spent_sat=3170582158,
                archive_sha256=s['archive_sha256'],example_txid=ex['txId'],
                kmeans_recomputed=True,dbscan_recomputed=True)
    pdf=ROOT/'report/Clusterizacao_ML_Lucas_Belchior.pdf'
    if pdf.exists():
        from pypdf import PdfReader
        reader=PdfReader(pdf)
        assert len(reader.pages)==6
        text='\n'.join(p.extract_text() or '' for p in reader.pages)
        assert all(term in text for term in ['K-Means','DBSCAN','31,70598704','16.546','0,469','Referências'])
        assert all(term not in text for term in ['ARI','PCA','n_init=50','0,504','31 endereços'])
        repo='https://github.com/LuksbellN/Clusteriza-o-ML-de-endere-os-ilicitos'
        for page in [reader.pages[0],reader.pages[-1]]:
            assert any(a.get_object().get('/A',{}).get('/URI')==repo for a in page.get('/Annots',[]))
        assert 'Clusterizacao_ML_reproducao.zip' in reader.attachments
        with zipfile.ZipFile(io.BytesIO(reader.attachments['Clusterizacao_ML_reproducao.zip'][0])) as z:
            assert all(f in z.namelist() for f in ['analyze.py','build_report.py','verify.py','README.md','results/addresses.csv'])
            for name in z.namelist():
                if name!='results/verification.json':assert z.read(name)==(ROOT/name).read_bytes(),name
        report.update(pdf_pages=6,pdf_text_checked=True,pdf_attachment_checked=True)
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':verify()
