import PySimpleGUI as sg

from scripts.compose_reports import compose_reports
from scripts.config import FONT
from scripts.generate_report import generate_report
from scripts.analyze_report import analyze_report

if __name__ == "__main__":
    sg.theme("DarkAmber")  # Add a touch of color
    # All the stuff inside your window.
    layout = [
        [sg.Text("This program can:")],
        [
            sg.Text(
                "A) Generate reports from plates obtained after ImageJ macro (press Generate reports)"
            )
        ],
        [
            sg.Text(
                "B) Gather generated reports together into a single big report (press Compose reports)"
            )
        ],
        [
            sg.Text(
                "С) Analyze reports converting counts to CFUs (press Analyze reports)"
            )
        ],
        [
            sg.Button("Generate reports"),
            sg.Button("Compose reports"),
            sg.Button("Analyze report"),
            sg.Button("Quit"),
        ],
    ]

    # Create the Window
    main_window = sg.Window("Make report for plates", layout, font=FONT)
    while True:
        event, values = main_window.read()
        if event in (None, "Quit"):  # if user closes window or clicks cancel
            break
        if event in (None, "Generate reports"):
            generate_report()
        if event in (None, "Compose reports"):
            compose_reports()
        if event in (None, "Analyze report"):
            analyze_report()

    main_window.close()
