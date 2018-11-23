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
        default="./resources/radiance_case")
    args = parser.parse_args()

    # Get the results files
    results_files = find_files(os.path.join(args.caseDirectory, "Results"), ".json")
    for i in results_files:
        print("Post-processing (combining) results for {0:}".format(os.path.basename(i)))

    # Load results into a Pandas DataFrame
    df = pd.DataFrame()
    for b in results_files:
        _res = load_json(b)
        temp = pd.DataFrame(_res)
        df = pd.concat([df, temp])
    df.reset_index(drop=True, inplace=True)

    # Print some metrics
    print("")
    print(df.describe().loc[['count', 'min', 'mean', 'max']])
    print("")

    # Write to a massive CSV
    output_path = os.path.join(args.caseDirectory, "results_joined.csv")
    df.to_csv(output_path, index=False)
    print("Combined results written to {0:}".format(output_path))
