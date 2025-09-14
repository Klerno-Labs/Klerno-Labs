        flags = score_risk(tx)
        category = tag_category(tx)
        tagged = TaggedTransaction(**_dump(tx), score=risk, flags=flags, category=category)
        d = tagged.model_dump()
        d["risk_score"] = d.get("score")
        d["risk_flags"] = d.get("flags")
        d["risk_bucket"] = _risk_bucket(d.get("risk_score", 0))
        store.save_tagged(d)
        saved += 1
        tagged_items.append(d)
        emails.append(notify_if_alert(tagged))
        await live.publish(d)
    return {
        "account": account,
        "requested": limit,
        "fetched": len(txs),
        "saved": saved,
        "threshold": float(os.getenv("RISK_THRESHOLD", "0.75")),
        "items": tagged_items,
        "emails": emails,
    }


# ---------------- CSV export (DB) ----------------
@app.get("/export/csv")
def export_csv_from_db(wallet: str | None = None, limit: int = 1000, _auth: bool = Security(enforce_api_key)):
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    if not rows:
        return {"rows": 0, "csv": ""}
    df = pd.DataFrame(rows)
    return {"rows": len(rows), "csv": df.to_csv(index=False)}


# ---- helper: allow ?key=... or x-api-key header for download ----
def _check_key_param_or_header(key: Optional[str] = None, x_api_key: Optional[str] = Header(default=None)):
    exp = expected_api_key() or ""
    incoming = (key or "").strip() or (x_api_key or "").strip()
    if exp and incoming != exp:
        raise HTTPException(status_code=401, detail="unauthorized")

@app.get("/export/csv/download")
def export_csv_download(wallet: str | None = None, limit: int = 1000, key: Optional[str] = None, x_api_key: Optional[str] = Header(None)):
    _check_key_param_or_header(key=key, x_api_key=x_api_key)
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(iter([buf.read()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=klerno-export.csv"})


# ---------------- CSV export (UI, session-protected) ----------------
@app.get("/uiapi/export/csv/download", include_in_schema=False)
def ui_export_csv_download(
    wallet: str | None = None,
    limit: int = 1000,
    _user = Depends(require_paid_or_admin),
):
    rows = store.list_by_wallet(wallet, limit=limit) if wallet else store.list_all(limit=limit)
    df = pd.DataFrame(rows)
    buf = StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=klerno-export.csv"},
    )


# ---------------- Metrics (JSON) ----------------

# tiny in-proc TTL cache to avoid heavy recompute
_METRICS_CACHE: Dict[Tuple[Optional[float], Optional[int]], Tuple[float, Dict[str, Any]]] = {}
_METRICS_TTL_SEC = 5.0

def _metrics_cached(threshold: Optional[float], days: Optional[int]) -> Optional[Dict[str, Any]]:
    key = (threshold, days)
    item = _METRICS_CACHE.get(key)
    now = datetime.utcnow().timestamp()
    if item and (now - item[0]) <= _METRICS_TTL_SEC:
        return item[1]
    return None

def _metrics_put(threshold: Optional[float], days: Optional[int], data: Dict[str, Any]):
    key = (threshold, days)
    _METRICS_CACHE[key] = (datetime.utcnow().timestamp(), data)

@app.get("/metrics")
def metrics(threshold: float | None = None, days: int | None = None, _auth: bool = Security(enforce_api_key)):
    cached = _metrics_cached(threshold, days)
    if cached is not None:
        return cached

    rows = store.list_all(limit=10000)
    if not rows:
        data = {"total": 0, "alerts": 0, "avg_risk": 0, "categories": {}, "series_by_day": [], "series_by_day_lmh": []}
        _metrics_put(threshold, days, data)
        return data

    env_threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    thr = env_threshold if threshold is None else float(threshold)
    thr = max(0.0, min(1.0, thr))

    cutoff = None
    if days is not None:
        try:
            d = max(1, min(int(days), 365))
            cutoff = datetime.utcnow() - timedelta(days=d)
        except Exception:
            cutoff = None

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["risk_score"] = df.apply(lambda rr: _row_score(rr), axis=1)
    if cutoff is not None:
        df = df[df["timestamp"] >= cutoff]
    if df.empty:
        data = {"total": 0, "alerts": 0, "avg_risk": 0, "categories": {}, "series_by_day": [], "series_by_day_lmh": []}
        _metrics_put(threshold, days, data)
        return data

    total = int(len(df))
    alerts = int((df["risk_score"] >= thr).sum())
    avg_risk = float(df["risk_score"].mean())

    # categories
    categories: Dict[str, int] = {}
    cats_series = (df["category"].fillna("unknown") if "category" in df.columns else pd.Series(["unknown"] * total))
    for cat, cnt in cats_series.value_counts().items():
        categories[str(cat)] = int(cnt)

    df["day"] = df["timestamp"].dt.date
    grp = df.groupby("day").agg(avg_risk=("risk_score", "mean")).reset_index()
    series = [{"date": str(d), "avg_risk": round(float(v), 3)} for d, v in zip(grp["day"], grp["avg_risk"])]

    # Low/Med/High daily counts for stacked chart
    df["bucket"] = df["risk_score"].apply(_risk_bucket)
    crosstab = df.pivot_table(index="day", columns="bucket", values="risk_score", aggfunc="count").fillna(0)
    crosstab = crosstab.reindex(sorted(crosstab.index))
    series_lmh = []
    for d, row in crosstab.iterrows():
        series_lmh.append({
            "date": str(d),
            "low": int(row.get("low", 0)),
            "medium": int(row.get("medium", 0)),
            "high": int(row.get("high", 0)),
        })

    data = {"total": total, "alerts": alerts, "avg_risk": round(avg_risk, 3), "categories": categories, "series_by_day": series, "series_by_day_lmh": series_lmh}
    _metrics_put(threshold, days, data)
    return data


# ---------------- UI API (session-protected; no x-api-key) ----------------
@app.get("/metrics-ui", include_in_schema=False)
def metrics_ui(
    threshold: float | None = None,
    days: int | None = None,
    _user=Depends(require_paid_or_admin),
):
    resp = FastJSON(content=metrics(threshold=threshold, days=days, _auth=True))
    # short client-side caching to cut churn
    resp.headers["Cache-Control"] = "private, max-age=10"
    return resp

@app.get("/alerts-ui/data", include_in_schema=False)
def alerts_ui_data(limit: int = 100, _user=Depends(require_paid_or_admin)):
    threshold = float(os.getenv("RISK_THRESHOLD", "0.75"))
    rows = store.list_alerts(threshold, limit=limit)
    return {"threshold": threshold, "count": len(rows), "items": rows}