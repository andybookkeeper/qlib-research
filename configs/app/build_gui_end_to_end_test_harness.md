# Build GUI End-to-End Test Harness Specification
# Selenium/Playwright UI testing

## Overview

End-to-end tests covering:
1. **Login flow** (future)
2. **Order entry** → Validation → Submission → Confirmation
3. **Portfolio view** → Refresh → P&L update
4. **Backtest** → Run → Results display
5. **Error handling** → Validation errors, network failures

## Implementation (Playwright)

```python
# tests/e2e/test_paper_trading_ui.py

import pytest
from playwright.sync_api import expect
import asyncio

@pytest.fixture(scope="session")
async def browser():
    """Start browser for session"""
    from playwright.sync_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    """Get new page"""
    page = await browser.new_page()
    await page.goto("http://localhost:5173")  # Vite dev server
    yield page
    await page.close()

async def test_order_entry_and_submit(page):
    """Test complete order flow"""
    
    # 1. Navigate to trading
    await page.click('a:has-text("Trading")')
    await page.wait_for_selector('text=Place Order')
    
    # 2. Fill form
    await page.fill('input[placeholder="e.g., AAPL"]', 'AAPL')
    await page.select_option('select:has-text("Side")', 'buy')
    await page.fill('input[placeholder="100"]', '100')
    
    # 3. Submit
    await page.click('button:has-text("Submit Order")')
    
    # 4. Verify confirmation
    await page.wait_for_selector('text=Order submitted')
    
    # 5. Check order appears in table
    await expect(page.locator('tr:has-text("AAPL")')).to_be_visible()

async def test_portfolio_refresh(page):
    """Test real-time portfolio updates"""
    
    # 1. Navigate to portfolio
    await page.click('a:has-text("Portfolio")')
    
    # 2. Capture initial value
    initial_value = await page.inner_text('text=Total Value:')
    
    # 3. Wait for refresh
    await page.wait_for_timeout(5000)
    
    # 4. Check value updated
    updated_value = await page.inner_text('text=Total Value:')
    
    # They may differ if price changed
    assert initial_value is not None and updated_value is not None

async def test_backtest_execution(page):
    """Test backtest workflow"""
    
    # 1. Go to analysis
    await page.click('a:has-text("Analysis")')
    
    # 2. Start backtest
    await page.click('button:has-text("Run Backtest")')
    
    # 3. Wait for results
    await page.wait_for_selector('text=Backtest Complete', timeout=30000)
    
    # 4. Verify metrics displayed
    await expect(page.locator('text=Sharpe Ratio')).to_be_visible()
    await expect(page.locator('text=Win Rate')).to_be_visible()

async def test_validation_error_handling(page):
    """Test form validation"""
    
    await page.click('a:has-text("Trading")')
    
    # Submit empty form
    await page.click('button:has-text("Submit Order")')
    
    # Should show error
    await expect(page.locator('text=Invalid input')).to_be_visible()

async def test_network_error_recovery(page):
    """Test graceful error handling"""
    
    # Simulate offline
    await page.context.set_offline(True)
    
    # Try to fetch portfolio
    await page.click('a:has-text("Portfolio")')
    
    # Should show error message
    await expect(page.locator('text=Failed to fetch')).to_be_visible()
    
    # Restore connection
    await page.context.set_offline(False)
    
    # Retry should work
    await page.click('button:has-text("Retry")')
    await page.wait_for_selector('text=Portfolio')
```

## Acceptance Criteria

- [ ] Playwright setup complete
- [ ] Order entry E2E test passing
- [ ] Portfolio refresh test passing
- [ ] Backtest execution test passing
- [ ] Validation error test passing
- [ ] Network error handling test passing
- [ ] 90%+ test coverage
