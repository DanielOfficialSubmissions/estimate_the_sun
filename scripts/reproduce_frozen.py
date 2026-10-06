"""Refit the frozen winner from official inputs; never reselect on lockbox scores."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import solar
import pandas as pd

root=Path(__file__).resolve().parents[1]
start=time.monotonic()
train,test,hashes=solar.load_data(root/'data/raw')
original=root/'artifacts/official'
selection=json.loads((original/'selection.json').read_text())
completed=json.loads((original/'completed.json').read_text())
if solar.provenance(hashes)!=selection['provenance'] or solar.digest(original/'selection.json')!=completed['selection_sha256']:
    raise ValueError('Code, input, environment or frozen selection differs')
model=solar.fit(train,selection['config'])
pred=solar.predict(model,test,selection['config'])
out=root/'artifacts/reproduction';out.mkdir(parents=True,exist_ok=True)
path=out/'submission.csv'
pd.DataFrame({'id':test.id,solar.TARGET:pred}).to_csv(path,index=False,float_format='%.8f')
validation=solar.validate_submission(path,test)
if validation['sha256']!=completed['submission']['sha256']:
    raise ValueError('Freshly trained model did not reproduce the original CSV byte for byte')
report={'status':'passed','fresh_fit_from_official_training_data':True,'lockbox_reselection':False,
        'loaded_existing_model':False,'submission_sha256':validation['sha256'],
        'source_sha256':solar.digest(root/'src/solar.py'),'input_sha256':hashes,
        'elapsed_seconds':time.monotonic()-start,'rows':len(test)}
solar.write_json(root/'reports/reproduction.json',report)
print(json.dumps(report,indent=2))
