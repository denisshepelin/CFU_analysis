from pathlib import Path

import PySimpleGUI as sg
import pandas as pd

from scripts.config import FONT


def compose_reports():
    """
    Creates UI for selecting reports that needs to be merged together
    """

    compose_report_layout = [
                [sg.Text('Please select the folder where the plates with reports are and press Run'),
                 sg.FolderBrowse(key="ReportRootPath")],
                [sg.Button('Run'), sg.Button('Cancel')] ]
    report_window = sg.Window("Where are reports located?", compose_report_layout, font = FONT)
    while True:
        r_event, r_values = report_window.read()
        if r_event in (None, "Cancel"):
            break
        if r_event in (None, "Run"):
            target_path = Path(r_values["ReportRootPath"])
            show_reports_selector(target_path)
            report_window.close()

    report_window.close()


def show_reports_selector(reports_root_path):
    """ Creates picker for a reports """
    reports = list(reports_root_path.glob("plate_*/report*.xlsx"))
    reports_map = {r.stem:r for r in reports}

    s_layout = []
    s_layout += [[sg.Text("Please mark reports that you want to merge:")]]
    for r in reports:
        s_layout += [[sg.Checkbox(' ', key=r.stem, font=FONT), sg.Text(r.stem)]]
    s_layout += [[sg.Text('Specify where to save to composed report'), sg.FolderBrowse(key="ComposedReportPath")]]
    s_layout += [[sg.Button("Merge"), sg.Button("Cancel")]]

    select_reports = sg.Window("Select reports", s_layout, font = FONT)

    while True:
        s_event, s_values = select_reports.read()
        if s_event in (None, "Cancel"):
            break
        if s_event in (None, "Merge"):
            selected_reports = [reports_map[v] for v in s_values if s_values[v] is True and v is not "ComposedReportPath"]
            save_path = Path(s_values["ComposedReportPath"])
            merge_reports(selected_reports, save_path)
            sg.popup("Success!", font=FONT)
            select_reports.close()

    select_reports.close()


def merge_reports(reports, save_path):
    """ Given a list of Excel reports make a new big composed report at save_path"""
    composed_report = pd.concat([pd.read_excel(r) for r in reports], ignore_index=True)
    to_drop = [c for c in composed_report.columns if c.startswith("Unnamed")]
    composed_report = composed_report.drop(to_drop, axis=1)
    reports_map = {r.stem: r for r in reports}

    # go through each row and paste Image in a correct column
    writer = pd.ExcelWriter(save_path / f"composed_report.xlsx", engine="xlsxwriter")
    composed_report.to_excel(writer, sheet_name="Sheet1")
    worksheet = writer.sheets['Sheet1']
    worksheet.set_default_row(130)
    # corresponds to D
    worksheet.set_column(3, 3, 25)
    worksheet.set_row(0, 20)

    for idx, row in composed_report.iterrows():
        # Find well image based on the name of the plate and Well
        well_image = (reports_map["report_"+row["Plate"]].parent
                      / "crops" / f"{row['Well']}.png").absolute().resolve()
        # index is 0-based, but we should put image based on 2-based because first row is a header
        index = "D" + str(idx + 2)

        worksheet.insert_image(index, str(well_image), {'object_position': 1})

    writer.save()