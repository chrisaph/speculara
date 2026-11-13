const number=(value:number)=>value.toLocaleString(undefined,{maximumFractionDigits:1})

export function ForecastValidation({data}:{data:any}) {
  const v=data.validation||{},perPost=data.basis==='post',count=perPost?v.test_posts:v.test_weeks
  const score=typeof data.accuracy==='number'&&Number.isFinite(data.accuracy)&&data.accuracy>=0&&data.accuracy<=100?data.accuracy:null
  const limited=score===0||data.reliability==='low'||data.reliability==='unknown'
  if (data.forecast_check) {
    const check = data.forecast_check
    const hasChecks = check.checks > 0 && typeof check.score === 'number'
    const beatsBaseline = hasChecks && check.score > check.baseline_score
    const guidance = !hasChecks ? 'More observed posts needed' : check.score > 50 && beatsBaseline ? 'Often close in this sample' : 'Use with caution'
    return <section aria-label="Forecast check results" className="neu-in rounded-2xl p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-wide text-slate-600">Automatic next-post check</p><p aria-label="Forecast check" className="mt-1 font-display text-3xl font-bold text-ink">{hasChecks ? `Forecast check: ${number(check.score)}%` : 'Not enough data to check'}</p></div>
        <span className="rounded-full border border-slate-300 px-3 py-2 text-xs font-semibold text-ink">{guidance}</span>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-slate-700">{hasChecks ? `${check.hits} of ${check.checks} predictions were within ${check.tolerance_pct}% of the recorded count. All ${check.checks} checks ran automatically using only earlier posts.` : check.reason}</p>
      {hasChecks && <div role="img" aria-label={`${check.hits} close results out of ${check.checks} completed checks`} className="mt-3 flex gap-1">{check.observations.map((o:any,i:number)=><span key={i} className={`h-2 flex-1 rounded-full ${o.within_tolerance ? 'bg-ink' : 'bg-slate-300'}`} />)}</div>}
      <p className="mt-3 text-sm leading-relaxed text-slate-700">Use this check to decide how much weight to give the forecast when planning content. More close results mean it matched this sample more often; fewer close results mean you should treat it as a rough guide.</p>
      <p className="mt-2 text-xs text-slate-600">Limited evidence. {data.coverage} These are snapshot counts, so older posts have had longer to gain activity.</p>
      <details className="mt-4 border-t border-slate-300 pt-3 text-xs leading-relaxed text-slate-600">
        <summary className="min-h-8 cursor-pointer font-semibold text-ink">See completed checks and how they work</summary>
        <p className="mt-3">A result is close when it falls within 30% of the recorded count: for 1,000 recorded likes, 700 to 1,300 is close. Outside range means the check ran and missed that range; it was not skipped. A recorded zero requires a rounded prediction of zero.</p>
        <p className="mt-2">The first ten observed posts train the model. Up to ten later posts are checked one at a time, using earlier posts only. Checks assess the next post, not the whole forecast horizon.</p>
        {hasChecks && <p className="mt-2">A simple recent four-post average was close in {check.baseline_hits} of {check.checks} checks ({check.baseline_score}%). {beatsBaseline ? 'The model did better on these checks.' : 'The model did not beat that simple average on these checks.'}</p>}
        {hasChecks && <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[24rem] text-left"><caption className="mb-2 text-left font-semibold text-ink">Completed checks</caption><thead><tr><th scope="col" className="py-2">Post date</th><th scope="col">Recorded</th><th scope="col">Predicted</th><th scope="col">Result</th></tr></thead><tbody>{check.observations.map((o:any,i:number)=><tr key={i} className="border-t border-slate-200"><td className="py-2">{o.date}</td><td>{number(o.actual)}</td><td>{number(o.predicted)}</td><td>{o.within_tolerance ? 'Close' : 'Outside range'}</td></tr>)}</tbody></table></div>}
        <p className="mt-3">Historical fit: {score == null ? 'unavailable' : `${number(score)}%`}.{data.model ? ` ${data.model}.` : ''} This separate score describes fit to training observations.</p>
      </details>
    </section>
  }

  if (data.score_basis === 'fitted_history' && score == null) return <p className="text-sm text-slate-600">{data.reason || 'No observed values are available for this metric.'}</p>
  if (data.score_basis === 'fitted_history') return <div className="space-y-3">
    <p aria-label="Prediction accuracy" className="text-center font-display text-2xl font-bold text-ink">{score == null ? 'Accuracy unavailable' : `Accuracy: ${number(score)}%`}</p>
    <p className="text-center text-xs leading-relaxed text-slate-600">Measures how closely the model matches historical weekly totals used to fit it. Calculated from average percentage fitting error, with the score limited to 0-97%.</p>
    <p className="text-xs text-slate-600">{data.model ? `${data.model}. ` : ''}{data.coverage}</p>
  </div>
  return <div className="space-y-3">
    <p aria-label="Prediction accuracy" className="text-center font-display text-2xl font-bold text-ink">{score==null?'Accuracy unavailable':`Accuracy: ${number(score)}%`}</p>
    <p className="text-center text-xs leading-relaxed text-slate-600">{score==null?'There is not enough held-out data to calculate an accuracy score.':'Python model score on held-out data, not a guarantee of future performance.'}{limited&&<span className="text-wine"> Low reliability; use this forecast as an exploratory estimate.</span>}</p>
    <details className="neu-in rounded-2xl p-4 text-xs leading-relaxed text-slate-600" aria-label="Prediction backtest details">
      <summary className="cursor-pointer font-semibold text-ink">Backtest details and evidence</summary>
      <div className="mt-3 space-y-3">
        {v.weighted_error_pct!=null&&<p><strong className="text-ink">Backtest error: {number(v.weighted_error_pct)}%</strong>. Lower error is better. {score===0?'The error reached or exceeded the held-out total, so the score is floored at 0%. This does not mean the posts had no activity.':'This compares predictions with observations that were excluded from model selection.'}</p>}
        <p>{count?`Tested on ${count} ${perPost?'latest posts':'completed weeks'} (${v.start||'date unavailable'} to ${v.end||'date unavailable'}), excluded from model selection. ${count<4?'This is a small validation sample.':''}`:`At least six ${perPost?'dated posts':'completed weeks'} and a non-zero held-out total are needed to report a percentage score.`} {data.coverage}</p>
        {data.model&&<p>Selected model: {data.model}. Compared against simple baselines using training observations only.</p>}
        {v.baseline_weighted_error_pct!=null&&<p>Comparison: {v.baseline_model} had {number(v.baseline_weighted_error_pct)}% error on the same holdout. Lower error is better.</p>}
        {data.reason&&!data.reason.startsWith('Forecast withheld:')&&<p>{data.reason}</p>}
        {!!data.partial_weeks?.length&&<p>Unfinished or future-dated weeks are excluded from training and validation: {data.partial_weeks.map((p:any)=>`${p.date} (${number(p.value)} observed so far)`).join(', ')}.</p>}
        {!!v.observations?.length&&<div className="overflow-x-auto"><table className="w-full text-left"><caption className="mb-2 text-left font-semibold text-ink">Held-out observations</caption><thead><tr><th className="p-2">{perPost?'Post date':'Week ending'}</th><th className="p-2">Actual</th><th className="p-2">Predicted</th></tr></thead><tbody>{v.observations.map((r:any,i:number)=><tr key={`${r.date}-${i}`}><td className="p-2">{r.date}</td><td className="p-2">{number(r.actual)}</td><td className="p-2">{number(r.predicted)}</td></tr>)}</tbody></table></div>}
        <p>Weighted absolute error = sum of absolute errors / sum of actual counts. Python accuracy = max(0, 100 - error percentage){score!=null?` = ${number(score)}%`:''}.{v.weighted_error_pct==null?' The held-out percentage error is unavailable, for example when the actual total is zero.':''} This is a forecast score, not classification accuracy.</p>
      </div>
    </details>
  </div>
}


export function PredictionAccuracy({data}:{data:any}) {
  const score = typeof data.accuracy === 'number' && Number.isFinite(data.accuracy) ? data.accuracy : null
  return <div className="pt-1 text-center">
    <p aria-label="Prediction accuracy" className="font-display text-3xl font-bold text-ink">{score == null ? 'Accuracy unavailable' : `Accuracy: ${number(score)}%`}</p>
    <p className="mt-1 text-xs leading-relaxed text-slate-600">Measures fit to historical data. Accuracy depends on the amount of data and date range.</p>

  </div>
}
