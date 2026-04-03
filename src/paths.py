"""プロジェクトルートとパス解決（カレントディレクトリに依存しない）。"""

from pathlib import Path

# このファイルは src/paths.py に置く
PROJECT_ROOT = Path(__file__).resolve().parent.parent
