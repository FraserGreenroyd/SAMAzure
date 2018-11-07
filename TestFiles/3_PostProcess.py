import os
import argparse
import json
import pandas as pd


def load_json(path):
    """
    Load a JSON file into a dictionary object
    :type path: Path to JSON file
    :return: Dictionary representing content of JSON file
    """
    with open(path) as data_file:
        return json.load(data_file)


def find_files(directory, extension):
    """Lists files of a specified extension in the target directory.

    :param str directory: The directory to explore
    :param str extension: The file extension to search for
    :return str: List of files in the directory with the specified extension
    """
    files = []
    for file in os.listdir(directory):
        if file.endswith(extension):
            files.append(os.path.abspath(os.path.join(directory, file)))
    return sorted(files)


if __name__ == '__main__':

    # Obtain arguments from the script inputs
    parser = argparse.ArgumentParser(description="Load results downloaded from Azure")
    parser.add_argument(
        "-d",
        "--caseDirectory",
        type=str,
        help="Path to the case directory from which simulation results are obtained",
        default=os.path.join('resources', 'radiance_case'))
    args = parser.parse_args()

    # Get the results files
    results_files = find_files(os.path.join(args.caseDirectory, "Results"), ".json")

    # Load results into a Pandas DataFrame
    df = pd.DataFrame()
    for b in results_files:
        _res = load_json(b)
        temp = pd.DataFrame(_res)
        df = pd.concat([df, temp])
    df.reset_index(drop=True, inplace=True)

    print(df.columns)

    # Print some metrics
    print("x-range: {} to {}".format(min(df["x"]), max(df["x"])))
    print("y-range: {} to {}".format(min(df["y"]), max(df["y"])))
    print("z-range: {} to {}".format(min(df["z"]), max(df["z"])))
    print("df-range: {} to {}".format(min(df["df"]), max(df["df"])))
    print("da-range: {} to {}".format(min(df["da"]), max(df["da"])))
    print("cda-range: {} to {}".format(min(df["cda"]), max(df["cda"])))
    print("udi_less-range: {} to {}".format(min(df["udi_less "]), max(df["udi_less "])))
    print("udi-range: {} to {}".format(min(df["udi"]), max(df["udi"])))
    print("udi_more-range: {} to {}".format(min(df["udi_more"]), max(df["udi_more"])))

    # Write to a massive CSV
    df.to_csv(os.path.join(args.caseDirectory, "results_joined.csv"), index=False)
