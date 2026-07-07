-- SKU Rationalization Framework — Diagnostic Queries
-- Run against Cinderhaven Postgres (flyctl proxy 5432:5432 -a cinderhaven-db)
--
-- These queries support the scoring output in data/cinderhaven_scored.json.
-- Each section answers a specific question a client or analyst would ask.
-- ----------------------------------------------------------------------------


-- ============================================================================
-- 1. PORTFOLIO OVERVIEW
--    Quick counts by action bucket and product line.
-- ============================================================================

WITH scored AS (
    SELECT
        pm.sku,
        pm.product_line,
        -- Velocity
        v.uspw,
        -- Loaded margin
        m.loaded_margin_pct,
        -- Shelf cost
        s.annual_shelf_space_cost,
        -- Complexity proxy
        (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) AS complexity_ratio,
        -- Cannibalization (proxy; NULL = fewer than 3 solo stores)
        GREATEST(0, COALESCE(-cp.velocity_delta_pct, 0)) AS cannibalization_risk
    FROM raw.product_master pm
    JOIN (
        SELECT sku, AVG(units_sold) AS uspw
        FROM raw.scan_data
        GROUP BY sku
    ) v ON pm.sku = v.sku
    JOIN public_intermediate.int_loaded_contribution_by_sku m ON pm.sku = m.sku
    JOIN public_intermediate.int_shelf_space_cost_by_sku s ON pm.sku = s.sku
    JOIN raw.sku_costs sc ON pm.sku = sc.sku
    LEFT JOIN public_intermediate.int_cannibalization_pairs cp
        ON pm.sku = cp.sku AND cp.solo_stores >= 3
)
SELECT
    product_line,
    COUNT(*) AS total_skus,
    ROUND(AVG(uspw)::numeric, 2) AS avg_uspw,
    ROUND(AVG(loaded_margin_pct)::numeric, 2) AS avg_loaded_margin_pct,
    ROUND(AVG(annual_shelf_space_cost)::numeric, 0) AS avg_shelf_cost,
    ROUND(AVG(complexity_ratio)::numeric, 4) AS avg_complexity_ratio
FROM scored
GROUP BY product_line
ORDER BY product_line;


-- ============================================================================
-- 2. KILL CANDIDATES — FULL DETAIL
--    SKUs with 2+ dimensions scoring <= 2 (red flags). Shows which dimensions
--    are failing so the fix-or-kill decision can be made on specifics.
-- ============================================================================

WITH dim_scores AS (
    SELECT
        pm.sku,
        pm.product_line,
        -- Velocity score
        CASE
            WHEN v.uspw >= 13.5066 THEN 5
            WHEN v.uspw >= 8.3338 THEN 4
            WHEN v.uspw >= 4.3606 THEN 3
            WHEN v.uspw >= 2.0201 THEN 2
            ELSE 1
        END AS vel_score,
        -- Margin score (higher = less negative = better)
        CASE
            WHEN m.loaded_margin_pct >= -4.3700 THEN 5
            WHEN m.loaded_margin_pct >= -4.7576 THEN 4
            WHEN m.loaded_margin_pct >= -6.9733 THEN 3
            WHEN m.loaded_margin_pct >= -7.7654 THEN 2
            ELSE 1
        END AS margin_score,
        -- Shelf cost score (lower = better)
        CASE
            WHEN s.annual_shelf_space_cost <= 40136.32 THEN 5
            WHEN s.annual_shelf_space_cost <= 74765.20 THEN 4
            WHEN s.annual_shelf_space_cost <= 119627.83 THEN 3
            WHEN s.annual_shelf_space_cost <= 137925.29 THEN 2
            ELSE 1
        END AS shelf_score,
        -- Complexity score (lower ratio = better)
        CASE
            WHEN (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) <= 0.2475 THEN 5
            WHEN (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) <= 0.2701 THEN 4
            WHEN (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) <= 0.3012 THEN 3
            WHEN (sc.landed_cost_per_unit / NULLIF(pm.msrp, 0)) <= 0.3167 THEN 2
            ELSE 1
        END AS complexity_score,
        -- Cannibalization score (0 = no signal → 5)
        CASE
            WHEN COALESCE(GREATEST(0, -cp.velocity_delta_pct), 0) = 0 THEN 5
            WHEN GREATEST(0, -cp.velocity_delta_pct) <= 0.0000             THEN 4
            WHEN GREATEST(0, -cp.velocity_delta_pct) <= 0.0745             THEN 3
            WHEN GREATEST(0, -cp.velocity_delta_pct) <= 0.2054             THEN 2
            ELSE 1
        END AS cannibal_score,
        -- Raw values
        ROUND(v.uspw::numeric, 2) AS uspw,
        ROUND(m.loaded_margin_pct::numeric, 2) AS loaded_margin_pct,
        ROUND(s.annual_shelf_space_cost::numeric, 0) AS annual_shelf_cost,
        ROUND((sc.landed_cost_per_unit / NULLIF(pm.msrp, 0))::numeric, 4) AS complexity_ratio,
        ROUND(GREATEST(0, COALESCE(-cp.velocity_delta_pct, 0))::numeric, 4) AS cannibal_risk
    FROM raw.product_master pm
    JOIN (SELECT sku, AVG(units_sold) AS uspw FROM raw.scan_data GROUP BY sku) v ON pm.sku = v.sku
    JOIN public_intermediate.int_loaded_contribution_by_sku m ON pm.sku = m.sku
    JOIN public_intermediate.int_shelf_space_cost_by_sku s ON pm.sku = s.sku
    JOIN raw.sku_costs sc ON pm.sku = sc.sku
    LEFT JOIN public_intermediate.int_cannibalization_pairs cp
        ON pm.sku = cp.sku AND cp.solo_stores >= 3
),
with_counts AS (
    SELECT *,
        (CASE WHEN vel_score       <= 2 THEN 1 ELSE 0 END +
         CASE WHEN margin_score    <= 2 THEN 1 ELSE 0 END +
         CASE WHEN shelf_score     <= 2 THEN 1 ELSE 0 END +
         CASE WHEN complexity_score<= 2 THEN 1 ELSE 0 END +
         CASE WHEN cannibal_score  <= 2 THEN 1 ELSE 0 END) AS red_flags
    FROM dim_scores
)
SELECT
    sku,
    product_line,
    red_flags,
    vel_score,
    margin_score,
    shelf_score,
    complexity_score,
    cannibal_score,
    ROUND((vel_score + margin_score + shelf_score + complexity_score + cannibal_score) / 5.0, 2) AS avg_score,
    uspw,
    loaded_margin_pct,
    annual_shelf_cost,
    complexity_ratio,
    cannibal_risk
FROM with_counts
WHERE red_flags >= 2
ORDER BY red_flags DESC, avg_score ASC;


-- ============================================================================
-- 3. REVENUE IMPACT OF KILL CANDIDATES
--    Estimated annual gross revenue and shelf cost for kill-bucket SKUs.
--    Use to quantify the "cost of the long tail."
-- ============================================================================

WITH kill_skus AS (
    -- Paste in the SKU list from query #2 above, or join to a temp table
    -- This version uses the same 2-red-flag threshold inline
    SELECT sku
    FROM (
        SELECT
            pm.sku,
            -- Red flag = score <= 2. Threshold is score >= 3 boundary:
            -- velocity/margin: P25; shelf/complexity/cannibalization: P75.
            (CASE WHEN v.uspw >= 4.3606 THEN 0 ELSE 1 END +
             CASE WHEN m.loaded_margin_pct >= -6.9733 THEN 0 ELSE 1 END +
             CASE WHEN s.annual_shelf_space_cost <= 119627.83 THEN 0 ELSE 1 END +
             CASE WHEN (sc.landed_cost_per_unit/NULLIF(pm.msrp,0)) <= 0.3012 THEN 0 ELSE 1 END +
             CASE WHEN COALESCE(GREATEST(0,-cp.velocity_delta_pct),0) <= 0.0745 THEN 0 ELSE 1 END
            ) AS red_flags
        FROM raw.product_master pm
        JOIN (SELECT sku, AVG(units_sold) AS uspw FROM raw.scan_data GROUP BY sku) v ON pm.sku = v.sku
        JOIN public_intermediate.int_loaded_contribution_by_sku m ON pm.sku = m.sku
        JOIN public_intermediate.int_shelf_space_cost_by_sku s ON pm.sku = s.sku
        JOIN raw.sku_costs sc ON pm.sku = sc.sku
        LEFT JOIN public_intermediate.int_cannibalization_pairs cp
            ON pm.sku = cp.sku AND cp.solo_stores >= 3
    ) t
    WHERE red_flags >= 2
)
SELECT
    COUNT(*)                                             AS kill_sku_count,
    ROUND(SUM(m.gross_revenue)::numeric, 0)             AS total_gross_revenue,
    ROUND(SUM(m.loaded_contribution)::numeric, 0)       AS total_loaded_contribution,
    ROUND(SUM(s.annual_shelf_space_cost)::numeric, 0)   AS total_shelf_cost,
    ROUND(AVG(m.loaded_margin_pct)::numeric, 2)         AS avg_loaded_margin_pct
FROM kill_skus k
JOIN public_intermediate.int_loaded_contribution_by_sku m ON k.sku = m.sku
JOIN public_intermediate.int_shelf_space_cost_by_sku s ON k.sku = s.sku;


-- ============================================================================
-- 4. CANNIBALIZATION DETAIL
--    For any SKU with a cannibalization signal, show which product line
--    siblings are co-distributed and how velocity differs.
-- ============================================================================

SELECT
    cp.sku,
    cp.product_line,
    cp.total_distribution_stores,
    cp.solo_stores,
    cp.shared_stores,
    ROUND(cp.solo_uspw::numeric, 3)   AS solo_uspw,
    ROUND(cp.shared_uspw::numeric, 3) AS shared_uspw,
    ROUND(cp.velocity_delta_pct::numeric, 4) AS velocity_delta_pct,
    ROUND(GREATEST(0, -cp.velocity_delta_pct)::numeric, 4) AS cannibalization_risk,
    cp.methodology_note
FROM public_intermediate.int_cannibalization_pairs cp
WHERE cp.solo_stores >= 3
  AND cp.velocity_delta_pct < 0   -- only SKUs with measurable cannibalization signal
ORDER BY cp.velocity_delta_pct ASC;


-- ============================================================================
-- 5. SHELF COST BREAKDOWN
--    Shows what's driving annual shelf cost per SKU: promo spend vs.
--    store-count maintenance proxy.
-- ============================================================================

SELECT
    s.sku,
    s.product_line,
    s.active_store_count,
    ROUND(s.annual_promo_cost::numeric, 0)          AS annual_promo_cost,
    ROUND(s.maintenance_cost_proxy::numeric, 0)     AS maintenance_cost_proxy,
    ROUND(s.annual_shelf_space_cost::numeric, 0)    AS total_shelf_cost,
    ROUND((s.annual_promo_cost / NULLIF(s.annual_shelf_space_cost, 0) * 100)::numeric, 1)
                                                    AS promo_pct_of_total
FROM public_intermediate.int_shelf_space_cost_by_sku s
ORDER BY s.annual_shelf_space_cost DESC;


-- ============================================================================
-- 6. LOADED CONTRIBUTION WATERFALL
--    Revenue → COGS → trade spend → chargebacks → deductions → net.
--    One row per SKU. Use to identify where margin is being destroyed.
-- ============================================================================

SELECT
    m.sku,
    m.product_line,
    ROUND(m.gross_revenue::numeric, 0)                      AS gross_revenue,
    ROUND(m.total_cogs::numeric, 0)                         AS cogs,
    ROUND(m.trade_spend::numeric, 0)                        AS trade_spend,
    ROUND(m.total_chargebacks::numeric, 0)                  AS chargebacks,
    ROUND(m.allocated_deductions::numeric, 0)               AS allocated_deductions,
    ROUND(m.loaded_contribution::numeric, 0)                AS loaded_contribution,
    ROUND(m.loaded_contribution_per_unit::numeric, 4)       AS contribution_per_unit,
    ROUND(m.loaded_margin_pct::numeric, 2)                  AS loaded_margin_pct
FROM public_intermediate.int_loaded_contribution_by_sku m
ORDER BY m.loaded_margin_pct DESC;
