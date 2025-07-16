{pkgs, ...}: {
  packages = with pkgs; [
    ruff
    cmake
    tesseract
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
    uvicorn app.main:app --reload
  '';

  git-hooks.hooks.ruff.enable = true;

  dotenv.enable = true;

  env.UV_CACHE_DIR = ".uv-cache";
}
