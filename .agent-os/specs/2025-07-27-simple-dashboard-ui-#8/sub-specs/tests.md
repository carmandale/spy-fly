# Tests Specification

This is the tests coverage details for the spec detailed in @.agent-os/specs/2025-07-27-simple-dashboard-ui-#8/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Test Coverage

### Unit Tests

**MarketDataCard Component**
- Renders current price correctly
- Displays positive change with green color and up arrow
- Displays negative change with red color and down arrow
- Shows volume with proper formatting (K/M suffix)
- Updates timestamp to relative time ("2 seconds ago")
- Handles null/undefined data gracefully

**SentimentGauge Component**
- Renders score value and max score
- Progress bar width matches percentage
- Color changes based on score ranges
- Threshold line positioned correctly
- Handles edge cases (0, 100, negative scores)

**TradingDecision Component**
- Shows PROCEED with green styling when decision is proceed
- Shows SKIP with red styling when decision is skip
- Displays appropriate icon for each decision
- Shows technical status details on hover/click
- Handles loading state with skeleton

**ComponentBreakdown Component**
- Renders all 6 sentiment components
- Displays correct score for each component
- Shows appropriate labels (Bullish/Bearish/Neutral)
- Progress bars match component scores
- Handles missing component data

**API Integration Tests**
- Mock successful API responses
- Handle 503 Service Unavailable errors
- Test retry logic with exponential backoff
- Verify caching behavior
- Test stale data handling

### Integration Tests

**Dashboard Data Flow**
- Fetch market quote and sentiment on mount
- Display loading states during fetch
- Update UI when data arrives
- Handle simultaneous API failures gracefully
- Maintain data during refetch

**Auto-Refresh Functionality**
- Refresh market data every 30 seconds
- Refresh sentiment every 60 seconds
- Pause refresh when tab not visible
- Resume refresh when tab becomes visible
- Manual refresh button works correctly

**Error Handling Flow**
- Network error shows retry button
- API error displays user message
- Rate limit triggers backoff
- Cached data indicator appears
- Error boundary catches component crashes

**Responsive Design**
- Mobile layout stacks cards vertically
- Tablet shows 2-column grid
- Desktop displays optimal 3-column
- Touch targets meet 44px minimum
- No horizontal scroll on any viewport

### Feature Tests

**Complete Dashboard Experience**
- User loads dashboard
- Sees loading skeletons
- Data appears with smooth transition
- Values update automatically
- Can manually refresh
- Errors show helpful messages

**Market Hours Awareness**
- Shows "Market Closed" outside hours
- Indicates pre-market/after-hours
- Adjusts refresh frequency
- Displays last close price when closed

**Performance Scenarios**
- Initial load time < 1 second
- Smooth 60fps animations
- No memory leaks after hours
- Handles rapid manual refreshes
- Works on slow 3G connection

### Visual Regression Tests

- Screenshot dashboard in all states
- Compare color accuracy
- Verify spacing consistency
- Check responsive breakpoints
- Validate dark mode appearance

### Accessibility Tests

- Keyboard navigation through all elements
- Screen reader announcements correct
- Focus indicators visible
- Color contrast ratios meet WCAG AA
- No motion sickness from animations

### Mocking Requirements

- **API Client**: Mock successful and error responses
- **Date/Time**: Mock for consistent "last updated" testing
- **Window.matchMedia**: Mock for dark mode testing
- **IntersectionObserver**: Mock for visibility detection
- **fetch**: Mock for network error scenarios

## Performance Metrics

- First Contentful Paint: < 1s
- Time to Interactive: < 2s
- Lighthouse Score: > 90
- Bundle Size: < 200KB
- No layout shifts (CLS = 0)

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile Safari iOS 14+
- Chrome Android 90+