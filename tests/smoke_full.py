"""End-to-end software-only fixture: official schema/calendar, fabricated values.
Runs in a temporary directory; never creates a deliverable competition submission.
"""
import contextlib
import hashlib
import io
import json
import platform
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import solar
import numpy as np
import pandas as pd


def fixture(start,end,prefix):
    t=pd.date_range(start,end,freq='30min',inclusive='left',tz='UTC')
    hour=t.hour.to_numpy()
    daylight=np.maximum(0,np.sin((hour-6)*np.pi/12))
    seasonal=0.7+0.3*np.cos((t.dayofyear.to_numpy()-172)*2*np.pi/365.2425)
    d={'id':pd.Series([f'SYNTHETIC_{prefix}_{i}' for i in range(len(t))],dtype='string'),solar.DATE:t,
       solar.CAP:14000+(t.year.to_numpy()-2022)*800}
    for j,p in enumerate(solar.POINTS):
        for k in solar.KINDS:
            d[f'{p}_{k}']= daylight*seasonal*(500+j) if k in ['ghi','clearsky'] else np.full(len(t),20+j)
    df=pd.DataFrame(d)
    df[solar.TARGET]=daylight*seasonal*df[solar.CAP]*0.3
    df.loc[::997,solar.WEATHER[0]]=np.nan
    return df.sample(frac=1,random_state=solar.SEED)


def main():
    start=time.monotonic()
    # Deliberately cheap; quality of fabricated predictions is meaningless.
    solar.TREE_PARAMS['max_iter']=12
    checks=[]
    with tempfile.TemporaryDirectory(prefix='solar_software_only_') as tmp:
        root=Path(tmp);data=root/'data';data.mkdir();out=root/'outputs';out.mkdir();log=root/'experiments.csv'
        train=fixture('2022-01-01','2025-07-01','train')
        test=fixture('2025-07-01','2026-07-01','test').drop(columns=solar.TARGET)
        train.to_csv(data/'train.csv',index=False);test.to_csv(data/'test.csv',index=False)
        pd.DataFrame({'id':test.id,solar.TARGET:0}).to_csv(data/'sample_submission.csv',index=False)
        loaded,test_loaded,hashes=solar.load_data(data)
        solar.audit(loaded,test_loaded,out,hashes)
        checks.append('full schema, shuffled IDs, exact official calendar, missing weather and audit-before-run')
        with contextlib.redirect_stdout(io.StringIO()):solar.run(data,out,log)
        first=solar.digest(out/'submission.csv')
        checks.append('all candidate fits, frozen selection, lockbox fits, full refit, model reload, submission validation')
        # Missing journal is recovered without re-training or new lockbox use.
        original_log=pd.read_csv(log)
        log.unlink()
        original_fit=solar.fit
        def forbidden_fit(*args,**kwargs):
            raise AssertionError('Resume must not fit models')
        solar.fit=forbidden_fit
        try:
            with contextlib.redirect_stdout(io.StringIO()):solar.run(data,out,log)
        finally:
            solar.fit=original_fit
        assert solar.digest(out/'submission.csv')==first
        assert len(pd.read_csv(log))==len(original_log)
        checks.append('idempotent resume and journal recovery without changed predictions')
        selected=json.loads((out/'selection.json').read_text())
        log_hash=solar.digest(log)
        selected['policy']='tampered'
        solar.write_json(out/'selection.json',selected)
        try:
            with contextlib.redirect_stdout(io.StringIO()):solar.run(data,out,log)
            raise AssertionError('tamper not rejected')
        except ValueError as exc:
            assert 'Selection changed' in str(exc)
        assert solar.digest(log)==log_hash
        checks.append('tampered frozen selection rejected without changing journal')
    report={'status':'passed','data':'FABRICATED SOFTWARE FIXTURES ONLY — no competition score',
            'checks':checks,'elapsed_seconds':time.monotonic()-start,'python':platform.python_version(),
            'max_threads':2,'smoke_tree_iterations':12,
            'synthetic_files':'temporary directory deleted; no synthetic submission retained'}
    solar.write_json(Path(__file__).resolve().parents[1]/'reports/synthetic_smoke.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
