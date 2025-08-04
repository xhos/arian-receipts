{pkgs, ...}: {
  packages = with pkgs; [
    grpcurl
    buf
    ruff
  ];

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };

    venv = {
      enable = true;
      quiet = true;
    };
  };

  scripts.run.exec = ''
    arian-receipts
  '';

  scripts.bump-proto.exec = ''
    git -C proto fetch origin
    git -C proto checkout main
    git -C proto pull --ff-only
    git add proto
    git commit -m "⬆️ bump proto files"
    git push
  '';

  dotenv.enable = true;

  env.UV_CACHE_DIR = ".uv-cache";
}
