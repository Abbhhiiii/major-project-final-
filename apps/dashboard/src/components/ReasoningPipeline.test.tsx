import { render, screen } from '@testing-library/react'

import { ReasoningPipeline } from './ReasoningPipeline'

describe('ReasoningPipeline', () => {
  it('shows completed verification evidence and remaining stages', () => {
    render(<ReasoningPipeline events={[{ stage: 'verification', payload: { verified: true, score: 0.91 } }]} isProcessing />)
    expect(screen.getByText('Verified · 91%')).toBeInTheDocument()
    expect(screen.getByText('Policy retrieval')).toBeInTheDocument()
    expect(screen.getByText('Processing')).toBeInTheDocument()
  })

  it('renders the live model decision and rationale', () => {
    render(
      <ReasoningPipeline
        events={[{
          stage: 'reasoning',
          payload: {
            severity: 'high',
            alert_message: 'Verified collision at Airport Road.',
            rationale: ['Uploaded policy requires a dashboard alert.'],
            notify_emergency_services: false,
            model: 'openai/gpt-oss-20b',
          },
        }]}
        isProcessing={false}
      />,
    )
    expect(screen.getByTestId('live-reasoning-output')).toBeInTheDocument()
    expect(screen.getByText('Verified collision at Airport Road.')).toBeInTheDocument()
    expect(screen.getByText('Uploaded policy requires a dashboard alert.')).toBeInTheDocument()
  })
})
