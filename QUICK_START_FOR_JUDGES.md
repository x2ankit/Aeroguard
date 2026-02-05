# QUICK START GUIDE FOR HACKATHON JUDGES

## ⚡ Run the Demo in 3 Commands

```bash
# 1. Navigate to project
cd /Users/sahin/Desktop/project/flight-ad-main

# 2. Activate environment (if needed)
source .venv/bin/activate

# 3. Run the demo
python demo_for_judges.py
```

**Expected output:** 21 seconds, 16 anomalies detected, 2 CSV files generated

---

## 📊 View Results

```bash
# See the 16 anomalous flights
cat anomalies_only.csv

# Or open in spreadsheet
open anomalies_only.csv
```

---

## 🎯 Key Files Created

| File | Purpose |
|------|---------|
| `demo_for_judges.py` | Live demonstration script |
| `anomalies_only.csv` | 16 flagged anomalous flights |
| `anomaly_report.csv` | All 400 flights with labels |
| `HACKATHON_PRESENTATION_GUIDE.md` | Complete presentation guide |
| `PROJECT_ANALYSIS.md` | Technical documentation |

---

## 💡 Where Anomalies Are Stored

**In Memory:**
```python
labels = learner.pipeline['dbscan'].labels_
# -1 = anomaly, 0+ = normal cluster
```

**On Disk:**
- `anomalies_only.csv` - Just the 16 anomalies
- `anomaly_report.csv` - All 400 flights

---

## 📈 Results Summary

```
✓ 400 flights processed in 21.5 seconds
✓ 16 anomalies detected (4.00%)
✓ 5 high severity, 2 medium, 9 low
✓ Zero manual tuning required
✓ Processing speed: 18.6 flights/second
```

---

**Good luck! 🚀**
