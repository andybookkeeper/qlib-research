# Phase 2 Roadmap and Enhancement Strategy
# Planned extensions beyond MVP

## Phase 2 Goals (Post-MVP)

### Q1 2025: Live Trading
- [ ] Interactive Brokers SDK integration
- [ ] Real account support (with kill switch)
- [ ] Order status webhooks
- [ ] Position and P&L reconciliation
- [ ] Account funding/withdrawal

### Q2 2025: Intraday + Options
- [ ] 1-minute bar data (Yahoo/broker API)
- [ ] Intraday model training (TimeSeriesSplit on minute bars)
- [ ] Options order entry (requires validated data source)
- [ ] Greeks-based options strategies
- [ ] Volatility term structure

### Q3 2025: ML & Scaling
- [ ] XGBoost, CatBoost models
- [ ] LSTM neural networks (20-50 day lookback)
- [ ] Model ensemble (voting, stacking)
- [ ] Hyperparameter optimization (Optuna)
- [ ] Feature selection (SHAP, permutation importance)

### Q4 2025: Multi-Tenant & Production
- [ ] Multi-user with authentication (OAuth)
- [ ] PostgreSQL (upgrade from SQLite)
- [ ] Per-user portfolio isolation
- [ ] Role-based access control (admin, trader, viewer)
- [ ] Database backups and recovery

### 2026: Cloud & Automation
- [ ] AWS/GCP deployment (ECS, Cloud Run)
- [ ] Kubernetes for scaling
- [ ] CI/CD (GitHub Actions, GitLab CI)
- [ ] Automated retraining pipeline (weekly/monthly)
- [ ] Model monitoring and alerting

## Estimated Effort

| Phase | Duration | Engineer-Months |
|-------|----------|-----------------|
| MVP (Phase 1) | Complete | 3-4 |
| Phase 2a (Live Trading) | Q1 2025 | 1.5-2 |
| Phase 2b (Intraday) | Q2 2025 | 2-2.5 |
| Phase 2c (ML) | Q3 2025 | 2-3 |
| Phase 2d (Multi-tenant) | Q4 2025 | 1.5-2 |
| Phase 3 (Cloud) | 2026 | 2-3 |
| **Total** | 2 years | 12-16.5 |

## Known Technical Debt

1. **Options data quality**: Yahoo Finance IV is stale/inaccurate. Need:
   - Bloomberg API (expensive, requires subscription)
   - OptionChain API (paid)
   - Broker-provided Greeks (IBKR, TD Ameritrade)

2. **Intraday data**: Daily data limits alpha signal quality. Need:
   - 1-5 minute bars for better timing
   - But requires live market data feed (expensive)

3. **Backtesting assumptions**:
   - Assumes fills at last close (realistic for EOD)
   - No slippage modeling
   - No commission/fees until Phase 2

4. **Model retraining**: Currently manual. Should automate:
   - Weekly model retraining
   - Performance monitoring
   - Automatic rollback if degraded

5. **Risk limits**: Currently soft warnings. Should upgrade:
   - Hard position limits
   - VaR stop-losses
   - Correlation-based concentration limits

## Success Metrics (Phase 2+)

| Metric | Target |
|--------|--------|
| Sharpe Ratio (live) | > 1.0 |
| Win Rate | > 52% |
| Max Drawdown | < -15% |
| Monthly Return | 2-3% |
| Uptime | 99.5% |
| Model Accuracy | > 55% directional |
| Data Lag | < 1 minute |

## Risk Mitigations

1. **Market Risk**: Diversify across multiple stocks (>50 holding)
2. **Model Risk**: Ensemble + walk-forward validation
3. **Data Risk**: Multiple data sources, fallback mechanism
4. **Technical Risk**: Comprehensive logging, automated alerts
5. **Operational Risk**: Paper trading only until proven

## Resource Requirements (Phase 2)

- **1-2 ML engineers** (feature engineering, model building)
- **1 backend engineer** (broker integration, API scaling)
- **0.5 frontend engineer** (UI for new features)
- **0.5 DevOps engineer** (cloud infrastructure)
- **0.5 data analyst** (data quality, monitoring)

**Total: 3.5 FTE**

## External Dependencies

| Dependency | Phase | Status |
|-----------|-------|--------|
| IBKR API | Phase 2a | Available |
| Yahoo Finance | Current | Free, rate-limited |
| Bloomberg API | Phase 2b | Requires subscription ($5k+/month) |
| AWS/GCP | Phase 3 | Available on-demand |
| MLflow | Current | Free, open-source |

## Acceptance Criteria

- [ ] Roadmap documented
- [ ] Effort estimated
- [ ] Dependencies identified
- [ ] Team requirements clear
- [ ] Success metrics defined
