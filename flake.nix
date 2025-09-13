{
  description = "GMGN Telethon relay (Nix flake)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        py = pkgs.python311;
        pyEnv = py.withPackages (ps: with ps; [
          telethon httpx python-dotenv uvloop fastapi uvicorn pydantic
          pytest mypy black
        ]);
      in {
        devShells.default = pkgs.mkShell {
          packages = [ pyEnv pkgs.ruff ];
          shellHook = ''
            export PYTHONPATH=$PWD/src:${PYTHONPATH:-}
            echo "DevShell ready: $(python --version)"
          '';
        };

        apps.bot = {
          type = "app";
          program = pkgs.writeShellScriptBin "bot" ''
            export PYTHONUNBUFFERED=1
            exec ${pyEnv}/bin/python main.py
          '' + "/bin/bot";
        };

        checks.ci = pkgs.runCommand "ci-checks" { buildInputs = [ pyEnv pkgs.ruff ]; } ''
          set -euo pipefail
          ruff check .
          black --check .
          mypy --strict src
          pytest -q
          mkdir -p "$out"
          touch "$out/done"
        '';

        formatter = pkgs.alejandra;
      }
    );
}
