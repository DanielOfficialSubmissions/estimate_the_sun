"""Post-selection diagnostics only; does not fit or choose models."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import solar
import numpy as np
import pandas as pd

root=Path(__file__).resolve().parents[1]
train,test,hashes=solar.load_data(root/'data/raw')
out=root/'artifacts/official'
selection=json.loads((out/'selection.json').read_text())
name=selection['selected']
report={'purpose':'Post-selection error analysis; no changes to model or predictions','splits':{}}
for split in ['development','lockbox']:
    saved=pd.read_csv(out/f'{split}_{name}_predictions.csv',dtype={'id':'string'})
    z=train.merge(saved[['id','prediction']],on='id',how='inner',validate='one_to_one')
    base=pd.read_csv(out/f'{split}_climatology_predictions.csv',dtype={'id':'string'})
    z=z.merge(base[['id','prediction']].rename(columns={'prediction':'baseline'}),on='id',validate='one_to_one')
    z['error']=(z.prediction-z[solar.TARGET]).abs()
    z['bias']=z.prediction-z[solar.TARGET]
    z['baseline_error']=(z.baseline-z[solar.TARGET]).abs()
    z['ghi_mean']=z[[f'{p}_ghi' for p in solar.POINTS]].mean(axis=1)
    z['irradiance_bin']=pd.cut(z.ghi_mean,[-np.inf,0,100,400,np.inf],labels=['zero_mean_ghi','0_to_100','100_to_400','over_400'])
    z['cloud_bin']=pd.cut(z[[f'{p}_cloud_pct' for p in solar.POINTS]].mean(axis=1),[-np.inf,25,75,np.inf],labels=['0_to_25','25_to_75','over_75'])
    z['minute']=z[solar.DATE].dt.minute
    summary={'rows':len(z),'mae_mw':float(z.error.mean()),'bias_mw':float(z.bias.mean()),
             'error_quantiles_mw':{str(q):float(z.error.quantile(q)) for q in [.5,.9,.95,.99,1]},'segments':{}}
    for key in ['irradiance_bin','cloud_bin','minute']:
        rows=[]
        for group,part in z.groupby(key,observed=True):
            rows.append({'segment':str(group),'rows':len(part),'mae_mw':float(part.error.mean()),
                         'bias_mw':float(part.bias.mean()),'baseline_mae_mw':float(part.baseline_error.mean())})
        summary['segments'][key]=rows
    summary['zero_target_prediction_mae_mw']=float(z.loc[z[solar.TARGET]==0,'error'].mean())
    summary['zero_target_rows']=int((z[solar.TARGET]==0).sum())
    # Complete days are the uncertainty unit. This ignores cross-day correlation,
    # so describe interval as a sensitivity diagnostic, not a universal guarantee.
    daily=z.groupby(z[solar.DATE].dt.floor('D'))[['error','baseline_error']].sum()
    counts=z.groupby(z[solar.DATE].dt.floor('D')).size().to_numpy()
    rng=np.random.default_rng(solar.SEED)
    ix=rng.integers(0,len(daily),size=(2000,len(daily)))
    gain=(daily.baseline_error.to_numpy()[ix].sum(axis=1)-daily.error.to_numpy()[ix].sum(axis=1))/counts[ix].sum(axis=1)
    summary['paired_day_bootstrap_gain_95_percent_mw']=np.quantile(gain,[.025,.975]).tolist()
    summary['bootstrap_note']='2000 day resamples; ignores cross-day correlation; diagnostic only'
    report['splits'][split]=summary
solar.write_json(root/'reports/error_analysis.json',report)
print(json.dumps(report,indent=2))
