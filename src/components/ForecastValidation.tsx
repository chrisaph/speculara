const number=(value:number)=>value.toLocaleString(undefined,{maximumFractionDigits:1})

export function ForecastValidation({data}:{data:any}) {
  const v=data.validation||{},perPost=data.basis==='post',count=perPost?v.test_posts:v.test_weeks
  const score=typeof data.accuracy==='number'&&Number.isFinite(data.accuracy)&&data.accuracy>=0&&data.accuracy<=100?data.accuracy:null
  const limited=score===0||data.reliability==='low'||data.reliability==='unknown'
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
