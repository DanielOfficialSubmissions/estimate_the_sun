"""Synthetic software tests, not competition evidence."""
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import solar
import numpy as np
import pandas as pd


def frame(start='2023-06-30', periods=96):
    t = pd.date_range(start, periods=periods, freq='30min', tz='UTC')
    rng = np.random.default_rng(19)
    sun = np.maximum(0, np.sin((t.hour.to_numpy()-6)/24*2*np.pi))
    d = {'id':pd.Series([f'TEST_{i}' for i in range(periods)],dtype='string'),
         solar.DATE:t,solar.CAP:15000+np.arange(periods)*0.1}
    for p in solar.POINTS:
        for k in solar.KINDS:
            d[f'{p}_{k}'] = sun*500 if k in ['ghi','clearsky'] else rng.uniform(1,30,periods)
    d[solar.TARGET] = sun*4000
    return pd.DataFrame(d)


class PipelineTests(unittest.TestCase):
    def test_ids_and_targets_never_features(self):
        d=frame()
        a=solar.features(d,True)
        d.id='DIFFERENT'
        d[solar.TARGET]=9999999
        pd.testing.assert_frame_equal(a,solar.features(d,True))

    def test_missing_and_all_missing_weather(self):
        d=frame()
        d.loc[0,solar.WEATHER]=-999
        d[solar.WEATHER[1]]=np.nan
        d=solar.validate_frame(d,True,strict=False)
        self.assertTrue(d.loc[0,solar.WEATHER].isna().all())
        x=solar.features(d,True)
        self.assertFalse(np.isinf(x.to_numpy()).any())
        cfg=solar.CONFIGS['hgb_features']
        model=solar.fit(d,cfg)
        self.assertTrue(np.isfinite(solar.predict(model,d,cfg)).all())

    def test_validation_rejects_bad_inputs(self):
        mutations=[lambda d:d.assign(installed_capacity_mwp=0),
                   lambda d:d.assign(installed_capacity_mwp=np.nan),
                   lambda d:d.assign(generation_mw=np.inf),
                   lambda d:d.assign(id='same'),
                   lambda d:d.assign(datetime_utc=pd.NaT),
                   lambda d:d.assign(london_ghi='bad'),
                   lambda d:d.assign(extra_target=0),
                   lambda d:d.assign(datetime_utc=d[solar.DATE]+pd.Timedelta(minutes=1))]
        for fn in mutations:
            with self.subTest(fn=fn):
                with self.assertRaises((ValueError,TypeError)):
                    solar.validate_frame(fn(frame()),True,strict=False)
        with self.assertRaises(ValueError):
            solar.validate_frame(frame(),True,strict=True)

    def test_temporal_boundaries(self):
        d=frame()
        before=d[d[solar.DATE]<pd.Timestamp(solar.DEV_START,tz='UTC')]
        after=d[d[solar.DATE]>=pd.Timestamp(solar.DEV_START,tz='UTC')]
        self.assertLess(before[solar.DATE].max(),after[solar.DATE].min())
        self.assertFalse(set(before[solar.DATE].dt.floor('h')) & set(after[solar.DATE].dt.floor('h')))

    def test_baseline_uses_only_fit_labels(self):
        d=frame()
        d[solar.TARGET]=d[solar.CAP]*0.2
        m=solar.Climatology().fit(d)
        v=frame('2024-01-01')
        v[solar.TARGET]=999999
        np.testing.assert_allclose(m.predict(v),v[solar.CAP]*0.2)

    def test_mw_weighted_loss_equivalence(self):
        c=np.array([100.,1000.,20000.]); y=np.array([50.,400.,12000.]); p=np.array([.4,.3,.5])
        self.assertAlmostEqual(float(np.sum(c*np.abs(y/c-p))),float(np.sum(np.abs(y-c*p))))

    def test_submission_roundtrip_and_rejections(self):
        test=frame().drop(columns=solar.TARGET).sample(frac=1,random_state=7)
        good=pd.DataFrame({'id':test.id,solar.TARGET:np.arange(len(test))*.1})
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'prediction.csv'
            good.to_csv(p,index=False)
            self.assertEqual(solar.validate_submission(p,test)['rows'],len(test))
            for bad in [good.iloc[::-1],good.iloc[:-1],good.assign(generation_mw=np.nan),good.assign(generation_mw=-1),good.assign(id='duplicate')]:
                bad.to_csv(p,index=False)
                with self.assertRaises(ValueError):solar.validate_submission(p,test)

    def test_stability_rejects_single_season_gain(self):
        old={'mae_mw':100,'quarter_mae_mw':dict(zip('abcd',[100]*4))}
        new={'mae_mw':95,'quarter_mae_mw':dict(zip('abcd',[70,101,101,108]))}
        self.assertFalse(solar.stable_improvement(new,old))
        good={'mae_mw':98,'quarter_mae_mw':dict(zip('abcd',[97,98,98,99]))}
        self.assertTrue(solar.stable_improvement(good,old))

    def test_duplicate_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.csv';p.write_text('id,id\na,b\n')
            with self.assertRaises(ValueError):solar.read_csv(p)

    def test_features_are_batch_independent(self):
        d=frame()
        full=solar.features(d,True)
        solo=solar.features(d.iloc[[17]],True)
        pd.testing.assert_frame_equal(full.iloc[[17]],solo)

    def test_no_official_data_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'Official files required'):
                solar.load_data(tmp)

if __name__=='__main__':unittest.main()
