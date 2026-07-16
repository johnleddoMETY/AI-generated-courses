import sys
from pathlib import Path

# Make the sibling llm_engine package importable regardless of cwd —
# more reliable than depending on the editable-install .pth hook firing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
