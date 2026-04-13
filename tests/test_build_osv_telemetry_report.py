from __future__ import annotations

import importlib.util
from pathlib import Path


def test_build_osv_telemetry_report_writes_html() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report_dir = repo_root / "device_reports" / "osmo-360" / "osv-telemetry-2026-04-12"
    tool_path = repo_root / "tools" / "build_osv_telemetry_report.py"

    spec = importlib.util.spec_from_file_location("build_osv_telemetry_report_tool", tool_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    manifest, data, data_file = module.load_report_bundle(report_dir)
    html = module.render_html(manifest, data, data_file)

    assert len(data["quaternions"]) == 4003
    assert "DJI Osmo 360 OSV Telemetry Analysis" in html
    assert "Quaternion Frames" in html
    assert "4003" in html
