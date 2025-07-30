# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-07-30-live-pl-calculation-#28/spec.md

> Created: 2025-07-30
> Status: Ready for Implementation

## Tasks

- [x] 1. Create Database Schema and Models
  - [x] 1.1 Write tests for new Position model fields
  - [x] 1.2 Create migration to add P/L fields to positions table
  - [x] 1.3 Write tests for PositionSnapshot model
  - [x] 1.4 Create position_snapshots table and model
  - [x] 1.5 Run migration and verify schema changes
  - [x] 1.6 Verify all tests pass

- [x] 2. Implement P/L Calculation Service
  - [x] 2.1 Write tests for PLCalculationService class
  - [x] 2.2 Create PLCalculationService with position value calculation
  - [x] 2.3 Implement unrealized P/L and percentage calculations
  - [x] 2.4 Add stop-loss alert detection logic
  - [x] 2.5 Implement batch calculation for all positions
  - [x] 2.6 Verify all tests pass

- [x] 3. Create P/L API Endpoints
  - [x] 3.1 Write tests for P/L API endpoints
  - [x] 3.2 Implement GET /api/v1/positions/pl/current endpoint
  - [x] 3.3 Implement GET /api/v1/positions/{id}/pl/history endpoint
  - [x] 3.4 Implement POST /api/v1/positions/pl/calculate endpoint
  - [x] 3.5 Add API documentation
  - [x] 3.6 Verify all tests pass

- [x] 4. Integrate WebSocket P/L Updates
  - [x] 4.1 Write tests for WebSocket P/L broadcasting
  - [x] 4.2 Extend WebSocketManager to handle P/L updates
  - [x] 4.3 Subscribe P/L service to SPY price updates
  - [x] 4.4 Implement pl_update message broadcasting
  - [x] 4.5 Add throttling to prevent update spam
  - [x] 4.6 Verify all tests pass

- [ ] 5. Schedule P/L Snapshot Job
  - [ ] 5.1 Write tests for scheduled P/L snapshots
  - [ ] 5.2 Add calculate_pl_snapshot job to scheduler
  - [ ] 5.3 Configure 15-minute interval during market hours
  - [ ] 5.4 Implement snapshot storage logic
  - [ ] 5.5 Test job execution and timing
  - [ ] 5.6 Verify all tests pass

- [ ] 6. Create Frontend P/L Components
  - [ ] 6.1 Write tests for P/L display components
  - [ ] 6.2 Create PLDisplay component for current P/L
  - [ ] 6.3 Implement PLHistory chart component
  - [ ] 6.4 Add stop-loss alert indicators
  - [ ] 6.5 Integrate WebSocket pl_update handling
  - [ ] 6.6 Verify all tests pass

- [ ] 7. Integration Testing and Polish
  - [ ] 7.1 Test complete P/L workflow end-to-end
  - [ ] 7.2 Verify real-time updates with live data
  - [ ] 7.3 Test stop-loss alerts trigger correctly
  - [ ] 7.4 Performance test with multiple positions
  - [ ] 7.5 Update documentation
  - [ ] 7.6 Verify all tests pass