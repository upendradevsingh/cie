# SalesLens Testing Guide

Complete guide to test all new features locally.

---

## 🚀 Quick Start

### **Step 1: Start the Backend**

```bash
# Start all services
docker-compose up -d

# Check they're running
docker-compose ps
```

Expected output:
```
NAME                         STATUS
saleslens-backend-1          Up
saleslens-db-1               Up
saleslens-redis-1            Up
saleslens-worker-1           Up
saleslens-frontend-1         Up
```

---

### **Step 2: Run Database Migration**

```bash
# Option A: Using the helper script (recommended)
./RUN_MIGRATION.sh

# Option B: Manual via Docker
docker-compose exec backend alembic upgrade head

# Option C: Manual via local Python (if not using Docker)
cd backend
source .venv/bin/activate
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 2026_03_02_0003 -> 2026_03_02_0004, add lead and data capture question models
```

---

### **Step 3: Verify Backend is Ready**

```bash
# Check health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

You should see the new endpoints:
- ✅ `GET /api/v1/analytics/correlations`
- ✅ `GET /api/v1/leads`
- ✅ `GET /api/v1/leads/{lead_id}`
- ✅ `GET /api/v1/data-capture-questions`
- ✅ `POST /api/v1/data-capture-questions`

---

### **Step 4: Create Test User & Upload Sample Data**

```bash
# Create tenant and admin user
curl -X POST http://localhost:8000/api/v1/auth/tenant \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Test Corp",
    "tenant_slug": "test-corp",
    "admin_email": "admin@test.com",
    "admin_password": "test123",
    "admin_name": "Test Admin"
  }'

# Save the access_token from response
```

**Optional: Upload sample call recording**

```bash
# Get a sample call recording (or use your own)
# Download: https://github.com/your-org/saleslens/tree/main/test-data/sample-call.mp3

# Upload it
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v1/calls/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/sample-call.mp3" \
  -F "lead_name=John Doe" \
  -F "lead_id=lead-001" \
  -F "lead_phone=+1234567890" \
  -F "agent_name=Test Agent"
```

---

### **Step 5: Run Automated Feature Tests**

```bash
# Install Python requests if needed
pip install requests

# Run the test suite
python test_new_features.py
```

**Expected Output:**
```
============================================================
1. AUTHENTICATION
============================================================

✓ Logged in as admin@test.com
ℹ Tenant ID: 123e4567-e89b-12d3-a456-426614174000

============================================================
2. CORRELATION ANALYSIS
============================================================

✓ Correlation analysis retrieved successfully
ℹ Calls analyzed: 5
ℹ Hot leads: 2
ℹ Cold leads: 1

Top Performing Parameters:
  • Closing Technique: correlation=0.35, impact=high
  • Need Discovery: correlation=0.28, impact=medium

Recommendations:
  → Focus coaching on 'Closing Technique' — it shows the strongest correlation

============================================================
3. LEAD-LEVEL ROLLUP
============================================================

✓ Retrieved 1 leads
ℹ
Sample Lead: John Doe
  • Lead ID: lead-001
  • Total Calls: 1
  • Avg Quality: 78.5
  • Classification: warm
  • Quality Trend: stable
  • Follow-up Urgency: this_week

============================================================
TEST SUMMARY
============================================================

✓ Correlation Analysis
✓ Lead Rollup
✓ Data Capture Questions
✓ Weekly Reports
✓ Analytics

Results: 5/5 tests passed

🎉 All features working correctly!
```

---

## 🧪 Manual Testing

### **Test 1: Correlation Analysis**

```bash
TOKEN="your_token"

curl http://localhost:8000/api/v1/analytics/correlations?period_days=30 \
  -H "Authorization: Bearer $TOKEN" | jq
```

**What to check:**
- ✅ Returns parameter correlations
- ✅ Shows top drivers and negative indicators
- ✅ Provides actionable recommendations

---

### **Test 2: Lead Rollup**

```bash
# List leads
curl http://localhost:8000/api/v1/leads \
  -H "Authorization: Bearer $TOKEN" | jq

# Get specific lead
curl http://localhost:8000/api/v1/leads/lead-001 \
  -H "Authorization: Bearer $TOKEN" | jq
```

**What to check:**
- ✅ Shows aggregated data from multiple calls
- ✅ Displays quality trend (improving/declining/stable)
- ✅ Lists top objections and pain points
- ✅ Shows BANT scores
- ✅ Includes recommended next steps

---

### **Test 3: Data Capture Questions**

```bash
# Create a question
curl -X POST http://localhost:8000/api/v1/data-capture-questions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the customers budget range?",
    "field_name": "budget_range",
    "expected_type": "text",
    "category": "qualification"
  }' | jq

# List questions
curl http://localhost:8000/api/v1/data-capture-questions \
  -H "Authorization: Bearer $TOKEN" | jq
```

**What to check:**
- ✅ Can create up to 10 questions per tenant
- ✅ Questions have display order
- ✅ Can be activated/deactivated
- ✅ Categorized for organization

---

### **Test 4: Weekly Reports**

```bash
# Generate report
curl -X POST http://localhost:8000/api/v1/reports/weekly \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "week_start": "2026-02-24"
  }' | jq

# List reports
curl http://localhost:8000/api/v1/reports/weekly \
  -H "Authorization: Bearer $TOKEN" | jq

# Get specific report
curl http://localhost:8000/api/v1/reports/weekly/{report_id} \
  -H "Authorization: Bearer $TOKEN" | jq
```

**What to check:**
- ✅ Report generates successfully
- ✅ Shows team summary
- ✅ Agent breakdowns included
- ✅ Hot leads highlighted
- ✅ Week-over-week trends displayed

---

## 🎨 Frontend Testing

### **1. Open Dashboard**

```bash
open http://localhost:3000
```

**Login with:**
- Email: `admin@test.com`
- Password: `test123`

---

### **2. Test New Features in UI**

**📊 Correlation Analysis:**
- Go to Analytics page
- Click "View Correlations" (if added to UI)
- Check which parameters drive success

**👥 Lead Management:**
- Go to Leads page (if added to nav)
- See list of all leads with aggregated data
- Click on a lead to see detailed view
- Check quality trend visualization

**📝 Data Capture Questions:**
- Go to Settings
- Navigate to "Data Capture Questions"
- Add/edit questions
- Test activation/deactivation

**📄 Weekly Reports:**
- Go to Reports page
- Click "Generate Report"
- Select week and generate
- View detailed breakdown

---

## 🔍 Troubleshooting

### **Migration fails with "relation already exists"**

```bash
# Check current migration version
docker-compose exec backend alembic current

# If stuck, rollback and retry
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head
```

---

### **Test script fails with "Connection refused"**

```bash
# Check backend is running
docker-compose ps

# Check logs
docker-compose logs backend

# Restart if needed
docker-compose restart backend
```

---

### **No data in correlation analysis**

You need at least 10 completed calls with different intent classifications.

```bash
# Upload more test calls
# Or use the sample data loader (if you created one)
python load_sample_data.py
```

---

## 📊 Expected Database State

After migration, you should have these new tables:

```sql
-- Check tables exist
docker-compose exec db psql -U saleslens -d saleslens -c "\dt"

-- Expected output includes:
--   leads
--   data_capture_questions
```

**Verify:**

```bash
docker-compose exec db psql -U saleslens -d saleslens -c "
  SELECT COUNT(*) FROM leads;
  SELECT COUNT(*) FROM data_capture_questions;
"
```

---

## ✅ Success Criteria

All tests pass when:

- [x] Migration runs without errors
- [x] New API endpoints return 200 OK
- [x] Correlation analysis returns data (or "insufficient data" message)
- [x] Lead rollup aggregates call data correctly
- [x] Data capture questions can be created/listed
- [x] Weekly reports generate successfully
- [x] Frontend displays new features
- [x] No errors in backend logs

---

## 🎉 Ready for Production!

Once all tests pass:

1. **Commit any remaining changes**
2. **Push to remote:** `git push origin main`
3. **Deploy to staging/production**
4. **Run migration on production**
5. **Monitor logs for any issues**

---

## 📞 Need Help?

If tests fail or you encounter issues:

1. Check `docker-compose logs backend`
2. Check `docker-compose logs worker`
3. Verify `.env` configuration
4. Ensure all services are running
5. Check database connectivity

**Happy testing! 🚀**
