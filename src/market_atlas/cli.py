from __future__ import annotations

import argparse
from datetime import date

from dotenv import load_dotenv

from market_atlas.config import AppConfig
from market_atlas.core.db import connect, init_db, reset_db
from market_atlas.exports.sapphire_signal import export_signals
from market_atlas.pipelines.backtest import run_backtest
from market_atlas.pipelines.features import rebuild_features
from market_atlas.pipelines.ingest import ingest_all, ingest_domains
from market_atlas.pipelines.intelligence import build_operator_brief
from market_atlas.pipelines.reporting import build_report
from market_atlas.pipelines.regimes import rebuild_regimes


def _date_or_default(value: str | None, fallback: str) -> str:
    return value or fallback


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Market Atlas AI CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")
    sub.add_parser("reset-db")

    ingest_p = sub.add_parser("ingest")
    ingest_p.add_argument("--start-date", default=None)
    ingest_p.add_argument(
        "--domains",
        default="all",
        help="Comma-separated: all|crypto|equities|commodities|macro|news|oss|betting",
    )

    sub.add_parser("features")
    sub.add_parser("regimes")

    backtest_p = sub.add_parser("backtest")
    backtest_p.add_argument("--strategy", default="momentum_regime")
    backtest_p.add_argument("--start-date", default="2024-01-01")
    backtest_p.add_argument("--end-date", default=str(date.today()))
    backtest_p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,SPY,QQQ,GLD,SLV")

    export_p = sub.add_parser("export-signals")
    export_p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT")
    export_p.add_argument("--output", default="data/latest_signals.json")

    report_p = sub.add_parser("report")
    report_p.add_argument("--run-id", default=None)
    report_p.add_argument("--output-dir", default="reports/latest")

    brief_p = sub.add_parser("brief")
    brief_p.add_argument("--symbols", default="BTCUSDT,ETHUSDT,SOLUSDT,SPY,QQQ,GLD,SLV,CL=F")
    brief_p.add_argument("--output", default="reports/latest/operator_brief.json")

    full = sub.add_parser("full-run")
    full.add_argument("--start-date", default="2024-01-01")
    full.add_argument("--end-date", default=str(date.today()))

    args = parser.parse_args()
    cfg = AppConfig.from_env()
    conn = connect(str(cfg.db_path))

    if args.command == "init-db":
        init_db(conn)
        print(f"✅ initialized db: {cfg.db_path}")
        return

    if args.command == "reset-db":
        reset_db(conn)
        init_db(conn)
        print(f"✅ reset db: {cfg.db_path}")
        return

    init_db(conn)

    if args.command == "ingest":
        start_date = _date_or_default(args.start_date, cfg.default_start_date)
        if args.domains.strip().lower() == "all":
            stats = ingest_all(conn, cfg, start_date)
        else:
            stats = ingest_domains(conn, cfg, start_date, args.domains.split(","))
        print("✅ ingest complete", stats)
        return

    if args.command == "features":
        count = rebuild_features(conn)
        print(f"✅ rebuilt features rows: {count}")
        return

    if args.command == "regimes":
        count = rebuild_regimes(conn)
        print(f"✅ rebuilt regimes rows: {count}")
        return

    if args.command == "backtest":
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        summary = run_backtest(
            conn=conn,
            strategy_name=args.strategy,
            symbols=symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            fee_bps=cfg.fee_bps,
            slippage_bps=cfg.slippage_bps,
            base_capital=cfg.base_capital,
        )
        print("✅ backtest complete", summary)
        return

    if args.command == "export-signals":
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        signals = export_signals(conn, symbols=symbols, output_path=args.output)
        print(f"✅ exported {len(signals)} signals to {args.output}")
        return

    if args.command == "report":
        artifact = build_report(conn, run_id=args.run_id, output_dir=args.output_dir)
        print("✅ report complete", artifact)
        return

    if args.command == "brief":
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
        brief = build_operator_brief(conn, symbols=symbols, output_path=args.output)
        print("✅ operator brief complete", brief)
        return

    if args.command == "full-run":
        stats = ingest_all(conn, cfg, args.start_date)
        feat = rebuild_features(conn)
        reg = rebuild_regimes(conn)
        report_symbols = cfg.crypto_symbols + [s for s in ["SPY", "QQQ", "GLD", "SLV", "CL=F"] if s in cfg.equity_symbols]
        summary = run_backtest(
            conn=conn,
            strategy_name="momentum_regime",
            symbols=report_symbols,
            start_date=args.start_date,
            end_date=args.end_date,
            fee_bps=cfg.fee_bps,
            slippage_bps=cfg.slippage_bps,
            base_capital=cfg.base_capital,
        )
        signals = export_signals(conn, cfg.crypto_symbols, "data/latest_signals.json")
        report = build_report(conn, run_id=summary.get("run_id"), output_dir="reports/latest")
        brief = build_operator_brief(conn, symbols=report_symbols, output_path="reports/latest/operator_brief.json")
        print(
            "✅ full-run complete",
            {
                "ingest": stats,
                "features": feat,
                "regimes": reg,
                "backtest": summary,
                "signals": len(signals),
                "report": report,
                "brief": brief,
            },
        )
        return


if __name__ == "__main__":
    main()
