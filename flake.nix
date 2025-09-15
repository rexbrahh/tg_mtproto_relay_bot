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
        pythonPackages = pkgs.python311Packages;
        telethonPkg = pythonPackages.buildPythonPackage rec {
          pname = "telethon";
          version = "1.41.2";
          pyproject = true;

          src = pythonPackages.fetchPypi {
            inherit pname version;
            sha256 = "0pnw5d6k6mh7a6172dlnqad3wms6lgywlikbc9w86rk2vx0k82ih";
          };

          build-system = [
            pythonPackages.setuptools
            pythonPackages.wheel
          ];

          dependencies = [
            pythonPackages.pyaes
            pythonPackages.rsa
          ];

          optional-dependencies = {
            cryptg = [ pythonPackages.cryptg ];
          };

          pythonImportsCheck = [ "telethon" ];
          doCheck = false;
        };
        pyEnv = py.withPackages (ps: [
          telethonPkg
          ps.httpx
          ps.python-dotenv
          ps.uvloop
          ps.fastapi
          ps.uvicorn
          ps.pydantic
          ps.pytest
          ps.pytest-asyncio
          ps.mypy
          ps.black
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
          meta = {
            description = "Run the GMGN relay bot";
          };
        };

        checks.ci = pkgs.runCommand "ci-checks" {
          buildInputs = [ pyEnv pkgs.ruff ];
          src = self;
        } ''
          cp -R "$src"/. .
          chmod -R +w .
          export PYTHONPATH=$PWD/src:${PYTHONPATH:-}
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
