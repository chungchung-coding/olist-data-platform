"""
Sales-readiness and delivery-readiness analysis on the analytics layer.

Connects with SQLAlchemy, explores with pandas, writes charts (PNG) and KPI
tables (CSV) to analysis/outputs/. The notebooks in analysis/notebooks/ walk
through the same steps interactively.

    python analysis/run_analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from warehouse import get_engine, query, table  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False})


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name)
    plt.close(fig)


def sales_readiness(engine) -> dict:
    kpis: dict = {}

    # 1. Monthly sales trend ---------------------------------------------------
    monthly = table("monthly_sales", engine).sort_values("month_start")
    monthly = monthly[(monthly.month_start >= "2017-01-01") & (monthly.month_start <= "2018-08-01")]  # trim thin edges
    monthly.to_csv(OUT / "monthly_sales.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(monthly.month_start, monthly.total_revenue / 1e3, marker="o")
    ax.set_title("Monthly revenue (R$ thousands), Jan 2017 – Aug 2018")
    ax.set_ylabel("R$ k")
    ax.axvline(pd.Timestamp("2017-11-01"), color="grey", ls="--", lw=1)
    ax.annotate("Black Friday\nNov 2017", (pd.Timestamp("2017-11-01"), monthly.total_revenue.max() / 1e3), ha="right")
    save(fig, "01_monthly_revenue.png")
    peak = monthly.loc[monthly.total_revenue.idxmax()]
    kpis["peak_month"] = str(peak.month_start)[:7]
    kpis["peak_month_revenue"] = round(float(peak.total_revenue), 2)
    kpis["total_revenue_2017"] = round(float(monthly[monthly.month_start.astype(str).str.startswith("2017")].total_revenue.sum()), 2)
    kpis["total_revenue_2018_ytd"] = round(float(monthly[monthly.month_start.astype(str).str.startswith("2018")].total_revenue.sum()), 2)

    # 2. Seasonality: which month-of-year is strongest (avg over years) -------
    monthly["month"] = pd.to_datetime(monthly.month_start).dt.month
    seasonal = monthly.groupby("month").total_revenue.mean()
    kpis["strongest_month_of_year"] = int(seasonal.idxmax())

    # 3. Top-50 products per month: how stable is the list? --------------------
    top = table("top_products_monthly", engine)
    top = top[(top.month_start >= "2017-01-01") & (top.month_start <= "2018-08-01")]
    top.sort_values(["month_start", "revenue_rank"]).to_csv(OUT / "top50_products_by_month.csv", index=False)
    appearances = top.groupby("product_id").size().sort_values(ascending=False)
    kpis["products_ever_in_top50"] = int(appearances.size)
    kpis["products_in_top50_6plus_months"] = int((appearances >= 6).sum())
    cat_share = top.groupby("category").revenue.sum().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    cat_share.head(12).sort_values().plot.barh(ax=ax)
    ax.set_title("Revenue from monthly top-50 products, by category")
    ax.set_xlabel("R$")
    save(fig, "02_top50_revenue_by_category.png")
    kpis["top50_categories"] = cat_share.head(5).round(0).to_dict()

    # 4. Categories and regions ---------------------------------------------
    cr = table("category_region_sales", engine)
    cat_total = cr.groupby("category").revenue.sum().sort_values(ascending=False)
    state_total = cr.groupby("customer_state").revenue.sum().sort_values(ascending=False)
    kpis["top_categories_overall"] = cat_total.head(5).round(0).to_dict()
    kpis["top_states_revenue_share"] = (state_total.head(5) / state_total.sum()).round(3).to_dict()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    cat_total.head(10).sort_values().plot.barh(ax=axes[0], title="Top 10 categories by revenue")
    (state_total.head(10) / 1e6).sort_values().plot.barh(ax=axes[1], title="Top 10 customer states by revenue (R$ m)")
    save(fig, "03_categories_and_states.png")
    # category x top-3 state heat table
    pivot = cr[cr.customer_state.isin(state_total.head(5).index) & cr.category.isin(cat_total.head(8).index)]
    pivot = pivot.pivot_table(index="category", columns="customer_state", values="revenue", aggfunc="sum").fillna(0)
    pivot.round(0).to_csv(OUT / "category_by_state_revenue.csv")

    # 5. Customer segments --------------------------------------------------
    cm = table("customer_metrics", engine)
    seg = cm.groupby("customer_segment").agg(customers=("customer_unique_id", "size"),
                                             revenue=("lifetime_value", "sum"),
                                             avg_ltv=("lifetime_value", "mean"),
                                             avg_orders=("order_count", "mean")).sort_values("revenue", ascending=False)
    seg["revenue_share"] = seg.revenue / seg.revenue.sum()
    seg["customer_share"] = seg.customers / seg.customers.sum()
    seg.round(3).to_csv(OUT / "customer_segments.csv")
    kpis["segments"] = seg[["customers", "revenue_share", "avg_ltv"]].round(3).to_dict("index")
    kpis["repeat_customer_rate"] = round(float((cm.order_count > 1).mean()), 4)
    gold = cm[cm.customer_segment == "gold"]
    kpis["gold_customers"] = int(len(gold))
    kpis["gold_revenue_share"] = round(float(gold.lifetime_value.sum() / cm.lifetime_value.sum()), 4)
    kpis["gold_top_states"] = gold.state.value_counts(normalize=True).head(5).round(3).to_dict()
    gold_cats = query(f"""
        select p.category, sum(f.price) as revenue
        from olist_analytics.fact_order_items f
        join olist_analytics.dim_customers c on f.customer_id = c.customer_id
        join olist_analytics.customer_metrics m on c.customer_unique_id = m.customer_unique_id
        join olist_analytics.dim_products p on f.product_id = p.product_id
        where m.customer_segment = 'gold'
        group by 1 order by 2 desc limit 10
    """, engine)
    gold_cats.to_csv(OUT / "gold_customer_categories.csv", index=False)
    kpis["gold_top_categories"] = gold_cats.head(5).set_index("category").revenue.round(0).to_dict()
    fig, ax = plt.subplots(figsize=(8, 4))
    seg.revenue_share.plot.bar(ax=ax, title="Revenue share by customer segment")
    ax.set_ylabel("share of revenue")
    save(fig, "04_segment_revenue_share.png")

    # 6. Sellers to prepare -------------------------------------------------
    sp = table("seller_performance", engine).dropna(subset=["revenue"]).sort_values("revenue", ascending=False)
    sp["cum_share"] = sp.revenue.cumsum() / sp.revenue.sum()
    kpis["sellers_for_80pct_revenue"] = int((sp.cum_share <= 0.8).sum() + 1)
    kpis["seller_count"] = int(len(sp))
    sp.head(50).to_csv(OUT / "top50_sellers.csv", index=False)
    return kpis


def delivery_readiness(engine) -> dict:
    kpis: dict = {}
    dp = table("delivery_performance_by_state", engine).sort_values("avg_delivery_days", ascending=False)
    dp.round(3).to_csv(OUT / "delivery_by_state.csv", index=False)
    kpis["national_avg_delivery_days"] = round(float(query(
        "select avg(actual_delivery_days) v from olist_analytics.fact_orders where order_status='delivered'", engine).v[0]), 2)
    kpis["national_late_rate"] = round(float(query(
        "select avg(case when is_late then 1.0 else 0.0 end) v from olist_analytics.fact_orders where order_status='delivered' and delivered_to_customer_at is not null", engine).v[0]), 4)
    kpis["slowest_states"] = dp.head(5).set_index("customer_state").avg_delivery_days.round(1).to_dict()
    kpis["highest_late_rate_states"] = dp.sort_values("late_rate", ascending=False).head(5).set_index("customer_state").late_rate.round(3).to_dict()
    kpis["fastest_states"] = dp.tail(3).set_index("customer_state").avg_delivery_days.round(1).to_dict()

    fig, ax = plt.subplots(figsize=(10, 5))
    d = dp.set_index("customer_state")[["avg_seller_handling_days", "avg_carrier_transit_days"]]
    d.plot.bar(stacked=True, ax=ax, title="Average delivery days by customer state: seller handling vs carrier transit")
    ax.set_ylabel("days")
    save(fig, "05_delivery_days_by_state.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(dp.avg_delivery_days, dp.late_rate * 100)
    for _, r in dp.iterrows():
        ax.annotate(r.customer_state, (r.avg_delivery_days, r.late_rate * 100), fontsize=7)
    ax.set_xlabel("avg delivery days")
    ax.set_ylabel("late deliveries (%)")
    ax.set_title("States: slower is also later")
    save(fig, "06_delivery_days_vs_late_rate.png")

    # Where is the delay generated? national split
    legs = query("""
        select avg(approval_days) approval, avg(seller_handling_days) seller, avg(carrier_transit_days) carrier
        from olist_analytics.fact_orders where order_status='delivered'
    """, engine).iloc[0].round(2).to_dict()
    kpis["national_leg_days"] = legs

    # Late deliveries hurt reviews
    rev = query("""
        select is_late, avg(review_score) avg_review, count(*) n
        from olist_analytics.fact_orders
        where order_status='delivered' and review_score is not null and is_late is not null
        group by is_late
    """, engine)
    kpis["avg_review_on_time_vs_late"] = rev.set_index("is_late").avg_review.round(2).to_dict()

    # Late rate by month (capacity effect)
    ml = table("monthly_sales", engine).sort_values("month_start")
    ml = ml[(ml.month_start >= "2017-01-01") & (ml.month_start <= "2018-08-01")]
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.bar(ml.month_start, ml.orders, width=20, alpha=0.4, label="orders")
    ax2 = ax1.twinx()
    ax2.plot(ml.month_start, ml.late_delivery_rate * 100, color="crimson", marker="o", label="late %")
    ax1.set_title("Order volume vs late-delivery rate by month")
    ax2.set_ylabel("late deliveries (%)")
    save(fig, "07_volume_vs_late_rate.png")
    kpis["worst_late_month"] = str(ml.loc[ml.late_delivery_rate.idxmax()].month_start)[:7]
    kpis["worst_late_month_rate"] = round(float(ml.late_delivery_rate.max()), 4)

    # Estimated-vs-actual gap: are promises too generous?
    gap = query("""
        select avg(estimated_delivery_days) est, avg(actual_delivery_days) act
        from olist_analytics.fact_orders where order_status='delivered'
    """, engine).iloc[0].round(1).to_dict()
    kpis["avg_estimated_vs_actual_days"] = gap
    return kpis


if __name__ == "__main__":
    engine = get_engine()
    kpis = {"sales_readiness": sales_readiness(engine), "delivery_readiness": delivery_readiness(engine)}
    (OUT / "kpis.json").write_text(json.dumps(kpis, indent=2, default=str))
    print(json.dumps(kpis, indent=2, default=str))
