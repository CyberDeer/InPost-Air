"""Prepare a persistent HA environment and config for a VS Code debug profile."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    selected = next(
        (
            item
            for item in project["tool"]["ha-debug"]["versions"]
            if item["ha"] == args.version
        ),
        None,
    )

    if selected is None:
        parser.error(f"HA {args.version} is not configured in tool.ha-debug.versions")

    environment = root / ".ha-envs" / selected["ha"]
    python = environment / "bin" / "python"

    if not python.exists():
        subprocess.run(
            [
                "uv",
                "--no-config",
                "venv",
                "--python",
                selected["python"],
                str(environment),
            ],
            cwd=root,
            check=True,
        )

    subprocess.run(
        [
            "uv",
            "--no-config",
            "pip",
            "install",
            "--python",
            str(python),
            f"homeassistant=={selected['ha']}",
            "debugpy>=1.8.17",
            *project["project"]["dependencies"],
        ],
        cwd=root,
        check=True,
    )
    config = root / "config" / "versions" / selected["ha"]
    config.mkdir(parents=True, exist_ok=True)
    configuration = config / "configuration.yaml"

    if not configuration.exists():
        shutil.copyfile(root / "config" / "configuration.yaml", configuration)

    components = config / "custom_components"

    if not components.exists():
        components.symlink_to(root / "custom_components", target_is_directory=True)

    print(f"Ready: HA {selected['ha']} / Python {selected['python']}")
    print(f"Config: {config}")


if __name__ == "__main__":
    main()
