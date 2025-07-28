# UI/UX Specification

This is the UI/UX specification for the spec detailed in @.agent-os/specs/2025-07-27-simple-dashboard-ui-#8/spec.md

> Created: 2025-07-27
> Version: 1.0.0

## Visual Design

### Layout Structure

```
┌─────────────────────────────────────────────────┐
│                  Header                         │
│              SPY-FLY Dashboard                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐  ┌─────────────────────┐  │
│  │  Market Data    │  │  Trading Decision   │  │
│  │  SPY: $637.10   │  │                     │  │
│  │  +$2.30 (+0.36%)│  │      SKIP          │  │
│  └─────────────────┘  └─────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │         Sentiment Score: 65/100          │  │
│  │     ████████████████░░░░░░░░░ (65%)     │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐  │
│  │          Component Breakdown             │  │
│  ├─────────────────────────────────────────┤  │
│  │ VIX          ████████ 20/20  Bullish    │  │
│  │ Futures      ████████ 20/20  Bullish    │  │
│  │ RSI          ░░░░░░░░  0/10  Overbought │  │
│  │ MA50         ████░░░░ 10/10  Above MA   │  │
│  │ Bollinger    ░░░░░░░░  0/10  Upper Band │  │
│  │ News         ██████░░ 15/15  Neutral    │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│        Last updated: 2 seconds ago             │
└─────────────────────────────────────────────────┘
```

### Color Palette

- **Primary**: Blue-600 (#2563eb) - Main actions and links
- **Success**: Emerald-500 (#10b981) - Positive changes, PROCEED
- **Warning**: Amber-500 (#f59e0b) - Neutral states
- **Danger**: Red-500 (#ef4444) - Negative changes, SKIP
- **Background**: Slate-50 (#f8fafc) light / Slate-900 (#0f172a) dark
- **Card Background**: White / Slate-800
- **Text**: Slate-900 / Slate-100

### Typography

- **Headings**: Inter or system font, semibold
- **Price Display**: Mono font, large size (3xl)
- **Body Text**: Inter or system font, regular
- **Small Text**: 0.875rem for timestamps and labels

### Component Specifications

#### Market Data Card
- Large price display with mono font
- Green up arrow or red down arrow for direction
- Percentage in parentheses with color coding
- Volume and timestamp in smaller text below

#### Trading Decision Panel
- Large, bold text (PROCEED or SKIP)
- Green background for PROCEED, red for SKIP
- Icon (check or X) for visual reinforcement
- Brief explanation text below

#### Sentiment Gauge
- Horizontal progress bar with gradient
- Numeric score prominently displayed
- Threshold indicator line
- Color transitions: red (0-40) → yellow (40-60) → green (60-100)

#### Component Breakdown
- Compact list view with mini progress bars
- Color-coded scores (green/yellow/red)
- Labels aligned right for easy scanning
- Hover states for more details

### Responsive Breakpoints

- **Mobile** (< 640px): Stack all cards vertically
- **Tablet** (640px - 1024px): 2-column grid
- **Desktop** (> 1024px): Optimal 3-column layout

### Animations

- Smooth transitions for value changes (300ms ease)
- Pulse animation on data refresh
- Skeleton loading states during fetch
- No jarring movements or layout shifts

### Accessibility

- ARIA labels for all interactive elements
- Keyboard navigation support
- High contrast mode support
- Screen reader announcements for updates
- Minimum touch target size of 44x44px

### Dark Mode

- Automatic detection of system preference
- Manual toggle in header
- Inverted color scheme maintaining contrast ratios
- Smooth transition between modes