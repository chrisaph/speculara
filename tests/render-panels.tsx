import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { SentimentPanel, DemandPanel } from '../src/components/AnalysisPanels'
import { PredictPanel, RecommendPanel, ChartsPanel, CorrelationPanel } from '../src/components/InsightPanels'
import { MetricCoverage, metricsTemplate } from '../src/components/MetricCoverage'
import { ForecastValidation } from '../src/components/ForecastValidation'
import { SuggestionStrip } from '../src/components/SuggestionStrip'
import App from '../src/App'
export { uploadDataset } from '../src/api'

// Load React and its renderer through the same Vite module graph on Windows.
export const renderSentiment = (analysis: any) => renderToStaticMarkup(React.createElement(SentimentPanel, { analysis }))
export const renderDemand = (analysis: any) => renderToStaticMarkup(React.createElement(DemandPanel, { analysis }))
export const renderPredict = (analysis: any) => renderToStaticMarkup(React.createElement(PredictPanel, { analysis }))
export const renderRecommend = (analysis: any) => renderToStaticMarkup(React.createElement(RecommendPanel, { analysis }))
export const renderCharts = (analysis: any) => renderToStaticMarkup(React.createElement(ChartsPanel, { analysis }))
export const renderCorrelation = (analysis: any) => renderToStaticMarkup(React.createElement(CorrelationPanel, { analysis }))
export const renderCoverage = (analysis: any) => renderToStaticMarkup(React.createElement(MetricCoverage, { analysis, onUpdated: () => {} }))
export const renderValidation = (data: any) => renderToStaticMarkup(React.createElement(ForecastValidation, { data }))
export const renderSuggestions = (items: string[]) => renderToStaticMarkup(React.createElement(SuggestionStrip, { items, onSelect: () => {} }))
export const metricsCSV = metricsTemplate
export const renderApp = () => renderToStaticMarkup(React.createElement(App))
