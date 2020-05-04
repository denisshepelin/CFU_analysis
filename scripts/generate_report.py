import base64
import math
import re
from pathlib import Path

import PySimpleGUI as sg
import pandas as pd

from scripts.config import (
    HUGE_COLONY_THRESHOLD,
    TOO_MANY_TO_COUNT_RESULT,
    FIXME_RESULT,
    FONT,
)


def get_counts(record):
    """
    takes _particles.csv result from Fiji and filters it.
    returns result, that can be:
    Either amount of colonies (including zero),
    "noncountable" class or FIXME keyword meaning there is a need for inspection
    """

    # record has a following structure:
    # Header is Area (square pixels), StdDev, Perim (pixels?)
    # Rows are particles found by the Analyze Particles

    # By default result is amount of particles found (nrows) in the given image
    result = len(record)

    # work out what happens if there is a colony size bigger than some threshold
    if (record["Area"] > HUGE_COLONY_THRESHOLD).any():
        result = TOO_MANY_TO_COUNT_RESULT

    return result


def make_excel_report(writer, report_df, image_files):
    """
    Make Excel report given pandas dataframe containing counts and set of images
    """

    report_df.to_excel(writer, sheet_name="Sheet1")
    worksheet = writer.sheets["Sheet1"]
    worksheet.set_default_row(130)
    worksheet.set_column(2, 2, 25)
    worksheet.set_row(0, 20)

    offset_map = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7}
    header_offset = 1
    detailed_well_regexp = r"^(?P<row>\D)(?P<column>\d{2})"

    for image in image_files:
        row, column = re.search(detailed_well_regexp, image.stem).groups()
        well_image = image.absolute()

        # Determine what is the cell index where we need to put an image
        index = "C" + str(header_offset + offset_map[row] * 12 + int(column))

        worksheet.insert_image(index, str(well_image), {"object_position": 1})

    return writer


def process_plate(plate_path):
    """
    Given single folder make a new report out of crops or optionally crops + counts
    """
    # find all particle files for a corresponding well image
    # Given the list of particle records for each well
    # make a table containing:
    # 1) ID of plate
    # 2) Well name
    # 3) Result

    plate_name = re.search(r"plate_(?P<plate>\S*)", plate_path.stem).group(1)
    print(f"Found plate {plate_name}, making report ...")

    crops = plate_path / "crops"
    image_files = list(crops.glob("*.png"))
    wells = []
    well_regexp = r"^(\D\d{2})"  # To match something like A12 in A12.png_particles.csv

    # Collect all counts if they exist or put FIXME
    for image in image_files:
        well_name = re.search(well_regexp, image.stem).group(1)
        # convert png to base64
        # well_image = (crops / f"{well_name}.png").absolute()
        png_base = base64.b64encode(open(image, "rb").read()).decode()

        try:
            well_data = pd.read_csv(f"{image}_particles.csv", index_col=0)
            well_result = get_counts(well_data)
        except:
            well_result = FIXME_RESULT

        well_image_img = f'<img src="data:image/png;base64,{png_base}"/>'

        well_record = pd.Series(
            {"Well": well_name, "Count": well_result, "Image": well_image_img}
        )

        wells.append(well_record)

    # report should have a following structure sorted by the well:
    # ID (name of the well image.jpg), actual Image, Count obtained from get_count
    # Some other columns representing plate wide parameters
    report = pd.DataFrame(data=wells).sort_values("Well").set_index("Well")
    report["Plate"] = plate_name

    report.to_html(plate_path / "report.html", escape=False)

    # If excel is the report type then prepare for some wild rodeo
    # remove original png embedding
    report["Image"] = ""

    report_file = plate_path / f"report_{plate_name}.xlsx"
    if report_file.exists():
        report_file.rename(plate_path / f"report_{plate_name}.xlsx.old")

    writer = pd.ExcelWriter(
        plate_path / f"report_{plate_name}.xlsx", engine="xlsxwriter"
    )
    writer = make_excel_report(writer=writer, report_df=report, image_files=image_files)
    writer.save()

    return plate_name


def process_folders(root_folder):
    """
    Given folder that contains subfolders for each plate make reports for each plate
    """

    # find all plate folders
    plate_folders = root_folder.glob("plate_*")

    plates_finished = []
    for plate_path in plate_folders:
        plate_name = process_plate(plate_path)
        plates_finished.append(plate_name)
    return plates_finished


def generate_report():
    """ UI for a Single plate and Batch generation"""

    generate_report_layout = [
        [
            sg.Text(
                "Please select either the folder with a single plate (and press Single plate) or with "
                "several plates (and press Run Batch)"
            ),
            sg.FolderBrowse(key="PlatesRootPath"),
        ],
        [sg.Button("Single plate"), sg.Button("Run Batch"), sg.Button("Cancel")],
    ]
    generate_report_window = sg.Window(
        "Generate reports for plates", generate_report_layout, font=FONT
    )
    while True:
        event, values = generate_report_window.read()
        if event in (None, "Cancel"):
            break
        if event in (None, "Single plate"):
            print("The path is ", values["PlatesRootPath"])
            plate = process_plate(plate_path=Path(values["PlatesRootPath"]))
            if plate:
                sg.popup(f"Done working for those plates - {plate}", font=FONT)
            else:
                sg.popup(
                    f"Some issue occurred while processing plate {plate}", font=FONT
                )
        if event in (None, "Run Batch"):
            print("The path is ", values["PlatesRootPath"])
            plates_finished = process_folders(
                root_folder=Path(values["PlatesRootPath"])
            )
            if len(plates_finished) == 0:
                sg.popup(
                    "There were no plates found, please check the root folder or the names of the plates folders",
                    font=FONT,
                )
            else:
                plate_list = ", ".join(plates_finished)
                sg.popup(f"Done working for those plates - {plate_list}", font=FONT)

    generate_report_window.close()
