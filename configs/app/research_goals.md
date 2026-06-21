# Research Goals

## Primary objectives

1. **Build a Qlib-backed research workflow** for stocks first, then extend to options.
2. **Support manual trade preparation** and paper trading before any live order routing.
3. **Keep quantitative research, signal generation, and UI execution flows separated** so each can evolve independently.
4. **Preserve a clean path** from data ingestion → feature generation → training → backtesting → signal serving.
5. **Make the built-in GUI usable** for interactive validation of the entire workflow.

## Success criteria for this step

- Qlib can initialize from a repo-local or external provider path.
- The app has an explicit paper-trading-first boundary.
- The UI workflow can support manual analysis and order preview.
- The roadmap remains sequenced so research precedes execution and UI wiring.

## Next steps

Once research goals are defined, move to:

1. Defining supported assets and modes
2. Defining user flows
3. Defining data and Qlib boundary
4. Defining acceptance criteria

Then proceed to the brokerage stack and market data pipeline.
