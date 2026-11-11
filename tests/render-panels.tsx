import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { SentimentPanel, DemandPanel } from '../src/components/AnalysisPanels'

// Load React and its renderer through the same Vite module graph on Windows.
export const renderSentiment = (analysis: any) => renderToStaticMarkup(React.createElement(SentimentPanel, { analysis }))
export const renderDemand = (analysis: any) => renderToStaticMarkup(React.createElement(DemandPanel, { analysis }))
