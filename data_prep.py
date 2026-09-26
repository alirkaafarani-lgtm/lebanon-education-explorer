"""Load and clean the Educational_Level-Lebanon-2023 dataset.

Source: AUB linked-data portal (https://linked.aub.edu.lb:8502/), published from
Impact Open Data. One row per Lebanese town, giving the share of residents at
each education level plus a school-dropout rate.
"""

import pathlib
import urllib.parse

import pandas as pd

DATA = pathlib.Path(__file__).resolve().parent / "Educational_Level-Lebanon-2023.csv"

PREFIX = "PercentageofEducationlevelofresidents-"

# Source column -> label used on every chart, in ascending order of attainment.
LEVELS = {
    f"{PREFIX}illeterate": "Illiterate",
    f"{PREFIX}elementary": "Elementary",
    f"{PREFIX}intermediate": "Intermediate",
    f"{PREFIX}secondary": "Secondary",
    f"{PREFIX}vocational": "Vocational",
    f"{PREFIX}university": "University",
    f"{PREFIX}highereducation": "Higher education",
}
LEVEL_ORDER = list(LEVELS.values())
DROPOUT = "PercentageofSchooldropout"

# The refArea column mixes governorate- and district-level URIs. Lebanon's eight
# governorates are the reporting unit people actually recognise, so districts are
# rolled up to their governorate.
DISTRICT_TO_GOVERNORATE = {
    "Matn": "Mount Lebanon",
    "Baabda": "Mount Lebanon",
    "Aley": "Mount Lebanon",
    "Keserwan": "Mount Lebanon",
    "Byblos": "Mount Lebanon",
    "Chouf": "Mount Lebanon",
    "Tripoli, Lebanon": "North",
    "Tripoli District, Lebanon": "North",  # slug puts ", Lebanon" after "District"
    "Zgharta": "North",
    "Batroun": "North",
    "Bsharri": "North",
    "Koura": "North",
    "Miniyeh–Danniyeh": "North",
    "Zahlé": "Beqaa",
    "Western Beqaa": "Beqaa",
    "Rashaya": "Beqaa",
    "Hermel": "Baalbek-Hermel",
    "Baalbek": "Baalbek-Hermel",
    "Tyre": "South",
    "Sidon": "South",
    "Jezzine": "South",
    "Bint Jbeil": "Nabatieh",
    "Marjeyoun": "Nabatieh",
    "Hasbaya": "Nabatieh",
    "Nabatieh": "Nabatieh",
    "Akkar": "Akkar",
}

GOVERNORATE_ORDER = [
    "Beirut",
    "Mount Lebanon",
    "North",
    "Akkar",
    "Beqaa",
    "Baalbek-Hermel",
    "South",
    "Nabatieh",
]


def _fix_mojibake(text: str) -> str:
    """The source file double-encodes non-ASCII (Zahlé -> ZahlÃ©). Undo it."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def _area_name(uri: str) -> str:
    slug = urllib.parse.unquote(str(uri).rsplit("/", 1)[-1])
    return _fix_mojibake(slug.replace("_", " ")).strip()


def load(path=DATA) -> pd.DataFrame:
    """Full dataset, tidied but unfiltered, so the quality story stays visible."""
    df = pd.read_csv(path)
    df = df.rename(columns=LEVELS)
    df["Town"] = df["Town"].map(_fix_mojibake)
    df["Dropout"] = df[DROPOUT]

    area = df["refArea"].map(_area_name)
    # "Akkar Governorate" -> "Akkar"; "Matn District" -> "Matn"
    unit = area.str.replace(r"\s+(Governorate|District)$", "", regex=True)
    df["Area"] = unit
    df["Governorate"] = unit.map(DISTRICT_TO_GOVERNORATE).fillna(unit)

    # Levels are shares of one population, so a valid row sums to 100. Rows that
    # miss badly are data-entry errors (one sums to 13,200) and are flagged, not
    # silently repaired.
    df["LevelSum"] = df[LEVEL_ORDER].sum(axis=1, min_count=1)
    df["Reported"] = df["LevelSum"].notna() & (df["LevelSum"] > 0)
    df["Consistent"] = df["Reported"] & df["LevelSum"].between(99, 101)
    return df


def analysis_frame(df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Only towns whose level shares sum to ~100 — the basis for every chart."""
    df = load() if df is None else df
    out = df[df["Consistent"]].copy()
    # A handful of these rows leave one level blank while the remaining six still
    # sum to ~100, which means that level's share is zero rather than unknown.
    # Dropout is left as NaN: a missing dropout figure really is unreported.
    out[LEVEL_ORDER] = out[LEVEL_ORDER].fillna(0.0)
    return out


def add_need_index(df: pd.DataFrame) -> pd.DataFrame:
    """A town-level need score: how far the population leans to the bottom of the
    education ladder rather than the top.

    Need = (illiterate + elementary) - (university + higher education), in
    percentage points. Positive means more residents stopped at or below
    elementary than reached tertiary education. Both halves are shares of the
    same population, so the difference needs no rescaling and stays readable.
    """
    df = df.copy()
    df["LowAttainment"] = df["Illiterate"] + df["Elementary"]
    df["Tertiary"] = df["University"] + df["Higher education"]
    df["NeedScore"] = df["LowAttainment"] - df["Tertiary"]
    return df


def variance_within_governorate(df: pd.DataFrame, column: str = "University") -> float:
    """Share of town-level variation that governorate does NOT explain (%)."""
    grand = df[column].mean()
    between = df.groupby("Governorate")[column].apply(
        lambda s: len(s) * (s.mean() - grand) ** 2
    ).sum()
    total = ((df[column] - grand) ** 2).sum()
    return (1 - between / total) * 100


def quality_report(df: pd.DataFrame) -> dict:
    return {
        "towns_total": len(df),
        "towns_no_data": int((~df["Reported"]).sum()),
        "towns_inconsistent": int((df["Reported"] & ~df["Consistent"]).sum()),
        "towns_analysed": int(df["Consistent"].sum()),
        "governorates": df.loc[df["Consistent"], "Governorate"].nunique(),
    }


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    full = load()
    print(quality_report(full))
    a = analysis_frame(full)
    print("\nTowns per governorate:")
    print(a["Governorate"].value_counts().to_string())
    print("\nMean % by level:")
    print(a[LEVEL_ORDER].mean().round(2).to_string())
