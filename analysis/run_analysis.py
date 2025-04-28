import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analysis.log'),
        logging.StreamHandler()
    ]
)

def moving_average(data, window_size):
    """Calculate the moving average of a time series."""
    return data.rolling(window=window_size).mean()

def consecutive_sequence(index_list, threshold):
    """Find consecutive sequences in a list of indices."""
    sequences = []
    if not index_list:
        return sequences
    current_sequence = [index_list[0]]
    for i in range(1, len(index_list)):
        if index_list[i] - index_list[i-1] <= threshold:
            current_sequence.append(index_list[i])
        else:
            if len(current_sequence) > 1:
                sequences.append(current_sequence)
            current_sequence = [index_list[i]]
    if len(current_sequence) > 1:
        sequences.append(current_sequence)
    return sequences

def normalize_column_names(df):
    """Robust column name normalization handling multiple formats"""
    new_columns = []
    for col in df.columns:
        col = str(col).strip().lower().replace(' ', '_')
        # Special handling for temperature sensor columns
        if 'ts' in col and '_flt' in col:
            col = 'ts' + col.split('ts')[-1]  # Normalize to tsX_flt format
        new_columns.append(col)
    df.columns = new_columns
    return df

def validate_columns(df, required_columns):
    """Enhanced column validation with detailed output"""
    missing = [col for col in required_columns if col not in df.columns]
    
    if missing:
        print(f"\n[VALIDATION] Missing required columns:")
        print(f"Expected: {required_columns}")
        print(f"Actual: {df.columns.tolist()}")
        print(f"Missing: {missing}\n")
        return False
        
    print(f"[VALIDATION] All required columns present")
    return True

def temp_fluctuation_detection(parquet_data):
    """Detect temperature fluctuations using data from the .parquet file"""
    try:
        Signal = 0
        critical_points = []
        # Required columns
        temp_arrays = ['ts1', 'ts2', 'ts3', 'ts4', 'ts5', 'ts6',
                      'ts7', 'ts8', 'ts9', 'ts10', 'ts11', 'ts12',
                      'ts0_flt', 'ts13_flt']
        # Find available columns (case-insensitive)
        available_sensors = [col for col in parquet_data.columns 
                           if col.lower() in [t.lower() for t in temp_arrays]]
        if not available_sensors:
            logging.warning("No temperature sensors found in data")
            return {"detected": False, "max_fluctuation": 0, "critical_points": []}
        # Parameters
        ThresholdValv1 = 0.0011
        ThresholdValv2 = 0.0025
        WindowThreshold = 20
        # Mean centering and variance calculation
        ts_centered = parquet_data[available_sensors] - parquet_data[available_sensors].mean()
        rolling_mean = ts_centered.rolling(window=WindowThreshold).mean()
        diff = ts_centered - rolling_mean
        variances = {}
        for i, sensor in enumerate(available_sensors):
            threshold = ThresholdValv1 if i < 12 else ThresholdValv2
            var = diff[sensor][WindowThreshold-1:].var()
            variances[sensor] = var
            if var > threshold:
                Signal = 1
                critical_points.append(sensor)
        max_var = max(variances.values()) if variances else 0
        return {
            "detected": bool(Signal),
            "max_fluctuation": max_var,
            "critical_points": critical_points
        }
    except Exception as e:
        logging.error(f"Temperature fluctuation detection failed: {str(e)}", exc_info=True)
        return {"detected": False, "max_fluctuation": 0, "critical_points": []}

def solder_issue_detection(parquet_data):
    """Detect solder issues using data from the .parquet file"""
    try:
        Signal = 0
        CellWithIssue = None
        # Required columns
        required_cols = ['dsg_current', 'chg_current'] + [f'cell{i}' for i in range(1, 15)]
        if not validate_columns(parquet_data, required_cols):
            return {"detected": False, "severity": "None", "locations": []}
        # Parameters
        Threshold = 15
        NeglectFirstRows = 5
        NeglectLastRows = 5
        CellDVThreshold = 0.01
        Distance = 0.01
        # Find rest periods
        rest_data = parquet_data[
            (parquet_data['dsg_current'] <= 1) & 
            (parquet_data['chg_current'] <= 1)
        ]
        if len(rest_data) < NeglectFirstRows + NeglectLastRows:
            return {"detected": False, "severity": "None", "locations": []}
        # Analyze sequences
        sequences = consecutive_sequence(rest_data.index.tolist(), Threshold)
        result_dfs = [rest_data.loc[seq] for seq in sequences if len(seq) > 1]
        for df in result_dfs:
            if len(df) < NeglectFirstRows + NeglectLastRows:
                continue
            df = df.iloc[NeglectFirstRows:-NeglectLastRows]
            cell_cols = [f'cell{i}' for i in range(1, 15)]
            MAX = df[cell_cols].max(axis=1)
            MIN = df[cell_cols].min(axis=1)
            CellDV = MAX - MIN
            if CellDV.max() >= CellDVThreshold:
                CentralTendency = [df[f'cell{i}'].mean() for i in range(1, 15)]
                max_idx = np.argmax(CentralTendency)
                min_idx = np.argmin(CentralTendency)
                if abs(max_idx - min_idx) == 1:
                    Q1 = np.percentile(CentralTendency, 25)
                    Q3 = np.percentile(CentralTendency, 75)
                    upper_limit = Q3 + Distance
                    lower_limit = Q1 - Distance
                    if (CentralTendency[max_idx] > upper_limit and 
                        CentralTendency[min_idx] < lower_limit):
                        Signal = 1
                        CellWithIssue = [
                            f"cell{min_idx + 1}",
                            f"cell{max_idx + 1}"
                        ]
                        break
        return {
            "detected": bool(Signal),
            "severity": "High" if Signal else "None",
            "locations": CellWithIssue if Signal else []
        }
    except Exception as e:
        logging.error(f"Solder issue detection failed: {str(e)}", exc_info=True)
        return {"detected": False, "severity": "Unknown", "locations": []}

def weld_issue_detection(parquet_data):
    """Detect weld issues using data from the .parquet file"""
    try:
        Signal = 0
        CellWithIssue = None
        # Required columns
        required_cols = ['dsg_current', 'chg_current'] + [f'cell{i}' for i in range(1, 15)] + ['max_soc']
        if not validate_columns(parquet_data, required_cols):
            return {"detected": False, "confidence": 0.05, "cell_with_issue": None}
        # Parameters
        Threshold = 50
        valv = 0.02
        SoCCheck = 20
        NeglectFirstRows = 20
        NeglectLastRows = 10
        # Get SOC
        soc = float(parquet_data['max_soc'].iloc[0]) if 'max_soc' in parquet_data.columns else 0
        # Find rest periods
        rest_data = parquet_data[
            (parquet_data['dsg_current'] <= 1) & 
            (parquet_data['chg_current'] <= 1)
        ]
        if len(rest_data) < NeglectFirstRows + NeglectLastRows:
            return {"detected": False, "confidence": 0.05, "cell_with_issue": None}
        # Analyze sequences
        sequences = consecutive_sequence(rest_data.index.tolist(), Threshold)
        result_dfs = [rest_data.loc[seq] for seq in sequences if len(seq) > 1]
        for df in result_dfs:
            if len(df) < NeglectFirstRows + NeglectLastRows:
                continue
            filtered = df.iloc[NeglectFirstRows:-NeglectLastRows]
            if soc <= SoCCheck:
                cells = filtered[[f'cell{i}' for i in range(1, 15)]]
                CellDV = cells.max(axis=1) - cells.min(axis=1)
                if CellDV.min() >= valv:
                    Signal = 1
                    min_idx = CellDV.idxmin()
                    CellWithIssue = cells.loc[min_idx].idxmin()
                    break
        return {
            "detected": bool(Signal),
            "confidence": 0.95 if Signal else 0.05,
            "cell_with_issue": CellWithIssue
        }
        
    except Exception as e:
        logging.error(f"Weld issue detection failed: {str(e)}", exc_info=True)
        return {"detected": False, "confidence": 0.05, "cell_with_issue": None}