from pathlib import Path

import PySimpleGUI as sg
import pandas as pd
from xlrd import XLRDError

from scripts.config import FONT

# Constants so far
VOLUME = 200  # μl from Maraiekes sheet
LOW_COUNTS = 2
HIGH_COUNTS = 30


def process_report(report_path, low_counts, high_counts, volume):
    """
    Given the report compute the CFU, CFU/g and other metrics
    """
    try:
        # Check if everything is in place
        # One contains images and counts called "Counts"
        # Second contains experimental factors such as dilution
        counts = pd.read_excel(report_path, sheet_name="Counts", index_col=0).set_index(
            ["Well", "Plate"]
        )
        design = pd.read_excel(report_path, sheet_name="Design").set_index(
            ["Well", "Plate"]
        )
    except XLRDError:
        sg.Popup(
            f"Check if there are sheets 'Counts' and 'Design' in report {report_path.stem}",
            font=FONT,
        )
        return None

    report_df = pd.merge(left=counts, right=design, left_index=True, right_index=True)
    report_df = report_df.drop(["Image"], axis=1)

    if "FIXME" in report_df["Count"].values:
        sg.Popup(
            f"There are FIXME values in 'Counts' in report {report_path.stem}. Please fix them before analysis",
            font=FONT,
        )
        return None

    # IMPORTANT
    # There could be TMTC in Counts that make type of column to be not a number but a string
    # Following line will forcibly change that to numbers and generate NaNs
    report_df["Numerical Count"] = pd.to_numeric(report_df["Count"], errors="coerce")
    counts_filter = (report_df["Numerical Count"] > low_counts) & (
        report_df["Numerical Count"] < high_counts
    )
    report_df["Numerical Count"] = report_df["Numerical Count"].where(counts_filter)

    if "Extra Dilution" not in report_df.columns:
        report_df["Extra Dilution"] = 1.0

    report_df["Total Dilution Factor"] = (
        report_df["Extra Dilution"] * 10 ** report_df["Plate Dilution Power"].abs()
    )

    report_df["CFU/ml"] = (
        report_df["Numerical Count"] * report_df["Total Dilution Factor"] * volume
    )

    if "Sample Weight, mg" in report_df.columns:
        report_df["CFU/g"] = report_df["CFU/ml"] / report_df["Sample Weight, mg"] * 1000

    return report_df


def analyze_report():
    """ UI for a Single plate and Batch generation"""

    analyze_report_layout = [
        [
            sg.Text(
                "Please select the report to be analyzed. Make sure that it contains two sheets - Counts and Design."
            ),
            sg.FileBrowse(key="ReportPath"),
        ],
        [
            sg.InputText(str(LOW_COUNTS), key="LowCounts"),
            sg.Text("Lower threshold for the counts"),
        ],
        [
            sg.InputText(str(HIGH_COUNTS), key="HighCounts"),
            sg.Text("Higher threshold for the counts"),
        ],
        [sg.InputText(str(VOLUME), key="Volume"), sg.Text("Volume (μl)")],
        [sg.Button("Analyze"), sg.Button("Cancel")],
    ]
    analyze_report_window = sg.Window(
        "Generate reports for plates", analyze_report_layout, font=FONT
    )
    while True:
        event, values = analyze_report_window.read()
        if event in (None, "Cancel"):
            break
        if event in (None, "Analyze"):
            report_path = Path(values["ReportPath"])
            print("The path is ", report_path)
            low_counts = int(values["LowCounts"])
            high_counts = int(values["HighCounts"])
            volume = int(values["Volume"])

            report_df = process_report(report_path, low_counts, high_counts, volume)
            if report_df is not None:
                report_df.to_excel(
                    (report_path.parent / f"{report_path.stem}_analyzed.xlsx"),
                    sheet_name="Analysis",
                )
                sg.popup(f"Analyzed report {report_path.stem}", font=FONT)
            else:
                sg.popup(
                    f"Some issue occurred while analyzing report {report_path.stem}. Operation failed",
                    font=FONT,
                )

    analyze_report_window.close()
