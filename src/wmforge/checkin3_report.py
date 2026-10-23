"""Completeness-aware Check-in 3 rates and quality intervals, without pooling history."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from wmforge import benchmark as b, metrics
from wmforge.harness import SCHEMES


def summarize(rows,calibrations):
    result=[]
    for scheme in SCHEMES:
        calibration=calibrations.get(scheme)
        cells=[('baseline',kind,'',0,n) for kind,n in [('watermarked',100),('unwatermarked',200),('real',100)]]
        if calibration and calibration['included']:
            cells += [('imprint','forged','imprint',step,10) for step in [50,100,150]]
            cells += [('removal','watermarked',attack,0,100) for attack in b.ATTACKS]
        for stage,kind,attack,step,expected in cells:
            found=[r for r in rows if (r['scheme'],r['stage'],r['kind'],r['attack'],r['step'])==(scheme,stage,kind,attack,step)]
            n=len(found)
            cell=dict(scheme=scheme,stage=stage,kind=kind,attack=attack,step=step,
                      expected_n=expected,observed_n=n,complete=n==expected,
                      included=None if calibration is None else calibration['included'])
            if n:
                successes=sum(r['native'] for r in found)
                cell.update(native_successes=successes,native_rate=successes/n,
                            native_wilson95=metrics.wilson_interval(successes,n))
                if calibration:
                    successes=sum(r['score']>calibration['threshold'] for r in found)
                    cell.update(calibrated_successes=successes,calibrated_rate=successes/n,
                                calibrated_wilson95=metrics.wilson_interval(successes,n),
                                calibrated_label='PRC score-only calibrated test' if scheme=='PRC' else 'calibrated score test')
                for name in ['psnr','ssim','lpips']:
                    values=[float(r[name]) for r in found if name in r and np.isfinite(float(r[name]))]
                    if values:
                        cell[name]=dict(mean=float(np.mean(values)),bootstrap95=metrics.bootstrap_ci(values,n_resamples=10000,seed=261),n_finite=len(values))
            result.append(cell)
    return result


def report(root):
    root=Path(root)
    log=b.BenchmarkLog(root/'measurements-v2.json')
    for row in log.rows:
        b.verify_artifact(root,row)
    calibrations={scheme:json.loads((root/f'{scheme}-calibration.json').read_text())
                  for scheme in SCHEMES if (root/f'{scheme}-calibration.json').exists()}
    table=summarize(log.rows,calibrations)
    b.atomic_bytes(root/'summary-v2.json',json.dumps(table,indent=2,allow_nan=False).encode())
    lines=['# Check-in 3 progress and measurements','',
           'Only exact step-50, step-100, and step-150 images enter forgery results. Rates below use observed items; incomplete cells are provisional and never substitute for the required denominator.',
           '', 'Calibration is an empirical operating point on 200 generated negatives (0.5-percentage-point resolution). It is not independent evidence of population FPR. PRC score-only decisions are separate from native decoder verdicts.',
           '', '| Scheme | Stage | Kind / attack / step | Observed / required | Native rate [Wilson 95%] | Calibrated rate [Wilson 95%] |',
           '|---|---|---|---|---|---|']
    def rate(cell,prefix):
        if prefix+'_rate' not in cell: return 'pending'
        low,high=cell[prefix+'_wilson95']
        return f"{cell[prefix+'_rate']:.1%} [{low:.1%}, {high:.1%}]"
    for cell in table:
        descriptor=cell['attack'] or cell['kind']
        if cell['step']: descriptor+=f" / {cell['step']}"
        status='' if cell['complete'] else ' (incomplete)'
        lines.append(f"| {cell['scheme']} | {cell['stage']} | {descriptor} | {cell['observed_n']}/{cell['expected_n']}{status} | {rate(cell,'native')} | {rate(cell,'calibrated')} |")
    for scheme,calibration in calibrations.items():
        if not calibration['included']:
            lines.extend(['',f"{scheme}: excluded by the native clean TPR / generated FPR inclusion rule."])
    lines.extend(['','Continuous metrics and their 10,000-resample bootstrap intervals are in `summary-v2.json`. Missing or infinite metric values are excluded explicitly through each metric’s `n_finite` count.'])
    b.atomic_bytes(root/'summary-v2.md','\n'.join(lines).encode())
    return table


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    table=report(args.run)
    print(f"{sum(c['complete'] for c in table)}/{len(table)} required cells complete")


if __name__=='__main__': main()
