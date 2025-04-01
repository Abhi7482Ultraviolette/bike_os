# analysis.py

import pandas as pd
import numpy as np

def moving_average(data, window_size):
    """Calculate the moving average of a time series."""
    return data.rolling(window=window_size).mean()

def temp_fluctuation_detection(data):
    """
    Detect temperature fluctuations in the provided data.
    :param data: Input data (DataFrame with temperature sensor readings)
    :return: Dictionary containing detection results
    """
    # Signal Initialization
    Signal = 0
    SensorWithIssue = None

    # Sensor Names
    TempArrays = ['TS1', 'TS2', 'TS3', 'TS4', 'TS5', 'TS6', 'TS7', 'TS8', 'TS9', 'TS10', 'TS11', 'TS12', 'TS0_FLT', 'TS13_FLT']

    # Parameters
    ThresholdValv1 = 0.0011
    ThresholdValv2 = 0.0025
    WindowThreshold = 20

    # Feature Fetching
    TS_FILE_DF = data[TempArrays]

    # Mean Centering
    TS_FILE_DF = TS_FILE_DF - TS_FILE_DF.mean()

    # Moving average filtered New data
    NewArr = np.array([moving_average(data=TS_FILE_DF[i], window_size=WindowThreshold) for i in TempArrays])

    # OldArr
    OldArr = np.array([np.array(TS_FILE_DF[i]) for i in TempArrays])

    # Old vs New Diff
    DiffArr = OldArr - NewArr

    # Variance Storage
    VarianceStorage = [np.var(DiffArr[i][WindowThreshold - 1:]) for i in range(len(DiffArr))]

    # Threshold Check
    for i in range(len(VarianceStorage)):
        if i <= 11:  # Threshold for temperature sensors 'TS1' to 'TS12'
            if VarianceStorage[i] > ThresholdValv1:
                SensorWithIssue = f"TS{i + 1}"
                Signal = 1
                break
        else:  # Threshold for temperature sensors 'TS0_FLT' and 'TS13_FLT'
            if VarianceStorage[i] > ThresholdValv2:
                if i == 12:
                    SensorWithIssue = "TS0_FLT"
                elif i == 13:
                    SensorWithIssue = "TS13_FLT"
                Signal = 1
                break

    return {
        "detected": Signal == 1,
        "max_fluctuation": max(VarianceStorage),
        "critical_points": [i for i, var in enumerate(VarianceStorage) if var > ThresholdValv1 or var > ThresholdValv2]
    }

def solder_issue_detection(data):
    """
    Detect solder issues in the provided data.
    :param data: Input data (DataFrame with cell voltage and current readings)
    :return: Dictionary containing detection results
    """
    # Signal Initialization
    Signal = 0
    CellWithIssue = None

    # Parameters
    Threshold = 15
    NeglectFirstRows = 5
    NeglectLastRows = 5
    CellDVThreshold = 0.01
    Distance = 0.01

    # Fetch all Rest periods
    Rest_period_data = data[(data['DSG_Current'] <= 1) & (data['CHG_Current'] <= 1)]
    sequences = consecutive_sequence(index_list=Rest_period_data.index, Threshold=Threshold)
    result_dfs = [Rest_period_data.loc[seq] for seq in sequences]

    # Ensure there are Rest Periods in dataframe
    if len(result_dfs) > 0:
        for RestPeriod in range(len(result_dfs)):
            df = result_dfs[RestPeriod]
            # Take required data for algorithm
            df = df.iloc[NeglectFirstRows:].reset_index(drop=True).iloc[:-NeglectLastRows].reset_index(drop=True)[
                ['Cell1', 'Cell2', 'Cell3', 'Cell4', 'Cell5', 'Cell6', 'Cell7', 'Cell8', 'Cell9', 'Cell10', 'Cell11', 'Cell12', 'Cell13', 'Cell14']
            ]

            # Calculate CellDV
            MAX = df.max(axis=1)
            MIN = df.min(axis=1)
            CellDV = np.array(MAX - MIN)

            # Condition for CellDV
            if max(CellDV) >= CellDVThreshold:
                CentralTendency = [df[f'Cell{avg}'].mean() for avg in range(1, 15)]

                # Check if MAX and MIN are adjacent
                if abs(CentralTendency.index(max(CentralTendency)) - CentralTendency.index(min(CentralTendency))) == 1:
                    Q1 = np.percentile(CentralTendency, 25)
                    Q3 = np.percentile(CentralTendency, 75)
                    UpperOutlierLimit = Q3 + Distance
                    LowerOutlierLimit = Q1 - Distance

                    if (max(CentralTendency) > UpperOutlierLimit) and (min(CentralTendency) < LowerOutlierLimit):
                        Signal = 1
                        CellWithIssue = [
                            f"Cell{CentralTendency.index(min(CentralTendency)) + 1}",
                            f"Cell{CentralTendency.index(max(CentralTendency)) + 1}"
                        ]
                        break

    return {
        "detected": Signal == 1,
        "severity": "High" if Signal == 1 else "None",
        "locations": CellWithIssue if Signal == 1 else []
    }

def weld_issue_detection(data):
    """
    Detect weld issues in the provided data.
    :param data: Input data (DataFrame with cell voltage and current readings)
    :return: Dictionary containing detection results
    """
    # Signal Initialization
    Signal = 0
    CellWithIssue = None

    # Parameters
    Threshold = 50
    valv = 0.02
    SoCCheck = 20
    NeglectFirstRows = 20
    NeglectLastRows = 10

    # Fetch all Rest periods
    Rest_period_data = data[(data['DSG_Current'] <= 1) & (data['CHG_Current'] <= 1)]
    sequences = consecutive_sequence(index_list=Rest_period_data.index, Threshold=Threshold)
    result_dfs = [Rest_period_data.loc[seq] for seq in sequences]

    # Ensure there are Rest Periods in dataframe
    if len(result_dfs) > 0:
        for RestPeriod in range(len(result_dfs)):
            df = result_dfs[RestPeriod]
            FilteredData = df.iloc[NeglectFirstRows:].reset_index(drop=True).iloc[:-NeglectLastRows].reset_index(drop=True)

            if len(FilteredData) > 1:
                # Fetch first SOC value
                SOC = df['SOC'][df.index[0]]

                # Calculate CellDV
                OnlyCells = FilteredData[
                    ['Cell1', 'Cell2', 'Cell3', 'Cell4', 'Cell5', 'Cell6', 'Cell7', 'Cell8', 'Cell9', 'Cell10', 'Cell11', 'Cell12', 'Cell13', 'Cell14']
                ]
                MAX = OnlyCells.max(axis=1)
                MIN = OnlyCells.min(axis=1)
                CellDV = np.array(MAX - MIN)

                if SOC <= SoCCheck:
                    if min(CellDV) >= valv:
                        Signal = 1
                        CellWithIssue = FilteredData[
                            ['Cell1', 'Cell2', 'Cell3', 'Cell4', 'Cell5', 'Cell6', 'Cell7', 'Cell8', 'Cell9', 'Cell10', 'Cell11', 'Cell12', 'Cell13', 'Cell14']
                        ].iloc[np.where(CellDV == min(CellDV))[0][0]].idxmin()

    return {
        "detected": Signal == 1,
        "confidence": 0.95 if Signal == 1 else 0.05
    }

def consecutive_sequence(index_list, Threshold):
    """
    Find consecutive sequences in a list of indices.
    :param index_list: List of indices
    :param Threshold: Maximum gap allowed between consecutive indices
    :return: List of lists containing consecutive indices
    """
    sequences = []
    current_sequence = [index_list[0]]

    for i in range(1, len(index_list)):
        if index_list[i] - index_list[i - 1] <= Threshold:
            current_sequence.append(index_list[i])
        else:
            sequences.append(current_sequence)
            current_sequence = [index_list[i]]

    sequences.append(current_sequence)
    return sequences