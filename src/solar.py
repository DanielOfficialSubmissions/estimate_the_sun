"""Offline, chronological solar estimation. Never downloads training data."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path

# Limit training centrally, before importing numerical libraries.
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '2'
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

SEED = 20261006
POINTS = 'london birmingham manchester leeds bristol norwich southampton plymouth cardiff newcastle glasgow edinburgh'.split()
KINDS = ['ghi', 'clearsky', 'temp_c', 'cloud_pct', 'wind_ms', 'rh_pct']
WEATHER = [f'{p}_{k}' for p in POINTS for k in KINDS]
TARGET, CAP, DATE = 'generation_mw', 'installed_capacity_mwp', 'datetime_utc'
DEV_START, LOCK_START, TEST_START = '2023-07-01', '2024-07-01', '2025-07-01'
CONFIGS = {
    'climatology': {'kind': 'climatology', 'hypothesis': 'Monthly half-hour capacity-factor mean baseline'},
    'hgb_mw': {'kind': 'hgb', 'normalized': False, 'engineered': False, 'hypothesis': 'Weather and calendar boosted-tree reference in MW'},
    'hgb_capacity': {'kind': 'hgb', 'normalized': True, 'engineered': False, 'hypothesis': 'Capacity normalization improves extrapolation as installed capacity grows'},
    'hgb_features': {'kind': 'hgb', 'normalized': True, 'engineered': True, 'hypothesis': 'Cyclic calendar and weather aggregates improve seasonal robustness'},
}
TREE_PARAMS = dict(loss='absolute_error', max_iter=180, learning_rate=0.07,
                   max_leaf_nodes=31, min_samples_leaf=30, l2_regularization=1.0,
                   early_stopping=False, random_state=SEED)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    temp.replace(path)


def read_csv(path):
    # Check original headers before pandas can silently mangle duplicates.
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        header = next(csv.reader(f))
    if len(set(header)) != len(header):
        raise ValueError(f'{path}: duplicate column names')
    return pd.read_csv(path, dtype={'id': 'string'})


def validate_frame(df, training, strict=True):
    expected = {'id', DATE, CAP, *WEATHER} | ({TARGET} if training else set())
    if set(df.columns) != expected:
        raise ValueError(f'Unexpected schema: missing={expected-set(df.columns)}, extra={set(df.columns)-expected}')
    df = df.copy()
    if df.id.isna().any() or df.id.duplicated().any() or (df.id.str.strip() == '').any():
        raise ValueError('IDs must be nonempty and unique')
    # Field is explicitly UTC, so timezone-naive values in this named field mean UTC.
    df[DATE] = pd.to_datetime(df[DATE], utc=True, errors='raise')
    if df[DATE].isna().any() or df[DATE].duplicated().any():
        raise ValueError('Timestamps must be nonempty and unique')
    if not ((df[DATE].dt.minute % 30 == 0) & (df[DATE].dt.second == 0) & (df[DATE].dt.microsecond == 0)).all():
        raise ValueError('Timestamps must be on half-hour boundaries')
    numeric = [CAP, *WEATHER] + ([TARGET] if training else [])
    df[numeric] = df[numeric].apply(pd.to_numeric, errors='raise')
    df[WEATHER] = df[WEATHER].replace(-999, np.nan)
    if np.isinf(df[numeric].to_numpy()).any():
        raise ValueError('Infinite numeric input')
    if not (np.isfinite(df[CAP]) & (df[CAP] > 0)).all():
        raise ValueError('Installed capacity must be positive and finite')
    if training and not (np.isfinite(df[TARGET]) & (df[TARGET] >= 0)).all():
        raise ValueError('Target must be finite and nonnegative')
    if strict:
        start, end = ('2022-01-01', TEST_START) if training else (TEST_START, '2026-07-01')
        expected_dates = pd.date_range(start, end, inclusive='left', freq='30min', tz='UTC')
        if not pd.DatetimeIndex(df[DATE].sort_values()).equals(expected_dates):
            raise ValueError(f'Unexpected time coverage or missing rows: expected {len(expected_dates)} half-hours')
    return df


def load_data(data_dir):
    data_dir = Path(data_dir)
    names = ['train.csv', 'test.csv', 'sample_submission.csv']
    missing = [n for n in names if not (data_dir/n).is_file()]
    if missing:
        raise ValueError('Official files required in data/raw: ' + ', '.join(missing) + '. Download through the authorized competition account; never retrieve withheld targets.')
    train = validate_frame(read_csv(data_dir/'train.csv'), True)
    test = validate_frame(read_csv(data_dir/'test.csv'), False)
    if set(train.id) & set(test.id):
        raise ValueError('Train/test IDs overlap')
    sample = read_csv(data_dir/'sample_submission.csv')
    if set(sample.columns) != {'id', TARGET} or sample.id.isna().any() or sample.id.duplicated().any() or set(sample.id) != set(test.id):
        raise ValueError('Sample submission does not match test IDs/schema')
    return train.sort_values(DATE).reset_index(drop=True), test, {n: digest(data_dir/n) for n in names}


def features(df, engineered=False):
    t = df[DATE]
    x = df[[CAP, *WEATHER]].copy()
    hour = t.dt.hour + t.dt.minute / 60
    x['month'], x['half_hour'], x['day_of_year'] = t.dt.month, t.dt.hour * 2 + t.dt.minute // 30, t.dt.dayofyear
    if engineered:
        for name, value, period in [('hour', hour, 24), ('year', t.dt.dayofyear - 1, 365.2425)]:
            x[name + '_sin'] = np.sin(2 * np.pi * value / period)
            x[name + '_cos'] = np.cos(2 * np.pi * value / period)
        for kind in KINDS:
            z = df[[f'{p}_{kind}' for p in POINTS]]
            for agg in ['mean', 'std', 'min', 'max']:
                x[f'{kind}_{agg}'] = getattr(z, agg)(axis=1)
            x[f'{kind}_missing'] = z.isna().sum(axis=1)
        # Small denominators replaced by NaN rather than unstable night-time ratios.
        clear = x['clearsky_mean'].where(x['clearsky_mean'] > 10)
        x['clearness_ratio'] = (x['ghi_mean']/clear).clip(0, 2)
    return x.astype(float)


class Climatology:
    def fit(self, df):
        z = pd.DataFrame({'month': df[DATE].dt.month, 'slot': df[DATE].dt.hour*2 + df[DATE].dt.minute//30,
                          'cf': df[TARGET]/df[CAP]})
        self.table = z.groupby(['month', 'slot']).cf.mean().to_dict()
        self.fallback = z.groupby('slot').cf.mean().to_dict()
        self.mean = float(z.cf.mean())
        return self

    def predict(self, df):
        keys = zip(df[DATE].dt.month, df[DATE].dt.hour*2 + df[DATE].dt.minute//30)
        return np.array([self.table.get((m,s), self.fallback.get(s,self.mean)) for m,s in keys]) * df[CAP].to_numpy()


def fit(df, config):
    if config['kind'] == 'climatology':
        return Climatology().fit(df)
    y = df[TARGET].to_numpy()
    weights = None
    if config['normalized']:
        y = y / df[CAP].to_numpy()
        # Sum C * abs(y/C - p) equals sum abs(y - C*p), matching MW MAE.
        weights = df[CAP].to_numpy() / df[CAP].mean()
    model = HistGradientBoostingRegressor(**TREE_PARAMS)
    with threadpool_limits(limits=2):
        model.fit(features(df, config['engineered']), y, sample_weight=weights)
    return model


def predict(model, df, config):
    if config['kind'] == 'climatology':
        pred = model.predict(df)
    else:
        with threadpool_limits(limits=2):
            pred = model.predict(features(df, config['engineered']))
        if config['normalized']:
            pred *= df[CAP].to_numpy()
    # Nonnegative physical output; no unverified hard upper bound or night zeroing.
    pred = np.maximum(pred, 0)
    if not np.isfinite(pred).all():
        raise ValueError('Nonfinite predictions')
    return pred


def metrics(df, pred):
    err = np.abs(df[TARGET].to_numpy() - pred)
    z = pd.DataFrame({'error': err, 'bias': pred-df[TARGET].to_numpy(),
                      'month': df[DATE].dt.strftime('%Y-%m').to_numpy(),
                      'quarter': df[DATE].dt.strftime('%Y').to_numpy() + '-Q' + df[DATE].dt.quarter.astype(str).to_numpy()})
    return {'mae_mw': float(err.mean()), 'bias_mw': float(z.bias.mean()), 'rows': len(df),
            'quarter_mae_mw': z.groupby('quarter').error.mean().to_dict(),
            'month_mae_mw': z.groupby('month').error.mean().to_dict()}


def stable_improvement(new, old):
    nq, oq = new['quarter_mae_mw'], old['quarter_mae_mw']
    if nq.keys() != oq.keys():
        raise ValueError('Quarter sets differ')
    return (new['mae_mw'] < old['mae_mw'] * 0.995
            and sum(nq[q] < oq[q] for q in nq) >= 3
            and all(nq[q] <= oq[q] * 1.05 for q in nq))


def append_experiment(path, name, config, split, result, seconds, artifact, decision):
    header = ['experiment_id','status','hypothesis','model','parameters','split','seed','mae_mw','elapsed_seconds','artifact_path','decision']
    # Idempotent recovery from cached metrics; never refit merely to repair a journal.
    path = Path(path)
    experiment_id = hashlib.sha256(str(Path(artifact).resolve()).encode()).hexdigest()[:12] + f'_{split}_{name}'
    rows = []
    if path.exists():
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
    record = dict(zip(header, [experiment_id, 'measured', config['hypothesis'], name,
        json.dumps({'config': config, 'tree': TREE_PARAMS if config['kind']=='hgb' else None}, sort_keys=True),
        split, SEED, result['mae_mw'], round(seconds,3), str(artifact), decision]))
    rows = [r for r in rows if r['experiment_id'] != experiment_id] + [record]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def evaluate(name, config, train, valid, out, split, log):
    start = time.monotonic()
    model = fit(train, config)
    pred = predict(model, valid, config)
    result = metrics(valid, pred)
    result['elapsed_seconds'] = time.monotonic()-start
    pd.DataFrame({'id': valid.id.to_numpy(), DATE: valid[DATE].to_numpy(), 'truth': valid[TARGET].to_numpy(), 'prediction': pred}).to_csv(out/f'{split}_{name}_predictions.csv', index=False)
    path = out/f'{split}_{name}_metrics.json'
    result['prediction_sha256'] = digest(out/f'{split}_{name}_predictions.csv')
    result['config'] = config
    write_json(path, result)
    append_experiment(log, name, config, split, result, result['elapsed_seconds'], path, 'evaluation_only')
    print(json.dumps({'model': name, 'split': split, 'mae_mw': result['mae_mw'], 'seconds': result['elapsed_seconds']}), flush=True)
    return result


def evaluate_or_resume(name, config, train, valid, out, split, log):
    path = out/f'{split}_{name}_metrics.json'
    if not path.exists():
        return evaluate(name, config, train, valid, out, split, log)
    result = json.loads(path.read_text())
    if result['config'] != config or result['prediction_sha256'] != digest(out/f'{split}_{name}_predictions.csv'):
        raise ValueError('Cached evaluation changed; preserve evidence and review before continuing')
    saved = pd.read_csv(out/f'{split}_{name}_predictions.csv', dtype={'id':'string'})
    if saved.id.tolist() != valid.id.tolist() or not np.allclose(saved.truth, valid[TARGET], rtol=1e-12, atol=1e-9):
        raise ValueError('Cached validation rows do not match current data')
    recomputed = metrics(valid, saved.prediction.to_numpy())
    if not np.isclose(result['mae_mw'], recomputed['mae_mw'], rtol=1e-12, atol=1e-9):
        raise ValueError('Cached MAE disagrees with saved predictions')
    for quarter,value in recomputed['quarter_mae_mw'].items():
        if not np.isclose(value,result['quarter_mae_mw'][quarter],rtol=1e-12,atol=1e-9):
            raise ValueError('Cached quarterly MAE disagrees with saved predictions')
    append_experiment(log,name,config,split,result,result['elapsed_seconds'],path,'evaluation_only')
    return result


def validate_submission(path, test):
    df = read_csv(path)
    if list(df.columns) != ['id', TARGET] or len(df) != len(test):
        raise ValueError('Wrong submission columns/row count')
    if df.id.isna().any() or df.id.duplicated().any() or df.id.tolist() != test.id.tolist():
        raise ValueError('Submission IDs must exactly preserve test order and uniqueness')
    y = pd.to_numeric(df[TARGET], errors='raise').to_numpy()
    if not (np.isfinite(y).all() and (y >= 0).all()):
        raise ValueError('Invalid submission numbers')
    if Path(path).stat().st_size > 10_000_000:
        raise ValueError('Submission exceeds conservative 10 MB limit')
    return {'rows': len(df), 'min_mw': float(y.min()), 'max_mw': float(y.max()), 'sha256': digest(path)}


def audit(train, test, out, hashes):
    # Only summarize development-era labels before the lockbox is opened.
    development = train[train[DATE] < pd.Timestamp(LOCK_START, tz='UTC')]
    result = {'input_sha256': hashes, 'train_rows': len(train), 'test_rows': len(test),
        'target_summary_scope': 'train before 2024-07-01 only; lockbox target summaries suppressed',
        'development_target': development[TARGET].describe().to_dict(),
        'development_capacity_factor': (development[TARGET]/development[CAP]).describe().to_dict(),
        'features': {}, 'warnings': []}
    for name, df in [('train',train), ('test',test)]:
        hour_groups = df.groupby(df[DATE].dt.floor('h'))[WEATHER].nunique(dropna=False)
        result['features'][name] = {'start_utc': str(df[DATE].min()), 'end_utc': str(df[DATE].max()),
            'capacity_range_mwp': [float(df[CAP].min()), float(df[CAP].max())],
            'missing_weather': df[WEATHER].isna().sum().to_dict(),
            'dtypes': {c:str(v) for c,v in df.dtypes.items()},
            'hours_with_different_weather_halfhours': int((hour_groups > 1).any(axis=1).sum())}
        if (hour_groups > 1).any().any():
            result['warnings'].append(f'{name}: half-hour weather differs within hour; review data card assumptions')
    write_json(out/'data_audit.json', result)
    return result


def provenance(hashes):
    root = Path(__file__).resolve().parents[1]
    code = {str(p.relative_to(root)): digest(p) for p in [Path(__file__).resolve(), root/'requirements.lock', root/'VALIDATION.md']}
    return {'input_sha256': hashes, 'source_sha256': code, 'seed': SEED, 'tree_params': TREE_PARAMS,
            'python': platform.python_version(), 'platform': platform.platform(),
            'packages': {'numpy':np.__version__, 'pandas':pd.__version__, 'sklearn':sklearn.__version__}}


def run(data_dir, out, log):
    train, test, hashes = load_data(data_dir)
    out, log = Path(out), Path(log)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out/'selection.json'
    prov = provenance(hashes)
    if (out/'run_provenance.json').exists():
        if json.loads((out/'run_provenance.json').read_text()) != prov:
            raise ValueError('Inputs, code, environment or protocol changed. Do not reuse an opened lockbox; review recorded results and plan first.')
    else:
        if any(p.name != 'data_audit.json' for p in out.iterdir()):
            raise ValueError('Output directory must be empty on first run')
        write_json(out/'run_provenance.json', prov)
    audit(train, test, out, hashes)
    if not manifest_path.exists():
        if (out/'lockbox_started.json').exists():
            raise ValueError('Lockbox was already opened; selection cannot be recomputed')
        dev_train = train[train[DATE] < pd.Timestamp(DEV_START,tz='UTC')]
        dev_valid = train[(train[DATE] >= pd.Timestamp(DEV_START,tz='UTC')) & (train[DATE] < pd.Timestamp(LOCK_START,tz='UTC'))]
        scores, best = {}, 'climatology'
        for name, config in CONFIGS.items():
            scores[name] = evaluate_or_resume(name, config, dev_train, dev_valid, out, 'development', log)
            if name != best and stable_improvement(scores[name],scores[best]):
                best = name
            write_json(out/'development_checkpoint.json', {'best_so_far':best,'completed':list(scores)})
        write_json(manifest_path, {'selected':best,'config':CONFIGS[best], 'development':scores,
            'policy':'overall MAE improves >=0.5%, improves at least 3/4 quarters, no quarter worsens >5%',
            'provenance':prov})
    selection = json.loads(manifest_path.read_text())
    if selection['provenance'] != prov or selection['config'] != CONFIGS[selection['selected']]:
        raise ValueError('Frozen selection does not match current run')
    # Persist selection before any lockbox fit or metric is computed.
    lock_marker = out/'lockbox_started.json'
    marker = {'selection_sha256':digest(manifest_path)}
    if lock_marker.exists() and json.loads(lock_marker.read_text()) != marker:
        raise ValueError('Selection changed after lockbox opened')
    write_json(lock_marker, marker)
    for name, result in selection['development'].items():
        append_experiment(log,name,CONFIGS[name],'development',result,result['elapsed_seconds'],
            out/f'development_{name}_metrics.json','selected' if name==selection['selected'] else 'not_selected')
    lock_train = train[train[DATE] < pd.Timestamp(LOCK_START,tz='UTC')]
    lock_valid = train[train[DATE] >= pd.Timestamp(LOCK_START,tz='UTC')]
    for name in dict.fromkeys(['climatology','hgb_mw',selection['selected']]):
        evaluate_or_resume(name, CONFIGS[name], lock_train, lock_valid, out, 'lockbox', log)
    model_path, submission_path = out/'model.joblib', out/'submission.csv'
    if not (out/'completed.json').exists():
        start = time.monotonic()
        final_model = fit(train, selection['config'])
        joblib.dump({'model':final_model,'config':selection['config'],'provenance':prov}, model_path)
        pred = predict(final_model, test, selection['config'])
        pd.DataFrame({'id':test.id, TARGET:pred}).to_csv(submission_path,index=False,float_format='%.8f')
        validation = validate_submission(submission_path,test)
        # Verify the saved model, not only the model retained in memory.
        saved = joblib.load(model_path)
        repeated = predict(saved['model'],test,saved['config'])
        if not np.array_equal(pred,repeated):
            raise ValueError('Reloaded model predictions differ')
        write_json(out/'completed.json', {'submission':validation,'model_sha256':digest(model_path),
            'selection_sha256':digest(manifest_path),'provenance':prov,'final_fit_seconds':time.monotonic()-start,
            'ai_declaration':'Autonomous','official_submission_made':False})
    completed = json.loads((out/'completed.json').read_text())
    if completed['selection_sha256'] != digest(manifest_path) or completed['provenance'] != prov:
        raise ValueError('Completed provenance or selection mismatch')
    if validate_submission(submission_path,test)['sha256'] != completed['submission']['sha256'] or digest(model_path) != completed['model_sha256']:
        raise ValueError('Completed artifacts have changed')
    print(f'Local package complete: {submission_path}; no upload performed.',flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['audit','run','check'])
    p.add_argument('--data', default='data/raw')
    p.add_argument('--out', default='artifacts/official')
    p.add_argument('--log', default='EXPERIMENTS.csv')
    p.add_argument('--submission')
    a = p.parse_args()
    try:
        if a.command == 'run':
            run(a.data,a.out,a.log)
        else:
            train,test,hashes = load_data(a.data)
            if a.command == 'audit':
                Path(a.out).mkdir(parents=True,exist_ok=True)
                audit(train,test,Path(a.out),hashes)
            elif not a.submission:
                p.error('--submission is required for check')
            else:
                print(json.dumps(validate_submission(a.submission,test),indent=2))
    except (ValueError, FileNotFoundError) as exc:
        p.exit(2, f'Cannot continue: {exc}\n')

if __name__ == '__main__':
    main()
