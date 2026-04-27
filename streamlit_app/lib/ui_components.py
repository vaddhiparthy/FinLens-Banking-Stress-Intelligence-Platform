import streamlit as st
import streamlit.components.v1 as components


def inject_styles(css: str) -> None:
    st.markdown(css, unsafe_allow_html=True)


def metric_card(label: str, value: str, subtext: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title: str, copy: str | None = None) -> None:
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)
    if copy:
        st.markdown(f'<div class="subsection-copy">{copy}</div>', unsafe_allow_html=True)


def empty_state(message: str) -> None:
    st.markdown(f'<div class="empty-card">{message}</div>', unsafe_allow_html=True)


def insight_card(label: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-label">{label}</div>
            <div class="insight-title">{title}</div>
            <div class="insight-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stack_badges(items: list[str]) -> None:
    chips = "".join(f'<div class="stack-chip">{item}</div>' for item in items)
    st.markdown(f'<div class="stack-row">{chips}</div>', unsafe_allow_html=True)


def intro_overlay(title: str, copy: str, stack: list[str], timeout_ms: int = 4500) -> None:
    chips = "".join(
        (
            '<span style="display:inline-block;border:1px solid #e4d7c6;'
            "background:rgba(255,250,243,0.92);border-radius:999px;padding:6px 10px;"
            'font:700 12px Manrope,sans-serif;color:#1f2933;margin:4px 6px 0 0;">'
            f"{item}</span>"
        )
        for item in stack
    )
    close_action = "document.getElementById('finlens-overlay').style.display='none'"
    eyebrow_style = (
        "letter-spacing:.16em;text-transform:uppercase;font-size:11px;"
        "font-weight:800;color:#7f6b58;"
    )
    components.html(
        f"""
        <div id="finlens-overlay" style="
            position:fixed;inset:0;display:flex;align-items:center;justify-content:center;
            background:rgba(33,29,24,0.18);backdrop-filter:blur(6px);z-index:9999;
            font-family:Manrope,sans-serif;">
          <div style="
              width:min(680px,92vw);background:linear-gradient(180deg,#fffdf9,#f7eee2);
              border:1px solid rgba(191,109,71,0.28);outline:1px solid rgba(255,255,255,0.74);
              border-radius:24px;padding:24px 26px 22px;
              box-shadow:0 22px 42px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.7);
              color:#1f2933;position:relative;">
            <button onclick="{close_action}" style="
                position:absolute;top:14px;right:14px;border:none;background:transparent;
                font-size:22px;cursor:pointer;color:#6a6b74;">×</button>
            <div style="{eyebrow_style}">
              FinLens
            </div>
            <div style="font:700 38px Fraunces,Georgia,serif;line-height:1.02;margin:10px 0 12px;">
              {title}
            </div>
            <div style="font-size:15px;line-height:1.7;color:#4b5563;max-width:58ch;">
              {copy}
            </div>
            <div style="margin-top:14px;">{chips}</div>
          </div>
        </div>
        <script>
          setTimeout(function() {{
            const overlay = document.getElementById('finlens-overlay');
            if (overlay) overlay.style.display = 'none';
          }}, {timeout_ms});
        </script>
        """,
        height=0,
    )


def choice_card(label: str, title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="welcome-card">
            <div class="welcome-kicker">{label}</div>
            <div class="welcome-title">{title}</div>
            <div class="welcome-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tech_bulletin(title: str, copy: str) -> None:
    st.markdown(
        f"""
        <div class="tech-bulletin">
            <div class="tech-bulletin-title">{title}</div>
            <div class="tech-bulletin-copy">{copy}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pipeline_stage_flow(stages: list[dict[str, object]]) -> None:
    html_parts: list[str] = ['<div class="flow-grid">']
    for index, stage in enumerate(stages):
        html_parts.append(
            f"""
            <div class="flow-card">
                <div class="flow-step">Stage {index + 1}</div>
                <div class="flow-name">{stage["name"]}</div>
                <div class="flow-copy">{stage["copy"]}</div>
                <div class="flow-metric">{stage["metric_1"]}</div>
                <div class="flow-metric">{stage["metric_2"]}</div>
                <div class="flow-metric">{stage["metric_3"]}</div>
            </div>
            """
        )
        if index < len(stages) - 1:
            html_parts.append('<div class="flow-arrow">→</div>')
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
