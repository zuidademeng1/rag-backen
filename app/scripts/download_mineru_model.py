#!/usr/bin/env python3
"""
MinerU Model Download Script

Downloads MinerU models (Pipeline + VLM) from HuggingFace or ModelScope
to a specified local directory, then configures MinerU to use local mode.

Usage:
    python download_mineru_model.py                          # HF, current dir
    python download_mineru_model.py -s modelscope            # ModelScope
    python download_mineru_model.py -o ./models              # custom output dir
    python download_mineru_model.py --pipeline-only           # only pipeline
    python download_mineru_model.py --vlm-only               # only VLM
    python download_mineru_model.py --write-config           # auto-write config

Requires: huggingface_hub or modelscope installed in the venv.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Model Repository Configuration
# ---------------------------------------------------------------------------

PIPELINE_REPO = {
    "huggingface": "opendatalab/PDF-Extract-Kit-1.0",
    "modelscope": "OpenDataLab/PDF-Extract-Kit-1.0",
}

VLM_REPO = {
    "huggingface": "opendatalab/MinerU2.5-Pro-2604-1.2B",
    "modelscope": "OpenDataLab/MinerU2.5-Pro-2604-1.2B",
}

# Key subpaths to verify after pipeline download
PIPELINE_CHECK_PATHS = [
    "models/Layout/PP-DocLayoutV2",
    "models/MFR/unimernet_hf_small_2503",
    "models/MFR/pp_formulanet_plus_m",
    "models/OCR/paddleocr_torch",
    "models/TabRec/SlanetPlus/slanet-plus.onnx",
    "models/TabRec/UnetStructure/unet.onnx",
    "models/TabCls/paddle_table_cls/PP-LCNet_x1_0_table_cls.onnx",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_dirname(repo_id: str) -> str:
    """Extract the last component of a repo ID (the directory name)."""
    return repo_id.rstrip("/").split("/")[-1]


def _download_hf(repo_id: str, dest: Path) -> None:
    from huggingface_hub import snapshot_download

    print(f"  Source: HuggingFace  Repo: {repo_id}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
        resume_download=True,
    )


def _download_ms(repo_id: str, dest: Path) -> None:
    from modelscope import snapshot_download

    print(f"  Source: ModelScope  Repo: {repo_id}")
    snapshot_download(model_id=repo_id, local_dir=str(dest))


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


def download_model(source: str, repo_type: str, output_dir: Path) -> Path:
    """
    Download one model repo (pipeline or vlm).

    Returns the Path to the downloaded model directory.
    """
    repos = PIPELINE_REPO if repo_type == "pipeline" else VLM_REPO
    repo_id = repos[source]
    model_dir = output_dir / _repo_dirname(repo_id)

    if model_dir.exists():
        check_paths = PIPELINE_CHECK_PATHS if repo_type == "pipeline" else []
        if _verify(model_dir, check_paths):
            print(f"  [{model_dir.name}] already exists and looks complete, skipping.")
            return model_dir
        print(f"  [{model_dir.name}] exists but incomplete, removing and re-downloading ...")
        shutil.rmtree(model_dir)

    model_dir.mkdir(parents=True, exist_ok=True)

    dl_fn = _download_hf if source == "huggingface" else _download_ms
    dl_fn(repo_id, model_dir)
    return model_dir


def _verify(model_dir: Path, check_paths: list[str]) -> bool:
    """Return True when every relative path under *model_dir* exists."""
    for rel in check_paths:
        if not (model_dir / rel).exists():
            return False
    return True


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _fmt_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def write_mineru_config(pipeline_dir: Path | None, vlm_dir: Path | None) -> None:
    """Write (or update) ~/mineru.json with absolute paths to the models."""
    cfg_path = Path.home() / "mineru.json"
    models_dir = {}

    if pipeline_dir:
        models_dir["pipeline"] = str(pipeline_dir.resolve())
    if vlm_dir:
        models_dir["vlm"] = str(vlm_dir.resolve())

    config = {"models-dir": models_dir}

    # backup existing config
    if cfg_path.exists():
        backup = cfg_path.with_suffix(".json.bak")
        shutil.copy2(cfg_path, backup)
        print(f"  Existing config backed up → {backup}")

    cfg_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  Config written → {cfg_path}")
    print(f"  Content: {json.dumps(config, indent=2, ensure_ascii=False)}")


def print_summary(source: str, pipeline_dir: Path | None, vlm_dir: Path | None) -> None:
    """Print final summary and usage instructions."""
    print()
    print("=" * 60)
    print("  Download Complete!")
    print("=" * 60)

    if pipeline_dir and pipeline_dir.exists():
        print(f"  Pipeline  ({_fmt_size(_dir_size(pipeline_dir))})")
        print(f"    {pipeline_dir}")
    if vlm_dir and vlm_dir.exists():
        print(f"  VLM       ({_fmt_size(_dir_size(vlm_dir))})")
        print(f"    {vlm_dir}")

    print()
    print("  To use local models, set the environment variable:")
    print()
    print('    export MINERU_MODEL_SOURCE=local     # Linux / macOS')
    print('    set MINERU_MODEL_SOURCE=local        # Windows CMD')
    print("    $env:MINERU_MODEL_SOURCE = 'local'   # PowerShell")
    print()
    print("  Or pass source='local' when calling the parser:")
    print("    parser.parse_document(..., source='local')")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download MinerU models (Pipeline + VLM) to a local directory.")

    p.add_argument(
        "-s", "--source",
        choices=["huggingface", "modelscope"],
        default="huggingface",
        help="Model source (default: huggingface)",
    )
    p.add_argument(
        "-o", "--output-dir",
        default=".",
        help="Target directory (default: current directory)",
    )

    # mutually exclusive download filters
    filters = p.add_argument_group("download filters")
    filters.add_argument("--pipeline-only", action="store_true", help="Download only the Pipeline model")
    filters.add_argument("--vlm-only", action="store_true", help="Download only the VLM model")
    filters.add_argument("--skip-pipeline", action="store_true", help="Skip Pipeline model")
    filters.add_argument("--skip-vlm", action="store_true", help="Skip VLM model")

    # config auto-write (default=None → prompt)
    p.add_argument(
        "--write-config",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Auto-write ~/mineru.json (default: prompt)",
    )

    return p.parse_args(argv)


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    dl_pipeline = not args.vlm_only and not args.skip_pipeline
    dl_vlm = not args.pipeline_only and not args.skip_vlm

    if not dl_pipeline and not dl_vlm:
        print("Nothing to download — all models were filtered out.")
        sys.exit(0)

    print(f"Source:      {args.source}")
    print(f"Output dir:  {output_dir}")
    print(f"Pipeline:    {'yes' if dl_pipeline else 'no'}")
    print(f"VLM:         {'yes' if dl_vlm else 'no'}")
    print()

    pipeline_dir: Path | None = None
    vlm_dir: Path | None = None

    # --- Pipeline ---
    if dl_pipeline:
        print("[1/{}] Pipeline model …".format(2 if dl_vlm else 1))
        pipeline_dir = download_model(args.source, "pipeline", output_dir)

        ok = _verify(pipeline_dir, PIPELINE_CHECK_PATHS)
        print(f"  Verify: {'OK' if ok else 'INCOMPLETE — some files missing'}")
        print()

    # --- VLM ---
    if dl_vlm:
        print("[2/2] VLM model …")
        vlm_dir = download_model(args.source, "vlm", output_dir)
        ok = vlm_dir.exists() and any(vlm_dir.iterdir())
        print(f"  Verify: {'OK' if ok else 'INCOMPLETE — directory empty'}")
        print()

    # --- Config ---
    # Decide whether to write ~/mineru.json
    should_write = args.write_config  # True / False / None
    if should_write is None:
        # prompt user when at least one model was downloaded successfully
        any_ok = (pipeline_dir and pipeline_dir.exists()) or (vlm_dir and vlm_dir.exists())
        if any_ok:
            ans = input("Write ~/mineru.json for local mode? (Y/n): ").strip().lower()
            should_write = ans in ("", "y", "yes")

    if should_write:
        write_mineru_config(pipeline_dir, vlm_dir)

    # --- Summary ---
    print_summary(args.source, pipeline_dir, vlm_dir)


if __name__ == "__main__":
    main()
