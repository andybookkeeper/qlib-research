# Build GUI Application Shell Specification
# React/Vue entry point, routing, layout

## Overview

```
App.tsx (Main entry)
├── Layout (Header, Sidebar, Main)
├── Routes
│   ├── Market (Watch price, charts)
│   ├── Analysis (Backtest, feature view)
│   ├── Trading (Order entry, manual trading)
│   ├── Portfolio (Positions, P&L)
│   ├── Research (Model metrics, signals)
│   └── Settings (Risk limits, preferences)
└── Auth (Login modal if multi-user future)
```

## Key Files

```typescript
// src/app/App.tsx

import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { MarketScreen } from './screens/Market';
import { AnalysisScreen } from './screens/Analysis';
import { TradingScreen } from './screens/Trading';
import { PortfolioScreen } from './screens/Portfolio';
import { ResearchScreen } from './screens/Research';
import { SettingsScreen } from './screens/Settings';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<MarketScreen />} />
          <Route path="/analysis" element={<AnalysisScreen />} />
          <Route path="/trading" element={<TradingScreen />} />
          <Route path="/portfolio" element={<PortfolioScreen />} />
          <Route path="/research" element={<ResearchScreen />} />
          <Route path="/settings" element={<SettingsScreen />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
};
```

## Acceptance Criteria

- [ ] React app compiles
- [ ] All routes working
- [ ] Navigation between screens
- [ ] Layout renders correctly
- [ ] Error boundary implemented
- [ ] API integration working
