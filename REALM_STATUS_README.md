# Realm Status Monitoring System

This system enables Ashoka to fetch, store, and analyze status data from Realm canisters for governance insights and monitoring.

## Features

- **DFX Integration**: Fetch current status from Realm canisters using DFX canister calls with JSON output
- **Database Storage**: Store historical status data for trend analysis as unstructured JSON
- **Background Scheduling**: Automatic periodic status collection
- **REST API**: Complete API for managing realm status data
- **Health Scoring**: Calculate health metrics based on realm activity
- **Network Support**: Support for IC mainnet and local development networks
- **Security**: Proper handling of DFX identity warnings for read-only operations

## Database Schema

The system adds a `realm_status` table with a simplified structure that stores all realm data as unstructured JSON:

```sql
CREATE TABLE realm_status (
    id SERIAL PRIMARY KEY,
    realm_principal TEXT NOT NULL,
    realm_url TEXT NOT NULL,
    status_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The `status_data` field contains the complete JSON response from the realm's status endpoint, allowing for flexible storage of any realm status information without schema constraints.

## Configuration

### Environment Variables

- `REALM_STATUS_SCHEDULER_ENABLED`: Enable/disable background scheduler (default: false)
- `REALM_STATUS_FETCH_INTERVAL`: Fetch interval in seconds (default: 300)
- `REALM_STATUS_NETWORK`: Network to use for DFX calls (default: ic)
- `REALMS_CONFIG`: JSON string with realm configurations

### Realms Configuration

Create `realms_config.json` or set `REALMS_CONFIG` environment variable:

```json
[
  {
    "principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
    "url": "https://rdmx6-jaaaa-aaaah-qcaiq-cai.ic0.app",
    "name": "Demo Realm"
  }
]
```

## API Endpoints

### Status Fetching

- `POST /api/realm-status/fetch` - Fetch status for a specific realm
- `POST /api/realm-status/batch-fetch` - Fetch status for multiple realms
- `GET /api/realm-status/{principal}` - Get latest status for a realm
- `GET /api/realm-status/{principal}/history` - Get status history
- `GET /api/realm-status/all` - Get all realms latest status

### Scheduler Management

- `GET /api/realm-status/scheduler/status` - Get scheduler status
- `POST /api/realm-status/scheduler/start` - Start scheduler
- `POST /api/realm-status/scheduler/stop` - Stop scheduler
- `POST /api/realm-status/scheduler/fetch-now` - Trigger immediate fetch
- `POST /api/realm-status/scheduler/realms` - Add realm to scheduler
- `DELETE /api/realm-status/scheduler/realms/{principal}` - Remove realm

## Usage Examples

### Fetch Single Realm Status
```bash
curl -X POST http://localhost:5000/api/realm-status/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "realm_principal": "rdmx6-jaaaa-aaaah-qcaiq-cai",
    "network": "ic"
  }'
```

### Get Realm Status Summary

```bash
curl http://localhost:5000/api/realm-status/rdmx6-jaaaa-aaaah-qcaiq-cai
```

### Start Background Scheduler

```bash
curl -X POST http://localhost:5000/api/realm-status/scheduler/start
```

## Health Scoring

The system calculates a health score (0-100) based on:

- **Base Score (50)**: Realm is online and responding
- **User Activity (20)**: Has registered users
- **Organizations (10)**: Has active organizations
- **Extensions (10)**: Has installed extensions
- **Recent Activity (10)**: Has recent governance activity

## Database Setup

Run the updated schema to create the realm_status table:

```bash
psql -h localhost -U ashoka_user -d ashoka_db -f database/schema.sql
```

## Integration with Ashoka

The realm status data is automatically available to Ashoka's AI responses through the existing conversation context system. When users ask questions about realm status, Ashoka can reference the stored data for accurate, up-to-date information.

## Monitoring and Alerts

The system provides comprehensive logging and can be extended with alerting for:

- Realm downtime detection
- Significant changes in user/organization counts
- Extension installation/removal
- Performance degradation

## Development

### Running Locally

1. Ensure PostgreSQL is running with the ashoka_db database
2. Update database schema: `psql -f database/schema.sql`
3. Set environment variables for scheduler if desired
4. Start Ashoka: `python api.py`

### Testing

Test the status fetching functionality:

```python
from realm_status_service import RealmStatusService

service = RealmStatusService()
status = service.fetch_and_store_realm_status(
    "rdmx6-jaaaa-aaaah-qcaiq-cai",
    "https://rdmx6-jaaaa-aaaah-qcaiq-cai.ic0.app"
)
```

## Future Enhancements

- IC Agent integration for direct canister calls
- Real-time WebSocket status updates
- Advanced analytics and trend detection
- Custom alerting rules
- Multi-network support (beyond IC mainnet)
