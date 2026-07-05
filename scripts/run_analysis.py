"""
Runs the full analysis suite against db/retail.db:
  1. Applies indexes (sql/02_indexes.sql) to the shipped database.
  2. Runs each analysis query, saving results to results/*.csv.
  3. Renders charts to visuals/*.png.
  4. Benchmarks a representative query before vs. after indexing (on
     throwaway copies of the pre-index database) and prints the result.

Run this after scripts/build_db.py. Everything printed here is the source
of every number quoted in README.md -- nothing is hand-typed.
"""
import os
import shutil
import sqlite3
import statistics
import tempfile
import time
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "db", "retail.db")
SQL_DIR = os.path.join(ROOT, "sql")
RESULTS_DIR = os.path.join(ROOT, "results")
VISUALS_DIR = os.path.join(ROOT, "visuals")

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#333333",
    "axes.grid": True,
    "grid.color": "#e0e0e0",
    "grid.linewidth": 0.6,
    "font.size": 11,
})
PALETTE = ["#2E5C8A", "#E8813A", "#4C9A73", "#B84C4C", "#7A5EA8", "#C9A227"]


def read_sql(name):
    with open(os.path.join(SQL_DIR, name)) as f:
        return f.read()


def run_query_df(conn, sql):
    return pd.read_sql_query(sql, conn)


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(VISUALS_DIR, exist_ok=True)

    # ---- 0. Apply indexes to the shipped DB ----
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(read_sql("02_indexes.sql"))
    conn.commit()

    # ---- 1. Revenue growth ----
    section("Revenue growth")
    rev = run_query_df(conn, read_sql("03_revenue_growth.sql"))
    rev.to_csv(os.path.join(RESULTS_DIR, "revenue_growth.csv"), index=False)
    print(rev.tail(6).to_string(index=False))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(rev["month"], rev["revenue"], color=PALETTE[0], alpha=0.55, label="Monthly revenue")
    ax.plot(rev["month"], rev["rolling_3mo_avg_revenue"], color=PALETTE[1], linewidth=2.4, marker="o", markersize=3, label="3-month rolling avg")
    ax.set_title("Monthly Revenue with 3-Month Rolling Average", fontsize=13, fontweight="bold")
    ax.set_ylabel("Revenue ($)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:.0f}K"))
    ax.set_xticks(range(0, len(rev), 3))
    ax.set_xticklabels(rev["month"].iloc[::3], rotation=45, ha="right")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(VISUALS_DIR, "revenue_trend.png"), dpi=150)
    plt.close(fig)

    # ---- 2. Cohort retention ----
    section("Cohort retention")
    coh = run_query_df(conn, read_sql("04_cohort_retention.sql"))
    coh.to_csv(os.path.join(RESULTS_DIR, "cohort_retention.csv"), index=False)
    pivot = coh.pivot(index="cohort_month", columns="month_number", values="active_customers")
    pct = pivot.div(pivot[0], axis=0) * 100
    m3 = pct[3].dropna() if 3 in pct.columns else pd.Series(dtype=float)
    m6 = pct[6].dropna() if 6 in pct.columns else pd.Series(dtype=float)
    print(f"Cohorts tracked: {len(pct)}")
    print(f"Avg month-3 retention: {m3.mean():.1f}%  (n={len(m3)} cohorts)")
    print(f"Avg month-6 retention: {m6.mean():.1f}%  (n={len(m6)} cohorts)")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    display_cols = [c for c in pct.columns if c <= 9]
    im = ax.imshow(pct[display_cols].values, cmap="YlGnBu", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(len(display_cols)))
    ax.set_xticklabels(display_cols)
    ax.set_yticks(range(len(pct)))
    ax.set_yticklabels(pct.index, fontsize=8)
    ax.set_xlabel("Months since first purchase")
    ax.set_title("Cohort Retention Heatmap (% active by month)", fontsize=13, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("% of cohort still active")
    fig.tight_layout()
    fig.savefig(os.path.join(VISUALS_DIR, "cohort_retention_heatmap.png"), dpi=150)
    plt.close(fig)

    # ---- 3. RFM segmentation ----
    section("RFM segmentation")
    rfm = run_query_df(conn, read_sql("05_rfm_segmentation.sql"))
    rfm.to_csv(os.path.join(RESULTS_DIR, "rfm_segmentation.csv"), index=False)
    seg = rfm.groupby("segment").agg(customers=("customer_id", "count"), revenue=("monetary", "sum"))
    seg["pct_customers"] = (100 * seg["customers"] / seg["customers"].sum()).round(1)
    seg["pct_revenue"] = (100 * seg["revenue"] / seg["revenue"].sum()).round(1)
    seg = seg.sort_values("revenue", ascending=False)
    print(seg)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    order = seg.index.tolist()
    colors = PALETTE[:len(order)]
    axes[0].bar(order, seg["pct_customers"], color=colors)
    axes[0].set_title("Share of Customers", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("% of customers")
    axes[0].tick_params(axis="x", rotation=30)
    axes[1].bar(order, seg["pct_revenue"], color=colors)
    axes[1].set_title("Share of Revenue", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("% of revenue")
    axes[1].tick_params(axis="x", rotation=30)
    fig.suptitle("RFM Segments: Customers vs. Revenue Contribution", fontsize=13, fontweight="bold", y=1.03)
    fig.tight_layout()
    fig.savefig(os.path.join(VISUALS_DIR, "rfm_segments.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)

    champions = seg.loc["Champions"]
    print(f"\nHEADLINE: Champions = {champions['pct_customers']}% of customers -> {champions['pct_revenue']}% of revenue")

    # ---- 4. Channel ROI ----
    section("Channel ROI (CAC vs LTV)")
    roi = run_query_df(conn, read_sql("06_channel_roi.sql"))
    roi.to_csv(os.path.join(RESULTS_DIR, "channel_roi.csv"), index=False)
    print(roi.to_string(index=False))
    best = roi.iloc[0]
    worst = roi.iloc[-1]
    multiple = best["ltv_cac_ratio"] / worst["ltv_cac_ratio"]
    print(f"\nHEADLINE: best channel ({best['channel']}, ratio {best['ltv_cac_ratio']}) is "
          f"{multiple:.1f}x more capital-efficient than worst ({worst['channel']}, ratio {worst['ltv_cac_ratio']})")

    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    x = range(len(roi))
    ax1.bar(x, roi["cac"], width=0.35, label="CAC ($)", color=PALETTE[3], alpha=0.85)
    ax1.set_ylabel("CAC ($)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(roi["channel"], rotation=20)
    ax2 = ax1.twinx()
    ax2.plot(x, roi["ltv_cac_ratio"], color=PALETTE[2], marker="o", linewidth=2.5, label="LTV:CAC ratio")
    ax2.set_ylabel("LTV : CAC ratio")
    ax2.grid(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, frameon=False, loc="upper right")
    ax1.set_title("Acquisition Channel Efficiency: CAC vs. LTV:CAC Ratio", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(VISUALS_DIR, "channel_roi.png"), dpi=150)
    plt.close(fig)

    # ---- 5. Product performance ----
    section("Top products per category (sample)")
    prod = run_query_df(conn, read_sql("07_product_performance.sql"))
    prod.to_csv(os.path.join(RESULTS_DIR, "product_performance.csv"), index=False)
    print(prod[prod["category_rank"] == 1].to_string(index=False))

    conn.close()

    # ---- 6. Query optimization benchmark (on throwaway copies) ----
    section("Query optimization benchmark")
    bench_query = read_sql("08_query_optimization.sql")
    random.seed(7)
    customer_ids = [random.randint(1, 5000) for _ in range(300)]

    tmp_dir = tempfile.gettempdir()
    before_db = os.path.join(tmp_dir, "retailpulse_bench_before.db")
    after_db = os.path.join(tmp_dir, "retailpulse_bench_after.db")

    # Build an un-indexed copy explicitly for a clean "before" baseline
    if os.path.exists(before_db):
        os.remove(before_db)
    shutil.copy(DB_PATH, before_db)
    # Strip the secondary indexes back off the "before" copy
    bconn = sqlite3.connect(before_db)
    idx_names = [r[0] for r in bconn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    ).fetchall()]
    for name in idx_names:
        bconn.execute(f"DROP INDEX IF EXISTS {name}")
    bconn.commit()

    plan_before = bconn.execute("EXPLAIN QUERY PLAN " + bench_query, (customer_ids[0],)).fetchall()
    t0 = time.perf_counter()
    for cid in customer_ids:
        bconn.execute(bench_query, (cid,)).fetchall()
    before_total = time.perf_counter() - t0
    bconn.close()

    shutil.copy(DB_PATH, after_db)  # already indexed
    aconn = sqlite3.connect(after_db)
    plan_after = aconn.execute("EXPLAIN QUERY PLAN " + bench_query, (customer_ids[0],)).fetchall()
    t0 = time.perf_counter()
    for cid in customer_ids:
        aconn.execute(bench_query, (cid,)).fetchall()
    after_total = time.perf_counter() - t0
    aconn.close()

    print(f"{len(customer_ids)} single-customer order-history lookups")
    print("BEFORE query plan:", plan_before)
    print("AFTER  query plan:", plan_after)
    print(f"BEFORE: {before_total*1000:.1f} ms total  ({before_total/len(customer_ids)*1000:.3f} ms/lookup)")
    print(f"AFTER:  {after_total*1000:.1f} ms total  ({after_total/len(customer_ids)*1000:.3f} ms/lookup)")
    print(f"HEADLINE: {before_total/after_total:.1f}x faster  ({(1 - after_total/before_total)*100:.1f}% reduction in latency)")

    os.remove(before_db)
    os.remove(after_db)

    section("Done. Results in results/*.csv, charts in visuals/*.png")


if __name__ == "__main__":
    main()
