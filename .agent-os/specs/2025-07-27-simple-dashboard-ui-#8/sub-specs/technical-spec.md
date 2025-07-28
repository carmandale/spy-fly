# Technical Specification

This is the technical specification for the spec detailed in @.agent-os/specs/2025-07-27-simple-dashboard-ui-#8/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Technical Requirements

### Frontend Architecture

- **React 18+** with TypeScript for type safety
- **TanStack Query** for data fetching with built-in caching and refetch
- **Zustand** for minimal state management if needed
- **Tailwind CSS v4** with shadcn/ui components
- **Vite** for fast development and building

### Data Flow

1. **API Integration**
   - Use existing API client at `/frontend/src/api/client.ts`
   - Endpoints: `/api/v1/market/quote/SPY` and `/api/v1/sentiment/calculate`
   - Handle both successful responses and error states

2. **Auto-Refresh Strategy**
   - 30-second interval for market data updates
   - 60-second interval for sentiment updates (less volatile)
   - Pause updates when tab is not visible (battery optimization)
   - Manual refresh button for immediate updates

3. **State Management**
   - TanStack Query for server state (API data)
   - Local state for UI preferences (if any)
   - No complex state management needed for Phase 1

### Component Architecture

```
Dashboard/
├── index.tsx (Main container)
├── components/
│   ├── MarketDataCard.tsx (SPY price display)
│   ├── SentimentGauge.tsx (Visual score indicator)
│   ├── TradingDecision.tsx (PROCEED/SKIP panel)
│   ├── ComponentBreakdown.tsx (Individual scores)
│   └── LoadingStates.tsx (Skeletons)
```

### Performance Optimizations

- Memoize expensive calculations
- Use React.memo for pure components
- Implement proper loading states to prevent layout shift
- Lazy load non-critical components

## Approach Options

**Option A: Single Component Approach**
- Pros: Simple, all logic in one place
- Cons: Harder to test, less reusable

**Option B: Modular Component Architecture** (Selected)
- Pros: Testable, reusable, clear separation of concerns
- Cons: More files to manage

**Option C: Full State Management Setup**
- Pros: Scalable for future features
- Cons: Overkill for current requirements

**Rationale:** Option B provides the right balance of simplicity and maintainability for a Phase 1 implementation while allowing for future growth.

## External Dependencies

- **@tanstack/react-query** - Already installed
  - **Justification:** Handles caching, refetching, and error states elegantly
  
- **recharts** - Already installed
  - **Justification:** May use for sentiment gauge visualization
  
- **lucide-react** - Already installed
  - **Justification:** Icon library for UI elements

## API Response Handling

### Quote Response
```typescript
interface QuoteResponse {
  ticker: string
  price: number
  change: number
  change_percent: number
  volume: number
  timestamp: string
  market_status: string
  cached: boolean
}
```

### Sentiment Response
```typescript
interface SentimentResponse {
  score: number
  decision: 'PROCEED' | 'SKIP'
  threshold: number
  timestamp: string
  breakdown: {
    vix: ComponentScore
    futures: ComponentScore
    rsi: ComponentScore
    ma50: ComponentScore
    bollinger: ComponentScore
    news: ComponentScore
  }
  technical_status: {
    all_bullish: boolean
    details: Record<string, string>
  }
  cached: boolean
}
```

## Error Handling

- Network errors: Show retry button with countdown
- API errors: Display user-friendly message
- Stale data: Show timestamp and "cached" indicator
- Rate limits: Implement exponential backoff