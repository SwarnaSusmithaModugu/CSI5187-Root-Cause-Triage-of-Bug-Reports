from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
DATASET_ROOT = RAW_ROOT / "mlClassifier" / "data"
BUGREPORTS_DIR = DATASET_ROOT / "bugreports"
PROJECT_DATA_DIR = RAW_ROOT / "githubanalysis" / "data"
TRAININGSETS = sorted(DATASET_ROOT.glob("trainingset_*.csv"))
DATASET_COMPOSITION = DATASET_ROOT / "dataset_composition.txt"
DATASET_README = RAW_ROOT / "README.md"
EXAMPLE_ISSUE = RAW_ROOT / "exampleIssue.json"
CONFIG_JSON = RAW_ROOT / "config.json"
KEYWORD_DATA_DIR = RAW_ROOT / "keywordSearch" / "data"
