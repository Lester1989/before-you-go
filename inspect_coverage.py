import json
import pathlib
import xml.etree.ElementTree as ET

import colorama


def perentage_bar(
    percent: float, length: int = 40, char: str = "█", empty: str = "-"
) -> str:
    return char * int(percent * length / 100) + empty * int(
        (100 - percent) * length / 100
    )


def line_color(new_coverage: float, old_coverage: float):
    is_improved = new_coverage > old_coverage
    color = colorama.Fore.GREEN if is_improved else colorama.Fore.RED
    if new_coverage == old_coverage or new_coverage < 0.5:
        color = (
            colorama.Fore.YELLOW if new_coverage < 0.5 else colorama.Fore.LIGHTWHITE_EX
        )
    return color


def display_coverage(new_coverage: float, old_coverage: float):
    is_improved = new_coverage > old_coverage
    return (
        perentage_bar(new_coverage * 100).ljust(40),
        f"{new_coverage*100:.0f} %".rjust(5),
        f"({old_coverage:.2f})".ljust(10),
        f'{"+" if is_improved else "-"}{new_coverage - old_coverage:.2f}',
    )

def main():
    last_coverage_file = pathlib.Path("last_coverage.json")
    if not last_coverage_file.exists():
        last_coverage_file.write_text("{}", encoding="utf8")
    last_coverage: dict[str, float] = json.loads(
        last_coverage_file.read_text(encoding="utf8")
    )
    coverage = pathlib.Path("coverage.xml").read_text(encoding="utf8")

    # parse xml to get the coverage
    root = ET.fromstring(coverage)
    packages = root.findall(".//package")

    this_coverage = {}

    for package in packages:
        package_name = package.get("name")
        old_coverage = last_coverage.get(package_name, 0)
        new_coverage = float(package.get("line-rate"))
        this_coverage[package_name] = new_coverage
        print(
            line_color(new_coverage, old_coverage),
            package_name.ljust(40, "-"),
            *display_coverage(new_coverage, old_coverage),
        )
        classes = package.findall(".//class")
        for class_ in classes:
            class_name = class_.get("name")
            old_coverage = last_coverage.get(f"{package_name}.{class_name}", 0)
            new_coverage = float(class_.get("line-rate"))
            this_coverage[f"{package_name}.{class_name}"] = new_coverage
            print(
                line_color(new_coverage, old_coverage),
                f" - {class_name}".ljust(40),
                *display_coverage(new_coverage, old_coverage),
            )

    print(colorama.Fore.RESET)
    last_coverage_file.write_text(json.dumps(this_coverage, indent=4), encoding="utf8")


if __name__ == "__main__":
    main()
