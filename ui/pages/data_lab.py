"""Data Lab: upload, profile, clean, and query a dataset with pandas and SQL."""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
import streamlit as st

from core import db
from ui.styles import hero, stat_card


def _profile(df: pd.DataFrame) -> dict[str, Any]:
    rows, cols = df.shape
    missing = df.isna().sum()
    missing_pct = (missing / rows * 100) if rows else missing
    duplicates = int(df.duplicated().sum())
    numeric = df.select_dtypes(include="number").columns.tolist()
    categorical = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime"]).columns.tolist()

    issues: list[str] = []
    for col in df.columns:
        m = int(missing[col])
        if m > 0:
            issues.append(f"**{col}** has {m} missing values ({missing_pct[col]:.1f}%).")
    if duplicates > 0:
        issues.append(f"Found **{duplicates} duplicate rows** ({duplicates / rows * 100:.1f}% of data).")
    for col in numeric:
        s = df[col].dropna()
        if len(s) < 4:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = int(((s < lo) | (s > hi)).sum())
        if outliers > 0:
            issues.append(f"**{col}** has {outliers} values outside the IQR range ({lo:.2f}–{hi:.2f}).")
    for col in df.columns:
        if df[col].nunique(dropna=True) <= 1:
            issues.append(f"**{col}** is constant — it carries no information.")
    if not issues:
        issues.append("No obvious data-quality issues detected. Still validate against the source.")

    return {
        "rows": rows,
        "cols": cols,
        "missing": missing,
        "missing_pct": missing_pct,
        "duplicates": duplicates,
        "numeric": numeric,
        "categorical": categorical,
        "datetime_cols": datetime_cols,
        "issues": issues,
    }


def _clean_suggestions(profile: dict[str, Any], df: pd.DataFrame) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    if profile["duplicates"] > 0:
        suggestions.append(
            {
                "title": "Remove duplicate rows",
                "reason": f"{profile['duplicates']} duplicate rows inflate counts and distort averages.",
                "code": "df = df.drop_duplicates().reset_index(drop=True)",
            }
        )
    for col in df.columns:
        m = int(profile["missing"][col])
        if m == 0:
            continue
        if col in profile["numeric"]:
            suggestions.append(
                {
                    "title": f"Fill missing values in {col}",
                    "reason": f"{m} missing values. Numeric columns are usually filled with the median.",
                    "code": (
                        f"df['{col}'] = df['{col}'].fillna(df['{col}'].median())"
                    ),
                }
            )
        else:
            suggestions.append(
                {
                    "title": f"Fill missing values in {col}",
                    "reason": f"{m} missing values. Categorical columns are usually filled with the mode or 'Unknown'.",
                    "code": (
                        f"df['{col}'] = df['{col}'].fillna(df['{col}'].mode().iloc[0] if not df['{col}'].mode().empty else 'Unknown')"
                    ),
                }
            )
    for col in profile["categorical"]:
        if any(str(v).strip() != v for v in df[col].dropna().astype(str).unique()[:5]):
            suggestions.append(
                {
                    "title": f"Strip whitespace in {col}",
                    "reason": "Leading or trailing spaces create phantom categories.",
                    "code": f"df['{col}'] = df['{col}'].astype(str).str.strip()",
                }
            )
    for col in df.columns:
        if col.lower() in {"date", "order_date", "created_at", "updated_at"} and df[col].dtype == object:
            suggestions.append(
                {
                    "title": f"Parse {col} as a date",
                    "reason": "Date columns stored as text cannot be used for time analysis.",
                    "code": f"df['{col}'] = pd.to_datetime(df['{col}'], errors='coerce')",
                }
            )
    if not suggestions:
        suggestions.append(
            {
                "title": "No automatic suggestions",
                "reason": "The profile looks clean. Review the data dictionary before analysis.",
                "code": "# Nothing to do",
            }
        )
    return suggestions


def _render_profile(df: pd.DataFrame, profile: dict[str, Any]) -> None:
    st.markdown("#### Profile")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(stat_card("Rows", f"{profile['rows']:,}"), unsafe_allow_html=True)
    c2.markdown(stat_card("Columns", str(profile["cols"])), unsafe_allow_html=True)
    c3.markdown(stat_card("Duplicates", str(profile["duplicates"]), "rows" if profile["duplicates"] else "none"), unsafe_allow_html=True)
    c4.markdown(stat_card("Missing cells", f"{int(profile['missing'].sum()):,}", "across all columns"), unsafe_allow_html=True)

    st.markdown("##### Column details")
    rows = []
    for col in df.columns:
        rows.append(
            {
                "Column": col,
                "Type": str(df[col].dtype),
                "Non-null": int(df[col].notna().sum()),
                "Missing": int(profile["missing"][col]),
                "Missing %": round(float(profile["missing_pct"][col]), 1),
                "Unique": int(df[col].nunique(dropna=True)),
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    if profile["numeric"]:
        st.markdown("##### Numeric summary")
        st.dataframe(df[profile["numeric"]].describe().T.round(3), width="stretch")
    if profile["categorical"]:
        st.markdown("##### Categorical columns")
        for col in profile["categorical"][:6]:
            top = df[col].value_counts(dropna=False).head(8)
            st.markdown(f"**{col}** — {df[col].nunique(dropna=True)} unique")
            st.dataframe(
                pd.DataFrame({"value": top.index.astype(str), "count": top.values}),
                width="stretch",
                hide_index=True,
            )

    if len(profile["numeric"]) >= 2:
        st.markdown("##### Correlations (numeric)")
        corr = df[profile["numeric"]].corr().round(2)
        st.dataframe(corr, width="stretch")

    st.markdown("##### Sample rows")
    st.dataframe(df.head(8), width="stretch")


def render() -> None:
    st.markdown(
        hero(
            "Data Lab",
            "Upload, profile, clean, and query a dataset",
            "Everything stays in your browser session. Nothing is uploaded anywhere. "
            "Export the cleaned file when you're done.",
        ),
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload a CSV or Excel file",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        help="Max 200 MB. The file is read into memory only.",
    )

    if uploaded is None:
        st.info(
            "Drop a CSV or Excel file above to start profiling. Try the Olist, IBM HR, or "
            "Bank Marketing datasets from your sprint for practice."
        )
        return

    try:
        if uploaded.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as exc:
        st.error(f"Could not read the file: {exc}")
        return

    if df.empty:
        st.error("The file loaded but contains no rows.")
        return

    st.session_state["data_lab_df"] = df
    st.session_state["data_lab_name"] = uploaded.name

    profile = _profile(df)

    st.success(f"Loaded **{uploaded.name}** — {profile['rows']:,} rows × {profile['cols']} columns.")

    tabs = st.tabs(["Profile", "Issues & cleaning", "Query (SQL)", "Export"])

    with tabs[0]:
        _render_profile(df, profile)

    with tabs[1]:
        st.markdown("#### Data-quality issues")
        for issue in profile["issues"]:
            st.markdown(f"- {issue}")

        st.markdown("#### Suggested cleaning steps")
        st.caption("Each step is plain pandas. Copy, adapt, and run them in order.")
        for suggestion in _clean_suggestions(profile, df):
            with st.container(border=True):
                st.markdown(f"**{suggestion['title']}**")
                st.caption(suggestion["reason"])
                st.code(suggestion["code"], language="python")

        st.markdown("#### Apply cleaning steps")
        st.caption("Select the steps to run. They are applied in order to a working copy.")
        codes = [s["code"] for s in _clean_suggestions(profile, df)]
        chosen = st.multiselect(
            "Steps to apply",
            options=list(range(len(codes))),
            format_func=lambda i: _clean_suggestions(profile, df)[i]["title"],
            default=[],
            key="data_lab_steps",
        )
        if st.button("Apply selected steps", type="primary"):
            working = df.copy()
            applied = 0
            for i in chosen:
                try:
                    exec(codes[i], {"df": working, "pd": pd})
                    applied += 1
                except Exception as exc:
                    st.error(f"Step failed: {exc}")
            if applied:
                st.session_state["data_lab_df"] = working
                st.session_state["data_lab_cleaned"] = True
                st.success(f"Applied {applied} step(s). {working.shape[0]:,} rows × {working.shape[1]} columns remain.")
                st.dataframe(working.head(10), width="stretch")

    with tabs[2]:
        st.markdown("#### Query with SQL (DuckDB)")
        st.caption("The table is named `df`. Use standard SQL. Read-only.")
        default_query = "SELECT * FROM df LIMIT 10"
        query = st.text_area("SQL", value=default_query, height=120, key="data_lab_query")
        if st.button("Run query", type="primary"):
            try:
                import duckdb

                result = duckdb.query(query).df()
                st.success(f"{len(result):,} rows returned.")
                st.dataframe(result, width="stretch")
                if len(result) > 0:
                    csv = result.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download result as CSV",
                        data=csv,
                        file_name="query_result.csv",
                        mime="text/csv",
                    )
            except Exception as exc:
                st.error(f"Query failed: {exc}")

    with tabs[3]:
        st.markdown("#### Export")
        working = st.session_state.get("data_lab_df", df)
        st.caption(f"Exporting {working.shape[0]:,} rows × {working.shape[1]} columns.")
        csv = working.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download cleaned CSV",
            data=csv,
            file_name=f"cleaned_{uploaded.name}",
            mime="text/csv",
            type="primary",
        )
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                working.to_excel(writer, index=False, sheet_name="cleaned")
            st.download_button(
                "Download cleaned Excel",
                data=buffer.getvalue(),
                file_name=f"cleaned_{uploaded.name.rsplit('.', 1)[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            st.caption(f"Excel export unavailable: {exc}")

        st.markdown("#### Data dictionary")
        dictionary = pd.DataFrame(
            {
                "column": working.columns,
                "dtype": [str(working[c].dtype) for c in working.columns],
                "non_null": [int(working[c].notna().sum()) for c in working.columns],
                "unique": [int(working[c].nunique(dropna=True)) for c in working.columns],
                "sample": [str(working[c].dropna().iloc[0]) if working[c].notna().any() else "" for c in working.columns],
            }
        )
        st.dataframe(dictionary, width="stretch", hide_index=True)
        st.download_button(
            "Download data dictionary (CSV)",
            data=dictionary.to_csv(index=False).encode("utf-8"),
            file_name="data_dictionary.csv",
            mime="text/csv",
        )
