import importlib.metadata

VERSION = "unknown"
BUILD_TIME = "unknown"
GIT_COMMIT = "unknown"
GIT_BRANCH = "unknown"

try:
	VERSION = importlib.metadata.version("arian-receipts")
except importlib.metadata.PackageNotFoundError:
	pass


def get_version_info() -> dict[str, str]:
	return {
		"version": VERSION,
		"build_time": BUILD_TIME,
		"git_commit": GIT_COMMIT,
		"git_branch": GIT_BRANCH,
	}
