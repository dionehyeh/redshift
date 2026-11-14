import os
import pandas as pd
from app.config import settings

def get_cell_path(cell_id: str, kind: str = "normals") -> str:
    os.makedirs(settings.cache_dir, exist_ok=True)
    return os.path.join(settings.cache_dir, f"{cell_id}_{kind}.parquet")

def load_cell_normals(cell_id: str) -> dict[str, list[float]]:
    path = get_cell_path(cell_id, "normals")
    if os.path.exists(path):
        df = pd.read_parquet(path)
        return {col: df[col].tolist() for col in df.columns}
    
    # In demo mode, load fallback fixture or synthetic 52-week normal curves
    # Baseline normal values for lowland Kerala:
    rain_baseline = [
        10, 8, 12, 15, 20, 25, 30, 45, 60, 80, 110, 150,
        220, 280, 310, 290, 260, 210, 180, 150, 120, 95, 80, 70,
        60, 55, 50, 45, 40, 35, 30, 35, 40, 50, 70, 95,
        140, 180, 210, 230, 190, 150, 110, 80, 60, 40, 25, 18,
        15, 12, 10, 10
    ]
    tmean_baseline = [27.0 + 1.5 * (1 - abs(w - 15) / 20) for w in range(1, 53)]
    tmax_baseline = [t + 4.5 for t in tmean_baseline]
    
    return {
        "rain": rain_baseline,
        "tmean": tmean_baseline,
        "tmax": tmax_baseline,
    }
