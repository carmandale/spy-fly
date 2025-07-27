# Dashboard UI Design Brief for SPY-FLY

## Overview
Design a single-page dashboard that displays the morning sentiment scan results and current trading recommendations for SPY 0-DTE bull-call-spreads. The UI should be clean, data-focused, and work well on both desktop and mobile.

## Key Requirements

### 1. **Sentiment Score Display**
- Large, prominent sentiment score (0-100)
- Visual indicator (gauge, dial, or progress bar)
- Clear PROCEED/SKIP decision with color coding
- Breakdown of individual components:
  - VIX score
  - Futures direction
  - Technical indicators (RSI, MA50, Bollinger)
  - News sentiment

### 2. **Recommended Spreads Section**
- Display 1-2 recommended bull-call-spreads
- Show for each spread:
  - Strike prices (long/short)
  - Debit amount
  - Max profit/loss
  - Probability of profit
  - Breakeven point
  - Quantity to trade (based on $5-10k risk)
- "Copy to Clipboard" button for order details

### 3. **Live P/L Monitor**
- Real-time profit/loss display
- Visual P/L bar or chart
- Current spread value vs entry price
- Time decay indicator
- Alert status (approaching profit target or stop loss)

### 4. **Market Status Bar**
- Current SPY price with change
- Market session status (pre-market, open, closed)
- VIX level
- Time until market close
- API connection status

### 5. **Historical Performance**
- Mini equity curve chart (last 30 days)
- Win rate percentage
- Average profit/loss

## Technical Constraints
- Must work with existing React/TypeScript/Tailwind CSS v4 setup
- Use shadcn/ui components where applicable
- Real-time updates via WebSocket (prepare for this)
- Mobile-responsive design
- Dark mode support

## Visual Style
- Professional trading terminal aesthetic
- High contrast for quick scanning
- Green/red color coding for bullish/bearish
- Minimal decorative elements
- Focus on data density without clutter

## Example Data to Display
```json
{
  "sentiment": {
    "score": 72,
    "decision": "PROCEED",
    "components": {
      "vix": { "score": 20, "value": 14.5 },
      "futures": { "score": 20, "change": "+0.35%" },
      "technical": { "score": 30, "status": "bullish" }
    }
  },
  "recommendation": {
    "spread": "SPY 568/571 Call",
    "debit": 0.85,
    "maxProfit": 2150,
    "maxLoss": 850,
    "probability": 0.42,
    "quantity": 10
  },
  "currentPosition": {
    "entryPrice": 0.85,
    "currentValue": 1.15,
    "pnl": 300,
    "pnlPercent": 35.3
  }
}
```

## Deliverable
Please provide either:
1. A mockup/wireframe (image or Figma/Sketch link)
2. A component hierarchy diagram
3. HTML/JSX structure with Tailwind classes
4. Or describe the layout and component organization

Focus on information hierarchy and usability for a trader who needs to make quick decisions at market open.